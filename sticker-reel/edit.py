"""Vibe Editing System ad: the full edit of the raw phone take, in the paper-sticker scrapbook style.

    python3 edit.py stills 1.0 4.2 ...    -> out/stills/*.png  (half res)
    python3 edit.py sheet                 -> out/sheet.png
    python3 edit.py audio                 -> work/mix.wav
    python3 edit.py render [--draft]      -> out/vibe_editing_reel.mp4

Every graphic is cued off the spoken words (cut.py holds the cut list and the word clock). The script describes
the edit itself, so each instruction happens on screen as it is said: the pauses get snipped, the captions get
punchy, the title goes behind him, the look goes cinematic, the music builds and drops.
"""

import math
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cut  # noqa: E402
from cut import FREEZES, P, WORDS, src_at  # noqa: E402
from theme import (BLUSH, INK, KRAFT, PAPER, PINK, PINK_D, RED, RULE, SAMP, WHITE, YEL, Sticker, arrow,  # noqa: E402
                   check_mark, clamp, e_back, e_in, e_io, e_out, fill, font, hand, hrand, ink_word, kit,
                   label_sticker, lerp, marker, measure, paper, paper_img, pink_word, pop_k, prog, rrect,
                   scribble_ellipse, slap, spring, stamp, strike, stroke, tape, type_text, word_w)

W, H, FPS = 1080, 1920, 30
OUT = HERE / "out"
FR = HERE / "work" / "frames"
NSRC = len(list(FR.glob("f_*.jpg")))
FACE = (590, 900)            # zoom anchor: middle of the face in the 1080x1920 frame
HEAD_TOP = 665               # top of the hair (median over the take)
END_CARD = 2.9
TOTAL = cut.SPEECH_END + END_CARD

# ================================================================== the script on the output clock
HOOK = P("video editing just changed")
NOTICED = P("and most people haven't noticed yet")
YEARS = P("for years editing meant one thing")
SIT = P("sit in front of timeline")
DRAG = P("drag clips")
KEYS = P("set keyframes")
HOURS = P("and spend six hours")
REEL60 = P("on a sixty-second reel")
FLIPS = P("vibe editing flips that")
DONTEDIT = P("you don't edit anymore")
DIRECT = P("you direct")
TELL = P("you tell the system what you want")
BRIEF = P("the same way you'd brief a top editor")
CUTP = P("cut the pauses")
PUNCHY = P("make the captions punchy")
TITLE = P("put the title behind me")
CINE = P("give it a cinematic look")
MUSIC = P("add music that builds")
BUILDS = P("and it builds it")
EVERY = [P("every cut"), P("every caption"), P("every effect"), P("every sound")]
CODE = P("made in code")
LAPTOP = P("right on your laptop")
NOTJUST = P("and it's not just reels")
SAMESYS = P("the same system makes")
FORMATS = [P("motion graphics", 1), P("product ads"), P("claymation"), P("vfx"), P("podcast clips")]
FIFTY = P("even fifty versions of one ad")
TEST = P("so you can test what works")
NEED = P("so what do you actually need")
FOOTAGE = P("your footage")
YLAPTOP = P("your laptop", 1)
VES = P("and the vibe editing system")
SKILLS = P("the editing skills")
COURSE = P("plus a full course")
SHOWS = P("that shows you how to direct every one of them")
NOAE = P("no after effects")
NOPR = P("no premiere pro")
NOKF = P("no keyframes")
WATCHED = P("and this video you just watched")
NOAPP = P("i didn't open a single editing app")
RECORDED = P("i recorded it on my phone")
REST = P("and the system did the rest")
DROP = FREEZES[0][2] + 0.02            # the freeze after "and it builds it": the music drops here
BPM = 100.0
BEAT = 60.0 / BPM
END_A = cut.SPEECH_END

# section windows (output clock)
SEC = dict(
    hook=(0.0, YEARS.s - 0.05), years=(YEARS.s - 0.05, SIT.s - 0.04), old=(SIT.s - 0.04, FLIPS.w(2)),
    flip=(FLIPS.w(2), TELL.s - 0.05), brief=(TELL.s - 0.05, CINE.s - 0.04), cine=(CINE.s - 0.04, MUSIC.s - 0.04),
    music=(MUSIC.s - 0.04, DROP), every=(DROP, NOTJUST.s - 0.05), formats=(NOTJUST.s - 0.05, FIFTY.s - 0.03),
    fifty=(FIFTY.s - 0.03, NEED.s - 0.05), need=(NEED.s - 0.05, SKILLS.s - 0.05),
    product=(SKILLS.s - 0.05, NOAE.s - 0.04), no=(NOAE.s - 0.04, WATCHED.s - 0.04),
    reveal=(WATCHED.s - 0.04, END_A), end=(END_A, TOTAL + 1),
)


def section(t):
    for k, (a, b) in SEC.items():
        if a <= t < b:
            return k
    return "end"


TEAR_T = HOOK.w(3) - 0.02              # "changed": the wall tears away to the notebook


# ================================================================== source frames, matte, grade
_cache = {}


def frame_rgb(fi):
    fi = int(clamp(fi, 0, NSRC - 1))
    if fi not in _cache:
        if len(_cache) > 12:
            _cache.pop(next(iter(_cache)))
        _cache[fi] = cv2.imread(str(FR / f"f_{fi:05d}.jpg"))[..., ::-1].copy()
    return _cache[fi]


_ALPHA = None


def alpha_small(fi):
    """refined matte at 540x960: a contrast curve kills the faint ghost of the chair behind his shoulder."""
    global _ALPHA
    if _ALPHA is None:
        _ALPHA = np.load(HERE / "work" / "alpha.npy", mmap_mode="r")
    a = np.asarray(_ALPHA[int(clamp(fi, 0, len(_ALPHA) - 1))]).astype(np.float32) / 255
    a = np.clip((a - 0.28) / 0.5, 0, 1)
    a = a * a * (3 - 2 * a)
    return (a * 255).astype(np.uint8)


def _curve(x, lift=0.0, gain=1.0, s=0.07):
    y = x + s * np.sin(2 * math.pi * (x - 0.5)) * 0.5 * (1 - np.abs(2 * x - 1)) * 2
    return np.clip(lift + y * (gain - lift), 0, 1)


def _luts():
    x = np.arange(256, dtype=np.float32) / 255
    L = {}
    # clean: gentle S, warm highlights to sit on cream paper, shadows kept neutral
    L["clean"] = [_curve(x, 0.015, 1.0, 0.09) * 1.02, _curve(x, 0.012, 0.99, 0.09), _curve(x, 0.02, 0.955, 0.08)]
    # old way: flat, cool, faded
    L["old"] = [_curve(x, 0.07, 0.93, 0.0), _curve(x, 0.075, 0.94, 0.0), _curve(x, 0.09, 0.97, 0.0)]
    # cinematic: deeper contrast, teal shadows, amber highlights
    L["cine"] = [_curve(x, 0.0, 1.02, 0.16) ** 1.08, _curve(x, 0.01, 0.98, 0.15), _curve(x ** 0.92, 0.045, 0.9, 0.12)]
    L["raw"] = [x, x, x]
    return {k: [(np.clip(c, 0, 1) * 255).astype(np.uint8) for c in v] for k, v in L.items()}


LUTS = _luts()
SAT = {"clean": 1.08, "old": 0.62, "cine": 0.92, "raw": 1.0}


def grade(rgb, kind="clean"):
    if kind == "raw":
        return rgb
    lut = LUTS[kind]
    o = np.empty_like(rgb)
    for ch in range(3):
        o[..., ch] = lut[ch][rgb[..., ch]]
    f = o.astype(np.float32)
    lum = f @ np.array([0.299, 0.587, 0.114], np.float32)
    f = lum[..., None] + (f - lum[..., None]) * SAT[kind]
    return np.clip(f, 0, 255).astype(np.uint8)


def grade_kind(t):
    s = section(t)
    if s in ("years", "old"):
        return "old"
    if s == "cine":
        return "cine"
    return "clean"


class Src:
    """everything drawable from one source frame: graded plate, cut-out person, sticker border and shadow."""

    def __init__(self, ts, kind="clean"):
        self.fi = int(round(ts * FPS))
        self.rgb = grade(frame_rgb(self.fi), kind)
        self._a = self._small = None

    @property
    def small(self):
        if self._small is None:
            self._small = alpha_small(self.fi)
        return self._small

    @property
    def alpha(self):
        if self._a is None:
            self._a = cv2.resize(self.small, (W, H), interpolation=cv2.INTER_LINEAR)
        return self._a

    def cine_plate(self):
        """dramatic lighting: the wall drops into a dark teal falloff, the speaker stays lit."""
        a = self.alpha.astype(np.float32)[..., None] / 255
        yy, xx = np.mgrid[0:H:4, 0:W:4].astype(np.float32)
        r = np.sqrt(((xx - FACE[0]) / 620) ** 2 + ((yy - FACE[1] + 80) / 900) ** 2)
        v = cv2.resize(np.clip(1.15 - r, 0.12, 1.0), (W, H))[..., None]
        f = self.rgb.astype(np.float32)
        wall = f * 0.34 * v * np.array([0.78, 0.98, 1.08], np.float32)
        lit = f * (0.82 + 0.18 * v)
        out = wall * (1 - a) + lit * a
        self.rgb = np.clip(out, 0, 255).astype(np.uint8)
        return self.plate()

    def plate(self):
        return skia.Image.fromarray(np.dstack([self.rgb, np.full((H, W), 255, np.uint8)]),
                                    colorType=skia.kRGBA_8888_ColorType)

    def person(self):
        return skia.Image.fromarray(np.dstack([self.rgb, self.alpha]), colorType=skia.kRGBA_8888_ColorType)

    def border(self, px=7):
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1))
        d = cv2.GaussianBlur(cv2.dilate(self.small, k), (3, 3), 0)
        d = cv2.resize(d, (W, H), interpolation=cv2.INTER_LINEAR)
        arr = np.zeros((H, W, 4), np.uint8)
        arr[..., :3] = 255
        arr[..., 3] = d
        return skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType)

    def shadow(self, px=7):
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1))
        d = cv2.GaussianBlur(cv2.dilate(self.small, k), (0, 0), 6)
        d = cv2.resize(d, (W, H), interpolation=cv2.INTER_LINEAR)
        arr = np.zeros((H, W, 4), np.uint8)
        arr[..., 0], arr[..., 1], arr[..., 2] = 40, 25, 10
        arr[..., 3] = (d.astype(np.float32) * 0.42).astype(np.uint8)
        return skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType)


# ================================================================== camera
ZLEVELS = [1.0, 1.07, 1.02, 1.11, 1.04, 1.09]
PUNCH = [  # (t, extra zoom) quick punch-ins on key words
    (HOOK.w(3), 0.10), (HOURS.w(2), 0.08), (DIRECT.w(1), 0.12), (PUNCHY.w(3), 0.10), (CODE.w(2), 0.06),
    (NEED.w(5), 0.08), (VES.w(3), 0.07), (NOKF.w(1), 0.09), (REST.w(4), 0.06),
]
SHAKES = [(TEAR_T, 10), (DIRECT.w(1), 18), (DROP, 26), (PUNCHY.w(0), 7), (PUNCHY.w(1), 8), (PUNCHY.w(2), 9),
          (PUNCHY.w(3), 14), (NOAE.s, 10), (NOPR.s, 10), (NOKF.s, 14), (TITLE.w(2), 8)]
FLAT = [SEC["fifty"], SEC["reveal"], SEC["end"]]
RUN_STARTS = [s[2] for s in cut.EDL]


def in_any(t, ivs):
    return any(a <= t < b for a, b in ivs)


def camera(t):
    """(scale, dx, dy, rot) for the footage around FACE."""
    if in_any(t, FLAT):
        z = 1.0
    else:
        k = max([i for i, s in enumerate(RUN_STARTS) if s <= t + 1e-6] or [0])
        z = ZLEVELS[k % len(ZLEVELS)] * (1 + 0.010 * (t - RUN_STARTS[k]))        # slow push inside a run
    if t < 0.35:
        z *= lerp(1.22, 1.0, e_out(t / 0.35))                                     # opening slam
    for pt, amt in PUNCH:
        if pt <= t < pt + 0.9:
            k = t - pt
            z *= 1 + amt * (e_out(k / 0.12) if k < 0.12 else 1 - e_io((k - 0.5) / 0.4) if k > 0.5 else 1)
    if DROP <= t < SEC["every"][1]:                                               # beat pump after the drop
        ph = ((t - DROP) % BEAT) / BEAT
        z *= 1 + 0.03 * (1 - ph) ** 3
    dx = dy = rot = 0.0
    for st, amp in SHAKES:
        if st <= t < st + 0.32:
            k = 1 - (t - st) / 0.32
            dx += amp * k * math.sin(t * 97.0)
            dy += amp * k * math.sin(t * 79.0 + 1)
            rot += amp * 0.05 * k * math.sin(t * 61.0)
    return z, dx, dy, rot


def apply_cam(c, cam, anchor=FACE):
    z, dx, dy, rot = cam
    c.translate(anchor[0] + dx, anchor[1] + dy)
    c.rotate(rot)
    c.scale(z, z)
    c.translate(-anchor[0], -anchor[1])


def head_top_screen(cam):
    z, dx, dy, rot = cam
    return FACE[1] + dy - (FACE[1] - HEAD_TOP) * z


# ================================================================== captions (behind the speaker)
ACCENTS = ["changed", "noticed", "years", "one thing", "timeline", "keyframes", "six hours", "sixtysecond", "flips",
           "edit", "direct", "system", "top editor", "pauses", "punchy", "title", "cinematic", "music", "builds",
           "builds", "cut", "caption", "effect", "sound", "code", "laptop", "reels", "motion graphics",
           "product ads", "claymation", "vfx", "podcast clips", "fifty versions", "test", "need", "footage", "laptop",
           "vibe editing system", "skills", "full course", "direct", "after effects", "premiere pro", "keyframes",
           "watched", "single", "phone", "rest"]


def _accent_set():
    acc, pos = set(), 0
    for ph in ACCENTS:
        toks = ph.lower().split()
        for i in range(pos, len(WORDS) - len(toks) + 1):
            if all(WORDS[i + j]["k"] == toks[j] for j in range(len(toks))):
                acc.update(range(i, i + len(toks)))
                pos = i + len(toks)
                break
        else:
            print("accent not found:", ph)
    return acc


ACC = _accent_set()
CAP_OFF = [SEC["no"], SEC["end"], (TITLE.s - 0.02, TITLE.e + 0.25)]


def _groups():
    groups, cur = [], []
    for w in WORDS:
        if cur and (len(cur) >= 4 or sum(len(x["d"]) + 1 for x in cur) + len(w["d"]) > 21
                    or w["os"] - cur[-1]["oe"] > 0.3 or cur[-1]["p"]):
            groups.append(cur)
            cur = []
        cur.append(w)
    groups.append(cur)
    out = []
    for i, g in enumerate(groups):
        nxt = groups[i + 1][0]["os"] if i + 1 < len(groups) else TOTAL
        out.append(dict(words=g, s=g[0]["os"] - 0.04, e=min(nxt - 0.03, g[-1]["oe"] + 0.6)))
    return out


GROUPS = _groups()


def cap_style(t):
    """(ink colour, accent colour, accent outline, plain font)"""
    s = section(t)
    if s in ("flip", "no", "product"):
        return INK, WHITE, PINK_D, "serif"
    if s == "cine":
        return WHITE, "#F3D9A4", "#1A1410", "serifi"
    return INK, PINK, PINK_D, "serif"


def _layout(g, size_p, size_a, maxw=900):
    items = [(w, w["i"] in ACC) for w in g["words"]]
    sp = 0.26 * size_p

    def width(it):
        return sum(word_w(w["d"], size_a if a else size_p, a) for w, a in it) + sp * (len(it) - 1)

    lines = [items]
    if (width(items) > maxw * 0.82 or len(items) >= 4) and len(items) > 1:
        best = min(range(1, len(items)), key=lambda k: max(width(items[:k]), width(items[k:])))
        lines = [items[:best], items[best:]]
    scale = min(1.0, maxw / max(width(l) for l in lines))
    return lines, scale, sp


def draw_captions(c, t, cam):
    if in_any(t, CAP_OFF):
        return
    g = next((g for g in GROUPS if g["s"] <= t < g["e"]), None)
    if g is None:
        return
    ink, acc_c, acc_o, plain = cap_style(t)
    punchy = PUNCHY.s - 0.05 <= t < PUNCHY.e + 0.4
    size_p, size_a = (124, 156) if punchy else (112, 138)
    lines, scale, sp = _layout(g, size_p, size_a)
    size_p, size_a, sp = size_p * scale, size_a * scale, sp * scale
    base = min(598, head_top_screen(cam) - 50)
    if section(t) in ("fifty", "reveal"):
        base = 560
    lh = size_a * 1.02
    y0 = base - lh * (len(lines) - 1)
    ko = e_in(clamp((t - (g["e"] - 0.1)) / 0.1))
    for li, line in enumerate(lines):
        lw = sum(word_w(w["d"], size_a if a else size_p, a) for w, a in line) + sp * (len(line) - 1)
        stagger = 0 if len(lines) == 1 else (-34 if li == 0 else 34)
        x = W / 2 - lw / 2 + stagger
        y = y0 + li * lh - ko * 24
        for w, a in line:
            sz = size_a if a else size_p
            ww = word_w(w["d"], sz, a)
            k = t - w["os"] + 0.03
            if k < 0:
                x += ww + sp
                continue
            sp_k = spring(k, w=24 if punchy else 20, z=0.38 if punchy else 0.5)
            al = clamp(k / 0.05) * (1 - ko)
            sc = (0.25 if punchy else 0.55) + (0.75 if punchy else 0.45) * sp_k
            c.save()
            c.translate(x + ww / 2, y - sz * 0.3 + (1 - sp_k) * 26)
            c.rotate((hrand(w["i"], 3) - 0.5) * (9 if punchy else 3))
            c.scale(sc, sc)
            c.translate(-ww / 2, sz * 0.3)
            if section(t) == "cine":
                c.drawString(w["d"], 0, 0, font("serifi", sz), fill("#000000", 0.45 * al, blur=10))
                c.drawString(w["d"], 0, 0, font("serifi", sz), fill(acc_c if a else ink, al))
            elif a:
                pink_word(c, w["d"], 0, 0, sz, al, color=YEL if punchy else acc_c, outline=acc_o)
            else:
                ink_word(c, w["d"], 0, 0, sz, al, color=ink, name=plain)
            c.restore()
            if w["k"] == "edit" and DONTEDIT.s <= w["os"] < DONTEDIT.e:          # "you don't edit" -> struck out
                strike(c, x - 8, x + ww + 8, y - sz * 0.32, prog(t, w["oe"], 0.25), RED, 13, seed=4)
            x += ww + sp


# ================================================================== graphics: shared bits
def star(c, x, y, r, color, n=5, inner=0.45, rot=0.0):
    path = skia.Path()
    for i in range(2 * n):
        rr = r if i % 2 == 0 else r * inner
        a = rot + math.pi * i / n - math.pi / 2
        (path.moveTo if i == 0 else path.lineTo)(x + rr * math.cos(a), y + rr * math.sin(a))
    path.close()
    c.drawPath(path, fill(color))


def note(c, x, y, s, color=INK):
    c.drawOval(skia.Rect(x - s * 0.5, y - s * 0.32, x + s * 0.5, y + s * 0.32), fill(color))
    c.drawRect(skia.Rect(x + s * 0.36, y - s * 1.6, x + s * 0.5, y), fill(color))
    path = skia.Path()
    path.moveTo(x + s * 0.43, y - s * 1.6)
    path.quadTo(x + s * 1.0, y - s * 1.3, x + s * 0.95, y - s * 0.8)
    c.drawPath(path, stroke(color, s * 0.14))


def scissors(c, x, y, s, open_k, rot=0.0, color=RED):
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    ang = 10 + 18 * open_k
    for sgn in (-1, 1):
        c.save()
        c.rotate(sgn * ang)
        c.drawRRect(rrect(0, -s * 0.06, s * 1.0, s * 0.12, s * 0.05), fill("#9AA3AD"))
        c.drawCircle(-s * 0.32, sgn * s * 0.12, s * 0.2, stroke(color, s * 0.1))
        c.restore()
    c.drawCircle(0, 0, s * 0.05, fill(INK))
    c.restore()


def clock(c, x, y, r, hours):
    c.drawCircle(x, y, r, fill(WHITE))
    c.drawCircle(x, y, r, stroke(INK, r * 0.08))
    for i in range(12):
        a = i * math.pi / 6
        c.drawLine(x + r * 0.78 * math.sin(a), y - r * 0.78 * math.cos(a), x + r * 0.9 * math.sin(a),
                   y - r * 0.9 * math.cos(a), stroke(INK, r * 0.05))
    ah, am = hours / 12 * 2 * math.pi, (hours % 1) * 2 * math.pi
    c.drawLine(x, y, x + r * 0.45 * math.sin(ah), y - r * 0.45 * math.cos(ah), stroke(INK, r * 0.09))
    c.drawLine(x, y, x + r * 0.7 * math.sin(am), y - r * 0.7 * math.cos(am), stroke(RED, r * 0.06))
    c.drawCircle(x, y, r * 0.07, fill(INK))


def phone_shape(c, cx, cy, w, h, body=INK):
    c.drawRRect(rrect(cx - w / 2, cy - h / 2, w, h, w * 0.13), fill(body))


def eq_bars(c, x0, x1, ybase, hmax, t, t0, energy, n=14, color=PINK):
    bw = (x1 - x0) / n
    for i in range(n):
        ph = math.sin(t * (6 + i * 0.7) + i * 1.7) * 0.5 + 0.5
        hgt = hmax * energy * (0.25 + 0.75 * ph) * (0.5 + 0.5 * math.sin(i * 0.9 + 1) ** 2)
        k = clamp((t - t0 - i * 0.02) / 0.2)
        hgt *= k
        c.drawRRect(rrect(x0 + i * bw + bw * 0.15, ybase - hgt, bw * 0.7, max(hgt, 1), bw * 0.2),
                    fill(color if i % 3 else YEL))


def confetti(c, t, t0, n=46, seed=3):
    if t < t0 or t > t0 + 1.6:
        return
    k = t - t0
    for i in range(n):
        ang = hrand(seed, i, 1) * 2 * math.pi
        sp = 600 + 1300 * hrand(seed, i, 2)
        x = W / 2 + math.cos(ang) * sp * k * (1 - k * 0.35)
        y = 900 + math.sin(ang) * sp * k * (1 - k * 0.35) + 900 * k * k
        a = clamp(1.6 - k)
        col = [PINK, YEL, RED, WHITE, "#7FB6D9"][i % 5]
        c.save()
        c.translate(x, y)
        c.rotate(k * 400 * (hrand(seed, i, 3) - 0.5))
        if i % 3 == 0:
            star(c, 0, 0, 22, col)
        elif i % 3 == 1:
            c.drawRect(skia.Rect(-14, -8, 14, 8), fill(col, a))
        else:
            c.drawCircle(0, 0, 10, fill(col, a))
        c.restore()


# ================================================================== section graphics (front layer)
def g_hook(c, t):
    label_sticker(c, "NEW", 205, 1010, 56, t, HOOK.w(3) + 0.05, rot=-9, bg=YEL, name="cond", t_out=YEARS.s - 0.2)
    if t >= NOTICED.w(4):          # "noticed": a pair of googly eyes peeks in on the right
        c.save()
        a = slap(c, t, NOTICED.w(4), 875, 980, 6, 1.0, YEARS.s - 0.2)
        with Sticker(c, (-95, -60, 95, 60), a=a):
            for sx in (-46, 46):
                c.drawCircle(sx, 0, 44, fill(WHITE))
                c.drawCircle(sx, 0, 44, stroke(INK, 5))
                lx = sx + 14 * math.sin(t * 5)
                c.drawCircle(lx, 6, 19, fill(INK))
                c.drawCircle(lx + 6, 0, 6, fill(WHITE))
        c.restore()


def g_years(c, t):
    # tear-off calendar: the year rolls 2009 -> 2025 while "for years" is said
    if t < YEARS.s:
        return
    c.save()
    a = slap(c, t, YEARS.s, 220, 990, -7, 1.0, SIT.s - 0.15)
    yr = int(lerp(2009, 2025, e_io(prog(t, YEARS.s, 1.2))))
    with Sticker(c, (-120, -125, 120, 125), a=a):
        c.drawRRect(rrect(-115, -120, 230, 240, 16), fill(WHITE))
        c.drawRRect(rrect(-115, -120, 230, 70, 16), fill(RED))
        c.drawRect(skia.Rect(-115, -70, 115, -50), fill(RED))
        for xx in (-60, 60):
            c.drawCircle(xx, -120, 12, fill(INK))
        type_text(c, "YEAR", 0, -70, 34, color=WHITE, anchor="c")
        c.drawString(str(yr), -measure(str(yr), "serif", 88) / 2, 60, font("serif", 88), fill(INK))
    c.restore()


def timeline_card(c, t, a=1.0):
    """the old way: a cluttered NLE timeline as a paper sticker over his torso."""
    x0, y0, w, h = 100, 1250, 860, 300
    with Sticker(c, (x0, y0, x0 + w, y0 + h), a=a):
        c.drawRRect(rrect(x0, y0, w, h, 18), fill("#2B2B30"))
        c.drawRRect(rrect(x0, y0, w, 46, 18), fill("#3A3A42"))
        type_text(c, "TIMELINE  00:00:47:12", x0 + 24, y0 + 32, 24, color="#C9C9D1")
        for i in range(40):
            xx = x0 + 20 + i * 21
            c.drawLine(xx, y0 + 52, xx, y0 + (62 if i % 5 else 70), stroke("#77777F", 2))
        rows = [("V2", "#E98AAE"), ("V1", "#7FB6D9"), ("A1", "#9BD19B"), ("A2", "#F3C969")]
        for r, (nm, colr) in enumerate(rows):
            yy = y0 + 84 + r * 52
            type_text(c, nm, x0 + 16, yy + 30, 22, color="#9A9AA3")
            xs = 70
            for j in range(9):
                cw = 40 + 70 * hrand(r, j)
                drag = 0
                if r == 1 and j == 3 and t >= DRAG.s:
                    drag = 150 * e_io(prog(t, DRAG.s, 0.6)) - 150
                c.drawRRect(rrect(x0 + xs + drag, yy, cw, 40, 6), fill(colr))
                c.drawRRect(rrect(x0 + xs + drag, yy, cw, 40, 6), stroke("#00000055", 2))
                xs += cw + 6
                if xs > w - 60:
                    break
        # keyframe diamonds pop in on "set keyframes"
        if t >= KEYS.s:
            for j in range(11):
                tk = KEYS.s + j * 0.06
                if t < tk:
                    continue
                k = spring(t - tk, w=26, z=0.45)
                xx, yy = x0 + 110 + j * 66, y0 + 104 + (j % 2) * 52
                c.save()
                c.translate(xx, yy)
                c.rotate(45)
                c.scale(k, k)
                c.drawRect(skia.Rect(-11, -11, 11, 11), fill(YEL))
                c.drawRect(skia.Rect(-11, -11, 11, 11), stroke(INK, 3))
                c.restore()
        ph = x0 + 70 + ((t * 120) % (w - 100))
        c.drawLine(ph, y0 + 50, ph, y0 + h - 10, stroke(RED, 4))
    if DRAG.s <= t < DRAG.e + 0.5:          # the cursor dragging a clip
        k = e_io(prog(t, DRAG.s, 0.6))
        cx, cy = x0 + 70 + 3 * 115 - 150 + 150 * k + 60, y0 + 84 + 52 + 26
        path = skia.Path()
        path.moveTo(cx, cy)
        path.lineTo(cx, cy + 46)
        path.lineTo(cx + 12, cy + 35)
        path.lineTo(cx + 24, cy + 56)
        path.lineTo(cx + 31, cy + 52)
        path.lineTo(cx + 20, cy + 32)
        path.lineTo(cx + 35, cy + 32)
        path.close()
        c.drawPath(path, fill(WHITE))
        c.drawPath(path, stroke(INK, 3))


def g_old(c, t):
    a = clamp((t - SIT.s) / 0.12) * (1 - clamp((t - (SEC["old"][1] - 0.12)) / 0.12))
    if t >= SIT.s:
        c.save()
        k = pop_k(t, SIT.s)
        c.translate(540, 1400)
        c.scale(0.4 + 0.6 * k, 0.4 + 0.6 * k)
        c.translate(-540, -1400)
        timeline_card(c, t, a)
        c.restore()
    if t >= HOURS.w(2):                     # "6 hours": clock spinning + hour counter
        c.save()
        aa = slap(c, t, HOURS.w(2), 215, 1010, -6, 1.0, SEC["old"][1] - 0.15)
        hrs = 6 * e_io(prog(t, HOURS.w(2), 0.9))
        with Sticker(c, (-110, -110, 110, 150), a=aa):
            clock(c, 0, 0, 100, hrs)
            c.drawRRect(rrect(-80, 112, 160, 50, 10), fill(YEL))
            type_text(c, f"{hrs:0.1f} HRS", 0, 148, 32, anchor="c")
        c.restore()
    if t >= REEL60.w(3):                    # "60-second reel": a tiny reel with its 0:60 timer
        c.save()
        aa = slap(c, t, REEL60.w(3), 870, 1000, 7, 1.0, SEC["old"][1] - 0.15)
        with Sticker(c, (-70, -115, 70, 115), a=aa):
            phone_shape(c, 0, 0, 130, 220)
            c.drawRRect(rrect(-56, -98, 112, 196, 12), fill(PINK))
            type_text(c, "0:60", 0, 14, 38, color=WHITE, anchor="c")
        c.restore()


def clapper(c, t, t0, x, y, s=1.0):
    c.save()
    a = slap(c, t, t0, x, y, -8, s, SEC["flip"][1] - 0.15)
    close = e_in(clamp((t - t0 - 0.15) / 0.12))
    with Sticker(c, (-130, -150, 130, 120), a=a):
        c.drawRRect(rrect(-120, -40, 240, 160, 10), fill(INK))
        type_text(c, "SCENE 01", -100, 20, 30, color=WHITE)
        type_text(c, "TAKE  1", -100, 70, 30, color=WHITE)
        type_text(c, "DIR: YOU", -100, 108, 26, color=PINK)
        c.save()
        c.translate(-120, -44)
        c.rotate(-28 * (1 - close))
        c.drawRect(skia.Rect(0, -44, 240, 0), fill(WHITE))
        for i in range(6):
            p = skia.Path()
            p.moveTo(i * 44, -44)
            p.lineTo(i * 44 + 24, -44)
            p.lineTo(i * 44 + 4, 0)
            p.lineTo(i * 44 - 20, 0)
            p.close()
            c.drawPath(p, fill(INK))
        c.restore()
    c.restore()


def g_flip(c, t):
    if t >= DIRECT.w(1):
        clapper(c, t, DIRECT.w(1) - 0.1, 800, 1210)
    if FLIPS.e <= t:                         # a little "↻ flipped" note in the margin
        c.save()
        a = slap(c, t, FLIPS.e - 0.05, 215, 1000, -5, 1.0, SEC["flip"][1] - 0.15)
        with Sticker(c, (-110, -60, 110, 60), a=a):
            c.drawRRect(rrect(-105, -55, 210, 110, 14), fill(YEL))
            hand(c, "flipped!", 0, 18, 64, rot=-3)
        c.restore()


BRIEF_ITEMS = [("cut the pauses", CUTP), ("punchy captions", PUNCHY), ("title behind me", TITLE),
               ("cinematic look", CINE), ("music that builds", MUSIC)]


def brief_card(c, t):
    """typed brief on an index card; each instruction types in as it is said and gets ticked as it happens."""
    t_in, t_out = BRIEF.w(4) - 0.05, CINE.s - 0.04
    if not t_in <= t < t_out + 0.3:
        return
    x0, y0, w, h = 150, 1180, 780, 390
    a = 1.0
    c.save()
    k = pop_k(t, t_in)
    if t > t_out:
        ko = e_in(clamp((t - t_out) / 0.25))
        c.translate(0, 600 * ko)
        c.rotate(8 * ko)
    c.translate(540, 1375)
    c.scale(0.5 + 0.5 * k, 0.5 + 0.5 * k)
    c.rotate(-2)
    c.translate(-540, -1375)
    with Sticker(c, (x0, y0, x0 + w, y0 + h), a=a):
        c.drawRRect(rrect(x0, y0, w, h, 8), fill("#FFFDF6"))
        c.drawRect(skia.Rect(x0, y0 + 72, x0 + w, y0 + 75), fill(MARGIN_RED := "#E0817F"))
        for i in range(5):
            c.drawRect(skia.Rect(x0, y0 + 128 + i * 56, x0 + w, y0 + 130 + i * 56), fill(RULE, 0.6))
        type_text(c, "BRIEF  for the editor", x0 + 30, y0 + 52, 36, color=INK)
        star(c, x0 + w - 50, y0 + 38, 24, PINK)
        for i, (txt, ph) in enumerate(BRIEF_ITEMS[:3] + BRIEF_ITEMS[3:]):
            ts = ph.s - 0.02
            if t < ts:
                continue
            n = int(clamp((t - ts) / max(0.35, ph.e - ph.s)) * len(txt) + 0.999)
            yy = y0 + 124 + i * 56
            c.drawRect(skia.Rect(x0 + 34, yy - 32, x0 + 66, yy), stroke(INK, 3))
            type_text(c, txt[:n], x0 + 86, yy - 4, 36, color=INK)
            done = ph.e + 0.12
            if t >= done:
                check_mark(c, x0 + 52, yy - 18, 40, prog(t, done, 0.2), PINK, 9)
    c.restore()
    if BRIEF.w(6) <= t < t_out:        # "top editor" label
        label_sticker(c, "TOP EDITOR", 845, 1000, 34, t, BRIEF.w(6), rot=6, bg=PINK, fg=WHITE, t_out=CUTP.s + 0.6)


def g_brief(c, t):
    if CUTP.s - 0.05 <= t < CUTP.e + 0.35:      # a dashed cut line and scissors snipping across
        k = prog(t, CUTP.w(0), 0.5)
        y = 1150
        x = lerp(-60, W + 60, e_io(k))
        p = stroke(INK, 5)
        p.setPathEffect(skia.DashPathEffect.Make([22, 14], 0))
        c.drawLine(0, y, W, y, p)
        c.save()
        with Sticker(c, (x - 90, y - 90, x + 90, y + 90), border=7):
            scissors(c, x, y, 90, abs(math.sin(t * 22)), rot=0)
        c.restore()
    if TITLE.s - 0.02 <= t < TITLE.e + 0.25:   # hand note pointing at the title behind him
        k = prog(t, TITLE.w(3), 0.35)
        hand(c, "behind me!", 860, 1130, 66, clamp(k * 3), rot=-6)
        arrow(c, 860, 1080, 790, 900, k, INK, 6, bend=0.3)
    brief_card(c, t)


def title_behind(c, t):
    """'put the title behind me': a huge TITLE set behind him (drawn before the person)."""
    if not TITLE.s - 0.02 <= t < TITLE.e + 0.25:
        return
    k = t - TITLE.w(2) + 0.05
    if k < 0:
        return
    s = 270
    word = "TITLE"
    sp = spring(k, w=16, z=0.45)
    a = clamp(k / 0.06) * (1 - clamp((t - TITLE.e - 0.1) / 0.15))
    c.save()
    c.translate(W / 2 - 10, 770)
    c.scale(0.6 + 0.4 * sp, 0.6 + 0.4 * sp)
    w = measure(word, "pink", s)
    pink_word(c, word, -w / 2, 0, s, a, color=PINK, outline=PINK_D, depth=0.035)
    c.restore()
    ww = measure("the", "serif", 96)
    ink_word(c, "the", W / 2 - 300 - ww / 2, 515, 96, a * clamp(k / 0.1))


def g_cine(c, t):
    k = e_out(prog(t, SEC["cine"][0], 0.3)) * (1 - e_in(prog(t, SEC["cine"][1] - 0.2, 0.2)))
    bh = 230 * k
    c.drawRect(skia.Rect(0, 0, W, bh), fill("#050505"))
    c.drawRect(skia.Rect(0, H - bh, W, H), fill("#050505"))
    if k > 0.5:
        a = clamp((k - 0.5) * 3)
        type_text(c, "SC. 04", 70, H - bh + 70, 28, a, color="#BFB7A6", name="typer")
        type_text(c, "2.39 : 1", W - 70, H - bh + 70, 28, a, color="#BFB7A6", name="typer", anchor="r")


def g_music(c, t):
    if t < MUSIC.s:
        return
    energy = lerp(0.35, 1.0, prog(t, MUSIC.s, DROP - MUSIC.s))
    c.save()
    a = clamp((t - MUSIC.s) / 0.15)
    with Sticker(c, (130, 1260, 950, 1560), a=a):
        c.drawRRect(rrect(130, 1290, 820, 270, 22), fill(WHITE))
        eq_bars(c, 160, 920, 1530, 210, t, MUSIC.s, energy)
    c.restore()
    for i, (x, y0, t0) in enumerate([(200, 1150, MUSIC.w(1)), (860, 1100, MUSIC.w(3)), (250, 900, BUILDS.w(2)),
                                     (840, 880, BUILDS.w(3))]):
        if t < t0:
            continue
        k = t - t0
        c.save()
        a = slap(c, t, t0, x + 20 * math.sin(k * 3 + i), y0 - 40 * k, (hrand(i, 9) - 0.5) * 30, 1.0)
        with Sticker(c, (-50, -100, 60, 40), border=8, a=a):
            note(c, 0, 0, 48, PINK if i % 2 else INK)
        c.restore()


def g_every(c, t):
    spots = [(215, 930, -8), (845, 900, 7), (225, 1230, 6), (805, 1215, -6)]
    t_out = SEC["every"][1] - 0.15
    for i, (ph, (x, y, r)) in enumerate(zip(EVERY, spots)):
        t0 = ph.w(1) - 0.03
        if t < t0:
            continue
        c.save()
        a = slap(c, t, t0, x, y, r, 1.0, t_out if i else min(t_out, CODE.s + 0.1))
        with Sticker(c, (-105, -105, 105, 105), a=a):
            if i == 0:
                c.drawCircle(0, 0, 100, fill(YEL))
                scissors(c, 4, 0, 78, 0.5, rot=-30)
            elif i == 1:
                c.drawRRect(rrect(-100, -80, 200, 160, 18), fill(WHITE))
                ink_word(c, "A", -70, 45, 120)
                pink_word(c, "a", 5, 45, 120, 1.0)
            elif i == 2:
                c.drawCircle(0, 0, 100, fill(PINK))
                star(c, -8, 6, 62, WHITE, n=4, inner=0.3)
                star(c, 50, -44, 26, YEL, n=4, inner=0.3)
            else:
                c.drawCircle(0, 0, 100, fill("#7FB6D9"))
                c.drawRect(skia.Rect(-60, -24, -28, 24), fill(INK))
                p = skia.Path()
                p.moveTo(-30, -24)
                p.lineTo(4, -54)
                p.lineTo(4, 54)
                p.lineTo(-30, 24)
                p.close()
                c.drawPath(p, fill(INK))
                for j in range(3):
                    kk = (t * 2 + j / 3) % 1
                    c.drawArc(skia.Rect(-10 - 30 * j, -40 - 20 * j, 40 + 30 * j, 40 + 20 * j), -50, 100, False,
                              stroke(INK, 7, 1 - kk * 0.6))
        c.restore()
    code_card(c, t)


CODE_LINES = [("edit", "(", "take.mp4", ")"), ("cut", "(", "pauses", ")"), ("captions", ".", "punch", "()"),
              ("title", ".", "behind", "(me)"), ("music", ".", "build", "()")]


def code_card(c, t):
    """'made in code' -> typed code, then 'right on your laptop' wraps it in a laptop."""
    t_in = CODE.s - 0.05
    if t < t_in:
        return
    t_out = SEC["every"][1] - 0.15
    lap = e_out(prog(t, LAPTOP.w(3) - 0.1, 0.35))
    c.save()
    k = pop_k(t, t_in)
    ko = e_in(clamp((t - t_out) / 0.2))
    c.translate(540, 1390 + 500 * ko)
    c.scale(0.5 + 0.5 * k, 0.5 + 0.5 * k)
    c.translate(-540, -1390)
    x0, y0, w, h = 190, 1230, 700, 320
    with Sticker(c, (x0 - 90 * lap, y0 - 20, x0 + w + 90 * lap, y0 + h + 70 * lap)):
        if lap > 0:
            c.drawRRect(rrect(x0 - 26, y0 - 26, w + 52, h + 52, 26), fill("#C9CCD3"))
            base = skia.Path()
            base.moveTo(x0 - 26 - 70 * lap, y0 + h + 26 + 46 * lap)
            base.lineTo(x0 + w + 26 + 70 * lap, y0 + h + 26 + 46 * lap)
            base.lineTo(x0 + w + 26, y0 + h + 26)
            base.lineTo(x0 - 26, y0 + h + 26)
            base.close()
            c.drawPath(base, fill("#AEB2BA"))
        c.drawRRect(rrect(x0, y0, w, h, 14), fill("#1E1D24"))
        for i, d in enumerate(["#FF6B6B", "#F5B414", "#5FD17A"]):
            c.drawCircle(x0 + 30 + i * 30, y0 + 28, 9, fill(d))
        type_text(c, "vibe.py", x0 + w - 24, y0 + 36, 24, color="#8E8C9A", name="typer", anchor="r")
        for i, (fn, dot, arg, end) in enumerate(CODE_LINES):
            ts = CODE.s + i * 0.24
            if t < ts:
                continue
            full = fn + dot + arg + end
            n = int(clamp((t - ts) / 0.22) * len(full) + 0.999)
            x, y = x0 + 30, y0 + 86 + i * 50
            parts = [(fn, PINK), (dot, "#E8E6F0"), (arg, YEL), (end, "#E8E6F0")]
            shown = 0
            for s, colr in parts:
                s2 = s[:max(0, n - shown)]
                shown += len(s)
                if s2:
                    x += type_text(c, s2, x, y, 34, color=colr)
            if n < len(full) or i == len(CODE_LINES) - 1:
                if (t * 3) % 1 < 0.6:
                    c.drawRect(skia.Rect(x + 3, y - 28, x + 20, y + 4), fill("#E8E6F0"))
    c.restore()


def polaroid(c, t, t0, x, y, rot, label, art, t_out):
    if t < t0:
        return
    c.save()
    a = slap(c, t, t0, x, y, rot, 1.0, t_out)
    w, h = 240, 280
    with Sticker(c, (-w / 2, -h / 2, w / 2, h / 2), border=4, shadow=(6, 10, 8, 0.3), a=a):
        c.drawRect(skia.Rect(-w / 2, -h / 2, w / 2, h / 2), fill(WHITE))
        c.save()
        c.clipRect(skia.Rect(-w / 2 + 14, -h / 2 + 14, w / 2 - 14, h / 2 - 66))
        art(c, t - t0, -w / 2 + 14, -h / 2 + 14, w - 28, h - 80)
        c.restore()
        hand(c, label, 0, h / 2 - 20, 44)
    tape(c, 0, -h / 2, 110, 34, rot=-4 + 8 * hrand(label))
    c.restore()


def art_motion(c, k, x, y, w, h):
    c.drawRect(skia.Rect(x, y, x + w, y + h), fill("#2C2A4A"))
    for i in range(3):
        a = k * 2.4 + i * 2.1
        cx, cy = x + w / 2 + 60 * math.cos(a), y + h / 2 + 40 * math.sin(a * 1.3)
        [c.drawCircle(cx, cy, 26, fill(PINK)), c.drawRect(skia.Rect(cx - 22, cy - 22, cx + 22, cy + 22), fill(YEL)),
         c.drawCircle(cx, cy, 18, fill("#7FB6D9"))][i]


def art_product(c, k, x, y, w, h):
    c.drawRect(skia.Rect(x, y, x + w, y + h), fill("#FBE3EA"))
    cx = x + w / 2
    c.drawRRect(rrect(cx - 34, y + 50, 68, 130, 16), fill(PINK))
    c.drawRect(skia.Rect(cx - 16, y + 28, cx + 16, y + 52), fill(INK))
    c.drawRRect(rrect(cx - 26, y + 92, 52, 40, 6), fill(WHITE))
    star(c, cx + 70, y + 50, 16 + 4 * math.sin(k * 8), YEL, n=4, inner=0.3)
    c.drawRRect(rrect(x + 16, y + h - 40, 70, 26, 13), fill(INK))
    type_text(c, "-30%", x + 51, y + h - 20, 18, color=WHITE, anchor="c")


def art_clay(c, k, x, y, w, h):
    c.drawRect(skia.Rect(x, y, x + w, y + h), fill("#BFE3D0"))
    cx, cy = x + w / 2, y + h / 2 + 12
    sq = 1 + 0.08 * math.sin(k * 7)
    c.drawOval(skia.Rect(cx - 60 * sq, cy - 52 / sq, cx + 60 * sq, cy + 52 / sq), fill("#F28A5B"))
    for sx in (-20, 20):
        c.drawCircle(cx + sx, cy - 10, 11, fill(WHITE))
        c.drawCircle(cx + sx + 2, cy - 8, 5, fill(INK))
    c.drawArc(skia.Rect(cx - 16, cy + 2, cx + 16, cy + 24), 20, 140, False, stroke(INK, 4))


def art_vfx(c, k, x, y, w, h):
    c.drawRect(skia.Rect(x, y, x + w, y + h), fill("#1D1B22"))
    cx, cy = x + w / 2, y + h / 2
    for i in range(10):
        a = i * math.pi / 5 + k
        r = 30 + 60 * ((k * 1.6 + i * 0.13) % 1)
        c.drawLine(cx, cy, cx + r * math.cos(a), cy + r * math.sin(a), stroke(YEL if i % 2 else "#FF7A3D", 7))
    c.drawCircle(cx, cy, 24, fill(WHITE))


def art_pod(c, k, x, y, w, h):
    c.drawRect(skia.Rect(x, y, x + w, y + h), fill("#F6E7B8"))
    cx = x + w / 2
    c.drawRRect(rrect(cx - 24, y + 28, 48, 80, 24), fill(INK))
    c.drawArc(skia.Rect(cx - 38, y + 60, cx + 38, y + 124), 0, 180, False, stroke(INK, 5))
    c.drawLine(cx, y + 124, cx, y + 140, stroke(INK, 5))
    for i in range(16):
        hh = 8 + 26 * abs(math.sin(k * 9 + i * 0.8))
        xx = x + 20 + i * (w - 40) / 16
        c.drawRRect(rrect(xx, y + h - 34 - hh / 2, 7, hh, 3), fill(PINK))


FORMAT_SPOTS = [(205, 880, -7), (850, 860, 6), (200, 1260, 5), (800, 1265, -5), (540, 1440, 3)]
FORMAT_ART = [("motion gfx", art_motion), ("product ads", art_product), ("claymation", art_clay), ("VFX", art_vfx),
              ("podcasts", art_pod)]


def g_formats(c, t):
    if NOTJUST.w(4) - 0.1 <= t < SAMESYS.s + 0.3:      # "not just reels": a REELS label gets an arrow out
        label_sticker(c, "REELS", 860, 1000, 46, t, NOTJUST.w(4) - 0.08, rot=6, bg=PINK, fg=WHITE, name="cond",
                      t_out=SAMESYS.s + 0.05)
    t_out = SEC["formats"][1] - 0.12
    for ph, (x, y, r), (lab, art) in zip(FORMATS, FORMAT_SPOTS, FORMAT_ART):
        polaroid(c, t, ph.s - 0.04, x, y, r, lab, art, t_out)


# ---------------------------------------------------------------- fifty versions
TILE_BGS = ["lined", "pink", "yellow", "graph", "blush", "kraft"]


@lru_cache(None)
def tile_bg(kind, w, h):
    img = paper_img(kind)
    return img.resize(w, h, SAMP) if hasattr(img, "resize") else img


def g_fifty(c, t, src):
    a0, a1 = SEC["fifty"]
    cols, rows = 10, 5
    tw, th, gap = 88, 156, 8
    gx0 = (W - (cols * tw + (cols - 1) * gap)) / 2
    gy0 = 660
    kout = e_in(clamp((t - (a1 - 0.25)) / 0.25))
    # one small person cut-out reused on six paper variants
    pw, phh = tw, th
    rgb = cv2.resize(src.rgb, (pw, phh), interpolation=cv2.INTER_AREA)
    al = cv2.resize(src.small, (pw, phh), interpolation=cv2.INTER_AREA)
    pimg = skia.Image.fromarray(np.dstack([rgb, al]), colorType=skia.kRGBA_8888_ColorType)
    win = 37
    n_shown = int(clamp((t - a0 - 0.15) / 1.3) * 50 + 0.999)
    for i in range(50):
        r, cc = divmod(i, cols)
        x, y = gx0 + cc * (tw + gap), gy0 + r * (th + gap)
        if i >= n_shown:
            continue
        ti = a0 + 0.15 + i * 1.3 / 50
        k = spring(t - ti, w=24, z=0.5)
        c.save()
        c.translate(x + tw / 2, y + th / 2 + 400 * kout * (1 + (i % 7) * 0.1))
        s = 0.3 + 0.7 * k
        c.scale(s, s)
        dim = TEST.w(3) <= t and i != win
        rr = rrect(-tw / 2, -th / 2, tw, th, 8)
        c.drawRRect(rr.makeOffset(3, 5), fill("#000000", 0.22, blur=4))
        c.save()
        c.clipRRect(rr, True)
        c.drawImageRect(paper_img(TILE_BGS[i % 6]), skia.Rect(-tw / 2, -th / 2, tw / 2, th / 2), SAMP)
        c.drawImageRect(pimg, skia.Rect(-tw / 2, -th / 2, tw / 2, th / 2), SAMP)
        c.drawRect(skia.Rect(-tw / 2 + 8, -th / 2 + 22, tw / 2 - 8, -th / 2 + 34),
                   fill([PINK, INK, YEL, RED, WHITE][i % 5]))
        if dim:
            c.drawRect(skia.Rect(-tw / 2, -th / 2, tw / 2, th / 2), fill(PAPER, 0.62))
        c.restore()
        c.drawRRect(rr, stroke(WHITE, 4))
        c.restore()
    # counter
    if t >= a0:
        label_sticker(c, f"VERSION {n_shown:02d} / 50", 540, 1560 + 400 * kout, 38, t, a0 + 0.1, rot=-2, bg=WHITE)
    if t >= TEST.w(3):
        r, cc = divmod(win, cols)
        x, y = gx0 + cc * (tw + gap) + tw / 2, gy0 + r * (th + gap) + th / 2
        scribble_ellipse(c, x, y + 400 * kout, 80, 112, prog(t, TEST.w(3), 0.4), PINK, 10)
        stamp(c, "WINNER", x - 150, y - 150 + 400 * kout, 54, prog(t, TEST.w(4), 0.5), RED, rot=-10)


def g_need(c, t):
    if t >= NEED.w(5) - 0.05:            # the big question mark
        c.save()
        a = slap(c, t, NEED.w(5) - 0.05, 895, 790, 10, 1.0, SEC["need"][1] - 0.15)
        with Sticker(c, (-90, -130, 90, 130), a=a):
            s = 260
            ww = measure("?", "pink", s)
            pink_word(c, "?", -ww / 2, 90, s, 1.0)
        c.restore()
    if t < FOOTAGE.s - 0.1:
        return
    # yellow sticky note with the handwritten checklist
    c.save()
    k = pop_k(t, FOOTAGE.s - 0.1)
    ko = e_in(clamp((t - (SEC["need"][1] - 0.2)) / 0.2))
    c.translate(540, 1390 + 600 * ko)
    c.rotate(-2)
    c.scale(0.5 + 0.5 * k, 0.5 + 0.5 * k)
    c.translate(-540, -1390)
    x0, y0, w, h = 170, 1190, 740, 380
    with Sticker(c, (x0, y0, x0 + w, y0 + h), border=6):
        c.drawRect(skia.Rect(x0, y0, x0 + w, y0 + h), fill("#FFE27A"))
        c.drawRect(skia.Rect(x0, y0, x0 + w, y0 + 40), fill("#F6D45A"))
    tape(c, 540, y0 + 4, 160, 40, rot=2)
    items = [("your footage", FOOTAGE), ("your laptop", YLAPTOP), ("Vibe Editing System", VES)]
    for i, (txt, ph) in enumerate(items):
        if t < ph.s - 0.05:
            continue
        yy = y0 + 130 + i * 92
        c.drawRect(skia.Rect(x0 + 50, yy - 44, x0 + 96, yy + 2), stroke(INK, 4))
        n = int(clamp((t - ph.s + 0.05) / 0.3) * len(txt) + 0.999)
        hand(c, txt[:n], x0 + 126, yy, 78 if i < 2 else 80, color=INK if i < 2 else "#C2185B", anchor="l")
        if t >= ph.e:
            check_mark(c, x0 + 74, yy - 22, 56, prog(t, ph.e, 0.2), RED if i < 2 else PINK, 10)
        if i == 2 and t >= ph.e + 0.1:
            marker(c, [(x0 + 120, yy + 18), (x0 + 700, yy + 12)], prog(t, ph.e + 0.1, 0.3), PINK, 7)
    c.restore()


SKILL_CARDS = ["talking head", "motion gfx", "product ads", "claymation", "VFX", "bulk ads"]


def product_box(c, t, t0, x, y, s=1.0, t_out=None):
    c.save()
    a = slap(c, t, t0, x, y, -4, s, t_out)
    w, h = 520, 250
    with Sticker(c, (-w / 2, -h / 2, w / 2, h / 2), a=a):
        c.drawRRect(rrect(-w / 2, -h / 2, w, h, 22), fill(INK))
        c.drawRRect(rrect(-w / 2 + 12, -h / 2 + 12, w - 24, h - 24, 14), stroke(PINK, 3))
        type_text(c, "THE", 0, -h / 2 + 62, 28, color=YEL, anchor="c")
        ww = measure("Vibe Editing", "pink", 72)
        pink_word(c, "Vibe Editing", -ww / 2, 22, 72, 1.0, color=PINK, outline="#000000")
        type_text(c, "S Y S T E M", 0, 68, 32, color=WHITE, anchor="c")
        hand(c, "by Ideabro Studio", 0, 108, 40, color=YEL)
    c.restore()


def g_product(c, t):
    t_out = SEC["product"][1] - 0.15
    product_box(c, t, SKILLS.s - 0.05, 540, 1250, t_out=t_out)
    # skill cards fan out of the box on "skills"
    for i, nm in enumerate(SKILL_CARDS):
        t0 = SKILLS.w(2) + i * 0.09
        if t < t0:
            continue
        x = 190 if i < 3 else 855                    # two columns beside him, clear of the face and the UI
        y = 860 + (i % 3) * 100
        label_sticker(c, nm, x, y, 32, t, t0, rot=(-5 if i < 3 else 5) + (i % 3 - 1) * 2, bg=[YEL, WHITE, PINK, WHITE, YEL, WHITE][i],
                      fg=INK if i != 2 else WHITE, t_out=t_out)
        if t >= SHOWS.w(7) + i * 0.1:          # "every one of them": each skill gets a tick
            check_mark(c, x + (95 if i < 3 else -95), y - 26, 34, prog(t, SHOWS.w(7) + i * 0.1, 0.18), RED, 7)
    if t >= COURSE.w(2):
        c.save()
        a = slap(c, t, COURSE.w(2), 540, 1500, 3, 1.0, t_out)
        with Sticker(c, (-230, -60, 230, 60), a=a):
            c.drawRRect(rrect(-225, -55, 450, 110, 55), fill(YEL))
            c.drawCircle(-170, 0, 36, fill(INK))
            p = skia.Path()
            p.moveTo(-182, -18)
            p.lineTo(-182, 18)
            p.lineTo(-152, 0)
            p.close()
            c.drawPath(p, fill(YEL))
            type_text(c, "+ FULL COURSE", 25, 14, 42, color=INK, anchor="c")
        c.restore()


NO_ITEMS = [("After Effects", NOAE), ("Premiere Pro", NOPR), ("keyframes", NOKF)]


def g_no(c, t, behind):
    """'No After Effects. No Premiere Pro. No keyframes.' as the caption itself: crossed out, stamped NO."""
    for i, (txt, ph) in enumerate(NO_ITEMS):
        if t < ph.s - 0.03:
            continue
        y = 330 + i * 118
        sz = 100
        w = measure(txt, "serif", sz)
        x = W / 2 - w / 2 + 70
        k = spring(t - ph.s + 0.03, w=20, z=0.5)
        if behind:
            c.save()
            c.translate(x + w / 2, y - 30)
            c.scale(0.5 + 0.5 * k, 0.5 + 0.5 * k)
            c.translate(-(x + w / 2), -(y - 30))
            ink_word(c, txt, x, y, sz, clamp((t - ph.s) / 0.05))
            c.restore()
            strike(c, x - 10, x + w + 10, y - 32, prog(t, ph.w(1) + 0.05, 0.22), RED, 14, seed=i)
        else:
            stamp(c, "NO", x - 95, y - 34, 64, prog(t, ph.s, 0.45), RED, rot=-12)


def g_end(c, t):
    a0 = END_A
    k = t - a0
    # big CTA
    s1, s2 = 120, 250
    w1 = measure("Comment", "serif", s1)
    sp = spring(max(0, k - 0.15), w=16, z=0.5)
    ink_word(c, "Comment", W / 2 - w1 / 2, 520, s1, clamp((k - 0.1) / 0.1))
    if k > 0.3:
        c.save()
        c.translate(W / 2, 760)
        sc = 0.4 + 0.6 * spring(k - 0.3, w=18, z=0.4)
        c.scale(sc, sc)
        c.rotate(-3)
        w2 = measure("VIBE", "pink", s2)
        pink_word(c, "VIBE", -w2 / 2, 0, s2, 1.0)
        c.restore()
    if k > 0.75:
        hand(c, "and I'll send you the details", W / 2, 880, 58, clamp((k - 0.75) / 0.2), rot=-2)
    # comment box typing VIBE
    if k > 0.9:
        c.save()
        a = slap(c, t, a0 + 0.9, 540, 1030, 0, 1.0)
        with Sticker(c, (-380, -60, 380, 60), border=8, a=a):
            c.drawRRect(rrect(-375, -55, 750, 110, 55), fill(WHITE))
            c.drawCircle(-315, 0, 32, fill(PINK))
            hand(c, "ib", -315, 14, 40, color=WHITE)
            n = int(clamp((k - 1.2) / 0.5) * 4 + 0.999) if k > 1.2 else 0
            txt = "VIBE"[:n]
            if n == 0:
                type_text(c, "Add a comment...", -255, 12, 34, color="#9A9A9A", name="typer")
            else:
                type_text(c, txt, -255, 14, 40, color=INK)
            sent = k > 1.9
            c.drawCircle(315, 0, 34, fill(PINK if sent else "#D9D9D9"))
            p = skia.Path()
            p.moveTo(298, -16)
            p.lineTo(334, 0)
            p.lineTo(298, 16)
            p.lineTo(304, 0)
            p.close()
            c.drawPath(p, fill(WHITE))
        c.restore()
    product_box(c, t, a0 + 0.5, 650, 1310, 0.85)
    if k > 1.95:
        for i in range(6):
            kk = k - 1.95 - i * 0.05
            if kk < 0:
                continue
            x = 855 + 30 * math.sin(i * 2.1) + kk * 40 * (i - 2.5)
            y = 1030 - kk * 380 - i * 14
            c.save()
            c.translate(x, y)
            c.scale(0.7, 0.7)
            heart(c, 0, 0, 34, [PINK, RED, YEL][i % 3], clamp(1.2 - kk))
            c.restore()


def heart(c, x, y, s, color, a=1.0):
    p = skia.Path()
    p.moveTo(x, y + s * 0.9)
    p.cubicTo(x - s * 1.6, y - s * 0.2, x - s * 0.7, y - s * 1.3, x, y - s * 0.45)
    p.cubicTo(x + s * 0.7, y - s * 1.3, x + s * 1.6, y - s * 0.2, x, y + s * 0.9)
    c.drawPath(p, fill(color, a))


# ================================================================== background plan
def bg_kind(t):
    s = section(t)
    return {"hook": "lined", "years": "graph", "old": "graph", "flip": "pink", "brief": "lined", "cine": None,
            "music": "lined", "every": "yellow", "formats": "graph", "fifty": "lined", "need": "lined",
            "product": "blush", "no": "pink", "reveal": "kraft", "end": "lined"}[s]


def draw_tear(c, k, src, cam):
    """the wall tears away bottom-to-top, revealing the notebook (k 0..1)."""
    yline = lerp(H + 60, -160, e_io(k))
    path = skia.Path()
    path.moveTo(0, H)
    n = 18
    for i in range(n + 1):
        x = W * i / n
        y = yline + 46 * math.sin(i * 1.7) + 30 * (hrand(7, i) - 0.5) + 0.12 * (x - W / 2)
        path.lineTo(x, y)
    path.lineTo(W, H)
    path.close()
    c.save()
    c.clipPath(path, skia.ClipOp.kDifference, True)
    c.save()
    apply_cam(c, cam)
    c.drawImage(src.plate(), 0, 0, SAMP)
    c.restore()
    c.restore()
    # torn paper edge: white fibre strip + shadow
    edge = skia.Path()
    for i in range(n + 1):
        x = W * i / n
        y = yline + 46 * math.sin(i * 1.7) + 30 * (hrand(7, i) - 0.5) + 0.12 * (x - W / 2)
        (edge.moveTo if i == 0 else edge.lineTo)(x, y)
    c.drawPath(edge, stroke("#000000", 26, 0.18, blur=10))
    c.drawPath(edge, stroke("#FBF8EE", 16))


def draw_person(c, src, cam, border_a=1.0, shadow=True):
    c.save()
    apply_cam(c, cam)
    if shadow and border_a > 0:
        c.save()
        c.translate(12, 16)
        c.drawImage(src.shadow(), 0, 0, SAMP, skia.Paint(Alphaf=border_a))
        c.restore()
    if border_a > 0:
        c.drawImage(src.border(), 0, 0, SAMP, skia.Paint(Alphaf=border_a))
    c.drawImage(src.person(), 0, 0, SAMP)
    c.restore()


# ---------------------------------------------------------------- the reveal: the edit inside a phone
PHONE = (540, 1130, 520, 925)          # cx, cy, w, h


def scene_full(c, t, src, cam, kind):
    """the normal composition (paper + captions + person), used inside the phone too."""
    paper(c, kind)
    draw_captions(c, t, cam)
    draw_person(c, src, cam)


def g_reveal(c, t, src):
    a0 = SEC["reveal"][0]
    k = e_io(prog(t, a0, 0.55))
    cx, cy, pw, ph = PHONE
    s = lerp(1.0, pw / W, k)
    ox, oy = lerp(W / 2, cx, k), lerp(H / 2, cy, k)
    raw_k = e_io(prog(t, RECORDED.w(2), 0.3)) * (1 - e_io(prog(t, REST.w(2), 0.35)))
    # phone body
    if k > 0:
        bw, bh = W * s + 34, H * s + 34
        c.save()
        c.translate(ox, oy)
        c.rotate(-2 * k)
        c.drawRRect(rrect(-bw / 2 + 14, -bh / 2 + 22, bw, bh, 60 * k), fill("#000000", 0.28 * k, blur=18))
        c.drawRRect(rrect(-bw / 2, -bh / 2, bw, bh, 60 * k), fill("#111114"))
        c.restore()
    c.save()
    c.translate(ox, oy)
    c.rotate(-2 * k)
    c.scale(s, s)
    c.translate(-W / 2, -H / 2)
    c.clipRRect(rrect(0, 0, W, H, 90 * k), True)
    cam0 = (1.0, 0.0, 0.0, 0.0)
    if raw_k < 1:
        paper(c, "lined")
        draw_person(c, src, cam0)
    if raw_k > 0:
        raw = Src(src_at(t), "raw").plate()
        c.save()
        c.clipRect(skia.Rect(0, H * (1 - raw_k), W, H))
        c.drawImage(raw, 0, 0, SAMP)
        c.restore()
        if raw_k > 0.6:
            c.drawCircle(110, 300, 22, fill(RED, 1.0 if (t * 2) % 1 < 0.6 else 0.25))
            type_text(c, "REC", 150, 314, 46, color=WHITE)
    c.restore()
    if k >= 1:
        # notch
        c.save()
        c.translate(ox, oy)
        c.rotate(-2)
        c.drawRRect(rrect(-70, -ph / 2 + 18, 140, 30, 15), fill("#111114"))
        c.restore()
        lbl = "RAW TAKE" if raw_k > 0.5 else "EDITED"
        bg = WHITE if raw_k > 0.5 else PINK
        label_sticker(c, lbl, 840, 760, 36, t, a0 + 0.55, rot=7, bg=bg, fg=INK if raw_k > 0.5 else WHITE)
    if t >= NOAPP.w(5) - 0.05:
        c.save()
        a = slap(c, t, NOAPP.w(5) - 0.05, 190, 1240, -8, 1.0, RECORDED.s + 0.4)
        with Sticker(c, (-125, -125, 125, 160), a=a):
            c.drawRRect(rrect(-100, -100, 200, 200, 44), fill("#3B3F8F"))
            for r in range(3):
                c.drawRRect(rrect(-62, -54 + r * 40, 70 + 40 * hrand(r, 2), 22, 6), fill(["#E98AAE", "#7FB6D9", "#9BD19B"][r]))
            marker(c, [(-110, -110), (110, 110)], prog(t, NOAPP.w(5) + 0.2, 0.18), RED, 18, smooth=False)
            marker(c, [(110, -110), (-110, 110)], prog(t, NOAPP.w(5) + 0.35, 0.18), RED, 18, smooth=False)
            type_text(c, "0 APPS", 0, 150, 34, anchor="c")
        c.restore()
    if t >= REST.w(4) - 0.05:
        for i in range(5):
            kk = t - REST.w(4) - i * 0.05
            if kk < 0:
                continue
            x = 540 + 330 * math.cos(i * 1.3 + 0.5)
            y = 1130 + 420 * math.sin(i * 1.3 + 0.5)
            sc = spring(kk, w=20, z=0.4)
            c.save()
            c.translate(x, y)
            c.scale(sc, sc)
            star(c, 0, 0, 34, [YEL, PINK, WHITE][i % 3], n=4, inner=0.3, rot=kk * 2)
            c.restore()


# ================================================================== the frame
def draw(c, t, f):
    s = section(t)
    ts = src_at(min(t, TOTAL))
    cam = camera(t)
    src = Src(ts, grade_kind(t))
    g = {"t": t, "s": s}
    if s == "end":
        paper(c, "lined")
        g_end(c, t)
        # the speaker as a small taped polaroid sticker, still talking/smiling
        k = e_out(prog(t, END_A, 0.4))
        c.save()
        c.translate(lerp(540, 250, k), lerp(960, 1470, k))
        c.rotate(-6 * k)
        sc = lerp(1.0, 0.26, k)
        c.scale(sc, sc)
        c.translate(-540, -960)
        cr = rrect(140, 520, 800, 900, 10)
        if k > 0:
            c.drawRRect(cr.makeOffset(16, 22), fill("#000000", 0.3 * k, blur=20))
            c.drawRRect(rrect(110, 490, 860, 1060, 10), fill(WHITE))
        c.save()
        c.clipRRect(cr, True)
        paper(c, "pink")
        draw_person(c, src, (1.0, 0, 0, 0), border_a=1.0, shadow=False)
        c.restore()
        c.restore()
        if k >= 1:
            tape(c, 250, 1470 - 140, 120, 36, rot=6)
        return g
    if s == "reveal":
        paper(c, "kraft")
        draw_captions(c, t, cam)
        g_reveal(c, t, src)
        return g
    if s == "fifty":
        paper(c, "lined")
        draw_captions(c, t, cam)
        # the speaker shrinks into tile #1 as the grid builds
        k = e_io(prog(t, SEC["fifty"][0], 0.35))
        if k < 1:
            c.save()
            c.translate(lerp(0, -380, k), lerp(0, -230, k))
            c.scale(lerp(1, 0.08, k), lerp(1, 0.08, k))
            draw_person(c, src, cam)
            c.restore()
        g_fifty(c, t, src)
        return g

    kind = bg_kind(t)
    if kind is None or (s == "hook" and t < TEAR_T + 0.5):
        # real footage plate (the hook before the tear, and the cinematic look)
        c.save()
        apply_cam(c, cam)
        c.drawImage(src.cine_plate() if kind is None else src.plate(), 0, 0, SAMP)
        c.restore()
    if s == "hook" and t < TEAR_T + 0.5:
        paper(c, "lined")
        draw_tear(c, prog(t, TEAR_T, 0.45), src, cam)
    elif kind is not None:
        paper(c, kind)
        if s == "every":
            ph = ((t - DROP) % BEAT) / BEAT
            r = 1400 * (0.9 + 0.1 * (1 - ph) ** 2)
            c.drawCircle(FACE[0], FACE[1], r, fill(WHITE, 0.0))
    # behind the speaker
    if s == "music" or s == "every":
        pass
    draw_captions(c, t, cam)
    title_behind(c, t)
    if s == "no":
        g_no(c, t, True)
    border_a = 0.0 if kind is None else (prog(t, TEAR_T + 0.1, 0.3) if s == "hook" else 1.0)
    draw_person(c, src, cam, border_a)
    # in front
    {"hook": g_hook, "years": g_years, "old": g_old, "flip": g_flip, "brief": g_brief, "cine": g_cine,
     "music": g_music, "every": g_every, "formats": g_formats, "need": g_need, "product": g_product}.get(
        s, lambda c, t: None)(c, t)
    if s == "brief":
        pass
    if s == "no":
        g_no(c, t, False)
    if s in ("brief", "music") and t >= CUTP.s:
        pass
    confetti(c, t, DROP)
    if DROP <= t < DROP + 0.12:
        c.drawRect(skia.Rect(0, 0, W, H), fill(WHITE, 0.85 * (1 - (t - DROP) / 0.12)))
    if s == "every" and DROP <= t < DROP + 0.9:
        stamp(c, "BUILT.", 540, 1380, 120, prog(t, DROP + 0.02, 0.5), RED, rot=-8)
    return g


# ================================================================== post: transitions, grain
WHIPS = [SEC["years"][0], SEC["brief"][0], SEC["music"][0], SEC["formats"][0], SEC["product"][0]]
FLIPS_T = [SEC["flip"][0], SEC["need"][0], SEC["end"][0]]
_grain = None


def post(rgb, g, f):
    global _grain
    t = g.get("t", f / FPS)
    out = rgb
    h, w = out.shape[:2]
    for T in WHIPS:                           # whip pan: blur + slide, out to the left, in from the right
        d = t - T
        if -0.12 <= d < 0.12:
            k = 1 - abs(d) / 0.12
            sh = int((w * 0.45) * (k ** 2) * (-1 if d < 0 else 1))
            ln = max(3, int(90 * k * w / W)) | 1
            ker = np.zeros((1, ln), np.float32)
            ker[0, :] = 1 / ln
            out = cv2.filter2D(np.roll(out, sh, axis=1), -1, ker)
    for T in FLIPS_T:                         # page flip around the vertical axis
        d = t - T
        if -0.14 <= d < 0.14:
            k = abs(d) / 0.14                     # 0 at the edge-on moment
            sx = max(0.02, e_out(k))
            hw = w * sx / 2
            persp = 70 * (1 - sx) * w / W
            src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
            if d < 0:
                dst = np.float32([[w / 2 - hw, persp], [w / 2 + hw, 0], [w / 2 + hw, h], [w / 2 - hw, h - persp]])
            else:
                dst = np.float32([[w / 2 - hw, 0], [w / 2 + hw, persp], [w / 2 + hw, h - persp], [w / 2 - hw, h]])
            M = cv2.getPerspectiveTransform(src, dst)
            desk = np.empty_like(out)
            desk[:] = (60, 44, 36)
            warped = cv2.warpPerspective(np.ascontiguousarray(out), M, (w, h), dst=desk, flags=cv2.INTER_LINEAR,
                                         borderMode=cv2.BORDER_TRANSPARENT)
            shade = 0.55 + 0.45 * sx
            out = np.clip(warped.astype(np.float32) * shade, 0, 255).astype(np.uint8)
    if _grain is None or _grain[0].shape != (h // 2 + 1, w // 2 + 1):
        rng = np.random.default_rng(5)
        _grain = [rng.standard_normal((h // 2 + 1, w // 2 + 1)).astype(np.float32) for _ in range(6)]
    gr = np.repeat(np.repeat(_grain[f % 6], 2, 0), 2, 1)[:h, :w]
    return np.clip(out.astype(np.float32) + gr[..., None] * 6.5, 0, 255).astype(np.uint8)


FILM = kit.Film(draw, dur=TOTAL, fps=FPS, post=post, out_dir=str(OUT))


def stills(ts, scale=0.5):
    FILM.stills(ts, scale)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "info"
    if cmd == "info":
        print(f"total {TOTAL:.2f}s  speech end {END_A:.2f}  drop {DROP:.2f}")
        for k, (a, b) in SEC.items():
            print(f"  {k:8s} {a:6.2f}-{b:6.2f}")
    elif cmd == "stills":
        stills([float(x) for x in sys.argv[2:]])
    elif cmd == "sheet":
        FILM.sheet(cols=8)
    elif cmd == "render":
        draft = "--draft" in sys.argv
        pic = FILM.render(OUT / ("draft_picture.mp4" if draft else "picture.mp4"), draft=draft)
        import soundtrack
        mix = soundtrack.build()
        finish(pic, mix, OUT / ("draft.mp4" if draft else "vibe_editing_reel.mp4"))
    elif cmd == "audio":
        import soundtrack
        soundtrack.build()


def finish(picture, audio, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(picture), "-i", str(audio), "-map", "0:v", "-map", "1:a",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-maxrate", "3300k", "-bufsize", "6400k",
                    "-pix_fmt", "yuv420p", "-profile:v", "high", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k",
                    "-ar", "48000", "-movflags", "+faststart", "-shortest", str(out)], check=True)
    print("->", out)


if __name__ == "__main__":
    main()
