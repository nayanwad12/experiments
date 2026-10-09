"""SYSTEM reel: the full edit of the raw phone take (work/frames + work/alpha.npy + work/words.json).

    python3 edit.py stills 1.0 4.2 ...    -> out/stills/*.png  (half res)
    python3 edit.py sheet                 -> out/sheet.png
    python3 edit.py render [--draft]      -> out/system_reel.mp4
    python3 edit.py audio                 -> work/mix.wav

Everything is cued off the spoken words: dead space between phrases is cut, the planted stumble is kept,
shown, rewound and "cut by the system", and the edit freezes on "...even this." for the big moment.
"""

import json
import math
import os
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "reels" / "common"))
import audio_kit as ak  # noqa: E402
import kit  # noqa: E402
from theme import (BLUE, INK, PAPER, RED, SAMP, WHITE, YEL, arrow, block_text, card, check_mark, clamp,  # noqa: E402
                   col, e_back, e_in, e_io, e_out, fill, font, halftone, hilite, hrand, kinetic, lerp, marker,
                   measure, paper_bg, paper_tex, prog, rays, scribble_ellipse, spring, stamp, stroke, tape)
from vibelib import ff, loudnorm_filter  # noqa: E402

W, H, FPS = 1080, 1920, 30
OUT = HERE / "out"
FR = HERE / "work" / "frames"
NSRC = len(list(FR.glob("f_*.jpg")))
FACE = (600, 1010)          # zoom anchor (face) in the 1080x1920 frame

# ================================================================== words + edit decision list
WORDS = json.loads((HERE / "work" / "words.json").read_text())
for i, w in enumerate(WORDS):
    w["i"] = i
    w["k"] = re.sub(r"[^a-z0-9']", "", w["d"].lower())


def _find(seq, n=1):
    toks = seq.lower().replace(",", "").replace(".", "").replace("?", "").split()
    hits = 0
    for i in range(len(WORDS) - len(toks) + 1):
        if all(WORDS[i + j]["k"] == toks[j] for j in range(len(toks))):
            hits += 1
            if hits == n:
                return i, i + len(toks) - 1
    raise KeyError(seq)


I_SORRY = _find("sorry")[0]
I_AGAIN = _find("again")[0]
I_LIKE = _find("like right now")[0]
I_THIS = _find("and even this")[1]
SRC_END_HOLD = 58.3


def build_edl():
    """[(kind, src_a, src_b, out_a, dur)] kinds: play | rev | freeze."""
    runs = []
    for w in WORDS:
        gap = w["s"] - runs[-1][1] if runs else 9
        if runs and (gap < 0.2 or w["i"] == I_SORRY) and w["i"] != I_AGAIN + 1:  # keep the beat before "sorry"
            runs[-1][1] = w["e"]
            runs[-1][3] = w["i"]
        else:
            runs.append([w["s"], w["e"], w["i"], w["i"]])
    keep = []
    for k, (a, b, i0, i1) in enumerate(runs):
        prev_e = runs[k - 1][1] if k else 0
        next_s = runs[k + 1][0] if k + 1 < len(runs) else SRC_END_HOLD
        a = max(a - 0.07, (prev_e + a) / 2)
        b = min(b + 0.10, (b + next_s) / 2) if k + 1 < len(runs) else SRC_END_HOLD
        keep.append([a, b, i0, i1])
    edl, t = [], 0.0
    for a, b, i0, i1 in keep:
        if i0 <= I_THIS <= i1 and WORDS[I_THIS]["e"] < b:      # freeze right after "...even this."
            m = WORDS[I_THIS]["e"] + 0.04
            edl.append(("play", a, m, t, m - a)); t += m - a
            edl.append(("freeze", m, m, t, 0.95)); t += 0.95
            edl.append(("play", m, b, t, b - m)); t += b - m
            continue
        edl.append(("play", a, b, t, b - a)); t += b - a
        if i0 <= I_AGAIN <= i1:                                # rewind the stumble after "...say that again."
            ra, rb = WORDS[I_LIKE]["s"] - 0.05, b
            d = (rb - ra) / 7.0
            edl.append(("rev", rb, ra, t, d)); t += d
    return edl, t


EDL, TOTAL = build_edl()
REW = next(s for s in EDL if s[0] == "rev")
FRZ = next(s for s in EDL if s[0] == "freeze")
RUN_STARTS = [s[3] for s in EDL if s[0] == "play"]


def src_at(t):
    """output time -> (source time, kind)."""
    for kind, a, b, o, d in EDL:
        if t < o + d:
            k = (t - o) / d if d else 0
            if kind == "play":
                return a + (t - o), kind
            if kind == "rev":
                return lerp(a, b, k), kind
            return a, kind
    kind, a, b, o, d = EDL[-1]
    return b, kind


def out_of(ts, start=True):
    for kind, a, b, o, d in EDL:
        if kind == "play" and (a - 1e-6 <= ts < b - 1e-6 if start else a + 1e-6 < ts <= b + 1e-6):
            return o + ts - a
    best = min((s for s in EDL if s[0] == "play"), key=lambda s: min(abs(ts - s[1]), abs(ts - s[2])))
    return best[3] + clamp(ts - best[1], 0, best[4])


for w in WORDS:
    w["os"], w["oe"] = out_of(w["s"], True), out_of(w["e"], False)


class P:
    """a spoken phrase on the output clock: P('my system did').s / .e / .w(i) word start / .we(i) word end"""

    def __init__(self, seq, n=1):
        self.i0, self.i1 = _find(seq, n)
        self.s, self.e = WORDS[self.i0]["os"], WORDS[self.i1]["oe"]

    def w(self, j):
        return WORDS[self.i0 + j]["os"]

    def we(self, j):
        return WORDS[self.i0 + j]["oe"]


HOOK = P("the video you're watching right now")
DIDNT = P("i didn't edit it")
SYSDID = P("my system did")
LEFT = P("on the left is the video straight from my phone")
RIGHT = P("and on the right what you're watching")
SAME = P("same video")
NOAPP = P("no editing app")
BUILT = P("i built this system for my own videos")
FOUR = P("it works in four simple steps")
STEPS = [P("step one"), P("step two"), P("step three"), P("step four")]
REC = P("i record on my phone")
ONETAKE = P("just one take")
MOK1 = P("mistakes are okay", 1)
LIKE = P("like right now i'm going to")
SORRY = P("sorry let me say that again")
MOK2 = P("mistakes are okay", 2)
TELL = P("i tell my system what i want")
SIMPLE = P("in simple words")
SHORT = P("like make it short")
BIG = P("add big text")
MUSIC = P("add music")
EDITS = P("the system edits it for me")
CUTS = P("it cuts the pauses")
ZOOMS = P("zooms in")
TEXT = P("adds the text")
THEMUSIC = P("and the music")
EVEN = P("and even this")
CHECK = P("i check it")
CHANGE = P("want a change")
SAYIT = P("i just say it")
READY = P("then it's ready for instagram youtube anywhere")
MADE = P("that's how this whole video was made")
EVERY = P("and every video on my page")
WANT = P("want to see how my system works")
COMMENT = P("comment system")
SEND = P("and i will send you the details")
FRZ_A, FRZ_B = FRZ[3], FRZ[3] + FRZ[4]
REW_A, REW_B = REW[3], REW[3] + REW[4]
SPLIT_A, SPLIT_B = LEFT.s - 0.08, NOAPP.e + 0.12
GRID_A, GRID_B = MADE.s - 0.05, WANT.s - 0.02
CTA_A = WANT.s - 0.02
STEP_NAMES = ["RECORD", "TELL IT", "IT EDITS", "CHECK"]
STEP_ENDS = [MOK2.e + 0.15, MUSIC.e + 0.2, FRZ_B, READY.e + 0.25]


def chapter_iv(n):
    s = STEPS[n]
    return s.s - 0.06, s.e + 0.28


# ================================================================== source frames
_cache = {}


def frame_rgb(fi):
    fi = int(clamp(fi, 0, NSRC - 1))
    if fi not in _cache:
        if len(_cache) > 24:
            _cache.pop(next(iter(_cache)))
        _cache[fi] = cv2.imread(str(FR / f"f_{fi + 1:05d}.jpg"))[..., ::-1]
    return _cache[fi]


_ALPHA = None


def alpha_small(fi):
    global _ALPHA
    if _ALPHA is None:
        _ALPHA = np.load(HERE / "work" / "alpha.npy", mmap_mode="r")
    return np.asarray(_ALPHA[int(clamp(fi, 0, len(_ALPHA) - 1))])


def _lut():
    x = np.arange(256, dtype=np.float32) / 255
    s = x + 0.075 * np.sin(2 * math.pi * (x - 0.5))                    # gentle S-curve
    s = np.clip((s - 0.02) / 0.97, 0, 1)
    r = np.clip(s * 1.03 + 0.005, 0, 1)
    b = np.clip(s * 0.97, 0, 1)
    return [(np.clip(c, 0, 1) * 255).astype(np.uint8) for c in (r, s, b)]


LUT = _lut()


def grade(rgb, sat=1.18):
    o = np.empty_like(rgb)
    for ch in range(3):
        o[..., ch] = LUT[ch][rgb[..., ch]]
    f = o.astype(np.float32)
    lum = f @ np.array([0.299, 0.587, 0.114], np.float32)
    f = lum[..., None] + (f - lum[..., None]) * sat
    return np.clip(f, 0, 255).astype(np.uint8)


class Src:
    """everything drawable from one source frame: graded bg, cut-out person, sticker outline."""

    def __init__(self, ts, graded=True):
        self.fi = int(round(ts * FPS))
        rgb = frame_rgb(self.fi)
        self.rgb = grade(rgb) if graded else rgb
        self._a = None

    @property
    def alpha(self):
        if self._a is None:
            self._a = cv2.resize(alpha_small(self.fi), (W, H), interpolation=cv2.INTER_LINEAR)
        return self._a

    def bg(self):
        return skia.Image.fromarray(np.dstack([self.rgb, np.full((H, W), 255, np.uint8)]),
                                    colorType=skia.kRGBA_8888_ColorType)

    def person(self):
        return skia.Image.fromarray(np.dstack([self.rgb, self.alpha]), colorType=skia.kRGBA_8888_ColorType)

    def outline(self, px=9, color=(255, 255, 255)):
        a = alpha_small(self.fi)
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1))
        d = cv2.resize(cv2.dilate(a, k), (W, H), interpolation=cv2.INTER_LINEAR)
        arr = np.zeros((H, W, 4), np.uint8)
        arr[..., :3] = color
        arr[..., 3] = d
        return skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType)


# ================================================================== camera
ZLEVELS = [1.0, 1.1, 1.04, 1.17, 1.07, 1.13]
FLAT = [(DIDNT.s - 0.05, SYSDID.e + 0.1), (FOUR.s - 0.05, FOUR.e + 0.2), (BIG.s - 0.05, BIG.e + 0.3),
        (FRZ_A - 0.4, FRZ_B), (CTA_A, TOTAL)] + [chapter_iv(n) for n in range(4)]
SHAKES = []      # (t, strength)


def in_any(t, ivs):
    return any(a <= t < b for a, b in ivs)


def camera(t):
    """(scale, dx, dy, rot) applied to the footage (bg + person) around FACE."""
    if in_any(t, FLAT):
        z = 1.0
    else:
        k = max([i for i, s in enumerate(RUN_STARTS) if s <= t + 1e-6] or [0])
        z = ZLEVELS[k % len(ZLEVELS)]
        z *= 1 + 0.012 * (t - RUN_STARTS[k])                       # slow push inside a run
    if t < 0.4:                                                     # opening slam
        z *= lerp(1.35, 1.0, e_out(t / 0.4))
    if ZOOMS.s - 0.02 <= t < TEXT.s:                              # "zooms in"
        z = lerp(z, 1.55, e_out(prog(t, ZOOMS.s - 0.02, 0.18)))
    if MUSIC.we(1) <= t < MUSIC.we(1) + 2.6:                        # pump on the beat after the drop
        beat = 60 / 128
        ph = ((t - MUSIC.w(1)) % beat) / beat
        z *= 1 + 0.035 * (1 - ph) ** 3
    dx = dy = rot = 0.0
    for st, amp in SHAKES:
        if st <= t < st + 0.35:
            k = 1 - (t - st) / 0.35
            dx += amp * k * math.sin(t * 91.0)
            dy += amp * k * math.sin(t * 77.0 + 1)
            rot += amp * 0.04 * k * math.sin(t * 63.0)
    return z, dx, dy, rot


def apply_cam(c, cam, anchor=FACE):
    z, dx, dy, rot = cam
    c.translate(anchor[0] + dx, anchor[1] + dy)
    c.rotate(rot)
    c.scale(z, z)
    c.translate(-anchor[0], -anchor[1])


# ================================================================== captions
CAP_OFF = [(DIDNT.s - 0.05, SYSDID.e + 0.12), (FOUR.s - 0.05, FOUR.e + 0.2), (BIG.s - 0.03, BIG.e + 0.3),
           (FRZ_A, FRZ_B), (REW_A, REW_B), (COMMENT.s - 0.05, TOTAL)] + [chapter_iv(n) for n in range(4)]
CAP_Y = 1430
CAP_SIZE = 108


def _cap_groups():
    groups, cur = [], []
    for w in WORDS:
        if cur and (len(cur) >= 3 or sum(len(x["d"]) + 1 for x in cur) + len(w["d"]) > 15
                    or w["os"] - cur[-1]["oe"] > 0.12 or cur[-1]["d"][-1] in ".,?…"):
            groups.append(cur)
            cur = []
        cur.append(w)
    groups.append(cur)
    return groups


CAPS = _cap_groups()


def cap_text(w):
    return w["d"].upper().strip(",.").replace("…", "")


def draw_captions(c, t, hi=YEL):
    if in_any(t, CAP_OFF):
        return
    g = None
    for k, grp in enumerate(CAPS):
        nxt = CAPS[k + 1][0]["os"] if k + 1 < len(CAPS) else grp[-1]["oe"] + 0.4
        if grp[0]["os"] - 0.04 <= t < min(nxt - 0.02, grp[-1]["oe"] + 0.45):
            g = grp
    if not g:
        return
    size = CAP_SIZE
    words = [cap_text(w) for w in g]
    gap = size * 0.24
    widths = [measure(s, "anton", size) for s in words]
    tot = sum(widths) + gap * (len(words) - 1)
    sc = min(1.0, 940 / tot)
    c.save()
    c.translate(540, CAP_Y)
    c.scale(sc, sc)
    x = -tot / 2
    for j, (w, s, wd) in enumerate(zip(g, words, widths)):
        if t < w["os"] - 0.04:
            break
        k = clamp((t - w["os"] + 0.04) / 0.22)
        sp = spring(k * 0.22, w=26, z=0.5)
        cur = w["os"] - 0.04 <= t < w["oe"] + 0.04 or (j == len(g) - 1 and t >= w["os"])
        c.save()
        c.translate(x + wd / 2, 0)
        s_ = (0.5 + 0.5 * sp) * (1.08 if cur else 1.0)
        c.scale(s_, s_)
        c.rotate((hrand(w["i"]) - 0.5) * 5)
        if cur:
            capH = font("anton", size).getMetrics().fCapHeight
            hilite(c, -wd / 2 - 16, -capH - 14, wd + 32, capH + 30, 1.0, hi, seed=w["i"], rot=0)
            block_text(c, s, 0, 0, size, color=INK, shadow=None)
        else:
            block_text(c, s, 0, 0, size, color=WHITE, shadow=INK, depth=0.05, outline=10)
        c.restore()
        x += wd + gap
    c.restore()


# ================================================================== scene pieces
def step_tracker(c, t):
    a0, a1 = STEPS[0].s, GRID_A - 0.3
    if not (a0 <= t < a1 + 0.3) or GRID_A <= t:
        return
    ka = e_out(prog(t, a0, 0.35)) * (1 - e_in(prog(t, a1, 0.3)))
    cur = max([n for n in range(4) if t >= STEPS[n].s] or [0])
    cw, ch, gap = 228, 66, 14
    x0 = 540 - (4 * cw + 3 * gap) / 2
    y = 200 - (1 - ka) * 140
    for n in range(4):
        x = x0 + n * (cw + gap)
        done = t >= STEP_ENDS[n]
        on = n == cur and not done
        bgc = YEL if on else INK if done else PAPER
        fg = INK if on or not done else YEL
        pop = 1 + 0.12 * math.sin(math.pi * prog(t, STEPS[n].s, 0.3)) if on else 1
        c.save()
        c.translate(x + cw / 2, y + ch / 2)
        c.scale(pop, pop)
        rr = kit.rrect(-cw / 2, -ch / 2, cw, ch, 14)
        c.drawRRect(rr.makeOffset(5, 6), fill(INK, 0.9 * ka))
        c.drawRRect(rr, fill(bgc, (1.0 if on or done else 0.92) * ka))
        c.drawRRect(rr, stroke(INK, 4, ka))
        lab = f"{n + 1:02d} {STEP_NAMES[n]}"
        kit.text(c, lab, 0, 11, "monob", 27, color=fg, a=ka)
        c.restore()


def viewfinder(c, t, a0, a1):
    if not (a0 <= t < a1):
        return
    k = e_out(prog(t, a0, 0.25)) * (1 - prog(t, a1 - 0.2, 0.2))
    m, L = 70 + 30 * (1 - k), 90
    top, bot = 300, 1720
    p = stroke(WHITE, 8, k)
    for (x, y, sx, sy) in [(m, top, 1, 1), (W - m, top, -1, 1), (m, bot, 1, -1), (W - m, bot, -1, -1)]:
        c.drawLine(x, y, x + sx * L, y, p)
        c.drawLine(x, y, x, y + sy * L, p)
    blink = (int(t * 2.5) % 2) == 0
    if blink:
        c.drawCircle(m + 40, top + 66, 15, fill(RED, k))
    kit.text(c, "REC", m + 66, top + 78, "monob", 34, color=WHITE, a=k, anchor="l", shadow=4)
    tc = t - a0 + 12.0
    kit.text(c, f"00:00:{int(tc):02d}:{int((tc % 1) * 30):02d}", W - m - 20, top + 78, "monob", 34, color=WHITE,
             a=k, anchor="r", shadow=4)


def timeline_strip(c, t):
    """the clip timeline in step 1: the stumble turns red, gets snipped, and the gap closes."""
    a0, a1 = LIKE.s - 0.1, MOK2.e + 0.1
    if not (a0 <= t < a1):
        return
    ka = e_out(prog(t, a0, 0.25)) * (1 - prog(t, a1 - 0.2, 0.2))
    x0, y0, w, h = 90, 330, 900, 92
    c.save()
    c.translate(0, -(1 - ka) * 60)
    card(c, x0 - 14, y0 - 14, w + 28, h + 72, PAPER, r=16, shadow=0.35)
    kit.text(c, "TIMELINE", x0, y0 + h + 44, "monob", 24, color=INK, anchor="l")
    # clip blocks: [good][stumble][good]
    sa = clamp((t - SORRY.s) / 0.15)
    cut_k = e_io(prog(t, REW_B - 0.05, 0.3))        # stumble collapses after the rewind
    red_w = 300 * (1 - cut_k) * (sa if t < REW_A else 1)
    good_w = 470
    c.drawRRect(kit.rrect(x0, y0, good_w, h, 10), fill(BLUE))
    for i in range(10):
        hh = h * (0.25 + 0.6 * hrand("wv", i))
        c.drawRect(skia.Rect.MakeXYWH(x0 + 20 + i * 44, y0 + h / 2 - hh / 2, 22, hh), fill(WHITE, 0.55))
    if red_w > 1:
        c.drawRRect(kit.rrect(x0 + good_w + 6, y0, red_w, h, 10), fill(RED))
        if red_w > 200:
            kit.text(c, "MISTAKE", x0 + good_w + 6 + red_w / 2, y0 + h / 2 + 12, "monob", 32, color=WHITE)
    tail_x = x0 + good_w + 6 + (red_w + 6 if red_w > 1 else 0)
    c.drawRRect(kit.rrect(tail_x, y0, max(0, x0 + w - tail_x), h, 10), fill(BLUE, 0.85 if t >= MOK2.s else 0.35))
    # playhead
    if t < REW_A:
        ph = lerp(x0 + 60, x0 + good_w + 6 + 300 * sa, clamp((t - a0) / (REW_A - a0)))
    elif t < REW_B:
        ph = lerp(x0 + good_w + 300, x0 + 40, e_io(prog(t, REW_A, REW_B - REW_A)))
    else:
        ph = lerp(x0 + 40, tail_x + 40, e_out(prog(t, REW_B, 0.6)))
    c.drawRect(skia.Rect.MakeXYWH(ph - 3, y0 - 18, 6, h + 36), fill(INK))
    c.drawCircle(ph, y0 - 18, 11, fill(INK))
    # scissors snip
    if REW_B - 0.08 <= t < REW_B + 0.5:
        k = prog(t, REW_B - 0.08, 0.3)
        sx = x0 + good_w + 3
        c.save()
        c.translate(sx, y0 - 40)
        c.rotate(90)
        op = 18 * abs(math.sin(k * math.pi * 2))
        for sgn in (-1, 1):
            c.save()
            c.rotate(sgn * op)
            c.drawRRect(kit.rrect(-6, -4, 70, 8, 4), fill(INK))
            c.drawCircle(-18, 0, 14, stroke(RED, 7))
            c.restore()
        c.restore()
    c.restore()


def rewind_icon(c, x, y, s, a):
    for i in range(2):
        path = skia.Path()
        ox = x + i * s * 0.9
        path.moveTo(ox, y)
        path.lineTo(ox + s, y - s * 0.65)
        path.lineTo(ox + s, y + s * 0.65)
        path.close()
        c.drawPath(path, fill(WHITE, a))


def prompt_box(c, t):
    """step 2: the system's prompt box; each command types out, sends, and lands as a chip."""
    a0, a1 = TELL.s - 0.05, min(MUSIC.e + 0.45, chapter_iv(2)[0])
    if not (a0 <= t < a1):
        return
    ka = e_out(prog(t, a0, 0.3)) * (1 - e_in(prog(t, a1 - 0.25, 0.25)))
    cmds = [("make it short", SHORT.w(1), SHORT.e), ("add big text", BIG.s, BIG.e), ("add music", MUSIC.s, MUSIC.e)]
    x0, y0, w, h = 70, 300, 940, 116
    c.save()
    c.translate(0, -(1 - ka) * 80)
    if not (BIG.s - 0.03 <= t < BIG.e + 0.3):
        card(c, x0, y0, w, h, WHITE, r=30, shadow=0.35, border=INK, bw=5)
        txt, sent = "", None
        for s, ta, tb in cmds:
            if t >= ta:
                n = int(len(s) * clamp((t - ta) / max(0.2, (tb - ta) * 0.9)))
                txt, sent = s[:n], tb
        if t >= sent if sent else False:
            txt = txt if t < sent + 0.08 else ""
        if not txt and t < cmds[0][1]:
            kit.text(c, "tell your system…", x0 + 48, y0 + 72, "mono", 36, color="#9A9A9A", anchor="l")
        else:
            x1, _ = kit.text(c, txt, x0 + 48, y0 + 72, "monob", 40, color=INK, anchor="l")
            tw = measure(txt, "monob", 40)
            if int(t * 3) % 2 == 0:
                c.drawRect(skia.Rect.MakeXYWH(x0 + 52 + tw, y0 + 36, 5, 46), fill(INK))
        c.drawCircle(x0 + w - 62, y0 + h / 2, 38, fill(YEL))
        c.drawCircle(x0 + w - 62, y0 + h / 2, 38, stroke(INK, 4))
        ap = skia.Path()
        ax, ay = x0 + w - 62, y0 + h / 2
        ap.moveTo(ax - 14, ay + 14); ap.lineTo(ax + 16, ay); ap.lineTo(ax - 14, ay - 14); ap.lineTo(ax - 6, ay)
        ap.close()
        c.drawPath(ap, fill(INK))
    # sent chips stacking on the left
    for j, (s, ta, tb) in enumerate(cmds):
        if t < tb:
            continue
        if BIG.s - 0.03 <= t < BIG.e + 0.3 and j == 1:
            continue
        k = e_back(prog(t, tb, 0.3))
        y = y0 + h + 40 + j * 78
        x = lerp(x0 + w - 100, x0, k)
        lab = "✓ " + s if False else s.upper()
        tw = measure(lab, "monob", 30) + 76
        c.drawRRect(kit.rrect(x + 4, y + 5, tw, 60, 30), fill(INK))
        c.drawRRect(kit.rrect(x, y, tw, 60, 30), fill(YEL))
        check_mark(c, x + 30, y + 30, 26, 1, INK, 6)
        kit.text(c, lab, x + 52, y + 41, "monob", 30, color=INK, anchor="l")
    c.restore()
    # "make it short": length counter
    if SHORT.e <= t < BIG.s + 0.1:
        k = prog(t, SHORT.e, 0.5)
        secs = int(round(lerp(NSRC / FPS, TOTAL, e_io(k))))
        tape(c, f"LENGTH 0:{secs:02d}", 790, 640, 34, prog(t, SHORT.e, 0.25), rot=4, seed=3)


def eq_bars(c, t, t0, t1, behind=True):
    if not (t0 <= t < t1):
        return
    ka = e_out(prog(t, t0, 0.25)) * (1 - e_in(prog(t, t1 - 0.3, 0.3)))
    beat = 60 / 128
    n = 15
    bw = W / n
    for i in range(n):
        ph = ((t - t0) % beat) / beat
        hgt = (220 + 520 * hrand("eq", i, int((t - t0) / (beat / 2)))) * (0.6 + 0.4 * (1 - ph) ** 2) * ka
        col_ = [YEL, RED, WHITE][i % 3]
        c.drawRRect(kit.rrect(i * bw + 8, 1360 - hgt, bw - 16, hgt + 40, 10), fill(INK, 0.9))
        c.drawRRect(kit.rrect(i * bw + 4, 1356 - hgt, bw - 16, hgt + 40, 10), fill(col_))
    # notes floating up
    for j in range(5):
        st = t0 + j * 0.22
        if t < st:
            continue
        k = (t - st) / 1.6
        if k > 1:
            continue
        x = 140 + 800 * hrand("nt", j) + 30 * math.sin(k * 6 + j)
        y = 900 - 500 * k
        a = ka * (1 - k)
        c.save()
        c.translate(x, y)
        c.rotate(-12 + 24 * hrand("nr", j))
        c.drawOval(skia.Rect.MakeXYWH(-26, -16, 44, 32), fill(INK, a))
        c.drawRect(skia.Rect.MakeXYWH(12, -90, 8, 80), fill(INK, a))
        c.drawRect(skia.Rect.MakeXYWH(12, -90, 36, 14), fill(INK, a))
        c.restore()


def checklist(c, t):
    a0, a1 = EDITS.s - 0.05, EVEN.s
    if not (a0 <= t < a1 + 0.2):
        return
    ka = e_back(prog(t, a0, 0.35)) * (1 - e_in(prog(t, a1, 0.2)))
    items = [("CUT PAUSES", CUTS.we(3)), ("ZOOM IN", ZOOMS.we(1)), ("ADD TEXT", TEXT.we(2)), ("MUSIC", THEMUSIC.we(2))]
    x0, y0, w, h = 80, 290, 920, 330
    c.save()
    c.translate(540, y0 + h / 2)
    c.scale(ka, ka)
    c.rotate(-1.5)
    c.translate(-540, -(y0 + h / 2))
    card(c, x0, y0, w, h, PAPER, r=20, shadow=0.4, border=INK, bw=5)
    hdr = "SYSTEM IS EDITING"
    dots = "." * (1 + int(t * 4) % 3)
    kit.text(c, hdr + dots, x0 + 40, y0 + 64, "monob", 32, color=INK, anchor="l")
    # spinner
    sa = (t * 400) % 360
    c.drawArc(skia.Rect.MakeXYWH(x0 + w - 86, y0 + 28, 46, 46), sa, 260, False, stroke(RED, 8))
    for j, (lab, tk) in enumerate(items):
        cx = x0 + 40 + (j % 2) * 440
        cy = y0 + 130 + (j // 2) * 110
        c.drawRRect(kit.rrect(cx, cy, 64, 64, 10), stroke(INK, 5))
        done = t >= tk
        if done:
            hilite(c, cx + 80, cy + 6, measure(lab, "anton", 54) + 24, 56, prog(t, tk, 0.2), YEL, seed=j)
            check_mark(c, cx + 34, cy + 30, 58, prog(t, tk, 0.18), RED, 12)
        kit.text(c, lab, cx + 92, cy + 54, "anton", 54, color=INK, anchor="l")
    c.restore()


def speed_lines(c, t, t0, dur=0.45):
    if not (t0 <= t < t0 + dur):
        return
    k = (t - t0) / dur
    for i in range(36):
        ang = i * 10 + 7 * hrand("sl", i)
        r0 = 680 + 140 * hrand("sr", i) - 160 * k
        L = 300 + 300 * hrand("sL", i)
        a = (1 - k) * 0.9
        x0 = FACE[0] + r0 * math.cos(math.radians(ang))
        y0 = FACE[1] - 60 + r0 * math.sin(math.radians(ang))
        c.drawLine(x0, y0, x0 + L * math.cos(math.radians(ang)), y0 + L * math.sin(math.radians(ang)),
                   stroke(WHITE, 6 + 6 * hrand("sw", i), a))


TEXT_SPAM = ["TEXT!", "BIG", "POP", "WOW", "BOLD", "LOUD"]


def text_spam(c, t):
    t0 = TEXT.s
    if not (t0 <= t < THEMUSIC.s + 0.1):
        return
    for j, s in enumerate(TEXT_SPAM):
        st = t0 + j * 0.07
        if t < st:
            continue
        x = [220, 870, 190, 900, 240, 860][j]
        y = [780, 760, 960, 950, 1130, 1120][j]
        size = [170, 150, 140, 150, 130, 130][j]
        colr = [YEL, WHITE, RED, YEL, WHITE, YEL][j]
        sc = e_back(prog(t, st, 0.18))
        c.save()
        c.translate(x, y)
        c.rotate((hrand("ts", j) - 0.5) * 24)
        c.scale(sc, sc)
        block_text(c, s, 0, 0, size, color=colr, shadow=INK, depth=0.07)
        c.restore()


def bubble(c, x, y, txt, k, who="YOU", dark=False, size=40, name="italic", tail="l"):
    if k <= 0:
        return
    sc = e_back(clamp(k / 0.6))
    tw = measure(txt, name, size)
    w, h = tw + 80, size * 2.1
    c.save()
    c.translate(x, y)
    c.scale(sc, sc)
    bgc, fg = (INK, WHITE) if dark else (WHITE, INK)
    path = skia.Path()
    path.addRRect(kit.rrect(-w / 2, -h / 2, w, h, h / 2))
    tx = -w / 2 + 50 if tail == "l" else w / 2 - 50
    path.moveTo(tx - 16, h / 2 - 6); path.lineTo(tx + (-26 if tail == "l" else 26), h / 2 + 30); path.lineTo(tx + 18, h / 2 - 6)
    c.drawPath(path, fill("#000000", 0.3, blur=10))
    c.drawPath(path, fill(bgc))
    c.drawPath(path, stroke(INK, 4))
    kit.text(c, who, -w / 2 + 24, -h / 2 - 14, "monob", 24, color=INK if not dark else INK, anchor="l")
    kit.text(c, txt, 0, size * 0.36, name, size, color=fg)
    c.restore()


def platform_cards(c, t):
    a0 = READY.w(4)
    if not (a0 - 0.1 <= t < GRID_A):
        return
    specs = [("INSTAGRAM", READY.w(4)), ("YOUTUBE", READY.w(5)), ("ANYWHERE", READY.w(6))]
    for j, (lab, ts) in enumerate(specs):
        if t < ts:
            continue
        k = prog(t, ts, 0.4)
        x = 200 + j * 340
        y = 520
        c.save()
        c.translate(lerp(x + 300, x, e_out(k)), y + (1 - e_back(k)) * 80)
        c.rotate(lerp(20, [-6, 3, -2][j], e_out(k)))
        card(c, -140, -150, 280, 300, PAPER, r=26, shadow=0.4, border=INK, bw=5)
        if j == 0:
            g = skia.GradientShader.MakeLinear([skia.Point(-70, 50), skia.Point(70, -100)],
                                               [col("#FEDA75"), col("#FA7E1E"), col("#D62976"), col("#962FBF"), col("#4F5BD5")])
            c.drawRRect(kit.rrect(-70, -110, 140, 140, 38), skia.Paint(Shader=g, AntiAlias=True))
            c.drawRRect(kit.rrect(-46, -86, 92, 92, 26), stroke(WHITE, 9))
            c.drawCircle(0, -40, 22, stroke(WHITE, 9))
            c.drawCircle(27, -68, 6, fill(WHITE))
        elif j == 1:
            c.drawRRect(kit.rrect(-82, -88, 164, 116, 32), fill("#FF0033"))
            tri = skia.Path()
            tri.moveTo(-20, -58); tri.lineTo(32, -30); tri.lineTo(-20, -2); tri.close()
            c.drawPath(tri, fill(WHITE))
        else:
            c.drawCircle(0, -40, 66, fill(BLUE))
            c.drawCircle(0, -40, 66, stroke(INK, 6))
            c.drawOval(skia.Rect.MakeXYWH(-30, -106, 60, 132), stroke(WHITE, 5))
            c.drawLine(-66, -40, 66, -40, stroke(WHITE, 5))
            c.drawLine(-58, -72, 58, -72, stroke(WHITE, 4))
            c.drawLine(-58, -8, 58, -8, stroke(WHITE, 4))
        kit.text(c, lab, 0, 100, "anton", 50, color=INK)
        c.restore()
    # export bar
    k = prog(t, READY.s, READY.w(6) - READY.s + 0.3)
    if t >= READY.s:
        ka = e_out(prog(t, READY.s, 0.2))
        x0, y0 = 120, 760
        c.drawRRect(kit.rrect(x0 + 5, y0 + 6, 840, 56, 28), fill(INK, ka))
        c.drawRRect(kit.rrect(x0, y0, 840, 56, 28), fill(PAPER, ka))
        c.drawRRect(kit.rrect(x0 + 6, y0 + 6, max(44, 828 * e_io(k)), 44, 22), fill(YEL, ka))
        c.drawRRect(kit.rrect(x0, y0, 840, 56, 28), stroke(INK, 4, ka))
        kit.text(c, f"EXPORT {int(100 * e_io(k))}%", x0 + 420, y0 + 40, "monob", 30, color=INK, a=ka)


def confetti(c, t, t0, n=70):
    if t < t0:
        return
    k = t - t0
    for i in range(n):
        ang = 2 * math.pi * hrand("cf", i)
        v = 900 + 1500 * hrand("cv", i)
        x = FACE[0] + math.cos(ang) * v * k
        y = FACE[1] - 200 + math.sin(ang) * v * k + 1400 * k * k
        if y > H + 50:
            continue
        c.save()
        c.translate(x, y)
        c.rotate(720 * k * (hrand("cr", i) - 0.5) + 90 * hrand("c0", i))
        cc = [YEL, RED, WHITE, INK, BLUE][i % 5]
        c.drawRect(skia.Rect.MakeXYWH(-14, -8, 28, 16), fill(cc, clamp(1.6 - k * 1.4)))
        c.restore()


def comment_ui(c, t):
    a0 = COMMENT.s - 0.08
    if t < a0:
        return
    k = e_back(prog(t, a0, 0.35))
    x0, y0, w, h = 60, 1350, 960, 136
    typed = "SYSTEM"
    n = int(len(typed) * clamp((t - COMMENT.w(1)) / 0.35))
    sent = t >= COMMENT.e + 0.08
    c.save()
    c.translate(540, y0 + h / 2)
    pulse = 1 + 0.06 * math.sin(math.pi * prog(t, COMMENT.e + 0.08, 0.25))
    c.scale(k * pulse, k * pulse)
    c.translate(-540, -(y0 + h / 2))
    card(c, x0, y0, w, h, WHITE, r=h / 2, shadow=0.4, border=INK, bw=6)
    c.drawCircle(x0 + 74, y0 + h / 2, 44, fill(YEL))
    c.drawCircle(x0 + 74, y0 + h / 2, 44, stroke(INK, 5))
    kit.text(c, "YOU", x0 + 74, y0 + h / 2 + 10, "monob", 26, color=INK)
    if n == 0 and not sent:
        kit.text(c, "Add a comment…", x0 + 146, y0 + h / 2 + 16, "mono", 40, color="#9A9A9A", anchor="l")
    else:
        block_text(c, typed[:max(n, 0)] if not sent else typed, x0 + 146, y0 + h / 2 + 30, 82, color=INK,
                   shadow=None, anchor="l")
    bx = x0 + w - 80
    c.drawCircle(bx, y0 + h / 2, 48, fill(RED if sent else YEL))
    c.drawCircle(bx, y0 + h / 2, 48, stroke(INK, 5))
    ap = skia.Path()
    ax, ay = bx, y0 + h / 2
    ap.moveTo(ax - 18, ay + 18); ap.lineTo(ax + 20, ay); ap.lineTo(ax - 18, ay - 18); ap.lineTo(ax - 8, ay); ap.close()
    c.drawPath(ap, fill(WHITE if sent else INK))
    c.restore()
    if sent:
        # hearts
        for j in range(5):
            st = COMMENT.e + 0.1 + j * 0.08
            if t < st:
                continue
            kk = (t - st) / 1.1
            if kk > 1:
                continue
            hx = x0 + w - 80 + 60 * math.sin(kk * 5 + j) - j * 20
            hy = y0 - 40 - 520 * kk
            heart(c, hx, hy, 34 * e_back(clamp(kk * 4)), RED, 1 - kk)
        # paper plane to the top right
        if t >= SEND.s:
            kk = e_io(prog(t, SEND.s, 0.9))
            px, py = lerp(x0 + w - 80, 980, kk), lerp(y0, 300, kk) - 160 * math.sin(kk * math.pi)
            for j in range(1, 9):
                kj = max(0, kk - j * 0.04)
                tx, ty = lerp(x0 + w - 80, 980, kj), lerp(y0, 300, kj) - 160 * math.sin(kj * math.pi)
                c.drawCircle(tx, ty, 5, fill(INK, 0.6 * (1 - j / 9)))
            plane(c, px, py, 1.0 - 0.4 * kk, -30 - 20 * kk)
            if kk >= 1:
                bubble(c, 560, 430, "here are the details", prog(t, SEND.s + 0.9, 0.3), who="DM", size=50)


def heart(c, x, y, s, color, a=1.0):
    path = skia.Path()
    path.moveTo(x, y + s * 0.9)
    path.cubicTo(x - s * 1.6, y - s * 0.2, x - s * 0.6, y - s * 1.2, x, y - s * 0.35)
    path.cubicTo(x + s * 0.6, y - s * 1.2, x + s * 1.6, y - s * 0.2, x, y + s * 0.9)
    c.drawPath(path, fill(color, a))
    c.drawPath(path, stroke(INK, 4, a))


def plane(c, x, y, s, rot):
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.scale(s, s)
    p = skia.Path()
    p.moveTo(-60, 0); p.lineTo(70, -40); p.lineTo(-10, 40); p.lineTo(-20, 10); p.close()
    c.drawPath(p, fill(WHITE))
    c.drawPath(p, stroke(INK, 5))
    c.drawLine(-20, 10, 70, -40, stroke(INK, 4))
    c.restore()


def marquee(c, t, word="SYSTEM", color=INK, alt=WHITE, size=250, y0=-40, rows=8):
    s = (word + " • ") * 6
    wd = measure(word + " • ", "anton", size)
    for r in range(rows):
        y = y0 + r * size * 0.95
        off = ((t * 260 * (1 if r % 2 else -1)) + r * 170) % wd
        cc = color if r % 2 else alt
        block_text(c, s, -off - wd, y + size * 0.8, size, color=cc, shadow=None if r % 2 else INK, depth=0.04,
                   anchor="l")


# ================================================================== backgrounds
def draw_bg_kind(c, kind, t, src, cam):
    if kind == "real":
        c.save()
        apply_cam(c, cam)
        c.drawImage(src.bg(), 0, 0, SAMP)
        c.restore()
    elif kind == "yellow":
        paper_bg(c, YEL)
        halftone(c, 540, 700, 900, "#E8B800", spacing=30, dot=12, a=0.55, rot=15)
    elif kind == "paper":
        paper_bg(c, PAPER)
        halftone(c, 540, 1900, 1200, "#D9CFBC", spacing=30, dot=11, a=0.8)
    elif kind == "burst":
        c.drawRect(skia.Rect.MakeWH(W, H), fill(RED))
        rays(c, FACE[0], FACE[1] - 150, 18, "#FF6A3D", rot=t * 0.8)
        halftone(c, FACE[0], FACE[1] - 150, 1100, YEL, spacing=34, dot=14, a=0.9, rot=t * 20)
    elif kind == "ink":
        c.drawRect(skia.Rect.MakeWH(W, H), fill(INK))
        halftone(c, 540, 600, 1100, "#2A2A2A", spacing=30, dot=12)


def bg_plan(t):
    """(kind, reveal 0..1 from the previous kind) for the backdrop behind the person."""
    plan = [("yellow", SYSDID.s - 0.02, SYSDID.e + 0.1)]
    for n in range(4):
        a, b = chapter_iv(n)
        plan.append(("yellow" if n % 2 == 0 else "paper", a, b))
    plan.append(("burst", FRZ_A - 0.02, FRZ_B))
    plan.append(("yellow", CTA_A, TOTAL + 1))
    for kind, a, b in plan:
        if a <= t < b:
            k_in = prog(t, a, 0.16)
            k_out = 1 - prog(t, b - 0.12, 0.12) if b < TOTAL else 1
            return kind, min(k_in, k_out)
    return "real", 1.0


def reveal_clip(c, k):
    r = 2200 * e_out(k)
    path = skia.Path()
    path.addCircle(FACE[0], FACE[1] - 100, r)
    c.clipPath(path, skia.ClipOp.kIntersect, True)


# ================================================================== behind-the-person type
def behind(c, t):
    # "I DIDN'T EDIT IT."
    if DIDNT.s - 0.05 <= t < SYSDID.s:
        c.drawRect(skia.Rect.MakeWH(W, H), fill(INK, 0.45 * e_out(prog(t, DIDNT.s - 0.05, 0.15))))
        kinetic(c, "I DIDN'T", 540, 470, 210, t, DIDNT.s - 0.05, color=WHITE, stagger=0.03)
        kinetic(c, "EDIT IT.", 540, 860, 420, t, DIDNT.w(2) - 0.03, color=YEL, stagger=0.04)
        if t > DIDNT.w(3):
            k = prog(t, DIDNT.w(3), 0.2)
            marker(c, [(70, 760), (560, 700), (1010, 640)], k, RED, 34)
    # "MY SYSTEM DID."
    if SYSDID.s - 0.02 <= t < SYSDID.e + 0.1:
        kinetic(c, "MY", 540, 330, 150, t, SYSDID.s - 0.02, color=INK, shadow=WHITE, depth=0.05)
        kinetic(c, "SYSTEM", 540, 840, 470, t, SYSDID.w(1) - 0.04, color=INK, shadow=WHITE, depth=0.05,
                stagger=0.03)
        if t > SYSDID.w(2):
            stamp(c, "DID.", 860, 1000, 150, prog(t, SYSDID.w(2) - 0.02, 0.4), RED, rot=-12)
    # "4 simple steps"
    if FOUR.s - 0.05 <= t < FOUR.e + 0.2:
        c.drawRect(skia.Rect.MakeWH(W, H), fill(INK, 0.4 * e_out(prog(t, FOUR.s - 0.05, 0.2))))
        if t >= FOUR.w(3) - 0.05:
            k = e_back(prog(t, FOUR.w(3) - 0.05, 0.3))
            c.save()
            c.translate(540, 1240)
            c.scale(k, k)
            block_text(c, "4", 0, 0, 1250, color=YEL, shadow=INK, depth=0.04)
            c.restore()
    # chapter numbers
    for n in range(4):
        a, b = chapter_iv(n)
        if a <= t < b:
            k = prog(t, a, 0.3)
            ko = prog(t, b - 0.12, 0.12)
            c.save()
            c.translate(540 + (1 - e_out(k)) * 500 - e_in(ko) * 600, 1240)
            c.rotate(-4 + 4 * e_out(k))
            ink, sh = (INK, WHITE) if n % 2 == 0 else (YEL, INK)
            block_text(c, f"0{n + 1}", 0, 0, 1000, color=ink, shadow=sh, depth=0.035)
            c.restore()
            kinetic(c, "STEP", 540, 440, 150, t, a, color=WHITE if n % 2 == 0 else INK,
                    shadow=INK if n % 2 == 0 else YEL)
    # "MISTAKE" glitch word
    if SORRY.s <= t < REW_A:
        k = prog(t, SORRY.s, 0.3)
        stamp(c, "MISTAKE!", 540, 620, 150, k, RED, rot=-7, fill_bg=WHITE)
    # BIG TEXT
    if BIG.s - 0.03 <= t < BIG.e + 0.3:
        c.drawRect(skia.Rect.MakeWH(W, H), fill(INK, 0.45))
        kinetic(c, "BIG", 540, 790, 640, t, BIG.w(1) - 0.05, color=YEL, stagger=0.05)
        kinetic(c, "TEXT", 540, 1300, 560, t, BIG.w(2) - 0.05, color=WHITE, stagger=0.04)
    # music bars behind
    eq_bars(c, t, MUSIC.w(1) - 0.02, min(MUSIC.e + 1.2, chapter_iv(2)[0] + 0.1))
    eq_bars(c, t, THEMUSIC.w(2) - 0.02, EVEN.w(1) + 0.1)
    text_spam(c, t)
    # "EVEN THIS?!"
    if FRZ_A - 0.02 <= t < FRZ_B:
        kinetic(c, "EVEN", 540, 520, 330, t, FRZ_A - 0.02, color=YEL, stagger=0.03)
        kinetic(c, "THIS?!", 540, 900, 420, t, FRZ_A + 0.1, color=WHITE, stagger=0.03)
    # CTA marquee
    if t >= CTA_A:
        k = e_out(prog(t, CTA_A, 0.3))
        c.save()
        c.translate(0, (1 - k) * 400)
        c.rotate(-6)
        marquee(c, t, alt=WHITE if t < COMMENT.w(1) else RED)
        c.restore()


# ================================================================== front graphics
def front(c, t, g):
    # hook: LIVE tag on "right now"
    if HOOK.w(4) <= t < DIDNT.s:
        tape(c, "● RIGHT NOW", 250, 330, 40, prog(t, HOOK.w(4), 0.25), rot=-5, bg=RED, fg=WHITE, seed=1)
    # split screen is drawn whole elsewhere
    # "for my own videos": arrow to the face
    if BUILT.w(5) <= t < FOUR.s:
        k = prog(t, BUILT.w(5), 0.35)
        tape(c, "BUILT IT MYSELF", 300, 480, 40, k, rot=-6, seed=5)
        arrow(c, 300, 540, 470, 790, prog(t, BUILT.w(5) + 0.1, 0.35), WHITE, 10)
    if FOUR.s - 0.05 <= t < FOUR.w(3) - 0.05:
        kinetic(c, "IT WORKS IN", 540, CAP_Y, 110, t, FOUR.s - 0.05, color=WHITE, stagger=0.02)
    if FOUR.w(3) - 0.05 <= t < min(FOUR.e + 0.2, chapter_iv(0)[0]):
        kinetic(c, "SIMPLE STEPS", 540, CAP_Y, 130, t, FOUR.w(4) - 0.03, color=WHITE, stagger=0.02)
    # chapter label
    for n in range(4):
        a, b = chapter_iv(n)
        if a <= t < b:
            tape(c, STEP_NAMES[n], 540, 1450, 64, prog(t, a + 0.06, 0.3), rot=-3, bg=INK if n % 2 == 0 else YEL,
                 fg=YEL if n % 2 == 0 else INK, seed=n, name="anton")
    step_tracker(c, t)
    # step 1
    viewfinder(c, t, REC.s - 0.05, MOK1.e + 0.2)
    if ONETAKE.w(1) <= t < MOK1.s + 0.3:
        stamp(c, "ONE TAKE", 540, 590, 130, prog(t, ONETAKE.w(1) - 0.02, 0.4), RED, rot=-8, fill_bg=WHITE)
    if MOK1.w(2) <= t < LIKE.s:
        check_mark(c, 900, 600, 150, prog(t, MOK1.w(2), 0.25), RED, 26)
    timeline_strip(c, t)
    if REW_A <= t < REW_B:
        a = 0.6 + 0.4 * (int(t * 12) % 2)
        rewind_icon(c, 80, 560, 70, a)
        kit.text(c, "REWIND", 240, 585, "monob", 70, color=WHITE, a=a, anchor="l", shadow=6)
        tape(c, "SYSTEM: CUT IT ✂" if False else "SYSTEM: CUT IT", 540, 720, 48, prog(t, REW_A, 0.15), rot=-4,
             bg=YEL, seed=7)
    if MOK2.w(2) <= t < STEPS[1].s:
        check_mark(c, 880, 610, 190, prog(t, MOK2.w(2), 0.25), RED, 30)
        tape(c, "NO RESHOOTS", 300, 640, 40, prog(t, MOK2.w(2) + 0.1, 0.3), rot=-6, seed=8)
    # step 2
    prompt_box(c, t)
    if MUSIC.w(1) <= t < MUSIC.w(1) + 0.12:
        g["flash"] = max(g.get("flash", 0), 0.5 * (1 - (t - MUSIC.w(1)) / 0.12))
    # step 3
    checklist(c, t)
    speed_lines(c, t, ZOOMS.s)
    # freeze: "even this"
    if FRZ_A <= t < FRZ_B:
        confetti(c, t, FRZ_A)
    # step 4
    if CHECK.w(1) <= t < CHANGE.s + 0.1:
        check_mark(c, 830, 560, 280, prog(t, CHECK.w(1), 0.3), RED, 36)
        stamp(c, "CHECKED", 330, 560, 110, prog(t, CHECK.w(2), 0.4), RED, rot=-10, fill_bg=WHITE)
    if CHANGE.s <= t < READY.s:
        bubble(c, 350, 470, "want a change?", prog(t, CHANGE.s, 0.3), who="YOU", size=50)
    if SAYIT.w(2) <= t < READY.s:
        bubble(c, 650, 660, "make the captions red", prog(t, SAYIT.w(2), 0.3), who="YOU", size=42, name="monob",
               tail="r")
        if t >= SAYIT.e:
            bubble(c, 330, 830, "done ✓" if False else "done.", prog(t, SAYIT.e, 0.3), who="SYSTEM", dark=True,
                   size=46, name="monob")
    platform_cards(c, t)
    # CTA
    comment_ui(c, t)
    if t >= SEND.e + 0.15:
        k = prog(t, SEND.e + 0.15, 0.4)
        stamp(c, "COMMENT \"SYSTEM\"", 540, 640, 100, k, YEL, rot=-4, fill_bg=INK)
        arrow(c, 930, 720, 960, 1290, prog(t, SEND.e + 0.4, 0.35), INK, 14, bend=-0.2)


# ================================================================== the split screen ("left" / "right")
def phone(c, img_fn, cx, cy, w, rot, label=None):
    h = w * 16 / 9
    c.save()
    c.translate(cx, cy)
    c.rotate(rot)
    c.drawRRect(kit.rrect(-w / 2 - 18 + 10, -h / 2 - 18 + 16, w + 36, h + 36, 58), fill("#000000", 0.35, blur=18))
    c.drawRRect(kit.rrect(-w / 2 - 18, -h / 2 - 18, w + 36, h + 36, 58), fill(INK))
    c.save()
    c.clipRRect(kit.rrect(-w / 2, -h / 2, w, h, 42), skia.ClipOp.kIntersect, True)
    c.translate(-w / 2, -h / 2)
    c.scale(w / W, h / H)
    img_fn(c)
    c.restore()
    c.drawRRect(kit.rrect(-60, -h / 2 + 10, 120, 30, 15), fill(INK))
    c.restore()


def draw_split(c, t, src_ts, g):
    raw = Src(src_ts, graded=False)
    edited = Src(src_ts)
    ka = e_out(prog(t, SPLIT_A, 0.35))
    kb = e_in(prog(t, SPLIT_B - 0.3, 0.3))       # grow the right phone back to full screen
    paper_bg(c)
    halftone(c, 540, 1900, 1300, "#D9CFBC", spacing=30, dot=11, a=0.8)
    pw = 460

    def raw_fn(cc):
        cc.drawImage(raw.bg(), 0, 0, SAMP)
        cc.drawCircle(90, 110, 22, fill(RED))
        kit.text(cc, "REC", 130, 128, "monob", 50, color=WHITE, anchor="l", shadow=4)

    def edit_fn(cc):
        cc.save()
        apply_cam(cc, (1.12, 0, 0, 0))
        cc.drawImage(edited.bg(), 0, 0, SAMP)
        cc.restore()
        cur = [w for w in WORDS if w["os"] - 0.04 <= t < w["oe"] + 0.1]
        if cur:
            s = cap_text(cur[-1])
            wd = measure(s, "anton", 150)
            hilite(cc, 540 - wd / 2 - 24, 1300, wd + 48, 150, 1, YEL, seed=cur[-1]["i"], rot=0)
            block_text(cc, s, 540, 1420, 150, color=INK, shadow=None)

    # left phone slides in
    lx = lerp(-400, 290, ka) - kb * 700
    phone(c, raw_fn, lx, 900, pw, -4 * ka)
    # right phone: from full screen down into place, and back up at the end
    k = ka * (1 - kb)
    rcx, rcy = lerp(540, 790, k), lerp(H / 2, 900, k)
    rw = lerp(W * 1.04, pw, k)
    phone(c, edit_fn, rcx, rcy, rw, 4 * k)
    if kb > 0:
        return
    # labels + arrows
    tape(c, "STRAIGHT FROM MY PHONE", 290, 400, 30, prog(t, LEFT.w(6), 0.3), rot=-6, seed=2)
    arrow(c, 200, 430, 230, 520, prog(t, LEFT.w(6) + 0.1, 0.3), INK, 8)
    tape(c, "WHAT YOU'RE WATCHING", 790, 400, 30, prog(t, RIGHT.w(4), 0.3), rot=5, bg=YEL, seed=3)
    arrow(c, 880, 430, 850, 520, prog(t, RIGHT.w(4) + 0.1, 0.3), INK, 8)
    if SAME.s - 0.02 <= t < NOAPP.s:
        stamp(c, "SAME VIDEO", 540, 900, 110, prog(t, SAME.s - 0.02, 0.4), RED, rot=-8, fill_bg=PAPER)
    if t >= NOAPP.s:
        k = e_back(prog(t, NOAPP.s, 0.3))
        c.save()
        c.translate(540, 1000)
        c.scale(k, k)
        c.rotate(-6)
        card(c, -130, -130, 260, 260, INK, r=58, shadow=0.45)
        for j, (cc_, ww) in enumerate([(YEL, 150), (BLUE, 110), (RED, 170)]):
            c.drawRRect(kit.rrect(-90, -70 + j * 52, ww, 32, 10), fill(cc_))
        c.drawLine(-20, -96, -20, 96, stroke(WHITE, 6))
        c.restore()
        kk = prog(t, NOAPP.w(1), 0.3)
        c.drawCircle(540, 1000, 190, stroke(RED, 30, clamp(kk * 4)))
        marker(c, [(410, 1130), (670, 870)], kk, RED, 30)
    g["noise"] = 0


# ================================================================== the page grid ("every video on my page")
GRID_LOOKS = [("yellow", "SYSTEM", 2.0), ("ink", "4 STEPS", 14.6), ("paper", "ONE TAKE", 18.4),
              ("real", "BIG TEXT", 32.6), (None, None, None), ("burst", "EVEN THIS", 41.8),
              ("paper", "CHECK", 43.5), ("yellow", "NO APP", 10.5), ("ink", "COMMENT", 55.3)]


def draw_grid(c, t, src_ts, g):
    gap = 70
    tw, th = W, H
    k_in = e_io(prog(t, GRID_A, 0.55))
    k_more = e_io(prog(t, EVERY.s - 0.05, 0.6))
    k_out = e_in(prog(t, GRID_B - 0.3, 0.3))
    z = lerp(1.0, 0.45, k_in)
    z = lerp(z, 0.3, k_more)
    z = lerp(z, 1.0, k_out)
    c.drawRect(skia.Rect.MakeWH(W, H), fill(INK))
    c.save()
    c.translate(W / 2, H / 2)
    c.scale(z, z)
    c.translate(-W / 2, -H / 2)
    for j in range(9):
        r, cc = divmod(j, 3)
        x = (cc - 1) * (tw + gap)
        y = (r - 1) * (th + gap)
        c.save()
        c.translate(x, y)
        c.clipRRect(kit.rrect(0, 0, tw, th, 60), skia.ClipOp.kIntersect, True)
        if j == 4:
            src = Src(src_ts)
            c.drawImage(src.bg(), 0, 0, SAMP)
        else:
            kind, word, st = GRID_LOOKS[j]
            if z > 0.98:
                c.restore()
                continue
            ts = st + ((t - GRID_A) % 2.0)
            src = Src(ts)
            draw_bg_kind(c, kind, t, src, (1, 0, 0, 0))
            if kind != "real":
                c.drawImage(src.outline(10), 0, 0, SAMP)
            else:
                c.drawRect(skia.Rect.MakeWH(W, H), fill(INK, 0.35))
            block_text(c, word, 540, 760, 260 if len(word) < 7 else 200, color=YEL if kind != "yellow" else INK,
                       shadow=INK if kind != "yellow" else WHITE)
            c.drawImage(src.person(), 0, 0, SAMP)
            if t < EVERY.w(1):
                c.drawRect(skia.Rect.MakeWH(W, H), fill(INK, 0.45))
        c.restore()
    c.restore()
    # labels
    if k_in > 0.9 and k_out == 0:
        cz = z
        cw, ch = W * cz, H * cz
        x0, y0 = W / 2 - cw / 2, H / 2 - ch / 2
        if t < EVERY.s:
            tape(c, "THIS WHOLE VIDEO", 540, y0 - 40, 44, prog(t, MADE.w(3), 0.3), rot=-4, bg=YEL, seed=11)
            c.drawRRect(kit.rrect(x0 - 10, y0 - 10, cw + 20, ch + 20, 40), stroke(YEL, 12, prog(t, MADE.w(3), 0.2)))
        else:
            tape(c, "EVERY VIDEO ON MY PAGE", 540, 210, 46, prog(t, EVERY.w(1), 0.3), rot=-3, bg=YEL, seed=12)


# ================================================================== frame
def draw(c, t, f):
    g = {}
    src_ts, kind = src_at(t)
    c.clear(col(INK))
    if SPLIT_A <= t < SPLIT_B:
        draw_split(c, t, src_ts, g)
        draw_captions(c, t)
        return g
    if GRID_A <= t < GRID_B:
        draw_grid(c, t, src_ts, g)
        draw_captions(c, t)
        return g
    src = Src(src_ts)
    cam = camera(t)
    bk, rk = bg_plan(t)
    if bk != "real" and rk >= 1:
        draw_bg_kind(c, bk, t, src, cam)
    else:
        draw_bg_kind(c, "real", t, src, cam)
        if bk != "real":
            c.save()
            reveal_clip(c, rk)
            draw_bg_kind(c, bk, t, src, cam)
            c.restore()
    behind(c, t)
    c.save()
    apply_cam(c, cam)
    if bk != "real":
        c.drawImage(src.outline(10), 0, 0, SAMP, skia.Paint(Alphaf=clamp(rk * 2)))
    c.drawImage(src.person(), 0, 0, SAMP)
    c.restore()
    front(c, t, g)
    hi = RED if SAYIT.e <= t < GRID_A else YEL
    draw_captions(c, t, hi)
    # glitches / looks
    if SORRY.s <= t < SORRY.s + 0.25 or REW_A <= t < REW_B:
        g["ca"] = 9
    if REW_A <= t < REW_B:
        g["vhs"] = 1
    if FRZ_A <= t < FRZ_A + 0.18:
        g["ca"] = 12
        g["flash"] = 0.8 * (1 - (t - FRZ_A) / 0.18)
    if t < 0.12:
        g["flash"] = 1 - t / 0.12
    for st in (SYSDID.w(1), BIG.w(1), FOUR.w(3), FRZ_A, FRZ_B):
        if st <= t < st + 0.08:
            g["ca"] = max(g.get("ca", 0), 7)
    return g


# shakes keyed to impacts
SHAKES += [(SYSDID.w(1), 16), (DIDNT.w(3), 10), (FOUR.w(3), 14), (BIG.w(1), 14), (BIG.w(2), 12), (MUSIC.w(1), 18),
           (FRZ_A, 22), (FRZ_B, 12), (CHECK.w(1), 8), (COMMENT.w(1), 12)]


# ================================================================== post
_VIG = None


def post(rgb, g, f):
    global _VIG
    if _VIG is None:
        h, w = rgb.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        _VIG = (1 - 0.28 * np.clip(r - 0.55, 0, None) ** 1.6)[..., None].astype(np.float32)
    out = rgb.astype(np.float32)
    s = rgb.shape[1] / W
    if g.get("vhs"):
        lum = out @ np.array([0.299, 0.587, 0.114], np.float32)
        out = lum[..., None] * 0.55 + out * 0.45
        out *= np.array([0.95, 1.0, 1.08], np.float32)
        out[::4] *= 0.78
        band = int((f * 37) % rgb.shape[0])
        out[band:band + int(40 * s)] = np.roll(out[band:band + int(40 * s)], int(30 * s), axis=1) * 1.15
    ca = int(g.get("ca", 0) * s)
    if ca:
        out[..., 0] = np.roll(out[..., 0], ca, axis=1)
        out[..., 2] = np.roll(out[..., 2], -ca, axis=1)
    if g.get("flash"):
        out = out + (255 - out) * g["flash"]
    out *= _VIG
    out = np.clip(out, 0, 255).astype(np.uint8)
    return kit.grain(out, f, amt=0.028)


FILM = kit.Film(draw, TOTAL, FPS, post=post, out_dir=OUT)


# ================================================================== audio
def sfx_list():
    S = []

    def a(t, kind, gain=-8, **kw):
        S.append(dict(t=t, kind=kind, gain_db=gain, **kw))

    a(0.0, "impact", -6)
    a(HOOK.w(4), "pop", -10)
    a(DIDNT.w(2) - 0.05, "whoosh", -12)
    a(DIDNT.w(3), "swish", -8)
    a(SYSDID.s - 0.12, "whoosh", -10)
    a(SYSDID.w(1), "impact", -5)
    a(SYSDID.w(2), "shutter", -8)
    a(SPLIT_A, "whoosh", -9)
    a(LEFT.w(6), "pop", -11)
    a(RIGHT.w(4), "pop", -11)
    a(SAME.s, "impact", -10)
    a(NOAPP.s, "pop", -9)
    a(NOAPP.w(1), "swish", -9)
    a(SPLIT_B - 0.3, "whoosh", -10)
    a(BUILT.w(5), "pop", -12)
    a(FOUR.w(3), "impact", -6)
    a(FOUR.w(4), "swish", -12)
    for n in range(4):
        a(chapter_iv(n)[0] - 0.05, "whoosh", -8)
        a(chapter_iv(n)[0] + 0.1, "tick", -10)
    a(REC.s, "shutter", -10)
    a(ONETAKE.w(1), "impact", -9)
    a(MOK1.w(2), "ding", -12)
    a(SORRY.s, "glitch", -6)
    a(REW_A, "downlifter", -8)
    a(REW_B - 0.05, "click", -4)
    a(MOK2.w(2), "ding", -10)
    a(TELL.s, "pop", -12)
    for P_, w0 in ((SHORT, 1), (BIG, 0), (MUSIC, 0)):
        a(P_.w(w0), "typing", -14, dur=max(0.3, P_.e - P_.w(w0)))
        a(P_.e, "click", -8)
    a(SHORT.e, "swish", -10)
    a(BIG.w(1), "impact", -5)
    a(BIG.w(2), "impact", -7)
    a(MUSIC.w(1), "bass_drop", -4)
    a(EDITS.s, "pop", -10)
    for tk in (CUTS.we(3), ZOOMS.we(1), TEXT.we(2), THEMUSIC.we(2)):
        a(tk - 0.05, "tick", -8)
    a(ZOOMS.s - 0.05, "whoosh", -8)
    for j in range(6):
        a(TEXT.s + j * 0.07, "pop", -13, pan=(hrand("p", j) - 0.5))
    a(EVEN.s - 0.6, "riser", -9, dur=0.6 + FRZ_A - EVEN.s)
    a(FRZ_A, "impact", -3)
    a(FRZ_A + 0.02, "sparkle", -8)
    a(FRZ_A + 0.1, "bass_drop", -7)
    a(FRZ_B - 0.08, "whoosh", -9)
    a(CHECK.w(1), "swish", -9)
    a(CHECK.w(2), "impact", -10)
    a(CHANGE.s, "pop", -11)
    a(SAYIT.w(2), "pop", -11)
    a(SAYIT.e, "ding", -12)
    for j in range(3):
        a(READY.w(4 + j), "whoosh", -12)
    a(READY.w(6) + 0.3, "ding", -11)
    a(GRID_A, "whoosh", -8)
    a(EVERY.s, "riser", -12, dur=0.6)
    a(GRID_B - 0.3, "whoosh", -8)
    a(CTA_A + 0.05, "impact", -8)
    a(COMMENT.w(1), "typing", -12, dur=0.35)
    a(COMMENT.e + 0.08, "pop", -6)
    a(COMMENT.e + 0.15, "sparkle", -10)
    a(SEND.s, "whoosh", -9)
    a(SEND.e + 0.15, "impact", -8)
    return S


def build_audio(sfx=None, mood="hype", name="mix.wav", seed=11):
    """voice cut to the EDL + music bed (muffled until "add music") + sfx, -> work/<name>.
    sfx: [{t, kind | clip, gain_db, pan?, dur?}] (defaults to this edit's list)."""
    SR = ak.SR
    work = HERE / "work"
    vpath = work / "voice_clean.wav"
    if not vpath.exists():
        ff("-i", str(HERE / "raw" / "take.mp4"), "-vn", "-af",
           "highpass=f=90,afftdn=nf=-28,acompressor=threshold=-20dB:ratio=3:attack=5:release=90:makeup=4,"
           "deesser=i=0.4", "-ar", str(SR), "-ac", "2", str(vpath))
    raw = ak.read_audio(vpath)
    n = int(TOTAL * SR) + 1
    voice = np.zeros((n, 2), np.float32)
    xf = int(0.008 * SR)
    for kind, a, b, o, d in EDL:
        i0 = int(o * SR)
        if kind == "play":
            seg = raw[int(a * SR):int(b * SR)].copy()
        elif kind == "rev":
            from scipy.signal import resample_poly
            seg = raw[int(b * SR):int(a * SR)][::-1]
            seg = resample_poly(seg, 1, 7, axis=0).astype(np.float32) * 0.7
        else:
            continue
        if len(seg) > 2 * xf:
            ramp = np.linspace(0, 1, xf, dtype=np.float32)[:, None]
            seg[:xf] *= ramp
            seg[-xf:] *= ramp[::-1]
        seg = seg[: max(0, n - i0)]
        voice[i0:i0 + len(seg)] += seg
    # music: muffled until "add music", then the full bed slams in
    bed = ak.music_bed(mood, seconds=TOTAL + 2, intro_bars=0, seed=seed)[:n]
    if len(bed) < n:
        bed = np.pad(bed, ((0, n - len(bed)), (0, 0)))
    low = np.stack([ak.filt(bed[:, ch], "lp", 520) for ch in range(2)], 1)
    drop = int(MUSIC.w(1) * SR)
    env = np.zeros(n, np.float32)
    env[drop:] = 1
    k = int(0.03 * SR)
    env[drop:drop + k] = np.linspace(0, 1, k)
    mus = low * (1 - env[:, None]) * ak.db(-6) + bed * env[:, None]
    # dip for the freeze, hold under the rewind
    for (a_, b_) in ((REW_A, REW_B),):
        mus[int(a_ * SR):int(b_ * SR)] *= 0.4
    mus *= ak.duck_gain(voice, -9)[:, None]
    fo = int(1.2 * SR)
    mus[-fo:] *= np.linspace(1, 0, fo)[:, None]
    out = voice + mus * ak.db(-13)
    for s in (sfx if sfx is not None else sfx_list()):
        kind = s.get("kind")
        if "clip" in s:
            clip = s["clip"]
        else:
            clip = ak.SFX[kind](s["dur"]) if "dur" in s and kind in ("whoosh", "riser", "typing") else ak.SFX[kind]()
        ak.place(out, clip, s["t"], s["gain_db"], s.get("pan", 0.0))
    peak = np.max(np.abs(out)) or 1
    if peak > 0.98:
        out = np.tanh(out / peak * 1.2) / math.tanh(1.2) * 0.98
    path = work / name
    ak.write_wav(path, out)
    print("->", path)
    return path


def finish(picture, audio, out):
    """delivery file: H.264 high, ~12 Mbps cap (grain-friendly), AAC 48k at -14 LUFS."""
    ln = loudnorm_filter(audio)
    ff("-i", str(picture), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "slow",
       "-crf", "19", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p", "-profile:v", "high", "-af", ln,
       "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out))
    print("->", out)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "stills":
        FILM.stills([float(x) for x in sys.argv[2:]])
    elif cmd == "sheet":
        FILM.sheet(cols=8, sheet_n=48) if False else FILM.sheet(
            [round(TOTAL * (i + 0.5) / 48, 2) for i in range(48)], cols=8)
    elif cmd == "audio":
        build_audio()
    elif cmd == "info":
        print(f"total {TOTAL:.2f}s  (raw {NSRC / FPS:.1f}s)")
        for s in EDL:
            print(f"  {s[0]:6} src {s[1]:6.2f}-{s[2]:6.2f}  out {s[3]:6.2f} +{s[4]:.2f}")
    elif cmd == "render":
        draft = "--draft" in sys.argv
        pic = FILM.render(OUT / ("draft_picture.mp4" if draft else "picture.mp4"), draft=draft)
        aud = build_audio()
        finish(pic, aud, OUT / ("draft.mp4" if draft else "system_reel.mp4"))


if __name__ == "__main__":
    main()
