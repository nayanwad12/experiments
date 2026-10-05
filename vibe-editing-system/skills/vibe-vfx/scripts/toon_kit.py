"""toon_kit: handmade looks on top of motion_kit: clay, crayon, paper-cut, doodles, simple characters.

    from motion_kit import *
    from toon_kit import *

    PAPER = paper_texture(1920, 1080, "#F2EEE3")           # build once, at module level
    def draw(c, t):
        ts = stepped(t, 12)                                  # animate "on twos" (12 drawings/s)
        c.drawImage(PAPER, 0, 0)
        blob(c, 960, 600, 180, rgb("#FFCFD8"), ts, seed=1, style="clay")      # a boiling clay blob
        doodle_line(c, [(200, 900), (600, 860), (900, 920)], rgb("#0B0B0D"), 8, ts)
        eyes(c, 900, 540, 30, t, look=(0.3, 0), blink_every=3.1)

Core ideas
  stepped(t, 12)   hold each drawing for 2 frames at 24 fps. This is the main thing that makes it feel handmade.
  boil             outlines re-wobble a little every drawing (seeded by the stepped time), like real clay/crayon.
  texture          a paper/clay grain image multiplied over shapes.
"""

import math
import sys
from pathlib import Path

import numpy as np
import skia

sys.path.insert(0, str(Path(__file__).resolve().parent))
from motion_kit import clamp, hex_rgb, noise1  # noqa: E402


# ------------------------------------------------------------------ time
def stepped(t, drawings_per_second=12):
    """Quantise time so motion advances in held drawings (stop-motion / hand-drawn feel)."""
    return math.floor(t * drawings_per_second) / drawings_per_second


def boil_seed(ts, rate=12):
    return int(round(ts * rate))


# ------------------------------------------------------------------ textures (build once at module level)
def paper_texture(w, h, base="#F2EEE3", grain=0.06, fibres=True, seed=3):
    """Warm paper with grain and soft fibres as a skia Image."""
    rng = np.random.default_rng(seed)
    r, g, b = hex_rgb(base)
    n = rng.normal(0, 1, (h // 2, w // 2)).astype(np.float32)
    from scipy.ndimage import gaussian_filter, zoom
    low = gaussian_filter(rng.normal(0, 1, (h // 16 + 1, w // 16 + 1)).astype(np.float32), 1.5)
    low = zoom(low, (h / low.shape[0], w / low.shape[1]), order=1)[:h, :w]
    fine = zoom(gaussian_filter(n, 0.6), 2, order=1)[:h, :w]
    tex = 1 + grain * (0.6 * fine + 0.8 * low)
    if fibres:
        for _ in range(int(w * h / 9000)):
            x, y = rng.integers(0, w), rng.integers(0, h)
            ln, ang = rng.integers(6, 28), rng.uniform(0, math.pi)
            for k in range(ln):
                xx, yy = int(x + k * math.cos(ang)), int(y + k * math.sin(ang))
                if 0 <= xx < w and 0 <= yy < h:
                    tex[yy, xx] *= 0.96
    img = np.empty((h, w, 4), np.uint8)
    for i, ch in enumerate((r, g, b)):
        img[..., i] = np.clip(ch * tex, 0, 255)
    img[..., 3] = 255
    return skia.Image.fromarray(img, colorType=skia.kRGBA_8888_ColorType)


def grain_overlay(w, h, amount=0.08, seed=5):
    """Neutral grain as a translucent image. Draw it on top with blend mode multiply/overlay."""
    rng = np.random.default_rng(seed)
    v = np.clip(128 + rng.normal(0, 255 * amount, (h, w)), 0, 255).astype(np.uint8)
    img = np.stack([v, v, v, np.full_like(v, 255)], -1)
    return skia.Image.fromarray(img, colorType=skia.kRGBA_8888_ColorType)


def draw_texture(c, img, mode=skia.BlendMode.kMultiply, alpha=1.0):
    c.drawImage(img, 0, 0, skia.SamplingOptions(), skia.Paint(BlendMode=mode, Alphaf=alpha))


# ------------------------------------------------------------------ wobbly shapes
def wobble_points(pts, amp, ts, seed=0, closed=True):
    """Jitter a polygon's points differently for every drawing (boil)."""
    s = boil_seed(ts)
    out = []
    for i, (x, y) in enumerate(pts):
        out.append((x + amp * noise1(i * 1.7 + s * 3.1, seed), y + amp * noise1(i * 2.3 + s * 2.7, seed + 9)))
    return out


def smooth_path(pts, closed=True):
    """Catmull-Rom through points -> skia.Path (soft, organic outlines)."""
    p = skia.Path()
    n = len(pts)
    if n < 2:
        return p
    p.moveTo(*pts[0])
    rng_ = range(n if closed else n - 1)
    for i in rng_:
        p0 = pts[(i - 1) % n] if closed or i > 0 else pts[i]
        p1, p2 = pts[i], pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if closed or i + 2 < n else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        p.cubicTo(*c1, *c2, *p2)
    if closed:
        p.close()
    return p


def blob_points(cx, cy, r, n=14, squash=1.0, lump=0.06, seed=0):
    """Organic round shape. squash>1 = wider and flatter (landing), <1 = tall (stretch)."""
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        rr = r * (1 + lump * noise1(i * 0.9, seed))
        pts.append((cx + rr * math.cos(a) * squash, cy + rr * math.sin(a) / squash))
    return pts


def blob(c, cx, cy, r, col, ts, seed=0, squash=1.0, style="clay", outline=None, boil=None):
    """A boiling organic shape. style: clay (soft 3D shading), flat, paper (drop shadow + flat)."""
    amp = boil if boil is not None else r * 0.025
    path = smooth_path(wobble_points(blob_points(cx, cy, r, squash=squash, seed=seed), amp, ts, seed))
    shaded(c, path, col, style, light=(cx - r * 0.4, cy - r * 0.5), size=r)
    if outline:
        c.drawPath(path, skia.Paint(Color=outline, AntiAlias=True, Style=skia.Paint.kStroke_Style,
                                    StrokeWidth=max(2, r * 0.04), StrokeJoin=skia.Paint.kRound_Join))
    return path


def shaded(c, path, col, style="clay", light=None, size=100):
    col4 = skia.Color4f(col)
    if style == "paper":
        c.save()
        c.translate(size * 0.04, size * 0.06)
        c.drawPath(path, skia.Paint(Color=skia.Color(0, 0, 0, 60), AntiAlias=True,
                                    MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, size * 0.05)))
        c.restore()
        c.drawPath(path, skia.Paint(Color4f=col4, AntiAlias=True))
        return
    if style == "flat":
        c.drawPath(path, skia.Paint(Color4f=col4, AntiAlias=True))
        return
    # clay: cast shadow, base, radial key light, darker rim, soft highlight
    b = path.getBounds()
    c.save()
    c.translate(size * 0.05, size * 0.09)
    c.drawPath(path, skia.Paint(Color=skia.Color(0, 0, 0, 55), AntiAlias=True,
                                MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, size * 0.08)))
    c.restore()
    lx, ly = light or (b.centerX() - b.width() * 0.2, b.centerY() - b.height() * 0.25)
    lighter = skia.Color4f(min(1, col4.fR * 1.15 + 0.06), min(1, col4.fG * 1.15 + 0.06), min(1, col4.fB * 1.15 + 0.06), 1)
    darker = skia.Color4f(col4.fR * 0.62, col4.fG * 0.62, col4.fB * 0.66, 1)
    shader = skia.GradientShader.MakeRadial((lx, ly), max(b.width(), b.height()) * 0.85,
                                            [lighter.toColor(), col4.toColor(), darker.toColor()], [0.0, 0.55, 1.0])
    c.drawPath(path, skia.Paint(Shader=shader, AntiAlias=True))
    hl = skia.Paint(Color=skia.Color(255, 255, 255, 70), AntiAlias=True,
                    MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, size * 0.06))
    c.drawOval(skia.Rect.MakeXYWH(lx - size * 0.18, ly - size * 0.1, size * 0.3, size * 0.16), hl)


# ------------------------------------------------------------------ hand-drawn lines and fills
def doodle_line(c, pts, col, width, ts, seed=0, passes=2, jitter=None, closed=False):
    """Shaky marker/crayon line drawn twice, like a real hand."""
    jitter = jitter if jitter is not None else width * 0.35
    for k in range(passes):
        wp = wobble_points(pts, jitter, ts, seed + k * 17, closed)
        p = smooth_path(wp, closed)
        c.drawPath(p, skia.Paint(Color=col, AntiAlias=True, Style=skia.Paint.kStroke_Style,
                                 StrokeWidth=width * (1 if k == 0 else 0.6), StrokeCap=skia.Paint.kRound_Cap,
                                 StrokeJoin=skia.Paint.kRound_Join, Alphaf=0.95 if k == 0 else 0.55))


def hatch_fill(c, path, col, ts, spacing=10, angle=-0.6, width=4, seed=0, alpha=0.9):
    """Scribble-fill a shape with zig-zag crayon strokes, clipped to the shape."""
    b = path.getBounds()
    c.save()
    c.clipPath(path, doAntiAlias=True)
    s = boil_seed(ts)
    ca, sa = math.cos(angle), math.sin(angle)
    diag = math.hypot(b.width(), b.height())
    cx, cy = b.centerX(), b.centerY()
    p = skia.Path()
    i, first = 0, True
    d = -diag / 2
    while d < diag / 2:
        j = spacing * 0.35 * noise1(i * 0.7 + s, seed)
        x0, y0 = cx + (d + j) * -sa - diag / 2 * ca, cy + (d + j) * ca - diag / 2 * sa
        x1, y1 = cx + (d + j) * -sa + diag / 2 * ca, cy + (d + j) * ca + diag / 2 * sa
        if first:
            p.moveTo(x0, y0)
            first = False
        (p.lineTo(x1, y1) if i % 2 == 0 else p.lineTo(x0, y0))
        nxt = d + spacing
        if i % 2 == 0:
            p.lineTo(cx + nxt * -sa + diag / 2 * ca, cy + nxt * ca + diag / 2 * sa)
        else:
            p.lineTo(cx + nxt * -sa - diag / 2 * ca, cy + nxt * ca - diag / 2 * sa)
        d = nxt
        i += 1
    c.drawPath(p, skia.Paint(Color=col, AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=width,
                             StrokeJoin=skia.Paint.kRound_Join, Alphaf=alpha))
    c.restore()


def draw_on(path, k):
    """Return the first k (0..1) of a path, for 'drawn on' strokes (sketch-in, signature, arrows)."""
    pm = skia.PathMeasure(path, False)
    out = skia.Path()
    lengths = []
    while True:
        lengths.append(pm.getLength())
        if not pm.nextContour():
            break
    total = sum(lengths)
    pm = skia.PathMeasure(path, False)
    remaining = total * clamp(k)
    for ln in lengths:
        if remaining <= 0:
            break
        pm.getSegment(0, min(ln, remaining), out, True)
        remaining -= ln
        pm.nextContour()
    return out


# ------------------------------------------------------------------ characters
def blink(t, every=3.3, dur=0.14, seed=0):
    """0 = open, 1 = closed. Irregular blinks feel alive."""
    period = every * (1 + 0.25 * noise1(math.floor(t / every) + seed, 4))
    ph = (t % period) / dur
    return 1 - abs(ph * 2 - 1) if ph < 1 else 0.0


def eyes(c, cx, cy, r, t, look=(0.0, 0.0), gap=None, blink_every=3.3, white="#FFFFFF", ink="#0B0B0D", seed=0):
    """A pair of cartoon eyes with pupils looking at `look` (-1..1, -1..1) and natural blinks."""
    gap = gap or r * 2.4
    bl = blink(t, blink_every, seed=seed)
    for side in (-1, 1):
        x = cx + side * gap / 2
        c.save()
        c.translate(x, cy)
        c.scale(1, max(0.08, 1 - bl))
        c.drawOval(skia.Rect.MakeXYWH(-r, -r * 1.15, 2 * r, 2.3 * r), skia.Paint(Color=skia.Color(*hex_rgb(white)), AntiAlias=True))
        c.drawCircle(look[0] * r * 0.45, look[1] * r * 0.5, r * 0.48, skia.Paint(Color=skia.Color(*hex_rgb(ink)), AntiAlias=True))
        c.drawCircle(look[0] * r * 0.45 - r * 0.15, look[1] * r * 0.5 - r * 0.18, r * 0.13, skia.Paint(Color=skia.ColorWHITE, AntiAlias=True))
        c.restore()


def squash_stretch(vel, k=0.0015, limit=0.35):
    """Scale (sx, sy) from vertical velocity in px/s: stretch when moving fast, keep volume."""
    s = clamp(1 + abs(vel) * k, 1, 1 + limit)
    return 1 / math.sqrt(s), s


def mouth_open_curve(wav_path, fps, smooth=0.5):
    """Per-frame mouth openness 0..1 from a voice file (simple, convincing lip-flap)."""
    import audio_kit as ak
    x = ak.read_audio(wav_path).mean(1)
    hop = int(ak.SR / fps)
    n = len(x) // hop
    rms = np.sqrt(np.mean(x[: n * hop].reshape(n, hop) ** 2, axis=1))
    rms = rms / (np.percentile(rms, 95) + 1e-6)
    out = np.zeros(n, np.float32)
    acc = 0.0
    for i, v in enumerate(np.clip(rms, 0, 1)):
        acc = smooth * acc + (1 - smooth) * v
        out[i] = acc
    return out


def mouth(c, cx, cy, w, open_k, ink="#0B0B0D", inside="#7A2E3A"):
    """Cartoon mouth from a smile line (0) to an open 'O' (1)."""
    h = w * 0.08 + w * 0.55 * clamp(open_k)
    if open_k < 0.08:
        p = skia.Path()
        p.moveTo(cx - w / 2, cy)
        p.quadTo(cx, cy + w * 0.25, cx + w / 2, cy)
        c.drawPath(p, skia.Paint(Color=skia.Color(*hex_rgb(ink)), AntiAlias=True, Style=skia.Paint.kStroke_Style,
                                 StrokeWidth=w * 0.08, StrokeCap=skia.Paint.kRound_Cap))
        return
    r = skia.Rect.MakeXYWH(cx - w * 0.38, cy - h * 0.3, w * 0.76, h)
    c.drawOval(r, skia.Paint(Color=skia.Color(*hex_rgb(inside)), AntiAlias=True))
    c.drawOval(r, skia.Paint(Color=skia.Color(*hex_rgb(ink)), AntiAlias=True, Style=skia.Paint.kStroke_Style,
                             StrokeWidth=w * 0.06))
