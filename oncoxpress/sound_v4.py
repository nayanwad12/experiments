"""v4 soundtrack: narration re-edit + score/SFX regenerated on the v4 timeline.

Voice: the clean v3 narration stem (work/voice_v3.wav, recovered by work/extract_voice.py) with
"Dr Aditya Sarin" replaced by the corrected take, a pause for the doctor cards, and the new
"And this is just the beginning…" paragraph. Music and SFX: sound.py's score and design, every event
moved through v4.warp(), plus new cues for the doctor cards and the coming-soon section.

    python3 sound_v4.py  ->  work/mix_v4.wav
"""
import json
import os
import subprocess

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt

import sound
import v4

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
SR = sound.SR
N = int(v4.DUR * SR)
filt, pan, T = sound.filt, sound.pan, sound.T


def load_mono(path):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(p.stdout, np.int16).astype(np.float64) / 32768


def process_take(x, target_rms):
    """The same chain sound.voice() used on the original narration, then matched to its speech loudness."""
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.89
    x = filt(x, "hp", 70, 2)
    env = np.sqrt(sosfiltfilt(butter(1, 10, "lp", fs=SR, output="sos"), x ** 2) + 1e-10)
    thr = 10 ** (-26 / 20)
    x = x * np.where(env > thr, (env / thr) ** (1 / 2.5 - 1), 1.0)
    x = x + 0.18 * filt(x, "bandpass", [160, 380]) + 0.22 * filt(x, "bandpass", [2800, 6500])
    x = x * target_rms / speech_rms(x)
    n = int(0.006 * SR)
    x[:n] *= np.linspace(0, 1, n)
    x[-n:] *= np.linspace(1, 0, n)
    return sound.reverb(np.stack([x, x], 1), 0.06, False)


def speech_rms(x):
    hop = SR // 50
    r = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop, hop)])
    return float(np.mean(r[r > np.max(r) * 0.12]))


def put(buf, x, t):
    i = int(round(t * SR))
    x = x[: max(0, len(buf) - i)]
    buf[i:i + len(x)] += x


def voice():
    sr, old = wavfile.read(os.path.join(WORK, "voice_v3.wav"))
    old = old.astype(np.float64) / 32767
    target = speech_rms(old[int(2 * SR):int(70 * SR), 0])
    out = np.zeros((N, 2))
    xf = int(0.010 * SR)

    def piece(a, b, at):
        x = old[int(a * SR):int(b * SR)].copy()
        r = np.linspace(0, 1, xf)[:, None]
        x[:xf] *= r
        x[-xf:] *= r[::-1]
        put(out, x, at)

    piece(0, v4.CUT_A0, 0)
    # "…of Dr Shyam Agrawal and Dr Aditya Sarin" — re-ordered so the voice follows the cards
    piece(v4.SHYAM_0, v4.SHYAM_1, v4.SHYAM_AT)
    piece(v4.AND_0, v4.AND_1, v4.AND_AT)
    put(out, process_take(load_mono(os.path.join(HERE, "raw", "vo_aditya.mp3")), target), v4.ADITYA_AT)
    piece(v4.PAUSE_AT, v4.SPLIT_V, v4.PAUSE_AT + v4.D2)
    put(out, process_take(load_mono(os.path.join(HERE, "raw", "vo_comingsoon.mp3")), target), v4.SOON_AT)
    piece(v4.SPLIT_V, 80.0, v4.END_AT)
    return out


# ---------------------------------------------------------------- music + sfx on the warped timeline
_place = sound.place


def warped_place(buf, x, t, g=1.0):
    if abs(t - 71.4) < 1e-6:            # the reverse whoosh that leads into the end card
        t2 = v4.END_AT - 1.0
    else:
        t2 = v4.warp(t, split_end=72.30)
    _place(buf, x, t2, g)


def new_score():
    mus = np.zeros((N, 2))
    G = ([55, 59, 62, 67], 43)
    D = ([57, 62, 66, 69], 50)
    Bm = ([59, 62, 66, 71], 47)
    A = ([57, 61, 64, 69], 45)
    Asus = ([57, 62, 64, 69], 45)
    for (t0, d, (pv, bass)) in [(74.3, 3.0, G), (77.3, 2.9, D), (80.2, 2.9, Bm), (83.1, 2.9, A), (86.0, 1.6, G), (87.6, 1.4, Asus)]:
        _place(mus, sound.pad(pv, d + 1.5, att=0.9, rel=1.6, bright=1500), t0)
        _place(mus, pan(sound.sub(bass, d + 0.8, att=0.6, rel=1.0), 0), t0, 0.9)
    for (t, m, v) in [(74.8, 74, .5), (75.6, 78, .45), (76.4, 81, .5), (77.4, 79, .45), (78.6, 78, .4), (79.8, 74, .4),
                      (81.0, 76, .45), (82.4, 78, .5), (83.8, 81, .5), (85.4, 83, .5), (86.5, 81, .45), (87.7, 78, .4)]:
        _place(mus, pan(sound.piano(m, 4.5, v), sound.rng.uniform(-0.3, 0.3)), t)
    arp = {"G": [67, 71, 74, 79], "D": [66, 69, 74, 78], "Bm": [66, 71, 74, 78], "A": [64, 69, 73, 76]}
    sched = [(77.3, "D"), (80.2, "Bm"), (83.1, "A"), (86.0, "G"), (87.6, "A")]
    t, i, step = 77.0, 0, sound.BEAT / 2
    while t < 88.7:
        ch = [c for (s, c) in sched if s <= t + 1e-6]
        chord = arp[ch[-1] if ch else "D"]
        build = np.clip((t - 77.0) / 11.0, 0, 1)
        if t > 81.9 and i % 2 == 0:
            _place(mus, pan(sound.softkick(0.4 + 0.4 * build), 0), t)
        if t > 83.7 and i % 2 == 1:
            _place(mus, pan(sound.shaker(0.5 + 0.6 * build), 0.35), t)
        _place(mus, pan(sound.pluck(chord[i % 4] + (12 if (i // 8) % 2 else 0), 0.25 + 0.35 * build), -0.4 + 0.8 * ((i % 4) / 3)), t)
        t += step
        i += 1
    return sound.reverb(mus, 0.42, True)


def new_fx():
    fx = np.zeros((N, 2))
    w, tick, pop = sound.whoosh, sound.tick, sound.pop
    # doctor cards
    _place(fx, pan(w(0.6, 0.8, 300, 3500), 0), 29.55)
    _place(fx, pan(tick(0.8, 1760), -0.3), 30.0)
    _place(fx, pan(w(0.6, 0.8, 300, 3500), 0.2), 31.3)
    _place(fx, pan(tick(0.8, 1976), 0.3), 31.7)
    _place(fx, pan(w(0.5, 0.6, 300, 3500), 0), 34.35)
    # coming soon
    _place(fx, sound.reverb(pan(sound.shimmer(2.2, 0.8, 86), 0), 0.5), 74.3)
    _place(fx, pan(sound.roomtone(2.8, 0.6), 0), 74.3)
    _place(fx, pan(w(0.7, 0.8, 250, 3500), 0), 76.6)
    for i in range(3):
        _place(fx, pan(pop(0.6, 520 + 60 * i), 0.3), 78.0 + i * 0.35)
    _place(fx, pan(w(0.6, 0.7, 300, 4000), 0), 81.6)
    for tt in (82.45, 83.85, 85.45):
        _place(fx, pan(tick(0.8, 2093), -0.3), tt)
    _place(fx, pan(sound.paper(0.6, 0.4), 0.2), 82.0)
    _place(fx, pan(w(0.7, 0.8, 250, 3500), 0), 86.1)
    for k, p in enumerate((-0.6, 0, 0.6)):
        _place(fx, pan(w(0.45, 0.45, 800, 5000), p), 86.9 + k * 0.12)
    _place(fx, pan(sound.impact(0.35), 0), 87.75)
    _place(fx, pan(sound.riser(0.9, 0.6), 0), 88.05)
    return fx


def main():
    sound.N, sound.DUR = N, v4.DUR
    sound.rng = np.random.default_rng(7)
    sound.place = warped_place
    m = sound.score()
    fx = sound.design()
    sound.place = _place
    m = m + new_score()
    fx = fx + new_fx()
    v = voice()
    ve = np.sqrt(sosfiltfilt(butter(1, 4, "lp", fs=SR, output="sos"), v[:, 0] ** 2) + 1e-10)
    duck = 1 - 0.62 * np.clip((20 * np.log10(ve) + 50) / 20, 0, 1)
    duck = sosfiltfilt(butter(1, 3, "lp", fs=SR, output="sos"), duck)
    m = m / (np.max(np.abs(m)) + 1e-9) * 10 ** (-9 / 20)
    mix = v + m * duck[:, None] * 0.85 + fx * 0.9
    t = T(N)
    mix *= np.clip(t / 0.6, 0, 1)[:, None] * np.clip((v4.DUR - t) / 2.0, 0, 1)[:, None]
    peak = np.max(np.abs(mix))
    mix = np.tanh(mix / max(peak, 1e-9) * 1.15) / np.tanh(1.15) * 10 ** (-1.0 / 20)
    wavfile.write(os.path.join(WORK, "mix_v4.wav"), SR, (mix * 32767).astype(np.int16))
    wavfile.write(os.path.join(WORK, "voice_v4.wav"), SR, (np.clip(v, -1, 1) * 32767).astype(np.int16))
    print("mix peak", peak)


if __name__ == "__main__":
    main()
