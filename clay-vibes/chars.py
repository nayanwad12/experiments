"""Clay characters: Woolly the editor-sheep (front + back views) and a hen.

All characters are built around a ground point (x, y) at scale s. Pose is a dict, so each
scene can puppet them the way an animator nudges a plasticine figure between exposures.
"""

import math

import skia

from lib import blob, clay, clay_stroke, paint, smooth_path, union, star_path

WOOL = "#F4EFE3"
WOOL_SH = "#D9CFBC"
FACE = "#E7BF93"
FACE_DK = "#C99A6C"
EAR_IN = "#E99A92"
LEG = "#3A2E29"
INK = "#1E1612"


def _wool_body(rx, ry, seed, frizz, f, boil):
    parts = [blob(0, 0, rx * 0.86, ry * 0.86, seed, 0.03, boil, f)]
    n = 15
    for i in range(n):
        a = 2 * math.pi * i / n + 0.2
        r = (0.30 + 0.06 * math.sin(i * 2.3 + seed)) * min(rx, ry) * (1 + 0.15 * frizz * math.sin(i * 5.1))
        parts.append(blob(rx * 0.8 * math.cos(a), ry * 0.8 * math.sin(a), r, r * 0.95,
                          seed + i * 3, 0.06 + 0.06 * frizz, boil, f, n=22))
    return union(parts)


def _curls(c, rx, ry, seed, alpha=0.35):
    """Little pressed-in curls so the wool reads as wool, not a pillow."""
    import numpy as np
    rng = np.random.default_rng(abs(seed))
    for _ in range(26):
        a = rng.uniform(0, 2 * math.pi)
        d = math.sqrt(rng.uniform(0.05, 0.85))
        x, y = rx * d * math.cos(a), ry * d * math.sin(a)
        r = rng.uniform(8, 15)
        p = skia.Path()
        p.addArc(skia.Rect.MakeXYWH(x - r, y - r, 2 * r, 2 * r), rng.uniform(0, 360), 250)
        c.drawPath(p, paint(WOOL_SH, alpha, stroke=3.2))
        q = skia.Path(p)
        q.offset(-1.5, -1.5)
        c.drawPath(q, paint("#ffffff", alpha * 0.8, stroke=2))


def _limb(c, p0, p1, seed, width=24, hoof=True):
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    nx, ny = -(p1[1] - p0[1]) * 0.08, (p1[0] - p0[0]) * 0.08
    clay_stroke(c, [p0, (mx + nx, my + ny), p1], width, LEG, seed, cast=False, tex=0.35)
    if hoof:
        clay(c, blob(p1[0], p1[1], width * 0.62, width * 0.52, seed + 1, 0.06), INK, seed + 2, cast=False, gloss=0.3)


def _mouth(c, kind, y, f, seed):
    if kind == "smile":
        pts = [(-20, y - 4), (-8, y + 6), (8, y + 6), (20, y - 4)]
    elif kind == "grin":
        p = smooth_path([(-26, y - 6), (-12, y + 2), (12, y + 2), (26, y - 6), (14, y + 16), (0, y + 19), (-14, y + 16)])
        clay(c, p, "#5A1E1E", seed, cast=False, tex=0.3, gloss=0.2)
        c.save()
        c.clipPath(p, skia.ClipOp.kIntersect, True)
        c.drawOval(skia.Rect.MakeXYWH(-10, y + 8, 20, 14), paint("#E46A6A"))
        c.restore()
        return
    elif kind == "frown":
        pts = [(-18, y + 6), (-8, y - 2), (8, y - 2), (18, y + 6)]
    elif kind == "o":
        p = blob(0, y + 3, 9, 11, seed, 0.06, 0.6, f)
        clay(c, p, "#4A1818", seed, cast=False, tex=0.2)
        return
    elif kind == "wavy":
        pts = [(-20, y + 2), (-10, y - 3), (0, y + 3), (10, y - 3), (20, y + 2)]
    else:
        pts = [(-15, y + 1), (0, y + 2), (15, y)]
    clay_stroke(c, pts, 5, INK, seed, cast=False, tex=0.2)


def _eye(c, ex, ey, rx, ry, look, lid, seed, f):
    e = blob(ex, ey, rx, ry, seed, 0.03, 0.4, f)
    clay(c, e, "#FBFAF5", seed, cast=False, tex=0.25, gloss=0.35, ao=0.35)
    c.save()
    c.clipPath(e, skia.ClipOp.kIntersect, True)
    px, py = ex + look[0] * rx * 0.42, ey + look[1] * ry * 0.38 + ry * 0.08
    clay(c, blob(px, py, rx * 0.36, ry * 0.36, seed + 9, 0.04), INK, seed + 9, cast=False, tex=0.1, gloss=0.0, hi=0.2)
    c.drawCircle(px - rx * 0.12, py - ry * 0.14, rx * 0.11, paint("#ffffff", 0.95))
    if lid > 0.01:
        top = ey - ry - 4
        hgt = (2 * ry + 8) * lid
        lp = skia.Path()
        lp.addOval(skia.Rect.MakeXYWH(ex - rx - 6, top - (2 * ry + 8) + hgt, 2 * rx + 12, 2 * ry + 8))
        clay(c, lp, FACE, seed + 4, cast=False, tex=0.3, gloss=0.1, ao=0.3)
        c.drawArc(skia.Rect.MakeXYWH(ex - rx - 6, top - (2 * ry + 8) + hgt, 2 * rx + 12, 2 * ry + 8),
                  20, 140, False, paint(FACE_DK, 0.9, stroke=3))
    c.restore()


def sheep(c, x, y, s=1.0, f=0, seed=1, look=(0, 0), lid=0.0, wink=0.0, mouth="smile", lean=0.0,
          bob=0.0, head_tilt=0.0, hands=None, frizz=0.0, legs=True, back=False, ground_shadow=True,
          sweat=0.0, squash=(1.0, 1.0), brows=None, blush=0.0, boil=0.7):
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    if ground_shadow:
        c.drawOval(skia.Rect.MakeXYWH(-150, -18, 300, 36), paint("#1a1008", 0.32, blur=12))
    c.scale(squash[0], squash[1])
    c.rotate(lean)
    c.translate(0, -bob)

    # legs
    if legs:
        for lx in (-58, 58):
            _limb(c, (lx, -95), (lx * 1.05, -14), seed + lx, 28)

    # body
    c.save()
    c.translate(0, -165)
    body = _wool_body(150, 112, seed, frizz, f, boil)
    clay(c, body, WOOL, seed + 50, gloss=0.18, ao=0.55, tex=0.5)
    c.save()
    c.clipPath(body, skia.ClipOp.kIntersect, True)
    _curls(c, 150, 112, seed)
    c.restore()
    if back:
        clay(c, blob(0, 70, 26, 22, seed + 77, 0.12, boil, f), WOOL, seed + 77)   # tail puff
    c.restore()

    # head
    c.save()
    c.translate(0, -285)
    c.rotate(head_tilt)
    for sx in (-1, 1):
        ear = blob(sx * 78, -22, 40, 15, seed + 30 + sx, 0.05, boil, f, rot=sx * 0.32)
        clay(c, ear, FACE_DK if back else FACE, seed + 31 + sx, gloss=0.15)
        if not back:
            clay(c, blob(sx * 84, -22, 24, 7, seed + 33 + sx, 0.05, rot=sx * 0.32), EAR_IN, seed + 34, cast=False,
                 tex=0.3, gloss=0.1)
    face = blob(0, 0, 60, 80, seed + 40, 0.035, boil, f)
    clay(c, face, FACE_DK if back else FACE, seed + 41, gloss=0.25)
    tuft = union([blob(dx, -74 + abs(dx) * 0.25, 22, 19, seed + 60 + i, 0.08, boil, f, n=20)
                  for i, dx in enumerate((-30, -12, 8, 28, -2))])
    clay(c, tuft, WOOL, seed + 61, gloss=0.2)
    if not back:
        lidl = max(lid, wink)
        _eye(c, -25, -22, 25, 29, look, lidl, seed + 70, f)
        _eye(c, 25, -22, 25, 29, look, lid, seed + 72, f)
        if brows:
            for sx, ang in ((-1, brows), (1, -brows)):
                c.save()
                c.translate(sx * 27, -58)
                c.rotate(ang)
                clay_stroke(c, [(-16, 0), (16, 0)], 7, FACE_DK, seed + 80 + sx, cast=False, tex=0.2)
                c.restore()
        # muzzle
        clay(c, blob(0, 46, 36, 26, seed + 42, 0.05, boil * 0.5, f), "#EDCBA4", seed + 43, cast=False, gloss=0.2,
             ao=0.35)
        for sx in (-1, 1):
            c.drawOval(skia.Rect.MakeXYWH(sx * 12 - 5, 33, 10, 7), paint("#5B3A2A", 0.9))
        _mouth(c, mouth, 58, f, seed + 90)
        if blush > 0:
            for sx in (-1, 1):
                c.drawOval(skia.Rect.MakeXYWH(sx * 42 - 13, 18, 26, 14), paint("#F07F7F", 0.5 * blush, blur=4))
        if sweat > 0:
            sp = skia.Path()
            sx0, sy0 = 62, -48 + 30 * sweat
            sp.moveTo(sx0, sy0 - 16)
            sp.cubicTo(sx0 + 10, sy0 - 2, sx0 + 10, sy0 + 10, sx0, sy0 + 10)
            sp.cubicTo(sx0 - 10, sy0 + 10, sx0 - 10, sy0 - 2, sx0, sy0 - 16)
            clay(c, sp, "#9ED6F2", seed + 95, cast=False, gloss=0.6, tex=0.15)
    c.restore()

    # arms / hooves (front view)
    if hands:
        for sx, (hx, hy) in zip((-1, 1), hands):
            _limb(c, (sx * 104, -205), (hx, hy), seed + 100 + sx, 24)
    c.restore()


def sheep_back(c, x, y, s=1.0, f=0, seed=1, bob=0.0, lean=0.0, head_turn=0.0, **kw):
    """Back view; head_turn > 0 means the head swivels to show a cheeky profile (handled by front draw)."""
    sheep(c, x, y, s, f, seed, back=True, bob=bob, lean=lean, legs=False, **kw)


def hen(c, x, y, s=1.0, f=0, seed=5, sleep=0.0, peck=0.0, bob=0.0, flap=0.0, face=1):
    c.save()
    c.translate(x, y)
    c.scale(s * face, s)
    c.drawOval(skia.Rect.MakeXYWH(-55, -10, 110, 20), paint("#1a1008", 0.3, blur=8))
    for lx in (-14, 12):
        clay_stroke(c, [(lx, -40), (lx + 2, -4), (lx + 12, 0)], 7, "#E8A23A", seed + lx, cast=False, tex=0.2)
    c.translate(0, -bob)
    body = union([blob(0, -68, 58, 46, seed, 0.05, 0.6, f), blob(-46, -92, 22, 30, seed + 1, 0.08, 0.6, f, rot=-0.5)])
    clay(c, body, "#C7743C", seed + 2, gloss=0.2)
    wing = blob(4, -66, 32 + 6 * flap, 22 - 4 * flap, seed + 3, 0.08, 0.6, f, rot=-0.15 - 0.9 * flap)
    clay(c, wing, "#A85E2E", seed + 4, gloss=0.15, cast=False)
    c.save()
    c.translate(42, -108)
    c.rotate(peck * 55)
    clay(c, union([blob(0, 0, 26, 28, seed + 5, 0.05, 0.6, f)]), "#C7743C", seed + 6, gloss=0.22)
    comb = union([blob(-8 + 9 * i, -28 - 4 * (i == 1), 8, 10, seed + 10 + i, 0.08) for i in range(3)])
    clay(c, comb, "#D93A30", seed + 7, cast=False)
    clay(c, blob(4, 18, 6, 10, seed + 8, 0.08), "#D93A30", seed + 8, cast=False)
    beak = smooth_path([(20, -6), (40, 1), (20, 8)])
    clay(c, beak, "#F0A531", seed + 9, cast=False, tex=0.2)
    if sleep > 0.5:
        c.drawArc(skia.Rect.MakeXYWH(2, -8, 14, 10), 10, 160, False, paint(INK, 1, stroke=3))
    else:
        c.drawCircle(9, -4, 6, paint(INK))
        c.drawCircle(7, -6, 2, paint("#ffffff"))
    c.restore()
    c.restore()


def sparkle(c, x, y, r, rot=0.0, color="#FFE27A", alpha=1.0):
    p = star_path(x, y, r, 0.3, 4, rot)
    c.drawPath(p, paint(color, alpha * 0.5, blur=r * 0.5))
    clay(c, p, color, int(x + y) % 97, cast=False, tex=0.2, gloss=0.4, ao=0.2)
