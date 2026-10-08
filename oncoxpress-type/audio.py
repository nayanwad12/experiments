"""Original 10 s cue for the OncoXpress type ad, synthesised in numpy (no samples).

    python3 audio.py  ->  out/audio.wav   (48 kHz stereo, 10 s = 20 beats at 120 BPM)

Cue times mirror type.js.
"""

import os

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
B = 0.5
DUR = 10.0
N = int(SR * DUR)
TAU = 2 * np.pi
HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(5)

# ---- cues (keep in sync with type.js)
THE, NAME, BAND, RING, BOTH, SOON, CARD = 0.25, 0.75, 2.0, 3.0, 4.0, 6.0, 8.0

# E major: E | C#m | A | B   (one chord per bar of 2 s)
CHORDS = [[52, 56, 59, 63, 66], [49, 52, 56, 59, 64], [45, 49, 52, 56, 59], [47, 51, 54, 59, 61]]
ROOTS = [40, 37, 33, 35]


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


def saw(f, t, ph=0.0):
    return 2 * ((f * t + ph) % 1) - 1


def chord_at(t):
    return int(t // 2.0) % 4


def piano(f, d=2.5, vel=1.0):
    n = int(d * SR)
    t = T(n)
    x = np.zeros(n)
    for k, (amp, dec) in enumerate([(1.0, 1.4), (0.45, 0.8), (0.25, 0.45), (0.12, 0.28), (0.07, 0.18)]):
        x += amp * np.sin(TAU * f * (k + 1) * (1 + 0.0004 * (k + 1) ** 2) * t) * np.exp(-t / dec)
    x += 0.15 * filt(rng.standard_normal(n), 'band', [1500, 5000]) * np.exp(-t / 0.006)
    return x * np.clip(t / 0.003, 0, 1) * np.clip((d - t) / 0.3, 0, 1) * 0.16 * vel


def pluck(f, d=0.8):
    n = int(d * SR)
    t = T(n)
    x = np.sin(TAU * f * t) * np.exp(-t / 0.35) + 0.35 * np.sin(TAU * f * 4 * t) * np.exp(-t / 0.07) + 0.15 * saw(f, t) * np.exp(-t / 0.06)
    return x * np.clip(t / 0.002, 0, 1) * 0.24


def pad(f, d, bright=0.5):
    n = int(d * SR)
    t = T(n)
    out = np.zeros((2, n))
    for k, det in enumerate((-0.1, -0.03, 0.04, 0.1)):
        s = saw(f * (1 + det / 100 * 5), t, rng.uniform(0, 1)) * 0.6 + np.sin(TAU * f * t + k) * 0.5
        out[k % 2] += s
        out[(k + 1) % 2] += s * 0.4
    for c in range(2):
        out[c] = filt(out[c], 'low', 600 + 2400 * bright)
    return out * np.clip(t / 0.4, 0, 1) * np.clip((d - t) / 0.8, 0, 1) * 0.04


def kick(g=1.0):
    n = int(0.4 * SR)
    t = T(n)
    f = 46 + 110 * np.exp(-t / 0.03)
    return np.tanh(np.sin(TAU * np.cumsum(f) / SR) * np.exp(-t / 0.2) * 1.8) * 0.65 * g


def clap(g=1.0):
    n = int(0.3 * SR)
    t = T(n)
    e = sum((t >= o) * np.exp(-np.maximum(t - o, 0) / (0.01 if o < 0.02 else 0.1)) for o in (0, 0.01, 0.021))
    return filt(rng.standard_normal(n), 'band', [900, 4800]) * e * 0.25 * g


def hat(g=1.0):
    n = int(0.06 * SR)
    t = T(n)
    return filt(rng.standard_normal(n), 'high', 8000) * np.exp(-t / 0.012) * 0.12 * g


def sub(f, d):
    n = int(d * SR)
    t = T(n)
    return np.tanh(1.3 * (np.sin(TAU * f * t) + 0.25 * np.sin(TAU * 2 * f * t))) * np.exp(-t / (d * 0.8)) * np.clip(t / 0.005, 0, 1) * 0.3


def riser(d, g=1.0):
    n = int(d * SR)
    t = T(n)
    nz = filt(rng.standard_normal(n), 'high', 1500)
    tone = np.sin(TAU * np.cumsum(np.geomspace(220, 1320, n)) / SR) * 0.12
    return (nz * 0.2 + tone) * (t / d) ** 2.2 * g


def impact(g=1.0):
    n = int(2.5 * SR)
    t = T(n)
    f = 32 + 70 * np.exp(-t / 0.07)
    return np.tanh(np.sin(TAU * np.cumsum(f) / SR) * np.exp(-t / 0.8) * 1.2 + filt(rng.standard_normal(n), 'band', [2000, 9000]) * np.exp(-t / 0.4) * 0.15) * 0.55 * g


def shimmer(d=2.5, base=76, g=1.0):
    n = int(d * SR)
    t = T(n)
    x = sum(np.sin(TAU * hz(m) * t + k) * np.exp(-t / (0.6 + 0.25 * k)) * np.clip((t - k * 0.05) / 0.01, 0, 1)
            for k, m in enumerate([base, base + 7, base + 12, base + 16, base + 19, base + 24]))
    return x * 0.05 * g


def whoosh(d=0.6, g=1.0):
    n = int(d * SR)
    t = T(n)
    nz = rng.standard_normal(n)
    fc = np.geomspace(500, 6000, n)
    y = np.zeros(n)
    for i in range(0, n, 512):
        c = fc[i]
        y[i:i + 512] = sosfilt(butter(2, [c * 0.6, min(c * 1.5, 20000)], 'band', fs=SR, output='sos'), nz[i:i + 512])
    return y * np.sin(np.pi * t / d) ** 2 * 0.2 * g


bus = {k: np.zeros((2, N)) for k in ('pad', 'keys', 'bass', 'drums', 'fx')}

for bar in range(5):
    for m in CHORDS[bar % 4]:
        add(bus['pad'], pad(hz(m), 2.6, 0.3 if bar < 2 else 0.6), bar * 2.0 - 0.1, 1.0)
for m in [40, 52, 56, 59, 63, 66, 71]:
    add(bus['pad'], pad(hz(m), 2.2, 0.55), CARD - 0.05, 1.2)

add(bus['keys'], piano(hz(64), 2.0, 0.8), THE)
for m in [52, 64, 68, 71]:
    add(bus['keys'], piano(hz(m), 2.4, 0.9), NAME)
add(bus['keys'], pluck(hz(71)), BAND, 1.1, pan=-0.3)
add(bus['keys'], pluck(hz(73)), RING, 1.1, pan=0.3)
for k in range(int((SOON + 2.0 - BOTH) / (B / 2))):
    tt = BOTH + k * B / 2
    ch = CHORDS[chord_at(tt)]
    add(bus['keys'], pluck(hz(ch[[0, 2, 4, 2, 1, 3, 4, 3][k % 8]] + 12)), tt, 0.55 * (1.0 if k % 2 == 0 else 0.7), pan=0.35 * np.sin(k * 1.3))
for m in [64, 68, 71, 76]:
    add(bus['keys'], piano(hz(m), 2.2, 1.0), CARD)

for tt in (NAME, BAND, RING):
    add(bus['drums'], kick(0.9), tt, 1.0)
for k in range(int((CARD - BOTH) / B)):
    tt = BOTH + k * B
    add(bus['drums'], kick(), tt, 1.0)
    if k % 2 == 1:
        add(bus['drums'], clap(), tt, 1.0)
    add(bus['drums'], hat(), tt + B / 2, 1.0, pan=0.3)
add(bus['drums'], kick(1.1), CARD, 1.0)
for bar in range(2, 4):
    r = ROOTS[bar % 4]
    for k in range(8):
        add(bus['bass'], sub(hz(r + (12 if k in (3, 7) else 0)), B / 2 - 0.02), bar * 2.0 + k * B / 2, 0.9)
add(bus['bass'], sub(hz(40), 2.0), CARD, 1.0)

add(bus['fx'], shimmer(2.5, 76, 1.0), NAME, 1.0)
add(bus['fx'], whoosh(0.5, 0.8), BAND - 0.3, 1.0)
add(bus['fx'], whoosh(0.5, 0.8), RING - 0.3, 1.0)
add(bus['fx'], impact(0.5), BOTH, 1.0)
add(bus['fx'], riser(1.0, 0.9), SOON - 1.0, 1.0)
add(bus['fx'], impact(0.9), SOON, 1.0)
add(bus['fx'], shimmer(2.0, 80, 1.1), SOON, 1.0)
add(bus['fx'], shimmer(2.0, 76, 1.2), CARD + 0.05, 1.0)


def reverb(x, d=2.4, mix=0.3):
    n = int(d * SR)
    t = T(n)
    out = np.zeros_like(x)
    for c in range(2):
        ir = filt(rng.standard_normal(n) * np.exp(-t / (d / 6.5)), 'low', 6000)
        ir[:int(0.015 * SR)] = 0
        out[c] = fftconvolve(x[c], ir)[:x.shape[1]] / (np.sqrt(np.sum(ir ** 2)) + 1e-9)
    return x * (1 - mix) + out * mix


mix = (reverb(bus['pad'], 3.0, 0.35) * 0.9 + reverb(bus['keys'], 2.2, 0.3) * 0.8 + bus['bass'] * 0.85
       + reverb(bus['drums'], 0.9, 0.1) * 0.8 + reverb(bus['fx'], 2.5, 0.3) * 0.75)
mix = filt(mix, 'high', 28)
t = T(N)
mix *= np.clip(t / 0.03, 0, 1) * np.clip((DUR - t) / 0.6, 0, 1) ** 1.3
mix = np.tanh(mix / np.max(np.abs(mix)) * 1.3) / np.tanh(1.3) * 0.89
os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
wavfile.write(os.path.join(HERE, 'out', 'audio.wav'), SR, (mix.T * 32767).astype(np.int16))
print('-> out/audio.wav', f'{DUR:.1f}s')
