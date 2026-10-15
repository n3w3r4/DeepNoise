"""Analyze a diagnostic capture: levels over time, dry->wet lag drift, repeated segments in the output.
Usage: python tools/analyze_diag.py logs/diag-YYYYmmdd-HHMMSS
"""
import sys
import wave

import numpy as np

SR = 48000


def load(path):
    with wave.open(path) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768


def db(x):
    return 10 * np.log10(np.mean(x**2) + 1e-12)


def lag_ms(a, b, max_ms=600):
    """Lag of b behind a using 2.5 ms energy envelopes (only meaningful when a has energy)."""
    k = 120
    ea = np.convolve(a**2, np.ones(k), "valid")[::k]
    eb = np.convolve(b**2, np.ones(k), "valid")[::k]
    ea = ea - ea.mean()
    best, best_l = -np.inf, 0
    for l in range(0, int(max_ms / 2.5)):
        seg = eb[l:l + len(ea) - int(max_ms / 2.5)]
        sc = np.dot(ea[: len(seg)], seg - seg.mean())
        if sc > best:
            best, best_l = sc, l
    return best_l * 2.5


def repeats(x, win=0.05, search=2.0, thr=0.97, min_db=-55):
    """Windows of x that almost exactly duplicate audio from 20 ms..search s earlier."""
    w, hits = int(win * SR), []
    for start in range(int(search * SR), len(x) - w, w):
        seg = x[start:start + w]
        if db(seg) < min_db:
            continue
        hist = x[start - int(search * SR):start - int(0.02 * SR) + w]
        c = np.correlate(hist, seg, "valid")
        energy = np.sqrt(np.convolve(hist**2, np.ones(w), "valid") * np.sum(seg**2)) + 1e-9
        r = c / energy
        i = int(np.argmax(r))
        if r[i] > thr:
            back = (start - (start - int(search * SR) + i)) / SR
            hits.append((start / SR, back, float(r[i]), db(seg)))
    return hits


base = sys.argv[1]
mic, df, out = (load(f"{base}-{n}.wav") for n in ("1-microfone", "2-deepfilternet", "3-saida"))
n = len(mic)
print(f"duração {n / SR:.1f} s")
print("\n  t(s)   mic dB   DF dB   saída dB   lag mic->DF (ms)")
for t in range(0, int(n / SR)):
    a, b, c = (s[t * SR:(t + 1) * SR] for s in (mic, df, out))
    lag = lag_ms(mic[t * SR:(t + 1) * SR + int(0.6 * SR)], df[t * SR:(t + 1) * SR + int(0.6 * SR)]) if db(a) > -50 else float("nan")
    print(f"  {t:4d}  {db(a):7.1f}  {db(b):7.1f}  {db(c):8.1f}   {lag:6.1f}")

for name, sig in (("saída", out), ("DeepFilterNet", df), ("microfone", mic)):
    h = repeats(sig)
    print(f"\ntrechos repetidos em {name}: {len(h)}")
    for t, back, r, lv in h[:25]:
        print(f"  em {t:6.2f}s repete áudio de {back * 1000:6.0f} ms antes (corr {r:.3f}, {lv:.0f} dB)")
