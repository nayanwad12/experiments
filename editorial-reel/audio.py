"""Soundtrack for "Same reel. Two editors.": cleaned narration + lo-fi bed + SFX, synthesised in numpy.

    python3 audio.py  ->  out/audio.wav   (48 kHz stereo, 35.8 s)

Cue times mirror T_ in reel.js (word onsets from work/words.json).
"""

import os
import subprocess

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 48000
DUR = 35.8
N = int(SR * DUR)
HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(8)

W = dict(two=1.04, e1a=2.27, e2a=4.29, e1b=6.29, drags=6.94, twoH=7.89, e2b=9.39, cut=10.62, pauses=11.02,
         e1c=12.09, key=13.01, capt=13.92, colour=14.70, export=15.47, crash=16.29, e2c=17.37, enter=18.25,
         six=19.07, posts=21.07, twelve=21.98, reel3=24.22, number=24.49, three=24.70, idea=25.48, same2=26.45,
         footage=26.81, only=27.54, diff=27.83, oneof=28.66, what=29.50, to=29.86, ask=29.96, for_=30.33,
         thats=30.98, vibe=31.39, comment=32.45, vibeW=32.81, and_=33.41, ill=33.57, show=33.67, you=33.83,
         how=33.99, sign=34.25)
SPLITS = [1.02, 2.22, 4.24, 6.24, 9.34, 12.04, 17.32, 18.99, 21.93, 25.43]


def T(n):
    return np.arange(n) / SR


def filt(x, kind, f, order=2):
    return sosfilt(butter(order, f, kind, fs=SR, output='sos'), x)


def env(n, a, d):
    t = T(n)
    e = np.exp(-t / d)
    return e * np.clip(t / a, 0, 1) if a > 0 else e


FX = np.zeros((2, N))


def place(buf, x, t, g=1.0, pan=0.0):
    i = int(round(t * SR))
    if x.ndim == 1:
        x = np.vstack([x * np.cos((pan + 1) * np.pi / 4), x * np.sin((pan + 1) * np.pi / 4)]) * 1.414
    if i < 0:
        x, i = x[:, -i:], 0
    x = x[:, :max(0, N - i)]
    buf[:, i:i + x.shape[1]] += g * x


# ------------------------------------------------------------------ voice
def voice():
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(HERE, 'work', 'narration.mp3'),
                          '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    v = np.frombuffer(raw, np.float32).astype(np.float64)
    v = filt(v, 'highpass', 80)
    v += 0.2 * filt(v, 'bandpass', [2500, 6000])
    e = np.sqrt(filt(v * v, 'lowpass', 30, 1).clip(1e-9))
    thr = 0.06
    v = v * np.where(e > thr, (e / thr) ** (1 / 3 - 1), 1.0)
    v = v / np.abs(v).max() * 0.85
    out = np.zeros(N)
    out[:min(N, len(v))] = v[:N]
    return out


# ------------------------------------------------------------------ instruments
def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def rhodes(notes, dur):
    n = int(dur * SR)
    t = T(n)
    x = np.zeros(n)
    for m in notes:
        f = hz(m)
        x += np.sin(2 * np.pi * f * t + .8 * np.sin(2 * np.pi * f * t) * np.exp(-t / .25)) * np.exp(-t / 1.6)
    x *= 1 + .25 * np.sin(2 * np.pi * 4.5 * t)            # tremolo
    x *= np.minimum(1, (dur - t) / .08).clip(0)
    return filt(x, 'lowpass', 2600) / len(notes)


def kick():
    n = int(.4 * SR)
    t = T(n)
    f = 48 + 80 * np.exp(-t / .04)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .002, .16)


def snare():
    n = int(.3 * SR)
    t = T(n)
    body = np.sin(2 * np.pi * 190 * t) * env(n, .001, .05)
    nz = filt(rng.standard_normal(n), 'bandpass', [1500, 6000]) * env(n, .001, .09)
    return filt(body * .6 + nz, 'lowpass', 7000) * .8


def hat():
    n = int(.06 * SR)
    return filt(rng.standard_normal(n), 'highpass', 7000) * env(n, .001, .018) * .5


def bass(m, dur):
    n = int(dur * SR)
    t = T(n)
    x = np.sin(2 * np.pi * hz(m) * t)
    return filt(np.tanh(2 * x), 'lowpass', 300) * np.minimum(1, t / .01) * np.minimum(1, (dur - t) / .05).clip(0) * .7


def crackle():
    x = np.zeros(N)
    idx = rng.integers(0, N, int(DUR * 35))
    x[idx] = rng.uniform(-1, 1, len(idx))
    x = filt(x, 'bandpass', [1000, 7000])
    hiss = filt(rng.standard_normal(N), 'bandpass', [2000, 9000]) * .015
    return x * .5 + hiss


def groove(t0, t1, out, gain=1.0, drums=True):
    """88 BPM boom-bap: Fmaj7 - Em7 - Dm7 - Cmaj7, swung hats."""
    B = 60 / 88
    prog = [([53, 57, 60, 64], 41), ([52, 55, 59, 62], 40), ([50, 53, 57, 60], 38), ([48, 52, 55, 59], 36)]
    bar = 0
    while t0 + bar * 4 * B < t1:
        tb = t0 + bar * 4 * B
        notes, root = prog[bar % 4]
        place(out, rhodes(notes, 4 * B), tb, .5 * gain)
        place(out, bass(root, 1.6 * B), tb, .45 * gain)
        place(out, bass(root, .9 * B), tb + 2.5 * B, .35 * gain)
        if drums:
            for k in range(4):
                if k in (0, 2):
                    place(out, kick(), tb + k * B + (.5 * B if k == 2 and bar % 2 else 0), .7 * gain)
                if k in (1, 3):
                    place(out, snare(), tb + k * B, .35 * gain)
                place(out, hat(), tb + k * B, .2 * gain, .3)
                place(out, hat(), tb + k * B + B * .62, .14 * gain, .3)       # swing
        bar += 1


def tape_stop(x, t0, dur):
    i0, n = int(t0 * SR), int(dur * SR)
    pos = i0 + np.cumsum(np.linspace(1, 0, n) ** 1.6)
    for c in range(2):
        seg = np.interp(pos, np.arange(x.shape[1]), x[c])
        x[c, i0:i0 + n] = seg * np.linspace(1, .3, n)
    return x


def music():
    out = np.zeros((2, N))
    groove(0.0, W['crash'] + .6, out)
    out = tape_stop(out, W['crash'], .5)
    out[:, int((W['crash'] + .5) * SR):] = 0
    groove(W['enter'], W['only'] + 1.0, out)
    i = int(W['only'] * SR)
    out[:, i:] *= np.r_[np.linspace(1, 0, int(.3 * SR)), np.zeros(N - i - int(.3 * SR))]
    place(out, rhodes([50, 53, 57, 60, 64], 2.0), W['only'], .35)                 # suspended chord under the question
    groove(W['what'], W['sign'] + .1, out)
    j = int(W['sign'] * SR)
    out[:, j:] = 0
    place(out, rhodes([41, 53, 57, 60, 64, 67], 1.6), W['sign'], .55)            # final Fmaj9
    return out


# ------------------------------------------------------------------ sfx
def tick(f=2600, d=.03):
    n = int(d * SR)
    return filt(rng.standard_normal(n), 'bandpass', [f * .7, f * 1.3]) * env(n, .0005, .006)


def ping(f, d=.6):
    n = int(d * SR)
    t = T(n)
    return (np.sin(2 * np.pi * f * t) + .3 * np.sin(2 * np.pi * 2.01 * f * t)) * env(n, .002, d / 4)


def swish(d=.4, lo=500, hi=6000):
    n = int(d * SR)
    t = T(n) / d
    return filt(rng.standard_normal(n), 'bandpass', [lo, hi]) * np.sin(np.pi * t) ** 2 * t ** .5


def thump(d=.35):
    n = int(d * SR)
    t = T(n)
    f = 60 + 90 * np.exp(-t / .03)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .002, .07)


def boom(d=1.0):
    n = int(d * SR)
    t = T(n)
    f = 36 + 70 * np.exp(-t / .07)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .003, .35) + .25 * filt(rng.standard_normal(n), 'lowpass', 500) * env(n, .001, .1)


def glitch(d=.5):
    n = int(d * SR)
    x = rng.standard_normal(n)
    x = np.round(x * 3) / 3                                         # crushed
    gate = (np.floor(T(n) * 40) % 3 != 0).astype(float)
    return filt(x * gate, 'bandpass', [300, 5000]) * env(n, .001, d / 2)


def shutter():
    a = tick(3500, .03)
    out = np.zeros(int(.12 * SR))
    out[:len(a)] += a
    out[int(.06 * SR):int(.06 * SR) + len(a)] += a * .8
    return out


def scribble(d):
    n = int(d * SR)
    t = T(n)
    x = filt(rng.standard_normal(n), 'bandpass', [1800, 5000])
    am = .5 + .5 * np.sin(2 * np.pi * (6 + 3 * np.sin(2 * np.pi * .7 * t)) * t)
    return x * am * np.minimum(1, t / .05) * np.minimum(1, (d - t) / .2).clip(0)


def sfx():
    for s in SPLITS:
        place(FX, swish(.45), s, .3, rng.uniform(-.5, .5))
    place(FX, thump(), 0.0, .5)
    place(FX, swish(.8, 300, 3000), 0.05, .25)                        # reel rolls in
    place(FX, thump(), W['e1a'] + .2, .35)                            # computer lands
    place(FX, ping(990, .3), W['e2a'] + 1.0, .12)                     # bubble
    for k in range(60):                                               # clips raining
        place(FX, tick(rng.uniform(1200, 3500), .03), W['drags'] - .05 + k * .022 + rng.uniform(0, .1), .22, rng.uniform(-.6, .6))
    for k in range(20):
        place(FX, tick(3000, .02), W['twoH'] + k * .034, .2)
    for k in range(14):                                               # typing "cut my pauses."
        place(FX, tick(rng.uniform(1300, 2200), .03), W['cut'] - .05 + k * .065, .3, .4)
    for t in (W['key'], W['capt'], W['colour'], W['export']):
        place(FX, thump(), t - .03, .45)
    for k in range(8):
        place(FX, tick(2400, .02), W['export'] + .15 + k * .1, .15)
    place(FX, glitch(.6), W['crash'] - .02, .5)                       # crash
    place(FX, boom(1.2), W['crash'], .7)
    place(FX, filt(rng.standard_normal(int(.5 * SR)), 'highpass', 3000) * env(int(.5 * SR), .001, .12), W['crash'] + .02, .3)
    place(FX, tick(800, .06), W['enter'] - .02, .9)                   # enter clack
    place(FX, boom(1.0), W['enter'], .6)
    for k in range(26):                                               # six hours on the clock
        place(FX, tick(2200, .03), W['six'] + k * .042, .22)
    place(FX, ping(660, .4), W['posts'], .15)
    place(FX, ping(784, .5), W['twelve'], .12)
    for t in (W['reel3'], W['number'], W['three']):
        place(FX, swish(.2, 2000, 9000), t - .06, .3)
        place(FX, thump(.2), t, .25)
    place(FX, shutter(), W['idea'] - .02, .5)
    place(FX, shutter(), W['same2'] - .02, .5)
    place(FX, ping(1047, .5), W['footage'] + .1, .15)
    place(FX, ping(587, 1.2), W['diff'] + .3, .15)
    for t in (W['what'], W['to'], W['ask'], W['for_']):
        place(FX, thump(), t - .03, .5)
    place(FX, ping(1320, .4), W['for_'] + .05, .12)
    place(FX, thump(), W['vibe'] - .03, .5)
    for k in range(6):
        place(FX, ping(1760 * (1 + .25 * k), .25), W['vibe'] + .3 + k * .07, .06)
    place(FX, ping(880, .4), W['vibeW'] - .1, .15)
    for k in range(4):
        place(FX, tick(1600, .03), W['vibeW'] + k * .085, .4)
    for t in (W['and_'], W['ill'], W['show'], W['you'], W['how']):
        place(FX, thump(.2), t - .03, .25)
    place(FX, scribble(1.3), W['sign'] + .25, .18)


# ------------------------------------------------------------------ mix
def main():
    v = voice()
    m = music()
    c = crackle()
    e = filt(np.abs(v), 'lowpass', 6, 1)
    m *= 1 - .45 * np.clip(e / .08, 0, 1)
    sfx()
    mix = .17 * m + .5 * FX + np.vstack([v, v]) * .9 + .8 * np.vstack([c, c])
    mix = np.tanh(mix * 1.1) / 1.1
    mix /= np.abs(mix).max() / .95
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    wavfile.write(os.path.join(HERE, 'out', 'audio.wav'), SR, (mix.T * 32767).astype(np.int16))
    print('-> out/audio.wav', round(N / SR, 2), 's')


if __name__ == '__main__':
    main()
