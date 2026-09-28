"""Talking-head reel editor: silence cuts, punch-in jump cuts, word-by-word paper captions,
paper-cut stickers, a full-screen title card, end card, SFX and a ducked music bed.

    python3 edit.py            -> out/reel.mp4  (+ out/before_after.mp4)
"""

import json
import zlib
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
import skia
from scipy.io import wavfile
from scipy.signal import butter, resample_poly, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "vibe-editing-promo"))

import audio as A  # noqa: E402
import scenes  # noqa: E402
from paper import (BLUSH, BLUSH_D, ICE, INK, LIME, PAPER, PERI, PERI_D, Ctx, R, circ_pts, draw_text, eob,  # noqa: E402
                   eoc, lerp, paper, pop, rect_pts, rgb, rrect_pts, sparkle_pts, text_width)

import imageio_ffmpeg  # noqa: E402

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
RAW = os.path.join(HERE, "raw", "raw.mp4")
OUT = os.path.join(HERE, "out")
W, H, FPS = 1080, 1920, 30
SW, SH = 576, 1024
SR = 44100
END_CARD = 2.6

# ------------------------------------------------------------------ edit decision list
WORDS = json.load(open(os.path.join(HERE, "work", "words.json")))
for w in WORDS:
    w["d"] = w["d"].upper()


def build_cuts(words, join_gap=0.30, pre=0.09, post=0.14):
    runs = []
    for w in words:
        if runs and w["s"] - runs[-1][1] < join_gap:
            runs[-1][1] = w["e"]
        else:
            runs.append([w["s"], w["e"]])
    keep = []
    for a, b in runs:
        a, b = max(0.0, a - pre), b + post
        if keep and a <= keep[-1][1]:
            keep[-1][1] = b
        else:
            keep.append([a, b])
    return keep


KEEP = build_cuts(WORDS)
SEG = []  # (src_a, src_b, out_a)
_t = 0.0
for a, b in KEEP:
    SEG.append((a, b, _t))
    _t += b - a
TALK_DUR = _t
TOTAL = TALK_DUR + END_CARD


def src_to_out(ts):
    for a, b, o in SEG:
        if ts < a:
            return o
        if ts <= b:
            return o + ts - a
    return TALK_DUR


def out_to_src(t):
    for i, (a, b, o) in enumerate(SEG):
        if t < o + (b - a):
            return a + (t - o), i
    a, b, o = SEG[-1]
    return b, len(SEG) - 1


for w in WORDS:
    w["os"], w["oe"] = src_to_out(w["s"]), src_to_out(w["e"])


def wi(word, n=1):
    """output start time of the n-th occurrence of a word."""
    k = 0
    for w in WORDS:
        if w["d"].strip(".,?'") == word.upper():
            k += 1
            if k == n:
                return w["os"]
    raise KeyError(word)


def we(word, n=1):
    k = 0
    for w in WORDS:
        if w["d"].strip(".,?'") == word.upper():
            k += 1
            if k == n:
                return w["oe"]
    raise KeyError(word)


# title card over "You direct. AI edits."
CARD_A, CARD_B = wi("YOU", 1) - 0.05, we("EDITS") + 0.25


# ------------------------------------------------------------------ captions
EMPH = {"FOUR", "HOURS", "THIRTY", "CREATE", "DIRECTING", "AI", "POP", "RAW", "TIMELINE", "TASTE",
        "STORYTELLING", "VIBE", "EDITING", "IDEABRO", "INSIDE", "SILENCES", "CAPTIONS"}


def word_w(w, size=104):
    # room for the pop-up scale of the highlighted (and emphasised) word
    grow = 1.24 if w["d"].strip(".,?'") in EMPH else 1.14
    return text_width(w["d"], size) * grow + 40


def build_phrases(budget=990):
    phrases, cur = [], []
    for i, w in enumerate(WORDS):
        if cur and (sum(map(word_w, cur)) + word_w(w) > budget or len(cur) >= 3
                    or w["os"] - cur[-1]["oe"] > 0.12 or w["oe"] - cur[0]["os"] > 1.2):
            phrases.append(cur)
            cur = []
        cur.append(w)
    phrases.append(cur)
    return phrases


PHRASES = build_phrases()


def draw_captions(ctx, t):
    if CARD_A <= t < CARD_B or t >= TALK_DUR:
        return
    ph = None
    for p in PHRASES:
        if p[0]["os"] - 0.05 <= t < (p[-1]["oe"] + 0.35):
            ph = p
    if not ph:
        return
    size = 104
    widths = [word_w(w, size) for w in ph]
    total = sum(widths)
    sc = min(1.0, 960 / total)
    x = 540 - total * sc / 2
    for j, w in enumerate(ph):
        cx = x + widths[j] * sc / 2
        x += widths[j] * sc
        if t < w["os"] - 0.03:
            continue
        cur = w["os"] - 0.03 <= t < w["oe"] + 0.05 or (j == len(ph) - 1 and t >= w["os"])
        key = w["d"].strip(".,?'")
        emph = key in EMPH
        s = pop(t, w["os"] - 0.03, 0.16) * sc * (1.12 if cur else 1.0) * (1.08 if emph else 1.0)
        back = (BLUSH if emph else LIME) if cur else PAPER
        draw_text(ctx, w["d"], cx, 1500, size, fill=INK, back=back, under=PERI if emph else None,
                  rot=(-3 if j % 2 else 3), sc=s, seed=zlib.crc32(w["d"].encode()) % 997 + j, pad=0.13, depth=1.6)


# ------------------------------------------------------------------ stickers
def tag(ctx, t, t0, t1, text, x, y, size=70, fill=INK, back=LIME, rot=0.0, seed=0, strike=False, out=0.18):
    if t < t0 or t > t1 + out:
        return
    s = pop(t, t0, 0.22)
    if t > t1:
        s *= 1 - eoc((t - t1) / out)
    draw_text(ctx, text, x, y, size, fill=fill, back=back, rot=rot, sc=s, seed=seed, pad=0.2, depth=2)
    if strike and t > t0 + 0.25:
        k = eoc((t - t0 - 0.25) / 0.15)
        wd = text_width(text, size) + 30
        ctx.push(x, y, rot - 6, s)
        paper(ctx, rect_pts(-wd / 2 + wd * k / 2, 0, wd * k, 16), BLUSH_D, seed + 9, depth=1.2, amp=1.2,
              outline=(INK, 4))
        ctx.pop()


def bubble(ctx, t, t0, t1, text, y, seed):
    if t < t0 or t > t1 + 0.2:
        return
    x = lerp(-500, 400, eob((t - t0) / 0.22))
    if t > t1:
        x = lerp(400, 1600, eoc((t - t1) / 0.2))
    n = min(len(text), int((t - t0) / 0.035) + 1)
    wd = text_width(text, 64, "bold") + 110
    ctx.push(x, y, -2, 1, wob=1, seed=seed)
    paper(ctx, rrect_pts(0, 0, wd + 14, 124, 50), INK, seed, depth=2.5, amp=1)
    paper(ctx, [(-wd / 2 + 40, 50), (-wd / 2 + 10, 95), (-wd / 2 + 90, 55)], INK, seed + 1, depth=0, amp=0.5)
    paper(ctx, rrect_pts(0, 0, wd, 110, 44), PAPER, seed + 2, depth=0, amp=0.8)
    draw_text(ctx, text[:n], -wd / 2 + 50, 0, 64, back=None, font="bold", align="l", seed=seed + 3, depth=0,
              wob=0.4, maxw=0)
    ctx.pop()


def logo_card(ctx, t, t0, t1, x, y, scale):
    if t < t0 or t > t1 + 0.2:
        return
    d = t - t0
    s = lerp(1.8, 1.0, (d / 0.1) ** 3) if d < 0.1 else 1.0
    if t > t1:
        s *= 1 - eoc((t - t1) / 0.2)
    ctx.push(x, y, -3, s * scale, wob=1, seed=700)
    paper(ctx, rrect_pts(0, 0, 920, 640, 40), INK, 701, depth=4, amp=2)
    draw_text(ctx, "VIBE", 0, -150, 270, fill=LIME, back=None, under=PERI_D, seed=702, depth=0, wob=0.6)
    draw_text(ctx, "EDITING", 0, 70, 175, fill=PAPER, back=None, under=BLUSH_D, seed=703, depth=0, wob=0.6)
    draw_text(ctx, "by IDEABRO STUDIO", 0, 225, 62, fill=INK, back=BLUSH, seed=704, depth=1, pad=0.22, rot=2)
    ctx.pop()


def mini_timeline(ctx, t, t0, t1, x, y, seed=760):
    if t < t0 or t > t1 + 0.2:
        return
    s = pop(t, t0, 0.22)
    if t > t1:
        s *= 1 - eoc((t - t1) / 0.2)
    ctx.push(x, y, -4, s, wob=1, seed=seed)
    paper(ctx, rrect_pts(0, 0, 440, 170, 18), PAPER, seed, depth=2.5, amp=1.2, outline=(INK, 5))
    cols = [LIME, BLUSH, ICE, PERI]
    for r in range(3):
        for i in range(9):
            paper(ctx, rrect_pts(-176 + i * 44, -45 + r * 45, 36, 34, 5), cols[(r + i) % 4], seed + 1 + r * 9 + i,
                  depth=0, amp=0.6, outline=(INK, 2))
    if t > t0 + 0.3:  # big paper X
        k = eoc((t - t0 - 0.3) / 0.15)
        for a in (40, -40):
            ctx.push(0, 0, a, (k, 1))
            paper(ctx, rect_pts(0, 0, 360, 34), BLUSH_D, seed + 40 + a, depth=2, amp=1, outline=(INK, 5))
            ctx.pop()
    ctx.pop()


def burst(ctx, t, t0, x, y, n=10, seed=900):
    if not (t0 <= t < t0 + 0.6):
        return
    d = t - t0
    for i in range(n):
        r = R("burst", seed, i)
        a = r.uniform(0, math.tau)
        dist = eoc(d / 0.5) * r.uniform(120, 320)
        s = r.uniform(18, 40) * (1 - d / 0.6)
        ctx.push(x + math.cos(a) * dist, y + math.sin(a) * dist, d * 400)
        paper(ctx, sparkle_pts(0, 0, s), [LIME, PAPER, BLUSH, PERI][i % 4], seed + i, depth=1, amp=0.8)
        ctx.pop()


def draw_stickers(ctx, t):
    # HOOK
    tag(ctx, t, wi("FOUR"), we("CONTENT"), "4 HRS / REEL", 790, 330, 76, back=BLUSH, rot=8, seed=100)
    tag(ctx, t, wi("THIRTY"), we("CONTENT"), "30 SEC", 290, 470, 70, back=LIME, rot=-7, seed=101)
    # PROBLEM: tasks pile up
    tag(ctx, t, wi("CUTTING"), we("CREATE"), "CUT CLIPS", 270, 330, 64, back=ICE, rot=-6, seed=110)
    tag(ctx, t, wi("CAPTIONS"), we("CREATE"), "CAPTIONS", 800, 420, 64, back=LIME, rot=7, seed=111)
    tag(ctx, t, wi("KEYFRAMING"), we("CREATE"), "KEYFRAMES", 290, 530, 64, back=BLUSH, rot=-4, seed=112)
    tag(ctx, t, wi("ANIMATION"), we("CREATE"), "ANIMATION", 790, 640, 64, back=PERI, rot=5, seed=113)
    tag(ctx, t, wi("ENERGY"), we("CREATE"), "BATTERY 1%", 540, 250, 60, fill=PAPER, back=INK, rot=-2, seed=114)
    # TURN
    tag(ctx, t, wi("STOPPED"), we("DIRECTING") + 0.3, "EDITING", 540, 330, 96, back=PAPER, rot=-3, seed=120,
        strike=True)
    tag(ctx, t, wi("DIRECTING"), we("DIRECTING") + 0.5, "DIRECTING", 560, 500, 120, back=LIME, rot=4, seed=121)
    # REVEAL: prompts typed as chat bubbles
    end_reveal = we("ME")
    bubble(ctx, t, wi("CUT") - 0.05, end_reveal, "cut the silences", 290, 130)
    bubble(ctx, t, wi("ADD") - 0.05, end_reveal, "add captions", 440, 140)
    bubble(ctx, t, wi("MAKE") - 0.05, end_reveal, "make it pop", 590, 150)
    burst(ctx, t, wi("POP"), 700, 590, seed=160)
    tag(ctx, t, wi("AND", 2), end_reveal, "AI EDITS IT", 760, 760, 64, fill=PAPER, back=INK, rot=-5, seed=161)
    # PROOF
    tag(ctx, t, wi("RAW"), we("TIMELINE"), "RECORDED RAW", 540, 300, 76, back=BLUSH, rot=-4, seed=170)
    mini_timeline(ctx, t, wi("TOUCH"), we("TIMELINE") + 0.35, 540, 520)
    # SHIFT
    tag(ctx, t, wi("SOFTWARE"), we("STORYTELLING"), "SOFTWARE", 300, 330, 72, back=PAPER, rot=-5, seed=180,
        strike=True)
    tag(ctx, t, wi("TASTE"), we("STORYTELLING") + 0.3, "TASTE", 760, 430, 120, back=BLUSH, rot=6, seed=181)
    tag(ctx, t, wi("STORYTELLING"), we("STORYTELLING") + 0.3, "STORYTELLING", 540, 600, 100, back=PERI, rot=-3,
        seed=182)
    # CTA
    logo_card(ctx, t, wi("VIBE") - 0.02, wi("CAPTIONS", 3) - 0.05, 540, 470, 0.72)
    ce = we("WANT", 2)
    tag(ctx, t, wi("CAPTIONS", 3), ce, "CAPTIONS", 270, 300, 64, back=LIME, rot=-6, seed=190)
    tag(ctx, t, wi("MOTION"), ce, "MOTION GRAPHICS", 720, 390, 62, back=ICE, rot=5, seed=191)
    tag(ctx, t, wi("ANIMATIONS"), ce, "ANIMATIONS", 300, 490, 64, back=BLUSH, rot=-3, seed=192)
    tag(ctx, t, wi("ADS"), ce, "ADS", 800, 560, 80, back=PERI, rot=8, seed=193)
    if t >= wi("LINK"):
        s = pop(t, wi("LINK"), 0.25) * (1 + 0.06 * math.exp(-((t - wi("LINK")) % 0.4) / 0.1))
        ctx.push(540, 420, -2, s * 0.85, wob=1, seed=195)
        paper(ctx, rrect_pts(16, 16, 760, 190, 95), INK, 196, depth=1, amp=1.2)
        paper(ctx, rrect_pts(0, 0, 760, 190, 95), LIME, 197, depth=0, amp=1.2, outline=(INK, 7))
        draw_text(ctx, "ENROLL NOW", 0, 0, 104, back=None, seed=198, depth=0, wob=0.5, maxw=640)
        ctx.pop()
        tag(ctx, t, wi("LINK") + 0.2, TALK_DUR, "LINK IN BIO", 540, 600, 66, fill=PAPER, back=INK, rot=2, seed=199)


# ------------------------------------------------------------------ frame renderer
PUNCH = [1.0 if i % 2 == 0 else 1.13 for i in range(len(SEG))]
FOCUS = (540, 900)  # eyes sit a little above centre


def grade_paint():
    p = skia.Paint()
    s, c = 1.12, 1.07
    lr, lg, lb = 0.2126, 0.7152, 0.0722
    m = []
    for i, base in enumerate((lr, lg, lb)):
        row = [(1 - s) * lr, (1 - s) * lg, (1 - s) * lb]
        row[i] += s
        row = [v * c for v in row]
        m += row + [0, (1 - c) * 0.5 + 0.012 * (1 if i == 0 else -0.5 if i == 2 else 0)]
    m += [0, 0, 0, 1, 0]
    p.setColorFilter(skia.ColorFilters.Matrix(m))
    return p


class Renderer:
    def __init__(self):
        self.surf = skia.Surface(W, H)
        self.ov = skia.Surface(W, H)
        self.card = skia.Surface(W, H)
        self.grade = grade_paint()
        self.ov_key = None
        self.card_key = None

    def overlay(self, t):
        step = int(t * 12)
        if step != self.ov_key:
            c = self.ov.getCanvas()
            c.clear(skia.ColorTRANSPARENT)
            ctx = Ctx(c, 5000 + step, t)
            n = c.getSaveCount()
            draw_stickers(ctx, step / 12)
            c.restoreToCount(n)
            self.ov_img = self.ov.makeImageSnapshot()
            self.ov_key = step
        return self.ov_img

    def card_img(self, fn, local, key):
        lstep = int(local * 12)
        k = (key, lstep)
        if k != self.card_key:
            c = self.card.getCanvas()
            c.clear(rgb(PAPER))
            n = c.getSaveCount()
            fn(Ctx(c, 9000 + lstep), lstep / 12)
            c.restoreToCount(n)
            self.card_im = self.card.makeImageSnapshot()
            self.card_key = k
        return self.card_im

    def frame(self, t, src_img, seg_i):
        c = self.surf.getCanvas()
        c.clear(rgb(INK))
        if t >= TALK_DUR:          # end card
            c.drawImage(self.card_img(scenes.s_cta, 0.25 + (t - TALK_DUR), "cta"), 0, 0)
            return self.finish(c, t)
        z = PUNCH[seg_i]
        # a quick zoom-settle on every jump cut sells the edit
        a, b, o = SEG[seg_i]
        z += 0.03 * math.exp(-(t - o) / 0.12)
        c.save()
        c.translate(FOCUS[0], FOCUS[1])
        c.scale(z, z)
        c.translate(-FOCUS[0], -FOCUS[1])
        c.scale(W / SW, H / SH)
        c.drawImage(src_img, 0, 0, skia.SamplingOptions(skia.CubicResampler.Mitchell()), self.grade)
        c.restore()
        if CARD_A <= t < CARD_B:
            local = 0.1 + (t - CARD_A) * 0.6
            c.drawImage(self.card_img(scenes.s_payoff, local, "payoff"), 0, 0)
        else:
            c.drawImage(self.overlay(t), 0, 0)
        ctx = Ctx(c, int(t * 12), t)
        n = c.getSaveCount()
        draw_captions(ctx, t)
        c.restoreToCount(n)
        return self.finish(c, t)

    def finish(self, c, t):
        v = skia.Paint()
        v.setShader(skia.GradientShader.MakeRadial((W / 2, H / 2), 1150, [skia.Color(255, 255, 255),
                    skia.Color(255, 255, 255), skia.Color(160, 155, 170)], [0.0, 0.6, 1.0]))
        v.setBlendMode(skia.BlendMode.kMultiply)
        c.drawPaint(v)
        return self.surf.makeImageSnapshot()


def render_chunk(args):
    f0, f1, path = args
    r = Renderer()
    dec = subprocess.Popen([FFMPEG, "-loglevel", "error", "-i", RAW, "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen([FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s",
                            f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf",
                            "20", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    fsz = SW * SH * 4
    cur_idx, cur = -1, None
    for f in range(f0, f1):
        t = f / FPS
        src_t, si = out_to_src(min(t, TALK_DUR - 1e-3))
        want = int(round(src_t * FPS))
        while cur_idx < want:
            buf = dec.stdout.read(fsz)
            if len(buf) < fsz:
                break
            cur, cur_idx = buf, cur_idx + 1
        img = skia.Image.fromarray(np.frombuffer(cur, np.uint8).reshape(SH, SW, 4))
        out = r.frame(t, img, si)
        enc.stdin.write(out.toarray(colorType=skia.kRGBA_8888_ColorType).tobytes())
    enc.stdin.close()
    enc.wait()
    dec.kill()
    return path


# ------------------------------------------------------------------ audio
def load_voice():
    wav = os.path.join(OUT, "voice_src.wav")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", RAW, "-ac", "1", "-ar", str(SR), wav], check=True)
    sr, x = wavfile.read(wav)
    return x.astype(np.float64) / 32768


def build_audio():
    x = load_voice()
    x = sosfilt(butter(2, 90, "hp", fs=SR, output="sos"), x)
    n_total = int(TOTAL * SR)
    voice = np.zeros(n_total)
    fade = int(0.012 * SR)
    for a, b, o in SEG:
        seg = x[int(a * SR):int(b * SR)].copy()
        seg[:fade] *= np.linspace(0, 1, fade)
        seg[-fade:] *= np.linspace(1, 0, fade)
        i = int(o * SR)
        voice[i:i + len(seg)] += seg[: n_total - i]
    # simple leveller: smooth RMS gain toward a target, then soft clip
    win = int(0.05 * SR)
    env = np.sqrt(np.convolve(voice ** 2, np.ones(win) / win, "same")) + 1e-4
    gain = np.clip(0.12 / env, 0.5, 4.0)
    gain = np.convolve(gain, np.ones(win * 4) / (win * 4), "same")
    voice = np.tanh(voice * gain * 1.5) / 1.5
    voice /= np.abs(voice).max() + 1e-9

    # music bed: same key/instruments as the promo, lighter arrangement
    bed = np.zeros(n_total)
    K, HC = A.kick(), A.hat()
    beat = A.BEAT
    nb = int(TOTAL / beat)
    for bi in range(nb):
        tb = bi * beat
        chord, root = A.chord_at(tb)
        A.place(bed, K * 0.55, tb)
        for s in range(2):
            A.place(bed, HC * 0.25, tb + s * beat / 2)
        A.place(bed, A.bass_note(root, 0.18) * 0.45, tb + beat / 2)
        A.place(bed, A.stab(chord, 0.2, 0.08) * 0.22, tb + beat / 2)
        seq = [chord[0] + 12, chord[2] + 12, chord[1] + 24, chord[2] + 12]
        A.place(bed, A.pluck(seq[bi % 4], 0.15) * 0.18, tb)
    bed = sosfilt(butter(2, 5000, "lp", fs=SR, output="sos"), bed)
    bed /= np.abs(bed).max() + 1e-9
    # duck under speech, open up on cards
    vs = np.convolve(np.abs(voice), np.ones(int(0.15 * SR)) / int(0.15 * SR), "same")
    duck = np.where(vs > 0.03, 0.16, 0.34)
    duck = np.convolve(duck, np.ones(int(0.2 * SR)) / int(0.2 * SR), "same")
    tt = np.arange(n_total) / SR
    duck = np.where((tt >= CARD_A) & (tt < CARD_B), 0.3, duck)
    duck = np.where(tt >= TALK_DUR, 0.55, duck)
    bed *= duck

    # SFX
    sfx = np.zeros(n_total)
    F = A.SFX_FNS
    cues = [
        (wi("FOUR"), "pop", 0.6), (wi("THIRTY"), "pop", 0.5), (wi("CUTTING"), "snip", 0.6),
        (wi("CAPTIONS"), "pop", 0.5), (wi("KEYFRAMING"), "pop", 0.5), (wi("ANIMATION"), "pop", 0.5),
        (wi("ENERGY"), "slap", 0.6), (we("CREATE"), "whoosh", 0.5), (wi("STOPPED") + 0.3, "snip", 0.6),
        (wi("DIRECTING"), "stamp", 0.8), (wi("POP"), "sparkle", 0.8), (wi("POP"), "pop", 0.7),
        (wi("RAW"), "pop", 0.6), (wi("TOUCH") + 0.3, "stamp", 0.5), (wi("SOFTWARE") + 0.25, "snip", 0.5),
        (wi("TASTE"), "stamp", 0.7), (wi("STORYTELLING"), "stamp", 0.7), (CARD_A, "whoosh", 0.8),
        (CARD_A + 0.15, "clack", 0.7), (CARD_B - 0.05, "whoosh", 0.6), (wi("VIBE"), "stamp", 0.9),
        (wi("CAPTIONS", 3), "pop", 0.5), (wi("MOTION"), "pop", 0.5), (wi("ANIMATIONS"), "pop", 0.5),
        (wi("ADS"), "pop", 0.6), (wi("LINK"), "pop", 0.8), (TALK_DUR, "tear", 0.8),
        (TALK_DUR + 0.65, "stamp", 1.0), (TALK_DUR + 1.45, "pop", 0.8), (TALK_DUR + 2.25, "type", 0.8),
    ]
    for k, w0 in enumerate(("CUT", "ADD", "MAKE")):
        cues.append((wi(w0) - 0.05, "whoosh", 0.4))
        for i in range(6):
            cues.append((wi(w0) + i * 0.07, "type", 0.35))
    for t0, kind, g in cues:
        A.place(sfx, F[kind]() * A.SFX_GAIN[kind], t0, g)
    sfx /= max(1.0, np.abs(sfx).max() / 0.9)

    mix = 1.0 * voice + 0.55 * bed + 0.5 * sfx
    mix /= np.abs(mix).max()
    mix = np.tanh(1.4 * mix) / np.tanh(1.4)
    fo = int(0.3 * SR)
    mix[-fo:] *= np.linspace(1, 0, fo) ** 2
    st = np.stack([mix, mix], 1) * 0.93
    path = os.path.join(OUT, "reel_audio.wav")
    wavfile.write(path, SR, (st * 32767).astype(np.int16))
    return path


# ------------------------------------------------------------------ build
def render_video():
    total = int(round(TOTAL * FPS))
    n = os.cpu_count() or 4
    bounds = [round(total * i / n) for i in range(n + 1)]
    jobs = [(bounds[i], bounds[i + 1], os.path.join(OUT, f"chunk{i}.mp4")) for i in range(n)]
    with Pool(n) as pool:
        parts = pool.map(render_chunk, jobs)
    lst = os.path.join(OUT, "chunks.txt")
    with open(lst, "w") as fh:
        fh.writelines(f"file '{p}'\n" for p in parts)
    path = os.path.join(OUT, "reel_noaudio.mp4")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", path],
                   check=True)
    for p in parts:
        os.remove(p)
    os.remove(lst)
    return path


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    print(f"talk {TALK_DUR:.2f}s (raw 58.5s), cuts {len(SEG)}, card {CARD_A:.2f}-{CARD_B:.2f}, total {TOTAL:.2f}s")
    if len(sys.argv) > 1 and sys.argv[1] == "stills":
        r = Renderer()
        os.makedirs(os.path.join(OUT, "stills"), exist_ok=True)
        for ts in map(float, sys.argv[2:]):
            src_t, si = out_to_src(min(ts, TALK_DUR - 1e-3))
            png = os.path.join(OUT, "stills", "src.png")
            subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-ss", f"{src_t:.3f}", "-i", RAW, "-frames:v", "1",
                            png], check=True)
            from PIL import Image
            im = skia.Image.fromarray(np.array(Image.open(png).convert("RGBA")))
            r.frame(ts, im, si).save(os.path.join(OUT, "stills", f"s{ts:05.2f}.png"), skia.kPNG)
        sys.exit()
    wav = build_audio()
    vid = render_video()
    final = os.path.join(OUT, "reel.mp4")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", vid, "-i", wav, "-c:v", "copy", "-c:a", "aac", "-b:a",
                    "192k", "-shortest", "-movflags", "+faststart", final], check=True)
    print("wrote", final)
