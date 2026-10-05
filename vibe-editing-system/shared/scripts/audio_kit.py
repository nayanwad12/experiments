"""audio_kit: original music beds, sound effects, voice clean-up and mixing, all synthesised in numpy.
No samples and no stock music, so there are no copyright claims.

CLI
    python3 scripts/audio_kit.py bed --mood hype --seconds 30 -o work/music.wav
    python3 scripts/audio_kit.py bed --mood chill --bpm 84 --bars 16 --key A -o work/music.wav
    python3 scripts/audio_kit.py sfx --list
    python3 scripts/audio_kit.py sfx whoosh -o work/whoosh.wav
    python3 scripts/audio_kit.py voice raw/take1.mp4 -o work/voice.wav --denoise
    python3 scripts/audio_kit.py mix work/cues.json -o work/mix.wav [--video work/picture.mp4 --out-video out/final.mp4]

cues.json for `mix` (times in seconds, gains in dB):
    {
      "duration": 30.0,
      "voice":  {"file": "work/voice.wav", "gain_db": 0, "t": 0},
      "music":  {"file": "work/music.wav", "gain_db": -8, "duck_db": -10, "fade_out": 1.5},
      "tracks": [{"file": "assets/jingle.wav", "t": 27.0, "gain_db": -4}],
      "sfx":    [{"t": 0.0, "kind": "impact", "gain_db": -3}, {"t": 2.4, "kind": "pop"}]
    }

Library use (from your own render script):
    import audio_kit as ak
    bed = ak.music_bed("upbeat", seconds=20)       # stereo float32 (n, 2) at ak.SR
    hit = ak.SFX["impact"]()                        # mono float32
"""

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vibelib import ff, ffmpeg_bin, loudnorm_filter, mux  # noqa: E402

SR = 48000
RNG = np.random.default_rng(7)


# ------------------------------------------------------------------ basics
def secs(n):
    return np.arange(int(n * SR)) / SR


def db(x):
    return 10 ** (x / 20)


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def filt(x, kind, f, order=2):
    nyq = SR / 2
    if kind == "bp":
        lo, hi = max(20, f[0]), min(nyq * 0.95, f[1])
        sos = butter(order, [lo / nyq, hi / nyq], btype="band", output="sos")
    else:
        sos = butter(order, min(f, nyq * 0.95) / nyq, btype="low" if kind == "lp" else "high", output="sos")
    return sosfilt(sos, x, axis=0).astype(np.float32)


def env_ad(n, attack, decay, curve=4.0):
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    d = np.exp(-curve * np.clip(t - attack, 0, None) / max(decay, 1e-4))
    return (a * d).astype(np.float32)


def sweep_sine(f0, f1, dur, curve=8.0):
    t = secs(dur)
    f = f1 + (f0 - f1) * np.exp(-curve * t / dur)
    return np.sin(2 * np.pi * np.cumsum(f) / SR).astype(np.float32)


def noise(dur):
    return RNG.uniform(-1, 1, int(dur * SR)).astype(np.float32)


def saw(freq, dur, detune=0.0):
    t = secs(dur)
    ph = (t * freq * (1 + detune) + RNG.random()) % 1.0
    return (2 * ph - 1).astype(np.float32)


def karplus(freq, dur, bright=0.5, decay=0.996):
    n = int(dur * SR)
    p = max(2, int(SR / freq))
    buf = filt(RNG.uniform(-1, 1, p).astype(np.float32), "lp", 2000 + 8000 * bright, 1)
    out = np.zeros(n, np.float32)
    b = buf.copy()
    reps = n // p + 1
    for i in range(reps):
        seg = b[: min(p, n - i * p)]
        out[i * p: i * p + len(seg)] = seg
        b = decay * 0.5 * (b + np.roll(b, 1))
    return out


def tvlp(x, cutoffs):
    """time-varying one-pole lowpass (cutoffs: array of Hz per sample)."""
    a = np.exp(-2 * np.pi * np.asarray(cutoffs) / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a[i]) * x[i] + a[i] * acc
        y[i] = acc
    return y


def norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1.0
    return (x / m * peak).astype(np.float32)


# ------------------------------------------------------------------ sound effects (mono)
def sfx_whoosh(dur=0.7):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    shape = np.sin(np.pi * t) ** 1.6
    cut = 300 + 5000 * np.sin(np.pi * t) ** 2
    x = tvlp(noise(dur), cut) * shape
    x = x + 0.5 * filt(noise(dur), "bp", (800, 3000)) * shape ** 3
    return norm(x, 0.8)


def sfx_swish():
    return sfx_whoosh(0.28)


def sfx_pop():
    x = sweep_sine(1100, 280, 0.09, 6) * env_ad(int(0.09 * SR), 0.001, 0.07)
    click = filt(noise(0.01), "hp", 3000) * env_ad(int(0.01 * SR), 0.0005, 0.006)
    x[: len(click)] += 0.4 * click
    return norm(x, 0.85)


def sfx_click():
    x = filt(noise(0.012), "bp", (1800, 7000)) * env_ad(int(0.012 * SR), 0.0003, 0.006)
    return norm(x, 0.7)


def sfx_tick():
    x = np.sin(2 * np.pi * 2200 * secs(0.03)) * env_ad(int(0.03 * SR), 0.0005, 0.02)
    return norm(x, 0.5)


def sfx_typing(dur=1.0, cps=13):
    out = np.zeros(int(dur * SR) + SR // 10, np.float32)
    t = 0.0
    while t < dur:
        k = sfx_click() * RNG.uniform(0.5, 1.0)
        i = int(t * SR)
        out[i: i + len(k)] += k
        t += RNG.uniform(0.6, 1.4) / cps
    return norm(out, 0.6)


def sfx_impact():
    d = 1.4
    n = int(d * SR)
    boom = sweep_sine(140, 38, d, 5) * env_ad(n, 0.002, 1.0, 3.5)
    crack = filt(noise(d), "lp", 2500) * env_ad(n, 0.001, 0.18, 5)
    x = boom + 0.45 * crack
    return norm(np.tanh(1.8 * x), 0.95)


def sfx_riser(dur=2.0):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    ns = tvlp(noise(dur), 200 + 9000 * t ** 2) * t ** 2
    f = 110 * 2 ** (3 * t)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * t ** 3 * 0.35
    return norm(ns + tone, 0.8)


def sfx_downlifter(dur=1.5):
    return norm(sfx_riser(dur)[::-1].copy(), 0.7)


def sfx_sparkle():
    d = 0.9
    out = np.zeros(int(d * SR), np.float32)
    for _ in range(9):
        f = RNG.uniform(2500, 7000)
        s = int(RNG.uniform(0, 0.45) * SR)
        ln = int(0.4 * SR)
        ping = np.sin(2 * np.pi * f * secs(0.4)) * env_ad(ln, 0.001, 0.3, 5)
        out[s: s + ln] += ping[: len(out) - s] * RNG.uniform(0.3, 1)
    return norm(out, 0.6)


def sfx_ding():
    d = 1.6
    n = int(d * SR)
    t = secs(d)
    x = sum(a * np.sin(2 * np.pi * 1318.5 * r * t) * np.exp(-t * k)
            for r, a, k in ((1, 1, 2.5), (2.76, 0.4, 4), (5.4, 0.2, 6), (8.9, 0.1, 9)))
    return norm(x * env_ad(n, 0.001, d, 0.1), 0.7)


def sfx_glitch():
    d = 0.35
    x = noise(d)
    steps = np.repeat(RNG.choice([0, 1], 24), int(d * SR) // 24 + 1)[: len(x)]
    x = np.round(x * 4) / 4 * steps
    x += 0.5 * np.sign(np.sin(2 * np.pi * 180 * secs(d))) * (1 - steps)
    return norm(filt(x, "hp", 200), 0.6)


def sfx_bass_drop():
    d = 2.0
    return norm(np.tanh(2 * sweep_sine(90, 30, d, 2.5) * env_ad(int(d * SR), 0.005, d, 2)), 0.95)


def sfx_shutter():
    a = filt(noise(0.03), "bp", (1500, 6000)) * env_ad(int(0.03 * SR), 0.0005, 0.02)
    out = np.zeros(int(0.12 * SR), np.float32)
    out[: len(a)] += a
    out[int(0.07 * SR): int(0.07 * SR) + len(a)] += 0.7 * a
    return norm(out, 0.7)


SFX = {
    "whoosh": sfx_whoosh, "swish": sfx_swish, "pop": sfx_pop, "click": sfx_click, "tick": sfx_tick,
    "typing": sfx_typing, "impact": sfx_impact, "riser": sfx_riser, "downlifter": sfx_downlifter,
    "sparkle": sfx_sparkle, "ding": sfx_ding, "glitch": sfx_glitch, "bass_drop": sfx_bass_drop,
    "shutter": sfx_shutter,
}


# ------------------------------------------------------------------ music instruments
def kick():
    d = 0.4
    n = int(d * SR)
    return 0.9 * np.tanh(2.2 * sweep_sine(160, 48, d, 9) * env_ad(n, 0.001, 0.32, 4))


def clap():
    d = 0.25
    n = int(d * SR)
    x = filt(noise(d), "bp", (900, 4000)) * env_ad(n, 0.001, 0.16, 6)
    for off in (0.008, 0.017):
        i = int(off * SR)
        x[i:] += 0.6 * x[: n - i]
    return 0.5 * x


def snare():
    d = 0.25
    n = int(d * SR)
    return 0.45 * filt(noise(d), "hp", 1200) * env_ad(n, 0.001, 0.14, 6) + \
        0.3 * np.sin(2 * np.pi * 190 * secs(d)) * env_ad(n, 0.001, 0.07)


def hat(open_=False):
    d = 0.25 if open_ else 0.05
    n = int(d * SR)
    return 0.22 * filt(noise(d), "hp", 7000) * env_ad(n, 0.0005, d * 0.8, 5)


def bass_note(m, dur, bright=500):
    f = midi_hz(m)
    n = int(dur * SR)
    x = 0.6 * filt(saw(f, dur), "lp", bright) + 0.7 * np.sin(2 * np.pi * f * secs(dur))
    return 0.5 * x * env_ad(n, 0.005, dur, 1.2)


def pad_chord(notes, dur, cutoff=1800):
    n = int(dur * SR)
    x = np.zeros(n, np.float32)
    for m in notes:
        f = midi_hz(m)
        for dt in (-0.006, 0.0, 0.007):
            x += saw(f, dur, dt)
    x = filt(x, "lp", cutoff) / (len(notes) * 3)
    a = np.clip(np.arange(n) / (0.25 * SR), 0, 1)
    r = np.clip((n - np.arange(n)) / (0.3 * SR), 0, 1)
    return 0.7 * x * a * r


def pluck(m, dur=0.6, bright=0.6):
    return 0.45 * karplus(midi_hz(m), dur, bright)


def glock(m, dur=0.8):
    f = midi_hz(m)
    t = secs(dur)
    return 0.25 * (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2.76 * t)) * np.exp(-t * 5)


def keys(m, dur=0.9):
    f = midi_hz(m)
    t = secs(dur)
    x = sum(np.sin(2 * np.pi * f * h * t) / h ** 1.5 for h in (1, 2, 3, 4))
    return 0.22 * x * np.exp(-t * 3.0) * np.clip(t / 0.004, 0, 1)


# ------------------------------------------------------------------ music bed
SCALES = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10]}
KEYS = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7,
        "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}

MOODS = {
    # bpm, scale, key, progression (scale degrees, 1-based), instruments
    "upbeat":     dict(bpm=118, scale="major", key="C", prog=[1, 5, 6, 4], drums="four", lead="pluck", pad=True),
    "hype":       dict(bpm=128, scale="minor", key="F", prog=[1, 6, 3, 7], drums="four", lead="pluck", pad=True, pump=True),
    "chill":      dict(bpm=84, scale="major", key="A", prog=[4, 3, 2, 1], drums="lofi", lead="keys", pad=True, sevenths=True),
    "corporate":  dict(bpm=110, scale="major", key="D", prog=[1, 6, 4, 5], drums="light", lead="keys", pad=True),
    "cinematic":  dict(bpm=72, scale="minor", key="D", prog=[1, 6, 4, 5], drums="cine", lead=None, pad=True),
    "playful":    dict(bpm=120, scale="major", key="G", prog=[1, 4, 5, 1], drums="light", lead="glock", pad=False),
    "tech":       dict(bpm=124, scale="minor", key="A", prog=[1, 1, 6, 7], drums="four", lead="pluck", pad=True, pump=True),
}


def chord(root_pc, scale, degree, octave=4, sevenths=False):
    sc = SCALES[scale]
    idx = [degree - 1, degree + 1, degree + 3] + ([degree + 5] if sevenths else [])
    out = []
    for i in idx:
        o, k = divmod(i, 7)
        out.append(12 * (octave + 1 + o) + root_pc + sc[k])
    return out


def music_bed(mood="upbeat", seconds=None, bars=None, bpm=None, key=None, intro_bars=1, seed=7):
    """Return a stereo (n, 2) float32 loop-friendly music bed."""
    global RNG
    RNG = np.random.default_rng(seed)
    p = dict(MOODS[mood])
    bpm = bpm or p["bpm"]
    beat = 60.0 / bpm
    bar = 4 * beat
    if bars is None:
        bars = max(2, math.ceil((seconds or 30) / bar))
    total = bars * bar
    n = int((total + 2.0) * SR)
    L = {k: np.zeros(n, np.float32) for k in ("drums", "bass", "pad", "lead")}
    root = KEYS[key or p["key"]]

    def add(track, sig, t, g=1.0):
        i = int(t * SR)
        if i >= n:
            return
        sig = sig[: n - i]
        L[track][i: i + len(sig)] += g * sig

    K, C, S, Hh, Ho = kick(), clap(), snare(), hat(), hat(True)
    kicks = []
    for b in range(bars):
        t0 = b * bar
        deg = p["prog"][b % len(p["prog"])]
        ch = chord(root, p["scale"], deg, 4, p.get("sevenths", False))
        drums_on = b >= intro_bars
        # pad
        if p["pad"]:
            add("pad", pad_chord(ch, bar + 0.25, 1400 if mood in ("chill", "cinematic") else 2200), t0)
        # bass
        bm = ch[0] - 24
        if mood == "cinematic":
            for i in range(8):
                add("bass", bass_note(bm, beat * 0.45, 300), t0 + i * beat / 2, 0.8)
        elif mood == "chill":
            add("bass", bass_note(bm, beat * 1.8, 350), t0)
            add("bass", bass_note(bm + 7, beat * 1.8, 350), t0 + 2 * beat)
        elif p.get("pump"):
            for i in range(4):
                add("bass", bass_note(bm, beat * 0.45, 700), t0 + i * beat + beat / 2)
        else:
            for i in range(8):
                add("bass", bass_note(bm + (12 if i % 4 == 3 else 0), beat * 0.42, 600), t0 + i * beat / 2, 0.9)
        # lead / arp
        lead = p["lead"]
        if lead and b >= intro_bars // 2:
            arp = ch + [ch[0] + 12]
            steps = 8 if lead != "keys" else 4
            for i in range(steps):
                m = arp[(i * 2 + b) % len(arp)] + 12 * (lead == "glock")
                tt = t0 + i * bar / steps
                if lead == "pluck":
                    add("lead", pluck(m, beat * 1.2, 0.55), tt, 0.8)
                elif lead == "glock":
                    add("lead", glock(m), tt, 0.9)
                else:
                    add("lead", keys(m, beat * 1.6), tt + (0.02 if i % 2 else 0), 0.8)
        # drums
        if drums_on:
            style = p["drums"]
            if style == "four":
                for i in range(4):
                    add("drums", K, t0 + i * beat)
                    kicks.append(t0 + i * beat)
                    add("drums", Ho if i % 2 else Hh, t0 + i * beat + beat / 2, 0.8)
                add("drums", C, t0 + beat)
                add("drums", C, t0 + 3 * beat)
            elif style == "light":
                for i in range(4):
                    if i in (0, 2):
                        add("drums", K, t0 + i * beat, 0.8)
                        kicks.append(t0 + i * beat)
                    add("drums", Hh, t0 + i * beat + beat / 2, 0.7)
                add("drums", C, t0 + beat, 0.6)
                add("drums", C, t0 + 3 * beat, 0.6)
            elif style == "lofi":
                sw = beat * 0.58
                add("drums", K, t0, 0.8)
                add("drums", K, t0 + 2.5 * beat, 0.6)
                kicks += [t0, t0 + 2.5 * beat]
                add("drums", S, t0 + beat, 0.7)
                add("drums", S, t0 + 3 * beat, 0.7)
                for i in range(4):
                    add("drums", Hh, t0 + i * beat, 0.5)
                    add("drums", Hh, t0 + i * beat + sw, 0.35)
            elif style == "cine":
                add("drums", sfx_impact() * 0.6, t0, 0.7)
                kicks.append(t0)
                for i in (2, 3):
                    add("drums", K * 0.7, t0 + i * beat + beat * 0.5 * (i == 3), 0.6)

    # side-chain pump on pad/bass for hype styles
    if p.get("pump") and kicks:
        g = np.ones(n, np.float32)
        ln = int(beat * 0.9 * SR)
        shape = 1 - 0.75 * np.exp(-np.arange(ln) / (0.09 * SR))
        for kt in kicks:
            i = int(kt * SR)
            seg = g[i: i + ln]
            seg *= shape[: len(seg)]
        L["pad"] *= g
        L["bass"] *= 0.6 + 0.4 * g

    mixL = 0.9 * L["drums"] + 0.8 * L["bass"] + 0.55 * L["pad"] * 1.08 + 0.5 * L["lead"] * 0.85
    mixR = 0.9 * L["drums"] + 0.8 * L["bass"] + 0.55 * L["pad"] * 0.92 + 0.5 * L["lead"] * 1.15
    st = np.stack([mixL, mixR], 1)
    end = int(total * SR) + int(1.2 * SR)
    st = st[:end]
    if seconds:
        end = int(seconds * SR)
        st = st[:end]
        fade = int(min(1.5, seconds * 0.1) * SR)
        st[-fade:] *= np.linspace(1, 0, fade)[:, None]
    st = np.tanh(1.2 * st / (np.max(np.abs(st)) or 1)) * 0.85
    return st.astype(np.float32)


# ------------------------------------------------------------------ io + mixing
def read_audio(path):
    """Decode any audio/video file to stereo float32 at SR via ffmpeg."""
    r = subprocess.run([ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-i", str(path), "-vn",
                        "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True)
    if r.returncode != 0:
        sys.exit(f"could not read audio from {path}: {r.stderr.decode()[-400:]}")
    return np.frombuffer(r.stdout, np.float32).reshape(-1, 2).copy()


def write_wav(path, x):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    x = np.asarray(x, np.float32)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    wavfile.write(str(path), SR, np.clip(x, -1, 1))


def place(buf, clip, t, gain_db=0.0, pan=0.0):
    clip = np.asarray(clip, np.float32)
    if clip.ndim == 1:
        lg, rg = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        clip = np.stack([clip * lg * 1.414, clip * rg * 1.414], 1)
    i = int(round(t * SR))
    if i < 0:
        clip, i = clip[-i:], 0
    if i >= len(buf):
        return
    seg = clip[: len(buf) - i]
    buf[i: i + len(seg)] += seg * db(gain_db)


def duck_gain(voice, depth_db=-10, attack=0.03, release=0.35, thresh=0.02):
    mono = np.abs(voice).mean(1)
    win = int(0.05 * SR)
    env = np.sqrt(np.convolve(mono ** 2, np.ones(win) / win, mode="same"))
    target = np.clip(env / thresh, 0, 1)
    a_up, a_dn = math.exp(-1 / (attack * SR)), math.exp(-1 / (release * SR))
    # coarse smoothing at 1 ms resolution for speed
    step = SR // 1000
    coarse = target[::step]
    sm = np.zeros_like(coarse)
    acc = 0.0
    au, ad = a_up ** step, a_dn ** step
    for i, v in enumerate(coarse):
        c = au if v > acc else ad
        acc = c * acc + (1 - c) * v
        sm[i] = acc
    g = np.repeat(sm, step)[: len(mono)]
    g = np.pad(g, (0, len(mono) - len(g)), mode="edge")
    return 1 - (1 - db(depth_db)) * g


def mix(cues, base_dir="."):
    base = Path(base_dir)
    dur = float(cues["duration"])
    n = int(dur * SR)
    out = np.zeros((n, 2), np.float32)
    voice_bus = np.zeros((n, 2), np.float32)
    v = cues.get("voice")
    if v:
        place(voice_bus, read_audio(base / v["file"]), v.get("t", 0), v.get("gain_db", 0))
    for tr in cues.get("tracks", []):
        place(out, read_audio(base / tr["file"]), tr.get("t", 0), tr.get("gain_db", 0))
    m = cues.get("music")
    if m:
        mus = np.zeros((n, 2), np.float32)
        place(mus, read_audio(base / m["file"]), m.get("t", 0), m.get("gain_db", -8))
        fo = m.get("fade_out", 1.5)
        if fo > 0:
            k = int(fo * SR)
            mus[-k:] *= np.linspace(1, 0, k)[:, None]
        if v and m.get("duck_db", -10) < 0:
            mus *= duck_gain(voice_bus, m.get("duck_db", -10))[:, None]
        out += mus
    for s in cues.get("sfx", []):
        kind = s["kind"]
        if kind in SFX:
            clip = SFX[kind]() if kind not in ("whoosh", "riser", "typing") or "dur" not in s else SFX[kind](s["dur"])
        else:
            clip = read_audio(base / kind)
        place(out, clip, s["t"], s.get("gain_db", -6), s.get("pan", 0.0))
    out += voice_bus
    peak = np.max(np.abs(out)) or 1
    if peak > 0.98:
        out = np.tanh(out / peak * 1.3) / math.tanh(1.3) * 0.98
    return out


def voice_chain(src, dst, denoise=False):
    chain = ["highpass=f=80", "lowpass=f=15000"]
    if denoise:
        chain.append("afftdn=nf=-25")
    chain += ["acompressor=threshold=-20dB:ratio=3:attack=5:release=90:makeup=3", "deesser=i=0.4"]
    ff("-i", src, "-vn", "-af", ",".join(chain), "-ar", str(SR), "-ac", "2", dst)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bed", help="generate an original music bed")
    b.add_argument("--mood", default="upbeat", choices=sorted(MOODS))
    b.add_argument("--seconds", type=float, default=None)
    b.add_argument("--bars", type=int, default=None)
    b.add_argument("--bpm", type=float, default=None)
    b.add_argument("--key", default=None, choices=sorted(KEYS))
    b.add_argument("--intro-bars", type=int, default=1, help="bars before the drums enter")
    b.add_argument("--seed", type=int, default=7, help="change for a different variation")
    b.add_argument("-o", "--out", default="work/music.wav")
    s = sub.add_parser("sfx", help="render one sound effect")
    s.add_argument("kind", nargs="?")
    s.add_argument("--list", action="store_true")
    s.add_argument("-o", "--out", default=None)
    vo = sub.add_parser("voice", help="clean a voice track (EQ, compression, de-ess, optional denoise)")
    vo.add_argument("src")
    vo.add_argument("-o", "--out", default="work/voice.wav")
    vo.add_argument("--denoise", action="store_true")
    mx = sub.add_parser("mix", help="mix voice + music + sfx from a cues.json")
    mx.add_argument("cues")
    mx.add_argument("-o", "--out", default="work/mix.wav")
    mx.add_argument("--lufs", type=float, default=-14.0)
    mx.add_argument("--video", help="picture to put the mix under")
    mx.add_argument("--out-video", help="where to write video+mix")
    a = ap.parse_args()

    if a.cmd == "bed":
        x = music_bed(a.mood, a.seconds, a.bars, a.bpm, a.key, a.intro_bars, a.seed)
        write_wav(a.out, x)
        p = MOODS[a.mood]
        bpm = a.bpm or p["bpm"]
        print(f"{a.mood} bed @ {bpm:g} BPM (1 beat = {60 / bpm:.3f}s, 1 bar = {240 / bpm:.3f}s), "
              f"{len(x) / SR:.1f}s -> {a.out}")
    elif a.cmd == "sfx":
        if a.list or not a.kind:
            print("sound effects:", ", ".join(sorted(SFX)))
            return
        if a.kind not in SFX:
            sys.exit(f"unknown sfx {a.kind!r}; try --list")
        out = a.out or f"work/sfx_{a.kind}.wav"
        write_wav(out, SFX[a.kind]())
        print("->", out)
    elif a.cmd == "voice":
        voice_chain(a.src, a.out, a.denoise)
        print("->", a.out)
    elif a.cmd == "mix":
        cues = json.loads(Path(a.cues).read_text())
        x = mix(cues, ".")
        tmp = Path(a.out).with_suffix(".raw.wav")
        write_wav(tmp, x)
        ff("-i", tmp, "-af", loudnorm_filter(tmp, a.lufs), "-ar", str(SR), "-c:a", "pcm_s16le", a.out)
        tmp.unlink(missing_ok=True)
        print(f"mix ({cues['duration']}s, {a.lufs} LUFS) -> {a.out}")
        if a.video:
            outv = a.out_video or str(Path(a.video).with_name(Path(a.video).stem + "_mixed.mp4"))
            mux(a.video, a.out, outv)
            print("video ->", outv)


if __name__ == "__main__":
    main()
