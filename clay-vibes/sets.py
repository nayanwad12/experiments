"""Miniature sets and props: the farm, the barn, the editing desk, and all the clay bits on it."""

import math

import numpy as np
import skia

from lib import (H, W, blob, clamp, clay, clay_letter, clay_stroke, col, glyph_paths, heart_path, hexrgb,
                 lerp, lumpy_poly, lumpy_rrect, mix, paint, smooth_path, star_path, tex_paint, union)

_CACHE = {}


def cached(key, fn):
    """Render a static layer once per process into a transparent image."""
    if key not in _CACHE:
        s = skia.Surface(W, H)
        cv = s.getCanvas()
        cv.clear(skia.ColorTRANSPARENT)
        fn(cv)
        _CACHE[key] = s.makeImageSnapshot()
    return _CACHE[key]


DIRECT = False   # close-ups draw sets live instead of upscaling a cached raster


def layer(c, key, fn):
    if DIRECT:
        c.saveLayer(None, None)
        fn(c)
        c.restore()
    else:
        c.drawImage(cached(key, fn), 0, 0)


def blurred_layer(c, sigma):
    c.saveLayer(None, skia.Paint(ImageFilter=skia.ImageFilters.Blur(sigma, sigma)))


# ================================================================ FARM
SKY_DAY = ("#7DBFE6", "#D7EEF3")
SKY_SUN = ("#F08A55", "#FFD79A")


def _sky(c, warm):
    top = mix(SKY_DAY[0], SKY_SUN[0], warm)
    bot = mix(SKY_DAY[1], SKY_SUN[1], warm)
    sh = skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, 820)], [col(top), col(bot)])
    c.drawPaint(skia.Paint(Shader=sh))
    c.drawPaint(tex_paint(3, 0.22, 3.0))        # painted-backdrop brush texture


def cloud_path(cx, cy, s, seed, f=0, boil=0.0):
    parts = [blob(cx + dx * s, cy + dy * s, r * s, r * s * 0.85, seed + i, 0.06, boil, f, n=24)
             for i, (dx, dy, r) in enumerate([(-70, 10, 48), (-20, -18, 62), (45, -5, 55), (95, 15, 40), (10, 22, 55)])]
    return union(parts)


def _hills_far(c, warm):
    g1, g2 = mix("#9CCB74", "#C9A56A", warm * 0.6), mix("#86BC63", "#B18E5A", warm * 0.6)
    clay(c, blob(420, 930, 820, 250, 21, 0.02), g1, 21, cast=False, gloss=0.08, tex=0.35, tex_scale=2)
    clay(c, blob(1500, 960, 900, 280, 22, 0.02), g2, 22, cast=False, gloss=0.08, tex=0.35, tex_scale=2)


def _tree(c, x, y, s, seed, warm):
    trunk = lumpy_rrect(x - 22 * s, y - 210 * s, 44 * s, 215 * s, 18 * s, seed, 2.5)
    clay(c, trunk, "#7A4E2D", seed)
    leaves = union([blob(x + dx * s, y + dy * s, r * s, r * s * 0.9, seed + i, 0.07, n=26)
                    for i, (dx, dy, r) in enumerate([(-80, -250, 85), (0, -320, 105), (85, -255, 88),
                                                     (-30, -210, 80), (40, -205, 78)])])
    clay(c, leaves, mix("#4E9A3E", "#6C8A3A", warm * 0.5), seed + 9, gloss=0.15)
    rng = np.random.default_rng(seed)
    for _ in range(7):   # apples
        ax, ay = x + rng.uniform(-130, 130) * s, y + rng.uniform(-360, -190) * s
        clay(c, blob(ax, ay, 13 * s, 13 * s, int(ax), 0.06), "#D9443A", int(ay), gloss=0.4)


def _barn(c, x, y, s, warm):
    """Ground-centre (x, y)."""
    w, h = 360 * s, 250 * s
    red = mix("#C2412F", "#B5402E", warm)
    body = lumpy_rrect(x - w / 2, y - h, w, h, 10 * s, 41, 2.5)
    clay(c, body, red, 41, tex_scale=1.2)
    for i in range(1, 9):     # siding grooves
        xx = x - w / 2 + w * i / 9
        c.drawLine(xx, y - h + 8, xx, y - 6, paint(red, 0.7, k=0.7, stroke=3))
    roof = lumpy_poly([(x - w / 2 - 30 * s, y - h + 6), (x, y - h - 150 * s), (x + w / 2 + 30 * s, y - h + 6)], 42, 2.5)
    clay(c, roof, "#5B3A2E", 42)
    trim = mix("#F6EFE2", "#FFE3C0", warm)
    clay_stroke(c, [(x - w / 2 - 22 * s, y - h + 2), (x, y - h - 140 * s), (x + w / 2 + 22 * s, y - h + 2)], 14 * s,
                trim, 43, cast=False)
    dx0, dw, dh = x - 85 * s, 170 * s, 150 * s
    door = lumpy_rrect(dx0, y - dh, dw, dh, 6, 44, 2)
    clay(c, door, mix(red, (90, 20, 15), 0.25), 44, cast=False)
    for p in ([(dx0 + 8, y - dh + 8), (dx0 + dw - 8, y - 8)], [(dx0 + dw - 8, y - dh + 8), (dx0 + 8, y - 8)],
              [(dx0 + 4, y - dh + 6), (dx0 + dw - 4, y - dh + 6), (dx0 + dw - 4, y - 4), (dx0 + 4, y - 4), (dx0 + 4, y - dh + 6)]):
        clay_stroke(c, p, 11 * s, trim, 45, cast=False, tex=0.3)
    lw = 70 * s
    loft = lumpy_rrect(x - lw / 2, y - h - 70 * s, lw, 70 * s, 6, 46, 1.5)
    clay(c, loft, "#3A2620", 46, cast=False)
    clay_stroke(c, [(x - lw / 2, y - h - 70 * s), (x + lw / 2, y - h), ], 8 * s, trim, 47, cast=False)
    clay_stroke(c, [(x + lw / 2, y - h - 70 * s), (x - lw / 2, y - h)], 8 * s, trim, 48, cast=False)


def _fence(c, x0, x1, y, warm):
    wood = mix("#A57A4F", "#B07A48", warm)
    n = int((x1 - x0) / 120)
    for k, yy in enumerate((y - 70, y - 35)):
        clay(c, lumpy_rrect(x0 - 10, yy, x1 - x0 + 20, 16, 7, 50 + k, 2), wood, 50 + k, gloss=0.1)
    for i in range(n + 1):
        px = x0 + (x1 - x0) * i / n
        clay(c, lumpy_rrect(px - 11, y - 95, 22, 100, 8, 60 + i, 1.8), mix(wood, (60, 35, 20), 0.15), 60 + i)


def farm_back(c, warm=0.0):
    def draw(cv):
        _sky(cv, warm)
        if warm < 0.5:
            sun = blob(1640, 175, 70, 70, 7, 0.03)
            cv.drawCircle(1640, 175, 120, paint("#FFF3B0", 0.55, blur=40))
            clay(cv, sun, "#FFD84D", 7, cast=False, gloss=0.3)
        else:
            cv.drawCircle(860, 620, 260, paint("#FFE2A0", 0.5, blur=70))
            clay(cv, blob(860, 620, 100, 100, 8, 0.02), "#FFB04A", 8, cast=False, gloss=0.2)
        blurred_layer(cv, 2.2)
        _hills_far(cv, warm)
        cv.restore()
        blurred_layer(cv, 1.0)
        _tree(cv, 230, 760, 1.05, 70, warm)
        _barn(cv, 1590, 790, 1.15, warm)
        _fence(cv, 420, 1330, 800, warm)
        cv.restore()
    layer(c, ("farm_back", warm), draw)


def farm_field(c, warm=0.0):
    def draw(cv):
        g = mix("#6FAE45", "#8C9A3C", warm * 0.55)
        field = smooth_path([(-40, 790), (300, 770), (700, 790), (1100, 775), (1500, 795), (1960, 780),
                             (1960, 1120), (-40, 1120)], closed=True)
        clay(cv, field, g, 81, cast=False, gloss=0.05, tex=0.45, tex_scale=1.6)
        rng = np.random.default_rng(82)
        for _ in range(240):  # grass tufts
            x, y = rng.uniform(0, W), rng.uniform(800, 1080)
            hgt = rng.uniform(10, 24) * (0.6 + (y - 800) / 400)
            for k in (-1, 0, 1):
                cv.drawLine(x, y, x + k * 5 + rng.uniform(-2, 2), y - hgt,
                            paint(g, 0.9, k=rng.uniform(0.75, 1.15), stroke=3.2))
        for _ in range(60):   # flowers
            x, y = rng.uniform(0, W), rng.uniform(810, 1060)
            r = 6 + (y - 800) / 50
            cc = ["#FFFFFF", "#FFE066", "#F7A8C4"][rng.integers(0, 3)]
            for k in range(5):
                a = k * 2 * math.pi / 5
                cv.drawCircle(x + r * math.cos(a), y + r * math.sin(a) * 0.8, r * 0.6, paint(cc))
            cv.drawCircle(x, y, r * 0.5, paint("#F2A23A"))
    layer(c, ("farm_field", warm), draw)


def stone_wall(c, y=905, warm=0.0):
    def draw(cv):
        rng = np.random.default_rng(91)
        greys = ["#9C9A93", "#8B8A84", "#ADA9A0", "#7F7D78", "#A39F95"]
        for row, (yy, hh) in enumerate([(y + 135, 70), (y + 70, 70), (y + 5, 72), (y - 58, 66)]):
            x = -40 - row * 45
            while x < W + 40:
                w = rng.uniform(110, 175)
                st = blob(x + w / 2, yy + hh / 2, w / 2 + 4, hh / 2 + 4, int(x * 7 + row), 0.07, n=30)
                clay(cv, st, mix(rng.choice(greys), "#C08A60", warm * 0.25), int(x + row * 13), gloss=0.12,
                     cast_alpha=0.4)
                if rng.uniform() < 0.3:   # moss
                    mx = x + rng.uniform(0.2, 0.8) * w
                    clay(cv, blob(mx, yy + 8, rng.uniform(16, 30), 9, int(mx), 0.15), "#6E9B3F", int(mx) + 1,
                         cast=False, tex=0.4)
                x += w + rng.uniform(-6, 4)
    layer(c, ("wall", y, warm), draw)


# ================================================================ BARN INTERIOR
PLANKS = ["#9C6A43", "#91603C", "#A57449", "#8A5B37", "#A06C45"]


def _planks(cv, x0, y0, x1, y1, pw=118, seed=100):
    rng = np.random.default_rng(seed)
    cv.drawRect(skia.Rect(x0, y0, x1, y1), paint("#3B2516"))
    x, i = x0 - 20, 0
    while x < x1 + 20:
        w = pw + rng.uniform(-10, 10)
        base = PLANKS[i % len(PLANKS)]
        p = lumpy_rrect(x + 3, y0 - 20, w - 6, y1 - y0 + 40, 8, seed + i, 1.8)
        clay(cv, p, base, seed + i, cast=False, gloss=0.06, tex=0.45, tex_scale=1.3)
        cv.save()
        cv.clipPath(p, skia.ClipOp.kIntersect, True)
        for g in range(6):    # grain
            gx = x + w * (0.12 + 0.15 * g) + rng.uniform(-6, 6)
            pts = [(gx + 6 * math.sin(yy / 90 + g + i), yy) for yy in np.arange(y0 - 20, y1 + 20, 40)]
            cv.drawPath(smooth_path(pts, False), paint(base, 0.55, k=0.72, stroke=2.2))
        for _ in range(rng.integers(0, 2) + 1):   # knots
            kx, ky = x + rng.uniform(0.3, 0.7) * w, rng.uniform(y0 + 60, y1 - 60)
            for r, k in ((16, 0.55), (10, 0.65), (5, 0.45)):
                cv.drawOval(skia.Rect.MakeXYWH(kx - r * 0.7, ky - r, r * 1.4, r * 2), paint(base, 0.9, k=k, stroke=2.5))
        for ny in (y0 + 40, y1 - 40):   # nails
            cv.drawCircle(x + w / 2, ny, 5, paint("#5A5550"))
            cv.drawCircle(x + w / 2 - 1.5, ny - 1.5, 2, paint("#B8B2A8"))
        cv.restore()
        x += w
        i += 1


WIN = (150, 120, 330, 290)   # x, y, w, h


def barn_wall(c, dim=False):
    def draw(cv):
        _planks(cv, 0, 0, W, 860)
        x, y, w, h = WIN
        hole = lumpy_rrect(x, y, w, h, 14, 120, 1.5)
        cv.drawPath(hole, skia.Paint(AntiAlias=True, BlendMode=skia.BlendMode.kClear))
        frame = skia.Path()
        frame.addPath(lumpy_rrect(x - 22, y - 22, w + 44, h + 44, 20, 121, 2))
        frame.addPath(hole)
        frame.setFillType(skia.PathFillType.kEvenOdd)
        clay(cv, frame, "#EDE3CF", 121)
        clay(cv, lumpy_rrect(x + w / 2 - 9, y, 18, h, 6, 122, 1.2), "#EDE3CF", 122, cast_alpha=0.25)
        clay(cv, lumpy_rrect(x, y + h / 2 - 9, w, 18, 6, 123, 1.2), "#EDE3CF", 123, cast_alpha=0.25)
        clay(cv, lumpy_rrect(x - 40, y + h + 16, w + 80, 26, 10, 124, 2), "#D8CBB2", 124)  # sill
        # floor
        floor = smooth_path([(-40, 850), (500, 840), (1100, 848), (1960, 838), (1960, 1120), (-40, 1120)])
        clay(cv, floor, "#C9A15B", 130, cast=False, gloss=0.04, tex=0.5)
        rng = np.random.default_rng(131)
        for _ in range(420):
            sx, sy = rng.uniform(-20, W + 20), rng.uniform(850, 1080)
            a = rng.uniform(-0.5, 0.5) + (math.pi if rng.uniform() < 0.5 else 0)
            ln = rng.uniform(16, 40)
            cv.drawLine(sx, sy, sx + ln * math.cos(a), sy + ln * math.sin(a) * 0.4,
                        paint(rng.choice(["#E6C46E", "#B88D45", "#F2D98C"]), 0.9, stroke=2.5))
        # skirting shadow
        cv.drawRect(skia.Rect(0, 836, W, 862), paint("#2A1A0E", 0.35, blur=10))
    layer(c, ("barn_wall", dim), draw)


def window_sky(c, tod):
    """tod: 0 day, 1 dusk, 2 night, 3 morning (continuous)."""
    keys = [("#8CCBEB", "#D9F0F5"), ("#E9895A", "#F8C88A"), ("#1E2850", "#3A4A7A"), ("#FFC27A", "#FFE9B8")]
    i = int(clamp(math.floor(tod), 0, 2))
    u = clamp(tod - i)
    top = mix(keys[i][0], keys[i + 1][0], u)
    bot = mix(keys[i][1], keys[i + 1][1], u)
    x, y, w, h = WIN
    c.save()
    c.clipRect(skia.Rect(x - 5, y - 5, x + w + 5, y + h + 5))
    sh = skia.GradientShader.MakeLinear([skia.Point(0, y), skia.Point(0, y + h)], [col(top), col(bot)])
    c.drawPaint(skia.Paint(Shader=sh))
    night = clamp(1 - abs(tod - 2) * 1.2)
    if night > 0:
        rng = np.random.default_rng(5)
        for _ in range(16):
            c.drawCircle(x + rng.uniform(0, w), y + rng.uniform(0, h * 0.7), rng.uniform(1.5, 3), paint("#FFF6D0", night))
    # sun / moon on an arc across the window
    a = (tod % 1.0)
    sx, sy = x + w * (0.1 + 0.8 * a), y + h * (0.85 - 0.6 * math.sin(math.pi * a))
    is_moon = 1.5 <= tod < 2.5
    c.drawCircle(sx, sy, 34, paint("#FFF3C4" if is_moon else "#FFE070", 0.9, blur=8))
    c.drawCircle(sx, sy, 26, paint("#F4F1E2" if is_moon else "#FFD23F"))
    # distant hill
    c.drawPath(blob(x + w * 0.4, y + h + 60, w * 0.8, 110, 8, 0.03), paint(mix("#7DB35A", "#1F3A33", night)))
    c.restore()


def clock(c, cx, cy, r, ang_min, ang_hr, f=0):
    clay(c, blob(cx, cy, r + 14, r + 14, 140, 0.02, 0.3, f), "#C8473A", 140)
    clay(c, blob(cx, cy, r, r, 141, 0.02), "#F7F0DE", 141, cast=False, gloss=0.3)
    for i in range(12):
        a = i * math.pi / 6
        c.drawCircle(cx + 0.78 * r * math.sin(a), cy - 0.78 * r * math.cos(a), 5 if i % 3 == 0 else 3, paint("#3A2E29"))
    for ang, ln, wd in ((ang_hr, 0.5, 9), (ang_min, 0.75, 6)):
        clay_stroke(c, [(cx, cy), (cx + ln * r * math.sin(ang), cy - ln * r * math.cos(ang))], wd, "#2B211C",
                    142, cast=False, tex=0.1)
    c.drawCircle(cx, cy, 7, paint("#C8473A"))


BOARD = (1010, 110, 820, 430)
CLIPS = [  # (track, start, length, colour) in board units: start/len as fraction of track
    (0, 0.00, 0.22, "#F2A65A"), (0, 0.22, 0.30, "#E86F68"), (0, 0.52, 0.18, "#F6D25C"), (0, 0.70, 0.30, "#8BC7E8"),
    (1, 0.00, 0.35, "#9B8BE0"), (1, 0.35, 0.25, "#7CCB88"), (1, 0.60, 0.40, "#F08FB4"),
    (2, 0.00, 0.50, "#5FB3A8"), (2, 0.50, 0.30, "#5FB3A8"), (2, 0.80, 0.20, "#5FB3A8"),
]


def board_track_rect(track, s0, ln):
    x, y, w, h = BOARD
    tx0, tw = x + 40, w - 80
    ty = y + 95 + track * 105
    return tx0 + tw * s0 + 3, ty, tw * ln - 6, 74


def timeline_board(c):
    def draw(cv):
        x, y, w, h = BOARD
        clay(cv, lumpy_rrect(x - 26, y - 26, w + 52, h + 52, 22, 150, 2.5), "#8B5A33", 150, cast_alpha=0.45)
        clay(cv, lumpy_rrect(x, y, w, h, 14, 151, 1.5), "#36504C", 151, gloss=0.05, cast=False, tex=0.5)
        for i in range(17):  # ruler ticks
            tx = x + 40 + (w - 80) * i / 16
            cv.drawLine(tx, y + 30, tx, y + (60 if i % 4 == 0 else 48), paint("#E9E3D2", 0.8, stroke=4))
        for tr in range(3):
            tx, ty, tw, th = board_track_rect(tr, 0, 1)
            cv.drawPath(lumpy_rrect(tx - 6, ty - 6, tw + 12, th + 12, 12, 152 + tr, 1.2),
                        paint("#24382F", 0.85))
    layer(c, "board", draw)


def clip_block(c, x, y, w, h, color, seed, rot=0.0, sq=(1, 1), f=0, audio=False):
    c.save()
    c.translate(x + w / 2, y + h)
    c.rotate(rot)
    c.scale(sq[0], sq[1])
    p = lumpy_rrect(-w / 2, -h, w, h, 14, seed, 1.6, 0.6, f)
    clay(c, p, color, seed, gloss=0.25)
    if audio:
        pts = [(-w / 2 + 14 + i * 9, -h / 2 + (12 if i % 2 else -12) * math.sin(i * 1.7 + seed) ** 2 * (1 if i % 2 else -1))
               for i in range(int((w - 28) / 9))]
        if len(pts) > 2:
            c.drawPath(smooth_path(pts, False), paint("#ffffff", 0.75, stroke=3))
    else:
        c.drawPath(lumpy_rrect(-w / 2 + 10, -h + 10, min(46, w - 20), h - 20, 6, seed + 1, 0.8),
                   paint("#ffffff", 0.45))
    c.restore()


def crate(c, x, y, w, h, seed=160):
    def draw(cv):
        top = lumpy_rrect(x - 12, y - 18, w + 24, 34, 10, seed, 1.5)
        n = 3
        for i in range(n):
            ph = h / n
            p = lumpy_rrect(x, y + i * ph + 3, w, ph - 6, 8, seed + 1 + i, 2)
            clay(cv, p, PLANKS[(i + 2) % 5], seed + 1 + i, cast_alpha=0.4, gloss=0.08)
            cv.save()
            cv.clipPath(p, skia.ClipOp.kIntersect, True)
            for g in range(3):
                gy = y + i * ph + ph * (0.3 + 0.2 * g)
                cv.drawPath(smooth_path([(x + xx, gy + 4 * math.sin(xx / 70 + g)) for xx in range(0, int(w) + 40, 40)],
                                        False), paint(PLANKS[(i + 2) % 5], 0.6, k=0.7, stroke=2))
            cv.restore()
        for bx in (x + 8, x + w - 48):
            clay(cv, lumpy_rrect(bx, y, 40, h, 8, seed + 10 + int(bx), 1.5), "#7E5232", seed + 11)
        clay(cv, top, "#B5845A", seed + 20, gloss=0.12)
    layer(c, ("crate", x, y, w, h), draw)


def laptop_back(c, cx, y, w=300, h=200, seed=170, glow=0.0, glow_col="#9FD8FF", f=0):
    if glow > 0:
        c.drawRect(skia.Rect.MakeXYWH(cx - w / 2 - 30, y - h - 40, w + 60, h + 40), paint(glow_col, 0.35 * glow, blur=40))
    clay(c, lumpy_rrect(cx - w / 2 - 20, y - 12, w + 40, 22, 8, seed, 1), "#7D858F", seed)
    lid = lumpy_rrect(cx - w / 2, y - h, w, h, 18, seed + 1, 1.5, 0.3, f)
    clay(c, lid, "#A9B1BA", seed + 1, gloss=0.3)
    logo = heart_path(cx, y - h / 2 - 4, 22)
    clay(c, logo, "#E9EDF1", seed + 2, cast=False, gloss=0.4, tex=0.2)


def hay_bale(c, x, y, w, h, seed=180):
    p = lumpy_rrect(x, y, w, h, 22, seed, 3.5)
    clay(c, p, "#E2B957", seed, gloss=0.1, cast_alpha=0.4)
    rng = np.random.default_rng(seed)
    c.save()
    c.clipPath(p, skia.ClipOp.kIntersect, True)
    for _ in range(int(w * h / 260)):
        sx, sy = x + rng.uniform(0, w), y + rng.uniform(0, h)
        a = rng.uniform(-0.4, 0.4)
        ln = rng.uniform(14, 30)
        c.drawLine(sx, sy, sx + ln * math.cos(a), sy + ln * math.sin(a),
                   paint(rng.choice(["#F4D67F", "#B98E36", "#CFA347"]), 0.9, stroke=2.4))
    for bx in (x + w * 0.27, x + w * 0.73):
        c.drawLine(bx, y - 5, bx + 4, y + h + 5, paint("#8A5A2C", 1, stroke=8))
    c.restore()
    for _ in range(14):   # stray straws poking out
        a = rng.uniform(0, 2 * math.pi)
        sx, sy = x + w / 2 + (w / 2) * math.cos(a), y + h / 2 + (h / 2) * math.sin(a)
        c.drawLine(sx, sy, sx + 18 * math.cos(a + rng.uniform(-0.5, 0.5)), sy + 18 * math.sin(a + rng.uniform(-0.5, 0.5)),
                   paint("#E8C46A", 1, stroke=2.4))


def mug(c, x, y, s=1.0, color="#E86F68", seed=190, steam=0.0, f=0):
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    clay_stroke(c, [(26, -52), (46, -46), (46, -24), (26, -18)], 10, color, seed + 1)
    body = lumpy_rrect(-30, -64, 60, 64, 12, seed, 1.2)
    clay(c, body, color, seed, gloss=0.35)
    c.drawOval(skia.Rect.MakeXYWH(-25, -66, 50, 12), paint("#4A2A18"))
    if steam > 0:
        for k in (-10, 8):
            pts = [(k + 7 * math.sin(i * 1.3 + f * 0.9 + k), -74 - i * 14) for i in range(5)]
            c.drawPath(smooth_path(pts, False), paint("#ffffff", 0.55 * steam, stroke=5, blur=2))
    c.restore()


def paper_ball(c, x, y, r, seed=200, f=0):
    p = blob(x, y, r, r * 0.92, seed, 0.12, 0.8, f, n=16)
    clay(c, p, "#F3F0E6", seed, gloss=0.15, tex=0.4)
    rng = np.random.default_rng(seed)
    c.save()
    c.clipPath(p, skia.ClipOp.kIntersect, True)
    for _ in range(5):
        a = rng.uniform(0, 2 * math.pi)
        c.drawLine(x + r * 0.2 * math.cos(a), y + r * 0.2 * math.sin(a), x + r * math.cos(a + 0.5),
                   y + r * math.sin(a + 0.5), paint("#B9B3A3", 0.8, stroke=2))
    c.restore()


def film_strip(c, pts, width=34, seed=210, cast=True):
    if len(pts) < 2:
        return
    sp = smooth_path(pts, False)
    out = skia.Path()
    paint(stroke=width, cap="butt").getFillPath(sp, out)
    clay(c, out, "#3C3B45", seed, tex=0.35, gloss=0.2, cast=cast)
    meas = skia.PathMeasure(sp, False)
    L = meas.getLength()
    d = 6.0
    i = 0
    while d < L - 4:
        pos, tan = meas.getPosTan(d)
        nx, ny = -tan.y(), tan.x()
        for side in (-1, 1):
            hx, hy = pos.x() + nx * side * width * 0.34, pos.y() + ny * side * width * 0.34
            c.drawCircle(hx, hy, width * 0.075, paint("#D9D4C7"))
        if i % 3 == 0:
            c.drawCircle(pos.x(), pos.y(), width * 0.17, paint(["#F2A65A", "#8BC7E8", "#F08FB4", "#7CCB88"][(i // 3) % 4], 0.75))
        d += width * 0.3
        i += 1


def bulb(c, cx, cy, s=1.0, on=1.0, f=0, seed=220):
    c.save()
    c.translate(cx, cy)
    c.scale(s, s)
    if on > 0:
        c.drawCircle(0, -10, 120, paint("#FFE98A", 0.55 * on, blur=45))
        for i in range(8):
            a = i * math.pi / 4 + 0.2
            r0, r1 = 72, 72 + 34 * on
            clay_stroke(c, [(r0 * math.cos(a), -10 + r0 * math.sin(a)), (r1 * math.cos(a), -10 + r1 * math.sin(a))],
                        10, "#FFD84D", seed + i, cast=False, tex=0.2)
    glass = union([blob(0, -14, 50, 52, seed, 0.03, 0.6, f), blob(0, 30, 24, 22, seed + 1, 0.03)])
    clay(c, glass, mix("#E8E4C9", "#FFE45C", on), seed, gloss=0.6, cast=False, tex=0.2)
    for k in range(3):
        clay(c, lumpy_rrect(-22, 44 + k * 11, 44, 12, 5, seed + 5 + k, 0.6), "#9097A0", seed + 5 + k, cast=False, tex=0.2)
    fil = skia.Path()
    fil.moveTo(-10, 30)
    fil.lineTo(-7, 2)
    fil.addArc(skia.Rect.MakeXYWH(-7, -6, 14, 14), 180, 180)
    fil.lineTo(10, 30)
    c.drawPath(fil, paint("#B8860B" if on < 0.5 else "#FF8A1E", 1, stroke=3))
    c.restore()


def bubble(c, x, y, w, h, tail=(0, 60), seed=230, f=0, color="#FFFFFF"):
    """Speech bubble centred at (x, y); tail is the tip offset from the bubble's bottom-centre."""
    body = blob(x, y, w / 2, h / 2, seed, 0.04, 0.8, f)
    tx, ty = x + tail[0], y + h / 2 + tail[1]
    tp = smooth_path([(x - w * 0.12, y + h * 0.3), (tx, ty), (x + w * 0.06, y + h * 0.35)])
    p = union([body, tp])
    clay(c, p, color, seed, gloss=0.25, cast_alpha=0.3)
    return p


def clay_text(c, text, x, y, size, color, fname="Unbounded-Black.ttf", seed=0, depth=6, tracking=0.0,
              scales=None, offsets=None):
    gl = glyph_paths(text, fname, size, tracking, seed, lump=max(0.6, size / 110))
    for i, (p, xc) in enumerate(gl):
        c.save()
        dx, dy = offsets[i] if offsets else (0, 0)
        sx, sy = scales[i] if scales else (1, 1)
        c.translate(x + xc + dx, y + dy)
        c.scale(sx, sy)
        c.translate(-xc, 0)
        clay_letter(c, p, color if isinstance(color, (str, tuple)) else color[i % len(color)], seed + i, depth)
        c.restore()
    return gl


def music_note(c, x, y, s=1.0, color="#3A2E29", seed=240, rot=0.0):
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.scale(s, s)
    p = union([blob(0, 0, 16, 12, seed, 0.05, rot=-0.4), _rect_path(10, -58, 7, 58)])
    flag = smooth_path([(13, -58), (34, -44), (30, -26), (24, -40), (13, -44)])
    p = union([p, flag])
    clay(c, p, color, seed, gloss=0.3, cast_alpha=0.25)
    c.restore()


def _rect_path(x, y, w, h):
    p = skia.Path()
    p.addRoundRect(skia.Rect.MakeXYWH(x, y, w, h), 3, 3)
    return p


def popcorn_bucket(c, x, y, s=1.0, seed=250):
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    for i in range(9):   # heap
        clay(c, blob(-48 + i * 12, -128 - 10 * math.sin(i * 1.1), 16, 14, seed + i, 0.15, n=14), "#FFF4CF", seed + i,
             cast=False, gloss=0.2)
    body = lumpy_poly([(-62, -122), (62, -122), (46, 0), (-46, 0)], seed, 1.5)
    clay(c, body, "#F7F2E6", seed, gloss=0.25)
    c.save()
    c.clipPath(body, skia.ClipOp.kIntersect, True)
    for k in range(-3, 4, 2):
        c.drawPath(lumpy_poly([(k * 18 - 9, -125), (k * 18 + 9, -125), (k * 14 + 7, 2), (k * 14 - 7, 2)], seed + k, 0.8),
                   paint("#D9443A"))
    c.restore()
    c.restore()


def kernel(c, x, y, r, seed):
    clay(c, union([blob(x + dx * r, y + dy * r, r * 0.6, r * 0.55, seed + i, 0.12, n=12)
                   for i, (dx, dy) in enumerate([(-0.3, 0), (0.3, -0.1), (0, -0.4), (0.05, 0.3)])]),
         "#FFF4CF", seed, cast_alpha=0.25, gloss=0.2)


def signpost(c, x, y, lines, seed=260, swing=0.0):
    c.save()
    c.translate(x, y)
    clay(c, lumpy_rrect(-14, -260, 28, 262, 8, seed, 1.5), "#7A4E2D", seed)
    c.translate(0, -250)
    c.rotate(swing)
    board = lumpy_rrect(-200, 0, 400, 150, 16, seed + 1, 2.2)
    clay(c, board, "#C08A55", seed + 1, gloss=0.1, cast_alpha=0.4)
    for nx in (-180, 180):
        c.drawCircle(nx, 20, 6, paint("#5A5550"))
    for (txt, size, yy, fname) in lines:
        f = __import__("lib").font(fname, size)
        wd = f.measureText(txt)
        c.save()
        c.translate(-wd / 2, yy)
        blob_ = skia.TextBlob.MakeFromString(txt, f)
        c.drawTextBlob(blob_, 2, 2, paint("#ffffff", 0.25))
        c.drawTextBlob(blob_, 0, 0, paint("#3A2414", 0.95))
        c.restore()
    c.restore()


def projector_screen(c, x, y, w, h, seed=270):
    rod = lumpy_rrect(x - 30, y - 26, w + 60, 26, 12, seed, 1.2)
    sheet = lumpy_poly([(x, y), (x + w, y), (x + w + 6, y + h), (x + w * 0.5, y + h + 10), (x - 6, y + h)], seed + 1, 3, 20)
    clay(c, sheet, "#F4F1E8", seed + 1, gloss=0.05, tex=0.3, cast_alpha=0.45)
    clay(c, rod, "#6B4A30", seed)
    return sheet
