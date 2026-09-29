"""Audio: voice cut to the EDL + cleaned up, an original synthesised music bed (ducked under the voice),
a cinematic drone for the documentary beat, and SFX locked to the words.

    python3 sound.py  ->  out/mix.wav
"""

import os
import subprocess

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, sosfiltfilt

from common import DUR, FFMPEG, OUT, OUT_DUR, RAW, SEGS, SPEED, WORK, ot, wt

SR = 44100
N = int(OUT_DUR * SR) + SR
rng = np.random.default_rng(11)


def T(n):
    return np.arange(n) / SR


def ns(d):
    return rng.standard_normal(int(d * SR))


def filt(x, kind, f, order=2):
    return sosfilt(butter(order, f, kind, fs=SR, output="sos"), x)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def place(buf, x, t, g=1.0):
    i = int(round(t * SR))
    if i >= len(buf) or i + len(x) <= 0:
        return
    if i < 0:
        x, i = x[-i:], 0
    x = x[: len(buf) - i]
    buf[i:i + len(x)] += g * x


def saw(f, n, ph=0.0):
    return 2 * ((f * T(n) + ph) % 1.0) - 1


# ------------------------------------------------------------------ voice
def voice():
    p = subprocess.run([FFMPEG, "-v", "error", "-i", RAW, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                       capture_output=True, check=True)
    src = np.frombuffer(p.stdout, np.int16).astype(np.float64) / 32768
    src = filt(src, "hp", 75, 4)
    out = np.zeros(int(DUR * SR) + SR)
    xf = int(0.012 * SR)
    pos = 0
    for a, b, _ in SEGS:
        x = src[int(a * SR):int(b * SR)].copy()
        ramp = np.linspace(0, 1, xf)
        x[:xf] *= ramp
        x[-xf:] *= ramp[::-1]
        out[pos:pos + len(x)] += x
        pos += len(x)
    # time-stretch edit time -> output time (ffmpeg atempo keeps the pitch)
    tmp_in, tmp_out = os.path.join(WORK, "_v_in.wav"), os.path.join(WORK, "_v_out.wav")
    wavfile.write(tmp_in, SR, (np.clip(out, -1, 1) * 32767).astype(np.int16))
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", tmp_in, "-af", f"atempo={SPEED}", tmp_out], check=True)
    out = wavfile.read(tmp_out)[1].astype(np.float64) / 32768
    os.remove(tmp_in); os.remove(tmp_out)
    out = np.pad(out, (0, max(0, N - len(out))))[:N]
    # gentle compression (RMS envelope follower) + presence lift
    env = np.sqrt(sosfiltfilt(butter(1, 12, "lp", fs=SR, output="sos"), out ** 2) + 1e-9)
    thr = 10 ** (-24 / 20)
    gain = np.where(env > thr, (env / thr) ** (1 / 3 - 1), 1.0)
    out = out * gain
    out = out + 0.25 * filt(out, "bandpass", [2500, 6000])
    out *= 10 ** (-3 / 20) / (np.max(np.abs(out)) + 1e-9)
    return out, env


# ------------------------------------------------------------------ instruments
def kick():
    n = int(0.42 * SR); t = T(n)
    f = 46 + 120 * np.exp(-t / 0.03)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(2.0 * np.sin(ph) * np.exp(-t / 0.18)) * 0.9


def snap():
    n = int(0.25 * SR); t = T(n)
    return filt(ns(0.25)[:n], "bandpass", [1200, 6000]) * np.exp(-t / 0.05) * 0.8


def hat(open_=False):
    d = 0.25 if open_ else 0.05
    n = int(d * SR)
    return filt(ns(d)[:n], "hp", 7500) * np.exp(-T(n) / (0.08 if open_ else 0.015))


def epiano(m, d):
    n = int(d * SR); t = T(n); f = hz(m)
    y = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.3) \
        + 0.12 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t / 0.1)
    return y * np.minimum(t / 0.005, 1) * np.exp(-t / 1.2) * np.minimum((d - t) / 0.05, 1)


def sub(m, d):
    n = int(d * SR); t = T(n)
    return np.sin(2 * np.pi * hz(m) * t) * np.minimum(t / 0.01, 1) * np.minimum((d - t) / 0.03, 1)


def pad(chord, d):
    n = int(d * SR); t = T(n)
    y = sum(saw(hz(m + det), n, rng.uniform()) for m in chord for det in (-0.08, 0.08))
    y = filt(y, "lp", 1400)
    return y * np.minimum(t / 0.8, 1) * np.minimum((d - t) / 0.8, 1) * 0.12


# ------------------------------------------------------------------ SFX
def whoosh(d=0.4, lo=400, hi=5000):
    n = int(d * SR)
    x = ns(d)[:n]
    out = np.zeros(n)
    seg = 24
    for s in range(seg):
        a, b = s * n // seg, (s + 1) * n // seg
        c = lo * (hi / lo) ** np.sin(np.pi * s / seg)
        out[a:b] = filt(x, "bandpass", [c * 0.6, min(c * 1.6, 20000)])[a:b]
    return out * np.sin(np.pi * T(n) / d) ** 2 * 1.4


def pop():
    n = int(0.12 * SR); t = T(n)
    f = 260 + 900 * np.exp(-t / 0.018)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / 0.04) * 0.9 + filt(ns(0.12)[:n], "hp", 3000) * np.exp(-t / 0.003) * 0.3


def sparkle():
    n = int(0.8 * SR); out = np.zeros(n)
    for i, m in enumerate([84, 88, 91, 96, 100, 103]):
        k = int(0.45 * SR); t = T(k)
        s = int(i * 0.04 * SR)
        out[s:s + k] += (np.sin(2 * np.pi * hz(m) * t) * np.exp(-t / 0.12))[: n - s]
    return out * 0.35


def boom(d=2.2):
    n = int(d * SR); t = T(n)
    f = 28 + 55 * np.exp(-t / 0.12)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(1.8 * np.sin(ph) * np.exp(-t / 0.7)) + filt(ns(d)[:n], "lp", 260) * np.exp(-t / 0.25) * 0.8


def braam(d=2.6):
    n = int(d * SR); t = T(n)
    y = sum(saw(hz(m) * (1 + 0.002 * v), n, rng.uniform()) for m in (33, 40, 45) for v in (-1, 1))
    cut = 180 + 1400 * np.exp(-t / 0.5)
    out = np.zeros(n)
    seg = 30
    for s in range(seg):
        a, b = s * n // seg, (s + 1) * n // seg
        out[a:b] = filt(y, "lp", float(cut[a]))[a:b]
    return np.tanh(out * 0.8) * np.minimum(t / 0.02, 1) * np.exp(-t / 1.1) + boom(d) * 0.6


def glass():
    d = 1.6
    n = int(d * SR); t = T(n)
    hit = filt(ns(d)[:n], "hp", 1500) * np.exp(-t / 0.05) * 1.2
    crack = np.zeros(n)
    k = 900
    idx = (rng.power(0.35, k) * n * 0.9).astype(int)
    crack[idx] = rng.uniform(-1, 1, k)
    crack = filt(np.convolve(crack, np.exp(-T(200) / 0.0008))[:n], "hp", 2500) * 2.0
    tinkle = np.zeros(n)
    for _ in range(38):
        s0 = int(rng.uniform(0.02, 1.2) * SR)
        f0 = rng.uniform(3000, 9000)
        m = int(0.25 * SR); tt = T(m)
        y = np.sin(2 * np.pi * f0 * tt) * np.exp(-tt / rng.uniform(0.02, 0.08)) * rng.uniform(0.1, 0.35)
        tinkle[s0:s0 + m] += y[: max(0, min(m, n - s0))]
    return hit + crack + tinkle + boom(1.6) * 0.7


def dust(d=1.1, rev=False):
    n = int(d * SR); t = T(n)
    x = ns(d)[:n]
    out = np.zeros(n)
    seg = 30
    for s in range(seg):
        a, b = s * n // seg, (s + 1) * n // seg
        c = 6000 * (600 / 6000) ** (s / seg)
        out[a:b] = filt(x, "bandpass", [c * 0.5, min(c * 1.8, 20000)])[a:b]
    grains = np.zeros(n)
    k = 1400
    grains[rng.integers(0, n, k)] = rng.uniform(-1, 1, k)
    grains = filt(np.convolve(grains, np.exp(-T(120) / 0.0006))[:n], "hp", 3000)
    y = (out * 0.8 + grains) * np.sin(np.pi * t / d) ** 1.5
    return y[::-1] if rev else y


def shimmer(d=1.0):
    n = int(d * SR); t = T(n); out = np.zeros(n)
    for m in (72, 76, 79, 84, 88, 91):
        out += np.sin(2 * np.pi * hz(m) * t + rng.uniform(0, 6)) * (0.6 + 0.4 * np.sin(2 * np.pi * 7 * t + m))
    return out / 6 * np.minimum(t / (d * 0.7), 1) * np.minimum((d - t) / 0.2, 1) * 0.6


def tick():
    n = int(0.03 * SR); t = T(n)
    return (np.sin(2 * np.pi * 2600 * t) * 0.6 + filt(ns(0.03)[:n], "hp", 5000) * 0.5) * np.exp(-t / 0.004)


def key():
    n = int(0.06 * SR); t = T(n)
    return (filt(ns(0.06)[:n], "hp", 2500) * np.exp(-t / 0.005) + np.sin(2 * np.pi * 1700 * t) * np.exp(-t / 0.01) * 0.5)


def ding():
    n = int(0.9 * SR); t = T(n)
    return (np.sin(2 * np.pi * hz(88) * t) + 0.5 * np.sin(2 * np.pi * hz(95) * t)) * np.exp(-t / 0.25) * 0.5


def riser(d, f0=200, f1=2400):
    n = int(d * SR); t = T(n); k = t / d
    f = f0 * (f1 / f0) ** (k ** 1.5)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * 0.3 + filt(ns(d)[:n], "bandpass", [800, 6000]) * 0.5) * k ** 2


def shutter():
    n = int(0.2 * SR); t = T(n)
    a = filt(ns(0.2)[:n], "bandpass", [1500, 7000])
    env = np.exp(-t / 0.01) + (t > 0.07) * np.exp(-np.clip(t - 0.07, 0, None) / 0.012)
    return a * env


# ------------------------------------------------------------------ music: 128 BPM, original, fully synthesised
BPM = 128
BEAT = 60 / BPM
BAR = BEAT * 4
PROG = [([57, 60, 64], 45), ([53, 57, 60], 41), ([48, 52, 55], 36), ([55, 59, 62], 43)]   # Am F C G


def clap():
    n = int(0.3 * SR); t = T(n)
    x = filt(ns(0.3)[:n], "bandpass", [900, 6000])
    env = 0.8 * np.exp(-t / 0.09)
    for d in (0.0, 0.01, 0.02):
        env += (t >= d) * np.exp(-np.clip(t - d, 0, None) / 0.006)
    return x * env * 0.8 + np.sin(2 * np.pi * 200 * t) * np.exp(-t / 0.04) * 0.4


def supersaw(m, d, voices=5, spread=0.16):
    n = int(d * SR)
    return sum(saw(hz(m + (v - (voices - 1) / 2) * spread), n, rng.uniform()) for v in range(voices)) / voices


def stab(chord, d=0.2):
    n = int(d * SR); t = T(n)
    y = sum(supersaw(m + 12, d) for m in chord)
    return filt(y, "lp", 5200) * np.minimum(t / 0.004, 1) * np.exp(-t / 0.09)


def bass(root, d):
    n = int(d * SR); t = T(n); f = hz(root)
    y = 0.55 * saw(f, n) + 0.8 * np.sin(2 * np.pi * f / 2 * t)
    return filt(y, "lp", 900) * np.minimum(t / 0.004, 1) * np.minimum((d - t) / 0.01, 1)


def crash(d=2.0):
    n = int(d * SR); t = T(n)
    return filt(ns(d)[:n], "hp", 3500) * np.exp(-t / 0.7) * 0.6


def taiko():
    n = int(1.0 * SR); t = T(n)
    f = 60 + 90 * np.exp(-t / 0.04)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(2.2 * np.sin(ph) * np.exp(-t / 0.35)) + filt(ns(1.0)[:n], "bandpass", [200, 1800]) * np.exp(-t / 0.03) * 0.8


def sweep_lp(x, t0, t1, f_lo, f_hi, t_edges):
    """Low-pass `x` between output times t0..t1 (the 'underwater' dip), with short ramps."""
    i0, i1 = int(t0 * SR), int(t1 * SR)
    if i1 <= i0:
        return x
    y = x.copy()
    muffled = filt(x[i0:i1], "lp", f_lo, 4)
    r = int(t_edges * SR)
    w = np.ones(i1 - i0)
    w[:r] = np.linspace(0, 1, r)
    w[-r:] = np.linspace(1, 0, r)
    y[i0:i1] = x[i0:i1] * (1 - w) + muffled * w
    return y


def music(cue):
    """Arrangement keyed to the edit (all output seconds):
    intro (filtered, tension) -> DROP on 'watch this' -> groove -> muffled while he's gone -> groove
    -> trailer percussion for the documentary -> DROP on 'that's crazy' -> build into 'AI' -> outro."""
    drums, hats, syn, low = np.zeros(N), np.zeros(N), np.zeros(N), np.zeros(N)
    t_end = OUT_DUR
    nb = int(t_end / BAR) + 2
    pump = np.ones(N)                 # kick sidechain envelope for synths/bass
    for b in range(nb):
        t0 = b * BAR
        chord, root = PROG[b % 4]
        for k in range(4):
            tb = t0 + k * BEAT
            if tb > t_end:
                break
            in_doc = cue["doc0"] - 0.05 < tb < cue["doc1"] - 0.05
            intro = tb < cue["drop1"] - 0.02
            if in_doc:
                continue
            # kick: four on the floor (intro: only 1 and 3)
            if not intro or k in (0, 2):
                place(drums, kick(), tb, 0.9 if not intro else 0.5)
                i = int(tb * SR)
                m = int(BEAT * SR * 0.9)
                seg = pump[i:i + m]
                seg *= 1 - 0.6 * np.exp(-T(len(seg)) / 0.08)
            if not intro:
                if k in (1, 3):
                    place(drums, clap(), tb, 0.45)
                for s16 in range(4):
                    place(hats, hat(), tb + s16 * BEAT / 4, 0.16 if s16 % 2 else 0.1)
                place(hats, hat(True), tb + BEAT / 2, 0.22)
                place(syn, stab(chord, 0.18), tb + BEAT / 2, 0.16)
                place(low, bass(root, BEAT * 0.45), tb + BEAT / 2, 0.42)
                place(low, bass(root, BEAT * 0.2), tb + BEAT * 0.75, 0.28)
            else:
                place(syn, pad(chord, BEAT * 1.05), tb, 0.8)
                place(low, sub(root - 12, BEAT), tb, 0.25)
    syn = syn * pump
    low = low * pump
    m = drums + hats + syn + low
    # documentary: trailer percussion + drone (half-time at 64 BPM)
    d0, d1 = cue["doc0"], cue["doc1"]
    tb = d0
    k = 0
    while tb < d1 - 0.1:
        place(m, taiko(), tb, 0.7 if k % 2 == 0 else 0.45)
        if k % 2 == 1:
            place(m, clap(), tb, 0.25)
        for s in range(4):
            place(m, tick(), tb + s * BEAT / 2, 0.18)
        tb += BEAT * 2
        k += 1
    dd = d1 - d0
    n = int(dd * SR); t = T(n)
    drone = sum(saw(hz(mm), n, rng.uniform()) for mm in (33, 40, 45))
    drone = filt(drone, "lp", 500) / 3 * np.minimum(t / 0.6, 1) * np.minimum((dd - t) / 0.15, 1)
    place(m, drone, d0, 0.35)
    # he's gone: whole track goes underwater until he's back
    m = sweep_lp(m, cue["gone0"], cue["gone1"], 450, 0, 0.25)
    # stop for a beat right before the glass hit -> the impact lands in silence
    i0, i1 = int((cue["impact"] - BEAT * 0.5) * SR), int(cue["impact"] * SR)
    m[i0:i1] *= np.linspace(1, 0.05, i1 - i0)
    i2 = int((cue["impact"] + BEAT * 1.0) * SR)
    m[i1:i2] *= np.linspace(0.05, 1, i2 - i1)
    fade = np.ones(N)
    i0, i1 = int((t_end - 0.9) * SR), int(t_end * SR)
    fade[i0:i1] = np.linspace(1, 0, i1 - i0)
    fade[i1:] = 0
    return m * fade


def build():
    v, env = voice()
    E = lambda word, after, end=False: ot(wt(word, after, end))  # noqa: E731  word -> output seconds
    cue = dict(drop1=E("Watch", 3), doc0=E("cinematic", 62), doc1=E("That's", 73), impact=E("camera.", 14.6, True) - 0.2,
               gone0=E("me.", 25.0) + 0.3, gone1=E("back.", 28.3))
    mus = music(cue)
    # sidechain ducking under the voice
    venv = np.sqrt(sosfiltfilt(butter(1, 5, "lp", fs=SR, output="sos"), v ** 2) + 1e-12)
    duck = 1 - 0.6 * np.clip(venv / 0.04, 0, 1)
    mus = mus * duck * 0.24

    fx = np.zeros(N)
    S = lambda x, t, g: place(fx, x, t, g)  # noqa: E731
    # hook
    S(riser(1.2, 150, 3000), 0.0, 0.25)
    for w_, a in (("Editing", 0), ("videos", 0.5), ("manually", 1)):
        S(whoosh(0.25, 800, 6000), E(w_, a) - 0.05, 0.3)
    S(boom(1.4), E("over.", 2), 0.6)
    S(crash(), E("Watch", 3), 0.45)
    S(whoosh(0.45, 300, 4000), E("Zoom", 4.5) - 0.1, 0.45)
    S(pop(), E("here", 7.7) + 0.05, 0.55)
    S(sparkle(), E("3D.", 8.8), 0.55)
    S(whoosh(0.3, 800, 7000), E("3D.", 8.8), 0.3)
    S(ding(), E("Nice.", 10), 0.25)
    S(whoosh(0.35, 600, 3000), E("grab", 11.5), 0.3)
    S(riser(1.1), E("throw", 13.0) - 0.2, 0.45)
    S(whoosh(0.7, 200, 7000), E("straight", 14.0), 0.7)
    S(glass(), cue["impact"], 0.85)
    S(dust(0.6), E("Okay.", 16.6) - 0.05, 0.3)
    S(pop(), E("Harder", 17.2), 0.35)
    S(whoosh(0.8, 200, 3000), E("Separate", 18.4), 0.5)
    for w_ in ("background,", "me,", "text."):
        S(pop(), E(w_, 21), 0.5)
    S(whoosh(0.5, 300, 5000), E("text.", 22.4, True) + 0.05, 0.4)
    S(dust(1.3), E("me.", 25.0), 0.7)
    S(shimmer(1.0), E("back.", 28.3) - 0.25, 0.5)
    S(dust(0.8, rev=True), E("back.", 28.3) - 0.1, 0.4)
    S(boom(1.0), E("back.", 28.3) + 0.55, 0.35)
    S(whoosh(0.6, 300, 4000), E("frame", 34.4), 0.5)
    S(whoosh(0.4, 500, 5000), E("left", 36.2), 0.35)
    for w_, a in (("anatomy", 37.5), ("hook,", 40.7), ("retention,", 41.8), ("share.", 43.9)):
        S(pop(), E(w_, a), 0.5)
    S(ding(), E("share.", 43.9) + 0.3, 0.35)
    S(whoosh(0.6, 300, 4000), E("Back", 47.0), 0.5)
    S(riser(1.0, 200, 3000), E("floating", 51.3) - 0.8, 0.3)
    S(whoosh(1.2, 150, 3000), E("floating", 51.3) - 0.2, 0.5)
    for k in range(5):
        S(pop(), E("floating", 51.3) + 0.12 * k, 0.25)
    S(sparkle(), E("Perfect!", 54.2), 0.5)
    S(whoosh(0.5, 400, 6000), E("Last", 56.8) - 0.15, 0.4)
    S(riser(1.4, 100, 1800), E("cinematic", 62) - 1.2, 0.35)
    S(braam(), cue["doc0"], 0.6)
    for k in range(5):
        S(dust(0.3), cue["doc0"] + 0.07 * k, 0.15)
    S(boom(), E("dramatic", 67.4), 0.65)
    S(riser(2.0, 90, 900), E("slow", 68.9), 0.2)
    S(braam(3.0), E("movie", 70.9), 0.55)
    S(crash(), cue["doc1"], 0.5)
    S(whoosh(0.4, 500, 6000), cue["doc1"] - 0.1, 0.45)
    S(boom(1.0), cue["doc1"], 0.5)
    S(whoosh(0.5, 300, 5000), E("all", 77.0) - 0.1, 0.45)
    for k in range(8):
        S(tick(), E("all", 77.0) + 0.05 + 0.05 * k, 0.3)
    S(riser(0.9), E("AI.", 79.3) - 0.9, 0.35)
    S(sparkle(), E("edited", 78.2), 0.5)
    S(boom(1.2), E("AI.", 79.3), 0.55)
    S(crash(), E("AI.", 79.3), 0.35)
    S(pop(), E("Comment", 80.5), 0.45)
    t_edit = E("EDIT", 81.0)
    for k in range(4):
        S(key(), t_edit + 0.08 * k, 0.45)
    S(pop(), E("how.", 82.6), 0.45)
    S(ding(), E("how.", 82.6) + 0.15, 0.3)
    fx = filt(fx, "hp", 30)

    mix = v * 1.0 + mus + fx * 0.75
    mix = np.tanh(mix * 1.15) / np.tanh(1.15)
    mix = mix[: int(OUT_DUR * SR)]
    fade = int(0.35 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix *= 10 ** (-1 / 20) / np.max(np.abs(mix))
    os.makedirs(OUT, exist_ok=True)
    wavfile.write(os.path.join(OUT, "mix.wav"), SR, (np.stack([mix, mix], 1) * 32767).astype(np.int16))
    act = np.convolve(v ** 2, np.ones(4410) / 4410, "same") > 1e-4
    db = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)  # noqa: E731
    print(f"while speaking: voice {db(v[act]):.1f} dB, music {db(mus[:len(act)][act]):.1f} dB; between lines: music {db(mus[:len(act)][~act]):.1f} dB")
    print("mix", len(mix) / SR, "s")


if __name__ == "__main__":
    build()
