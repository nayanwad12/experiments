"""diary: the ad take re-edited in the cozy film-diary style of the second reference clip.

Reference (6 s, measured): warm filmic grade, soft; every spoken word set in a soft condensed display serif
(pale butter #F6F39D, soft shadow), each word dropped into its own spot around the speaker and built up
word by word, then cleared; a scrapbook sticker layer (pale blue envelope with a red ribbon bow, hand-drawn
pink and cream stars) whose word swaps one at a time ("digital" -> "journal" -> "entry" -> "#1").
Here: Fraunces Soft (condensed) for the words; envelope, lined note, cassette and taped polaroids as
stickers; the room relit to a dim lamp-lit warm tone so the pale type reads; jump-cut zooms between phrases.
Same cut and 1.15x speed as reel.py (core.py). Meta-ad safe: nothing in the top 14 % or bottom 35 %.

    python3 diary.py sheet [t ...]    -> out/diary_sheet.png
    python3 diary.py render           -> out/vibe40_diary.mp4
"""

import math
import re
import sys
from pathlib import Path

import cv2
import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "reels" / "common"))
import audio_kit as ak  # noqa: E402
import core as E  # noqa: E402
import kit  # noqa: E402
from kit import clamp, e_back, e_in, e_io, e_out, fill, hrand, lerp, prog, stroke  # noqa: E402

cv2.setNumThreads(1)
W, H, FPS = 1080, 1920, 30
OUT = HERE / "out"
TOTAL = E.TOTAL
SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNone)
FONT_FILE = HERE.parent / "reels" / "fonts" / "FrauncesSoft-SemiBold.ttf"
TF = skia.Typeface.MakeFromFile(str(FONT_FILE))
SCALE_X = 0.76                                   # condensed, like the reference

BUTTER = "#F6F39D"
CREAM = "#FBF3C2"
PINK = "#F4B8CE"
SKY = "#C6DAE4"
RIBBON = "#8E1B22"
INKB = "#3A2A1C"                                 # warm dark brown for type on pastel grounds
PASTELS = ["#F4C9D6", "#F3EBB0", "#C9DCE6", "#CFE0C3"]


def col(c, a=1.0):
    r, g, b = kit.rgb(c)
    return skia.Color(r, g, b, int(255 * clamp(a)))


# ================================================================== grade: warm, dim, lamp-lit room
def _lut():
    x = np.arange(256, dtype=np.float32) / 255
    s = np.clip(x + 0.05 * np.sin(2 * math.pi * (x - 0.5)), 0, 1)
    r = 0.06 + 0.9 * s ** 0.96
    g = 0.055 + 0.84 * s
    b = 0.04 + 0.78 * s ** 1.06
    return np.ascontiguousarray(np.stack([(np.clip(c, 0, 1) * 255).astype(np.uint8) for c in (r, g, b)], 1)
                                .reshape(256, 1, 3))


LUT = _lut()
ROOM = np.array([0.60, 0.56, 0.45], np.float32)          # cream wall -> warm lamp-lit beige
_LAMP = None


def lamp():
    """warm pool of light from the upper left, falling off across the wall."""
    global _LAMP
    if _LAMP is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - 150) / 950) ** 2 + ((yy - 300) / 1200) ** 2)
        _LAMP = (1.25 - 0.55 * np.clip(r, 0, 1.3)).astype(np.float32)
    return _LAMP


def sk_img(rgb, a=None):
    out = cv2.cvtColor(rgb, cv2.COLOR_RGB2RGBA)
    if a is not None:
        out[..., 3] = a
    return skia.Image.fromarray(out, colorType=skia.kRGBA_8888_ColorType)


class Src:
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

    def _graded(self):
        def make():
            raw = E.frame_rgb(self.fi)
            p = cv2.LUT(raw, LUT)
            gray = cv2.cvtColor(cv2.cvtColor(p, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB)
            p = cv2.addWeighted(p, 0.86, gray, 0.14, 0)
            a = cv2.resize(E.alpha_small(self.fi), (W, H)).astype(np.float32) / 255
            a = a * a * (3 - 2 * a)
            m = (1 - a) * lamp()
            fac = cv2.merge([a + m * ROOM[ch] for ch in range(3)])
            return cv2.multiply(p, fac, dtype=cv2.CV_8U), (a * 255).astype(np.uint8), p
        return self._memo("g", make)

    def img(self):
        return self._memo("img", lambda: sk_img(self._graded()[0]))

    def person(self):
        return self._memo("person", lambda: sk_img(self._graded()[2], self._graded()[1]))

    def raw(self):
        return self._memo("raw", lambda: sk_img(E.frame_rgb(self.fi)))


# ================================================================== phrases
P = E.P
PH = [P("the video you are watching right now"), P("i didn't edit it my vibe editing system did"),
      P("i recorded one take on my phone"), P("pauses mistakes everything"),
      P("then i told it what i want in simple words"), P("it cut every pause down to the exact word"),
      P("it added these captions"), P("put text behind me"), P("and changed my background"),
      P("even the music and sound effects made from scratch no copyright"),
      P("and before exporting it showed me every key moment"), P("one command and it's ready for every platform"),
      P("no timeline no editing app"), P("just my system"), P("so if you want to learn my system"),
      P("tap the link below")]
DROP_T = PH[9].w(2)                                 # the music opens up on "music"


def phrase_start(k):
    return E.run_start(PH[k])


def phrase_end(k):
    return phrase_start(k + 1) if k + 1 < len(PH) else TOTAL + 1


# ================================================================== framing: jump-cut zooms between phrases
BASE_DY = 0


def cam(t, ts):
    fx, fy = E.face(ts)
    k = max([i for i, s in enumerate(E.RUN_STARTS) if s <= t + 1e-6] or [0])
    z = (1.0, 1.12)[k % 2] * (1 + 0.006 * (t - E.RUN_STARTS[k]))
    if t < 0.25:
        z *= lerp(1.08, 1.0, e_out(t / 0.25))
    return z, fx, fy, 0.0, BASE_DY


def apply(c, cm):
    z, fx, fy, dx, dy = cm
    c.translate(fx + dx, fy + dy)
    c.scale(z, z)
    c.translate(-fx, -fy)


# ================================================================== type
def font(size):
    f = skia.Font(TF, size)
    f.setScaleX(SCALE_X)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    f.setSubpixel(True)
    return f


def wmeasure(s, size):
    return font(size).measureText(s)


def word(c, s, x, y, size, k, anchor="l", color=BUTTER, maxw=None, seed=0, shadow=True):
    """one diary word: letters on a slightly bouncy baseline, popping in by k (0..1)."""
    if k <= 0 or not s:
        return
    if maxw:
        w0 = wmeasure(s, size)
        if w0 > maxw:
            size *= maxw / w0
    f = font(size)
    w = f.measureText(s)
    x0 = x if anchor == "l" else x - w if anchor == "r" else x - w / 2
    sc = lerp(0.82, 1.0, e_back(clamp(k)))
    a = clamp(k * 4)
    c.save()
    c.translate(x0 + w / 2, y - size * 0.3)
    c.scale(sc, sc)
    c.rotate((hrand(s, seed) - 0.5) * 4)
    c.translate(-(x0 + w / 2), -(y - size * 0.3))
    xx = x0
    for i, ch in enumerate(s):
        dy = (hrand(s, i, seed) - 0.5) * size * 0.05
        if shadow:
            c.drawString(ch, xx + 2, y + dy + 4, f, fill("#1A0F05", 0.45 * a, blur=size * 0.05))
        c.drawString(ch, xx, y + dy, f, fill(color, a))
        xx += f.measureText(ch)
    c.restore()


# slots: (x, baseline y, anchor, max width)  - all clear of the face, the top 14 % and the bottom 35 %
SLOT = dict(TL=(90, 455, "l", 430), TR=(990, 455, "r", 430), TC=(540, 455, "c", 900),
            L=(70, 830, "l", 270), R=(1010, 830, "r", 230), BC=(540, 1235, "c", 880),
            BL=(80, 1235, "l", 420), BR=(1000, 1235, "r", 420))

# scattered phrases: phrase index -> [(first word, last word, slot, size, text or None)]
SCATTER = {
    0: [(0, 0, "TL", 130, None), (1, 1, "TR", 150, None), (2, 3, "L", 120, None), (4, 4, "R", 110, None),
        (5, 6, "BC", 130, "right now")],
    1: [(0, 0, "TL", 150, None), (1, 1, "TR", 150, None), (2, 3, "BC", 140, "edit it")],
    2: [(0, 1, "TC", 140, "I recorded"), (2, 3, "L", 120, "one take"), (4, 6, "BC", 130, "on my phone")],
    3: [(0, 0, "TL", 130, "pauses"), (1, 1, "TR", 130, "mistakes"), (2, 2, "BC", 150, "everything")],
    5: [(0, 1, "TL", 130, "it cut"), (2, 3, "TR", 130, "every pause"), (4, 5, "L", 110, "down to"),
        (6, 8, "BC", 130, "the exact word")],
    6: [(0, 1, "TC", 140, "it added"), (2, 2, "L", 130, "these"), (3, 3, "BC", 150, "captions")],
    7: [(0, 0, "TL", 140, "put"), (2, 3, "BC", 140, "behind me")],
    8: [(0, 1, "TC", 130, "and changed"), (2, 2, "L", 130, "my"), (3, 3, "BC", 150, "background")],
    10: [(0, 1, "TL", 120, "and before"), (2, 2, "TR", 120, "exporting"), (3, 5, "BC", 130, "it showed me")],
    11: [(0, 1, "TC", 140, "one command"), (2, 3, "L", 120, "and it's"), (4, 4, "R", 110, "ready"),
         (5, 7, "BC", 130, "for every platform")],
    12: [(0, 1, "TC", 140, "no timeline"), (2, 4, "BC", 140, "no editing app")],
    14: [(0, 3, "TC", 130, "so if you want"), (4, 5, "L", 120, "to learn"), (6, 7, "BC", 140, "my system")],
}
# sticker phrases: phrase index -> (sticker, [(first word, text)])  the word on the sticker swaps
STICKER = {
    1: ("envelope", [(4, "my"), (5, "vibe"), (6, "editing"), (7, "system"), (8, "did")]),
    4: ("note", [(0, "then I told it"), (4, "what I want"), (7, "in simple words")]),
    9: ("cassette", [(0, "the music"), (3, "& sound effects"), (6, "from scratch"), (9, "no copyright")]),
    13: ("envelope", [(0, "just"), (1, "my system")]),
    15: ("envelope", [(0, "tap the link"), (3, "below")]),
}


def scatter_end(k):
    """scattered words clear when a sticker (or the polaroids) takes over inside the same phrase."""
    if k == 1:
        return PH[1].w(4) - 0.12
    if k == 10:
        return PH[10].w(6) - 0.05
    return phrase_end(k)


def draw_scatter(c, t, k, dark=False):
    if k not in SCATTER or not phrase_start(k) - 0.02 <= t < scatter_end(k):
        return
    p = PH[k]
    for j, (w0, w1, slot, size, txt) in enumerate(SCATTER[k]):
        t0 = p.w(w0) - 0.03
        s = txt or " ".join(E.WORDS[p.i0 + q]["d"].strip(".,?") for q in range(w0, w1 + 1)).lower()
        s = re.sub(r"\bi\b", "I", s)
        x, y, anc, mw = SLOT[slot]
        on_bg = dark and slot not in ("BC", "BL", "BR")       # chest slots sit on the black shirt: keep butter
        word(c, s, x, y, size, prog(t, t0, 0.14), anc, INKB if on_bg else BUTTER, mw, seed=k * 10 + j,
             shadow=not on_bg)


# ================================================================== stickers
def paper_noise():
    if not hasattr(paper_noise, "img"):
        g = np.random.default_rng(3)
        n = (g.standard_normal((256, 256)) * 10 + 235).clip(200, 255).astype(np.uint8)
        paper_noise.img = sk_img(cv2.cvtColor(n, cv2.COLOR_GRAY2RGB))
    return paper_noise.img


def paper(c, rect_path, color, a=1.0, shadow=0.35):
    sh = skia.Path(rect_path)
    sh.offset(5, 10)
    c.drawPath(sh, fill("#000000", shadow * a, blur=12))
    c.drawPath(rect_path, fill(color, a))
    c.save()
    c.clipPath(rect_path, skia.ClipOp.kIntersect, True)
    c.drawImageRect(paper_noise(), rect_path.getBounds(), SAMP,
                    skia.Paint(BlendMode=skia.BlendMode.kMultiply, Alphaf=0.35 * a))
    c.restore()


def star(c, x, y, r, color, k, rot=0.0, seed=0):
    """hand-drawn star sticker: wobbly outline, crayon hatch fill."""
    if k <= 0:
        return
    s = lerp(0.3, 1.0, e_back(clamp(k / 0.7)))
    c.save()
    c.translate(x, y)
    c.rotate(rot + 8 * math.sin(k * 3))
    c.scale(s, s)
    p = skia.Path()
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.45
        th = -math.pi / 2 + i * math.pi / 5
        rr *= 1 + (hrand(seed, i) - 0.5) * 0.18
        (p.moveTo if i == 0 else p.lineTo)(rr * math.cos(th), rr * math.sin(th))
    p.close()
    c.drawPath(p, fill(color))
    c.save()
    c.clipPath(p, skia.ClipOp.kIntersect, True)
    for i in range(-12, 13):
        c.drawLine(-r + i * r / 6, -r, -r + i * r / 6 + r, r, stroke("#FFFFFF", 2.2, 0.45))
    c.restore()
    c.drawPath(p, stroke("#4A3A30", 3.5, 0.85))
    c.restore()


def bow(c, x, y, s):
    p = stroke(RIBBON, s * 0.09)
    path = skia.Path()
    path.moveTo(x, y)
    path.cubicTo(x - s * 0.5, y - s * 0.45, x - s * 0.55, y + s * 0.25, x, y)
    path.cubicTo(x + s * 0.55, y - s * 0.45, x + s * 0.5, y + s * 0.25, x, y)
    c.drawPath(path, p)
    c.drawLine(x, y, x - s * 0.3, y + s * 0.55, p)
    c.drawLine(x, y, x + s * 0.32, y + s * 0.5, p)
    c.drawCircle(x, y, s * 0.06, fill(RIBBON))


ENV = (540, 405, 520, 270)                       # centre x, centre y, w, h (top band, clear of the face)


def envelope(c, t, k, text, t_text, dark_text=False):
    if k <= 0:
        return
    cx, cy, w, h = ENV
    s = lerp(0.6, 1.0, e_back(clamp(k / 0.6)))
    c.save()
    c.translate(cx, cy)
    c.rotate(-2 + 1.2 * math.sin(t * 1.3))
    c.scale(s, s)
    rect = skia.Path()
    rect.addRect(skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h))
    paper(c, rect, SKY, clamp(k * 3))
    flap = stroke("#9FB9C6", 3)
    c.drawLine(-w / 2, -h / 2, 0, h * 0.08, flap)
    c.drawLine(w / 2, -h / 2, 0, h * 0.08, flap)
    c.drawLine(-w / 2, h / 2, -w * 0.12, -h * 0.02, stroke("#AFC6D2", 2.5))
    c.drawLine(w / 2, h / 2, w * 0.12, -h * 0.02, stroke("#AFC6D2", 2.5))
    bow(c, 0, h * 0.22, 64)
    word(c, text, 0, -h * 0.02, 128, prog(t, t_text, 0.12), "c", BUTTER, w * 0.86, seed=len(text))
    c.restore()
    star(c, cx - w / 2 + 10, cy + h / 2 - 20, 58, PINK, clamp(k * 2), -12, 1)
    star(c, cx + w / 2 - 6, cy - h / 2 + 30, 50, CREAM, clamp(k * 2 - 0.3), 14, 2)


def note(c, t, k, text, t_text):
    if k <= 0:
        return
    cx, cy, w, h = 540, 405, 660, 265
    s = lerp(0.6, 1.0, e_back(clamp(k / 0.6)))
    c.save()
    c.translate(cx, cy)
    c.rotate(2.5)
    c.scale(s, s)
    rect = skia.Path()
    rect.addRect(skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h))
    paper(c, rect, "#FFFDF2", clamp(k * 3))
    for i in range(5):
        y = -h / 2 + 55 + i * 42
        c.drawLine(-w / 2 + 10, y, w / 2 - 10, y, stroke("#A9C7E8", 2, 0.8))
    c.drawLine(-w / 2 + 60, -h / 2, -w / 2 + 60, h / 2, stroke("#E8A0A8", 2.5, 0.9))
    c.drawRect(skia.Rect.MakeXYWH(-70, -h / 2 - 22, 140, 44), fill(PINK, 0.8))         # washi tape
    word(c, text, 30, 40, 104, prog(t, t_text, 0.12), "c", INKB, w - 120, seed=len(text), shadow=False)
    c.restore()


def cassette(c, t, k, text, t_text):
    if k <= 0:
        return
    cx, cy, w, h = 540, 405, 580, 290
    s = lerp(0.6, 1.0, e_back(clamp(k / 0.6)))
    c.save()
    c.translate(cx, cy)
    c.rotate(-3)
    c.scale(s, s)
    body = skia.Path()
    body.addRRect(kit.rrect(-w / 2, -h / 2, w, h, 26))
    paper(c, body, "#F2C6CF", clamp(k * 3))
    c.drawRRect(kit.rrect(-w / 2 + 30, -h / 2 + 26, w - 60, 120, 12), fill("#FFFDF2"))
    word(c, text, 0, -h / 2 + 118, 92, prog(t, t_text, 0.12), "c", INKB, w - 100, seed=len(text), shadow=False)
    c.drawRRect(kit.rrect(-150, 10, 300, 90, 45), fill("#5B4636"))
    for sx in (-95, 95):
        c.save()
        c.translate(sx, 55)
        c.rotate(t * 160)
        c.drawCircle(0, 0, 32, fill("#FFFDF2"))
        for i in range(6):
            a = i * math.pi / 3
            c.drawLine(0, 0, 26 * math.cos(a), 26 * math.sin(a), stroke("#5B4636", 4))
        c.restore()
    c.restore()
    star(c, cx + w / 2 - 10, cy + h / 2 - 30, 52, CREAM, clamp(k * 2 - 0.3), 10, 4)


def polaroid(c, src_ts, x, y, w, rot, k, label_seed=0):
    if k <= 0:
        return
    h = w * 1.18
    s = lerp(0.5, 1.0, e_back(clamp(k / 0.6)))
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.scale(s, s)
    frame = skia.Path()
    frame.addRect(skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h))
    paper(c, frame, "#FBF8EE", clamp(k * 3))
    pw = w - 30
    fx, fy = E.face(src_ts)
    sh = 760
    sr = skia.Rect.MakeXYWH(clamp(fx - sh / 2, 0, W - sh), clamp(fy - sh * 0.45, 0, H - sh), sh, sh)
    c.drawImageRect(Src(src_ts).img(), sr, skia.Rect.MakeXYWH(-pw / 2, -h / 2 + 15, pw, pw), SAMP)
    c.drawRect(skia.Rect.MakeXYWH(-45, -h / 2 - 16, 90, 32), fill(CREAM, 0.85))
    c.restore()


# ================================================================== the special beats
def text_behind(c, t):
    p = PH[7]
    if not p.w(1) - 0.04 <= t < phrase_end(7):
        return
    k = prog(t, p.w(1) - 0.04, 0.18)
    c.save()
    c.translate(540, 780)
    s = lerp(1.25, 1.0, e_out(k))
    c.scale(s, s)
    f = font(560)
    w = f.measureText("text")
    c.drawString("text", -w / 2 + 6, 10, f, fill("#1A0F05", 0.4 * clamp(k * 3), blur=16))
    c.drawString("text", -w / 2, 0, f, fill(BUTTER, clamp(k * 3)))
    c.restore()


def bg_swap(t):
    p = PH[8]
    if not p.w(1) - 0.04 <= t < phrase_end(8):
        return None
    n = int((t - p.w(1) + 0.04) / 0.22)
    return PASTELS[n % len(PASTELS)]


STILLS = []


def stills_beat(c, t):
    p = PH[10]
    if not p.w(6) - 0.05 <= t < phrase_end(10):
        return
    spots = [(200, 760, 250, -7), (880, 770, 230, 6), (540, 420, 250, 3)]
    for j, (x, y, w, r) in enumerate(spots):
        polaroid(c, STILLS[j], x, y, w, r, prog(t, p.w(6 + j) - 0.05, 0.3), j)
    word(c, "every key moment", 540, 1235, 130, prog(t, p.w(6) - 0.03, 0.14), "c", BUTTER, 880, seed=99)


def stickers(c, t):
    for k, (kind, chunks) in STICKER.items():
        a, b = phrase_start(k), phrase_end(k)
        if not a <= t < b:
            continue
        p = PH[k]
        cur, tc = chunks[0][1], p.w(chunks[0][0]) - 0.03
        for w0, txt in chunks:
            if t >= p.w(w0) - 0.03:
                cur, tc = txt, p.w(w0) - 0.03
        t_in = p.w(chunks[0][0]) - 0.12
        if k == 15:                              # the end card: the envelope stays to the last frame
            envelope(c, t, prog(t, t_in, 0.3), cur, tc)
            cta_arrows(c, t, p)
        elif kind == "envelope":
            envelope(c, t, prog(t, t_in, 0.3), cur, tc)
        elif kind == "note":
            note(c, t, prog(t, t_in, 0.3), cur, tc)
        elif kind == "cassette":
            cassette(c, t, prog(t, t_in, 0.3), cur, tc)


def cta_arrows(c, t, p):
    """'below': a hand-drawn arrow and the words pointing down at the ad button (kept above the bottom 35 %)."""
    kb = prog(t, p.w(3) - 0.05, 0.4)
    if kb <= 0:
        return
    pts = [(880, 620), (940, 760), (920, 900), (880, 1030), (860, 1120)]
    path = skia.Path()
    path.moveTo(*pts[0])
    for i in range(1, len(pts) - 1):
        mx, my = (pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2
        path.quadTo(pts[i][0], pts[i][1], mx, my)
    path.lineTo(*pts[-1])
    st = stroke(BUTTER, 8)
    if kb < 0.8:
        st.setPathEffect(skia.TrimPathEffect.Make(0, kb / 0.8))
    c.drawPath(path, st)
    if kb > 0.8:
        hk = e_out((kb - 0.8) / 0.2) * 44
        for sg in (-1, 1):
            a2 = math.atan2(1120 - 1030, 860 - 880) + math.pi + sg * 0.55
            c.drawLine(860, 1120, 860 + hk * math.cos(a2), 1120 + hk * math.sin(a2), stroke(BUTTER, 8))
    bob = 8 * math.sin((t - p.w(3)) * 6)
    word(c, "learn more", 540, 1235 + bob * 0.3, 140, prog(t, p.w(3) - 0.03, 0.15), "c", BUTTER, 760, seed=7)
    star(c, 230, 1080, 46, PINK, prog(t, p.w(3) + 0.15, 0.3), -10, 8)


# ================================================================== draw
def draw(c, t, f):
    g = {}
    ts = E.src_at(t)
    src = Src(ts)
    cm = cam(t, ts)
    c.clear(col("#2A2018"))
    sw = bg_swap(t)
    behind = PH[7].w(1) - 0.04 <= t < phrase_end(7)
    if sw:
        c.drawRect(skia.Rect.MakeWH(W, H), fill(sw))
    else:
        c.save()
        apply(c, cm)
        c.drawImageRect(src.img(), skia.Rect.MakeXYWH(0, 0, W, 24), skia.Rect.MakeXYWH(0, -400, W, 412), SAMP)
        c.drawImage(src.img(), 0, 0, SAMP)
        c.restore()
    if behind:
        text_behind(c, t)
    if sw or behind:
        c.save()
        apply(c, cm)
        c.drawImage(src.person(), 0, 0, SAMP)
        c.restore()
    k = max([i for i in range(len(PH)) if phrase_start(i) <= t + 1e-6] or [0])
    draw_scatter(c, t, k, dark=bool(sw))
    stickers(c, t)
    stills_beat(c, t)
    if 0 <= t < 0.06:
        g["flash"] = 0.3 * (1 - t / 0.06)
    return g


_VIG = None


def post(rgb, g, f):
    """film: soft bloom, halation on the highlights, vignette, grain."""
    global _VIG
    if _VIG is None or _VIG.shape[:2] != rgb.shape[:2]:
        h, w = rgb.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h * 0.45) / (h / 2)) ** 2)
        _VIG = (1 - 0.38 * np.clip(r - 0.4, 0, None) ** 1.4)[..., None].astype(np.float32)
    out = rgb.astype(np.float32)
    small = cv2.resize(rgb, (rgb.shape[1] // 6, rgb.shape[0] // 6), interpolation=cv2.INTER_AREA).astype(np.float32)
    soft = cv2.resize(cv2.GaussianBlur(small, (0, 0), 3), (rgb.shape[1], rgb.shape[0]))
    out = out * 0.86 + soft * 0.14                                  # dreamy softness
    hi = np.clip(soft - 170, 0, None)
    out += hi * np.array([0.45, 0.3, 0.12], np.float32)             # warm halation
    if g.get("flash"):
        out = out + (255 - out) * g["flash"]
    out *= _VIG
    out = np.clip(out, 0, 255).astype(np.uint8)
    return kit.grain(out, f, amt=0.018, scale=2)


FILM = kit.Film(draw, TOTAL, FPS, post=post, out_dir=OUT)
STILLS += [E.src_at(x) for x in (PH[0].w(3), PH[5].w(2), PH[7].w(2))]


# ================================================================== audio
def sfx_list():
    S = []

    def a(t, kind, gain=-14, **kw):
        S.append(dict(t=t, kind=kind, gain_db=gain, **kw))

    for k, (kind, chunks) in STICKER.items():
        p = PH[k]
        a(p.w(chunks[0][0]) - 0.12, "pop", -15)
        a(p.w(chunks[0][0]) - 0.05, "sparkle", -20)
        for w0, _ in chunks[1:]:
            a(p.w(w0) - 0.05, "swish", -19)
        if kind == "note":
            a(p.w(0), "typing", -22, dur=max(0.3, p.e - p.s))
    a(PH[7].w(1) - 0.04, "impact", -17)
    for j in range(5):
        a(PH[8].w(1) - 0.04 + j * 0.22, "tick", -18)
    for j in range(3):
        a(PH[10].w(6 + j) - 0.05, "shutter", -18)
    a(DROP_T - 0.5, "riser", -19, dur=0.5)
    a(PH[15].w(3) - 0.05, "swish", -15)
    a(PH[15].w(3) + 0.3, "ding", -18)
    return S


def build_audio():
    SR = ak.SR
    work = HERE / "work"
    voice = E.build_voice()
    n = len(voice)
    ak.MOODS.setdefault("cozy", dict(bpm=84, scale="major", key="F", prog=[4, 3, 2, 1], drums="lofi", lead="keys",
                                     pad=True, sevenths=True))
    bed = ak.music_bed("cozy", seconds=TOTAL + 2, intro_bars=0, seed=41)[:n]
    bed = np.pad(bed, ((0, max(0, n - len(bed))), (0, 0)))
    low = np.stack([ak.filt(bed[:, ch], "low", 700) for ch in range(2)], 1)
    low *= np.sqrt(np.mean(bed ** 2) / (np.mean(low ** 2) + 1e-12)) * ak.db(-5)
    env = np.zeros(n, np.float32)
    d0 = int(DROP_T * SR)
    k = int(0.35 * SR)
    env[d0:] = 1
    env[d0 - k:d0] = np.linspace(0, 1, k)
    mus = low * (1 - env[:, None]) + bed * env[:, None]               # the same bed opens up on "music"
    fi = int(0.4 * SR)
    mus[:fi] *= np.linspace(0, 1, fi)[:, None]
    mus *= ak.duck_gain(voice, -7)[:, None]
    end = int((TOTAL - 0.05) * SR)
    fo = int(1.2 * SR)
    mus[end - fo:end] *= np.linspace(1, 0, fo)[:, None]
    mus[end:] = 0
    mus *= ak.db(-8)
    fx = np.zeros_like(voice)
    for s in sfx_list():
        kind = s["kind"]
        clip = ak.SFX[kind](s["dur"]) if "dur" in s and kind in ("whoosh", "riser", "typing") else ak.SFX[kind]()
        ak.place(fx, clip, max(0.0, s["t"]), s["gain_db"], s.get("pan", 0.0))
    for name, x in (("voice", voice), ("music", mus), ("sfx", fx)):
        ak.write_wav(work / f"diary_stem_{name}.wav", x)
    out = voice + mus + fx
    peak = np.max(np.abs(out)) or 1
    if peak > 0.98:
        out = np.tanh(out / peak * 1.2) / math.tanh(1.2) * 0.98
    path = work / "diary_mix.wav"
    ak.write_wav(path, out)
    print("->", path)
    return path


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "stills":
        FILM.stills([float(x) for x in sys.argv[2:]])
    elif cmd == "sheet":
        ts = [float(x) for x in sys.argv[2:]] or [round(TOTAL * (i + 0.5) / 40, 2) for i in range(40)]
        FILM.sheet(ts, cols=8, scale=0.25, name="diary_sheet.png")
    elif cmd == "audio":
        build_audio()
    elif cmd == "render":
        pic = FILM.render(OUT / "diary_picture.mp4")
        aud = build_audio()
        E.finish(pic, aud, OUT / "vibe40_diary.mp4")


if __name__ == "__main__":
    main()
