"""Soundtrack for the faceless reel: cleaned narration + original music bed + SFX, all synthesised in numpy.

    python3 audio.py  ->  out/audio.wav   (48 kHz stereo, 39.5 s)

Cue times mirror W_ in reel.js (word onsets from work/words.json).
"""

import os
import subprocess

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 48000
DUR = 39.5
N = int(SR * DUR)
HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(5)

W = dict(fourteen=0.52, still=1.92, cuts=4.61, captions=5.66, keyframes=6.98, everywhere=7.90,
         so=9.28, stopped=9.61, meet=10.89, vibe=11.28, six=13.64, ugh=15.24,
         cutting=17.06, capt=18.00, zooms=19.07, sound=19.99, twelve=21.48, nice=22.67,
         type=23.97, hit=25.05, enter=25.30, posted=28.51, fewer=29.46, more=30.49, vibe2=31.84,
         oh=33.32, made=35.17, ai=35.73, comment=36.63, vibeW=37.42)


def T(n):
    return np.arange(n) / SR


def filt(x, kind, f, order=2):
    return sosfilt(butter(order, f, kind, fs=SR, output='sos'), x)


def env(n, a, d):
    t = T(n)
    e = np.exp(-t / d)
    return e * np.clip(t / a, 0, 1) if a > 0 else e


BUS = {k: np.zeros((2, N)) for k in ('music', 'fx')}


def place(bus, x, t, g=1.0, pan=0.0):
    i = int(round(t * SR))
    if x.ndim == 1:
        x = np.vstack([x * np.cos((pan + 1) * np.pi / 4), x * np.sin((pan + 1) * np.pi / 4)]) * 1.414
    if i < 0:
        x, i = x[:, -i:], 0
    x = x[:, :max(0, N - i)]
    BUS[bus][:, i:i + x.shape[1]] += g * x


# ------------------------------------------------------------------ voice
def voice():
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(HERE, 'work', 'narration.mp3'),
                          '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    v = np.frombuffer(raw, np.float32).astype(np.float64)
    v = filt(v, 'highpass', 85)
    v += 0.25 * filt(v, 'bandpass', [2500, 6000])          # a little presence
    # gentle 3:1 compression on a 30 ms RMS envelope
    e = np.sqrt(filt(v * v, 'lowpass', 30, 1).clip(1e-9))
    thr = 0.06
    g = np.where(e > thr, (e / thr) ** (1 / 3 - 1), 1.0)
    v = v * g
    v = v / np.abs(v).max() * 0.85
    out = np.zeros(N)
    out[:min(N, len(v))] = v[:N]
    return out


# ------------------------------------------------------------------ instruments
def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def pad(notes, dur, bright=1200):
    n = int(dur * SR)
    t = T(n)
    x = np.zeros(n)
    for m in notes:
        for det in (-0.08, 0.0, 0.07):
            f = hz(m + det)
            x += np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) + 0.35 * np.sin(4 * np.pi * f * t)
    x = filt(x, 'lowpass', bright)
    a = np.minimum(1, t / 0.25) * np.minimum(1, (dur - t) / 0.3).clip(0)
    return x * a / (len(notes) * 3)


def kick():
    n = int(.35 * SR)
    t = T(n)
    f = 45 + 90 * np.exp(-t / .035)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .002, .12)


def clap():
    n = int(.22 * SR)
    x = filt(rng.standard_normal(n), 'bandpass', [900, 3500]) * env(n, .001, .06)
    return x * 0.8


def hat(open_=False):
    n = int((.18 if open_ else .05) * SR)
    return filt(rng.standard_normal(n), 'highpass', 7000) * env(n, .001, .05 if open_ else .015) * .5


def pluck(m, dur=.35):
    n = int(dur * SR)
    t = T(n)
    f = hz(m)
    x = (np.sin(2 * np.pi * f * t) + .5 * np.sin(4 * np.pi * f * t) + .2 * np.sin(6 * np.pi * f * t))
    return filt(x, 'lowpass', 3500) * env(n, .003, .12) * .5


def bass(m, dur):
    n = int(dur * SR)
    t = T(n)
    f = hz(m)
    x = np.sin(2 * np.pi * f * t) + .3 * np.sin(4 * np.pi * f * t)
    return x * np.minimum(1, t / .01) * np.minimum(1, (dur - t) / .05).clip(0) * .6


# ------------------------------------------------------------------ music bed
def music():
    out = np.zeros((2, N))

    def put(x, t, g=1.0, pan=0.0):
        i = int(t * SR)
        if x.ndim == 1:
            x = np.vstack([x * np.cos((pan + 1) * np.pi / 4), x * np.sin((pan + 1) * np.pi / 4)]) * 1.414
        x = x[:, :max(0, N - i)]
        out[:, i:i + x.shape[1]] += g * x

    # act 1 (0 -> stopped): dark drone, rising a little as the mess builds
    d = pad([45, 52, 57, 59], W['so'] + .5, bright=700)
    d *= np.linspace(.55, 1.0, len(d))
    put(d, 0, .2)
    put(pad([33], W['so'] + .5, bright=200), 0, .25)
    # act 2 (meet -> oh): light groove, 100 BPM, F - C - Am - G
    B = 0.6
    t0 = W['meet']
    prog = [([53, 57, 60, 64], 41), ([52, 55, 60, 64], 36), ([52, 57, 60, 64], 33), ([50, 55, 59, 62], 31)]
    bar = 0
    while t0 + bar * 4 * B < W['oh'] + 1.0:
        tb = t0 + bar * 4 * B
        notes, root = prog[bar % 4]
        put(pad(notes, 4 * B + .3, 1800), tb, .38)
        for k in range(4):
            put(kick(), tb + k * B, .55 if k % 2 == 0 else .0)
            if k % 2:
                put(clap(), tb + k * B, .22, .1)
            put(hat(), tb + k * B + B / 2, .22, .3)
            put(bass(root, B * .9), tb + k * B, .32)
        for k in range(8):                      # arpeggio in 8ths
            m = notes[[0, 2, 1, 3, 2, 1, 3, 2][k]] + 12
            put(pluck(m), tb + k * B / 2, .18, -.35 + .1 * k)
        bar += 1
    return out


def tape_stop(x, t0, dur):
    """Slow the music to a stop at t0 over dur (pitch + speed drop), silence after."""
    i0, n = int(t0 * SR), int(dur * SR)
    rate = np.linspace(1, 0, n) ** 1.6
    pos = i0 + np.cumsum(rate)
    for c in range(2):
        seg = np.interp(pos, np.arange(x.shape[1]), x[c])
        x[c, i0:i0 + n] = seg * np.linspace(1, .4, n)
        x[c, i0 + n:] = 0
    return x


# ------------------------------------------------------------------ sfx
def tick(f=2600, d=.03):
    n = int(d * SR)
    return filt(rng.standard_normal(n), 'bandpass', [f * .7, f * 1.3]) * env(n, .0005, .006)


def ping(f, d=.6, a=.002):
    n = int(d * SR)
    t = T(n)
    return (np.sin(2 * np.pi * f * t) + .3 * np.sin(2 * np.pi * 2.01 * f * t)) * env(n, a, d / 4)


def whoosh(d=.5, lo=300, hi=3000, rev=False):
    n = int(d * SR)
    t = T(n) / d
    x = rng.standard_normal(n)
    x = filt(x, 'bandpass', [lo, hi])
    e = np.sin(np.pi * t) ** 2 * (t ** .6)
    if rev:
        e = t ** 2.5 * np.minimum(1, (1 - t) / .04)
    return x * e


def boom(d=.9):
    n = int(d * SR)
    t = T(n)
    f = 38 + 70 * np.exp(-t / .06)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .003, .3) + .2 * filt(rng.standard_normal(n), 'lowpass', 400) * env(n, .001, .08)


def sparkle(d=.7, n_=7, base=2400):
    out = np.zeros(int(d * SR))
    for k in range(n_):
        p = ping(base * (1 + .25 * k) * rng.uniform(.97, 1.03), .25)
        i = int(k * d / n_ * .7 * SR)
        out[i:i + len(p)] += p[:len(out) - i] * (1 - k / n_ / 1.5)
    return out


def sfx():
    for s in range(5):
        place('fx', tick(2200, .04), s + .02, .35)                      # clock ticks
    place('fx', tick(1500, .05), W['fourteen'], .7)                     # digit flips
    place('fx', ping(880, .25), W['fourteen'] + .02, .08)
    for k in range(140):                                                 # timeline flood
        t = W['still'] + .15 + k * .0095 + rng.uniform(0, .05)
        place('fx', tick(rng.uniform(1800, 4200), .02), t, .16, rng.uniform(-.7, .7))
    place('fx', whoosh(.55, 400, 4000), W['cuts'] - .12, .35, -.6)
    place('fx', whoosh(.55, 400, 4000), W['captions'] - .12, .35, .6)
    place('fx', whoosh(.6, 300, 3000), W['keyframes'] - .1, .3)
    place('fx', whoosh(1.1, 200, 2500), W['everywhere'] - .2, .4)
    place('fx', whoosh(.7, 200, 5000, rev=True), W['so'] + .05, .45)     # suck into the dot
    place('fx', boom(.6), W['so'] + .72, .55)
    place('fx', boom(1.2), W['meet'] - .02, .7)                          # reveal
    place('fx', whoosh(.5, 1000, 8000), W['meet'] - .1, .25)
    place('fx', sparkle(.8, 6, 1760), W['vibe'], .22)                    # logo
    for k in range(18):                                                  # count up to 6h
        place('fx', tick(3000, .02), W['six'] + k * .035, .25)
    place('fx', ping(196, .5), W['ugh'], .25)                            # ugh
    place('fx', ping(147, .6), W['ugh'] + .08, .2)
    for t in (W['cutting'], W['capt'], W['zooms'], W['sound'] + .1):     # deductions
        place('fx', whoosh(.25, 2000, 9000), t - .03, .3)
        place('fx', ping(660, .3), t + .1, .12)
        for k in range(7):
            place('fx', tick(2600, .02), t + .2 + k * .05, .18)
    place('fx', ping(784, .7), W['twelve'], .22)                         # 12 minutes
    place('fx', ping(1175, .9), W['twelve'] + .12, .18)
    place('fx', sparkle(.6, 5, 2600), W['nice'], .2)
    for k in range(44):                                                  # typing
        t = W['type'] - .05 + k * (W['hit'] - W['type'] - .03) / 44
        place('fx', tick(rng.uniform(1200, 2200), .03), t, .3, rng.uniform(-.2, .2))
    place('fx', tick(900, .05), W['enter'], .7)
    place('fx', ping(523, .4), W['enter'] + .02, .2)
    place('fx', whoosh(.6, 300, 4000), W['enter'] + .4, .3)
    place('fx', ping(1047, .5), W['posted'], .25)                        # notification
    place('fx', ping(1568, .7), W['posted'] + .13, .22)
    for k in range(9):
        place('fx', ping(rng.uniform(1300, 2200), .15), W['posted'] + .3 + k * .14, .08, rng.uniform(-.5, .5))
    place('fx', boom(.5), W['fewer'] - .02, .35)
    place('fx', boom(.5), W['more'] - .02, .35)
    place('fx', sparkle(.8, 6, 1760), W['vibe2'], .22)
    place('fx', whoosh(.6, 200, 2000), W['oh'], .35)
    place('fx', whoosh(.5, 400, 5000), W['made'] - .1, .25)
    place('fx', sparkle(.7, 6, 2200), W['ai'], .2)
    place('fx', ping(659, .4), W['comment'] - .02, .2)
    for k in range(4):
        place('fx', tick(1600, .03), W['vibeW'] + k * .085, .4)
    place('fx', sparkle(1.0, 9, 1980), W['vibeW'] + .3, .25)


# ------------------------------------------------------------------ mix
def main():
    v = voice()
    m = music()
    m = tape_stop(m, W['oh'], .45)
    # act 3 bed: soft pad that swells into the CTA
    i = int(W['oh'] * SR)
    tail = pad([45, 52, 57, 60, 64], DUR - W['oh'], bright=900)
    tail *= np.linspace(.2, 1, len(tail)) * np.minimum(1, (DUR - W['oh'] - T(len(tail))) / 1.2).clip(0)
    m[:, i:i + len(tail)] += .45 * tail
    # sidechain: music ducks under the voice
    e = filt(np.abs(v), 'lowpass', 6, 1)
    duck = 1 - .45 * np.clip(e / .08, 0, 1)
    m *= duck
    sfx()
    mix = .32 * m + .55 * BUS['fx'] + np.vstack([v, v]) * .9
    mix = np.tanh(mix * 1.1) / 1.1
    mix /= np.abs(mix).max() / .95
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    wavfile.write(os.path.join(HERE, 'out', 'audio.wav'), SR, (mix.T * 32767).astype(np.int16))
    print('-> out/audio.wav', round(N / SR, 2), 's')


if __name__ == '__main__':
    main()
