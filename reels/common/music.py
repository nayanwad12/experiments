"""music: arranged, mixed and mastered original music in numpy (no samples, no stock, no Content ID).

    from music import Song, GENRES
    song = GENRES["future_bass"](dur=32.0, bpm=140, key="F#", marks={"drop": 12.0, "drop2": 24.0})
    stereo = song.master()          # (n, 2) float32 at SR; song.stems -> {name: (n, 2)}; song.kicks -> [t]

A Song is a set of tracks (stereo buffers) + sends (reverb, delay) + sidechain from the kick, then a master chain
(glue compression, soft-clip limiter, gentle width). Genre functions write the arrangement: they read the section
marks (seconds, snapped to bars) so drops, builds and breaks land where the picture needs them.
"""

import math

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt, sosfilt_zi

SR = 48000
NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
        "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
SCALES = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10], "dorian": [0, 2, 3, 5, 7, 9, 10],
          "phrygian": [0, 1, 3, 5, 7, 8, 10], "lydian": [0, 2, 4, 6, 7, 9, 11]}


def hz(m):
    return 440.0 * 2 ** ((np.asarray(m, float) - 69) / 12)


def tt(dur):
    return np.arange(int(round(dur * SR))) / SR


def db(x):
    return 10 ** (x / 20)


# ---------------------------------------------------------------- filters / dsp
def _sos(kind, f, order=2, q=None):
    nyq = SR / 2
    if kind == "bp":
        lo, hi = max(20, f[0]), min(nyq * 0.95, f[1])
        return butter(order, [lo / nyq, hi / nyq], btype="band", output="sos")
    return butter(order, min(max(f, 20), nyq * 0.95) / nyq, btype="low" if kind == "lp" else "high", output="sos")


def filt(x, kind, f, order=2):
    return sosfilt(_sos(kind, f, order), x, axis=0).astype(np.float32)


def sweep(x, f_of_t, kind="lp", block=256, order=2):
    """time-varying filter: f_of_t(array of block times in s) -> cutoffs."""
    x = np.asarray(x, np.float32)
    mono = x.ndim == 1
    X = x[:, None] if mono else x
    out = np.zeros_like(X)
    nb = (len(X) + block - 1) // block
    cuts = np.asarray(f_of_t(np.arange(nb) * block / SR), float)
    zi = None
    for i in range(nb):
        sos = _sos(kind, float(cuts[i]), order)
        if zi is None:
            zi = np.repeat(sosfilt_zi(sos)[:, :, None], X.shape[1], 2) * X[0][None, None, :]
        seg = X[i * block:(i + 1) * block]
        y, zi = sosfilt(sos, seg, axis=0, zi=zi)
        out[i * block:(i + 1) * block] = y
    return out[:, 0] if mono else out


def env(n, a=0.005, d=0.2, s=0.0, r=0.05, hold=None, curve=4.0):
    """ADSR-ish envelope of n samples; hold = sustain length in s (default: whatever is left)."""
    t = np.arange(n) / SR
    A = np.clip(t / max(a, 1e-4), 0, 1)
    dec = s + (1 - s) * np.exp(-curve * np.clip(t - a, 0, None) / max(d, 1e-4))
    e = np.where(t < a, A, dec)
    if r:
        rel_start = (hold if hold is not None else n / SR - r)
        e *= np.clip(1 - (t - rel_start) / r, 0, 1)
    return e.astype(np.float32)


def sat(x, drive=1.5):
    return (np.tanh(x * drive) / math.tanh(drive)).astype(np.float32)


RNG = np.random.default_rng(7)


def noise(n):
    return RNG.uniform(-1, 1, n).astype(np.float32)


def osc_saw(f, n, phase=None):
    ph = (np.cumsum(np.broadcast_to(f, (n,)) / SR) + (RNG.random() if phase is None else phase)) % 1.0
    # polyBLEP-lite: soften the discontinuity a little
    return (2 * ph - 1).astype(np.float32)


def osc_sq(f, n, duty=0.5):
    ph = (np.cumsum(np.broadcast_to(f, (n,)) / SR) + RNG.random()) % 1.0
    return np.where(ph < duty, 1.0, -1.0).astype(np.float32)


def osc_sin(f, n, phase=0.0):
    return np.sin(2 * np.pi * np.cumsum(np.broadcast_to(f, (n,)) / SR) + phase).astype(np.float32)


def pan2(x, p=0.0):
    a = (p + 1) * math.pi / 4
    return np.stack([x * math.cos(a) * 1.414, x * math.sin(a) * 1.414], 1).astype(np.float32)


def reverb_ir(dur=2.6, decay=2.6, damp=6500, pre=0.012, seed=3):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)).astype(np.float32) * np.exp(-decay * t)[:, None]
    # darker tail: progressively low-passed
    ir = 0.6 * filt(ir, "lp", damp) + 0.4 * filt(ir, "lp", damp / 3)
    ir[: int(pre * SR)] = 0
    for k, (dt, g) in enumerate(((0.017, 0.5), (0.023, 0.4), (0.031, 0.35), (0.041, 0.3))):  # early reflections
        ir[int(dt * SR), k % 2] += g
    return ir / np.sqrt((ir ** 2).sum(0, keepdims=True))


def conv_reverb(x, ir):
    return np.stack([fftconvolve(x[:, i], ir[:, i])[: len(x)] for i in range(2)], 1).astype(np.float32)


def pingpong(x, bpm, div=0.75, fb=0.38, n_taps=6, lp=5000):
    """tempo-synced ping-pong delay (div in beats)."""
    d = int(60 / bpm * div * SR)
    out = np.zeros_like(x)
    src = x.mean(1) if x.ndim == 2 else x
    src = filt(src, "lp", lp)
    for k in range(1, n_taps + 1):
        g = fb ** k
        sh = d * k
        if sh >= len(out):
            break
        out[sh:, k % 2] += src[: len(out) - sh] * g
    return out


def compressor(x, thresh_db=-14, ratio=3.0, attack=0.01, release=0.15, makeup_db=0.0, knee=6.0):
    mono = np.abs(x).max(1) if x.ndim == 2 else np.abs(x)
    step = 32
    lvl = mono[: len(mono) // step * step].reshape(-1, step).max(1)
    lvl_db = 20 * np.log10(lvl + 1e-9)
    over = lvl_db - thresh_db
    gr = np.where(over <= -knee / 2, 0, np.where(over >= knee / 2, over * (1 - 1 / ratio),
                                                 (over + knee / 2) ** 2 / (2 * knee) * (1 - 1 / ratio)))
    a_at, a_re = math.exp(-step / (attack * SR)), math.exp(-step / (release * SR))
    sm = np.zeros_like(gr)
    acc = 0.0
    for i, g in enumerate(gr):
        c = a_at if g > acc else a_re
        acc = c * acc + (1 - c) * g
        sm[i] = acc
    gain = db(-np.repeat(sm, step) + makeup_db)
    gain = np.pad(gain, (0, len(mono) - len(gain)), mode="edge")
    return (x * (gain[:, None] if x.ndim == 2 else gain)).astype(np.float32)


# ---------------------------------------------------------------- drums
def kick(tone=48, punch=1.0, decay=0.42, click=0.6, drive=2.2):
    n = int((decay + 0.15) * SR)
    t = np.arange(n) / SR
    f = tone + (190 * punch) * np.exp(-t * 32) + 40 * np.exp(-t * 6)
    body = osc_sin(f, n) * np.exp(-t / decay * 2.4)
    clk = filt(noise(n), "hp", 2500) * np.exp(-t * 450) * click
    return sat(body * 1.1 + clk, drive) * 0.95


def k808(note, dur, glide_from=None, glide=0.06, drive=1.8):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = hz(note) * np.ones(n)
    if glide_from is not None:
        f = hz(note) + (hz(glide_from) - hz(note)) * np.exp(-t / glide)
    f = f * (1 + 0.6 * np.exp(-t * 40))
    x = osc_sin(f, n) * env(n, 0.002, dur * 0.9, 0.6, 0.06, curve=1.5)
    return sat(x, drive) * 0.9


def snare(tone=190, snap=1.0, decay=0.18, body=0.6):
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    b = osc_sin(tone * (1 + 0.5 * np.exp(-t * 60)), n) * np.exp(-t * 28) * body
    nz = filt(noise(n), "bp", (1500, 9000)) * np.exp(-t / decay * 3) * snap
    return sat(b + nz * 0.9, 1.6) * 0.8


def clap(spread=0.012, decay=0.16):
    n = int(0.4 * SR)
    t = np.arange(n) / SR
    x = np.zeros(n, np.float32)
    for k in range(4):
        i = int(k * spread * SR / 1.7)
        burst = filt(noise(n - i), "bp", (900, 5000)) * np.exp(-(t[: n - i]) * (90 if k < 3 else 1 / decay * 2.2))
        x[i:] += burst * (0.8 if k < 3 else 1.0)
    return x * 0.6


def hat(open_=False, tone=8000, vel=1.0):
    d = 0.32 if open_ else 0.045
    n = int((d + 0.05) * SR)
    t = np.arange(n) / SR
    m = sum(osc_sq(tone * r / 8000 * 600, n) for r in (2, 3, 4.16, 5.43, 6.79, 8.21))  # metallic
    x = filt(0.5 * m / 6 + 0.7 * noise(n), "hp", 7000) * np.exp(-t / d * 3)
    return x * 0.35 * vel


def shaker(vel=1.0):
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    return filt(noise(n), "bp", (4000, 11000)) * np.sin(np.pi * np.clip(t / 0.08, 0, 1)) ** 2 * 0.25 * vel


def crash(dur=2.2):
    n = int(dur * SR)
    t = np.arange(n) / SR
    m = sum(osc_sq(f, n) for f in (420, 563, 691, 857, 1120))
    x = filt(0.4 * m / 5 + noise(n), "hp", 4500) * np.exp(-t * 2.2)
    return x * 0.3


def tom(note=45, decay=0.3):
    n = int(decay * 1.5 * SR)
    t = np.arange(n) / SR
    return osc_sin(hz(note) * (1 + 0.5 * np.exp(-t * 20)), n) * np.exp(-t / decay * 2.5) * 0.8


def taiko(note=36, decay=0.9):
    n = int(decay * 1.6 * SR)
    t = np.arange(n) / SR
    b = osc_sin(hz(note) * (1 + 0.8 * np.exp(-t * 25)), n) * np.exp(-t / decay * 2.2)
    sk = filt(noise(n), "bp", (150, 1200)) * np.exp(-t * 18)
    return sat(b + 0.5 * sk, 1.4)


def woodblock(note=79):
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    return (osc_sin(hz(note), n) + 0.4 * osc_sin(hz(note) * 2.7, n)) * np.exp(-t * 55) * 0.5


# ---------------------------------------------------------------- melodic
def supersaw(notes, dur, cutoff=3500, voices=7, detune=0.16, a=0.01, r=0.12, s=0.85, d=0.3, width=0.9):
    n = int(dur * SR)
    L = np.zeros(n, np.float32)
    R = np.zeros(n, np.float32)
    for m in notes:
        for v in range(voices):
            dt = (v - (voices - 1) / 2) / ((voices - 1) / 2 or 1) * detune
            x = osc_saw(hz(m + dt), n)
            p = (v / (voices - 1) * 2 - 1) * width if voices > 1 else 0
            L += x * (1 - p) * 0.5
            R += x * (1 + p) * 0.5
    st = np.stack([L, R], 1) / (len(notes) * voices) * 2.2
    st = filt(st, "lp", cutoff)
    return (st * env(n, a, d, s, r)[:, None]).astype(np.float32)


def pluck(note, dur=0.35, bright=4500, decay=0.18, detune=0.08):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = osc_saw(hz(note), n) + osc_saw(hz(note + detune), n) + 0.5 * osc_sq(hz(note - 12), n)
    x = sweep(x, lambda tb: 300 + bright * np.exp(-tb / decay * 2.5), "lp")
    return x * np.exp(-t / decay * 1.2) * 0.35


def epiano(note, dur=1.2, bright=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = hz(note)
    mod = 1.8 * bright * np.exp(-t * 4) * np.sin(2 * np.pi * f * t)
    x = np.sin(2 * np.pi * f * t + mod) + 0.25 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 6)
    trem = 1 + 0.08 * np.sin(2 * np.pi * 5 * t)
    return (x * np.exp(-t * 1.6) * trem * env(n, 0.003, 9, 1, 0.08) * 0.32).astype(np.float32)


def bell(note, dur=1.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = hz(note)
    x = np.sin(2 * np.pi * f * t + 2.2 * np.exp(-t * 3) * np.sin(2 * np.pi * f * 3.5 * t))
    return (x * np.exp(-t * 2.4) * 0.25).astype(np.float32)


def marimba(note, dur=0.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = hz(note)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 9) + 0.35 * np.sin(2 * np.pi * f * 3.93 * t) * np.exp(-t * 30) \
        + 0.15 * np.sin(2 * np.pi * f * 9.2 * t) * np.exp(-t * 60)
    return (x * 0.4).astype(np.float32)


def pizz(note, dur=0.5, bright=0.5):
    """karplus-strong plucked string."""
    n = int(dur * SR)
    p = max(2, int(SR / hz(note)))
    buf = filt(noise(p), "lp", 1500 + 6000 * bright)
    out = np.zeros(n, np.float32)
    reps = n // p + 1
    b = buf.copy()
    for i in range(reps):
        seg = b[: min(p, n - i * p)]
        out[i * p: i * p + len(seg)] = seg
        b = 0.996 * 0.5 * (b + np.roll(b, 1))
    return out * 0.5 * np.exp(-np.arange(n) / SR * 3)


def sub(note, dur, a=0.005, r=0.05):
    n = int(dur * SR)
    return osc_sin(hz(note), n) * env(n, a, 9, 1, r) * 0.7


def reese(note, dur, cutoff=900):
    n = int(dur * SR)
    x = osc_saw(hz(note - 0.12), n) + osc_saw(hz(note + 0.12), n) + 0.6 * osc_sin(hz(note - 12), n)
    return filt(x, "lp", cutoff) * env(n, 0.005, 9, 1, 0.04) * 0.4


def pad(notes, dur, cutoff=1600, a=0.6, r=0.8):
    st = supersaw(notes, dur, cutoff, voices=5, detune=0.1, a=a, r=r, s=1.0, d=9, width=1.0)
    return st * 0.8


def strings(notes, dur, cutoff=2600, a=0.08, r=0.15):
    n = int(dur * SR)
    t = np.arange(n) / SR
    L = np.zeros(n, np.float32)
    R = np.zeros(n, np.float32)
    for m in notes:
        for v in range(4):
            vib = 1 + 0.004 * np.sin(2 * np.pi * (5.2 + 0.3 * v) * t + v)
            x = osc_saw(hz(m + (v - 1.5) * 0.06) * vib, n)
            (L if v % 2 else R)[:] += x
    st = filt(np.stack([L, R], 1) / (len(notes) * 2), "lp", cutoff)
    st = filt(st, "hp", 120)
    return (st * env(n, a, 9, 1, r)[:, None] * 0.5).astype(np.float32)


def vox(note, dur, vowel="a", a=0.02, r=0.12):
    """formant 'vocal chop' synth (future-bass lead)."""
    F = {"a": (800, 1150, 2900), "o": (450, 800, 2830), "e": (400, 2000, 2550), "u": (350, 600, 2700),
         "i": (300, 2300, 3000)}[vowel]
    n = int(dur * SR)
    t = np.arange(n) / SR
    src = osc_saw(hz(note) * (1 + 0.003 * np.sin(2 * np.pi * 5.5 * t)), n)
    x = sum(filt(src, "bp", (f * 0.85, f * 1.15)) * g for f, g in zip(F, (1.0, 0.6, 0.3)))
    return x * env(n, a, 9, 1, r) * 0.9


def brass_braam(note, dur):
    n = int(dur * SR)
    x = sum(osc_saw(hz(m + d), n) for m in (note, note + 7, note - 12) for d in (-0.08, 0.08))
    x = sweep(x, lambda tb: 200 + 2600 * np.clip(tb / (dur * 0.5), 0, 1) ** 1.5 * np.exp(-tb / dur), "lp")
    return sat(x / 6, 2.5) * env(n, 0.05, 9, 1, 0.6) * 0.6


# ---------------------------------------------------------------- fx
def riser(dur, top=9000):
    n = int(dur * SR)
    t = np.arange(n) / SR
    k = t / dur
    ns = sweep(noise(n), lambda tb: 300 + top * (tb / dur) ** 2, "lp")
    tone = osc_saw(110 * 2 ** (3 * k), n) * 0.25
    return ((ns + filt(tone, "lp", 4000)) * k ** 2 * 0.6).astype(np.float32)


def downlifter(dur):
    return riser(dur)[::-1].copy() * 0.8


def impact(dur=2.5, sub_note=29):
    n = int(dur * SR)
    t = np.arange(n) / SR
    boom = osc_sin(hz(sub_note) * (1 + 2 * np.exp(-t * 12)), n) * np.exp(-t * 1.6)
    crack = filt(noise(n), "lp", 3000) * np.exp(-t * 7)
    return sat(boom + 0.5 * crack, 1.8) * 0.9


def reverse_crash(dur=1.5):
    return crash(dur)[::-1].copy() * 1.4


def snare_roll(dur, start_rate=4, end_rate=32, tone=200):
    n = int(dur * SR)
    out = np.zeros(n, np.float32)
    t = 0.0
    while t < dur:
        k = t / dur
        rate = start_rate * (end_rate / start_rate) ** k
        s = snare(tone, 0.9, 0.08, 0.3) * (0.3 + 0.7 * k)
        i = int(t * SR)
        seg = s[: n - i]
        out[i: i + len(seg)] += seg
        t += 1.0 / rate
    return out


# ---------------------------------------------------------------- song
# mix targets: RMS (dBFS, measured only where the track is playing) for each role, before the master chain
TARGET = {"cow": -15, "kick": -11, "snare": -15, "hats": -25, "bass": -12.5, "chords": -15, "pad": -20, "pluck": -19, "vox": -16,
          "lead": -17, "fx": -18, "perc": -20, "pizz": -17, "mar": -17.5, "tuba": -18, "glock": -25, "ost": -18,
          "pulse": -17, "tick": -30, "keys": -16, "bell": -25, "vinyl": -42}


def active_rms_db(x, win=0.05, floor_db=-50):
    m = x.mean(1) if x.ndim == 2 else x
    w = int(win * SR)
    k = len(m) // w
    if k == 0:
        return -120.0
    p = (m[: k * w].reshape(k, w) ** 2).mean(1)
    pdb = 10 * np.log10(p + 1e-12)
    act = pdb > max(floor_db, pdb.max() - 35)
    return float(10 * np.log10(p[act].mean() + 1e-12)) if act.any() else -120.0


class Song:
    def __init__(self, dur, bpm, key="C", scale="minor", seed=7):
        global RNG
        RNG = np.random.default_rng(seed)
        self.dur, self.bpm = dur, bpm
        self.beat = 60.0 / bpm
        self.bar = 4 * self.beat
        self.root = NOTE[key]
        self.scale = SCALES[scale]
        self.n = int((dur + 3.0) * SR)
        self.tracks = {}
        self.sends = {}          # track -> (reverb, delay)
        self.kicks = []
        self.sidechain = {}      # track -> depth (0..1)
        self.gains = {}
        self.offsets = {}        # fine-tune a track's level relative to its TARGET (dB)

    def level(self, name, offset_db):
        self.offsets[name] = offset_db
        return self

    # --- harmony helpers
    def chord(self, degree, octave=4, size=3, inv=0):
        idx = [degree - 1 + 2 * i for i in range(size)]
        out = []
        for i in idx:
            o, k = divmod(i, 7)
            out.append(12 * (octave + 1 + o) + self.root + self.scale[k])
        for _ in range(inv):
            out = out[1:] + [out[0] + 12]
        return out

    def deg(self, degree, octave=4):
        o, k = divmod(degree - 1, 7)
        return 12 * (octave + 1 + o) + self.root + self.scale[k]

    def at_bar(self, b, beat=0.0):
        return b * self.bar + beat * self.beat

    def snap(self, t):
        return round(t / self.bar) * self.bar

    # --- placement
    def track(self, name, rev=0.0, dly=0.0, sc=0.0, gain_db=0.0):
        if name not in self.tracks:
            self.tracks[name] = np.zeros((self.n, 2), np.float32)
        self.sends[name] = (rev, dly)
        self.sidechain[name] = sc
        self.gains[name] = gain_db
        return name

    def add(self, name, sig, t, gain_db=0.0, pan=0.0):
        if name not in self.tracks:
            self.track(name)
        sig = np.asarray(sig, np.float32)
        if sig.ndim == 1:
            sig = pan2(sig, pan)
        i = int(round(t * SR))
        if i < 0:
            sig, i = sig[-i:], 0
        if i >= self.n:
            return
        sig = sig[: self.n - i]
        self.tracks[name][i: i + len(sig)] += sig * db(gain_db)
        if name == "kick":
            self.kicks.append(t)

    def automate(self, name, fn):
        """multiply a track by fn(t_array) (volume automation) ."""
        t = np.arange(self.n) / SR
        self.tracks[name] *= np.asarray(fn(t), np.float32)[:, None]

    def filter_auto(self, name, f_of_t, kind="lp"):
        self.tracks[name] = sweep(self.tracks[name], f_of_t, kind)

    # --- mix
    def _sc_env(self, depth, release=None):
        g = np.ones(self.n, np.float32)
        rel = release or self.beat * 0.85
        ln = int(rel * SR)
        tt_ = np.arange(ln) / SR
        shape = 1 - depth * np.exp(-tt_ / (rel * 0.28)) * np.clip(tt_ / 0.004, 0, 1) ** 0.5
        shape[:int(0.004 * SR)] = 1 - depth
        for k in self.kicks:
            i = int(k * SR)
            seg = g[i: i + ln]
            np.minimum(seg, shape[: len(seg)], out=seg)
        return g

    def master(self, width=1.15, glue=True, out_db=-1.0):
        rev_bus = np.zeros((self.n, 2), np.float32)
        dly_bus = np.zeros((self.n, 2), np.float32)
        mix = np.zeros((self.n, 2), np.float32)
        self.stems = {}
        sc_cache = {}
        for name, x in self.tracks.items():
            if np.abs(x).max() == 0:
                continue
            target = TARGET.get(name, -18) + self.offsets.get(name, 0.0)
            x = x * db(target - active_rms_db(x))
            d = self.sidechain.get(name, 0)
            if d > 0:
                if d not in sc_cache:
                    sc_cache[d] = self._sc_env(d)
                x = x * sc_cache[d][:, None]
            r, dl = self.sends.get(name, (0, 0))
            if r:
                rev_bus += x * r
            if dl:
                dly_bus += x * dl
            self.stems[name] = x
            mix += x
        if np.abs(dly_bus).max() > 0:
            dl = pingpong(dly_bus, self.bpm)
            rev_bus += dl * 0.3
            mix += dl
        if np.abs(rev_bus).max() > 0:
            wet = conv_reverb(filt(rev_bus, "hp", 250), reverb_ir())
            if self.sidechain and self.kicks:
                wet *= self._sc_env(0.5)[:, None]
            mix += wet * 0.9
            self.stems["_reverb"] = wet * 0.9
        # master: low cut, width, glue, limiter
        mix = filt(mix, "hp", 28)
        m, s = (mix[:, 0] + mix[:, 1]) / 2, (mix[:, 0] - mix[:, 1]) / 2
        s = filt(s, "hp", 180) * width
        mix = np.stack([m + s, m - s], 1)
        pk = np.abs(mix).max() or 1
        mix = mix / pk * db(-6)
        if glue:
            mix = compressor(mix, -16, 2.0, 0.015, 0.2, 2.5)
        mix = sat(mix * db(4), 1.25)
        mix = mix / (np.abs(mix).max() or 1) * db(out_db)
        end = int(self.dur * SR)
        fade = int(0.04 * SR)
        mix = mix[:end]
        mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
        for k in self.stems:
            self.stems[k] = self.stems[k][:end]
        return mix.astype(np.float32)


# ---------------------------------------------------------------- drum patterns
def drums_trap(S, b0, b1, hats="16", snare_beat=2, kick_pattern=(0, 1.75, 2.5), roll_last=True, gain=0.0):
    """half-time trap: kicks per pattern, snare/clap on beat 3, hats 16ths with triplet rolls."""
    S.track("kick", sc=0, gain_db=gain)
    S.track("snare", rev=0.18, gain_db=gain - 2)
    S.track("hats", rev=0.05, gain_db=gain - 7)
    K, SN, CL = kick(46, 1.1, 0.5), snare(210, 1.1, 0.16), clap()
    for b in range(b0, b1):
        t0 = S.at_bar(b)
        for kp in kick_pattern:
            S.add("kick", K, t0 + kp * S.beat)
        S.add("snare", SN * 0.7 + np.pad(CL, (0, max(0, len(SN) - len(CL))))[: len(SN)], t0 + snare_beat * S.beat)
        step = S.beat / (4 if hats == "16" else 2)
        for i in range(int(4 * S.beat / step)):
            v = 0.55 + 0.45 * (i % 2 == 0)
            S.add("hats", hat(False, vel=v), t0 + i * step, pan=0.25)
        if roll_last and b % 2 == 1:
            for j in range(6):
                S.add("hats", hat(False, vel=0.6 + j * 0.06), t0 + 3 * S.beat + j * S.beat / 6, pan=0.25)


def drums_four(S, b0, b1, open_hat=True, clap_on=(1, 3), gain=0.0, ride=False):
    S.track("kick", gain_db=gain)
    S.track("snare", rev=0.15, gain_db=gain - 3)
    S.track("hats", rev=0.04, gain_db=gain - 8)
    K, CL = kick(50, 1.0, 0.38), clap()
    for b in range(b0, b1):
        t0 = S.at_bar(b)
        for i in range(4):
            S.add("kick", K, t0 + i * S.beat)
            if open_hat:
                S.add("hats", hat(True, vel=0.7), t0 + (i + 0.5) * S.beat, pan=-0.2)
            for j in range(4):
                if j != 2 or not open_hat:
                    S.add("hats", hat(False, vel=0.4 + 0.3 * (j % 2)), t0 + (i + j / 4) * S.beat, pan=0.3)
        for cb in clap_on:
            S.add("snare", CL, t0 + cb * S.beat)


def chop_melody(S, track, b0, b1, degrees, octave=5, vowel="a", rhythm=None, gain=0.0):
    """future-bass style vocal-chop lead: short formant notes on a syncopated rhythm."""
    rhythm = rhythm or [0, 0.75, 1.5, 2.0, 2.75, 3.5]
    S.track(track, rev=0.25, dly=0.18, sc=0.5, gain_db=gain)
    k = 0
    for b in range(b0, b1):
        for r in rhythm:
            d = degrees[k % len(degrees)]
            S.add(track, vox(S.deg(d, octave), S.beat * 0.45, "aeoui"[k % 2 * 2] if vowel == "mix" else vowel),
                  S.at_bar(b, r), pan=0.2 * math.sin(k))
            k += 1


# ---------------------------------------------------------------- genres
def _bars(S, t):
    return int(round(t / S.bar))


def future_bass(dur, bpm=140, key="F#", marks=None, seed=7, energy=1.0):
    """intro (filtered pads) -> build (snare roll + riser) -> DROP (supersaw chops, 808, trap drums) -> break -> drop2."""
    marks = marks or {}
    S = Song(dur, bpm, key, "major", seed)
    nb = _bars(S, dur) + 1
    drop = _bars(S, marks.get("drop", dur * 0.35))
    brk = _bars(S, marks.get("break", dur * 0.62))
    drop2 = _bars(S, marks.get("drop2", dur * 0.75))
    prog_ = [6, 4, 1, 5]
    S.track("pad", rev=0.35, sc=0.0, gain_db=-4)
    S.track("chords", rev=0.22, sc=0.75, gain_db=-1)
    S.track("bass", sc=0.0, gain_db=-1)
    S.track("pluck", rev=0.2, dly=0.25, sc=0.4, gain_db=-8)
    S.track("fx", rev=0.3, gain_db=-4)
    for b in range(nb):
        deg = prog_[b % 4]
        ch = S.chord(deg, 4, 4)
        in_drop = drop <= b < brk or b >= drop2
        if in_drop:
            # chopped supersaw stabs on a syncopated grid
            for r, ln in ((0, 0.6), (0.75, 0.5), (1.5, 0.4), (2.0, 0.9), (3.0, 0.4), (3.5, 0.45)):
                S.add("chords", supersaw(ch + [ch[0] + 12], S.beat * ln, 5200, 7, 0.18, 0.004, 0.06, 0.8, 0.25),
                      S.at_bar(b, r))
            bn = S.deg(deg, 1)
            S.add("bass", k808(bn, S.bar * 0.48, glide_from=None), S.at_bar(b, 0))
            S.add("bass", k808(bn, S.bar * 0.45, glide_from=bn + 5), S.at_bar(b, 2.0))
        else:
            S.add("pad", pad(ch, S.bar + 0.3, 1400 if b < drop else 2000), S.at_bar(b))
            if b >= 2:
                for i in range(8):
                    S.add("pluck", pluck(ch[i % 4] + 12 * (i // 4), S.beat * 0.6, 3800), S.at_bar(b, i / 2),
                          pan=0.3 * (1 if i % 2 else -1))
    # drums
    drums_trap(S, drop, brk)
    drums_trap(S, drop2, nb)
    if drop >= 2:
        for b in range(max(0, drop - 2), drop):           # pre-drop: claps on 2 & 4, hats speeding
            for i in range(8):
                S.add("hats", hat(False, vel=0.4 + 0.07 * i), S.at_bar(b, i / 2), pan=0.25)
    chop_melody(S, "vox", drop, brk, [3, 5, 6, 5, 3, 2, 1, 2], 5, "mix", gain=-3)
    chop_melody(S, "vox", drop2, nb, [5, 6, 8, 6, 5, 3, 2, 3], 5, "mix", gain=-3)
    # transitions
    for d in (drop, drop2):
        td = S.at_bar(d)
        if td - S.bar * 2 > 0:
            S.add("fx", riser(S.bar * 2), td - S.bar * 2, -3)
            S.add("snare", snare_roll(S.bar, 4, 32), td - S.bar, -6)
        S.add("fx", impact(), td, -2)
        S.add("fx", crash(), td, -6)
    S.add("fx", downlifter(S.bar), S.at_bar(brk), -6)
    S.filter_auto("pad", lambda tb: np.where(tb < S.at_bar(drop), 500 + 6000 * np.clip(tb / max(S.at_bar(drop), 1e-3),
                                                                                        0, 1) ** 2, 12000))
    return S


def synthwave(dur, bpm=112, key="A", marks=None, seed=5):
    """driving 16th bass arp, gated reverb snare, retro poly chords, four-on-floor."""
    marks = marks or {}
    S = Song(dur, bpm, key, "minor", seed)
    nb = _bars(S, dur) + 1
    full = _bars(S, marks.get("full", S.bar * 2))
    prog_ = [1, 6, 3, 7]
    S.track("bass", sc=0.45, gain_db=-2)
    S.track("chords", rev=0.3, sc=0.5, gain_db=-5)
    S.track("lead", rev=0.25, dly=0.3, gain_db=-7)
    S.track("fx", rev=0.3, gain_db=-4)
    for b in range(nb):
        deg = prog_[b % 4]
        root = S.deg(deg, 2)
        for i in range(16):
            n_ = root + (12 if i % 4 == 2 else 0)
            S.add("bass", filt(osc_saw(hz(n_), int(S.beat / 4 * 0.9 * SR)), "lp", 1100 + 500 * (i % 2)) *
                  env(int(S.beat / 4 * 0.9 * SR), 0.002, 0.08, 0.3, 0.02) * 0.5, S.at_bar(b, i / 4))
        S.add("chords", supersaw(S.chord(deg, 4, 4), S.bar * 0.95, 2600, 5, 0.12, 0.02, 0.3, 0.8, 0.5), S.at_bar(b))
        if b >= full:
            mel = [5, 3, 2, 3, 5, 6, 5, 3]
            for i in range(4):
                S.add("lead", pluck(S.deg(mel[(b * 4 + i) % 8], 5), S.beat * 0.9, 5000, 0.35), S.at_bar(b, i),
                      pan=0.1)
    drums_four(S, full, nb, open_hat=True, clap_on=(1, 3))
    # gated-reverb snare feel: extra short bright reverb hit
    for b in range(full, nb):
        for cb in (1, 3):
            S.add("snare", snare(180, 1.2, 0.12, 0.8), S.at_bar(b, cb), -2)
    S.add("fx", riser(S.bar * 1.5), max(0, S.at_bar(full) - S.bar * 1.5), -4)
    S.add("fx", impact(), S.at_bar(full), -4)
    S.add("fx", crash(), S.at_bar(full), -6)
    return S


def whimsical(dur, bpm=104, key="D", marks=None, seed=9):
    """claymation score: pizzicato ostinato, marimba melody, tuba-ish bass, woodblock + shaker, glock sparkles."""
    marks = marks or {}
    S = Song(dur, bpm, key, "major", seed)
    nb = _bars(S, dur) + 1
    prog_ = [1, 4, 5, 1, 6, 4, 2, 5]
    S.track("pizz", rev=0.2, gain_db=-3)
    S.track("mar", rev=0.25, dly=0.1, gain_db=-5)
    S.track("tuba", gain_db=-3)
    S.track("perc", rev=0.1, gain_db=-9)
    S.track("glock", rev=0.35, gain_db=-12)
    mel = [3, 5, 6, 5, 3, 1, 2, 3, 5, 8, 7, 5, 6, 5, 3, 2]
    for b in range(nb):
        deg = prog_[b % 8]
        ch = S.chord(deg, 4)
        for i in range(8):
            if i % 2 == 0 or b % 2:
                S.add("pizz", pizz(ch[i % 3] + (12 if i in (3, 7) else 0), 0.4, 0.6), S.at_bar(b, i / 2),
                      pan=0.3 * math.sin(i))
        S.add("tuba", filt(osc_sq(hz(S.deg(deg, 2)), int(S.beat * 0.9 * SR), 0.4), "lp", 600) *
              env(int(S.beat * 0.9 * SR), 0.01, 0.4, 0.6, 0.05) * 0.4, S.at_bar(b, 0))
        S.add("tuba", filt(osc_sq(hz(S.deg(deg, 2) + 7), int(S.beat * 0.9 * SR), 0.4), "lp", 600) *
              env(int(S.beat * 0.9 * SR), 0.01, 0.4, 0.6, 0.05) * 0.35, S.at_bar(b, 2))
        if b >= 2:
            for i in range(4):
                S.add("mar", marimba(S.deg(mel[(b * 4 + i) % 16], 5)), S.at_bar(b, i + (0.5 if i == 3 else 0)))
        for i in range(8):
            S.add("perc", shaker(0.6 + 0.4 * (i % 2)), S.at_bar(b, i / 2 + 0.03))
        S.add("perc", woodblock(84), S.at_bar(b, 1))
        S.add("perc", woodblock(79), S.at_bar(b, 3))
        if b % 4 == 3:
            for j, d in enumerate((8, 10, 12)):
                S.add("glock", bell(S.deg(d, 5), 1.2), S.at_bar(b, 2 + j * 0.5))
    return S


def cinematic(dur, bpm=90, key="D", marks=None, seed=4):
    """documentary tension: string ostinato, pulse sub, taikos, braams on hits, ticking, risers."""
    marks = marks or {}
    S = Song(dur, bpm, key, "minor", seed)
    nb = _bars(S, dur) + 1
    hits = marks.get("hits", [])
    calm = marks.get("calm", [])
    S.track("ost", rev=0.3, gain_db=-6)
    S.track("pad", rev=0.4, gain_db=-8)
    S.track("pulse", gain_db=-5)
    S.track("perc", rev=0.25, gain_db=-4)
    S.track("tick", rev=0.1, gain_db=-14)
    S.track("fx", rev=0.35, gain_db=-3)
    prog_ = [1, 1, 6, 6, 3, 3, 7, 5]
    for b in range(nb):
        deg = prog_[b % 8]
        ch = S.chord(deg, 3)
        S.add("pad", strings(S.chord(deg, 4), S.bar + 0.3, 1800, 0.4, 0.5), S.at_bar(b))
        for i in range(8):
            n_ = ch[[0, 1, 2, 1][i % 4]] + 12
            S.add("ost", strings([n_], S.beat / 2 * 0.8, 3200, 0.005, 0.05), S.at_bar(b, i / 2),
                  pan=0.3 * (1 if i % 2 else -1))
        for i in range(4):
            S.add("pulse", sub(S.deg(deg, 1), S.beat * 0.5), S.at_bar(b, i))
            S.add("tick", woodblock(96), S.at_bar(b, i))
            S.add("tick", woodblock(91), S.at_bar(b, i + 0.5), -6)
        if b % 2 == 0:
            S.add("perc", taiko(38), S.at_bar(b, 0))
            S.add("perc", taiko(43, 0.5), S.at_bar(b, 2.5), -4)
            S.add("perc", taiko(43, 0.5), S.at_bar(b, 3), -3)
    for h in hits:
        S.add("fx", brass_braam(S.deg(1, 2), 3.0), h, -2)
        S.add("fx", impact(3.0, 26), h, 0)
        if h - 2.0 > 0:
            S.add("fx", riser(2.0), h - 2.0, -5)
    # duck everything for 'calm' windows (t0, t1)
    if calm:
        def g(t):
            out = np.ones_like(t)
            for a, b_ in calm:
                out *= 1 - 0.85 * np.clip(np.minimum((t - a) / 0.4, (b_ - t) / 0.6), 0, 1)
            return out
        for tr in ("ost", "pulse", "perc", "tick", "pad"):
            S.automate(tr, g)
    return S


def lofi_trap(dur, bpm=88, key="Eb", marks=None, seed=3):
    """tight hip-hop: dusty e-piano 7ths, 808 slides, crisp trap hats, vinyl crackle."""
    marks = marks or {}
    S = Song(dur, bpm, key, "minor", seed)
    nb = _bars(S, dur) + 1
    beat_in = _bars(S, marks.get("beat", S.bar))
    prog_ = [1, 6, 4, 5]
    S.track("keys", rev=0.25, sc=0.3, gain_db=-4)
    S.track("bass", gain_db=-1)
    S.track("vinyl", gain_db=-24)
    S.track("bell", rev=0.3, dly=0.25, gain_db=-12)
    for b in range(nb):
        deg = prog_[b % 4]
        ch = S.chord(deg, 4, 4)
        for j, m in enumerate(ch):
            S.add("keys", epiano(m, S.bar * 0.95), S.at_bar(b, 0) + j * 0.012)
        for j, m in enumerate(S.chord(deg, 4, 3, 1)):
            S.add("keys", epiano(m, S.beat * 1.4, 0.7), S.at_bar(b, 2.5) + j * 0.01, -5)
        if b >= beat_in:
            bn = S.deg(deg, 1)
            S.add("bass", k808(bn, S.beat * 1.4), S.at_bar(b, 0))
            S.add("bass", k808(bn, S.beat * 0.9, glide_from=bn + 7), S.at_bar(b, 2.5))
        if b % 2 == 1:
            for i, d in enumerate((5, 3, 2)):
                S.add("bell", bell(S.deg(d, 5), 1.0), S.at_bar(b, 1 + i * 0.75))
    drums_trap(S, beat_in, nb, kick_pattern=(0, 1.5, 2.75), gain=-1)
    vin = filt(noise(S.n), "bp", (800, 6000))
    vin *= (RNG.random(S.n) > 0.9993) * 6 + 0.15
    S.add("vinyl", vin, 0)
    return S


def edm_layers(dur, bpm=124, key="F", marks=None, seed=11):
    """future house, built layer by layer for the audio-led reel.
    marks: kick, hats, bass, chords, lead, build, drop, (end) -> seconds where each layer enters."""
    m = marks
    S = Song(dur, bpm, key, "minor", seed)
    nb = _bars(S, dur) + 1
    B = {k: _bars(S, v) for k, v in m.items()}
    prog_ = [1, 6, 3, 7]
    S.track("kick", gain_db=0)
    S.track("hats", rev=0.05, gain_db=-8)
    S.track("bass", sc=0.7, gain_db=-2)
    S.track("chords", rev=0.25, sc=0.7, gain_db=-4)
    S.track("lead", rev=0.25, dly=0.25, sc=0.4, gain_db=-5)
    S.track("snare", rev=0.15, gain_db=-4)
    S.track("fx", rev=0.3, gain_db=-3)
    K = kick(52, 1.1, 0.36)
    drop, build = B["drop"], B["build"]
    for b in range(nb):
        deg = prog_[b % 4]
        in_build = build <= b < drop
        if b >= B["kick"] and not in_build:
            for i in range(4):
                S.add("kick", K, S.at_bar(b, i))
        if b >= B["hats"]:
            for i in range(4):
                S.add("hats", hat(True, vel=0.7), S.at_bar(b, i + 0.5), pan=-0.2)
                S.add("hats", hat(False, vel=0.35), S.at_bar(b, i + 0.25), pan=0.3)
                S.add("hats", hat(False, vel=0.35), S.at_bar(b, i + 0.75), pan=0.3)
            if b >= drop or (B["chords"] <= b < build):
                S.add("snare", clap(), S.at_bar(b, 1))
                S.add("snare", clap(), S.at_bar(b, 3))
        if b >= B["bass"] and not in_build:
            bn = S.deg(deg, 2)
            for i in range(8):
                ln = int(S.beat * 0.42 * SR)
                x = reese(bn + (12 if i % 4 == 3 else 0), S.beat * 0.45, 700 if b < drop else 1400)
                S.add("bass", x, S.at_bar(b, i / 2 + 0.5 * (i % 2 == 0) * 0))
        if b >= B["chords"]:
            ch = S.chord(deg, 4, 4)
            if b >= drop:
                for r in (0, 0.75, 1.5, 2.25, 3.0):
                    S.add("chords", supersaw(ch, S.beat * 0.55, 6000, 7, 0.2, 0.003, 0.05, 0.7, 0.3), S.at_bar(b, r))
            else:
                S.add("chords", supersaw(ch, S.bar, 2200, 5, 0.12, 0.05, 0.3, 0.9, 0.6), S.at_bar(b))
        if b >= B["lead"]:
            mel = [5, 6, 8, 6, 5, 3, 5, 2] if b < drop else [8, 10, 9, 8, 6, 8, 5, 6]
            for i in range(8):
                if b >= drop:
                    S.add("lead", vox(S.deg(mel[i], 5), S.beat * 0.42, "aeoui"[i % 3]), S.at_bar(b, i / 2), -1,
                          pan=0.25 * math.sin(i))
                else:
                    S.add("lead", pluck(S.deg(mel[i], 5), S.beat * 0.45, 5000, 0.2), S.at_bar(b, i / 2))
    tb, td = S.at_bar(build), S.at_bar(drop)
    S.add("snare", snare_roll(td - tb, 2, 32, 220), tb, -2)
    S.add("fx", riser(td - tb), tb, 0)
    S.add("fx", impact(3.0), td, 0)
    S.add("fx", crash(3.0), td, -3)
    S.filter_auto("chords", lambda t_: np.where((t_ >= tb) & (t_ < td), 600 + 9000 * ((t_ - tb) / max(td - tb, 1e-3)) ** 2,
                                                np.where(t_ < tb, 9000, 14000)))
    return S


def cowbell(note, dur=0.28):
    """phonk cowbell: two detuned squares through a resonant band, fast decay."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = hz(note)
    x = osc_sq(f, n, 0.5) + osc_sq(f * 1.483, n, 0.5)
    x = filt(x, "bp", (f * 0.9, f * 3.2))
    return sat(x * np.exp(-t * 9) * 0.6, 1.6) * 0.6


def phonk(dur, bpm=130, key="C#", marks=None, seed=13):
    """drift phonk: cowbell melody, distorted 808 slides, crunchy kick, snare on 3, triplet hats.
    marks: {"drop": t} (before it: cowbell + filtered 808 only), {"hits": [t...]} (impacts)."""
    marks = marks or {}
    S = Song(dur, bpm, key, "phrygian", seed)
    nb = _bars(S, dur) + 1
    drop = _bars(S, marks.get("drop", 0))
    S.track("cow", rev=0.2, dly=0.12, gain_db=0)
    S.track("bass", gain_db=0)
    S.track("fx", rev=0.3)
    mel = [(0, 1), (0.5, 1), (1.0, 2), (1.5, 1), (2.0, 4), (2.5, 3), (3.0, 2), (3.25, 1), (3.5, 2), (3.75, 1)]
    prog_ = [1, 1, 2, 7]
    for b in range(nb):
        deg = prog_[b % 4]
        for r, d in mel:
            S.add("cow", cowbell(S.deg(d + deg - 1, 5)), S.at_bar(b, r), pan=0.15 * math.sin(r * 3))
        bn = S.deg(deg, 1)
        x = k808(bn, S.beat * 1.6, drive=4.0)
        S.add("bass", x, S.at_bar(b, 0))
        S.add("bass", k808(bn + 12, S.beat * 0.9, glide_from=bn, drive=4.0), S.at_bar(b, 2.5))
        if b >= drop:
            K = sat(kick(44, 1.3, 0.45, 0.9), 3.0)
            for kp in (0, 1.5, 2.75):
                S.add("kick", K, S.at_bar(b, kp))
            sn, cl = snare(200, 1.3, 0.2), clap()
            S.add("snare", sat(sn + np.pad(cl, (0, len(sn) - len(cl))), 2.2), S.at_bar(b, 2))
            for i in range(12):                                  # triplet hats
                S.add("hats", hat(i % 3 == 2, vel=0.5 + 0.3 * (i % 3 == 0)), S.at_bar(b, i / 3), pan=0.3)
    if drop > 0:
        S.filter_auto("bass", lambda tb: np.where(tb < S.at_bar(drop), 400, 16000))
        S.add("fx", riser(S.bar), S.at_bar(drop) - S.bar, -3)
    for h in marks.get("hits", []):
        S.add("fx", impact(1.6), h, -2)
    S.sends["snare"] = (0.12, 0)
    return S


GENRES = {"future_bass": future_bass, "synthwave": synthwave, "whimsical": whimsical, "cinematic": cinematic,
          "lofi_trap": lofi_trap, "edm_layers": edm_layers,
          "phonk": phonk}
