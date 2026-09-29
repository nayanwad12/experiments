"""Original 128 BPM soundtrack + UI/transition SFX, synthesised in numpy (no samples).

    python3 audio.py  ->  out/audio.wav   (48 kHz stereo, 30 s = 64 beats)

Cue beats mirror the timeline in reel.js (sections every 8 beats, prompts, hits).
"""

import os

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 48000
BPM = 128
B = 60 / BPM
BEATS = 64
DUR = BEATS * B
N = int(SR * DUR)
HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(11)

# keep in sync with PROMPTS / HITS in reel.js
PROMPTS = [(5.9, 8, 'make it pop'), (14.5, 16, 'make it kinetic'), (22.7, 24, 'make it geometric'),
           (30.5, 32, 'make it flow'), (38.5, 40, 'make it deep'), (46.5, 48, 'make it glitch'), (50.5, 52, 'make it hit')]
SECTIONS = [8, 16, 24, 32, 40, 48, 52, 56]
CUTS = [52, 52.5, 53, 53.5, 54, 54.5, 55, 55.25, 55.5]

# F minor: i - VI - III - VII  (Fm, Db, Ab, Eb), one chord per bar
CHORDS = [[53, 56, 60, 65], [49, 53, 56, 61], [48, 51, 56, 60], [51, 55, 58, 63]]
ROOTS = [41, 37, 44, 39]


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


# ---------------------------------------------------------------- arrangement
def drums():
    for b in range(64):
        in_groove = 8 <= b < 56
        half_time_liquid = 32 <= b < 36
        if in_groove and not (half_time_liquid and b % 2):
            place('drums', kick(), b, 1.0); KICKS.append(b)
        if 56 <= b < 63 and b % 2 == 0:
            place('drums', kick(), b, 1.0); KICKS.append(b)
        if b < 8 and b % 2 == 0 and b < 7:
            place('drums', filt(kick(.2), 'lp', 300), b, .55)
        if 8 <= b < 56 and b % 2 == 1 and not half_time_liquid:
            place('drums', clap(), b, .8)
        if 56 <= b < 62 and b % 4 == 2:
            place('drums', clap(), b, .7)
        # hats
        if 8 <= b < 56:
            place('drums', hat(open_=(b % 2 == 1 and 16 <= b < 24)), b + .5, .45, pan=.3)
            if 16 <= b < 24 or 40 <= b < 48:
                for s in (.25, .75):
                    place('drums', hat(), b + s, .22 + .1 * rng.random(), pan=-.3)
        if b < 8:
            for s in (0, .5):
                place('drums', click(1.4), b + s, .2, pan=.5 if s else -.5)
    # snare roll into the logo
    for b in np.arange(52, 54, .5):
        place('drums', snare(), b + .25, .35)
    for b in np.arange(54, 55, .25):
        place('drums', snare(), b, .4 + .1 * (b - 54))
    for b in np.arange(55, 55.75, .125):
        place('drums', snare(), b, .55 + .3 * (b - 55))


def bass():
    for b in range(8, 56):
        r = ROOTS[chord_at(b)]
        if 32 <= b < 36:
            if b % 2 == 0:
                place('bass', bass_note(r, B * 1.8, 500), b, .9)
            continue
        for s in (.25, .5, .75):
            place('bass', bass_note(r + (12 if (s == .75 and b % 4 == 3) else 0), B * .22, 1100), b + s, .8)
    for b in (56, 58, 60, 62):
        place('bass', bass_note(ROOTS[0] - 12, B * 1.9, 400) * 1.2, b, 1.0)


def music():
    # intro pad swelling in, then chords under everything
    for bar in range(16):
        b0 = bar * 4
        notes = CHORDS[bar % 4]
        if bar < 2:
            p = supersaw(notes, B * 4.2, 900 + bar * 700)
            fade = np.linspace(.2 + bar * .35, .55 + bar * .35, p.shape[1])
            place('music', p * fade, b0, .5)
        elif 8 <= bar < 10 or bar >= 14:
            place('music', supersaw(notes, B * 4.1, 2600), b0, .45)
        else:
            place('music', supersaw(notes, B * 4.1, 1200), b0, .22)
    # offbeat stabs in title + kinetic
    for b in range(8, 24):
        notes = [m + 12 for m in CHORDS[chord_at(b)]]
        st = supersaw(notes, .16, 4200)
        st *= env(st.shape[1], .002, .06)
        place('music', st, b + .5, .55)
    # liquid bubbles
    scale = [65, 68, 70, 72, 75, 77, 80, 84]
    for i, b in enumerate(np.arange(32, 40, .5)):
        m = scale[int(rng.random() * len(scale))]
        place('music', blip(hz(m)), b + (.25 if i % 3 == 2 else 0), .5, pan=rng.uniform(-.8, .8))
    # 3D arp
    for b in np.arange(40, 48, .25):
        ch = CHORDS[chord_at(b)]
        k = int(round((b - 40) * 4))
        m = ch[k % 4] + 12 * ((k // 4) % 2) + 12
        place('music', pluck(m, .22, 2500 + 2500 * ((b - 40) / 8)), b, .38, pan=.5 * np.sin(k * .7))
    # outro: big final chord + last hit
    big = supersaw([41, 53, 56, 60, 65, 68, 72], B * 8, 3000, detune=.18, voices=7)
    big *= np.minimum(1, np.linspace(1.4, 0, big.shape[1]))
    place('music', big, 56, .5)
    fin = supersaw([53, 60, 65, 68, 72, 77], B * 2, 5000, voices=7)
    fin *= env(fin.shape[1], .002, .5)
    place('music', fin, 62, .5)


def fx():
    for s in SECTIONS:
        place('fx', crash(), s, .55 if s in (8, 56) else .4)
        place('fx', whoosh(B * 1.0, rev=True), s - 1.0, .5)
    for s in (8, 56):
        place('fx', impact(), s, 1.0)
    place('fx', impact(.6), 62, 1.0)
    place('fx', crash(3.0), 62, .5)
    place('fx', riser(B * 3.7), 4.0, .9)
    place('fx', riser(B * 3.7), 52.0, .9)
    for b in (1, 3, 5):   # the easing ball sweeping across
        place('fx', whoosh(B * 1.6), b, .25)
    for b in range(24, 29):   # shape-grid wave pops
        for k in range(4):
            place('fx', pop(500 + 180 * k + 60 * (b - 24)), b + k * .09, .35, pan=(k - 1.5) / 2)
    for b in (28.8, 29.3, 29.8, 30.3, 30.8):   # morph steps
        place('fx', pop(900), b, .3)
    for b in range(40, 48):   # 3D morph shimmers
        place('fx', filt(whoosh(B * .6), 'hp', 2000), b, .3, pan=.4 if b % 2 else -.4)
    for b in np.arange(48, 52, 1 / 6):   # glitch zaps
        if rng.random() < .45:
            n = int(.06 * SR)
            z = np.sign(np.sin(2 * np.pi * rng.uniform(200, 1800) * T(n))) * env(n, 0, .02) * .25
            place('fx', z, b, 1.0, pan=rng.uniform(-.7, .7))
    for c in CUTS:
        place('fx', filt(ns(.08), 'hp', 2000) * env(int(.08 * SR), 0, .015) * .7, c, 1.0)
    # prompt typing + send
    for a, b, s in PROMPTS:
        L = len(s)
        for k in range(L):
            tb = a + .15 + (k + 1) / L * (b - a) * .6
            place('fx', click(.8 + .4 * rng.random()), tb, .55, pan=rng.uniform(-.2, .2))
        place('fx', pop(1400), b - .2, .5)
    # outro tagline typing (every other char) + final collapse into the dot
    tag = 'DIRECT THE VIBE.  LET AI DO THE KEYFRAMES.'
    for k in range(0, len(tag), 2):
        place('fx', click(1.2), 57.4 + (k + 1) / len(tag) * 1.2, .25)
    place('fx', whoosh(B * .9, rev=True), 62.9, .5)
    place('fx', blip(hz(89)), 63.5, .6)
    place('fx', blip(hz(84)), 0.0, .5)


def sidechain(x):
    g = np.ones(N)
    n = int(.3 * SR)
    shape = 1 - .75 * np.exp(-T(n) / .09)
    for b in KICKS:
        i = int(b * B * SR)
        m = min(n, N - i)
        g[i:i + m] = np.minimum(g[i:i + m], shape[:m])
    return x * g


def stutter(x):
    """Beat-repeat + bitcrush for the glitch section (beats 49-52)."""
    y = x.copy()
    def rep(b0, b1, size):
        i0, i1, L = int(b0 * B * SR), int(b1 * B * SR), int(size * B * SR)
        chunk = x[:, i0:i0 + L].copy()
        fade = np.minimum(1, np.minimum(np.arange(L), L - np.arange(L)) / 60)
        for i in range(i0, i1, L):
            m = min(L, i1 - i)
            y[:, i:i + m] = chunk[:, :m] * fade[:m]
    rep(49, 50, .25)
    rep(50, 51, .125)
    rep(51, 51.75, 1 / 16)
    i0, i1 = int(48 * B * SR), int(52 * B * SR)
    seg = y[:, i0:i1]
    seg = np.round(seg * 24) / 24
    step = 3
    seg = np.repeat(seg[:, ::step], step, axis=1)[:, :i1 - i0]
    y[:, i0:i1] = seg
    y[:, int(51.75 * B * SR):i1] *= 0.15
    return y


def main():
    drums(); bass(); music(); fx()
    d = BUS['drums']
    # liquid section: drums filtered down, then opening back up
    lp = np.vstack([filt(d[0], 'lp', 500), filt(d[1], 'lp', 500)])
    e = np.zeros(N)
    t = np.arange(N) / SR / B
    e = np.clip(np.where(t < 32, 0, np.where(t < 36, 1, 1 - (t - 36) / 3)), 0, 1)
    d = d * (1 - e) + lp * e
    mus = sidechain(BUS['bass'] * .85 + BUS['music'] * .7)
    mix = d * .8 + mus
    mix = stutter(mix)
    # drop-out right before the logo impact
    g = np.ones(N)
    g[int(55.75 * B * SR):int(56 * B * SR)] = 0.0
    mix *= g
    mix += BUS['fx'] * .8
    # master: gentle glue + limiter
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    mix /= np.max(np.abs(mix)) + 1e-9
    mix *= 10 ** (-1 / 20)
    fade = np.ones(N); fl = int(.25 * SR); fade[-fl:] = np.linspace(1, 0, fl)
    mix *= fade
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    wavfile.write(os.path.join(HERE, 'out', 'audio.wav'), SR, (mix.T * 32767).astype(np.int16))
    print('wrote out/audio.wav', mix.shape)


if __name__ == '__main__':
    main()
