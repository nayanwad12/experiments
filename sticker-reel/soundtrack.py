"""sound: voice clean-up + cut, an original score with its drop on the beat, sound effects on every cue, -14 LUFS.

    python3 soundtrack.py     -> work/mix.wav (48 kHz stereo)

Nothing sampled: the music and every effect are synthesised here (reels/common/music.py + audio_kit.py).
"""

import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "reels" / "common"))
import audio_kit as ak  # noqa: E402
import music as mu  # noqa: E402

import cut  # noqa: E402
import edit as E  # noqa: E402

SR = 48000
WORK = HERE / "work"


# ================================================================== voice
def voice():
    """clean the whole raw take (de-noise, EQ, compression, de-ess), then cut it to the edit with tiny crossfades."""
    clean = WORK / "voice_clean.wav"
    chain = ",".join([
        "highpass=f=78:poles=2", "afftdn=nf=-38:nr=10:tn=1",
        "equalizer=f=220:t=q:w=1.1:g=-2.5", "equalizer=f=3300:t=q:w=1.4:g=2.5", "highshelf=f=9500:g=2",
        "acompressor=threshold=-22dB:ratio=3.2:attack=6:release=90:makeup=4", "deesser=i=0.35",
        "alimiter=limit=0.9:attack=3:release=40",
    ])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(WORK / "voice_raw.wav"), "-af", chain, "-ac", "1",
                    "-ar", str(SR), "-c:a", "pcm_f32le", str(clean)], check=True)
    sr, x = wavfile.read(clean)
    x = x.astype(np.float32)
    n = int(E.TOTAL * SR)
    out = np.zeros(n, np.float32)
    xf = int(0.008 * SR)
    for a, b, o, d in cut.EDL:
        if b <= a:
            continue                                    # freeze: silence (the drop fills it)
        seg = x[int(a * SR): int(b * SR)].copy()
        r = np.linspace(0, 1, xf, dtype=np.float32)
        seg[:xf] *= r
        seg[-xf:] *= r[::-1]
        i = int(round(o * SR))
        seg = seg[: n - i]
        out[i: i + len(seg)] += seg
    return np.stack([out, out], 1)


# ================================================================== music
def score(total):
    bpm = E.BPM
    bar = 240.0 / bpm
    shift = (bar - E.DROP % bar) % bar                  # song clock = output clock + shift; a bar line on DROP
    S = mu.Song(total + shift + bar, bpm, "D", "major", seed=21)
    nb = int((total + shift) / bar) + 2

    def T(t_out):
        return t_out + shift

    def bar_of(t_out):
        return int(math.floor(T(t_out) / bar + 1e-6))

    drop_b = bar_of(E.DROP)
    build_b = bar_of(E.MUSIC.s)          # build starts on the bar that holds "add music"
    old_a, old_b = bar_of(E.SEC["old"][0]), bar_of(E.FLIPS.w(2))
    no_a, no_b = bar_of(E.NOAE.s), bar_of(E.WATCHED.s)
    end_b = bar_of(E.END_A)
    prog_ = [1, 5, 6, 4]
    S.track("kick", gain_db=0)
    S.track("snare", rev=0.12, gain_db=-5)
    S.track("hats", rev=0.05, gain_db=-11)
    S.track("bass", sc=0.6, gain_db=-3)
    S.track("keys", rev=0.25, sc=0.45, gain_db=-6)
    S.track("pluck", rev=0.2, dly=0.22, sc=0.3, gain_db=-9)
    S.track("pad", rev=0.35, gain_db=-9)
    S.track("lead", rev=0.25, dly=0.2, sc=0.3, gain_db=-8)
    S.track("fx", rev=0.3, gain_db=-4)
    K = mu.kick(50, 1.0, 0.34)
    for b in range(nb):
        deg = prog_[b % 4]
        ch = S.chord(deg, 4, 4)
        t0 = S.at_bar(b)
        in_build = build_b <= b < drop_b
        post = b >= drop_b
        is_no = no_a <= b < no_b
        is_end = b >= end_b
        energy = 0.5 if b < old_a else 0.35 if b < old_b else 0.6 if b < build_b else 0.8 if in_build else 1.0
        # harmony
        if not is_no:
            if b < drop_b or is_end:
                S.add("pad", mu.pad(ch, bar + 0.4, 1300 if b < old_b else 1900), t0)
            for i in range(4 if b < old_b else 8):
                if is_end and i > 3:
                    break
                note = ch[[0, 2, 1, 3, 2, 1, 3, 0][i]] + 12
                S.add("pluck", mu.marimba(note, 0.5), t0 + i * S.beat * (1 if b < old_b else 0.5),
                      -2 if i % 2 else 0, pan=0.3 * (1 if i % 2 else -1))
            if post and not is_end:
                for r, ln in ((0, 0.45), (0.75, 0.4), (1.5, 0.4), (2.5, 0.45), (3.25, 0.35)):
                    S.add("keys", mu.epiano(ch[0] + 12, S.beat * ln) + mu.epiano(ch[2] + 12, S.beat * ln) * 0.8,
                          S.at_bar(b, r))
        # bass
        if b >= 1 and not in_build and not is_end and not is_no:
            bn = S.deg(deg, 2)
            for r in ((0, 1.5, 2.5, 3.5) if post else (0, 2)):
                S.add("bass", mu.sub(bn, S.beat * (0.8 if post else 1.6)), S.at_bar(b, r))
        if is_no:            # the three "No"s: a single stab + sub on each
            pass
        # drums
        if b >= 1 and not in_build and not is_end and not is_no:
            for i in range(4):
                if b >= old_b or i % 2 == 0:
                    S.add("kick", K, S.at_bar(b, i), 0 if post else -3)
            if b >= old_b:
                S.add("snare", mu.clap(), S.at_bar(b, 1))
                S.add("snare", mu.clap(), S.at_bar(b, 3))
            for i in range(8 if post else 4):
                S.add("hats", mu.hat(False, vel=0.35 + 0.3 * (i % 2)),
                      S.at_bar(b, i / (2 if post else 1) + (0.5 if not post else 0)), pan=0.25)
        if post and not is_end and not is_no and drop_b <= b < bar_of(E.SEC["every"][1]) + 1:
            mel = [5, 6, 8, 6, 5, 3, 5, 6]
            for i in range(8):
                S.add("lead", mu.vox(S.deg(mel[i], 5), S.beat * 0.42, "aeo"[i % 3]), S.at_bar(b, i / 2), -2,
                      pan=0.2 * math.sin(i))
    # transitions
    tb, td = S.at_bar(build_b), S.at_bar(drop_b)
    S.add("snare", mu.snare_roll(td - tb, 2, 32, 210), tb, -3)
    S.add("fx", mu.riser(td - tb), tb, 0)
    S.add("fx", mu.impact(2.6), td, 0)
    S.add("fx", mu.crash(2.6), td, -4)
    S.filter_auto("pluck", lambda t_: np.where((t_ >= S.at_bar(old_a)) & (t_ < S.at_bar(old_b)), 900, 14000))
    S.filter_auto("keys", lambda t_: np.full_like(t_, 9000))
    S.filter_auto("pad", lambda t_: np.where((t_ >= tb) & (t_ < td), 600 + 8000 * ((t_ - tb) / (td - tb)) ** 2,
                                             np.where(t_ < S.at_bar(old_b), 1400, 6000)))
    for ph in (E.NOAE, E.NOPR, E.NOKF):          # stabs on each "No"
        ch = S.chord(1, 4, 4)
        S.add("keys", mu.epiano(ch[0] + 12, 0.5) + mu.epiano(ch[2] + 12, 0.5), T(ph.s), 2)
        S.add("bass", mu.sub(S.deg(1, 2), 0.45), T(ph.s), 2)
        S.add("kick", K, T(ph.s), 0)
    # final chord on the end card
    S.add("keys", sum(mu.epiano(n_ + 12, 2.6) for n_ in S.chord(1, 4, 4)) * 0.6, T(E.END_A + 0.05), 0)
    S.add("fx", mu.impact(2.0), T(E.END_A), -6)
    mix = S.master(out_db=-1.0)
    i0 = int(shift * SR)
    m = mix[i0: i0 + int(total * SR)]
    if len(m) < int(total * SR):
        m = np.pad(m, ((0, int(total * SR) - len(m)), (0, 0)))
    # tape stop on "flips": the old-way groove winds down into the page flip
    ts = int((E.FLIPS.w(2) - 0.45) * SR)
    te = int(E.FLIPS.w(2) * SR)
    seg = m[ts:te].copy()
    ln = te - ts
    pos = np.cumsum(np.linspace(1.0, 0.05, ln))
    pos = np.clip(pos, 0, ln - 1)
    for ch_ in range(2):
        m[ts:te, ch_] = np.interp(pos, np.arange(ln), seg[:, ch_]) * np.linspace(1, 0.2, ln)
    return m.astype(np.float32)


# ================================================================== sound effects
def sfx_rip():
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    am = (np.random.default_rng(3).random(n // 240 + 1) ** 3).repeat(240)[:n]
    x = mu.filt(mu.noise(n), "bp", (900, 6500)) * am * np.exp(-t * 3) * np.clip(t / 0.02, 0, 1)
    return (x / (np.abs(x).max() + 1e-9) * 0.9).astype(np.float32)


def sfx_slap():
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    x = mu.filt(mu.noise(n), "bp", (300, 3500)) * np.exp(-t * 55) + 0.6 * np.sin(2 * np.pi * 160 * t) * np.exp(-t * 40)
    return (x / (np.abs(x).max() + 1e-9) * 0.9).astype(np.float32)


def sfx_flip():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    flutter = 0.5 + 0.5 * np.sin(2 * np.pi * (28 - 40 * t) * t)
    x = mu.filt(mu.noise(n), "bp", (500, 5000)) * flutter * np.sin(np.pi * t / 0.35) ** 2
    return (x / (np.abs(x).max() + 1e-9) * 0.8).astype(np.float32)


def sfx_snip():
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    x = mu.filt(mu.noise(n), "hp", 3500) * np.exp(-t * 70) + 0.4 * np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 90)
    return (x / (np.abs(x).max() + 1e-9) * 0.9).astype(np.float32)


def sfx_stamp():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * (90 + 120 * np.exp(-t * 30)) * t) * np.exp(-t * 14) + \
        0.5 * mu.filt(mu.noise(n), "lp", 1800) * np.exp(-t * 35)
    return (x / (np.abs(x).max() + 1e-9) * 0.95).astype(np.float32)


def sfx_pen():
    n = int(0.22 * SR)
    t = np.arange(n) / SR
    x = mu.filt(mu.noise(n), "bp", (2000, 7000)) * (0.4 + 0.6 * np.abs(np.sin(2 * np.pi * 9 * t))) * np.exp(-t * 6)
    return (x / (np.abs(x).max() + 1e-9) * 0.6).astype(np.float32)


def sfx_slate():
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    x = mu.filt(mu.noise(n), "bp", (600, 4000)) * np.exp(-t * 60) + 0.7 * np.sin(2 * np.pi * 900 * t) * np.exp(-t * 50)
    return (x / (np.abs(x).max() + 1e-9) * 0.95).astype(np.float32)


def sfx_clock(dur=0.9):
    out = np.zeros(int(dur * SR), np.float32)
    tk = ak.SFX["tick"]()
    for i in range(int(dur / 0.075)):
        j = int(i * 0.075 * SR)
        seg = tk[: len(out) - j]
        out[j: j + len(seg)] += seg * (0.7 if i % 2 else 1.0)
    return out


def sfx_beep():
    n = int(0.16 * SR)
    t = np.arange(n) / SR
    return (0.5 * np.sin(2 * np.pi * 1320 * t) * np.clip(t / 0.005, 0, 1) * np.clip((0.16 - t) / 0.02, 0, 1)).astype(np.float32)


FX = dict(ak.SFX)
FX.update(rip=sfx_rip, slap=sfx_slap, flip=sfx_flip, snip=sfx_snip, stamp=sfx_stamp, pen=sfx_pen, slate=sfx_slate,
          clock=sfx_clock, beep=sfx_beep)


def cues():
    """[(t, kind, gain_db, pan)] on the output clock."""
    out = []

    def a(t, kind, g=-12, pan=0.0):
        out.append((t, kind, g, pan))

    a(0.0, "whoosh", -14)
    a(0.02, "impact", -16)
    a(E.TEAR_T - 0.02, "rip", -8)
    for t in cut.CUT_TIMES:                       # every jump cut: a soft tick
        a(t, "tick", -24)
    for g in E.GROUPS:                            # caption slams: soft pop per line, louder on accent words
        if E.in_any(g["s"] + 0.05, E.CAP_OFF):
            continue
        a(g["s"] + 0.03, "click", -27)
        for w in g["words"]:
            if w["i"] in E.ACC:
                a(w["os"], "pop", -22, 0.1)
    for T in E.WHIPS:
        a(T - 0.16, "whoosh", -11, -0.2)
    for T in E.FLIPS_T:
        a(T - 0.14, "flip", -9)
    # stickers slapping on
    stickers = [E.HOOK.w(3) + 0.05, E.NOTICED.w(4), E.YEARS.s, E.SIT.s, E.HOURS.w(2), E.REEL60.w(3), E.FLIPS.e - 0.05,
                E.BRIEF.w(4) - 0.05, E.BRIEF.w(6), E.MUSIC.s, E.CODE.s - 0.05, E.LAPTOP.w(3) - 0.1,
                E.NOTJUST.w(4) - 0.08, E.NEED.w(5) - 0.05, E.FOOTAGE.s - 0.1, E.SKILLS.s - 0.05, E.COURSE.w(2),
                E.WATCHED.s + 0.5, E.NOAPP.w(5) - 0.05, E.END_A + 0.5, E.END_A + 0.9]
    stickers += [ph.w(1) - 0.03 for ph in E.EVERY] + [ph.s - 0.04 for ph in E.FORMATS]
    stickers += [E.SKILLS.w(2) + i * 0.09 for i in range(6)]
    for t in stickers:
        a(t, "slap", -13, (hash(round(t, 2)) % 7 - 3) / 6)
    a(E.YEARS.s + 0.05, "clock", -18)                     # calendar rolling
    for j in range(11):                                  # keyframes popping on
        a(E.KEYS.s + j * 0.06, "tick", -17, -0.3 + j * 0.06)
    a(E.DRAG.s, "swish", -16)
    a(E.HOURS.w(2), "clock", -13)
    a(E.DIRECT.w(1) + 0.05, "slate", -6)
    a(E.DIRECT.w(1) + 0.05, "impact", -12)
    for ph in E.BRIEF_ITEMS:                             # typing each brief line, pen tick when done
        a(ph[1].s - 0.02, "typing", -17)
        a(ph[1].e + 0.12, "pen", -14)
    a(E.CUTP.w(0), "snip", -9)
    a(E.CUTP.w(0) + 0.22, "snip", -10)
    for j in range(4):
        a(E.PUNCHY.w(j), "impact", -15 + j * 1.5)
    a(E.TITLE.w(2) - 0.03, "impact", -9)
    a(E.TITLE.w(2) - 0.05, "whoosh", -14)
    a(E.CINE.s - 0.06, "bass_drop", -10)
    a(E.CINE.s - 0.04, "shutter", -14)
    a(E.DROP, "impact", -4)
    a(E.DROP + 0.02, "stamp", -8)
    a(E.DROP + 0.05, "sparkle", -12)
    for i in range(5):
        a(E.CODE.s + i * 0.24, "typing", -19)
    a(E.SEC["fifty"][0], "whoosh", -12)
    for i in range(0, 50, 2):
        a(E.SEC["fifty"][0] + 0.15 + i * 1.3 / 50, "tick", -22, -0.4 + i / 60)
    a(E.TEST.w(3), "pen", -10)
    a(E.TEST.w(4), "stamp", -8)
    for ph in (E.FOOTAGE, E.YLAPTOP, E.VES):
        a(ph.s - 0.05, "pen", -15)
        a(ph.e, "pen", -11)
    for i in range(6):
        a(E.SHOWS.w(7) + i * 0.1, "pen", -17)
    for ph in E.NO_ITEMS:
        a(ph[1].s, "stamp", -6)
        a(ph[1].w(1) + 0.05, "pen", -12)
    a(E.SEC["reveal"][0], "whoosh", -10, 0.2)
    a(E.NOAPP.w(5) + 0.2, "pen", -10)
    a(E.NOAPP.w(5) + 0.35, "pen", -10)
    a(E.RECORDED.w(2), "beep", -12)
    a(E.RECORDED.w(2), "glitch", -18)
    a(E.REST.w(2), "whoosh", -13)
    a(E.REST.w(4), "sparkle", -9)
    a(E.END_A, "whoosh", -10)
    a(E.END_A + 1.2, "typing", -14)
    a(E.END_A + 1.9, "ding", -9)
    a(E.END_A + 1.95, "pop", -14)
    return out


# ================================================================== mix
def build():
    total = E.TOTAL
    n = int(total * SR)
    v = voice()[:n]
    v = np.pad(v, ((0, n - len(v)), (0, 0)))
    mus = score(total)[:n]
    duck = ak.duck_gain(v, depth_db=-11, attack=0.02, release=0.3, thresh=0.015)
    mus = mus * duck[:, None]
    fx = np.zeros((n, 2), np.float32)
    for t, kind, g, pan in cues():
        clip = FX[kind]() if kind not in ("typing", "whoosh") else (FX[kind](0.6) if kind == "typing" else FX[kind](0.4))
        ak.place(fx, clip, max(0.0, t), g, pan)
    fx = fx * (0.55 + 0.45 * duck)[:, None]       # effects tuck under the voice too
    mix = v * ak.db(0) + mus * ak.db(-1.5) + fx * ak.db(1)
    pk = np.abs(mix).max()
    if pk > 0.98:
        mix = np.tanh(mix / pk * 1.2) / math.tanh(1.2) * 0.98
    raw = WORK / "mix_raw.wav"
    wavfile.write(raw, SR, mix.astype(np.float32))
    for nm, x in (("voice", v), ("music", mus * ak.db(-1.5)), ("fx", fx)):
        wavfile.write(WORK / f"stem_{nm}.wav", SR, x.astype(np.float32))
    out = WORK / "mix.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", ak.loudnorm_filter(raw, -14.0),
                    "-ar", str(SR), "-c:a", "pcm_s16le", str(out)], check=True)
    print("mix ->", out)
    return out


if __name__ == "__main__":
    build()
