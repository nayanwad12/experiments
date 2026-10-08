"""props: the objects of the collage. Greyscale drawings become halftone die-cut stickers (collage.halftone);
flat paper props are drawn live each frame so they can tear, flip and fly."""
import math

import skia

from collage import (INK, NEWS, RED, SLATE, WHITE, YEL, Cut, flat_cut, halftone, paper_path, torn_path, tape)
from kit import col, fill, font, hrand, lin_grad, rad_grad, stroke


def G(v):
    """grey level 0..255 -> hex"""
    v = int(max(0, min(255, v)))
    return f"#{v:02x}{v:02x}{v:02x}"


# ---------------------------------------------------------------- film strip (5 frames of a running figure)
FILM_W, FILM_H = 1300, 250


def _film(c, clip=None):
    if clip:
        c.clipRect(skia.Rect.MakeLTRB(*clip))
    c.drawRect(skia.Rect.MakeWH(FILM_W, FILM_H), fill(G(34)))
    for x in range(16, FILM_W, 44):
        for y in (14, FILM_H - 40):
            c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, 22, 26), 5, 5), fill(G(222)))
    fw, fh = 232, 136
    for i in range(5):
        x0, y0 = 32 + i * 250, 57
        c.drawRect(skia.Rect.MakeXYWH(x0, y0, fw, fh), lin_grad(0, y0, 0, y0 + fh, [G(235), G(150)]))
        c.drawRect(skia.Rect.MakeXYWH(x0, y0 + fh * 0.74, fw, fh * 0.26), fill(G(95)))
        # a runner, one pose per frame (a nod to the first motion studies)
        cx, gy = x0 + fw * (0.3 + 0.1 * i), y0 + fh * 0.74
        ph = i * 1.25
        c.drawCircle(cx + 6, gy - 92, 13, fill(G(25)))
        body = stroke(G(25), 13)
        c.drawLine(cx, gy - 76, cx - 4, gy - 40, body)
        for s in (1, -1):
            a = math.sin(ph) * 0.7 * s
            kx, ky = cx - 4 + math.sin(a) * 22, gy - 40 + math.cos(a) * 20
            c.drawLine(cx - 4, gy - 40, kx, ky, body)
            c.drawLine(kx, ky, kx + math.sin(a - 0.6 * s) * 20, gy - 2, body)
            c.drawLine(cx, gy - 70, cx + math.sin(-a) * 26, gy - 52, stroke(G(25), 10))
        c.drawCircle(x0 + fw * 0.82, y0 + 30, 16, fill(G(250)))


def film_cuts():
    whole = halftone(_film, FILM_W, FILM_H, seed=3)
    left = halftone(lambda c: _film(c, (0, 0, FILM_W / 2, FILM_H)), FILM_W, FILM_H, seed=4)
    right = halftone(lambda c: _film(c, (FILM_W / 2, 0, FILM_W, FILM_H)), FILM_W, FILM_H, seed=5)
    return whole, left, right


# ---------------------------------------------------------------- scissors (two blades, shared pivot)
SC_W, SC_H, SC_PX, SC_PY = 620, 280, 360, 140


def _blade(c, flip):
    c.save()
    if flip:
        c.translate(0, SC_H)
        c.scale(1, -1)
    ring = skia.Path()
    ring.addOval(skia.Rect.MakeXYWH(26, 28, 170, 112))
    ring.addOval(skia.Rect.MakeXYWH(58, 54, 106, 60))
    ring.setFillType(skia.PathFillType.kEvenOdd)
    c.drawPath(ring, lin_grad(0, 28, 0, 140, [G(70), G(20)]))
    arm = skia.Path()
    arm.moveTo(176, 62)
    arm.quadTo(270, 96, SC_PX, SC_PY - 16)
    arm.lineTo(SC_PX, SC_PY + 8)
    arm.quadTo(262, 126, 168, 116)
    arm.close()
    c.drawPath(arm, lin_grad(0, 60, 0, 130, [G(60), G(25)]))
    bl = skia.Path()
    bl.moveTo(SC_PX - 30, SC_PY - 20)
    bl.lineTo(SC_W - 4, SC_PY - 6)
    bl.lineTo(SC_PX - 10, SC_PY + 16)
    bl.close()
    c.drawPath(bl, lin_grad(0, SC_PY - 20, 0, SC_PY + 16, [G(250), G(185), G(120)]))
    c.drawLine(SC_PX - 20, SC_PY - 2, SC_W - 10, SC_PY - 5, stroke(G(255), 3))
    c.restore()
    if not flip:
        c.drawCircle(SC_PX, SC_PY, 15, rad_grad(SC_PX - 4, SC_PY - 4, 16, [G(230), G(60)]))
        c.drawLine(SC_PX - 8, SC_PY, SC_PX + 8, SC_PY, stroke(G(30), 3))


def scissor_cuts():
    return (halftone(lambda c: _blade(c, False), SC_W, SC_H, seed=6, border=11),
            halftone(lambda c: _blade(c, True), SC_W, SC_H, seed=7, border=11))


# ---------------------------------------------------------------- clock
def _clock(c, d=560):
    r = d / 2
    c.drawCircle(r, r, r, rad_grad(r * 0.7, r * 0.6, r * 1.3, [G(120), G(30)]))
    c.drawCircle(r, r, r * 0.86, rad_grad(r * 0.8, r * 0.7, r, [G(250), G(205)]))
    for i in range(60):
        a = i / 60 * 2 * math.pi
        l = 0.12 if i % 5 == 0 else 0.05
        c.drawLine(r + math.cos(a) * r * 0.8, r + math.sin(a) * r * 0.8, r + math.cos(a) * r * (0.8 - l),
                   r + math.sin(a) * r * (0.8 - l), stroke(G(30), 7 if i % 5 == 0 else 3))
    f = font("serif", 76)
    for n, a in ((12, -90), (3, 0), (6, 90), (9, 180)):
        s = str(n)
        x = r + math.cos(math.radians(a)) * r * 0.55 - f.measureText(s) / 2
        y = r + math.sin(math.radians(a)) * r * 0.55 + 26
        c.drawString(s, x, y, f, fill(G(25)))


def clock_cut():
    return halftone(_clock, 560, 560, seed=8, cell=7.5)


def clock_hands(c, cx, cy, t, sc=1.0):
    for ln, w, speed in ((150, 16, 0.6), (215, 9, 3.2)):
        a = t * speed * 2 * math.pi - math.pi / 2
        ex, ey = cx + math.cos(a) * ln * sc, cy + math.sin(a) * ln * sc
        c.drawLine(cx + 4, cy + 7, ex + 4, ey + 7, stroke("#000000", w, 0.25, blur=4))
        c.drawLine(cx, cy, ex, ey, stroke(INK, w))
    c.drawCircle(cx, cy, 16 * sc, fill(RED))


# ---------------------------------------------------------------- clip card (a video frame)
def _clip(c, w=520, h=300):
    c.drawRect(skia.Rect.MakeWH(w, h), lin_grad(0, 0, 0, h, [G(240), G(160)]))
    c.drawCircle(w * 0.72, h * 0.32, 44, fill(G(252)))
    m = skia.Path()
    m.moveTo(0, h * 0.78)
    for i, (x, y) in enumerate([(0.18, 0.42), (0.34, 0.66), (0.52, 0.36), (0.74, 0.7), (0.9, 0.5), (1, 0.62)]):
        m.lineTo(w * x, h * y)
    m.lineTo(w, h)
    m.lineTo(0, h)
    m.close()
    c.drawPath(m, lin_grad(0, h * 0.35, 0, h, [G(110), G(40)]))
    c.drawCircle(w / 2, h / 2, 52, fill(G(250)))
    p = skia.Path()
    p.moveTo(w / 2 - 16, h / 2 - 26)
    p.lineTo(w / 2 + 28, h / 2)
    p.lineTo(w / 2 - 16, h / 2 + 26)
    p.close()
    c.drawPath(p, fill(G(20)))


def clip_cut():
    return halftone(_clip, 520, 300, seed=9)


# ---------------------------------------------------------------- clapperboard (body + hinged top bar)
CL_W, CL_H = 520, 330


def _slate(c):
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeWH(CL_W, CL_H), 14, 14), lin_grad(0, 0, 0, CL_H, [G(55), G(20)]))
    for y in (110, 200):
        c.drawLine(24, y, CL_W - 24, y, stroke(G(200), 3))
    c.drawLine(CL_W / 2, 110, CL_W / 2, 200, stroke(G(200), 3))
    f, f2 = font("monob", 34), font("black", 58)
    c.drawString("VIBE EDITING", 30, 78, f2, fill(G(235)))
    c.drawString("SCENE 07", 34, 168, f, fill(G(225)))
    c.drawString("TAKE 1", CL_W / 2 + 22, 168, f, fill(G(225)))
    c.drawString("DIR: YOU", 34, 262, f, fill(G(225)))


def _clap_bar(c):
    c.drawRect(skia.Rect.MakeWH(CL_W, 70), fill(G(25)))
    for i in range(7):
        p = skia.Path()
        x = i * 82 - 10
        p.moveTo(x, 0)
        p.lineTo(x + 44, 0)
        p.lineTo(x + 14, 70)
        p.lineTo(x - 30, 70)
        p.close()
        c.save()
        c.clipRect(skia.Rect.MakeWH(CL_W, 70))
        c.drawPath(p, fill(G(240)))
        c.restore()


def clapper_cuts():
    return halftone(_slate, CL_W, CL_H, seed=10), halftone(_clap_bar, CL_W, 70, seed=11, border=9)


# ---------------------------------------------------------------- flat props (drawn live)
def cursor(c, x, y, sc=1.0, rot=0.0, down=False):
    pts = [(0, 0), (0, 62), (15, 48), (26, 74), (37, 69), (26, 44), (46, 44)]
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    p.close()
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    s = sc * (0.9 if down else 1.0)
    c.scale(s * 1.6, s * 1.6)
    paper_path(c, p, WHITE, 1, (3, 5, 3, 0.3))
    c.drawPath(p, stroke(INK, 3.2))
    c.restore()


def diamond(c, x, y, s, rot=0.0, color=YEL, a=1.0):
    p = skia.Path()
    p.moveTo(0, -s)
    p.lineTo(s * 0.8, 0)
    p.lineTo(0, s)
    p.lineTo(-s * 0.8, 0)
    p.close()
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    paper_path(c, p, color, a, (3, 5, 3, 0.25))
    c.drawPath(p, stroke(INK, max(2.0, s * 0.09), a))
    c.restore()


def timeline(c, cx, cy, w=900, h=400, seed=2, playhead=0.35, clip_path=None):
    """an editing timeline cut from dark paper: ruler, three tracks of clips, red playhead."""
    c.save()
    if clip_path is not None:
        c.clipPath(clip_path, doAntiAlias=True)
    x0, y0 = cx - w / 2, cy - h / 2
    paper_path(c, torn_path(x0, y0, x0 + w, y0 + h, seed, amp=4, step=16), SLATE)
    f = font("monob", 24)
    c.drawString("TIMELINE   00:01:00:00", x0 + 28, y0 + 44, f, fill("#BDB8AD"))
    for i in range(31):
        x = x0 + 28 + i * (w - 56) / 30
        c.drawLine(x, y0 + 62, x, y0 + (80 if i % 5 == 0 else 72), stroke("#8C877D", 2))
    cols = [NEWS, YEL, WHITE, "#BFB9AD", YEL]
    for tr in range(3):
        ty = y0 + 100 + tr * 92
        x = x0 + 28
        k = 0
        while x < x0 + w - 40:
            cw = 70 + hrand(seed, tr, k) * 150
            cw = min(cw, x0 + w - 28 - x)
            colr = cols[int(hrand(seed, tr, k, 3) * len(cols))]
            c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, ty, cw - 6, 70), 6, 6), fill(colr))
            for j in range(int(cw // 26)):
                c.drawLine(x + 10 + j * 26, ty + 14, x + 10 + j * 26, ty + 56, stroke(INK, 2, 0.18))
            x += cw
            k += 1
    px = x0 + 28 + (w - 56) * playhead
    c.drawLine(px, y0 + 56, px, y0 + h - 18, stroke(RED, 5))
    c.drawCircle(px, y0 + 58, 10, fill(RED))
    c.restore()


def polaroid(c, kind, cx, cy, rot, sc, t, seed, label):
    """instant photo with a tiny collage scene inside; kind in captions / motion / animation / ads."""
    w, h = 380, 430
    c.save()
    c.translate(cx, cy)
    c.rotate(rot)
    c.scale(sc, sc)
    paper_path(c, torn_path(-w / 2, -h / 2, w / 2, h / 2, seed, amp=1.2, step=30), WHITE, 1, (6, 10, 9, 0.3))
    iw, ih = w - 40, 300
    ix, iy = -iw / 2, -h / 2 + 20
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(ix, iy, iw, ih))
    c.drawRect(skia.Rect.MakeXYWH(ix, iy, iw, ih), fill(SLATE if kind in ("captions", "motion") else NEWS))
    k = (t * 12 // 1) / 12
    if kind == "captions":
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-70, iy + 22, 140, 256), 18, 18), fill("#4A4844"))
        c.drawCircle(0, iy + 110, 34, fill("#8A857B"))
        c.drawRect(skia.Rect.MakeXYWH(-52, iy + 190, 104, 26), fill(WHITE))
        c.drawRect(skia.Rect.MakeXYWH(-52 + 104 * ((k * 2) % 1) * 0.6, iy + 190, 40, 26), fill(YEL))
    elif kind == "motion":
        f = font("anton", 64)
        for i, wd in enumerate(("MAKE", "IT", "MOVE")):
            off = math.sin(k * 6 + i) * 30
            c.drawString(wd, -f.measureText(wd) / 2 + off, iy + 92 + i * 80, f, fill(YEL if i == 1 else WHITE))
        for i in range(4):
            c.drawLine(ix + 20, iy + 60 + i * 60, ix + 80, iy + 60 + i * 60, stroke(WHITE, 3, 0.5))
    elif kind == "animation":
        for i in range(6):
            x = ix + 50 + i * 52
            y = iy + 240 - abs(math.sin(i * 0.9 + 0.3)) * 170
            c.drawCircle(x, y, 22, fill(RED, 0.25 + 0.15 * i))
        bx = ix + 50 + (k * 3 % 1) * 260
        c.drawCircle(bx, iy + 240 - abs(math.sin((k * 3 % 1) * 4.5 + 0.3)) * 170, 26, fill(RED))
        c.drawLine(ix, iy + 268, ix + iw, iy + 268, stroke(INK, 4))
    elif kind == "ads":
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-46, iy + 80, 92, 190), 22, 22), fill(SLATE))
        c.drawRect(skia.Rect.MakeXYWH(-24, iy + 50, 48, 36), fill(SLATE))
        c.drawRect(skia.Rect.MakeXYWH(-46, iy + 140, 92, 60), fill(YEL))
        burst = skia.Path()
        for i in range(24):
            r = 70 if i % 2 == 0 else 50
            a = i / 24 * 2 * math.pi + k
            (burst.lineTo if i else burst.moveTo)(ix + 270 + math.cos(a) * r, iy + 80 + math.sin(a) * r)
        burst.close()
        c.drawPath(burst, fill(RED))
        f = font("black", 32)
        c.drawString("SALE", ix + 270 - f.measureText("SALE") / 2, iy + 92, f, fill(WHITE))
    c.restore()
    f = font("caveat", 56)
    c.drawString(label, -f.measureText(label) / 2, h / 2 - 34, f, fill(INK))
    c.restore()
    tape(c, cx + math.sin(math.radians(rot)) * 200, cy - math.cos(math.radians(rot)) * 215 * sc, 150, 44,
         rot + (hrand(seed) - 0.5) * 16, seed)


def sparkle(c, x, y, r, rot=0.0, color=YEL, a=1.0):
    p = skia.Path()
    for i in range(8):
        rr = r if i % 2 == 0 else r * 0.32
        ang = i / 8 * 2 * math.pi + rot
        (p.lineTo if i else p.moveTo)(x + math.cos(ang) * rr, y + math.sin(ang) * rr)
    p.close()
    paper_path(c, p, color, a, (3, 5, 3, 0.22))
    c.drawPath(p, stroke(INK, 2.5, a))


__all__ = ["film_cuts", "scissor_cuts", "clock_cut", "clock_hands", "clip_cut", "clapper_cuts", "cursor", "diamond",
           "timeline", "polaroid", "sparkle", "FILM_W", "FILM_H", "SC_PX", "SC_PY", "CL_W", "CL_H", "Cut", "col", "flat_cut"]
