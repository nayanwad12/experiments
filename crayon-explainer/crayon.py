"""Crayon-on-paper rendering engine (skia-python + numpy).

Everything is drawn as wobbly polylines through a paper "tooth" texture: pigment only lands on
the high points of the paper, so strokes come out grainy and broken like wax crayon. Lines are
re-wobbled 12 times a second ("boiling"), the way hand-drawn animation is redrawn every frame.
"""
import functools
import math
import os

import numpy as np
import skia
from scipy.ndimage import gaussian_filter

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1920, 1080
FPS = 24
BOIL_FPS = 12

# crayon box
INK = "#2D2A3A"
RED = "#E0453A"
ORANGE = "#F2943A"
YELLOW = "#F6CB3F"
LIME = "#A6D44A"
GREEN = "#4FAE5A"
TEAL = "#3BB3A8"
SKY = "#8CCBF0"
BLUE = "#3E78CF"
PERI = "#8E92F0"
PURPLE = "#7E55C2"
PINK = "#EF7BA6"
BLUSH = "#F7B6C4"
BROWN = "#8A5A3B"
TAN = "#E8C9A0"
WHITE = "#FFFDF6"
GREY = "#9A97A3"


def col(c):
    c = c.lstrip("#")
    return skia.Color(int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


# ----------------------------------------------------------------------------- textures
TILE = 1024


def _uniformize(a):
    r = np.argsort(np.argsort(a.ravel()))
    return (r / (a.size - 1)).reshape(a.shape).astype(np.float32)


@functools.lru_cache(None)
def tooth_field():
    rng = np.random.default_rng(7)
    n = rng.standard_normal((TILE, TILE)).astype(np.float32)
    fine = gaussian_filter(n, 0.8, mode="wrap")
    mid = gaussian_filter(rng.standard_normal((TILE, TILE)).astype(np.float32), 2.2, mode="wrap")
    # faint diagonal laid-paper streaks
    streak = gaussian_filter(rng.standard_normal((TILE, TILE)).astype(np.float32), (0.6, 5.0), mode="wrap")
    a = fine / fine.std() + 0.9 * mid / mid.std() + 0.35 * streak / streak.std()
    return _uniformize(a)


@functools.lru_cache(None)
def tooth_image(pressure):
    """White RGBA tile whose alpha is crayon coverage at this pressure (premultiplied)."""
    t = tooth_field()
    soft = 0.16
    a = np.clip((t - (1.0 - pressure)) / soft + 0.5, 0, 1)
    a = np.clip(a * 1.08, 0, 1)
    a8 = (a * 255).astype(np.uint8)
    rgba = np.dstack([a8, a8, a8, a8])
    return skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)


PRESSURES = (0.25, 0.4, 0.55, 0.7, 0.82, 0.92)


def _qp(p):
    return min(PRESSURES, key=lambda q: abs(q - p))


@functools.lru_cache(None)
def paper_image():
    rng = np.random.default_rng(3)
    base = np.array([246, 239, 223], np.float32)
    low = gaussian_filter(rng.standard_normal((H // 8, W // 8)), 6)
    low = np.kron(low / low.std(), np.ones((8, 8)))[:H, :W]
    low = gaussian_filter(low, 4)
    fib = gaussian_filter(rng.standard_normal((H, W)), (0.5, 3.0))
    fib2 = gaussian_filter(rng.standard_normal((H, W)), (3.0, 0.5))
    grain = gaussian_filter(rng.standard_normal((H, W)), 0.7)
    shade = 1.0 + 0.018 * low + 0.012 * (fib / fib.std() + fib2 / fib2.std()) * 0.5 + 0.02 * grain / grain.std()
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2))
    vign = 1.0 - 0.13 * np.clip(r - 0.45, 0, None) ** 1.6
    img = base[None, None, :] * (shade * vign)[..., None]
    # a few faint fibres
    for _ in range(140):
        x0, y0 = rng.uniform(0, W), rng.uniform(0, H)
        ang = rng.uniform(0, math.pi)
        L = rng.uniform(8, 28)
        for s in np.linspace(0, L, int(L)):
            xi, yi = int(x0 + s * math.cos(ang)), int(y0 + s * math.sin(ang))
            if 0 <= xi < W and 0 <= yi < H:
                img[yi, xi] *= 0.965
    img = np.clip(img, 0, 255).astype(np.uint8)
    rgba = np.dstack([img, np.full((H, W), 255, np.uint8)])
    return skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType)


# ----------------------------------------------------------------------------- geometry
def hrand(*key):
    """Deterministic hash -> float in [0,1)."""
    h = 2166136261
    for k in key:
        for ch in str(k):
            h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
        h = ((h ^ 0x9E) * 16777619) & 0xFFFFFFFF
    return (h % 100000) / 100000.0


def resample(pts, step=6.0, closed=False):
    pts = np.asarray(pts, np.float64)
    if closed:
        pts = np.vstack([pts, pts[:1]])
    d = np.hypot(*np.diff(pts, axis=0).T)
    s = np.concatenate([[0], np.cumsum(d)])
    L = s[-1]
    if L < 1e-6:
        return pts.copy(), 0.0
    n = max(2, int(math.ceil(L / step)) + 1)
    u = np.linspace(0, L, n)
    x = np.interp(u, s, pts[:, 0])
    y = np.interp(u, s, pts[:, 1])
    return np.stack([x, y], 1), L


def wobble(pts, amp, seed, closed=False):
    """Smooth hand-wobble along arc length (amp in px)."""
    if amp <= 0 or len(pts) < 2:
        return pts
    d = np.hypot(*np.diff(pts, axis=0).T)
    s = np.concatenate([[0], np.cumsum(d)])
    L = max(s[-1], 1.0)
    off = np.zeros_like(pts)
    for ax in range(2):
        for i, lam in enumerate((260.0, 90.0, 37.0)):
            ph = hrand(seed, ax, i) * 2 * math.pi
            a = (1.0, 0.55, 0.25)[i]
            if closed:  # keep the loop closed: whole number of periods
                k = max(1, round(L / lam))
                off[:, ax] += a * np.sin(2 * math.pi * k * s / L + ph)
            else:
                off[:, ax] += a * np.sin(2 * math.pi * s / lam + ph)
    return pts + amp * off / 1.4


def ellipse(cx, cy, rx, ry, n=72, a0=0.0, a1=2 * math.pi):
    a = np.linspace(a0, a1, n)
    return np.stack([cx + rx * np.cos(a), cy + ry * np.sin(a)], 1)


def rrect(x, y, w, h, r=18, n=8):
    r = min(r, w / 2, h / 2)
    pts = []
    for cx, cy, a0 in ((x + w - r, y + r, -math.pi / 2), (x + w - r, y + h - r, 0),
                       (x + r, y + h - r, math.pi / 2), (x + r, y + r, math.pi)):
        for a in np.linspace(a0, a0 + math.pi / 2, n):
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return np.array(pts)


def star(cx, cy, r1, r2, k=5, rot=-math.pi / 2):
    pts = []
    for i in range(2 * k):
        r = r1 if i % 2 == 0 else r2
        a = rot + i * math.pi / k
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return np.array(pts)


def bezier(*ctrl, n=40):
    c = np.asarray(ctrl, np.float64)
    k = len(c) - 1
    t = np.linspace(0, 1, n)[:, None]
    out = np.zeros((n, 2))
    for i in range(k + 1):
        out += math.comb(k, i) * (1 - t) ** (k - i) * t ** i * c[i]
    return out


def heart(cx, cy, s):
    t = np.linspace(0, 2 * math.pi, 80)
    x = 16 * np.sin(t) ** 3
    y = -(13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t))
    return np.stack([cx + x * s / 16, cy + y * s / 16], 1)


def cloud(cx, cy, w, h):
    pts = []
    bumps = [(-0.38, 0.1, 0.24), (-0.18, -0.22, 0.3), (0.12, -0.3, 0.32), (0.36, -0.05, 0.25), (0.22, 0.22, 0.2), (-0.1, 0.25, 0.22)]
    # polar outline built from max of bump circles
    a = np.linspace(0, 2 * math.pi, 160, endpoint=False)
    rr = np.zeros_like(a)
    for bx, by, br in bumps:
        # ray-circle intersection from centre
        dx, dy = np.cos(a), np.sin(a)
        b = dx * bx * w + dy * by * h * 1.6
        c = (bx * w) ** 2 + (by * h * 1.6) ** 2 - (br * w) ** 2
        disc = b * b - c
        r = np.where(disc > 0, b + np.sqrt(np.maximum(disc, 0)), 0)
        rr = np.maximum(rr, r)
    return np.stack([cx + rr * np.cos(a), cy + rr * np.sin(a) / 1.6], 1)


# ----------------------------------------------------------------------------- easing
def clamp01(x):
    return max(0.0, min(1.0, x))


def seg(t, a, b):
    return clamp01((t - a) / (b - a)) if b > a else float(t >= a)


def ease_out(x):
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    return x * x * (3 - 2 * x)


def back_out(x, k=1.9):
    x = clamp01(x)
    return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2


def pop(t, t0, dur=0.35):
    return back_out(seg(t, t0, t0 + dur))


# ----------------------------------------------------------------------------- transforms
def M_translate(x, y):
    return np.array([[1, 0, x], [0, 1, y], [0, 0, 1]], np.float64)


def M_scale(s, sy=None):
    return np.diag([s, s if sy is None else sy, 1.0])


def M_rot(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def M_about(cx, cy, s=1.0, rot=0.0, sy=None, dx=0.0, dy=0.0):
    return M_translate(cx + dx, cy + dy) @ M_rot(rot) @ M_scale(s, sy) @ M_translate(-cx, -cy)


def apply(M, pts):
    pts = np.asarray(pts, np.float64)
    return pts @ M[:2, :2].T + M[:2, 2]


# ----------------------------------------------------------------------------- fonts
FONTS = {
    "title": os.path.join(HERE, "fonts", "LuckiestGuy-Regular.ttf"),
    "hand": os.path.join(HERE, "fonts", "GochiHand-Regular.ttf"),
    "print": os.path.join(HERE, "fonts", "PatrickHand-Regular.ttf"),
    "brush": os.path.join(HERE, "fonts", "CaveatBrush-Regular.ttf"),
}


@functools.lru_cache(None)
def _typeface(name):
    return skia.Typeface.MakeFromFile(FONTS[name])


@functools.lru_cache(4096)
def glyph_contours(fontname, ch):
    """Contours of one glyph at size 100, plus its advance."""
    font = skia.Font(_typeface(fontname), 100)
    g = font.textToGlyphs(ch)
    adv = font.getWidths(g)[0]
    path = font.getPath(g[0]) if len(g) else None
    contours = []
    if path is not None:
        pm = skia.PathMeasure(path, False, 1.0)
        while True:
            L = pm.getLength()
            if L > 0:
                n = max(8, int(L / 1.5))
                pts = [pm.getPosTan(L * i / n)[0] for i in range(n)]
                contours.append(np.array([(p.x(), p.y()) for p in pts]))
            if not pm.nextContour():
                break
    return contours, adv


def text_layout(s, fontname, size, x, y, anchor="c", tracking=0.0):
    """-> list of (char, contours-in-world, glyph-centre) and total width."""
    k = size / 100.0
    advs = [glyph_contours(fontname, ch)[1] * k + tracking for ch in s]
    width = sum(advs) - tracking
    font = skia.Font(_typeface(fontname), size)
    m = font.getMetrics()
    cap = -m.fCapHeight if m.fCapHeight else size * 0.7
    if anchor == "c":
        x0 = x - width / 2
    elif anchor == "r":
        x0 = x - width
    else:
        x0 = x
    base = y + (-cap) / 2 * -1  # vertically centre caps on y
    base = y + (m.fCapHeight if m.fCapHeight else size * 0.7) / 2
    out = []
    cx = x0
    for ch, a in zip(s, advs):
        cs, _ = glyph_contours(fontname, ch)
        cs = [c * k + np.array([cx, base]) for c in cs]
        out.append((ch, cs, (cx + (a - tracking) / 2, base - size * 0.35)))
        cx += a
    return out, width


# ----------------------------------------------------------------------------- pen
class Pen:
    """One frame's drawing context. All coordinates are world px (1920x1080); the camera matrix
    and any pushed matrices are applied to points before wobble, so wobble stays screen-sized."""

    def __init__(self, canvas, t, cam=None):
        self.c = canvas
        self.t = t
        self.boil = int(math.floor(t * BOIL_FPS + 1e-6))
        self.stack = [np.eye(3) if cam is None else cam]
        self.scale = 1.0

    # matrices
    def push(self, M):
        self.stack.append(self.stack[-1] @ M)
        return self

    def pop(self):
        self.stack.pop()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.pop()

    def X(self, pts):
        return apply(self.stack[-1], pts)

    def sx(self):
        M = self.stack[-1]
        return math.sqrt(abs(M[0, 0] * M[1, 1] - M[0, 1] * M[1, 0]))

    # paints
    def _paint(self, color, pressure, alpha, seed, stroke=None, cap=True, streak=None):
        img = tooth_image(_qp(pressure))
        ox = hrand(seed, "ox", self.boil) * TILE
        oy = hrand(seed, "oy", self.boil) * TILE
        m = skia.Matrix.Translate(ox, oy)
        if streak is not None:  # grain stretched along the stroke direction
            m = m.preConcat(skia.Matrix.RotateDeg(streak)).preConcat(skia.Matrix.Scale(2.6, 0.9))
        sh = img.makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat,
                            skia.SamplingOptions(skia.FilterMode.kLinear), m)
        kw = dict(Shader=sh, AntiAlias=True,
                  ColorFilter=skia.ColorFilters.Blend(col(color), skia.BlendMode.kSrcIn))
        if stroke is not None:
            kw.update(Style=skia.Paint.kStroke_Style, StrokeWidth=stroke,
                      StrokeCap=skia.Paint.kRound_Cap if cap else skia.Paint.kButt_Cap,
                      StrokeJoin=skia.Paint.kRound_Join)
        p = skia.Paint(**kw)
        p.setAlphaf(clamp01(alpha))
        return p

    @staticmethod
    def _path(polys, closed=False):
        path = skia.Path()
        for pts in polys:
            if len(pts) < 2:
                continue
            path.moveTo(*pts[0])
            for q in pts[1:]:
                path.lineTo(*q)
            if closed:
                path.close()
        return path

    # primitives
    def line(self, pts, color=INK, width=7, pressure=0.8, draw=1.0, seed="l", wob=1.0, alpha=1.0,
             double=True, closed=False, scale_width=True, start=0.0):
        if draw <= start or alpha <= 0:
            return
        P = self.X(pts)
        P, L = resample(P, 5.0, closed)
        if L < 0.5:
            return
        w = width * (self.sx() ** 0.5 if scale_width else 1.0)
        passes = 2 if double else 1
        for k in range(passes):
            sd = (seed, k, self.boil)
            Q = wobble(P, 1.6 * wob + 0.5 * k, sd)
            if draw < 1.0 or start > 0:
                n1 = max(2, int(len(Q) * draw))
                n0 = min(int(len(Q) * start), n1 - 2)
                Q = Q[n0:n1]
            pr = pressure if k == 0 else pressure * 0.75
            self.c.drawPath(self._path([Q]), self._paint(color, pr, alpha, (seed, k), stroke=w * (1.0 if k == 0 else 0.7)))

    def shape(self, contours, fill=None, stroke=INK, width=6.5, pressure=0.76, fill_pressure=0.72,
              hatch=45, gap=9.0, fill_draw=1.0, stroke_draw=1.0, seed="s", wob=1.0, alpha=1.0,
              under=0.3, double=True, fill_alpha=1.0):
        """Closed shape(s): scribble-hatched crayon fill + wobbly outline."""
        if isinstance(contours, np.ndarray):
            contours = [contours]
        if alpha <= 0:
            return
        world = [self.X(c) for c in contours]
        wobbled = []
        for i, c in enumerate(world):
            P, L = resample(c, 5.0, closed=True)
            wobbled.append(wobble(P, 1.6 * wob, (seed, i, self.boil), closed=True))
        if fill is not None and fill_draw > 0:
            clip = self._path(wobbled, closed=True)
            clip.setFillType(skia.PathFillType.kWinding)
            self.c.save()
            self.c.clipPath(clip, skia.ClipOp.kIntersect, True)
            if under > 0 and fill_draw >= 1.0:
                self.c.drawPath(clip, self._paint(fill, under, alpha * fill_alpha, (seed, "u")))
            b = clip.computeTightBounds()
            self._hatch(b, fill, hatch, gap * max(0.75, min(1.3, self.sx())), fill_pressure, fill_draw,
                        alpha * fill_alpha, seed)
            self.c.restore()
        if stroke is not None and stroke_draw > 0:
            w = width * self.sx() ** 0.5
            for k in range(2 if double else 1):
                polys = []
                for i, c in enumerate(world):
                    P, _ = resample(c, 5.0, closed=True)
                    Q = wobble(P, 1.6 * wob + 0.6 * k, (seed, "o", i, k, self.boil), closed=True)
                    if k == 1:  # second pass starts a little rotated and overlaps the end
                        r = int(len(Q) * hrand(seed, i) * 0.5)
                        Q = np.roll(Q, r, axis=0)
                        Q = np.vstack([Q, Q[: max(2, len(Q) // 12)]])
                    if stroke_draw < 1.0:
                        Q = Q[: max(2, int(len(Q) * stroke_draw))]
                    polys.append(Q)
                pr = pressure if k == 0 else pressure * 0.7
                self.c.drawPath(self._path(polys), self._paint(stroke, pr, alpha, (seed, "o", k),
                                                               stroke=w * (1.0 if k == 0 else 0.65)))

    def _hatch(self, b, color, angle, gap, pressure, draw, alpha, seed):
        cx, cy = (b.left() + b.right()) / 2, (b.top() + b.bottom()) / 2
        R = math.hypot(b.width(), b.height()) / 2 + gap * 2
        a = math.radians(angle + (hrand(seed, "ang", self.boil) - 0.5) * 6)
        u = np.array([math.cos(a), math.sin(a)])
        v = np.array([-u[1], u[0]])
        n = int(2 * R / gap) + 1
        pts = []
        for i in range(n):
            off = -R + i * gap + (hrand(seed, i, self.boil) - 0.5) * gap * 0.5
            e1 = np.array([cx, cy]) + v * off + u * (-R) * (1 if i % 2 == 0 else -1)
            e1 = e1 + u * (hrand(seed, "j", i, self.boil) - 0.5) * gap * 2
            pts.append(e1)
        pts = np.array(pts)
        # zig-zag: alternate ends => continuous scribble
        if draw < 1.0:
            k = max(2, int(len(pts) * draw))
            pts = pts[:k]
        if len(pts) < 2:
            return
        # three interleaved passes with different pressure -> visible individual strokes
        for g, pf in enumerate((1.0, 0.82, 0.66)):
            sel = pts[g::3]
            if len(sel) < 1:
                continue
            polys = []
            for j in range(0, len(sel)):
                i = g + 3 * j
                if i + 1 >= len(pts):
                    break
                seg_ = np.vstack([pts[i], pts[i + 1]])
                P, _ = resample(seg_, 8.0)
                polys.append(wobble(P, 1.0, (seed, "h", i, self.boil)))
            if polys:
                self.c.drawPath(self._path(polys), self._paint(color, pressure * pf, alpha, (seed, "h", g),
                                                               stroke=gap * 1.15, streak=math.degrees(a)))

    def dot(self, x, y, r, color, pressure=0.85, seed="d", alpha=1.0):
        self.shape(ellipse(x, y, r, r, 24), fill=color, stroke=None, seed=seed, alpha=alpha, gap=max(3, r / 2),
                   fill_pressure=pressure, under=0.6)

    def text(self, s, fontname, size, x, y, color=INK, anchor="c", reveal=1.0, pressure=0.9, outline=None,
             outline_w=5.0, seed="t", alpha=1.0, pop_t=None, tracking=0.0, hatch=False, colors=None,
             gap=7.0, wave=0.0):
        """Crayon lettering. reveal (0..1) types letters on; pop_t (per-letter start times) pops them."""
        glyphs, width = text_layout(s, fontname, size, x, y, anchor, tracking)
        nvis = len(s) * reveal
        for i, (ch, cs, (gx, gy)) in enumerate(glyphs):
            if ch == " " or not cs:
                continue
            if pop_t is not None:
                k = pop(self.t, pop_t[i], 0.4)
                if k <= 0:
                    continue
            else:
                k = clamp01(nvis - i)
                if k <= 0:
                    continue
                k = back_out(k)
            dy = math.sin(self.t * 5 + i * 0.7) * wave
            rot = (hrand(seed, i) - 0.5) * 0.08
            with self.push(M_about(gx, gy, k, rot, dy=dy)):
                c = colors[i % len(colors)] if colors else color
                if hatch:
                    self.shape(cs, fill=c, stroke=outline or INK, width=outline_w, seed=(seed, i), gap=gap,
                               alpha=alpha, hatch=35 + 20 * hrand(seed, "h", i), fill_pressure=0.8, under=0.5)
                else:
                    self.shape(cs, fill=c, stroke=None, seed=(seed, i), gap=max(3.0, size / 22), alpha=alpha,
                               fill_pressure=pressure, under=0.62, wob=0.5)
        return width


def new_surface():
    return skia.Surface(W, H)


def frame_to_rgb(surface):
    a = surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
    return np.ascontiguousarray(a[:, :, :3])
