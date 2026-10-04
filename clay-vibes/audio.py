"""Original cartoon score + foley, fully synthesised in numpy (no samples, nothing to license).

120 BPM in F major: oom-pah tuba, strummed Karplus-Strong ukulele, glockenspiel, a whistled tune,
xylophone, woodblock. The grind goes minor with a sad trombone. Ends on "shave and a haircut, two bits".
Foley: clay plops, boings, a synthesised sheep bleat, hen cluck, typing, pops, whooshes, slide whistles.

    python3 audio.py   ->  out/audio.wav
"""

import os

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

from timeline import *

SR = 44100
N = int(SR * DUR)
rng = np.random.default_rng(12)
HERE = os.path.dirname(os.path.abspath(__file__))


def T(n):
    return np.arange(n) / SR


def ns(n):
    return rng.standard_normal(n)


def filt(x, kind, f, order=2):
    return sosfilt(butter(order, f, kind, fs=SR, output="sos"), x)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "Eb": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "Ab": 8, "A": 9, "Bb": 10, "B": 11}


def m(name):
    """'A4' -> midi"""
    return 12 * (int(name[-1]) + 1) + NOTE[name[:-1]]


def env_adsr(n, a=0.005, d=0.1, s=0.6, r=0.05):
    t = T(n)
    dur = n / SR
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    return e * np.clip((dur - t) / r, 0, 1)


class Bus:
    def __init__(self):
        self.L = np.zeros(N)
        self.R = np.zeros(N)

    def add(self, x, t, g=1.0, pan=0.0):
        i = int(round(t * SR))
        if i >= N or len(x) == 0:
            return
        if i < 0:
            x, i = x[-i:], 0
        x = x[: N - i]
        gl, gr = g * np.sqrt((1 - pan) / 2) * 1.414, g * np.sqrt((1 + pan) / 2) * 1.414
        self.L[i:i + len(x)] += gl * x
        self.R[i:i + len(x)] += gr * x


# ================================================================ instruments
def ks(f, dur, decay=0.996, bright=0.6):
    """Vectorised Karplus-Strong pluck."""
    P = max(2, int(SR / f))
    n = int(dur * SR)
    burst = rng.uniform(-1, 1, P)
    if bright < 1:
        burst = filt(np.tile(burst, 3), "lp", 800 + 7000 * bright)[P:2 * P]
    y = np.zeros(n + 2 * P)
    y[:P] = burst
    k = 1
    while k * P < n + P:
        a, b = k * P, min((k + 1) * P, len(y))
        prev = y[a - P:b - P]
        prev1 = y[a - P - 1:b - P - 1] if a - P - 1 >= 0 else np.concatenate([[0], y[a - P:b - P - 1]])
        y[a:b] = decay * 0.5 * (prev + prev1)
        k += 1
    out = y[:n]
    return out * np.clip((dur - T(n)) / 0.02, 0, 1)


def uke_strum(chord, dur=0.45, up=False, g=1.0):
    notes = [chord[0] + 12, chord[1] + 12, chord[2] + 12, chord[0] + 24]
    if up:
        notes = notes[::-1]
    n = int((dur + 0.06) * SR)
    out = np.zeros(n)
    for i, mm in enumerate(notes):
        x = ks(hz(mm), dur, 0.993, 0.55) * (0.8 if up else 1.0)
        s = int(i * 0.012 * SR)
        out[s:s + len(x)] += x[: n - s]
    return out * g * 0.35


def tuba(mm, dur):
    n = int(dur * SR)
    t = T(n)
    f = hz(mm) * (1 - 0.025 * np.exp(-t / 0.03))
    ph = 2 * np.pi * np.cumsum(f) / SR
    amps = [1, 0.75, 0.5, 0.32, 0.2, 0.12]
    y = sum(a * np.sin((k + 1) * ph) for k, a in enumerate(amps))
    y = filt(y, "lp", 900)
    return np.tanh(1.4 * y) * env_adsr(n, 0.025, 0.15, 0.55, 0.06) * 0.55


def glock(mm, dur=0.9):
    n = int(dur * SR)
    t = T(n)
    f = hz(mm)
    y = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d) for r, a, d in
            ((1, 1, 0.5), (2.76, 0.35, 0.15), (5.4, 0.18, 0.06), (8.93, 0.08, 0.03)))
    return y * np.minimum(t / 0.001, 1) * 0.4


def xylo(mm, dur=0.4):
    n = int(dur * SR)
    t = T(n)
    f = hz(mm)
    y = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d) for r, a, d in
            ((1, 1, 0.16), (3.93, 0.35, 0.05), (9.2, 0.12, 0.02)))
    y += filt(ns(n), "bandpass", [1500, 6000]) * np.exp(-t / 0.004) * 0.4
    return y * 0.5


def whistle(mm, dur):
    n = int(dur * SR)
    t = T(n)
    vib = 1 + 0.007 * np.sin(2 * np.pi * 5.6 * t) * np.clip((t - 0.12) / 0.1, 0, 1)
    f = hz(mm) * vib
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) + 0.06 * np.sin(2 * ph)
    breath = filt(ns(n), "bandpass", [hz(mm) * 0.8, hz(mm) * 1.25]) * 0.25
    return (y + breath) * env_adsr(n, 0.03, 0.2, 0.8, 0.05) * 0.3


def pizz(mm, dur=0.35):
    return ks(hz(mm), dur, 0.982, 0.35) * 0.7


def trombone(mm, dur, wobble=False):
    n = int(dur * SR)
    t = T(n)
    vib = 1 + (0.02 * np.sin(2 * np.pi * 5 * t) * np.clip((t - 0.1) / 0.1, 0, 1) if wobble else 0)
    f = hz(mm) * vib * (1 - 0.03 * np.exp(-t / 0.04))
    ph = (np.cumsum(f) / SR) % 1.0
    saw = 2 * ph - 1
    out = np.zeros(n)
    seg = 32
    for s in range(seg):   # opening "wah" filter
        a, b = s * n // seg, (s + 1) * n // seg
        u = s / seg
        cut = 350 + 1700 * np.sin(np.pi * min(u * 1.6, 1)) ** 2
        out[a:b] = filt(saw, "lp", cut)[a:b]
    return np.tanh(1.5 * out) * env_adsr(n, 0.04, 0.3, 0.8, 0.08) * 0.5


def woodblock(f=1100, g=1.0):
    n = int(0.08 * SR)
    t = T(n)
    return (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.018) + 0.4 * np.sin(2 * np.pi * f * 2.3 * t) * np.exp(-t / 0.008)) * g * 0.5


def shaker():
    n = int(0.07 * SR)
    t = T(n)
    return filt(ns(n), "hp", 6000) * np.minimum(t / 0.01, 1) * np.exp(-t / 0.025) * 0.25


def kick_soft():
    n = int(0.25 * SR)
    t = T(n)
    f = 55 + 90 * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12) * 0.8


def snap():
    n = int(0.12 * SR)
    t = T(n)
    return filt(ns(n), "bandpass", [1200, 5000]) * np.exp(-t / 0.02) * 0.6


def pad(chord, dur):
    n = int(dur * SR)
    y = np.zeros(n)
    for mm in chord:
        for d in (-0.08, 0.08):
            ph = (hz(mm + d) * T(n) + rng.uniform()) % 1.0
            y += 2 * ph - 1
    y = filt(y, "lp", 1400)
    return y * env_adsr(n, 0.3, 1.0, 1.0, 0.4) * 0.08


def bell(mm, dur=1.6):
    n = int(dur * SR)
    t = T(n)
    f = hz(mm)
    return sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d) for r, a, d in
               ((1, 1, 0.8), (2.0, 0.5, 0.5), (3.01, 0.3, 0.3), (4.17, 0.25, 0.15), (5.43, 0.15, 0.08))) * 0.35


# ================================================================ voices
def baa(dur=0.6, f0=430, mood="happy", seed=0):
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    t = T(n)
    u = t / dur
    if mood == "happy":
        contour = 1 + 0.10 * np.sin(np.pi * np.minimum(u * 1.4, 1)) - 0.12 * u
    elif mood == "sad":
        contour = 1.05 - 0.3 * u
    elif mood == "grumble":
        contour = 0.75 + 0.05 * np.sin(2 * np.pi * 3 * t)
    elif mood == "aww":
        contour = 1.15 - 0.35 * u ** 0.7
    else:  # surprised
        contour = 0.9 + 0.4 * np.minimum(u * 3, 1)
    trem_rate = 7.5 + r.uniform(-0.5, 0.5) if mood != "grumble" else 11
    f = f0 * contour * (1 + 0.035 * np.sin(2 * np.pi * trem_rate * t))
    ph = (np.cumsum(f) / SR) % 1.0
    src = (2 * ph - 1) * 0.7 + np.sin(2 * np.pi * ph) * 0.3
    src += filt(ns(n), "bandpass", [1800, 5000]) * 0.12
    F = [(750, 1.0), (1350, 0.7), (2600, 0.3)] if mood != "aww" else [(650, 1.0), (1000, 0.6), (2500, 0.2)]
    y = sum(g * filt(src, "bandpass", [fc * 0.85, fc * 1.18]) for fc, g in F)
    lips = filt(src, "lp", 450)     # the "b": closed lips before the vowel opens
    open_ = np.clip(t / 0.05, 0, 1)
    y = lips * (1 - open_) * 0.6 + y * open_
    am = 1 - 0.55 * (0.5 + 0.5 * np.sin(2 * np.pi * trem_rate * t - np.pi / 2)) * np.clip((t - 0.08) / 0.08, 0, 1)
    return y * am * env_adsr(n, 0.025, 0.4, 0.85, 0.12) * 1.6


def cluck():
    out = np.zeros(int(0.5 * SR))
    for k, (t0, d, f0) in enumerate(((0.0, 0.07, 700), (0.11, 0.07, 760), (0.24, 0.16, 820))):
        n = int(d * SR)
        t = T(n)
        f = f0 * (1.3 - 0.4 * t / d)
        ph = (np.cumsum(f) / SR) % 1.0
        src = 2 * ph - 1
        y = filt(src, "bandpass", [900, 1500]) + 0.5 * filt(src, "bandpass", [2000, 3200])
        y *= env_adsr(n, 0.005, 0.05, 0.7, 0.02)
        i = int(t0 * SR)
        out[i:i + n] += y
    return out * 1.4


# ================================================================ foley
def plop(pitch=1.0):
    n = int(0.32 * SR)
    t = T(n)
    f = (70 + 200 * np.exp(-t / 0.035)) * pitch
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.09)
    sq = filt(ns(n), "bandpass", [250 * pitch, 1600 * pitch]) * np.exp(-t / 0.03) * 0.7
    k = np.clip((t - 0.02) / 0.05, 0, 1)
    suck = np.sin(2 * np.pi * np.cumsum(350 + 700 * k) / SR) * np.exp(-((t - 0.05) / 0.02) ** 2) * 0.25
    return np.tanh(1.5 * (body + sq + suck)) * 0.8


def boing(f0=220, dur=0.55):
    n = int(dur * SR)
    t = T(n)
    f = f0 * (1 + 0.35 * np.exp(-t * 5) * np.sin(2 * np.pi * 13 * t)) * (1 + 0.3 * np.exp(-t / 0.05))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph)) * np.exp(-t / 0.22) * 0.5


def pop(f0=900, g=1.0):
    n = int(0.1 * SR)
    t = T(n)
    f = 260 + f0 * np.exp(-t / 0.015)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.035) +
            filt(ns(n), "hp", 3000) * np.exp(-t / 0.003) * 0.3) * g * 0.7


def slide_whistle(f0, f1, dur):
    n = int(dur * SR)
    t = T(n)
    u = t / dur
    f = f0 * (f1 / f0) ** u * (1 + 0.01 * np.sin(2 * np.pi * 6 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) + filt(ns(n), "bandpass", [1500, 4000]) * 0.08) * np.sin(np.pi * u) ** 0.5 * 0.35


def whoosh(d=0.4):
    n = int(d * SR)
    x = ns(n)
    out = np.zeros(n)
    seg = 20
    for s in range(seg):
        a, b = s * n // seg, (s + 1) * n // seg
        c = 500 * (5000 / 500) ** np.sin(np.pi * s / seg)
        out[a:b] = filt(x, "bandpass", [c * 0.6, c * 1.6])[a:b]
    return out * np.sin(np.pi * T(n) / d) ** 2 * 0.8


def crackle(d, density, hp=1800, tau=0.0025):
    n = int(d * SR)
    x = np.zeros(n)
    k = int(density * d)
    idx = rng.integers(0, n, k)
    x[idx] = rng.uniform(-1, 1, k)
    kern = np.exp(-T(int(0.02 * SR)) / tau) * ns(int(0.02 * SR))
    return filt(np.convolve(x, kern)[:n], "hp", hp)


def crumple(d=0.5):
    n = int(d * SR)
    t = T(n)
    return (crackle(d, 1300, 1200, 0.004) + filt(ns(n), "bandpass", [1500, 7000]) * 0.25) * np.minimum(t / 0.1, 1) * \
        np.clip((d - t) / 0.08, 0, 1) * 0.9


def clink(f=2300):
    n = int(0.35 * SR)
    t = T(n)
    return sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / dd) for r, a, dd in
               ((1, 1, 0.12), (1.52, 0.6, 0.08), (2.27, 0.4, 0.05), (3.1, 0.2, 0.03))) * 0.3


def tick(hi=True):
    return woodblock(2400 if hi else 1700, 0.35)


def type_click():
    n = int(0.04 * SR)
    t = T(n)
    return (filt(ns(n), "hp", 2500) * np.exp(-t / 0.004) + np.sin(2 * np.pi * rng.uniform(1500, 2000) * t) *
            np.exp(-t / 0.008) * 0.5) * rng.uniform(0.6, 1.0) * 0.5


def clack():
    n = int(0.25 * SR)
    t = T(n)
    return (filt(ns(n), "bandpass", [600, 3500]) * np.exp(-t / 0.02) * 1.2 + np.sin(2 * np.pi * 180 * t) *
            np.exp(-t / 0.06) * 0.9) * 0.8


def riser(d):
    n = int(d * SR)
    t = T(n)
    k = t / d
    f = 300 * (2400 / 300) ** (k ** 1.4)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR)
    out = np.zeros(n)
    nz = ns(n)
    seg = 24
    for s in range(seg):
        a, b = s * n // seg, (s + 1) * n // seg
        c = 500 * (8000 / 500) ** (s / seg)
        out[a:b] = filt(nz, "bandpass", [c * 0.7, min(c * 1.4, 20000)])[a:b]
    return (tone * 0.25 + out * 0.6) * k ** 2


def sparkle_run(n_notes=10, span=0.6, base=84, up=True):
    out = np.zeros(int((span + 0.9) * SR))
    scale = [0, 2, 4, 5, 7, 9, 11, 12, 14, 16, 17, 19]
    for i in range(n_notes):
        mm = base + scale[(i if up else n_notes - 1 - i) % len(scale)]
        x = glock(mm, 0.8) * 0.6
        s = int(span * i / n_notes * SR)
        out[s:s + len(x)] += x[: len(out) - s]
    return out


def slurp(d=0.9):
    n = int(d * SR)
    t = T(n)
    u = t / d
    f = 180 * (1400 / 180) ** u
    tone = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.3
    am = 0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 38 * t))
    return filt(tone * am + filt(ns(n), "bandpass", [800, 4000]) * 0.3, "lp", 3500) * np.sin(np.pi * u) * 0.6


def flutter(d=0.35):
    n = int(d * SR)
    t = T(n)
    return filt(ns(n), "bandpass", [300, 2500]) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 17 * t))) * \
        np.sin(np.pi * t / d) * 0.5


def rub(d=0.9):
    n = int(d * SR)
    t = T(n)
    return filt(ns(n), "bandpass", [700, 2500]) * (0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 6 * t))) * \
        np.sin(np.pi * t / d) * 0.35


def thud_wood():
    y = plop(0.7) * 0.5
    w = woodblock(420, 1.2)
    y[:len(w)] += w
    return y


# ================================================================ score
CH = {"F": [53, 57, 60], "Dm": [50, 53, 57], "Bb": [46, 50, 53], "C": [48, 52, 55], "Am": [45, 48, 52],
      "A": [45, 49, 52], "Gm": [43, 46, 50]}
ROOT = {"F": 41, "Dm": 38, "Bb": 34, "C": 36, "Am": 33, "A": 33, "Gm": 31}
FIFTH = {"F": 48, "Dm": 45, "Bb": 41, "C": 43, "Am": 40, "A": 40, "Gm": 38}

# bar index (2 s each) -> chord
BARS = ["F", "C",                         # title
        "Dm", "Am", "Bb", "A",            # grind
        "Dm", "F", "C",                   # idea / prompt
        "F", "Dm", "Bb", "C", "F",        # magic
        "F", "Dm", "Bb",                  # screening
        "F", "C", "F"]                    # end card


def groove(mus, perc, b0, b1, level=1.0, drums=True, uke=True):
    for b in range(b0, b1):
        t0 = b * BAR
        ch = BARS[b]
        for k in range(4):
            tb = t0 + k * BEAT
            if k % 2 == 0:
                mus.add(tuba(ROOT[ch] if k == 0 else FIFTH[ch], 0.42), tb, 0.9 * level, -0.1)
            elif uke:
                mus.add(uke_strum(CH[ch], 0.3), tb, 0.9 * level, 0.25)
                mus.add(uke_strum(CH[ch], 0.22, up=True), tb + BEAT / 2, 0.6 * level, 0.25)
            if drums:
                if k % 2 == 0:
                    perc.add(kick_soft(), tb, 0.5 * level)
                else:
                    perc.add(snap(), tb, 0.55 * level, 0.1)
                perc.add(shaker(), tb + BEAT / 2, 0.8 * level, 0.35)
                perc.add(woodblock(1300 if k % 2 else 1000), tb + 0.75 * BEAT, 0.25 * level, -0.4)


def melody(mus, notes, t0, inst="whistle", g=1.0, pan=0.0):
    for beat, name, dur in notes:
        t = t0 + beat * BEAT
        mm = m(name)
        if inst == "whistle":
            x = whistle(mm, dur * BEAT * 0.95)
        elif inst == "glock":
            x = glock(mm)
        elif inst == "xylo":
            x = xylo(mm)
        else:
            x = pizz(mm, max(0.25, dur * BEAT))
        mus.add(x, t, g, pan)


def build():
    mus, perc, sfx, vox = Bus(), Bus(), Bus(), Bus()

    # ---- title (bars 0-1): bouncy intro, glock motif
    groove(mus, perc, 0, 2, 0.85)
    melody(mus, [(0, "C5", 1), (1, "F5", 1), (2, "A5", 1), (3, "F5", 1),
                 (4, "G5", 1), (5, "E5", 1), (6, "C5", 1.5), (7.5, "G4", 0.5)], 0.0, "glock", 0.8, -0.2)

    # ---- grind (bars 2-5): minor plod, tuba melody, pizz, clock ticks
    for b in range(2, 6):
        t0 = b * BAR
        ch = BARS[b]
        mus.add(tuba(ROOT[ch], 0.9), t0, 0.8, -0.1)
        mus.add(tuba(FIFTH[ch], 0.9), t0 + 2 * BEAT, 0.6, -0.1)
        for k in range(4):
            mus.add(pizz(CH[ch][k % 3] + 12, 0.3), t0 + k * BEAT + BEAT / 2, 0.55, 0.3)
    melody(mus, [(0, "D4", 1.5), (1.5, "F4", 0.5), (2, "E4", 1), (3, "D4", 1),
                 (4, "C4", 1.5), (5.5, "E4", 0.5), (6, "D4", 1), (7, "C4", 1),
                 (8, "Bb3", 1.5), (9.5, "D4", 0.5), (10, "C4", 1), (11, "Bb3", 1),
                 (12, "A3", 2)], 4.0, "pizz", 0.9, -0.25)
    for i in range(int((12.0 - 4.0) / 0.25)):
        sfx.add(tick(i % 2 == 0), 4.0 + i * 0.25, 0.55, 0.45)
    for i, (tm, f) in enumerate(zip([10.9, 11.15, 11.4, 11.65], [58, 57, 56, 55])):
        mus.add(trombone(f, 0.24 if i < 3 else 0.55, wobble=i == 3), tm, 0.9, 0.1)

    # ---- idea (12-14.5): hush, ding, curious pizz climb
    mus.add(pad(CH["Dm"], 1.0), 12.0, 1.0)
    climb = ["F4", "A4", "C5", "F5", "A4", "C5", "F5", "A5", "C5", "F5", "A5", "C6"]
    for i, nm in enumerate(climb[:7]):
        mus.add(pizz(m(nm), 0.3), 12.875 + i * 0.25, 0.7, 0.2 * (i % 2 * 2 - 1))
    mus.add(pad(CH["F"], 2.0), 12.8, 1.2)

    # ---- prompt (14.5-18): sparse ticking bass while typing, riser, Enter
    for i in range(6):
        tb = 14.5 + i * BEAT
        mus.add(pizz(41 if i % 2 == 0 else 48, 0.3), tb, 0.6, -0.1)
        perc.add(woodblock(1500), tb + BEAT / 2, 0.15, 0.3)
    mus.add(pad(CH["C"], 2.3), 15.0, 1.0)
    sfx.add(riser(0.6), ENTER - 0.6, 0.5)

    # ---- magic (bars 9-13): full band
    groove(mus, perc, 9, 14, 1.0)
    mus.add(pad(CH["F"], 2.0), 18.0, 1.2)
    melody(mus, [(0, "A4", 0.5), (0.5, "C5", 0.5), (1, "F5", 1), (2, "E5", 0.5), (2.5, "D5", 0.5), (3, "C5", 1)],
           18.0, "whistle", 0.9, 0.15)
    for i in range(10):   # one xylophone note per clip landing: the timeline literally climbs a scale
        tl = HOP_T0 + i * HOP_DT + HOP_LEN
        nm = ["F4", "G4", "A4", "Bb4", "C5", "D5", "E5", "F5", "G5", "A5"][i]
        mus.add(xylo(m(nm)), tl, 1.0, -0.3 + 0.06 * i)
        sfx.add(plop(1.6 + 0.05 * i), tl, 0.25, -0.3 + 0.06 * i)
    melody(mus, [(0, "G4", 1), (1, "C5", 0.5), (1.5, "E5", 0.5), (2, "G5", 1.5), (3.5, "E5", 0.5),
                 (4, "F5", 0.5), (4.5, "E5", 0.5), (5, "F5", 0.5), (5.5, "A5", 0.5), (6, "G5", 0.5), (6.5, "F5", 0.5),
                 (7, "C5", 0.5)], 24.0, "whistle", 0.9, 0.15)
    melody(mus, [(0, "C5", 0.5), (0.5, "F5", 0.5), (1, "A5", 0.5), (1.5, "C6", 0.5)], 24.0, "glock", 0.5, -0.3)

    # ---- screening (bars 14-16): softer, no kit, glock lullaby
    groove(mus, perc, 14, 17, 0.6, drums=False)
    for b, ch in zip(range(14, 17), ("F", "Dm", "Bb")):
        mus.add(pad(CH[ch], BAR), b * BAR, 1.3)
    melody(mus, [(0, "C5", 1), (1, "F5", 1), (2, "A5", 1), (3, "F5", 1),
                 (4, "A5", 1), (5, "G5", 1), (6, "F5", 1), (7, "D5", 1),
                 (8, "D5", 1), (9, "F5", 1), (10, "Bb5", 1.5), (11.5, "A5", 0.5)], 28.0, "glock", 0.7, -0.2)

    # ---- end card (bars 17-19): groove into "shave and a haircut... two bits"
    groove(mus, perc, 17, 18, 0.9)
    shave = ["F5", "C5", "C5", "D5", "C5", "E5", "F5"]
    sh_ch = ["F", "F", "F", "Bb", "F", "C", "F"]
    for i, (tm, nm) in enumerate(zip(SHAVE, shave)):
        last = i == len(SHAVE) - 1
        mus.add(xylo(m(nm)), tm, 1.0, -0.2)
        mus.add(whistle(m(nm), 0.22 if not last else 0.45), tm, 0.8, 0.15)
        mus.add(tuba(ROOT[sh_ch[i]] + (12 if not last else 0), 0.25 if not last else 0.5), tm, 0.9, -0.1)
        mus.add(uke_strum(CH[sh_ch[i]], 0.25 if not last else 0.5), tm, 0.8, 0.25)
        perc.add(kick_soft() if i in (0, 5, 6) else snap(), tm, 0.6)
    mus.add(glock(m("F6"), 1.2), 39.5, 0.5)

    # ---- foley + voices
    sfx.add(slide_whistle(500, 1500, 0.5), 0.0, 0.7)
    for i, tl in enumerate(LAND_VIBE + LAND_EDITING):
        sfx.add(plop(0.8 + 0.06 * i), tl, 0.75, -0.5 + i * 0.09)
    sfx.add(pop(1100), POPUP1, 0.8, 0.3)
    sfx.add(boing(260, 0.45), POPUP1 + 0.05, 0.45, 0.3)
    vox.add(baa(0.62, 440, "happy", 1), BAA1, 0.9, 0.3)

    for f in range(int(4.0 * 12), int(10.5 * 12)):   # frantic typing in the grind, one key per exposure
        tm = f / 12
        if CRUMPLE - 0.05 <= tm < TOSS + 0.4 or rng.uniform() < 0.25:
            continue
        sfx.add(type_click(), tm, 0.55, -0.05)
    for i, tm in enumerate(MUGS):
        sfx.add(clink(2100 + 180 * i), tm + 0.1, 0.45, [-0.4, -0.3, 0.3, 0.4][i])
    sfx.add(crumple(0.45), CRUMPLE, 0.75, -0.2)
    sfx.add(whoosh(0.4), TOSS, 0.35, -0.4)
    sfx.add(plop(1.4), TOSS_LAND, 0.5, -0.7)
    sfx.add(slide_whistle(1400, 500, 0.4), BLOCK_FALL, 0.4, 0.5)
    sfx.add(plop(0.6), BLOCK_LAND, 0.8, 0.4)
    sfx.add(woodblock(500, 1.0), BLOCK_LAND, 0.4, 0.4)
    vox.add(baa(0.3, 470, "surprised", 2), BLOCK_FALL + 0.05, 0.65, 0)
    vox.add(baa(0.55, 330, "grumble", 3), GRUMBLE, 0.85, -0.1)

    sfx.add(boing(380, 0.35), WAKE, 0.4)
    sfx.add(bell(m("A6"), 1.6), DING, 0.65)
    sfx.add(sparkle_run(6, 0.25, 88), DING + 0.05, 0.4)
    sfx.add(rub(0.9), 13.45, 0.5)

    for i in range(len(PROMPT)):
        sfx.add(type_click(), TYPE_T0 + i * TYPE_DT, 0.85, -0.1 + 0.02 * i)
    sfx.add(sparkle_run(5, 0.2, 91), SPARKLE_T, 0.55)
    sfx.add(clack(), ENTER, 1.0, 0.3)

    sfx.add(sparkle_run(14, 0.8, 84), MAGIC, 0.8)
    sfx.add(whoosh(0.6), MAGIC, 0.5)
    sfx.add(slurp(RETRACT[1] - RETRACT[0]), RETRACT[0], 0.6)
    for i, tm in enumerate(MUG_POP):
        sfx.add(pop(900 + 250 * i), tm, 0.7, [-0.4, -0.3, 0.3, 0.4][i])
    for i, tm in enumerate(BALL_HOP):
        sfx.add(boing(200 + 60 * i, 0.5), tm, 0.55, -0.6 if i == 0 else 0.6)
    vox.add(cluck(), HEN_WAKE, 0.6, 0.65)
    sfx.add(flutter(0.35), HEN_WAKE, 0.5, 0.65)
    vox.add(cluck(), HEN_WAKE + 1.5, 0.35, 0.65)
    sfx.add(whoosh(0.35), PLAYHEAD[0], 0.3, 0.3)
    sfx.add(bell(m("C7"), 0.8), PLAYHEAD[0], 0.25, 0.4)
    vox.add(baa(0.6, 470, "happy", 4), BAA_HAPPY, 0.85)

    for i, tm in enumerate(POPS):
        sfx.add(pop(1300 + rng.uniform(-200, 300), 0.6), tm, 0.55, rng.uniform(-0.2, 0.2))
    sfx.add(whoosh(0.25), TURN, 0.35, -0.3)
    sfx.add(sparkle_run(4, 0.15, 96), WINK1, 0.5, -0.3)
    for k, (f0, dt, pan) in enumerate(((420, 0.0, -0.6), (380, 0.05, 0.2), (460, 0.09, 0.6), (350, 0.03, -0.2))):
        vox.add(baa(0.85, f0, "aww", 10 + k), FLOCK_AWW + dt, 0.45, pan)

    sfx.add(whoosh(0.3), END_DROP - 0.25, 0.4)
    for i in range(4):
        sfx.add(plop(0.75 + 0.15 * i), END_DROP + i * 0.15, 0.6, -0.4 + 0.27 * i)
    for i, tm in enumerate(TAG_WORDS):
        sfx.add(pop(800 + 200 * i), tm, 0.6, -0.3 + 0.2 * i)
    sfx.add(thud_wood(), SIGN + 0.25, 0.8, -0.5)
    sfx.add(pop(1100), POPUP2, 0.7, 0.3)
    sfx.add(sparkle_run(4, 0.15, 96), WINK2, 0.5, 0.3)
    vox.add(baa(0.55, 470, "happy", 5), BAA2, 0.9, 0.3)
    sfx.add(slide_whistle(1600, 300, IRIS[1] - IRIS[0] + 0.05), IRIS[0], 0.55)

    # ---- mix: a small room for the music, a touch on foley
    def verb(bus, wet, length=1.1, tau=0.28):
        n = int(length * SR)
        out = []
        for ch, sd in ((bus.L, 1), (bus.R, 2)):
            r = np.random.default_rng(sd)
            ir = r.standard_normal(n) * np.exp(-T(n) / tau)
            ir = filt(ir, "lp", 5000)
            ir /= np.sqrt((ir ** 2).sum())
            out.append(ch + wet * fftconvolve(ch, ir)[:N])
        return out

    mL, mR = verb(mus, 0.35)
    pL, pR = verb(perc, 0.2)
    sL, sR = verb(sfx, 0.12, 0.6, 0.12)
    vL, vR = verb(vox, 0.18, 0.8, 0.15)
    L = 0.8 * mL + 0.75 * pL + 0.9 * sL + 1.0 * vL
    R = 0.8 * mR + 0.75 * pR + 0.9 * sR + 1.0 * vR
    st = np.stack([L, R], 1)
    st = filt(st.T, "hp", 30).T
    st /= np.abs(st).max()
    st = np.tanh(1.6 * st) / np.tanh(1.6)       # gentle soft-clip glue
    st *= 0.89 / np.abs(st).max()
    fade = np.clip((DUR - T(N)) / 0.25, 0, 1)
    return st * fade[:, None]


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    p = os.path.join(HERE, "out", "audio.wav")
    wavfile.write(p, SR, (build() * 32767).astype(np.int16))
    print("wrote", p)
