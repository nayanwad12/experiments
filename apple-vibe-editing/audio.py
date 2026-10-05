"""Soundtrack: original 120 BPM bed + close-mic ASMR foley + narration, all synthesised here.
    python3 audio.py      -> work/music.wav, work/sfx.wav, work/voice.wav, work/mix.wav
"""
import json
import math
import sys

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

sys.path.insert(0, "vibe")
import audio_kit as ak  # noqa: E402
from timeline import *  # noqa: E402,F401,F403

SR = ak.SR
N = int(DURATION * SR)
rng = np.random.default_rng(3)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), x)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "lowpass", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "highpass", fs=SR, output="sos"), x)


def env(n, a, d, curve=5.0):
    i = np.arange(n) / SR
    att = np.clip(i / max(a, 1e-4), 0, 1)
    dec = np.exp(-np.clip(i - a, 0, None) * curve / max(d, 1e-4))
    return att * dec


def tone(f, dur):
    return np.sin(2 * np.pi * f * np.arange(int(dur * SR)) / SR)


def nz(dur):
    return rng.standard_normal(int(dur * SR))


def reverb_ir(dur=1.6, decay=3.2, damp=5000):
    n = int(dur * SR)
    ir = rng.standard_normal((n, 2)) * np.exp(-np.arange(n) / SR * decay)[:, None]
    ir = np.stack([lp(ir[:, 0], damp), lp(ir[:, 1], damp)], 1)
    ir[0] = 0
    return ir / np.sqrt((ir ** 2).sum(0))


IR = reverb_ir()


def verb(st, wet=0.2):
    out = np.stack([fftconvolve(st[:, ch], IR[:, ch])[: len(st)] for ch in range(2)], 1)
    return st + wet * out


def place(buf, clip, t, g_db=0.0, pan=0.0):
    ak.place(buf, clip, t, g_db, pan)


# ------------------------------------------------------------------ ASMR foley (mono, close & soft)
def s_tap(pitch=1.0):
    d = 0.09
    n = int(d * SR)
    click = bp(nz(d), 2500 * pitch, 9000) * env(n, 0.0004, 0.004, 6)
    body = tone(170 * pitch, d) * env(n, 0.001, 0.05, 5)
    return ak.norm(0.7 * click + 0.6 * body, 0.8)


def s_glass(f=2600):
    d = 0.5
    n = int(d * SR)
    x = (tone(f, d) + 0.45 * tone(f * 2.71, d) + 0.2 * tone(f * 5.1, d)) * env(n, 0.002, 0.35, 6)
    x += 0.4 * bp(nz(d), 4000, 12000) * env(n, 0.0005, 0.01, 6)
    return ak.norm(x, 0.6)


def s_bubble(f0=380, f1=1100):
    d = 0.07
    n = int(d * SR)
    f = np.linspace(f0, f1, n) ** 1
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * np.linspace(0, 1, n)) ** 0.6
    return ak.norm(x, 0.7)


def s_swipe(d=0.42, lo=500, hi=6000):
    n = int(d * SR)
    t = np.linspace(0, 1, n)
    shape = np.sin(np.pi * t ** 0.7) ** 2
    x = bp(nz(d), lo, hi) * shape
    cut = 600 + 7000 * shape
    x = ak.tvlp(x, cut)
    return ak.norm(x, 0.7)


def s_whoosh(d=0.6):
    n = int(d * SR)
    t = np.linspace(0, 1, n)
    shape = (t ** 2.2) * np.exp(-((t - 0.8) ** 2) / 0.03) + 0.2 * t ** 3
    shape /= shape.max()
    x = ak.tvlp(nz(d), 300 + 9000 * shape) * shape
    return ak.norm(x, 0.8)


def s_key(pitch=1.0):
    d = 0.08
    n = int(d * SR)
    clack = bp(nz(d), 1800 * pitch, 6500 * pitch) * env(n, 0.0003, 0.006, 6)
    thock = tone(210 * pitch, d) * env(n, 0.001, 0.03, 5) + 0.5 * lp(nz(d), 900) * env(n, 0.0005, 0.02, 5)
    rel = np.zeros(n)
    k = int(0.045 * SR)
    rel[k:] = 0.35 * bp(nz(d), 2500, 7000)[: n - k] * env(n - k, 0.0003, 0.004, 6)
    return ak.norm(clack + 0.8 * thock + rel, 0.8)


def s_enter():
    return ak.norm(s_key(0.8) + 0.6 * np.pad(s_key(0.7), (int(0.004 * SR), 0))[: int(0.08 * SR)], 0.9)


def s_scribble(d=0.3):
    n = int(d * SR)
    t = np.linspace(0, 1, n)
    grain = 0.6 + 0.4 * np.sin(2 * np.pi * 38 * t * d) ** 2
    x = bp(nz(d), 1800, 7000) * np.sin(np.pi * t) ** 0.5 * grain
    return ak.norm(x, 0.6)


def s_soft_hit():
    d = 1.6
    n = int(d * SR)
    f = 55 + 70 * np.exp(-np.arange(n) / SR * 18)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.003, 1.2, 4)
    air = lp(nz(d), 1800) * env(n, 0.001, 0.25, 5)
    return ak.norm(np.tanh(1.6 * (sub + 0.35 * air)), 0.95)


def s_shimmer():
    d = 1.4
    out = np.zeros(int(d * SR))
    notes = [72, 76, 79, 84, 88, 91]
    for i, m in enumerate(notes):
        s = int(i * 0.07 * SR)
        x = tone(ak.midi_hz(m + 12), d)[: len(out) - s] * env(len(out) - s, 0.003, 0.7, 5)
        out[s:] += x * (0.8 - i * 0.08)
    return ak.norm(out, 0.5)


def s_tick():
    d = 0.03
    n = int(d * SR)
    return ak.norm(tone(3200, d) * env(n, 0.0003, 0.012, 6) + 0.4 * bp(nz(d), 5000, 12000) * env(n, 0.0002, 0.003, 6), 0.6)


def s_riser(d):
    n = int(d * SR)
    t = np.linspace(0, 1, n)
    x = ak.tvlp(nz(d), 300 + 8000 * t ** 2) * t ** 2.5
    f = 220 * 2 ** (2 * t)
    x += 0.25 * np.sin(2 * np.pi * np.cumsum(f) / SR) * t ** 3
    return ak.norm(x, 0.7)


def s_fwoop(d=0.5):          # reverse whoosh into the zoom-out
    return ak.norm(s_whoosh(d)[::-1].copy(), 0.7)


def sfx_track():
    buf = np.zeros((N, 2), np.float32)
    P = lambda clip, t, g, pan=0.0: place(buf, clip, t, g, pan)  # noqa: E731
    # intro caret taps
    P(s_tap(1.2), 0.1, -16)
    P(s_tap(1.2), 0.32, -18)
    # app names: soft swipe into a crisp tap
    for i, th in enumerate(APP_HITS):
        P(s_swipe(0.3), th - 0.24, -17, [-0.3, 0.3, 0][i])
        P(s_tap(1 + 0.1 * i), th, -10)
        P(s_glass(2900 + 250 * i), th + 0.01, -24)
    P(s_whoosh(0.5), 3.05 - 0.42, -12)
    # notifications: glassy pings, stereo spread
    for i, tn in enumerate(NOTIF_T):
        P(s_glass(2300 + 140 * i), tn, -15, 0.35)
        P(s_tap(1.3), tn, -20, 0.35)
    # cards falling
    for i in range(7):
        P(s_swipe(0.25, 300, 3000), 5.27 + i * 0.035, -24, 0.4)
    P(s_tap(0.7), ANY_T, -12)
    P(s_swipe(0.5, 300, 4000), ANY_T - 0.3, -20)
    # into the era: zoom, riser, hit, shimmer
    P(s_whoosh(0.55), 7.75 - 0.45, -11)
    P(s_riser(1.05), VIBE_T - 1.05, -14)
    P(s_soft_hit(), VIBE_T, -5)
    P(s_shimmer(), SHIMMER_T, -16)
    P(s_tick(), CAPTION_T, -18)
    P(s_whoosh(0.5), 10.9 - 0.4, -12, -0.2)
    # keyframe diamonds popping like bubbles
    import scenes
    for idx in range(len(scenes.DIAMONDS)):
        td = DIAMOND_T + scenes.DIA_ORDER.index(idx) * 0.028
        P(s_bubble(rng.uniform(320, 520), rng.uniform(900, 1500)), td + 0.06, -17, rng.uniform(-0.6, 0.6))
    P(s_swipe(0.5, 400, 5000), MORPH_T, -17)
    # typing
    for tt, ch in zip(type_times(PROMPT, TYPE_T0, TYPE_T1), PROMPT):
        P(s_key(0.85 if ch == " " else rng.uniform(0.95, 1.12)), tt, -14 if ch != " " else -12, rng.uniform(-0.15, 0.15))
    P(s_enter(), ENTER_T, -8)
    P(s_whoosh(0.45), IRIS_T1 - 0.42, -11)
    P(s_soft_hit(), 15.0, -9)
    # features
    P(s_tap(0.9), SMOOTH_T, -16)
    P(s_tap(1.0), TRANSITIONS_T, -17)
    P(s_swipe(0.45), IRIS2_T0, -14)
    import random as _r
    rr = _r.Random(2)
    for i in range(12):
        t0 = (KINETIC_T if i < 7 else TYPE_WORD_T) + (i % 8) * 0.032
        P(s_bubble(rr.uniform(300, 600), rr.uniform(800, 1600)), t0 + 0.04, -16, rr.uniform(-0.5, 0.5))
    P(s_swipe(0.35), SOUND_PUSH_T - 0.05, -15, 0.3)
    P(s_tap(1.1), SOUND_T, -16)
    for tm, _ in MONTAGE:
        P(s_tap(0.8), tm, -9)
        P(s_tick(), tm, -14)
    # meta
    P(s_fwoop(0.45), 20.3, -12)
    P(s_tick(), FRAME_T, -12)
    for k in range(6):
        P(s_tick(), FRAME_T + 0.08 * (k + 1), -22 - k)
    P(s_glass(1900), SOUND2_T, -18)
    for tt, ch in zip(type_times(PROMPT2, PROMPT2_T0, PROMPT2_T1), PROMPT2):
        P(s_key(rng.uniform(1.0, 1.15)), tt, -18, rng.uniform(-0.1, 0.1))
    # nos
    P(s_whoosh(0.5), 24.75 - 0.42, -12)
    for t0 in NO_T:
        P(s_tap(0.9), t0, -11)
        P(s_scribble(0.32), t0 + 0.22, -14, 0.4)
        P(s_scribble(0.16), t0 + 0.5, -16, 0.4)
    # idea
    P(s_swipe(0.5, 300, 4000), 28.3 - 0.2, -18)
    for tw in IDEA_WORDS:
        P(s_tap(1.1), tw, -19)
    for tt, ch in zip(type_times(WORDS_LINE, WORDS_T0, WORDS_T1), WORDS_LINE):
        if ch != " ":
            P(s_key(rng.uniform(0.95, 1.1)), tt, -16, rng.uniform(-0.15, 0.15))
    # end
    P(s_whoosh(0.55), 32.35 - 0.45, -11)
    P(s_tap(1.0), WELCOME_T, -16)
    P(s_soft_hit(), LOGO_T, -5)
    P(s_shimmer(), LOGO_SHIMMER_T, -15)
    P(s_glass(2100), TAGLINE_T, -17)
    for i, ts in enumerate(STRIKES):
        P(s_scribble(0.26), ts, -15, -0.4 + 0.27 * i)
    P(s_soft_hit(), FINAL_HIT, -11)
    return verb(buf, 0.12)


# ------------------------------------------------------------------ music: 120 BPM, F major 7ths
BEAT = 60 / BPM
BAR = 4 * BEAT
PROG = [1, 3, 6, 4]           # Fmaj7 - Am7 - Dm7 - Bbmaj7
ROOT = 5


def kick_soft():
    d = 0.35
    n = int(d * SR)
    f = 48 + 110 * np.exp(-np.arange(n) / SR * 30)
    return 0.9 * np.tanh(1.8 * np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.28, 4))


def shaker(acc=1.0):
    d = 0.06
    n = int(d * SR)
    return 0.12 * acc * hp(nz(d), 6000) * env(n, 0.004, 0.04, 5)


def snap():
    d = 0.2
    n = int(d * SR)
    x = bp(nz(d), 1200, 5000) * env(n, 0.001, 0.09, 6)
    for off in (0.006, 0.013):
        i = int(off * SR)
        x[i:] += 0.5 * x[: n - i]
    return 0.32 * x


def section(t):
    """0 intro, 1 full, 2 breakdown, 3 final, 4 tail"""
    if t < VIBE_T:
        return 0
    if t < 29.0:
        return 1
    if t < 33.0:
        return 2
    if t < FINAL_HIT:
        return 3
    return 4


def music():
    n = N + SR * 2
    L = {k: np.zeros(n) for k in ("drums", "bass", "pad", "arp")}

    def add(tr, sig, t, g=1.0):
        i = int(t * SR)
        if i < 0 or i >= n:
            return
        sig = sig[: n - i]
        L[tr][i: i + len(sig)] += g * sig

    K, Sn = kick_soft(), snap()
    kicks = []
    bar_starts = [BAR0 - BAR] + [BAR0 + b * BAR for b in range(int((DURATION - BAR0) / BAR) + 1)]
    for bi, t0 in enumerate(bar_starts):
        deg = PROG[bi % 4]
        ch = ak.chord(ROOT, "major", deg, 4, True)
        sec = section(t0 + 0.01)
        if t0 >= FINAL_HIT:          # tail: one long final chord
            add("pad", ak.pad_chord(ak.chord(ROOT, "major", 1, 4, True), 3.2, 1600), t0, 1.2)
            add("bass", ak.bass_note(ROOT + 36 - 12, 2.6, 300), t0, 0.8)
            break
        cutoff = 1500 if sec in (0, 2) else 2400
        add("pad", ak.pad_chord(ch, BAR + 0.3, cutoff), max(t0, 0), 1.0 if t0 >= 0 else 0.6)
        # arp: 8ths, softly filtered in the intro
        arp = ch + [ch[0] + 12, ch[1] + 12]
        for i in range(8):
            tt = t0 + i * BEAT / 2
            if tt < 0.0:
                continue
            m = arp[[0, 2, 1, 3, 4, 3, 2, 5][i] % len(arp)] + 12
            sig = ak.pluck(m, BEAT * 1.4, 0.35 if sec in (0, 2) else 0.55)
            add("arp", sig, tt, 0.55 if sec in (0, 2) else 0.75)
        # bass
        bm = ch[0] - 24
        if sec in (1, 3):
            for i in range(4):
                add("bass", ak.bass_note(bm, BEAT * 0.42, 520), t0 + i * BEAT + BEAT / 2, 0.95)
        elif sec == 0 and t0 >= BAR0 + 2 * BAR:
            add("bass", ak.bass_note(bm, BAR * 0.9, 300), t0, 0.6)
        # drums
        for i in range(4):
            tb = t0 + i * BEAT
            if tb < 0:
                continue
            # gap before the iris / big moments
            if 14.42 <= tb < 15.0:
                continue
            if sec in (1, 3):
                add("drums", K, tb)
                kicks.append(tb)
                if i in (1, 3):
                    add("drums", Sn, tb, 0.9)
                for j in range(4):
                    add("drums", shaker(1.0 if j == 2 else 0.55), tb + j * BEAT / 4)
            elif sec == 0 and t0 >= BAR0:
                if i == 0:
                    add("drums", K, tb, 0.55)
                    kicks.append(tb)
                add("drums", shaker(0.7), tb + BEAT / 2)
                if t0 >= BAR0 + 2 * BAR:
                    add("drums", shaker(0.4), tb + BEAT / 4)
                    add("drums", shaker(0.4), tb + 3 * BEAT / 4)
            elif sec == 2:
                add("drums", shaker(0.5), tb + BEAT / 2)
    # side-chain pump
    g = np.ones(n)
    ln = int(BEAT * 0.9 * SR)
    shape = 1 - 0.6 * np.exp(-np.arange(ln) / (0.08 * SR))
    for kt in kicks:
        i = int(kt * SR)
        seg = g[i: i + ln]
        seg *= shape[: len(seg)]
    L["pad"] *= g
    L["arp"] *= 0.5 + 0.5 * g
    L["bass"] *= 0.55 + 0.45 * g
    dry = 0.9 * L["drums"] + 0.75 * L["bass"]
    wetsrc = 0.5 * L["pad"] + 0.45 * L["arp"]
    st = np.stack([dry + wetsrc * 1.05, dry + wetsrc * 0.95], 1)
    # ping-pong the arp a little for width
    d = int(BEAT * 0.75 * SR)
    echo = np.zeros_like(st)
    echo[d:, 0] = 0.22 * L["arp"][:-d]
    echo[2 * d:, 1] = 0.16 * L["arp"][:-2 * d]
    st = verb(st + echo, 0.18)[:N]
    # fade in, tail fade
    fi = int(0.4 * SR)
    st[:fi] *= np.linspace(0, 1, fi)[:, None]
    fo0, fo1 = int(37.6 * SR), int(DURATION * SR)
    st[fo0:fo1] *= np.linspace(1, 0, fo1 - fo0)[:, None] ** 1.5
    st = np.tanh(1.1 * st / np.max(np.abs(st))) * 0.85
    return st.astype(np.float32)


# ------------------------------------------------------------------ voice
def voice():
    meta = {m["id"]: m for m in json.load(open("work/vo.json"))}
    buf = np.zeros((N, 2), np.float32)
    for lid, t0 in VO.items():
        x = ak.read_audio(f"work/vo_{lid}.wav")[:, 0]
        x = hp(x, 80)
        # gentle presence lift + compression for a close, polished read
        pres = bp(x, 2500, 6000)
        x = x + 0.25 * pres
        x = np.tanh(2.0 * x / (np.max(np.abs(x)) or 1)) / math.tanh(2.0) * 0.8
        place(buf, x, t0, 0)
        assert lid in meta
    return verb(buf, 0.05)


def main():
    m, s, v = music(), sfx_track(), voice()
    ak.write_wav("work/music.wav", m)
    ak.write_wav("work/sfx.wav", s)
    ak.write_wav("work/voice.wav", v)
    duck = ak.duck_gain(v, -9)[:, None]
    mix = 0.5 * m * duck + 1.05 * s + 1.0 * v
    peak = np.max(np.abs(mix))
    mix = mix / peak * 0.95
    ak.write_wav("work/mix_raw.wav", mix)
    print("peak", peak)


if __name__ == "__main__":
    main()
