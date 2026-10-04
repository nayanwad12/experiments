"""Soundtrack: original music bed + crayon/paper SFX + narration, all synthesised in numpy.

Music is 100 BPM in C major (C-G-Am-F), plucks + glockenspiel + soft bass. The first scene (the old way)
gets only a tired, muffled loop and a ticking clock; the full band comes in on the reveal. The beat grid
starts at the reveal cut (8.1 s), so "all on the beat" (24.3 s) lands on a downbeat.
"""
import json
import os

import numpy as np
import soundfile as sf
from scipy.signal import butter, resample_poly, sosfilt

import scenes

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
DUR = scenes.DUR
N = int(DUR * SR)
BPM = 100
BEAT = 60 / BPM
GRID0 = 8.1
rng = np.random.default_rng(1)


def mtof(m):
    return 440 * 2 ** ((m - 69) / 12)


def place(buf, x, t, gain=1.0):
    i = int(t * SR)
    if i >= len(buf) or i + len(x) <= 0:
        return
    if i < 0:
        x, i = x[-i:], 0
    n = min(len(x), len(buf) - i)
    buf[i:i + n] += gain * x[:n]


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), x)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "lowpass", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "highpass", fs=SR, output="sos"), x)


# ----------------------------------------------------------------------------- instruments
def pluck(f, dur=0.9, bright=1.0):
    t = np.arange(int(dur * SR)) / SR
    y = np.zeros_like(t)
    for k in range(1, 9):
        y += (0.7 ** (k - 1)) * bright ** (k - 1) * np.sin(2 * np.pi * f * k * t + k) * np.exp(-t * (3 + 2.2 * k))
    att = np.minimum(1, t / 0.004)
    return y * att * 0.5


def glock(f, dur=1.4):
    t = np.arange(int(dur * SR)) / SR
    y = (np.sin(2 * np.pi * f * t) * np.exp(-t * 3.2) + 0.4 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 9)
         + 0.2 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 18))
    return y * np.minimum(1, t / 0.002) * 0.45


def bass(f, dur):
    t = np.arange(int(dur * SR)) / SR
    y = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    env = np.minimum(1, t / 0.01) * np.exp(-t * 1.6) * np.minimum(1, (dur - t) / 0.05)
    return y * env * 0.55


def kick():
    t = np.arange(int(0.35 * SR)) / SR
    f = 50 + 90 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 11) * 0.9


def shaker():
    n = rng.standard_normal(int(0.07 * SR))
    t = np.arange(len(n)) / SR
    return hp(n, 6000) * np.minimum(1, t / 0.01) * np.exp(-t * 60) * 0.25


def tick(high=True):
    n = rng.standard_normal(int(0.03 * SR))
    t = np.arange(len(n)) / SR
    return bp(n, 2500 if high else 1600, 6000) * np.exp(-t * 220) * 0.6


# ----------------------------------------------------------------------------- sfx
def scribble(dur, rate=7.0, lo=1800, hi=6500):
    """Crayon on paper: grainy band-passed noise, swelling with each back-and-forth stroke."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = bp(rng.standard_normal(n), lo, hi)
    grain = np.abs(lp(rng.standard_normal(n), 300))
    strokes = np.abs(np.sin(np.pi * rate * t + rng.uniform(0, 3))) ** 0.6
    env = np.minimum(1, t / 0.03) * np.minimum(1, (dur - t) / 0.05)
    return x * (0.4 + grain) * strokes * env * 0.35


def popsnd(f=700, dur=0.12):
    t = np.arange(int(dur * SR)) / SR
    ff = f * (1 + 1.2 * np.exp(-t * 40))
    return np.sin(2 * np.pi * np.cumsum(ff) / SR) * np.exp(-t * 32) * 0.5


def whoosh(dur=0.45, up=True):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n)
    out = np.zeros(n)
    # sweep a band through a few blocks
    blocks = 12
    for b in range(blocks):
        a, z = b * n // blocks, (b + 1) * n // blocks
        fc = 400 + 3100 * (b / blocks) if up else 3500 - 3100 * (b / blocks)
        out[a:z] = bp(x, max(200, fc * 0.6), fc * 1.4)[a:z]
    env = np.sin(np.pi * t / dur) ** 2
    return out * env * 0.5


def thud():
    t = np.arange(int(0.5 * SR)) / SR
    f = 45 + 60 * np.exp(-t * 18)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 8)
    clank = bp(rng.standard_normal(len(t)), 700, 2500) * np.exp(-t * 25) * 0.4
    return (body + clank) * 0.9


def boing():
    t = np.arange(int(0.6 * SR)) / SR
    f = 220 + 140 * np.sin(2 * np.pi * 9 * t) * np.exp(-t * 4) + 120 * np.exp(-t * 6)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4.5) * 0.4


def ding(f=1568):
    return glock(f, 2.0) + 0.6 * glock(f * 1.5, 2.0)


def sparkle_gliss(t0, buf, n=9, up=True, gain=0.5):
    notes = [72, 74, 76, 79, 81, 84, 86, 88, 91]
    for i in range(n):
        m = notes[i] if up else notes[-1 - i]
        place(buf, glock(mtof(m), 1.0), t0 + i * 0.045, gain * (0.6 + 0.4 * i / n))


def punch():
    t = np.arange(int(0.4 * SR)) / SR
    f = 70 + 200 * np.exp(-t * 35)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 10)
    snap = hp(rng.standard_normal(len(t)), 1500) * np.exp(-t * 45) * 0.6
    return np.tanh(2.2 * (body + snap)) * 0.6


# ----------------------------------------------------------------------------- music
CHORDS = [(48, [60, 64, 67, 72]), (43, [59, 62, 67, 71]), (45, [60, 64, 69, 72]), (41, [60, 65, 69, 72])]
MELODY = [  # (beat-in-bar, midi) per chord, glockenspiel
    [(0, 76), (1.5, 79), (2, 84), (3, 79)], [(0, 74), (1.5, 79), (2, 83), (3, 79)],
    [(0, 76), (1, 81), (2, 84), (3.5, 81)], [(0, 77), (1.5, 81), (2, 84), (3, 86)]]


def music():
    L = np.zeros(N)
    R = np.zeros(N)
    # --- intro (old way): muffled slow loop + ticking clock
    intro = np.zeros(N)
    slow = 0.75
    t = 0.2
    i = 0
    while t < GRID0 - 0.2:
        root, ch = CHORDS[(i // 4) % 4]
        place(intro, pluck(mtof(ch[i % 4] - 12), 1.2, 0.6), t, 0.5)
        if i % 4 == 0:
            place(intro, bass(mtof(root), 2.8), t, 0.5)
        t += slow
        i += 1
    intro = lp(intro, 1400)
    for k in range(int(GRID0 / 0.5)):
        tt = 0.25 + k * 0.5
        if tt < GRID0 - 0.3:
            place(intro, tick(k % 2 == 0), tt, 0.35 * (1 + 0.6 * (tt > scenes.CUE["hours"])))
    L += intro
    R += intro
    # --- full band from the reveal
    bars = int((DUR - GRID0) / (4 * BEAT)) + 1
    for b in range(bars):
        t0 = GRID0 + b * 4 * BEAT
        root, ch = CHORDS[b % 4]
        place(L, bass(mtof(root - 12 + 12), 4 * BEAT), t0, 0.55)
        place(R, bass(mtof(root - 12 + 12), 4 * BEAT), t0, 0.55)
        for e in range(8):  # eighth-note plucks, panned
            tt = t0 + e * BEAT / 2
            m = ch[[0, 2, 1, 3, 2, 1, 3, 2][e]]
            x = pluck(mtof(m), 0.8, 0.9)
            pan = 0.35 + 0.3 * (e % 2)
            place(L, x, tt, 0.32 * (1 - pan) * 2)
            place(R, x, tt, 0.32 * pan * 2)
        if b >= 2:  # melody enters on the third bar
            for beat, m in MELODY[b % 4]:
                x = glock(mtof(m))
                place(L, x, t0 + beat * BEAT, 0.22)
                place(R, x, t0 + beat * BEAT, 0.26)
        for q in range(4):
            tt = t0 + q * BEAT
            if b >= 1 and q in (0, 2):
                k = kick()
                place(L, k, tt, 0.5)
                place(R, k, tt, 0.5)
            for s in range(2):
                sh = shaker()
                place(L, sh, tt + s * BEAT / 2 + BEAT / 4, 0.6)
                place(R, sh, tt + s * BEAT / 2 + BEAT / 4, 0.5)
    # gentle fade-in of the band and the end
    t = np.arange(N) / SR
    band = np.clip((t - GRID0) / 0.3, 0, 1)
    fade = np.clip((DUR - t) / 2.5, 0, 1)
    intro_part = (t < GRID0).astype(float)
    L = (L * (band + intro_part * 1.0)) * fade
    R = (R * (band + intro_part * 1.0)) * fade
    return L, R


def sfx():
    s = np.zeros(N)
    C = scenes.CUE
    for w0, dur, *_ in scenes.WIPES:
        place(s, scribble(dur + 0.1, 9, 1500, 7000), w0, 0.9)
    for c in ("cutting", "dragging", "keyframing"):
        place(s, popsnd(900), C[c], 0.5)
        place(s, scribble(0.3, 10), C[c] + 0.2, 0.4)
    for k in range(10):  # mouse clicks while editing
        place(s, tick(True), 1.0 + k * 0.62 + 0.1 * np.sin(k), 0.3)
    place(s, boing(), C["square"], 0.8)
    place(s, scribble(0.6, 6), C["newway"], 0.5)
    place(s, ding(), C["newway"] + 0.8, 0.45)
    for i in range(12):
        place(s, popsnd(500 + 40 * i), C["vibe_title"] + i * 0.055, 0.22)
    sparkle_gliss(C["vibe_title"] + 0.5, s, gain=0.35)
    place(s, scribble(0.5, 12), C["fighting"], 0.6)
    place(s, scribble(0.25, 8), C["timeline"], 0.6)
    place(s, scribble(0.25, 8), C["timeline"] + 0.15, 0.6)
    place(s, whoosh(0.5), 13.4, 0.6)
    place(s, popsnd(650), 13.8, 0.5)
    place(s, scribble(0.7, 5), 13.95, 0.45)
    place(s, scribble(1.9, 11, 2500, 8000), C["make"], 0.25)  # handwriting
    place(s, ding(1319), C["warm"], 0.3)
    place(s, punch(), C["punchy"], 0.9)
    sparkle_gliss(C["dreamy"], s, n=7, up=False, gain=0.35)
    place(s, popsnd(500), 19.6, 0.5)
    place(s, whoosh(0.5), 20.25, 0.5)
    place(s, thud(), 21.95, 0.8)
    for c in ("cuts", "colors", "captions", "music"):
        place(s, popsnd(800), C[c], 0.5)
    place(s, popsnd(550), 25.65, 0.5)
    place(s, scribble(0.6, 9), C["weekend"] - 0.3, 0.55)
    place(s, scribble(0.4, 4), C["coffee"] - 0.3, 0.4)
    place(s, popsnd(700), C["coffee"], 0.5)
    place(s, whoosh(0.5), 28.5, 0.6)
    place(s, popsnd(600), 28.75, 0.5)
    place(s, popsnd(750), 30.1, 0.5)
    for i in range(12):
        place(s, popsnd(520 + 40 * i), C["outro_title"] + i * 0.05, 0.2)
    for i in range(8):
        place(s, scribble(0.35, 9), C["outro_title"] + 0.4 + i * 0.12, 0.25)
    sparkle_gliss(C["life"], s, gain=0.4)
    place(s, ding(1047), 37.0, 0.3)
    return s


def narration():
    vo = json.load(open(os.path.join(HERE, "work", "vo.json")))
    out = np.zeros(N)
    for lid, t0 in scenes.VO.items():
        x, sr = sf.read(vo[lid]["wav"])
        x = resample_poly(x, SR, sr)
        x = hp(x, 70)
        x = x / (np.max(np.abs(x)) + 1e-9) * 0.8
        place(out, x, t0)
    return out


def compress(x, thr=0.35, ratio=3.0):
    env = lp(np.abs(x), 30, 1) * 1.6
    g = np.where(env > thr, (thr + (env - thr) / ratio) / np.maximum(env, 1e-9), 1.0)
    return x * g


def main():
    L, R = music()
    s = sfx()
    v = narration()
    v = compress(v)
    # duck the music under the voice
    env = lp(np.abs(v), 6, 1)
    duck = 1 - 0.6 * np.clip(env / 0.06, 0, 1)
    L = L * duck * 0.42
    R = R * duck * 0.42
    mixL = L + s * 0.8 + v
    mixR = R + s * 0.8 + v
    mix = np.stack([mixL, mixR], 1)
    peak = np.max(np.abs(mix))
    mix = np.tanh(mix / peak * 1.2) / np.tanh(1.2) * 0.84
    sf.write(os.path.join(HERE, "work", "mix.wav"), mix.astype(np.float32), SR)
    print("mix written", mix.shape, "peak", peak)


if __name__ == "__main__":
    main()
