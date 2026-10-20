"""Speech-energy helpers on work/audio16k.wav.

    python3 timing.py pauses 57.3 59.5      # internal pauses (>= 70 ms) in a source range
    words(s, e, "romanised words ...")       # word timings spread over the voiced parts of [s, e]
"""
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.io import wavfile

HERE = Path(__file__).resolve().parent
HOP = 0.01


@lru_cache(None)
def env_db():
    sr, a = wavfile.read(HERE / "work" / "audio16k.wav")
    a = a.astype(np.float32) / 32768
    n = int(sr * HOP)
    m = len(a) // n
    fr = a[: m * n].reshape(m, n)
    rms = np.sqrt((fr ** 2).mean(1) + 1e-10)
    db = 20 * np.log10(rms)
    return np.convolve(db, np.ones(3) / 3, mode="same")


def voiced(s, e, rel=24.0):
    db = env_db()
    i0, i1 = int(s / HOP), int(e / HOP)
    seg = db[i0:i1]
    if len(seg) == 0:
        return np.zeros(0, bool)
    thr = np.percentile(seg, 92) - rel
    return seg > thr


def pauses(s, e, min_len=0.07):
    v = voiced(s, e)
    out, run = [], None
    for i, on in enumerate(v):
        if not on and run is None:
            run = i
        elif on and run is not None:
            if (i - run) * HOP >= min_len:
                out.append((round(s + run * HOP, 2), round(s + i * HOP, 2)))
            run = None
    return out


def speech_bounds(s, e):
    """tighten [s, e] to the first / last voiced frame."""
    v = voiced(s, e)
    idx = np.nonzero(v)[0]
    if not len(idx):
        return s, e
    return s + idx[0] * HOP, s + (idx[-1] + 1) * HOP


def words(s, e, txt):
    """[(word, ws, we)] across the voiced time of [s, e], weighted by letters (+1 per word)."""
    ws = txt.split()
    v = voiced(s, e).astype(np.float32)
    if v.sum() < 3:
        v[:] = 1
    cum = np.concatenate([[0], np.cumsum(v)])
    tot = cum[-1]
    wts = np.array([len(w.strip(".,!?")) + 1.5 for w in ws], np.float32)
    edges = np.concatenate([[0], np.cumsum(wts)]) / wts.sum() * tot
    out = []
    for i, w in enumerate(ws):
        a = np.searchsorted(cum, edges[i], side="right") - 1
        b = np.searchsorted(cum, edges[i + 1], side="left")
        out.append((w, round(s + a * HOP, 3), round(s + max(a + 1, b) * HOP, 3)))
    return out


if __name__ == "__main__":
    if sys.argv[1] == "pauses":
        s, e = float(sys.argv[2]), float(sys.argv[3])
        print("bounds", [round(x, 2) for x in speech_bounds(s, e)])
        for p in pauses(s, e):
            print(p)
