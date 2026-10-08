"""collage: a Vox-style paper collage kit on skia.

Grid-paper desk, grayscale halftone cutouts with white die-cut borders and baked shadows, torn paper, masking tape,
yellow highlighter, red marker strokes, rubber stamps, typewriter tags, ransom-note letters, stop-motion jitter.
Art direction: references/vox-papercut/BRIEF.md
"""
import math
import sys
from pathlib import Path

import numpy as np
import skia
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "common"))
from kit import W, H, clamp, col, e_back, e_out, fill, font, hrand, lerp, measure, prog, stroke, text  # noqa: E402,F401

PAPER = "#EEEAE1"      # desk / grid paper
WHITE = "#FAF8F2"      # cut paper white
INK = "#161514"
YEL = "#FFD21F"        # the one loud colour
RED = "#E0352B"        # marker + stamps only
NEWS = "#D8D3C8"       # newsprint
SLATE = "#2A2927"      # dark paper
TAPE = "#E8DCBC"
GRID = "#8FA7B4"
SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)


# ---------------------------------------------------------------- stop motion
def on_twos(t):
    """paper moves at 12 fps, like it's being nudged by hand between exposures."""
    return math.floor(t * 12) / 12


def jit(seed, t, amp=2.0, rot=0.6):
    k = math.floor(t * 12)
    return ((hrand(seed, k, 1) - 0.5) * 2 * amp, (hrand(seed, k, 2) - 0.5) * 2 * amp, (hrand(seed, k, 3) - 0.5) * 2 * rot)


def pop(t, t0, d=0.25, s=2.0):
    """0 before t0, overshooting pop to 1 (sampled on twos)."""
    return e_back(prog(on_twos(t), t0, d), s) if t >= t0 else 0.0


# ---------------------------------------------------------------- textures
def fibre_texture(seed=4):
    rng = np.random.default_rng(seed)
    big = ndimage.gaussian_filter(rng.standard_normal((H // 8, W // 8)), 6)
    big = np.kron(big, np.ones((8, 8)))[:H, :W]
    mid = ndimage.gaussian_filter(rng.standard_normal((H, W)), 2.2)
    fine = rng.standard_normal((H, W))
    tex = 1 + 0.06 * big / (np.abs(big).max() + 1e-9) + 0.025 * mid / (mid.std() + 1e-9) + 0.012 * fine
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    vig = 1 - 0.22 * np.clip(r - 0.45, 0, None) ** 1.4
    return (tex * vig).astype(np.float32)


def _to_image(rgba):
    rgba = np.ascontiguousarray(np.clip(rgba, 0, 255).astype(np.uint8))
    return skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType)


class Cut:
    """A pre-rendered cutout image + where its anchor is inside it."""

    def __init__(self, img, ax, ay, cx=0.0, cy=0.0):
        self.img, self.ax, self.ay, self.cx, self.cy = img, ax, ay, cx, cy
        self.w, self.h = img.width(), img.height()

    def draw(self, c, x, y, rot=0.0, sc=1.0, a=1.0, pivot=None):
        """pivot: (px, py) in the drawing's own coords; defaults to the drawing's centre."""
        px, py = pivot if pivot else (self.cx, self.cy)
        c.save()
        c.translate(x, y)
        c.rotate(rot)
        c.scale(sc, sc)
        p = skia.Paint(AntiAlias=True)
        if a < 1:
            p.setAlphaf(clamp(a))
        c.drawImage(self.img, -self.ax - px, -self.ay - py, SAMP, p)
        c.restore()


def halftone(draw, w, h, cell=7.0, border=13, seed=0, angle=38, shadow=(7, 11, 9, 0.32), tint=None):
    """Render draw(c) (greys, transparent background) into a printed-looking die-cut sticker:
    newspaper halftone dots for the tones, a rough white paper border, and a soft shadow underneath."""
    pad = border + 30
    sw, sh = int(w + 2 * pad), int(h + 2 * pad)
    surf = skia.Surface(sw, sh)
    with surf as c:
        c.clear(skia.ColorTRANSPARENT)
        c.translate(pad, pad)
        draw(c)
    a = surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType)
    a = a.astype(np.float32) / 255
    A = a[..., 3]
    L = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2])
    yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
    th = math.radians(angle)
    u = (xx * math.cos(th) + yy * math.sin(th)) / cell
    v = (-xx * math.sin(th) + yy * math.cos(th)) / cell
    d = np.hypot(u - np.floor(u) - 0.5, v - np.floor(v) - 0.5)
    r = 0.74 * np.sqrt(np.clip(1 - L, 0, 1))
    dots = np.clip((r - d) / 0.09 + 0.5, 0, 1)
    dots = np.where(L < 0.06, 1.0, dots)                  # solid blacks stay solid
    ink = dots * A
    # die-cut border with a slightly wobbly scissor line
    mask = A > 0.4
    dist = ndimage.distance_transform_edt(~mask)
    rng = np.random.default_rng(seed)
    wob = ndimage.gaussian_filter(rng.standard_normal((sh, sw)), 9)
    wob = wob / (np.abs(wob).max() + 1e-9) * 3.0
    cut = np.clip(border + wob - dist + 0.5, 0, 1)
    cut = np.maximum(cut, A)
    paper = np.array([int(WHITE[i:i + 2], 16) / 255 for i in (1, 3, 5)], np.float32)
    inkc = np.array([int(INK[i:i + 2], 16) / 255 for i in (1, 3, 5)], np.float32)
    rgb = paper[None, None] * (1 - ink[..., None]) + inkc[None, None] * ink[..., None]
    if tint is not None:          # spot colour where the drawing used pure tint (kept flat, not screened)
        tc = np.array([int(tint[i:i + 2], 16) / 255 for i in (1, 3, 5)], np.float32)
        spot = (np.abs(a[..., 0] - tc[0]) + np.abs(a[..., 1] - tc[1]) + np.abs(a[..., 2] - tc[2]) < 0.08) & mask
        rgb[spot] = tc
    alpha = cut
    if shadow:
        dx, dy, blur, sa = shadow
        sh_ = ndimage.shift(ndimage.gaussian_filter(cut, blur), (dy, dx), order=1) * sa
        out_a = alpha + sh_ * (1 - alpha)
        rgb = (rgb * alpha[..., None]) / np.maximum(out_a, 1e-6)[..., None]
        alpha = out_a
    rgba = np.dstack([rgb * 255, alpha * 255])
    return Cut(_to_image(rgba), pad, pad, w / 2, h / 2)


def flat_cut(draw, w, h, shadow=(5, 9, 7, 0.3)):
    """A flat-colour paper cutout (no screen) with a baked shadow."""
    pad = 30
    sw, sh = int(w + 2 * pad), int(h + 2 * pad)
    surf = skia.Surface(sw, sh)
    with surf as c:
        c.clear(skia.ColorTRANSPARENT)
        c.translate(pad, pad)
        draw(c)
    a = surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType)
    a = a.astype(np.float32) / 255
    alpha, rgb = a[..., 3], a[..., :3]
    if shadow:
        dx, dy, blur, sa = shadow
        sh_ = ndimage.shift(ndimage.gaussian_filter(alpha, blur), (dy, dx), order=1) * sa
        out_a = alpha + sh_ * (1 - alpha)
        rgb = rgb * alpha[..., None] / np.maximum(out_a, 1e-6)[..., None]
        alpha = out_a
    return Cut(_to_image(np.dstack([rgb * 255, alpha * 255])), pad, pad, w / 2, h / 2)


# ---------------------------------------------------------------- paper primitives
def torn_path(x0, y0, x1, y1, seed, amp=7.0, step=14.0, sides="tblr"):
    """rectangle whose chosen sides are torn (jagged, uneven)."""
    def edge(ax, ay, bx, by, torn, k):
        n = max(2, int(math.hypot(bx - ax, by - ay) / step))
        nx, ny = -(by - ay), (bx - ax)
        ln = math.hypot(nx, ny) or 1
        nx, ny = nx / ln, ny / ln
        pts = []
        for i in range(n):
            f = i / n
            o = ((hrand(seed, k, i) - 0.5) * 2 * amp + math.sin(f * 9 + seed) * amp * 0.4) if torn else 0
            pts.append((ax + (bx - ax) * f + nx * o, ay + (by - ay) * f + ny * o))
        return pts
    pts = (edge(x0, y0, x1, y0, "t" in sides, 1) + edge(x1, y0, x1, y1, "r" in sides, 2)
           + edge(x1, y1, x0, y1, "b" in sides, 3) + edge(x0, y1, x0, y0, "l" in sides, 4))
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    p.close()
    return p


def paper_path(c, path, color, a=1.0, shadow=(5, 9, 7, 0.28)):
    if shadow:
        dx, dy, blur, sa = shadow
        c.save()
        c.translate(dx, dy)
        c.drawPath(path, fill("#000000", sa * a, blur=blur))
        c.restore()
    c.drawPath(path, fill(color, a))


def tape(c, cx, cy, w, h, rot, seed, a=1.0):
    """a strip of masking tape with zig-zag torn ends."""
    c.save()
    c.translate(cx, cy)
    c.rotate(rot)
    p = skia.Path()
    n = 7
    p.moveTo(-w / 2, -h / 2)
    p.lineTo(w / 2, -h / 2)
    for i in range(1, n + 1):
        p.lineTo(w / 2 + (5 if i % 2 else -2) + hrand(seed, i) * 4, -h / 2 + h * i / n)
    p.lineTo(-w / 2, h / 2)
    for i in range(1, n + 1):
        p.lineTo(-w / 2 + (-5 if i % 2 else 2) - hrand(seed, i, 9) * 4, h / 2 - h * i / n)
    p.close()
    c.save()
    c.translate(2, 4)
    c.drawPath(p, fill("#000000", 0.12 * a, blur=4))
    c.restore()
    c.drawPath(p, fill(TAPE, 0.86 * a))
    for i in range(5):                                 # crepe texture lines
        y = -h / 2 + h * (i + 0.5) / 5
        c.drawLine(-w / 2 + 6, y, w / 2 - 6, y, stroke("#B9A980", 1.2, 0.18 * a))
    c.restore()


def highlighter(c, x0, y0, x1, y1, k, seed=0, color=YEL, a=1.0):
    """chisel-marker swipe from left to right, revealed by k."""
    if k <= 0:
        return
    xe = lerp(x0, x1, clamp(k))
    p = skia.Path()
    n = 18
    for i in range(n + 1):
        x = lerp(x0, xe, i / n)
        p.lineTo(x, y0 + (hrand(seed, i) - 0.5) * 6) if i else p.moveTo(x, y0 + (hrand(seed, i) - 0.5) * 6)
    for i in range(n, -1, -1):
        x = lerp(x0, xe, i / n)
        p.lineTo(x, y1 + (hrand(seed, i, 3) - 0.5) * 6)
    p.close()
    pt = fill(color, 0.92 * a)
    pt.setBlendMode(skia.BlendMode.kMultiply)
    c.drawPath(p, pt)


def marker(c, pts, k, color=RED, w=9.0, a=1.0):
    """hand-drawn marker stroke along pts, drawn on progressively (k 0..1)."""
    if k <= 0 or len(pts) < 2:
        return
    seg = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
    tot = sum(seg)
    lim = tot * clamp(k)
    p = skia.Path()
    p.moveTo(*pts[0])
    acc = 0
    for i, s in enumerate(seg):
        if acc + s >= lim:
            f = (lim - acc) / s if s else 0
            p.lineTo(lerp(pts[i][0], pts[i + 1][0], f), lerp(pts[i][1], pts[i + 1][1], f))
            break
        p.lineTo(*pts[i + 1])
        acc += s
    c.drawPath(p, stroke(color, w, 0.92 * a))


def ring_pts(cx, cy, rx, ry, seed, turns=1.18, n=70):
    pts = []
    a0 = hrand(seed) * 6.28
    for i in range(n + 1):
        f = i / n
        a = a0 + f * turns * 2 * math.pi
        wob = 1 + 0.05 * math.sin(f * 7 + seed) + 0.04 * f
        pts.append((cx + math.cos(a) * rx * wob, cy + math.sin(a) * ry * wob))
    return pts


def arrow_pts(x0, y0, x1, y1, bend=0.25, n=24):
    mx, my = (x0 + x1) / 2 - (y1 - y0) * bend, (y0 + y1) / 2 + (x1 - x0) * bend
    pts = [((1 - f) ** 2 * x0 + 2 * (1 - f) * f * mx + f * f * x1, (1 - f) ** 2 * y0 + 2 * (1 - f) * f * my + f * f * y1)
           for f in (i / n for i in range(n + 1))]
    return pts


def arrow(c, x0, y0, x1, y1, k, color=RED, w=8.0, bend=0.25):
    pts = arrow_pts(x0, y0, x1, y1, bend)
    marker(c, pts, k / 0.8, color, w)
    if k > 0.8:
        kk = (k - 0.8) / 0.2
        ex, ey = pts[-1]
        px, py = pts[-3]
        ang = math.atan2(ey - py, ex - px)
        for s in (-1, 1):
            a = ang + math.pi - s * 0.5
            marker(c, [(ex, ey), (ex + math.cos(a) * 34, ey + math.sin(a) * 34)], kk, color, w)


def scribble_x(c, cx, cy, r, k, color=RED, w=14.0):
    marker(c, [(cx - r, cy - r * 0.9), (cx + r * 0.95, cy + r)], k * 2, color, w)
    marker(c, [(cx + r, cy - r), (cx - r * 0.9, cy + r * 0.92)], k * 2 - 1, color, w)


_STAMPS = {}


def stamp(c, txt, x, y, size, rot, k, color=RED, box=True):
    """rubber stamp: slams in from 1.5x, inky and patchy."""
    if k <= 0:
        return
    key = (txt, size, color, box)
    if key not in _STAMPS:
        f = font("black", size)
        tw = f.measureText(txt)
        pad = size * 0.28
        w, h = int(tw + 2 * pad + 20), int(size * 1.05 + 2 * pad + 20)
        surf = skia.Surface(w, h)
        with surf as cc:
            cc.clear(skia.ColorTRANSPARENT)
            if box:
                cc.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(10, 10, w - 20, h - 20), 10, 10),
                             stroke(color, size * 0.07))
            cc.drawString(txt, w / 2 - tw / 2, h / 2 + size * 0.36, f, fill(color))
        arr = surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType)
        rng = np.random.default_rng(len(txt) * 7 + size)
        nz = ndimage.gaussian_filter(rng.standard_normal(arr.shape[:2]), 1.6)
        nz2 = ndimage.gaussian_filter(rng.standard_normal(arr.shape[:2]), 7)
        keep = np.clip((nz + 0.9 * nz2 / (nz2.std() + 1e-9) + 1.5) * 2, 0, 1)
        arr = arr.astype(np.float32)
        arr[..., 3] *= keep * 0.93
        _STAMPS[key] = Cut(_to_image(arr), w / 2, h / 2)
    s = _STAMPS[key]
    sc = lerp(1.6, 1.0, e_out(clamp(k)))
    s.draw(c, x, y, rot, sc, clamp(k * 3), pivot=(0, 0))


def tag(c, txt, x, y, rot=0.0, size=30, a=1.0, seed=1, bg=WHITE, fg=INK, anchor="l"):
    """typewriter label on a scrap of paper."""
    f = font("monob", size)
    tw = f.measureText(txt)
    w, h = tw + size * 1.2, size * 1.7
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    x0 = 0 if anchor == "l" else -w / 2
    paper_path(c, torn_path(x0, -h / 2, x0 + w, h / 2, seed, amp=2.2, step=10, sides="r"), bg, a, (3, 6, 5, 0.25))
    c.drawString(txt, x0 + size * 0.6, size * 0.36, f, fill(fg, a))
    c.restore()
    return w


RANSOM = [(YEL, INK, "black", 1.0), (INK, WHITE, "anton", 1.12), (WHITE, INK, "serif", 1.3), (NEWS, INK, "mont", 0.96),
          (RED, WHITE, "black", 1.0), (WHITE, INK, "black", 1.0), (SLATE, YEL, "mont", 0.96)]


def ransom(c, word, cx, cy, size, t, t0, step=0.07, seed=0, a=1.0):
    """ransom-note lettering: every letter cut from a different scrap. Returns total width."""
    letters = []
    for i, ch in enumerate(word):
        if ch == " ":
            letters.append(None)
            continue
        bg, fg, fn, k = RANSOM[int(hrand(seed, i) * len(RANSOM))]
        s = size * k
        f = font(fn, s)
        cw = f.measureText(ch)
        letters.append((ch, bg, fg, f, s, cw + size * 0.36))
    widths = [L[5] if L else size * 0.35 for L in letters]
    tot = sum(widths) + 8 * (len(letters) - 1)
    x = cx - tot / 2
    n = 0
    for i, L in enumerate(letters):
        if L is None:
            x += widths[i] + 8
            continue
        ch, bg, fg, f, s, bw = L
        k = pop(t, t0 + n * step, 0.22, 2.4)
        n += 1
        if k > 0:
            jx, jy, jr = jit(seed * 31 + i, t, 1.2, 0.5)
            bh = size * 1.32
            c.save()
            c.translate(x + bw / 2 + jx, cy + (hrand(seed, i, 5) - 0.5) * size * 0.16 + jy)
            c.rotate((hrand(seed, i, 7) - 0.5) * 12 + jr)
            c.scale(k, k)
            paper_path(c, torn_path(-bw / 2, -bh / 2, bw / 2, bh / 2, seed * 13 + i, amp=3.0, step=12), bg, a,
                       (4, 7, 5, 0.3))
            m = f.getMetrics()
            cap = -m.fCapHeight
            c.drawString(ch, -f.measureText(ch) / 2, -cap / 2 * 0.98, f, fill(fg, a))
            c.restore()
        x += widths[i] + 8
    return tot


# ---------------------------------------------------------------- the desk
def desk(c, cam_x=0.0, cam_y=0.0):
    c.clear(col(PAPER))
    step = 54
    ox, oy = (-cam_x) % step, (-cam_y) % step
    thin, thick = stroke(GRID, 1.3, 0.28), stroke(GRID, 2.0, 0.42)
    i0x, i0y = int(math.floor(cam_x / step)), int(math.floor(cam_y / step))
    for i in range(-1, W // step + 2):
        x = ox + i * step
        c.drawLine(x, 0, x, H, thick if (i + i0x) % 5 == 0 else thin)
    for j in range(-1, H // step + 2):
        y = oy + j * step
        c.drawLine(0, y, W, y, thick if (j + i0y) % 5 == 0 else thin)
