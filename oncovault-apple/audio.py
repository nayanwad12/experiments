"""Original 120 BPM soundtrack + SFX for the OncoVault promo, synthesised in numpy (no samples).

    python3 audio.py  ->  out/audio.wav   (48 kHz stereo, 40 s = 80 beats = 20 bars)

Cue times mirror film.js.
"""

import os

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
BPM = 120
B = 60 / BPM
DUR = 40.0
N = int(SR * DUR)
HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(7)


# ---- cues (keep in sync with film.js)
OPEN = [0.5, 2.0, 4.0]
JOURNEY = 6.5
TRACK = 9.7
PAIRS = [10.0, 12.0, 14.0]
TILES = [10.3, 10.8, 12.3, 12.8, 14.3, 14.8]
TOGETHER = 16.0
GLOW = 16.8
PHONE = 20.0
TREAT = 22.0
AIPASS = 24.0
LOGO = 28.0
WORD = 28.25
SOON = 34.0
STORY = 35.6

# D major: Dmaj9 | Bm9 | Gmaj9 | A6/9   (one chord per bar)
CHORDS = [[50, 54, 57, 61, 64], [47, 50, 54, 57, 61], [43, 47, 50, 54, 57], [45, 49, 52, 54, 59]]
ROOTS = [38, 35, 31, 33]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def T(n):
    return np.arange(n) / SR


def filt(x, kind, f, order=2):
    return sosfilt(butter(order, f, kind, fs=SR, output='sos'), x)


def add(bus, x, t, gain=1.0, pan=0.0):
    i = int(t * SR)
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
    return int(t // (4 * B)) % 4


bus = {k: np.zeros((2, N)) for k in ('pad', 'keys', 'bass', 'drums', 'fx', 'ui')}


# ------------------------------------------------------------------ instruments
def pad_voice(f, d, bright=1.0):
    n = int(d * SR)
    t = T(n)
    out = np.zeros((2, n))
    for k, det in enumerate((-0.11, -0.04, 0.03, 0.09, 0.13)):
        ph = rng.uniform(0, 1)
        saw = 2 * ((f * (1 + det / 100 * 6) * t + ph) % 1) - 1
        out[k % 2] += saw
        out[(k + 1) % 2] += saw * 0.5
    out[0] = filt(out[0], 'low', 900 + 1800 * bright)
    out[1] = filt(out[1], 'low', 900 + 1800 * bright)
    a = np.clip(t / 0.9, 0, 1) * np.clip((d - t) / 1.2, 0, 1)
    return out * a * 0.05


def pluck(f, d=1.2, hard=1.0):
    # marimba / soft bell: sine partials with fast decay + mallet click
    n = int(d * SR)
    t = T(n)
    x = np.sin(TAU * f * t) * np.exp(-t / 0.55)
    x += 0.35 * np.sin(TAU * f * 4.0 * t) * np.exp(-t / 0.09) * hard
    x += 0.18 * np.sin(TAU * f * 9.9 * t) * np.exp(-t / 0.03) * hard
    x += 0.10 * np.sin(TAU * f * 2 * t) * np.exp(-t / 0.3)
    return x * np.clip(t / 0.002, 0, 1) * 0.3


def kick(g=1.0):
    n = int(0.45 * SR)
    t = T(n)
    f = 45 + 110 * np.exp(-t / 0.035)
    x = np.sin(TAU * np.cumsum(f) / SR) * np.exp(-t / 0.22)
    x += 0.25 * filt(rng.standard_normal(n), 'high', 2500) * np.exp(-t / 0.004)
    return np.tanh(x * 1.6) * 0.75 * g


def clap():
    n = int(0.35 * SR)
    t = T(n)
    nz = filt(rng.standard_normal(n), 'band', [900, 4200])
    e = np.zeros(n)
    for o in (0, 0.011, 0.022):
        e += (t >= o) * np.exp(-np.maximum(t - o, 0) / (0.012 if o < 0.02 else 0.12))
    return nz * e * 0.32


def hat(op=False):
    n = int((0.25 if op else 0.06) * SR)
    t = T(n)
    return filt(rng.standard_normal(n), 'high', 8000) * np.exp(-t / (0.08 if op else 0.014)) * 0.16


def shaker():
    n = int(0.09 * SR)
    t = T(n)
    return filt(rng.standard_normal(n), 'band', [5000, 11000]) * np.sin(np.pi * t / t[-1]) ** 2 * 0.07


def sub_note(f, d):
    n = int(d * SR)
    t = T(n)
    x = np.sin(TAU * f * t) + 0.25 * np.sin(TAU * 2 * f * t) + 0.1 * np.sin(TAU * 3 * f * t)
    return np.tanh(1.3 * x) * np.clip(t / 0.01, 0, 1) * np.clip((d - t) / 0.05, 0, 1) * 0.33


def whoosh(d=0.8, up=True, g=1.0):
    n = int(d * SR)
    t = T(n)
    nz = rng.standard_normal(n)
    fc = np.linspace(300, 6000, n) if up else np.linspace(6000, 300, n)
    out = np.zeros(n)
    blk = 512
    for i in range(0, n, blk):
        seg = nz[i:i + blk]
        c = fc[i]
        out[i:i + blk] = sosfilt(butter(2, [c * 0.6, min(c * 1.6, 20000)], 'band', fs=SR, output='sos'), seg)
    e = np.sin(np.pi * t / d) ** 2
    return out * e * 0.25 * g


def riser(d, g=1.0):
    n = int(d * SR)
    t = T(n)
    nz = filt(rng.standard_normal(n), 'high', 1500)
    tone = sum(np.sin(TAU * hz(62 + k * 12) * (1 + 0.5 * (t / d) ** 2) * t) for k in range(2)) * 0.15
    e = (t / d) ** 2.2
    return (nz * 0.22 + tone) * e * g


def impact(g=1.0):
    n = int(3.0 * SR)
    t = T(n)
    f = 32 + 70 * np.exp(-t / 0.08)
    boom = np.sin(TAU * np.cumsum(f) / SR) * np.exp(-t / 0.9)
    air = filt(rng.standard_normal(n), 'band', [2000, 9000]) * np.exp(-t / 0.5) * 0.15
    return np.tanh((boom * 1.2 + air)) * 0.6 * g


def shimmer(d=2.5, base=74, g=1.0):
    n = int(d * SR)
    t = T(n)
    x = np.zeros(n)
    for k, m in enumerate([base, base + 7, base + 12, base + 16, base + 19, base + 24]):
        x += np.sin(TAU * hz(m) * t + k) * np.exp(-t / (0.6 + 0.25 * k)) * np.clip((t - k * 0.06) / 0.01, 0, 1)
    return x * 0.06 * g


def key_click():
    n = int(0.05 * SR)
    t = T(n)
    x = filt(rng.standard_normal(n), 'band', [1800, 7000]) * np.exp(-t / 0.006)
    x += 0.4 * np.sin(TAU * 2400 * t) * np.exp(-t / 0.004)
    return x * rng.uniform(0.6, 1.0) * 0.12


def pop(f=900):
    n = int(0.12 * SR)
    t = T(n)
    fr = f * (1 + 0.8 * np.exp(-t / 0.01))
    return np.sin(TAU * np.cumsum(fr) / SR) * np.exp(-t / 0.035) * 0.22


def tick():
    n = int(0.08 * SR)
    t = T(n)
    return (np.sin(TAU * 3200 * t) * np.exp(-t / 0.008) + 0.5 * filt(rng.standard_normal(n), 'high', 4000) * np.exp(-t / 0.004)) * 0.08


TAU = 2 * np.pi

def piano(f, d=2.5, vel=1.0):
    n = int(d * SR)
    t = T(n)
    x = np.zeros(n)
    for k, (amp, dec) in enumerate([(1.0, 1.6), (0.45, 0.9), (0.25, 0.5), (0.12, 0.3), (0.07, 0.2)]):
        fk = f * (k + 1) * (1 + 0.0004 * (k + 1) ** 2)
        x += amp * np.sin(TAU * fk * t) * np.exp(-t / (dec * (1.3 - 0.3 * vel)))
    x += 0.15 * filt(rng.standard_normal(n), 'band', [1500, 5000]) * np.exp(-t / 0.006) * vel
    return x * np.clip(t / 0.003, 0, 1) * np.clip((d - t) / 0.3, 0, 1) * 0.17 * vel


def beats(t0, t1, step=B):
    k = 0
    while True:
        t = t0 + k * step
        if t >= t1 - 1e-6:
            return
        yield k, t
        k += 1


bus = {k: np.zeros((2, N)) for k in ('pad', 'keys', 'bass', 'drums', 'fx', 'ui')}

# ------------------------------------------------------------------ arrangement
# PAD: every bar, opening up as the film builds
for bar in range(20):
    t0 = bar * 4 * B
    bright = 0.15 if t0 < TRACK else 0.45 if t0 < PHONE else 0.75 if t0 < LOGO else 0.6
    for m in CHORDS[bar % 4]:
        add(bus['pad'], pad_voice(hz(m), 4 * B + 1.4, bright), t0 - 0.3, 1.0)
for m in [50, 54, 57, 61, 64, 69]:      # final Dmaj9
    add(bus['pad'], pad_voice(hz(m), 4.4, 0.6), 36.0 - 0.1, 1.3)

# PIANO on the opening lines, the journey line, the closing line
for t, ms in [(OPEN[0], [74, 62]), (OPEN[1], [78, 66]), (OPEN[2], [76, 64]), (JOURNEY, [74, 62, 50]),
              (TREAT, [78, 66]), (STORY, [81, 69]), (36.0, [74, 62, 50])]:
    for j, m in enumerate(ms):
        add(bus['keys'], piano(hz(m), 3.0, 1.0 - 0.2 * j), t, 0.9, pan=-0.15 + 0.15 * j)

# MARIMBA: one note per tile, then arps
for i, t in enumerate(TILES):
    ch = CHORDS[chord_at(t)]
    add(bus['keys'], pluck(hz(ch[[0, 2, 1, 3, 2, 4][i]] + 12), 1.4), t, 1.1, pan=-0.6 + i * 0.24)
arp_pat = [0, 2, 4, 1, 3, 4, 2, 1]


def arp(t0, t1, step=0.25, g=0.7, oct=12):
    for k, t in beats(t0, t1, step):
        ch = CHORDS[chord_at(t)]
        add(bus['keys'], pluck(hz(ch[arp_pat[k % 8]] + oct), 0.9, 0.8), t, g * (1.0 if k % 2 == 0 else 0.75), pan=0.35 * np.sin(k * 1.3))


arp(TOGETHER, PHONE, 0.5, 0.5)
arp(PHONE, LOGO - 0.5, 0.25, 0.55)
arp(30.0, 38.0, 0.5, 0.4)

# BASS
for bar in range(20):
    t0 = bar * 4 * B
    r = ROOTS[bar % 4]
    if PAIRS[0] <= t0 < PHONE:
        add(bus['bass'], sub_note(hz(r), 4 * B - 0.05), t0, 0.7)
    elif PHONE <= t0 < LOGO:
        for k in range(8):
            add(bus['bass'], sub_note(hz(r + (12 if k in (3, 7) else 0)), B / 2 - 0.02), t0 + k * B / 2, 0.85)
    elif t0 >= 30.0 and t0 < 38.0:
        add(bus['bass'], sub_note(hz(r), 4 * B - 0.05), t0, 0.7)
add(bus['bass'], sub_note(hz(38), 3.8), 36.0, 0.9)

# DRUMS
kicks = [t for k, t in beats(PAIRS[0], TOGETHER) if k % 4 == 0]          # half-time pulse under the pairs
kicks += [t for k, t in beats(TOGETHER, PHONE - 1.0) if k % 2 == 0]
kicks += [t for _, t in beats(PHONE, LOGO - 0.5)]                        # full groove
kicks += [t for k, t in beats(30.0, 36.0) if k % 2 == 0]
kicks += [LOGO]
kicks = sorted(set(round(k, 4) for k in kicks))
for t in kicks:
    add(bus['drums'], kick(0.8 if t < PHONE else 1.0), t, 1.0)
for k, t in beats(PHONE, LOGO - 0.5):
    if k % 2 == 1:
        add(bus['drums'], clap(), t, 0.9, pan=0.05)
    add(bus['drums'], hat(op=True), t + B / 2, 0.7, pan=0.25)
    add(bus['drums'], hat(), t + B / 4, 0.4, pan=-0.3)
for k, t in beats(TOGETHER, PHONE - 1.0):
    add(bus['drums'], hat(op=True), t + B / 2, 0.45, pan=0.25)
for k, t in beats(PAIRS[0], PHONE):
    add(bus['drums'], shaker(), t + B / 2, 0.8, pan=0.3)
for k, t in beats(30.0, 36.0):
    add(bus['drums'], shaker(), t + B / 2, 0.7, pan=0.3)
for k in range(8):                      # soft roll into "One patient"
    add(bus['drums'], clap(), PHONE - 1.0 + k * 0.125, 0.1 + 0.4 * k / 8)

# FX
add(bus['fx'], shimmer(2.5, 74, 0.8), OPEN[1], 1.0)
add(bus['fx'], whoosh(0.8, False, 0.5), 5.3, 1.0)
add(bus['fx'], whoosh(1.0, True, 0.5), JOURNEY - 0.5, 1.0)
add(bus['fx'], impact(0.5), JOURNEY, 1.0)
add(bus['fx'], whoosh(0.8, False, 0.6), 9.3, 1.0)
add(bus['fx'], impact(0.4), PAIRS[0], 1.0)
add(bus['fx'], shimmer(2.6, 78, 1.3), GLOW, 1.0)
add(bus['fx'], riser(2.0, 0.9), PHONE - 2.0, 0.7)
add(bus['fx'], impact(0.85), PHONE, 1.0)
add(bus['fx'], whoosh(1.2, True, 0.6), PHONE - 0.2, 1.0)
add(bus['fx'], shimmer(2.0, 74, 1.0), AIPASS, 1.0)
add(bus['fx'], whoosh(0.8, False, 0.6), 27.3, 1.0)
add(bus['fx'], riser(2.0, 1.0), LOGO - 2.0, 0.75)
add(bus['fx'], impact(1.0), LOGO, 1.0)
add(bus['fx'], shimmer(3.5, 74, 1.5), LOGO + 0.4, 1.0)
add(bus['fx'], whoosh(1.0, True, 0.4), 32.6, 1.0)
add(bus['fx'], shimmer(3.0, 78, 1.2), STORY, 1.0)

# UI
for t in TILES:
    add(bus['ui'], pop(700 + 40 * TILES.index(t)), t + 0.05, 0.6)
for i in range(6):
    add(bus['ui'], tick(), PHONE + 0.7 + i * 0.22, 0.6)
add(bus['ui'], pop(880), SOON, 0.8)

# ------------------------------------------------------------------ mix
kick_env = np.zeros(N)
for t in kicks:
    i = int(t * SR)
    n = min(int(0.3 * SR), N - i)
    kick_env[i:i + n] = np.maximum(kick_env[i:i + n], np.exp(-T(n) / 0.11))
duck = 1 - 0.6 * kick_env


def reverb(x, d=2.4, mix=0.25):
    n = int(d * SR)
    t = T(n)
    out = np.zeros_like(x)
    for c in range(2):
        ir = rng.standard_normal(n) * np.exp(-t / (d / 6.5))
        ir = filt(ir, 'low', 6000)
        ir[:int(0.012 * SR)] = 0
        wet = fftconvolve(x[c], ir)[:x.shape[1]]
        out[c] = wet / (np.sqrt(np.sum(ir ** 2)) + 1e-9)
    return x * (1 - mix) + out * mix


mixbus = (
    reverb(bus['pad'], 3.0, 0.35) * 0.9 * (1 - 0.35 * kick_env)
    + reverb(bus['keys'], 2.2, 0.3) * 0.75
    + bus['bass'] * duck * 0.9
    + reverb(bus['drums'], 0.9, 0.08) * 0.75
    + reverb(bus['fx'], 2.5, 0.3) * 0.75
    + reverb(bus['ui'], 0.8, 0.15) * 0.55
)
mixbus = filt(mixbus, 'high', 28)
# fade in/out
t = T(N)
mixbus *= np.clip(t / 0.05, 0, 1) * np.clip((DUR - t) / 1.2, 0, 1) ** 1.5
peak = np.max(np.abs(mixbus))
mixbus = np.tanh(mixbus / peak * 1.25) / np.tanh(1.25) * 0.89
os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
wavfile.write(os.path.join(HERE, 'out', 'audio.wav'), SR, (mixbus.T * 32767).astype(np.int16))
print('-> out/audio.wav', f'{DUR:.1f}s')
