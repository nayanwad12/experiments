"""reel: the Meta-ad edit of the 40 s "I didn't edit this, my system did" take, in the creator-tutorial format.

Same look as talking-reel/creator.py (the Pinterest reference): moody relit room, hand-lettered line + wide
italic yellow word, small white subtitles, white app-UI split screens, glitch cuts. Everything the script
claims happens on screen at that word: the captions get called out, real text goes behind the speaker,
the background swaps, the music drops in on "music", stills of this very edit, the export. Ends on
"tap the link below" -> LEARN MORE + arrows down at the ad button. Text kept out of the bottom 35 %
(Meta Reels-ad safe zone: caption + CTA button).
Whole edit at 1.15x (core.SPEED), pauses trimmed to a breath.

    python3 reel.py sheet [t ...]     -> out/reel_sheet.png
    python3 reel.py render            -> out/vibe40_ad.mp4
"""

import math
import sys
from pathlib import Path

import cv2
import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "reels" / "common"))
import core as E  # noqa: E402  (words, cut list at 1.15x, matte, voice)
import audio_kit as ak  # noqa: E402
import kit  # noqa: E402
from kit import clamp, e_back, e_in, e_io, e_out, fill, font, hrand, lerp, measure, prog, spring, stroke  # noqa: E402
from vibelib import ff, loudnorm_filter  # noqa: E402

cv2.setNumThreads(1)
kit.FONTS.update(wide="ArchivoExpanded-BlackItalic.ttf", hand="RockSalt.ttf")
W, H, FPS = 1080, 1920, 30
OUT = HERE / "out"
TOTAL = E.TOTAL
SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNone)
CTA_WORD = "VIBE"

YEL = "#F8E20A"
WHITE = "#FFFFFF"
INK = "#0B0C0C"
UI_LINE = "#E6E7EA"
UI_SOFT = "#F3F4F6"
UI_TXT = "#15161A"
UI_SUB = "#8A8D96"
LIME = "#B8F230"
GREEN = "#1FD12E"
PURPLE = "#9B7BFF"
BLUE = "#2F7BFF"
SKY = "#D8ECFF"
RED = "#FF4D3D"


def col(c, a=1.0):
    r, g, b = kit.rgb(c)
    return skia.Color(r, g, b, int(255 * clamp(a)))


# ================================================================== grade: moody room relight
def _luts():
    x = np.arange(256, dtype=np.float32) / 255
    s = np.clip(x + 0.07 * np.sin(2 * math.pi * (x - 0.5)), 0, 1)
    person = [0.03 + 0.86 * s ** 1.08, 0.035 + 0.83 * s ** 1.1, 0.04 + 0.78 * s ** 1.12]
    return np.ascontiguousarray(np.stack([(np.clip(c, 0, 1) * 255).astype(np.uint8) for c in person], 1)
                                .reshape(256, 1, 3))


PLUT = _luts()
ROOM = np.array([0.30, 0.355, 0.37], np.float32)      # cream wall (~228) -> ~ (68, 81, 84) teal-grey
_LIGHT = None


def room_light():
    """soft window light from the upper left on the wall, falling off to the floor."""
    global _LIGHT
    if _LIGHT is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - 200) / 900) ** 2 + ((yy - 350) / 1100) ** 2)
        _LIGHT = (1.2 - 0.45 * np.clip(r, 0, 1.4)).astype(np.float32)
    return _LIGHT


def kit_img(rgb, a=None):
    out = cv2.cvtColor(rgb, cv2.COLOR_RGB2RGBA)
    if a is not None:
        out[..., 3] = a
    return skia.Image.fromarray(out, colorType=skia.kRGBA_8888_ColorType)


class Src:
    """one source frame relit: person warm, room dark teal-grey."""
    _cache = {}

    def __new__(cls, ts):
        fi = int(clamp(round(ts * E.SRC_FPS), 0, E.NSRC - 1))
        if fi in cls._cache:
            return cls._cache[fi]
        o = super().__new__(cls)
        if len(cls._cache) > 14:
            cls._cache.pop(next(iter(cls._cache)))
        cls._cache[fi] = o
        o.fi, o.ts, o._m = fi, ts, {}
        return o

    def _memo(self, k, fn):
        if k not in self._m:
            self._m[k] = fn()
        return self._m[k]

    def graded(self):
        def make():
            raw = E.frame_rgb(self.fi)
            p = cv2.LUT(raw, PLUT)
            gray = cv2.cvtColor(cv2.cvtColor(p, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB)
            p = cv2.addWeighted(p, 0.88, gray, 0.12, 0)
            a = cv2.resize(E.alpha_small(self.fi), (W, H)).astype(np.float32) / 255
            a = a * a * (3 - 2 * a)                                  # firmer edge: no bright halo
            m = (1 - a) * room_light()
            fac = cv2.merge([a + m * ROOM[ch] for ch in range(3)])
            return cv2.multiply(p, fac, dtype=cv2.CV_8U), (a * 255).astype(np.uint8), p
        return self._memo("g", make)

    def img(self):
        return self._memo("img", lambda: kit_img(self.graded()[0]))

    def person(self):
        return self._memo("person", lambda: kit_img(self.graded()[2], self.graded()[1]))

    def raw(self):
        return self._memo("raw", lambda: kit_img(E.frame_rgb(self.fi)))


# ================================================================== timing
def at(p):
    """the cut point that opens phrase p (or just before it, when p starts mid-run)."""
    rs = E.run_start(p)
    return rs if p.s - rs < 0.3 else p.s - 0.05


P = E.P
HOOK = P("the video you are watching right now i didn't edit it")
DID = P("my vibe editing system did")
REC1 = P("i recorded one take on my phone")
PME = P("pauses mistakes everything")
TOLD = P("then i told it what i want in simple words")
CUT = P("it cut every pause down to the exact word")
CAPS = P("it added these captions")
BEH = P("put text behind me")
BG = P("and changed my background")
MUS = P("even the music and sound effects made from scratch no copyright")
STL = P("and before exporting it showed me every key moment")
CMD = P("one command and it's ready for every platform")
NOT = P("no timeline no editing app just my system")
CTA = P("so if you want to learn my system tap the link below")
DROP_T = MUS.w(2)                     # the music drops in on "music"
NOCOPY = MUS.w(9) - 0.06

SPLITS = [("upload", at(REC1), at(TOLD)), ("prompt", at(TOLD), at(CUT)), ("timeline", at(CUT), at(CAPS)),
          ("sound", at(MUS), NOCOPY), ("nocopy", NOCOPY, at(STL)), ("stills", at(STL), at(CMD)),
          ("export", at(CMD), at(NOT))]


def split_now(t):
    for name, a, b in SPLITS:
        if a <= t < b:
            return name, a, b
    return None


# background swaps on "changed my background" (None = the relit room)
SWAPS = [(BG.w(1) - 0.04, YEL), (BG.w(2) - 0.04, WHITE), (BG.w(3) - 0.04, LIME),
         (BG.w(3) + 0.3, PURPLE), (BG.e + 0.05, None)]
GLITCHES = sorted({a for _, a, _ in SPLITS} | {b for _, _, b in SPLITS})


def bg_now(t):
    cur = None
    for tt, cc in SWAPS:
        if t >= tt:
            cur = cc
    return cur if BG.w(1) - 0.04 <= t < BG.e + 0.05 else None


# ================================================================== framing
BASE_Z, BASE_DY = 1.1, 75           # closer, larger face in this take: head top just under the titles
SPLIT_DY = 360                      # in split screen the speaker sits in the lower half
SHAKES = []


def cam(t, ts, split=False):
    fx, fy = E.face(ts)
    k = max([i for i, s in enumerate(E.RUN_STARTS) if s <= t + 1e-6] or [0])
    z = BASE_Z * (1.0, 1.05, 1.02, 1.07)[k % 4] * (1 + 0.01 * (t - E.RUN_STARTS[k]))
    if t < 0.3:
        z *= lerp(1.25, 1.0, e_out(t / 0.3))
    for t0, amt in ((DID.w(1) - 0.04, 1.1), (NOT.w(5) - 0.04, 1.12), (CTA.w(8) - 0.04, 1.1)):
        if t0 <= t < t0 + 1.4:
            z *= lerp(1.0, amt, e_out(prog(t, t0, 0.18)))
    if E.SPEECH_END + 0.2 <= t:
        z *= lerp(1.0, 0.97, e_io(prog(t, E.SPEECH_END + 0.2, 1.5)))
    if DROP_T <= t < at(NOT):
        ph = ((t - DROP_T) % BEAT) / BEAT
        z *= 1 + 0.02 * (1 - ph) ** 3
    dy = BASE_DY + (SPLIT_DY if split else 0)
    dx = 0.0
    for st, amp in SHAKES:
        if st <= t < st + 0.25:
            kk = 1 - (t - st) / 0.25
            dx += amp * kk * math.sin(t * 95)
            dy += amp * kk * math.sin(t * 81 + 1)
    return z, fx, fy, dx, dy


def draw_footage(c, src, cm):
    """the relit frame, with the plain wall extended upward to fill what the drop leaves open."""
    c.save()
    apply(c, cm)
    c.drawImageRect(src.img(), skia.Rect.MakeXYWH(0, 0, W, 24), skia.Rect.MakeXYWH(0, -700, W, 712), SAMP)
    c.drawImage(src.img(), 0, 0, SAMP)
    c.restore()


def apply(c, cm):
    z, fx, fy, dx, dy = cm
    c.translate(fx + dx, fy + dy)
    c.scale(z, z)
    c.translate(-fx, -fy)


def head_top(t, ts, split=False):
    z, fx, fy, dx, dy = cam(t, ts, split)
    top = E.head_top_src(ts)
    return fy + dy + z * (top - fy)


# ================================================================== type
def txt(c, s, x, y, name, size, color=WHITE, a=1.0, anchor="l", paint=None):
    return kit.text(c, s, x, y, name, size, color=color, a=a, anchor=anchor, paint=paint)


def hand(c, s, x, y, size, k=1.0, color=WHITE, anchor="c", a=1.0):
    """small hand-lettered caps line, written on left to right by k."""
    if k <= 0:
        return
    w = measure(s, "hand", size)
    x0 = x - w / 2 if anchor == "c" else x - w if anchor == "r" else x
    c.save()
    c.clipRect(skia.Rect.MakeLTRB(x0 - 20, y - size * 2, x0 + (w + 40) * e_out(k), y + size))
    kit.text(c, s, x0 + 2, y + 3, "hand", size, color="#000000", a=0.35 * a, anchor="l",
             paint=fill("#000000", 0.35 * a, blur=4))
    kit.text(c, s, x0, y, "hand", size, color=color, a=a, anchor="l")
    c.restore()


def fit(s, maxw=960, size=150):
    """font size for the big word so it fits maxw, and its cap height."""
    w = measure(s, "wide", size)
    if w > maxw:
        size *= maxw / w
    return size, font("wide", size).getMetrics().fCapHeight


def big_type(c, s, x, y, t, t0, maxw=960, size=150, anchor="c", color=YEL, stagger=0.045, a=1.0, t_out=None):
    """huge wide italic word, typed on letter by letter; each letter flies in big and settles."""
    if t < t0 or a <= 0:
        return 0
    w = measure(s, "wide", size)
    if w > maxw:
        size *= maxw / w
        w = measure(s, "wide", size)
    f = font("wide", size)
    x0 = x - w / 2 if anchor == "c" else x
    xx = x0
    for i, ch in enumerate(s):
        cw = f.measureText(ch)
        k = clamp((t - t0 - i * stagger) / 0.2)
        if k > 0:
            sp = e_out(k)
            sc = lerp(1.7, 1.0, sp)
            dx = lerp(size * 0.35, 0, sp)
            dy = lerp(size * 0.2, 0, sp)
            aa = a * clamp(k * 4)
            if t_out is not None and t > t_out:
                ko = clamp((t - t_out - i * 0.015) / 0.12)
                aa *= 1 - ko
                dy -= ko * size * 0.3
            c.save()
            c.translate(xx + cw / 2 + dx, y + dy)
            c.scale(sc, sc)
            c.drawString(ch, -cw / 2 + 3, 5, f, fill("#000000", 0.35 * aa, blur=6))
            c.drawString(ch, -cw / 2, 0, f, fill(color, aa))
            c.restore()
        xx += cw
    return w


def scribble(c, x0, x1, y, k, color=INK, width=7, seed=1):
    """loose hand-drawn loop underline (the reference's black scribble)."""
    if k <= 0:
        return
    pts = []
    n = 60
    for i in range(n + 1):
        u = i / n
        xx = lerp(x0, x1, u)
        yy = y + 10 * math.sin(u * 7 + seed) + (hrand(seed, i) - 0.5) * 3
        if 0.35 < u < 0.5:
            th = (u - 0.35) / 0.15 * 2 * math.pi
            xx += 26 * math.sin(th)
            yy -= 22 * (1 - math.cos(th)) / 2
        pts.append((xx, yy))
    path = skia.Path()
    path.moveTo(*pts[0])
    for p in pts[1:]:
        path.lineTo(*p)
    p = stroke(color, width)
    if k < 1:
        p.setPathEffect(skia.TrimPathEffect.Make(0, clamp(k)))
    c.drawPath(path, p)


def bubble_doodle(c, x, y, s, k, color=INK):
    if k <= 0:
        return
    path = skia.Path()
    path.addOval(skia.Rect.MakeXYWH(x - s, y - s * 0.8, 2 * s, 1.6 * s))
    path.moveTo(x - s * 0.45, y + s * 0.65)
    path.lineTo(x - s * 0.75, y + s * 1.15)
    path.lineTo(x - s * 0.05, y + s * 0.78)
    p = stroke(color, 8)
    if k < 1:
        p.setPathEffect(skia.TrimPathEffect.Make(0, clamp(k)))
    c.drawPath(path, p)


def arrow_doodle(c, pts, k, color=WHITE, width=7):
    if k <= 0:
        return
    path = skia.Path()
    path.moveTo(*pts[0])
    for i in range(1, len(pts) - 1):
        mx, my = (pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2
        path.quadTo(pts[i][0], pts[i][1], mx, my)
    path.lineTo(*pts[-1])
    p = stroke(color, width)
    if k < 0.8:
        p.setPathEffect(skia.TrimPathEffect.Make(0, clamp(k / 0.8)))
    c.drawPath(path, p)
    if k > 0.8:
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        ang = math.atan2(y1 - y0, x1 - x0)
        hk = e_out((k - 0.8) / 0.2) * 40
        for sg in (-1, 1):
            a2 = ang + math.pi + sg * 0.55
            c.drawLine(x1, y1, x1 + hk * math.cos(a2), y1 + hk * math.sin(a2), stroke(color, width))


# ================================================================== titles (full frame)
TITLE_Y = 634          # big word baseline (reference: 30-33 % of the frame)
BEAT = 60 / 96
TITLES = [
    # small line, big word, t small, t big, t end
    ("THE VIDEO YOU ARE WATCHING", "I DIDN'T EDIT IT", HOOK.s - 0.03, HOOK.w(7) - 0.05, DID.s - 0.03),
    ("IT WAS EDITED BY MY", "VIBE EDITING SYSTEM", DID.s - 0.03, DID.w(1) - 0.05, at(REC1)),
    ("", "JUST MY SYSTEM", NOT.s - 0.03, NOT.w(5) - 0.05, CTA.s - 0.03),
    ("WANT TO LEARN", "MY SYSTEM?", CTA.s - 0.03, CTA.w(6) - 0.05, CTA.w(8) - 0.04),
]


def draw_titles(c, t, ht):
    for small, big, ts_, tb, te in TITLES:
        if not ts_ <= t < te:
            continue
        y = min(TITLE_Y, ht - 40)
        cap = fit(big)[1] if big else 0
        if small:
            hand(c, small, 540, y - cap - 36, 40, prog(t, ts_, 0.3))
        w = big_type(c, big, 540, y, t, tb) if big else 0
        if big.startswith("I DIDN'T"):
            scribble(c, 540 - w / 2 + 60, 540 + w / 2 - 40, y + 44, prog(t, tb + 0.35, 0.45), INK, 7, 3)
    # (no floating UI pieces in the ad cut: this take is framed tighter and they would crowd the hook title)
    # "no timeline, no editing app": hand lines struck through, above "JUST MY SYSTEM"
    if NOT.s - 0.03 <= t < CTA.s - 0.03:
        y = min(TITLE_Y, ht - 40) - fit("JUST MY SYSTEM")[1] - 36
        for j, (s_, t0) in enumerate((("NO TIMELINE", NOT.s - 0.03), ("NO EDITING APP", NOT.w(2) - 0.03))):
            yy = y - (1 - j) * 78
            hand(c, s_, 540, yy, 40, prog(t, t0, 0.3))
            w_ = measure(s_, "hand", 40)
            ks = prog(t, t0 + 0.35, 0.2)
            if ks > 0:
                p_ = stroke(YEL, 7)
                if ks < 1:
                    p_.setPathEffect(skia.TrimPathEffect.Make(0, ks))
                c.drawLine(540 - w_ / 2 - 12, yy - 18, 540 + w_ / 2 + 12, yy - 26, p_)


def ui_float(c, t, t0):
    items = [(150, 335, "toggle"), (300, 335, "dots"), (470, 335, "pill"), (690, 335, "lime"), (880, 335, "purple")]
    for j, (x, y, kind) in enumerate(items):
        k = prog(t, t0 + j * 0.06, 0.3)
        if k <= 0:
            continue
        s = e_back(k)
        c.save()
        c.translate(x, y + 6 * math.sin(t * 2 + j))
        c.scale(s, s)
        if kind == "toggle":
            c.drawRRect(kit.rrect(-50, -26, 100, 52, 26), fill(GREEN))
            c.drawCircle(22, 0, 20, fill(WHITE))
        elif kind == "dots":
            for q, cc in enumerate((BLUE, LIME, PURPLE)):
                c.drawCircle(-40 + q * 40, 0, 16, fill(cc))
        elif kind == "pill":
            c.drawRRect(kit.rrect(-95, -26, 190, 52, 26), fill(INK))
            txt(c, "Auto-edit", 0, 9, "bold", 24, WHITE, anchor="c")
        elif kind == "lime":
            c.drawRRect(kit.rrect(-90, -55, 180, 110, 16), fill(LIME))
            txt(c, "6 steps", -70, -20, "bold", 22, INK)
            c.drawCircle(60, 32, 14, fill(INK))
        elif kind == "purple":
            c.drawRRect(kit.rrect(-80, -55, 160, 110, 16), fill("#C9B8FF"))
            for q in range(3):
                c.drawRRect(kit.rrect(-60, -35 + q * 26, 90 - q * 20, 12, 6), fill(WHITE, 0.8))
        elif kind == "slider":
            c.drawRRect(kit.rrect(-90, -4, 180, 8, 4), fill(WHITE, 0.6))
            c.drawRRect(kit.rrect(-90, -4, 120, 8, 4), fill(WHITE))
            c.drawCircle(30, 0, 14, fill(WHITE))
        elif kind == "wave":
            for q in range(14):
                hh = 12 + 26 * abs(math.sin(q * 1.3 + t * 6))
                c.drawRRect(kit.rrect(-100 + q * 15, -hh / 2, 8, hh, 4), fill(WHITE))
        elif kind == "chip":
            c.drawRRect(kit.rrect(-90, -26, 180, 52, 12), fill("#2B2E33"))
            txt(c, "cut  0:02", 0, 9, "monob", 22, WHITE, anchor="c")
        c.restore()


# ================================================================== subtitles
def _groups():
    used = sorted([w for w in E.WORDS if w["os"] is not None], key=lambda w: w["os"])
    groups, cur = [], []
    for w in used:
        if cur and (len(cur) >= 3 or sum(len(x["d"]) + 1 for x in cur) + len(w["d"]) > 18
                    or w["os"] - cur[-1]["oe"] > 0.3 or cur[-1]["d"][-1] in ".,?"):
            groups.append(cur)
            cur = []
        cur.append(w)
    groups.append(cur)
    return groups


SUBS = _groups()


SUB_Y = 1238           # under the chin; Meta Reels ads cover the bottom ~35 % (y > 1250) with caption + CTA


def draw_subs(c, t, split):
    g = None
    for k, grp in enumerate(SUBS):
        nxt = SUBS[k + 1][0]["os"] if k + 1 < len(SUBS) else grp[-1]["oe"] + 0.5
        if grp[0]["os"] - 0.04 <= t < min(nxt - 0.02, grp[-1]["oe"] + 0.5):
            g = grp
    if not g:
        return
    s = " ".join(w["d"] for w in g)
    if g[0]["k"] == "this" and g[0]["os"] < 0.1:
        s = s[0].upper() + s[1:]
    if split:
        size = 40
        w = measure(s, "medium", size)
        y = 958
        c.drawRect(skia.Rect.MakeXYWH(540 - w / 2 - 10, y - 44, w + 20, 54), fill("#000000"))
        txt(c, s, 540, y - 4, "medium", size, WHITE, anchor="c")
    else:
        size = 46
        txt(c, s, 540, SUB_Y + 4, "medium", size, "#000000", anchor="c", paint=fill("#000000", 0.55, blur=8))
        txt(c, s, 540, SUB_Y, "medium", size, WHITE, anchor="c")


# ================================================================== UI kit (B-roll panel, 1080 x 960)
PANEL = 960


def cursor(c, x, y, click_k=0.0, s=1.0):
    if click_k > 0:
        r = 18 + 50 * e_out(click_k)
        c.drawCircle(x, y, r, fill(BLUE, 0.25 * (1 - click_k)))
    p = skia.Path()
    pts = [(0, 0), (0, 46), (12, 35), (21, 55), (29, 51), (20, 32), (36, 32)]
    p.moveTo(x + pts[0][0] * s, y + pts[0][1] * s)
    for px, py in pts[1:]:
        p.lineTo(x + px * s, y + py * s)
    p.close()
    c.drawPath(p, fill("#000000", 0.25, blur=4))
    c.drawPath(p, fill(INK))
    c.drawPath(p, stroke(WHITE, 3))


def card(c, x, y, w, h, bg=WHITE, r=22, border=UI_LINE, shadow=0.08, bw=2):
    rr = kit.rrect(x, y, w, h, r)
    if shadow:
        c.drawRRect(rr.makeOffset(0, 6), fill("#000000", shadow, blur=14))
    c.drawRRect(rr, fill(bg))
    if border:
        c.drawRRect(rr, stroke(border, bw))
    return rr


def green_box(c, x, y, w, h, k, width=10):
    """the reference's bright green highlight rectangle."""
    if k <= 0:
        return
    c.drawRRect(kit.rrect(x, y, w, h, 8), stroke(GREEN, width * e_out(k), clamp(k * 3)))


def check(c, x, y, s, k, color=GREEN):
    if k <= 0:
        return
    p = skia.Path()
    p.moveTo(x - 0.5 * s, y)
    p.lineTo(x - 0.12 * s, y + 0.38 * s)
    p.lineTo(x + 0.55 * s, y - 0.45 * s)
    st = stroke(color, s * 0.18)
    if k < 1:
        st.setPathEffect(skia.TrimPathEffect.Make(0, clamp(k)))
    c.drawPath(p, st)


def nav(c, title="vibe editing system"):
    c.drawRRect(kit.rrect(50, 40, 44, 44, 12), fill(INK))
    txt(c, "v", 72, 72, "black", 32, LIME, anchor="c")
    txt(c, title, 110, 72, "bold", 28, UI_TXT)
    for j, s in enumerate(("Steps", "Pricing", "Docs")):
        txt(c, s, 560 + j * 120, 72, "medium", 24, UI_SUB)
    c.drawRRect(kit.rrect(890, 40, 140, 46, 23), fill(INK))
    txt(c, "Open app", 960, 71, "bold", 22, WHITE, anchor="c")


def wave(c, x, y, w, h, n, seed, color, a=1.0, k=1.0, bars=True):
    for q in range(int(n * clamp(k))):
        lv = abs(math.sin(q * 0.7 + seed)) * (0.5 + 0.5 * abs(math.sin(q * 0.23 + seed * 3)))
        hh = max(4, h * lv)
        c.drawRRect(kit.rrect(x + q * w / n, y - hh / 2, w / n * 0.6, hh, 3), fill(color, a))


def thumb_rect(ts, aspect=1.0, zoom=1.0):
    """source crop rect around the face for a thumbnail of the given aspect (w/h)."""
    fx, fy = E.face(ts)
    h = 1000 / zoom
    w = min(W, h * aspect)
    h = w / aspect
    return skia.Rect.MakeXYWH(clamp(fx - w / 2, 0, W - w), clamp(fy - h * 0.42, 0, H - h), w, h)


def img_card(c, img, x, y, w, h, sr, r=16, a=1.0):
    rr = kit.rrect(x, y, w, h, r)
    c.save()
    c.clipRRect(rr, skia.ClipOp.kIntersect, True)
    c.drawImageRect(img, sr, skia.Rect.MakeXYWH(x, y, w, h), SAMP, skia.Paint(Alphaf=a))
    c.restore()


# ---------------------------------------------------------------- full-frame demonstrations
def captions_demo(c, t):
    """on "it added these captions": the words themselves become big pop captions, called out."""
    if not CAPS.s - 0.03 <= t < BEH.s - 0.03:
        return False
    words = [E.WORDS[CAPS.i0 + j] for j in range(4)]
    shown = [w for w in words if t >= w["os"] - 0.04]
    if shown:
        s = " ".join(w["d"].upper().strip(".,") for w in shown)
        size, _ = fit(s, 900, 92)
        f = font("wide", size)
        x = 540 - measure(s, "wide", size) / 2
        for j, w in enumerate(shown):
            wd = w["d"].upper().strip(".,") + " "
            k = prog(t, w["os"] - 0.04, 0.16)
            sc = lerp(1.5, 1.0, e_out(k))
            cw = f.measureText(wd)
            c.save()
            c.translate(x + cw / 2, SUB_Y)
            c.scale(sc, sc)
            cur = w["os"] - 0.04 <= t < w["oe"]
            c.drawString(wd, -cw / 2 + 4, 6, f, fill("#000000", 0.5, blur=8))
            c.drawString(wd, -cw / 2, 0, f, fill(YEL if cur or j == 3 else WHITE))
            c.restore()
            x += cw
    if t >= CAPS.w(2):
        k = prog(t, CAPS.w(2), 0.4)
        hand(c, "THESE ONES", 840, SUB_Y - 230, 36, k, anchor="c")
        arrow_doodle(c, [(840, SUB_Y - 200), (860, SUB_Y - 140), (800, SUB_Y - 90)], k, WHITE, 6)
    return True


def text_behind(c, t):
    """real text behind the speaker (drawn between the room and the cut-out person)."""
    if not BEH.w(1) - 0.05 <= t < BG.w(1) - 0.04:
        return
    k = prog(t, BEH.w(1) - 0.05, 0.25)
    ko = prog(t, BG.w(1) - 0.16, 0.12)
    c.save()
    c.translate(540, 830)
    s = lerp(1.35, 1.0, e_out(k))
    c.scale(s, s)
    kit.text(c, "TEXT", 6, 12, "wide", 330, color="#000000", a=0.35 * (1 - ko), paint=fill("#000000", 0.35, blur=14))
    kit.text(c, "TEXT", 0, 0, "wide", 330, color=YEL, a=clamp(k * 3) * (1 - ko))
    c.restore()


def person_layer(c, src, cm):
    c.save()
    apply(c, cm)
    c.drawImage(src.person(), 0, 0, SAMP)
    c.restore()


# ---------------------------------------------------------------- the scenes (white app UI, top half)
def sc_upload(c, t, a, b):
    nav(c)
    txt(c, "New edit", 70, 175, "heavy", 48, UI_TXT)
    dz = kit.rrect(70, 215, 940, 400, 28)
    t_drop = REC1.w(3)
    kd = prog(t, t_drop, 0.2)
    c.drawRRect(dz, fill("#F6FFF0" if kd > 0 else UI_SOFT))
    pth = skia.Path()
    pth.addRRect(dz)
    st = stroke(GREEN if kd > 0 else "#C5C8CF", 4)
    st.setPathEffect(skia.DashPathEffect.Make([18, 12], 0))
    c.drawPath(pth, st)
    if kd <= 0:
        c.drawLine(540, 330, 540, 410, stroke(UI_SUB, 8))
        c.drawLine(510, 360, 540, 330, stroke(UI_SUB, 8))
        c.drawLine(570, 360, 540, 330, stroke(UI_SUB, 8))
        txt(c, "Drop one take from your phone", 540, 470, "bold", 32, UI_SUB, anchor="c")
    kf = e_io(prog(t, a + 0.05, t_drop - a - 0.05))
    fx, fy = lerp(120, 380, kf), lerp(820, 300, kf)
    src = Src(E.src_at(t))
    card(c, fx, fy, 320, 120, WHITE, 16, shadow=0.18)
    img_card(c, src.raw(), fx + 14, fy + 14, 70, 92, thumb_rect(src.ts, 70 / 92), 10)
    txt(c, "take_01.mov", fx + 100, fy + 52, "bold", 28, UI_TXT)
    txt(c, "0:40  ·  iPhone", fx + 100, fy + 88, "medium", 22, UI_SUB)
    if kd <= 0:
        cursor(c, fx + 250, fy + 70)
    else:
        bar = clamp((t - t_drop - 0.05) / 0.7)
        c.drawRRect(kit.rrect(380, 460, 560, 14, 7), fill(UI_LINE))
        c.drawRRect(kit.rrect(380, 460, 560 * e_io(bar), 14, 7), fill(GREEN))
        txt(c, "Uploaded" if bar >= 1 else f"Uploading… {int(100 * e_io(bar))}%", 380, 520, "bold", 26, UI_TXT)
        check(c, 920, 510, 40, prog(t, t_drop + 0.8, 0.25))
    if t >= REC1.w(2) - 0.05:
        kk = e_back(prog(t, REC1.w(2) - 0.05, 0.3))
        c.drawRRect(kit.rrect(70, 650, 200 * kk, 64, 32), fill(LIME))
        if kk > 0.6:
            txt(c, "1 take", 170, 692, "bold", 28, INK, anchor="c")
    # the raw take's problems, tagged as he names them
    for j, (lab, tj) in enumerate((("pauses", PME.w(0)), ("mistakes", PME.w(1)), ("everything", PME.w(2)))):
        kj = prog(t, tj - 0.05, 0.3)
        if kj <= 0:
            continue
        x = 300 + j * 230
        s = e_back(kj)
        c.save()
        c.translate(x + 100, 682)
        c.scale(s, s)
        c.drawRRect(kit.rrect(-100, -32, 200, 64, 32), fill("#FFE4E1"))
        c.drawRRect(kit.rrect(-100, -32, 200, 64, 32), stroke(RED, 3))
        txt(c, lab, 0, 10, "bold", 26, RED, anchor="c")
        c.restore()
    if t >= PME.w(2) + 0.3:
        txt(c, "all of it is fine. the system fixes it.", 70, 790, "bold", 26, GREEN, a=prog(t, PME.w(2) + 0.3, 0.25))


def sc_prompt(c, t, a, b):
    nav(c)
    txt(c, "Tell it what you want", 70, 175, "heavy", 48, UI_TXT)
    src = Src(E.src_at(t))
    img_card(c, src.img(), 70, 220, 330, 590, thumb_rect(src.ts, 330 / 590, 0.85), 20)
    msg = "make it a premium reel. cut the pauses, add captions, add music."
    n = int(clamp((t - TOLD.w(2)) / max(0.3, TOLD.e - TOLD.w(2) - 0.1)) * len(msg))
    card(c, 440, 220, 570, 330, WHITE, 22)
    lines = kit.wrap(msg[:n], "medium", 34, 500)
    for j, ln in enumerate(lines):
        txt(c, ln, 470, 285 + j * 50, "medium", 34, UI_TXT)
    if n < len(msg) and int(t * 4) % 2:
        lx = 470 + measure(lines[-1] if lines else "", "medium", 34)
        c.drawRect(skia.Rect.MakeXYWH(lx + 3, 252 + 50 * max(0, len(lines) - 1), 3, 42), fill(UI_TXT))
    green_box(c, 430, 210, 590, 350, prog(t, TOLD.w(8) - 0.05, 0.2))
    if t >= TOLD.w(8):
        txt(c, "simple words", 440, 600, "bold", 28, GREEN, a=prog(t, TOLD.w(8), 0.2))
    if t >= TOLD.e - 0.15:
        k = prog(t, TOLD.e - 0.15, 0.2)
        c.drawRRect(kit.rrect(820, 480, 170, 56, 28), fill(INK, k))
        txt(c, "send", 905, 517, "bold", 26, WHITE, anchor="c", a=k)
        cursor(c, 930, 520, prog(t, TOLD.e - 0.05, 0.3))


BLOCKS = [("clip", 1.2), ("PAUSE", 0.55), ("clip", 0.9), ("PAUSE", 0.6), ("clip", 1.3), ("PAUSE", 0.5),
          ("clip", 0.7), ("PAUSE", 0.65), ("clip", 1.0)]


def sc_timeline(c, t, a, b):
    nav(c)
    txt(c, "Cut", 70, 175, "heavy", 48, UI_TXT)
    src = Src(E.src_at(t))
    img_card(c, src.img(), 340, 205, 400, 300, thumb_rect(src.ts, 4 / 3, 0.9), 18)
    card(c, 50, 540, 980, 360, "#16181C", 22, border=None)
    if t < CUT.w(4) - 0.05:
        kg = e_io(prog(t, CUT.w(2) - 0.05, 0.45))
        tot0 = sum(d for _, d in BLOCKS)
        tot1 = sum(d for n_, d in BLOCKS if n_ == "clip")
        x = 80
        for j, (nm, d) in enumerate(BLOCKS):
            bad = nm != "clip"
            bw = 920 * (d * (1 - kg) if bad else d) / lerp(tot0, tot1, kg)
            if bw > 1:
                if bad:
                    c.drawRRect(kit.rrect(x + 2, 600, bw - 4, 120, 10), fill(RED))
                    if bw > 70:
                        txt(c, nm, x + bw / 2, 670, "black", 20, WHITE, anchor="c", a=1 - kg)
                else:
                    c.drawRRect(kit.rrect(x + 2, 600, bw - 4, 120, 10), fill("#3D7BFF"))
                    wave(c, x + 10, 660, bw - 20, 70, int(bw / 12), j * 1.7, "#BFD3FF")
                c.drawRRect(kit.rrect(x + 2, 745, bw - 4, 60, 8), fill("#2A2D33"))
            x += bw
        if kg > 0:
            txt(c, f"-{2.3 * kg:.1f}s of pauses", 1000, 860, "bold", 26, GREEN, anchor="r")
        c.drawRect(skia.Rect.MakeXYWH(80 + 920 * clamp((t - a) / (b - a)), 585, 4, 230), fill(WHITE))
    else:
        words = ["down", "to", "the", "exact", "word"]
        x = 90
        cut_x = 0
        for j, wd in enumerate(words):
            kj = prog(t, CUT.w(4 + j) - 0.04, 0.2)
            ww = measure(wd, "bold", 34) + 50
            c.drawRRect(kit.rrect(x, 600, ww, 80, 14), fill("#3D7BFF" if kj > 0 else "#2A2D33"))
            txt(c, wd, x + ww / 2, 652, "bold", 34, WHITE, anchor="c")
            wave(c, x, 760, ww, 70, int(ww / 10), j * 2.1, "#BFD3FF")
            if j == 3:
                cut_x = x - 11
            x += ww + 22
        kc = e_back(prog(t, CUT.w(7) - 0.05, 0.3))
        if kc > 0:
            c.drawRect(skia.Rect.MakeXYWH(cut_x - 3, 580, 6, 290 * kc), fill(GREEN))
            c.drawCircle(cut_x, 580, 12 * kc, fill(GREEN))
            txt(c, "cut point · frame accurate", 90, 870, "bold", 24, GREEN, a=clamp(kc))


def sc_sound(c, t, a, b):
    nav(c)
    txt(c, "Sound", 70, 175, "heavy", 48, UI_TXT)
    txt(c, "0 samples · 0 licences", 1010, 175, "bold", 24, UI_SUB, anchor="r")
    rows = [("Music · original score", PURPLE, MUS.w(2)), ("Sound effects", BLUE, MUS.w(5))]
    for j, (nm, cc, tj) in enumerate(rows):
        y = 225 + j * 180
        kj = prog(t, tj - 0.05, 0.3)
        card(c, 70, y, 940, 150, WHITE, 18)
        c.drawCircle(130, y + 75, 34, fill(cc, 0.15 + 0.85 * clamp(kj * 2)))
        tri = skia.Path()
        tri.moveTo(121, y + 58)
        tri.lineTo(121, y + 92)
        tri.lineTo(147, y + 75)
        tri.close()
        c.drawPath(tri, fill(WHITE))
        txt(c, nm, 190, y + 62, "bold", 30, UI_TXT)
        if kj > 0:
            if j == 0:
                wave(c, 190, y + 108, 790, 40, 90, 1.3, cc, k=clamp((t - tj) / 1.0))
            else:
                for q, lab in enumerate(("whoosh", "pop", "hit", "click", "riser")):
                    kq = prog(t, tj + q * 0.08, 0.2)
                    if kq > 0:
                        c.drawRRect(kit.rrect(190 + q * 160, y + 88, 140 * e_back(kq), 44, 22), fill(cc, 0.15))
                        txt(c, lab, 260 + q * 160, y + 118, "bold", 22, cc, anchor="c", a=kq)
    ks = prog(t, MUS.w(6) - 0.05, 0.25)
    c.drawRRect(kit.rrect(70, 610, 940, 100, 50), fill(INK if ks <= 0 else GREEN))
    txt(c, "Make from scratch" if ks <= 0 else "Made from scratch", 540, 672, "bold", 32, WHITE, anchor="c")
    if MUS.w(6) - 0.6 <= t < MUS.w(6) + 0.5:
        km = e_io(prog(t, MUS.w(6) - 0.6, 0.5))
        cursor(c, lerp(900, 560, km), lerp(860, 660, km), prog(t, MUS.w(6) - 0.05, 0.3))


def big_card(c, t, words, ts_list):
    """a giant black word on a yellow gradient card, sliding (the reference's 'Smooth' card)."""
    x, y, w, h = 40, 150, 1000, 640
    rr = kit.rrect(x, y, w, h, 34)
    p = skia.Paint(Shader=skia.GradientShader.MakeLinear([skia.Point(x, y), skia.Point(x, y + h)],
                                                         [col(YEL), col("#FFFBD2")]), AntiAlias=True)
    c.drawRRect(rr, p)
    cur = 0
    for j, tj in enumerate(ts_list):
        if t >= tj:
            cur = j
    t0 = ts_list[cur]
    c.save()
    c.clipRRect(rr, skia.ClipOp.kIntersect, True)
    k = prog(t, t0, 0.3)
    xx = lerp(x + w + 40, x + 70, e_out(k)) - (t - t0) * 80
    kit.text(c, words[cur], xx, y + h / 2 + 125, "anton", 330, color=INK, anchor="l")
    c.restore()


def sc_nocopy(c, t, a, b):
    big_card(c, t, ["NO COPYRIGHT."], [a])


STILL_SRC = []           # filled after the cut list: source times of six key moments of this edit


def sc_stills(c, t, a, b):
    nav(c)
    txt(c, "Before export", 70, 175, "heavy", 48, UI_TXT)
    txt(c, "every key moment", 400, 175, "medium", 28, UI_SUB)
    for j, ts in enumerate(STILL_SRC):
        tj = STL.w(4) - 0.05 + j * 0.13
        kj = prog(t, tj, 0.3)
        x = 70 + (j % 3) * 320
        y = 215 + (j // 3) * 330
        if kj <= 0:
            c.drawRRect(kit.rrect(x, y, 290, 300, 18), fill(UI_SOFT))
            continue
        s = Src(ts)
        c.save()
        c.translate(x + 145, y + 150)
        c.scale(e_back(kj), e_back(kj))
        c.translate(-x - 145, -y - 150)
        img_card(c, s.img(), x, y, 290, 300, thumb_rect(ts, 290 / 300, 0.95), 18)
        c.restore()
        c.drawCircle(x + 255, y + 35, 22, fill(WHITE, clamp(kj * 2)))
        check(c, x + 255, y + 36, 26, prog(t, STL.w(6) + j * 0.1, 0.25))


FORMATS = [("Reels", "9:16", 9 / 16), ("Feed", "4:5", 4 / 5), ("YouTube", "16:9", 16 / 9), ("Square", "1:1", 1.0)]


def sc_export(c, t, a, b):
    nav(c)
    t_f = CMD.w(6) - 0.05
    if t < t_f:
        cmd = "/export --all"
        card(c, 70, 160, 940, 100, INK, 50, border=None)
        n = int(clamp((t - CMD.w(0)) / 0.45) * len(cmd))
        txt(c, cmd[:n] + ("|" if int(t * 4) % 2 else ""), 120, 225, "monob", 36, WHITE)
        if t >= CMD.w(2) - 0.05:
            k = prog(t, CMD.w(2) - 0.05, 0.25)
            card(c, 70, 300, 940, 560, SKY, 26, border=None, shadow=0)
            pct = int(100 * clamp((t - CMD.w(2)) / max(0.3, t_f - CMD.w(2) - 0.1)))
            txt(c, f"{pct}%", 120, 620, "light", 240, BLUE, a=k)
            txt(c, "ready" if pct >= 100 else "exporting", 130, 700, "bold", 30, BLUE, a=k)
            c.drawRRect(kit.rrect(130, 760, 820, 14, 7), fill(WHITE, k))
            c.drawRRect(kit.rrect(130, 760, 820 * pct / 100, 14, 7), fill(BLUE, k))
        return
    txt(c, "Every platform", 70, 175, "heavy", 48, UI_TXT)
    src = Src(E.src_at(t))
    boxes = [(70, 230, 236, 420), (340, 230, 336, 420), (710, 230, 300, 169), (710, 480, 170, 170)]
    for j, (nm, ar, asp) in enumerate(FORMATS):
        kj = prog(t, t_f + j * 0.12, 0.3)
        if kj <= 0:
            continue
        x, y, ww, hh = boxes[j]
        c.save()
        c.translate(x + ww / 2, y + hh / 2)
        c.scale(e_back(kj), e_back(kj))
        c.translate(-x - ww / 2, -y - hh / 2)
        img_card(c, src.img(), x, y, ww, hh, thumb_rect(src.ts, asp, 0.8 if asp > 1 else 1.0), 14)
        c.restore()
        txt(c, f"{nm}  {ar}", x, y + hh + 38, "bold", 24, UI_TXT, a=clamp(kj * 2))
        check(c, x + ww - 26, y + 30, 30, prog(t, t_f + 0.5 + j * 0.06, 0.25))


SCENES = dict(upload=sc_upload, prompt=sc_prompt, timeline=sc_timeline, sound=sc_sound, nocopy=sc_nocopy,
              stills=sc_stills, export=sc_export)


# ================================================================== CTA + end card
def cta(c, t):
    """ "tap the link below": LEARN MORE (the ad button's words) and arrows down at the button."""
    if t < CTA.w(8) - 0.04:
        return
    t0 = CTA.w(8) - 0.04
    cap = fit("LEARN MORE", 960, 150)[1]
    hand(c, "TAP THE LINK BELOW", 540, TITLE_Y - cap - 36, 40, prog(t, t0, 0.3))
    big_type(c, "LEARN MORE", 540, TITLE_Y, t, t0 + 0.05, size=150)
    kb = prog(t, CTA.w(11) - 0.08, 0.35)
    if kb > 0:
        # hand-drawn arrow from beside the head down towards the button, and bouncing chevrons
        arrow_doodle(c, [(860, 700), (930, 820), (910, 950), (870, 1060)], kb, WHITE, 8)
        for j in range(3):                    # beside the face, under the arrow, pointing at the button
            ph = ((t - CTA.w(11)) * 1.6 - j * 0.18) % 1.0
            a = clamp(kb * 2) * (0.35 + 0.65 * math.sin(math.pi * ph))
            y = 1110 + j * 40 + 8 * math.sin(2 * math.pi * ph)
            p = stroke(YEL, 9, a)
            c.drawLine(820, y, 870, y + 30, p)
            c.drawLine(870, y + 30, 920, y, p)


# ================================================================== glitch
GL_COLS = [LIME, PURPLE, BLUE, GREEN, WHITE, YEL]


def glitch_k(t):
    for tg in GLITCHES:
        if tg - 0.05 <= t < tg + 0.1:
            return tg, 1 - abs(t - tg - 0.02) / 0.1
    return None, 0.0


def glitch_blocks(c, t, tg, k):
    f = int(t * FPS)
    for j in range(7):
        r = hrand(tg, f, j)
        x = hrand(tg, f, j, 1) * W
        y = hrand(tg, f, j, 2) * H * 0.8
        w = 80 + 300 * hrand(tg, f, j, 3)
        h = 40 + 220 * hrand(tg, f, j, 4)
        c.drawRect(skia.Rect.MakeXYWH(x - w / 2, y, w, h), fill(GL_COLS[int(r * len(GL_COLS)) % len(GL_COLS)],
                                                                 0.9 * clamp(k * 1.5)))


# ================================================================== draw
def draw(c, t, f):
    g = {}
    ts = E.src_at(t)
    src = Src(ts)
    c.clear(col("#30393A"))
    sp = split_now(t)
    split = sp is not None
    cm = cam(t, ts, split)
    bgc = bg_now(t)
    if bgc is not None:                        # "changed my background": a real swap behind the cut-out
        c.drawRect(skia.Rect.MakeWH(W, H), fill(bgc))
        person_layer(c, src, cm)
    else:
        draw_footage(c, src, cm)
        if BEH.w(1) - 0.05 <= t < BG.w(1) - 0.04:
            text_behind(c, t)
            person_layer(c, src, cm)
    if split:
        name, a, b = sp
        c.save()
        c.clipRect(skia.Rect.MakeWH(W, PANEL))
        c.drawRect(skia.Rect.MakeWH(W, PANEL), fill(WHITE))
        z = 1 + 0.045 * e_io(prog(t, a, b - a))
        c.translate(540, 480)
        c.scale(z, z)
        c.translate(-540, -480)
        SCENES[name](c, t, a, b)
        c.restore()
    else:
        draw_titles(c, t, head_top(t, ts))
        if BEH.w(2) <= t < BG.w(1) - 0.04:
            hand(c, "BEHIND ME", 540, 520, 44, prog(t, BEH.w(2) - 0.03, 0.3))
        if bgc is not None:
            dark = bgc in (YEL, WHITE, LIME)
            hand(c, "CHANGED MY", 540, TITLE_Y - fit("BACKGROUND")[1] - 36, 40, 1.0, color=INK if dark else WHITE)
            big_type(c, "BACKGROUND", 540, TITLE_Y, t, BG.w(3) - 0.05, color=INK if dark else YEL)
        cta(c, t)
    if not captions_demo(c, t):
        draw_subs(c, t, split)
    tg, k = glitch_k(t)
    if k > 0:
        glitch_blocks(c, t, tg, k)
        g["glitch"] = k
    if t < 0.08:
        g["flash"] = 0.5 * (1 - t / 0.08)
    for tt, _ in SWAPS:                         # background swaps: a soft flash, no glitch over the face
        if tt <= t < tt + 0.07:
            g["flash"] = max(g.get("flash", 0), 0.25 * (1 - (t - tt) / 0.07))
    return g


SHAKES += [(HOOK.w(7), 9), (DID.w(4), 10), (MUS.w(10), 10), (NOT.w(5), 8), (CTA.w(8), 10)]

_VIG = None


def post(rgb, g, f):
    global _VIG
    if _VIG is None or _VIG.shape[:2] != rgb.shape[:2]:
        h, w = rgb.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h * 0.45) / (h / 2)) ** 2)
        _VIG = (1 - 0.42 * np.clip(r - 0.45, 0, None) ** 1.4)[..., None].astype(np.float32)
    s = rgb.shape[1] / W
    out = rgb.astype(np.float32)
    k = g.get("glitch", 0)
    if k:
        sh = int(14 * k * s)
        out[..., 0] = np.roll(out[..., 0], sh, axis=1)
        out[..., 2] = np.roll(out[..., 2], -sh, axis=1)
        rng = np.random.default_rng(f)
        for _ in range(6):
            y0 = int(rng.uniform(0, out.shape[0] - 60 * s))
            hh = int(rng.uniform(10, 70) * s)
            out[y0:y0 + hh] = np.roll(out[y0:y0 + hh], int(rng.uniform(-80, 80) * s * k), axis=1)
    if g.get("flash"):
        out = out + (255 - out) * g["flash"]
    out *= _VIG
    out = np.clip(out, 0, 255).astype(np.uint8)
    return kit.grain(out, f, amt=0.014, scale=2)


TOTAL = E.TOTAL
FILM = kit.Film(draw, TOTAL, FPS, post=post, out_dir=OUT)
STILL_SRC += [E.src_at(x) for x in (HOOK.w(8), DID.w(2), REC1.w(3), CAPS.w(3), BEH.w(2), MUS.w(2))]


# ================================================================== audio
def sfx_list():
    S = []

    def a(t, kind, gain=-10, **kw):
        S.append(dict(t=t, kind=kind, gain_db=gain, **kw))

    for small, big, ts_, tb, te in TITLES:
        if big:
            a(tb, "typing", -17, dur=0.045 * len(big) + 0.1)
            a(tb + 0.045 * len(big), "pop", -15)
        if small:
            a(ts_, "swish", -17)
    for tg in GLITCHES:
        a(tg - 0.05, "glitch", -14)
        a(tg - 0.12, "whoosh", -16, dur=0.25)
    a(0.0, "impact", -9)
    a(HOOK.w(7), "impact", -11)
    a(DID.w(4), "impact", -10)
    a(REC1.w(2) - 0.05, "pop", -13)
    a(REC1.w(3), "click", -9)
    a(REC1.w(3) + 0.8, "ding", -16)
    for j in range(3):
        a(PME.w(j) - 0.05, "pop", -13)
    a(TOLD.w(2), "typing", -16, dur=max(0.4, TOLD.e - TOLD.w(2) - 0.1))
    a(TOLD.e - 0.05, "click", -10)
    a(CUT.w(2) - 0.05, "swish", -12)
    a(CUT.w(7) - 0.05, "click", -10)
    for j in range(4):
        a(CAPS.w(j) - 0.04, "pop", -12)
    a(BEH.w(1) - 0.05, "impact", -12)
    a(BEH.w(2), "swish", -15)
    for tt, _ in SWAPS:
        a(tt, "tick", -12)
    a(DROP_T - 0.6, "riser", -14, dur=0.6)
    a(DROP_T, "bass_drop", -12)
    a(MUS.we(5) - 0.08, "whoosh", -9, dur=0.4)          # "sound effects" -> the effects, right after the word
    a(MUS.we(5) + 0.2, "impact", -10)
    a(MUS.w(6) - 0.05, "click", -9)
    a(MUS.w(6), "sparkle", -14)
    a(NOCOPY, "impact", -11)
    for j in range(6):
        a(STL.w(4) - 0.05 + j * 0.13, "shutter", -17, pan=(j - 2.5) / 4)
    a(CMD.w(0), "typing", -15, dur=0.45)
    a(CMD.w(6) - 0.15, "ding", -13)
    for j in range(4):
        a(CMD.w(6) - 0.05 + j * 0.12, "pop", -14)
    a(NOT.w(0) + 0.35, "swish", -14)
    a(NOT.w(2) + 0.35, "swish", -14)
    a(CTA.w(8) - 0.04, "pop", -12)
    a(CTA.w(8), "typing", -15, dur=0.5)
    a(CTA.w(11) - 0.08, "swish", -11)
    a(CTA.w(11) + 0.2, "ding", -13)
    return S


MUSIC_DB, SFX_DB, DUCK_DB = -9, 0, -7


def build_audio():
    SR = ak.SR
    work = HERE / "work"
    voice = E.build_voice()
    n = len(voice)
    drop = int(DROP_T * SR)
    bed_a = ak.music_bed("retro_a", seconds=DROP_T + 2, intro_bars=0, seed=31)
    bed_b = ak.music_bed("retro_b", seconds=TOTAL - DROP_T + 2, intro_bars=0, seed=33)
    mus = np.zeros((n, 2), np.float32)
    la = np.stack([ak.filt(bed_a[:, ch], "low", 900) for ch in range(2)], 1)[:drop]
    la *= np.sqrt(np.mean(bed_a[:drop] ** 2) / (np.mean(la ** 2) + 1e-12)) * ak.db(-6)   # muffled until "music"
    mus[:len(la)] = la
    lb = bed_b[: n - drop]
    mus[drop:drop + len(lb)] = lb
    fi = int(0.4 * SR)
    mus[:fi] *= np.linspace(0, 1, fi)[:, None]
    mus *= ak.duck_gain(voice, DUCK_DB)[:, None]
    end = int((TOTAL - 0.05) * SR)
    fo = int(1.0 * SR)
    mus[end - fo:end] *= np.linspace(1, 0, fo)[:, None]
    mus[end:] = 0
    mus *= ak.db(MUSIC_DB)
    fx = np.zeros_like(voice)
    for s in sfx_list():
        kind = s["kind"]
        clip = ak.SFX[kind](s["dur"]) if "dur" in s and kind in ("whoosh", "riser", "typing") else ak.SFX[kind]()
        ak.place(fx, clip, max(0.0, s["t"]), s["gain_db"] + SFX_DB, s.get("pan", 0.0))
    for name, x in (("voice", voice), ("music", mus), ("sfx", fx)):
        ak.write_wav(work / f"stem_{name}.wav", x)
    out = voice + mus + fx
    peak = np.max(np.abs(out)) or 1
    if peak > 0.98:
        out = np.tanh(out / peak * 1.2) / math.tanh(1.2) * 0.98
    path = work / "mix.wav"
    ak.write_wav(path, out)
    print("->", path)
    return path


ak.MOODS.setdefault("retro_a", dict(bpm=96, scale="major", key="A", prog=[4, 3, 2, 1], drums="lofi", lead="keys",
                                     pad=True, sevenths=True))
ak.MOODS.setdefault("retro_b", dict(bpm=96, scale="major", key="A", prog=[4, 3, 2, 1], drums="four", lead="pluck",
                                     pad=True, sevenths=True, pump=True))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "stills":
        FILM.stills([float(x) for x in sys.argv[2:]])
    elif cmd == "sheet":
        ts = [float(x) for x in sys.argv[2:]] or [round(TOTAL * (i + 0.5) / 40, 2) for i in range(40)]
        FILM.sheet(ts, cols=8, scale=0.25, name="reel_sheet.png")
    elif cmd == "audio":
        build_audio()
    elif cmd == "render":
        pic = FILM.render(OUT / "picture.mp4")
        aud = build_audio()
        E.finish(pic, aud, OUT / "vibe40_ad.mp4")


if __name__ == "__main__":
    main()

