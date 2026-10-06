"""Claymation toolkit: lumpy hand-rolled paths, plasticine shading, thumbprint texture, clay type.

Everything is drawn with skia. "Clay" is faked with: lumpy outlines (static harmonic noise),
a per-animation-frame boil, a radial key light, offset inner shadow/highlight, a tiled
plasticine texture (lumps, thumbprints, tool scrapes) in overlay, a soft gloss and a cast shadow.
"""

import math
import os

import numpy as np
import skia

W, H = 1080, 1920
FPS = 12                      # animation is shot "on twos": 12 unique drawings per second
HERE = os.path.dirname(os.path.abspath(__file__))
LIGHT = (-0.55, -0.83)        # key light from top-left, like a studio softbox


# ---------------------------------------------------------------- colour
def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def col(c, a=1.0, k=1.0):
    r, g, b = hexrgb(c) if isinstance(c, str) else c
    r, g, b = (max(0, min(255, int(v * k))) for v in (r, g, b))
    return skia.ColorSetARGB(int(max(0, min(1, a)) * 255), r, g, b)


def mix(c1, c2, t):
    a, b = hexrgb(c1) if isinstance(c1, str) else c1, hexrgb(c2) if isinstance(c2, str) else c2
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def paint(c=None, a=1.0, k=1.0, stroke=None, blur=None, cap="round", **kw):
    p = skia.Paint(AntiAlias=True, **kw)
    if c is not None:
        p.setColor(col(c, a, k))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap if cap == "round" else skia.Paint.kButt_Cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


# ---------------------------------------------------------------- easing / timing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, t):
    return a + (b - a) * t


def prog(t, t0, t1):
    return clamp((t - t0) / (t1 - t0)) if t1 > t0 else float(t >= t0)


def ease_out(x):
    return 1 - (1 - x) ** 3


def ease_in(x):
    return x ** 3


def ease_io(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def back_out(x, s=1.9):
    x -= 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def bounce_land(x):
    """0..1 drop then two little bounces (cartoon landing)."""
    if x < 0.55:
        return (x / 0.55) ** 2
    if x < 0.8:
        u = (x - 0.675) / 0.125
        return 1 - 0.12 * (1 - u * u)
    u = (x - 0.9) / 0.1
    return 1 - 0.03 * (1 - u * u)


def squash_at(t, t_land, dur=0.35, amt=0.32):
    """(sx, sy) squash/stretch after an impact at t_land."""
    if t < t_land or t > t_land + dur:
        return 1.0, 1.0
    u = (t - t_land) / dur
    s = amt * math.exp(-4 * u) * math.cos(u * 3 * math.pi)
    return 1 + s, 1 - s


# ---------------------------------------------------------------- noise helpers
def _harm(seed, kmin, kmax, amp):
    rng = np.random.default_rng(abs(int(seed)) % (2 ** 32))
    ks = np.arange(kmin, kmax + 1)
    return ks, rng.uniform(0, 2 * np.pi, len(ks)), amp * rng.uniform(0.4, 1.0, len(ks)) / np.sqrt(ks)


def smooth_path(pts, closed=True):
    p = skia.Path()
    n = len(pts)
    if n < 3:
        return p
    p.moveTo(*pts[0])
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = pts[(i - 1) % n] if closed or i > 0 else pts[0]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if closed or i + 2 < n else pts[-1]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        p.cubicTo(c1[0], c1[1], c2[0], c2[1], p2[0], p2[1])
    if closed:
        p.close()
    return p


def blob(cx, cy, rx, ry, seed=0, lump=0.05, boil=0.0, f=0, n=36, rot=0.0):
    """Hand-rolled ellipse: static lumps + per-frame boil (pixels)."""
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ks, ph, am = _harm(seed, 2, 6, lump)
    r = 1 + (am[:, None] * np.cos(ks[:, None] * th + ph[:, None])).sum(0)
    x, y = rx * r * np.cos(th), ry * r * np.sin(th)
    if boil:
        bks, bph, bam = _harm(seed * 131 + f * 7919 + 17, 2, 5, boil)
        d = (bam[:, None] * np.cos(bks[:, None] * th + bph[:, None])).sum(0)
        x += d * np.cos(th)
        y += d * np.sin(th)
    cr, sr = math.cos(rot), math.sin(rot)
    pts = [(cx + a * cr - b * sr, cy + a * sr + b * cr) for a, b in zip(x, y)]
    return smooth_path(pts)


def rrect_pts(x, y, w, h, r, ds=10.0):
    r = max(1.0, min(r, w / 2 - 0.1, h / 2 - 0.1))
    pts = []

    def line(x0, y0, x1, y1):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / ds))
        for i in range(n):
            pts.append((x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n))

    def arc(cx, cy, a0):
        n = max(3, int(r * math.pi / 2 / ds))
        for i in range(n):
            a = a0 + (math.pi / 2) * i / n
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))

    line(x + r, y, x + w - r, y)
    arc(x + w - r, y + r, -math.pi / 2)
    line(x + w, y + r, x + w, y + h - r)
    arc(x + w - r, y + h - r, 0)
    line(x + w - r, y + h, x + r, y + h)
    arc(x + r, y + h - r, math.pi / 2)
    line(x, y + h - r, x, y + r)
    arc(x + r, y + r, math.pi)
    return pts


def lumpify(pts, seed=0, amp=2.0, boil=0.0, f=0, wl=(50, 220)):
    """Push a closed polyline along its normals by smooth noise (static lumps + frame boil)."""
    P = np.asarray(pts, float)
    n = len(P)
    seg = np.linalg.norm(np.roll(P, -1, 0) - P, axis=1)
    s = np.concatenate([[0], np.cumsum(seg)[:-1]])
    L = max(1.0, seg.sum())
    nxt, prv = np.roll(P, -1, 0), np.roll(P, 1, 0)
    t = nxt - prv
    t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-6)
    nrm = np.stack([t[:, 1], -t[:, 0]], 1)
    d = np.zeros(n)
    for sd, a in ((seed, amp), (seed * 131 + f * 7919 + 5, boil)):
        if not a:
            continue
        kmin, kmax = max(1, int(L / wl[1])), max(2, int(L / wl[0]))
        if kmax - kmin > 10:
            kmin = kmax - 10
        ks, ph, am = _harm(sd, kmin, kmax, a)
        am = am / am.sum() * a * 1.6 if am.sum() else am
        d += (am[:, None] * np.sin(2 * np.pi * ks[:, None] * s / L + ph[:, None])).sum(0)
    return [tuple(v) for v in P + nrm * d[:, None]]


def lumpy_rrect(x, y, w, h, r, seed=0, amp=2.0, boil=0.0, f=0, ds=10.0):
    return smooth_path(lumpify(rrect_pts(x, y, w, h, r, ds), seed, amp, boil, f))


def lumpy_poly(pts, seed=0, amp=1.5, ds=8.0, boil=0.0, f=0):
    dense = []
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        k = max(1, int(math.hypot(x1 - x0, y1 - y0) / ds))
        for j in range(k):
            dense.append((x0 + (x1 - x0) * j / k, y0 + (y1 - y0) * j / k))
    return smooth_path(lumpify(dense, seed, amp, boil, f))


def union(paths):
    b = skia.OpBuilder()
    for p in paths:
        b.add(p, skia.kUnion_PathOp)
    return b.resolve()


def xform(path, tx=0, ty=0, sx=1, sy=1, rot=0, px=0, py=0):
    """Scale/rotate about (px, py), then translate."""
    m = skia.Matrix()
    m.setTranslate(tx, ty)
    m.preTranslate(px, py)
    m.preRotate(rot)
    m.preScale(sx, sy)
    m.preTranslate(-px, -py)
    out = skia.Path(path)
    out.transform(m)
    return out


# ---------------------------------------------------------------- plasticine texture
def _make_texture(size=1024, seed=11):
    rng = np.random.default_rng(seed)
    img = np.zeros((size, size), np.float32)

    def tile_noise(cells, amp):
        g = rng.standard_normal((cells, cells)).astype(np.float32)
        # periodic bicubic-ish upsample via FFT zero padding keeps it tileable
        F = np.fft.fft2(g)
        Fp = np.zeros((size, size), complex)
        h = cells // 2
        Fp[:h, :h] = F[:h, :h]
        Fp[:h, -h:] = F[:h, -h:]
        Fp[-h:, :h] = F[-h:, :h]
        Fp[-h:, -h:] = F[-h:, -h:]
        out = np.real(np.fft.ifft2(Fp))
        return out / (out.std() + 1e-6) * amp

    img += tile_noise(8, 0.35) + tile_noise(24, 0.35) + tile_noise(96, 0.18)
    img += rng.standard_normal((size, size)).astype(np.float32) * 0.10   # fine grit
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    # thumbprints: patches of concentric ridges
    for _ in range(34):
        cx, cy = rng.uniform(0, size, 2)
        rad = rng.uniform(30, 75)
        ex = rng.uniform(0.6, 1.0)
        ang = rng.uniform(0, np.pi)
        dx = (xx - cx + size / 2) % size - size / 2
        dy = (yy - cy + size / 2) % size - size / 2
        u = dx * np.cos(ang) + dy * np.sin(ang)
        v = (-dx * np.sin(ang) + dy * np.cos(ang)) / ex
        d = np.sqrt(u * u + v * v)
        mask = np.clip(1 - d / rad, 0, 1) ** 0.7
        ridge = np.sin(d * rng.uniform(0.75, 0.95) + 0.03 * u)
        img += ridge * mask * 0.28 - mask * 0.15
    # tool scrapes
    for _ in range(26):
        cx, cy = rng.uniform(0, size, 2)
        ang = rng.uniform(0, np.pi)
        ln = rng.uniform(40, 130)
        dx = (xx - cx + size / 2) % size - size / 2
        dy = (yy - cy + size / 2) % size - size / 2
        u = dx * np.cos(ang) + dy * np.sin(ang)
        v = -dx * np.sin(ang) + dy * np.cos(ang)
        m = np.exp(-(v / 1.6) ** 2) * (np.abs(u) < ln) * np.clip(1 - np.abs(u) / ln, 0, 1) ** 0.4
        img += m * 0.55 - np.exp(-((v - 2.5) / 1.6) ** 2) * (np.abs(u) < ln) * 0.3
    img = (img - img.mean()) / (img.std() + 1e-6)
    g = np.clip(128 + img * 30, 0, 255).astype(np.uint8)
    rgba = np.dstack([g, g, g, np.full_like(g, 255)])
    return skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType)


_TEX = None


def texture():
    global _TEX
    if _TEX is None:
        _TEX = _make_texture()
    return _TEX


def tex_paint(seed=0, alpha=0.55, scale=1.0, mode=skia.BlendMode.kOverlay):
    rng = np.random.default_rng(abs(int(seed) + 991))
    m = skia.Matrix()
    m.setTranslate(*rng.uniform(0, 1024, 2))
    m.preScale(scale, scale)
    m.preRotate(rng.uniform(0, 360))
    sh = texture().makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat,
                              skia.SamplingOptions(skia.FilterMode.kLinear), m)
    p = skia.Paint(Shader=sh, AntiAlias=True)
    p.setBlendMode(mode)
    p.setAlphaf(alpha)
    return p


# ---------------------------------------------------------------- the clay material
def shadow(c, path, off=(9, 11), blur=8, alpha=0.33):
    c.save()
    c.translate(*off)
    c.drawPath(path, paint("#1a1208", alpha, blur=blur))
    c.restore()


def _ring(path, b, pad):
    r = skia.Path()
    r.addRect(skia.Rect(b.left() - pad, b.top() - pad, b.right() + pad, b.bottom() + pad))
    r.addPath(path)
    r.setFillType(skia.PathFillType.kEvenOdd)
    return r


def clay(c, path, color, seed=0, shade=True, cast=True, cast_off=None, cast_blur=None, cast_alpha=0.32,
         tex=0.55, tex_scale=1.0, gloss=0.22, ao=0.5, hi=0.35, light=LIGHT, flat=False):
    b = path.computeTightBounds()
    w, h = max(b.width(), 1), max(b.height(), 1)
    s = min(w, h)
    if cast:
        k = clamp(s / 60, 0.35, 1.6)
        off = cast_off or (-light[0] * 11 * k, -light[1] * 11 * k)
        shadow(c, path, off, cast_blur or 7 * k, cast_alpha)
    base = hexrgb(color) if isinstance(color, str) else color
    c.save()
    c.clipPath(path, skia.ClipOp.kIntersect, True)
    if flat:
        c.drawPath(path, paint(base))
    else:
        cx, cy = b.centerX() + light[0] * w * 0.32, b.centerY() + light[1] * h * 0.32
        R = max(w, h) * 0.95
        sh = skia.GradientShader.MakeRadial(skia.Point(cx, cy), R,
                                            [col(base, 1, 1.13), col(base, 1, 1.0), col(base, 1, 0.8)],
                                            [0.0, 0.45, 1.0])
        c.drawPaint(skia.Paint(Shader=sh, AntiAlias=True))
    if shade:
        ring = _ring(path, b, 60)
        d = clamp(s * 0.10, 2, 18)
        c.save()
        c.translate(light[0] * d, light[1] * d)
        c.drawPath(ring, paint(base, ao, k=0.45, blur=clamp(s * 0.09, 2, 22)))
        c.restore()
        c.save()
        c.translate(-light[0] * d * 0.6, -light[1] * d * 0.6)
        c.drawPath(ring, paint(mix(base, (255, 250, 235), 0.6), hi, blur=clamp(s * 0.06, 1.5, 14)))
        c.restore()
    if tex:
        c.drawPaint(tex_paint(seed, tex, tex_scale))
    if gloss:
        gx, gy = b.centerX() + light[0] * w * 0.26, b.centerY() + light[1] * h * 0.3
        c.drawOval(skia.Rect.MakeXYWH(gx - w * 0.16, gy - h * 0.09, w * 0.32, h * 0.18),
                   paint("#ffffff", gloss, blur=clamp(s * 0.06, 2, 20)))
    c.restore()


def clay_stroke(c, pts, width, color, seed=0, closed=False, cast=True, tex=0.4):
    """A rolled clay 'sausage' along a polyline (legs, wires, film strips, mouths...)."""
    sp = smooth_path(pts, closed) if len(pts) > 2 else _line(pts)
    stroker = paint(stroke=width)
    out = skia.Path()
    stroker.getFillPath(sp, out)
    out = skia.Op(out, out, skia.kUnion_PathOp) or out
    clay(c, out, color, seed, cast=cast, tex=tex, gloss=0.15)
    return out


def _line(pts):
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    return p


# ---------------------------------------------------------------- clay type
_FONTS = {}


def font(name, size):
    if name not in _FONTS:
        _FONTS[name] = skia.Typeface.MakeFromFile(os.path.join(HERE, "..", "fonts", name))
    f = skia.Font(_FONTS[name], size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


def _resample(path, ds=5.0):
    """Path -> list of closed contours sampled every ds pixels."""
    out = []
    it = skia.PathMeasure(path, True)
    while True:
        L = it.getLength()
        if L > 1:
            n = max(6, int(L / ds))
            pts = []
            for i in range(n):
                pos, _ = it.getPosTan(L * i / n)
                pts.append((pos.x(), pos.y()))
            out.append(pts)
        if not it.nextContour():
            break
    return out


def glyph_paths(text, fname, size, tracking=0.0, seed=0, lump=1.4, ds=5.0):
    """Hand-rolled letter paths centred on x=0, baseline y=0. Returns [(path, advance_x_centre)]."""
    f = font(fname, size)
    glyphs = f.textToGlyphs(text)
    widths = f.getWidths(glyphs)
    total = sum(widths) + tracking * (len(glyphs) - 1)
    x = -total / 2
    res = []
    for i, (g, wdt) in enumerate(zip(glyphs, widths)):
        p = f.getPath(g)
        if p is None or p.isEmpty():
            x += wdt + tracking
            continue
        cont = _resample(p, ds)
        lp = skia.Path()
        for j, ctr in enumerate(cont):
            lp.addPath(smooth_path(lumpify(ctr, seed * 97 + i * 13 + j, lump, wl=(25, 90))))
        lp.setFillType(p.getFillType())
        lp.offset(x, 0)
        res.append((lp, x + wdt / 2))
        x += wdt + tracking
    return res


def clay_letter(c, path, color, seed=0, depth=10, cast=True, gloss=0.25, tex=0.5):
    """Extruded clay letter: a darker 'side' stack then the shaded face."""
    b = path.computeTightBounds()
    if cast:
        shadow(c, path, (12, depth + 12), 9, 0.35)
    side = mix(color, (40, 20, 10), 0.35)
    for k in range(depth, 0, -2):
        q = skia.Path(path)
        q.offset(k * 0.35, k)
        c.drawPath(q, paint(side, k=0.85 + 0.15 * (1 - k / depth)))
    clay(c, path, color, seed, cast=False, gloss=gloss, tex=tex)
    return b


# ---------------------------------------------------------------- misc drawing
def star_path(cx, cy, r, inner=0.38, pts=4, rot=0.0):
    p = []
    for i in range(pts * 2):
        a = rot + math.pi * i / pts - math.pi / 2
        rr = r if i % 2 == 0 else r * inner
        p.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return smooth_path(p)


def heart_path(cx, cy, s):
    p = skia.Path()
    p.moveTo(cx, cy + s * 0.9)
    p.cubicTo(cx - s * 1.3, cy + s * 0.05, cx - s * 0.75, cy - s * 0.95, cx, cy - s * 0.3)
    p.cubicTo(cx + s * 0.75, cy - s * 0.95, cx + s * 1.3, cy + s * 0.05, cx, cy + s * 0.9)
    p.close()
    return p
