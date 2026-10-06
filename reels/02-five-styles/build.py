"""Reel 02: "Same prompt. Five completely different videos."
One scene (a paper boat sails into the sunrise), five renderers: clay, crayon, paper cut, pixel art, neon.

    python3 build.py sheet | stills 1 5 9 | draft | render | sound | all
"""
import math
import sys
from pathlib import Path

import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
sys.path.insert(0, str(HERE))
import clay as C  # noqa: E402
from kit import (W, H, INK, LIME, WHITE, Captions, Film, clamp, col, e_back, e_io, e_out, endcard, fill,  # noqa: E402
                 hrand, lerp, measure, mixc, prog, prompt_bar, rrect, stroke, text)
from script import LINES, VOICE  # noqa: E402
from voice import Script, narrate  # noqa: E402

vo = narrate(LINES, HERE / "work", VOICE)
SEG = 3.3
S = Script(vo, [("hook", 0.2), ("prompt", 0.3), ("clay", "@", 7.0), ("crayon", "@", 7.0 + SEG),
                ("paper", "@", 7.0 + 2 * SEG), ("pixel", "@", 7.0 + 3 * SEG), ("neon", "@", 7.0 + 4 * SEG),
                ("word", "@", 7.0 + 5 * SEG + 0.25), ("nos", 0.3), ("cta", 0.35)])
END_T = S.end("cta") + 0.45
DUR = END_T + 3.0
FPS = 30

STYLES = ["clay", "crayon", "paper", "pixel", "neon"]
LABEL = {"clay": "Claymation", "crayon": "Crayon", "paper": "Paper cut", "pixel": "Pixel art", "neon": "Neon"}
SEG_T = {s: S.t(s) - 0.25 for s in STYLES}            # each style's shot starts just before its name
STYLES_END = SEG_T["neon"] + SEG
PROMPT = "a paper boat sails into the sunrise"
P_T0, P_T1 = S.find("prompt", "a") - 0.05, S.end("prompt") - 0.1
HOOK_END = S.t("prompt") - 0.15
COLLAGE_T = S.t("word") - 0.2

HORIZON = 1120


# ---------------------------------------------------------------- shared story
def story(u, tt):
    return dict(sun_y=lerp(1230, 800, e_out(u)), boat_x=lerp(300, 760, e_io(u)), bob=9 * math.sin(tt * 2.4),
                tilt=4.5 * math.sin(tt * 1.7 + 0.6), tt=tt)


def sea_y(x, tt, row=0):
    return 1265 + row * 120 + 12 * math.sin(x * 0.011 + tt * 2.0 + row * 1.7) + 6 * math.sin(x * 0.027 - tt * 1.3)


def boat_parts(st, s=1.0):
    """hull, sail, left flap, right flap as point lists in canvas space."""
    x, y = st["boat_x"], sea_y(st["boat_x"], st["tt"]) - 16 + st["bob"]
    a = math.radians(st["tilt"])
    ca, sa = math.cos(a), math.sin(a)

    def tr(pts):
        return [(x + s * (px * ca - py * sa), y + s * (px * sa + py * ca)) for px, py in pts]
    hull = tr([(-165, -30), (165, -30), (112, 42), (-112, 42)])
    sail = tr([(-78, -30), (0, -190), (78, -30)])
    lf = tr([(-165, -30), (-108, -92), (-62, -30)])
    rf = tr([(165, -30), (108, -92), (62, -30)])
    return hull, sail, lf, rf


def poly(pts):
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    p.close()
    return p


CLOUDS = [(230, 520, 1.0), (820, 400, 0.8), (640, 650, 0.6)]


# ---------------------------------------------------------------- 1. clay
def r_clay(c, st, t):
    f = int(t * 12)
    tt = math.floor(st["tt"] * 12) / 12
    st = story_q(st, tt)
    sh = skia.GradientShader.MakeLinear([skia.Point(0, 300), skia.Point(0, HORIZON)],
                                        [C.col("#7FC6F0"), C.col("#FFD2AE"), C.col("#FF9D7A")], [0, 0.65, 1])
    c.drawPaint(skia.Paint(Shader=sh))
    c.drawPaint(C.tex_paint(5, 0.22, 1.5))
    C.clay(c, C.blob(540, st["sun_y"], 150, 148, 7, 0.03, 1.2, f), "#FFC53A", 7, cast=False, gloss=0.3)
    for i, (x, y, s) in enumerate(CLOUDS):
        x = x + tt * 12
        parts = [C.blob(x + dx * s, y + dy * s, r * s, r * 0.8 * s, 30 + i * 5 + j, 0.05, 1, f, n=22)
                 for j, (dx, dy, r) in enumerate(((-70, 10, 60), (0, -16, 78), (72, 8, 56)))]
        C.clay(c, C.union(parts), WHITE, 30 + i, cast_alpha=0.12, tex=0.3)
    for row, colr in enumerate(("#3E8FD6", "#2F7BC4", "#2569AE", "#1D5895", "#174A80")):
        y0 = HORIZON + row * 160 - 10
        pts = [(x, (y0 if row == 0 else sea_y(x, tt, row - 1) + 40) + 8 * math.sin(x * 0.02 + row + tt * 2))
               for x in range(-40, W + 60, 40)]
        pts += [(W + 60, H + 50), (-40, H + 50)]
        C.clay(c, C.smooth_path(pts, True), colr, 50 + row, cast=row > 0, cast_alpha=0.25, tex=0.45, gloss=0.08)
        if row == 0:
            hull, sail, lf, rf = boat_parts(st)
            for k, (pp, cc) in enumerate(((sail, "#F7F3EA"), (lf, "#E9E3D5"), (rf, "#E9E3D5"), (hull, "#FFFFFF"))):
                C.clay(c, C.lumpy_poly(pp, 60 + k, 1.6, boil=0.9, f=f), cc, 60 + k, tex=0.4)


def story_q(st, tt):
    return dict(st, tt=tt, bob=9 * math.sin(tt * 2.4), tilt=4.5 * math.sin(tt * 1.7 + 0.6),
                boat_x=st["boat_x"], sun_y=st["sun_y"])


# ---------------------------------------------------------------- 2. crayon
def _jit(pts, amp, seed):
    return [(x + amp * (hrand(seed, i, 1) - 0.5), y + amp * (hrand(seed, i, 2) - 0.5)) for i, (x, y) in enumerate(pts)]


def _resample(pts, closed=True, ds=12):
    out = []
    n = len(pts)
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
        k = max(1, int(math.hypot(x1 - x0, y1 - y0) / ds))
        out += [(x0 + (x1 - x0) * j / k, y0 + (y1 - y0) * j / k) for j in range(k)]
    if closed:
        out.append(out[0])
    return out


def crayon_shape(c, path, outline_pts, colr, seed, f, angle=0.5, gap=11, w=9, alpha=0.8, line_c=None):
    b = path.computeTightBounds()
    c.save()
    c.clipPath(path, skia.ClipOp.kIntersect, True)
    cx, cy = b.centerX(), b.centerY()
    R = math.hypot(b.width(), b.height()) / 2 + 20
    ca, sa = math.cos(angle), math.sin(angle)
    p = stroke(colr, w, alpha)
    i = 0
    d = -R
    while d < R:
        pts = []
        for k in range(9):
            s = -R + 2 * R * k / 8
            jx = 3.5 * (hrand(seed, f, i, k) - 0.5)
            pts.append((cx + s * ca - (d + jx) * sa, cy + s * sa + (d + jx) * ca))
        pa = skia.Path()
        pa.moveTo(*pts[0])
        for q in pts[1:]:
            pa.lineTo(*q)
        c.drawPath(pa, p)
        d += gap * (0.8 + 0.4 * hrand(seed, f, i))
        i += 1
    c.restore()
    lc = line_c or mixc(colr, "#000000", 0.35)
    for pas in range(2):
        q = _jit(outline_pts, 5, seed * 7 + pas * 13 + f * 101)
        pa = skia.Path()
        pa.moveTo(*q[0])
        for pt in q[1:]:
            pa.lineTo(*pt)
        c.drawPath(pa, stroke(lc, 5 - pas * 1.5, 0.85))


def r_crayon(c, st, t):
    f = int(t * 8)                                       # crayon boils at 8 drawings/s
    c.drawPaint(fill("#FBF6EA"))
    sun = skia.Path()
    sun.addCircle(540, st["sun_y"], 140)
    sky = skia.Path()
    sky.addRect(skia.Rect.MakeLTRB(0, 250, W, HORIZON))
    crayon_shape(c, sky, [], "#9CD2F2", 1, f, angle=0.15, gap=16, w=10, alpha=0.45, line_c="#9CD2F2")
    pts = [(540 + 140 * math.cos(a / 30 * 2 * math.pi), st["sun_y"] + 140 * math.sin(a / 30 * 2 * math.pi))
           for a in range(31)]
    crayon_shape(c, sun, pts, "#FFC93A", 2, f, angle=0.9, gap=9, w=9, alpha=0.9, line_c="#F08A1C")
    for i in range(12):
        a = i * math.pi / 6 + st["tt"] * 0.3
        r0, r1 = 175, 225 + 15 * math.sin(i * 2 + f)
        q = _jit([(540 + r0 * math.cos(a), st["sun_y"] + r0 * math.sin(a)),
                  (540 + r1 * math.cos(a), st["sun_y"] + r1 * math.sin(a))], 6, f * 3 + i)
        if q[1][1] < HORIZON:
            c.drawLine(*q[0], *q[1], stroke("#F5A623", 8, 0.85))
    for i, (x, y, s) in enumerate(CLOUDS):
        x += st["tt"] * 12
        cp = skia.Path()
        for dx, dy, r in ((-70, 10, 60), (0, -16, 78), (72, 8, 56)):
            cp.addCircle(x + dx * s, y + dy * s, r * s)
        cp = skia.Op(cp, cp, skia.kUnion_PathOp) or cp
        outline = []
        crayon_shape(c, cp, outline, "#FFFFFF", 10 + i, f, gap=8, w=9, alpha=0.95, line_c="#8BB7D9")
        for dx, dy, r in ((-70, 10, 60), (0, -16, 78), (72, 8, 56)):
            pts = [(x + dx * s + r * s * math.cos(a * 0.25), y + dy * s + r * s * math.sin(a * 0.25)) for a in range(26)]
            q = _jit(pts, 4, f * 5 + i)
            pa = skia.Path()
            pa.moveTo(*q[0])
            for pt in q[1:]:
                pa.lineTo(*pt)
            c.drawPath(pa, stroke("#8BB7D9", 4, 0.7))
    for row, colr in enumerate(("#4A9BE0", "#3A84CC", "#2C6EB5", "#215B9C")):
        top = [(x, (HORIZON if row == 0 else sea_y(x, st["tt"], row - 1) + 40)) for x in range(-40, W + 80, 60)]
        pts = top + [(W + 60, H + 50), (-40, H + 50)]
        crayon_shape(c, poly(pts), _resample(top, False, 20), colr, 20 + row, f, angle=-0.25 + row * 0.2, gap=10,
                     w=10, alpha=0.75)
        if row == 0:
            hull, sail, lf, rf = boat_parts(st)
            for k, (pp, cc) in enumerate(((sail, "#FFFFFF"), (lf, "#F2EEE4"), (rf, "#F2EEE4"), (hull, "#FF6B5B"))):
                crayon_shape(c, poly(pp), _resample(pp), cc, 30 + k, f, angle=0.8, gap=9, w=8, alpha=0.95,
                             line_c="#3B3B48")
    c.drawPaint(C.tex_paint(77, 0.45, 0.7))


# ---------------------------------------------------------------- 3. paper cut
def paper_layer(c, path, colr, seed, depth=10, alpha=0.32):
    c.save()
    c.translate(0, depth * 0.6)
    c.drawPath(path, fill("#2A1A10", alpha, blur=depth))
    c.restore()
    c.drawPath(path, fill(colr))
    c.save()
    c.clipPath(path, skia.ClipOp.kIntersect, True)
    c.drawPaint(C.tex_paint(seed, 0.35, 0.5))
    c.restore()


def torn(pts, seed, amp=4, ds=8):
    dense = _resample(pts, True, ds)[:-1]
    return [(x + amp * (hrand(seed, i) - 0.5), y + amp * (hrand(seed, i, 9) - 0.5)) for i, (x, y) in enumerate(dense)]


def r_paper(c, st, t):
    tt = math.floor(st["tt"] * 12) / 12
    st = story_q(st, tt)
    c.drawPaint(fill("#FFE3C9"))
    for i, (r, colr) in enumerate(((620, "#FFD0B0"), (470, "#FFBE99"), (330, "#FFAA85"))):
        p = skia.Path()
        p.addCircle(540, st["sun_y"], r)
        paper_layer(c, p, colr, 90 + i, 14, 0.18)
    sp = poly(torn([(540 + 150 * math.cos(a / 40 * 2 * math.pi), st["sun_y"] + 150 * math.sin(a / 40 * 2 * math.pi))
                    for a in range(40)], 5, 3))
    paper_layer(c, sp, "#FFE15A", 95, 12)
    for i, (x, y, s) in enumerate(CLOUDS):
        x += tt * 12
        cp = skia.Path()
        for dx, dy, r in ((-70, 10, 60), (0, -16, 78), (72, 8, 56)):
            cp.addCircle(x + dx * s, y + dy * s, r * s)
        cp.addRect(skia.Rect.MakeLTRB(x - 130 * s, y + 10 * s, x + 128 * s, y + 70 * s))
        cp = skia.Op(cp, cp, skia.kUnion_PathOp) or cp
        paper_layer(c, cp, WHITE, 100 + i, 12, 0.22)
    for row, colr in enumerate(("#6BC5D9", "#3FA4C9", "#2A83B5", "#1E6698", "#164D78")):
        top = [(x, (HORIZON + 8 * math.sin(x * 0.01 + tt) if row == 0 else sea_y(x, tt, row - 1) + 40))
               for x in range(-40, W + 80, 30)]
        pts = top + [(W + 60, H + 50), (-40, H + 50)]
        paper_layer(c, poly(pts), colr, 110 + row, 16, 0.3)
        if row == 0:
            hull, sail, lf, rf = boat_parts(st)
            for k, (pp, cc) in enumerate(((sail, "#FFFFFF"), (lf, "#F1ECE2"), (rf, "#F1ECE2"), (hull, "#FF7B5C"))):
                paper_layer(c, poly(torn(pp, 120 + k, 2.5, 10)), cc, 120 + k, 10)
            # fold crease
            c.drawLine(*sail[1], *(((sail[0][0] + sail[2][0]) / 2, (sail[0][1] + sail[2][1]) / 2)),
                       stroke("#000000", 2, 0.12))


# ---------------------------------------------------------------- 4. pixel art
PX = 8
PAL = {"sky0": "#2B3A67", "sky1": "#4F5D9A", "sky2": "#E9727A", "sky3": "#FFB27A", "sun": "#FFE27A",
       "sun2": "#FFC94A", "sea0": "#2E5FA8", "sea1": "#1F4687", "sea2": "#163266", "foam": "#A9D8FF",
       "white": "#FFFFFF", "grey": "#C9CCD6", "red": "#E34D4D", "cloud": "#F4E9FF", "dk": "#1A1C2C"}


def r_pixel(c, st, t):
    tt = math.floor(st["tt"] * 10) / 10
    st = story_q(st, tt)
    w, h = W // PX, H // PX
    surf = skia.Surface(w, h)
    k = surf.getCanvas()
    nofx = lambda colr: skia.Paint(Color=col(PAL[colr]), AntiAlias=False)  # noqa: E731
    hz = HORIZON // PX
    bands = [("sky0", 0), ("sky1", int(hz * 0.45)), ("sky2", int(hz * 0.72)), ("sky3", int(hz * 0.88))]
    for i, (name, y0) in enumerate(bands):
        y1 = bands[i + 1][1] if i + 1 < len(bands) else hz
        k.drawRect(skia.Rect.MakeLTRB(0, y0, w, y1), nofx(name))
        if i + 1 < len(bands):    # dither the band edge
            for x in range(0, w, 2):
                k.drawRect(skia.Rect.MakeXYWH(x + (y1 % 2), y1 - 1, 1, 1), nofx(bands[i + 1][0]))
                k.drawRect(skia.Rect.MakeXYWH(x + 1 - (y1 % 2), y1, 1, 1), nofx(name))
    for i in range(30):                                  # stars, twinkling
        x, y = int(hrand(i, 1) * w), int(hrand(i, 2) * hz * 0.5)
        if hrand(i, int(tt * 4)) > 0.3:
            k.drawRect(skia.Rect.MakeXYWH(x, y, 1, 1), nofx("white"))
    sx, sy, r = 540 // PX, int(st["sun_y"] / PX), 18
    for yy in range(-r, r + 1):
        half = int(math.sqrt(max(0, r * r - yy * yy)))
        if sy + yy < hz:
            k.drawRect(skia.Rect.MakeXYWH(sx - half, sy + yy, 2 * half + 1, 1), nofx("sun" if yy < 6 else "sun2"))
    for i, (x, y, s) in enumerate(CLOUDS):
        cx, cy = int((x + tt * 12) / PX), int(y / PX)
        for dx, dy, ww in ((-8, 0, 16), (-5, -3, 10), (-12, 2, 25)):
            k.drawRect(skia.Rect.MakeXYWH(cx + int(dx * s), cy + dy, int(ww * s), 3), nofx("cloud"))
    k.drawRect(skia.Rect.MakeLTRB(0, hz, w, h), nofx("sea0"))
    for row in range(hz, h):
        d = row - hz
        if d % 6 == 3:
            k.drawRect(skia.Rect.MakeLTRB(0, row, w, row + 2), nofx("sea1" if d < 40 else "sea2"))
        if d > 40:
            k.drawRect(skia.Rect.MakeLTRB(0, row, w, row + 1), nofx("sea2" if d % 3 else "sea1"))
    for i in range(40):                                   # foam glints that drift
        y = hz + 2 + int(hrand(i, 3) * (h - hz - 4))
        x = int((hrand(i, 4) * w + tt * (6 + 10 * hrand(i, 5))) % w)
        k.drawRect(skia.Rect.MakeXYWH(x, y, 2 + int(hrand(i, 6) * 3), 1), nofx("foam"))
    # sun reflection
    for j in range(6):
        y = hz + 2 + j * 3
        ww = 14 - j * 2 + int(2 * math.sin(tt * 3 + j))
        k.drawRect(skia.Rect.MakeXYWH(sx - ww // 2, y, ww, 1), nofx("sun2"))
    hull, sail, lf, rf = boat_parts(st)
    for pp, name in ((sail, "white"), (lf, "grey"), (rf, "grey"), (hull, "red")):
        q = [(round(x / PX), round(y / PX)) for x, y in pp]
        k.drawPath(poly(q), nofx(name))
        k.drawPath(poly(q), skia.Paint(Color=col(PAL["dk"]), AntiAlias=False, Style=skia.Paint.kStroke_Style,
                                       StrokeWidth=1))
    img = surf.makeImageSnapshot()
    c.drawImageRect(img, skia.Rect.MakeWH(W, H), skia.SamplingOptions(skia.FilterMode.kNearest))
    # scanlines
    p = fill("#000000", 0.07)
    for y in range(0, H, 4):
        c.drawRect(skia.Rect.MakeXYWH(0, y, W, 1), p)


# ---------------------------------------------------------------- 5. neon
def glow_path(c, path, colr, w=4, core=WHITE, a=1.0):
    for wd, bl, al in ((w * 6, 26, 0.35), (w * 2.5, 9, 0.6), (w, 0, 1.0)):
        p = stroke(colr, wd, al * a)
        if bl:
            p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, bl))
        p.setBlendMode(skia.BlendMode.kPlus)
        c.drawPath(path, p)
    c.drawPath(path, stroke(core, w * 0.4, 0.85 * a))


def r_neon(c, st, t):
    tt = st["tt"]
    sh = skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, HORIZON)],
                                        [col("#07021A"), col("#1E0A45"), col("#4A1260")], [0, 0.7, 1])
    c.drawRect(skia.Rect.MakeLTRB(0, 0, W, HORIZON), skia.Paint(Shader=sh))
    for i in range(70):
        x, y = hrand(i, 11) * W, hrand(i, 12) * (HORIZON - 300)
        c.drawCircle(x, y, 1.5 + 2 * hrand(i, 13), fill(WHITE, 0.3 + 0.6 * abs(math.sin(tt * 1.5 + i))))
    # synthwave sun with slices
    sy = st["sun_y"]
    c.save()
    c.clipRect(skia.Rect.MakeLTRB(0, 0, W, HORIZON))
    glow = skia.GradientShader.MakeRadial(skia.Point(540, sy), 420, [col("#FF4FA3", 0.55), col("#FF4FA3", 0)])
    c.drawCircle(540, sy, 420, skia.Paint(Shader=glow))
    sun = skia.Path()
    sun.addCircle(540, sy, 190)
    for i in range(7):
        yy = sy + 20 + i * 26
        gap = 4 + i * 2.6
        cut = skia.Path()
        cut.addRect(skia.Rect.MakeLTRB(300, yy - gap / 2 - ((tt * 20) % 26), 780, yy + gap / 2 - ((tt * 20) % 26)))
        sun = skia.Op(sun, cut, skia.kDifference_PathOp) or sun
    sp = skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeLinear(
        [skia.Point(0, sy - 190), skia.Point(0, sy + 190)], [col("#FFE55C"), col("#FF7A3D"), col("#FF2E88")],
        [0, 0.5, 1]))
    c.drawPath(sun, sp)
    c.restore()
    # mountains silhouette
    m = poly([(-20, HORIZON), (120, 980), (250, 1060), (380, 940), (470, HORIZON), (620, HORIZON), (760, 960),
              (880, 1040), (1000, 930), (1100, HORIZON)])
    c.drawPath(m, fill("#12052B"))
    glow_path(c, m, "#7A5CFF", 3, a=0.8)
    # grid sea
    c.drawRect(skia.Rect.MakeLTRB(0, HORIZON, W, H), fill("#0A0218"))
    for i in range(1, 22):
        z = (i - (tt * 1.6) % 1.0)
        y = HORIZON + 900 / (z * 0.55 + 0.6) - 900 / 0.6 + 900 * (1 - 1 / (1 + z * 0.35))
        y = HORIZON + (H - HORIZON) * (1 - 1 / (1 + z * 0.22)) * 1.1
        if HORIZON < y < H:
            pa = skia.Path()
            pa.moveTo(0, y)
            pa.lineTo(W, y)
            glow_path(c, pa, "#FF2E88", 2, a=0.25 + 0.6 * (y - HORIZON) / (H - HORIZON))
    for i in range(-12, 13):
        pa = skia.Path()
        pa.moveTo(540 + i * 40, HORIZON)
        pa.lineTo(540 + i * 260, H)
        glow_path(c, pa, "#FF2E88", 2, a=0.45)
    glow_path(c, poly([(-10, HORIZON), (W + 10, HORIZON), (W + 10, HORIZON + 1), (-10, HORIZON + 1)]), "#FF8AD8", 3)
    # sun reflection streaks
    for j in range(5):
        y = HORIZON + 30 + j * 40
        ww = 260 - j * 40 + 20 * math.sin(tt * 3 + j)
        c.drawRect(skia.Rect.MakeXYWH(540 - ww / 2, y, ww, 6), fill("#FF7A3D", 0.5, blur=6))
    hull, sail, lf, rf = boat_parts(st)
    for pp in (sail, lf, rf, hull):
        c.drawPath(poly(pp), fill("#0A0218", 0.92))
    for pp, cc in ((sail, "#3DF5FF"), (lf, "#3DF5FF"), (rf, "#3DF5FF"), (hull, "#3DF5FF")):
        glow_path(c, poly(pp), cc, 4)


RENDER = {"clay": r_clay, "crayon": r_crayon, "paper": r_paper, "pixel": r_pixel, "neon": r_neon}


# ---------------------------------------------------------------- overlays
def style_badge(c, t, t0, name, idx):
    k = e_back(prog(t, t0 + 0.05, 0.4), 2.0)
    out = e_out(prog(t, t0 + SEG - 0.25, 0.2))
    a = clamp(k) * (1 - out)
    if a <= 0:
        return
    label = LABEL[name]
    size = 118
    wl = measure(label, "black", size)
    c.save()
    c.translate(W / 2, 520)
    c.scale(lerp(0.7, 1, k), lerp(0.7, 1, k))
    c.drawRRect(rrect(-wl / 2 - 46, -118, wl + 92, 160, 40), fill(INK, 0.86 * a))
    text(c, label, 0, 0, "black", size, WHITE, a, tracking=-0.02)
    text(c, f"{idx + 1}/5", 0, -150, "monob", 42, LIME, a)
    c.restore()


def prompt_pill(c, t, style_name, swap_t, a=1.0):
    """top pill: the prompt + the one word that changes."""
    base = PROMPT + ", "
    size = 38
    word = LABEL[style_name].lower()
    k = prog(t, swap_t, 0.25)
    wb = measure(base, "medium", size)
    ww = measure(word, "bold", size)
    tot = wb + ww
    x0 = W / 2 - tot / 2
    c.drawRRect(rrect(x0 - 36, 238, tot + 72, 84, 42), fill("#000000", 0.55 * a))
    text(c, base, x0, 294, "medium", size, WHITE, a * 0.92, anchor="l")
    c.save()
    c.clipRect(skia.Rect.MakeLTRB(x0 + wb - 4, 250, x0 + tot + 10, 316))
    text(c, word, x0 + wb, 294 + 50 * (1 - e_out(k)), "bold", size, LIME, a, anchor="l")
    c.restore()


def collage(c, t, labels=True, dim=0.0):
    band = H / 5
    for i, sname in enumerate(STYLES):
        c.save()
        c.clipRect(skia.Rect.MakeXYWH(0, i * band, W, band))
        c.translate(W / 2, i * band + band / 2)
        c.scale(0.5, 0.5)
        c.translate(-540, -1060)
        u = 0.55 + 0.25 * math.sin(t * 0.6 + i)
        RENDER[sname](c, story(u, t + i * 0.7), t)
        c.restore()
        if labels:
            text(c, LABEL[sname], 40, i * band + band - 34, "black", 46, WHITE, 0.95, anchor="l", outline=7)
        c.drawRect(skia.Rect.MakeXYWH(0, i * band - 3, W, 6), fill(INK))
    if dim:
        c.drawRect(skia.Rect.MakeWH(W, H), fill(INK, dim))


def draw(c, t, f):
    if t < HOOK_END:
        # all five at once, bands slide in one by one
        collage(c, t)
        for i in range(5):
            k = e_out(prog(t, 0.05 + i * 0.12, 0.45))
            if k < 1:
                c.drawRect(skia.Rect.MakeXYWH(W * k, i * H / 5, W, H / 5), fill(INK))
    elif t < SEG_T["clay"]:
        c.drawPaint(fill("#0F0F14"))
        glow = skia.GradientShader.MakeRadial(skia.Point(W / 2, 900), 700, [col(LIME, 0.1), col(LIME, 0)])
        c.drawPaint(skia.Paint(Shader=glow))
        a = e_out(prog(t, HOOK_END, 0.3))
        text(c, "the prompt", W / 2, 680, "italic", 92, WHITE, a * 0.9)
        prompt_bar(c, t, PROMPT, P_T0, P_T1, cy=900, w=980, dark=True, size=56, a=a, sent_t=SEG_T["clay"] - 0.15)
    elif t < STYLES_END:
        i = max(j for j, s in enumerate(STYLES) if t >= SEG_T[s])
        sname = STYLES[i]
        lt = t - SEG_T[sname]
        u = clamp(0.15 + lt / SEG * 0.8)
        RENDER[sname](c, story(u, lt + i * 0.4), t)
        prompt_pill(c, t, sname, SEG_T[sname] + 0.15)
        style_badge(c, t, SEG_T[sname], sname, i)
        # wipe from the previous style
        if i > 0 and lt < 0.22:
            k = e_io(lt / 0.22)
            prev = STYLES[i - 1]
            c.save()
            c.clipRect(skia.Rect.MakeLTRB(W * k, 0, W, H))
            RENDER[prev](c, story(0.95, SEG + (i - 1) * 0.4), t)
            c.restore()
            c.drawRect(skia.Rect.MakeXYWH(W * k - 10, 0, 20, H), fill(LIME))
    else:
        dim = 0.55 * e_out(prog(t, S.t("nos") - 0.1, 0.4))
        collage(c, t, labels=t < S.t("nos"), dim=dim)
        if t >= S.t("nos") - 0.1:
            items = [(S.t("nos"), "No AI video tool.", WHITE), (S.find("nos", "editing") - 0.25, "No editing software.",
                                                              WHITE), (S.find("nos", "Just"), "Just vibe editing.", LIME)]
            if t >= S.t("cta"):
                items = [(S.t("cta"), "Which one is", WHITE), (S.t("cta") + 0.25, "your favourite?", LIME)]
            for j, (ti, s, cc) in enumerate(items):
                k = e_back(prog(t, ti, 0.35), 2)
                if k > 0:
                    text(c, s, W / 2, 820 + j * 130 + 30 * (1 - k), "black", 92 if cc == LIME else 80, cc, clamp(k),
                         outline=10)
            if t >= S.t("cta") + 0.6:
                k = e_out(prog(t, S.t("cta") + 0.6, 0.35))
                text(c, "Comment 1 – 5", W / 2, 1150, "monob", 54, WHITE, k)
    if t >= END_T:
        endcard(c, t, END_T)
    CAP.draw(c, t)


CAP = Captions(S.words(skip=STYLES), y=1640, size=82).mute(S.t("nos") - 0.2, END_T)
CAP.mute(P_T0, SEG_T["clay"])
film = Film(draw, DUR, FPS, out_dir=HERE / "out", warm=C.texture)


# ---------------------------------------------------------------- sound
def sound():
    import audio_kit as ak
    from sound import Mix
    m = Mix(DUR)
    m.voice(S.placements())
    bed = ak.music_bed("upbeat", seconds=DUR + 1, bpm=110, key="D", intro_bars=1, seed=11)
    m.music(bed, gain_db=-14, duck_db=-8)
    for i in range(5):
        m.sfx("swish", 0.05 + i * 0.12, -14)
    m.sfx("typing", P_T0, -13, dur=P_T1 - P_T0, cps=20)
    m.sfx("click", SEG_T["clay"] - 0.15, -5)
    for i, s in enumerate(STYLES):
        m.sfx("whoosh" if i else "impact", SEG_T[s] - (0.1 if i else 0), -10 if i else -12)
        m.sfx("pop", SEG_T[s] + 0.08, -10)
    m.sfx("riser", COLLAGE_T - 1.2, -16, dur=1.2)
    m.sfx("impact", COLLAGE_T, -12)
    m.sfx("whoosh", S.t("nos") - 0.15, -12)
    for t in (S.t("nos"), S.find("nos", "editing") - 0.25, S.find("nos", "Just")):
        m.sfx("pop", t, -9)
    m.sfx("sparkle", S.t("cta"), -10)
    m.sfx("whoosh", END_T - 0.25, -10)
    m.sfx("ding", END_T + 0.1, -12)
    m.finish(HERE / "out" / "picture.mp4", HERE / "out" / "02_same_prompt_five_styles.mp4", HERE / "work")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    print(f"duration {DUR:.2f}s")
    if cmd == "sheet":
        film.sheet()
    elif cmd == "stills":
        film.stills([float(x) for x in sys.argv[2:]])
    elif cmd == "draft":
        film.render(draft=True)
    elif cmd == "render":
        film.render()
    elif cmd == "sound":
        sound()
    elif cmd == "all":
        film.render()
        sound()
