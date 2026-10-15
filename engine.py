"""Audio engine shared by the desktop UI (app.py).

Mic chain:
  physical mic -> high-pass -> echo cancel (AEC3, far-end = speaker chain) -> DeepFilterNet3
  -> distant-voice gate -> pause gate -> dry/wet blend -> mute -> virtual mic (CABLE Input)
                                                                      -> optional monitor (headset)
Speaker chain (incoming audio):
  apps play into a virtual cable -> DeepFilterNet3 -> dry/wet -> headset ; output also feeds AEC.

Devices are referred to by name, so a restart (device unplugged, PortAudio re-init) can
reopen them. A watchdog (called from the main thread) restarts everything when a stream
dies or stops calling back (device removed, format changed, exclusive mode taken...).
"""

import sys
import threading
import time

import numpy as np
import sounddevice as sd

from ladspa_df import SAMPLE_RATE, DeepFilterMono
from mixer import DryWetMixer, HighPass, NoiseGate
from realtime import boost

HOP = 480  # 10 ms
PLUGIN_LATENCY = 1920  # 40 ms, measured with bench_file.py

DEFAULTS = {
    "enabled": True,        # mic noise cancellation on/off (off = audio passes through)
    "level": 100.0,         # mic suppression level 0-100 (dry/wet)
    "pf": 0.02,             # DeepFilterNet post-filter beta 0-0.05
    "gate": -50.0,          # pause gate threshold dB, None = off
    "hpf": 100.0,           # high-pass cutoff Hz, None = off
    "monitor": False,       # also play the clean mic to the monitor device
    "aec": True,            # echo cancellation (active only with the speaker chain on)
    "bvc": False,           # distant-voice suppression (experimental)
    "bvc_threshold": None,  # dB, set by voice calibration
    "spk_enabled": False,   # speaker chain on/off
    "spk_level": 100.0,     # speaker suppression level 0-100
    "lock_mic": None,       # lock Windows mic volume at this percent, None = off
    "hotkey": True,         # Ctrl+Alt+M toggles mute
    "lang": None,           # UI language: "pt-BR", "en-US", or None = follow Windows
}


def db(x):
    return float(10 * np.log10(np.mean(np.square(x, dtype=np.float32)) + 1e-12))


def wasapi_index():
    for i, api in enumerate(sd.query_hostapis()):
        if "WASAPI" in api["name"]:
            return i
    raise RuntimeError("WASAPI host API not found")


def reinit_portaudio():
    """Refresh PortAudio's device list (it is fixed at initialization). All streams must be closed."""
    sd._terminate()
    sd._initialize()


def list_devices():
    """WASAPI devices by name: {"inputs": [{"name", "default"}], "outputs": [...]}."""
    api = wasapi_index()
    info = sd.query_hostapis(api)
    out = {"inputs": [], "outputs": []}
    for i, d in enumerate(sd.query_devices()):
        if d["hostapi"] != api:
            continue
        if d["max_input_channels"]:
            out["inputs"].append({"name": d["name"], "default": i == info["default_input_device"]})
        if d["max_output_channels"]:
            out["outputs"].append({"name": d["name"], "default": i == info["default_output_device"]})
    return out


def is_raw_mic(name):
    n = name.lower()
    return not any(k in n for k in ("krisp", "virtual", "mix", "sonar", "stream", "cable", "line ("))


def is_cable(name):
    return "cable" in name.lower()


def resolve(name, kind):
    """WASAPI device index for an exact name (or a name fragment), else None."""
    if not name:
        return None
    key = "max_input_channels" if kind == "input" else "max_output_channels"
    api = wasapi_index()
    devs = [(i, d) for i, d in enumerate(sd.query_devices()) if d["hostapi"] == api and d[key]]
    for i, d in devs:
        if d["name"] == name:
            return i
    for i, d in devs:
        if name.lower() in d["name"].lower():
            return i
    return None


def default_mic():
    devs = list_devices()["inputs"]
    raw = [d["name"] for d in devs if is_raw_mic(d["name"])]
    return raw[0] if raw else (devs[0]["name"] if devs else None)


class Ring:
    """Thread-safe FIFO between two audio clocks. Underflow -> zeros; if it grows beyond
    max_ms (drift), it is trimmed back to target_ms."""

    def __init__(self, target_ms=30, max_ms=120):
        self.target = int(SAMPLE_RATE * target_ms / 1000)
        self.max = int(SAMPLE_RATE * max_ms / 1000)
        self.buf = np.zeros(0, np.float32)
        self.lock = threading.Lock()

    def write(self, x):
        with self.lock:
            self.buf = np.concatenate([self.buf, x])
            if len(self.buf) > self.max:
                self.buf = self.buf[-self.target:]

    def read(self, n):
        with self.lock:
            if len(self.buf) >= n:
                out, self.buf = self.buf[:n], self.buf[n:]
                return out
        return np.zeros(n, np.float32)

    def clear(self):
        with self.lock:
            self.buf = np.zeros(0, np.float32)


class DiagRecorder:
    """Ring buffer with the last `seconds` of mic (after high-pass/AEC), denoiser output and final output."""

    def __init__(self, seconds=60):
        self.n = seconds * SAMPLE_RATE
        self.buf = np.zeros((3, self.n), np.float32)
        self.pos = 0
        self.filled = 0

    def push(self, dry, wet, out):
        k = len(dry)
        idx = (self.pos + np.arange(k)) % self.n
        self.buf[0, idx], self.buf[1, idx], self.buf[2, idx] = dry, wet, out
        self.pos = (self.pos + k) % self.n
        self.filled = min(self.filled + k, self.n)

    def snapshot(self):
        order = (self.pos - self.filled + np.arange(self.filled)) % self.n
        return self.buf[:, order].copy()


class EchoCanceller:
    """WebRTC AEC3 (via livekit's AudioProcessingModule) on 10 ms int16 frames."""

    def __init__(self, delay_ms=40):
        from livekit import rtc

        self.rtc = rtc
        self.apm = rtc.AudioProcessingModule(echo_cancellation=True)
        self.apm.set_stream_delay_ms(delay_ms)

    def _frame(self, x):
        return self.rtc.AudioFrame((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes(), SAMPLE_RATE, 1, len(x))

    def process(self, near, far):
        self.apm.process_reverse_stream(self._frame(far))
        f = self._frame(near)
        self.apm.process_stream(f)
        return np.frombuffer(bytes(f.data), np.int16).astype(np.float32) / 32767


class AudioEngine:
    """Owns all streams. start()/stop()/watchdog() must run on the main (COM) thread."""

    def __init__(self, settings=None, devices=None):
        self.settings = {**DEFAULTS, **(settings or {})}
        self.devices = {"input": None, "output": None, "monitor": None, "spk_input": None, "spk_output": None}
        self.devices.update(devices or {})
        self.streams = {}
        self.dfs = []
        self.beats = {}
        self.xruns = 0
        self.muted = False
        self.status = "stopped"  # stopped | running | waiting | error
        self.error = None
        self.waiting_for = None
        self._meter_lock = threading.Lock()
        self._meter = {"in_db": -120.0, "out_db": -120.0, "spk_in_db": -120.0, "spk_out_db": -120.0}
        self.diag = DiagRecorder()
        self.far = Ring(target_ms=20, max_ms=200)   # speaker output -> AEC reference
        self.mon = Ring(target_ms=30, max_ms=120)   # mic output -> monitor stream
        self._calib = None
        self.aec = None

    # --- settings -------------------------------------------------------------------
    def apply(self, **changes):
        for k, v in changes.items():
            if k in DEFAULTS:
                self.settings[k] = v
        s = self.settings
        if "mic" in self.streams:
            self.mic_mixer.level = s["level"] if s["enabled"] else 0.0
            self.mic_df.set_control("Post Filter Beta", min(max(float(s["pf"]), 0.0), 0.05))
            self.gate.threshold_db = None if s["gate"] is None or not s["enabled"] else float(s["gate"])
            self.bvc.threshold_db = (float(s["bvc_threshold"]) if s["bvc"] and s["enabled"] and s["bvc_threshold"] is not None
                                     else None)
            want = None if s["hpf"] is None else float(s["hpf"])
            if want != self.hpf.cutoff_hz:
                self.hpf.set_cutoff(want)
        if "spk" in self.streams:
            self.spk_mixer.level = float(s["spk_level"])

    def needs_restart(self, changes):
        """Settings that add/remove streams require a restart."""
        return any(k in changes for k in ("monitor", "spk_enabled"))

    # --- lifecycle --------------------------------------------------------------------
    def _beat(self, name):
        self.beats[name] = time.monotonic()

    def start(self):
        applied = boost()
        if applied:
            print("realtime:", ", ".join(applied), file=sys.stderr, flush=True)
        self.stop()
        reinit_portaudio()
        self.error = self.waiting_for = None
        s, d = self.settings, self.devices
        # First run only: pick sensible devices. A saved device that is missing is waited for instead.
        if not d["input"]:
            d["input"] = default_mic()
        if not d["output"]:
            outs = [o["name"] for o in list_devices()["outputs"]]
            cables = [o for o in outs if is_cable(o) and "hi-fi" not in o.lower()]
            d["output"] = cables[0] if cables else next((o["name"] for o in list_devices()["outputs"] if o["default"]), None)
        try:
            self._start_mic()
            if s["monitor"] and d["monitor"]:
                self._start_monitor()
            if s["spk_enabled"]:
                self._start_speaker()
            self.apply()
            self.status = "running"
        except LookupError as e:  # a selected device is not present (unplugged)
            self.stop()
            self.status, self.waiting_for = "waiting", str(e)
        except Exception as e:
            self.stop()
            self.status, self.error = "error", str(e)

    def _open(self, name, kind):
        idx = resolve(name, kind)
        if idx is None:
            raise LookupError(name)
        return idx

    def _start_mic(self):
        d = self.devices
        dev_in = self._open(d["input"], "input")
        dev_out = self._open(d["output"], "output")
        out_ch = min(2, sd.query_devices(dev_out)["max_output_channels"])
        self.mic_df = DeepFilterMono()
        self.dfs.append(self.mic_df)
        self.mic_mixer = DryWetMixer(delay_samples=PLUGIN_LATENCY)
        self.gate = NoiseGate(hold=0.25)
        self.bvc = NoiseGate(floor_db=-30.0, hold=0.3, release=0.08)
        self.hpf = HighPass(None)
        if self.aec is None:
            try:
                self.aec = EchoCanceller()
            except Exception as e:  # livekit missing: run without AEC
                print(f"AEC unavailable: {e}", file=sys.stderr)
                self.aec = False
        self.far.clear()
        self.mon.clear()

        def cb(indata, outdata, frames, _t, status):
            self._beat("mic")
            if status:
                self.xruns += 1
            s = self.settings
            x = self.hpf.process(indata[:, 0].copy())
            if self.aec and s["aec"] and "spk" in self.streams:
                x = self.aec.process(x, self.far.read(frames))
            raw_wet = self.mic_df.process(x)
            wet = self.gate.process(self.bvc.process(raw_wet))
            y = self.mic_mixer.mix_block(x, wet)
            if self.muted:
                y = np.zeros_like(y)
            outdata[:] = np.repeat(y[:, None], out_ch, axis=1)
            if "monitor" in self.streams:
                self.mon.write(y)
            self.diag.push(x, raw_wet, y)
            if self._calib is not None:
                self._calib.append(db(raw_wet))
            with self._meter_lock:
                m = self._meter
                m["in_db"] = 0.8 * m["in_db"] + 0.2 * db(x)
                m["out_db"] = 0.8 * m["out_db"] + 0.2 * db(y)

        self.streams["mic"] = self._stream(cb, (dev_in, dev_out), (1, out_ch))

    def _start_monitor(self):
        dev = self._open(self.devices["monitor"], "output")
        ch = min(2, sd.query_devices(dev)["max_output_channels"])

        def cb(outdata, frames, _t, status):
            self._beat("monitor")
            outdata[:] = np.repeat(self.mon.read(frames)[:, None], ch, axis=1)

        wasapi = sd.WasapiSettings(auto_convert=True)
        st = sd.OutputStream(samplerate=SAMPLE_RATE, blocksize=HOP, dtype="float32", device=dev, channels=ch,
                             latency="low", extra_settings=wasapi, callback=cb)
        st.start()
        self.streams["monitor"] = st

    def _start_speaker(self):
        d = self.devices
        dev_in = self._open(d["spk_input"], "input")
        dev_out = self._open(d["spk_output"], "output")
        in_ch = min(2, sd.query_devices(dev_in)["max_input_channels"])
        out_ch = min(2, sd.query_devices(dev_out)["max_output_channels"])
        self.spk_df = DeepFilterMono()
        self.dfs.append(self.spk_df)
        self.spk_mixer = DryWetMixer(delay_samples=PLUGIN_LATENCY)

        def cb(indata, outdata, frames, _t, status):
            self._beat("spk")
            if status:
                self.xruns += 1
            x = indata.mean(axis=1).astype(np.float32)  # voice calls are effectively mono
            y = self.spk_mixer.mix_block(x, self.spk_df.process(x))
            outdata[:] = np.repeat(y[:, None], out_ch, axis=1)
            self.far.write(y)
            with self._meter_lock:
                m = self._meter
                m["spk_in_db"] = 0.8 * m["spk_in_db"] + 0.2 * db(x)
                m["spk_out_db"] = 0.8 * m["spk_out_db"] + 0.2 * db(y)

        self.streams["spk"] = self._stream(cb, (dev_in, dev_out), (in_ch, out_ch))

    def _stream(self, cb, devices, channels):
        wasapi = sd.WasapiSettings(auto_convert=True)  # Windows resamples devices not at 48 kHz
        st = sd.Stream(samplerate=SAMPLE_RATE, blocksize=HOP, dtype="float32", device=devices, channels=channels,
                       latency="low", extra_settings=(wasapi, wasapi), callback=cb)
        st.start()
        return st

    def stop(self):
        for st in self.streams.values():
            try:
                st.stop()
                st.close()
            except Exception:
                pass
        self.streams = {}
        for df in self.dfs:
            df.close()
        self.dfs = []
        self.beats = {}
        if self.status == "running":
            self.status = "stopped"

    def watchdog(self):
        """Main thread, ~1 Hz. Returns a reason string if it restarted, else None."""
        now = time.monotonic()
        if self.status in ("waiting", "error"):
            if now < getattr(self, "_next_retry", 0):
                return None
            self._next_retry = now + 3  # start() re-inits PortAudio, so a re-plugged device is found
            before = self.waiting_for or self.error
            self.start()
            return f"reconnect ({before}) -> {self.status}"
        for name, st in list(self.streams.items()):
            beat = self.beats.get(name, now)
            if not st.active or now - beat > 1.5:
                reason = f"stream '{name}' parou"
                self.start()
                return reason
        return None

    # --- features -----------------------------------------------------------------------
    def toggle_mute(self):
        self.muted = not self.muted
        return self.muted

    def calibrate_voice(self, seconds=5.0):
        """Record the denoised level while the user speaks; distant voices are gated below
        (user's typical speech level - 15 dB). Blocks the calling (HTTP) thread."""
        self._calib = []
        time.sleep(seconds)
        levels, self._calib = np.array(self._calib), None
        speech = levels[levels > -60]
        if len(speech) < 50:  # < 0.5 s of speech
            raise ValueError("no_speech")  # UI shows a translated message for this code
        voice = float(np.percentile(speech, 50))
        threshold = round(voice - 15.0, 1)
        self.apply(bvc_threshold=threshold, bvc=True)
        return {"voice_db": round(voice, 1), "threshold_db": threshold}

    @property
    def running(self):
        return self.status == "running"

    def meters(self):
        with self._meter_lock:
            return dict(self._meter, xruns=self.xruns, running=self.running, status=self.status,
                        muted=self.muted, waiting_for=self.waiting_for)
