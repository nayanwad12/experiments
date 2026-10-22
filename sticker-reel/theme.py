"""theme: the "paper sticker scrapbook" look for the Vibe Editing System ad.

Built from the reference: ruled notebook paper (cream, faded blue rules, red margin), everything cut out as a
paper sticker (white die-cut border + soft drop shadow), black display serif for the plain words and a heavy
pink italic serif with a dark outline for the key words. Supporting faces: Courier Prime for typed labels,
Caveat for handwritten notes. Accents pulled from the reference stickers: taxi yellow, net-bag red.
"""

import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "reels" / "common"))
import kit  # noqa: E402
from kit import (W, H, clamp, e_back, e_in, e_io, e_out, fill, hrand, lerp, prog, rgb, rrect, spring,  # noqa: E402,F401
                 stroke)

F = HERE / "fonts"
kit.FONTS.update({
    "serif": str(F / "DMSerifDisplay-Regular.ttf"), "serifi": str(F / "DMSerifDisplay-Italic.ttf"),
    "pink": str(F / "PlayfairDisplay-BlackItalic.ttf"), "type": str(F / "CourierPrime-Bold.ttf"),
    "typer": str(F / "CourierPrime-Regular.ttf"), "hand": str(F / "Caveat-Bold.ttf"),
    "cond": str(F / "Oswald-Bold.ttf"),
})
font, measure = kit.font, kit.measure

# ---------------------------------------------------------------- palette (sampled from the reference)
PAPER = "#F3EBC4"      # notebook cream
PAPER_D = "#E6DCAE"
RULE = "#9DB3C9"       # faded blue rule
MARGIN = "#E0817F"     # red margin line
INK = "#151313"
PINK = "#EE7AA1"
PINK_D = "#3B0F1E"     # outline of the pink words
YEL = "#F5B414"        # taxi yellow
RED = "#D8343B"        # net-bag red
WHITE = "#FFFFFF"
KRAFT = "#C9A57A"
BLUSH = "#F6B9CB"
GRAPH = "#F6F3EA"
SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNone)


def col(c, a=1.0):
    r, g, b = rgb(c)
    return skia.Color(r, g, b, int(255 * clamp(a)))


# ---------------------------------------------------------------- paper (built once per process)
def _fbm(h, w, seed, octaves=5):
    g = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    import cv2
    for o in range(octaves):
        s = 2 ** (o + 1)
        n = g.standard_normal((h // s + 2, w // s + 2)).astype(np.float32)
        n = cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC)
        out += n * amp
        tot += amp
        amp *= 0.6
    out /= tot
    return (out - out.mean()) / (out.std() + 1e-6)


def _base(color, seed, fib=7.0, blot=6.0):
    h, w = H, W
    import cv2
    n = _fbm(h // 2, w // 2, seed) * blot
    n = cv2.resize(n, (w, h), interpolation=cv2.INTER_LINEAR)
    fibres = np.random.default_rng(seed + 1).standard_normal((h, w)).astype(np.float32)
    fibres = cv2.GaussianBlur(fibres, (0, 0), sigmaX=2.2, sigmaY=0.6) * fib
    base = np.array(rgb(color), np.float32)[None, None, :]
    img = base + (n + fibres)[..., None]
    return img


def _rgba(img):
    img = np.clip(img, 0, 255).astype(np.uint8)
    return skia.Image.fromarray(np.dstack([img, np.full(img.shape[:2], 255, np.uint8)]),
                                colorType=skia.kRGBA_8888_ColorType)


@lru_cache(None)
def paper_img(kind):
    """full-frame paper backgrounds: lined | graph | pink | kraft | blush."""
    import cv2
    if kind == "lined":
        img = _base(PAPER, 3)
        ov = np.zeros((H, W), np.float32)
        for y in range(236, H, 68):
            cv2.line(ov, (0, y), (W, y), 1.0, 3, cv2.LINE_AA)
        img = img * (1 - 0.55 * ov[..., None]) + np.array(rgb(RULE), np.float32) * 0.55 * ov[..., None]
        mg = np.zeros((H, W), np.float32)
        cv2.line(mg, (176, 0), (176, H), 1.0, 3, cv2.LINE_AA)
        cv2.line(mg, (186, 0), (186, H), 0.6, 2, cv2.LINE_AA)
        img = img * (1 - 0.8 * mg[..., None]) + np.array(rgb(MARGIN), np.float32) * 0.8 * mg[..., None]
        # punched holes down the left edge
        for y in (420, 960, 1500):
            cv2.circle(img, (70, y), 26, (205, 196, 160), -1, cv2.LINE_AA)
            cv2.circle(img, (70, y), 22, (188, 178, 140), -1, cv2.LINE_AA)
    elif kind == "graph":
        img = _base(GRAPH, 5, fib=5)
        ov = np.zeros((H, W), np.float32)
        for x in range(0, W, 45):
            cv2.line(ov, (x, 0), (x, H), 0.45 if x % 225 else 1.0, 1 if x % 225 else 2, cv2.LINE_AA)
        for y in range(0, H, 45):
            cv2.line(ov, (0, y), (W, y), 0.45 if y % 225 else 1.0, 1 if y % 225 else 2, cv2.LINE_AA)
        img = img * (1 - 0.35 * ov[..., None]) + np.array(rgb("#8FB8B0"), np.float32) * 0.35 * ov[..., None]
    elif kind == "pink":
        img = _base(PINK, 7, fib=9, blot=7)
    elif kind == "blush":
        img = _base(BLUSH, 11, fib=7, blot=5)
    elif kind == "kraft":
        img = _base(KRAFT, 9, fib=14, blot=10)
        specks = np.random.default_rng(12).random((H, W)) > 0.9985
        img[specks] *= 0.6
    elif kind == "yellow":
        img = _base(YEL, 13, fib=8, blot=6)
    else:
        raise KeyError(kind)
    # soft vignette baked into the paper
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    img *= (1 - 0.13 * np.clip(r - 0.55, 0, None) ** 1.6)[..., None]
    return _rgba(img)


def paper(c, kind, rect=None, a=1.0):
    p = skia.Paint(Alphaf=a)
    if rect is None:
        c.drawImage(paper_img(kind), 0, 0, SAMP, p)
    else:
        c.save()
        c.clipRect(rect)
        c.drawImage(paper_img(kind), 0, 0, SAMP, p)
        c.restore()


# ---------------------------------------------------------------- the sticker look
@lru_cache(None)
def _sticker_filter(border, sh_dx, sh_dy, sh_blur, sh_a):
    d = skia.ImageFilters.Dilate(border, border)
    white = skia.ImageFilters.ColorFilter(skia.ColorFilters.Blend(skia.ColorWHITE, skia.BlendMode.kSrcIn), d)
    shadow = skia.ImageFilters.DropShadowOnly(sh_dx, sh_dy, sh_blur, sh_blur, skia.Color(40, 25, 10, int(255 * sh_a)), d)
    return skia.ImageFilters.Merge([shadow, white, None])


class Sticker:
    """with Sticker(c, bounds): draw...  -> everything drawn inside gets a die-cut white border + drop shadow."""

    def __init__(self, c, bounds=None, border=11, shadow=(7, 11, 9, 0.32), a=1.0):
        self.c, self.bounds, self.border, self.shadow, self.a = c, bounds, border, shadow, a

    def __enter__(self):
        p = skia.Paint(ImageFilter=_sticker_filter(int(self.border), *self.shadow), Alphaf=clamp(self.a))
        b = self.bounds
        if b is not None:
            pad = self.border + 40
            b = skia.Rect(b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad)
        self.c.saveLayer(b, p)
        return self.c

    def __exit__(self, *exc):
        self.c.restore()


def pop_k(t, t0, dur=0.38):
    """0..~1.1..1 overshoot scale for a sticker slapping on."""
    if t < t0:
        return 0.0
    x = t - t0
    return spring(x, w=20, z=0.42) if x < 1.2 else 1.0


def slap(c, t, t0, x, y, rot=0.0, scale=1.0, t_out=None, out_dur=0.22):
    """transform for a sticker centred at (x, y) slapping on at t0 (and peeling away at t_out). Returns alpha."""
    k = pop_k(t, t0)
    a = clamp((t - t0) / 0.06)
    s = scale * (0.35 + 0.65 * k)
    r = rot + (1 - min(1, k)) * 14 * (1 if hrand(x, y) > 0.5 else -1)
    if t_out is not None and t > t_out:
        ko = e_in(clamp((t - t_out) / out_dur))
        s *= 1 - 0.6 * ko
        a *= 1 - ko
        r += 20 * ko
    c.translate(x, y)
    c.rotate(r)
    c.scale(s, s)
    return a


# ---------------------------------------------------------------- type
def ink_word(c, s, x, y, size, a=1.0, color=INK, name="serif"):
    """plain caption word (left baseline at x, y)."""
    c.drawString(s, x, y, font(name, size), fill(color, a))


def pink_word(c, s, x, y, size, a=1.0, color=PINK, outline=PINK_D, depth=0.045):
    """key word: heavy pink italic with a dark outline and a hard offset shadow, like the reference."""
    f = font("pink", size)
    d = size * depth
    sp = fill(outline, a)
    for i in range(1, 5):
        c.drawString(s, x + d * i / 4, y + d * i / 4, f, sp)
    c.drawString(s, x, y, f, stroke(outline, size * 0.055, a))
    c.drawString(s, x, y, f, fill(color, a))


def word_w(s, size, accent):
    return measure(s, "pink" if accent else "serif", size)


def type_text(c, s, x, y, size, a=1.0, color=INK, name="type", anchor="l"):
    w = measure(s, name, size)
    x0 = x - w / 2 if anchor == "c" else x - w if anchor == "r" else x
    c.drawString(s, x0, y, font(name, size), fill(color, a))
    return w


def hand(c, s, x, y, size, a=1.0, color=INK, anchor="c", rot=0.0):
    w = measure(s, "hand", size)
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    x0 = -w / 2 if anchor == "c" else -w if anchor == "r" else 0
    c.drawString(s, x0, 0, font("hand", size), fill(color, a))
    c.restore()
    return w


def label_sticker(c, s, x, y, size, t, t0, rot=-3, bg=WHITE, fg=INK, name="type", t_out=None, pad=0.45, r=10):
    """typed label on a rounded paper sticker, slapped on at t0."""
    if t < t0:
        return
    c.save()
    a = slap(c, t, t0, x, y, rot, 1.0, t_out)
    w = measure(s, name, size)
    cap = font(name, size).getMetrics().fCapHeight
    bw, bh = w + size * pad * 2, cap + size * pad * 2
    with Sticker(c, (-bw / 2, -bh / 2, bw / 2, bh / 2), border=8, a=a):
        c.drawRRect(rrect(-bw / 2, -bh / 2, bw, bh, r), fill(bg))
        c.drawString(s, -w / 2, cap / 2, font(name, size), fill(fg))
    c.restore()


# ---------------------------------------------------------------- hand-made marks
def marker(c, pts, k, color=RED, width=14, a=1.0, smooth=True):
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


def scribble_ellipse(c, cx, cy, rx, ry, k, color=RED, width=10, seed=0, turns=1.15):
    n = 48
    pts = []
    for i in range(int(n * turns) + 1):
        th = -math.pi * 0.6 + 2 * math.pi * i / n
        wob = 1 + 0.05 * math.sin(i * 0.7 + seed) + 0.03 * (i / n)
        pts.append((cx + rx * wob * math.cos(th), cy + ry * wob * math.sin(th)))
    marker(c, pts, k, color, width)


def check_mark(c, x, y, s, k, color=RED, width=16):
    marker(c, [(x - 0.5 * s, y), (x - 0.15 * s, y + 0.38 * s), (x + 0.6 * s, y - 0.55 * s)], k, color, width,
           smooth=False)


def strike(c, x0, x1, y, k, color=RED, width=14, seed=0):
    pts = [(lerp(x0, x1, i / 6), y + (hrand(seed, i) - 0.5) * 8) for i in range(7)]
    marker(c, pts, k, color, width)


def arrow(c, x0, y0, x1, y1, k, color=INK, width=7, bend=0.25, head=26):
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    nx, ny = -(y1 - y0) * bend, (x1 - x0) * bend
    pts = []
    for i in range(21):
        s = i / 20
        pts.append(((1 - s) ** 2 * x0 + 2 * (1 - s) * s * (mx + nx) + s ** 2 * x1,
                    (1 - s) ** 2 * y0 + 2 * (1 - s) * s * (my + ny) + s ** 2 * y1))
    marker(c, pts, k, color, width, smooth=False)
    if k > 0.85:
        dx, dy = pts[-1][0] - pts[-3][0], pts[-1][1] - pts[-3][1]
        ang = math.atan2(dy, dx)
        hk = e_out((k - 0.85) / 0.15)
        for sgn in (-1, 1):
            a2 = ang + math.pi + sgn * 0.5
            marker(c, [(x1, y1), (x1 + head * hk * math.cos(a2), y1 + head * hk * math.sin(a2))], 1, color, width,
                   smooth=False)


def tape(c, x, y, w=120, h=38, rot=-8, a=0.85, color="#EFE6C8"):
    """translucent masking tape strip centred at (x, y)."""
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    path = skia.Path()
    n = 6
    path.moveTo(-w / 2, -h / 2)
    path.lineTo(w / 2, -h / 2)
    for i in range(n + 1):
        path.lineTo(w / 2 + (5 if i % 2 else -2), -h / 2 + h * i / n)
    path.lineTo(-w / 2, h / 2)
    for i in range(n, -1, -1):
        path.lineTo(-w / 2 + (-5 if i % 2 else 2), -h / 2 + h * i / n)
    path.close()
    c.drawPath(path, fill("#000000", 0.12 * a, blur=4))
    c.drawPath(path, fill(color, a))
    c.restore()


def stamp(c, s, x, y, size, k, color=RED, rot=-8, name="cond", pad=0.3, a=1.0):
    """rubber stamp that slams in from 1.9x."""
    if k <= 0:
        return
    sc = lerp(1.9, 1.0, e_out(clamp(k / 0.4)))
    aa = a * clamp(k / 0.12) * 0.92
    w = measure(s, name, size)
    cap = font(name, size).getMetrics().fCapHeight
    bw, bh = w + size * pad * 2, cap + size * pad * 2
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.scale(sc, sc)
    r = rrect(-bw / 2, -bh / 2, bw, bh, size * 0.1)
    c.drawRRect(r, stroke(color, size * 0.08, aa))
    c.drawString(s, -w / 2, cap / 2, font(name, size), fill(color, aa))
    c.restore()
