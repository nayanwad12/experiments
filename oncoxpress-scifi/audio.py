"""Original sci-fi score + SFX for the OncoXpress teaser, synthesised in numpy (no samples).

    python3 audio.py  ->  out/audio.wav   (48 kHz stereo, 26.4 s = 11 bars at 100 BPM)

Cue times mirror scifi.js.
"""

import os

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
BPM = 100
B = 60 / BPM          # 0.6 s
BAR = 4 * B           # 2.4 s
DUR = 26.4
N = int(SR * DUR)
TAU = 2 * np.pi
HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(21)

# ---- cues (keep in sync with scifi.js)
BOOT = [0.35, 0.85, 1.35]
TITLE = 2.4
BAND = 4.8
CALLOUTS = [6.6, 7.1, 13.2, 13.7]
DISSOLVE = 9.6
RING = 12.0
BOTH = 16.8
SYNC = 18.4
SOON = 21.6

ROOT = 38   # D2


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


def tvlp(x, cut):
    """time-varying low-pass, block-wise"""
    y = np.zeros_like(x)
    for i in range(0, len(x), 256):
        y[i:i + 256] = sosfilt(butter(2, float(np.clip(cut[min(i, len(cut) - 1)], 40, 20000)), 'low', fs=SR, output='sos'), x[i:i + 256])
    return y


bus = {k: np.zeros((2, N)) for k in ('drone', 'pulse', 'braam', 'drums', 'fx', 'ui')}

# ------------------------------------------------------------------ drone bed: D + A, slowly breathing, with wind
t = T(N)
dr = np.zeros(N)
for m, a in ((ROOT - 12, 0.6), (ROOT, 0.5), (ROOT + 7, 0.3), (ROOT + 12, 0.15)):
    for det in (-0.08, 0.07):
        dr += a * saw(hz(m) * (1 + det / 100 * 4), t, rng.uniform(0, 1))
cut = 180 + 260 * (0.5 + 0.5 * np.sin(t * 0.35)) + 900 * np.clip((t - BAND) / 12, 0, 1)
dr = tvlp(dr, cut) * 0.085
env = np.clip(t / 2.0, 0, 1) * np.clip((DUR - t) / 2.5, 0, 1)
wind = filt(rng.standard_normal(N), 'band', [300, 2400]) * (0.5 + 0.5 * np.sin(t * 0.21)) * 0.012
bus['drone'][0] += (dr + wind) * env
bus['drone'][1] += (dr * 0.95 + filt(rng.standard_normal(N), 'band', [300, 2400]) * 0.012) * env

# ------------------------------------------------------------------ pulse: 16th arp, opening filter, sidechained
pat = [0, 12, 7, 12, 3, 12, 7, 15]   # D minor colours (root, octave, fifth, minor third)


def pulse_note(f, d):
    n = int(d * SR)
    tt = T(n)
    x = saw(f, tt) * 0.6 + saw(f * 1.005, tt, 0.3) * 0.4
    return x * np.exp(-tt / 0.07) * np.clip(tt / 0.002, 0, 1)


k = 0
step = B / 4
tt = BAND
while tt < SOON - 1e-6:
    if not (DISSOLVE + 0.4 <= tt < RING):            # drop out for the morph
        m = ROOT + 24 + pat[k % 8] + (5 if (tt // BAR) % 4 == 2 else 0)
        x = pulse_note(hz(m), step * 0.95)
        prog = (tt - BAND) / (SOON - BAND)
        x = filt(x, 'low', 700 + 4200 * prog)
        add(bus['pulse'], x, tt, 0.34 * (1.0 if k % 4 == 0 else 0.7), pan=0.3 * np.sin(k * 0.9))
    tt += step
    k += 1

# ------------------------------------------------------------------ braam: low brass chord, filter opens then closes
def braam(d=3.2, g=1.0, chord=(ROOT - 12, ROOT, ROOT + 7, ROOT + 12, ROOT + 15)):
    n = int(d * SR)
    tt = T(n)
    out = np.zeros((2, n))
    for j, m in enumerate(chord):
        for det in (-0.1, 0.1):
            s = saw(hz(m) * (1 + det / 100 * 6), tt, rng.uniform(0, 1))
            out[(j + (det > 0)) % 2] += s
    cut = 120 + 2600 * np.exp(-tt / 0.45) * np.clip(tt / 0.06, 0, 1) + 200
    env = np.clip(tt / 0.04, 0, 1) * np.exp(-tt / 1.4)
    for c in range(2):
        out[c] = np.tanh(tvlp(out[c], cut) * 1.6) * env
    sub = np.sin(TAU * hz(ROOT - 12) * tt) * np.exp(-tt / 1.6) * np.clip(tt / 0.02, 0, 1)
    out += sub * 0.5
    return out * 0.32 * g


for tt, g in ((BAND, 1.0), (RING, 1.0), (BOTH, 0.6)):
    add(bus['braam'], braam(3.4, g), tt, 1.0)
add(bus['braam'], braam(4.6, 1.3, (ROOT - 12, ROOT, ROOT + 7, ROOT + 12, ROOT + 17, ROOT + 19)), SOON, 1.0)


# ------------------------------------------------------------------ drums
def kick(g=1.0):
    n = int(0.5 * SR)
    tt = T(n)
    f = 40 + 120 * np.exp(-tt / 0.03)
    return np.tanh(np.sin(TAU * np.cumsum(f) / SR) * np.exp(-tt / 0.25) * 2.0) * 0.7 * g


def taiko(g=1.0):
    n = int(0.9 * SR)
    tt = T(n)
    f = 70 + 60 * np.exp(-tt / 0.05)
    body = np.sin(TAU * np.cumsum(f) / SR) * np.exp(-tt / 0.32)
    skin = filt(rng.standard_normal(n), 'band', [150, 1200]) * np.exp(-tt / 0.08) * 0.5
    return np.tanh((body + skin) * 1.5) * 0.55 * g


def hat(g=1.0):
    n = int(0.05 * SR)
    tt = T(n)
    return filt(rng.standard_normal(n), 'high', 8000) * np.exp(-tt / 0.01) * 0.11 * g


for tt in (BAND, RING, BOTH, SOON):
    add(bus['drums'], kick(1.2), tt, 1.0)
for k2, tt in enumerate(np.arange(RING, SOON - 0.01, B)):
    if k2 % 4 == 0:
        add(bus['drums'], kick(0.7), tt, 1.0)
    add(bus['drums'], hat(), tt + B / 2, 1.0, pan=0.3)
# taiko build into the final hit (accelerating)
tt = 19.2
k2 = 0
while tt < SOON - 1e-6:
    u = (tt - 19.2) / (SOON - 19.2)
    add(bus['drums'], taiko(0.5 + 0.7 * u), tt, 1.0, pan=0.25 * np.sin(k2 * 1.7))
    tt += B / 2 if u < 0.5 else (B / 4 if u < 0.85 else B / 8)
    k2 += 1


# ------------------------------------------------------------------ fx / ui
def riser(d, g=1.0, f0=200, f1=4000):
    n = int(d * SR)
    tt = T(n)
    nz = rng.standard_normal(n)
    fc = np.geomspace(f0, f1, n)
    y = np.zeros(n)
    for i in range(0, n, 512):
        c = fc[i]
        y[i:i + 512] = sosfilt(butter(2, [c * 0.7, min(c * 1.4, 20000)], 'band', fs=SR, output='sos'), nz[i:i + 512])
    tone = np.sin(TAU * np.cumsum(np.geomspace(110, 880, n)) / SR) * 0.25
    return (y + tone) * (tt / d) ** 2.2 * 0.3 * g


def sweep(d=1.6, g=1.0, down=True):
    n = int(d * SR)
    tt = T(n)
    nz = rng.standard_normal(n)
    fc = np.geomspace(6000, 400, n) if down else np.geomspace(400, 6000, n)
    y = np.zeros(n)
    for i in range(0, n, 512):
        c = fc[i]
        y[i:i + 512] = sosfilt(butter(2, [c * 0.8, min(c * 1.25, 20000)], 'band', fs=SR, output='sos'), nz[i:i + 512])
    return y * np.sin(np.pi * tt / d) * 0.22 * g


def blip(f=1800, d=0.07, g=1.0):
    n = int(d * SR)
    tt = T(n)
    return np.sign(np.sin(TAU * f * tt)) * np.exp(-tt / (d / 3)) * 0.05 * g


def glitch(d=0.5, g=1.0):
    n = int(d * SR)
    y = np.zeros(n)
    i = 0
    while i < n:
        L = int(rng.uniform(0.008, 0.04) * SR)
        kind = rng.integers(3)
        seg = T(min(L, n - i))
        if kind == 0:
            y[i:i + len(seg)] = np.sign(np.sin(TAU * rng.uniform(300, 3000) * seg)) * 0.6
        elif kind == 1:
            y[i:i + len(seg)] = rng.standard_normal(len(seg)) * 0.5
        i += L + int(rng.uniform(0, 0.02) * SR)
    return filt(y, 'band', [200, 9000]) * 0.18 * g


def impact(g=1.0):
    n = int(3.0 * SR)
    tt = T(n)
    f = 28 + 60 * np.exp(-tt / 0.08)
    boom = np.sin(TAU * np.cumsum(f) / SR) * np.exp(-tt / 1.0)
    air = filt(rng.standard_normal(n), 'band', [1500, 9000]) * np.exp(-tt / 0.5) * 0.2
    return np.tanh(boom * 1.3 + air) * 0.6 * g


def chime(f=1760, d=2.0, g=1.0):
    n = int(d * SR)
    tt = T(n)
    return (np.sin(TAU * f * tt) * np.exp(-tt / 0.8) + 0.4 * np.sin(TAU * f * 2.01 * tt) * np.exp(-tt / 0.3)) * 0.06 * g


def whoosh(d=1.2, g=1.0):
    return sweep(d, g, down=False) + sweep(d, g * 0.5, down=True)


# boot: blips per typed line, ticks
for k3, t0 in enumerate(BOOT):
    for j in range(10):
        add(bus['ui'], blip(1400 + 200 * k3 + 60 * (j % 3), 0.03, 0.6), t0 + j * 0.06, 1.0, pan=-0.3)
    add(bus['ui'], blip(2400, 0.09, 1.0), t0 + 0.6, 1.0)
add(bus['fx'], riser(TITLE, 0.5, 120, 1800), 0.0, 1.0)
add(bus['fx'], impact(0.6), TITLE, 1.0)
add(bus['fx'], chime(hz(ROOT + 36), 3.0), TITLE + 0.1, 1.0)
for j in range(14):
    add(bus['ui'], blip(900 + 150 * (j % 5), 0.025, 0.5), TITLE + j * 0.045, 1.0, pan=0.2)
add(bus['fx'], glitch(0.45), 4.35, 1.0)
add(bus['fx'], riser(1.0, 0.8, 300, 5000), BAND - 1.0, 1.0)
add(bus['fx'], impact(0.9), BAND, 1.0)
add(bus['fx'], sweep(1.6, 1.0), BAND, 1.0)          # scan
for t0 in CALLOUTS:
    for j in range(6):
        add(bus['ui'], blip(2000 + 120 * j, 0.03, 0.6), t0 + 0.3 + j * 0.05, 1.0, pan=0.5 if t0 < 10 else -0.5)
add(bus['fx'], glitch(0.6, 1.2), DISSOLVE - 0.05, 1.0)
add(bus['fx'], whoosh(1.8, 1.2), DISSOLVE + 0.1, 1.0)
add(bus['fx'], riser(1.6, 0.9, 300, 6000), RING - 1.6, 1.0)
add(bus['fx'], impact(0.9), RING, 1.0)
add(bus['fx'], sweep(1.2, 0.9), 11.4, 1.0)          # ring scan
add(bus['fx'], whoosh(1.0, 0.8), 16.15, 1.0)
add(bus['fx'], sweep(1.1, 0.8), BOTH, 1.0)
for j in range(3):
    add(bus['fx'], chime(hz(ROOT + 31 + j * 5), 1.6, 0.9), SYNC + j * 0.2, 1.0, pan=-0.4 + j * 0.4)
add(bus['fx'], riser(2.4, 1.2, 150, 7000), SOON - 2.4, 1.0)
add(bus['fx'], glitch(0.4, 1.0), SOON - 0.42, 1.0)
add(bus['fx'], impact(1.3), SOON, 1.0)
add(bus['fx'], chime(hz(ROOT + 36), 4.0, 1.4), SOON + 0.05, 1.0)
add(bus['fx'], chime(hz(ROOT + 43), 4.0, 1.0), SOON + 0.1, 1.0)

# ------------------------------------------------------------------ mix
kick_env = np.zeros(N)
for tt in np.arange(RING, SOON - 0.01, B * 4):
    i = int(tt * SR)
    n = min(int(0.3 * SR), N - i)
    kick_env[i:i + n] = np.maximum(kick_env[i:i + n], np.exp(-T(n) / 0.12))


def reverb(x, d=3.0, mix=0.3):
    n = int(d * SR)
    tt = T(n)
    out = np.zeros_like(x)
    for c in range(2):
        ir = filt(rng.standard_normal(n) * np.exp(-tt / (d / 6.5)), 'low', 6000)
        ir[:int(0.02 * SR)] = 0
        out[c] = fftconvolve(x[c], ir)[:x.shape[1]] / (np.sqrt(np.sum(ir ** 2)) + 1e-9)
    return x * (1 - mix) + out * mix


mix = (
    reverb(bus['drone'], 4.0, 0.3)
    + reverb(bus['pulse'], 1.5, 0.25) * (1 - 0.5 * kick_env)
    + reverb(bus['braam'], 4.0, 0.35)
    + reverb(bus['drums'], 1.6, 0.2) * 0.9
    + reverb(bus['fx'], 3.5, 0.35) * 0.85
    + reverb(bus['ui'], 1.0, 0.2) * 0.7
)
mix = filt(mix, 'high', 25)
mix *= np.clip(t / 0.05, 0, 1) * np.clip((DUR - t) / 1.2, 0, 1) ** 1.3
peak = np.max(np.abs(mix))
mix = np.tanh(mix / peak * 1.3) / np.tanh(1.3) * 0.89
os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
wavfile.write(os.path.join(HERE, 'out', 'audio.wav'), SR, (mix.T * 32767).astype(np.int16))
print('-> out/audio.wav', f'{DUR:.1f}s @ {BPM} BPM')
