"""audio: original soft piano/pad score, room tone, gentle UI-style SFX and the narration -> work/mix.wav (-14 LUFS).

Everything is synthesised (repo audio_kit), so there are no music or SFX licences to clear.
Cue times come from work/timeline.json so sound stays locked to cuts and graphics.
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.signal import fftconvolve

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "vibe-editing-system/shared/scripts"))
import audio_kit as ak  # noqa: E402
from vibelib import loudnorm_filter  # noqa: E402

SR = ak.SR
TL = json.loads((HERE / "work/timeline.json").read_text())
DUR = TL["dur"]
N = int(DUR * SR)
G = {s["gfx"]: s for s in TL["shots"] if "gfx" in s}
L = TL["lines"]
rng = np.random.default_rng(11)


def buf():
    return np.zeros((N, 2), np.float32)


def reverb(x, secs=2.6, wet=0.35):
    n = int(secs * SR)
    t = np.arange(n) / SR
    ir = np.stack([rng.standard_normal(n) * np.exp(-t * 3.2), rng.standard_normal(n) * np.exp(-t * 3.2)], 1)
    ir /= np.sqrt((ir ** 2).sum(0))
    y = np.stack([fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], 1)
    return (1 - wet) * x + wet * y * 2.2


# ------------------------------------------------------------------ score: D major, 80 bpm, vi-IV-I-V
BEAT = 60 / 80
BAR = 4 * BEAT
PROG = [(59, [47, 54, 59, 62, 66]),     # Bm
        (55, [43, 50, 55, 59, 62]),     # G
        (50, [38, 45, 50, 54, 57]),     # D
        (57, [45, 52, 57, 61, 64])]     # A
MEL = [74, 73, 71, 69, 71, 66, 69, 64]    # sparse top line, one note per half bar from the build section


def score():
    pad, piano, low = buf(), buf(), buf()
    logo = G["logo"]["s"]
    t, bar = 0.0, 0
    while t < logo:
        root, notes = PROG[bar % 4]
        chord = ak.pad_chord([n + 12 for n in notes[1:4]], BAR + 0.4, cutoff=1400)
        ak.place(pad, chord, t, -6 + (2 if t > 20 else 0), pan=0)
        # piano: single notes at first, eighth-note arpeggio once the story turns hopeful
        if t < 6.5:
            for k, n in enumerate([notes[2] + 12, notes[3] + 12]):
                ak.place(piano, ak.keys(n, 2.4), t + k * 2 * BEAT, -4, pan=-0.2 + 0.4 * k)
        else:
            arp = [notes[1] + 12, notes[2] + 12, notes[3] + 12, notes[4] + 12, notes[3] + 12, notes[2] + 12, notes[3] + 12, notes[4] + 12]
            for k, n in enumerate(arp):
                ak.place(piano, ak.keys(n, 1.6), t + k * BEAT / 2, -9 + (2 if k % 4 == 0 else 0), pan=(k % 2) * 0.3 - 0.15)
        if t > 19.5:
            for h in range(2):
                ak.place(piano, ak.keys(MEL[(bar * 2 + h) % len(MEL)], 2.0), t + h * 2 * BEAT, -3, pan=0.1)
            ak.place(low, ak.bass_note(root - 12, BAR, bright=260), t, -8)
            for b in (0, 2):
                ak.place(low, ak.kick() * 0.5, t + b * BEAT, -16)
        t += BAR
        bar += 1
    # resolve on D major for the logo + end card
    ak.place(pad, ak.pad_chord([62, 66, 69, 74], DUR - logo + 0.5, cutoff=1800), logo, -3)
    ak.place(low, ak.bass_note(38, DUR - logo, bright=200), logo, -6)
    for k, n in enumerate([62, 66, 69, 74, 78]):
        ak.place(piano, ak.keys(n, 3.5), logo + k * 0.09, -5, pan=-0.3 + 0.15 * k)
    end = G["endcard"]["s"]
    for k, n in enumerate([74, 78, 81]):
        ak.place(piano, ak.keys(n, 3.0), end + 0.6 + k * BEAT, -7)
    mus = reverb(pad + piano, 3.0, 0.4) + low
    # fade in over the first 1.5 s and out with the picture
    fin = np.clip(np.arange(N) / (1.5 * SR), 0, 1)
    fout = np.clip((DUR - 0.05 - np.arange(N) / SR) / 0.9, 0, 1)
    return mus * (fin * fout)[:, None]


# ------------------------------------------------------------------ SFX (soft, "product film" palette)
def blip(f=1250, d=0.22):
    t = ak.secs(d)
    x = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t * 22)
    return (x * np.clip(t / 0.002, 0, 1)).astype(np.float32) * 0.5


def thump(f=70, d=0.7):
    t = ak.secs(d)
    x = np.sin(2 * np.pi * (f * t + 25 * (1 - np.exp(-t * 18)) / 18)) * np.exp(-t * 7)
    air = ak.filt(ak.noise(d), "lp", 900) * np.exp(-t * 30) * 0.4
    return np.tanh(1.5 * (x + air)).astype(np.float32) * 0.8


def room_tone():
    x = ak.filt(rng.standard_normal((N, 2)).astype(np.float32), "lp", 500)
    x += 0.3 * ak.filt(rng.standard_normal((N, 2)).astype(np.float32), "bp", (900, 2500))
    x /= np.abs(x).max()
    gate = np.zeros(N, np.float32)
    for s in TL["shots"]:
        if "src" in s and "gfx" not in s:
            a, b = int(s["s"] * SR), int(s["e"] * SR)
            gate[a:b] = 1
    k = int(0.15 * SR)
    gate = np.convolve(gate, np.ones(k) / k, mode="same")
    return x * gate[:, None]


def sfx():
    out = buf()
    put = lambda clip, t, g, pan=0.0: ak.place(out, clip, t, g, pan)
    whoosh = lambda d: ak.sfx_whoosh(d)
    # G1 questions
    q = G["questions"]
    put(whoosh(0.6), q["s"] - 0.3, -16)
    for i, d in enumerate([0.15, 0.5, 0.85, 1.2, 1.55]):
        put(blip(900 + 90 * i, 0.3), q["s"] + d + 0.05, -26, pan=[-0.5, 0.4, 0.5, -0.4, 0.1][i])
    put(ak.sfx_riser(1.8), q["e"] - 1.8, -21)
    put(thump(60), q["e"], -24)
    # cuts in the footage
    for s in TL["shots"]:
        if "src" in s and "gfx" not in s and s["s"] > 7:
            put(ak.sfx_swish(), s["s"] - 0.14, -27)
    # G2 options UI
    o = G["options"]
    put(whoosh(0.5), o["s"] - 0.25, -16)
    for i in range(4):
        put(ak.sfx_click(), o["s"] + 0.36 + i * 0.13, -24, pan=-0.3 + 0.2 * i)
    put(blip(1400), o["s"] + 1.12, -20)
    # G3 guidance words + care circle
    g = G["guidance"]
    put(whoosh(0.5), g["s"] - 0.25, -16)
    for i in (10, 11, 12):
        put(thump(75 + (i - 10) * 8, 0.5), L[i]["s"] - 0.03, -28)
    put(ak.sfx_sparkle(), L[12]["s"] + 0.1, -26)
    put(blip(1000, 0.35), 23.27, -20)
    for i in range(4):
        put(blip(1300 + 140 * i), 23.62 + i * 0.12, -24, pan=[-0.5, -0.5, 0.5, 0.5][i])
    # logo
    lg = G["logo"]
    put(ak.sfx_riser(1.1), lg["s"] - 1.1, -19)
    put(thump(55, 1.2), lg["s"], -20)
    put(ak.sfx_sparkle(), lg["s"] + 0.35, -21)
    # G5 profile
    p = G["profile"]
    put(whoosh(0.6), p["s"] - 0.1, -17)
    for i in range(4):
        put(blip(1500 + 100 * i, 0.2), p["s"] + 1.33 + i * 0.17, -27, pan=0.3)
    for i in range(2):
        put(ak.sfx_click(), p["s"] + 2.23 + i * 0.2, -24)
    # end card
    e = G["endcard"]
    put(whoosh(0.7), e["s"] - 0.3, -16)
    put(ak.sfx_ding(), e["s"] + 0.35, -20)
    put(blip(1600, 0.3), e["s"] + 1.4, -20)
    return out


def main():
    voice = buf()
    ak.place(voice, ak.read_audio(HERE / "work/vo_edit.wav"), 0.0, 0.0)
    mus = score() * ak.db(-15)
    mus *= ak.duck_gain(voice, depth_db=-6)[:, None]
    mix = voice + mus + room_tone() * ak.db(-46) + sfx() * ak.db(-5)
    peak = np.abs(mix).max()
    if peak > 0.98:
        mix = np.tanh(mix / peak * 1.3) / math.tanh(1.3) * 0.98
    raw = HERE / "work/mix_raw.wav"
    ak.write_wav(raw, mix)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", loudnorm_filter(str(raw), -14.0, -1.0),
                    "-ar", str(SR), str(HERE / "work/mix.wav")], check=True)
    print("  -> work/mix.wav")


if __name__ == "__main__":
    main()
