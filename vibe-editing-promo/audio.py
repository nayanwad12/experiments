"""Original 150 BPM track + paper SFX, fully synthesised (no samples, no licensing issues).

    python3 audio.py   ->  ./out/audio.wav
"""

import os

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

from timeline import BEAT, DUR, SFX

SR = 44100
N = int(SR * DUR)
BAR = BEAT * 4
rng = np.random.default_rng(3)
HERE = os.path.dirname(os.path.abspath(__file__))


def T(n):
    return np.arange(n) / SR


def ns(d):
    return rng.standard_normal(int(d * SR))


def filt(x, kind, f, order=2):
    return sosfilt(butter(order, f, kind, fs=SR, output="sos"), x)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def place(buf, x, t, g=1.0):
    i = int(round(t * SR))
    if i >= len(buf) or i + len(x) <= 0:
        return
    if i < 0:
        x, i = x[-i:], 0
    x = x[: len(buf) - i]
    buf[i:i + len(x)] += g * x


def saw(f, n, ph=0.0):
    return 2 * ((f * T(n) + ph) % 1.0) - 1


# ---------------------------------------------------------------- drums
def kick():
    n = int(0.42 * SR)
    t = T(n)
    f = 46 + 130 * np.exp(-t / 0.028)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / 0.2) + 0.6 * np.sin(ph) * np.exp(-t / 0.018)
    click = filt(ns(0.42)[:n], "hp", 2500) * np.exp(-t / 0.003) * 0.5
    return np.tanh(2.0 * y) * 0.9 + click


def clap():
    n = int(0.35 * SR)
    t = T(n)
    x = filt(ns(0.35)[:n], "bandpass", [900, 5500])
    env = 0.8 * np.exp(-t / 0.1)
    for d in (0.0, 0.011, 0.022):
        env += (t >= d) * np.exp(-np.clip(t - d, 0, None) / 0.007)
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05) * 0.5
    return x * env * 0.8 + body


def hat(open_=False):
    d = 0.3 if open_ else 0.06
    n = int(d * SR)
    return filt(ns(d)[:n], "hp", 7500) * np.exp(-T(n) / (0.1 if open_ else 0.018))


def crash(d=2.2):
    n = int(d * SR)
    t = T(n)
    x = filt(ns(d)[:n], "hp", 3000) * np.exp(-t / 0.8)
    metal = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) for f in (3120, 4470, 5830, 7210)) * 0.05
    return (x + metal * np.exp(-t / 0.5)) * 0.6


def boom():
    n = int(1.4 * SR)
    t = T(n)
    f = 30 + 50 * np.exp(-t / 0.15)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(1.6 * np.sin(ph) * np.exp(-t / 0.5)) + filt(ns(1.4)[:n], "lp", 300) * np.exp(-t / 0.2) * 0.8


# ---------------------------------------------------------------- tonal
CHORDS = [[57, 60, 64], [53, 57, 60], [55, 60, 64], [55, 59, 62]]   # Am  F  C/G  G
ROOTS = [45, 41, 48, 43]


def chord_at(t):
    i = int(t / BAR) % 4
    return CHORDS[i], ROOTS[i]


def supersaw(m, d, voices=3, spread=0.14):
    n = int(d * SR)
    out = np.zeros(n)
    for v in range(voices):
        det = (v - (voices - 1) / 2) * spread
        out += saw(hz(m + det), n, rng.uniform(0, 1))
    return out / voices


def stab(chord, d=0.22, tau=0.1, oct_=12):
    n = int(d * SR)
    t = T(n)
    y = sum(supersaw(m + oct_, d) for m in chord)
    env = np.minimum(t / 0.004, 1) * np.exp(-t / tau)
    return y * env


def bass_note(root, d=0.18, tau=0.12):
    n = int(d * SR)
    t = T(n)
    f = hz(root)
    y = 0.7 * saw(f, n) + 0.3 * saw(f * 1.005, n) + 0.7 * np.sin(2 * np.pi * f / 2 * t)
    env = np.minimum(t / 0.003, 1) * np.exp(-t / tau) * np.minimum((d - t) / 0.01, 1)
    return y * env


def pluck(m, d=0.12):
    n = int(d * SR)
    t = T(n)
    f = hz(m)
    y = saw(f, n) * 0.6 + np.sign(np.sin(2 * np.pi * f * 1.002 * t)) * 0.4
    return y * np.minimum(t / 0.002, 1) * np.exp(-t / 0.05)


def pad(chord, d):
    n = int(d * SR)
    t = T(n)
    y = sum(supersaw(m, d, 5, 0.18) + 0.5 * supersaw(m + 12, d, 3, 0.1) for m in chord)
    return y * np.minimum(t / 0.15, 1) * np.minimum((d - t) / 0.05, 1)


def riser(d, f0=180, f1=2200):
    n = int(d * SR)
    t = T(n)
    k = t / d
    f = f0 * (f1 / f0) ** (k ** 1.5)
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = ((ph / (2 * np.pi)) % 1.0) * 2 - 1
    nz = ns(d)[:n]
    out = np.zeros(n)
    seg = 40
    for s in range(seg):  # sweep a band-pass up through the noise
        a, b = s * n // seg, (s + 1) * n // seg
        c = 400 * (9000 / 400) ** (s / seg)
        out[a:b] = filt(nz, "bandpass", [c * 0.7, min(c * 1.4, 20000)])[a:b]
    return (0.5 * tone * 0.4 + out) * k ** 2


# ---------------------------------------------------------------- SFX
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


def sfx_impact():
    return boom() * 0.9


SFX_FNS = {"whoosh": sfx_whoosh, "pop": sfx_pop, "rustle": sfx_rustle, "crumple": sfx_crumple, "tear": sfx_tear,
           "snip": sfx_snip, "stamp": sfx_stamp, "slap": sfx_slap, "tick": sfx_tick, "type": sfx_type,
           "clack": sfx_clack, "sparkle": sfx_sparkle, "impact": sfx_impact}
SFX_GAIN = {"whoosh": 0.45, "pop": 0.5, "rustle": 0.55, "crumple": 0.6, "tear": 0.55, "snip": 0.55,
            "stamp": 0.75, "slap": 0.45, "tick": 0.3, "type": 0.45, "clack": 0.55, "sparkle": 0.5,
            "impact": 0.75}


# ---------------------------------------------------------------- arrangement
def build():
    drums = np.zeros(N)
    hats = np.zeros(N)
    bass = np.zeros(N)
    stabs = np.zeros(N)
    pads = np.zeros(N)
    lead_l = np.zeros(N)
    lead_r = np.zeros(N)
    fx = np.zeros(N)
    K, C, HC, HO = kick(), clap(), hat(), hat(True)
    kicks = []

    def section(t):
        if t < 7.2:
            return "A"
        if t < 9.6:
            return "B"
        if t < 11.0:
            return "C"
        if t < 11.2:
            return "gap"
        if t < 23.2:
            return "D"
        if t < 26.0:
            return "E"
        if t < 26.8:
            return "roll"
        if t < 29.6:
            return "F"
        return "end"

    nb = int(DUR / BEAT)
    for b in range(nb):
        t = b * BEAT
        sec = section(t)
        chord, root = chord_at(t)
        full = sec in ("A", "D", "E", "F")
        if full or (sec == "C" and t < 10.8) or (sec == "roll" and t < 26.4):
            place(drums, K, t)
            kicks.append(t)
        if sec == "C" and t >= 10.8:
            for s in range(2):
                place(drums, K, t + s * BEAT / 2, 0.9)
                kicks.append(t + s * BEAT / 2)
        if full and b % 2 == 1:
            place(drums, C, t, 0.8)
        if full or sec == "B":
            for s in range(4):
                g = (0.35 if s % 2 else 0.2) if sec != "B" else 0.12
                place(hats, HO if (s == 2 and sec != "B") else HC, t + s * BEAT / 4, g)
        if full:
            # off-beat pumping bass (16th roll in the drop)
            offs = (0.25, 0.5, 0.75) if sec in ("D", "F") else (0.5,)
            for o in offs:
                place(bass, bass_note(root, 0.09 if len(offs) > 1 else 0.18), t + o * BEAT, 1.0)
            place(stabs, stab(chord), t + BEAT / 2, 1.0)
        if sec in ("D", "F"):
            seq = [chord[0] + 12, chord[1] + 12, chord[2] + 12, chord[1] + 24]
            for s in range(4):
                m = seq[(b * 4 + s) % 4]
                p = pluck(m)
                if s % 2:
                    place(lead_l, p, t + s * BEAT / 4, 0.5)
                    place(lead_r, p, t + s * BEAT / 4, 1.0)
                else:
                    place(lead_l, p, t + s * BEAT / 4, 1.0)
                    place(lead_r, p, t + s * BEAT / 4, 0.5)
        if sec == "B":
            seq = [chord[0] + 12, chord[2] + 12, chord[1] + 24, chord[2] + 12]
            for s in range(2):
                p = pluck(seq[(b * 2 + s) % 4], 0.2)
                place(lead_l, p, t + s * BEAT / 2, 0.6)
                place(lead_r, p, t + s * BEAT / 2, 0.6)

    # pads over breakdown / build
    for bar_t in (7.2, 8.8, 10.4):
        chord, _ = chord_at(bar_t)
        d = min(BAR, 11.0 - bar_t)
        place(pads, pad(chord, d), bar_t)

    # snare rolls
    def roll(t0, t1):
        t = t0
        while t < t1:
            k = (t - t0) / (t1 - t0)
            step = BEAT / 2 if k < 0.5 else BEAT / 4 if k < 0.8 else BEAT / 8
            place(drums, C, t, 0.25 + 0.6 * k)
            t += step

    roll(9.6, 11.0)
    roll(26.0, 26.8)

    # risers, crashes, hits
    place(fx, riser(3.0), 8.0, 0.55)
    place(fx, riser(1.6, 250, 3000), 25.2, 0.45)
    for t in (0.0, 11.2, 14.4, 17.6, 20.8, 23.2, 26.8, 29.6):
        place(fx, crash(), t, 0.45)
    for t in (11.2, 26.8):
        place(fx, boom(), t, 0.6)
    # final hit
    place(drums, K, 29.6, 1.1)
    place(stabs, stab(CHORDS[0], 0.4, 0.25), 29.6, 1.3)
    place(bass, bass_note(45, 0.4, 0.25), 29.6, 1.0)

    # sidechain pump
    sc = np.ones(N)
    m = int(0.3 * SR)
    curve = 1 - 0.7 * np.exp(-T(m) / 0.07)
    for tk in kicks:
        i = int(tk * SR)
        j = min(N, i + m)
        sc[i:j] = np.minimum(sc[i:j], curve[: j - i])

    bass = filt(bass, "lp", 1100) * sc
    stabs = filt(stabs, "lp", 4200) * sc
    pads = filt(pads, "lp", 1800) * sc
    lead_l = filt(lead_l, "lp", 6000) * sc
    lead_r = filt(lead_r, "lp", 6000) * sc

    # SFX
    sfx = np.zeros(N)
    for (t, kind, g) in SFX:
        place(sfx, SFX_FNS[kind](), t, g * SFX_GAIN[kind])

    def nrm(x):
        return x / (np.abs(x).max() + 1e-9)

    drums, hats, bass, stabs, pads = map(nrm, (drums, hats, bass, stabs, pads))
    lead_l, lead_r = lead_l / (np.abs(lead_l).max() + 1e-9), lead_r / (np.abs(lead_r).max() + 1e-9)
    fx = nrm(fx)

    haas = int(0.011 * SR)
    stabs_r = np.concatenate([np.zeros(haas), stabs[:-haas]])
    music_l = 0.95 * drums + 0.22 * hats + 0.55 * bass + 0.3 * stabs + 0.28 * pads + 0.16 * lead_l + 0.3 * fx
    music_r = 0.95 * drums + 0.26 * hats + 0.55 * bass + 0.3 * stabs_r + 0.28 * pads + 0.16 * lead_r + 0.3 * fx
    sfx = nrm(sfx)
    L = 0.62 * music_l + 0.75 * sfx
    Rr = 0.62 * music_r + 0.75 * sfx
    st = np.stack([L, Rr], 1)
    st = st / np.abs(st).max()
    st = np.tanh(1.8 * st) / np.tanh(1.8)          # glue / loudness
    fade = int(0.3 * SR)
    st[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 2
    st = st / np.abs(st).max() * 0.94
    return st


if __name__ == "__main__":
    out = os.path.join(HERE, "out")
    os.makedirs(out, exist_ok=True)
    st = build()
    wavfile.write(os.path.join(out, "audio.wav"), SR, (st * 32767).astype(np.int16))
    print("wrote", os.path.join(out, "audio.wav"), st.shape)
