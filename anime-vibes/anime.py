"""Drawing engine: skia helpers for cel-shaded anime frames (paths, gradients, outlines, screentone,
speed lines, sparkles, outlined type, easing)."""
import math
import os

import numpy as np
import skia

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1920, 1080
FPS = 24
INK = "#1B1426"

FONTS = {
    "bang": "Bangers-Regular.ttf",          # manga sound effects / kinetic type
    "dela": "DelaGothicOne-Regular.ttf",    # heavy Japanese gothic (titles, kana)
    "pop": "MochiyPopOne-Regular.ttf",      # rounded pop (subtitles, shojo, chibi)
    "zen": "ZenDots-Regular.ttf",           # mecha HUD
    "orb": "Orbitron[wght].ttf",            # mecha HUD numbers
}


# ----------------------------------------------------------------------------- colour / paint
def col(c, a=1.0):
    if isinstance(c, int):
        return c
    c = c.lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    if len(c) == 8:
        a *= int(c[6:8], 16) / 255
    return skia.ColorSetARGB(int(255 * max(0.0, min(1.0, a))), r, g, b)


def mix(c1, c2, k):
    c1, c2 = c1.lstrip("#")[:6], c2.lstrip("#")[:6]
    a = [int(c1[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(c2[i:i + 2], 16) for i in (0, 2, 4)]
    k = max(0.0, min(1.0, k))
    return "#" + "".join(f"{int(round(x + (y - x) * k)):02X}" for x, y in zip(a, b))


def fill(c, a=1.0, blend=None, blur=0.0, shader=None):
    p = skia.Paint(AntiAlias=True, Color=col(c, a))
    if shader is not None:
        p.setShader(shader)
        p.setAlphaf(a)
    if blend is not None:
        p.setBlendMode(blend)
    if blur > 0:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


def stroke(c, w, a=1.0, cap=skia.Paint.kRound_Cap, blur=0.0, blend=None):
    p = skia.Paint(AntiAlias=True, Color=col(c, a), Style=skia.Paint.kStroke_Style, StrokeWidth=w,
                   StrokeCap=cap, StrokeJoin=skia.Paint.kRound_Join)
    if blur > 0:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if blend is not None:
        p.setBlendMode(blend)
    return p


def lin(x0, y0, x1, y1, colors, pos=None):
    return skia.GradientShader.MakeLinear([skia.Point(x0, y0), skia.Point(x1, y1)],
                                          [col(c) if isinstance(c, str) else c for c in colors], pos)


def rad(cx, cy, r, colors, pos=None):
    return skia.GradientShader.MakeRadial(skia.Point(cx, cy), max(r, 0.01),
                                          [col(c) if isinstance(c, str) else c for c in colors], pos)


def grad_rect(c, x, y, w, h, colors, pos=None, vertical=True, a=1.0):
    sh = lin(x, y, x, y + h, colors, pos) if vertical else lin(x, y, x + w, y, colors, pos)
    c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), fill("#000000", a, shader=sh))


# ----------------------------------------------------------------------------- geometry
def path(pts, closed=True, smooth=True, tension=0.5):
    """Catmull-Rom spline through pts as cubic Béziers."""
    p = skia.Path()
    n = len(pts)
    if n < 2:
        return p
    p.moveTo(*pts[0])
    if not smooth or n < 3:
        for q in pts[1:]:
            p.lineTo(*q)
        if closed:
            p.close()
        return p
    m = n if closed else n - 1
    for i in range(m):
        p0 = pts[(i - 1) % n] if (closed or i > 0) else pts[0]
        p1 = pts[i % n]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if (closed or i + 2 < n) else pts[-1]
        k = tension / 3 * 2
        c1 = (p1[0] + (p2[0] - p0[0]) * k / 2, p1[1] + (p2[1] - p0[1]) * k / 2)
        c2 = (p2[0] - (p3[0] - p1[0]) * k / 2, p2[1] - (p3[1] - p1[1]) * k / 2)
        p.cubicTo(c1[0], c1[1], c2[0], c2[1], p2[0], p2[1])
    if closed:
        p.close()
    return p


def poly(pts, closed=True):
    return path(pts, closed, smooth=False)


def ellipse(cx, cy, rx, ry):
    p = skia.Path()
    p.addOval(skia.Rect.MakeLTRB(cx - rx, cy - ry, cx + rx, cy + ry))
    return p


def star_pts(cx, cy, r1, r2, k=4, rot=-math.pi / 2):
    out = []
    for i in range(2 * k):
        r = r1 if i % 2 == 0 else r2
        a = rot + i * math.pi / k
        out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def rrect(x, y, w, h, r):
    p = skia.Path()
    p.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r))
    return p


def cel(c, p, base, line=INK, lw=5.0, a=1.0):
    """Flat cel fill + ink outline."""
    c.drawPath(p, fill(base, a))
    if lw > 0:
        c.drawPath(p, stroke(line, lw, a))


def shade(c, clip_path, shadow_path, color, a=1.0):
    """Hard-edged cel shadow: shadow_path clipped to clip_path."""
    c.save()
    c.clipPath(clip_path, doAntiAlias=True)
    c.drawPath(shadow_path, fill(color, a))
    c.restore()


# ----------------------------------------------------------------------------- easing / time
def clamp01(x):
    return max(0.0, min(1.0, x))


def seg(t, a, b):
    return clamp01((t - a) / (b - a)) if b > a else float(t >= a)


def ease_out(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ease_in(x):
    x = clamp01(x)
    return x ** 3


def ease_io(x):
    x = clamp01(x)
    return 3 * x * x - 2 * x * x * x


def back_out(x, k=2.2):
    x = clamp01(x)
    x -= 1
    return 1 + x * x * ((k + 1) * x + k)


def elastic(x):
    x = clamp01(x)
    if x in (0.0, 1.0):
        return x
    return 2 ** (-10 * x) * math.sin((x * 10 - 0.75) * 2 * math.pi / 3) + 1


def twos(t):
    """Character animation on twos (12 drawings a second), like TV anime."""
    return math.floor(t * 12) / 12


def hrand(*key):
    h = 2166136261
    for ch in repr(key):
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return (h & 0xFFFFFF) / 0xFFFFFF


def shake(t, t0, amp=18, dur=0.35, f=31):
    k = seg(t, t0, t0 + dur)
    if k <= 0 or k >= 1:
        return 0.0, 0.0
    d = (1 - k) ** 2 * amp
    return d * math.sin(t * f * 6.1), d * math.cos(t * f * 4.7)


# ----------------------------------------------------------------------------- type
_tf = {}


def typeface(name):
    if name not in _tf:
        _tf[name] = skia.Typeface.MakeFromFile(os.path.join(HERE, "fonts", FONTS[name]))
    return _tf[name]


def font(name, size):
    f = skia.Font(typeface(name), size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    f.setSubpixel(True)
    return f


def text_width(s, name, size):
    return font(name, size).measureText(s)


def text(c, s, name, size, x, y, color="#FFFFFF", anchor="c", outline=None, ow=8.0, a=1.0,
         shadow=None, shadow_off=(6, 6), shader=None, outline2=None, ow2=0.0, tracking=0.0):
    """Outlined anime title type. anchor: l/c/r on x, baseline at y + size*0.35 (visual centre)."""
    f = font(name, size)
    if tracking:
        widths = f.getWidths(f.textToGlyphs(s))
        total = sum(widths) + tracking * (len(s) - 1)
    else:
        total = f.measureText(s)
    x0 = x - total / 2 if anchor == "c" else (x - total if anchor == "r" else x)
    yb = y + size * 0.35
    blob = None
    if tracking:
        glyphs = f.textToGlyphs(s)
        widths = f.getWidths(glyphs)
        xs = []
        cx = x0
        for wv in widths:
            xs.append(cx)
            cx += wv + tracking
        b = skia.TextBlobBuilder()
        b.allocRunPosH(f, glyphs, xs, yb)
        blob = b.make()

    def draw(p, dx=0.0, dy=0.0):
        if blob is not None:
            c.drawTextBlob(blob, dx, dy, p)
        else:
            c.drawString(s, x0 + dx, yb + dy, f, p)

    if shadow:
        draw(fill(shadow, a), *shadow_off)
        if outline:
            draw(stroke(shadow, ow * 2, a), *shadow_off)
    if outline2:
        draw(stroke(outline2, ow2 * 2, a))
    if outline:
        draw(stroke(outline, ow * 2, a))
    p = fill(color, a)
    if shader is not None:
        p.setShader(shader)
    draw(p)
    return total


# ----------------------------------------------------------------------------- effects
def speed_lines_radial(c, cx, cy, t, n=90, r0=260, color="#FFFFFF", a=1.0, seed=0, rmax=2200, wmax=26):
    """Manga focus lines converging on (cx, cy); redrawn 12x a second."""
    fr = math.floor(t * 12)
    for i in range(n):
        ang = 2 * math.pi * (i + hrand(seed, i, fr)) / n
        w = wmax * (0.25 + hrand(seed, i, fr, "w"))
        r1 = r0 * (0.7 + 0.9 * hrand(seed, i, fr, "r"))
        da = w / rmax
        p = poly([(cx + r1 * math.cos(ang), cy + r1 * math.sin(ang)),
                  (cx + rmax * math.cos(ang - da), cy + rmax * math.sin(ang - da)),
                  (cx + rmax * math.cos(ang + da), cy + rmax * math.sin(ang + da))])
        c.drawPath(p, fill(color, a))


def speed_lines_h(c, t, color="#FFFFFF", a=0.6, n=40, seed=1, y0=0, y1=H, speed=4200, dir=-1):
    """Horizontal streaks for whip pans / dashes."""
    for i in range(n):
        y = y0 + (y1 - y0) * hrand(seed, i)
        L = 200 + 700 * hrand(seed, i, "l")
        v = speed * (0.6 + 0.8 * hrand(seed, i, "v"))
        x = ((hrand(seed, i, "x") * (W + L) + dir * v * t) % (W + 2 * L)) - L
        w = 2 + 6 * hrand(seed, i, "w")
        c.drawRect(skia.Rect.MakeXYWH(x, y, L, w), fill(color, a * (0.4 + 0.6 * hrand(seed, i, "a"))))


def sparkle(c, x, y, r, color="#FFFFFF", a=1.0, rot=0.0, glow=True):
    if r <= 0.5 or a <= 0:
        return
    if glow:
        c.drawCircle(x, y, r * 0.9, fill(color, a * 0.35, blur=r * 0.5))
    c.drawPath(path(star_pts(x, y, r, r * 0.18, 4, rot - math.pi / 2), True, smooth=False), fill(color, a))
    c.drawCircle(x, y, r * 0.16, fill("#FFFFFF", a))


def glow_circle(c, x, y, r, color, a=1.0):
    c.drawCircle(x, y, r, fill("#000000", a, shader=rad(x, y, r, [col(color, 1), col(color, 0)])))


_tone = {}


def screentone(level, size=9.0):
    """Manga halftone dot shader. level 0..1 = ink coverage."""
    key = (round(level, 2), size)
    if key not in _tone:
        s = int(size)
        n = s * 8
        yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) + 0.5
        # checkerboard lattice = dots on a 45-degree grid, seamless over the tile
        px, py = xx % (2 * s), yy % (2 * s)
        d = np.full(px.shape, 1e9, np.float32)
        for ox, oy in ((0, 0), (2 * s, 0), (0, 2 * s), (2 * s, 2 * s), (s, s)):
            d = np.minimum(d, np.hypot(px - ox, py - oy))
        r = s * math.sqrt(2 * level / math.pi)
        ink = np.clip(r - d + 0.5, 0, 1)
        img = np.zeros((n, n, 4), np.uint8)
        img[..., 0] = 0x1B
        img[..., 1] = 0x14
        img[..., 2] = 0x26
        img[..., 3] = (ink * 255).astype(np.uint8)
        im = skia.Image.fromarray(img, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType)
        _tone[key] = im
    return _tone[key].makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat)


def tone_fill(c, p, level, size=9.0, a=1.0):
    c.drawPath(p, fill("#000000", a, shader=screentone(level, size)))


# ----------------------------------------------------------------------------- frame io
def new_surface():
    return skia.Surface(W, H)


def frame_to_rgb(surface):
    a = surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
    return np.ascontiguousarray(a[:, :, :3])
