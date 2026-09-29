"""The edit. Every effect is locked to a word in the transcript (work/words.json).

    python3 render.py            -> out/final.mp4 (1920x1080, 30 fps)
    python3 render.py --stills   -> out/stills/*.jpg (one frame per beat, for checking)
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

from common import (DUR, FACE, FFMPEG, FONTS, FPS, H, NFRAMES, OUT, S0, SEGS, SH, SW, W, WORDS, WORK, clamp, eio,
                    ei, eo, eob, lerp, prog, spring, src_of_out, out_of_src, window, wt)

# ------------------------------------------------------------------ palette + fonts
INK = (17, 17, 20)
YEL = (255, 210, 63)
RED = (255, 59, 48)
VIO = (124, 92, 255)
PINK = (255, 92, 168)
ORG = (255, 178, 63)
WHITE = (255, 255, 255)
BGD = (13, 12, 20)


def col(rgb, a=1.0):
    return skia.Color4f(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, clamp(a))


_TF = {}


def tf(name):
    if name not in _TF:
        _TF[name] = skia.Typeface.MakeFromFile(os.path.join(FONTS, name + ".ttf"))
    return _TF[name]


def font(name, size):
    f = skia.Font(tf(name), size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    f.setSubpixel(True)
    return f


def text_w(txt, f, track=0.0):
    return f.measureText(txt) + track * f.getSize() * max(len(txt) - 1, 0)


def draw_text(c, txt, x, y, f, fill=WHITE, a=1.0, align="l", track=0.0, stroke=None, sw=0.0, shadow=0.0):
    """Draw text with optional stroke/shadow. align l/c/r; y is the baseline."""
    w = text_w(txt, f, track)
    x0 = x - (w / 2 if align == "c" else w if align == "r" else 0)
    blob = None
    if track == 0:
        blob = skia.TextBlob.MakeFromString(txt, f)
    else:
        b = skia.TextBlobBuilder()
        glyphs = f.textToGlyphs(txt)
        widths = f.getWidths(glyphs)
        pos, xx = [], 0.0
        for gw in widths:
            pos.append(skia.Point(xx, 0))
            xx += gw + track * f.getSize()
        b.allocRunPos(f, glyphs, pos)
        blob = b.make()
    if shadow > 0:
        p = skia.Paint(AntiAlias=True, Color4f=col((0, 0, 0), 0.45 * a))
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, shadow))
        c.drawTextBlob(blob, x0, y + shadow * 0.6, p)
    if stroke is not None and sw > 0:
        p = skia.Paint(AntiAlias=True, Color4f=col(stroke, a), Style=skia.Paint.kStroke_Style, StrokeWidth=sw,
                       StrokeJoin=skia.Paint.kRound_Join)
        c.drawTextBlob(blob, x0, y, p)
    c.drawTextBlob(blob, x0, y, skia.Paint(AntiAlias=True, Color4f=col(fill, a)))
    return w


# ------------------------------------------------------------------ data (lazy, per worker)
_D = {}


def D(key):
    if key not in _D:
        if key in ("frames", "alpha"):
            _D[key] = np.load(os.path.join(WORK, key + ".npy"), mmap_mode="r")
        elif key == "plate":
            _D[key] = np.load(os.path.join(WORK, "plate.npy"))
        elif key == "palm":
            _D[key] = np.load(os.path.join(WORK, "palm.npy"))
        elif key.startswith("clip_"):
            _D[key] = np.load(os.path.join(WORK, key + ".npy"), mmap_mode="r")
        elif key == "nf":
            _D[key] = int(open(os.path.join(WORK, "nframes.txt")).read())
    return _D[key]


# ------------------------------------------------------------------ beats (output seconds)
B = dict(
    watch=wt("Watch", 3), over=wt("over.", 2), zoom=wt("Zoom", 4.5), hand_end=wt("hand.", 5.3, end=True),
    here=wt("here", 7.7) + 0.08, d3=wt("3D.", 8.8), nice=wt("Nice.", 10),
    grab=wt("grab", 11.5), throw=wt("throw", 13.0), straight=wt("straight", 14.0),
    impact=wt("camera.", 14.6, end=True) - 0.22, okay=wt("Okay.", 16.6), harder=wt("Harder", 17.2),
    sep=wt("Separate", 18.4), l_bg=wt("background,", 21), l_me=wt("me,", 21.5), l_text=wt("text.", 22.4),
    text_end=wt("text.", 22.4, end=True), remove=wt("remove", 24.7), rm=wt("me.", 25.0) + 0.1,
    bring=wt("Bring", 27.8), back=wt("back.", 28.3) - 0.05,
    frame=wt("frame", 34.4), left=wt("left", 36.2), anat=wt("anatomy", 37.5), viral=wt("viral", 38.5),
    first=wt("First,", 39.9), hook=wt("hook,", 40.8), ret=wt("retention,", 41.8), share=wt("share.", 43.9),
    full=wt("Back", 47.0), videos=wt("videos", 51.0), floating=wt("floating", 51.3), d3b=wt("3D.", 52.8),
    perfect=wt("Perfect!", 54.2), last=wt("Last", 56.8),
    cine=wt("cinematic", 64.5), dramatic=wt("dramatic", 67.4), slow=wt("slow", 68.9), movie=wt("movie", 70.9),
    crazy=wt("That's", 73.6), all_=wt("all", 77.0), edited=wt("edited", 78.2), ai=wt("AI.", 79.3),
    comment=wt("Comment", 80.5), edit=wt("EDIT", 81.0), how=wt("how.", 82.6),
)
B["screens_out"] = out_of_src(54.86)
B["layers_close"] = B["text_end"] + 0.02
B["text_fade"] = out_of_src(29.02)


# ------------------------------------------------------------------ camera
def cam_clamp(z, cx, cy):
    hw, hh = W / (2 * z * S0), H / (2 * z * S0)
    return z, clamp(cx, hw, SW - hw), clamp(cy, hh, SH - hh)


def camera(t, si):
    z0 = SEGS[si][2]
    z, cx, cy = z0, SW / 2, (SH / 2 if z0 == 1.0 else 205.0)
    # "watch this": small push
    k = eo(prog(t, B["watch"] - 0.05, 0.3)) * (1 - prog(t, B["zoom"] - 0.1, 0.01))
    z *= 1 + 0.05 * k
    cy = lerp(cy, 205, k)
    # zoom on the hand, hold for the logo, ease back out on "grab"
    kin = eio(prog(t, B["zoom"] - 0.05, 0.55))
    kout = eio(prog(t, B["grab"] - 0.1, 0.75))
    kh = kin * (1 - kout)
    if kh > 0:
        z = lerp(z, 1.6, kh)
        cx = lerp(cx, 250, kh)
        cy = lerp(cy, 292, kh)
    # documentary: slow push-in toward the face, snapped back on "That's crazy"
    kp = eio(prog(t, B["slow"], 4.2)) * (1 - eio(prog(t, B["crazy"], 0.3)))
    if kp > 0:
        z = lerp(z, 1.2, kp)
        cy = lerp(cy, 175, kp)
    z, cx, cy = cam_clamp(z, cx, cy)
    # impact shake
    sx = sy = 0.0
    d = t - B["impact"]
    if 0 <= d < 0.45:
        amp = 26 * (1 - d / 0.45) ** 2
        sx = amp * math.sin(d * 97)
        sy = amp * math.cos(d * 83)
    return z, cx, cy, sx, sy


def affine(z, cx, cy, sx=0.0, sy=0.0):
    s = z * S0
    return np.float32([[s, 0, W / 2 - cx * s + sx], [0, s, H / 2 - cy * s + sy]])


def to_out(M, x, y):
    return M[0, 0] * x + M[0, 2], M[1, 1] * y + M[1, 2]


# ------------------------------------------------------------------ image helpers
_LUT = None


def grade(img):
    """Mild S-curve + a touch of warmth for the phone footage."""
    global _LUT
    if _LUT is None:
        x = np.arange(256) / 255.0
        s = x + 0.10 * np.sin(2 * np.pi * (x - 0.5)) * -0.5 * 2 * (0.5 - np.abs(x - 0.5))
        s = np.clip(0.5 + (s - 0.5) * 1.06, 0, 1)
        r = np.clip(s * 1.015 + 0.004, 0, 1)
        b = np.clip(s * 0.985, 0, 1)
        _LUT = np.stack([(r * 255), (s * 255), (b * 255)], -1).astype(np.uint8)[:, None, :]
    out = np.empty_like(img)
    for c in range(3):
        out[..., c] = cv2.LUT(img[..., c], _LUT[:, 0, c])
    return out


def sharpen(img, amt=0.55):
    blur = cv2.GaussianBlur(img, (0, 0), 1.6)
    return cv2.addWeighted(img, 1 + amt, blur, -amt, 0)


def satur(img, s):
    g = img.mean(2, keepdims=True)
    return g + (img - g) * s


def src_frame(t):
    s, si = src_of_out(t)
    fi = int(np.clip(round(s * FPS), 0, D("nf") - 1))
    return fi, si, s


def base_layers(t, M):
    fi, si, s = src_frame(t)
    f = np.ascontiguousarray(D("frames")[fi])
    a = np.ascontiguousarray(D("alpha")[fi])
    base = cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    base = sharpen(grade(base))
    al = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32) / 255
    return base, al, fi


def plate_out(M):
    p = cv2.warpAffine(D("plate"), M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    return sharpen(grade(p))


def rgba_surface(img_rgb):
    arr = np.empty((H, W, 4), np.uint8)
    arr[..., :3] = img_rgb
    arr[..., 3] = 255
    return arr, skia.Surface(arr)


def new_layer(w=W, h=H):
    arr = np.zeros((h, w, 4), np.uint8)
    return arr, skia.Surface(arr)


def over(dst, layer, mask=None):
    """dst float32 RGB; layer uint8 RGBA (unpremultiplied); optional extra mask multiplies layer alpha."""
    a = layer[..., 3:4].astype(np.float32) / 255
    if mask is not None:
        a = a * mask[..., None]
    return dst * (1 - a) + layer[..., :3].astype(np.float32) * a


def sk_image(arr, unpremul=True):
    arr = np.ascontiguousarray(arr)
    if arr.shape[2] == 3:
        arr = np.concatenate([arr, np.full(arr.shape[:2] + (1,), 255, np.uint8)], 2)
    return skia.Image.fromarray(arr, colorType=skia.ColorType.kRGBA_8888_ColorType,
                                alphaType=skia.AlphaType.kUnpremul_AlphaType if unpremul else skia.AlphaType.kPremul_AlphaType)


SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)


# ------------------------------------------------------------------ 1. hook: kinetic type behind him
def hook_layer(t):
    if t > B["watch"] + 0.45:
        return None
    arr, s = new_layer()
    c = s.getCanvas()
    out = eio(prog(t, B["watch"], 0.35))
    fb = font("Montserrat-Black", 128)
    words = [("EDITING", wt("Editing", 0), 300), ("VIDEOS", wt("videos", 0.5), 428), ("MANUALLY", wt("manually", 1), 556)]
    for txt, t0, y in words:
        k = prog(t, t0 - 0.04, 0.28)
        if k <= 0:
            continue
        a = min(1, k * 2) * (1 - out)
        c.save()
        c.translate(775, y + 40 * (1 - eob(k)) - 30 * out)
        c.scale(1 + 0.15 * out, 1 + 0.15 * out)
        draw_text(c, txt, 0, 0, fb, INK, a, "r")
        c.restore()
    # strike through MANUALLY on "over"
    ko = prog(t, B["over"] - 0.05, 0.25)
    if ko > 0:
        w = text_w("MANUALLY", fb)
        p = skia.Paint(AntiAlias=True, Color4f=col(RED, 1 - out), StrokeWidth=16, Style=skia.Paint.kStroke_Style,
                       StrokeCap=skia.Paint.kRound_Cap)
        x0 = 775 - w - 10
        c.drawLine(x0, 520, x0 + (w + 20) * eo(ko), 506, p)
    fs = font("Montserrat-Black", 58)
    km = prog(t, wt("might", 1.5) - 0.04, 0.25)
    if km > 0:
        draw_text(c, "MIGHT BE", 1130, 330 + 20 * (1 - eob(km)), fs, INK, min(1, km * 2) * (1 - out))
    kv = prog(t, B["over"] - 0.04, 0.3)
    if kv > 0:
        c.save()
        c.translate(1125, 520)
        c.rotate(-5)
        sc = lerp(2.2, 1.0, eob(kv)) * (1 + 0.15 * out)
        c.scale(sc, sc)
        draw_text(c, "OVER.", 0, 0, font("Montserrat-Black", 196), RED, min(1, kv * 3) * (1 - out))
        c.restore()
    return arr


# ------------------------------------------------------------------ 2. the 3D logo
def logo_outline(n=14):
    pts = []
    r = 0.26
    for cx, cy, a0 in ((0.5 - r, -0.5 + r, -90), (0.5 - r, 0.5 - r, 0), (-0.5 + r, 0.5 - r, 90), (-0.5 + r, -0.5 + r, 180)):
        for i in range(n):
            a = math.radians(a0 + 90 * i / (n - 1))
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


OUTLINE = logo_outline()
TRI = [(-0.13, -0.2), (0.22, 0.0), (-0.13, 0.2)]


def draw_logo(c, x, y, size, yaw=0.0, pitch=0.0, depth=1.0, a=1.0, glow=0.0):
    cyw, syw, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    f = 5.0
    dz = 0.34 * depth

    def P(px, py, pz):
        X = px * cyw + pz * syw
        Z = -px * syw + pz * cyw
        Y = py * cp - Z * sp
        Z2 = py * sp + Z * cp
        k = f / (f + Z2)
        return skia.Point(x + X * size * k, y + Y * size * k), Z2

    front = [P(px, py, -dz / 2) for px, py in OUTLINE]
    back = [P(px, py, dz / 2) for px, py in OUTLINE]
    facing = cyw * cp > 0
    if glow > 0:
        p = skia.Paint(AntiAlias=True, Color4f=col(PINK, 0.55 * glow * a))
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, size * 0.25))
        c.drawCircle(x, y, size * 0.55, p)
    # far cap
    far, near = (back, front) if facing else (front, back)
    path = skia.Path()
    path.addPoly([p for p, _ in far], True)
    c.drawPath(path, skia.Paint(AntiAlias=True, Color4f=col((40, 24, 110), a)))
    # side walls, far to near
    if depth > 0.02:
        n = len(OUTLINE)
        quads = []
        for i in range(n):
            j = (i + 1) % n
            zc = front[i][1] + front[j][1] + back[i][1] + back[j][1]
            ex, ey = OUTLINE[j][0] - OUTLINE[i][0], OUTLINE[j][1] - OUTLINE[i][1]
            nx, ny = ey, -ex
            ln = math.hypot(nx, ny) + 1e-9
            nxr = (nx / ln) * cyw
            lit = clamp(0.55 + 0.45 * (-nxr * 0.7 - (ny / ln) * 0.6))
            quads.append((zc, i, j, lit))
        quads.sort(key=lambda q: -q[0])
        for _, i, j, lit in quads:
            qp = skia.Path()
            qp.addPoly([front[i][0], front[j][0], back[j][0], back[i][0]], True)
            shade = (int(lerp(46, 150, lit)), int(lerp(26, 90, lit)), int(lerp(120, 255, lit)))
            pp = skia.Paint(AntiAlias=True, Color4f=col(shade, a))
            c.drawPath(qp, pp)
            pp.setStyle(skia.Paint.kStroke_Style)
            pp.setStrokeWidth(0.8)
            c.drawPath(qp, pp)
    # near face with gradient + play glyph
    fp = skia.Path()
    fp.addPoly([p for p, _ in near], True)
    b = fp.getBounds()
    shader = skia.GradientShader.MakeLinear([skia.Point(b.left(), b.top()), skia.Point(b.right(), b.bottom())],
                                            [skia.Color4f(*[v / 255 for v in VIO], a).toColor(),
                                             skia.Color4f(*[v / 255 for v in PINK], a).toColor(),
                                             skia.Color4f(*[v / 255 for v in ORG], a).toColor()])
    c.drawPath(fp, skia.Paint(AntiAlias=True, Shader=shader))
    zface = -dz / 2 if facing else dz / 2
    tp = skia.Path()
    tp.addPoly([P(px if facing else -px, py, zface)[0] for px, py in TRI], True)
    c.drawPath(tp, skia.Paint(AntiAlias=True, Color4f=col(WHITE, a), PathEffect=skia.CornerPathEffect.Make(size * 0.04)))
    # gloss sweep
    gl = skia.Paint(AntiAlias=True)
    gx = b.left() + (b.width()) * ((math.sin(yaw * 1.3) + 1) / 2)
    gl.setShader(skia.GradientShader.MakeLinear(
        [skia.Point(gx - size * 0.3, b.top()), skia.Point(gx + size * 0.3, b.bottom())],
        [skia.Color4f(1, 1, 1, 0).toColor(), skia.Color4f(1, 1, 1, 0.28 * a).toColor(), skia.Color4f(1, 1, 1, 0).toColor()]))
    c.drawPath(fp, gl)
    edge = skia.Paint(AntiAlias=True, Color4f=col(WHITE, 0.35 * a), Style=skia.Paint.kStroke_Style, StrokeWidth=max(1.0, size * 0.012))
    c.drawPath(fp, edge)


def palm_at(fi):
    p = D("palm")
    k = int(np.clip(fi - p[0, 0], 0, len(p) - 1))
    return float(p[k, 1]), float(p[k, 2])


IMPACT_XY = (W * 0.5, H * 0.44)


def logo_state(t, M, fi):
    """-> None or dict(x, y, size, yaw, depth, a, glow) in output px."""
    if t < B["here"] - 0.02 or t > B["impact"] + 0.02:
        return None
    px, py = palm_at(fi)
    ox, oy = to_out(M, px, py)
    zs = M[0, 0] / S0
    size0 = 66 * S0 * zs
    x, y = ox, oy - size0 * 0.62
    kp = prog(t, B["here"], 0.45)
    size = size0 * spring(kp, 2.2, 6) if kp < 1 else size0
    k3 = eo(prog(t, B["d3"], 0.9))
    depth = k3
    yaw = 2 * math.pi * k3 + 0.45 * math.sin(1.7 * (t - B["d3"])) * prog(t, B["d3"] + 0.6, 0.6)
    pitch = 0.22 * k3
    y += -8 * zs * math.sin(2.4 * (t - B["here"])) * k3
    glow = 0.6 * k3
    # wind-up on "throw it"
    kw = eo(prog(t, B["throw"] - 0.05, 0.55))
    x += -30 * zs * kw
    y += -110 * zs * kw
    yaw += -0.6 * kw
    size *= 1 + 0.12 * kw
    # launch straight at the lens
    t0, t1 = B["straight"] + 0.05, B["impact"]
    kl = prog(t, t0, t1 - t0)
    if kl > 0:
        e = ei(kl)
        x = lerp(x, IMPACT_XY[0], eio(kl))
        y = lerp(y, IMPACT_XY[1], eio(kl))
        size = size * (1 + 26 * e * e + 2 * e)
        yaw += 4 * math.pi * e
        pitch += 0.5 * e
        glow = 0.6 + 0.4 * e
    return dict(x=x, y=y, size=size, yaw=yaw, pitch=pitch, depth=max(depth, 0.001), a=1.0, glow=glow, kl=kl)


def palm_shadow(c, st, M, fi):
    if st["kl"] > 0:
        return
    px, py = palm_at(fi)
    ox, oy = to_out(M, px, py)
    zs = M[0, 0] / S0
    lift = clamp((oy - st["y"]) / (st["size"] * 1.2 + 1e-6))
    p = skia.Paint(AntiAlias=True, Color4f=col((20, 10, 10), 0.32 * clamp(st["size"] / (66 * S0 * zs)) / (0.6 + lift)))
    p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10 * zs))
    c.drawOval(skia.Rect.MakeXYWH(ox - st["size"] * 0.45, oy - 12 * zs, st["size"] * 0.9, 20 * zs), p)


# ------------------------------------------------------------------ 3. glass crack
@lru_cache(None)
def crack_image():
    rng = np.random.default_rng(7)
    arr, s = new_layer()
    c = s.getCanvas()
    cx, cy = IMPACT_XY
    rays = sorted(rng.uniform(0, 2 * math.pi, 17))
    ray_pts = []
    lines = []
    for a0 in rays:
        pts = [(cx + 34 * math.cos(a0), cy + 34 * math.sin(a0))]
        a, r = a0, 34.0
        L = rng.uniform(650, 1500)
        while r < L:
            r += rng.uniform(28, 70)
            a += rng.normal(0, 0.05)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
            if rng.random() < 0.18 and r > 120:
                b = a + rng.choice([-1, 1]) * rng.uniform(0.25, 0.6)
                bp = [pts[-1]]
                rb = 0.0
                Lb = rng.uniform(80, 280)
                while rb < Lb:
                    rb += rng.uniform(25, 55)
                    b += rng.normal(0, 0.1)
                    bp.append((bp[-1][0] + 40 * math.cos(b), bp[-1][1] + 40 * math.sin(b)))
                lines.append((bp, 1.8))
        ray_pts.append(pts)
        lines.append((pts, 3.2))
    # web rings
    for R in (70, 150, 260, 420):
        for i in range(len(ray_pts)):
            if rng.random() < 0.25:
                continue
            p1, p2 = ray_pts[i], ray_pts[(i + 1) % len(ray_pts)]

            def at(pp):
                for q in pp:
                    if math.hypot(q[0] - cx, q[1] - cy) >= R:
                        return q
                return pp[-1]
            a_, b_ = at(p1), at(p2)
            mid = ((a_[0] + b_[0]) / 2 + rng.normal(0, 6), (a_[1] + b_[1]) / 2 + rng.normal(0, 6))
            lines.append(([a_, mid, b_], 2.0))
    # facets
    for i in range(len(ray_pts)):
        if rng.random() < 0.55:
            p1, p2 = ray_pts[i], ray_pts[(i + 1) % len(ray_pts)]
            k = min(len(p1), len(p2), int(rng.integers(3, 8)))
            path = skia.Path()
            path.addPoly([skia.Point(*q) for q in p1[:k]] + [skia.Point(*q) for q in reversed(p2[:k])], True)
            c.drawPath(path, skia.Paint(AntiAlias=True, Color4f=col(WHITE, rng.uniform(0.03, 0.1))))
    dark = skia.Paint(AntiAlias=True, Color4f=col((0, 0, 0), 0.35), Style=skia.Paint.kStroke_Style,
                      StrokeJoin=skia.Paint.kRound_Join, StrokeCap=skia.Paint.kRound_Cap)
    lite = skia.Paint(AntiAlias=True, Color4f=col(WHITE, 0.92), Style=skia.Paint.kStroke_Style,
                      StrokeJoin=skia.Paint.kRound_Join, StrokeCap=skia.Paint.kRound_Cap)
    for pts, wdt in lines:
        path = skia.Path()
        path.addPoly([skia.Point(*q) for q in pts], False)
        dark.setStrokeWidth(wdt * 2.4)
        c.save(); c.translate(1.5, 1.5); c.drawPath(path, dark); c.restore()
        lite.setStrokeWidth(wdt)
        c.drawPath(path, lite)
    # pulverised centre
    for _ in range(90):
        r = abs(rng.normal(0, 22))
        a = rng.uniform(0, 2 * math.pi)
        qx, qy = cx + r * math.cos(a), cy + r * math.sin(a)
        path = skia.Path()
        path.addPoly([skia.Point(qx + rng.normal(0, 6), qy + rng.normal(0, 6)) for _ in range(3)], True)
        c.drawPath(path, skia.Paint(AntiAlias=True, Color4f=col(WHITE, rng.uniform(0.3, 0.8))))
    g = skia.Paint(AntiAlias=True, Color4f=col(WHITE, 0.5))
    g.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 18))
    c.drawCircle(cx, cy, 30, g)
    return sk_image(arr)


def draw_crack(c, t):
    d = t - B["impact"]
    if d < 0:
        return
    fall = t - B["okay"] + 0.05
    if fall > 0.75:
        return
    a = 1.0 if fall < 0 else 1 - prog(fall, 0.15, 0.6)
    dy = 0 if fall < 0 else 0.5 * 5200 * fall ** 2
    c.save()
    c.translate(0, dy)
    if fall > 0:
        c.rotate(3 * fall, W / 2, H / 2)
    c.drawImage(crack_image(), 0, 0, SAMP, skia.Paint(Alphaf=a))
    c.restore()
    if d < 0.2:
        c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Color4f=col(WHITE, 0.85 * (1 - d / 0.2) ** 2)))


# ------------------------------------------------------------------ 4. layers, remove me, bring me back
@lru_cache(None)
def title_layer():
    """'NO TIMELINE' layer that sits between the room and him."""
    arr, s = new_layer()
    c = s.getCanvas()
    f = font("Montserrat-Black", 214)
    draw_text(c, "NO TIMELINE", W / 2, 520, f, YEL, 1.0, "c", stroke=INK, sw=16, shadow=14)
    return arr


@lru_cache(None)
def dissolve_field():
    rng = np.random.default_rng(3)
    n = rng.random((H // 60, W // 60)).astype(np.float32)
    n = cv2.resize(n, (W, H), interpolation=cv2.INTER_CUBIC)
    n = (n - n.min()) / (n.max() - n.min())
    fine = cv2.GaussianBlur(rng.random((H, W)).astype(np.float32), (0, 0), 1.0)
    xg = np.linspace(0, 1, W, dtype=np.float32)[None, :]
    f = 0.72 * xg + 0.18 * n + 0.10 * fine
    return (f - f.min()) / (f.max() - f.min())


@lru_cache(None)
def particles():
    """Particles sampled from his pixels at the moment he dissolves."""
    rng = np.random.default_rng(9)
    t = B["rm"] + 0.2
    z, cx, cy, _, _ = camera(t, src_frame(t)[1])
    M = affine(z, cx, cy)
    base, al, _ = base_layers(t, M)
    ys, xs = np.nonzero(al > 0.6)
    k = rng.choice(len(xs), 5000, replace=False)
    xs, ys = xs[k].astype(np.float32), ys[k].astype(np.float32)
    colr = base[ys.astype(int), xs.astype(int)].astype(np.float32)
    th = dissolve_field()[ys.astype(int), xs.astype(int)]
    vx = rng.uniform(80, 420, len(xs)).astype(np.float32)
    vy = rng.uniform(-260, -40, len(xs)).astype(np.float32)
    sz = rng.uniform(1.5, 4.0, len(xs)).astype(np.float32)
    return xs, ys, colr, th, vx, vy, sz


def dissolve_amount(t):
    """0 = fully present, 1 = gone. Out on 'remove me', back on 'bring me back'."""
    return eio(prog(t, B["rm"], 1.0)) * (1 - eio(prog(t, B["back"], 0.85)))


def draw_particles(img, t):
    xs, ys, colr, th, vx, vy, sz = particles()
    q_out = (t - B["rm"]) / 1.0
    q_in = (B["back"] + 0.85 - t) / 0.85
    if B["rm"] <= t < B["rm"] + 2.0:
        age = t - (B["rm"] + eio_inv(th) * 1.0)
    elif B["back"] - 0.9 <= t <= B["back"] + 0.9:
        age = (B["back"] + (1 - eio_inv(th)) * 0.85) - t
        age = np.where(t < B["back"] + (1 - eio_inv(th)) * 0.85, age, -1)
    else:
        return img
    live = (age > 0) & (age < 1.1)
    if not live.any():
        return img
    ag = age[live]
    px = xs[live] + vx[live] * ag + 60 * ag ** 2
    py = ys[live] + vy[live] * ag - 40 * ag ** 2
    a = np.clip(1 - ag / 1.1, 0, 1) ** 1.5
    layer = np.zeros((H, W, 3), np.float32)
    wgt = np.zeros((H, W), np.float32)
    for dx in (0, 1):
        for dy in (0, 1):
            xi = np.clip(px.astype(int) + dx, 0, W - 1)
            yi = np.clip(py.astype(int) + dy, 0, H - 1)
            np.add.at(wgt, (yi, xi), a)
            for ch in range(3):
                np.add.at(layer[..., ch], (yi, xi), a * (colr[live, ch] * 0.6 + 255 * 0.4))
    wgt = cv2.GaussianBlur(wgt, (0, 0), 1.0)
    layer = cv2.GaussianBlur(layer, (0, 0), 1.0)
    m = np.clip(wgt, 0, 1)[..., None]
    img = img * (1 - m) + (layer / np.maximum(wgt[..., None], 1e-4)) * m
    return img


def eio_inv(y):
    """Inverse of eio on [0,1] (numeric) so particles leave exactly when their pixel dissolves."""
    xs = np.linspace(0, 1, 256)
    return np.interp(y, [eio(v) for v in xs], xs)


def project_plane(z, e, scale):
    """Corners of a WxH plane at depth z under the exploded-view camera -> list of skia points."""
    yaw = math.radians(-42 * e)
    pitch = math.radians(12 * e)
    f = 2200.0
    pts = []
    for x, y in ((-W / 2, -H / 2), (W / 2, -H / 2), (W / 2, H / 2), (-W / 2, H / 2)):
        X = x * math.cos(yaw) + z * math.sin(yaw)
        Z = -x * math.sin(yaw) + z * math.cos(yaw)
        Y = y * math.cos(pitch) - Z * math.sin(pitch)
        Z2 = y * math.sin(pitch) + Z * math.cos(pitch)
        k = f / (f + Z2)
        pts.append(skia.Point(W / 2 + X * k * scale - 90 * e, H / 2 + Y * k * scale + 10 * e))
    return pts


def draw_plane(c, img, pts, alpha=1.0, border=0.0):
    m = skia.Matrix()
    m.setPolyToPoly([skia.Point(0, 0), skia.Point(W, 0), skia.Point(W, H), skia.Point(0, H)], pts)
    c.save()
    c.concat(m)
    c.drawImage(img, 0, 0, SAMP, skia.Paint(Alphaf=alpha))
    if border > 0:
        c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(AntiAlias=True, Color4f=col(WHITE, 0.8 * border),
                                                   Style=skia.Paint.kStroke_Style, StrokeWidth=5))
    c.restore()


def chip(c, x, y, txt, fill=YEL, fg=INK, size=34, a=1.0, sc=1.0):
    f = font("Montserrat-Black", size)
    w = text_w(txt, f, 0.06)
    c.save()
    c.translate(x, y)
    c.scale(sc, sc)
    r = skia.RRect.MakeRectXY(skia.Rect(-18, -size * 0.95, w + 18, size * 0.45), 14, 14)
    sh = skia.Paint(AntiAlias=True, Color4f=col((0, 0, 0), 0.4 * a))
    sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8))
    c.drawRRect(r, sh)
    c.drawRRect(r, skia.Paint(AntiAlias=True, Color4f=col(fill, a)))
    draw_text(c, txt, 0, 0, f, fg, a, track=0.06)
    c.restore()


@lru_cache(None)
def studio_bg():
    arr, s = new_layer()
    arr[..., 3] = 255
    c = s.getCanvas()
    c.drawPaint(skia.Paint(Shader=skia.GradientShader.MakeRadial(
        skia.Point(W * 0.55, H * 0.45), W * 0.8,
        [skia.Color4f(0.12, 0.10, 0.2, 1).toColor(), skia.Color4f(0.03, 0.03, 0.06, 1).toColor()])))
    p = skia.Paint(AntiAlias=True, Color4f=col((255, 255, 255), 0.07))
    for x in range(0, W + 1, 48):
        for y in range(0, H + 1, 48):
            c.drawCircle(x, y, 1.6, p)
    return arr[..., :3].astype(np.float32)


def layers_section(t, base, al, M):
    """Returns composited float frame for the layer beats, or None when not active."""
    t_open, t_close = B["sep"] - 0.05, B["layers_close"]
    tf_ = B["text_fade"]
    if not (t_open <= t <= tf_ + 0.5):
        return None
    e = eio(prog(t, t_open, 0.9)) * (1 - eio(prog(t, t_close, 0.75)))
    text_a = eo(prog(t, B["l_text"] - 0.05, 0.4)) * (1 - prog(t, tf_, 0.45))
    dz = dissolve_amount(t)
    plate = plate_out(M).astype(np.float32)
    basef = base.astype(np.float32)
    # background with him removed where needed
    need_plate = max(e, clamp(dz * 6))
    if need_plate > 0:
        ad = cv2.GaussianBlur(cv2.dilate(al, np.ones((15, 15), np.uint8)), (0, 0), 4)[..., None]
        bgl = basef * (1 - ad * need_plate) + plate * ad * need_plate
    else:
        bgl = basef
    person_a = al.copy()
    glow = None
    if dz > 0:
        fld = dissolve_field()
        thr = dz * 1.08 - 0.04
        keep = np.clip((fld - thr) / 0.04, 0, 1)
        person_a = person_a * keep
        band = np.clip(1 - np.abs(fld - thr) / 0.018, 0, 1) ** 2 * al * (0 < dz < 1)
        band = cv2.GaussianBlur(band, (0, 0), 2.5)
        glow = band
    tl = title_layer()
    if e <= 0.001:
        out = bgl
        if text_a > 0:
            out = over(out, tl, np.full((H, W), text_a, np.float32))
        out = out * (1 - person_a[..., None]) + basef * person_a[..., None]
        if glow is not None:
            out = out + glow[..., None] * np.array([90, 190, 255], np.float32) * 0.7
            out = draw_particles(out, t)
        return out
    # exploded 3D view
    arr, s = rgba_surface(studio_bg().astype(np.uint8))
    c = s.getCanvas()
    sc = 1 - 0.45 * e
    d = 760 * e
    planes = [(d, sk_image(bgl.astype(np.uint8)), "BACKGROUND", B["l_bg"]),
              (0, sk_image(tl), "TEXT", B["l_text"]),
              (-d, sk_image(np.dstack([base, (person_a * 255).astype(np.uint8)])), "ME", B["l_me"])]
    for z, img, label, tl_t in planes:
        pts = project_plane(z, e, sc)
        if label == "TEXT":
            if text_a <= 0:
                continue
            draw_plane(c, img, pts, text_a)
            fr = skia.Path()
            fr.addPoly(pts, True)
            c.drawPath(fr, skia.Paint(AntiAlias=True, Color4f=col(YEL, 0.55 * text_a * e), Style=skia.Paint.kStroke_Style,
                                      StrokeWidth=3, PathEffect=skia.DashPathEffect.Make([18, 12], 0)))
        else:
            draw_plane(c, img, pts, 1.0, border=e if label == "BACKGROUND" else 0)
            if label == "ME":
                fr = skia.Path()
                fr.addPoly(pts, True)
                c.drawPath(fr, skia.Paint(AntiAlias=True, Color4f=col(WHITE, 0.5 * e), Style=skia.Paint.kStroke_Style,
                                          StrokeWidth=3, PathEffect=skia.DashPathEffect.Make([18, 12], 0)))
        kl = prog(t, tl_t - 0.05, 0.35)
        if kl > 0 and e > 0.3:
            p0 = {"BACKGROUND": pts[0], "TEXT": pts[1], "ME": pts[1]}[label]
            dx = {"BACKGROUND": 10, "TEXT": -110, "ME": -70}[label]
            dy = {"BACKGROUND": -22, "TEXT": -22, "ME": -22}[label]
            chip(c, p0.x() + dx, p0.y() + dy, label, YEL if label != "ME" else WHITE, INK, 34, e * min(1, kl * 3),
                 0.6 + 0.4 * eob(kl))
    return arr[..., :3].astype(np.float32)


# ------------------------------------------------------------------ 5. frame on the right + anatomy of a viral reel
CARD = skia.Rect(1130, 105, 1130 + 486, 105 + 864)
CROP = (960 - 304, 0, 960 + 304, H)


def frame_k(t):
    return eio(prog(t, B["frame"] - 0.05, 0.75)) * (1 - eio(prog(t, B["full"] - 0.05, 0.7)))


def icon_heart(c, x, y, s, p):
    path = skia.Path()
    path.moveTo(x, y + s * 0.35)
    path.cubicTo(x - s * 0.9, y - s * 0.25, x - s * 0.35, y - s * 0.85, x, y - s * 0.35)
    path.cubicTo(x + s * 0.35, y - s * 0.85, x + s * 0.9, y - s * 0.25, x, y + s * 0.35)
    c.drawPath(path, p)


def icon_bubble(c, x, y, s, p):
    c.drawCircle(x, y - s * 0.1, s * 0.45, p)
    path = skia.Path()
    path.addPoly([skia.Point(x - s * 0.35, y + s * 0.15), skia.Point(x - s * 0.5, y + s * 0.5), skia.Point(x - s * 0.05, y + s * 0.3)], True)
    c.drawPath(path, p)


def icon_share(c, x, y, s, p):
    path = skia.Path()
    path.addPoly([skia.Point(x - s * 0.5, y - s * 0.05), skia.Point(x + s * 0.5, y - s * 0.45),
                  skia.Point(x + s * 0.15, y + s * 0.5), skia.Point(x + s * 0.02, y + s * 0.08)], True)
    c.drawPath(path, p)


def icon_hook(c, x, y, s, a):
    p = skia.Paint(AntiAlias=True, Color4f=col(YEL, a), Style=skia.Paint.kStroke_Style, StrokeWidth=s * 0.12,
                   StrokeCap=skia.Paint.kRound_Cap)
    path = skia.Path()
    path.moveTo(x + s * 0.1, y - s * 0.5)
    path.lineTo(x + s * 0.1, y + s * 0.15)
    path.arcTo(skia.Rect(x - s * 0.35, y - s * 0.1, x + s * 0.1, y + s * 0.4), 0, 180, False)
    path.lineTo(x - s * 0.22, y + s * 0.02)
    c.drawPath(path, p)
    c.drawCircle(x + s * 0.1, y - s * 0.55, s * 0.08, p)


def step_card(c, t, t0, y, num, title, sub, viz):
    k = prog(t, t0 - 0.06, 0.45)
    if k <= 0:
        return
    a = min(1, k * 2.5)
    x = 110 - 60 * (1 - eob(k))
    c.save()
    c.translate(x, y)
    r = skia.RRect.MakeRectXY(skia.Rect(0, 0, 900, 150), 26, 26)
    sh = skia.Paint(AntiAlias=True, Color4f=col((0, 0, 0), 0.5 * a))
    sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 16))
    c.drawRRect(r, sh)
    c.drawRRect(r, skia.Paint(AntiAlias=True, Color4f=col((30, 27, 46), 0.96 * a)))
    hl = 1 - prog(t, t0 + 0.4, 0.6)
    c.drawRRect(r, skia.Paint(AntiAlias=True, Color4f=col(YEL, (0.25 + 0.6 * hl) * a), Style=skia.Paint.kStroke_Style,
                               StrokeWidth=2.5))
    c.drawCircle(75, 75, 42, skia.Paint(AntiAlias=True, Color4f=col(YEL, a)))
    draw_text(c, num, 75, 92, font("SpaceMono-Bold", 40), INK, a, "c")
    draw_text(c, title, 145, 72, font("Montserrat-Black", 50), WHITE, a)
    draw_text(c, sub, 147, 115, font("SpaceGrotesk-Bold", 27), (175, 170, 205), a)
    viz(c, t - t0, a)
    c.restore()


def viz_hook(c, dt, a):
    cx, cy, r = 810, 75, 46
    k = eo(clamp(dt / 1.0))
    c.drawCircle(cx, cy, r, skia.Paint(AntiAlias=True, Color4f=col(WHITE, 0.12 * a), Style=skia.Paint.kStroke_Style, StrokeWidth=9))
    arc = skia.Path()
    arc.addArc(skia.Rect(cx - r, cy - r, cx + r, cy + r), -90, 360 * k)
    c.drawPath(arc, skia.Paint(AntiAlias=True, Color4f=col(YEL, a), Style=skia.Paint.kStroke_Style, StrokeWidth=9,
                               StrokeCap=skia.Paint.kRound_Cap))
    draw_text(c, f"0:0{int(round(3 * k))}", cx, cy + 12, font("SpaceMono-Bold", 30), WHITE, a, "c")
    icon_hook(c, 690, 75, 60, a)


def viz_ret(c, dt, a):
    x0, y0, w, h = 650, 30, 230, 92
    k = eo(clamp(dt / 1.1))
    pts = [(0, 0.0), (0.12, 0.25), (0.25, 0.33), (0.45, 0.36), (0.65, 0.4), (0.85, 0.42), (1.0, 0.44)]
    path = skia.Path()
    fill = skia.Path()
    fill.moveTo(x0, y0 + h)
    n = 60
    for i in range(n + 1):
        u = i / n * k
        v = np.interp(u, [p[0] for p in pts], [p[1] for p in pts])
        X, Y = x0 + u * w, y0 + v * h
        (path.moveTo if i == 0 else path.lineTo)(X, Y)
        fill.lineTo(X, Y)
    fill.lineTo(x0 + k * w, y0 + h)
    fill.close()
    c.drawPath(fill, skia.Paint(AntiAlias=True, Color4f=col(YEL, 0.18 * a)))
    c.drawPath(path, skia.Paint(AntiAlias=True, Color4f=col(YEL, a), Style=skia.Paint.kStroke_Style, StrokeWidth=5,
                                StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join))
    draw_text(c, f"{int(78 * k)}%", x0 + w, y0 + 22, font("SpaceMono-Bold", 28), WHITE, a * clamp(k * 2), "r")


def viz_share(c, dt, a):
    k = eo(clamp(dt / 1.2))
    val = 12.4 * k
    draw_text(c, f"{val:0.1f}K", 880, 92, font("SpaceMono-Bold", 44), WHITE, a, "r")
    sc = 1 + 0.25 * math.exp(-dt * 5) * math.sin(dt * 22) if dt > 0 else 1
    c.save()
    c.translate(675, 75)
    c.scale(sc, sc)
    icon_share(c, 0, 0, 46, skia.Paint(AntiAlias=True, Color4f=col(YEL, a)))
    c.restore()


def frame_section(t, base):
    k = frame_k(t)
    if k <= 0:
        return None
    arr, s = rgba_surface((studio_bg()).astype(np.uint8))
    c = s.getCanvas()
    dst = skia.Rect(lerp(0, CARD.left(), k), lerp(0, CARD.top(), k), lerp(W, CARD.right(), k), lerp(H, CARD.bottom(), k))
    src = skia.Rect(lerp(0, CROP[0], k), lerp(0, CROP[1], k), lerp(W, CROP[2], k), lerp(H, CROP[3], k))
    rad = 34 * k
    rr = skia.RRect.MakeRectXY(dst, rad, rad)
    sh = skia.Paint(AntiAlias=True, Color4f=col((0, 0, 0), 0.6 * k))
    sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 30))
    c.drawRRect(rr.makeOffset(0, 18) if hasattr(rr, "makeOffset") else rr, sh)
    c.save()
    c.clipRRect(rr, True)
    c.drawImageRect(sk_image(base), src, dst, SAMP)
    # reel UI
    ui = clamp((k - 0.85) / 0.15)
    if ui > 0:
        pr = skia.Paint(AntiAlias=True, Color4f=col(WHITE, 0.35 * ui))
        c.drawRect(skia.Rect(dst.left() + 24, dst.top() + 22, dst.right() - 24, dst.top() + 27), pr)
        pp = (t - B["frame"]) / (B["full"] - B["frame"])
        c.drawRect(skia.Rect(dst.left() + 24, dst.top() + 22, dst.left() + 24 + (dst.width() - 48) * clamp(pp), dst.top() + 27),
                   skia.Paint(AntiAlias=True, Color4f=col(WHITE, ui)))
        grad = skia.Paint(Shader=skia.GradientShader.MakeLinear(
            [skia.Point(0, dst.bottom() - 260), skia.Point(0, dst.bottom())],
            [skia.Color4f(0, 0, 0, 0).toColor(), skia.Color4f(0, 0, 0, 0.55 * ui).toColor()]))
        c.drawRect(skia.Rect(dst.left(), dst.bottom() - 260, dst.right(), dst.bottom()), grad)
        ix = dst.right() - 52
        fp = skia.Paint(AntiAlias=True, Color4f=col(WHITE, ui))
        fs = font("SpaceGrotesk-Bold", 22)
        pulse_l = 1 + 0.3 * math.exp(-max(0, t - B["ret"]) * 6) * (t > B["ret"])
        c.save(); c.translate(ix, dst.bottom() - 330); c.scale(pulse_l, pulse_l)
        icon_heart(c, 0, 0, 40, skia.Paint(AntiAlias=True, Color4f=col((255, 70, 90) if t > B["ret"] else WHITE, ui)))
        c.restore()
        draw_text(c, "98.2K" if t > B["ret"] else "1.2K", ix, dst.bottom() - 285, fs, WHITE, ui, "c")
        icon_bubble(c, ix, dst.bottom() - 225, 40, fp)
        draw_text(c, "2,041", ix, dst.bottom() - 182, fs, WHITE, ui, "c")
        ps = 1 + 0.35 * math.exp(-max(0, t - B["share"]) * 5) * (t > B["share"])
        c.save(); c.translate(ix, dst.bottom() - 125); c.scale(ps, ps)
        icon_share(c, 0, 0, 36, skia.Paint(AntiAlias=True, Color4f=col(YEL if t > B["share"] else WHITE, ui)))
        c.restore()
        shares = 12.4 * eo(prog(t, B["share"], 1.2))
        draw_text(c, f"{shares:0.1f}K" if t > B["share"] else "310", ix, dst.bottom() - 82, fs, WHITE, ui, "c")
        draw_text(c, "@you", dst.left() + 28, dst.bottom() - 70, font("Montserrat-Black", 30), WHITE, ui)
        draw_text(c, "how I edit with AI  ·  original audio", dst.left() + 28, dst.bottom() - 34,
                  font("SpaceGrotesk-Bold", 20), (230, 230, 235), ui)
    c.restore()
    c.drawRRect(rr, skia.Paint(AntiAlias=True, Color4f=col(WHITE, 0.9 * k), Style=skia.Paint.kStroke_Style, StrokeWidth=4))
    # left panel
    pa = 1 - eio(prog(t, B["full"] - 0.1, 0.45))
    if pa > 0:
        c.save()
        c.translate(-300 * (1 - pa), 0)
        kc = prog(t, B["left"] - 0.1, 0.4)
        if kc > 0:
            chip(c, 128, 170, "BREAKDOWN", VIO, WHITE, 30, pa * min(1, kc * 3), 0.7 + 0.3 * eob(kc))
        ka = prog(t, B["anat"] - 0.08, 0.4)
        if ka > 0:
            draw_text(c, "ANATOMY OF A", 110, 262 + 30 * (1 - eob(ka)), font("Montserrat-Black", 66), WHITE, pa * min(1, ka * 2.5))
        kv = prog(t, B["viral"] - 0.08, 0.45)
        if kv > 0:
            c.save()
            c.translate(110, 382)
            c.scale(lerp(0.6, 1, eob(kv)), lerp(0.6, 1, eob(kv)))
            draw_text(c, "VIRAL REEL", 0, 0, font("Montserrat-Black", 116), YEL, pa * min(1, kv * 2.5), shadow=10)
            c.restore()
        c.saveLayerAlpha(None, int(255 * pa))
        step_card(c, t, B["hook"], 440, "01", "THE HOOK", "The first 3 seconds stop the scroll", viz_hook)
        step_card(c, t, B["ret"], 612, "02", "RETENTION", "Keep them watching to the end", viz_ret)
        step_card(c, t, B["share"], 784, "03", "THE SHARE", "Give them a reason to send it", viz_share)
        c.restore()
        c.restore()
    return arr[..., :3].astype(np.float32), pa


# ------------------------------------------------------------------ 6. best videos floating behind me, in 3D
SCREENS = [  # clip, centre x, centre y, height, yaw(deg), pitch, delay
    ("clip_promo", 330, 520, 600, 30, -4, 0.00),
    ("clip_evo", 960, 170, 300, 0, -14, 0.14),
    ("clip_expl", 1590, 520, 600, -30, -4, 0.28),
    ("clip_promo2", 1335, 180, 290, -18, -10, 0.42),
    ("clip_promo", 585, 180, 290, 18, -10, 0.56),
]


def screen_quad(cx, cy, w, h, yaw, pitch, zoff=0.0):
    f = 1800.0
    yaw, pitch = math.radians(yaw), math.radians(pitch)
    pts = []
    for x, y in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        X = x * math.cos(yaw)
        Z = -x * math.sin(yaw) + zoff
        Y = y * math.cos(pitch) - Z * math.sin(pitch)
        Z2 = y * math.sin(pitch) + Z * math.cos(pitch)
        k = f / (f + Z2)
        pts.append(skia.Point(cx + X * k, cy + Y * k))
    return pts


def screens_section(t, base, al):
    t0 = B["floating"] - 0.25
    t_out = B["screens_out"]
    if not (t0 <= t <= t_out + 0.45):
        return None
    dim = eio(prog(t, t0, 0.6)) * (1 - eio(prog(t, t_out, 0.4)))
    out = base.astype(np.float32)
    # dim + cool the room so the screens glow
    vign = studio_bg()
    out = out * (1 - 0.55 * dim) + vign * 0.55 * dim
    arr, s = new_layer()
    c = s.getCanvas()
    for i, (clip, cx, cy, hgt, yaw, pitch, dl) in enumerate(SCREENS):
        k = prog(t, t0 + 0.15 + dl, 0.7)
        ko = eio(prog(t, t_out + 0.04 * i, 0.4))
        if k <= 0 or ko >= 1:
            continue
        frames = D(clip)
        fi = int((t - t0) * FPS) % len(frames)
        fr = np.ascontiguousarray(frames[fi])
        fh, fw = fr.shape[:2]
        w = hgt * fw / fh
        e = eob(k)
        bob = 10 * math.sin(1.6 * t + i * 1.3)
        wob = 4 * math.sin(1.1 * t + i) + 18 * math.exp(-max(0, t - B["d3b"]) * 3) * math.sin(max(0, t - B["d3b"]) * 12) * (t > B["d3b"])
        zoff = lerp(900, 0, eo(k)) + 700 * ko
        pts = screen_quad(cx, cy + bob - 40 * ko, w * lerp(0.6, 1, e), hgt * lerp(0.6, 1, e), yaw + wob, pitch, zoff)
        a = min(1, k * 2.5) * (1 - ko)
        glow = skia.Paint(AntiAlias=True, Color4f=col(tuple(int(v) for v in fr.reshape(-1, 3).mean(0) * 1.4 + 40), 0.8 * a))
        glow.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 38))
        gp = skia.Path()
        gp.addPoly(pts, True)
        c.drawPath(gp, glow)
        m = skia.Matrix()
        m.setPolyToPoly([skia.Point(0, 0), skia.Point(fw, 0), skia.Point(fw, fh), skia.Point(0, fh)], pts)
        c.save()
        c.concat(m)
        rr = skia.RRect.MakeRectXY(skia.Rect(0, 0, fw, fh), fw * 0.06, fw * 0.06)
        c.clipRRect(rr, True)
        c.drawImage(sk_image(fr), 0, 0, SAMP, skia.Paint(Alphaf=a))
        c.restore()
        c.save()
        c.concat(m)
        c.drawRRect(rr, skia.Paint(AntiAlias=True, Color4f=col(WHITE, 0.85 * a), Style=skia.Paint.kStroke_Style,
                                   StrokeWidth=max(2.0, fw * 0.012)))
        c.restore()
    out = over(out, arr, 1 - al)
    return out


# ------------------------------------------------------------------ 7. cinematic documentary
def cine_k(t):
    return eio(prog(t, B["cine"], 0.7)) * (1 - eio(prog(t, B["crazy"] - 0.05, 0.3)))


@lru_cache(None)
def vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2)
    return np.clip(1 - 0.75 * r ** 2.2, 0.15, 1)[..., None]


@lru_cache(None)
def beam():
    arr, s = new_layer()
    c = s.getCanvas()
    p = skia.Paint(AntiAlias=True, Color4f=col((255, 214, 170), 0.5))
    p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 60))
    path = skia.Path()
    path.addPoly([skia.Point(80, -50), skia.Point(420, -50), skia.Point(1150, H), skia.Point(620, H)], True)
    c.drawPath(path, p)
    return arr[..., 3:4].astype(np.float32) / 255


def cinematic(t, img, al):
    k = cine_k(t)
    if k <= 0:
        return img
    light = eio(prog(t, B["dramatic"], 0.9)) * (1 - eio(prog(t, B["crazy"] - 0.05, 0.3)))
    a3 = al[..., None]
    if light > 0:
        xg = np.linspace(1.45, 0.45, W, dtype=np.float32)[None, :, None]
        key = np.array([1.06, 0.98, 0.88], np.float32) * xg
        person = img * lerp(1, 1, 0) * (1 + (key - 1) * light)
        bg = img * (1 - 0.72 * light) * np.array([0.88, 0.97, 1.15], np.float32)
        bg = bg + beam() * np.array([255, 210, 160], np.float32) * 0.28 * light
        rim = np.clip(al - cv2.GaussianBlur(np.roll(al, 7, axis=1), (0, 0), 3), 0, 1)[..., None]
        img = person * a3 + bg * (1 - a3) + rim * np.array([255, 190, 130], np.float32) * 0.9 * light
    # teal / orange split tone, contrast, desat
    lum = img.mean(2, keepdims=True) / 255
    tone = (1 - lum) * np.array([-14, 4, 16], np.float32) + lum * np.array([16, 6, -14], np.float32)
    g = satur(img, 0.82) + tone
    g = (g - 128) * 1.12 + 128
    g = g * lerp(1, 1, 0) * (vignette() ** 1.0)
    img = img * (1 - k) + g * k
    rng = np.random.default_rng(int(t * FPS))
    grain = cv2.resize(rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32), (W, H))[..., None]
    img = img + grain * 7 * k
    return img


def cine_overlay(c, t):
    k = cine_k(t)
    if k <= 0:
        return
    bar = 138 * k
    p = skia.Paint(Color4f=col((0, 0, 0), 1))
    c.drawRect(skia.Rect(0, 0, W, bar), p)
    c.drawRect(skia.Rect(0, H - bar, W, H), p)
    km = prog(t, B["movie"] - 0.05, 0.9)
    out = 1 - prog(t, B["crazy"] - 0.1, 0.25)
    if km > 0:
        band = skia.Paint(Shader=skia.GradientShader.MakeLinear(
            [skia.Point(0, 540), skia.Point(0, H - bar)],
            [skia.Color4f(0, 0, 0, 0).toColor(), skia.Color4f(0, 0, 0, 0.72 * eo(km) * out).toColor()]))
        c.drawRect(skia.Rect(0, 540, W, H - bar), band)
    if km > 0:
        draw_text(c, "A  FILM  ABOUT  THE  ONE  WHO", W / 2, 640, font("Jost-Light", 30), (235, 225, 210),
                  eo(km) * out, "c", track=0.35)
    kt = prog(t, B["movie"] + 0.35, 1.3)
    if kt > 0:
        tr = lerp(0.08, 0.22, eo(kt))
        draw_text(c, "STOPPED EDITING", W / 2, 790, font("Cormorant-Light", 132), (255, 248, 236), eo(kt) * out, "c",
                  track=tr, shadow=12)
    ks = prog(t, B["movie"] + 1.0, 0.9)
    if ks > 0:
        draw_text(c, "A  DOCUMENTARY", W / 2, 850, font("Jost-Light", 26), (220, 205, 185), eo(ks) * out * 0.9, "c", track=0.5)


# ------------------------------------------------------------------ 8. recap grid
RECAP = [("logo", lambda: B["d3"] + 0.7), ("crack", lambda: B["impact"] + 0.3), ("layers", lambda: B["l_text"] + 0.35),
         ("room", lambda: B["rm"] + 1.3), ("hook", lambda: B["over"] + 0.3), ("anatomy", lambda: B["share"] + 0.6),
         ("screens", lambda: B["perfect"] + 0.1), ("cine", lambda: B["movie"] + 1.6)]


@lru_cache(None)
def recap_tile(i):
    img = render(RECAP[i][1](), recap=False)
    return sk_image(cv2.resize(img, (W // 3, H // 3), interpolation=cv2.INTER_AREA))


def recap_k(t):
    return eio(prog(t, B["all_"] - 0.05, 0.55)) * (1 - eio(prog(t, B["ai"] + 0.05, 0.5)))


def recap_section(t, img):
    k = recap_k(t)
    if k <= 0:
        return img
    arr, s = rgba_surface(studio_bg().astype(np.uint8))
    c = s.getCanvas()
    g = 16
    tw, th = (W - 4 * g) / 3, (H - 4 * g) / 3
    slots = [(0, 0), (1, 0), (2, 0), (0, 1), (2, 1), (0, 2), (1, 2), (2, 2)]
    for i, (cx, cy) in enumerate(slots):
        kt = prog(t, B["all_"] + 0.05 + 0.055 * i, 0.35) * (1 - eio(prog(t, B["ai"] + 0.05, 0.4)))
        if kt <= 0:
            continue
        r = skia.Rect.MakeXYWH(g + cx * (tw + g), g + cy * (th + g), tw, th)
        sc = lerp(0.6, 1, eob(kt))
        c.save()
        c.translate(r.centerX(), r.centerY())
        c.scale(sc, sc)
        c.translate(-r.centerX(), -r.centerY())
        rr = skia.RRect.MakeRectXY(r, 18, 18)
        c.save()
        c.clipRRect(rr, True)
        c.drawImageRect(recap_tile(i), r, SAMP, skia.Paint(Alphaf=min(1, kt * 2)))
        c.restore()
        c.drawRRect(rr, skia.Paint(AntiAlias=True, Color4f=col(WHITE, 0.35 * min(1, kt * 2)), Style=skia.Paint.kStroke_Style,
                                   StrokeWidth=2))
        c.restore()
    center = skia.Rect.MakeXYWH(g + tw + g, g + th + g, tw, th)
    dst = skia.Rect(lerp(0, center.left(), k), lerp(0, center.top(), k), lerp(W, center.right(), k), lerp(H, center.bottom(), k))
    rr = skia.RRect.MakeRectXY(dst, 18 * k, 18 * k)
    c.save()
    c.clipRRect(rr, True)
    c.drawImageRect(sk_image(np.clip(img, 0, 255).astype(np.uint8)), dst, SAMP)
    c.restore()
    c.drawRRect(rr, skia.Paint(AntiAlias=True, Color4f=col(YEL, k), Style=skia.Paint.kStroke_Style, StrokeWidth=5))
    return arr[..., :3].astype(np.float32)


def recap_overlay(c, t):
    ke = prog(t, B["edited"] - 0.05, 0.4)
    ko = eio(prog(t, B["ai"] + 0.45, 0.35))
    if ke <= 0 or ko >= 1:
        return
    a = min(1, ke * 3) * (1 - ko)
    sc = lerp(1.6, 1, eob(ke)) * (1 + 0.1 * ko)
    c.save()
    c.translate(W / 2, H - 120)
    c.scale(sc, sc)
    f = font("Montserrat-Black", 150)
    w1 = text_w("EDITED WITH ", f)
    w2 = text_w("AI", f)
    x0 = -(w1 + w2) / 2
    draw_text(c, "EDITED WITH ", x0, 0, f, WHITE, a, stroke=INK, sw=18, shadow=20)
    kai = prog(t, B["ai"] - 0.05, 0.25)
    c.save()
    c.translate(x0 + w1 + w2 / 2, -50)
    s2 = 1 + 0.25 * math.exp(-max(0, t - B["ai"]) * 6) * (t > B["ai"])
    c.scale(s2, s2)
    draw_text(c, "AI", -w2 / 2, 50, f, YEL if kai > 0 else WHITE, a, stroke=INK, sw=18)
    c.restore()
    c.restore()


# ------------------------------------------------------------------ 9. CTA comment box
def cta_overlay(c, t):
    k = prog(t, B["comment"] - 0.1, 0.5)
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
    av = skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeLinear(
        [skia.Point(x + 20, y + 20), skia.Point(x + 100, y + 100)],
        [col(VIO, a).toColor(), col(ORG, a).toColor()]))
    c.drawCircle(x + 62, y + h / 2, 38, av)
    draw_text(c, "Y", x + 62, y + h / 2 + 15, font("Montserrat-Black", 40), WHITE, a, "c")
    typed = int(clamp((t - B["edit"]) / 0.09 + 1, 0, 4)) if t >= B["edit"] else 0
    ft = font("Montserrat-Black", 52)
    if typed == 0:
        draw_text(c, "Add a comment…", x + 125, y + h / 2 + 17, font("SpaceGrotesk-Bold", 40), (150, 150, 160), a)
        tx = x + 125
    else:
        txt = "EDIT"[:typed]
        tx = x + 125 + draw_text(c, txt, x + 125, y + h / 2 + 19, ft, INK, a)
    if int(t * 2.2) % 2 == 0 or typed == 0:
        c.drawRect(skia.Rect.MakeXYWH(tx + 6, y + 30, 4, h - 60), skia.Paint(Color4f=col((56, 151, 240), a)))
    kh = prog(t, B["how"] - 0.1, 0.3)
    bs = 1 + 0.25 * math.sin(math.pi * clamp(kh))
    c.save()
    c.translate(x + w - 62, y + h / 2)
    c.scale(bs, bs)
    c.drawCircle(0, 0, 40, skia.Paint(AntiAlias=True, Color4f=col((56, 151, 240) if typed else (200, 200, 210), a)))
    path = skia.Path()
    path.addPoly([skia.Point(-14, -16), skia.Point(18, 0), skia.Point(-14, 16), skia.Point(-7, 0)], True)
    c.drawPath(path, skia.Paint(AntiAlias=True, Color4f=col(WHITE, a)))
    c.restore()
    if kh > 0:
        kk = prog(t, B["how"] + 0.1, 0.5)
        for i in range(8):
            ang = i * math.pi / 4 + 0.3
            r0 = 50 + 60 * eo(kk)
            c.drawCircle(x + w - 62 + r0 * math.cos(ang), y + h / 2 + r0 * math.sin(ang), 6 * (1 - kk),
                         skia.Paint(AntiAlias=True, Color4f=col(YEL, a * (1 - kk))))


# ------------------------------------------------------------------ captions
def caption_groups():
    groups, cur = [], []
    for i, w in enumerate(WORDS):
        cur.append(w)
        nxt = WORDS[i + 1] if i + 1 < len(WORDS) else None
        brk = w["w"][-1] in ".,!?" or len(cur) >= 3 or nxt is None or nxt["s"] - w["e"] > 0.35
        if brk:
            groups.append(cur)
            cur = []
    out = []
    for gi, g in enumerate(groups):
        t0 = g[0]["s"] - 0.04
        t1 = g[-1]["e"] + 0.25
        if gi + 1 < len(groups):
            t1 = min(t1, groups[gi + 1][0]["s"] - 0.04) if groups[gi + 1][0]["s"] - g[-1]["e"] < 0.6 else t1
        out.append((t0, t1, g))
    return out


GROUPS = caption_groups()


def caption_mode(t):
    if t < B["watch"] - 0.05:
        return None
    if recap_k(t) > 0.02 or prog(t, B["edited"] - 0.1, 0.01) * (1 - prog(t, B["ai"] + 0.8, 0.01)) > 0:
        return None
    if cine_k(t) > 0.5:
        return "cine"
    if frame_k(t) > 0.5:
        return "panel"
    if t > B["comment"] - 0.1:
        return "cta"
    return "main"


def draw_captions(c, t):
    mode = caption_mode(t)
    if mode is None:
        return
    for t0, t1, g in GROUPS:
        if not (t0 <= t < t1):
            continue
        if mode == "cine":
            txt = " ".join(w["w"] for w in g)
            a = min(prog(t, t0, 0.12), 1 - prog(t, t1 - 0.1, 0.1))
            draw_text(c, txt, W / 2, H - 52, font("Jost-Light", 44), (240, 235, 225), a, "c", track=0.04)
            return
        size = {"main": 66, "panel": 50, "cta": 62}[mode]
        cx = {"main": W / 2, "panel": 575, "cta": W / 2}[mode]
        y = {"main": H - 92, "panel": H - 62, "cta": H - 238}[mode]
        f = font("Montserrat-Black", size)
        words = [w["w"].upper() for w in g]
        gap = size * 0.55
        widths = [text_w(x, f) for x in words]
        total = sum(widths) + gap * (len(words) - 1)
        kin = prog(t, t0, 0.14)
        sc = lerp(0.86, 1, eob(kin))
        c.save()
        c.translate(cx, y)
        c.scale(sc, sc)
        x = -total / 2
        for w, txt, wd in zip(g, words, widths):
            active = w["s"] - 0.03 <= t < w["e"] + 0.05 or (t >= w["e"] and w is g[-1])
            said = t >= w["s"] - 0.03
            colr = YEL if (active and t < w["e"] + 0.05) else WHITE
            a = 1.0 if said else 0.55
            ws = 1.04 if colr == YEL else 1.0
            c.save()
            c.translate(x + wd / 2, 0)
            c.scale(ws, ws)
            draw_text(c, txt, -wd / 2, 0, f, colr, a, stroke=INK, sw=size * 0.2, shadow=8)
            c.restore()
            x += wd + gap
        c.restore()
        return


# ------------------------------------------------------------------ frame
def render(t, recap=True):
    fi, si, s = src_frame(t)
    z, cx, cy, sx, sy = camera(t, si)
    M = affine(z, cx, cy, sx, sy)
    base, al, fi = base_layers(t, M)

    img = None
    ls = layers_section(t, base, al, M)
    if ls is not None:
        img = ls
    fs = frame_section(t, base)
    if fs is not None:
        img = fs[0]
    sc = screens_section(t, base, al)
    if sc is not None:
        img = sc
    if img is None:
        img = base.astype(np.float32)
    hl = hook_layer(t)
    if hl is not None:
        img = over(img, hl, 1 - al)
    img = cinematic(t, img, al)
    if recap:
        img = recap_section(t, img)

    arr, surf = rgba_surface(np.clip(img, 0, 255).astype(np.uint8))
    c = surf.getCanvas()
    st = logo_state(t, M, fi)
    if st is not None:
        palm_shadow(c, st, M, fi)
        if st["kl"] > 0:
            for gh in range(4, 0, -1):
                t_g = t - gh * 0.018
                sg = logo_state(t_g, M, fi)
                if sg is not None and sg["kl"] > 0:
                    draw_logo(c, sg["x"], sg["y"], sg["size"], sg["yaw"], sg["pitch"], sg["depth"], 0.18 * (5 - gh) / 4)
        draw_logo(c, st["x"], st["y"], st["size"], st["yaw"], st["pitch"], st["depth"], st["a"], st["glow"])
    draw_crack(c, t)
    cine_overlay(c, t)
    if recap:
        recap_overlay(c, t)
    cta_overlay(c, t)
    draw_captions(c, t)
    out = arr[..., :3]
    end_fade = prog(t, DUR - 0.4, 0.4)
    if end_fade > 0:
        out = (out.astype(np.float32) * (1 - end_fade)).astype(np.uint8)
    return np.ascontiguousarray(out)


# ------------------------------------------------------------------ drivers
def render_chunk(args):
    i0, i1, path = args
    p = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "15",
                          "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for i in range(i0, i1):
        p.stdin.write(render(i / FPS).tobytes())
    p.stdin.close()
    p.wait()
    return path


def main():
    os.makedirs(OUT, exist_ok=True)
    if "--stills" in sys.argv:
        d = os.path.join(OUT, "stills")
        os.makedirs(d, exist_ok=True)
        keys = sys.argv[sys.argv.index("--stills") + 1:] or list(B.keys())
        for k in keys:
            for off in (0.0, 0.4):
                t = B[k] + off
                cv2.imwrite(os.path.join(d, f"{t:06.2f}_{k}.jpg"), cv2.cvtColor(render(t), cv2.COLOR_RGB2BGR),
                            [cv2.IMWRITE_JPEG_QUALITY, 85])
        return
    n = NFRAMES
    workers = int(os.environ.get("WORKERS", "4"))
    k = 24
    bounds = np.linspace(0, n, k + 1).astype(int)
    tmp = os.path.join(OUT, "chunks")
    os.makedirs(tmp, exist_ok=True)
    jobs = [(int(bounds[i]), int(bounds[i + 1]), os.path.join(tmp, f"c{i:03d}.mp4")) for i in range(k)]
    with Pool(workers) as pool:
        for pth in pool.imap_unordered(render_chunk, jobs):
            print("done", os.path.basename(pth), flush=True)
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join(f"file '{j[2]}'\n" for j in jobs))
    final = os.path.join(OUT, "final.mp4")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", os.path.join(OUT, "mix.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest",
                    "-movflags", "+faststart", final], check=True)
    print("wrote", final)


if __name__ == "__main__":
    main()
