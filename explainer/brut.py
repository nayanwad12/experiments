"""Neo-brutalist UI kit on skia: flat colour, thick ink outlines, hard offset shadows,
chunky app windows, pills, arrows, checkmarks. Everything moves at a smooth 30 fps."""

import math
import os

import skia

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920

INK = 0x111111
CREAM = 0xFFFAF0
GRID = 0xECE3D2
WHITE = 0xFFFFFF
PERI = 0xC4C6FF
LIME = 0xE3F59B
BLUSH = 0xFFCFD8
ICE = 0xC8F0EC
BLUSH_D = 0xFF8FA6
PERI_D = 0x8E92F5

SW = 6      # outline width
SH = 12     # hard shadow offset

_TF = {}
FONTS = {"head": "SpaceGrotesk-Bold.ttf", "mono": "SpaceMono-Bold.ttf", "black": "Montserrat-Black.ttf"}


def tf(name):
    if name not in _TF:
        _TF[name] = skia.Typeface.MakeFromFile(os.path.join(HERE, "fonts", FONTS[name]))
    return _TF[name]


def col(h, a=255):
    return skia.Color((h >> 16) & 255, (h >> 8) & 255, h & 255, a)


def paint(color, a=255, stroke=0.0):
    p = skia.Paint(AntiAlias=True, Color=col(color, a))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeJoin(skia.Paint.kRound_Join)
        p.setStrokeCap(skia.Paint.kRound_Cap)
    return p


# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def eob(x, s=1.7):
    x = clamp(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def eoc(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def eio(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def pop(t, t0, d=0.35):
    return 0.0 if t < t0 else eob((t - t0) / d)


def slide(t, t0, d=0.4):
    return 0.0 if t < t0 else eoc((t - t0) / d)


# ---------------------------------------------------------------- transforms
def push(c, x=0.0, y=0.0, rot=0.0, sc=1.0):
    c.save()
    c.translate(x, y)
    if rot:
        c.rotate(rot)
    if isinstance(sc, tuple):
        c.scale(*sc)
    elif sc != 1:
        c.scale(sc, sc)


def popc(c):
    c.restore()


# ---------------------------------------------------------------- shapes
def rrect(x, y, w, h, r):
    return skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x - w / 2, y - h / 2, w, h), r, r)


def box(c, x, y, w, h, fill, r=22, sh=SH, sw=SW, shadow=INK):
    if sh:
        c.drawRRect(rrect(x + sh, y + sh, w, h, r), paint(shadow))
    c.drawRRect(rrect(x, y, w, h, r), paint(fill))
    if sw:
        c.drawRRect(rrect(x, y, w, h, r), paint(INK, stroke=sw))


def circle(c, x, y, r, fill, sh=8, sw=SW):
    if sh:
        c.drawCircle(x + sh, y + sh, r, paint(INK))
    c.drawCircle(x, y, r, paint(fill))
    if sw:
        c.drawCircle(x, y, r, paint(INK, stroke=sw))


def poly(c, pts, fill, sh=8, sw=SW):
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    p.close()
    if sh:
        c.save()
        c.translate(sh, sh)
        c.drawPath(p, paint(INK))
        c.restore()
    c.drawPath(p, paint(fill))
    if sw:
        c.drawPath(p, paint(INK, stroke=sw))


def font(name, size):
    return skia.Font(tf(name), size)


def tw(s, size, name="head"):
    return font(name, size).measureText(s)


def text(c, s, x, y, size, color=INK, name="head", align="c", a=255):
    """(x, y) = visual centre of the line (left edge if align='l', right if 'r')."""
    f = font(name, size)
    w = f.measureText(s)
    x0 = x - w / 2 if align == "c" else x if align == "l" else x - w
    c.drawString(s, x0, y + size * 0.35, f, paint(color, a))
    return w


def label(c, s, x, y, size, fill, color=INK, name="head", padx=0.55, pady=0.42, sh=8, sw=5, rot=0.0, sc=1.0,
          r=None):
    if sc <= 0.001:
        return
    w = tw(s, size, name) + size * padx * 2
    h = size * (1 + pady * 2)
    push(c, x, y, rot, sc)
    box(c, 0, 0, w, h, fill, r=h / 2 if r is None else r, sh=sh, sw=sw)
    text(c, s, 0, 0, size, color, name)
    popc(c)
    return w


def window(c, x, y, w, h, title, fill=WHITE, bar=PERI, sc=1.0):
    """App window with a title bar; returns nothing, caller draws content in page coords."""
    push(c, x, y, 0, sc)
    box(c, 0, 0, w, h, fill, r=26)
    rr = rrect(0, 0, w, h, 26)
    c.save()
    c.clipRRect(rr, doAntiAlias=True)
    c.drawRect(skia.Rect.MakeXYWH(-w / 2, -h / 2, w, 76), paint(bar))
    c.restore()
    c.drawLine(-w / 2, -h / 2 + 76, w / 2, -h / 2 + 76, paint(INK, stroke=SW))
    c.drawRRect(rr, paint(INK, stroke=SW))
    for i, dc in enumerate((BLUSH_D, LIME, ICE)):
        circle(c, -w / 2 + 44 + i * 42, -h / 2 + 38, 13, dc, sh=0, sw=4)
    text(c, title, -w / 2 + 180, -h / 2 + 38, 30, INK, "mono", align="l")
    popc(c)


def check(c, x, y, s=1.0, fill=LIME):
    circle(c, x, y, 26 * s, fill, sh=0, sw=4)
    p = skia.Path()
    p.moveTo(x - 11 * s, y + 1 * s)
    p.lineTo(x - 3 * s, y + 9 * s)
    p.lineTo(x + 12 * s, y - 9 * s)
    c.drawPath(p, paint(INK, stroke=6 * s))


def xmark(c, x, y, s=1.0, fill=BLUSH):
    box(c, x, y, 54 * s, 54 * s, fill, r=10 * s, sh=5, sw=4)
    for a, b in ((-1, 1), (1, -1)):
        c.drawLine(x - 12 * s, y + a * 12 * s * -1, x + 12 * s, y + b * 12 * s * -1, paint(INK, stroke=6 * s))


def arrow(c, pts, color=INK, w=10, head=30):
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    c.drawPath(p, paint(color, stroke=w))
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    a = math.atan2(y1 - y0, x1 - x0)
    tip = [(x1 + math.cos(a) * 8, y1 + math.sin(a) * 8),
           (x1 - math.cos(a - 0.5) * head, y1 - math.sin(a - 0.5) * head),
           (x1 - math.cos(a + 0.5) * head, y1 - math.sin(a + 0.5) * head)]
    poly(c, tip, color, sh=0, sw=0)


def cursor(c, x, y, s=1.0):
    pts = [(0, 0), (0, 120), (30, 92), (55, 145), (80, 133), (56, 82), (95, 80)]
    poly(c, [(x + px * s, y + py * s) for px, py in pts], WHITE, sh=6, sw=6)


def grid_bg(c, t, color=CREAM, line=GRID, step=72):
    c.drawPaint(paint(color))
    off = (t * 18) % step
    p = paint(line, stroke=3)
    x = -off
    while x < W:
        c.drawLine(x, 0, x, H, p)
        x += step
    y = -off
    while y < H:
        c.drawLine(0, y, W, y, p)
        y += step
