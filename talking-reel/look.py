"""look: the design system for the Vibe Editing System reel, pulled from the reference pin.

Reference: olive-green ground, retro photo cards with torn, burnt rounded edges, soft-glowing cream brush
lettering, chunky cream grotesk caps in tight blocks, a line-drawn smiley sticker, warm faded film colour
(tomato reds, cream whites), grain. No brand names or logos are taken from it.

    OLIVE ground / CREAM type / TOMATO accent / PINK second accent / INK
    brush   -> Caveat Brush (glowing headline words, like the reference "Tutorial")
    caps    -> Montserrat Black (captions, small-caps blocks)
    serif   -> Instrument Serif italic (asides)
    mono    -> JetBrains Mono (labels, UI)
"""

import math
import sys
from pathlib import Path

import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "reels" / "common"))
sys.path.insert(0, str(HERE.parent / "system-reel"))
import kit  # noqa: E402
from kit import (W, H, clamp, e_back, e_in, e_io, e_out, fill, font, hrand, lerp, measure, prog,  # noqa: E402,F401
                 rgb, spring, stroke)
from theme import arrow, check_mark, hilite, marker, scribble_ellipse  # noqa: E402,F401

OLIVE = "#4D5E21"
OLIVE_D = "#323D13"
OLIVE_L = "#6A7B32"
CREAM = "#F4EDB6"
PAPER = "#EFE7D2"
TOMATO = "#E2472C"
PINK = "#EE8E9E"
INK = "#17190F"
WHITE = "#FFFDF4"
SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNone)


def col(c, a=1.0):
    r, g, b = rgb(c)
    return skia.Color(r, g, b, int(255 * clamp(a)))


# ---------------------------------------------------------------- grounds
_TEX = {}


def _noise_img(key, seed, lo, hi, blur=0):
    if key not in _TEX:
        g = np.random.default_rng(seed)
        h, w = H // 4, W // 4
        n = g.standard_normal((h, w)).astype(np.float32)
        if blur:
            import cv2
            n = cv2.GaussianBlur(n, (0, 0), blur)
            n = (n - n.mean()) / (n.std() + 1e-6)
        v = np.clip((lo + hi) / 2 + n * (hi - lo) / 4, 0, 255).astype(np.uint8)
        _TEX[key] = skia.Image.fromarray(np.dstack([v, v, v, np.full_like(v, 255)]), colorType=skia.kRGBA_8888_ColorType)
    return _TEX[key]


def ground(c, color=OLIVE, rect=None, t=0.0, leak=True):
    """flat colour ground with soft mottling, a darker edge and a slow warm light leak (reference look)."""
    r = rect or skia.Rect.MakeWH(W, H)
    c.save()
    c.clipRect(r)
    c.drawRect(r, fill(color))
    c.drawImageRect(_noise_img("mottle", 7, 205, 255, blur=6), r, SAMP,
                    skia.Paint(BlendMode=skia.BlendMode.kMultiply, Alphaf=0.55))
    if leak:
        cx = r.left() + r.width() * (0.75 + 0.15 * math.sin(t * 0.7))
        cy = r.top() + r.height() * (0.18 + 0.05 * math.cos(t * 0.5))
        p = kit.rad_grad(cx, cy, r.width() * 0.8, ["#FFB46A", "#FFB46A"], [0, 1], a=1)
        p.setShader(skia.GradientShader.MakeRadial(skia.Point(cx, cy), r.width() * 0.8,
                                                   [col("#FFB46A", 0.22), col("#FFB46A", 0)]))
        p.setBlendMode(skia.BlendMode.kScreen)
        c.drawRect(r, p)
    p = skia.Paint(Shader=skia.GradientShader.MakeRadial(
        skia.Point(r.centerX(), r.centerY()), max(r.width(), r.height()) * 0.75,
        [col("#000000", 0), col("#000000", 0.38)], [0.55, 1.0]))
    c.drawRect(r, p)
    c.restore()


# ---------------------------------------------------------------- torn photo cards
def torn_path(x, y, w, h, r=34, seed=0, rough=5.0, step=14):
    """rounded rect with a rough, torn paper edge."""
    pts = []
    corners = [(x + w - r, y + r, -90), (x + w - r, y + h - r, 0), (x + r, y + h - r, 90), (x + r, y + r, 180)]
    edges = [((x + r, y), (x + w - r, y)), ((x + w, y + r), (x + w, y + h - r)),
             ((x + w - r, y + h), (x + r, y + h)), ((x, y + h - r), (x, y + r))]
    k = 0
    for (cx, cy, a0), ((ex0, ey0), (ex1, ey1)) in zip([corners[3], corners[0], corners[1], corners[2]], edges):
        for j in range(7):
            a = math.radians(a0 + 90 * j / 6)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        n = max(2, int(math.hypot(ex1 - ex0, ey1 - ey0) / step))
        nx, ny = (ey1 - ey0), -(ex1 - ex0)
        ln = math.hypot(nx, ny) or 1
        nx, ny = nx / ln, ny / ln
        for j in range(1, n):
            s = j / n
            jit = (hrand(seed, k, 3) - 0.5) * 2 * rough + (hrand(seed, k // 4, 9) - 0.5) * rough * 1.6
            k += 1
            pts.append((ex0 + (ex1 - ex0) * s + nx * jit, ey0 + (ey1 - ey0) * s + ny * jit))
    path = skia.Path()
    path.moveTo(*pts[0])
    for p in pts[1:]:
        path.lineTo(*p)
    path.close()
    return path


def photo_card(c, img, x, y, w, h, seed=0, src_rect=None, burn=0.85, shadow=0.45, rot=0.0, a=1.0, glow=True):
    """footage inside a torn, edge-burnt retro photo card (the reference's stacked photos)."""
    c.save()
    c.translate(x + w / 2, y + h / 2)
    c.rotate(rot)
    c.translate(-w / 2, -h / 2)
    path = torn_path(0, 0, w, h, r=min(w, h) * 0.06, seed=seed)
    if shadow:
        sh = skia.Path(path)
        sh.offset(6, 14)
        c.drawPath(sh, fill("#000000", shadow * a, blur=18))
    c.save()
    c.clipPath(path, skia.ClipOp.kIntersect, True)
    dst = skia.Rect.MakeWH(w, h)
    p = skia.Paint(Alphaf=a)
    if src_rect is not None:
        c.drawImageRect(img, src_rect, dst, SAMP, p)
    else:
        c.drawImageRect(img, dst, SAMP, p)
    # burnt edge: warm dark falloff + a thin cream halation line
    if burn:
        for i, (wd, al, cc) in enumerate(((60, 0.55, "#2A1A08"), (26, 0.5, "#6B3A12"))):
            c.drawPath(path, stroke(cc, wd, al * burn * a, blur=wd * 0.45))
    c.restore()
    if glow:
        c.drawPath(path, stroke(CREAM, 3, 0.35 * a, blur=4))
    c.restore()
    return path


# ---------------------------------------------------------------- type
def glow_text(c, s, x, y, size, color=CREAM, name="caveat", a=1.0, anchor="c", glow=1.0, rot=0.0, maxw=None,
              tracking=0.0):
    """soft, blooming brush lettering (the reference 'Tutorial' title). y = baseline."""
    if a <= 0:
        return 0
    if maxw:
        w0 = measure(s, name, size, tracking)
        if w0 > maxw:
            size *= maxw / w0
    w = measure(s, name, size, tracking)
    x0 = -w / 2 if anchor == "c" else -w if anchor == "r" else 0
    f = font(name, size)
    c.save()
    c.translate(x, y)
    c.rotate(rot)

    def draw(p, dx=0, dy=0):
        if not tracking:
            c.drawString(s, x0 + dx, dy, f, p)
        else:
            xx = x0 + dx
            for ch in s:
                c.drawString(ch, xx, dy, f, p)
                xx += f.measureText(ch) + tracking * size

    if glow:
        draw(fill(color, 0.55 * a * glow, blur=size * 0.16))
        draw(fill(color, 0.5 * a * glow, blur=size * 0.05))
        draw(fill(color, 0.35 * a, blur=2), size * 0.012, size * 0.01)
    draw(fill(color, a))
    c.restore()
    return w


def caps(c, s, x, y, size, color=CREAM, a=1.0, anchor="l", name="mont", tracking=-0.01, glow=0.0, outline=0,
         outline_color=INK):
    """heavy grotesk caps (the reference's small text block)."""
    if glow:
        kit.text(c, s, x, y, name, size, color=color, a=a * 0.5 * glow, anchor=anchor, tracking=tracking,
                 paint=fill(color, a * 0.45 * glow, blur=size * 0.12))
    return kit.text(c, s, x, y, name, size, color=color, a=a, anchor=anchor, tracking=tracking, outline=outline,
                    outline_color=outline_color)


def caps_block(c, lines, x, y, size, color=CREAM, a=1.0, lead=0.92, anchor="l", k=1.0):
    """stacked caps lines, revealed line by line by k (0..1)."""
    for i, ln in enumerate(lines):
        kk = clamp(k * len(lines) - i)
        if kk <= 0:
            continue
        caps(c, ln, x, y + i * size * lead + (1 - e_out(kk)) * size * 0.4, size, color, a * e_out(kk), anchor)


def mono(c, s, x, y, size=30, color=CREAM, a=1.0, anchor="l"):
    return kit.text(c, s, x, y, "monob", size, color=color, a=a, anchor=anchor)


def serif(c, s, x, y, size=60, color=CREAM, a=1.0, anchor="c"):
    return kit.text(c, s, x, y, "italic", size, color=color, a=a, anchor=anchor)


# ---------------------------------------------------------------- stickers
def smiley(c, x, y, r, color=CREAM, a=1.0, rot=0.0, k=1.0, width=None):
    """line-drawn smiley in a circle (the reference sticker, generic)."""
    if k <= 0:
        return
    s = lerp(0.4, 1.0, e_back(clamp(k / 0.6)))
    width = width or r * 0.09
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.scale(s, s)
    p = stroke(color, width, a)
    c.drawCircle(0, 0, r, fill(color, 0.25 * a, blur=r * 0.25) if False else p)
    c.drawCircle(0, 0, r, stroke(color, width * 2.2, 0.25 * a, blur=r * 0.12))
    c.drawLine(-r * 0.32, -r * 0.32, -r * 0.18, -r * 0.08, p)
    c.drawLine(r * 0.02, -r * 0.38, r * 0.14, -r * 0.14, p)
    path = skia.Path()
    path.moveTo(-r * 0.45, r * 0.2)
    path.quadTo(-r * 0.05, r * 0.72, r * 0.48, r * 0.02)
    c.drawPath(path, p)
    c.restore()


def pill(c, s, x, y, size=30, bg=CREAM, fg=INK, a=1.0, k=1.0, name="monob", anchor="c", rot=0.0, border=None):
    """rounded label pill centred on (x, y) (or left-anchored)."""
    if k <= 0:
        return 0
    sc = lerp(0.5, 1.0, e_back(clamp(k / 0.5)))
    aa = a * clamp(k / 0.2)
    tw = measure(s, name, size)
    w, h = tw + size * 1.2, size * 1.75
    c.save()
    c.translate(x + (w / 2 if anchor == "l" else 0), y)
    c.rotate(rot)
    c.scale(sc, sc)
    rr = kit.rrect(-w / 2, -h / 2, w, h, h / 2)
    c.drawRRect(rr.makeOffset(3, 6), fill("#000000", 0.25 * aa, blur=6))
    c.drawRRect(rr, fill(bg, aa))
    if border:
        c.drawRRect(rr, stroke(border, 3, aa))
    cap = font(name, size).getMetrics().fCapHeight
    c.drawString(s, -tw / 2, cap / 2, font(name, size), fill(fg, aa))
    c.restore()
    return w


def stamp(c, s, x, y, size, k, color=TOMATO, rot=-8, name="mont", pad=0.3, a=1.0, fill_bg=None, fg=None):
    """rubber stamp that slams in from 1.9x."""
    if k <= 0:
        return
    sc = lerp(1.9, 1.0, e_out(clamp(k / 0.4))) if k < 0.4 else 1.0
    aa = a * clamp(k / 0.12)
    w = measure(s, name, size)
    cap = font(name, size).getMetrics().fCapHeight
    bw, bh = w + size * pad * 2, cap + size * pad * 2
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.scale(sc, sc)
    r = kit.rrect(-bw / 2, -bh / 2, bw, bh, size * 0.16)
    if fill_bg:
        c.drawRRect(r.makeOffset(4, 8), fill("#000000", 0.3 * aa, blur=8))
        c.drawRRect(r, fill(fill_bg, aa))
    c.drawRRect(r, stroke(color, size * 0.08, aa))
    c.drawString(s, -w / 2, cap / 2, font(name, size), fill(fg or color, aa))
    c.restore()


def ui_card(c, x, y, w, h, bg=PAPER, r=26, a=1.0, border=None, shadow=0.35):
    rr = kit.rrect(x, y, w, h, r)
    if shadow:
        c.drawRRect(rr.makeOffset(6, 12), fill("#000000", shadow * a, blur=16))
    c.drawRRect(rr, fill(bg, a))
    if border:
        c.drawRRect(rr, stroke(border, 4, a))
    return rr


def pop_in(c, x, y, k, fn, rot=0.0, from_s=0.3):
    """scale-pop a drawing fn(c) around (x, y) by k."""
    if k <= 0:
        return
    s = lerp(from_s, 1.0, e_back(clamp(k)))
    c.save()
    c.translate(x, y)
    c.rotate(rot * (1 - e_out(k)))
    c.scale(s, s)
    c.translate(-x, -y)
    fn(c)
    c.restore()
