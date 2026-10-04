"""Character rigs, all drawn in code: Kai (front bust, back view, chibi), the client (shojo bust) and
the Vibe spirit. Bust rigs live in a local frame with the head centred on (0, 0), about 500 units tall."""
import math

import skia

from anime import (INK, cel, ellipse, fill, glow_circle, hrand, lin, mix, path, poly, rad, shade,
                   sparkle, stroke)

KAI = dict(
    skin="#FFE3D0", skin_sh="#F0B49C", blush="#FF8FA0",
    hair="#252C55", hair_sh="#141936", hair_hi="#5B7BE0",
    iris_top="#0A3B57", iris_bot="#4FE3E6", pupil="#06202E",
    top="#FF7A2F", top_sh="#D2501A", tee="#1E1E2C",
    hair_style="spiky",
)
CLIENT = dict(
    skin="#FFE8DA", skin_sh="#F3BCA8", blush="#FF7FA2",
    hair="#E3779F", hair_sh="#B44C78", hair_hi="#FFC2DA",
    iris_top="#4B1F78", iris_bot="#FF8FD0", pupil="#260B3D",
    top="#283A6E", top_sh="#1A274D", tee="#FFFFFF",
    hair_style="long",
)

LW = 6.0


# ----------------------------------------------------------------------------- hair
def spiky_back(lift=0.0, t=0.0, wind=0.0, seed=0):
    """Chunky clumps of spiky hair around the head. lift 0 = hanging, 1 = flaring up (power-up)."""
    p = skia.Path()
    n = 9
    a0, a1 = math.radians(158), math.radians(382)
    cx, cy = 0, -30
    da = (a1 - a0) / n

    def P(a, r):
        return cx + r * math.cos(a), cy + r * math.sin(a) * 1.04

    start = P(a0, 200)
    p.moveTo(150, 140)
    p.lineTo(-150, 140)
    p.lineTo(*start)
    for i in range(n):
        am = a0 + da * (i + 0.5)
        side = math.cos(am)
        up = -math.sin(am)                       # 1 at the top of the head
        rt = 300 + 45 * hrand(seed, i) + 70 * lift * (0.4 + up)
        droop = (0.5 * side) * (1 - lift) - 0.22 * side * lift
        sway = 0.05 * math.sin(t * 9 + i * 1.7) * (0.3 + wind + 1.5 * lift)
        ta = am + droop + sway
        tip = P(ta, rt)
        if lift > 0:
            tip = (tip[0], tip[1] - 60 * lift * max(0.0, up))
        b0 = P(a0 + da * i, 205)
        b1 = P(a0 + da * (i + 1), 205)
        # convex sides: control points bulge outward
        c0 = P(a0 + da * (i + 0.15) + droop * 0.5, (205 + rt) * 0.55 + 25)
        c1 = P(a0 + da * (i + 0.85) + droop * 0.4, (205 + rt) * 0.5 + 10)
        if i == 0:
            p.lineTo(*b0)
        p.quadTo(c0[0], c0[1], tip[0], tip[1])
        p.quadTo(c1[0], c1[1], b1[0], b1[1])
    p.close()
    return p


def spiky_bangs(lift=0.0, t=0.0):
    top = [(-188, -40), (-196, -150), (-140, -245), (-40, -285), (60, -282), (150, -240), (198, -140), (190, -40)]
    tips = [(190, -40), (178, 40), (150, -55), (122, 10), (95, -75), (55, 20), (30, -85), (-8, 35), (-35, -90),
            (-70, 10), (-98, -70), (-130, 25), (-152, -50), (-178, 55), (-188, -40)]
    out = []
    for i, (x, y) in enumerate(tips):
        k = 1 - lift * 0.55
        sway = 6 * math.sin(t * 8 + i)
        out.append((x + sway * (1 if i % 2 else 0), -90 + (y + 90) * k))
    return poly(top + out[1:-1])


def long_back(t=0.0):
    sw = 8 * math.sin(t * 2.2)
    pts = [(-215, -60), (-200, -200), (-110, -285), (0, -305), (110, -285), (200, -200), (215, -60),
           (240, 160), (270, 380), (300 + sw, 560), (180 + sw, 600), (150, 420), (120, 240),
           (-120, 240), (-150, 420), (-180 - sw, 600), (-300 - sw, 560), (-270, 380), (-240, 160)]
    return path(pts, True, tension=0.45)


def long_bangs(t=0.0):
    top = [(-200, -20), (-205, -160), (-130, -260), (0, -292), (130, -260), (205, -160), (200, -20)]
    # blunt, slightly jagged fringe + face-framing locks
    fringe = [(212, 40), (230, 230), (196, 300), (168, 120), (150, -30), (110, -55), (95, -30), (60, -60),
              (30, -35), (0, -62), (-30, -35), (-60, -60), (-95, -30), (-110, -55), (-150, -30), (-168, 120),
              (-196, 300), (-230, 230), (-212, 40)]
    return poly(top + fringe)


# ----------------------------------------------------------------------------- face parts
FACE = [(-168, -150), (-174, -30), (-166, 70), (-132, 150), (-70, 212), (-20, 242), (0, 250), (20, 242),
        (70, 212), (132, 150), (166, 70), (174, -30), (168, -150), (100, -225), (0, -245), (-100, -225)]


def face_path():
    return path(FACE, True, tension=0.42)


def eye(c, side, P, ex=0.0, open_=1.0, look=(0, 0), mood="normal", glow=0.0, t=0.0):
    """One anime eye centred on the local origin; side=+1 right (screen), -1 left (mirrored)."""
    c.save()
    c.scale(side, 1)
    if mood == "happy":
        c.drawPath(path([(-48, 20), (-10, -18), (40, -10), (58, 14)], False), stroke(INK, 11))
        c.restore()
        return
    if mood == "squeeze":   # >_<
        c.drawPath(poly([(-46, -30), (40, 5), (-46, 40)], False), stroke(INK, 11))
        c.restore()
        return
    if open_ < 0.12:
        c.drawPath(path([(-50, 12), (0, 22), (58, 6)], False), stroke(INK, 9))
        c.restore()
        return
    c.save()
    c.translate(0, 55)
    c.scale(1, open_)
    c.translate(0, -55)
    # determined: inner corner pulled down, lid flattened
    lid_in = -10 + (16 if mood == "determined" else 0)
    lid_mid = -60 + (18 if mood == "determined" else 0) + (26 if mood == "tired" else 0)
    upper = [(-54, lid_in), (-30, lid_mid + 6), (14, lid_mid), (52, lid_mid + 18), (66, -22)]
    white_pts = upper + [(52, 30), (25, 58), (-20, 60), (-50, 30)]
    white = path(white_pts, True, tension=0.5)
    c.drawPath(white, fill("#FFFFFF"))
    c.save()
    c.clipPath(white, doAntiAlias=True)
    sx, sy = 1.0, 1.0
    if mood == "sparkle":
        sx, sy = 1.12, 1.08
    if mood == "shock":
        sx, sy = 0.75, 0.75
    ix, iy = look[0] * side, 10 + look[1]
    irx, iry = 40 * sx, 54 * sy
    iris = ellipse(ix, iy, irx, iry)
    top, bot = P["iris_top"], P["iris_bot"]
    if glow > 0:
        top, bot = mix(top, "#B8320A", glow), mix(bot, "#FFF07A", glow)
    c.drawPath(iris, fill("#000000", shader=lin(0, iy - iry, 0, iy + iry, [top, mix(top, bot, 0.45), bot],
                                             [0, 0.45, 1])))
    if mood == "shock":
        c.drawCircle(ix, iy, 10, fill(P["pupil"]))
    else:
        c.drawPath(ellipse(ix, iy + 2, 17 * sx, 25 * sy), fill(P["pupil"]))
    c.drawPath(iris, stroke(mix(top, INK, 0.5), 4))
    # lid shadow across the top of the eye
    c.drawPath(path([(-60, -80), (70, -80), (70, lid_mid + 26), (14, lid_mid + 18), (-40, lid_mid + 26)], True),
               fill("#5560A0", 0.28))
    # highlights
    hl = 1.0 if mood != "tired" else 0.6
    c.drawPath(ellipse(ix - 14 * sx, iy - 20 * sy, 14 * sx * hl, 19 * sy * hl), fill("#FFFFFF"))
    c.drawCircle(ix + 17 * sx, iy + 26 * sy, 6.5 * sx, fill("#FFFFFF"))
    if mood == "sparkle":
        tw = 0.8 + 0.2 * math.sin(t * 14)
        sparkle(c, ix + 12, iy - 26, 20 * tw, "#FFFFFF", 1.0, glow=False)
        sparkle(c, ix - 18, iy + 22, 11 * tw, "#FFFFFF", 0.9, rot=0.4, glow=False)
        c.drawCircle(ix + 22, iy + 2, 5, fill("#FFFFFF"))
    if glow > 0:
        c.drawPath(iris, fill("#FFF3B0", 0.25 * glow, blend=skia.BlendMode.kScreen))
    c.restore()
    # lash line
    lash = path(upper, False, tension=0.5)
    c.drawPath(lash, stroke(INK, 11))
    c.drawPath(poly([(52, lid_mid + 14), (78, -36), (60, -12)]), fill(INK))   # outer flick
    c.drawPath(path([(-30, 58), (10, 62), (40, 46)], False), stroke(INK, 3.5))
    c.restore()
    if mood == "tired":
        c.drawPath(path([(-40, 78), (0, 90), (40, 80)], False), stroke("#8A6A9A", 4))
        c.drawPath(path([(-28, 92), (6, 100), (30, 94)], False), stroke("#8A6A9A", 3))
    c.restore()


def brow(c, side, mood="normal", lift=0.0):
    c.save()
    c.scale(side, 1)
    if mood in ("determined", "shout"):
        pts = [(-42, -62), (0, -84), (52, -104)]
    elif mood == "worried":
        pts = [(-42, -104), (0, -100), (50, -86)]
    else:
        pts = [(-42, -86), (0, -100), (50, -96)]
    pts = [(x, y - lift) for x, y in pts]
    c.drawPath(path(pts, False), stroke(INK, 10))
    c.restore()


def mouth(c, kind, P, t=0.0, amt=1.0):
    if kind == "smile":
        c.drawPath(path([(-30, 160), (0, 172), (32, 158)], False), stroke(INK, 5))
    elif kind == "flat":
        c.drawPath(path([(-18, 168), (18, 166)], False), stroke(INK, 5))
    elif kind == "wavy":
        c.drawPath(path([(-34, 168), (-17, 158), (0, 170), (17, 158), (34, 168)], False), stroke(INK, 5))
    elif kind == "o":
        p = ellipse(0, 172, 16, 20 * amt + 4)
        cel(c, p, "#6B1A2A", INK, 5)
    elif kind in ("shout", "grin"):
        depth = (95 if kind == "shout" else 55) * (0.4 + 0.6 * amt)
        wd = 62 if kind == "shout" else 55
        p = path([(-wd, 150), (0, 156), (wd, 150), (wd * 0.55, 150 + depth * 0.75), (0, 150 + depth),
                  (-wd * 0.55, 150 + depth * 0.75)], True, tension=0.45)
        c.drawPath(p, fill("#5C1426"))
        c.save()
        c.clipPath(p, doAntiAlias=True)
        c.drawPath(ellipse(0, 150 + depth + 10, wd * 0.6, depth * 0.45), fill("#FF7A8E"))
        c.drawRect(skia.Rect.MakeLTRB(-wd, 140, wd, 166), fill("#FFFFFF"))
        c.restore()
        c.drawPath(p, stroke(INK, 5))


def blush(c, P, a=1.0):
    for s in (-1, 1):
        c.drawPath(ellipse(s * 108, 112, 42, 18), fill(P["blush"], 0.45 * a, blur=6))
        for k in range(3):
            x = s * 108 + (k - 1) * 18
            c.drawLine(x - 8, 120, x + 4, 102, stroke(P["blush"], 3.5, 0.8 * a))


def sweat(c, x, y, s=1.0, a=1.0):
    p = path([(x, y - 34 * s), (x + 18 * s, y), (x + 14 * s, y + 18 * s), (x, y + 24 * s), (x - 14 * s, y + 18 * s),
              (x - 18 * s, y)], True)
    cel(c, p, "#BDEBFF", "#3A6E9E", 4, a)
    c.drawPath(ellipse(x - 6 * s, y + 6 * s, 4 * s, 8 * s), fill("#FFFFFF", a))


# ----------------------------------------------------------------------------- bodies
def hoodie(c, P, t=0.0, breathe=0.0, headphones=True):
    by = 4 * breathe
    body = path([(-90, 285 + by), (90, 285 + by), (210, 318 + by), (330, 380 + by), (395, 520), (420, 760),
                 (-420, 760), (-395, 520), (-330, 380 + by), (-210, 318 + by)], True, tension=0.4)
    # hood lump behind neck
    cel(c, path([(-215, 330), (-180, 255), (0, 232), (180, 255), (215, 330), (0, 360)], True), P["top_sh"], INK, LW)
    cel(c, body, P["top"], INK, LW)
    shade(c, body, poly([(150, 300), (460, 300), (460, 800), (230, 800), (250, 520)]), P["top_sh"])
    shade(c, body, poly([(-460, 600), (-300, 560), (-200, 700), (-460, 800)]), P["top_sh"], 0.6)
    # collar / tee
    cel(c, path([(-78, 292 + by), (78, 292 + by), (0, 420)], True, tension=0.3), P["tee"], INK, LW)
    c.drawPath(path([(-110, 300 + by), (-60, 370), (0, 430), (60, 370), (110, 300 + by)], False), stroke(INK, LW))
    # drawstrings
    for s in (-1, 1):
        x0 = s * 52
        sw = 4 * math.sin(t * 3 + s)
        c.drawPath(path([(x0, 380), (x0 + s * 6 + sw, 450), (x0 + s * 4 + sw, 525)], False), stroke("#FFFFFF", 7))
        c.drawPath(path([(x0, 380), (x0 + s * 6 + sw, 450), (x0 + s * 4 + sw, 525)], False),
                   stroke(INK, 2.5, 0.6))
        c.drawRoundRect(skia.Rect.MakeXYWH(x0 + s * 4 + sw - 6, 520, 12, 26), 4, 4, fill("#C9CCE0"))
    # arm creases
    for s in (-1, 1):
        c.drawPath(path([(s * 300, 470), (s * 315, 600), (s * 330, 740)], False), stroke(INK, 4, 0.7))
    if headphones:
        for s in (-1, 1):
            c.save()
            c.translate(s * 118, 300 + by)
            c.rotate(s * 18)
            cel(c, rrect_path(-46, -38, 92, 76, 30), "#2C2C3C", INK, LW)
            cel(c, rrect_path(-30, -24, 60, 48, 20), "#FF3D7F", INK, 3.5)
            c.drawPath(ellipse(-10, -10, 10, 6), fill("#FFFFFF", 0.5))
            c.restore()


def rrect_path(x, y, w, h, r):
    p = skia.Path()
    p.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r))
    return p


def blazer(c, P, t=0.0):
    body = path([(-90, 285), (90, 285), (210, 318), (330, 380), (395, 520), (420, 760),
                 (-420, 760), (-395, 520), (-330, 380), (-210, 318)], True, tension=0.4)
    cel(c, body, P["top"], INK, LW)
    shade(c, body, poly([(150, 300), (460, 300), (460, 800), (230, 800), (250, 520)]), P["top_sh"])
    cel(c, path([(-95, 290), (95, 290), (40, 520), (0, 560), (-40, 520)], True, tension=0.3), "#FFFFFF", INK, LW)
    for s in (-1, 1):   # lapels
        cel(c, poly([(s * 95, 290), (s * 150, 330), (s * 90, 420), (s * 40, 520)]), P["top_sh"], INK, 4.5)
    # ribbon tie
    cel(c, poly([(0, 330), (-58, 300), (-62, 360)]), "#FF5C8A", INK, 4)
    cel(c, poly([(0, 330), (58, 300), (62, 360)]), "#FF5C8A", INK, 4)
    c.drawCircle(0, 330, 13, fill("#E8436F"))


# ----------------------------------------------------------------------------- full bust
def bust(c, x, y, s, P=KAI, t=0.0, eyes="normal", open_=1.0, look=(0, 0), brows="normal", mouth_kind="smile",
         mouth_amt=1.0, blush_a=0.0, lift=0.0, glow=0.0, sweat_a=0.0, rot=0.0, tears=0.0, breathe=True):
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    c.rotate(rot)
    br = math.sin(t * 2.4) if breathe else 0.0
    long_hair = P["hair_style"] == "long"
    # back hair
    back = long_back(t) if long_hair else spiky_back(lift, t)
    cel(c, back, P["hair_sh"], INK, LW)
    # torso
    if long_hair:
        blazer(c, P, t)
    else:
        hoodie(c, P, t, br)
    # neck
    c.save()
    c.translate(0, -3 * br)
    neck = poly([(-60, 140), (60, 140), (66, 300), (0, 318), (-66, 300)])
    cel(c, neck, P["skin"], INK, LW)
    shade(c, neck, path([(-90, 120), (90, 120), (90, 230), (0, 280), (-90, 230)], True), P["skin_sh"])
    # ears
    for sd in (-1, 1):
        cel(c, ellipse(sd * 168, 20, 24, 44), P["skin"], INK, LW)
        c.drawPath(path([(sd * 165, 0), (sd * 176, 20), (sd * 168, 42)], False), stroke(P["skin_sh"], 5))
    face = face_path()
    cel(c, face, P["skin"], INK, LW)
    # cel shadow: right cheek + under bangs
    shade(c, face, path([(120, -200), (230, -200), (230, 260), (40, 260), (120, 160), (150, 40)], True),
          P["skin_sh"], 0.85)
    bangs = long_bangs(t) if long_hair else spiky_bangs(lift, t)
    c.save()
    c.clipPath(face, doAntiAlias=True)
    c.translate(10, 30)
    c.drawPath(bangs, fill(P["skin_sh"]))
    c.restore()
    if blush_a > 0:
        blush(c, P, blush_a)
    # nose
    c.drawPath(path([(8, 98), (2, 116), (-6, 118)], False), stroke(mix(P["skin_sh"], INK, 0.3), 4))
    # eyes
    for sd in (-1, 1):
        c.save()
        c.translate(sd * 86, 26)
        if glow > 0:
            glow_circle(c, 0, 10, 110, "#FFD34D", 0.35 * glow)
        eye(c, sd, P, open_=open_, look=look, mood=eyes, glow=glow, t=t)
        c.restore()
    mouth(c, mouth_kind, P, t, mouth_amt)
    # bangs + highlight ring
    cel(c, bangs, P["hair"], INK, LW)
    c.save()
    c.clipPath(bangs, doAntiAlias=True)
    shade(c, bangs, path([(60, -320), (260, -320), (260, 80), (90, 80)], True), P["hair_sh"], 0.7)
    hl = skia.Path()
    for i in range(9):
        u = -0.8 + 1.6 * i / 8
        ang = -math.pi / 2 + u * 0.95
        cxh, cyh = 205 * math.cos(ang), -30 + 205 * math.sin(ang) * 1.0
        w = 16
        hl.addPoly([(cxh - w * math.sin(ang) * 0, cyh - 22), (cxh + w, cyh), (cxh, cyh + 26), (cxh - w, cyh)], True)
    c.drawPath(hl, fill(P["hair_hi"], 0.9))
    c.restore()
    # strand lines
    for xx, yy in ((-110, -200), (-20, -230), (70, -215), (130, -170)):
        c.drawPath(path([(xx, yy), (xx + 12, yy + 60), (xx + 6, yy + 120)], False), stroke(P["hair_sh"], 4, 0.7))
    for sd in (-1, 1):
        c.save()
        c.translate(sd * 86, 26)
        brow(c, sd, brows, 6 * lift)
        c.restore()
    if long_hair:   # hair bow
        c.save()
        c.translate(150, -200)
        c.rotate(20)
        cel(c, path([(0, 0), (-60, -40), (-70, 20)], True, tension=0.3), "#FFFFFF", INK, 4.5)
        cel(c, path([(0, 0), (60, -40), (70, 20)], True, tension=0.3), "#FFFFFF", INK, 4.5)
        cel(c, ellipse(0, 0, 16, 16), "#FF8FB8", INK, 4)
        c.restore()
    if tears > 0:
        for sd in (-1, 1):
            L = 40 + 110 * tears
            pts_l, pts_r = [], []
            for k in range(9):
                v = k / 8
                x0 = sd * (62 + 45 * v + 6 * math.sin(t * 5 + v * 4))
                y0 = 82 + v * L
                w = 4 + 9 * math.sin(math.pi * min(1.0, v * 1.3)) * (1 - 0.5 * v)
                pts_l.append((x0 - w, y0))
                pts_r.append((x0 + w, y0))
            p = path(pts_l + list(reversed(pts_r)), True, tension=0.4)
            c.drawPath(p, fill("#D8F6FF", 0.85 * min(1.0, tears * 2)))
            c.drawPath(p, stroke("#5AA8E0", 2.5, 0.8 * min(1.0, tears * 2)))
            ph = (t * 1.3 + (0.5 if sd > 0 else 0)) % 1.0
            dy = 82 + L + ph * 120
            c.drawPath(path([(sd * 94, dy - 22), (sd * 94 + 10, dy), (sd * 94, dy + 10), (sd * 94 - 10, dy)], True),
                       fill("#D8F6FF", (1 - ph) * tears))
            sparkle(c, sd * 72, 92, 18 * tears, "#FFFFFF", tears, rot=t)
    if sweat_a > 0:
        sweat(c, 200, -60, 1.4, sweat_a)
    c.restore()
    c.restore()


# ----------------------------------------------------------------------------- back view
def back_view(c, x, y, s, rim="#6FE7FF", rim_a=1.0, t=0.0):
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    dark = "#0C1022"
    body = path([(-90, 285), (90, 285), (210, 318), (330, 380), (395, 520), (420, 760),
                 (-420, 760), (-395, 520), (-330, 380), (-210, 318)], True, tension=0.4)
    hood = path([(-190, 330), (-150, 230), (0, 200), (150, 230), (190, 330), (0, 420)], True)
    neck = poly([(-60, 140), (60, 140), (66, 300), (-66, 300)])
    hair = spiky_back(0.0, t * 0.5)
    head = ellipse(0, -10, 175, 230)
    for p in (body, neck, head, hair, hood):
        c.drawPath(p, stroke(rim, 16, 0.55 * rim_a, blur=10))
    nape = poly([(-185, 40), (-160, 190), (-120, 90), (-80, 215), (-40, 110), (0, 230), (40, 110), (80, 215),
                 (120, 90), (160, 190), (185, 40)])
    c.drawPath(nape, stroke(rim, 16, 0.4 * rim_a, blur=10))
    for p in (body, neck, head, hair, nape):
        c.drawPath(p, fill(dark))
    cel(c, hood, "#151A33", "#05070F", 4)
    c.drawPath(path([(-150, 240), (0, 300), (150, 240)], False), stroke("#2A3166", 5))
    # headphone band
    c.drawPath(path([(-170, 300), (-120, 220), (0, 196), (120, 220), (170, 300)], False), stroke("#22263D", 22))
    for sd in (-1, 1):
        c.drawPath(ellipse(sd * 175, 305, 38, 46), fill("#22263D"))
        c.drawPath(ellipse(sd * 175, 305, 38, 46), stroke(rim, 4, 0.8 * rim_a))
    # rim light edges (facing the monitor = top/right)
    for p in (hair, body, nape):
        c.save()
        c.clipPath(p, doAntiAlias=True)
        if p is hair:
            c.clipRect(skia.Rect.MakeLTRB(-600, -600, 600, 100))
        elif p is nape:
            c.clipRect(skia.Rect.MakeLTRB(-600, 60, 600, 900))
        c.drawPath(p, stroke(rim, 10, 0.9 * rim_a))
        c.restore()
    c.restore()


# ----------------------------------------------------------------------------- chibi
def chibi(c, x, y, s, t=0.0, mode="cry", P=KAI, squash=0.0):
    """Super-deformed Kai: 2.5 heads tall. mode: cry | soul | stare"""
    c.save()
    c.translate(x, y)
    c.scale(s * (1 + squash * 0.12), s * (1 - squash * 0.12))
    # tiny body
    cel(c, path([(-95, 150), (95, 150), (120, 330), (-120, 330)], True, tension=0.3), P["top"], INK, LW)
    shade(c, path([(-95, 150), (95, 150), (120, 330), (-120, 330)], True, tension=0.3),
          poly([(40, 140), (140, 140), (140, 340), (60, 340)]), P["top_sh"])
    for sd in (-1, 1):   # arms
        wob = 10 * math.sin(t * 30 + sd) if mode == "cry" else 0
        cel(c, ellipse(sd * 135, 250 + wob, 34, 52), P["top"], INK, LW)
        cel(c, ellipse(sd * 140, 300 + wob, 24, 22), P["skin"], INK, LW)
    # head
    cel(c, spiky_back(0.1, t, 0.3, seed=3), P["hair_sh"], INK, LW)
    head = path([(-220, -40), (-200, 90), (-110, 165), (0, 185), (110, 165), (200, 90), (220, -40),
                 (150, -170), (0, -210), (-150, -170)], True)
    cel(c, head, P["skin"], INK, LW)
    if mode == "soul":
        # blank white eyes, open jaw
        for sd in (-1, 1):
            cel(c, ellipse(sd * 85, 40, 34, 40), "#FFFFFF", INK, 7)
            c.drawCircle(sd * 85, 40, 5, fill(INK))
        p = path([(-36, 100), (36, 100), (28, 160), (0, 172), (-28, 160)], True)
        cel(c, p, "#5C1426", INK, 5)
        # gloom lines on the forehead
        for k in range(6):
            xx = -120 + k * 48
            c.drawLine(xx, -150, xx, -40, stroke("#5560A0", 7, 0.55))
    elif mode == "cry":
        for sd in (-1, 1):
            c.save()
            c.translate(sd * 85, 40)
            c.scale(sd, 1)
            c.drawPath(poly([(-34, -26), (30, 0), (-34, 26)], False), stroke(INK, 11))
            c.restore()
        wob = math.sin(t * 40)
        p = path([(-50, 105), (0, 98 + 4 * wob), (50, 105), (36, 150), (0, 165), (-36, 150)], True)
        cel(c, p, "#5C1426", INK, 5)
        c.drawPath(ellipse(0, 152, 26, 10), fill("#FF7A8E"))
    else:
        for sd in (-1, 1):
            cel(c, ellipse(sd * 85, 40, 46, 56), P["iris_top"], INK, 6)
            c.drawCircle(sd * 85 - 14, 18, 16, fill("#FFFFFF"))
            c.drawCircle(sd * 85 + 14, 62, 7, fill("#FFFFFF"))
        c.drawPath(path([(-20, 120), (0, 112), (20, 120)], False), stroke(INK, 5))
    # blush
    for sd in (-1, 1):
        c.drawPath(ellipse(sd * 140, 110, 34, 14), fill(P["blush"], 0.5, blur=5))
    bangs = poly([(-215, -30), (-200, -150), (-100, -225), (40, -235), (170, -170), (220, -40),
                  (200, 20), (160, -60), (120, 0), (80, -80), (40, -10), (0, -90), (-40, -15), (-80, -85),
                  (-120, 0), (-160, -60), (-200, 25)])
    cel(c, bangs, P["hair"], INK, LW)
    c.save()
    c.clipPath(bangs, doAntiAlias=True)
    c.drawPath(path([(-150, -130), (-80, -175), (0, -188), (80, -175), (150, -130)], False),
               stroke(P["hair_hi"], 16, 0.9, cap=skia.Paint.kButt_Cap))
    c.restore()
    c.restore()


def waterfall_tears(c, x, y, s, t, h=380):
    """Two comedic tear streams pouring out of chibi eyes."""
    for sd in (-1, 1):
        x0 = x + sd * 85 * s
        y0 = y + 50 * s
        pts_l, pts_r = [], []
        for k in range(14):
            v = k / 13
            yy = y0 + v * h
            off = sd * (30 + 60 * v) * s + 6 * math.sin(t * 25 + k)
            wdt = (14 + 22 * v) * s
            pts_l.append((x0 + off - wdt, yy))
            pts_r.append((x0 + off + wdt, yy))
        p = path(pts_l + list(reversed(pts_r)), True, tension=0.3)
        cel(c, p, "#9FE3FF", "#3A7FC4", 4, 0.92)
        for k in range(5):
            ph = (t * 3 + k / 5) % 1
            yy = y0 + ph * h
            c.drawLine(x0 + sd * (30 + 60 * ph) * s - 6, yy, x0 + sd * (30 + 60 * ph) * s - 6, yy + 30,
                       stroke("#FFFFFF", 4, 0.8))
        c.drawPath(ellipse(x0 + sd * 95 * s, y0 + h, 80 * s, 18 * s), fill("#9FE3FF", 0.8))


def soul(c, x, y, s, t, a=1.0):
    """The classic 'soul leaving the body' ghost."""
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    wob = math.sin(t * 6)
    pts = [(0, -90), (60, -70), (80, -10), (70, 50), (40 + 10 * wob, 100), (10, 150 + 10 * wob),
           (-20, 190), (-10, 130), (-50, 90), (-80, 30), (-75, -40), (-50, -78)]
    p = path(pts, True)
    c.drawPath(p, fill("#FFFFFF", 0.35 * a, blur=18))
    cel(c, p, "#F4FBFF", "#7A8CC4", 4, 0.92 * a)
    for sd in (-1, 1):
        c.drawPath(path([(sd * 34 - 12, -20), (sd * 34, -30), (sd * 34 + 12, -20)], False), stroke(INK, 5, a))
    c.drawPath(ellipse(0, 10, 9, 7), fill(INK, a))
    c.restore()


# ----------------------------------------------------------------------------- the vibe spirit
def spirit(c, x, y, s, t, a=1.0, glow=1.0, happy=True):
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    # trailing light ribbons
    for k in range(3):
        pts = []
        for i in range(14):
            v = i / 13
            pts.append((-40 * v * 9 + 0 * k, 30 + 22 * math.sin(t * 3 + v * 5 + k * 2) + v * (60 + 40 * k)))
        col = ["#9DF6FF", "#FFB3E6", "#FFF2A8"][k]
        c.drawPath(path(pts, False), stroke(col, 18 * (1 - 0.2 * k), 0.35 * a, blur=6))
        c.drawPath(path(pts, False), stroke("#FFFFFF", 4, 0.7 * a))
    glow_circle(c, 0, 0, 300, "#9DF6FF", 0.55 * a * glow)
    glow_circle(c, 0, 0, 180, "#FFFFFF", 0.6 * a * glow)
    # ears
    for sd in (-1, 1):
        ear = path([(sd * 40, -70), (sd * 92, -128), (sd * 95, -40)], True, tension=0.3)
        cel(c, ear, "#FFFFFF", "#7AB8FF", 5, a)
        c.drawPath(path([(sd * 60, -70), (sd * 86, -108), (sd * 86, -60)], True, tension=0.3), fill("#FFB3E6", a))
    body = path([(0, -95), (80, -60), (100, 20), (60, 85), (0, 100), (-60, 85), (-100, 20), (-80, -60)], True)
    c.drawPath(body, fill("#000000", a, shader=rad(-20, -30, 140, ["#FFFFFF", "#E6FDFF", "#A8EEFF"], [0, 0.6, 1])))
    c.drawPath(body, stroke("#7AB8FF", 5, a))
    # play-triangle forehead mark
    c.drawPath(poly([(-12, -62), (-12, -34), (14, -48)]), fill("#FF5FA8", a))
    # face
    if happy:
        for sd in (-1, 1):
            c.drawPath(path([(sd * 34 - 14, 6), (sd * 34, -8), (sd * 34 + 14, 6)], False), stroke(INK, 6, a))
    else:
        for sd in (-1, 1):
            c.drawPath(ellipse(sd * 34, 0, 9, 13), fill(INK, a))
            c.drawCircle(sd * 34 - 3, -5, 3.5, fill("#FFFFFF", a))
    c.drawPath(path([(-14, 26), (-7, 34), (0, 26), (7, 34), (14, 26)], False), stroke(INK, 4, a))   # ω mouth
    for sd in (-1, 1):
        c.drawPath(ellipse(sd * 62, 28, 18, 9), fill("#FF9FC8", 0.7 * a, blur=3))
    c.restore()
