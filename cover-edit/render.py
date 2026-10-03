"""'Boring -> Editorial Cover': every spoken command adds the next layer of the edit, in one consistent magazine theme.

    python3 render.py                 -> out/final.mp4 (1080x1920, 30 fps)
    python3 render.py --stills k ...  -> out/stills/*.jpg at the named beats
"""

import math
import os
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool

import cv2
import numpy as np
import skia


from common import (DUR, FFMPEG, FONTS, FPS, H, NFRAMES, OFFS, OUT, S0, SEGS, SH, SPEED, SW, W, WORDS, WORK, clamp, eio,
                    ei, eo, eob, lerp, out_of_src, prog, spring, src_of_out, wt)

INK = (17, 17, 20)
WHITE = (255, 255, 255)
YEL = (255, 210, 63)
RED = (226, 30, 45)
NAVY = (12, 28, 64)


# ------------------------------------------------------------------ drawing helpers
def col(rgb, a=1.0):
    return skia.Color4f(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, clamp(a))


_TF = {}


def font(name, size):
    if name not in _TF:
        _TF[name] = skia.Typeface.MakeFromFile(os.path.join(FONTS, name + ".ttf"))
    f = skia.Font(_TF[name], size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    f.setSubpixel(True)
    return f


def text_w(txt, f, track=0.0):
    return f.measureText(txt) + track * f.getSize() * max(len(txt) - 1, 0)


def draw_text(c, txt, x, y, f, fill=WHITE, a=1.0, align="l", track=0.0, stroke=None, sw=0.0, shadow=0.0):
    w = text_w(txt, f, track)
    x0 = x - (w / 2 if align == "c" else w if align == "r" else 0)
    if track == 0:
        blob = skia.TextBlob.MakeFromString(txt, f)
    else:
        b = skia.TextBlobBuilder()
        glyphs = f.textToGlyphs(txt)
        pos, xx = [], 0.0
        for gw in f.getWidths(glyphs):
            pos.append(skia.Point(xx, 0))
            xx += gw + track * f.getSize()
        b.allocRunPos(f, glyphs, pos)
        blob = b.make()
    if shadow > 0:
        p = skia.Paint(AntiAlias=True, Color4f=col((0, 0, 0), 0.5 * a))
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, shadow))
        c.drawTextBlob(blob, x0, y + shadow * 0.6, p)
    if stroke is not None and sw > 0:
        c.drawTextBlob(blob, x0, y, skia.Paint(AntiAlias=True, Color4f=col(stroke, a), Style=skia.Paint.kStroke_Style,
                                               StrokeWidth=sw, StrokeJoin=skia.Paint.kRound_Join))
    c.drawTextBlob(blob, x0, y, skia.Paint(AntiAlias=True, Color4f=col(fill, a)))
    return w


def rrect(c, x, y, w, h, r, fill, a=1.0, shadow=0.0):
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r)
    if shadow:
        p = skia.Paint(AntiAlias=True, Color4f=col((0, 0, 0), 0.45 * a))
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, shadow))
        c.drawRRect(rr.makeOffset(0, shadow * 0.5) if hasattr(rr, "makeOffset") else rr, p)
    c.drawRRect(rr, skia.Paint(AntiAlias=True, Color4f=col(fill, a)))
    return rr


def poly(c, pts, fill, a=1.0, stroke=None, sw=0.0):
    path = skia.Path()
    path.addPoly([skia.Point(*p) for p in pts], True)
    c.drawPath(path, skia.Paint(AntiAlias=True, Color4f=col(fill, a)))
    if stroke is not None:
        c.drawPath(path, skia.Paint(AntiAlias=True, Color4f=col(stroke, a), Style=skia.Paint.kStroke_Style, StrokeWidth=sw,
                                    StrokeJoin=skia.Paint.kRound_Join))


def star_pts(cx, cy, ro, ri, n=5, a0=-90.0):
    return [(cx + (ro if i % 2 == 0 else ri) * math.cos(math.radians(a0 + 180 * i / n)),
             cy + (ro if i % 2 == 0 else ri) * math.sin(math.radians(a0 + 180 * i / n))) for i in range(n * 2)]


def burst_pts(cx, cy, ro, ri, n=14, seed=0):
    rng = np.random.default_rng(seed)
    return [(cx + (ro * rng.uniform(0.85, 1.1) if i % 2 == 0 else ri) * math.cos(2 * math.pi * i / (2 * n)),
             cy + (ro * rng.uniform(0.85, 1.1) if i % 2 == 0 else ri) * math.sin(2 * math.pi * i / (2 * n))) for i in range(2 * n)]


# ---- 5x7 pixel font for the video-game style
PIX = {
    "A": "01110 10001 10001 11111 10001 10001 10001", "B": "11110 10001 10001 11110 10001 10001 11110",
    "C": "01110 10001 10000 10000 10000 10001 01110", "D": "11110 10001 10001 10001 10001 10001 11110",
    "E": "11111 10000 10000 11110 10000 10000 11111", "F": "11111 10000 10000 11110 10000 10000 10000",
    "G": "01110 10001 10000 10111 10001 10001 01111", "H": "10001 10001 10001 11111 10001 10001 10001",
    "I": "01110 00100 00100 00100 00100 00100 01110", "J": "00111 00010 00010 00010 00010 10010 01100",
    "K": "10001 10010 10100 11000 10100 10010 10001", "L": "10000 10000 10000 10000 10000 10000 11111",
    "M": "10001 11011 10101 10101 10001 10001 10001", "N": "10001 10001 11001 10101 10011 10001 10001",
    "O": "01110 10001 10001 10001 10001 10001 01110", "P": "11110 10001 10001 11110 10000 10000 10000",
    "Q": "01110 10001 10001 10001 10101 10010 01101", "R": "11110 10001 10001 11110 10100 10010 10001",
    "S": "01111 10000 10000 01110 00001 00001 11110", "T": "11111 00100 00100 00100 00100 00100 00100",
    "U": "10001 10001 10001 10001 10001 10001 01110", "V": "10001 10001 10001 10001 10001 01010 00100",
    "W": "10001 10001 10001 10101 10101 10101 01010", "X": "10001 10001 01010 00100 01010 10001 10001",
    "Y": "10001 10001 01010 00100 00100 00100 00100", "Z": "11111 00001 00010 00100 01000 10000 11111",
    "0": "01110 10001 10011 10101 11001 10001 01110", "1": "00100 01100 00100 00100 00100 00100 01110",
    "2": "01110 10001 00001 00010 00100 01000 11111", "3": "11110 00001 00001 01110 00001 00001 11110",
    "4": "00010 00110 01010 10010 11111 00010 00010", "5": "11111 10000 11110 00001 00001 10001 01110",
    "6": "00110 01000 10000 11110 10001 10001 01110", "7": "11111 00001 00010 00100 01000 01000 01000",
    "8": "01110 10001 10001 01110 10001 10001 01110", "9": "01110 10001 10001 01111 00001 00010 01100",
    "!": "00100 00100 00100 00100 00100 00000 00100", ".": "00000 00000 00000 00000 00000 00000 00100",
    ",": "00000 00000 00000 00000 00100 00100 01000", "-": "00000 00000 00000 11111 00000 00000 00000",
    "+": "00000 00100 00100 11111 00100 00100 00000", ":": "00000 00100 00000 00000 00000 00100 00000",
    "'": "00100 00100 01000 00000 00000 00000 00000", "/": "00001 00010 00010 00100 01000 01000 10000",
    "?": "01110 10001 00001 00010 00100 00000 00100", " ": "00000 00000 00000 00000 00000 00000 00000",
}


def pix_w(txt, px):
    return len(txt) * 6 * px - px


def pix_text(c, txt, x, y, px, fill, a=1.0, align="l", shadow=True, outline=None):
    """y = top of the glyphs. Chunky 5x7 bitmap letters with a hard drop shadow."""
    w = pix_w(txt, px)
    x0 = x - (w / 2 if align == "c" else w if align == "r" else 0)
    layers = []
    if outline is not None:
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
            layers.append((dx * px * 0.6, dy * px * 0.6, outline))
    if shadow:
        layers.append((px * 0.7, px * 0.7, (0, 0, 0)))
    layers.append((0, 0, fill))
    for ox, oy, colr in layers:
        p = skia.Paint(Color4f=col(colr, a))
        for i, ch in enumerate(txt.upper()):
            rows = PIX.get(ch, PIX["?"]).split()
            for r, row in enumerate(rows):
                for q, bit in enumerate(row):
                    if bit == "1":
                        c.drawRect(skia.Rect.MakeXYWH(x0 + ox + (i * 6 + q) * px, y + oy + r * px, px, px), p)
    return w


# ------------------------------------------------------------------ data
_D = {}


def D(key):
    if key not in _D:
        if key in ("frames", "alpha"):
            _D[key] = np.load(os.path.join(WORK, key + ".npy"), mmap_mode="r")
        elif key == "nf":
            _D[key] = int(open(os.path.join(WORK, "nframes.txt")).read())
    return _D[key]



sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vibe-editing-promo"))
import paper as P  # noqa: E402

COBALT = (36, 58, 214)
COBALT_D = (18, 28, 120)
YELLOW = (255, 214, 10)
PAPER = (242, 239, 232)
MARK = (228, 38, 38)
SAFE_T, SAFE_B, SAFE_L, SAFE_R = 220, 1500, 35, 960


# ------------------------------------------------------------------ beats (edit seconds)
B = dict(
    cut=wt("Cut", 5), pauses=wt("pauses.", 6), see=wt("See?"), captions=wt("captions."), pop=wt("pop."),
    style=wt("style."), again1=wt("Again.", 15.4), again2=wt("again.", 16.8),
    background=wt("background.", 19.3), cover=wt("cover.", 21.9), notes=wt("notes", 23.8), designer=wt("designer", 26),
    split=wt("Split", 27.8), frames=wt("frames.", 29), clips=wt("clips.", 31.7), music=wt("music.", 32.9, end=True),
    sound=wt("sound", 34.5), effects=wt("effects", 34.8), everything=wt("everything.", 35.3),
    paper=wt("paper", 37.4), move=wt("move.", 39.5),
    prem=wt("Premiere", 41.5), after=wt("After", 42.5), davinci=wt("DaVinci,", 43.5), higgs=wt("Higgsfield,", 44.5),
    no2=wt("no", 42.5), no3=wt("no", 43.7), no4=wt("no", 44.7), just=wt("just", 45.6), claude=wt("Claude.", 45.9),
    from_=wt("From", 46.8), boring=wt("boring", 47), this=wt("this.", 48), comment=wt("Comment", 49), edit=wt("EDIT", 49.5),
    how=wt("how.", 50.5),
)
BUMPS = [B[k] for k in ("pauses", "see", "captions", "pop", "style", "again1", "again2", "cover", "frames", "clips", "music",
                        "sound", "effects", "everything", "paper", "move", "claude", "this", "comment")]


def stage(t):
    """Which layers of the edit are switched on at time t."""
    return dict(
        boring=t < B["cut"],
        cutout=t >= B["background"] - 0.1,
        cover=t >= B["cover"] - 0.05,
        grid=B["split"] - 0.05 <= t < B["clips"] - 0.1,
        phones=B["clips"] - 0.2 <= t < B["music"] + 0.9,
        music=t >= B["music"],
        paper=t >= B["paper"] - 0.05,
        move=t >= B["move"] - 0.05,
        apps=B["prem"] - 0.15 <= t < B["claude"],
        just=t >= B["claude"] - 0.05,
    )


# ------------------------------------------------------------------ camera
def camera(t):
    s, si = src_of_out(t)
    z = SEGS[si][2] if t >= B["cut"] else 1.0
    cx, cy = SW / 2, SH / 2
    if t >= B["cut"]:
        for tb in BUMPS:
            d = t - tb
            if 0 <= d < 0.6:
                z *= 1 + 0.05 * math.exp(-d / 0.1)
    if t >= B["move"]:                                   # "now make it move": slow float
        k = eo(prog(t, B["move"], 0.8))
        z *= 1 + 0.025 * k * (1 + math.sin(t * 1.3))
        cx += 6 * k * math.sin(t * 0.9)
    hw, hh = W / (2 * z * S0), H / (2 * z * S0)
    cx, cy = clamp(cx, hw, SW - hw), clamp(cy, hh, SH - hh)
    sx = sy = 0.0
    for tb, amp in ((B["cover"], 14), (B["claude"], 20), (B["everything"], 12)):
        d = t - tb
        if 0 <= d < 0.35:
            sx += amp * (1 - d / 0.35) ** 2 * math.sin(d * 90)
            sy += amp * (1 - d / 0.35) ** 2 * math.cos(d * 77)
    return z, cx, cy, sx, sy


def affine(z, cx, cy, sx=0.0, sy=0.0):
    s = z * S0
    return np.float32([[s, 0, W / 2 - cx * s + sx], [0, s, H / 2 - cy * s + sy]])


def base_layers(t):
    s, si = src_of_out(t)
    fi = int(np.clip(round(s * FPS), 0, D("nf") - 1))
    z, cx, cy, sx, sy = camera(t)
    M = affine(z, cx, cy, sx, sy)
    f = np.ascontiguousarray(D("frames")[fi])
    a = np.ascontiguousarray(D("alpha")[fi])
    base = cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    blur = cv2.GaussianBlur(base, (0, 0), 1.3)
    base = cv2.addWeighted(base, 1.4, blur, -0.4, 0)
    al = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32) / 255
    return base.astype(np.float32), al, M


def new_layer():
    arr = np.zeros((H, W, 4), np.uint8)
    return arr, skia.Surface(arr)


def over(dst, layer, mask=None):
    a = layer[..., 3:4].astype(np.float32) / 255
    if mask is not None:
        a = a * mask[..., None]
    return dst * (1 - a) + layer[..., :3].astype(np.float32) * a


def sk_image(arr):
    arr = np.ascontiguousarray(arr)
    if arr.shape[2] == 3:
        arr = np.concatenate([arr, np.full(arr.shape[:2] + (1,), 255, np.uint8)], 2)
    return skia.Image.fromarray(arr, colorType=skia.ColorType.kRGBA_8888_ColorType, alphaType=skia.AlphaType.kUnpremul_AlphaType)


SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)


def satur(img, s):
    g = img.mean(2, keepdims=True)
    return g + (img - g) * s


def grade_good(img):
    g = satur(img, 1.12)
    g = (g - 128) * 1.08 + 132
    return g * np.array([1.03, 1.0, 0.97], np.float32)


def grade_boring(img):
    g = satur(img, 0.55)
    return (g - 128) * 0.85 + 128 + 6


@lru_cache(None)
def halftone_mask(h=H, w=W, period=12):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = ((xx + yy) % period - period / 2) / (period / 2)
    v = ((xx - yy) % period - period / 2) / (period / 2)
    return np.sqrt(u * u + v * v)                      # 0 at dot centres .. ~1.4 at gaps


def duotone(img, dark, light, dots=True):
    lum = (img @ np.array([0.3, 0.59, 0.11], np.float32)) / 255
    lum = np.clip((lum - 0.5) * 1.25 + 0.55, 0, 1)
    if dots:
        r = (1 - lum) * 1.15
        lum = np.where(halftone_mask(*lum.shape) < r, lum * 0.55, np.minimum(1, lum * 1.08))
    lum = lum[..., None]
    return np.array(dark, np.float32) * (1 - lum) + np.array(light, np.float32) * lum


# ------------------------------------------------------------------ cover paper
@lru_cache(None)
def paper_bg():
    arr, s = new_layer()
    arr[..., 3] = 255
    c = s.getCanvas()
    c.drawPaint(skia.Paint(Color4f=col(PAPER)))
    g = skia.Paint(AntiAlias=True, Color4f=col((36, 58, 214), 0.08), StrokeWidth=2)
    for x in range(0, W + 1, 90):
        c.drawLine(x, 0, x, H, g)
    for y in range(0, H + 1, 90):
        c.drawLine(0, y, W, y, g)
    out = arr[..., :3].astype(np.float32)
    rng = np.random.default_rng(2)
    grain = cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 0.8)[..., None] * 5
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vig = 1 - 0.18 * (((xx - W / 2) / (W * 0.7)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2)
    return out * vig[..., None] + grain


def fit_font(name, txt, width, max_size):
    f = font(name, 100)
    w = text_w(txt, f)
    return font(name, min(max_size, 100 * width / max(w, 1)))


def headline_layer(t, st):
    """Cover typography that sits BEHIND him (masked by the matte)."""
    arr, s = new_layer()
    c = s.getCanvas()
    k = eob(prog(t, B["cover"] - 0.05, 0.4))
    if k <= 0:
        return None
    beat = 0.0
    if st["music"]:
        to = t / SPEED
        mo = B["music"] / SPEED
        ph = ((to - mo) * 118 / 60) % 1.0
        beat = math.exp(-ph * 6) * 0.035
    if st["just"]:
        kj = eob(prog(t, B["claude"] - 0.05, 0.45))
        c.save()
        c.translate(W / 2, 600)
        sc = kj * (1 + beat)
        c.scale(sc, sc)
        f = font("Anton-Regular", fit_font("Anton-Regular", "VIBE EDITING", 990, 330).getSize() * 1.18)
        draw_text(c, "CLAUDE", 0, 0, f, COBALT, 1.0, "c")
        c.restore()
        return arr
    if st["apps"]:
        return None
    c.save()
    c.translate(W / 2, 580)
    sc = lerp(1.25, 1.0, k) * (1 + beat)
    c.scale(sc, sc)
    f = fit_font("Anton-Regular", "VIBE EDITING", 990, 330)
    if st["move"]:
        x = -text_w("VIBE EDITING", f) / 2
        for i, ch in enumerate("VIBE EDITING"):
            dy = -18 * math.sin(t * 6 - i * 0.6) * eo(prog(t, B["move"], 0.5))
            draw_text(c, ch, x, dy, f, COBALT, min(1, k * 2))
            x += text_w(ch, f)
    else:
        draw_text(c, "VIBE EDITING", 0, 0, f, COBALT, min(1, k * 2), "c")
    c.restore()
    return arr


def cover_front(c, t, st):
    """Cover typography in front of him: header row, issue info, tape banner, side notes."""
    k = eo(prog(t, B["cover"] - 0.05, 0.4))
    if k <= 0:
        return
    tq = math.floor(t * 12) / 12
    small = font("SpaceGrotesk-Bold", 24)
    for txt, x, al in (("MARKETING", 60, "l"), ("DESIGN", W / 2, "c"), ("AI EDITING", 1020, "r")):
        draw_text(c, txt, x, 262, small, INK, k, al, track=0.12)
    # barcode + issue
    if not st["apps"] and not st["just"]:
        r = np.random.default_rng(5)
        x = 820
        for i in range(34):
            wdt = r.choice([2, 2, 3, 5])
            if i % 2 == 0:
                c.drawRect(skia.Rect.MakeXYWH(x, 290, wdt, 44), skia.Paint(Color4f=col(INK, k)))
            x += wdt + 1
        draw_text(c, "Nº 001 · OCT 2026", 1020, 360, font("SpecialElite-Regular", 22), INK, k, "r")
    # tape banner across the top of the head
    if not st["apps"] and not st["just"]:
        kb = eob(prog(t, B["cover"] + 0.15, 0.4))
        if kb > 0:
            c.save()
            c.translate(W / 2, 668)
            c.rotate(-3)
            c.scale(kb, kb)
            f = font("Anton-Regular", 50)
            txt = "EDITED 100% BY CLAUDE  —  ZERO EDITING APPS"
            w = text_w(txt, f, 0.03)
            rrect(c, -w / 2 - 30, -50, w + 60, 68, 3, YELLOW, 1.0, shadow=8)
            draw_text(c, txt, 0, 0, f, INK, 1.0, "c", track=0.03)
            c.restore()
    # side typewriter notes
    tw = font("SpecialElite-Regular", 26)
    if not st["grid"]:
        for i, ln in enumerate(["one take.", "zero timeline.", "zero apps."]):
            draw_text(c, ln, 60, 800 + i * 34, tw, INK, k)
        for i, ln in enumerate(["Cód: 001", "Prod: 03/10/2026"]):
            draw_text(c, ln, 1020, 800 + i * 34, tw, INK, k, "r")
    if st["just"]:
        kj = eob(prog(t, B["claude"], 0.4))
        c.save()
        c.translate(W / 2, 330)
        c.rotate(-4)
        c.scale(kj, kj)
        f = font("Anton-Regular", 96)
        w = text_w("JUST", f, 0.05)
        rrect(c, -w / 2 - 34, -92, w + 68, 112, 4, YELLOW, 1.0, shadow=10)
        draw_text(c, "JUST", 0, 0, f, INK, 1.0, "c", track=0.05)
        c.restore()


def scribble_outline(c, al, t, k, color=YELLOW, width=13, offset=24):
    """Hand-drawn marker outline around him (stop-motion jitter at 12 fps)."""
    if k <= 0:
        return
    small = cv2.resize((al > 0.5).astype(np.uint8) * 255, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    small = cv2.dilate(small, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (offset // 2, offset // 2)))
    cnts, _ = cv2.findContours(small, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cnts:
        return
    cnt = max(cnts, key=cv2.contourArea)[:, 0, :].astype(np.float32) * 4
    cnt = cnt[(cnt[:, 1] < H - 6)]
    if len(cnt) < 10:
        return
    step = max(1, len(cnt) // 220)
    pts = cnt[::step]
    r = np.random.default_rng(int(t * 12))
    pts = pts + r.normal(0, 2.2, pts.shape)
    n = max(2, int(len(pts) * clamp(k)))
    path = skia.Path()
    path.moveTo(*pts[0])
    for p in pts[1:n]:
        path.lineTo(*p)
    c.drawPath(path, skia.Paint(AntiAlias=True, Color4f=col(color), Style=skia.Paint.kStroke_Style, StrokeWidth=width,
                                StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join,
                                PathEffect=skia.CornerPathEffect.Make(20)))


def die_cut(al, px=16):
    a8 = (al * 255).astype(np.uint8)
    b = cv2.dilate(a8, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (px * 2 + 1, px * 2 + 1)))
    b = cv2.GaussianBlur(b, (0, 0), 1.0).astype(np.float32) / 255
    sh = cv2.GaussianBlur(np.roll(np.roll(b, 18, 0), 12, 1), (0, 0), 10)
    return b, sh


# ------------------------------------------------------------------ notes, stickers, doodles
NOTES = [("THAT'S ME", 170, 1005, -6, (430, 920)), ("ONE TAKE", 900, 990, 5, (760, 900)),
         ("NO EDITOR", 175, 1255, 4, (380, 1180)), ("100% CLAUDE", 880, 1240, -5, (720, 1160))]


def tape_note(c, txt, x, y, rot, k, size=46):
    if k <= 0:
        return
    f = font("PermanentMarker-Regular", size)
    w = text_w(txt, f)
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.scale(eob(k), eob(k))
    rrect(c, -w / 2 - 22, -size * 0.95, w + 44, size * 1.4, 2, YELLOW, 1.0, shadow=6)
    draw_text(c, txt, 0, 0, f, INK, 1.0, "c")
    c.restore()


def arrow(c, x0, y0, x1, y1, k, color=INK, w=6):
    if k <= 0:
        return
    mx, my = (x0 + x1) / 2 + (y1 - y0) * 0.25, (y0 + y1) / 2 - (x1 - x0) * 0.25
    path = skia.Path()
    path.moveTo(x0, y0)
    path.quadTo(mx, my, x1, y1)
    meas = skia.PathMeasure(path, False)
    seg = skia.Path()
    meas.getSegment(0, meas.getLength() * clamp(k), seg, True)
    p = skia.Paint(AntiAlias=True, Color4f=col(color), Style=skia.Paint.kStroke_Style, StrokeWidth=w, StrokeCap=skia.Paint.kRound_Cap)
    c.drawPath(seg, p)
    if k >= 0.95:
        ang = math.atan2(y1 - my, x1 - mx)
        for da in (2.6, -2.6):
            c.drawLine(x1, y1, x1 + 30 * math.cos(ang + da), y1 + 30 * math.sin(ang + da), p)


def notes_overlay(c, t, st):
    if t < B["notes"] - 0.05 or st["grid"] or st["apps"] or st["phones"]:
        return
    tq = math.floor(t * 12) / 12
    gone = 1 - prog(t, B["from_"] - 0.2, 0.25)
    if gone <= 0:
        return
    for i, (txt, x, y, rot, tgt) in enumerate(NOTES):
        t0 = B["notes"] + 0.12 + 0.38 * i
        k = prog(tq, t0, 0.3) * gone
        wob = 1.5 * math.sin(tq * 7 + i)
        tape_note(c, txt, x, y, rot + wob, k)
        arrow(c, x + (60 if x < 540 else -60), y - 50, tgt[0], tgt[1], prog(tq, t0 + 0.12, 0.3) * (gone >= 1))
    kd = prog(tq, B["designer"], 0.5)
    if kd > 0:
        for i, (sx, sy, rr) in enumerate(((120, 470, 34), (980, 470, 28), (130, 1430, 26))):
            ks = eob(prog(tq, B["designer"] + 0.08 * i, 0.3)) * gone
            if ks > 0.02:
                poly(c, star_pts(sx, sy, rr * ks, rr * 0.4 * ks), YELLOW, 1.0, INK, 4)


def sfx_stickers(c, t):
    tq = math.floor(t * 12) / 12
    for txt, t0, x, y, rot, fill, fg in (("WHOOSH!", B["sound"], 230, 1120, -10, COBALT, YELLOW),
                                         ("POP!", B["effects"], 860, 1080, 8, YELLOW, INK),
                                         ("BOOM!", B["everything"], 540, 1290, -4, MARK, WHITE)):
        k = prog(tq, t0 - 0.05, 0.25)
        ko = prog(tq, t0 + 0.9, 0.25)
        if k <= 0 or ko >= 1:
            continue
        s = eob(k) * (1 - eio(ko))
        c.save()
        c.translate(x, y)
        c.rotate(rot + 2 * math.sin(tq * 9))
        c.scale(s, s)
        poly(c, burst_pts(0, 8, 170, 115, 12, hash(txt) % 50), INK)
        poly(c, burst_pts(0, 0, 170, 115, 12, hash(txt) % 50), fill)
        draw_text(c, txt, 0, 30, font("Anton-Regular", 92), fg, 1.0, "c")
        c.restore()


def music_badge(c, t):
    k = prog(t, B["music"], 0.3)
    if k <= 0 or t > B["paper"] + 0.2:
        return
    ko = prog(t, B["sound"] - 0.2, 0.2)
    to, mo = t / SPEED, B["music"] / SPEED
    ph = ((to - mo) * 118 / 60) % 1.0
    c.save()
    c.translate(540, 1150)
    c.scale(eob(k) * (1 - eio(ko)), eob(k) * (1 - eio(ko)))
    rrect(c, -230, -70, 460, 130, 65, INK, 0.92, shadow=10)
    for i in range(9):
        h = 18 + 52 * abs(math.sin(t * 7 + i * 1.3)) * (0.6 + 0.4 * math.exp(-ph * 5))
        c.drawRoundRect(skia.Rect.MakeXYWH(-190 + i * 24, -h / 2, 14, h), 7, 7, skia.Paint(AntiAlias=True, Color4f=col(YELLOW)))
    draw_text(c, "NOW PLAYING", 40, -6, font("SpaceGrotesk-Bold", 24), WHITE, 1.0, track=0.1)
    draw_text(c, "vibe beat", 40, 30, font("PermanentMarker-Regular", 34), YELLOW, 1.0)
    c.restore()


# ------------------------------------------------------------------ split grid + phones
def grid_frame(t, base, al):
    """2x2 editorial grid: the same live frame in four treatments."""
    k = eo(prog(t, B["split"] - 0.05, 0.45))
    out = paper_bg().copy()
    g = 18
    x0, y0, x1, y1 = SAFE_L, SAFE_T + 30, W - SAFE_L, SAFE_B
    cw, ch = (x1 - x0 - g) / 2, (y1 - y0 - g) / 2
    looks = [lambda im: grade_good(im), lambda im: duotone(im, COBALT_D, (150, 175, 255)),
             lambda im: duotone(im, (60, 40, 0), YELLOW), lambda im: duotone(im, (10, 10, 10), (240, 240, 240))]
    crop_w, crop_h = int(cw * 1.2), int(ch * 1.2)
    cxs, cys = W // 2, 1010
    src = base[max(0, cys - crop_h // 2):cys + crop_h // 2, max(0, cxs - crop_w // 2):cxs + crop_w // 2]
    for i in range(4):
        ki = eob(prog(t, B["split"] + 0.08 * i, 0.35))
        if ki <= 0:
            continue
        cx = x0 + (i % 2) * (cw + g)
        cy = y0 + (i // 2) * (ch + g)
        tile = cv2.resize(np.clip(looks[i](src), 0, 255), (int(cw), int(ch)), interpolation=cv2.INTER_AREA)
        sc = lerp(0.7, 1.0, ki)
        tw, th = int(cw * sc), int(ch * sc)
        tile = cv2.resize(tile, (tw, th))
        ox, oy = int(cx + (cw - tw) / 2), int(cy + (ch - th) / 2)
        out[oy:oy + th, ox:ox + tw] = tile
    arr = np.empty((H, W, 4), np.uint8)
    arr[..., :3] = np.clip(out, 0, 255).astype(np.uint8)
    arr[..., 3] = 255
    s = skia.Surface(arr)
    c = s.getCanvas()
    labels = ["ORIGINAL", "COBALT", "SUNSHINE", "MONO"]
    for i in range(4):
        cx = x0 + (i % 2) * (cw + g)
        cy = y0 + (i // 2) * (ch + g)
        c.drawRect(skia.Rect.MakeXYWH(cx, cy, cw, ch), skia.Paint(AntiAlias=True, Color4f=col(INK), Style=skia.Paint.kStroke_Style, StrokeWidth=4))
        f = font("SpecialElite-Regular", 24)
        rrect(c, cx + 14, cy + 14, text_w(labels[i], f) + 24, 38, 3, PAPER)
        draw_text(c, labels[i], cx + 26, cy + 41, f, INK)
    # split lines draw in
    kl = prog(t, B["split"] - 0.1, 0.3)
    p = skia.Paint(AntiAlias=True, Color4f=col(MARK), StrokeWidth=6, StrokeCap=skia.Paint.kRound_Cap)
    if kl < 1:
        c.drawLine(W / 2, y0, W / 2, lerp(y0, y1, kl), p)
        c.drawLine(x0, (y0 + y1) / 2, lerp(x0, x1, kl), (y0 + y1) / 2, p)
    return arr[..., :3].astype(np.float32) * k + 0  # caller blends


PHONES = [("cartoon", 175, 860, -9), ("game", 905, 800, 8), ("logo", 190, 1330, 6), ("trailer", 890, 1350, -7)]


def clip(name):
    key = "clip_" + name
    if key not in _D:
        _D[key] = np.load(os.path.join(WORK, key + ".npy"), mmap_mode="r")
    return _D[key]


def phones_overlay(c, t):
    for i, (name, x, y, rot) in enumerate(PHONES):
        k = prog(t, B["clips"] - 0.15 + 0.1 * i, 0.45)
        ko = prog(t, B["music"] + 0.35 + 0.06 * i, 0.4)
        if k <= 0 or ko >= 1:
            continue
        fr = clip(name)
        img = np.ascontiguousarray(fr[int((t - B["clips"]) * FPS) % len(fr)])
        e = eob(k)
        dx = (-700 if x < 540 else 700) * ei(ko)
        c.save()
        c.translate(x + (1 - e) * (-300 if x < 540 else 300) + dx, y + 4 * math.sin(t * 2 + i))
        c.rotate(rot + 3 * math.sin(t * 1.5 + i))
        sc = 0.55 * e
        c.scale(sc, sc)
        pw, ph = 300, 560
        rrect(c, -pw / 2, -ph / 2, pw, ph, 42, INK, 1.0, shadow=18)
        sr = skia.RRect.MakeRectXY(skia.Rect(-pw / 2 + 14, -ph / 2 + 14, pw / 2 - 14, ph / 2 - 14), 30, 30)
        c.save()
        c.clipRRect(sr, True)
        c.drawImageRect(sk_image(img), skia.Rect(-pw / 2 + 14, -ph / 2 + 14, pw / 2 - 14, ph / 2 - 14), SAMP)
        c.restore()
        c.drawRoundRect(skia.Rect.MakeXYWH(-40, -ph / 2 + 22, 80, 18), 9, 9, skia.Paint(AntiAlias=True, Color4f=col(INK)))
        c.restore()


# ------------------------------------------------------------------ paper-cut + motion layer
@lru_cache(None)
def paper_frame_layer():
    arr, s = new_layer()
    c = s.getCanvas()
    ctx = P.Ctx(c, 0)
    P.torn(ctx, [(-60, -60), (W + 60, -60), (W + 60, 34), (-60, 52)], 0x111111, 3, depth=2, edge=(0, -6), amp=8)
    P.torn(ctx, [(-60, H - 46), (W + 60, H - 30), (W + 60, H + 60), (-60, H + 60)], 0x111111, 4, depth=2, edge=(0, 6), amp=8)
    return arr


def motion_bg(c, t, st):
    """Paper shapes that live on the cover (behind him)."""
    tq = math.floor(t * 12) / 12
    kp = eo(prog(t, B["paper"] - 0.05, 0.5))
    if kp <= 0:
        return
    mv = eo(prog(t, B["move"], 0.6))
    ctx = P.Ctx(c, int(t * 12))
    rot = 25 * tq * mv
    c.save()
    c.translate(150, 1520)
    c.rotate(rot)
    c.scale(kp, kp)
    P.paper(ctx, [(x, y) for x, y in burst_pts(0, 0, 150, 105, 14, 3)], 0x7C5CFF, 11, depth=2, amp=2)
    c.restore()
    c.save()
    c.translate(980, 1080 + 30 * math.sin(tq * 1.7) * mv)
    c.rotate(-rot * 0.6)
    c.scale(kp, kp)
    P.paper(ctx, P.circ_pts(0, 0, 70, 30), 0xFFD60A, 12, depth=2, amp=2)
    c.restore()
    for i in range(6):
        x = (120 + i * 170 + 90 * tq * mv) % (W + 200) - 100
        y = 1700 + 25 * math.sin(tq * 2 + i)
        P.paper(ctx, P.rect_pts(x, y, 90, 26), [0x243AD6, 0xFFD60A, 0xE42626][i % 3], 20 + i, depth=1.5, amp=1.5)


# ------------------------------------------------------------------ apps crossed out
APPS = [("PREMIERE PRO", "prem", "no2"), ("AFTER EFFECTS", "after", "no3"), ("DAVINCI", "davinci", "no4"), ("HIGGSFIELD", "higgs", "just")]


def apps_overlay(c, t):
    if not (B["prem"] - 0.15 <= t < B["claude"] + 0.3):
        return
    out = eio(prog(t, B["claude"] - 0.05, 0.3))
    f = font("Anton-Regular", 92)
    for i, (name, k_in, k_strike) in enumerate(APPS):
        k = prog(t, B[k_in] - 0.06, 0.18)
        if k <= 0:
            continue
        y = 380 + i * 112
        w = text_w(name, f, 0.03)
        sc = lerp(1.6, 1.0, eo(k))
        c.save()
        c.translate(W / 2 + (i % 2 * 2 - 1) * 14, y)
        c.rotate((i % 2 * 2 - 1) * 2.5)
        c.scale(sc, sc)
        c.translate(-W * out * (1 if i % 2 else -1), 0)
        rrect(c, -w / 2 - 30, -88, w + 60, 108, 3, WHITE, 1.0, shadow=8)
        c.drawRect(skia.Rect(-w / 2 - 30, -88, w / 2 + 30, 20), skia.Paint(AntiAlias=True, Color4f=col(INK), Style=skia.Paint.kStroke_Style, StrokeWidth=4))
        draw_text(c, name, 0, 0, f, INK, 1.0, "c", track=0.03)
        ks = prog(t, B[k_strike] - 0.05, 0.22)
        if ks > 0:
            p = skia.Paint(AntiAlias=True, Color4f=col(MARK), Style=skia.Paint.kStroke_Style, StrokeWidth=13, StrokeCap=skia.Paint.kRound_Cap)
            c.drawLine(-w / 2 - 40, -20, -w / 2 - 40 + (w + 80) * eo(ks), -48, p)
        c.restore()


# ------------------------------------------------------------------ from boring to this + CTA
@lru_cache(None)
def boring_still():
    fi = int(1.5 * FPS)
    f = np.ascontiguousarray(D("frames")[fi]).astype(np.float32)
    return np.clip(grade_boring(f), 0, 255).astype(np.uint8)


def boring_overlay(c, t):
    k = prog(t, B["from_"] - 0.05, 0.4)
    ko = prog(t, B["comment"] + 0.2, 0.3)
    if k <= 0 or ko >= 1:
        return
    e = eob(k)
    c.save()
    c.translate(lerp(-300, 215, e) - 500 * ei(ko), 1000)
    c.rotate(-8)
    pw, ph = 300, 470
    rrect(c, -pw / 2, -ph / 2, pw, ph, 4, WHITE, 1.0, shadow=16)
    c.drawImageRect(sk_image(boring_still()), skia.Rect(-pw / 2 + 16, -ph / 2 + 16, pw / 2 - 16, ph / 2 - 80), SAMP)
    draw_text(c, "boring", 0, ph / 2 - 26, font("PermanentMarker-Regular", 42), INK, 1.0, "c")
    rrect(c, -60, -ph / 2 - 20, 120, 40, 2, YELLOW, 0.85)
    c.restore()
    kt = prog(t, B["this"] - 0.08, 0.3)
    if kt > 0:
        arrow(c, 830, 770, 700, 900, kt * (1 - ko), MARK, 8)
        tape_note(c, "THIS", 880, 740, 6, kt * (1 - ko), 64)


def cta_overlay(c, t):
    k = prog(t, B["comment"] - 0.1, 0.45)
    if k <= 0:
        return
    e = eob(k)
    w, h = 820, 128
    x, y = W / 2 - w / 2 - 40, 1300 + 260 * (1 - e)
    c.save()
    c.translate(x + w / 2, y + h / 2)
    c.rotate(-2)
    c.translate(-(x + w / 2), -(y + h / 2))
    rrect(c, x, y, w, h, 18, WHITE, 1.0, shadow=18)
    c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), skia.Paint(AntiAlias=True, Color4f=col(INK), Style=skia.Paint.kStroke_Style, StrokeWidth=4))
    rrect(c, x + w / 2 - 70, y - 22, 140, 44, 2, YELLOW, 0.9)
    c.drawCircle(x + 68, y + h / 2, 40, skia.Paint(AntiAlias=True, Color4f=col(COBALT)))
    draw_text(c, "Y", x + 68, y + h / 2 + 16, font("Anton-Regular", 46), WHITE, 1.0, "c")
    typed = int(clamp((t - B["edit"]) / 0.08 + 1, 0, 4)) if t >= B["edit"] else 0
    if typed == 0:
        draw_text(c, "Add a comment…", x + 130, y + h / 2 + 14, font("SpecialElite-Regular", 40), (130, 130, 140))
        tx = x + 130
    else:
        tx = x + 130 + draw_text(c, "EDIT"[:typed], x + 130, y + h / 2 + 22, font("Anton-Regular", 64), INK)
    if int(t * 2.2) % 2 == 0 or typed == 0:
        c.drawRect(skia.Rect.MakeXYWH(tx + 8, y + 32, 5, h - 64), skia.Paint(Color4f=col(COBALT)))
    kh = prog(t, B["how"] - 0.1, 0.3)
    bs = 1 + 0.25 * math.sin(math.pi * clamp(kh))
    c.save()
    c.translate(x + w - 70, y + h / 2)
    c.scale(bs, bs)
    c.drawCircle(0, 0, 44, skia.Paint(AntiAlias=True, Color4f=col(COBALT if typed else (200, 200, 210))))
    poly(c, [(-15, -17), (19, 0), (-15, 17), (-8, 0)], WHITE)
    c.restore()
    c.restore()


# ------------------------------------------------------------------ boring + cut overlays
def boring_hud(c, t):
    if t >= B["cut"] + 0.25:
        return
    a = 1 - prog(t, B["cut"], 0.25)
    f = font("SpaceMono-Bold", 26)
    draw_text(c, "RAW_0001.MP4  ·  UNEDITED", 60, 280, f, WHITE, 0.85 * a, shadow=4)
    if int(t * 2) % 2 == 0:
        c.drawCircle(1000, 271, 11, skia.Paint(AntiAlias=True, Color4f=col((230, 40, 40), a)))
    tc = f"00:00:{int(t):02d}:{int((t % 1) * 30):02d}"
    draw_text(c, tc, 1020, 1460, f, WHITE, 0.8 * a, "r", shadow=4)


def cut_overlay(c, t):
    d = t - (B["pauses"] - 0.05)
    if not (0 <= d < 1.6):
        return
    k = prog(d, 0, 0.35)
    p = skia.Paint(AntiAlias=True, Color4f=col(MARK), Style=skia.Paint.kStroke_Style, StrokeWidth=7,
                   PathEffect=skia.DashPathEffect.Make([26, 16], 0))
    y = 1130
    c.drawLine(40, y, 40 + (W - 80) * eo(k), y, p)
    sx = 40 + (W - 80) * eo(k)
    for a in (25, -25):
        c.drawLine(sx, y, sx + 50 * math.cos(math.radians(180 + a)), y + 50 * math.sin(math.radians(180 + a)),
                   skia.Paint(AntiAlias=True, Color4f=col(MARK), StrokeWidth=8, StrokeCap=skia.Paint.kRound_Cap))
    kc = prog(d, 0.25, 0.3) * (1 - prog(d, 1.3, 0.3))
    if kc > 0:
        tape_note(c, f"-{DEAD_AIR:.1f}s DEAD AIR", 540, 1060, -3, kc, 50)


# ------------------------------------------------------------------ captions in five styles
def caption_groups():
    groups, cur = [], []
    for i, w in enumerate(WORDS):
        cur.append(w)
        nxt = WORDS[i + 1] if i + 1 < len(WORDS) else None
        if w["w"][-1] in ".,!?" or len(cur) >= 3 or nxt is None or nxt["s"] - w["e"] > 0.35:
            groups.append(cur)
            cur = []
    out = []
    for gi, g in enumerate(groups):
        t0, t1 = g[0]["s"] - 0.04, g[-1]["e"] + 0.25
        if gi + 1 < len(groups) and groups[gi + 1][0]["s"] - g[-1]["e"] < 0.6:
            t1 = min(t1, groups[gi + 1][0]["s"] - 0.04)
        out.append((t0, t1, g))
    return out


GROUPS = caption_groups()


def cap_style(t):
    if t < B["captions"] - 0.05:
        return None
    if t < B["style"] + 0.1:
        return "A"
    if t < B["again1"]:
        return "B"
    if t < B["again2"]:
        return "C"
    if t < B["background"] - 0.1:
        return "D"
    return "E"


RANSOM_FONTS = ["Anton-Regular", "ArchivoBlack-Regular", "Cormorant-Light", "SpecialElite-Regular", "PermanentMarker-Regular", "Montserrat-Black"]
RANSOM_COLS = [(WHITE, INK), (YELLOW, INK), (COBALT, WHITE), (INK, WHITE), (MARK, WHITE), (PAPER, COBALT)]


def draw_captions(c, t, st):
    style = cap_style(t)
    if style is None or st["grid"] or st["apps"] or t >= B["comment"] - 0.1:
        return
    if B["claude"] - 0.05 <= t < B["claude"] + 0.5:
        return
    for t0, t1, g in GROUPS:
        if not (t0 <= t < t1):
            continue
        words = [w["w"].upper() if style in "AE" else w["w"] for w in g]
        y = 1400
        kin = eob(prog(t, t0, 0.16))
        if style == "A":
            f = font("Montserrat-Black", 70)
            gap = 26
            ws = [text_w(x, f) for x in words]
            x = W / 2 - (sum(ws) + gap * (len(ws) - 1)) / 2
            c.save(); c.translate(W / 2, y); c.scale(kin, kin); c.translate(-W / 2, -y)
            for w, txt, wd in zip(g, words, ws):
                active = w["s"] - 0.03 <= t < w["e"] + 0.05
                if active:
                    rrect(c, x - 12, y - 66, wd + 24, 84, 14, YELLOW)
                draw_text(c, txt, x, y, f, INK if active else WHITE, 1.0 if t >= w["s"] - 0.03 else 0.55,
                          stroke=None if active else INK, sw=14, shadow=0 if active else 8)
                x += wd + gap
            c.restore()
        elif style == "B":
            f = font("PermanentMarker-Regular", 84)
            line = " ".join(words)
            c.save(); c.translate(W / 2, y); c.rotate(-4); c.scale(kin, kin)
            draw_text(c, line, 0, 0, f, YELLOW, 1.0, "c", stroke=INK, sw=12, shadow=8)
            c.restore()
        elif style == "C":
            line = " ".join(words)
            sizes = 74
            r = np.random.default_rng(abs(hash(line)) % 1000)
            items = []
            for i, ch in enumerate(line):
                fn = RANSOM_FONTS[r.integers(len(RANSOM_FONTS))]
                fg_bg = RANSOM_COLS[r.integers(len(RANSOM_COLS))]
                f = font(fn, sizes * r.uniform(0.85, 1.15))
                items.append((ch, f, fg_bg, r.uniform(-8, 8), r.uniform(-8, 8)))
            total = sum((text_w(ch, f) + 22 if ch != " " else 30) for ch, f, *_ in items)
            x = W / 2 - total / 2
            for i, (ch, f, (bg, fg), rot, dy) in enumerate(items):
                if ch == " ":
                    x += 30
                    continue
                wd = text_w(ch, f)
                ki = eob(prog(t, t0 + 0.02 * i, 0.15))
                c.save(); c.translate(x + wd / 2 + 11, y + dy); c.rotate(rot); c.scale(ki, ki)
                rrect(c, -wd / 2 - 9, -f.getSize() * 0.88, wd + 18, f.getSize() * 1.1, 2, bg, 1.0, shadow=4)
                draw_text(c, ch, -wd / 2, 0, f, fg)
                c.restore()
                x += wd + 22
        elif style == "D":
            f = font("SpecialElite-Regular", 66)
            line = " ".join(words)
            n = int(len(line) * clamp((t - t0) / max(0.2, g[-1]["e"] - t0)))
            w = text_w(line, f)
            c.save(); c.translate(W / 2, y); c.rotate(1.5)
            rrect(c, -w / 2 - 30, -64, w + 60, 92, 2, WHITE, 1.0, shadow=8)
            for xx in (-w / 2 - 40, w / 2 + 10):
                rrect(c, xx, -78, 60, 30, 2, YELLOW, 0.8)
            draw_text(c, line[:max(1, n)], -w / 2, 0, f, INK)
            c.restore()
        else:   # E: editorial — Anton on yellow tape, active word in cobalt
            f = font("Anton-Regular", 84)
            gap = 22
            ws = [text_w(x, f) for x in words]
            total = sum(ws) + gap * (len(ws) - 1)
            c.save(); c.translate(W / 2 - 40, y); c.rotate(-2); c.scale(kin, kin)
            rrect(c, -total / 2 - 26, -84, total + 52, 108, 2, YELLOW, 1.0, shadow=8)
            x = -total / 2
            for w, txt, wd in zip(g, words, ws):
                active = w["s"] - 0.03 <= t < w["e"] + 0.05
                draw_text(c, txt, x, 0, f, COBALT if active else INK, 1.0 if t >= w["s"] - 0.03 else 0.5)
                x += wd + gap
            c.restore()
        return


def caption_flash(c, t):
    """Light-switch flash when captions turn on, and a swish card on each style change."""
    for t0, label in ((B["style"], "STYLE 2"), (B["again1"], "STYLE 3"), (B["again2"], "STYLE 4")):
        d = t - t0
        if 0 <= d < 0.5:
            k = math.sin(math.pi * d / 0.5)
            f = font("SpaceMono-Bold", 30)
            rrect(c, 60, 1500 - 64, text_w(label, f) + 40, 50, 25, INK, 0.85 * k)
            draw_text(c, label, 80, 1500 - 28, f, YELLOW, k)


# ------------------------------------------------------------------ frame
def render(t):
    st = stage(t)
    img, al, M = base_layers(t)
    a3 = al[..., None]
    if st["boring"]:
        img = grade_boring(img)
    elif not st["cutout"]:
        img = grade_good(img)
    else:
        person = grade_good(img)
        if not st["cover"]:
            # background turns into a cobalt halftone duotone; a yellow marker outline draws around him
            kd = eo(prog(t, B["background"] - 0.1, 0.4))
            bg = duotone(img, COBALT_D, (170, 190, 255))
            bg = img * (1 - kd) + bg * kd
        else:
            bg = paper_bg()
        if st["paper"]:
            b, sh = die_cut(al)
            kpp = eo(prog(t, B["paper"] - 0.05, 0.4))
            bg = bg * (1 - 0.35 * (sh * kpp)[..., None])
            bg = bg * (1 - (b * kpp)[..., None]) + np.array([252, 250, 245], np.float32) * (b * kpp)[..., None]
        if st["cover"]:
            # paper motion shapes + headline sit behind him
            larr, ls = new_layer()
            motion_bg(ls.getCanvas(), t, st)
            bg = over(bg, larr)
            hl = headline_layer(t, st)
            if hl is not None:
                bg = over(bg, hl)
        img = person * a3 + bg * (1 - a3)
    if st["grid"]:
        kg = eo(prog(t, B["split"] - 0.05, 0.3)) * (1 - eo(prog(t, B["clips"] - 0.3, 0.2)))
        img = img * (1 - kg) + grid_frame(t, img, al) * kg
    arr = np.empty((H, W, 4), np.uint8)
    arr[..., :3] = np.clip(img, 0, 255).astype(np.uint8)
    arr[..., 3] = 255
    s = skia.Surface(arr)
    c = s.getCanvas()
    if st["cutout"] and not st["grid"]:
        kk = prog(t, B["background"] - 0.05, 0.7)
        scribble_outline(c, al, t, kk)
    boring_hud(c, t)
    cut_overlay(c, t)
    if st["cover"] and not st["grid"]:
        cover_front(c, t, st)
    notes_overlay(c, t, st)
    if st["phones"]:
        phones_overlay(c, t)
    music_badge(c, t)
    sfx_stickers(c, t)
    apps_overlay(c, t)
    boring_overlay(c, t)
    caption_flash(c, t)
    draw_captions(c, t, st)
    cta_overlay(c, t)
    if st["paper"]:
        kp = eo(prog(t, B["paper"] - 0.05, 0.4))
        c.save()
        c.translate(0, (1 - kp) * -60)
        c.drawImage(sk_image(paper_frame_layer()), 0, 0, SAMP, skia.Paint(Alphaf=kp))
        c.restore()
    d = t - B["claude"]
    if 0 <= d < 0.16:
        c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Color4f=col(WHITE, 0.7 * (1 - d / 0.16))))
    out = arr[..., :3]
    fade = prog(t, DUR - 0.3, 0.3)
    if fade > 0:
        out = (out.astype(np.float32) * (1 - fade)).astype(np.uint8)
    return np.ascontiguousarray(out)


DEAD_AIR = 51.68 - DUR


def render_chunk(args):
    i0, i1, path = args
    p = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", path],
                         stdin=subprocess.PIPE)
    for i in range(i0, i1):
        p.stdin.write(render(i / FPS * SPEED).tobytes())
    p.stdin.close()
    p.wait()
    return path


def main():
    os.makedirs(OUT, exist_ok=True)
    if "--stills" in sys.argv:
        d = os.path.join(OUT, "stills")
        os.makedirs(d, exist_ok=True)
        for k in sys.argv[sys.argv.index("--stills") + 1:] or list(B):
            for off in (0.0, 0.4):
                t = B[k] + off if k in B else float(k) + off
                cv2.imwrite(os.path.join(d, f"{t:06.2f}_{k}.jpg"), cv2.cvtColor(render(t), cv2.COLOR_RGB2BGR),
                            [cv2.IMWRITE_JPEG_QUALITY, 85])
        return
    k = 24
    bounds = np.linspace(0, NFRAMES, k + 1).astype(int)
    tmp = os.path.join(OUT, "chunks")
    os.makedirs(tmp, exist_ok=True)
    jobs = [(int(bounds[i]), int(bounds[i + 1]), os.path.join(tmp, f"c{i:03d}.mp4")) for i in range(k)]
    with Pool(int(os.environ.get("WORKERS", "4"))) as pool:
        for pth in pool.imap_unordered(render_chunk, jobs):
            print("done", os.path.basename(pth), flush=True)
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join(f"file '{j[2]}'\n" for j in jobs))
    final = os.path.join(OUT, "final.mp4")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", os.path.join(OUT, "mix.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
                    "-movflags", "+faststart", final], check=True)
    print("wrote", final)


if __name__ == "__main__":
    main()
