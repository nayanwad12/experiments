"""Claymation renderer: any skia path becomes a lit plasticine object.

Height field = blurred silhouette (pillowy) + hand-made lumps + fine grain, shaded with a
fixed top-left key light in float precision, plus soft contact shadows on the set."""

import math
import os
import random

import numpy as np
import skia
from scipy.ndimage import gaussian_filter

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920

PERI = (196, 198, 255)
LIME = (227, 245, 155)
BLUSH = (255, 207, 216)
ICE = (200, 240, 236)
INK = (38, 36, 44)          # clay is never pure black
CREAM = (250, 244, 232)
BLUSH_D = (250, 150, 172)
PERI_D = (150, 154, 240)

_L = np.array([-0.55, -0.75, 0.9])
LIGHT = _L / np.linalg.norm(_L)
_H = LIGHT + np.array([0, 0, 1.0])
HALF = _H / np.linalg.norm(_H)


def R(*k):
    return random.Random(":".join(map(str, k)))


def _noise(n, sigma, seed):
    a = gaussian_filter(np.random.default_rng(seed).standard_normal((n, n)), sigma, mode="wrap")
    return (a / a.std()).astype(np.float32)


NF = 512
FINE = _noise(NF, 1.1, 1)
LUMP = _noise(NF, 18, 2)
PRINT = _noise(NF, 3.5, 3)   # fingerprint-ish mid frequency


def _crop(field, x0, y0, w, h):
    ys = (np.arange(h) + y0) % NF
    xs = (np.arange(w) + x0) % NF
    return field[np.ix_(ys, xs)]


_WHITE = skia.Paint(AntiAlias=True, Color=skia.ColorWHITE)


def clay_sprite(path, color, seed=0, soft=10.0, depth=24.0, gloss=0.2, grain=1.0, drift=0):
    """path in device coords -> (premultiplied skia.Image, x0, y0)."""
    b = path.computeTightBounds()
    pad = int(soft * 2 + 6)
    x0, y0 = int(math.floor(b.left())) - pad, int(math.floor(b.top())) - pad
    w, h = int(math.ceil(b.width())) + 2 * pad, int(math.ceil(b.height())) + 2 * pad
    if w <= 2 or h <= 2 or w * h > 3_000_000:
        return None, 0, 0
    surf = skia.Surface(w, h)
    c = surf.getCanvas()
    c.clear(skia.ColorTRANSPARENT)
    c.translate(-x0, -y0)
    c.drawPath(path, _WHITE)
    a = surf.makeImageSnapshot().toarray()[..., 3].astype(np.float32) / 255.0
    hgt = np.clip(gaussian_filter(a, soft), 0, 1) ** 0.5 * depth
    ox, oy = seed * 131 + drift, seed * 197
    hgt += grain * (0.05 * _crop(FINE, ox, oy, w, h) + 1.1 * _crop(LUMP, ox, oy, w, h)
                    + 0.13 * _crop(PRINT, ox + 50, oy + 90, w, h))
    gy, gx = np.gradient(hgt)
    inv = 1.0 / np.sqrt(gx * gx + gy * gy + 1.0)
    nx, ny, nz = -gx * inv, -gy * inv, inv
    ndl = np.clip(nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2], 0, None)
    shade = 0.42 + 0.58 * ndl / LIGHT[2]
    ndh = np.clip(nx * HALF[0] + ny * HALF[1] + nz * HALF[2], 0, 1)
    spec = gloss * ndh ** 22
    occl = 0.8 + 0.2 * np.clip(hgt / depth, 0, 1)
    col = np.array(color, np.float32) / 255.0
    rgb = np.clip(col[None, None, :] * (shade * occl)[..., None] + spec[..., None], 0, 1)
    out = np.empty((h, w, 4), np.uint8)
    out[..., :3] = (rgb * a[..., None] * 255).astype(np.uint8)
    out[..., 3] = (a * 255).astype(np.uint8)
    return skia.Image.fromarray(out, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType), x0, y0


# ---------------------------------------------------------------- shapes (local coords)
def circle(r, x=0.0, y=0.0):
    p = skia.Path()
    p.addCircle(x, y, r)
    return p


def rrect(w, h, r, x=0.0, y=0.0):
    p = skia.Path()
    p.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x - w / 2, y - h / 2, w, h), r, r))
    return p


def poly(pts, round_=0.0):
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    p.close()
    return inflate(p, round_) if round_ else p


def star(ro, ri, n=5, round_=8.0):
    pts = []
    for i in range(n * 2):
        a = math.radians(-90 + 180 * i / n)
        r = ro if i % 2 == 0 else ri
        pts.append((r * math.cos(a), r * math.sin(a)))
    return poly(pts, round_)


def sparkle(r, round_=5.0):
    pts = []
    for i in range(8):
        a = math.radians(-90 + 45 * i)
        rr = r if i % 2 == 0 else r * 0.24
        pts.append((rr * math.cos(a), rr * math.sin(a)))
    return poly(pts, round_)


def ring(ro, ri):
    p = skia.Path()
    p.addCircle(0, 0, ro)
    p.addCircle(0, 0, ri, skia.PathDirection.kCCW)
    p.setFillType(skia.PathFillType.kEvenOdd)
    return p


def union(*paths):
    out = paths[0]
    for q in paths[1:]:
        out = skia.Op(out, q, skia.kUnion_PathOp)
    return out


def inflate(p, amount):
    sp = skia.Paint(AntiAlias=True)
    sp.setStyle(skia.Paint.kStrokeAndFill_Style)
    sp.setStrokeWidth(amount * 2)
    sp.setStrokeJoin(skia.Paint.kRound_Join)
    out = skia.Path()
    sp.getFillPath(p, out)
    return out


_TF = None


def glyphs(text, size):
    """list of (path centred on its own glyph box, x centre offset, advance) + total width."""
    global _TF
    if _TF is None:
        _TF = skia.Typeface.MakeFromFile(os.path.join(HERE, "fonts", "Montserrat-Black.ttf"))
    f = skia.Font(_TF, size)
    gs = f.textToGlyphs(text)
    ws = f.getWidths(gs)
    total = sum(ws)
    out, x = [], -total / 2
    cap = size * 0.70
    for g, wd in zip(gs, ws):
        p = f.getPath(g)
        if p is not None and not p.isEmpty():
            p.offset(-wd / 2, cap / 2)
            out.append((inflate(p, size * 0.018), x + wd / 2, wd))
        x += wd
    return out, total


# ---------------------------------------------------------------- scene drawing
class Set:
    """One frame of the stop-motion set."""

    def __init__(self, canvas, step):
        self.c = canvas
        self.step = step

    def obj(self, path, color, x=0.0, y=0.0, rot=0.0, sx=1.0, sy=1.0, seed=0, lift=0.0, soft=None, depth=None,
            gloss=0.2, boil=1.0, shadow=True):
        if sx <= 0.01 or sy <= 0.01:
            return
        r = R("boil", seed, self.step)
        x += r.uniform(-1.6, 1.6) * boil
        y += r.uniform(-1.6, 1.6) * boil
        rot += r.uniform(-0.9, 0.9) * boil
        s = r.uniform(-0.012, 0.012) * boil
        m = skia.Matrix()
        m.setTranslate(x, y)
        m.preRotate(rot)
        m.preScale(sx * (1 + s), sy * (1 - s))
        dp = skia.Path(path)
        dp.transform(m)
        b = dp.computeTightBounds()
        size = min(b.width(), b.height())
        if soft is None:
            soft = max(5.0, min(22.0, size * 0.12))
        if depth is None:
            depth = soft * 2.0
        if shadow:
            for (dx, dy, sig, al) in ((10 + 50 * lift, 18 + 80 * lift, 14 + 18 * lift, 80 - 40 * lift),
                                      (3 + 30 * lift, 6 + 50 * lift, 4 + 14 * lift, 120 - 90 * lift)):
                sp = skia.Paint(AntiAlias=True, Color=skia.Color(40, 20, 45, int(max(0, al))))
                sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, sig))
                self.c.save()
                self.c.translate(dx, dy)
                self.c.drawPath(dp, sp)
                self.c.restore()
        img, x0, y0 = clay_sprite(dp, color, seed, soft, depth, gloss, drift=self.step % 3)
        if img is not None:
            self.c.drawImage(img, x0, y0)

    def word(self, text, x, y, size, colors, anim=None, seed=0, **kw):
        """anim(i, n) -> (dx, dy, rot, sx, sy, lift) or None to hide the letter."""
        gl, total = glyphs(text, size)
        for i, (p, cx, wd) in enumerate(gl):
            st = (0, 0, 0, 1, 1, 0) if anim is None else anim(i, len(gl))
            if st is None:
                continue
            dx, dy, rot, sx, sy, lift = st
            self.obj(p, colors[i % len(colors)], x + cx + dx, y + dy, rot, sx, sy, seed=seed + i, lift=lift, **kw)


def backdrop(c, color, step):
    """Seamless-paper sweep lit by a soft box, with a little per-frame exposure flicker."""
    r, g, b = color
    k = 1 + R("flick", step).uniform(-0.025, 0.025)
    cc = lambda f: skia.Color(*(int(min(255, v * f * k)) for v in (r, g, b)))  # noqa: E731
    p = skia.Paint()
    p.setShader(skia.GradientShader.MakeRadial((W * 0.42, H * 0.36), 1500, [cc(1.04), cc(0.97), cc(0.78)],
                                               [0.0, 0.5, 1.0]))
    c.drawPaint(p)


def clamp_(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x
