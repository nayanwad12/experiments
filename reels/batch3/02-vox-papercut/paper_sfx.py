"""paper_sfx: paper foley synthesised in numpy (rustle, crumple, tear, snip, stamp, slap, tick, type, clack, pop,
whoosh, sparkle). Ported from vibe-editing-promo/audio.py at 48 kHz."""
import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
rng = np.random.default_rng(3)


def T(n):
    return np.arange(n) / SR


def ns(d):
    return rng.standard_normal(int(d * SR) + 1)


def filt(x, kind, f, order=2):
    return sosfilt(butter(order, f, kind, fs=SR, output="sos"), x)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def sfx_whoosh(d=0.38):
    n = int(d * SR)
    x = ns(d)[:n]
    out = np.zeros(n)
    seg = 24
    for s in range(seg):
        a, b = s * n // seg, (s + 1) * n // seg
        c = 500 * (5000 / 500) ** np.sin(np.pi * s / seg)
        out[a:b] = filt(x, "bandpass", [c * 0.6, c * 1.6])[a:b]
    k = T(n) / d
    return out * np.sin(np.pi * k) ** 2 * 1.4


def sfx_pop():
    n = int(0.12 * SR)
    t = T(n)
    f = 260 + 900 * np.exp(-t / 0.018)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / 0.04) * 0.9 + filt(ns(0.12)[:n], "hp", 3000) * np.exp(-t / 0.003) * 0.3


def crackle(d, density, hp=1800, tau=0.0025):
    n = int(d * SR)
    x = np.zeros(n)
    k = int(density * d)
    idx = rng.integers(0, n, k)
    x[idx] = rng.uniform(-1, 1, k)
    kern = np.exp(-T(int(0.02 * SR)) / tau) * rng.standard_normal(int(0.02 * SR))
    y = np.convolve(x, kern)[:n]
    return filt(y, "hp", hp)


def sfx_rustle(d=0.35):
    n = int(d * SR)
    t = T(n)
    y = crackle(d, 500) + filt(ns(d)[:n], "bandpass", [2000, 9000]) * 0.25
    return y * np.sin(np.pi * t / d) * 0.9


def sfx_crumple(d=0.75):
    n = int(d * SR)
    t = T(n)
    y = crackle(d, 1400, 1200, 0.004) * 1.2 + filt(ns(d)[:n], "bandpass", [1500, 7000]) * 0.3
    return y * np.minimum(t / (d * 0.6), 1) * np.minimum((d - t) / 0.08, 1)


def sfx_tear(d=0.42):
    n = int(d * SR)
    t = T(n)
    x = filt(ns(d)[:n], "bandpass", [900, 7000])
    am = 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * (55 + 40 * t / d) * t + rng.uniform(0, 6) * np.sin(9 * t)))
    y = x * (0.35 + 0.65 * am) + crackle(d, 700, 1500) * 0.6
    return y * np.minimum(t / 0.03, 1) * (1 - t / d) ** 0.5 * 1.1


def sfx_snip():
    n = int(0.18 * SR)
    out = np.zeros(n)
    for d0, g in ((0.0, 0.8), (0.07, 1.0)):
        m = int(0.05 * SR)
        t = T(m)
        y = sum(np.sin(2 * np.pi * f * t) for f in (3100, 4650, 6200)) / 3 * np.exp(-t / 0.012)
        y += filt(ns(0.05)[:m], "hp", 4000) * np.exp(-t / 0.002)
        i = int(d0 * SR)
        out[i:i + m] += g * y
    return out


def sfx_stamp():
    n = int(0.8 * SR)
    t = T(n)
    f = 38 + 60 * np.exp(-t / 0.05)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.tanh(2.2 * np.sin(ph) * np.exp(-t / 0.22))
    slap = filt(ns(0.8)[:n], "bandpass", [600, 3000]) * np.exp(-t / 0.025) * 1.2
    thump = filt(ns(0.8)[:n], "lp", 350) * np.exp(-t / 0.06) * 1.5
    return body + slap + thump


def sfx_slap():
    n = int(0.12 * SR)
    t = T(n)
    return (filt(ns(0.12)[:n], "bandpass", [700, 4000]) * np.exp(-t / 0.015)
            + np.sin(2 * np.pi * 140 * t) * np.exp(-t / 0.03) * 0.6) * 0.8


def sfx_tick():
    n = int(0.03 * SR)
    t = T(n)
    return (np.sin(2 * np.pi * 2600 * t) * 0.6 + filt(ns(0.03)[:n], "hp", 5000) * 0.5) * np.exp(-t / 0.004)


def sfx_type():
    n = int(0.05 * SR)
    t = T(n)
    return (filt(ns(0.05)[:n], "hp", 2500) * np.exp(-t / 0.004)
            + np.sin(2 * np.pi * 1700 * t) * np.exp(-t / 0.008) * 0.5) * rng.uniform(0.7, 1.0)


def sfx_clack():
    n = int(0.15 * SR)
    t = T(n)
    return (filt(ns(0.15)[:n], "bandpass", [800, 3500]) * np.exp(-t / 0.012) * 1.3
            + np.sin(2 * np.pi * 850 * t) * np.exp(-t / 0.035) * 0.7)


def sfx_sparkle():
    n = int(0.6 * SR)
    out = np.zeros(n)
    for i, m in enumerate([84, 88, 91, 96, 100, 103]):
        k = int(0.4 * SR)
        t = T(k)
        y = np.sin(2 * np.pi * hz(m) * t) * np.exp(-t / 0.12)
        s = int(i * 0.035 * SR)
        out[s:s + k] += y[: n - s]
    return out * 0.35



_F = {"whoosh": sfx_whoosh, "pop": sfx_pop, "rustle": sfx_rustle, "crumple": sfx_crumple, "tear": sfx_tear,
      "snip": sfx_snip, "stamp": sfx_stamp, "slap": sfx_slap, "tick": sfx_tick, "type": sfx_type,
      "clack": sfx_clack, "sparkle": sfx_sparkle}
_G = {"whoosh": 0.45, "pop": 0.5, "rustle": 0.55, "crumple": 0.6, "tear": 0.55, "snip": 0.55,
      "stamp": 0.75, "slap": 0.45, "tick": 0.3, "type": 0.45, "clack": 0.55, "sparkle": 0.5}
SFX = {k: (lambda k=k: (np.asarray(_F[k](), np.float32) * _G[k]).astype(np.float32)) for k in _F}
