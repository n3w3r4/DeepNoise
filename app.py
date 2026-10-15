"""DeepNoise desktop app: audio engine + local HTTP UI + tray icon with a quick-actions flyout.

  python app.py              # tray icon + main window; closing the window keeps running in the tray
  python app.py --tray       # start in the tray only (used by "Start with Windows")
  python app.py --no-window  # no tray/windows, only serve http://127.0.0.1:<port>/ (debugging)

Threading: PortAudio/WASAPI and Core Audio (COM) calls run on the main thread. HTTP handler
threads hand device operations to it through App.run_main(); the main loop also runs the
watchdog (stream health, device hot-plug), the mic volume lock and the trend log.
"""

import argparse
import gc
import json
import os
import queue
import sys
import threading
import time
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np

import desktop
import winaudio
import windows
from local_api import allowed_request, read_json_body
from engine import DEFAULTS, AudioEngine, is_cable, is_raw_mic

FROZEN = getattr(sys, "frozen", False)
ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))  # bundled resources (ui/, vendor/)
DATA = Path(os.environ["APPDATA"]) / "DeepNoise" if FROZEN else Path(__file__).parent  # user data
UI = ROOT / "ui"
CONFIG = DATA / "settings.json"
LOG = DATA / "logs" / "deepnoise.log"
STATIC = {"/": "index.html", "/index.html": "index.html", "/flyout.html": "flyout.html",
          "/api.js": "api.js", "/style.css": "style.css", "/i18n.js": "i18n.js", "/icon.png": "icon.png"}
TYPES = {".png": "image/png", ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8"}
desktop.ICON_SOURCE = UI / "icon.png"  # tray icon base (built from assets/app-icon/deepnoise-source.png)
DEVICE_KEYS = ("input", "output", "monitor", "spk_input", "spk_output")


def log(msg):
    print(f"{time.strftime('%H:%M:%S')} {msg}", file=sys.stderr, flush=True)


def load_config():
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(cfg):
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


class App:
    def __init__(self):
        cfg = load_config()
        devices = {k: cfg.get(k) for k in DEVICE_KEYS}
        self.engine = AudioEngine({**DEFAULTS, **cfg.get("settings", {})}, devices)
        self.lock = threading.Lock()
        self.jobs = queue.Queue()
        # Core Audio (COM) objects must be created *and released* on the audio thread only: a COM
        # pointer freed by the garbage collector on another thread/apartment crashes the process.
        self.endpoints = frozenset()
        self.usage = {"mic": [], "voice": [], "spk": []}
        self.mic_volume = None
        self.hotkey_ok = None
        self.win = None  # windows.Windows (None with --no-window)
        self.quitting = threading.Event()

    def quit(self):
        self.quitting.set()
        if self.win:
            self.win.quit()  # destroys the windows -> webview.start() returns on the main thread

    # --- audio-thread executor -----------------------------------------------------------
    def run_main(self, fn):
        """Run fn on the audio thread (the one that owns PortAudio/COM) and return its result."""
        done, box = threading.Event(), {}
        self.jobs.put((fn, done, box))
        done.wait()
        if "error" in box:
            raise box["error"]
        return box.get("result")

    def pump(self, timeout):
        try:
            fn, done, box = self.jobs.get(timeout=timeout)
        except queue.Empty:
            return
        try:
            box["result"] = fn()
        except Exception as e:
            box["error"] = e
        done.set()

    # --- config -----------------------------------------------------------------------
    def save(self):
        save_config({**self.engine.devices, "settings": dict(self.engine.settings)})

    def state(self):
        e = self.engine
        caps = sorted({n for n, f in self.endpoints if f == "capture"})
        rends = sorted({n for n, f in self.endpoints if f == "render"})
        return {
            "devices": {
                "inputs": [{"name": n, "raw": is_raw_mic(n), "cable": is_cable(n)} for n in caps],
                "outputs": [{"name": n, "cable": is_cable(n)} for n in rends],
            },
            "selected": dict(e.devices),
            "settings": e.settings,
            "status": e.status, "running": e.running, "error": e.error, "waiting_for": e.waiting_for,
            "muted": e.muted,
            "aec_available": e.aec is not False,
            "usage": self.usage,
            "voice_device": winaudio.cable_capture_side(e.devices["output"], set(caps)),
            "mic_volume": self.mic_volume,
            "hotkey_ok": self.hotkey_ok,
            "autostart": desktop.get_autostart(),
        }

    # --- actions (HTTP threads) ----------------------------------------------------------
    def select(self, data):
        with self.lock:
            for k in DEVICE_KEYS:
                if k in data:
                    self.engine.devices[k] = data[k]
            self.run_main(self.engine.start)
            self.save()

    def settings(self, data):
        with self.lock:
            if "autostart" in data:
                desktop.set_autostart(bool(data.pop("autostart")))
                log(f"start with Windows: {desktop.get_autostart()}")
            self.engine.apply(**data)
            if self.engine.needs_restart(data):
                self.run_main(self.engine.start)
            self.save()

    def save_diag(self):
        snap = self.engine.diag.snapshot()
        stamp = time.strftime("%Y%m%d-%H%M%S")
        paths = []
        for row, name in zip(snap, ("1-mic", "2-deepfilternet", "3-output")):
            p = LOG.parent / f"diag-{stamp}-{name}.wav"
            with wave.open(str(p), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(48000)
                w.writeframes((np.clip(row, -1, 1) * 32767).astype(np.int16).tobytes())
            paths.append(str(p))
        log(f"diagnostics saved: {paths[0]} (+2)")
        return paths

    # --- periodic work (main thread) ------------------------------------------------------
    def tick_fast(self):
        """~1 Hz: stream health and mic volume lock."""
        reason = self.engine.watchdog()
        if reason:
            log(f"watchdog: {reason}")
        e = self.engine
        lock = e.settings["lock_mic"]
        if lock is not None and e.devices["input"]:
            if not hasattr(self, "_vol"):
                self._vol = winaudio.EndpointVolume()
            if self._vol.lock(e.devices["input"], float(lock)):
                log(f"mic volume restored to {lock}% (another app changed it)")

    def tick_slow(self):
        """~0.3 Hz (audio thread): device hot-plug and which apps use our devices."""
        eps = winaudio.active_endpoints()
        if eps != self.endpoints:
            gone = {n for n, _ in self.endpoints - eps}
            new = {n for n, _ in eps - self.endpoints}
            self.endpoints = eps
            log(f"devices changed: +{sorted(new)} -{sorted(gone)}")
            e = self.engine
            selected = {v for k, v in e.devices.items() if v}
            if e.status != "running" or gone & selected:
                e.start()
                log(f"restarted after a device change -> {e.status}")
        e = self.engine
        caps = {n for n, f in self.endpoints if f == "capture"}
        voice = winaudio.cable_capture_side(e.devices["output"], caps)
        spk_render = None
        if e.devices["spk_input"] and "output" in e.devices["spk_input"].lower():
            i = e.devices["spk_input"].lower().index("output")
            spk_render = e.devices["spk_input"][:i] + "Input" + e.devices["spk_input"][i + 6:]
        self.usage = {
            "mic": winaudio.apps_using(e.devices["input"]),
            "voice": winaudio.apps_using(voice) if voice else [],
            "spk": winaudio.apps_using(spk_render) if spk_render else [],
        }
        if not hasattr(self, "_vol_reader"):
            self._vol_reader = winaudio.EndpointVolume()
        self.mic_volume = self._vol_reader.read(e.devices["input"])


APP = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _allowed(self):
        if not allowed_request(self.headers, self.server.server_address[1], self.command):
            self._json({"error": "forbidden"}, 403)
            return False
        return True

    def do_GET(self):
        if not self._allowed():
            return
        if self.path in STATIC:
            f = UI / STATIC[self.path]
            body = f.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", TYPES[f.suffix])
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/state":
            self._json(APP.state())
        elif self.path == "/api/meters":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            try:
                while True:
                    self.wfile.write(f"data: {json.dumps(APP.engine.meters())}\n\n".encode())
                    self.wfile.flush()
                    time.sleep(0.05)
            except (ConnectionError, OSError):
                return
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        if not self._allowed():
            return
        try:
            data = read_json_body(self.headers, self.rfile)
        except ValueError as exc:
            return self._json({"error": str(exc)}, 400)
        try:
            if self.path == "/api/select":
                APP.select(data)
            elif self.path == "/api/settings":
                APP.settings(data)
            elif self.path == "/api/mute":
                log(f"muted: {APP.engine.toggle_mute()}")
            elif self.path == "/api/calibrate":
                result = APP.engine.calibrate_voice()
                APP.save()
                log(f"voice calibration: {result}")
                return self._json({**APP.state(), "calibration": result})
            elif self.path == "/api/window/open":
                if APP.win:
                    APP.win.open_main()
                return self._json({"ok": True})
            elif self.path == "/api/window/toggle-flyout":  # same as a left click on the tray icon
                if APP.win:
                    APP.win.toggle_flyout()
                return self._json({"ok": True})
            elif self.path == "/api/window/hide-flyout":
                if APP.win:
                    APP.win.hide_flyout()
                return self._json({"ok": True})
            elif self.path == "/api/quit":
                APP.quit()
                return self._json({"ok": True})
            elif self.path == "/api/diag":
                return self._json({"saved": APP.save_diag()})
            else:
                return self._json({"error": "not found"}, 404)
            self._json(APP.state())
        except Exception as e:
            self._json({**APP.state(), "error": str(e)}, 500)


def redirect_logs():
    """Send stderr (ours and the Rust plugin's warnings such as "Underrun detected") to logs/deepnoise.log.
    Under pythonw there is no console, so without this the plugin's diagnostics are lost."""
    LOG.parent.mkdir(parents=True, exist_ok=True)
    f = open(LOG, "a", buffering=1, encoding="utf-8")
    os.dup2(f.fileno(), 2)
    sys.stderr = f
    import faulthandler

    faulthandler.enable(f, all_threads=True)  # native crashes (access violations) leave a Python stack in the log
    from version import VERSION

    print(f"=== {time.strftime('%Y-%m-%d %H:%M:%S')} DeepNoise {VERSION} started ===", file=sys.stderr)


INSTANCE = DATA / "instance.json"


def single_instance(tray_only):
    """One DeepNoise per user. A second launch asks the running one to show its window, then exits."""
    import ctypes

    ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\DeepNoise.SingleInstance")
    if ctypes.windll.kernel32.GetLastError() != 183:  # ERROR_ALREADY_EXISTS
        return True
    try:
        port = json.loads(INSTANCE.read_text(encoding="utf-8"))["port"]
        if not tray_only:
            import urllib.request

            urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/api/window/open", data=b"{}", headers={"Content-Type": "application/json", "X-DeepNoise-Request": "1"}), timeout=3)
        log(f"already running (port {port}); asked the running instance to show its window")
    except Exception as e:
        log(f"already running; could not reach the running instance: {e}")
    return False


def main():
    global APP
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-window", action="store_true", help="no tray/windows (debug)")
    ap.add_argument("--tray", action="store_true", help="start in the tray without opening the main window")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--console", action="store_true", help="keep logs on the console instead of logs/deepnoise.log")
    ap.add_argument("--config", help="settings file (default settings.json)")
    args = ap.parse_args()
    if args.config:
        global CONFIG
        CONFIG = Path(args.config)
    if not args.console:
        redirect_logs()
    if not args.no_window and not single_instance(args.tray):
        return

    APP = App()
    # Always registered; the "hotkey" setting only gates the action, so toggling it applies immediately.
    hk = winaudio.Hotkey(lambda: APP.engine.settings["hotkey"] and log(f"muted (hotkey): {APP.engine.toggle_mute()}"))
    APP.hotkey_ok = hk.ok
    log(f"hotkey Ctrl+Alt+M: {'ok' if hk.ok else 'unavailable (used by another app)'}")

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.daemon_threads = True
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    log(f"interface at {url}")
    if not args.no_window:
        INSTANCE.write_text(json.dumps({"port": server.server_address[1], "pid": os.getpid()}), encoding="utf-8")

    if args.no_window:
        try:
            audio_loop(None)
        except KeyboardInterrupt:
            pass
    else:
        import webview

        APP.win = windows.Windows(url, start_hidden=args.tray, on_quit=APP.quit)
        e = APP.engine
        tray = desktop.Tray(
            on_quick=APP.win.toggle_flyout,
            on_open=APP.win.open_main,
            on_mute=lambda: log(f"muted (tray): {e.toggle_mute()}"),
            on_toggle_nc=lambda: APP.settings({"enabled": not e.settings["enabled"]}),
            on_quit=APP.quit,
            get_state=lambda: {"lang": e.settings["lang"], "muted": e.muted, "enabled": e.settings["enabled"],
                               "status": e.status},
        )
        audio = threading.Thread(target=audio_loop, args=(tray,), daemon=True, name="audio")
        audio.start()
        webview.start(private_mode=False, storage_path=str(DATA / "webview"))  # GUI loop; returns on quit
        APP.quitting.set()
        audio.join(timeout=5)
        tray.stop()
    server.shutdown()
    log("stopped")


def audio_loop(tray):
    """Owns PortAudio and COM: engine start/restart, watchdog, device scan, volume lock, trend log."""
    import comtypes

    # MTA: an STA apartment would need a message pump, and WASAPI/Core Audio calls would block on it.
    comtypes.CoInitializeEx(comtypes.COINIT_MULTITHREADED)
    APP.endpoints = winaudio.active_endpoints()
    APP.engine.start()
    log(f"audio: {APP.engine.status} {APP.engine.error or ''}")
    last_fast = last_slow = last_trend = 0.0
    last_xruns, samples = 0, []
    try:
        while not APP.quitting.is_set():
            APP.pump(timeout=0.05)
            now = time.monotonic()
            if APP.win:
                APP.win.autohide()
            m = APP.engine.meters()
            if m["running"]:
                samples.append((m["in_db"], m["out_db"]))
            if now - last_fast >= 1:
                last_fast = now
                APP.tick_fast()
                if tray:
                    tray.refresh()
                if APP.engine.xruns != last_xruns:
                    log(f"stream: {APP.engine.xruns - last_xruns} buffer dropout(s) (total {APP.engine.xruns})")
                    last_xruns = APP.engine.xruns
            if now - last_slow >= 3:
                last_slow = now
                APP.tick_slow()
                gc.collect()  # free the scan's COM wrappers here, on the thread that created them
            if now - last_trend >= 30 and samples:
                last_trend = now
                ins = sorted(x[0] for x in samples)
                v = APP.mic_volume
                log(f"trend: mic volume {v[0] if v else '?'}% | mic noise floor {ins[len(ins) // 10]:.1f} dB | "
                    f"output avg {sum(x[1] for x in samples) / len(samples):.1f} dB | muted {APP.engine.muted}")
                samples.clear()
    finally:
        APP.engine.stop()


if __name__ == "__main__":
    main()
