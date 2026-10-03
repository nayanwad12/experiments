"""Audio for the 'boring -> editorial cover' edit.
Voice: cut to the EDL, time-stretched (pitch kept), then a broadcast voice chain (rumble HPF, FFT denoise, EQ for warmth
and presence, de-esser, compressor, limiter). Music only arrives on "add music" and builds from there; every visual
upgrade has its own sound. Master is loudness-normalised to -14 LUFS (Instagram/Reels standard).

    python3 sound.py  ->  out/mix.wav
"""

import json
import os
import subprocess

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt, sosfiltfilt

from common import DUR, FFMPEG, OUT, OUT_DUR, RAW, SEGS, SPEED, WORK, ot, wt

SR = 48000
N = int(OUT_DUR * SR) + SR
rng = np.random.default_rng(8)


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


def sq(f, n, duty=0.5):
    return np.where((f * T(n)) % 1.0 < duty, 1.0, -1.0)


def env(n, a=0.005, d=0.2):
    t = T(n)
    return np.minimum(t / a, 1) * np.exp(-t / d)


VOICE_CHAIN = ",".join([
    f"atempo={SPEED}",
    "highpass=f=80:poles=2",                       # rumble / fan
    "afftdn=nr=14:nf=-48:tn=1",                    # broadband noise reduction, noise tracking
    "equalizer=f=220:t=q:w=1.1:g=-2.5",            # clear the low-mid mud
    "equalizer=f=120:t=q:w=0.9:g=1.5",             # a little chest warmth
    "equalizer=f=3200:t=q:w=1.2:g=3",              # presence / intelligibility
    "highshelf=f=9000:g=2.5",                      # air
    "deesser=i=0.45:m=0.5:f=0.5",
    "acompressor=threshold=-22dB:ratio=3.2:attack=6:release=90:makeup=5:knee=4",
    "alimiter=limit=0.89:attack=3:release=40",
])


def voice():
    p = subprocess.run([FFMPEG, "-v", "error", "-i", RAW, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                       capture_output=True, check=True)
    src = np.frombuffer(p.stdout, np.int16).astype(np.float64) / 32768
    out = np.zeros(int(DUR * SR) + SR)
    xf = int(0.015 * SR)
    pos = 0
    for a, b, _ in SEGS:
        x = src[int(a * SR):int(b * SR)].copy()
        r = np.linspace(0, 1, xf)
        x[:xf] *= r
        x[-xf:] *= r[::-1]
        out[pos:pos + len(x)] += x
        pos += len(x)
    tin, tout = os.path.join(WORK, "_v_in.wav"), os.path.join(WORK, "_v_out.wav")
    wavfile.write(tin, SR, (np.clip(out, -1, 1) * 32767).astype(np.int16))
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", tin, "-af", VOICE_CHAIN, "-ar", str(SR), tout], check=True)
    v = wavfile.read(tout)[1].astype(np.float64) / 32768
    os.remove(tin)
    os.remove(tout)
    return np.pad(v, (0, max(0, N - len(v))))[:N]


def window(x, t0, t1, fx, ramp=0.03):
    """Replace x between output times t0..t1 by fx(x) with short crossfades."""
    i0, i1 = int(t0 * SR), int(t1 * SR)
    y = fx(x)
    w = np.zeros(len(x))
    r = int(ramp * SR)
    w[i0:i1] = 1
    w[i0:i0 + r] = np.linspace(0, 1, r)
    w[i1 - r:i1] = np.linspace(1, 0, r)
    return x * (1 - w) + y * w


def reverb(x, d=1.6, mix=0.35):
    n = int(d * SR)
    ir = rng.standard_normal(n) * np.exp(-T(n) / (d / 5))
    ir = filt(ir, "lp", 5000)
    wet = fftconvolve(x, ir)[: len(x)]
    wet *= np.max(np.abs(x)) / (np.max(np.abs(wet)) + 1e-9)
    return x * (1 - mix) + wet * mix


def gramophone(x):
    y = filt(filt(x, "hp", 450, 4), "lp", 2800, 4)
    return np.tanh(y * 3.0) / 1.6


# ------------------------------------------------------------------ drums / tones
def kick(d=0.4):
    n = int(d * SR); t = T(n)
    f = 46 + 120 * np.exp(-t / 0.03)
    return np.tanh(2 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.18)) * 0.9


def snare():
    n = int(0.25 * SR); t = T(n)
    return filt(ns(0.25)[:n], "bandpass", [1200, 7000]) * np.exp(-t / 0.06) + np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.04) * 0.5


def clap():
    n = int(0.3 * SR); t = T(n)
    e = 0.8 * np.exp(-t / 0.09)
    for d in (0.0, 0.01, 0.02):
        e += (t >= d) * np.exp(-np.clip(t - d, 0, None) / 0.006)
    return filt(ns(0.3)[:n], "bandpass", [900, 6000]) * e * 0.8


def hat(open_=False):
    d = 0.25 if open_ else 0.05
    n = int(d * SR)
    return filt(ns(d)[:n], "hp", 7500) * np.exp(-T(n) / (0.08 if open_ else 0.015))


def tom(f0=90, d=0.6):
    n = int(d * SR); t = T(n)
    f = f0 + 60 * np.exp(-t / 0.05)
    return np.tanh(2 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.25))


def boom(d=1.8):
    n = int(d * SR); t = T(n)
    f = 28 + 55 * np.exp(-t / 0.12)
    return np.tanh(1.8 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.6)) + filt(ns(d)[:n], "lp", 260) * np.exp(-t / 0.25) * 0.8


def braam(d=2.4):
    n = int(d * SR); t = T(n)
    y = sum(saw(hz(m) * (1 + 0.002 * v), n, rng.uniform()) for m in (33, 40, 45) for v in (-1, 1))
    out = np.zeros(n)
    for s in range(30):
        a, b = s * n // 30, (s + 1) * n // 30
        out[a:b] = filt(y, "lp", float(180 + 1400 * np.exp(-a / SR / 0.5)))[a:b]
    return np.tanh(out * 0.8) * np.minimum(t / 0.02, 1) * np.exp(-t / 1.0) + boom(d) * 0.6


def whoosh(d=0.4, lo=400, hi=5000):
    n = int(d * SR)
    x = ns(d)[:n]
    out = np.zeros(n)
    for s in range(24):
        a, b = s * n // 24, (s + 1) * n // 24
        c = lo * (hi / lo) ** np.sin(np.pi * s / 24)
        out[a:b] = filt(x, "bandpass", [c * 0.6, min(c * 1.6, 20000)])[a:b]
    return out * np.sin(np.pi * T(n) / d) ** 2 * 1.4


def riser(d, f0=200, f1=2400):
    n = int(d * SR); t = T(n); k = t / d
    f = f0 * (f1 / f0) ** (k ** 1.5)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3 + filt(ns(d)[:n], "bandpass", [800, 6000]) * 0.5) * k ** 2


def pop():
    n = int(0.12 * SR); t = T(n)
    f = 260 + 900 * np.exp(-t / 0.018)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.04) * 0.9


def ding(m=88):
    n = int(0.8 * SR); t = T(n)
    return (np.sin(2 * np.pi * hz(m) * t) + 0.4 * np.sin(2 * np.pi * hz(m + 7) * t)) * np.exp(-t / 0.25) * 0.5


def tick():
    n = int(0.03 * SR); t = T(n)
    return (np.sin(2 * np.pi * 2600 * t) * 0.6 + filt(ns(0.03)[:n], "hp", 5000) * 0.5) * np.exp(-t / 0.004)


def key():
    n = int(0.06 * SR); t = T(n)
    return filt(ns(0.06)[:n], "hp", 2500) * np.exp(-t / 0.005) + np.sin(2 * np.pi * 1700 * t) * np.exp(-t / 0.01) * 0.5


def supersaw(m, d, voices=5, spread=0.16):
    n = int(d * SR)
    return sum(saw(hz(m + (v - (voices - 1) / 2) * spread), n, rng.uniform()) for v in range(voices)) / voices


def stab(chord, d=0.2):
    n = int(d * SR)
    return filt(sum(supersaw(m + 12, d) for m in chord), "lp", 5200) * env(n, 0.004, 0.09)


def bass(root, d):
    n = int(d * SR); t = T(n); f = hz(root)
    y = 0.55 * saw(f, n) + 0.8 * np.sin(2 * np.pi * f / 2 * t)
    return filt(y, "lp", 900) * np.minimum(t / 0.004, 1) * np.minimum((d - t) / 0.01, 1)


def piano(m, d=0.6, g=1.0):
    n = int(d * SR); t = T(n); f = hz(m)
    y = sum((0.6 ** k) * np.sin(2 * np.pi * f * (k + 1) * (1 + 0.0015 * k) * t) for k in range(6))
    y += 0.5 * sum((0.6 ** k) * np.sin(2 * np.pi * f * 1.004 * (k + 1) * t) for k in range(4))   # honky-tonk detune
    return y * env(n, 0.002, 0.35) * g * 0.3


def marimba(m, d=0.35):
    n = int(d * SR); t = T(n); f = hz(m)
    return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t / 0.02)) * env(n, 0.002, 0.12)


def boing(d=0.5):
    n = int(d * SR); t = T(n)
    f = 180 + 220 * np.exp(-t / 0.2) + 40 * np.sin(2 * np.pi * 14 * t)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.003, 0.25) * 0.8


def slide_whistle(d=0.6, up=True):
    n = int(d * SR); t = T(n); k = t / d
    f = (500 + 1400 * k if up else 1900 - 1400 * k) * (1 + 0.01 * np.sin(2 * np.pi * 6 * t))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * k) * 0.5


def chip_note(m, d, duty=0.5):
    n = int(d * SR)
    return sq(hz(m), n, duty) * env(n, 0.002, d * 0.8) * 0.25


def tri(m, d):
    n = int(d * SR); f = hz(m)
    return (2 * np.abs(2 * ((f * T(n)) % 1) - 1) - 1) * np.minimum((d - T(n)) / 0.01, 1) * 0.35


def coin():
    return np.concatenate([chip_note(83, 0.06, 0.25), chip_note(88, 0.3, 0.25)])


def levelup():
    return np.concatenate([chip_note(m, 0.08, 0.5) for m in (72, 76, 79, 84, 88, 91)] + [chip_note(96, 0.5, 0.5)])


def projector(d):
    n = int(d * SR)
    x = np.zeros(n)
    step = int(SR / 24)
    for i in range(0, n, step):
        m = int(0.012 * SR)
        click = filt(ns(0.012)[:m], "bandpass", [1500, 5000]) * np.exp(-T(m) / 0.003)
        x[i:i + m] += click[: len(x[i:i + m])]
    crackle = np.zeros(n)
    k = int(d * 90)
    crackle[rng.integers(0, n, k)] = rng.uniform(-1, 1, k)
    crackle = filt(np.convolve(crackle, np.exp(-T(80) / 0.0005))[:n], "hp", 2000)
    return x * 0.5 + crackle * 0.7 + filt(ns(d)[:n], "bandpass", [300, 3000]) * 0.02


def tape_rewind(d):
    n = int(d * SR); t = T(n); k = t / d
    f = 300 + 2600 * k ** 1.2
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.4 + filt(ns(d)[:n], "bandpass", [1500, 6000]) * 0.6
    return y * np.minimum(t / 0.03, 1) * np.minimum((d - t) / 0.02, 1) * (0.6 + 0.4 * np.sin(2 * np.pi * 30 * t))



# ------------------------------------------------------------------ extra SFX for this edit
def snip():
    n = int(0.18 * SR); out = np.zeros(n)
    for d0, g in ((0.0, 0.8), (0.07, 1.0)):
        m = int(0.05 * SR); t = T(m)
        y = sum(np.sin(2 * np.pi * f * t) for f in (3100, 4650, 6200)) / 3 * np.exp(-t / 0.012)
        y += filt(ns(0.05)[:m], "hp", 4000) * np.exp(-t / 0.002)
        i = int(d0 * SR); out[i:i + m] += g * y
    return out


def click():
    n = int(0.08 * SR); t = T(n)
    return (filt(ns(0.08)[:n], "bandpass", [1500, 6000]) * np.exp(-t / 0.004) + np.sin(2 * np.pi * 900 * t) * np.exp(-t / 0.01) * 0.4)


def swish(d=0.22):
    return whoosh(d, 1200, 9000) * 0.8


def tear(d=0.45):
    n = int(d * SR); t = T(n)
    x = filt(ns(d)[:n], "bandpass", [900, 7000])
    am = 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * (55 + 40 * t / d) * t))
    return x * (0.35 + 0.65 * am) * np.minimum(t / 0.03, 1) * (1 - t / d) ** 0.5


def marker(d=0.35):
    n = int(d * SR); t = T(n)
    f = 1800 + 600 * np.sin(2 * np.pi * 7 * t)
    x = filt(ns(d)[:n], "bandpass", [1500, 5000]) * (0.6 + 0.4 * np.sin(2 * np.pi * np.cumsum(f) / SR))
    return x * np.sin(np.pi * t / d) * 0.7


def shutter():
    n = int(0.2 * SR); t = T(n)
    a = filt(ns(0.2)[:n], "bandpass", [1500, 7000])
    return a * (np.exp(-t / 0.01) + (t > 0.07) * np.exp(-np.clip(t - 0.07, 0, None) / 0.012))


def stamp():
    n = int(0.6 * SR); t = T(n)
    f = 40 + 60 * np.exp(-t / 0.05)
    body = np.tanh(2.2 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.18))
    return body + filt(ns(0.6)[:n], "bandpass", [600, 3000]) * np.exp(-t / 0.025) * 1.2


def crumple(d=0.6):
    n = int(d * SR); t = T(n)
    k = int(1400 * d); x = np.zeros(n)
    x[rng.integers(0, n, k)] = rng.uniform(-1, 1, k)
    y = filt(np.convolve(x, np.exp(-T(200) / 0.003) * rng.standard_normal(200))[:n], "hp", 1200)
    return y * np.minimum(t / (d * 0.5), 1) * np.minimum((d - t) / 0.08, 1)


def room_tone(d):
    n = int(d * SR)
    return filt(ns(d)[:n], "lp", 600) * 0.012


# ------------------------------------------------------------------ music: editorial house, 118 BPM
BPM = 118
BEAT = 60 / BPM
PROG = [([62, 65, 69, 72], 38), ([60, 64, 67, 71], 36), ([57, 60, 64, 67], 33), ([59, 62, 65, 69], 35)]


def keys(chord, d):
    n = int(d * SR)
    y = sum(np.sin(2 * np.pi * hz(m) * T(n)) + 0.35 * np.sin(2 * np.pi * 2 * hz(m) * T(n)) * np.exp(-T(n) / 0.15) for m in chord)
    return y / len(chord) * env(n, 0.004, 0.22)


def groove(seg, d, layers=2, t_offset=0.0):
    k = 0
    while k * BEAT < d:
        tb = k * BEAT
        chord, root = PROG[(k // 4) % 4]
        place(seg, kick(), tb, 0.9)
        if k % 2 == 1:
            place(seg, clap(), tb, 0.42)
        for s in range(4):
            place(seg, hat(), tb + s * BEAT / 4, 0.09 if s % 2 else 0.05)
        place(seg, hat(True), tb + BEAT / 2, 0.16)
        place(seg, keys(chord, BEAT * 0.45), tb + BEAT * 0.5, 0.55)
        if k % 2 == 0:
            place(seg, keys(chord, BEAT * 0.3), tb + BEAT * 0.75, 0.35)
        place(seg, bass(root + 12, BEAT * 0.4), tb + BEAT / 2, 0.42)
        if layers >= 2:
            place(seg, bass(root + 12, BEAT * 0.2), tb + BEAT * 0.75, 0.3)
            if k % 4 == 3:
                place(seg, keys([c + 12 for c in chord], BEAT * 0.25), tb + BEAT * 0.25, 0.3)
            for s in (1, 3):
                place(seg, hat(), tb + s * BEAT / 4 + BEAT * 0.03, 0.06)
        k += 1
    # kick sidechain pump on everything but the kick
    pump = np.ones(len(seg))
    for kk in range(int(d / BEAT) + 1):
        i = int(kk * BEAT * SR); m = int(BEAT * 0.8 * SR)
        s_ = pump[i:i + m]
        s_ *= 1 - 0.45 * np.exp(-T(len(s_)) / 0.09)
    seg *= 0.7 + 0.3 * pump


def section(buf, t0, t1, fn):
    seg = np.zeros(int((t1 - t0) * SR) + SR)
    fn(seg, t1 - t0)
    seg = seg[: int((t1 - t0) * SR)]
    f = int(0.015 * SR)
    seg[:f] *= np.linspace(0, 1, f)
    seg[-f:] *= np.linspace(1, 0, f)
    place(buf, seg, t0)


def build():
    v = voice()
    E = lambda w, after=0.0, end=False: ot(wt(w, after, end))  # noqa: E731
    t_music = E("music.", 32.9, True) - 0.02
    t_paper = E("paper", 37)
    t_no = E("No", 41.3)
    t_claude = E("Claude.", 45.9)
    mus = np.zeros(N)
    section(mus, t_music, t_paper, lambda s, d: groove(s, d, 1))
    section(mus, t_paper, t_no, lambda s, d: groove(s, d, 2))
    # breakdown under the crossed-out apps: bass pulses only
    def breakdown(seg, d):
        k = 0
        while k * BEAT < d:
            place(seg, bass(38 + 12, BEAT * 0.9), k * BEAT, 0.4)
            place(seg, hat(), k * BEAT + BEAT / 2, 0.06)
            k += 1
        r = riser(d, 150, 2500) * 0.5
        seg[:len(r)] += r[: len(seg)]
    section(mus, t_no, t_claude, breakdown)
    section(mus, t_claude, OUT_DUR, lambda s, d: groove(s, d, 2))
    ve = np.sqrt(sosfiltfilt(butter(1, 5, "lp", fs=SR, output="sos"), v ** 2) + 1e-12)
    duck = 1 - 0.6 * np.clip(ve / 0.05, 0, 1)
    mus = mus * duck * 0.3

    fx = np.zeros(N)
    S = lambda x, t, g: place(fx, x, t, g)  # noqa: E731
    place(fx, room_tone(E("Cut", 5)), 0.0, 1.0)
    for k in range(int(E("Cut", 5) / 1.0)):
        S(tick(), k * 1.0 + 0.3, 0.12)
    S(snip(), E("pauses.", 6), 0.6)
    S(whoosh(0.35, 500, 6000), E("pauses.", 6, True), 0.35)
    S(click(), E("captions.", 10), 0.55)
    S(pop(), E("pop.", 12), 0.6)
    for w_, a in (("style.", 14), ("Again.", 15.4), ("again.", 16.8)):
        S(swish(), E(w_, a), 0.5)
        S(pop(), E(w_, a) + 0.08, 0.3)
    S(tear(), E("background.", 19.3), 0.6)
    S(marker(0.6), E("background.", 19.3) + 0.25, 0.35)
    S(boom(1.2), E("cover.", 21.9), 0.55)
    S(shutter(), E("cover.", 21.9), 0.45)
    for i in range(4):
        S(marker(0.25), E("notes", 23.8) + 0.12 + 0.38 * i, 0.4)
    S(marker(0.4), E("designer", 26), 0.3)
    for i in range(3):
        S(shutter(), E("frames.", 29) + 0.09 * i, 0.4)
    for i in range(4):
        S(whoosh(0.3, 600, 6000), E("clips.", 31.7) - 0.1 + 0.12 * i, 0.25)
    S(riser(0.7, 200, 3000), t_music - 0.7, 0.4)
    S(crash_(), t_music, 0.3)
    S(whoosh(0.4, 400, 7000), E("sound", 34.5), 0.45)
    S(pop(), E("effects", 34.8), 0.5)
    S(boom(0.9), E("everything.", 35.3), 0.45)
    S(tear(0.5), E("paper", 37.4), 0.55)
    S(crumple(0.6), E("cut.", 37.7), 0.45)
    S(whoosh(0.6, 200, 5000), E("move.", 39.6), 0.45)
    for w_ in ("Premiere", "After", "DaVinci,", "Higgsfield,"):
        t_ = E(w_, 41.5)
        S(stamp(), t_, 0.55)
    for w_ in ("no", "no", "no"):
        pass
    for t_ in (E("no", 42.5), E("no", 43.7), E("no", 44.7), E("just", 45.6)):
        S(marker(0.22), t_ - 0.05, 0.45)
    S(boom(1.6), t_claude, 0.7)
    S(crash_(), t_claude, 0.4)
    S(tape_rewind(0.45), E("From", 46.8), 0.4)
    S(whoosh(0.5, 300, 6000), E("this.", 48.2), 0.45)
    S(pop(), E("Comment", 49), 0.45)
    for k in range(4):
        S(key(), E("EDIT", 49.5) + 0.08 * k, 0.45)
    S(ding(), E("how.", 50.5) + 0.1, 0.3)
    fx = filt(fx, "hp", 30)

    mix = v + mus + fx * 0.6
    tmp = os.path.join(WORK, "_mix.wav")
    mix = mix[: int(OUT_DUR * SR)]
    f = int(0.25 * SR)
    mix[-f:] *= np.linspace(1, 0, f)
    mix /= max(1.0, np.max(np.abs(mix)) / 0.95)
    wavfile.write(tmp, SR, (mix * 32767).astype(np.int16))
    # two-pass EBU R128 loudness normalisation to -14 LUFS, true peak -1.5 dBTP
    meas = subprocess.run([FFMPEG, "-hide_banner", "-i", tmp, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    j = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
    out = os.path.join(OUT, "mix.wav")
    os.makedirs(OUT, exist_ok=True)
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", tmp, "-af",
                    f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
                    f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true",
                    "-ar", str(SR), "-ac", "2", out], check=True)
    os.remove(tmp)
    act = np.convolve(v ** 2, np.ones(4800) / 4800, "same") > 1e-4
    db = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)  # noqa: E731
    print(f"mix {OUT_DUR:.2f}s | input loudness {j['input_i']} LUFS -> -14 | speaking: voice {db(v[act]):.1f} dB, "
          f"music {db(mus[act]):.1f} dB")


def crash_(d=1.8):
    n = int(d * SR); t = T(n)
    return filt(ns(d)[:n], "hp", 3500) * np.exp(-t / 0.6) * 0.6


if __name__ == "__main__":
    build()
