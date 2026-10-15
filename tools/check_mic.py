"""Silent mic test: capture N seconds through DeepFilterNet, play nothing, print levels per second
and save logs/mic_original.wav and logs/mic_denoised.wav for listening.

  python check_mic.py [-i "QuadCast"] [--seconds 10] [--gain 0]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # app modules live in the repo root

import argparse
import time
from pathlib import Path

import numpy as np
import sounddevice as sd

from bench_file import write_wav
from engine import HOP, PLUGIN_LATENCY, db, default_mic, resolve
from ladspa_df import SAMPLE_RATE, DeepFilterMono

SAMPLES = Path(__file__).resolve().parent.parent / "logs"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input")
    ap.add_argument("--seconds", type=float, default=10)
    ap.add_argument("--gain", type=float, default=0, help="input gain in dB before denoising")
    args = ap.parse_args()

    dev = resolve(args.input or default_mic(), "input")
    if dev is None:
        raise SystemExit(f"microphone not found: {args.input}")
    print(f"input: {sd.query_devices(dev)['name']}")
    df = DeepFilterMono()
    gain = 10 ** (args.gain / 20)
    blocks, xruns, cb_ms = [], 0, []

    def callback(indata, frames, _time, status):
        nonlocal xruns
        xruns += bool(status)
        t = time.perf_counter()
        dry = indata[:, 0] * gain
        blocks.append((dry, df.process(dry)))
        cb_ms.append((time.perf_counter() - t) * 1000)

    wasapi = sd.WasapiSettings(auto_convert=True)
    print(f"recording {args.seconds:.0f} s: talk now, with a pause in the middle (noise only)")
    with sd.InputStream(samplerate=SAMPLE_RATE, blocksize=HOP, dtype="float32", device=dev,
                        channels=1, latency="low", extra_settings=wasapi, callback=callback):
        for s in range(int(args.seconds)):
            time.sleep(1)
            recent = blocks[-100:]
            if recent:
                d = np.concatenate([b[0] for b in recent])
                w = np.concatenate([b[1] for b in recent])
                print(f"  {s + 1:2d}s  original {db(d):6.1f} dB (pico {20 * np.log10(np.abs(d).max() + 1e-9):6.1f})"
                      f" | filtrado {db(w):6.1f} dB")
    df.close()

    dry = np.concatenate([b[0] for b in blocks])
    wet = np.concatenate([b[1] for b in blocks])[PLUGIN_LATENCY:]
    SAMPLES.mkdir(exist_ok=True)
    write_wav(str(SAMPLES / "mic_original.wav"), dry)
    write_wav(str(SAMPLES / "mic_denoised.wav"), wet)
    print(f"blocks {len(blocks)} | stream dropouts {xruns} | worst callback {max(cb_ms):.2f} ms")
    print(f"total: original {db(dry):.1f} dB | filtrado {db(wet):.1f} dB")
    print(f"salvos: {SAMPLES / 'mic_original.wav'} e {SAMPLES / 'mic_denoised.wav'}")


if __name__ == "__main__":
    main()
