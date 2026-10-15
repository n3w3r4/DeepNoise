"""Run a 48 kHz mono WAV through DeepFilterNet in 10 ms blocks, paced at real time like a live mic.

Reports per-block timing, measured latency and noise-floor reduction, and writes the result.
Usage: python tools/bench_file.py your_48k_mono.wav [out.wav] [--level 100] [--atten 100]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # app modules live in the repo root

import argparse
import time
import wave

import numpy as np

from ladspa_df import SAMPLE_RATE, DeepFilterMono
from mixer import DryWetMixer

HOP = 480  # 10 ms at 48 kHz


def read_wav(path):
    with wave.open(path) as w:
        if w.getframerate() != SAMPLE_RATE or w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise SystemExit("expected 48 kHz, mono, 16-bit WAV")
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768


def write_wav(path, x):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def db(s):
    return 10 * np.log10(np.mean(s**2) + 1e-12)


def estimate_lag(x, y, max_lag):
    """Lag of y behind x, from cross-correlating 10 ms energy envelopes."""
    env = lambda s: np.convolve(s**2, np.ones(HOP) / HOP, "same")
    ex = env(x)
    ex -= ex.mean()
    ey = env(y)
    best, best_lag = -np.inf, 0
    for lag in range(0, max_lag, 48):
        seg = ey[lag : lag + len(x)]
        score = np.dot(ex, seg - seg.mean())
        if score > best:
            best, best_lag = score, lag
    return best_lag


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--level", type=float, default=100, help="suppression level (dry/wet), 0-100 %%")
    ap.add_argument("--atten", type=float, default=100, help="DeepFilterNet attenuation limit, dB")
    args = ap.parse_args()

    x = read_wav(args.wav)
    tail = SAMPLE_RATE  # 1 s of silence flushes the plugin's internal buffers
    x_pad = np.concatenate([x, np.zeros(tail, np.float32)])
    df = DeepFilterMono(controls={"Attenuation Limit": args.atten})

    wet, block_ms = [], []
    next_t = time.perf_counter()
    for i in range(0, len(x_pad) - HOP + 1, HOP):
        t = time.perf_counter()
        wet.append(df.process(x_pad[i : i + HOP]))
        block_ms.append((time.perf_counter() - t) * 1000)
        next_t += HOP / SAMPLE_RATE
        wait = next_t - time.perf_counter()
        if wait > 0:
            time.sleep(wait)
    df.close()
    wet = np.concatenate(wet)

    lag = estimate_lag(x, wet, tail)
    wet = wet[lag : lag + len(x)]
    y = DryWetMixer(args.level).mix_aligned(x, wet)

    # Noise floor = quietest 20 % of 20 ms frames (pauses between words).
    frames = lambda s: s[: len(s) // 960 * 960].reshape(-1, 960)
    quiet = np.argsort(np.mean(frames(x) ** 2, 1))[: len(frames(x)) // 5]
    nf_in, nf_out = db(frames(x)[quiet]), db(frames(y)[quiet])
    bm = np.array(block_ms)
    print(f"audio {len(x) / SAMPLE_RATE:.1f} s | bloco: média {bm.mean():.2f} ms, p99 {np.percentile(bm, 99):.2f} ms, pior {bm.max():.2f} ms (orçamento 10 ms)")
    print(f"latência do plugin: {lag} amostras = {lag / 48:.0f} ms")
    print(f"nível total: {db(x):.1f} dB -> {db(y):.1f} dB")
    print(f"ruído de fundo (pausas): {nf_in:.1f} dB -> {nf_out:.1f} dB  (redução {nf_in - nf_out:.1f} dB)")
    if args.out:
        write_wav(args.out, y)
        print(f"salvo: {args.out}")


if __name__ == "__main__":
    main()
