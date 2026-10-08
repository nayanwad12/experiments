"""theme: the "ink & highlighter" look for the SYSTEM reel (Vox-style explainer collage).

Newsprint paper, ink black, highlighter yellow, marker red. Anton for kinetic type, Instrument Serif
italic for editorial asides, JetBrains Mono for labels and UI. Everything hand-made looking: ragged
highlighter swipes, marker strokes that draw on, rubber stamps, masking-tape labels, halftone dots.
"""

import math
import sys
from pathlib import Path

import numpy as np
import skia

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "reels" / "common"))
from kit import (W, H, clamp, e_back, e_in, e_io, e_out, fill, font, hrand, lerp, measure, prog,  # noqa: E402,F401
                 rgb, spring, stroke)

PAPER = "#F2ECE1"
PAPER_D = "#E4DCCD"
INK = "#121212"
YEL = "#FFD43B"
RED = "#FF3B2F"
WHITE = "#FFFFFF"
BLUE = "#2D5BFF"
SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNone)


def col(c, a=1.0):
    r, g, b = rgb(c)
    return skia.Color(r, g, b, int(255 * clamp(a)))


# ---------------------------------------------------------------- textures (built once per process)
_TEX = {}


def _fbm(h, w, seed, octaves=5):
    g = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        s = 2 ** (o + 2)
        n = g.standard_normal((h // s + 2, w // s + 2)).astype(np.float32)
        n = np.repeat(np.repeat(n, s, 0), s, 1)[:h, :w]
        k = max(1, s // 2) * 2 + 1
        ker = np.ones(k, np.float32) / k
        n = np.apply_along_axis(lambda r: np.convolve(r, ker, "same"), 1, n)
        n = np.apply_along_axis(lambda r: np.convolve(r, ker, "same"), 0, n)
        out += n * amp
        tot += amp
        amp *= 0.55
    out /= tot
    return (out - out.mean()) / (out.std() + 1e-6)


def paper_tex():
    """grey multiply texture for paper: fibres + blotches."""
    if "paper" not in _TEX:
        h, w = H // 2, W // 2
        n = _fbm(h, w, 3) * 0.6 + np.random.default_rng(4).standard_normal((h, w)).astype(np.float32) * 0.35
        v = np.clip(235 + n * 9, 200, 255).astype(np.uint8)
        a = np.dstack([v, v, v, np.full_like(v, 255)])
        img = skia.Image.fromarray(a, colorType=skia.kRGBA_8888_ColorType)
        _TEX["paper"] = img
    return _TEX["paper"]


def paper_bg(c, color=PAPER, rect=None, tex=0.9):
    r = rect or skia.Rect.MakeWH(W, H)
    c.drawRect(r, fill(color))
    p = skia.Paint(BlendMode=skia.BlendMode.kMultiply, Alphaf=tex)
    c.save()
    c.clipRect(r)
    c.drawImageRect(paper_tex(), skia.Rect.MakeWH(W, H), SAMP, p)
    c.restore()


def halftone(c, cx, cy, r_max, color, spacing=26, dot=11, a=1.0, rect=None, rot=0.0):
    """radial-fade halftone dots centred on (cx, cy)."""
    r = rect or skia.Rect.MakeWH(W, H)
    p = fill(color, a)
    c.save()
    c.clipRect(r)
    c.translate(cx, cy)
    c.rotate(rot)
    n = int(r_max / spacing) + 2
    path = skia.Path()
    for iy in range(-n, n + 1):
        for ix in range(-n, n + 1):
            x, y = ix * spacing + (spacing / 2 if iy % 2 else 0), iy * spacing
            d = math.hypot(x, y) / r_max
            if d >= 1:
                continue
            rr = dot * (1 - d) ** 0.8
            if rr > 0.6:
                path.addCircle(x, y, rr)
    c.drawPath(path, p)
    c.restore()


def rays(c, cx, cy, n, color, a=1.0, rot=0.0, r=2600):
    path = skia.Path()
    for i in range(n):
        a0 = rot + i * 2 * math.pi / n
        a1 = a0 + math.pi / n
        path.moveTo(cx, cy)
        path.lineTo(cx + r * math.cos(a0), cy + r * math.sin(a0))
        path.lineTo(cx + r * math.cos(a1), cy + r * math.sin(a1))
        path.close()
    c.drawPath(path, fill(color, a))


# ---------------------------------------------------------------- hand-made marks
def _jitter(seed, i, amp):
    return (hrand(seed, i, 1) - 0.5) * 2 * amp


def hilite(c, x, y, w, h, k, color=YEL, seed=0, a=0.95, rot=-1.5):
    """highlighter swipe revealed left to right by k (0..1). (x, y) top-left."""
    if k <= 0:
        return
    k = e_out(k)
    ww = w * k
    c.save()
    c.translate(x, y + h / 2)
    c.rotate(rot)
    path = skia.Path()
    steps = 10
    path.moveTo(_jitter(seed, 0, 6), -h / 2 + _jitter(seed, 1, 4))
    for i in range(1, steps + 1):
        path.lineTo(ww * i / steps, -h / 2 + _jitter(seed, i + 2, 4))
    path.lineTo(ww + _jitter(seed, 40, 8), 0)
    for i in range(steps, -1, -1):
        path.lineTo(ww * i / steps, h / 2 + _jitter(seed, i + 20, 4))
    path.close()
    c.drawPath(path, fill(color, a))
    c.restore()


def marker(c, pts, k, color=RED, width=16, a=1.0, smooth=True):
    """marker stroke through pts, drawn on by k (0..1)."""
    if k <= 0 or len(pts) < 2:
        return
    path = skia.Path()
    path.moveTo(*pts[0])
    if smooth and len(pts) > 2:
        for i in range(1, len(pts) - 1):
            mx, my = (pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2
            path.quadTo(pts[i][0], pts[i][1], mx, my)
        path.lineTo(*pts[-1])
    else:
        for p in pts[1:]:
            path.lineTo(*p)
    p = stroke(color, width, a)
    if k < 1:
        p.setPathEffect(skia.TrimPathEffect.Make(0, clamp(k)))
    c.drawPath(path, p)


def scribble_ellipse(c, cx, cy, rx, ry, k, color=RED, width=12, seed=0, turns=1.15):
    n = 48
    pts = []
    for i in range(int(n * turns) + 1):
        th = -math.pi * 0.6 + 2 * math.pi * i / n
        wob = 1 + 0.05 * math.sin(i * 0.7 + seed) + 0.03 * (i / n)
        pts.append((cx + rx * wob * math.cos(th), cy + ry * wob * math.sin(th)))
    marker(c, pts, k, color, width)


def check_mark(c, x, y, s, k, color=RED, width=22):
    marker(c, [(x - 0.5 * s, y), (x - 0.15 * s, y + 0.38 * s), (x + 0.6 * s, y - 0.55 * s)], k, color, width,
           smooth=False)


def arrow(c, x0, y0, x1, y1, k, color=INK, width=9, bend=0.25, head=34):
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    nx, ny = -(y1 - y0) * bend, (x1 - x0) * bend
    pts = []
    for i in range(21):
        s = i / 20
        qx = (1 - s) ** 2 * x0 + 2 * (1 - s) * s * (mx + nx) + s ** 2 * x1
        qy = (1 - s) ** 2 * y0 + 2 * (1 - s) * s * (my + ny) + s ** 2 * y1
        pts.append((qx, qy))
    marker(c, pts, k, color, width, smooth=False)
    if k > 0.85:
        dx, dy = pts[-1][0] - pts[-3][0], pts[-1][1] - pts[-3][1]
        ang = math.atan2(dy, dx)
        hk = e_out((k - 0.85) / 0.15)
        for sgn in (-1, 1):
            a2 = ang + math.pi + sgn * 0.5
            marker(c, [(x1, y1), (x1 + head * hk * math.cos(a2), y1 + head * hk * math.sin(a2))], 1, color, width,
                   smooth=False)


# ---------------------------------------------------------------- type
def block_text(c, s, x, y, size, name="anton", color=YEL, shadow=INK, depth=0.06, outline=0, a=1.0, anchor="c",
               tracking=0.0):
    """chunky text with a solid offset (block) shadow. y is the baseline."""
    d = size * depth
    f = font(name, size)
    w = measure(s, name, size, tracking)
    x0 = x - w / 2 if anchor == "c" else x - w if anchor == "r" else x

    def draw(p, ox, oy):
        if not tracking:
            c.drawString(s, x0 + ox, y + oy, f, p)
        else:
            xx = x0 + ox
            for ch in s:
                c.drawString(ch, xx, y + oy, f, p)
                xx += f.measureText(ch) + tracking * size

    if shadow and d:
        sp = fill(shadow, a)
        for i in range(1, 7):
            draw(sp, d * i / 6, d * i / 6)
    if outline:
        draw(stroke(shadow or INK, outline, a), 0, 0)
    draw(fill(color, a), 0, 0)
    return x0, w


def kinetic(c, s, x, y, size, t, t0, name="anton", color=YEL, shadow=INK, depth=0.06, stagger=0.035,
            dur=0.32, a=1.0, from_y=0.55, rot=0.0, tracking=0.0, t_out=None, out_dur=0.18, maxw=1000):
    """letters pop up one by one (spring), optional fall-away at t_out. Shrinks to fit maxw."""
    if t < t0:
        return
    w = measure(s, name, size, tracking)
    if w > maxw:
        size *= maxw / w
    f = font(name, size)
    w = measure(s, name, size, tracking)
    xx = x - w / 2
    for i, ch in enumerate(s):
        cw = f.measureText(ch)
        k = clamp((t - t0 - i * stagger) / dur)
        if k <= 0:
            xx += cw + tracking * size
            continue
        sp = spring(k * dur, w=22, z=0.45)
        yy = y + (1 - sp) * size * from_y
        sc = 0.6 + 0.4 * sp
        aa = a * clamp(k * 3)
        if t_out is not None and t > t_out:
            ko = clamp((t - t_out - i * stagger * 0.5) / out_dur)
            yy -= e_in(ko) * size * 0.5
            aa *= 1 - ko
        c.save()
        c.translate(xx + cw / 2, yy)
        c.rotate(rot + (hrand(s, i) - 0.5) * 6 * (1 - sp))
        c.scale(sc, sc)
        block_text(c, ch, 0, 0, size, name, color, shadow, depth, a=aa)
        c.restore()
        xx += cw + tracking * size


def stamp(c, s, x, y, size, k, color=RED, rot=-8, name="anton", pad=0.28, a=1.0, fill_bg=None):
    """rubber stamp: slams in from 1.8x."""
    if k <= 0:
        return
    sc = lerp(1.9, 1.0, e_out(clamp(k / 0.45))) if k < 0.45 else 1 + 0.06 * math.sin(clamp((k - 0.45) / 0.3) * math.pi) * (1 - clamp((k - 0.45) / 0.3))
    aa = a * clamp(k / 0.15)
    w = measure(s, name, size)
    cap = font(name, size).getMetrics().fCapHeight
    bw, bh = w + size * pad * 2, cap + size * pad * 2
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.scale(sc, sc)
    r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-bw / 2, -bh / 2, bw, bh), size * 0.12, size * 0.12)
    if fill_bg:
        c.drawRRect(r, fill(fill_bg, aa))
    c.drawRRect(r, stroke(color, size * 0.09, aa))
    c.drawString(s, -w / 2, cap / 2, font(name, size), fill(color, aa))
    c.restore()


def tape(c, s, x, y, size=34, k=1.0, rot=-3, name="monob", bg="#F7F1D9", fg=INK, a=1.0, seed=0):
    """masking-tape label centred on (x, y)."""
    if k <= 0:
        return
    sc = lerp(0.6, 1.0, e_back(clamp(k / 0.5)))
    aa = a * clamp(k / 0.2)
    w = measure(s, name, size) + size * 1.1
    h = size * 1.6
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.scale(sc, sc)
    path = skia.Path()
    n = 7
    path.moveTo(-w / 2, -h / 2)
    path.lineTo(w / 2, -h / 2)
    for i in range(n + 1):
        path.lineTo(w / 2 + (6 if i % 2 else -2) + _jitter(seed, i, 2), -h / 2 + h * i / n)
    path.lineTo(-w / 2, h / 2)
    for i in range(n, -1, -1):
        path.lineTo(-w / 2 + (-6 if i % 2 else 2) + _jitter(seed, i + 9, 2), -h / 2 + h * i / n)
    path.close()
    c.drawPath(path, fill("#000000", 0.18 * aa, blur=6))
    c.drawPath(path, fill(bg, 0.94 * aa))
    cap = font(name, size).getMetrics().fCapHeight
    c.drawString(s, -measure(s, name, size) / 2, cap / 2, font(name, size), fill(fg, aa))
    c.restore()


def card(c, x, y, w, h, color=PAPER, r=18, shadow=0.3, border=None, bw=5):
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r)
    if shadow:
        c.drawRRect(rr.makeOffset(8, 12), fill("#000000", shadow, blur=14))
    c.drawRRect(rr, fill(color))
    if border:
        c.drawRRect(rr, stroke(border, bw))
