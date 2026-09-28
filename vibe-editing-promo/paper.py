"""Paper-cut drawing kit on top of skia: textured cutouts, soft layered shadows,
rough die-cut edges, torn strips, sticker-style lettering and stop-motion jitter."""

import math
import os
import random

import numpy as np
import skia
from scipy.ndimage import gaussian_filter

from timeline import W, H

HERE = os.path.dirname(os.path.abspath(__file__))


def rgb(h, a=255):
    return skia.Color((h >> 16) & 255, (h >> 8) & 255, h & 255, a)


PERI = 0xC4C6FF
LIME = 0xE3F59B
BLUSH = 0xFFCFD8
ICE = 0xC8F0EC
INK = 0x111111
PAPER = 0xFBF8F1
# slightly deeper tints of the brand colours, used only for depth layers
PERI_D = 0xA9ACF7
LIME_D = 0xCFE37A
BLUSH_D = 0xF9B3C1
ICE_D = 0xA5E0D9
BRAND = [PERI, LIME, BLUSH, ICE]


# ---------------------------------------------------------------- utilities
def R(*key):
    return random.Random(":".join(str(k) for k in key))


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def eob(x, s=1.9):
    x = clamp(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def eoc(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def eic(x):
    x = clamp(x)
    return x * x * x


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def pop(t, t0, d=0.28):
    """0 before t0, overshooting scale-in after."""
    return 0.0 if t < t0 else eob((t - t0) / d)


def beat_pulse(t, period=0.4, tau=0.09, offset=0.0):
    if t < offset:
        return 0.0
    return math.exp(-((t - offset) % period) / tau)


# ---------------------------------------------------------------- texture
def _make_texture(n=1024):
    rng = np.random.default_rng(11)

    def layer(sigma):
        a = gaussian_filter(rng.standard_normal((n, n)), sigma, mode="wrap")
        return a / (a.std() + 1e-9)

    tex = 0.965 + 0.018 * layer(0.7) + 0.012 * layer(4) + 0.018 * layer(40)
    img = np.clip(tex, 0.86, 1.0)
    rgba = np.empty((n, n, 4), np.uint8)
    rgba[..., :3] = (img * 255)[..., None].astype(np.uint8)
    rgba[..., 3] = 255
    surf = skia.Surface(rgba)
    c = surf.getCanvas()
    p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style)
    r = random.Random(5)
    for i in range(900):  # paper fibres
        x, y = r.uniform(0, n), r.uniform(0, n)
        a = r.uniform(0, math.tau)
        L = r.uniform(6, 26)
        p.setStrokeWidth(r.uniform(0.5, 1.3))
        v = r.choice([(0, 0, 0, 18), (255, 255, 255, 60)])
        p.setColor(skia.Color(*v))
        path = skia.Path()
        path.moveTo(x, y)
        path.quadTo(x + math.cos(a) * L / 2 + r.uniform(-3, 3), y + math.sin(a) * L / 2 + r.uniform(-3, 3),
                    x + math.cos(a) * L, y + math.sin(a) * L)
        c.drawPath(path, p)
    # re-wrap as a plain raster image: a snapshot of an array-backed surface is very slow to sample
    return skia.Image.fromarray(surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType))


def _premul(img):
    s = skia.Surface(img.width(), img.height())
    s.getCanvas().drawImage(img, 0, 0)
    return s.makeImageSnapshot()


TEX = _premul(_make_texture())
# build the image shader once: makeShader converts the whole texture on every call
TEX_SHADER = TEX.makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat, skia.SamplingOptions(skia.FilterMode.kLinear))


_PAINTS = {}


def paper_paint(color, seed=0, alpha=255):
    """Textured paper paint. Handing the image shader to skia-python is very slow (~300 ms), so we
    build one paint per colour and return cheap copies; per-shape texture variation comes from tdraw()."""
    key = (color, alpha)
    if key not in _PAINTS:
        p = skia.Paint(AntiAlias=True)
        p.setShader(TEX_SHADER)
        p.setColorFilter(skia.ColorFilters.Blend(rgb(color, alpha), skia.BlendMode.kModulate))
        _PAINTS[key] = p
    return skia.Paint(_PAINTS[key])


def tdraw(c, path, paint, seed=0):
    """drawPath with the paper texture shifted by a per-shape offset."""
    ox, oy = seed * 137 % 1024, seed * 311 % 1024
    c.save()
    c.translate(ox, oy)
    q = skia.Path(path)
    q.offset(-ox, -oy)
    c.drawPath(q, paint)
    c.restore()


# ---------------------------------------------------------------- context
class Ctx:
    def __init__(self, canvas, step, t_global=0.0):
        self.c = canvas
        self.step = step
        self.t = t_global
        self.rot = [0.0]
        self.sc = [1.0]

    def push(self, x=0.0, y=0.0, rot=0.0, sc=1.0, wob=0.0, seed=0):
        if wob:
            r = R("wob", seed, self.step)
            x += r.uniform(-1, 1) * 2.6 * wob
            y += r.uniform(-1, 1) * 2.6 * wob
            rot += r.uniform(-1, 1) * 1.0 * wob
        self.c.save()
        self.c.translate(x, y)
        if rot:
            self.c.rotate(rot)
        if isinstance(sc, tuple):
            self.c.scale(sc[0], sc[1])
            s = (abs(sc[0]) + abs(sc[1])) / 2
        else:
            if sc != 1:
                self.c.scale(sc, sc)
            s = abs(sc)
        self.rot.append(self.rot[-1] + rot)
        self.sc.append(self.sc[-1] * s)

    def pop(self):
        self.c.restore()
        self.rot.pop()
        self.sc.pop()

    def shadow(self, depth):
        if depth <= 0:
            return None
        a = math.radians(-self.rot[-1])
        s = max(self.sc[-1], 0.08)
        dx0, dy0 = 3.0 * depth, 7.0 * depth
        dx = (dx0 * math.cos(a) - dy0 * math.sin(a)) / s
        dy = (dx0 * math.sin(a) + dy0 * math.cos(a)) / s
        sig = (2.5 + 2.6 * depth) / s
        alpha = int(255 * min(0.42, 0.2 + 0.05 * depth))
        return skia.ImageFilters.DropShadow(dx, dy, sig, sig, skia.Color(17, 17, 30, alpha))


# ---------------------------------------------------------------- geometry
def rect_pts(cx, cy, w, h):
    return [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)]


def rrect_pts(cx, cy, w, h, r, n=5):
    r = min(r, w / 2, h / 2)
    pts = []
    corners = [(cx + w / 2 - r, cy - h / 2 + r, -90), (cx + w / 2 - r, cy + h / 2 - r, 0),
               (cx - w / 2 + r, cy + h / 2 - r, 90), (cx - w / 2 + r, cy - h / 2 + r, 180)]
    for (ox, oy, a0) in corners:
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    return pts


def ellipse_pts(cx, cy, rx, ry, n=40, a0=0.0):
    return [(cx + rx * math.cos(a0 + math.tau * i / n), cy + ry * math.sin(a0 + math.tau * i / n)) for i in range(n)]


def circ_pts(cx, cy, r, n=48):
    return ellipse_pts(cx, cy, r, r, n)


def star_pts(cx, cy, ro, ri, n=5, a0=-90.0):
    pts = []
    for i in range(n * 2):
        a = math.radians(a0 + 180 * i / n)
        r = ro if i % 2 == 0 else ri
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def sparkle_pts(cx, cy, r, pinch=0.22):
    pts = []
    for i in range(4):
        a = math.radians(-90 + 90 * i)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        b = a + math.radians(45)
        pts.append((cx + r * pinch * math.cos(b), cy + r * pinch * math.sin(b)))
    return pts


def rough(pts, seed, amp=2.0, seg=40.0, closed=True):
    r = R("rough", seed)
    out = []
    n = len(pts)
    for i in range(n if closed else n - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        L = math.hypot(x1 - x0, y1 - y0) or 1.0
        k = max(1, int(L / seg))
        nx, ny = -(y1 - y0) / L, (x1 - x0) / L
        for j in range(k):
            f = j / k
            o = r.uniform(-amp, amp)
            out.append((x0 + (x1 - x0) * f + nx * o, y0 + (y1 - y0) * f + ny * o))
    if not closed:
        out.append(pts[-1])
    return out


def path_of(pts, closed=True):
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    if closed:
        p.close()
    return p


def offset(pts, dx, dy):
    return [(x + dx, y + dy) for x, y in pts]


# ---------------------------------------------------------------- drawing
def paper(ctx, shape, color, seed=0, depth=1.0, amp=1.6, seg=40.0, outline=None, alpha=255):
    """Draw one cutout. shape = point list (gets rough die-cut edges) or skia.Path."""
    path = shape if isinstance(shape, skia.Path) else path_of(rough(shape, seed, amp, seg))
    if outline:
        oc, ow = outline
        po = paper_paint(oc, seed + 7, alpha)
        po.setStyle(skia.Paint.kStrokeAndFill_Style)
        po.setStrokeWidth(ow * 2)
        po.setStrokeJoin(skia.Paint.kRound_Join)
        f = ctx.shadow(depth)
        if f:
            po.setImageFilter(f)
        tdraw(ctx.c, path, po, seed)
        p = paper_paint(color, seed, alpha)
    else:
        p = paper_paint(color, seed, alpha)
        f = ctx.shadow(depth)
        if f:
            p.setImageFilter(f)
    tdraw(ctx.c, path, p, seed)
    return path


def torn(ctx, pts, color, seed=0, depth=2.0, edge=(0, 9), amp=10.0):
    """Torn paper: a white fibre core peeking out along the torn edge."""
    white = path_of(rough(pts, seed, amp, 13))
    p = paper_paint(PAPER, seed + 3)
    f = ctx.shadow(depth)
    if f:
        p.setImageFilter(f)
    tdraw(ctx.c, white, p, seed)
    col = path_of(rough(offset(pts, *edge), seed + 1, amp * 0.9, 13))
    tdraw(ctx.c, col, paper_paint(color, seed), seed)


def fill_bg(ctx, color, seed=0):
    ctx.c.drawPaint(paper_paint(color, seed))


def bg(ctx, base, a1, a2, seed=0, layout=0):
    """Scene background: base sheet plus two layered cutouts for depth."""
    fill_bg(ctx, base, seed)
    if layout == 0:
        paper(ctx, circ_pts(W + 40, 150, 330, 44), a2, seed + 1, depth=2, amp=4)
        torn(ctx, [(-90, H - 380), (W + 90, H - 520), (W + 90, H + 90), (-90, H + 90)], a1, seed + 2)
    elif layout == 1:
        paper(ctx, circ_pts(-60, H - 380, 300, 44), a2, seed + 1, depth=2, amp=4)
        torn(ctx, [(-90, -90), (W + 90, -90), (W + 90, 260), (-90, 380)], a1, seed + 2, edge=(0, -9))
    else:
        torn(ctx, [(-90, H - 300), (W + 90, H - 300), (W + 90, H + 90), (-90, H + 90)], a1, seed + 2)
        paper(ctx, circ_pts(W - 60, 260, 200, 40), a2, seed + 1, depth=2, amp=4)
        paper(ctx, circ_pts(90, 520, 90, 30), a1, seed + 5, depth=1.5, amp=3)


# ---------------------------------------------------------------- lettering
_TF = {}
FONTS = {"black": "Montserrat-Black.ttf", "bold": "Montserrat-Bold.ttf"}


def typeface(name):
    if name not in _TF:
        _TF[name] = skia.Typeface.MakeFromFile(os.path.join(HERE, "fonts", FONTS[name]))
    return _TF[name]


def glyphs(text, size, font="black", track=0.0):
    f = skia.Font(typeface(font), size)
    gs = f.textToGlyphs(text)
    ws = f.getWidths(gs)
    ps = [f.getPath(g) for g in gs]
    xs, x = [], 0.0
    for w in ws:
        xs.append(x)
        x += w + track * size
    total = x - track * size
    return ps, xs, ws, total


def text_width(text, size, font="black", track=0.0):
    return glyphs(text, size, font, track)[3]


def draw_text(ctx, text, x, y, size, fill=INK, back=PAPER, under=None, pad=0.1, rot=0.0, sc=1.0,
              seed=0, wob=1.0, maxw=1000.0, depth=2.0, anim=None, font="black", track=0.0, align="c",
              alpha=255):
    """Sticker-cut lettering: paper backing (die-cut outline), optional offset colour layer, ink letters.
    (x, y) is the visual centre of the line (or left edge if align='l')."""
    if sc <= 0.001 or not text:
        return
    ps, xs, ws, total = glyphs(text, size, font, track)
    if maxw and total > maxw:
        size *= maxw / total
        ps, xs, ws, total = glyphs(text, size, font, track)
    cap = 0.70 * size
    x0 = -total / 2 if align == "c" else 0.0
    ctx.push(x, y, rot, sc)
    items = []
    for i, (p, lx, w) in enumerate(zip(ps, xs, ws)):
        if p is None or p.isEmpty():
            continue
        jr = R("glyph", seed, i, ctx.step)
        dx = jr.uniform(-1, 1) * 1.6 * wob
        dy = jr.uniform(-1, 1) * 1.6 * wob
        dr = jr.uniform(-1, 1) * 1.8 * wob
        ds = 1.0
        if anim:
            ax, ay, ar, asc = anim(i)
            dx, dy, dr, ds = dx + ax, dy + ay, dr + ar, ds * asc
        if ds <= 0.001:
            continue
        items.append((p, x0 + lx + w / 2 + dx, dy, dr, ds, w, i))
    passes = []
    if back is not None:
        passes.append("back")
    if under is not None:
        passes.append("under")
    passes.append("fill")
    for ps_name in passes:
        for (p, cx, cy, dr, ds, w, i) in items:
            ctx.push(cx, cy, dr, ds)
            ctx.c.translate(-w / 2, cap / 2)
            if ps_name == "back":
                pt = paper_paint(back, seed + i, alpha)
                pt.setStyle(skia.Paint.kStrokeAndFill_Style)
                pt.setStrokeWidth(2 * pad * size)
                pt.setStrokeJoin(skia.Paint.kRound_Join)
                f = ctx.shadow(depth)
                if f:
                    pt.setImageFilter(f)
                tdraw(ctx.c, p, pt, seed)
            elif ps_name == "under":
                ctx.c.save()
                ctx.c.translate(size * 0.045, size * 0.05)
                tdraw(ctx.c, p, paper_paint(under, seed + 50 + i, alpha), seed + i)
                ctx.c.restore()
            else:
                pt = paper_paint(fill, seed + 90 + i, alpha)
                if back is None and depth > 0:
                    f = ctx.shadow(depth)
                    if f:
                        pt.setImageFilter(f)
                tdraw(ctx.c, p, pt, seed)
            ctx.pop()
    ctx.pop()
