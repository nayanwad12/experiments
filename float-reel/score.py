"""score: the floating-UI cut's sound. Same cleaned voice as ../sticker-reel; a new groove (sub, plucks, bells,
shaker) with the drop on the same beat; UI sound design (pops for every element, toggle clicks, off-blips, typing).

    python3 score.py          -> work/mix.wav
"""

import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import skia
from scipy.io import wavfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reel as R  # noqa: E402  (also puts ../sticker-reel and reels/common on the path)
import soundtrack as ST  # noqa: E402  (voice clean-up + cut, SFX library)
import audio_kit as ak  # noqa: E402
import music as mu  # noqa: E402

SR = 48000
WORK = HERE / "work"


def groove(total):
    bpm = 100.0
    bar = 240.0 / bpm
    shift = (bar - R.DROP % bar) % bar
    S = mu.Song(total + shift + bar, bpm, "A", "minor", seed=33)
    nb = int((total + shift) / bar) + 2

    def bar_of(t_out):
        return int(math.floor((t_out + shift) / bar + 1e-6))

    drop_b, build_b = bar_of(R.DROP), bar_of(R.MUSIC.s)
    old_a, old_b = bar_of(R.SEC["years"][0]), bar_of(R.FLIPS.w(2))
    no_a, no_b = bar_of(R.NOAE.s), bar_of(R.WATCHED.s)
    end_b = bar_of(R.END_A)
    prog_ = [1, 6, 3, 7]
    S.track("kick", gain_db=0)
    S.track("snare", rev=0.15, gain_db=-5)
    S.track("hats", rev=0.05, gain_db=-12)
    S.track("bass", sc=0.55, gain_db=-2)
    S.track("pluck", rev=0.22, dly=0.25, sc=0.35, gain_db=-8)
    S.track("bell", rev=0.35, dly=0.2, gain_db=-12)
    S.track("pad", rev=0.4, gain_db=-10)
    S.track("lead", rev=0.25, dly=0.2, sc=0.3, gain_db=-9)
    S.track("fx", rev=0.3, gain_db=-4)
    K = mu.kick(48, 1.0, 0.38)
    for b in range(nb):
        deg = prog_[b % 4]
        ch = S.chord(deg, 4, 4)
        in_build, post = build_b <= b < drop_b, b >= drop_b
        is_no, is_end, is_old = no_a <= b < no_b, b >= end_b, old_a <= b < old_b
        t0 = S.at_bar(b)
        if not is_no:
            S.add("pad", mu.pad(ch, bar + 0.4, 1100 if is_old else 1800), t0)
            step = 0.5 if not is_old else 1.0
            for i in range(int(4 / step)):
                if is_end and i > 3:
                    break
                note = ch[[0, 2, 1, 3, 2, 3, 1, 2][i % 8]] + 12
                S.add("pluck", mu.pluck(note, S.beat * 0.45, 3200 if not post else 5200, 0.16),
                      t0 + i * step * S.beat, -1 if i % 2 else 0, pan=0.3 * (1 if i % 2 else -1))
            if b % 2 == 0 and not is_old:
                S.add("bell", mu.bell(ch[2] + 24, 1.4), t0 + S.beat * 1.5, pan=0.4)
        if b >= 1 and not in_build and not is_end and not is_no:
            bn = S.deg(deg, 2)
            for r in ((0, 0.75, 2, 2.75) if post else (0, 2)):
                S.add("bass", mu.sub(bn, S.beat * (0.6 if post else 1.6)), S.at_bar(b, r))
            for i in range(4):
                if not is_old or i % 2 == 0:
                    S.add("kick", K, S.at_bar(b, i) if post else S.at_bar(b, [0, 1.5, 2, 3.5][i]), 0 if post else -3)
            if not is_old:
                S.add("snare", mu.snare(200, 0.9, 0.16), S.at_bar(b, 1))
                S.add("snare", mu.snare(200, 0.9, 0.16), S.at_bar(b, 3))
            for i in range(8):
                swing = 0.08 if i % 2 else 0
                S.add("hats", mu.shaker(0.5 + 0.3 * (i % 2)) if not post else mu.hat(False, vel=0.4 + 0.3 * (i % 2)),
                      S.at_bar(b, i / 2 + swing), pan=0.25)
        if post and not is_end and not is_no and b < bar_of(R.SEC["every"][1]) + 1:
            mel = [5, 7, 8, 7, 5, 3, 5, 4]
            for i in range(8):
                S.add("lead", mu.pluck(S.deg(mel[i], 5), S.beat * 0.4, 6000, 0.2), S.at_bar(b, i / 2), -2)
    tb, td = S.at_bar(build_b), S.at_bar(drop_b)
    S.add("snare", mu.snare_roll(td - tb, 2, 32, 220), tb, -4)
    S.add("fx", mu.riser(td - tb), tb, 0)
    S.add("fx", mu.impact(2.6), td, 0)
    S.add("fx", mu.crash(2.4), td, -5)
    S.filter_auto("pad", lambda t_: np.where((t_ >= tb) & (t_ < td), 500 + 8000 * ((t_ - tb) / (td - tb)) ** 2, 5000))
    for ph in (R.NOAE, R.NOPR, R.NOKF):
        S.add("bass", mu.sub(S.deg(1, 2), 0.4), ph.w(1) + shift, 2)
        S.add("kick", K, ph.w(1) + shift, 0)
    S.add("bell", sum(mu.bell(n_ + 12, 2.5) for n_ in S.chord(1, 4, 3)) * 0.5, R.END_A + shift + 0.05, 0)
    S.add("fx", mu.impact(2.0), R.END_A + shift, -7)
    mix = S.master(out_db=-1.0)
    i0 = int(shift * SR)
    m = mix[i0: i0 + int(total * SR)]
    if len(m) < int(total * SR):
        m = np.pad(m, ((0, int(total * SR) - len(m)), (0, 0)))
    return m.astype(np.float32)


def sfx_toggle():
    out = np.zeros(int(0.12 * SR), np.float32)
    for j, f in ((0, 2600), (int(0.045 * SR), 3400)):
        t = np.arange(int(0.03 * SR)) / SR
        out[j: j + len(t)] += np.sin(2 * np.pi * f * t) * np.exp(-t * 180) * 0.7
    return out


def sfx_off():
    t = np.arange(int(0.22 * SR)) / SR
    f = 700 * np.exp(-t * 6)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 12) * 0.6).astype(np.float32)


def sfx_softpop():
    t = np.arange(int(0.09 * SR)) / SR
    f = 900 * np.exp(-t * 30) + 300
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 45) * 0.7).astype(np.float32)


FX = dict(ST.FX)
FX.update(toggle=sfx_toggle, off=sfx_off, softpop=sfx_softpop)


def ui_times():
    """run every UI drawer over the whole timeline on a tiny canvas; R.ui() logs each element's pop-in time."""
    surf = skia.Surface(54, 96)
    with surf as c:
        for f in range(0, int(R.TOTAL * 15)):
            t = f / 15
            c.save()
            c.scale(0.05, 0.05)
            s = R.section(t)
            R.UI.get(s, lambda c, t: None)(c, t)
            R.g_brief(c, t)
            R.g_lower(c, t)
            if s == "every":
                R.g_every(c, t)
            if s == "reveal":
                R.g_reveal(c, t, R.raw_amount(t))
            if s == "end":
                R.g_end_front(c, t)
            c.restore()
    return sorted(R.UI_LOG)


def cues():
    out = []

    def a(t, kind, g=-12, pan=0.0):
        out.append((t, kind, g, pan))

    a(0.0, "whoosh", -14)
    for i, t in enumerate(ui_times()):
        a(t, "softpop", -17, ((i * 37) % 9 - 4) / 6)
    for t in ST.cut.CUT_TIMES:
        a(t, "tick", -25)
    for g in R.GROUPS:
        if R.SK.in_any(g["s"] + 0.05, R.CAP_OFF):
            continue
        for w in g["words"]:
            if w["i"] in R.ACC:
                a(w["os"], "pop", -20)
                a(w["os"] + 0.08, "pen", -22)
                break
    for T in R.CUTS_FX:
        a(T - 0.14, "whoosh", -11)
    a(R.HOOK.w(3) - 0.05, "sparkle", -14)
    a(R.NOTICED.w(4), "toggle", -12)
    a(R.YEARS.s + 0.05, "clock", -18)
    for j in range(11):
        a(R.KEYS.s + j * 0.06, "tick", -18, -0.3 + j * 0.06)
    a(R.DRAG.s, "swish", -16)
    a(R.HOURS.w(2), "clock", -14)
    a(R.FLIPS.w(2) + 0.05, "toggle", -9)
    a(R.DIRECT.w(1) - 0.05, "swish", -12)
    a(R.DIRECT.w(1), "impact", -13)
    a(R.TELL.s, "typing", -16)
    a(R.BRIEF.s, "typing", -16)
    for lab, ph in R.ROWS:
        a(ph.e + 0.08, "toggle", -9)
    a(R.CUTP.w(0), "snip", -11)
    for j in range(4):
        a(R.PUNCHY.w(j), "impact", -16 + j * 1.5)
    a(R.TITLE.w(2) - 0.03, "impact", -9)
    a(R.CINE.s - 0.06, "bass_drop", -10)
    a(R.CINE.s - 0.04, "shutter", -14)
    a(R.DROP, "impact", -4)
    a(R.DROP + 0.05, "sparkle", -10)
    for i in range(4):
        a(R.CODE.s + i * 0.26, "typing", -19)
    for ph in R.FORMATS:
        a(ph.s - 0.05, "swish", -18)
    for i in range(0, 50, 2):
        a(R.SEC["fifty"][0] + 0.1 + i * 1.3 / 50, "tick", -22, -0.4 + i / 60)
    a(R.TEST.w(3), "ding", -12)
    for ph in (R.FOOTAGE, R.YLAPTOP, R.VES):
        a(ph.e, "ding", -15)
    for i in range(6):
        a(R.SHOWS.w(7) + i * 0.1, "tick", -16)
    for lab, ph in R.NO_ROWS:
        a(ph.w(1), "off", -8)
        a(ph.w(1), "toggle", -12)
    a(R.NOAPP.w(5) + 0.15, "pen", -12)
    a(R.RECORDED.w(2) - 0.05, "glitch", -14)
    a(R.RECORDED.w(2), "beep", -13)
    a(R.REST.w(2), "glitch", -14)
    a(R.REST.w(4), "sparkle", -9)
    a(R.END_A + 1.1, "typing", -14)
    a(R.END_A + 1.75, "ding", -9)
    return out


def build():
    total = R.TOTAL
    n = int(total * SR)
    v = ST.voice()[:n]
    v = np.pad(v, ((0, n - len(v)), (0, 0)))
    mus = groove(total)[:n]
    duck = ak.duck_gain(v, depth_db=-11, attack=0.02, release=0.3, thresh=0.015)
    mus = mus * duck[:, None]
    fx = np.zeros((n, 2), np.float32)
    for t, kind, g, pan in cues():
        clip = FX[kind](0.6) if kind == "typing" else FX[kind](0.4) if kind == "whoosh" else FX[kind]()
        ak.place(fx, clip, max(0.0, t), g, pan)
    fx = fx * (0.55 + 0.45 * duck)[:, None]
    mix = v + mus * ak.db(0.5) + fx * ak.db(1)
    pk = np.abs(mix).max()
    if pk > 0.98:
        mix = np.tanh(mix / pk * 1.2) / math.tanh(1.2) * 0.98
    WORK.mkdir(exist_ok=True)
    raw = WORK / "mix_raw.wav"
    wavfile.write(raw, SR, mix.astype(np.float32))
    wavfile.write(WORK / "stem_voice.wav", SR, v.astype(np.float32))
    wavfile.write(WORK / "stem_music.wav", SR, (mus * ak.db(0.5)).astype(np.float32))
    out = WORK / "mix.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", ak.loudnorm_filter(raw, -14.0),
                    "-ar", str(SR), "-c:a", "pcm_s16le", str(out)], check=True)
    print("mix ->", out, f"({len(cues())} sfx cues)")
    return out


if __name__ == "__main__":
    build()
