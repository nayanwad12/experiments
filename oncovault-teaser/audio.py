"""Original cinematic soundtrack for the OncoVault teaser, synthesised in numpy (no samples).

    python3 audio.py  ->  out/audio.wav   (48 kHz stereo, 40 s = 16 bars at 96 BPM)

Cue times mirror teaser.js.
"""

import os

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
BPM = 96
B = 60 / BPM          # 0.625 s
BAR = 4 * B           # 2.5 s
DUR = 40.0
N = int(SR * DUR)
TAU = 2 * np.pi
HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(3)

# ---- cues (keep in sync with teaser.js)
TEXT1 = [0.6, 2.1, 4.7]
JOURNEY = 7.8
NODES = [10.0, 10.625, 12.5, 13.125, 15.0, 15.625]
MORPH = 17.5
ONE = 20.0
WIDGETS = [22.4, 23.0]
LOGO = 27.6
WORDMARK = 29.0
SOON = 33.4
STORY = 35.0
FOOTER = 36.3

# F major: Fmaj9 | C/E | Dm9 | Bbmaj9   (one chord per bar)
CHORDS = [[53, 57, 60, 64, 67], [52, 55, 60, 64, 67], [50, 53, 57, 60, 64], [46, 50, 53, 57, 60]]
ROOTS = [41, 40, 38, 34]


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


bus = {k: np.zeros((2, N)) for k in ('pad', 'piano', 'bell', 'bass', 'drums', 'fx')}


# ------------------------------------------------------------------ instruments
def saw(f, t, ph=0.0):
    return 2 * ((f * t + ph) % 1) - 1


def pad_voice(f, d, bright=0.5):
    n = int(d * SR)
    t = T(n)
    out = np.zeros((2, n))
    for k, det in enumerate((-0.1, -0.04, 0.03, 0.08)):
        s = saw(f * (1 + det / 100 * 5), t, rng.uniform(0, 1)) * 0.6 + np.sin(TAU * f * t + k) * 0.6
        out[k % 2] += s
        out[(k + 1) % 2] += s * 0.4
    for c in range(2):
        out[c] = filt(out[c], 'low', 500 + 2000 * bright)
    a = np.clip(t / 1.2, 0, 1) * np.clip((d - t) / 1.4, 0, 1)
    return out * a * 0.045


def piano(f, d=2.5, vel=1.0):
    n = int(d * SR)
    t = T(n)
    x = np.zeros(n)
    for k, (amp, dec) in enumerate([(1.0, 1.6), (0.45, 0.9), (0.25, 0.5), (0.12, 0.3), (0.07, 0.2)]):
        fk = f * (k + 1) * (1 + 0.0004 * (k + 1) ** 2)
        x += amp * np.sin(TAU * fk * t) * np.exp(-t / (dec * (1.3 - 0.3 * vel)))
    x += 0.15 * filt(rng.standard_normal(n), 'band', [1500, 5000]) * np.exp(-t / 0.006) * vel
    return x * np.clip(t / 0.003, 0, 1) * np.clip((d - t) / 0.3, 0, 1) * 0.16 * vel


def bell(f, d=2.4):
    n = int(d * SR)
    t = T(n)
    x = np.sin(TAU * f * t) * np.exp(-t / 1.1) + 0.5 * np.sin(TAU * f * 2.76 * t) * np.exp(-t / 0.4) + 0.25 * np.sin(TAU * f * 5.4 * t) * np.exp(-t / 0.15)
    return x * np.clip(t / 0.002, 0, 1) * 0.09


def heartbeat(g=1.0):
    n = int(0.6 * SR)
    t = T(n)
    out = np.zeros(n)
    for o, a in ((0, 1.0), (0.2, 0.7)):
        tt = np.maximum(t - o, 0)
        f = 42 + 30 * np.exp(-tt / 0.03)
        out += (t >= o) * np.sin(TAU * np.cumsum(f * (t >= o)) / SR) * np.exp(-tt / 0.12) * a
    return np.tanh(out * 1.5) * 0.5 * g


def kick(g=1.0):
    n = int(0.4 * SR)
    t = T(n)
    f = 46 + 90 * np.exp(-t / 0.035)
    return np.tanh(np.sin(TAU * np.cumsum(f) / SR) * np.exp(-t / 0.2) * 1.6) * 0.55 * g


def clap(g=1.0):
    n = int(0.35 * SR)
    t = T(n)
    nz = filt(rng.standard_normal(n), 'band', [900, 4500])
    e = np.zeros(n)
    for o in (0, 0.01, 0.021):
        e += (t >= o) * np.exp(-np.maximum(t - o, 0) / (0.012 if o < 0.02 else 0.13))
    return nz * e * 0.18 * g


def shaker(g=1.0):
    n = int(0.1 * SR)
    t = T(n)
    return filt(rng.standard_normal(n), 'band', [5000, 11000]) * np.sin(np.pi * t / t[-1]) ** 2 * 0.06 * g


def sub_note(f, d):
    n = int(d * SR)
    t = T(n)
    x = np.sin(TAU * f * t) + 0.2 * np.sin(TAU * 2 * f * t)
    return np.tanh(1.2 * x) * np.clip(t / 0.03, 0, 1) * np.clip((d - t) / 0.2, 0, 1) * 0.3


def whoosh(d=0.9, up=True, g=1.0):
    n = int(d * SR)
    t = T(n)
    nz = rng.standard_normal(n)
    fc = np.geomspace(250, 5000, n) if up else np.geomspace(5000, 250, n)
    out = np.zeros(n)
    for i in range(0, n, 512):
        c = fc[i]
        out[i:i + 512] = sosfilt(butter(2, [c * 0.6, min(c * 1.6, 20000)], 'band', fs=SR, output='sos'), nz[i:i + 512])
    return out * np.sin(np.pi * t / d) ** 2 * 0.2 * g


def riser(d, g=1.0):
    n = int(d * SR)
    t = T(n)
    nz = filt(rng.standard_normal(n), 'high', 1200)
    tone = sum(np.sin(TAU * hz(65 + k * 12) * (1 + 0.4 * (t / d) ** 2) * t) for k in range(2)) * 0.1
    return (nz * 0.15 + tone) * (t / d) ** 2.4 * g


def impact(g=1.0):
    n = int(3.5 * SR)
    t = T(n)
    f = 30 + 55 * np.exp(-t / 0.09)
    boom = np.sin(TAU * np.cumsum(f) / SR) * np.exp(-t / 1.1)
    air = filt(rng.standard_normal(n), 'band', [1500, 7000]) * np.exp(-t / 0.6) * 0.12
    return np.tanh(boom * 1.1 + air) * 0.55 * g


def shimmer(d=3.0, base=77, g=1.0):
    n = int(d * SR)
    t = T(n)
    x = np.zeros(n)
    for k, m in enumerate([base, base + 7, base + 12, base + 16, base + 19, base + 24]):
        x += np.sin(TAU * hz(m) * t + k) * np.exp(-t / (0.7 + 0.3 * k)) * np.clip((t - k * 0.07) / 0.01, 0, 1)
    return x * 0.05 * g


def pop(f=900):
    n = int(0.12 * SR)
    t = T(n)
    fr = f * (1 + 0.6 * np.exp(-t / 0.012))
    return np.sin(TAU * np.cumsum(fr) / SR) * np.exp(-t / 0.04) * 0.16


def beats(t0, t1, step=B):
    k = 0
    while True:
        t = t0 + k * step
        if t >= t1 - 1e-6:
            return
        yield k, t
        k += 1


# ------------------------------------------------------------------ arrangement
# PAD: every bar; darker in the intro, open from "One patient", warm on the logo
for bar in range(16):
    t0 = bar * BAR
    bright = 0.15 if t0 < JOURNEY else 0.35 if t0 < ONE else 0.6 if t0 < LOGO else 0.5
    ch = CHORDS[bar % 4] if bar < 15 else CHORDS[0]
    for m in ch:
        add(bus['pad'], pad_voice(hz(m), BAR + 1.6, bright), t0 - 0.2, 1.0)
for m in [41, 53, 57, 60, 64, 67, 72]:   # final Fmaj9 swell
    add(bus['pad'], pad_voice(hz(m), 5.5, 0.55), 35.0 - 0.3, 1.1)

# PIANO: single notes on the opening lines, then 8th arpeggios, sparse melody at the end
for t, m in zip(TEXT1, [72, 76, 74]):
    add(bus['piano'], piano(hz(m), 3.0, 0.9), t, 1.0, pan=-0.1)
    add(bus['piano'], piano(hz(m - 12), 3.0, 0.6), t, 0.8, pan=0.1)
arp_pat = [0, 2, 4, 2, 1, 3, 4, 3]


def arp(t0, t1, step=B / 2, g=0.7, oct=12):
    for k, t in beats(t0, t1, step):
        ch = CHORDS[chord_at(t)]
        add(bus['piano'], piano(hz(ch[arp_pat[k % 8]] + oct), 1.4, 0.7), t, g * (1.0 if k % 2 == 0 else 0.7), pan=0.35 * np.sin(k * 1.1))


arp(JOURNEY - 0.3 + 0.3, LOGO, B / 2, 0.55)
arp(LOGO + BAR, 37.5, B / 2, 0.45)
for t, m in [(ONE, 77), (ONE + 1.25, 76), (21.3, 72), (25.0, 74), (STORY, 77), (37.5, 72)]:
    add(bus['piano'], piano(hz(m), 3.0, 1.0), t, 1.0)
add(bus['piano'], piano(hz(53), 3.0, 0.9), 37.5, 0.8)
add(bus['piano'], piano(hz(65), 3.0, 0.9), 37.5, 0.8)

# BELLS: one per treatment stage, then the logo
for i, t in enumerate(NODES):
    ch = CHORDS[chord_at(t)]
    add(bus['bell'], bell(hz(ch[[2, 4, 1, 3, 2, 4][i]] + 24)), t, 1.0, pan=-0.6 + i * 0.24)
for k, m in enumerate([77, 81, 84, 89]):
    add(bus['bell'], bell(hz(m), 3.0), LOGO + 0.1 + k * 0.12, 0.9, pan=-0.3 + k * 0.2)
add(bus['bell'], bell(hz(84), 2.6), SOON, 0.9)

# HEARTBEAT under the intro and the journey
for bar in range(1, 8):
    add(bus['drums'], heartbeat(0.7 if bar < 3 else 0.55), bar * BAR, 1.0)

# GROOVE: soft pulse from "One patient", lighter after the logo
for k, t in beats(ONE, LOGO):
    if k % 2 == 0:
        add(bus['drums'], kick(), t, 1.0)
    else:
        add(bus['drums'], clap(), t, 0.8 if t >= ONE + BAR else 0.0)
    add(bus['drums'], shaker(), t + B / 2, 1.0, pan=0.3)
for k, t in beats(10.0, ONE, B / 2):
    add(bus['drums'], shaker(0.7), t, 1.0, pan=0.3)
for k, t in beats(LOGO + BAR, 37.5):
    if k % 2 == 0:
        add(bus['drums'], kick(0.7), t, 1.0)
    add(bus['drums'], shaker(0.8), t + B / 2, 1.0, pan=0.3)

# BASS
for bar in range(16):
    t0 = bar * BAR
    if t0 < JOURNEY:
        continue
    r = ROOTS[bar % 4] if bar < 15 else ROOTS[0]
    add(bus['bass'], sub_note(hz(r), BAR - 0.05), t0, 0.7 if t0 < ONE else 1.0)

# FX
add(bus['fx'], whoosh(1.2, True, 0.5), JOURNEY - 0.6, 1.0)
add(bus['fx'], whoosh(1.0, False, 0.6), MORPH, 1.0)
add(bus['fx'], shimmer(2.5, 77, 0.8), MORPH + 0.6, 1.0)
add(bus['fx'], riser(2.0, 0.8), ONE - 2.0, 0.7)
add(bus['fx'], impact(0.6), ONE, 1.0)
add(bus['fx'], whoosh(0.8, True, 0.5), WIDGETS[0] - 0.3, 1.0)
add(bus['fx'], whoosh(1.0, False, 0.6), 26.8, 1.0)
add(bus['fx'], riser(2.5, 1.0), LOGO - 2.5, 0.8)
add(bus['fx'], impact(1.0), LOGO, 1.0)
add(bus['fx'], shimmer(4.0, 77, 1.4), LOGO + 0.2, 1.0)
add(bus['fx'], whoosh(1.2, True, 0.4), 32.3, 1.0)
add(bus['fx'], shimmer(3.5, 72, 1.0), STORY, 1.0)
for t in WIDGETS:
    add(bus['fx'], pop(820), t + 0.05, 0.6)
add(bus['fx'], pop(980), SOON, 0.7)

# ------------------------------------------------------------------ mix
kick_env = np.zeros(N)
for k, t in beats(ONE, LOGO):
    if k % 2 == 0:
        i = int(t * SR)
        n = min(int(0.3 * SR), N - i)
        kick_env[i:i + n] = np.maximum(kick_env[i:i + n], np.exp(-T(n) / 0.12))


def reverb(x, d=2.4, mix=0.3):
    n = int(d * SR)
    t = T(n)
    out = np.zeros_like(x)
    for c in range(2):
        ir = filt(rng.standard_normal(n) * np.exp(-t / (d / 6.5)), 'low', 5500)
        ir[:int(0.015 * SR)] = 0
        out[c] = fftconvolve(x[c], ir)[:x.shape[1]] / (np.sqrt(np.sum(ir ** 2)) + 1e-9)
    return x * (1 - mix) + out * mix


mixbus = (
    reverb(bus['pad'], 3.5, 0.4) * 0.9 * (1 - 0.3 * kick_env)
    + reverb(bus['piano'], 2.8, 0.35) * 0.85
    + reverb(bus['bell'], 3.2, 0.45) * 0.8
    + bus['bass'] * (1 - 0.4 * kick_env) * 0.85
    + reverb(bus['drums'], 1.2, 0.12) * 0.75
    + reverb(bus['fx'], 3.0, 0.35) * 0.7
)
mixbus = filt(mixbus, 'high', 28)
t = T(N)
mixbus *= np.clip(t / 0.3, 0, 1) * np.clip((DUR - t) / 2.0, 0, 1) ** 1.3
peak = np.max(np.abs(mixbus))
mixbus = np.tanh(mixbus / peak * 1.15) / np.tanh(1.15) * 0.89
os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
wavfile.write(os.path.join(HERE, 'out', 'audio.wav'), SR, (mixbus.T * 32767).astype(np.int16))
print('-> out/audio.wav', f'{DUR:.1f}s @ {BPM} BPM')
