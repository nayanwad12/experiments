"""'One video, 5 styles — just by saying it.' Each spoken command switches the whole look (and the music, in sound.py).

    python3 render.py                 -> out/final.mp4 (1920x1080, 30 fps)
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

import worlds as WD

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


# ------------------------------------------------------------------ beats (edit seconds)
B = dict(
    five=wt("five"), times=wt("times"), saying=wt("saying"), watch=wt("Watch"),
    news=wt("channel") + 0.05, breaking=wt("Breaking"), editing_n=wt("editing", 7), easy=wt("easy"),
    trailer=wt("trailer") + 0.05, in_=wt("In", 11.5), world=wt("world"), where=wt("where"), nobody=wt("nobody"),
    anymore=wt("anymore"),
    cartoon=wt("cartoon") + 0.05, hi=wt("Hi!"), everything=wt("Everything"), colorful=wt("colorful"),
    game=wt("game") + 0.05, level=wt("Level"), up=wt("up!"), new=wt("New", 22.5), unlocked=wt("unlocked"),
    old=wt("movie", 26) + 0.05, twenties=wt("twenties"), silent0=wt("A", 28.8) - 0.12, silent1=wt("editing.", 31.4, end=True) + 0.25,
    rewind=float(OFFS[5]) - 0.62, back=wt("Back", 33), normal=wt("normal"), fun=wt("fun"),
    didnt=wt("didn't"), said=wt("said", 38.5), loud=wt("loud"),
    comment=wt("comment", 40), edit=wt("EDIT", 40.5), how=wt("how"),
)
STYLES = [("news", B["news"], B["trailer"]), ("trailer", B["trailer"], B["cartoon"]), ("cartoon", B["cartoon"], B["game"]),
          ("game", B["game"], B["old"]), ("old", B["old"], B["rewind"])]
LABEL = {"news": "NEWS CHANNEL", "trailer": "MOVIE TRAILER", "cartoon": "CARTOON", "game": "VIDEO GAME", "old": "1920s FILM"}
REWIND = 0.62


def style_at(t):
    for i, (name, a, b) in enumerate(STYLES):
        if a <= t < b:
            return name, i, t - a
    return None, -1, 0.0


# ------------------------------------------------------------------ camera
def camera(t):
    s, si = src_of_out(t)
    z = SEGS[si][2]
    cx, cy = SW / 2, SH / 2 - (0 if z == 1 else 40)
    z *= 1 + 0.16 * (1 - eo(prog(t, 0.0, 0.55)))                   # punched-in open
    name, _, lt = style_at(t)
    if name == "trailer":                                          # slow push-in
        z *= 1 + 0.12 * eio(prog(lt, 0.2, 4.5))
        cy -= 30 * eio(prog(lt, 0.2, 4.5))
    for tb in BUMPS:
        d = t - tb
        if 0 <= d < 0.6:
            z *= 1 + 0.05 * math.exp(-d / 0.1)
    hw, hh = W / (2 * z * S0), H / (2 * z * S0)
    cx, cy = clamp(cx, hw, SW - hw), clamp(cy, hh, SH - hh)
    sx = sy = 0.0
    if name == "old":                                              # projector gate weave
        r = np.random.default_rng(int(t * 16))
        sx, sy = r.uniform(-3, 3), r.uniform(-4, 4)
    for tb, amp in ((B["nobody"], 18), (B["up"], 14), (B["trailer"], 10)):
        d = t - tb
        if 0 <= d < 0.35:
            sx += amp * (1 - d / 0.35) ** 2 * math.sin(d * 90)
            sy += amp * (1 - d / 0.35) ** 2 * math.cos(d * 77)
    return z, cx, cy, sx, sy


BUMPS = [B[k] for k in ("five", "watch", "news", "breaking", "cartoon", "hi", "colorful", "game", "level", "old",
                        "normal", "didnt", "loud", "comment")]


def affine(z, cx, cy, sx=0.0, sy=0.0):
    s = z * S0
    return np.float32([[s, 0, W / 2 - cx * s + sx], [0, s, H / 2 - cy * s + sy]])


_LUT = None


def grade(img):
    global _LUT
    if _LUT is None:
        x = np.arange(256) / 255.0
        s = np.clip(0.5 + (x - 0.5) * 1.08 + 0.03 * np.sin(2 * np.pi * x), 0, 1)
        _LUT = [(np.clip(s * 1.01, 0, 1) * 255).astype(np.uint8), (s * 255).astype(np.uint8),
                (np.clip(s * 0.99, 0, 1) * 255).astype(np.uint8)]
    return np.dstack([cv2.LUT(img[..., i], _LUT[i]) for i in range(3)])


def base_layers(t, hold_fps=None):
    s, si = src_of_out(t)
    if hold_fps:
        s = math.floor(s * hold_fps) / hold_fps
    fi = int(np.clip(round(s * FPS), 0, D("nf") - 1))
    z, cx, cy, sx, sy = camera(t)
    M = affine(z, cx, cy, sx, sy)
    f = np.ascontiguousarray(D("frames")[fi])
    a = np.ascontiguousarray(D("alpha")[fi])
    base = cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    blur = cv2.GaussianBlur(base, (0, 0), 1.4)
    base = cv2.addWeighted(grade(base), 1.45, grade(blur), -0.45, 0)
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


@lru_cache(None)
def radial(strength=0.6, rx=0.62, ry=0.72):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * rx)) ** 2 + ((yy - H / 2) / (H * ry)) ** 2)
    return np.clip(1 - strength * r ** 2.2, 0.1, 1)[..., None]


def satur(img, s):
    g = img.mean(2, keepdims=True)
    return g + (img - g) * s


# ------------------------------------------------------------------ style looks (numpy)
def look_news(img, al, lt):
    g = satur(img, 1.05)
    g = (g - 128) * 1.06 + 128
    return g * np.array([0.98, 1.0, 1.04], np.float32) * radial(0.25)


def look_trailer(img, al, t, lt):
    a3 = al[..., None]
    lum = img.mean(2, keepdims=True) / 255
    tone = (1 - lum) * np.array([-18, 6, 22], np.float32) + lum * np.array([22, 8, -16], np.float32)
    g = satur(img, 0.8) + tone
    g = (g - 128) * 1.18 + 128
    bg = g * np.array([0.55, 0.62, 0.72], np.float32)
    g = g * a3 + bg * (1 - a3)
    rim = np.clip(al - cv2.GaussianBlur(np.roll(al, -9, axis=1), (0, 0), 3), 0, 1)[..., None]
    g = g + rim * np.array([120, 190, 255], np.float32) * 0.7
    g = g * radial(0.75)
    rng = np.random.default_rng(int(t * FPS))
    g = g + cv2.resize(rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32), (W, H))[..., None] * 6
    return g


def look_cartoon(img, al):
    small = cv2.resize(np.clip(img, 0, 255).astype(np.uint8), (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    for _ in range(2):
        small = cv2.bilateralFilter(small, 7, 55, 7)
    hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.55 + 10, 0, 255)
    hsv[..., 2] = np.clip(hsv[..., 2] * 1.06 + 8, 0, 255)
    small = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
    q = (small // 36) * 36 + 18
    gray = cv2.medianBlur(cv2.cvtColor(small, cv2.COLOR_RGB2GRAY), 5)
    edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 5)
    edges = cv2.erode(edges, np.ones((2, 2), np.uint8))
    toon = (q.astype(np.float32) * (edges[..., None] / 255))
    toon = cv2.resize(toon, (W, H), interpolation=cv2.INTER_LINEAR)
    a8 = (al * 255).astype(np.uint8)
    ring = (cv2.dilate(a8, np.ones((9, 9), np.uint8)).astype(np.float32) - cv2.erode(a8, np.ones((5, 5), np.uint8))) / 255
    ring = cv2.GaussianBlur(np.clip(ring, 0, 1), (0, 0), 1.2)[..., None]
    return toon * (1 - ring)


@lru_cache(None)
def halftone():
    arr, s = new_layer()
    c = s.getCanvas()
    p = skia.Paint(AntiAlias=True, Color4f=col((255, 90, 160), 0.22))
    for y in range(0, H + 20, 22):
        for x in range(0, W + 20, 22):
            off = 11 if (y // 22) % 2 else 0
            r = 3 + 3 * (y / H)
            c.drawCircle(x + off, y, r, p)
    return arr


@lru_cache(None)
def scanlines():
    m = np.ones((H, W, 1), np.float32)
    m[::4] = 0.78
    m[1::4] = 0.9
    return m


def look_game(img, al):
    small = cv2.resize(img, (W // 10, H // 10), interpolation=cv2.INTER_AREA)
    small = (np.clip(small, 0, 255) // 40) * 40 + 20
    pix = cv2.resize(small, (W, H), interpolation=cv2.INTER_NEAREST)
    pix = satur(pix, 1.35)
    a3 = al[..., None]
    g = img * a3 + pix * (1 - a3)
    return g * scanlines()


def look_old(img, al, t):
    lum = img @ np.array([0.3, 0.59, 0.11], np.float32)
    lum = np.clip((lum - 128) * 1.3 + 128, 0, 255)[..., None]
    g = lum * np.array([1.06, 1.0, 0.86], np.float32)
    r = np.random.default_rng(int(t * 16))
    g = g * (1 + r.uniform(-0.07, 0.07))
    g = g * radial(1.1, 0.5, 0.62)
    g = g + cv2.resize(r.normal(0, 1, (H // 3, W // 3)).astype(np.float32), (W, H))[..., None] * 16
    return g


def old_overlays(c, t):
    r = np.random.default_rng(int(t * 16) + 7)
    for _ in range(r.integers(0, 3)):
        x = r.uniform(300, W - 300)
        c.drawLine(x, 0, x + r.uniform(-8, 8), H, skia.Paint(AntiAlias=True, Color4f=col((230, 225, 210) if r.random() < 0.5 else (30, 28, 24), r.uniform(0.25, 0.6)),
                                                             StrokeWidth=r.uniform(1, 2.5)))
    for _ in range(r.integers(4, 12)):
        x, y = r.uniform(240, W - 240), r.uniform(0, H)
        c.drawCircle(x, y, r.uniform(1.5, 5), skia.Paint(AntiAlias=True, Color4f=col((20, 18, 15) if r.random() < 0.7 else (240, 235, 220), r.uniform(0.4, 0.8))))
    if r.random() < 0.08:
        c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Color4f=col((255, 250, 235), 0.18)))
    # 4:3 gate with rounded corners
    gw = H * 4 / 3
    x0 = (W - gw) / 2
    path = skia.Path()
    path.setFillType(skia.PathFillType.kEvenOdd)
    path.addRect(skia.Rect(0, 0, W, H))
    path.addRRect(skia.RRect.MakeRectXY(skia.Rect(x0, 10, x0 + gw, H - 10), 60, 60))
    c.drawPath(path, skia.Paint(AntiAlias=True, Color4f=col((6, 5, 4))))


# ------------------------------------------------------------------ style overlays (skia)
def news_overlay(c, t, lt, out_k):
    a = 1 - out_k
    # channel bug
    kb = eob(prog(lt, 0.15, 0.4))
    if kb > 0:
        c.save()
        c.translate(W - 70, 70)
        c.scale(kb, kb)
        rrect(c, -250, 0, 250, 74, 10, NAVY, a, shadow=10)
        draw_text(c, "VIBE", -232, 52, font("Montserrat-Black", 40), WHITE, a)
        draw_text(c, "24", -112, 52, font("Montserrat-Black", 40), YEL, a)
        live = 0.6 + 0.4 * math.sin(t * 8)
        rrect(c, -64, 22, 52, 30, 6, RED, a)
        c.drawCircle(-54, 37, 5, skia.Paint(AntiAlias=True, Color4f=col(WHITE, a * live)))
        draw_text(c, "LIVE", -45, 44, font("Montserrat-Black", 15), WHITE, a)
        c.restore()
    # lower third
    kl = eo(prog(t, B["breaking"] - 0.1, 0.35))
    if kl > 0:
        y0 = 790
        w1 = 440 * kl
        c.save()
        c.clipRect(skia.Rect(0, y0 - 10, W, H))
        rrect(c, 80, y0, w1, 70, 0, RED, a)
        if kl > 0.6:
            draw_text(c, "BREAKING NEWS", 100, y0 + 50, font("Montserrat-Black", 42), WHITE, a * clamp((kl - 0.6) / 0.4))
        kh = eo(prog(t, B["breaking"] + 0.12, 0.4))
        rrect(c, 80, y0 + 70, 1100 * kh, 84, 0, WHITE, a)
        head = "EDITING JUST GOT EASY"
        n = int(len(head) * clamp((t - B["editing_n"] + 0.05) / 0.6)) if t > B["editing_n"] - 0.05 else 0
        if kh > 0.5:
            draw_text(c, head[:n] if n < len(head) else head, 104, y0 + 130, font("Montserrat-Black", 50), NAVY, a)
        rrect(c, 80, y0 + 154, 560 * kh, 40, 0, NAVY, a)
        if kh > 0.6:
            draw_text(c, "LIVE FROM THE GARDEN  ·  VIBE CORRESPONDENT", 96, y0 + 182, font("SpaceGrotesk-Bold", 20), WHITE, a, track=0.04)
        c.restore()
    # ticker
    kt = eo(prog(lt, 0.25, 0.35))
    if kt > 0:
        y = H - 58 * kt
        c.drawRect(skia.Rect(0, y, W, H), skia.Paint(Color4f=col(NAVY, a)))
        c.drawRect(skia.Rect(0, y, 190, H), skia.Paint(Color4f=col(YEL, a)))
        draw_text(c, "TOP STORIES", 20, y + 38, font("Montserrat-Black", 22), NAVY, a)
        msg = "CREATORS STUNNED AS TIMELINES DISAPPEAR   •   AI NOW EDITS VIDEOS BY VOICE   •   EXPERTS: 'JUST SAY IT'   •   "
        f = font("Montserrat-Bold", 24)
        wmsg = text_w(msg, f)
        x = 210 - ((lt * 260) % wmsg)
        c.save()
        c.clipRect(skia.Rect(190, y, W, H))
        for k in range(3):
            draw_text(c, msg, x + k * wmsg, y + 38, f, WHITE, a)
        c.restore()


def trailer_overlay(c, t, lt, out_k):
    bar = 138 * eo(prog(lt, 0.0, 0.3)) * (1 - out_k)
    p = skia.Paint(Color4f=col((0, 0, 0)))
    c.drawRect(skia.Rect(0, 0, W, bar), p)
    c.drawRect(skia.Rect(0, H - bar, W, H), p)
    # anamorphic flare sweep
    kf = prog(lt, 0.1, 1.6)
    if 0 < kf < 1:
        x = lerp(-200, W + 200, kf)
        g = skia.Paint(AntiAlias=True, Color4f=col((120, 190, 255), 0.55 * math.sin(math.pi * kf)))
        g.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6))
        c.drawRect(skia.Rect(x - 700, 395, x + 700, 401), g)
        g2 = skia.Paint(AntiAlias=True, Color4f=col((200, 230, 255), 0.6 * math.sin(math.pi * kf)))
        g2.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 40))
        c.drawCircle(x, 398, 60, g2)
    # dust in the light
    r = np.random.default_rng(3)
    for i in range(40):
        x = (r.uniform(0, W) + t * r.uniform(8, 30)) % W
        y = (r.uniform(bar, H - bar) - t * r.uniform(4, 14)) % H
        c.drawCircle(x, y, r.uniform(1, 2.6), skia.Paint(AntiAlias=True, Color4f=col((255, 230, 200), 0.35 * (1 - out_k))))
    # titles
    card0, card1 = B["in_"] - 0.08, B["where"] - 0.06
    if card0 <= t < card1:
        c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Color4f=col((0, 0, 0))))
        k = prog(t, card0, card1 - card0)
        sc = lerp(1.0, 1.08, k)
        c.save()
        c.translate(W / 2, H / 2 + 40)
        c.scale(sc, sc)
        draw_text(c, "IN A WORLD…", 0, 0, font("Cormorant-Light", 150), (245, 238, 225), eo(min(1, k * 4)), "c",
                  track=lerp(0.12, 0.2, k))
        c.restore()
    kb = prog(t, B["where"] - 0.06, 0.3) * (1 - prog(t, B["cartoon"] - 0.2, 0.15))
    if kb > 0:
        band = skia.Paint(Shader=skia.GradientShader.MakeLinear(
            [skia.Point(0, 600), skia.Point(0, H - 138)],
            [skia.Color4f(0, 0, 0, 0).toColor(), skia.Color4f(0, 0, 0, 0.75 * kb).toColor()]))
        c.drawRect(skia.Rect(0, 600, W, H - 138), band)
    for txt, t0, y, size in (("WHERE NOBODY EDITS", B["where"] - 0.06, 800, 96), ("ANYMORE", B["anymore"] - 0.05, 900, 120)):
        k = prog(t, t0, 0.45)
        ko = prog(t, B["cartoon"] - 0.2, 0.15)
        if k > 0 and ko < 1:
            sc = lerp(1.1, 1.0, eo(k))
            c.save()
            c.translate(W / 2, y)
            c.scale(sc, sc)
            draw_text(c, txt, 0, 0, font("Montserrat-Black", size), (250, 244, 232), eo(k) * (1 - ko), "c",
                      track=lerp(0.05, 0.16, eo(k)), shadow=18)
            c.restore()
    ks = prog(t, B["anymore"] + 0.35, 0.4)
    if ks > 0:
        draw_text(c, "COMING SOON  ·  TO YOUR FEED", W / 2, H - 55, font("Montserrat-Bold", 30), (240, 232, 218),
                  eo(ks) * (1 - out_k), "c", track=0.35)
    # flash on "nobody"
    d = t - B["nobody"]
    if 0 <= d < 0.18:
        c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Color4f=col(WHITE, 0.8 * (1 - d / 0.18))))


def cartoon_overlay(c, t, lt, out_k):
    a = 1 - out_k
    # "POW!" on entry, as a glossy 3D burst
    kp = prog(lt, 0.0, 0.7)
    if 0 < kp < 1:
        s = eob(min(1, kp * 2.5)) * (1 - prog(kp, 0.7, 0.3))
        c.save()
        c.translate(1560, 300)
        c.rotate(-10)
        c.scale(s, s)
        poly(c, burst_pts(0, 12, 200, 130, 12, 1), (255, 140, 0), a)
        poly(c, burst_pts(0, 0, 200, 130, 12, 1), YEL, a)
        WD.text3d(c, "POW!", 0, 40, font("Montserrat-Black", 110), (255, 70, 70), depth=12, a=a)
        c.restore()
    # glossy "HI!" bubble on the wave
    kh = prog(t, B["hi"] - 0.05, 0.35)
    ko = prog(t, B["everything"] + 0.2, 0.25)
    if kh > 0 and ko < 1:
        s = eob(kh) * (1 - eio(ko))
        bob = 8 * math.sin(t * 5)
        c.save()
        c.translate(560, 290 + bob)
        c.scale(s, s)
        sh = skia.Paint(AntiAlias=True, Color4f=col((0, 40, 90), 0.25))
        sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 18))
        c.drawOval(skia.Rect(-170, -100, 180, 150), sh)
        bub = skia.Paint(AntiAlias=True)
        bub.setShader(skia.GradientShader.MakeRadial(skia.Point(-60, -70), 300,
                                                     [WD.cint((255, 255, 255)), WD.cint((236, 246, 255)), WD.cint((190, 215, 245))], [0, 0.5, 1]))
        c.drawOval(skia.Rect(-175, -120, 175, 115), bub)
        tail = skia.Path()
        tail.addPoly([skia.Point(70, 80), skia.Point(200, 175), skia.Point(10, 105)], True)
        c.drawPath(tail, bub)
        WD.text3d(c, "HI!", 0, 45, font("Montserrat-Black", 130), (40, 150, 255), depth=14)
        c.restore()
    # "COLORFUL!" glossy balloon letters bouncing
    kc = prog(t, B["colorful"] - 0.1, 0.1)
    if kc > 0:
        word = "COLORFUL!"
        cols = [(255, 70, 80), (255, 150, 30), (255, 205, 40), (60, 200, 100), (40, 170, 255), (110, 100, 240), (190, 90, 230),
                (255, 70, 160), (255, 70, 80)]
        f = font("Montserrat-Black", 132)
        total = sum(f.measureText(ch) for ch in word) + 10 * (len(word) - 1)
        x = W / 2 - total / 2
        for i, ch in enumerate(word):
            ki = prog(t, B["colorful"] - 0.1 + 0.035 * i, 0.3)
            wch = f.measureText(ch)
            if ki > 0:
                bounce = -50 * (1 - eob(ki)) - 12 * abs(math.sin((t - B["colorful"]) * 8 + i))
                c.save()
                c.translate(x + wch / 2, 250 + bounce)
                c.rotate(math.sin(i * 1.7) * 7)
                c.scale(eob(ki), eob(ki))
                WD.text3d(c, ch, 0, 0, f, cols[i], depth=16, a=a)
                c.restore()
            x += wch + 10
        for i in range(10):
            ki = prog(t, B["colorful"] + 0.03 * i, 0.4)
            r = np.random.default_rng(40 + i)
            sx, sy = r.uniform(140, W - 140), r.uniform(360, 760)
            if abs(sx - 960) < 360:
                sx += 560 if sx > 960 else -560
            WD.sphere(c, sx, sy + 10 * math.sin(t * 4 + i), 22 * eob(ki), cols[i % 8], a * min(1, ki * 3))


def game_overlay(c, t, lt, out_k, score, coins):
    a = 1 - out_k
    px = 6
    # retro HUD: player/score, coins, world, time
    kh = eo(prog(lt, 0.1, 0.35))
    if kh > 0:
        y = 26 - 120 * (1 - kh)
        px = 5
        pix_text(c, "VIBE", 120, y, px, WHITE, a)
        pix_text(c, f"{score:06d}", 120, y + 46, px, WHITE, a)
        cx = 600
        c.drawCircle(cx + 12, y + 64, 12, skia.Paint(AntiAlias=False, Color4f=col((252, 188, 60), a)))
        pix_text(c, f"x{coins:02d}", cx + 36, y + 46, px, WHITE, a)
        pix_text(c, "WORLD", 1180, y, px, WHITE, a)
        pix_text(c, " 5-4", 1180, y + 46, px, WHITE, a)
        pix_text(c, "TIME", 1580, y, px, WHITE, a)
        pix_text(c, f" {max(0, 300 - int(lt * 9)):03d}", 1580, y + 46, px, WHITE, a)
    # +100 on each word
    for w in WORDS:
        if B["game"] < w["s"] < B["old"] - 0.4 and w["s"] <= t < w["s"] + 0.7:
            k = (t - w["s"]) / 0.7
            x = 1240 + (hash(w["w"]) % 280)
            pix_text(c, "100", x, 520 - 140 * eo(k), 5, WHITE, a * (1 - k))
    # LEVEL UP!
    kl = prog(t, B["level"] - 0.05, 0.3)
    ko = prog(t, B["new"] - 0.05, 0.25)
    if kl > 0 and ko < 1:
        s = eob(kl) * (1 - eio(ko))
        c.save()
        c.translate(430, 330)
        c.rotate(-6)
        c.scale(s, s)
        pix_text(c, "LEVEL", 0, 0, 14, (252, 216, 60), a, "c", outline=(0, 0, 0))
        pix_text(c, "UP!", 0, 118, 18, (252, 216, 60), a, "c", outline=(0, 0, 0))
        c.restore()
    # NES-style dialog box: skill unlocked
    ka = prog(t, B["new"] - 0.05, 0.3)
    kao = prog(t, B["old"] - 0.35, 0.3)
    if ka > 0 and kao < 1:
        n = int(len("VIBE EDITING") * clamp((t - B["new"] - 0.2) / 0.5))
        cxb = 1480
        x0, y0, bw, bh = cxb - 380, 300, 760, 170
        sc = eob(ka) * (1 - eio(kao))
        c.save()
        c.translate(cxb, y0 + bh / 2)
        c.scale(sc, sc)
        c.translate(-cxb, -(y0 + bh / 2))
        c.drawRect(skia.Rect.MakeXYWH(x0, y0, bw, bh), skia.Paint(Color4f=col((0, 0, 0), 0.92)))
        for inset, wdt in ((10, 6), (22, 3)):
            c.drawRect(skia.Rect.MakeXYWH(x0 + inset, y0 + inset, bw - 2 * inset, bh - 2 * inset),
                       skia.Paint(Color4f=col(WHITE), Style=skia.Paint.kStroke_Style, StrokeWidth=wdt))
        pix_text(c, "NEW SKILL UNLOCKED!", cxb, y0 + 44, 5, (252, 216, 60), 1.0, "c")
        pix_text(c, "VIBE EDITING"[:n], cxb, y0 + 96, 8, WHITE, 1.0, "c")
        c.restore()


@lru_cache(None)
def _ray_cache():
    return None


def _ray(ang):
    p = skia.Path()
    p.moveTo(0, 0)
    p.lineTo(900 * math.cos(ang - 0.06), 900 * math.sin(ang - 0.06))
    p.lineTo(900 * math.cos(ang + 0.06), 900 * math.sin(ang + 0.06))
    p.close()
    return p


def old_title(c, t, lt):
    k = prog(t, B["twenties"] - 0.05, 0.3)
    ko = prog(t, B["silent0"] - 0.2, 0.2)
    if k > 0 and ko < 1:
        a = min(1, k * 3) * (1 - ko)
        draw_text(c, "~ ANNO 1923 ~", W / 2, 140, font("Cormorant-Light", 76), (250, 244, 228), a, "c", track=0.3, shadow=10)


def intertitle(c, t):
    """Silent-film card; the voice is muted underneath it (sound.py)."""
    if not (B["silent0"] <= t < B["silent1"]):
        return False
    gw = H * 4 / 3
    x0 = (W - gw) / 2
    c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Color4f=col((8, 7, 6))))
    r = np.random.default_rng(int(t * 16))
    fl = 1 + r.uniform(-0.06, 0.06)
    cream = tuple(int(min(255, v * fl)) for v in (238, 230, 212))
    ins = 70
    for k, w in ((0, 5), (18, 2)):
        c.drawRect(skia.Rect(x0 + ins + k, ins + k, x0 + gw - ins - k, H - ins - k),
                   skia.Paint(AntiAlias=True, Color4f=col(cream), Style=skia.Paint.kStroke_Style, StrokeWidth=w))
    for cx, cy in ((x0 + ins, ins), (x0 + gw - ins, ins), (x0 + ins, H - ins), (x0 + gw - ins, H - ins)):
        poly(c, [(cx, cy - 22), (cx + 22, cy), (cx, cy + 22), (cx - 22, cy)], cream)
    lines = ["A silent film", "about a man", "who stopped editing."]
    f = font("Cormorant-Light", 92)
    for i, ln in enumerate(lines):
        draw_text(c, ln, W / 2, 400 + i * 120, f, cream, 1.0, "c", track=0.03)
    draw_text(c, "❦", W / 2, 820, font("Cormorant-Light", 60), cream, 0.9, "c")
    return True


# ------------------------------------------------------------------ transitions
def transition(c, img_arr, t):
    """Style-switch transitions drawn on top."""
    # news: red/white diagonal bars sweep
    d = t - (B["news"] - 0.2)
    if 0 <= d < 0.5:
        k = d / 0.5
        for i, colr in enumerate((RED, WHITE, NAVY)):
            x = lerp(-1400, W + 400, eio(clamp(k * 1.2 - i * 0.1)))
            poly(c, [(x, 0), (x + 500, 0), (x + 200, H), (x - 300, H)], colr)
    # cartoon: yellow starburst iris
    d = t - (B["cartoon"] - 0.2)
    if 0 <= d < 0.45:
        k = d / 0.45
        r = 1400 * math.sin(math.pi * k)
        c.save()
        c.translate(W / 2, H / 2)
        c.rotate(k * 120)
        poly(c, burst_pts(0, 0, r, r * 0.75, 16, 2), YEL, 1.0, INK, 10)
        c.restore()
    # trailer: cut to black
    d = t - (B["trailer"] - 0.12)
    if 0 <= d < 0.3:
        c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Color4f=col((0, 0, 0), 1 - prog(d, 0.12, 0.18))))


def pixel_transition(img, t):
    d = t - (B["game"] - 0.25)
    if 0 <= d < 0.5:
        k = math.sin(math.pi * d / 0.5)
        n = max(1, int(60 * k))
        small = cv2.resize(img, (max(1, W // n), max(1, H // n)), interpolation=cv2.INTER_AREA)
        return cv2.resize(small, (W, H), interpolation=cv2.INTER_NEAREST)
    return img


def film_burn(img, t):
    d = t - (B["old"] - 0.2)
    if 0 <= d < 0.45:
        k = math.sin(math.pi * d / 0.45)
        yy, xx = np.mgrid[0:H:4, 0:W:4].astype(np.float32)
        blob = np.exp(-(((xx - W * 0.8) / 500) ** 2 + ((yy - H * 0.3) / 380) ** 2))
        blob = cv2.resize(blob, (W, H))[..., None]
        return img + blob * k * np.array([255, 170, 60], np.float32) * 1.4
    return img


# ------------------------------------------------------------------ rewind back to normal
def rewind_frame(t):
    d = t - B["rewind"]
    if not (0 <= d < REWIND):
        return None
    k = d / REWIND
    t_back = lerp(B["rewind"] - 0.3, B["news"] + 1.5, eio(k))
    img = render(t_back, overlays=True, recap=False).astype(np.float32)
    img = satur(img, 0.7)
    rng = np.random.default_rng(int(t * FPS))
    shift = 14
    img[..., 0] = np.roll(img[..., 0], shift, axis=1)
    img[..., 2] = np.roll(img[..., 2], -shift, axis=1)
    for _ in range(3):
        y = int(rng.uniform(0, H - 40))
        h = int(rng.uniform(8, 40))
        img[y:y + h] = np.roll(img[y:y + h], int(rng.uniform(-80, 80)), axis=1) * 1.2
    img = img + rng.normal(0, 18, (H, W, 1)).astype(np.float32)
    arr = np.empty((H, W, 4), np.uint8)
    arr[..., :3] = np.clip(img, 0, 255).astype(np.uint8)
    arr[..., 3] = 255
    s = skia.Surface(arr)
    c = s.getCanvas()
    poly(c, [(125, 70), (125, 130), (80, 100)], WHITE)
    poly(c, [(170, 70), (170, 130), (125, 100)], WHITE)
    pix_text(c, "REWIND", 190, 78, 6, WHITE, 1.0)
    return arr[..., :3]


# ------------------------------------------------------------------ recap grid for the CTA
RECAP_T = [("NEWS", lambda: B["easy"]), ("TRAILER", lambda: B["anymore"] + 0.1), ("CARTOON", lambda: B["colorful"] + 0.25),
           ("GAME", lambda: B["level"] + 0.3), ("1920s", lambda: B["twenties"] + 0.1)]


@lru_cache(None)
def recap_tile(i):
    img = render(RECAP_T[i][1](), overlays=True, recap=False)
    return sk_image(cv2.resize(img, (W // 3, H // 3), interpolation=cv2.INTER_AREA))


def recap_k(t):
    return eio(prog(t, B["didnt"] - 0.05, 0.5)) * (1 - eio(prog(t, B["said"] - 0.1, 0.45)))


@lru_cache(None)
def studio_bg():
    arr, s = new_layer()
    arr[..., 3] = 255
    c = s.getCanvas()
    c.drawPaint(skia.Paint(Shader=skia.GradientShader.MakeRadial(
        skia.Point(W * 0.5, H * 0.45), W * 0.8,
        [skia.Color4f(0.13, 0.11, 0.22, 1).toColor(), skia.Color4f(0.03, 0.03, 0.06, 1).toColor()])))
    p = skia.Paint(AntiAlias=True, Color4f=col(WHITE, 0.07))
    for x in range(0, W + 1, 48):
        for y in range(0, H + 1, 48):
            c.drawCircle(x, y, 1.6, p)
    return arr[..., :3].copy()


def recap(t, img):
    k = recap_k(t)
    if k <= 0:
        return img
    arr = np.empty((H, W, 4), np.uint8)
    arr[..., :3] = studio_bg()
    arr[..., 3] = 255
    s = skia.Surface(arr)
    c = s.getCanvas()
    g = 18
    tw, th = (W - 4 * g) / 3, (H - 3 * g) / 2.35
    y0 = (H - (2 * th + g)) / 2
    slots = [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1)]
    for i, (cx, cy) in enumerate(slots):
        kt = prog(t, B["didnt"] + 0.05 + 0.06 * i, 0.35) * (1 - eio(prog(t, B["said"] - 0.1, 0.35)))
        if kt <= 0:
            continue
        r = skia.Rect.MakeXYWH(g + cx * (tw + g), y0 + cy * (th + g), tw, th)
        sc = lerp(0.6, 1, eob(kt))
        c.save()
        c.translate(r.centerX(), r.centerY())
        c.scale(sc, sc)
        c.translate(-r.centerX(), -r.centerY())
        rr = skia.RRect.MakeRectXY(r, 18, 18)
        c.save()
        c.clipRRect(rr, True)
        c.drawImageRect(recap_tile(i), r, SAMP)
        c.restore()
        c.drawRRect(rr, skia.Paint(AntiAlias=True, Color4f=col(WHITE, 0.4), Style=skia.Paint.kStroke_Style, StrokeWidth=2))
        f = font("Montserrat-Black", 24)
        wtxt = text_w(RECAP_T[i][0], f, 0.08)
        rrect(c, r.left() + 14, r.top() + 14, wtxt + 28, 40, 20, YEL)
        draw_text(c, RECAP_T[i][0], r.left() + 28, r.top() + 42, f, INK, 1.0, track=0.08)
        c.restore()
    live = skia.Rect.MakeXYWH(g + 2 * (tw + g), y0 + (th + g), tw, th)
    dst = skia.Rect(lerp(0, live.left(), k), lerp(0, live.top(), k), lerp(W, live.right(), k), lerp(H, live.bottom(), k))
    rr = skia.RRect.MakeRectXY(dst, 18 * k, 18 * k)
    c.save()
    c.clipRRect(rr, True)
    c.drawImageRect(sk_image(np.clip(img, 0, 255).astype(np.uint8)), dst, SAMP)
    c.restore()
    c.drawRRect(rr, skia.Paint(AntiAlias=True, Color4f=col(YEL, k), Style=skia.Paint.kStroke_Style, StrokeWidth=5))
    if k > 0.5:
        f = font("Montserrat-Black", 24)
        rrect(c, dst.left() + 14, dst.top() + 14, text_w("LIVE · NO EDITS", f, 0.08) + 28, 40, 20, RED, k)
        draw_text(c, "LIVE · NO EDITS", dst.left() + 28, dst.top() + 42, f, WHITE, k, track=0.08)
    return arr[..., :3].astype(np.float32)


# ------------------------------------------------------------------ hook, tracker, CTA, captions
def hook_overlay(c, t):
    """Drawn on a layer that sits behind him (see render())."""
    if t > B["news"]:
        return
    names = ["NEWS", "TRAILER", "CARTOON", "GAME", "1920s"]
    cols = [RED, (40, 40, 48), (255, 150, 0), (80, 200, 120), (150, 130, 100)]
    f = font("Montserrat-Black", 34)
    ws = [text_w(n, f, 0.06) + 44 for n in names]
    total = sum(ws) + 18 * 4
    x = W / 2 - total / 2
    fly = eio(prog(t, B["watch"] + 0.1, 0.45))
    for i, n in enumerate(names):
        k = prog(t, B["five"] + 0.07 * i, 0.3)
        if k <= 0:
            x += ws[i] + 18
            continue
        tx = lerp(x, 60 + i * 34, fly)
        ty = lerp(H - 250, 60, fly)
        sc = lerp(eob(k), 0.0, fly)
        c.save()
        c.translate(tx + ws[i] / 2, ty)
        c.scale(sc, sc)
        c.rotate((i - 2) * 3 * (1 - fly))
        rrect(c, -ws[i] / 2, -32, ws[i], 64, 32, cols[i], 1.0, shadow=10)
        draw_text(c, n, 0, 12, f, WHITE, 1.0, "c", track=0.06)
        c.restore()
        x += ws[i] + 18


def tracker(c, t):
    if not (B["watch"] + 0.4 <= t < B["rewind"]):
        return
    name, idx, lt = style_at(t)
    if name == "game" and lt > 0.2:
        return
    names = ["NEWS", "TRAILER", "CARTOON", "GAME", "1920s"]
    a = eo(prog(t, B["watch"] + 0.4, 0.3))
    x, y = 60, 44
    for i in range(5):
        on = i == idx
        done = i < idx
        r = 11 if on else 8
        c.drawCircle(x + i * 34 + 10, y + 16, r, skia.Paint(AntiAlias=True, Color4f=col(YEL if on else WHITE, a * (1 if on or done else 0.4))))
    if idx >= 0:
        k = eob(prog(lt, 0.0, 0.3))
        lab = f"{idx + 1}/5  {LABEL[name]}"
        f = font("Montserrat-Black", 26)
        c.save()
        c.translate(x + 180, y + 26)
        c.scale(k, k)
        rrect(c, -8, -26, text_w(lab, f, 0.06) + 24, 38, 19, (0, 0, 0), 0.55 * a)
        draw_text(c, lab, 4, 0, f, WHITE, a, track=0.06)
        c.restore()


def cta_overlay(c, t):
    k = prog(t, B["comment"] - 0.1, 0.45)
    if k <= 0:
        return
    e = eob(k)
    a = min(1, k * 3)
    w, h = 820, 118
    x, y = W / 2 - w / 2, H - 70 - h + 160 * (1 - e)
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), h / 2, h / 2)
    sh = skia.Paint(AntiAlias=True, Color4f=col((0, 0, 0), 0.45 * a))
    sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 20))
    c.drawRRect(rr, sh)
    c.drawRRect(rr, skia.Paint(AntiAlias=True, Color4f=col(WHITE, a)))
    c.drawCircle(x + 62, y + h / 2, 38, skia.Paint(AntiAlias=True, Color4f=col((124, 92, 255), a)))
    draw_text(c, "Y", x + 62, y + h / 2 + 15, font("Montserrat-Black", 40), WHITE, a, "c")
    typed = int(clamp((t - B["edit"]) / 0.08 + 1, 0, 4)) if t >= B["edit"] else 0
    if typed == 0:
        draw_text(c, "Add a comment…", x + 125, y + h / 2 + 15, font("SpaceGrotesk-Bold", 40), (150, 150, 160), a)
        tx = x + 125
    else:
        tx = x + 125 + draw_text(c, "EDIT"[:typed], x + 125, y + h / 2 + 19, font("Montserrat-Black", 52), INK, a)
    if int(t * 2.2) % 2 == 0 or typed == 0:
        c.drawRect(skia.Rect.MakeXYWH(tx + 6, y + 30, 4, h - 60), skia.Paint(Color4f=col((56, 151, 240), a)))
    kh = prog(t, B["how"] - 0.1, 0.3)
    bs = 1 + 0.25 * math.sin(math.pi * clamp(kh))
    c.save()
    c.translate(x + w - 62, y + h / 2)
    c.scale(bs, bs)
    c.drawCircle(0, 0, 40, skia.Paint(AntiAlias=True, Color4f=col((56, 151, 240) if typed else (200, 200, 210), a)))
    poly(c, [(-14, -16), (18, 0), (-14, 16), (-7, 0)], WHITE, a)
    c.restore()


def loud_overlay(c, t, al_img=None):
    k = prog(t, B["said"] - 0.05, 0.3)
    ko = prog(t, B["comment"] - 0.3, 0.25)
    if k > 0 and ko < 1:
        s = eob(k) * (1 - eio(ko))
        c.save()
        c.translate(W / 2, H - 110)
        c.scale(s, s)
        draw_text(c, "JUST BY SAYING IT", 0, 0, font("Montserrat-Black", 100), YEL, 1.0, "c", stroke=INK, sw=16, shadow=16)
        c.restore()


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


def draw_captions(c, t):
    name, _, lt = style_at(t)
    if recap_k(t) > 0.02 or (B["said"] - 0.1 < t < B["comment"] - 0.2):
        return
    if B["rewind"] <= t < B["rewind"] + REWIND:
        return
    if name == "news" and t > B["breaking"] - 0.1:
        return
    if name == "trailer" and t > B["in_"] - 0.1:
        return
    if name == "old":
        return
    for t0, t1, g in GROUPS:
        if not (t0 <= t < t1):
            continue
        words = [w["w"].upper() for w in g]
        y = H - 95 if t < B["comment"] - 0.1 else H - 240
        if name == "game":
            px = 9
            line = " ".join(words)
            pix_text(c, line, W / 2, y - 60, px, WHITE, 1.0, "c", outline=(0, 0, 0))
            return
        size = 66
        f = font("Montserrat-Black", size)
        gap = size * 0.55
        widths = [text_w(x, f) for x in words]
        total = sum(widths) + gap * (len(words) - 1)
        sc = lerp(0.86, 1, eob(prog(t, t0, 0.14)))
        c.save()
        c.translate(W / 2, y)
        c.scale(sc, sc)
        if name == "cartoon":
            c.rotate(-3)
        x = -total / 2
        palette = [(255, 59, 48), (0, 170, 255), (52, 199, 89), (255, 149, 0)]
        for j, (w, txt, wd) in enumerate(zip(g, words, widths)):
            active = w["s"] - 0.03 <= t < w["e"] + 0.05
            said = t >= w["s"] - 0.03
            if name == "cartoon":
                fill = palette[(hash(w["w"]) + j) % 4] if active else WHITE
            else:
                fill = YEL if active else WHITE
            c.save()
            c.translate(x + wd / 2, 0)
            s2 = 1.05 if active else 1.0
            c.scale(s2, s2)
            if name == "cartoon":
                WD.text3d(c, txt, 0, 0, f, fill if active else (255, 255, 255), side=(40, 90, 200) if not active else None,
                          depth=9, a=1.0 if said else 0.6, outline=(20, 40, 90))
            else:
                draw_text(c, txt, -wd / 2, 0, f, fill, 1.0 if said else 0.55, stroke=INK, sw=size * 0.2, shadow=8)
            c.restore()
            x += wd + gap
        c.restore()
        return


# ------------------------------------------------------------------ frame
def render(t, overlays=True, recap=True):
    rw = rewind_frame(t) if recap else None
    if rw is not None:
        return rw
    name, idx, lt = style_at(t)
    hold = 16 if name == "old" else None
    img, al, M = base_layers(t, hold)
    out_k = 0.0
    if name:
        _, a, b = STYLES[idx]
        out_k = prog(t, b - 0.12, 0.12)
    if name == "news":
        img = look_news(img, al, lt)
    elif name == "trailer":
        img = look_trailer(img, al, t, lt)
    elif name == "cartoon":
        bg, fg = WD.toon_world(t, lt, 1.0)
        a3 = al[..., None]
        img = WD.pixar_person(img, al) * a3 + bg * (1 - a3)
        img = over(img, fg)
    elif name == "game":
        img = WD.platformer(t, lt, B["level"], img, al)
    elif name == "old":
        img = look_old(img, al, t)
    img = pixel_transition(img, t)
    img = film_burn(img, t)
    if recap:
        img = globals()["recap"](t, img)
    arr = np.empty((H, W, 4), np.uint8)
    arr[..., :3] = np.clip(img, 0, 255).astype(np.uint8)
    arr[..., 3] = 255
    s = skia.Surface(arr)
    c = s.getCanvas()
    if overlays:
        if name == "news":
            news_overlay(c, t, lt, out_k)
        elif name == "trailer":
            trailer_overlay(c, t, lt, out_k)
        elif name == "cartoon":
            cartoon_overlay(c, t, lt, out_k)
        elif name == "game":
            score = int(1200 * max(0, lt) + 5000 * eo(prog(t, B["level"], 0.6)))
            coins = sum(1 for w in WORDS if B["game"] < w["s"] <= t) + (1 if t >= B["level"] else 0)
            game_overlay(c, t, lt, out_k, score, coins)
        elif name == "old":
            old_overlays(c, t)
            old_title(c, t, lt)
            intertitle(c, t)
        hook_overlay(c, t)
        transition(c, arr, t)
        if recap:
            tracker(c, t)
            loud_overlay(c, t)
            cta_overlay(c, t)
            draw_captions(c, t)
    out = arr[..., :3]
    fade = prog(t, DUR - 0.35, 0.35)
    if fade > 0:
        out = (out.astype(np.float32) * (1 - fade)).astype(np.uint8)
    return np.ascontiguousarray(out)


def render_chunk(args):
    i0, i1, path = args
    p = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", path],
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
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", final],
                   check=True)
    print("wrote", final)


if __name__ == "__main__":
    main()
