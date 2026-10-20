"""Original 144 BPM trailer score + sound design, synthesised in numpy (no samples).

    python3 audio.py  ->  out/audio.wav   (48 kHz stereo, 20 s = 48 beats)

Cue beats mirror the timeline in trailer.js (styles every 2 beats from 12, montage 36-40, finale 40-48).
"""

import os

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 48000
BPM = 144
B = 60 / BPM
BEATS = 48
DUR = BEATS * B
N = int(SR * DUR)
HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(7)

# keep in sync with trailer.js
TITLES = [2, 3.5, 5]
STROBE = (5.75, 7.375)
STYLE_CUTS = list(range(12, 36, 2))
MONT = [36, 36.5, 37, 37.5, 37.75, 38, 38.25, 38.5, 38.75, 39, 39.25]

# D minor: i - VI - III - VII  (Dm, Bb, F, C), one chord per bar
CHORDS = [[62, 65, 69], [58, 62, 65], [60, 65, 69], [60, 64, 67]]
ROOTS = [38, 34, 41, 36]
def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def T(n):
    return np.arange(n) / SR


def ns(d):
    return rng.standard_normal(int(d * SR))


def filt(x, kind, f, order=2):
    return sosfilt(butter(order, f, kind, fs=SR, output='sos'), x)


def env(n, a, d):
    t = T(n)
    e = np.exp(-t / d)
    if a > 0:
        e *= np.clip(t / a, 0, 1)
    return e


def buses():
    return {k: np.zeros((2, N)) for k in ('drums', 'bass', 'music', 'fx')}


BUS = buses()
KICKS = []


def place(bus, x, beat, g=1.0, pan=0.0):
    """Add mono or stereo signal x at a beat position (pan -1..1 for mono)."""
    i = int(round(beat * B * SR))
    if x.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        x = np.vstack([x * l * 1.414, x * r * 1.414])
    if i >= N:
        return
    if i < 0:
        x, i = x[:, -i:], 0
    x = x[:, :N - i]
    BUS[bus][:, i:i + x.shape[1]] += g * x


def svf(x, f0, f1, q=0.7, kind='bp'):
    """Chamberlin state-variable filter with an exponential cutoff sweep f0 -> f1."""
    n = len(x)
    fc = f0 * (f1 / f0) ** (np.arange(n) / max(1, n - 1))
    F = 2 * np.sin(np.pi * np.minimum(fc, SR / 6) / SR)
    lo = bp = 0.0
    out = np.empty(n)
    damp = 1 / q
    for i in range(n):
        hi = x[i] - lo - damp * bp
        bp += F[i] * hi
        lo += F[i] * bp
        out[i] = bp if kind == 'bp' else lo if kind == 'lp' else hi
    return out


# ---------------------------------------------------------------- instruments
def kick(punch=1.0):
    n = int(.45 * SR); t = T(n)
    f = 48 + 150 * np.exp(-t / .03)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / .22) + .5 * np.sin(ph) * np.exp(-t / .02)
    click = filt(ns(.45)[:n], 'hp', 3000) * np.exp(-t / .003) * .45 * punch
    return np.tanh(2.2 * y) * .95 + click


def clap():
    n = int(.35 * SR); t = T(n)
    x = filt(ns(.35)[:n], 'bp', [900, 2600])
    e = np.zeros(n)
    for k, o in enumerate([0, .011, .022]):
        i = int(o * SR); e[i:] += np.exp(-(t[:n - i]) / (.006 if k < 2 else .14))
    return x * e * .9


def hat(open_=False):
    d = .22 if open_ else .045
    n = int(d * SR)
    return filt(ns(d)[:n], 'hp', 7500) * env(n, 0, d / 3) * .5


def snare():
    n = int(.25 * SR); t = T(n)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t / .05) * .5
    return (filt(ns(.25)[:n], 'hp', 1500) * np.exp(-t / .07) + tone) * .7


def crash(d=2.4):
    n = int(d * SR); t = T(n)
    x = filt(ns(d)[:n], 'hp', 5000)
    metal = sum(np.sign(np.sin(2 * np.pi * f * t)) for f in (421, 587, 723, 911, 1187)) * .04
    return (x + filt(metal, 'hp', 3000)) * np.exp(-t / .7) * .45


def boom(d=2.2, f0=90, f1=34):
    n = int(d * SR); t = T(n)
    f = f1 + (f0 - f1) * np.exp(-t / .12)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .75)
    return np.tanh(1.6 * y)


def impact(big=1.0):
    k = kick(1.5)
    b = boom()
    nz = filt(ns(1.0), 'lp', 2500) * env(SR, 0, .18) * .6
    out = np.zeros(len(b)); out[:len(k)] += k; out[:len(nz)] += nz; out += b * .9
    return out * big


def whoosh(d, rev=False):
    n = int(d * SR)
    x = svf(ns(d)[:n], 300, 7000, q=2.2) if not rev else svf(ns(d)[:n], 7000, 300, q=2.2)
    e = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    if rev:
        e = np.linspace(0, 1, n) ** 3
    return x * e * .55


def riser(d):
    n = int(d * SR); t = T(n)
    p = t / d
    nz = svf(ns(d)[:n], 400, 9000, q=1.5) * p ** 2 * .5
    f = 180 * 2 ** (3 * p)
    tone = (2 * ((np.cumsum(f) / SR) % 1) - 1) * p ** 2.5 * .12
    return nz + filt(tone, 'hp', 300)


def click(hi=1.0):
    n = int(.03 * SR)
    return filt(ns(.03)[:n], 'bp', [2000 * hi, 6000 * hi]) * env(n, 0, .004) * .6


def pop(f=600):
    n = int(.12 * SR); t = T(n)
    ff = f * (1 + 1.5 * np.exp(-t / .01))
    return np.sin(2 * np.pi * np.cumsum(ff) / SR) * env(n, .001, .035) * .6


def blip(f):
    n = int(.25 * SR); t = T(n)
    ff = f * (0.5 + 0.5 * np.clip(t / .03, 0, 1))
    return np.sin(2 * np.pi * np.cumsum(ff) / SR) * env(n, .002, .07) * .5


def supersaw(notes, d, cutoff, detune=.12, voices=5):
    n = int(d * SR); t = T(n)
    y = np.zeros((2, n))
    for m in notes:
        for v in range(voices):
            det = (v - (voices - 1) / 2) / ((voices - 1) / 2) * detune
            f = hz(m + det)
            ph = rng.random()
            s = 2 * ((f * t + ph) % 1) - 1
            pan = (v / (voices - 1)) * 2 - 1
            y[0] += s * (1 - pan) / 2
            y[1] += s * (1 + pan) / 2
    y /= len(notes) * voices / 2.5
    return np.vstack([filt(y[0], 'lp', cutoff), filt(y[1], 'lp', cutoff)])


def bass_note(m, d, cutoff=900):
    n = int(d * SR); t = T(n)
    f = hz(m)
    s = (2 * ((f * t) % 1) - 1) * .6 + np.sin(2 * np.pi * f * t) * .7
    return filt(s, 'lp', cutoff) * env(n, .003, d * .6)


def pluck(m, d=.25, bright=4000):
    n = int(d * SR); t = T(n)
    f = hz(m)
    s = np.sign(np.sin(2 * np.pi * f * t)) * .5 + (2 * ((f * t) % 1) - 1) * .5
    return filt(s, 'lp', bright) * env(n, .001, .09) * .5


def chord_at(beat):
    return int(beat // 4) % 4


# ---------------------------------------------------------------- trailer instruments
def sweep_lp(x, cut, block=256):
    """Lowpass whose cutoff follows the array `cut` (block-wise, filter state carried)."""
    out = np.empty_like(x)
    zi = None
    for i in range(0, len(x), block):
        c = float(np.clip(cut[min(i, len(cut) - 1)], 30, SR * .45))
        sos = butter(2, c, 'lp', fs=SR, output='sos')
        if zi is None:
            zi = np.zeros((sos.shape[0], 2))
        out[i:i + block], zi = sosfilt(sos, x[i:i + block], zi=zi)
    return out


def braam(d=1.8, notes=(26, 38, 45, 50), bright=1.0):
    """Detuned brass-like saw cluster with a filter that blasts open and closes: the trailer hit."""
    n = int(d * SR); t = T(n)
    y = np.zeros(n)
    for m in notes:
        for det in (-.16, 0, .13):
            y += 2 * ((hz(m + det) * t + rng.random()) % 1) - 1
    y /= len(notes) * 1.5
    cut = 140 + 2400 * bright * np.exp(-t / .5) * (1 - np.exp(-t / .03))
    e = np.clip(t / .012, 0, 1) * np.exp(-t / (d * .42))
    sub = np.sin(2 * np.pi * hz(notes[0]) * t) * e * .8
    return np.tanh(2.6 * sweep_lp(y, cut) * e) * .8 + sub


def sub_drop(d=1.6, f0=90, f1=28):
    n = int(d * SR); t = T(n)
    f = f1 + (f0 - f1) * np.exp(-t / .35)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (d * .5)) * .9


def shing(f0=2100, d=1.4):
    n = int(d * SR); t = T(n)
    y = sum(np.sin(2 * np.pi * f0 * r * t + k) * np.exp(-t / (.5 / (1 + k * .4))) for k, r in enumerate((1, 1.618, 2.47, 3.73, 5.1)))
    sw = svf(ns(.35)[:int(.35 * SR)], 2500, 11000, q=3) * np.linspace(1, 0, int(.35 * SR)) ** 2
    y[:len(sw)] += sw * 1.4
    return y * .18


def chime(f, d=1.6, a=.5):
    n = int(d * SR); t = T(n)
    return sum(np.sin(2 * np.pi * f * r * t) * np.exp(-t / (d * .35 / (1 + i))) / (1 + i) for i, r in enumerate((1, 2.76, 5.4, 8.93))) * env(n, .002, 10) * a


def zap():
    n = int(.14 * SR); t = T(n)
    f = 90 + 2400 * np.exp(-t / .025)
    return np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * env(n, 0, .05) * .25


def buzz(d, gate):
    n = int(d * SR); t = T(n)
    y = sum(np.sign(np.sin(2 * np.pi * 120 * k * t)) / k for k in (1, 2, 3))
    y = filt(y, 'bp', [180, 3000]) + filt(ns(d)[:n], 'bp', [2000, 6000]) * .3
    return y * gate[:n] * .35


def bloop(f0=380, f1=1500, d=.18):
    n = int(d * SR); t = T(n)
    f = f0 + (f1 - f0) * (1 - np.exp(-t / .03))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .002, .05) * .5


def boing(f=330):
    n = int(.35 * SR); t = T(n)
    ff = f * (1 + .6 * np.exp(-t / .04)) * (1 + .05 * np.sin(2 * np.pi * 16 * t))
    return np.sin(2 * np.pi * np.cumsum(ff) / SR) * env(n, .002, .12) * .5


def square(f, d, a=.18):
    n = int(d * SR); t = T(n)
    return np.sign(np.sin(2 * np.pi * f * t)) * env(n, .001, d * .7) * a


def coin():
    a = square(988, .07, .2)
    b = square(1319, .4, .2)
    return np.concatenate([a, b])


def pow_hit():
    s = snare() * 1.2
    k = kick(1.2)
    n = max(len(s), len(k))
    y = np.zeros(n); y[:len(s)] += s; y[:len(k)] += k * .8
    return y


def scribble(d):
    n = int(d * SR); t = T(n)
    am = np.clip(np.sin(2 * np.pi * 19 * t + 3 * np.sin(2 * np.pi * 5 * t)), 0, 1) ** .5
    return filt(ns(d)[:n], 'bp', [1500, 5000]) * am * .3


def tom(f=110):
    n = int(.5 * SR); t = T(n)
    ff = f * (1 + .8 * np.exp(-t / .03))
    y = np.sin(2 * np.pi * np.cumsum(ff) / SR) * np.exp(-t / .22)
    return np.tanh(1.8 * y) * .8 + filt(ns(.5)[:n], 'bp', [400, 2000]) * np.exp(-t / .02) * .3


def rev_crash(d):
    c = crash(d)[::-1]
    return c * np.linspace(0, 1, len(c)) ** 2


def noise_burst(d=.08, hp=2000):
    n = int(d * SR)
    return filt(ns(d)[:n], 'hp', hp) * env(n, 0, d / 5) * .7


def big_chord(notes, d, cutoff, voices=7):
    y = supersaw(notes, d, cutoff, detune=.16, voices=voices)
    return y * np.minimum(1, np.linspace(1.6, 0, y.shape[1]))


def jhash(n):
    """Same hash as trailer.js, so flickers line up with the picture."""
    x = np.sin(n * 127.1 + 311.7) * 43758.5453
    return x - np.floor(x)


# ---------------------------------------------------------------- arrangement
def intro():
    # drone + dark pad swelling toward the strobe
    n = int(7.45 * B * SR); t = T(n)
    swell = np.clip(t / (7.45 * B), 0, 1)
    drone = np.sin(2 * np.pi * hz(26) * t) * .7 + filt(2 * ((hz(38) * t) % 1) - 1, 'lp', 220) * .35
    place('music', drone * (.15 + .85 * swell ** 2), 0, .3)
    for bar in range(2):
        p = supersaw([50, 57, 62, 65], B * 4.1, 500 + bar * 900)
        place('music', p * np.linspace(.2 + bar * .4, .6 + bar * .4, p.shape[1]), bar * 4, .16)
    for b, g in ((0, .9), (.45, .6), (1, .9), (1.45, .6)):   # heartbeat
        place('drums', filt(kick(.3), 'lp', 260), b, g * 1.4)
    place('fx', chime(1175, 2.0, .25), .5, .5, pan=-.3)
    place('fx', rev_crash(B * 1.2), 2 - 1.2, .35)
    for a in TITLES:
        place('fx', braam(1.5), a, .8)
        place('fx', impact(.7), a, .9)
        place('fx', crash(1.6), a, .2)
        place('fx', whoosh(B * .7, rev=True), a - .7, .35)
    for i in range(13):   # one tick per strobe still, climbing
        b = STROBE[0] + i * .125
        place('fx', blip(700 * 2 ** (i / 9)), b, .45, pan=.4 if i % 2 else -.4)
        place('fx', click(1.3), b, .5)
    place('fx', riser(B * 3.4), 4.0, .85)
    place('fx', noise_burst(.12, 1500), STROBE[1], 1.0)
    place('fx', impact(.5), STROBE[1], .6)
    place('fx', whoosh(B * .5, rev=True), 7.5, .8)
    place('fx', rev_crash(B * .5), 7.5, .5)


def groove():
    for b in range(8, 36):
        place('drums', kick(1.1), b, 1.0); KICKS.append(b)
        if b % 2 == 1:
            place('drums', clap(), b, .8); place('drums', snare(), b, .45)
        for s in (.25, .5, .75):
            place('drums', hat(open_=(s == .5 and b >= 24 and b % 2 == 0)), b + s, .42 if s == .5 else .2 + .1 * rng.random(), pan=.3 if s == .5 else -.3)
        if b % 8 == 7:
            for s in (.5, .625, .75, .875):
                place('drums', snare(), b + s, .3 + .3 * s)
        r = ROOTS[chord_at(b)]
        for s in (.25, .5, .75):
            place('bass', bass_note(r + (12 if (s == .75 and b % 2) else 0), B * .22, 1300), b + s, .85)
    for bar in range(2, 9):
        place('music', supersaw([m - 12 for m in CHORDS[bar % 4]] + CHORDS[bar % 4], B * 4.05, 1400), bar * 4, .22)
    for c in [8] + STYLE_CUTS:   # stab on every style cut
        st = supersaw([m + 12 for m in CHORDS[chord_at(c)]] + CHORDS[chord_at(c)], .22, 5200)
        place('music', st * env(st.shape[1], .002, .08), c, .55)
    for b in np.arange(16, 36, .25):   # arp, brightening toward the montage
        ch = CHORDS[chord_at(b)]
        k = int(round((b - 16) * 4))
        m = ch[k % 3] + 12 * (1 + (k // 3) % 2)
        place('music', pluck(m, .2, 1800 + 4000 * (b - 16) / 20), b, .3, pan=.45 * np.sin(k * .9))


def styles():
    # 01 chrome: the drop
    place('fx', impact(1.3), 8, 1.0); place('fx', braam(2.2, bright=1.2), 8, .9)
    place('fx', crash(3.0), 8, .55); place('fx', sub_drop(), 8, .8)
    place('fx', shing(2100), 8.12, .9, pan=.3); place('fx', shing(2600, 1.0), 10, .7, pan=-.4)
    for c in STYLE_CUTS:
        place('fx', whoosh(B * .75, rev=True), c - .75, .45, pan=.5 if c % 4 else -.5)
        place('fx', impact(.35), c, .55)
    # 02 glass
    for i, (b, f) in enumerate(((12.08, 1568), (12.3, 2093), (12.5, 2637), (13.2, 3136))):
        place('fx', chime(f, 1.4, .35), b, .5, pan=(-.5, .4, -.2, .5)[i])
    # 03 neumorph: button, slider, toggle
    place('fx', pop(420), 14.05, .8); place('fx', click(.7), 14.6, .6)
    place('fx', pop(950), 15.0, .7); place('fx', click(1.2), 15.02, .6)
    # 04 neon: buzz that follows the flicker, zap on the sign frame
    n = int(2 * B * SR); lb = np.arange(n) / SR / B
    gate = np.zeros(n)
    for k in range(11):
        st = .04 + jhash(k * 3.3 + 1) * .42
        on = (lb >= st) & (lb < st + .22) & (jhash(np.floor(lb * 30) + k * 13) > .5)
        gate += on
    gate = np.clip(gate / 2, 0, 1) + .08 * (lb > .5)
    place('fx', buzz(2 * B, gate), 16, .9)
    place('fx', zap(), 16.15, .7, pan=-.4)
    # 05 glitch: zaps on the bursts (the beat-repeat lives in stutter())
    for a, b in ((18, 18.5), (18.98, 19.14), (19.45, 19.6), (19.82, 20)):
        for x in np.arange(a, b, 1 / 12):
            if rng.random() < .6:
                nn = int(.05 * SR)
                z = np.sign(np.sin(2 * np.pi * rng.uniform(200, 2200) * T(nn))) * env(nn, 0, .02) * .3
                place('fx', z, x, 1.0, pan=rng.uniform(-.7, .7))
    # 06 liquid: rising bloops as the letters fill
    for i, b in enumerate(np.linspace(20.0, 20.8, 9)):
        place('fx', bloop(300 + 90 * i, 900 + 160 * i), b, .6, pan=rng.uniform(-.6, .6))
    place('fx', bloop(1200, 400, .3), 21.1, .5)
    # 07 clay: a squish for every letter that lands
    for k in range(11):
        place('fx', boing(220 * 2 ** ((k % 6) / 12 * 5)), 22 + .06 + k * .045, .5, pan=(k - 5) / 7)
    # 08 kinetic: whips + the hero punch
    place('fx', whoosh(B * .6), 24, .55, pan=-.6); place('fx', whoosh(B * .6), 24.2, .55, pan=.6)
    place('fx', impact(.45), 25, .6)
    # 09 pixel: chip blips per letter, coin, chiptune run
    pent = [0, 3, 5, 7, 10, 12, 15, 17, 19, 22, 24]
    for j in range(11):
        place('fx', square(hz(72 + pent[j]), .07), 26 + .08 + j * .045 + .1, .7)
    place('fx', coin(), 26.75, .8)
    for i, b in enumerate(np.arange(27, 28, .125)):
        place('fx', square(hz(74 + pent[(i * 2) % 8]), .1, .12), b, .6, pan=.3)
    # 10 pop art
    place('fx', pow_hit(), 28.05, .9); place('fx', whoosh(B * .4), 28.35, .5, pan=-.5)
    # 11 particles: sparkle shower, then the burst
    for _ in range(40):
        b = 30 + rng.uniform(0, 1.3)
        place('fx', blip(rng.uniform(2500, 6000)) * .4, b, .5, pan=rng.uniform(-.9, .9))
    place('fx', whoosh(B * .8), 31.5, .6); place('fx', sub_drop(.8, 70, 30), 31.6, .4)
    # 12 blueprint: pencil + ruler ticks
    place('fx', scribble(B * .9), 32.08, .8)
    for b in np.arange(32.5, 32.82, .04):
        place('fx', click(1.6), b, .35)
    # 13 holo: ascending chime glissando
    for k in range(9):
        place('fx', chime(hz(79 + pent[k]), 1.0, .25), 34 + k * .06, .45, pan=(k - 4) / 5)


def montage():
    for b in np.arange(34.5, 36, .5):
        place('drums', snare(), b, .3)
    roll = list(np.arange(36, 37.5, .5)) + list(np.arange(37.5, 38.5, .25)) + list(np.arange(38.5, 39.5, .125))
    for i, b in enumerate(roll):
        place('drums', snare(), b, .35 + .45 * i / len(roll))
    for c in MONT:
        place('drums', kick(1.3), c, 1.0); KICKS.append(c)
        place('fx', noise_burst(), c, .7, pan=rng.uniform(-.5, .5))
        place('fx', impact(.3), c, .5)
    for b in np.arange(36, 39.5, 1):
        place('bass', bass_note(ROOTS[0] - 12, B * .9, 400), b, 1.0)
    place('fx', riser(B * 3.5), 36, 1.0)
    place('fx', whoosh(B * .5, rev=True), 39.5, .9)
    place('fx', rev_crash(B * .5), 39.5, .6)


def finale():
    place('fx', impact(1.4), 40, 1.0); place('fx', braam(2.4, bright=1.3), 40, .95)
    place('fx', crash(3.0), 40, .55); place('fx', sub_drop(2.0), 40, .9)
    for k in range(5):
        place('fx', whoosh(B * .35), 40 + k * .05, .2, pan=(k - 2) / 2)
    for b, g in ((40, 1), (41, .9), (41.5, .8), (41.75, .9)):
        place('drums', kick(1.3), b, g); KICKS.append(b)
    place('drums', tom(120), 41.5, .8); place('drums', tom(90), 41.75, .9)
    place('fx', riser(B * .45), 41.55, .7)
    place('fx', whoosh(B * .45, rev=True), 41.55, .7)
    # the hero slam
    place('fx', impact(1.4), 42, 1.0); place('fx', braam(2.8, bright=1.4), 42, 1.0)
    place('fx', crash(3.0), 42, .5); place('fx', sub_drop(2.2), 42, .9)
    place('music', big_chord([38, 50, 57, 62, 65, 69, 74, 76], B * 4.1, 3600), 42, .5)
    place('music', big_chord([34, 46, 53, 58, 62, 65, 70], B * 1.05, 3200), 44, .45)
    place('music', big_chord([36, 48, 55, 60, 64, 67, 72], B * 1.05, 3400), 45, .45)
    for k in range(11):
        place('fx', click(1.1), 42 + k * .03 + .3, .3, pan=(k - 5) / 6)
    place('fx', shing(2400), 43.0, .8, pan=.2)
    tag = 'ONE NAME  ·  EVERY VIBE'
    for i, ch in enumerate(tag):
        if ch != ' ':
            place('fx', click(1.5), 43.05 + i * .035, .3, pan=(i / len(tag) - .5))
    place('fx', chime(2637, 1.6, .35), 43.6, .5, pan=.5)
    for b in (44, 45):
        place('drums', kick(1.2), b, .9); KICKS.append(b)
        place('drums', clap(), b + .5, .5)
    place('drums', tom(140), 45.5, .7); place('drums', tom(110), 45.75, .8)
    # last hit, ring out
    place('fx', impact(1.5), 46, 1.0); place('fx', braam(3.0, bright=1.5), 46, 1.0)
    place('fx', crash(3.5), 46, .55); place('fx', sub_drop(2.4, 80, 26), 46, .9)
    place('fx', shing(2800, 1.2), 46.05, .6, pan=-.3)
    place('music', big_chord([26, 38, 45, 50, 57, 62, 69, 74], B * 2.6, 5000, voices=7), 46, .6)


def sidechain(x):
    g = np.ones(N)
    n = int(.26 * SR)
    shape = 1 - .7 * np.exp(-T(n) / .08)
    for b in KICKS:
        i = int(b * B * SR)
        m = min(n, N - i)
        if m > 0:
            g[i:i + m] = np.minimum(g[i:i + m], shape[:m])
    return x * g


def stutter(x):
    """Beat-repeat + bitcrush under the datamosh style (beats 18-20)."""
    y = x.copy()

    def rep(b0, b1, size):
        i0, i1, L = int(b0 * B * SR), int(b1 * B * SR), int(size * B * SR)
        chunk = x[:, i0:i0 + L].copy()
        fade = np.minimum(1, np.minimum(np.arange(L), L - np.arange(L)) / 60)
        for i in range(i0, i1, L):
            m = min(L, i1 - i)
            y[:, i:i + m] = chunk[:, :m] * fade[:m]
    rep(18, 18.5, 1 / 8)
    rep(18.98, 19.14, 1 / 32)
    rep(19.45, 19.6, 1 / 16)
    rep(19.82, 20, 1 / 32)
    i0, i1 = int(18 * B * SR), int(20 * B * SR)
    seg = np.round(y[:, i0:i1] * 20) / 20
    y[:, i0:i1] = np.repeat(seg[:, ::3], 3, axis=1)[:, :i1 - i0]
    return y


def main():
    intro(); groove(); styles(); montage(); finale()
    mus = sidechain(BUS['bass'] * 2.2 + BUS['music'] * 1.9)
    mix = BUS['drums'] * .5 + mus
    mix = stutter(mix)
    g = np.ones(N)   # the breaths: silence before the drop and before the finale
    for a, b in ((7.42, 8.0), (39.5, 40.0)):
        g[int(a * B * SR):int(b * B * SR)] = 0.0
    mix *= g
    mix += BUS['fx'] * .5
    mix /= np.percentile(np.abs(mix), 99.7) + 1e-9   # glue: soft-clip only the transients
    mix = np.tanh(mix * 1.1)
    mix /= np.max(np.abs(mix)) + 1e-9
    mix *= 10 ** (-.8 / 20)
    fl = int(.6 * SR)
    mix[:, -fl:] *= np.linspace(1, 0, fl) ** 2
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    wavfile.write(os.path.join(HERE, 'out', 'audio.wav'), SR, (mix.T * 32767).astype(np.int16))
    print('wrote out/audio.wav', mix.shape)


if __name__ == '__main__':
    main()
