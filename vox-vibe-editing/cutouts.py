"""Archival photo cutouts, drawn as greyscale 'photos' and printed through design.cutout() as halftone
newsprint with rough white paper borders. Built once, lazily, then reused as sprites."""

import math
from functools import lru_cache

import skia

from design import Sprite, gpaint, gray, lin_grad, rad_grad


def _rr(c, x, y, w, h, r, p):
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), p)


def _stroke(w, col):
    return skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=w, Color=col,
                      StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join)


# ---------------------------------------------------------------- film strip (the through-line object)
def _runner(c, cx, base, s, ph):
    """Muybridge-style running figure, phase ph in [0,1)."""
    a = ph * math.tau
    hip = (cx, base - 0.55 * s)
    sh = (cx + 0.06 * s, base - 0.98 * s)
    p = _stroke(0.11 * s, gray(0.12))
    c.drawLine(*hip, *sh, p)
    c.drawCircle(sh[0] + 0.05 * s, sh[1] - 0.17 * s, 0.1 * s, gpaint(color=gray(0.12)))
    for side in (0, math.pi):
        th = 0.75 * math.sin(a + side)
        knee = (hip[0] + 0.3 * s * math.sin(th), hip[1] + 0.3 * s * math.cos(th))
        sh2 = th - 0.6 - 0.5 * math.cos(a + side)
        foot = (knee[0] + 0.3 * s * math.sin(sh2), knee[1] + 0.3 * s * math.cos(sh2))
        c.drawLine(*hip, *knee, p)
        c.drawLine(*knee, *foot, p)
        ar = -0.8 * math.sin(a + side)
        el = (sh[0] + 0.24 * s * math.sin(ar), sh[1] + 0.24 * s * math.cos(ar))
        hand = (el[0] + 0.22 * s * math.sin(ar + 1.3), el[1] - 0.22 * s * math.cos(ar + 1.3) * -1)
        c.drawLine(*sh, *el, p)
        c.drawLine(*el, *hand, p)


def _film_draw(n, fw, fh, kind):
    def draw(c, w, h):
        m = 46
        _rr(c, 0, 0, w, h, 6, gpaint(color=gray(0.10)))
        for i in range(int(w / 34)):   # sprocket holes
            for y in (12, h - 12 - 20):
                _rr(c, 10 + i * 34, y, 18, 20, 4, gpaint(color=gray(0.86)))
        for i in range(n):
            x = 14 + i * (fw + 14)
            c.save()
            c.clipRect(skia.Rect.MakeXYWH(x, m, fw, fh))
            c.drawRect(skia.Rect.MakeXYWH(x, m, fw, fh),
                       gpaint(lin_grad(0, m, 0, m + fh, [(235, 235, 235, 255), (170, 170, 170, 255)])))
            c.drawRect(skia.Rect.MakeXYWH(x, m + fh * 0.78, fw, fh), gpaint(color=gray(0.52)))
            if kind == "runner":
                _runner(c, x + fw * 0.5, m + fh * 0.84, fh * 0.62, (i * 0.13) % 1)
            else:  # blank-ish frames with a soft shape
                c.drawCircle(x + fw * 0.5, m + fh * 0.48, fh * 0.26, gpaint(color=gray(0.35 + 0.1 * (i % 3))))
            c.restore()
    return draw


@lru_cache(None)
def film_strip(n=8, fw=190, fh=142, kind="runner", seed=1):
    w = 14 + n * (fw + 14)
    h = fh + 92
    return Sprite(_film_draw(n, fw, fh, kind), w, h, seed=seed, border=12)


# ---------------------------------------------------------------- scissors (two halves, pivot at anchor)
def _blade_draw(flip):
    def draw(c, w, h):
        py = h / 2
        c.save()
        if flip:
            c.translate(0, h)
            c.scale(1, -1)
        px = 250
        blade = skia.Path()
        blade.moveTo(px - 10, py - 4)
        blade.cubicTo(px + 160, py - 30, px + 330, py - 22, px + 430, py - 2)
        blade.lineTo(px + 430, py + 2)
        blade.cubicTo(px + 300, py + 8, px + 150, py + 14, px - 10, py + 16)
        blade.close()
        c.drawPath(blade, gpaint(lin_grad(0, py - 28, 0, py + 16,
                                          [(250, 250, 250, 255), (140, 140, 140, 255), (215, 215, 215, 255)])))
        c.drawPath(blade, _stroke(2.5, gray(0.25)))
        # shank + finger ring
        shank = skia.Path()
        shank.moveTo(px + 10, py - 2)
        shank.cubicTo(px - 60, py + 6, px - 100, py + 30, px - 135, py + 52)
        c.drawPath(shank, _stroke(26, gray(0.14)))
        c.drawOval(skia.Rect.MakeXYWH(px - 240, py + 30, 120, 88), _stroke(24, gray(0.13)))
        c.drawCircle(px, py + 4, 13, gpaint(color=gray(0.55)))
        c.drawCircle(px, py + 4, 13, _stroke(3, gray(0.15)))
        c.restore()
    return draw


@lru_cache(None)
def scissor_half(flip=False):
    w, h = 700, 290
    # anchor = pivot screw
    return Sprite(_blade_draw(flip), w, h, anchor=(250, h / 2 + (4 if not flip else -4)), seed=3 + flip, border=11)


# ---------------------------------------------------------------- 1924 Moviola-style editing machine
def _moviola_draw(c, w, h):
    dk, md, lt = gray(0.12), gray(0.32), gray(0.62)
    # base + column
    _rr(c, w * 0.18, h - 70, w * 0.64, 60, 10, gpaint(color=dk))
    _rr(c, w * 0.43, h * 0.42, w * 0.14, h * 0.55, 6, gpaint(lin_grad(w * 0.43, 0, w * 0.57, 0,
                                                                       [(60, 60, 60, 255), (150, 150, 150, 255), (40, 40, 40, 255)])))
    # upper body / head
    _rr(c, w * 0.25, h * 0.30, w * 0.50, h * 0.16, 10, gpaint(color=md))
    _rr(c, w * 0.30, h * 0.33, w * 0.40, h * 0.04, 4, gpaint(color=dk))
    # viewer hood
    hood = skia.Path()
    hood.moveTo(w * 0.40, h * 0.30)
    hood.lineTo(w * 0.36, h * 0.20)
    hood.lineTo(w * 0.62, h * 0.20)
    hood.lineTo(w * 0.60, h * 0.30)
    hood.close()
    c.drawPath(hood, gpaint(color=dk))
    _rr(c, w * 0.42, h * 0.215, w * 0.16, h * 0.06, 6, gpaint(rad_grad(w * 0.5, h * 0.245, w * 0.1,
                                                                     [(245, 245, 245, 255), (120, 120, 120, 255)])))
    # reels on arms
    for (rx, ry, r) in ((w * 0.22, h * 0.14, w * 0.17), (w * 0.78, h * 0.15, w * 0.15)):
        c.drawLine(rx, ry, w * 0.5, h * 0.32, _stroke(10, dk))
        c.drawCircle(rx, ry, r, gpaint(rad_grad(rx, ry, r, [(90, 90, 90, 255), (30, 30, 30, 255)])))
        c.drawCircle(rx, ry, r * 0.9, _stroke(4, md))
        for k in range(3):
            a = k * math.tau / 3 + 0.3
            c.drawCircle(rx + r * 0.52 * math.cos(a), ry + r * 0.52 * math.sin(a), r * 0.24, gpaint(color=lt))
        c.drawCircle(rx, ry, r * 0.12, gpaint(color=gray(0.85)))
    # film loop
    loop = skia.Path()
    loop.moveTo(w * 0.22, h * 0.14 + w * 0.17)
    loop.cubicTo(w * 0.28, h * 0.32, w * 0.35, h * 0.36, w * 0.45, h * 0.36)
    c.drawPath(loop, _stroke(9, gray(0.05)))
    # pedals
    _rr(c, w * 0.30, h - 95, w * 0.12, 26, 6, gpaint(color=md))
    _rr(c, w * 0.58, h - 95, w * 0.12, 26, 6, gpaint(color=md))


@lru_cache(None)
def moviola():
    return Sprite(_moviola_draw, 520, 760, seed=5, border=14)


# ---------------------------------------------------------------- 1989 workstation (screen drawn live)
SCREEN_1989 = (70, 62, 400, 280)  # x, y, w, h inside the sprite


def _crt_draw(c, w, h):
    _rr(c, 10, 10, w - 20, 420, 26, gpaint(lin_grad(0, 10, 0, 430, [(230, 228, 220, 255), (170, 168, 160, 255)])))
    x, y, sw, sh = SCREEN_1989
    _rr(c, x - 18, y - 16, sw + 36, sh + 32, 18, gpaint(color=gray(0.45)))
    _rr(c, x, y, sw, sh, 14, gpaint(color=gray(0.08)))
    for i in range(6):
        c.drawLine(w - 120, 370 + i * 9, w - 40, 370 + i * 9, _stroke(3, gray(0.4)))
    _rr(c, 70, 440, w - 140, 26, 6, gpaint(color=gray(0.55)))
    _rr(c, 0, 470, w, 110, 14, gpaint(lin_grad(0, 470, 0, 580, [(215, 213, 205, 255), (150, 148, 140, 255)])))
    for r in range(3):
        for k in range(14):
            _rr(c, 22 + k * 37, 488 + r * 30, 30, 22, 4, gpaint(color=gray(0.78 - 0.04 * (k % 3))))


@lru_cache(None)
def crt():
    return Sprite(_crt_draw, 540, 590, seed=6, border=13)


# ---------------------------------------------------------------- laptop (screen drawn live)
SCREEN_LAPTOP = (40, 36, 560, 352)


def _laptop_draw(c, w, h):
    _rr(c, 10, 10, w - 20, 410, 22, gpaint(color=gray(0.18)))
    x, y, sw, sh = SCREEN_LAPTOP
    _rr(c, x, y, sw, sh, 6, gpaint(color=gray(0.05)))
    base = skia.Path()
    base.moveTo(0, 420)
    base.lineTo(w, 420)
    base.lineTo(w - 30, 470)
    base.lineTo(30, 470)
    base.close()
    c.drawPath(base, gpaint(lin_grad(0, 420, 0, 470, [(200, 200, 200, 255), (110, 110, 110, 255)])))
    _rr(c, w / 2 - 70, 424, 140, 12, 6, gpaint(color=gray(0.4)))


@lru_cache(None)
def laptop():
    return Sprite(_laptop_draw, 640, 470, seed=8, border=13)


# ---------------------------------------------------------------- phone (screen drawn live)
SCREEN_PHONE = (28, 30, 464, 900)


def _phone_draw(c, w, h):
    _rr(c, 0, 0, w, h, 70, gpaint(lin_grad(0, 0, w, 0, [(70, 70, 70, 255), (25, 25, 25, 255), (60, 60, 60, 255)])))
    x, y, sw, sh = SCREEN_PHONE
    _rr(c, x, y, sw, sh, 52, gpaint(color=gray(0.04)))


@lru_cache(None)
def phone():
    return Sprite(_phone_draw, 520, 960, seed=9, border=14)


# ---------------------------------------------------------------- ornate portrait frame (inside drawn live)
FRAME_IN = (88, 92, 444, 556)


def _frame_draw(c, w, h):
    for i, (inset, g) in enumerate(((0, 0.22), (18, 0.55), (34, 0.3), (52, 0.7), (70, 0.4))):
        _rr(c, inset, inset, w - 2 * inset, h - 2 * inset, 28 - i * 4,
            gpaint(lin_grad(0, 0, w, h, [gray(g + 0.15), gray(g - 0.12), gray(g + 0.08)])))
    for (x, y) in ((40, 40), (w - 40, 40), (40, h - 40), (w - 40, h - 40)):
        c.drawCircle(x, y, 26, gpaint(rad_grad(x - 6, y - 6, 30, [(240, 240, 240, 255), (60, 60, 60, 255)])))
    x, y, fw, fh = FRAME_IN
    c.drawRect(skia.Rect.MakeXYWH(x, y, fw, fh), gpaint(color=gray(0.9)))


@lru_cache(None)
def portrait_frame():
    return Sprite(_frame_draw, 620, 740, seed=11, border=14)


# ---------------------------------------------------------------- film reel
def _reel_draw(c, w, h):
    r = w / 2
    c.drawCircle(r, r, r - 2, gpaint(rad_grad(r, r, r, [(120, 120, 120, 255), (35, 35, 35, 255)])))
    c.drawCircle(r, r, r * 0.92, _stroke(5, gray(0.55)))
    for k in range(5):
        a = k * math.tau / 5
        c.drawCircle(r + r * 0.55 * math.cos(a), r + r * 0.55 * math.sin(a), r * 0.2, gpaint(color=gray(0.86)))
    c.drawCircle(r, r, r * 0.13, gpaint(color=gray(0.9)))


@lru_cache(None)
def reel():
    return Sprite(_reel_draw, 260, 260, seed=12, border=12)
