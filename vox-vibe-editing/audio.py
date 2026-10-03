"""Score + SFX + narration mix, all synthesised in numpy (no samples, no licensing).

    python3 audio.py   ->  out/mix.wav

Score: an 84 BPM documentary pulse in D minor (Dm9 - Bbmaj7 - Fmaj7 - C6), soft pads, a muted pluck
arpeggio and a sub heartbeat; it ducks under the narration. SFX are paper/marker foley on cue.
"""

import json
import math
import os

import numpy as np
import soundfile as sf
from scipy.signal import butter, resample_poly, sosfilt

import scenes
from script import N, SCENE, VOICE_IN

SR = 48000
DUR = N * SCENE
NS = int(SR * DUR)
BPM = 84
BEAT = 60 / BPM
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
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


# ---------------------------------------------------------------- score
CHORDS = [[50, 57, 60, 64, 65], [46, 53, 57, 62, 65], [41, 53, 57, 60, 64], [48, 55, 60, 64, 69]]


def pad(chord, d):
    n = int(d * SR)
    t = T(n)
    y = np.zeros(n)
    for m in chord:
        for det in (-0.08, 0.0, 0.07):
            f = hz(m + 12) * 2 ** (det / 12)
            y += np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) + 0.3 * np.sin(4 * np.pi * f * t)
    y = filt(y, "lp", 1800)
    env = np.minimum(t / 1.2, 1) * np.minimum((d - t) / 1.0, 1)
    return y * env / (len(chord) * 3)


def pluck(m, d=0.6):
    n = int(d * SR)
    t = T(n)
    f = hz(m)
    y = (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(4 * np.pi * f * t) + 0.15 * np.sin(6 * np.pi * f * t))
    return filt(y * np.exp(-t / 0.16), "lp", 2600)


def heartbeat():
    n = int(0.5 * SR)
    t = T(n)
    f = 44 + 50 * np.exp(-t / 0.04)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)


def score():
    buf = np.zeros(NS)
    bar = BEAT * 4
    nb = int(DUR / bar) + 2
    for b in range(nb):
        ch = CHORDS[b % 4]
        place(buf, pad(ch, bar + 1.2), b * bar - 0.3, 0.55)
        arp = [ch[1] + 12, ch[2] + 12, ch[3] + 12, ch[4] + 12, ch[3] + 12, ch[2] + 12, ch[3] + 12, ch[4] + 24]
        for k, m in enumerate(arp):
            t0 = b * bar + k * BEAT / 2
            if t0 > 2.0:   # let the cold open breathe
                place(buf, pluck(m), t0, 0.16 * (1.0 if k % 2 == 0 else 0.7))
        for k in range(4):
            t0 = b * bar + k * BEAT
            if t0 > 10.0:
                place(buf, heartbeat(), t0, 0.5 if k % 2 == 0 else 0.3)
    # tail fade
    t = T(NS)
    buf *= np.clip((DUR - t) / 2.5, 0, 1)
    return buf


# ---------------------------------------------------------------- SFX
def sfx_whoosh(d=0.42):
    n = int(d * SR)
    x = ns(d)[:n]
    out = np.zeros(n)
    seg = 24
    for s in range(seg):
        a, b = s * n // seg, (s + 1) * n // seg
        c = 400 * (4500 / 400) ** math.sin(math.pi * s / seg)
        out[a:b] = filt(x, "bandpass", [c * 0.6, c * 1.6])[a:b]
    k = T(n) / d
    return out * np.sin(np.pi * k) ** 2 * 1.4


def sfx_pop():
    n = int(0.12 * SR)
    t = T(n)
    f = 240 + 800 * np.exp(-t / 0.018)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.04) * 0.8
            + filt(ns(0.12)[:n], "hp", 3000) * np.exp(-t / 0.003) * 0.3)


def crackle(d, density, hp=1800, tau=0.0025):
    n = int(d * SR)
    x = np.zeros(n)
    k = int(density * d)
    x[rng.integers(0, n, k)] = rng.uniform(-1, 1, k)
    m = int(0.02 * SR)
    kern = np.exp(-T(m) / tau) * rng.standard_normal(m)
    return filt(np.convolve(x, kern)[:n], "hp", hp)


def sfx_rustle(d=0.4):
    n = int(d * SR)
    t = T(n)
    y = crackle(d, 500) + filt(ns(d)[:n], "bandpass", [2000, 9000]) * 0.25
    return y * np.sin(np.pi * t / d) * 0.9


def sfx_tear(d=0.45):
    n = int(d * SR)
    t = T(n)
    x = filt(ns(d)[:n], "bandpass", [900, 7000])
    am = 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * (55 + 40 * t / d) * t + 3 * np.sin(9 * t)))
    y = x * (0.35 + 0.65 * am) + crackle(d, 700, 1500) * 0.6
    return y * np.minimum(t / 0.03, 1) * (1 - t / d) ** 0.5 * 1.1


def sfx_snip():
    n = int(0.2 * SR)
    out = np.zeros(n)
    for d0, g in ((0.0, 0.7), (0.06, 1.0)):
        m = int(0.05 * SR)
        t = T(m)
        y = sum(np.sin(2 * np.pi * f * t) for f in (3100, 4650, 6200)) / 3 * np.exp(-t / 0.012)
        y += filt(ns(0.05)[:m], "hp", 4000) * np.exp(-t / 0.002)
        i = int(d0 * SR)
        out[i:i + m] += g * y
    return out


def sfx_stamp():
    n = int(0.7 * SR)
    t = T(n)
    f = 40 + 60 * np.exp(-t / 0.05)
    body = np.tanh(2.0 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.2))
    slap = filt(ns(0.7)[:n], "bandpass", [600, 3000]) * np.exp(-t / 0.025) * 1.1
    return (body + slap) * 0.8


def sfx_tick():
    n = int(0.03 * SR)
    t = T(n)
    return (np.sin(2 * np.pi * 2400 * t) * 0.6 + filt(ns(0.03)[:n], "hp", 5000) * 0.5) * np.exp(-t / 0.004)


def sfx_type():
    n = int(0.05 * SR)
    t = T(n)
    return (filt(ns(0.05)[:n], "hp", 2500) * np.exp(-t / 0.004)
            + np.sin(2 * np.pi * 1700 * t) * np.exp(-t / 0.008) * 0.5) * rng.uniform(0.6, 1.0)


def sfx_marker(d=0.45):
    """Felt tip dragged across paper: squeaky band-passed noise with a wobble."""
    n = int(d * SR)
    t = T(n)
    x = filt(ns(d)[:n], "bandpass", [1800, 5200])
    wob = 0.6 + 0.4 * np.sin(2 * np.pi * (11 + 6 * t / d) * t)
    sq = np.sin(2 * np.pi * (1300 + 300 * np.sin(2 * np.pi * 3 * t)) * t) * 0.12
    return (x * wob + sq) * np.sin(np.pi * t / d) ** 0.7 * 0.8


def sfx_sparkle():
    n = int(0.7 * SR)
    out = np.zeros(n)
    for i, m in enumerate([86, 89, 93, 98, 101]):
        k = int(0.45 * SR)
        y = np.sin(2 * np.pi * hz(m) * T(k)) * np.exp(-T(k) / 0.12)
        s = int(i * 0.04 * SR)
        out[s:s + k] += y[: n - s]
    return out * 0.3


def sfx_impact():
    n = int(1.0 * SR)
    t = T(n)
    f = 34 + 70 * np.exp(-t / 0.06)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.35)
    return np.tanh(1.6 * y) * 0.9 + filt(ns(1.0)[:n], "lp", 600) * np.exp(-t / 0.08) * 0.5


FNS = {"whoosh": sfx_whoosh, "pop": sfx_pop, "rustle": sfx_rustle, "tear": sfx_tear, "snip": sfx_snip,
       "stamp": sfx_stamp, "tick": sfx_tick, "type": sfx_type, "marker": sfx_marker, "sparkle": sfx_sparkle,
       "impact": sfx_impact}
GAIN = {"whoosh": 0.35, "pop": 0.35, "rustle": 0.4, "tear": 0.45, "snip": 0.5, "stamp": 0.5, "tick": 0.22,
        "type": 0.3, "marker": 0.32, "sparkle": 0.35, "impact": 0.55}


def sfx_track(cues):
    buf = np.zeros(NS)
    for k in range(N):
        for (t, name, g) in scenes.SFX[k](cues[k]):
            place(buf, FNS[name](), k * SCENE + t, GAIN[name] * g)
    for b in range(1, N):   # whip-pan whooshes at every boundary
        place(buf, sfx_whoosh(0.55), b * SCENE - 0.3, 0.5)
    return buf


# ---------------------------------------------------------------- narration
def voice_track():
    buf = np.zeros(NS)
    for k in range(N):
        x, sr = sf.read(os.path.join(OUT, "voice", f"scene{k + 1:02d}.wav"))
        if x.ndim > 1:
            x = x.mean(1)
        if sr != SR:
            x = resample_poly(x, SR, sr)
        x = filt(x, "hp", 70)
        x = x / (np.abs(x).max() + 1e-9) * 0.9
        place(buf, x, k * SCENE + VOICE_IN)   # take starts at its first phrase; cues include this lead-in
    return buf


def envelope(x, tau=0.12):
    a = np.abs(x)
    k = int(tau * SR)
    return np.convolve(a, np.ones(k) / k, mode="same")


def main():
    with open(os.path.join(OUT, "cues.json")) as fh:
        cues = [c["phrases"] for c in json.load(fh)]
    v = voice_track()
    m = score()
    s = sfx_track(cues)
    duck = 1 - 0.55 * np.clip(envelope(v, 0.25) / 0.08, 0, 1)
    mix = 0.95 * v + 0.2 * m * duck + 0.5 * s * (1 - 0.3 * (1 - duck))
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    mix *= 0.89 / (np.abs(mix).max() + 1e-9)
    sf.write(os.path.join(OUT, "mix.wav"), np.stack([mix, mix], 1).astype(np.float32), SR)
    print("mix ->", os.path.join(OUT, "mix.wav"))


if __name__ == "__main__":
    main()
