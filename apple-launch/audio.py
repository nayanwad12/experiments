"""Original fast-paced 150 BPM soundtrack + UI SFX for the launch film, synthesised in numpy (no samples).

    python3 audio.py  ->  out/audio.wav   (48 kHz stereo, 40 s = 100 beats = 25 bars)

Cue times are real seconds and mirror launch.js (its scenes are authored on a 120 BPM grid and
played at 1.25x, so virtual time v maps to real time 0.8 * v before the montage).
"""

import os

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
BPM = 150
B = 60 / BPM          # 0.4 s
BAR = 4 * B           # 1.6 s
DUR = 40.0
N = int(SR * DUR)
TAU = 2 * np.pi
HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(7)

# ---- cues, real seconds (keep in sync with launch.js)
SLOT = [1.2, 1.8, 2.4, 3.0]
STRIKE = 3.4
PILL_IN = 4.0
TYPE1 = (4.44, 31.25, len('Make it punchy. Fast cuts, bold captions, neon accents.'))
SEND1 = 6.4
REVEAL = 8.0
SUB = 9.2
LAPTOP = 11.2
TYPE2 = (12.68, 30.0, len('high-contrast mono grade, cut to the beat'))
DROP = 14.4
CAPS = 15.52
CARDS = [19.2 + 0.2 * k for k in range(6)]
LESS, MORE = 25.6, 26.4
MON0, MON1 = 28.8, 35.2
VIBE = MON0 + 12 * B   # "vibe." slam
LOGO = 35.2
SWEEP = 35.75
CTA = 36.7

# E minor: Em9 | Cmaj7 | G6 | D(add9)   (one chord per bar)
CHORDS = [[52, 55, 59, 62, 66], [48, 52, 55, 59, 64], [50, 55, 59, 62, 64], [50, 54, 57, 62, 64]]
ROOTS = [40, 36, 43, 38]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def T(n):
    return np.arange(n) / SR


def filt(x, kind, f, order=2):
    return sosfilt(butter(order, f, kind, fs=SR, output='sos'), x)


def add(bus, x, t, gain=1.0, pan=0.0):
    i = int(round(t * SR))
    if i >= N:
        return
    if i < 0:
        x = x[..., -i:]
        i = 0
    x = x[..., : N - i]
    if x.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        bus[0, i:i + len(x)] += x * gain * l * 1.414
        bus[1, i:i + len(x)] += x * gain * r * 1.414
    else:
        bus[:, i:i + x.shape[1]] += x * gain


def chord_at(t):
    return int(t // BAR) % 4


bus = {k: np.zeros((2, N)) for k in ('pad', 'keys', 'stab', 'bass', 'drums', 'fx', 'ui')}


# ------------------------------------------------------------------ instruments
def saw(f, t, ph=0.0):
    return 2 * ((f * t + ph) % 1) - 1


def pad_voice(f, d, bright=1.0):
    n = int(d * SR)
    t = T(n)
    out = np.zeros((2, n))
    for k, det in enumerate((-0.12, -0.05, 0.04, 0.1, 0.15)):
        s = saw(f * (1 + det / 100 * 6), t, rng.uniform(0, 1))
        out[k % 2] += s
        out[(k + 1) % 2] += s * 0.5
    for c in range(2):
        out[c] = filt(out[c], 'low', 700 + 2200 * bright)
    a = np.clip(t / 0.5, 0, 1) * np.clip((d - t) / 0.8, 0, 1)
    return out * a * 0.04


def pluck(f, d=0.6, hard=1.0):
    n = int(d * SR)
    t = T(n)
    x = np.sin(TAU * f * t) * np.exp(-t / 0.28)
    x += 0.35 * np.sin(TAU * f * 4.0 * t) * np.exp(-t / 0.06) * hard
    x += 0.15 * np.sin(TAU * f * 9.9 * t) * np.exp(-t / 0.02) * hard
    x += 0.2 * saw(f, t) * np.exp(-t / 0.08)
    return x * np.clip(t / 0.002, 0, 1) * 0.26


def stab(ch, d=0.32, g=1.0):
    n = int(d * SR)
    t = T(n)
    out = np.zeros((2, n))
    for k, m in enumerate(ch):
        for j, det in enumerate((-0.15, 0.15)):
            out[(k + j) % 2] += saw(hz(m + 12) * (1 + det / 100 * 5), t, rng.uniform(0, 1))
    env = np.exp(-t / 0.11)
    cut = 900 + 5200 * np.exp(-t / 0.07)
    for c in range(2):
        y = np.zeros(n)
        blk = 256
        for i in range(0, n, blk):   # time-varying low-pass, block-wise
            y[i:i + blk] = sosfilt(butter(2, min(cut[i], 18000), 'low', fs=SR, output='sos'), out[c, i:i + blk])
        out[c] = y
    return out * env * 0.06 * g


def kick(g=1.0):
    n = int(0.36 * SR)
    t = T(n)
    f = 48 + 140 * np.exp(-t / 0.028)
    x = np.sin(TAU * np.cumsum(f) / SR) * np.exp(-t / 0.17)
    x += 0.3 * filt(rng.standard_normal(n), 'high', 3000) * np.exp(-t / 0.003)
    return np.tanh(x * 2.0) * 0.72 * g


def clap(g=1.0):
    n = int(0.3 * SR)
    t = T(n)
    nz = filt(rng.standard_normal(n), 'band', [1000, 5000])
    e = np.zeros(n)
    for o in (0, 0.009, 0.018):
        e += (t >= o) * np.exp(-np.maximum(t - o, 0) / (0.01 if o < 0.015 else 0.09))
    body = np.sin(TAU * 200 * t) * np.exp(-t / 0.03) * 0.3
    return (nz * e + body) * 0.33 * g


def snare(g=1.0):
    n = int(0.18 * SR)
    t = T(n)
    return (filt(rng.standard_normal(n), 'band', [1500, 8000]) * np.exp(-t / 0.05) + np.sin(TAU * 190 * t) * np.exp(-t / 0.04) * 0.5) * 0.28 * g


def hat(op=False, g=1.0):
    n = int((0.22 if op else 0.045) * SR)
    t = T(n)
    return filt(rng.standard_normal(n), 'high', 8500) * np.exp(-t / (0.07 if op else 0.01)) * 0.15 * g


def bass16(f, d):
    n = int(d * SR)
    t = T(n)
    x = np.sin(TAU * f * t) + 0.5 * saw(f, t)
    x = filt(x, 'low', 900)
    return np.tanh(1.8 * x) * np.exp(-t / 0.09) * np.clip(t / 0.003, 0, 1) * 0.36


def sub_note(f, d):
    n = int(d * SR)
    t = T(n)
    x = np.sin(TAU * f * t) + 0.25 * np.sin(TAU * 2 * f * t)
    return np.tanh(1.3 * x) * np.clip(t / 0.01, 0, 1) * np.clip((d - t) / 0.05, 0, 1) * 0.3


def whoosh(d=0.6, up=True, g=1.0):
    n = int(d * SR)
    t = T(n)
    nz = rng.standard_normal(n)
    fc = np.geomspace(300, 7000, n) if up else np.geomspace(7000, 300, n)
    out = np.zeros(n)
    for i in range(0, n, 512):
        c = fc[i]
        out[i:i + 512] = sosfilt(butter(2, [c * 0.6, min(c * 1.6, 20000)], 'band', fs=SR, output='sos'), nz[i:i + 512])
    return out * np.sin(np.pi * t / d) ** 2 * 0.28 * g


def riser(d, g=1.0):
    n = int(d * SR)
    t = T(n)
    nz = filt(rng.standard_normal(n), 'high', 1500)
    tone = sum(np.sin(TAU * hz(64 + k * 12) * (1 + 0.6 * (t / d) ** 2) * t) for k in range(2)) * 0.12
    return (nz * 0.22 + tone) * (t / d) ** 2.2 * g


def impact(g=1.0):
    n = int(2.4 * SR)
    t = T(n)
    f = 34 + 80 * np.exp(-t / 0.07)
    boom = np.sin(TAU * np.cumsum(f) / SR) * np.exp(-t / 0.7)
    air = filt(rng.standard_normal(n), 'band', [2000, 9000]) * np.exp(-t / 0.35) * 0.18
    return np.tanh(boom * 1.3 + air) * 0.6 * g


def shimmer(d=2.0, base=76, g=1.0):
    n = int(d * SR)
    t = T(n)
    x = np.zeros(n)
    for k, m in enumerate([base, base + 7, base + 12, base + 15, base + 19, base + 24]):
        x += np.sin(TAU * hz(m) * t + k) * np.exp(-t / (0.5 + 0.2 * k)) * np.clip((t - k * 0.05) / 0.01, 0, 1)
    return x * 0.055 * g


def key_click():
    n = int(0.04 * SR)
    t = T(n)
    x = filt(rng.standard_normal(n), 'band', [1800, 7000]) * np.exp(-t / 0.005)
    x += 0.4 * np.sin(TAU * 2400 * t) * np.exp(-t / 0.004)
    return x * rng.uniform(0.6, 1.0) * 0.11


def pop(f=900):
    n = int(0.1 * SR)
    t = T(n)
    fr = f * (1 + 0.8 * np.exp(-t / 0.01))
    return np.sin(TAU * np.cumsum(fr) / SR) * np.exp(-t / 0.03) * 0.22


def tick():
    n = int(0.06 * SR)
    t = T(n)
    return (np.sin(TAU * 3200 * t) * np.exp(-t / 0.007) + 0.5 * filt(rng.standard_normal(n), 'high', 4000) * np.exp(-t / 0.004)) * 0.08


def beats(t0, t1, step=B, off=0.0):
    k = 0
    while True:
        t = t0 + off + k * step
        if t >= t1 - 1e-6:
            return
        yield k, t
        k += 1


# ------------------------------------------------------------------ arrangement
FULL = [(DROP, LESS), (MON0, MON1)]                 # full-energy sections
MID = [(1.6, SEND1), (REVEAL, DROP), (LOGO, 38.4)]   # driving but lighter


def in_any(t, spans):
    return any(a <= t < b for a, b in spans)


# PAD: every bar, darker in the breaks
for bar in range(25):
    t0 = bar * BAR
    bright = 0.35 if t0 < REVEAL else 0.7
    for m in CHORDS[bar % 4]:
        add(bus['pad'], pad_voice(hz(m), BAR + 0.9, bright), t0 - 0.15, 1.0)
for m in [52, 55, 59, 62, 66, 71]:
    add(bus['pad'], pad_voice(hz(m), 4.8, 0.8), 38.4 - 0.1, 1.3)

# KICK: four on the floor through the driving sections, single hits in the breaks
kicks = []
for a, b in MID + FULL:
    kicks += [t for _, t in beats(a, b)]
kicks += [SLOT[0], SLOT[2], REVEAL - 0.0, LESS, MORE, VIBE]
kicks = sorted(set(round(k, 4) for k in kicks))
for t in kicks:
    add(bus['drums'], kick(), t, 1.0)

# CLAP on 2 & 4, HATS
for a, b in MID + FULL:
    for k, t in beats(a, b):
        if k % 2 == 1:
            add(bus['drums'], clap(), t, 1.0, pan=0.05)
        add(bus['drums'], hat(op=True), t + B / 2, 0.75, pan=0.25)
        if in_any(t, FULL) or a >= LOGO:
            for s in (1, 3):
                add(bus['drums'], hat(g=0.8 if s == 1 else 0.6), t + s * B / 4, 1.0, pan=-0.3)
# intro: just ticking 8th hats under the first words
for k, t in beats(0, 1.6, B / 2):
    add(bus['drums'], hat(g=0.6 + 0.4 * (k % 2)), t, 1.0, pan=-0.2)


def roll(t0, t1, g0=0.15, g1=0.7):
    # accelerating snare roll: 8ths -> 16ths -> 32nds
    d = t1 - t0
    t = t0
    while t < t1 - 1e-6:
        u = (t - t0) / d
        step = B / 2 if u < 0.5 else (B / 4 if u < 0.8 else B / 8)
        add(bus['drums'], snare(), t, g0 + (g1 - g0) * u)
        t += step


roll(SEND1 + 0.8, REVEAL)
roll(DROP - BAR, DROP)
roll(MORE + 0.8, MON0, 0.1, 0.8)
roll(MON1 - 2 * B, MON1, 0.2, 0.8)

# BASS: rolling 16ths in the full sections, offbeat 8ths in the driving ones, sub in breaks
for bar in range(25):
    t0 = bar * BAR
    r = ROOTS[bar % 4]
    if in_any(t0, FULL):
        for k in range(16):
            m = r + (12 if k % 4 == 2 else 0)
            add(bus['bass'], bass16(hz(m), B / 4), t0 + k * B / 4, 1.0 if k % 4 else 0.8)
    elif in_any(t0, MID):
        for k in range(4):
            add(bus['bass'], bass16(hz(r), B / 2), t0 + k * B + B / 2, 1.0)
            add(bus['bass'], bass16(hz(r + 12), B / 4), t0 + k * B + 3 * B / 4, 0.6)
    elif t0 >= 38.4:
        add(bus['bass'], sub_note(hz(40), 1.6), t0, 0.9)
add(bus['bass'], sub_note(hz(40), 1.2), LESS, 0.8)
add(bus['bass'], sub_note(hz(36), 1.2), MORE, 0.8)

# ARP: 16th plucks most of the film
arp_pat = [0, 2, 4, 2, 1, 3, 4, 3]


def arp(t0, t1, step=B / 4, g=0.55, oct=12):
    for k, t in beats(t0, t1, step):
        ch = CHORDS[chord_at(t)]
        add(bus['keys'], pluck(hz(ch[arp_pat[k % 8]] + oct), 0.5), t, g * (1.0 if k % 2 == 0 else 0.7), pan=0.4 * np.sin(k * 1.3))


arp(0, SEND1, B / 4, 0.45)
arp(REVEAL, DROP, B / 4, 0.5)
arp(DROP, LESS, B / 4, 0.55)
arp(LOGO, 38.4, B / 4, 0.4)
for i, t in enumerate(SLOT):
    add(bus['keys'], pluck(hz([76, 78, 79, 83][i]), 1.0), t, 1.1, pan=[-0.3, 0.3, -0.2, 0.2][i])

# STABS: syncopated in the drop, on every montage word
for bar in range(25):
    t0 = bar * BAR
    ch = CHORDS[bar % 4]
    if DROP <= t0 < LESS:
        for o in (0, 1.5 * B, 3 * B):
            add(bus['stab'], stab(ch), t0 + o, 0.9)
for k, t in beats(MON0, MON1):
    add(bus['stab'], stab(CHORDS[chord_at(t)], 0.3, 1.2 if k < 8 else 0.9), t, 1.0)
for t in (REVEAL, LESS, MORE, VIBE, LOGO):
    add(bus['stab'], stab(CHORDS[chord_at(t)], 0.6, 1.3), t, 1.0)

# FX
add(bus['fx'], whoosh(0.4, False, 0.6), STRIKE - 0.05, 1.0)
add(bus['fx'], whoosh(0.5, True, 0.5), PILL_IN - 0.25, 1.0)
add(bus['fx'], riser(SEND1 - 4.8), 4.8, 0.35)
add(bus['fx'], shimmer(2.0, 76, 1.2), SEND1, 1.0)
add(bus['fx'], whoosh(0.9, True, 0.8), SEND1 + 0.5, 1.0)
add(bus['fx'], riser(1.6, 0.9), REVEAL - 1.6, 0.8)
add(bus['fx'], impact(1.0), REVEAL, 1.0)
add(bus['fx'], shimmer(2.4, 80, 1.3), REVEAL, 1.0)
add(bus['fx'], whoosh(0.7, False, 0.6), 10.85, 1.0)
add(bus['fx'], whoosh(0.9, True, 0.7), LAPTOP - 0.15, 1.0)
add(bus['fx'], riser(BAR, 1.0), DROP - BAR, 0.7)
add(bus['fx'], impact(0.9), DROP, 1.0)
add(bus['fx'], shimmer(1.8, 76, 1.2), DROP + 0.05, 1.0)
add(bus['fx'], whoosh(0.7, False, 0.7), 18.3, 1.0)
add(bus['fx'], whoosh(0.7, True, 0.5), 18.65, 1.0)
add(bus['fx'], whoosh(0.6, False, 0.6), 25.1, 1.0)
add(bus['fx'], impact(0.6), LESS, 1.0)
add(bus['fx'], whoosh(0.45, True, 0.9), MORE - 0.2, 1.0)
add(bus['fx'], impact(0.8), MORE, 1.0)
add(bus['fx'], riser(2.4, 1.0), MON0 - 2.4, 0.75)
add(bus['fx'], impact(1.0), MON0, 1.0)
for k, t in beats(MON0, MON0 + 8 * B):
    add(bus['fx'], whoosh(0.22, k % 2 == 0, 0.9), t - 0.08, 0.8, pan=-0.4 if k % 2 else 0.4)
add(bus['fx'], impact(1.0), VIBE, 1.0)
add(bus['fx'], shimmer(1.6, 76, 1.2), VIBE, 1.0)
add(bus['fx'], riser(2 * B, 1.0), MON1 - 2 * B, 0.7)
add(bus['fx'], impact(1.0), LOGO, 1.0)
add(bus['fx'], shimmer(3.5, 76, 1.5), SWEEP, 1.0)

# UI
for t in SLOT:
    add(bus['ui'], tick(), t + 0.08, 1.0)
for start, cps, n in (TYPE1, TYPE2):
    for k in range(n):
        add(bus['ui'], key_click(), start + k / cps + rng.uniform(-0.004, 0.004), 1.0 if start < 10 else 0.6, pan=rng.uniform(-0.2, 0.2))
add(bus['ui'], pop(700), SEND1, 1.0)
add(bus['ui'], pop(600), DROP - 0.02, 0.7)
for i, t in enumerate(CARDS):
    add(bus['ui'], pop(650 + 70 * i), t, 0.6, pan=-0.5 + i * 0.2)
for k in range(4):
    add(bus['ui'], tick(), CAPS + k * 0.104, 0.7)
add(bus['ui'], pop(880), CTA, 0.8)

# ------------------------------------------------------------------ mix
kick_env = np.zeros(N)
for t in kicks:
    i = int(t * SR)
    n = min(int(0.25 * SR), N - i)
    kick_env[i:i + n] = np.maximum(kick_env[i:i + n], np.exp(-T(n) / 0.08))
duck = 1 - 0.65 * kick_env


def reverb(x, d=2.0, mix=0.25):
    n = int(d * SR)
    t = T(n)
    out = np.zeros_like(x)
    for c in range(2):
        ir = filt(rng.standard_normal(n) * np.exp(-t / (d / 6.5)), 'low', 6000)
        ir[:int(0.012 * SR)] = 0
        out[c] = fftconvolve(x[c], ir)[:x.shape[1]] / (np.sqrt(np.sum(ir ** 2)) + 1e-9)
    return x * (1 - mix) + out * mix


mixbus = (
    reverb(bus['pad'], 2.6, 0.35) * 0.8 * (1 - 0.5 * kick_env)
    + reverb(bus['keys'], 1.6, 0.25) * 0.7 * (1 - 0.3 * kick_env)
    + reverb(bus['stab'], 1.4, 0.22) * 0.9 * (1 - 0.3 * kick_env)
    + bus['bass'] * duck * 0.95
    + reverb(bus['drums'], 0.7, 0.06) * 0.8
    + reverb(bus['fx'], 2.2, 0.28) * 0.75
    + reverb(bus['ui'], 0.6, 0.12) * 0.55
)
mixbus = filt(mixbus, 'high', 30)
t = T(N)
mixbus *= np.clip(t / 0.02, 0, 1) * np.clip((DUR - t) / 1.0, 0, 1) ** 1.5
peak = np.max(np.abs(mixbus))
mixbus = np.tanh(mixbus / peak * 1.6) / np.tanh(1.6) * 0.9
os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
wavfile.write(os.path.join(HERE, 'out', 'audio.wav'), SR, (mixbus.T * 32767).astype(np.int16))
print('-> out/audio.wav', f'{DUR:.1f}s @ {BPM} BPM')
