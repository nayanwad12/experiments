"""Energetic score + SFX + narration mix, all synthesised in numpy (no samples, no licensing).

    python3 audio.py   ->  out/mix.wav

Score: 128 BPM, D minor (Dm - Bb - F - C), arranged on the energy map in timeline.py: a filtered build
that drops on "The cut.", a rolling groove, a snare-roll build that drops on "It happens.", a breakdown
on "But here's the catch.", and a last drop with a lead line that peaks on "YOU". Kick sidechain pumps
the music, the music ducks under the narration, and every scene change gets a riser, reverse cymbal
and impact.
"""

import math
import os

import numpy as np
import soundfile as sf
from scipy.signal import butter, resample_poly, sosfilt

import scenes
import timeline as TL
from script import BEAT, N, VOICE_IN

SR = 48000
DUR = TL.DUR
NS = int(SR * DUR) + 1
BAR = BEAT * 4
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


def saw(f, n, ph=0.0):
    return 2 * ((f * T(n) + ph) % 1.0) - 1


# ---------------------------------------------------------------- drums
def kick():
    n = int(0.42 * SR)
    t = T(n)
    f = 46 + 140 * np.exp(-t / 0.026)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / 0.22) + 0.6 * np.sin(ph) * np.exp(-t / 0.018)
    click = filt(ns(0.42)[:n], "hp", 2500) * np.exp(-t / 0.003) * 0.5
    return np.tanh(2.2 * y) * 0.9 + click


def clap():
    n = int(0.35 * SR)
    t = T(n)
    x = filt(ns(0.35)[:n], "bandpass", [900, 5500])
    env = 0.8 * np.exp(-t / 0.1)
    for d in (0.0, 0.011, 0.022):
        env += (t >= d) * np.exp(-np.clip(t - d, 0, None) / 0.007)
    return x * env * 0.8 + np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05) * 0.5


def snare():
    n = int(0.25 * SR)
    t = T(n)
    return (filt(ns(0.25)[:n], "bandpass", [1500, 8000]) * np.exp(-t / 0.06)
            + np.sin(2 * np.pi * 210 * t) * np.exp(-t / 0.04) * 0.7)


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
    f = 30 + 55 * np.exp(-t / 0.15)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(1.6 * np.sin(ph) * np.exp(-t / 0.5)) + filt(ns(1.4)[:n], "lp", 300) * np.exp(-t / 0.2) * 0.8


def riser(d, f0=180, f1=2400):
    n = int(d * SR)
    t = T(n)
    k = t / d
    f = f0 * (f1 / f0) ** (k ** 1.5)
    tone = ((np.cumsum(f) / SR) % 1.0) * 2 - 1
    nz = ns(d)[:n]
    out = np.zeros(n)
    seg = 40
    for s in range(seg):
        a, b = s * n // seg, (s + 1) * n // seg
        c = 400 * (9000 / 400) ** (s / seg)
        out[a:b] = filt(nz, "bandpass", [c * 0.7, min(c * 1.4, 20000)])[a:b]
    return (0.2 * tone + out) * k ** 2


# ---------------------------------------------------------------- tonal
CHORDS = [[62, 65, 69], [58, 62, 65], [57, 60, 65], [55, 60, 64]]   # Dm  Bb  F/A  C/G
ROOTS = [38, 34, 41, 36]


def chord_at(t):
    i = int(t / BAR) % 4
    return CHORDS[i], ROOTS[i]


def supersaw(m, d, voices=3, spread=0.14):
    n = int(d * SR)
    out = np.zeros(n)
    for v in range(voices):
        out += saw(hz(m + (v - (voices - 1) / 2) * spread), n, rng.uniform(0, 1))
    return out / voices


def stab(chord, d=0.2, tau=0.09, oct_=12):
    n = int(d * SR)
    t = T(n)
    y = sum(supersaw(m + oct_ - 12, d) for m in chord)
    return filt(y * np.minimum(t / 0.004, 1) * np.exp(-t / tau), "lp", 5200)


def bass_note(root, d=0.11, tau=0.09):
    n = int(d * SR)
    t = T(n)
    f = hz(root)
    y = 0.7 * saw(f, n) + 0.3 * saw(f * 1.005, n) + 0.8 * np.sin(np.pi * f * t)
    env = np.minimum(t / 0.003, 1) * np.exp(-t / tau) * np.minimum((d - t) / 0.01, 1)
    return filt(y * env, "lp", 1400)


def pluck(m, d=0.14):
    n = int(d * SR)
    t = T(n)
    f = hz(m)
    y = saw(f, n) * 0.6 + np.sign(np.sin(2 * np.pi * f * 1.002 * t)) * 0.4
    return filt(y * np.minimum(t / 0.002, 1) * np.exp(-t / 0.055), "lp", 4500)


def pad(chord, d):
    n = int(d * SR)
    t = T(n)
    y = sum(supersaw(m, d, 5, 0.18) + 0.5 * supersaw(m + 12, d, 3, 0.1) for m in chord)
    return filt(y, "lp", 2200) * np.minimum(t / 0.3, 1) * np.minimum((d - t) / 0.1, 1)


def score():
    """Returns (music, kick-only) so the kick can drive the sidechain."""
    music = np.zeros(NS)
    kicks = np.zeros(NS)
    K, C, S, HC, HO = kick(), clap(), snare(), hat(), hat(True)
    kick_times = []
    nb = int(DUR / BEAT) + 1
    end_hit = TL.STARTS[-1] + TL.LENS[-1] - 1.3
    for b in range(nb):
        t = b * BEAT
        if t > end_hit + 0.01:
            break
        sec = TL.section(t)
        chord, root = chord_at(t)
        full = sec in ("drop", "drop2", "drop3")
        gap = (sec == "build" and t > TL.DROP2 - 0.3) or (sec == "intro" and t > TL.DROP1 - 0.3)
        if (full or sec == "intro" or (sec == "build" and t < TL.DROP2 - BAR)) and not gap:
            place(kicks, K, t)
            kick_times.append(t)
        if full and b % 2 == 1:
            place(music, C, t, 0.75)
        if full or sec in ("intro", "build"):
            for s in range(4):
                g = (0.32 if s % 2 else 0.18) * (0.6 if sec == "intro" else 1.0)
                place(music, HO if (s == 2 and full) else HC, t + s * BEAT / 4, g)
        if sec == "break":
            for s in range(2):
                place(music, HC, t + s * BEAT / 2, 0.14)
        if full or sec == "build":
            for o in (0.25, 0.5, 0.75):
                place(music, bass_note(root), t + o * BEAT, 0.9)
            place(music, stab(chord), t + BEAT / 2, 0.55)
        if sec == "intro":
            place(music, bass_note(root, 0.2, 0.12), t + 0.5 * BEAT, 0.6)
        if sec in ("drop2", "drop3"):
            seq = [chord[0] + 12, chord[1] + 12, chord[2] + 12, chord[1] + 24]
            for s in range(4):
                place(music, pluck(seq[(b * 4 + s) % 4]), t + s * BEAT / 4, 0.32)
        if sec in ("intro", "drop"):
            seq = [chord[0] + 12, chord[2] + 12, chord[1] + 24, chord[2] + 12]
            for s in range(2):
                place(music, pluck(seq[(b * 2 + s) % 4], 0.2), t + s * BEAT / 2, 0.2)
    # breakdown pads
    t = TL.BREAK
    while t < TL.DROP3 - 0.01:
        chord, _ = chord_at(t)
        d = min(BAR, TL.DROP3 - t)
        place(music, pad(chord, d), t, 0.16)
        t += BAR

    def roll(t0, t1, g=1.0):
        t = t0
        while t < t1 - 0.01:
            k = (t - t0) / (t1 - t0)
            step = BEAT / 2 if k < 0.4 else BEAT / 4 if k < 0.75 else BEAT / 8
            place(music, S, t, (0.2 + 0.6 * k) * g)
            t += step

    roll(max(0.0, TL.DROP1 - 2 * BEAT * 2), TL.DROP1 - 0.3, 0.8)
    roll(TL.BUILD, TL.DROP2 - 0.3)
    roll(TL.DROP3 - BAR, TL.DROP3 - 0.05, 0.9)
    place(music, riser(TL.DROP1 - 0.1), 0.0, 0.5)
    place(music, riser(TL.DROP2 - TL.BUILD, 250, 3200), TL.BUILD, 0.55)
    place(music, riser(BAR * 1.5, 200, 3000), TL.DROP3 - BAR * 1.5, 0.5)
    for t in TL.DROPS:
        place(music, crash(), t, 0.5)
        place(kicks, boom(), t, 0.55)
    t = TL.DROP1 + BAR * 4
    while t < end_hit:   # crash every 4 bars inside the drops
        if TL.section(t) in ("drop", "drop2", "drop3"):
            place(music, crash(1.4), t, 0.3)
        t += BAR * 4
    # final hit
    place(kicks, K, end_hit, 1.1)
    place(kicks, boom(), end_hit, 0.7)
    place(music, stab(CHORDS[0], 0.9, 0.35), end_hit, 1.1)
    place(music, bass_note(38, 0.9, 0.4), end_hit, 1.0)
    place(music, crash(2.5), end_hit, 0.55)
    # sidechain pump from kicks
    sc = np.ones(NS)
    for kt in kick_times:
        i = int(kt * SR)
        n = int(BEAT * SR)
        env = 1 - 0.55 * np.exp(-T(n) / 0.09)
        sc[i:i + n] = np.minimum(sc[i:i + n], env[: len(sc[i:i + n])])
    return music * sc, kicks


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


def sfx_track():
    buf = np.zeros(NS)
    for k in range(N):
        for (t, name, g) in scenes.SFX[k](TL.PHRASES[k]):
            tt = TL.STARTS[k] + t
            place(buf, FNS[name](), tt, GAIN[name] * g)
            if name == "pop":   # every pop-in gets a little swish ahead of it
                place(buf, sfx_whoosh(0.22), tt - 0.16, 0.18 * g)
    for b in range(1, N):   # scene changes: riser + reverse cymbal into a whoosh and impact
        B = TL.STARTS[b]
        place(buf, riser(0.9, 300, 4000), B - 0.9, 0.22)
        rc = crash(1.0)[::-1]
        place(buf, rc, B - 1.0, 0.35)
        place(buf, sfx_whoosh(0.4), B - 0.22, 0.55)
        place(buf, sfx_impact(), B, 0.3)
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
        x = filt(x, "hp", 80)
        x = x / (np.abs(x).max() + 1e-9) * 0.9
        place(buf, x, TL.STARTS[k] + VOICE_IN)   # take starts at its first phrase
    return buf


def envelope(x, tau=0.12):
    k = int(tau * SR)
    return np.convolve(np.abs(x), np.ones(k) / k, mode="same")


def main():
    v = voice_track()
    m, kk = score()
    s = sfx_track()
    duck = 1 - 0.74 * np.clip(envelope(v, 0.25) / 0.035, 0, 1)   # music dips ~12 dB under the voice
    music = (m + kk * 0.9)
    mix = 1.0 * v + 0.25 * music * duck + 0.5 * s * (1 - 0.3 * (1 - duck))
    mix = np.tanh(mix * 1.2) / np.tanh(1.2)
    mix *= 0.89 / (np.abs(mix).max() + 1e-9)
    sf.write(os.path.join(OUT, "mix.wav"), np.stack([mix, mix], 1).astype(np.float32), SR)
    print("mix ->", os.path.join(OUT, "mix.wav"))


if __name__ == "__main__":
    main()
