"""Original score + sound design + mix for the OncoXpress film.

Score: felt piano, warm string pad and a soft pulse in D major / B minor (84 bpm), written to the edit:
hushed and unresolved while the records are scattered, resolving on the brand, a gentle heartbeat pulse
under the product section, a warm D-major landing on the end card.
Sound design: room tone, paper, taps, typing, UI ticks, whooshes, a riser + impact into the brand reveal.
Narration sits on top; the bed is side-chain ducked under it.

    python3 sound.py  ->  work/mix.wav (48 kHz stereo)
"""
import json
import os
import subprocess

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt, sosfiltfilt

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
SR = 48000
DUR = 80.0
N = int(DUR * SR)
OFF = 1.0                      # narration starts 1 s into the film
rng = np.random.default_rng(7)
FFMPEG = "ffmpeg"


def T(n):
    return np.arange(n) / SR


def filt(x, kind, f, order=2):
    return sosfilt(butter(order, f, kind, fs=SR, output="sos"), x, axis=0)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def place(buf, x, t, g=1.0):
    i = int(round(t * SR))
    if x.ndim == 1 and buf.ndim == 2:
        x = np.stack([x, x], 1)
    if i >= len(buf) or i + len(x) <= 0:
        return
    if i < 0:
        x, i = x[-i:], 0
    x = x[: len(buf) - i]
    buf[i:i + len(x)] += g * x


def pan(x, p):
    """p in [-1, 1] -> stereo (constant power)."""
    a = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], 1)


def env_ar(n, a, r):
    t = T(n)
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / r)


# ---------------------------------------------------------------- reverb
def make_ir(sec, decay, lp, seed):
    r = np.random.default_rng(seed)
    n = int(sec * SR)
    x = r.standard_normal(n) * np.exp(-T(n) / decay)
    x = filt(x, "lp", lp, 1)
    x[: int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))
    return x / np.sqrt(np.sum(x ** 2))


IR_L, IR_R = make_ir(3.2, 0.9, 5000, 1), make_ir(3.2, 0.9, 5000, 2)
IRs_L, IRs_R = make_ir(1.2, 0.3, 7000, 3), make_ir(1.2, 0.3, 7000, 4)


def reverb(st, wet=0.35, big=True):
    a, b = (IR_L, IR_R) if big else (IRs_L, IRs_R)
    l = fftconvolve(st[:, 0], a)[: len(st)]
    r = fftconvolve(st[:, 1], b)[: len(st)]
    return st * (1 - wet) + np.stack([l, r], 1) * wet * 1.6


# ---------------------------------------------------------------- instruments
def piano(m, dur=3.5, vel=0.8):
    """Felt piano: inharmonic partials, soft hammer, fast top-end decay."""
    n = int(dur * SR)
    t = T(n)
    f = hz(m)
    x = np.zeros(n)
    for k in range(1, 9):
        fk = f * k * np.sqrt(1 + 0.00035 * k * k)
        if fk > 12000:
            break
        amp = (0.9 ** k) / k ** 0.6
        x += amp * np.sin(2 * np.pi * fk * t + rng.uniform(0, 6.28)) * np.exp(-t * (0.9 + 0.55 * k * (f / 440) ** 0.5))
    x += 0.35 * np.sin(2 * np.pi * f * t * 1.0015) * np.exp(-t * 0.7)        # slight detune = warmth
    hammer = filt(rng.standard_normal(int(0.02 * SR)), "bandpass", [f, min(f * 6, 9000)]) * np.linspace(1, 0, int(0.02 * SR))
    x[: len(hammer)] += 0.25 * hammer
    x *= np.minimum(1, t / 0.006)
    x = filt(x, "lp", 2400 + 2600 * vel, 1)                                   # felt
    return x * vel * 0.32


def pad(notes, dur, att=2.0, rel=2.5, bright=1200):
    n = int(dur * SR)
    t = T(n)
    st = np.zeros((n, 2))
    for j, m in enumerate(notes):
        for d, p in ((-0.09, -0.7), (0.0, 0.0), (0.08, 0.7)):
            f = hz(m) * 2 ** (d / 12)
            ph = rng.uniform(0, 1)
            x = 2 * ((f * t + ph) % 1.0) - 1
            x += 0.5 * (2 * ((f * 2.003 * t + ph) % 1.0) - 1)
            st += pan(x, p * (0.5 + 0.1 * j)) / 3
    st = filt(st, "lp", bright, 2)
    e = np.minimum(1, t / att) * np.minimum(1, np.maximum(0, (dur - t) / rel))
    lfo = 1 + 0.06 * np.sin(2 * np.pi * 0.18 * t)
    return st * (e * lfo)[:, None] * 0.05


def sub(m, dur, att=1.0, rel=1.5):
    n = int(dur * SR)
    t = T(n)
    x = np.sin(2 * np.pi * hz(m) * t) + 0.25 * np.sin(4 * np.pi * hz(m) * t)
    e = np.minimum(1, t / att) * np.minimum(1, np.maximum(0, (dur - t) / rel))
    return x * e * 0.10


def pluck(m, vel=0.5):
    n = int(0.9 * SR)
    t = T(n)
    f = hz(m)
    x = 2 * ((f * t) % 1.0) - 1
    cut = 600 + 3000 * np.exp(-t / 0.05)
    # time-varying lowpass approximated by blending two filtered copies
    a = filt(x, "lp", 3200, 2)
    b = filt(x, "lp", 700, 2)
    k = np.exp(-t / 0.06)
    y = a * k + b * (1 - k)
    return y * np.exp(-t / 0.22) * np.minimum(1, t / 0.002) * vel * 0.10 + 0 * cut


def softkick(vel=1.0):
    n = int(0.5 * SR)
    t = T(n)
    f = 48 + 70 * np.exp(-t / 0.035)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
    return filt(x, "lp", 400, 2) * vel * 0.55


def shaker(vel=1.0):
    n = int(0.12 * SR)
    x = filt(rng.standard_normal(n), "bandpass", [5000, 11000]) * env_ar(n, 0.008, 0.03)
    return x * vel * 0.05


# ---------------------------------------------------------------- sfx
def noise_burst(d, lo, hi, a=0.01, r=0.1, g=1.0):
    n = int(d * SR)
    return filt(rng.standard_normal(n), "bandpass", [lo, hi]) * env_ar(n, a, r) * g


def paper(d=0.6, g=1.0):
    n = int(d * SR)
    x = rng.standard_normal(n)
    crackle = (rng.random(n) < 0.004) * rng.standard_normal(n) * 6
    x = filt(x + crackle, "bandpass", [1800, 7500])
    e = np.sin(np.pi * np.clip(T(n) / d, 0, 1)) ** 1.5 * (0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 7 * T(n))))
    return x * e * g * 0.05


def click(g=1.0, f=3500):
    n = int(0.03 * SR)
    x = filt(rng.standard_normal(n), "bandpass", [f * 0.6, f * 1.6]) * env_ar(n, 0.0005, 0.004)
    x += 0.4 * np.sin(2 * np.pi * 900 * T(n)) * np.exp(-T(n) / 0.006)
    return x * g * 0.35


def key(g=1.0):
    a = click(g * 0.8, rng.uniform(2200, 4200))
    out = np.zeros(int(0.06 * SR) + len(a))
    out[:len(a)] += a
    out[int(0.06 * SR):] += click(g * 0.3, 1800)
    return out


def tick(g=1.0, f=1760):
    n = int(0.25 * SR)
    t = T(n)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.05) + 0.3 * np.sin(2 * np.pi * f * 2.01 * t) * np.exp(-t / 0.02)
    return x * np.minimum(1, t / 0.002) * g * 0.06


def pop(g=1.0, f=520):
    n = int(0.18 * SR)
    t = T(n)
    ff = f * (1 + 0.6 * np.exp(-t / 0.02))
    x = np.sin(2 * np.pi * np.cumsum(ff) / SR) * np.exp(-t / 0.045)
    return x * np.minimum(1, t / 0.002) * g * 0.10


def whoosh(d=0.7, g=1.0, lo=300, hi=4000, rev=False):
    n = int(d * SR)
    t = T(n) / d
    x = rng.standard_normal(n)
    a = filt(x, "bandpass", [lo, hi])
    b = filt(x, "bandpass", [lo * 2.5, min(hi * 2.5, 16000)])
    k = t if not rev else 1 - t
    y = a * (1 - k) + b * k
    e = np.sin(np.pi * t) ** 2 if not rev else t ** 3 * (1 - np.exp(-(1 - t) * 40))
    return y * e * g * 0.12


def riser(d=1.2, g=1.0):
    n = int(d * SR)
    t = T(n)
    x = filt(rng.standard_normal(n), "hp", 1500, 2) * (t / d) ** 2.2 * 0.08
    f = 220 * 2 ** (2 * t / d)
    x += 0.04 * np.sin(2 * np.pi * np.cumsum(f) / SR) * (t / d) ** 2
    x[-int(0.02 * SR):] *= np.linspace(1, 0, int(0.02 * SR))
    return x * g


def impact(g=1.0):
    n = int(2.8 * SR)
    t = T(n)
    f = 38 + 50 * np.exp(-t / 0.08)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.7) * 0.5
    x += filt(rng.standard_normal(n), "lp", 900, 2) * np.exp(-t / 0.25) * 0.15
    return x * np.minimum(1, t / 0.003) * g


def shimmer(d=2.0, g=1.0, base=86):
    n = int(d * SR)
    t = T(n)
    x = np.zeros(n)
    for m in (base, base + 7, base + 12, base + 16):
        x += np.sin(2 * np.pi * hz(m) * t + rng.uniform(0, 6)) * (0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(3, 7) * t))
    return x * np.minimum(1, t / 0.3) * np.exp(-t / (d / 2.5)) * g * 0.012


def roomtone(d, g=1.0):
    n = int(d * SR)
    x = filt(rng.standard_normal(n), "lp", 700, 2) * 0.05
    x += filt(rng.standard_normal(n), "bandpass", [300, 1600]) * 0.012 * (0.6 + 0.4 * np.sin(2 * np.pi * 0.3 * T(n)))
    x += 0.004 * np.sin(2 * np.pi * 100 * T(n))
    e = np.minimum(1, T(n) / 0.8) * np.minimum(1, (d - T(n)) / 0.8)
    return x * e * g


# ---------------------------------------------------------------- score
BEAT = 60 / 84


def score():
    mus = np.zeros((N, 2))
    B = BEAT
    # chord table (midi): pad voicing, bass root
    Bm = ([59, 62, 66, 69], 47)
    G = ([55, 59, 62, 66], 43)
    D = ([57, 62, 66, 69], 50)
    A = ([57, 61, 64, 69], 45)
    Asus = ([57, 62, 64, 69], 45)
    Fs = ([58, 61, 66, 70], 42)
    D2 = ([62, 66, 69, 74], 50)
    # (start, dur, chord)
    prog = [
        (0.0, 4.6, Bm), (4.6, 4.6, G), (9.2, 3.2, D), (12.4, 4.0, A), (16.4, 4.9, Bm), (21.3, 4.9, Asus),
        (26.2, 5.8, D2), (32.0, 3.6, A), (35.6, 3.5, Bm),
        (39.1, 3.4, G), (42.5, 3.4, D), (45.9, 3.4, A), (49.3, 3.4, Bm),
        (52.7, 3.4, G), (56.1, 3.2, D), (59.3, 3.0, A), (62.3, 1.4, Asus),
        (63.7, 3.9, G), (67.6, 3.1, D), (70.7, 1.65, Asus), (72.35, 7.65, D2),
    ]
    for (t0, d, (pv, bass)) in prog:
        g = 1.0 if 26 < t0 < 72 else 0.8
        place(mus, pad(pv, d + 1.5, att=0.9 if t0 else 3.0, rel=1.6, bright=900 if t0 < 26 else 1500), t0, g)
        place(mus, pan(sub(bass, d + 0.8, att=0.6, rel=1.0), 0), t0, 0.9 if t0 >= 9 else 0.5)
    # piano motif: sparse and questioning early, fuller and major after the brand
    motif_a = [(0.8, 78, .55), (2.2, 74, .45), (3.6, 71, .4), (5.3, 76, .5), (6.9, 74, .45), (7.9, 71, .35),
               (9.3, 81, .45), (10.6, 78, .4), (12.5, 76, .45), (13.9, 73, .35), (15.4, 76, .4), (16.5, 74, .45),
               (17.9, 78, .4), (19.6, 71, .4)]
    motif_b = [(26.25, 74, .7), (26.25, 66, .5), (26.95, 78, .55), (27.65, 81, .55), (29.0, 78, .45), (30.4, 76, .45),
               (32.1, 73, .45), (33.5, 76, .4), (35.7, 74, .45), (37.1, 78, .4)]
    motif_c = [(63.8, 79, .45), (65.1, 78, .4), (66.4, 74, .4), (67.7, 78, .45), (69.0, 81, .45), (70.75, 76, .5)]
    motif_d = [(72.4, 74, .75), (72.4, 62, .55), (72.4, 69, .5), (73.5, 78, .55), (75.1, 81, .6), (76.2, 86, .5),
               (76.2, 78, .45), (77.6, 74, .4)]
    for (t, m, v) in motif_a + motif_b + motif_c + motif_d:
        place(mus, pan(piano(m, 4.5, v), rng.uniform(-0.3, 0.3)), t)
    # product section: heartbeat kick, shaker, plucked arpeggio (8ths), building to the "complete picture"
    arp = {0: [67, 71, 74, 79], 1: [66, 69, 74, 78], 2: [64, 69, 73, 76], 3: [66, 71, 74, 78]}
    t = 39.1
    step = B / 2
    i = 0
    while t < 63.6:
        bar = int((t - 39.1) / (4 * B))
        chord = arp[[0, 1, 2, 3, 0, 1, 2, 3][bar % 8]]
        build = np.clip((t - 39.1) / 20.0, 0, 1)
        if i % 2 == 0:
            place(mus, pan(softkick(0.55 + 0.35 * build), 0), t)
        if i % 2 == 1:
            place(mus, pan(shaker(0.6 + 0.6 * build), 0.35), t)
        place(mus, pan(pluck(chord[i % 4] + (12 if (i // 8) % 2 else 0), 0.35 + 0.35 * build), -0.4 + 0.8 * ((i % 4) / 3)), t)
        t += step
        i += 1
    # half-time after the product section
    t = 63.7
    while t < 70.6:
        place(mus, pan(softkick(0.35), 0), t)
        t += 2 * B
    mus = reverb(mus, 0.42, True)
    return mus


# ---------------------------------------------------------------- sound design
def design():
    fx = np.zeros((N, 2))
    place(fx, roomtone(9.4, 1.0), 0.0)
    place(fx, roomtone(12.2, 0.7), 9.2)
    place(fx, roomtone(10.6, 0.7), 28.7)
    place(fx, roomtone(4.0, 0.7), 63.6)
    place(fx, roomtone(3.3, 0.7), 67.5)
    # clip 1 / 3: paper
    place(fx, pan(paper(0.7, 1.0), 0.2), 7.1)
    place(fx, pan(paper(0.5, 0.7), 0.1), 8.3)
    place(fx, pan(paper(0.8, 0.8), -0.1), 10.3)
    place(fx, pan(paper(0.6, 0.6), 0.2), 11.7)
    # clip 2: phone, portal, email, pdf
    for tt in (12.9, 13.55):
        place(fx, pan(click(0.7, 2600), 0.2), tt)
    place(fx, pan(click(0.8, 3000), 0.1), 15.1)
    for k in range(7):
        place(fx, pan(key(0.6), 0.1), 16.55 + k * 0.11 + rng.uniform(0, 0.03))
    place(fx, pan(click(0.8, 3000), 0.1), 18.7)
    place(fx, pan(paper(0.9, 1.0), 0.0), 19.7)
    # split-screen
    for tt in (21.35, 21.62, 22.93, 23.15):
        place(fx, pan(pop(1.0, 440), rng.uniform(-0.4, 0.4)), tt)
        place(fx, pan(whoosh(0.35, 0.5, 800, 5000), 0), tt - 0.1)
    for k in range(5):
        place(fx, pan(tick(0.5, 1320), -0.3 + 0.15 * k), 23.4 + k * 0.15)
    brk = noise_burst(0.35, 400, 3000, 0.002, 0.07, 0.10) + 0.05 * np.sin(2 * np.pi * 110 * T(int(0.35 * SR))) * np.exp(-T(int(0.35 * SR)) / 0.08)
    place(fx, pan(brk, 0), 24.3)
    place(fx, pan(whoosh(0.9, 0.8, 200, 3000, rev=True), 0), 25.3)
    place(fx, pan(riser(1.15, 1.0), 0), 25.05)
    place(fx, pan(impact(0.55), 0), 26.2)
    place(fx, reverb(pan(shimmer(2.5, 1.0, 86), 0), 0.5), 26.7)
    place(fx, pan(whoosh(0.6, 0.6, 300, 3000), 0), 28.5)
    # clip 4/5
    for k in range(18):
        place(fx, pan(key(0.35), 0.25), 34.2 + k * 0.19 + rng.uniform(0, 0.06))
    place(fx, pan(pop(0.8, 600), -0.5), 36.0)
    place(fx, pan(click(0.7, 2800), 0.3), 38.75)
    # product sequence
    place(fx, pan(whoosh(0.7, 0.9, 250, 3500), 0), 38.8)
    for i in range(5):
        place(fx, pan(whoosh(0.4, 0.45, 900, 6000), [-0.6, -0.3, 0.6, 0.6, -0.5][i]), 39.15 + i * 0.1)
        place(fx, pan(tick(0.6, 1568), 0.2), 39.95 + i * 0.32)
    for tt in (41.27, 42.43, 43.44):
        place(fx, pan(tick(1.0, 2093), -0.4), tt)
    for i in range(5):
        place(fx, pan(tick(0.45, 2637), 0.3), 43.3 + 0.3 * i)
    place(fx, pan(whoosh(1.0, 0.5, 2000, 9000), 0.2), 45.6)
    place(fx, pan(whoosh(0.4, 0.5, 900, 6000), 0.3), 46.6)
    place(fx, pan(whoosh(0.6, 0.7, 300, 4000), 0.2), 47.85)
    for i in range(5):
        place(fx, pan(pop(0.55, 500 + 40 * i), 0.3), 48.3 + i * 0.22)
    for tt in (45.75, 46.65, 47.9):
        place(fx, pan(tick(0.6, 1760), -0.4), tt)
    place(fx, pan(whoosh(0.6, 0.7, 300, 4000), 0.2), 52.5)
    for i in range(4):
        place(fx, pan(pop(0.5, 620 + 60 * i), 0.3), 53.2 + i * 0.3)
    for tt in (53.18, 54.39, 55.36, 56.30, 56.97, 58.16):
        place(fx, pan(tick(0.7, 1976), -0.45), tt - 0.1)
        place(fx, pan(whoosh(0.35, 0.3, 1200, 7000), 0.3), tt - 0.1)
    place(fx, pan(whoosh(1.1, 1.0, 150, 2500), 0), 59.2)
    for k, p in ((1, -0.7), (1, 0.7), (2, -0.9), (2, 0.9)):
        place(fx, pan(whoosh(0.5, 0.4, 700, 5000), p), 59.5 + k * 0.12)
    place(fx, pan(whoosh(0.8, 0.8, 200, 3000, rev=True), 0), 62.1)
    place(fx, pan(impact(0.45), 0), 62.92)
    place(fx, reverb(pan(shimmer(1.8, 0.7, 81), 0), 0.5), 62.95)
    # search
    place(fx, pan(whoosh(0.5, 0.5, 400, 4000), 0), 65.55)
    for k in range(7):
        place(fx, pan(key(0.7), 0), 66.25 + k * 0.06)
    for i in range(3):
        place(fx, pan(pop(0.6, 560 + 80 * i), 0.2), 66.8 + i * 0.1)
    place(fx, pan(click(0.6, 2800), 0.3), 68.5)
    place(fx, pan(click(0.5, 2800), 0.3), 69.7)
    # under 60 seconds: a clock that runs fast
    tt = 70.75
    d = 0.24
    while tt < 72.1:
        place(fx, pan(click(0.45, 4200), 0.1), tt)
        tt += d
        d = max(0.07, d * 0.85)
    place(fx, pan(impact(0.35), 0), 70.95)
    # end card
    place(fx, pan(whoosh(1.0, 0.7, 200, 3000, rev=True), 0), 71.4)
    place(fx, pan(impact(0.5), 0), 72.35)
    place(fx, reverb(pan(shimmer(3.5, 1.0, 86), 0), 0.55), 72.8)
    return fx


# ---------------------------------------------------------------- voice
def voice():
    p = subprocess.run([FFMPEG, "-v", "error", "-i", os.path.join(HERE, "raw", "narration.mp3"), "-ac", "1", "-ar", str(SR),
                        "-f", "s16le", "-"], capture_output=True, check=True)
    v = np.frombuffer(p.stdout, np.int16).astype(np.float64) / 32768
    v = filt(v, "hp", 70, 2)
    # gentle compression + a touch of warmth and presence
    env = np.sqrt(sosfiltfilt(butter(1, 10, "lp", fs=SR, output="sos"), v ** 2) + 1e-10)
    thr = 10 ** (-26 / 20)
    v = v * np.where(env > thr, (env / thr) ** (1 / 2.5 - 1), 1.0)
    v = v + 0.18 * filt(v, "bandpass", [160, 380]) + 0.22 * filt(v, "bandpass", [2800, 6500])
    v = v / (np.max(np.abs(v)) + 1e-9) * 10 ** (-2.5 / 20)
    out = np.zeros(N)
    i = int(OFF * SR)
    out[i:i + len(v)] = v[: N - i]
    st = np.stack([out, out], 1)
    st = reverb(st, 0.06, False)            # a hint of room so it sits in the picture
    return st


def main():
    v = voice()
    m = score()
    fx = design()
    # side-chain duck the music under the voice
    ve = np.sqrt(sosfiltfilt(butter(1, 4, "lp", fs=SR, output="sos"), v[:, 0] ** 2) + 1e-10)
    duck = 1 - 0.62 * np.clip((20 * np.log10(ve) + 50) / 20, 0, 1)
    duck = sosfiltfilt(butter(1, 3, "lp", fs=SR, output="sos"), duck)
    m = m / (np.max(np.abs(m)) + 1e-9) * 10 ** (-9 / 20)
    mix = v + m * duck[:, None] * 0.85 + fx * 0.9
    # fades
    t = T(N)
    mix *= np.clip(t / 0.6, 0, 1)[:, None] * np.clip((DUR - t) / 2.0, 0, 1)[:, None]
    # soft-knee limiter
    peak = np.max(np.abs(mix))
    mix = np.tanh(mix / max(peak, 1e-9) * 1.15) / np.tanh(1.15) * 10 ** (-1.0 / 20)
    wavfile.write(os.path.join(WORK, "mix.wav"), SR, (mix * 32767).astype(np.int16))
    for nm, x in (("stem_voice", v), ("stem_music", m * duck[:, None]), ("stem_fx", fx)):
        wavfile.write(os.path.join(WORK, nm + ".wav"), SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))
    print("mix peak", peak)


if __name__ == "__main__":
    main()
