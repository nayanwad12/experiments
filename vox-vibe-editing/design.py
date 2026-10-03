"""The Vox "mixed media" design system as a skia drawing kit.

Tokens (from the vox-animation skill's mixed style):
  - flat bold colour fields: warm yellow, off-white paper, deep navy, coral accent
  - archival photo cutouts: halftone-printed objects with rough white paper borders and soft drop shadows
  - paper grain + halftone dot textures, torn edges, tape strips
  - black hand-drawn marker annotations (circles, underlines, arrows) that draw themselves
  - abstract data graphics and flat UI shapes; text kept to short archival labels
  - motion: quick ease-out entrances with overshoot, slow push-ins, whip-pans hidden in motion blur
"""

import math
import os
import random

import numpy as np
import skia
from scipy.ndimage import binary_fill_holes, distance_transform_edt, gaussian_filter, shift as nd_shift

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30

# ---------------------------------------------------------------- tokens
YELLOW = 0xF7C948
CREAM = 0xF2ECDF
NAVY = 0x1E2B4D
CORAL = 0xEF6351
INK = 0x161514
WHITE = 0xFCFAF5
TEAL = 0x5FB3A8       # rare secondary accent (UI chips only)
NAVY_L = 0x2E3E66
YELLOW_D = 0xE9B52E
CUT_INK = (30, 28, 26)        # halftone ink for cutouts
CUT_PAPER = (234, 227, 212)   # newsprint tone for cutouts


def rgb(h, a=255):
    return skia.Color((h >> 16) & 255, (h >> 8) & 255, h & 255, a)


def font(name, size):
    return skia.Font(_TF[name], size)


_TF = {k: skia.Typeface.MakeFromFile(os.path.join(HERE, "fonts", f)) for k, f in
       (("black", "Montserrat-Black.ttf"), ("mono", "SpaceMono-Bold.ttf"), ("grotesk", "SpaceGrotesk-Bold.ttf"))}


# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def eob(x, s=1.7):           # ease-out-back: snappy overshoot
    x = clamp(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def eoc(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def eic(x):
    x = clamp(x)
    return x ** 3


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def prog(t, t0, d):
    return clamp((t - t0) / d)


def pop(t, t0, d=0.32):
    return 0.0 if t < t0 else eob((t - t0) / d)


def R(*key):
    return random.Random(":".join(str(k) for k in key))


# ---------------------------------------------------------------- textures
def _grain(n=1024):
    rng = np.random.default_rng(7)

    def layer(s):
        a = gaussian_filter(rng.standard_normal((n, n)), s, mode="wrap")
        return a / (a.std() + 1e-9)

    g = np.clip(0.97 + 0.02 * layer(0.8) + 0.012 * layer(5) + 0.015 * layer(60), 0.85, 1.0)
    return g


GRAIN = _grain()


def _bg_array(color, w, h, seed=0):
    """Flat colour field + paper grain + a halftone dot gradient pooling in two corners."""
    r, g, b = (color >> 16) & 255, (color >> 8) & 255, color & 255
    base = np.array([r, g, b], np.float32)
    gy = np.tile(GRAIN, (h // 1024 + 1, w // 1024 + 1))[:h, :w]
    img = base[None, None, :] * gy[..., None]
    # halftone dots, density rising toward top-left and bottom-right
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cell = 16.0
    a = math.radians(45)
    u = (xx * math.cos(a) + yy * math.sin(a)) / cell
    v = (-xx * math.sin(a) + yy * math.cos(a)) / cell
    d = np.hypot(u - np.floor(u) - 0.5, v - np.floor(v) - 0.5)
    rr = np.random.default_rng(seed)
    c1 = (rr.uniform(-0.1, 0.2) * w, rr.uniform(-0.1, 0.15) * h)
    c2 = (rr.uniform(0.8, 1.1) * w, rr.uniform(0.85, 1.1) * h)
    k = np.maximum(np.exp(-((xx - c1[0]) ** 2 + (yy - c1[1]) ** 2) / (2 * (0.33 * w) ** 2)),
                   np.exp(-((xx - c2[0]) ** 2 + (yy - c2[1]) ** 2) / (2 * (0.36 * w) ** 2)))
    rad = 0.42 * np.sqrt(k)
    m = np.clip((rad - d) / 0.05 + 0.5, 0, 1)
    lum = base.mean()
    tint = base * (0.84 if lum > 110 else 1.25)
    img = img * (1 - m[..., None] * 0.55) + np.clip(tint, 0, 255)[None, None, :] * gy[..., None] * (m[..., None] * 0.55)
    out = np.empty((h, w, 4), np.uint8)
    out[..., :3] = np.clip(img, 0, 255)
    out[..., 3] = 255
    return out


_BG = {}


def bg_image(color, seed=0):
    key = (color, seed)
    if key not in _BG:
        _BG[key] = skia.Image.fromarray(_bg_array(color, W + 400, H + 400, seed), colorType=skia.kRGBA_8888_ColorType)
    return _BG[key]


def draw_bg(c, color, seed=0):
    c.drawImage(bg_image(color, seed), -200, -200)


def _tex_shader():
    a = np.empty((1024, 1024, 4), np.uint8)
    a[..., :3] = (GRAIN * 255)[..., None]
    a[..., 3] = 255
    img = skia.Image.fromarray(a, colorType=skia.kRGBA_8888_ColorType)
    s = skia.Surface(1024, 1024)
    s.getCanvas().drawImage(img, 0, 0)
    return s.makeImageSnapshot().makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat,
                                            skia.SamplingOptions(skia.FilterMode.kLinear))


TEX = _tex_shader()
_PAINTS = {}


def paper_paint(color, alpha=255):
    key = (color, alpha)
    if key not in _PAINTS:
        p = skia.Paint(AntiAlias=True)
        p.setShader(TEX)
        p.setColorFilter(skia.ColorFilters.Blend(rgb(color, alpha), skia.BlendMode.kModulate))
        _PAINTS[key] = p
    return skia.Paint(_PAINTS[key])


def shadow(depth=1.0, rot=0.0, scale=1.0):
    a = math.radians(-rot)
    s = max(scale, 0.1)
    dx0, dy0 = 3.0 * depth, 8.0 * depth
    dx = (dx0 * math.cos(a) - dy0 * math.sin(a)) / s
    dy = (dx0 * math.sin(a) + dy0 * math.cos(a)) / s
    sig = (3 + 4 * depth) / s
    return skia.ImageFilters.DropShadow(dx, dy, sig, sig, skia.Color(15, 18, 35, int(255 * 0.34)))


# ---------------------------------------------------------------- geometry
def rough_poly(pts, seed, amp=3.0, step=16):
    """Subdivide a polygon and jitter it into a hand-cut paper edge."""
    r = R("rough", seed)
    out = []
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        L = math.hypot(x1 - x0, y1 - y0)
        k = max(1, int(L / step))
        for j in range(k):
            t = j / k
            out.append((x0 + (x1 - x0) * t + r.uniform(-amp, amp), y0 + (y1 - y0) * t + r.uniform(-amp, amp)))
    return out


def path_of(pts, close=True):
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    if close:
        p.close()
    return p


def rect_pts(cx, cy, w, h):
    return [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)]


def smooth_path(pts):
    """Catmull-Rom through points -> cubic path."""
    p = skia.Path()
    p.moveTo(*pts[0])
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        p.cubicTo(*c1, *c2, *p2)
    return p


# ---------------------------------------------------------------- transform stack
class Cam:
    """Tiny transform helper that tracks rotation/scale so baked-in shadows stay plausible."""

    def __init__(self, c):
        self.c = c

    def __call__(self, x=0, y=0, rot=0, sc=1.0):
        return _Push(self.c, x, y, rot, sc)


class _Push:
    def __init__(self, c, x, y, rot, sc):
        self.c, self.a = c, (x, y, rot, sc)

    def __enter__(self):
        x, y, rot, sc = self.a
        self.c.save()
        self.c.translate(x, y)
        if rot:
            self.c.rotate(rot)
        if isinstance(sc, tuple):
            self.c.scale(*sc)
        elif sc != 1:
            self.c.scale(sc, sc)
        return self.c

    def __exit__(self, *a):
        self.c.restore()


# ---------------------------------------------------------------- paper pieces
def paper_rect(c, cx, cy, w, h, color, seed=0, depth=1.0, amp=2.5, rot=0.0):
    p = paper_paint(color)
    if depth:
        p.setImageFilter(shadow(depth, rot))
    c.drawPath(path_of(rough_poly(rect_pts(cx, cy, w, h), seed, amp)), p)


def paper_rrect(c, cx, cy, w, h, r, color, depth=1.0, rot=0.0, alpha=255):
    p = paper_paint(color, alpha)
    if depth:
        p.setImageFilter(shadow(depth, rot))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - w / 2, cy - h / 2, w, h), r, r), p)


def tape(c, cx, cy, w=150, h=46, rot=0.0, seed=0):
    r = R("tape", seed)
    pts = []
    for x in np.linspace(-w / 2, w / 2, 8):
        pts.append((x, -h / 2 + r.uniform(-1, 1)))
    for y in np.linspace(-h / 2, h / 2, 5):
        pts.append((w / 2 + r.uniform(-5, 5), y))
    for x in np.linspace(w / 2, -w / 2, 8):
        pts.append((x, h / 2 + r.uniform(-1, 1)))
    for y in np.linspace(h / 2, -h / 2, 5):
        pts.append((-w / 2 + r.uniform(-5, 5), y))
    with Cam(c)(cx, cy, rot):
        p = paper_paint(0xEDE6CF, 200)
        c.drawPath(path_of(pts), p)


def text_w(s, f):
    return f.measureText(s)


def text(c, s, x, y, f, color=INK, align="center", alpha=255):
    w = f.measureText(s)
    dx = {"center": -w / 2, "left": 0, "right": -w}[align]
    c.drawString(s, x + dx, y, f, skia.Paint(AntiAlias=True, Color=rgb(color, alpha)))


def tag(c, s, cx, cy, size=46, bg=WHITE, fg=INK, face="mono", rot=0.0, sc=1.0, seed=0, padx=26, pady=18,
        depth=1.0):
    """Archival paper label with typewritten text."""
    if sc <= 0.001:
        return
    f = font(face, size)
    w = f.measureText(s) + 2 * padx
    h = size * 0.95 + 2 * pady
    with Cam(c)(cx, cy, rot, sc):
        paper_rect(c, 0, 0, w, h, bg, seed, depth, amp=2.0, rot=rot)
        text(c, s, 0, size * 0.36, f, fg)


def highlight(c, x0, y0, x1, y1, t, color=YELLOW, alpha=235, seed=0):
    """Highlighter swipe from left to right, drawn behind text."""
    if t <= 0:
        return
    r = R("hl", seed)
    xe = lerp(x0, x1, eoc(t))
    pts = [(x0 - 6, y0 + r.uniform(-3, 3)), (xe, y0 + r.uniform(-4, 4)), (xe + 4, y1 + r.uniform(-4, 4)),
           (x0 - 2, y1 + r.uniform(-3, 3))]
    p = skia.Paint(AntiAlias=True, Color=rgb(color, alpha))
    c.drawPath(path_of(pts), p)


# ---------------------------------------------------------------- marker annotations
def marker(c, pts, t, width=11, color=INK, alpha=255, smooth_=True):
    """A felt-marker stroke that draws itself along pts (t: 0..1)."""
    if t <= 0:
        return
    path = smooth_path(pts) if smooth_ else path_of(pts, False)
    meas = skia.PathMeasure(path, False)
    L = meas.getLength()
    seg = skia.Path()
    meas.getSegment(0, L * clamp(t), seg, True)
    p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=width, Color=rgb(color, alpha),
                   StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join)
    c.drawPath(seg, p)
    # dry-ink streak inside the stroke
    p2 = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=width * 0.28,
                    Color=skia.Color(255, 255, 255, 38), StrokeCap=skia.Paint.kRound_Cap)
    with Cam(c)(width * 0.18, -width * 0.12):
        c.drawPath(seg, p2)


def circle_pts(cx, cy, rx, ry, seed=0, turns=1.18, n=64):
    r = R("circ", seed)
    a0 = r.uniform(-2.4, -1.6)
    w1, w2 = r.uniform(0.03, 0.06), r.uniform(0, math.tau)
    pts = []
    for i in range(n + 1):
        u = i / n
        a = a0 + turns * math.tau * u
        k = 1 + w1 * math.sin(2 * a + w2) + 0.05 * u
        pts.append((cx + rx * k * math.cos(a), cy + ry * k * math.sin(a)))
    return pts


def marker_circle(c, cx, cy, rx, ry, t, seed=0, width=11, color=INK):
    marker(c, circle_pts(cx, cy, rx, ry, seed), eoc(t), width, color)


def marker_arrow(c, x0, y0, x1, y1, t, bend=0.25, width=11, color=INK, seed=0, head=38):
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    nx, ny = -(y1 - y0), (x1 - x0)
    pts = []
    for i in range(21):
        u = i / 20
        b = 4 * u * (1 - u) * bend
        pts.append((lerp(x0, x1, u) + nx * b, lerp(y0, y1, u) + ny * b))
    marker(c, pts, eoc(clamp(t / 0.8)), width, color)
    th = clamp((t - 0.75) / 0.25)
    if th > 0:
        ex, ey = pts[-1]
        px, py = pts[-3]
        a = math.atan2(ey - py, ex - px)
        for s in (1, -1):
            hx = ex - head * math.cos(a + s * 0.55) * eoc(th)
            hy = ey - head * math.sin(a + s * 0.55) * eoc(th)
            marker(c, [(ex, ey), (hx, hy)], 1.0, width, color, smooth_=False)


def marker_underline(c, x0, x1, y, t, seed=0, width=10, color=INK):
    r = R("ul", seed)
    pts = [(lerp(x0, x1, u), y + r.uniform(-3, 3) + 6 * math.sin(u * 3 + seed)) for u in np.linspace(0, 1, 8)]
    marker(c, pts, eoc(t), width, color)


def marker_check(c, cx, cy, s, t, width=14, color=INK):
    marker(c, [(cx - s, cy), (cx - s * 0.3, cy + s * 0.7), (cx + s, cy - s * 0.9)], eoc(t), width, color,
           smooth_=False)


def scribble_question(c, cx, cy, s, t, width=11, color=INK):
    pts = []
    for i in range(18):
        a = math.pi * 1.15 - i / 17 * math.pi * 1.5
        pts.append((cx + s * 0.5 * math.cos(a), cy - s * 0.55 + s * 0.45 * math.sin(-a)))
    pts += [(cx + s * 0.05, cy + s * 0.05), (cx, cy + s * 0.35)]
    marker(c, pts, eoc(clamp(t / 0.85)), width, color)
    if t > 0.9:
        p = skia.Paint(AntiAlias=True, Color=rgb(color))
        c.drawCircle(cx, cy + s * 0.68, width * 0.75, p)


def dashed_cut(c, x0, y0, x1, y1, t, color=CORAL, width=7, dash=26, gap=16, phase=0.0):
    if t <= 0:
        return
    p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=width, Color=rgb(color),
                   StrokeCap=skia.Paint.kRound_Cap)
    p.setPathEffect(skia.DashPathEffect.Make([dash, gap], phase))
    c.drawLine(x0, y0, lerp(x0, x1, eoc(t)), lerp(y0, y1, eoc(t)), p)


# ---------------------------------------------------------------- halftone cutouts
def _render_gray(draw, w, h, ss=1):
    s = skia.Surface(w, h)
    c = s.getCanvas()
    c.clear(skia.Color(0, 0, 0, 0))
    draw(c, w, h)
    a = s.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType).astype(np.float32) / 255
    alpha = a[..., 3]
    with np.errstate(invalid="ignore", divide="ignore"):
        lum = np.where(alpha > 0, (a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11) / np.maximum(alpha, 1e-4), 1)
    return np.clip(lum, 0, 1), alpha


def cutout(draw, w, h, seed=0, border=14, cell=6.5, ink=CUT_INK, paper=CUT_PAPER, tone=0.45, border_color=WHITE,
           shadow_on=True, keep_color=False):
    """Render draw(canvas, w, h) (any colours; luminance is what counts) as an archival halftone photo
    cutout: newsprint tone + 45deg halftone dots, rough white paper border and a baked drop shadow.
    Returns (skia.Image, (ox, oy)) where (ox, oy) is the sprite pixel matching the drawing's (0,0)."""
    pad = border + 34
    lum, alpha = _render_gray(draw, w, h)
    if keep_color:
        s = skia.Surface(w, h)
        s.getCanvas().clear(skia.Color(0, 0, 0, 0))
        draw(s.getCanvas(), w, h)
        col = s.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType).astype(np.float32)
    lum = np.pad(lum, pad, constant_values=1)
    alpha = np.pad(alpha, pad)
    Hh, Ww = lum.shape
    yy, xx = np.mgrid[0:Hh, 0:Ww].astype(np.float32)
    a = math.radians(45)
    u = (xx * math.cos(a) + yy * math.sin(a)) / cell
    v = (-xx * math.sin(a) + yy * math.cos(a)) / cell
    d = np.hypot(u - np.floor(u) - 0.5, v - np.floor(v) - 0.5)
    D = 1 - gaussian_filter(lum, cell * 0.35)
    rad = np.sqrt(np.clip(D, 0, 1)) * 0.66
    m = np.clip((rad - d) / 0.07 + 0.5, 0, 1) * (D > 0.04)
    paper_a = np.array(paper, np.float32)
    ink_a = np.array(ink, np.float32)
    g = np.tile(GRAIN, (Hh // 1024 + 1, Ww // 1024 + 1))[:Hh, :Ww]
    base = paper_a[None, None, :] * (1 - tone * D[..., None]) * g[..., None]
    if keep_color:
        cpad = np.pad(col[..., :3] / np.maximum(col[..., 3:4] / 255, 1e-3), ((pad, pad), (pad, pad), (0, 0)),
                      constant_values=255)
        base = cpad * g[..., None]
    img = base * (1 - m[..., None]) + ink_a[None, None, :] * m[..., None]
    # rough white border
    solid = binary_fill_holes(alpha > 0.5)
    dist = distance_transform_edt(~solid)
    rng = np.random.default_rng(seed)
    noise = gaussian_filter(rng.standard_normal((Hh, Ww)), 6)
    noise = noise / (noise.std() + 1e-9)
    thr = border + 2.2 * noise
    ba = np.clip(thr - dist + 0.5, 0, 1)
    bc = np.array([(border_color >> 16) & 255, (border_color >> 8) & 255, border_color & 255], np.float32)
    bcol = bc[None, None, :] * g[..., None]
    out_rgb = img * alpha[..., None] + bcol * (1 - alpha[..., None])
    out_a = np.maximum(alpha, ba)
    if shadow_on:
        sh = gaussian_filter(nd_shift(out_a, (9, 4), order=1), 7) * 0.36
        comb_a = out_a + sh * (1 - out_a)
        shade = np.array([18, 20, 38], np.float32)
        with np.errstate(invalid="ignore", divide="ignore"):
            out_rgb = np.where(comb_a[..., None] > 0,
                               (out_rgb * out_a[..., None] + shade * (sh * (1 - out_a))[..., None]) / np.maximum(comb_a, 1e-4)[..., None],
                               0)
        out_a = comb_a
    rgba = np.empty((Hh, Ww, 4), np.uint8)
    # premultiply for skia
    rgba[..., :3] = np.clip(out_rgb * out_a[..., None], 0, 255)
    rgba[..., 3] = np.clip(out_a * 255, 0, 255)
    img = skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)
    return img, (pad, pad)


class Sprite:
    def __init__(self, draw, w, h, anchor=None, **kw):
        self.img, (self.ox, self.oy) = cutout(draw, w, h, **kw)
        self.w, self.h = w, h
        self.anchor = anchor if anchor else (w / 2, h / 2)

    def space(self, c, x, y, rot=0.0, sc=1.0):
        """Context in the drawing's own coordinates (for live screens drawn on top of the sprite)."""
        return _Space(c, x, y, rot, sc, self.anchor)

    def draw(self, c, x, y, rot=0.0, sc=1.0, alpha=255):
        if (sc if not isinstance(sc, tuple) else min(sc)) <= 0.001 or alpha <= 0:
            return
        with Cam(c)(x, y, rot, sc):
            p = skia.Paint(AntiAlias=True)
            if alpha < 255:
                p.setAlphaf(alpha / 255)
            c.drawImage(self.img, -self.ox - self.anchor[0], -self.oy - self.anchor[1],
                        skia.SamplingOptions(skia.FilterMode.kLinear), p)


class _Space(_Push):
    def __init__(self, c, x, y, rot, sc, anchor):
        super().__init__(c, x, y, rot, sc)
        self.anchor = anchor

    def __enter__(self):
        super().__enter__()
        self.c.translate(-self.anchor[0], -self.anchor[1])
        return self.c


def lin_grad(x0, y0, x1, y1, cols, pos=None):
    return skia.GradientShader.MakeLinear([(x0, y0), (x1, y1)], [skia.Color(*cc) if isinstance(cc, tuple) else cc
                                                                 for cc in cols], pos)


def rad_grad(cx, cy, r, cols, pos=None):
    return skia.GradientShader.MakeRadial((cx, cy), r, [skia.Color(*cc) if isinstance(cc, tuple) else cc
                                                       for cc in cols], pos)


def gpaint(shader=None, color=None):
    p = skia.Paint(AntiAlias=True)
    if shader is not None:
        p.setShader(shader)
    if color is not None:
        p.setColor(skia.Color(*color) if isinstance(color, tuple) else color)
    return p


def gray(v, a=255):
    v = int(clamp(v) * 255)
    return skia.Color(v, v, v, a)
