"""Audio: voice cut to the EDL + cleaned up, an original synthesised music bed (ducked under the voice),
a cinematic drone for the documentary beat, and SFX locked to the words.

    python3 sound.py  ->  out/mix.wav
"""

import os
import subprocess

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, sosfiltfilt

from common import DUR, FFMPEG, OUT, RAW, SEGS, WORDS, wt

SR = 44100
N = int(DUR * SR) + SR
rng = np.random.default_rng(11)


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


# ------------------------------------------------------------------ voice
def voice():
    p = subprocess.run([FFMPEG, "-v", "error", "-i", RAW, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                       capture_output=True, check=True)
    src = np.frombuffer(p.stdout, np.int16).astype(np.float64) / 32768
    src = filt(src, "hp", 75, 4)
    out = np.zeros(N)
    xf = int(0.012 * SR)
    pos = 0
    for a, b, _ in SEGS:
        x = src[int(a * SR):int(b * SR)].copy()
        ramp = np.linspace(0, 1, xf)
        x[:xf] *= ramp
        x[-xf:] *= ramp[::-1]
        out[pos:pos + len(x)] += x
        pos += len(x)
    # gentle compression (RMS envelope follower) + presence lift
    env = np.sqrt(sosfiltfilt(butter(1, 12, "lp", fs=SR, output="sos"), out ** 2) + 1e-9)
    thr = 10 ** (-24 / 20)
    gain = np.where(env > thr, (env / thr) ** (1 / 3 - 1), 1.0)
    out = out * gain
    out = out + 0.25 * filt(out, "bandpass", [2500, 6000])
    out *= 10 ** (-3 / 20) / (np.max(np.abs(out)) + 1e-9)
    return out, env


# ------------------------------------------------------------------ instruments
def kick():
    n = int(0.42 * SR); t = T(n)
    f = 46 + 120 * np.exp(-t / 0.03)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(2.0 * np.sin(ph) * np.exp(-t / 0.18)) * 0.9


def snap():
    n = int(0.25 * SR); t = T(n)
    return filt(ns(0.25)[:n], "bandpass", [1200, 6000]) * np.exp(-t / 0.05) * 0.8


def hat(open_=False):
    d = 0.25 if open_ else 0.05
    n = int(d * SR)
    return filt(ns(d)[:n], "hp", 7500) * np.exp(-T(n) / (0.08 if open_ else 0.015))


def epiano(m, d):
    n = int(d * SR); t = T(n); f = hz(m)
    y = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.3) \
        + 0.12 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t / 0.1)
    return y * np.minimum(t / 0.005, 1) * np.exp(-t / 1.2) * np.minimum((d - t) / 0.05, 1)


def sub(m, d):
    n = int(d * SR); t = T(n)
    return np.sin(2 * np.pi * hz(m) * t) * np.minimum(t / 0.01, 1) * np.minimum((d - t) / 0.03, 1)


def pad(chord, d):
    n = int(d * SR); t = T(n)
    y = sum(saw(hz(m + det), n, rng.uniform()) for m in chord for det in (-0.08, 0.08))
    y = filt(y, "lp", 1400)
    return y * np.minimum(t / 0.8, 1) * np.minimum((d - t) / 0.8, 1) * 0.12


# ------------------------------------------------------------------ SFX
def whoosh(d=0.4, lo=400, hi=5000):
    n = int(d * SR)
    x = ns(d)[:n]
    out = np.zeros(n)
    seg = 24
    for s in range(seg):
        a, b = s * n // seg, (s + 1) * n // seg
        c = lo * (hi / lo) ** np.sin(np.pi * s / seg)
        out[a:b] = filt(x, "bandpass", [c * 0.6, min(c * 1.6, 20000)])[a:b]
    return out * np.sin(np.pi * T(n) / d) ** 2 * 1.4


def pop():
    n = int(0.12 * SR); t = T(n)
    f = 260 + 900 * np.exp(-t / 0.018)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / 0.04) * 0.9 + filt(ns(0.12)[:n], "hp", 3000) * np.exp(-t / 0.003) * 0.3


def sparkle():
    n = int(0.8 * SR); out = np.zeros(n)
    for i, m in enumerate([84, 88, 91, 96, 100, 103]):
        k = int(0.45 * SR); t = T(k)
        s = int(i * 0.04 * SR)
        out[s:s + k] += (np.sin(2 * np.pi * hz(m) * t) * np.exp(-t / 0.12))[: n - s]
    return out * 0.35


def boom(d=2.2):
    n = int(d * SR); t = T(n)
    f = 28 + 55 * np.exp(-t / 0.12)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(1.8 * np.sin(ph) * np.exp(-t / 0.7)) + filt(ns(d)[:n], "lp", 260) * np.exp(-t / 0.25) * 0.8


def braam(d=2.6):
    n = int(d * SR); t = T(n)
    y = sum(saw(hz(m) * (1 + 0.002 * v), n, rng.uniform()) for m in (33, 40, 45) for v in (-1, 1))
    cut = 180 + 1400 * np.exp(-t / 0.5)
    out = np.zeros(n)
    seg = 30
    for s in range(seg):
        a, b = s * n // seg, (s + 1) * n // seg
        out[a:b] = filt(y, "lp", float(cut[a]))[a:b]
    return np.tanh(out * 0.8) * np.minimum(t / 0.02, 1) * np.exp(-t / 1.1) + boom(d) * 0.6


def glass():
    d = 1.6
    n = int(d * SR); t = T(n)
    hit = filt(ns(d)[:n], "hp", 1500) * np.exp(-t / 0.05) * 1.2
    crack = np.zeros(n)
    k = 900
    idx = (rng.power(0.35, k) * n * 0.9).astype(int)
    crack[idx] = rng.uniform(-1, 1, k)
    crack = filt(np.convolve(crack, np.exp(-T(200) / 0.0008))[:n], "hp", 2500) * 2.0
    tinkle = np.zeros(n)
    for _ in range(38):
        s0 = int(rng.uniform(0.02, 1.2) * SR)
        f0 = rng.uniform(3000, 9000)
        m = int(0.25 * SR); tt = T(m)
        y = np.sin(2 * np.pi * f0 * tt) * np.exp(-tt / rng.uniform(0.02, 0.08)) * rng.uniform(0.1, 0.35)
        tinkle[s0:s0 + m] += y[: max(0, min(m, n - s0))]
    return hit + crack + tinkle + boom(1.6) * 0.7


def dust(d=1.1, rev=False):
    n = int(d * SR); t = T(n)
    x = ns(d)[:n]
    out = np.zeros(n)
    seg = 30
    for s in range(seg):
        a, b = s * n // seg, (s + 1) * n // seg
        c = 6000 * (600 / 6000) ** (s / seg)
        out[a:b] = filt(x, "bandpass", [c * 0.5, min(c * 1.8, 20000)])[a:b]
    grains = np.zeros(n)
    k = 1400
    grains[rng.integers(0, n, k)] = rng.uniform(-1, 1, k)
    grains = filt(np.convolve(grains, np.exp(-T(120) / 0.0006))[:n], "hp", 3000)
    y = (out * 0.8 + grains) * np.sin(np.pi * t / d) ** 1.5
    return y[::-1] if rev else y


def shimmer(d=1.0):
    n = int(d * SR); t = T(n); out = np.zeros(n)
    for m in (72, 76, 79, 84, 88, 91):
        out += np.sin(2 * np.pi * hz(m) * t + rng.uniform(0, 6)) * (0.6 + 0.4 * np.sin(2 * np.pi * 7 * t + m))
    return out / 6 * np.minimum(t / (d * 0.7), 1) * np.minimum((d - t) / 0.2, 1) * 0.6


def tick():
    n = int(0.03 * SR); t = T(n)
    return (np.sin(2 * np.pi * 2600 * t) * 0.6 + filt(ns(0.03)[:n], "hp", 5000) * 0.5) * np.exp(-t / 0.004)


def key():
    n = int(0.06 * SR); t = T(n)
    return (filt(ns(0.06)[:n], "hp", 2500) * np.exp(-t / 0.005) + np.sin(2 * np.pi * 1700 * t) * np.exp(-t / 0.01) * 0.5)


def ding():
    n = int(0.9 * SR); t = T(n)
    return (np.sin(2 * np.pi * hz(88) * t) + 0.5 * np.sin(2 * np.pi * hz(95) * t)) * np.exp(-t / 0.25) * 0.5


def riser(d, f0=200, f1=2400):
    n = int(d * SR); t = T(n); k = t / d
    f = f0 * (f1 / f0) ** (k ** 1.5)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * 0.3 + filt(ns(d)[:n], "bandpass", [800, 6000]) * 0.5) * k ** 2


def shutter():
    n = int(0.2 * SR); t = T(n)
    a = filt(ns(0.2)[:n], "bandpass", [1500, 7000])
    env = np.exp(-t / 0.01) + (t > 0.07) * np.exp(-np.clip(t - 0.07, 0, None) / 0.012)
    return a * env


# ------------------------------------------------------------------ music
BPM = 96
BEAT = 60 / BPM
PROG = [([57, 60, 64, 67], 45), ([53, 57, 60, 64], 41), ([48, 52, 55, 59], 36), ([55, 59, 62, 65], 43)]


def music(t_beat_in, t_doc0, t_doc1, t_end):
    """Warm lo-fi groove. Soft intro, beat drops at `t_beat_in`, drops out for the documentary beat."""
    m = np.zeros(N)
    bar = BEAT * 4
    nb = int(t_end / bar) + 2
    for b in range(nb):
        t0 = b * bar
        chord, root = PROG[b % 4]
        if t0 > t_end:
            break
        in_doc = t_doc0 - 0.2 < t0 < t_doc1 - bar * 0.5
        if in_doc:
            continue
        place(m, pad(chord, bar + 0.4), t0, 0.9)
        for i, mm in enumerate(chord):
            place(m, epiano(mm + 12, bar), t0 + i * 0.012, 0.10)
        place(m, epiano(chord[1] + 12, BEAT * 1.5), t0 + BEAT * 2.5, 0.07)
        if t0 >= t_beat_in - 0.01:
            for k in range(4):
                tb = t0 + k * BEAT
                if t_doc0 - 0.1 < tb < t_doc1:
                    continue
                if k in (0, 2):
                    place(m, kick(), tb, 0.55)
                if k in (1, 3):
                    place(m, snap(), tb, 0.22)
                place(m, hat(), tb + BEAT / 2, 0.16)
                place(m, hat(), tb, 0.08)
                place(m, sub(root, BEAT * 0.9), tb, 0.30 if k in (0, 2) else 0.18)
    # documentary drone
    d = t_doc1 - t_doc0
    n = int(d * SR); t = T(n)
    drone = sum(np.sin(2 * np.pi * hz(mm) * t + rng.uniform(0, 6)) for mm in (33, 40, 45, 52)) / 4
    drone += filt(ns(d)[:n], "lp", 400) * 0.25
    drone *= np.minimum(t / 1.0, 1) * np.minimum((d - t) / 0.25, 1)
    place(m, drone, t_doc0, 0.5)
    fade = np.ones(N)
    i0, i1 = int((t_end - 1.2) * SR), int(t_end * SR)
    fade[i0:i1] = np.linspace(1, 0, i1 - i0)
    fade[i1:] = 0
    return m * fade


def build():
    v, env = voice()
    t_end = DUR
    doc0 = wt("cinematic", 62)
    doc1 = wt("That's", 73)
    mus = music(wt("Watch", 3), doc0, doc1, t_end)
    # sidechain-ish ducking under the voice
    venv = np.sqrt(sosfiltfilt(butter(1, 4, "lp", fs=SR, output="sos"), v ** 2) + 1e-12)
    duck = 1 - 0.55 * np.clip(venv / 0.05, 0, 1)
    mus = mus * duck * 0.55

    fx = np.zeros(N)
    S = lambda x, t, g: place(fx, x, t, g)  # noqa: E731
    S(whoosh(0.5), wt("Watch", 3) - 0.15, 0.35)
    S(whoosh(0.45, 300, 4000), wt("Zoom", 4.5) - 0.1, 0.4)
    S(pop(), wt("here", 7.7) + 0.05, 0.55)
    S(sparkle(), wt("3D.", 8.8), 0.5)
    S(whoosh(0.35, 600, 3000), wt("grab", 11.5), 0.25)
    S(riser(1.0), wt("throw", 13.0) - 0.2, 0.35)
    S(whoosh(0.7, 200, 7000), wt("straight", 14.0), 0.6)
    S(glass(), wt("camera.", 14.6, end=True) - 0.28, 0.8)
    S(dust(0.6), wt("Okay.", 16.6) - 0.05, 0.25)
    S(pop(), wt("Harder", 17.2), 0.3)
    S(whoosh(0.8, 200, 3000), wt("Separate", 18.4), 0.45)
    for w_ in ("background,", "me,", "text."):
        S(pop(), wt(w_, 21), 0.45)
    S(whoosh(0.5, 300, 5000), wt("text.", 22.4, end=True) + 0.1, 0.35)
    S(dust(1.3), wt("me.", 25.0) + 0.1, 0.6)
    S(shimmer(1.0), wt("back.", 28.3) - 0.25, 0.45)
    S(dust(0.8, rev=True), wt("back.", 28.3) - 0.1, 0.35)
    S(whoosh(0.6, 300, 4000), wt("frame", 34.4), 0.45)
    S(whoosh(0.4, 500, 5000), wt("left", 36.2), 0.3)
    for w_, a in (("anatomy", 37.5), ("hook,", 40.7), ("retention,", 41.8), ("share.", 43.9)):
        S(pop(), wt(w_, a), 0.45)
    S(ding(), wt("share.", 43.9) + 0.35, 0.35)
    S(whoosh(0.6, 300, 4000), wt("Back", 47.0), 0.45)
    S(whoosh(1.0, 150, 3000), wt("floating", 51.3) - 0.2, 0.45)
    for k in range(4):
        S(pop(), wt("floating", 51.3) + 0.15 * k, 0.25)
    S(sparkle(), wt("Perfect!", 54.2), 0.45)
    S(whoosh(0.5, 400, 6000), wt("Last", 56.8) - 0.15, 0.35)
    S(braam(), doc0, 0.55)
    S(boom(), wt("dramatic", 67.4), 0.6)
    S(riser(2.0, 90, 900), wt("slow", 68.9), 0.18)
    S(braam(3.0), wt("movie", 70.9), 0.5)
    S(whoosh(0.4, 500, 6000), wt("That's", 73.6) - 0.1, 0.4)
    S(whoosh(0.5, 300, 5000), wt("all", 77.0) - 0.1, 0.4)
    for k in range(8):
        S(tick(), wt("all", 77.0) + 0.05 + 0.06 * k, 0.25)
    S(sparkle(), wt("edited", 78.2), 0.45)
    S(whoosh(0.4, 500, 5000), wt("AI.", 79.3) + 0.1, 0.35)
    S(pop(), wt("Comment", 80.5), 0.4)
    t_edit = wt("EDIT", 81.0)
    for k in range(4):
        S(key(), t_edit + 0.09 * k, 0.4)
    S(pop(), wt("how.", 82.6), 0.4)
    S(ding(), wt("how.", 82.6) + 0.15, 0.25)
    fx = filt(fx, "hp", 30)

    mix = v * 0.95 + mus + fx * 0.8
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    mix = mix[: int(DUR * SR)]
    fade = int(0.35 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix *= 10 ** (-1 / 20) / np.max(np.abs(mix))
    os.makedirs(OUT, exist_ok=True)
    wavfile.write(os.path.join(OUT, "mix.wav"), SR, (np.stack([mix, mix], 1) * 32767).astype(np.int16))
    print("mix", len(mix) / SR, "s")


if __name__ == "__main__":
    build()
