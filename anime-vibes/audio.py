"""Soundtrack: an original anime-OP style score, SFX and the narration mix, all synthesised in numpy.

150 BPM, A minor (Am-F-C-G). Each scene gets the scoring its genre would: rain + piano for the cinematic
open, a tense string ostinato under the manga panels, a bouncy xylophone for the chibi gag (with the
'chiin' bell when his soul leaves), harp and celesta for the spirit, a drum-roll power-up into the
impact frame, then a full J-rock band (power-chord synths, bass, drums, lead) to the end card.
"""
import json
import os
import subprocess

import numpy as np
import soundfile as sf
from scipy.signal import butter, fftconvolve, resample_poly, sosfilt

import timeline as TL

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
DUR = TL.DUR
N = int(DUR * SR)
B = TL.BEAT
def V(k):
    return TL.VO_AT[k]


rng = np.random.default_rng(3)


def mtof(m):
    return 440 * 2 ** ((m - 69) / 12)


def tt(d):
    return np.arange(int(d * SR)) / SR


def place(buf, x, t, gain=1.0, pan=0.0):
    """buf is (N, 2). pan -1..1."""
    i = int(round(t * SR))
    if x.ndim == 1:
        lg, rg = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        x = np.stack([x * lg * 1.414, x * rg * 1.414], 1)
    if i >= len(buf) or i + len(x) <= 0:
        return
    if i < 0:
        x, i = x[-i:], 0
    n = min(len(x), len(buf) - i)
    buf[i:i + n] += gain * x[:n]


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), x, axis=0)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "lowpass", fs=SR, output="sos"), x, axis=0)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "highpass", fs=SR, output="sos"), x, axis=0)


def env_adsr(n, a=0.005, d=0.1, s=0.7, r=0.08):
    t = np.arange(n) / SR
    dur = n / SR
    e = np.minimum(1, t / max(a, 1e-4))
    e = np.where(t > a, s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)), e)
    e *= np.clip((dur - t) / r, 0, 1)
    return e


def saw(f, d, detune=0.0):
    t = tt(d)
    ph = (f * (1 + detune) * t + rng.random()) % 1.0
    return 2 * ph - 1


def reverb(x, secs=1.6, wet=0.3, bright=6000, seed=0):
    r = np.random.default_rng(seed)
    n = int(secs * SR)
    t = np.arange(n) / SR
    ir = np.stack([r.standard_normal(n), r.standard_normal(n)], 1) * np.exp(-t * 6.9 / secs)[:, None]
    ir = lp(ir, bright)
    ir[: int(0.012 * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum(0, keepdims=True))
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    y = np.stack([fftconvolve(x[:, k], ir[:, k])[: len(x)] for k in range(2)], 1)
    return x * (1 - wet) + y * wet * 2.2


# ----------------------------------------------------------------------------- instruments
def piano(f, d=1.6):
    t = tt(d)
    y = sum((0.6 ** k) * np.sin(2 * np.pi * f * (k + 1) * t * (1 + 0.0004 * k * k)) * np.exp(-t * (1.6 + 1.3 * k))
            for k in range(6))
    return y * np.minimum(1, t / 0.003) * 0.4


def glock(f, d=1.2):
    t = tt(d)
    y = (np.sin(2 * np.pi * f * t) * np.exp(-t * 3.5) + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 9)
         + 0.2 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 18))
    return y * np.minimum(1, t / 0.002) * 0.4


def xylo(f, d=0.35):
    t = tt(d)
    y = np.sin(2 * np.pi * f * t) * np.exp(-t * 14) + 0.5 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 30)
    return y * 0.5


def harp(f, d=1.5):
    p = int(SR / f)
    buf = rng.uniform(-1, 1, p)
    out = np.zeros(int(d * SR))
    for i in range(len(out)):
        out[i] = buf[i % p]
        buf[i % p] = 0.5 * (buf[i % p] + buf[(i + 1) % p]) * 0.996
    return out * 0.45


_harp_cache = {}


def harp_c(m, d=1.5):
    if m not in _harp_cache:
        _harp_cache[m] = harp(mtof(m), d)
    return _harp_cache[m]


def pad(freqs, d, cutoff=2400, a=0.5, r=0.6, voices=3):
    y = np.zeros(int(d * SR))
    for f in freqs:
        for v in range(voices):
            y += saw(f, d, (v - 1) * 0.006)
    y = lp(y, cutoff, 2) / (len(freqs) * voices)
    e = np.minimum(1, tt(d) / a) * np.clip((d - tt(d)) / r, 0, 1)
    return y * e


def power_chord(root, d, gain=1.0):
    """Distorted saw power chord (root, fifth, octave)."""
    y = np.zeros(int(d * SR))
    for m in (root, root + 7, root + 12):
        for v in (-1, 0, 1):
            y += saw(mtof(m), d, v * 0.004)
    y = np.tanh(3.0 * y / 6)
    y = lp(y, 3800, 2)
    e = env_adsr(len(y), 0.004, 0.25, 0.75, 0.05)
    return y * e * 0.5 * gain


def bass(m, d):
    f = mtof(m)
    t = tt(d)
    y = np.tanh(1.5 * (np.sin(2 * np.pi * f * t) + 0.5 * saw(f, d)))
    y = lp(y, 900)
    return y * env_adsr(len(y), 0.003, 0.12, 0.6, 0.03) * 0.55


def lead(m, d, vib=True):
    f = mtof(m)
    t = tt(d)
    fm = f * (1 + (0.006 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.15) * 4, 0, 1) if vib else 0))
    ph = np.cumsum(fm) / SR
    y = 0.6 * (2 * (ph % 1) - 1) + 0.4 * np.sign(np.sin(2 * np.pi * ph))
    y = lp(y, 4200)
    return y * env_adsr(len(y), 0.01, 0.2, 0.75, 0.06) * 0.3


def kick():
    t = tt(0.35)
    f = 48 + 110 * np.exp(-t * 28)
    return np.tanh(2 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)) * 0.9


def snare():
    t = tt(0.25)
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25)
    nz = bp(rng.standard_normal(len(t)), 1500, 9000) * np.exp(-t * 16)
    return (0.5 * body + 0.9 * nz) * 0.7


def hat(open_=False):
    t = tt(0.3 if open_ else 0.06)
    return hp(rng.standard_normal(len(t)), 7000) * np.exp(-t * (10 if open_ else 70)) * 0.3


def crash(d=2.0):
    t = tt(d)
    return hp(rng.standard_normal(len(t)), 4000) * np.exp(-t * 2.2) * 0.45


# ----------------------------------------------------------------------------- sfx
def boom(d=1.4, f0=40):
    t = tt(d)
    f = f0 + 80 * np.exp(-t * 12)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3)
    nz = lp(rng.standard_normal(len(t)), 600) * np.exp(-t * 8) * 0.6
    return np.tanh(1.8 * (y + nz)) * 0.9


def stab(m=45):
    """Orchestral-ish hit: low boom + brassy chord + noise burst."""
    d = 1.2
    t = tt(d)
    y = boom(d, 38) * 0.8
    for k in (0, 7, 12, 15):
        y += saw(mtof(m + k), d) * np.exp(-t * 5) * 0.15
    y += bp(rng.standard_normal(len(t)), 600, 5000) * np.exp(-t * 20) * 0.4
    return lp(y, 5000)


def whoosh(d=0.45, up=True, lo=300, hi=4000):
    n = int(d * SR)
    x = rng.standard_normal(n)
    out = np.zeros(n)
    blocks = 14
    for b in range(blocks):
        a, z = b * n // blocks, (b + 1) * n // blocks
        k = b / blocks if up else 1 - b / blocks
        fc = lo + (hi - lo) * k
        out[a:z] = bp(x, max(80, fc * 0.6), min(20000, fc * 1.5))[a:z]
    return out * np.sin(np.pi * np.arange(n) / n) ** 2 * 0.6


def riser(d, f0=200, f1=2400):
    t = tt(d)
    f = f0 * (f1 / f0) ** (t / d)
    y = sum(np.sin(2 * np.pi * np.cumsum(f * (1 + 0.01 * k)) / SR) for k in range(-2, 3)) / 5
    nz = hp(rng.standard_normal(len(t)), 2000) * (t / d) ** 2 * 0.5
    return (y * 0.5 + nz) * (t / d) ** 1.5


def boing():
    t = tt(0.45)
    f = 260 + 160 * np.sin(2 * np.pi * 10 * t) * np.exp(-t * 5) + 140 * np.exp(-t * 7)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6) * 0.35


def popsnd(f=800):
    t = tt(0.12)
    ff = f * (1 + 1.5 * np.exp(-t * 45))
    return np.sin(2 * np.pi * np.cumsum(ff) / SR) * np.exp(-t * 35) * 0.45


def chiin():
    """Buddhist rin bell: the anime 'he's dead' gag sound."""
    t = tt(3.0)
    y = np.zeros(len(t))
    for ratio, amp, dec in ((1, 1, 0.7), (2.71, 0.5, 1.2), (5.2, 0.25, 2.0), (8.4, 0.12, 3.0)):
        y += amp * np.sin(2 * np.pi * 1180 * ratio * t) * np.exp(-t * dec)
    y *= 1 + 0.15 * np.sin(2 * np.pi * 4 * t)
    return y * np.minimum(1, t / 0.002) * 0.3


def wah_wah():
    out = []
    for m, d in ((58, 0.3), (57, 0.3), (56, 0.3), (55, 0.9)):
        t = tt(d)
        f = mtof(m) * (1 + 0.012 * np.sin(2 * np.pi * 6 * t) * (d > 0.5))
        ph = np.cumsum(f) / SR
        y = sum(np.sin(2 * np.pi * ph * k) / k for k in range(1, 8))
        wah = 0.5 + 0.5 * np.sin(np.pi * t / d)
        y = lp(y, 900) * wah + lp(y, 2200) * (1 - wah) * 0.3
        out.append(y * env_adsr(len(y), 0.02, 0.2, 0.9, 0.06))
    return np.concatenate(out) * 0.5


def heartbeat():
    t = tt(0.5)
    y = np.zeros(len(t))
    for t0, a in ((0.0, 1.0), (0.18, 0.7)):
        tt_ = np.clip(t - t0, 0, None)
        y += a * np.sin(2 * np.pi * 55 * tt_) * np.exp(-tt_ * 18) * (t >= t0)
    return np.tanh(2 * y) * 0.8


def tick():
    t = tt(0.03)
    return bp(rng.standard_normal(len(t)), 2500, 7000) * np.exp(-t * 200) * 0.5


def blip(f=1800, d=0.07):
    t = tt(d)
    return np.sign(np.sin(2 * np.pi * f * t)) * np.exp(-t * 40) * 0.18


def shing():
    t = tt(0.6)
    y = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * dk) for f, dk in ((3200, 6), (4700, 8), (6100, 10)))
    nz = hp(rng.standard_normal(len(t)), 5000) * np.exp(-t * 30)
    return (y * 0.15 + nz * 0.4)


def thunder():
    t = tt(3.5)
    nz = lp(rng.standard_normal(len(t)), 300, 4)
    e = np.exp(-t * 1.2) * (0.6 + 0.4 * np.abs(np.sin(t * 7)))
    return nz * e * 6.0


def rain(d):
    n = int(d * SR)
    x = np.stack([rng.standard_normal(n), rng.standard_normal(n)], 1)
    x = bp(x, 1200, 9000) * 0.08
    drops = np.zeros((n, 2))
    for _ in range(int(d * 60)):
        i = rng.integers(0, n - 2000)
        tt_ = np.arange(1500) / SR
        drops[i:i + 1500, rng.integers(0, 2)] += np.sin(2 * np.pi * rng.uniform(2500, 6000) * tt_) * np.exp(-tt_ * 300) * 0.05
    return x + drops


def sparkle_gliss(buf, t0, n=10, up=True, gain=0.5, base=79):
    notes = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24]
    for i in range(n):
        m = base + (notes[i] if up else notes[n - 1 - i])
        place(buf, glock(mtof(m), 1.0), t0 + i * 0.04, gain * (0.5 + 0.5 * i / n), pan=-0.6 + 1.2 * i / n)


# ----------------------------------------------------------------------------- score
PROG = [(45, [57, 60, 64]), (41, [57, 60, 65]), (48, [55, 60, 64]), (43, [55, 59, 62])]   # Am F C G
BAR = 4 * B


def chord_at(t, t0=0.0):
    return PROG[int((t - t0) // BAR) % 4]


def score(mus, sfx):
    # --- 1. city: rain, thunder, piano arpeggios + pad
    place(sfx, rain(5.9), 0.0, 0.9)
    place(sfx, thunder(), 0.1, 0.5)
    for b in range(4):
        t0 = b * BAR
        root, ch = PROG[b % 4]
        place(mus, pad([mtof(m) for m in ch], BAR + 0.3, 1600, 0.6, 0.4), t0, 0.22)
        arp = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[1] + 24, ch[2] + 12, ch[1] + 12, ch[0] + 24, ch[2] + 12]
        for i, m in enumerate(arp):
            if t0 + i * B / 2 < 5.5:
                place(mus, piano(mtof(m), 1.4), t0 + i * B / 2, 0.38, pan=-0.3 + 0.6 * (i % 2))
    place(mus, piano(mtof(33), 3.0) + piano(mtof(45), 3.0), 0.0, 0.5)
    place(sfx, whoosh(0.5, True), 5.15, 0.4)

    # --- 2. manga: tense string ostinato, ticking clock, panel slams, heartbeat
    for i in range(int(4.8 / (B / 2))):
        t0 = 5.6 + i * B / 2
        m = [45, 45, 48, 45, 44, 45, 47, 45][i % 8]
        place(mus, lp(saw(mtof(m), B / 2 * 0.9) * env_adsr(int(B / 2 * 0.9 * SR), 0.005, 0.08, 0.5, 0.03), 1800),
              t0, 0.22, pan=-0.2)
        place(mus, lp(saw(mtof(m + 12), B / 2 * 0.9) * env_adsr(int(B / 2 * 0.9 * SR), 0.005, 0.08, 0.5, 0.03), 2400),
              t0, 0.12, pan=0.3)
    for i in range(12):
        place(sfx, tick(), 5.6 + i * B, 0.5, pan=0.4)
    for k in ("dead", "clips", "sleep"):
        tk = 5.6 if k == "dead" else V(k) - 0.1      # the panel slam
        place(sfx, stab(45 if k != "clips" else 46), tk, 0.5)
        place(sfx, whoosh(0.2, False, 400, 3000), tk - 0.2, 0.3)
    place(sfx, heartbeat(), 6.45, 0.9)
    place(sfx, heartbeat(), 7.0, 0.7)
    place(mus, pad([mtof(33), mtof(40)], 1.5, 400), 8.9, 0.5)

    # --- 3. chibi: bouncy xylophone, boings, pops, then wah-wah + chiin
    soul_t = V("chibi2") + 0.25
    mel = [76, 79, 81, 79, 76, 74, 72, 74, 76, 79, 84, 83, 81, 79, 76, 79]
    for i in range(int((soul_t - 10.4) / (B / 2))):
        t0 = 10.4 + i * B / 2
        place(mus, xylo(mtof(mel[i % 16])), t0, 0.45, pan=0.2)
        if i % 2 == 0:
            root = [45, 41, 48, 43][(i // 8) % 4]
            place(mus, xylo(mtof(root + 12), 0.25), t0, 0.5, pan=-0.3)
        if i % 4 == 2:
            place(mus, snare() * 0.5, t0, 0.35)
    for i in range(int((soul_t - 10.4) / (np.pi / 11))):
        tb = 10.4 + i * np.pi / 11
        if i % 3 == 0:
            place(sfx, boing(), tb, 0.25, pan=-0.2)
    for i in range(3):
        for n_ in range(4):
            tp = 10.4 + (n_ - i / 3) / 1.6
            if 10.4 <= tp < soul_t:
                place(sfx, popsnd(700 + 200 * i), tp, 0.5, pan=[-0.5, 0.5, 0.2][i])
    for d in (1, 2):
        place(sfx, whoosh(0.3, True, 1500, 7000), V("chibi1") + d * 0.63, 0.35, pan=0.6)
    place(mus, wah_wah(), soul_t, 0.5)
    place(sfx, chiin(), soul_t + 0.6, 0.85)

    # --- 4. spirit: harp gliss, celesta, warm pad
    for i, m in enumerate([57, 60, 64, 67, 69, 72, 76, 79, 81, 84, 88]):
        place(mus, harp_c(m, 1.6), 14.8 + i * 0.045, 0.5, pan=-0.6 + 0.12 * i)
    for b in range(3):
        t0 = 14.8 + b * BAR
        ch = [[53, 57, 60, 64], [55, 59, 62, 67], [57, 60, 64, 69]][b]
        place(mus, pad([mtof(m) for m in ch], BAR + 0.5, 2200, 0.5, 0.6), t0, 0.28)
        for i in range(8):
            m = ch[[0, 2, 1, 3, 2, 3, 1, 2][i]] + 24
            place(mus, glock(mtof(m), 1.4), t0 + i * B / 2, 0.22, pan=0.5 * np.sin(i))
    sparkle_gliss(sfx, 15.6, 10, True, 0.35)
    for i in range(int(0.9 * 22)):
        place(sfx, tick() * 0.6, V("spirit2") + 0.2 + i / 22 * 1.0, 0.45, pan=0.5)

    # --- 5. power-up: drum roll, riser, hits; impact
    t_roll0 = 19.6
    t = t_roll0
    while t < 22.55:
        k = (t - t_roll0) / (22.55 - t_roll0)
        place(mus, snare(), t, 0.22 + 0.35 * k, pan=0.1)
        t += B / (2 + 4 * k)
    for b in range(2):
        place(mus, pad([mtof(m) for m in (57, 64, 69, 72)], BAR + 0.2, 1200 + 1800 * b, 0.3, 0.2), 19.6 + b * BAR, 0.3)
        place(mus, bass(33, BAR), 19.6 + b * BAR, 0.6)
    place(sfx, riser(3.0, 120, 1600), 19.6, 0.35)
    for k in ("epic", "emo", "beat"):
        place(sfx, stab(45), V(k) - 0.04, 0.4)
        place(sfx, crash(1.0), V(k) - 0.04, 0.18)
    # eye close-up: suck-in riser, then 80 ms of silence before the hit
    place(sfx, riser(TL.IMPACT - 22.6 - 0.08, 400, 5000), 22.6, 0.4)
    place(sfx, boom(3.0, 32), TL.IMPACT, 0.8)
    place(sfx, stab(33), TL.IMPACT, 0.55)
    place(sfx, crash(3.0), TL.IMPACT + 0.12, 0.45)
    place(sfx, whoosh(0.8, False, 200, 6000), TL.IMPACT + 0.2, 0.4)

    # --- 6-8. J-rock band from the impact to the end
    band0 = TL.IMPACT
    end_hit = 39.2
    lead_mel = [  # (beat offset in bar, midi, beats) per chord
        [(0, 76, 1.5), (1.5, 74, 0.5), (2, 72, 1), (3, 71, 1)],
        [(0, 72, 1.5), (1.5, 74, 0.5), (2, 76, 1.5), (3.5, 77, 0.5)],
        [(0, 79, 2), (2, 76, 1), (3, 74, 1)],
        [(0, 74, 1), (1, 76, 1), (2, 79, 1), (3, 83, 1)],
    ]
    nbars = int((end_hit - band0) / BAR) + 1
    for b in range(nbars):
        t0 = band0 + b * BAR
        root, ch = PROG[b % 4]
        shojo = 30.4 <= t0 < 35.2
        mecha = 25.6 <= t0 < 30.4
        for e in range(8):     # driving eighths
            te = t0 + e * B / 2
            if te >= end_hit:
                break
            place(mus, bass(root - 12 + (12 if e % 4 == 3 else 0), B / 2 * 0.92), te, 0.55)
            if not shojo:
                place(mus, power_chord(root, B / 2 * 0.9, 0.9 if e % 2 == 0 else 0.6), te, 0.32, pan=-0.45)
                place(mus, power_chord(root, B / 2 * 0.9, 0.9 if e % 2 == 0 else 0.6), te + 0.012, 0.32, pan=0.45)
            place(mus, hat(e % 2 == 1 and shojo), te, 0.5, pan=0.3)
        for q in range(4):
            tq = t0 + q * B
            if tq >= end_hit:
                break
            if q in (0, 2) or (q == 3 and not shojo):
                place(mus, kick(), tq, 0.8)
            if q in (1, 3):
                place(mus, snare(), tq, 0.55)
        if shojo:
            place(mus, pad([mtof(m) for m in ch], BAR + 0.1, 3000, 0.1, 0.2), t0, 0.3)
            for i in range(8):
                m = ch[[0, 1, 2, 1, 2, 0, 2, 1][i]] + 24
                place(mus, glock(mtof(m), 0.9), t0 + i * B / 2, 0.28, pan=0.4 * np.sin(i * 1.3))
        if b % 4 == 0 or t0 in (25.6, 30.4):
            place(mus, crash(2.0), t0, 0.45)
        if not mecha or b % 2:
            for off, m, beats in lead_mel[b % 4]:
                ts = t0 + off * B
                if ts < end_hit - 0.05:
                    place(mus, lead(m + (12 if shojo else 0), beats * B * 0.95), ts, 0.4 if not shojo else 0.25,
                          pan=0.15)
    for tc in (25.6, 30.4, 35.2):
        place(mus, crash(2.0), tc, 0.5)
    # final hit
    place(mus, power_chord(45, 3.0, 1.2), end_hit, 0.55, pan=-0.4)
    place(mus, power_chord(45, 3.0, 1.2), end_hit + 0.01, 0.55, pan=0.4)
    place(mus, bass(33, 2.5), end_hit, 0.7)
    place(mus, kick(), end_hit, 1.0)
    place(mus, crash(3.0), end_hit, 0.7)
    place(mus, glock(mtof(93), 3.0), end_hit, 0.4)

    # mecha SFX
    place(sfx, whoosh(0.3, True, 800, 9000), 25.32, 0.5)
    for i in range(9):
        place(sfx, blip(1500 + 120 * i), V("cuts") - 0.1 + i * 0.07 + 0.3, 0.6, pan=-0.6 + 0.15 * i)
    place(sfx, shing(), V("cuts"), 0.6, pan=-0.5)
    place(sfx, whoosh(0.5, True, 200, 6000), V("color"), 0.5)
    for i in range(7):
        place(sfx, blip(2400, 0.04), V("caps") + i * 0.1, 0.6, pan=0.5)
    place(sfx, stab(57), V("music"), 0.35)
    t = tt(0.9)
    place(sfx, np.sign(np.sin(2 * np.pi * np.cumsum(400 + 1400 * t / 0.9) / SR)) * 0.08, V("synced"), 0.8)
    place(sfx, stab(45), V("synced") + 0.9, 0.7)
    for k in ("cuts", "color", "caps", "music"):
        place(sfx, blip(2200, 0.1), V(k) + 0.05, 0.6)

    # shojo: sparkles + sugoi burst
    sparkle_gliss(sfx, 30.4, 10, True, 0.35, 84)
    sparkle_gliss(sfx, V("sugoi") - 0.05, 10, True, 0.5, 79)
    sparkle_gliss(sfx, V("client") + 0.1, 8, False, 0.3, 84)
    place(sfx, boing(), V("client") + 0.45, 0.35, pan=0.6)

    # title
    place(sfx, whoosh(0.4, True), 35.2, 0.4)
    place(sfx, stab(45), V("title") - 0.05 + 0.18, 0.5)
    place(sfx, stab(48), V("title") + 0.32 + 0.18, 0.5)
    sparkle_gliss(sfx, V("title") + 0.8, 11, True, 0.45, 84)
    sparkle_gliss(sfx, V("alive") + 0.6, 8, True, 0.3, 91)

    # cut whooshes
    for tc in (10.4, 19.6, 30.4):
        place(sfx, whoosh(0.35, True), tc - 0.25, 0.35)


# ----------------------------------------------------------------------------- voice
def load_vo():
    vo = json.load(open(os.path.join(HERE, "work", "vo.json")))
    out = {}
    for k, v in vo.items():
        x, sr = sf.read(v["wav"])
        if sr != SR:
            x = resample_poly(x, SR, sr)
        out[k] = x.astype(np.float64)
    return out


def comp(x, thr=0.25, ratio=3.0):
    env = np.abs(x)
    a = np.exp(-1 / (0.003 * SR))
    r = np.exp(-1 / (0.08 * SR))
    e = np.zeros_like(env)
    lvl = 0.0
    for i in range(len(env)):
        v = env[i]
        lvl = a * lvl + (1 - a) * v if v > lvl else r * lvl + (1 - r) * v
        e[i] = lvl
    g = np.where(e > thr, (thr + (e - thr) / ratio) / np.maximum(e, 1e-9), 1.0)
    return x * g


def voice_track():
    vo = load_vo()
    track = np.zeros((N, 2))
    spirit = np.zeros((N, 2))
    duck = np.zeros(N)
    for k, x in vo.items():
        y = comp(x / (np.abs(x).max() + 1e-9) * 0.9)
        y = hp(y, 90)
        t0 = V(k)
        if k.startswith("spirit"):
            # ethereal: long bright reverb
            place(spirit, y, t0, 0.95)
        else:
            g = 1.0
            if k in ("edit",):
                g = 2.0
                # echo
                for j, (dt, gg) in enumerate(((0.0, 1.0), (0.18, 0.45), (0.36, 0.22), (0.54, 0.1))):
                    place(track, y, t0 + dt, g * gg, pan=(-0.3, 0.3)[j % 2] if j else 0)
                continue
            place(track, y, t0, g)
        i0 = int(t0 * SR)
        duck[i0:i0 + len(y)] = 1
    track = reverb(track, 1.0, 0.12, 7000, 1)
    spirit = reverb(spirit, 2.6, 0.45, 9000, 2)
    # smooth the duck envelope
    k = int(0.12 * SR)
    duck = np.convolve(duck, np.ones(k) / k, "same")
    return track + spirit, np.clip(duck, 0, 1)


def main():
    mus = np.zeros((N, 2))
    sfx = np.zeros((N, 2))
    score(mus, sfx)
    mus = reverb(mus, 1.4, 0.18, 8000, 3)
    sfx = reverb(sfx, 1.0, 0.1, 9000, 4)
    voice, duck = voice_track()
    gmus = 1 - 0.68 * duck
    mix = mus * gmus[:, None] * 0.75 + sfx * (1 - 0.5 * duck)[:, None] * 0.8 + voice * 1.5
    # gentle bus limiter
    mix = np.tanh(mix * 0.9) / 0.9
    fade = np.clip((DUR - np.arange(N) / SR) / 0.4, 0, 1)
    mix *= fade[:, None]
    raw = os.path.join(HERE, "work", "mix_raw.wav")
    sf.write(raw, mix.astype(np.float32), SR)
    out = os.path.join(HERE, "work", "mix.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-ar", str(SR), out], check=True)
    print("wrote", out)


if __name__ == "__main__":
    main()
