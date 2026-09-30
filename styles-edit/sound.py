"""Audio for the 5-styles edit: every style switch also switches the music genre.
modern beat -> news bed -> trailer percussion -> cartoon bounce -> chiptune -> ragtime piano -> tape rewind -> beat drop.
The voice is cut, time-stretched (pitch kept), gets reverb in the trailer, a gramophone EQ in the 1920s and is muted
under the silent-film card.

    python3 sound.py  ->  out/mix.wav
"""

import os
import subprocess

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt, sosfiltfilt

from common import DUR, FFMPEG, OUT, OUT_DUR, RAW, SEGS, SPEED, WORK, ot, wt

SR = 44100
N = int(OUT_DUR * SR) + SR
rng = np.random.default_rng(5)


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


# ------------------------------------------------------------------ voice
def voice():
    p = subprocess.run([FFMPEG, "-v", "error", "-i", RAW, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                       capture_output=True, check=True)
    src = np.frombuffer(p.stdout, np.int16).astype(np.float64) / 32768
    src = filt(src, "hp", 80, 4)
    out = np.zeros(int(DUR * SR) + SR)
    xf = int(0.012 * SR)
    pos = 0
    for a, b, _ in SEGS:
        x = src[int(a * SR):int(b * SR)].copy()
        r = np.linspace(0, 1, xf)
        x[:xf] *= r
        x[-xf:] *= r[::-1]
        out[pos:pos + len(x)] += x
        pos += len(x)
    tmp_in, tmp_out = os.path.join(WORK, "_v_in.wav"), os.path.join(WORK, "_v_out.wav")
    wavfile.write(tmp_in, SR, (np.clip(out, -1, 1) * 32767).astype(np.int16))
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", tmp_in, "-af", f"atempo={SPEED}", tmp_out], check=True)
    out = wavfile.read(tmp_out)[1].astype(np.float64) / 32768
    os.remove(tmp_in)
    os.remove(tmp_out)
    out = np.pad(out, (0, max(0, N - len(out))))[:N]
    e = np.sqrt(sosfiltfilt(butter(1, 12, "lp", fs=SR, output="sos"), out ** 2) + 1e-9)
    thr = 10 ** (-24 / 20)
    out = out * np.where(e > thr, (e / thr) ** (1 / 3 - 1), 1.0)
    out = out + 0.25 * filt(out, "bandpass", [2500, 6000])
    return out * 10 ** (-3 / 20) / (np.max(np.abs(out)) + 1e-9)


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


# ------------------------------------------------------------------ music by section
def section(buf, t0, t1, fn):
    seg = np.zeros(int((t1 - t0) * SR) + SR)
    fn(seg, t1 - t0)
    seg = seg[: int((t1 - t0) * SR)]
    f = int(0.02 * SR)
    seg[:f] *= np.linspace(0, 1, f)
    seg[-f:] *= np.linspace(1, 0, f)
    place(buf, seg, t0)


PROG = [([57, 60, 64], 45), ([53, 57, 60], 41), ([48, 52, 55], 36), ([55, 59, 62], 43)]


def modern(seg, d, bpm=126, full=True):
    beat = 60 / bpm
    k = 0
    while k * beat < d:
        tb = k * beat
        chord, root = PROG[(k // 4) % 4]
        place(seg, kick(), tb, 0.85)
        if k % 2 == 1:
            place(seg, clap(), tb, 0.4)
        for s in range(2):
            place(seg, hat(), tb + s * beat / 2, 0.12 if s else 0.08)
        if full:
            place(seg, hat(True), tb + beat / 2, 0.18)
            place(seg, stab(chord, 0.16), tb + beat / 2, 0.14)
            place(seg, bass(root, beat * 0.45), tb + beat / 2, 0.4)
        k += 1


def news_bed(seg, d, bpm=120):
    beat = 60 / bpm
    place(seg, sum(stab([60, 64, 67], 0.25) * g for g in (1,)), 0.0, 0.5)
    for i, (m, g) in enumerate(((60, 0.5), (60, 0.5), (67, 0.8))):
        place(seg, stab([m, m + 4, m + 7], 0.3), i * beat * 0.5, g)
        place(seg, tom(70), i * beat * 0.5, 0.5)
    k = 0
    while k * beat < d:
        tb = k * beat
        for s in range(4):
            place(seg, tick(), tb + s * beat / 4, 0.35 if s == 0 else 0.18)
        if k % 2 == 0:
            place(seg, tom(65, 0.5), tb, 0.45)
        root = [48, 48, 51, 46][(k // 2) % 4]
        for s in range(2):
            n = int(beat / 2 * SR)
            place(seg, filt(saw(hz(root + 12), n) + saw(hz(root + 19), n), "lp", 2200) * env(n, 0.005, 0.12) * 0.12, tb + s * beat / 2)
        place(seg, bass(root, beat * 0.9), tb, 0.3)
        k += 1


def trailer_bed(seg, d):
    place(seg, braam(2.6), 0.0, 0.7)
    beat = 60 / 64
    k = 1
    while k * beat < d:
        place(seg, tom(55, 1.0), k * beat, 0.8)
        place(seg, boom(1.0), k * beat, 0.25)
        k += 1
    n = int(d * SR); t = T(n)
    drone = sum(saw(hz(m), n, rng.uniform()) for m in (33, 40, 45))
    place(seg, filt(drone, "lp", 420) / 3 * np.minimum(t / 0.8, 1), 0.0, 0.35)


def cartoon_bed(seg, d, bpm=150):
    beat = 60 / bpm
    mel = [72, 76, 79, 76, 74, 77, 81, 77, 72, 76, 79, 84, 83, 79, 74, 71]
    k = 0
    while k * beat / 2 < d:
        tb = k * beat / 2
        place(seg, marimba(mel[k % len(mel)]), tb, 0.55)
        if k % 2 == 0:
            root = [48, 53, 55, 48][(k // 8) % 4]
            n = int(beat * 0.8 * SR)
            place(seg, (np.sin(2 * np.pi * hz(root) * T(n)) + 0.3 * sq(hz(root), n) * 0.3) * env(n, 0.005, 0.15) * 0.5,
                  tb if (k // 2) % 2 == 0 else tb, 1.0)
        if k % 4 == 2:
            place(seg, hat(), tb, 0.15)
        k += 1


def chiptune(seg, d, bpm=176):
    """Bouncy, swung 8-bit platformer tune (original melody): square lead, triangle bass, noise drums."""
    beat = 60 / bpm
    lead = [76, 76, 0, 76, 0, 72, 76, 0, 79, 0, 0, 0, 67, 0, 0, 0,
            72, 0, 0, 67, 0, 0, 64, 0, 0, 69, 0, 71, 0, 70, 69, 0]
    bassn = [48, 0, 55, 0, 48, 0, 55, 0, 43, 0, 50, 0, 43, 0, 50, 0]
    k = 0
    while k * beat / 2 < d:
        tb = k * beat / 2 + (beat * 0.08 if k % 2 else 0)      # swing
        m = lead[k % len(lead)]
        if m:
            place(seg, chip_note(m, beat * 0.45, 0.25), tb, 0.55)
            place(seg, chip_note(m - 12, beat * 0.45, 0.5), tb, 0.12)
        bm = bassn[k % len(bassn)]
        if bm:
            place(seg, tri(bm, beat * 0.45), tb, 0.9)
        if k % 4 == 0:
            place(seg, filt(ns(0.06), "lp", 2500) * env(int(0.06 * SR), 0.001, 0.02), tb, 0.5)
        if k % 4 == 2:
            place(seg, filt(ns(0.08), "hp", 3000) * env(int(0.08 * SR), 0.001, 0.04), tb, 0.3)
        k += 1


def bump():
    n = int(0.12 * SR); t = T(n)
    f = 180 - 90 * t / 0.12
    return np.where((np.cumsum(f) / SR) % 1 < 0.5, 1.0, -1.0) * env(n, 0.001, 0.05) * 0.4


def jump():
    n = int(0.25 * SR); t = T(n)
    f = 300 + 900 * t / 0.25
    return np.where((np.cumsum(f) / SR) % 1 < 0.25, 1.0, -1.0) * env(n, 0.002, 0.15) * 0.25


def ragtime(seg, d, bpm=190):
    beat = 60 / bpm
    prog = [(48, [64, 67, 72]), (43, [62, 65, 71]), (48, [64, 67, 72]), (41, [65, 69, 72])]
    mel = [76, 79, 81, 79, 76, 74, 72, 74, 76, 76, 79, 84, 83, 81, 79, 77]
    k = 0
    while k * beat < d:
        tb = k * beat
        root, chord = prog[(k // 4) % 4]
        if k % 2 == 0:
            place(seg, piano(root - (12 if (k // 2) % 2 else 0), 0.5), tb, 0.9)
        else:
            for m in chord:
                place(seg, piano(m - 12, 0.3), tb, 0.45)
        place(seg, piano(mel[k % len(mel)], 0.35), tb + (beat * 0.5 if k % 3 == 1 else 0), 0.55)
        k += 1
    place(seg, projector(d), 0.0, 0.35)


def build():
    v = voice()
    E = lambda word, after, end=False: ot(wt(word, after, end))  # noqa: E731
    s_news, s_tr, s_ca, s_ga, s_old = (E("channel", 5) + 0.05 / SPEED, E("trailer", 10) + 0.05 / SPEED,
                                       E("cartoon", 15) + 0.05 / SPEED, E("game", 20) + 0.05 / SPEED,
                                       E("movie", 26) + 0.05 / SPEED)
    s_rw = ot(float(np.cumsum([0] + [e - s for s, e, _ in SEGS])[5]) - 0.62)   # rewind sits in the silence before "back"
    rw_d = 0.62 / SPEED
    sil0, sil1 = E("A", 28.8) - 0.12 / SPEED, E("editing.", 31.4, True) + 0.25 / SPEED

    # voice treatments
    v = window(v, s_tr, s_ca - 0.05, lambda x: reverb(x, 1.8, 0.32), 0.05)
    v = window(v, s_old, sil0, gramophone, 0.04)
    v = window(v, sil0, sil1, lambda x: x * 0.0, 0.04)
    v = window(v, s_rw, s_rw + rw_d, lambda x: x * 0.0, 0.02)

    mus = np.zeros(N)
    section(mus, 0.0, s_news, lambda seg, d: modern(seg, d, 126, full=False))
    section(mus, s_news - 0.05, s_tr, news_bed)
    section(mus, s_tr, s_ca, trailer_bed)
    section(mus, s_ca, s_ga, cartoon_bed)
    section(mus, s_ga, s_old, chiptune)
    section(mus, s_old, s_rw, ragtime)
    section(mus, s_rw + rw_d, OUT_DUR, lambda seg, d: modern(seg, d, 126, full=True))
    ve = np.sqrt(sosfiltfilt(butter(1, 5, "lp", fs=SR, output="sos"), v ** 2) + 1e-12)
    duck = 1 - 0.55 * np.clip(ve / 0.04, 0, 1)
    # the silent-film card: piano comes up to carry it
    lift = np.ones(N)
    i0, i1 = int(sil0 * SR), int(sil1 * SR)
    lift[i0:i1] = 2.2
    mus = mus * duck * lift * 0.26

    fx = np.zeros(N)
    S = lambda x, t, g: place(fx, x, t, g)  # noqa: E731
    for i in range(5):
        S(pop(), E("five", 1.5) + 0.07 * i / SPEED, 0.45)
    S(ding(91), E("times", 2), 0.3)
    S(riser(0.8), E("Watch", 4) - 0.7, 0.35)
    S(whoosh(0.5), E("Watch", 4) + 0.1, 0.45)
    # switches
    S(whoosh(0.5, 300, 6000), s_news - 0.25, 0.55)
    S(boom(1.0), s_tr - 0.1, 0.6)
    S(boom(1.4), E("nobody", 12.5), 0.6)
    S(whoosh(0.6, 200, 5000), E("where", 12.5) - 0.1, 0.35)
    S(slide_whistle(0.5, True), s_ca - 0.35, 0.5)
    S(boing(), s_ca, 0.6)
    S(boing(0.4), E("Hi!", 16.5), 0.5)
    S(slide_whistle(0.5, False), E("colorful", 18), 0.3)
    for i in range(9):
        S(pop(), E("colorful", 18) - 0.1 / SPEED + 0.035 * i / SPEED, 0.25)
    S(coin(), s_ga - 0.1, 0.5)
    S(bump(), E("Level", 21.5) - 0.02, 0.6)
    S(coin(), E("Level", 21.5) + 0.05, 0.5)
    S(levelup(), E("Level", 21.5) + 0.15, 0.55)
    S(jump(), s_ga + 0.2, 0.4)
    for w_ in ("New", "skills", "unlocked"):
        S(coin(), E(w_, 22.5), 0.3)
    S(riser(0.6, 400, 3000), s_old - 0.5, 0.3)
    S(projector(0.4) * 2, s_old - 0.15, 0.6)
    S(tape_rewind(rw_d), s_rw, 0.7)
    S(boom(1.2), s_rw + rw_d, 0.55)
    S(whoosh(0.5, 300, 5000), E("didn't", 36), 0.45)
    for i in range(5):
        S(tick(), E("didn't", 36) + (0.05 + 0.06 * i) / SPEED, 0.3)
    S(boom(1.0), E("loud", 38.8), 0.4)
    S(pop(), E("comment", 40), 0.45)
    for i in range(4):
        S(key(), E("EDIT", 40.5) + 0.08 * i / SPEED, 0.45)
    S(ding(), E("how", 41.5) + 0.1, 0.3)
    fx = filt(fx, "hp", 30)

    mix = v + mus + fx * 0.7
    mix = np.tanh(mix * 1.15) / np.tanh(1.15)
    mix = mix[: int(OUT_DUR * SR)]
    f = int(0.3 * SR)
    mix[-f:] *= np.linspace(1, 0, f)
    mix *= 10 ** (-1 / 20) / np.max(np.abs(mix))
    os.makedirs(OUT, exist_ok=True)
    wavfile.write(os.path.join(OUT, "mix.wav"), SR, (np.stack([mix, mix], 1) * 32767).astype(np.int16))
    act = np.convolve(v ** 2, np.ones(4410) / 4410, "same") > 1e-4
    db = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)  # noqa: E731
    print(f"mix {len(mix) / SR:.2f}s | speaking: voice {db(v[act]):.1f} dB, music {db(mus[act]):.1f} dB")


if __name__ == "__main__":
    build()
