"""The eight shots, one anime style each, plus subtitles, style tags and cut flashes."""
import math

import numpy as np
import skia

import chars
from anime import (H, INK, W, back_out, cel, clamp01, ease_in, ease_io, ease_out, elastic, ellipse, fill,
                   glow_circle, grad_rect, hrand, lin, mix, path, poly, rad, rrect, seg, shake, sparkle,
                   speed_lines_h, speed_lines_radial, star_pts, stroke, text, text_width, tone_fill, twos)
from timeline import IMPACT, SCENES, STYLE_TAG, VO_AT, scene_at, vo_end

DUR = 40.0


def V(k):
    return VO_AT[k]


# ============================================================================= shared scenery
_city = {}


def _city_layers():
    if _city:
        return _city
    rng = np.random.default_rng(7)
    layers = []
    spec = [  # (base y, min h, max h, body colour, window alpha, parallax)
        (760, 160, 420, "#1A1B4A", 0.35, 0.25),
        (820, 220, 560, "#121335", 0.6, 0.5),
        (900, 300, 700, "#0A0A22", 0.9, 1.0),
    ]
    for li, (base, hmin, hmax, colr, wa, par) in enumerate(spec):
        bodies, warm, cool, tops = skia.Path(), skia.Path(), skia.Path(), []
        x = -600
        while x < 2600:
            w = rng.uniform(90, 230)
            h = rng.uniform(hmin, hmax)
            y0 = base - h
            bodies.addRect(skia.Rect.MakeXYWH(x, y0, w - 8, h + 400))
            if rng.random() < 0.4:
                bodies.addRect(skia.Rect.MakeXYWH(x + w * 0.4, y0 - 60, 6, 60))
                tops.append((x + w * 0.4 + 3, y0 - 62, rng.random()))
            ws, hs = 7 + li * 3, 10 + li * 4
            for yy in np.arange(y0 + 14, base + 200, hs + 9):
                for xx in np.arange(x + 10, x + w - 20, ws + 8):
                    r = rng.random()
                    if r < 0.2:
                        warm.addRect(skia.Rect.MakeXYWH(xx, yy, ws, hs))
                    elif r < 0.28:
                        cool.addRect(skia.Rect.MakeXYWH(xx, yy, ws, hs))
            x += w
        signs = []
        if li == 2:
            for sx, txt, colr2 in ((140, "編集", "#FF3D9A"), (620, "バイブ", "#3DF2FF"), (1480, "24時", "#FFE45C"),
                                   (1900, "映像", "#A66BFF"), (1100, "カット", "#FF7A2F")):
                signs.append((sx, txt, colr2))
        layers.append(dict(bodies=bodies, warm=warm, cool=cool, color=colr, wa=wa, par=par, tops=tops, signs=signs,
                           base=base))
    _city["layers"] = layers
    rng2 = np.random.default_rng(3)
    _city["stars"] = [(rng2.uniform(0, W), rng2.uniform(0, 520), rng2.uniform(0.6, 2.2), rng2.random())
                      for _ in range(160)]
    return _city


def city_bg(c, t, pan=0.0, rain=1.0, clips=0.0, moon=True):
    """Night city in the rain, cinematic. pan shifts the parallax layers."""
    L = _city_layers()
    grad_rect(c, 0, 0, W, H, ["#070A24", "#1A1650", "#4B2477", "#B0457F"], [0, 0.45, 0.75, 1.0])
    for x, y, r, ph in L["stars"]:
        tw = 0.5 + 0.5 * math.sin(t * 3 + ph * 20)
        c.drawCircle(x, y, r, fill("#FFFFFF", 0.35 + 0.5 * tw))
    if moon:
        glow_circle(c, 1480, 230, 330, "#9CC9FF", 0.35)
        c.drawCircle(1480, 230, 120, fill("#000000", shader=rad(1450, 200, 140, ["#FFFFFF", "#DCEBFF"])))
        c.drawCircle(1520, 260, 22, fill("#C7D9F5", 0.6))
        c.drawCircle(1440, 190, 14, fill("#C7D9F5", 0.5))
    # horizon haze
    grad_rect(c, 0, 520, W, 400, ["#FF5FA800", "#FF5FA855"], vertical=True)
    for ly in L["layers"]:
        c.save()
        c.translate(-pan * ly["par"], 0)
        c.drawPath(ly["bodies"], fill(ly["color"]))
        c.drawPath(ly["warm"], fill("#FFD27A", ly["wa"]))
        c.drawPath(ly["cool"], fill("#7FE6FF", ly["wa"] * 0.8))
        for x, y, ph in ly["tops"]:
            if math.sin(t * 4 + ph * 30) > 0:
                glow_circle(c, x, y, 14, "#FF3355", 0.9)
        for sx, txt, sc in ly["signs"]:
            fl = 0.75 + 0.25 * math.sin(t * 23 + sx) if hrand(sx, math.floor(t * 8)) > 0.08 else 0.2
            n = len(txt)
            hh = 96 * n + 30
            sy = 420
            c.drawRoundRect(skia.Rect.MakeXYWH(sx - 55, sy, 110, hh), 12, 12, stroke(sc, 30, 0.25 * fl, blur=20))
            c.drawRoundRect(skia.Rect.MakeXYWH(sx - 55, sy, 110, hh), 12, 12, fill("#0B0820"))
            c.drawRoundRect(skia.Rect.MakeXYWH(sx - 55, sy, 110, hh), 12, 12, stroke(sc, 5, fl))
            for i, ch in enumerate(txt):
                text(c, ch, "dela", 76, sx, sy + 60 + i * 96, mix(sc, "#FFFFFF", 0.7), a=fl, outline=sc, ow=3)
        c.restore()
    # street glow
    grad_rect(c, 0, 880, W, 200, ["#FF4FA000", "#FF4FA066"])
    if clips > 0:
        falling_clips(c, t, clips)
    if rain > 0:
        rain_fx(c, t, rain)


def rain_fx(c, t, a=1.0, n=260, seed=5):
    p = skia.Path()
    for i in range(n):
        x = (hrand(seed, i) * (W + 300) - t * 260) % (W + 300) - 100
        y = (hrand(seed, i, "y") * (H + 200) + t * (1700 + 500 * hrand(seed, i, "v"))) % (H + 200) - 100
        Lr = 30 + 50 * hrand(seed, i, "l")
        p.moveTo(x, y)
        p.lineTo(x - Lr * 0.18, y + Lr)
    c.drawPath(p, stroke("#CFE3FF", 2.2, 0.35 * a))


CLIP_COLS = ["#FF5C8A", "#3DD6FF", "#FFC23D", "#8C6BFF", "#4CF2A0", "#FF7A2F"]


def clip_card(c, x, y, w, h, colr, rot=0.0, a=1.0, play=True):
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    r = skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h)
    c.drawRoundRect(r, 8, 8, fill("#000000", a, shader=lin(0, -h / 2, 0, h / 2, [mix(colr, "#FFFFFF", 0.35), colr])))
    # film perforations
    for k in range(int(w // 22)):
        xx = -w / 2 + 8 + k * 22
        c.drawRect(skia.Rect.MakeXYWH(xx, -h / 2 + 4, 10, 6), fill("#FFFFFF", 0.6 * a))
        c.drawRect(skia.Rect.MakeXYWH(xx, h / 2 - 10, 10, 6), fill("#FFFFFF", 0.6 * a))
    if play:
        s = min(w, h) * 0.18
        c.drawPath(poly([(-s * 0.6, -s), (-s * 0.6, s), (s, 0)]), fill("#FFFFFF", 0.9 * a))
    c.drawRoundRect(r, 8, 8, stroke(INK, 4, a))
    c.restore()


def falling_clips(c, t, a=1.0, n=22, seed=11):
    for i in range(n):
        sp = 120 + 160 * hrand(seed, i, "s")
        x = hrand(seed, i) * W + 40 * math.sin(t * 1.3 + i)
        y = (hrand(seed, i, "y") * (H + 300) + t * sp) % (H + 300) - 150
        w = 90 + 80 * hrand(seed, i, "w")
        clip_card(c, x, y, w, w * 0.6, CLIP_COLS[i % 6], rot=40 * math.sin(t * 0.8 + i * 2.1), a=a * 0.92)


def flash(c, a, colr="#FFFFFF"):
    if a > 0:
        c.drawRect(skia.Rect.MakeWH(W, H), fill(colr, clamp01(a)))


def vignette(c, a=0.55):
    c.drawRect(skia.Rect.MakeWH(W, H), fill("#000000", 1, shader=rad(W / 2, H / 2, 1250,
                                                                      [skia.ColorSetARGB(0, 0, 0, 0),
                                                                       skia.ColorSetARGB(0, 0, 0, 0),
                                                                       skia.ColorSetARGB(int(255 * a), 5, 3, 20)],
                                                                      [0, 0.55, 1])))


# ============================================================================= 1. city (cinematic)
def monitor_ui(c, x, y, w, h, t, chaos=1.0):
    """The editor's screen: a messy timeline."""
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(x, y, w, h))
    c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), fill("#0E1430"))
    # preview + bins
    c.drawRect(skia.Rect.MakeXYWH(x + w * 0.3, y + 20, w * 0.4, h * 0.38), fill("#000000", shader=lin(
        x, y, x + w, y + h * 0.4, ["#3B2A7A", "#FF5C8A"])))
    for k in range(12):
        bx = x + 18 + (k % 3) * (w * 0.085)
        by = y + 24 + (k // 3) * 48
        c.drawRect(skia.Rect.MakeXYWH(bx, by, w * 0.075, 38), fill(CLIP_COLS[k % 6], 0.8))
    # tracks
    ty = y + h * 0.5
    for tr in range(7):
        yy = ty + tr * (h * 0.068)
        c.drawRect(skia.Rect.MakeXYWH(x, yy, w, h * 0.06), fill("#18204A"))
        xx = x + 6
        k = 0
        while xx < x + w:
            bw = 20 + 110 * hrand(tr, k)
            jit = chaos * 6 * math.sin(t * 7 + tr * 3 + k)
            c.drawRect(skia.Rect.MakeXYWH(xx + jit, yy + 3, bw - 4, h * 0.06 - 6),
                       fill(CLIP_COLS[(tr + k) % 6], 0.85))
            xx += bw
            k += 1
    # warnings
    for k in range(4):
        if math.sin(t * 6 + k * 1.7) > 0.2:
            wx, wy = x + w * (0.15 + 0.22 * k), y + h * (0.55 + 0.1 * (k % 2))
            c.drawPath(poly([(wx, wy - 22), (wx + 24, wy + 18), (wx - 24, wy + 18)]), fill("#FF3355"))
            text(c, "!", "bang", 30, wx, wy + 2, "#FFFFFF")
    ph = x + (t * 0.37 % 1) * w
    c.drawRect(skia.Rect.MakeXYWH(ph, ty - 10, 3, h * 0.5), fill("#FF3355"))
    c.restore()


def scene_city(c, t, lt):
    if t < 3.2:
        # wide: drowning in footage
        k = lt / 3.2
        c.save()
        z = 1.08 - 0.06 * ease_io(k)
        c.translate(W / 2, H / 2)
        c.scale(z, z)
        c.translate(-W / 2, -H / 2 + 30 * ease_io(k))
        city_bg(c, t, pan=60 * k, rain=1.0, clips=clamp01(lt / 0.6))
        c.restore()
        vignette(c, 0.6)
    else:
        lt2 = t - 3.2
        z = 1.0 + 0.05 * ease_io(lt2 / 2.4)
        c.save()
        c.translate(W / 2, H * 0.55)
        c.scale(z, z)
        c.translate(-W / 2, -H * 0.55)
        grad_rect(c, 0, 0, W, H, ["#05061A", "#0D1234"])
        # window with the city
        wx, wy, ww, wh = 1220, 90, 620, 560
        c.save()
        c.clipRect(skia.Rect.MakeXYWH(wx, wy, ww, wh))
        c.translate(wx, wy)
        c.scale(0.42, 0.55)
        c.translate(-600, -60)
        city_bg(c, t, pan=0, rain=0.0, moon=True)
        c.restore()
        rain_fx(c, t, 0.6, n=60, seed=9)
        c.drawRect(skia.Rect.MakeXYWH(wx, wy, ww, wh), stroke("#1E2552", 18))
        c.drawLine(wx + ww / 2, wy, wx + ww / 2, wy + wh, stroke("#1E2552", 12))
        # monitor glow + monitor
        glow_circle(c, 760, 430, 800, "#3DA8FF", 0.35)
        mx, my, mw, mh = 300, 130, 920, 540
        c.drawRoundRect(skia.Rect.MakeXYWH(mx - 18, my - 18, mw + 36, mh + 36), 18, 18, fill("#0A0B14"))
        monitor_ui(c, mx, my, mw, mh, t)
        c.drawRect(skia.Rect.MakeXYWH(mx + mw / 2 - 40, my + mh + 18, 80, 90), fill("#0A0B14"))
        # desk
        grad_rect(c, 0, 760, W, 320, ["#1A1F45", "#07081A"])
        c.drawLine(0, 760, W, 760, stroke("#4FA8FF", 3, 0.6))
        # cans + clock
        for i, cx_ in enumerate((1330, 1395, 1460, 1370)):
            cy_ = 700 if i < 3 else 640
            c.drawRoundRect(skia.Rect.MakeXYWH(cx_ - 26, cy_, 52, 92), 10, 10,
                            fill("#000000", shader=lin(cx_ - 26, 0, cx_ + 26, 0, ["#2B3A8F", "#7FA6FF", "#2B3A8F"])))
            c.drawPath(poly([(cx_ + 6, cy_ + 22), (cx_ - 12, cy_ + 50), (cx_ + 1, cy_ + 50), (cx_ - 6, cy_ + 72),
                             (cx_ + 13, cy_ + 42), (cx_, cy_ + 42)]), fill("#FFE45C"))
        c.drawRoundRect(skia.Rect.MakeXYWH(120, 640, 210, 100), 14, 14, fill("#0A0B14"))
        text(c, "3:47", "orb", 60, 225, 690, "#FF3355", outline=None)
        text(c, "AM", "orb", 20, 300, 720, "#FF3355")
        chars.back_view(c, 780, 740, 0.7, rim="#7FD8FF", t=t)
        c.restore()
        vignette(c, 0.65)


# ============================================================================= 2. manga
PAPER = "#F6F2E8"


def gray_layer(c, contrast=1.15):
    m = []
    lw = (0.3, 0.59, 0.11)
    for _ in range(3):
        m += [lw[0] * contrast, lw[1] * contrast, lw[2] * contrast, 0, -0.08]
    m += [0, 0, 0, 1, 0]
    p = skia.Paint()
    p.setColorFilter(skia.ColorFilters.Matrix(m))
    c.saveLayer(None, p)


def panel_slam(t, t0):
    k = seg(t, t0, t0 + 0.22)
    return k, 1.12 - 0.12 * back_out(k, 1.4)


def manga_panel(c, pts, t, t0, draw_fn):
    k, s = panel_slam(t, t0)
    if k <= 0:
        return
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    pp = poly(pts)
    c.save()
    c.translate(cx, cy)
    c.scale(s, s)
    c.translate(-cx, -cy)
    # drop shadow + panel
    c.save()
    c.translate(10, 12)
    c.drawPath(pp, fill(INK, 0.25 * k))
    c.restore()
    c.save()
    c.clipPath(pp, doAntiAlias=True)
    c.drawPath(pp, fill("#FFFFFF"))
    draw_fn(c, t - t0, (min(xs), min(ys), max(xs), max(ys)))
    c.restore()
    c.drawPath(pp, stroke(INK, 9, cap=skia.Paint.kSquare_Cap))
    c.restore()


def sfx_text(c, s, x, y, size, rot, color="#FFFFFF", outline=INK, font_="dela", a=1.0, ow=10):
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    text(c, s, font_, size, 0, 0, color, outline=outline, ow=ow, a=a)
    c.restore()


def p1_deadline(c, lt, box):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    speed_lines_radial(c, cx - 120, cy, lt + 5, n=70, r0=160, color=INK, rmax=1200, wmax=10, seed=21)
    # calendar
    c.save()
    c.translate(cx - 150, cy + 10)
    c.rotate(-6)
    cel(c, rrect(-170, -150, 340, 300, 10), "#FFFFFF", INK, 7)
    c.drawRect(skia.Rect.MakeXYWH(-170, -150, 340, 70), fill(INK))
    text(c, "DEADLINE", "bang", 50, 0, -116, "#FFFFFF")
    for i in range(4):
        for j in range(5):
            xx, yy = -140 + j * 66, -50 + i * 50
            tone_fill(c, rrect(xx, yy, 46, 34, 4), 0.25 if (i + j) % 3 else 0.5, 7)
    # red circle on tomorrow (manga spot colour)
    k = ease_out(seg(lt, 0.25, 0.7))
    pth = skia.Path()
    pth.addArc(skia.Rect.MakeXYWH(-30, -2, 90, 70), -100, 340 * k)
    c.drawPath(pth, stroke("#E8203A", 11))
    c.restore()
    sfx_text(c, "TOMORROW!", cx + 210, cy - 60, 92, -8, "#FFFFFF", INK, "bang", ow=9)
    sfx_text(c, "ドクン", x1 - 200, y1 - 90, 70, 10, INK, "#FFFFFF", "dela", ow=6)


def p2_clips(c, lt, box):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    tone_fill(c, poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]), 0.18, 8)
    # monitor full of thumbnails, counting up
    n = int(1000 * ease_out(seg(lt, 0.0, 1.1)))
    mx, my, mw, mh = cx - 300, cy - 170, 600, 340
    cel(c, rrect(mx - 14, my - 14, mw + 28, mh + 28, 12), "#FFFFFF", INK, 7)
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(mx, my, mw, mh))
    cols, rows = 16, 9
    shown = min(cols * rows, int(n / 1000 * cols * rows * 1.3))
    for i in range(shown):
        xx = mx + (i % cols) * (mw / cols)
        yy = my + (i // cols) * (mh / rows)
        tone_fill(c, rrect(xx + 2, yy + 2, mw / cols - 4, mh / rows - 4, 2), [0.2, 0.45, 0.7][i % 3], 5)
    c.restore()
    # overflow cards bursting out of the panel
    for i in range(int(14 * seg(lt, 0.5, 1.4))):
        a = -2.6 + i * 0.37
        r = 330 + 140 * ease_out(seg(lt, 0.5 + i * 0.05, 0.9 + i * 0.05))
        c.save()
        c.translate(cx + r * math.cos(a), cy + r * math.sin(a) * 0.6)
        c.rotate(30 * math.sin(i * 2.3))
        cel(c, rrect(-40, -26, 80, 52, 6), "#FFFFFF", INK, 5)
        tone_fill(c, rrect(-40, -26, 80, 52, 6), 0.35, 5)
        c.drawPath(poly([(-8, -12), (-8, 12), (14, 0)]), fill(INK))
        c.restore()
    c.drawRect(skia.Rect.MakeXYWH(cx - 250, y1 - 118, 500, 92), fill(INK))
    text(c, f"CLIPS: {n:,}", "bang", 74, cx, y1 - 72, "#FFFFFF")


def p3_sleep(c, lt, box):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    tone_fill(c, poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]), 0.55, 9)
    # gloom lines
    for i in range(40):
        xx = x0 + i * 48 + 10
        c.drawLine(xx, y0, xx, y0 + 140 + 60 * hrand(i), stroke(INK, 6))
    z = 1 + 0.04 * lt
    gray_layer(c, 1.1)
    chars.bust(c, cx + 40, cy - 26 * 2.3 * z + 10, 2.3 * z, t=lt, eyes="tired", open_=0.85, brows="worried", mouth_kind="wavy",
               sweat_a=1.0, breathe=False)
    c.restore()
    sfx_text(c, "SLEEP: 0", x0 + 270, y1 - 80, 96, -6, "#FFFFFF", INK, "bang", ow=10)
    sh = 6 * math.sin(lt * 40)
    for i, ch in enumerate("ゴゴゴ"):
        sfx_text(c, ch, x1 - 230 + i * 70 + sh, y0 + 120 + i * 110, 110, 12, INK, "#FFFFFF", "dela", ow=7)


def scene_manga(c, t, lt):
    c.drawRect(skia.Rect.MakeWH(W, H), fill(PAPER))
    zoom = 1.0 + 0.025 * lt
    dx, dy = 0, 0
    for k in ("dead", "clips", "sleep"):
        sx, sy = shake(t, V(k) - 0.1, 14, 0.3)
        dx += sx
        dy += sy
    c.save()
    c.translate(W / 2 + dx, H / 2 + dy)
    c.scale(zoom, zoom)
    c.translate(-W / 2, -H / 2)
    manga_panel(c, [(50, 46), (1010, 46), (940, 500), (50, 500)], t, 5.6, p1_deadline)
    manga_panel(c, [(1040, 46), (1870, 46), (1870, 500), (970, 500)], t, V("clips") - 0.1, p2_clips)
    manga_panel(c, [(50, 530), (1870, 530), (1870, 1034), (50, 1034)], t, V("sleep") - 0.1, p3_sleep)
    c.restore()


# ============================================================================= 3. chibi
def scene_chibi(c, t, lt):
    # pastel polka + diagonal stripes
    grad_rect(c, 0, 0, W, H, ["#FFF1C9", "#FFD3E6"])
    c.save()
    c.rotate(-12)
    for i in range(-6, 30):
        c.drawRect(skia.Rect.MakeXYWH(-400 + i * 120 + (lt * 60) % 120, -400, 50, 2200), fill("#FFFFFF", 0.35))
    c.restore()
    for i in range(40):
        x = (i % 8) * 260 + (130 if (i // 8) % 2 else 0) + 20
        y = (i // 8) * 240 + 60
        c.drawCircle(x, y, 22, fill("#FF9FC8", 0.35))
    soul_t = V("chibi2") + 0.25
    souled = t >= soul_t
    # three-day counter: calendar pages tearing off
    day = 1 + min(2, int(seg(t, V("chibi1"), V("chibi1") + 1.9) * 3))
    cx0, cy0 = 1500, 300
    c.save()
    c.translate(cx0, cy0)
    c.rotate(6)
    cel(c, rrect(-150, -130, 300, 260, 16), "#FFFFFF", INK, 7)
    c.drawRect(skia.Rect.MakeXYWH(-150, -130, 300, 70), fill("#FF5C8A"))
    c.drawRoundRect(skia.Rect.MakeXYWH(-150, -130, 300, 260), 16, 16, stroke(INK, 7))
    text(c, "DAY", "bang", 46, 0, -96, "#FFFFFF")
    text(c, str(day), "bang", 150, 0, 40, INK)
    c.restore()
    # flying torn pages
    for d in (1, 2):
        tt = V("chibi1") + d * 0.63
        k = seg(t, tt, tt + 0.9)
        if 0 < k < 1:
            c.save()
            c.translate(cx0 + 400 * k, cy0 - 200 * k + 500 * k * k)
            c.rotate(200 * k)
            cel(c, rrect(-150, -60, 300, 190, 10), "#FFFFFF", INK, 6, 1 - k * 0.5)
            text(c, str(d), "bang", 120, 0, 40, INK, a=1 - k * 0.5)
            c.restore()
    # desk + laptop
    c.drawRoundRect(skia.Rect.MakeXYWH(260, 760, 900, 70), 20, 20, fill("#B7795A"))
    c.drawRoundRect(skia.Rect.MakeXYWH(260, 760, 900, 70), 20, 20, stroke(INK, 7))
    c.drawRect(skia.Rect.MakeXYWH(320, 830, 40, 260), fill("#8C5A40"))
    c.drawRect(skia.Rect.MakeXYWH(1060, 830, 40, 260), fill("#8C5A40"))
    # chibi bounce on twos
    tb = twos(t)
    if not souled:
        bounce = abs(math.sin(tb * 11)) * 18
        sq = 0.5 * math.sin(tb * 22)
        chars.chibi(c, 640, 470 - bounce, 0.95, tb, "cry", squash=sq)
        chars.waterfall_tears(c, 640, 470 - bounce, 0.95, tb, h=300)
    else:
        sk = shake(t, soul_t, 10, 0.25)
        chars.chibi(c, 640 + sk[0], 470, 0.95, tb, "soul")
        ks = seg(t, soul_t, soul_t + 1.4)
        chars.soul(c, 640 + 30 * math.sin(t * 3), 560 - 420 * ease_out(ks), 0.9 * (0.4 + 0.6 * ease_out(ks * 2)), t,
                   a=clamp01(ks * 4))
        if t > soul_t + 0.6:
            k2 = seg(t, soul_t + 0.6, soul_t + 0.8)
            sfx_text(c, "チーン", 1080, 330, 110 * back_out(k2), -8, "#FFFFFF", INK, "dela", ow=8)
    # laptop in front of the chibi
    c.save()
    c.translate(820, 760)
    c.drawPath(poly([(-150, 0), (150, 0), (120, -170), (-120, -170)]), fill("#C9CDE0"))
    c.drawPath(poly([(-150, 0), (150, 0), (120, -170), (-120, -170)]), stroke(INK, 6))
    c.drawCircle(0, -85, 18, fill("#FFFFFF"))
    c.restore()
    # popping task words (cut / drag / keyframe), looping until the soul leaves
    words = [("CUT!", 1180, 560, -10, "#FF5C8A"), ("DRAG!", 300, 330, 8, "#3DA8FF"), ("KEYFRAME!", 1360, 720, 6, "#8C6BFF")]
    if not souled:
        for i, (w_, x, y, r, colr) in enumerate(words):
            ph = (lt * 1.6 + i / 3) % 1
            k = back_out(seg(ph, 0, 0.25))
            a = 1 - seg(ph, 0.75, 1)
            c.save()
            c.translate(x, y)
            c.scale(k, k)
            sfx_text(c, w_, 0, 0, 84, r, colr, INK, "bang", a=a, ow=8)
            c.restore()


# ============================================================================= 4. spirit (fantasy)
def magic_circle(c, x, y, r, t, a=1.0, sy=1.0):
    c.save()
    c.translate(x, y)
    c.scale(1, sy)
    c.rotate(t * 25)
    for rr, w in ((r, 5), (r * 0.86, 3), (r * 0.62, 4), (r * 0.5, 2)):
        c.drawCircle(0, 0, rr, stroke("#FFFFFF", w, a))
        c.drawCircle(0, 0, rr, stroke("#9DF6FF", w * 4, a * 0.25, blur=8))
    c.drawPath(path(star_pts(0, 0, r * 0.62, r * 0.62, 3, 0), True, smooth=False), stroke("#FFFFFF", 3, a))
    c.drawPath(path(star_pts(0, 0, r * 0.62, r * 0.62, 3, math.pi / 3), True, smooth=False), stroke("#FFFFFF", 3, a))
    runes = "カットカラーテロップオンガクバイブ"
    for i, ch in enumerate(runes):
        ang = i / len(runes) * 2 * math.pi
        c.save()
        c.rotate(math.degrees(ang))
        text(c, ch, "dela", r * 0.11, 0, -r * 0.93, "#FFFFFF", a=a)
        c.restore()
    c.restore()


def clouds(c, t, layer_y, colr, a, speed, seed, scale=1.0):
    for i in range(6):
        x = (hrand(seed, i) * (W + 800) + t * speed) % (W + 800) - 400
        y = layer_y + 40 * hrand(seed, i, "y")
        s = scale * (0.8 + 0.5 * hrand(seed, i, "s"))
        for dx, dy, r in ((0, 0, 110), (110, -40, 130), (240, 0, 110), (120, 40, 120), (-90, 30, 80), (330, 30, 80)):
            c.drawCircle(x + dx * s, y + dy * s, r * s, fill(colr, a))


def prompt_bar(c, x, y, w, h, typed, t, a=1.0, glow=1.0):
    c.drawRoundRect(skia.Rect.MakeXYWH(x - 6, y - 6, w + 12, h + 12), h, h, stroke("#FF8FD0", 18, 0.4 * a * glow, blur=12))
    c.drawRoundRect(skia.Rect.MakeXYWH(x, y, w, h), h / 2, h / 2, fill("#FFFFFF", 0.92 * a))
    c.drawRoundRect(skia.Rect.MakeXYWH(x, y, w, h), h / 2, h / 2, stroke("#B57BFF", 4, a))
    sparkle(c, x + 50, y + h / 2, 20, "#B57BFF", a, glow=False)
    tw = text(c, typed, "pop", h * 0.42, x + 90, y + h / 2, "#3A2466", anchor="l", a=a)
    if math.sin(t * 12) > 0:
        c.drawRect(skia.Rect.MakeXYWH(x + 96 + tw, y + h * 0.25, 4, h * 0.5), fill("#3A2466", a))


def scene_spirit(c, t, lt):
    grad_rect(c, 0, 0, W, H, ["#8FB7FF", "#C9B6FF", "#FFC9E3", "#FFE6C4"], [0, 0.4, 0.75, 1])
    glow_circle(c, 1380, 380, 900, "#FFFFFF", 0.5)
    # god rays
    c.save()
    c.translate(1380, -100)
    for i in range(9):
        a = -60 + i * 15 + 4 * math.sin(lt * 0.8 + i)
        c.save()
        c.rotate(a)
        c.drawPath(poly([(-20, 0), (20, 0), (140, 1500), (-140, 1500)]), fill("#FFFFFF", 0.12))
        c.restore()
    c.restore()
    clouds(c, lt, 120, "#FFFFFF", 0.55, 25, 1, 0.9)
    clouds(c, lt, 860, "#FFFFFF", 0.85, 45, 2, 1.4)
    # drifting light motes
    for i in range(50):
        x = (hrand(i, "mx") * W + 30 * math.sin(lt + i)) % W
        y = (hrand(i, "my") * H - lt * (30 + 50 * hrand(i))) % H
        sparkle(c, x, y, 6 + 10 * hrand(i, "r"), "#FFFFFF", 0.4 + 0.5 * math.sin(lt * 3 + i) ** 2, glow=False)
    # spirit descends
    kd = ease_out(seg(lt, 0.0, 1.0))
    sx, sy = 1380, -200 + 640 * kd + 18 * math.sin(lt * 2.5)
    magic_circle(c, sx, sy, 360 * ease_out(seg(lt, 0.4, 1.2)), lt, 1.0)
    talking = V("spirit1") <= t <= vo_end("spirit1") or V("spirit2") <= t <= vo_end("spirit2")
    chars.spirit(c, sx, sy, 1.5, t, happy=not talking or math.sin(t * 18) > 0)
    # Kai looks up in awe
    look = (10, -12)
    blink = 0.05 if 0.6 < (lt % 2.7) < 0.7 else 1.0
    chars.bust(c, 520, 700 + 20 * (1 - kd), 1.02, t=twos(t), eyes="sparkle" if lt > 1.2 else "normal", open_=blink,
               look=look, mouth_kind="o", mouth_amt=0.7, blush_a=0.6, rot=-4)
    # warm light wash from the spirit
    c.drawRect(skia.Rect.MakeWH(W, H), fill("#000000", 1, shader=rad(sx, sy, 1100, ["#FFF6D055", "#FFF6D000"])))
    if t > V("spirit2") - 0.1:
        k = ease_out(seg(t, V("spirit2") - 0.1, V("spirit2") + 0.4))
        msg = "describe your vibe..."
        n = int(len(msg) * seg(t, V("spirit2") + 0.2, V("spirit2") + 1.2))
        prompt_bar(c, 1000, 800 + 80 * (1 - k), 820, 96, msg[:max(n, 0)], t, a=k)


# ============================================================================= 5. power-up (shonen)
def aura(c, cx, cy, t, s=1.0, a=1.0, colr="#FFB52E"):
    fr = math.floor(t * 12)
    for layer, (col_, sc) in enumerate(((colr, 1.0), ("#FFF2A0", 0.75))):
        pts = []
        n = 26
        for i in range(n):
            ang = math.pi * 2 * i / n
            up = -math.sin(ang)
            r = (430 + 140 * max(0.0, up) + 70 * hrand(fr, i, layer)) * sc * s
            if i % 2:
                r *= 0.8
            pts.append((cx + r * math.cos(ang) * 0.85, cy + r * math.sin(ang) - 160 * max(0.0, up) * s * sc))
        c.drawPath(poly(pts), fill(col_, a * (0.85 if layer == 0 else 0.7), blur=6))


def kinetic(c, s, x, y, size, rot, t, t0, colr, a=1.0):
    k = seg(t, t0, t0 + 0.16)
    if k <= 0:
        return
    sc = 2.2 - 1.2 * ease_out(k)
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.scale(sc, sc)
    text(c, s, "bang", size, 0, 0, colr, outline=INK, ow=10, a=a * k, shadow="#FFFFFF", shadow_off=(10, 10),
         outline2="#FFFFFF", ow2=16)
    c.restore()


def impact_frame(c, t, k_frame):
    """Classic black/white inverted impact frame."""
    inv = k_frame % 2 == 0
    bg, fg = ("#000000", "#FFFFFF") if inv else ("#FFFFFF", "#000000")
    c.drawRect(skia.Rect.MakeWH(W, H), fill(bg))
    speed_lines_radial(c, W / 2, H / 2, t, n=110, r0=240, color=fg, rmax=2400, wmax=30, seed=8)
    # silhouette
    c.save()
    c.translate(W / 2, 640)
    c.scale(1.2, 1.2)
    c.drawPath(chars.spiky_back(1.0, t), fill(fg))
    c.drawPath(chars.face_path(), fill(fg))
    c.drawPath(poly([(-420, 760), (420, 760), (330, 380), (90, 285), (-90, 285), (-330, 380)]), fill(fg))
    for sd in (-1, 1):
        c.drawPath(ellipse(sd * 86, 36, 46, 30), fill(bg))
    c.restore()


def scene_power(c, t, lt):
    eye_t = V("vibe") - 0.05
    if t < eye_t:
        build = seg(t, 19.6, 21.6)
        sx, sy = shake(t, 20.0, 10 + 20 * build, 3.0, 37)
        c.save()
        c.translate(sx, sy)
        grad_rect(c, -40, -40, W + 80, H + 80, ["#FF2E4D", "#FF8A1F", "#FFD23F"], [0, 0.6, 1])
        speed_lines_radial(c, W / 2, 560, t, n=80, r0=380, color="#FFFFFF", rmax=2300, wmax=34, seed=4, )
        speed_lines_radial(c, W / 2, 560, t, n=60, r0=460, color=INK, rmax=2300, wmax=14, seed=6)
        # rising rocks
        for i in range(16):
            x = 120 + i * 115 + 30 * hrand(i)
            y = 1100 - ((lt * (120 + 160 * hrand(i, "v")) + 400 * hrand(i, "o")) % 1300)
            r = 16 + 30 * hrand(i, "r")
            c.save()
            c.translate(x, y)
            c.rotate(lt * 90 * (hrand(i, "w") - 0.5))
            cel(c, poly([(-r, -r * 0.6), (r * 0.4, -r), (r, 0), (r * 0.3, r * 0.8), (-r * 0.9, r * 0.5)]),
                "#6B4A3A", INK, 4)
            c.restore()
        aura(c, W / 2, 640, t, 1.0 + 0.1 * build, a=0.35 + 0.65 * build)
        talking = any(V(k) <= t <= vo_end(k) for k in ("epic", "emo", "beat"))
        amt = 0.6 + 0.4 * abs(math.sin(t * 16))
        chars.bust(c, W / 2, 640, 1.05, t=twos(t), eyes="determined", brows="determined",
                   mouth_kind="shout" if talking else "grin", mouth_amt=amt if talking else 0.5,
                   lift=ease_out(build), glow=build)
        aura(c, W / 2, 900, t * 1.3, 0.55, a=0.35 * build, colr="#FFF2A0")
        kinetic(c, "EPIC!", 380, 250, 150, -12, t, V("epic"), "#FFD23F")
        kinetic(c, "EMOTIONAL!", 1520, 300, 120, 9, t, V("emo"), "#FF5C8A")
        kinetic(c, "ON THE BEAT!", 960, 960, 130, -4, t, V("beat"), "#3DE0FF")
        c.restore()
    elif t < IMPACT:
        # extreme close-up on the eye
        k = seg(t, eye_t, IMPACT)
        c.drawRect(skia.Rect.MakeWH(W, H), fill("#120400"))
        s = 4.2 + 1.2 * ease_in(k)
        c.save()
        c.translate(W / 2, H / 2)
        c.translate(-86 * s, -36 * s)
        chars.bust(c, 0, 0, s, t=twos(t), eyes="determined", brows="determined", mouth_kind="grin", lift=1.0, glow=1.0)
        c.restore()
        c.drawRect(skia.Rect.MakeXYWH(0, 0, W, 170), fill("#000000"))
        c.drawRect(skia.Rect.MakeXYWH(0, H - 170, W, 170), fill("#000000"))
        speed_lines_h(c, t, "#FFD23F", 0.25, n=24, seed=3, y0=170, y1=H - 170)
        text(c, "VIBE...", "bang", 120, W / 2, H - 85, "#FFFFFF", a=seg(t, eye_t + 0.1, eye_t + 0.3), tracking=18)
    else:
        lt2 = t - IMPACT
        if lt2 < 0.25:
            impact_frame(c, t, int(lt2 * 24))
            sfx_text(c, "ドンッ!", W / 2 + 420, 230, 200, -10, "#FF2E4D", "#FFFFFF", "dela", ow=12)
            return
        sx, sy = shake(t, IMPACT + 0.25, 26, 0.7)
        c.save()
        c.translate(sx, sy)
        grad_rect(c, -40, -40, W + 80, H + 80, ["#FFF7D6", "#FFB52E", "#FF3D6E"], [0, 0.45, 1])
        speed_lines_radial(c, W / 2, H / 2, t, n=100, r0=300, color="#FFFFFF", rmax=2300, wmax=30, seed=12)
        # shockwave rings
        for i in range(3):
            k = seg(lt2, 0.25 + i * 0.18, 1.3 + i * 0.18)
            if 0 < k < 1:
                c.drawCircle(W / 2, H / 2, 100 + 1300 * ease_out(k), stroke("#FFFFFF", 40 * (1 - k), 1 - k))
        # clips blasting outward
        for i in range(26):
            ang = i * 2.4
            k = ease_out(seg(lt2, 0.25, 1.6))
            r = 120 + (900 + 300 * hrand(i)) * k
            clip_card(c, W / 2 + r * math.cos(ang), H / 2 + r * math.sin(ang) * 0.7, 150, 92, CLIP_COLS[i % 6],
                      rot=ang * 50 + 200 * k)
        aura(c, W / 2, 680, t, 1.15, a=0.9)
        chars.bust(c, W / 2, 680, 0.95, t=twos(t), eyes="determined", brows="determined", mouth_kind="grin",
                   mouth_amt=0.8, lift=1.0, glow=1.0)
        k = seg(lt2, 0.25, 0.45)
        c.save()
        c.translate(W / 2, 220)
        sc = 2.0 - back_out(k, 1.5)
        c.scale(sc, sc)
        c.rotate(-5)
        text(c, "VIBE EDIT!!", "bang", 230, 0, 0, "#FFD23F", outline=INK, ow=14, outline2="#FFFFFF", ow2=24,
             a=clamp01(k * 3), shadow="#FF2E4D", shadow_off=(14, 14))
        c.restore()
        c.restore()
        flash(c, 1 - seg(lt2, 0.25, 0.55))


# ============================================================================= 6. mecha HUD
def hud_brackets(c, x, y, w, h, colr="#3DF2FF", a=1.0, L=40):
    p = stroke(colr, 5, a, cap=skia.Paint.kSquare_Cap)
    for (px, py, dx, dy) in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        c.drawLine(px, py, px + dx * L, py, p)
        c.drawLine(px, py, px, py + dy * L, p)


def graded(c, amt):
    """Colour-grade layer: amt 0 = flat/grey, 1 = vivid."""
    s = 0.25 + 0.95 * amt
    lw = (0.3, 0.59, 0.11)
    m = []
    for i in range(3):
        row = [lw[j] * (1 - s) + (s if i == j else 0) for j in range(3)]
        m += row + [0, 0.02 * amt]
    m += [0, 0, 0, 1, 0]
    p = skia.Paint()
    p.setColorFilter(skia.ColorFilters.Matrix(m))
    c.saveLayer(None, p)


def scene_mecha(c, t, lt):
    sx, sy = 0, 0
    for k in ("cuts", "color", "caps", "music", "synced"):
        a, b = shake(t, V(k), 8, 0.2)
        sx += a
        sy += b
    c.save()
    c.translate(sx, sy)
    grad_rect(c, -20, -20, W + 40, H + 40, ["#02040F", "#071433", "#0B1E4A"])
    # perspective grid floor
    hz = 640
    for i in range(-20, 21):
        c.drawLine(W / 2 + i * 40, hz, W / 2 + i * 260, H + 40, stroke("#1E6BFF", 2, 0.35))
    for j in range(12):
        z = ((j + lt * 2) % 12) / 12
        y = hz + (H - hz + 40) * z ** 2
        c.drawLine(0, y, W, y, stroke("#1E6BFF", 2, 0.35 * z))
    # rotating HUD rings behind the monitor
    c.save()
    c.translate(W / 2, 360)
    for i, (r, sp, dash) in enumerate(((420, 20, 30), (470, -12, 12), (520, 8, 60))):
        c.save()
        c.rotate(lt * sp)
        p = stroke("#3DF2FF", 3, 0.35)
        p.setPathEffect(skia.DashPathEffect.Make([dash, dash * 0.6], 0))
        c.drawCircle(0, 0, r, p)
        c.restore()
    c.restore()
    # preview monitor
    mx, my, mw, mh = 560, 110, 800, 450
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(mx, my, mw, mh))
    graded(c, ease_io(seg(t, V("color"), V("color") + 0.6)))
    c.translate(mx, my)
    c.scale(mw / W, mh / H)
    city_bg(c, t, pan=40 * lt, rain=0.6)
    chars.back_view(c, 960, 1000, 0.9, rim="#FF8FD0", t=t)
    c.restore()
    c.restore()
    if t > V("caps"):
        k = seg(t, V("caps"), V("caps") + 0.3)
        c.drawRect(skia.Rect.MakeXYWH(mx + mw / 2 - 260, my + mh - 70, 520, 50), fill("#000000", 0.55 * k))
        text(c, "Say the vibe.", "pop", 30, mx + mw / 2, my + mh - 45, "#FFFFFF", a=k)
    c.drawRect(skia.Rect.MakeXYWH(mx, my, mw, mh), stroke("#3DF2FF", 3, 0.8))
    hud_brackets(c, mx - 16, my - 16, mw + 32, mh + 32)
    # scanline over preview
    yy = my + (lt * 260) % mh
    c.drawRect(skia.Rect.MakeXYWH(mx, yy, mw, 3), fill("#3DF2FF", 0.35))
    # timeline tracks
    tx, ty, tw_ = 260, 660, 1400
    for i, lab in enumerate(("V1", "CC", "A1")):
        y = ty + i * 72
        c.drawRect(skia.Rect.MakeXYWH(tx, y, tw_, 58), fill("#0D2352", 0.85))
        c.drawRect(skia.Rect.MakeXYWH(tx, y, tw_, 58), stroke("#1E6BFF", 2, 0.8))
        text(c, lab, "orb", 24, tx - 40, y + 29, "#3DF2FF")
    # V1: clips fly in and snap
    xs = [0, 170, 300, 520, 640, 830, 990, 1130, 1260, 1400]
    for i in range(len(xs) - 1):
        t0 = V("cuts") - 0.1 + i * 0.07
        k = seg(t, t0, t0 + 0.3)
        if k <= 0:
            continue
        e = back_out(k, 1.6)
        fx = tx + xs[i] + (hrand(i, "fx") - 0.5) * 1200 * (1 - e)
        fy = ty + 4 - (300 + 300 * hrand(i, "fy")) * (1 - e)
        c.drawRoundRect(skia.Rect.MakeXYWH(fx + 3, fy, xs[i + 1] - xs[i] - 6, 50), 6, 6, fill(CLIP_COLS[i % 6]))
        if k >= 1 and t - t0 < 0.45:
            c.drawLine(tx + xs[i] + 1, ty - 20, tx + xs[i] + 1, ty + 80, stroke("#FFFFFF", 6, 1 - (t - t0 - 0.3) / 0.15))
    # CC: caption blocks
    kc = seg(t, V("caps"), V("caps") + 0.7)
    for i in range(7):
        if kc * 7 > i:
            c.drawRoundRect(skia.Rect.MakeXYWH(tx + 20 + i * 196, ty + 84, 170, 34), 8, 8, fill("#FFD23F"))
            c.drawRect(skia.Rect.MakeXYWH(tx + 40 + i * 196, ty + 97, 110, 8), fill("#5A4300"))
    # A1: waveform
    km = seg(t, V("music"), V("music") + 0.5)
    if km > 0:
        n = int(140 * km)
        for i in range(n):
            amp = 0.3 + 0.7 * abs(math.sin(i * 0.37) * math.sin(i * 0.11 + lt * 6))
            if i % 8 == 0:
                amp = 1.0
            hgt = 50 * amp
            c.drawRect(skia.Rect.MakeXYWH(tx + 6 + i * 10, ty + 144 + 29 - hgt / 2, 6, hgt), fill("#4CF2A0"))
    # playhead
    if t > V("synced"):
        ph = tx + tw_ * ((t - V("synced")) * 0.45 % 1)
        c.drawRect(skia.Rect.MakeXYWH(ph, ty - 24, 4, 240), fill("#FF3D7F"))
        c.drawPath(poly([(ph - 12, ty - 36), (ph + 16, ty - 36), (ph + 2, ty - 20)]), fill("#FF3D7F"))
    # module labels at the sides
    mods = [("cuts", "CUTS", 250, 160), ("color", "COLOR", 250, 330), ("caps", "CAPTIONS", 1670, 160),
            ("music", "MUSIC", 1670, 330)]
    for key, lab, x, y in mods:
        on = t >= V(key)
        k = seg(t, V(key), V(key) + 0.2)
        colr = "#3DF2FF" if not on else "#FFD23F"
        w = 340
        c.drawPath(poly([(x - w / 2 + 20, y - 40), (x + w / 2, y - 40), (x + w / 2 - 20, y + 40), (x - w / 2, y + 40)]),
                   fill("#081A40", 0.9))
        c.drawPath(poly([(x - w / 2 + 20, y - 40), (x + w / 2, y - 40), (x + w / 2 - 20, y + 40), (x - w / 2, y + 40)]),
                   stroke(colr, 4))
        text(c, lab, "zen", 30, x - 24, y, colr)
        if on:
            sc = 1 + 0.6 * (1 - k)
            c.save()
            c.translate(x + 130, y)
            c.scale(sc, sc)
            c.drawPath(path([(-14, 0), (-4, 12), (16, -14)], False, smooth=False), stroke("#FFD23F", 7))
            c.restore()
            if k < 1:
                c.drawRect(skia.Rect.MakeXYWH(x - w / 2, y - 40, w, 80), fill("#FFFFFF", 0.6 * (1 - k)))
    # color wheels during the grade
    kw = seg(t, V("color"), V("color") + 0.3) * (1 - seg(t, V("caps"), V("caps") + 0.3))
    if kw > 0:
        for i, colr in enumerate(("#FF5C8A", "#4CF2A0", "#3DA8FF")):
            x = 760 + i * 200
            c.drawCircle(x, 560, 60 * kw, fill("#000000", 0.8, shader=skia.GradientShader.MakeSweep(
                x, 560, [0xFFFF0000, 0xFFFFFF00, 0xFF00FF00, 0xFF00FFFF, 0xFF0000FF, 0xFFFF00FF, 0xFFFF0000])))
            c.drawCircle(x, 560, 60 * kw, stroke("#FFFFFF", 4))
            ang = lt * 3 + i
            c.drawCircle(x + 30 * kw * math.cos(ang), 560 + 30 * kw * math.sin(ang), 9, fill("#FFFFFF"))
    # sync rate
    ks = ease_io(seg(t, V("synced"), V("synced") + 0.9))
    if t > V("synced") - 0.1:
        a = seg(t, V("synced") - 0.1, V("synced") + 0.1)
        c.drawRect(skia.Rect.MakeXYWH(560, 900, 800, 120), fill("#081A40", 0.92 * a))
        c.drawRect(skia.Rect.MakeXYWH(560, 900, 800, 120), stroke("#FFD23F", 4, a))
        text(c, "シンクロ率", "dela", 34, 600, 935, "#FFD23F", anchor="l", a=a)
        text(c, f"{int(100 * ks):3d}%", "orb", 64, 1330, 960, "#FFFFFF", anchor="r", a=a)
        c.drawRect(skia.Rect.MakeXYWH(600, 975, 520 * ks, 22), fill("#FFD23F", a))
        c.drawRect(skia.Rect.MakeXYWH(600, 975, 520, 22), stroke("#FFD23F", 2, a))
        if ks >= 1:
            k2 = seg(t, V("synced") + 0.9, V("synced") + 1.05)
            c.save()
            c.translate(W / 2, 330)
            c.rotate(-8)
            sc = 1.6 - 0.6 * ease_out(k2)
            c.scale(sc, sc)
            c.drawRoundRect(skia.Rect.MakeXYWH(-330, -80, 660, 160), 18, 18, stroke("#FF3D7F", 14, k2))
            text(c, "SYNCED", "zen", 110, 0, 0, "#FF3D7F", a=k2)
            c.restore()
    # cockpit frame
    for sd in (-1, 1):
        x0 = 0 if sd < 0 else W
        c.drawPath(poly([(x0, 0), (x0 - sd * -120, 0), (x0 - sd * -40, 420), (x0 - sd * -40, 680), (x0 - sd * -160, H),
                         (x0, H)]), fill("#0A1230"))
        c.drawPath(poly([(x0 - sd * -120, 0), (x0 - sd * -40, 420), (x0 - sd * -40, 680), (x0 - sd * -160, H)], False),
                   stroke("#3DF2FF", 3, 0.7))
    text(c, "VIBE ENGINE // ONLINE", "orb", 24, W / 2, 50, "#3DF2FF", tracking=6)
    c.restore()
    # scanlines
    for y in range(0, H, 4):
        c.drawRect(skia.Rect.MakeXYWH(0, y, W, 1), fill("#000000", 0.12))


# ============================================================================= 7. shojo
def rose(c, x, y, s, colr="#FF5C8A", a=1.0, rot=0.0):
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    c.rotate(rot)
    for sd in (-1, 1):
        cel(c, path([(0, 40), (sd * 70, 80), (sd * 110, 50), (sd * 60, 30)], True), "#5FBF7A", INK, 3, a)
    for i in range(5):
        r = 60 - i * 11
        ang = i * 1.3
        p = path([(r * math.cos(ang + k * 1.2), r * math.sin(ang + k * 1.2) * 0.85) for k in range(5)], True)
        cel(c, p, mix(colr, "#FFFFFF", i * 0.1), INK, 3, a)
    c.restore()


def scene_shojo(c, t, lt):
    grad_rect(c, 0, 0, W, H, ["#FFD6EC", "#FFB3D9", "#E9B5FF"])
    # bokeh bubbles
    for i in range(26):
        x = hrand(i, "bx") * W + 30 * math.sin(lt * 0.7 + i)
        y = (hrand(i, "by") * (H + 300) - lt * 40 * (0.5 + hrand(i))) % (H + 300) - 150
        r = 40 + 110 * hrand(i, "br")
        c.drawCircle(x, y, r, fill("#FFFFFF", 0.18))
        c.drawCircle(x, y, r, stroke("#FFFFFF", 3, 0.35))
    # radial sparkle burst on SUGOI
    if t > V("sugoi"):
        k = seg(t, V("sugoi"), V("sugoi") + 0.4)
        speed_lines_radial(c, W / 2, 520, t, n=60, r0=300, color="#FFFFFF", rmax=2000, wmax=20, seed=31,
                           a=0.6 * (1 - 0.6 * seg(t, V("sugoi") + 0.6, V("sugoi") + 1.5)) * k)
    # screentone flower border
    for i in range(12):
        x = i * 175 + 30
        for y in (40, H - 40):
            c.drawCircle(x, y, 60, fill("#FFFFFF", 0.4))
    for x, y, s, r in ((120, 160, 1.2, 10), (1800, 170, 1.3, -20), (110, 950, 1.4, 30), (1810, 940, 1.2, -10),
                       (300, 1020, 0.9, 0), (1640, 1030, 0.9, 40)):
        rose(c, x, y, s, rot=r + 5 * math.sin(lt * 2 + x))
    tears = ease_io(seg(t, V("client") + 0.1, V("client") + 0.9))
    happy_bounce = 10 * abs(math.sin(twos(t) * 7)) if t > V("sugoi") else 0
    chars.bust(c, W / 2, 610 - happy_bounce, 0.98, P=chars.CLIENT, t=twos(t), eyes="sparkle",
               mouth_kind="grin" if t > V("sugoi") - 0.05 else "o", mouth_amt=0.9, blush_a=1.0, tears=tears)
    # petals
    for i in range(40):
        x = (hrand(i, "px") * (W + 200) + lt * 120 + 60 * math.sin(lt * 1.5 + i)) % (W + 200) - 100
        y = (hrand(i, "py") * (H + 200) + lt * (90 + 60 * hrand(i))) % (H + 200) - 100
        c.save()
        c.translate(x, y)
        c.rotate(lt * 120 + i * 40)
        c.scale(1, 0.5 + 0.5 * math.sin(lt * 4 + i))
        c.drawPath(path([(0, -16), (12, 0), (0, 16), (-12, 0)], True), fill("#FFF0F6", 0.95))
        c.restore()
    for i in range(18):
        x, y = hrand(i, "sx") * W, hrand(i, "sy") * H
        tw = math.sin(lt * 5 + i * 1.3)
        if tw > 0:
            sparkle(c, x, y, 26 * tw, "#FFFFFF", tw)
    if t > V("sugoi"):
        k = seg(t, V("sugoi"), V("sugoi") + 0.25)
        c.save()
        c.translate(W / 2 + 470, 230)
        c.rotate(10)
        sc = 0.3 + 0.7 * elastic(k)
        c.scale(sc, sc)
        text(c, "すごい!!", "pop", 150, 0, 0, "#FF3D8B", outline="#FFFFFF", ow=14, outline2="#FF3D8B", ow2=20)
        c.restore()
        c.save()
        c.translate(W / 2 - 520, 260)
        c.rotate(-10)
        c.scale(sc, sc)
        text(c, "SUGOI!", "pop", 100, 0, 0, "#FFFFFF", outline="#B44CFF", ow=10)
        c.restore()
    # Kai chibi cameo, proud
    if t > V("client") + 0.4:
        k = back_out(seg(t, V("client") + 0.4, V("client") + 0.75))
        chars.chibi(c, 1640, 1180 - 330 * k + 10 * math.sin(t * 9), 0.62, twos(t), "stare")
        if k > 0.9:
            sparkle(c, 1560, 760, 30, "#FFFFFF", 1.0, rot=t)
            text(c, "V!", "bang", 70, 1790, 800, "#FFD23F", outline=INK, ow=7)


# ============================================================================= 8. title / opening card
def sun_stripes(c, x, y, r):
    c.save()
    p = ellipse(x, y, r, r)
    c.clipPath(p, doAntiAlias=True)
    c.drawPath(p, fill("#000000", shader=lin(0, y - r, 0, y + r, ["#FFF07A", "#FF8A3D", "#FF3D7F"])))
    for i in range(7):
        hh = 6 + i * 4
        yy = y + r * 0.1 + i * (r * 0.14)
        c.drawRect(skia.Rect.MakeXYWH(x - r, yy, 2 * r, hh), fill("#FF7BA8"))
    c.restore()


def scene_title(c, t, lt):
    grad_rect(c, 0, 0, W, H, ["#1E1347", "#6B2FA0", "#FF4F8B", "#FF9A5A"], [0, 0.35, 0.7, 1])
    sun_stripes(c, W / 2, 700, 380)
    text(c, "バイブ編集", "dela", 300, W / 2, 420, "#FFFFFF", a=0.13 * seg(lt, 0, 0.6))
    # skyline silhouette + hill
    L = _city_layers()
    c.save()
    c.translate(-60 * lt, 160)
    c.drawPath(L["layers"][1]["bodies"], fill("#2A1240"))
    c.drawPath(L["layers"][1]["warm"], fill("#FFB35C", 0.5))
    c.restore()
    c.drawPath(path([(-50, H + 50), (-50, 930), (400, 870), (900, 900), (1400, 860), (1970, 920), (1970, H + 50)], True),
               fill("#1A0B2E"))
    # Kai (back) + spirit on the hill
    chars.back_view(c, 1500, 855, 0.32, rim="#FFB35C", t=t)
    chars.spirit(c, 1640, 640 + 12 * math.sin(t * 2.5), 0.45, t, a=1.0, glow=0.6)
    # petals
    for i in range(46):
        x = (hrand(i, "tx") * (W + 200) - lt * 260 + 40 * math.sin(lt + i)) % (W + 200) - 100
        y = (hrand(i, "ty") * (H + 200) + lt * (120 + 80 * hrand(i))) % (H + 200) - 100
        c.save()
        c.translate(x, y)
        c.rotate(lt * 140 + i * 37)
        c.scale(1, 0.5 + 0.5 * math.sin(lt * 4 + i))
        c.drawPath(path([(0, -14), (10, 0), (0, 14), (-10, 0)], True), fill("#FFD6EC", 0.95))
        c.restore()
    # title slam
    for i, (word, y, t0) in enumerate((("VIBE", 300, V("title") - 0.05), ("EDITING", 500, V("title") + 0.32))):
        k = seg(t, t0, t0 + 0.2)
        if k <= 0:
            continue
        sx, sy = shake(t, t0 + 0.2, 16, 0.3)
        c.save()
        c.translate(W / 2 + sx, y + sy)
        sc = 2.4 - 1.4 * ease_out(k)
        c.scale(sc, sc)
        c.rotate(-4)
        sh = lin(0, -100, 0, 100, ["#FFF7B0", "#FFD23F", "#FF5C8A"])
        text(c, word, "dela", 210 if i == 0 else 170, 0, 0, "#FFFFFF", outline=INK, ow=14, outline2="#FFFFFF",
             ow2=24, shadow="#3DD6FF", shadow_off=(14, 14), shader=sh, a=clamp01(k * 2), tracking=10)
        c.restore()
    # light sweep across the title
    ks = seg(t, V("title") + 0.8, V("title") + 1.4)
    if 0 < ks < 1:
        x = -400 + (W + 800) * ks
        c.save()
        c.rotate(-4)
        c.drawRect(skia.Rect.MakeXYWH(x, 150, 120, 500), fill("#FFFFFF", 0.35, blur=20))
        c.restore()
    if t > V("say"):
        k = ease_out(seg(t, V("say"), V("say") + 0.35))
        text(c, "Say the vibe.", "pop", 66, W / 2 - 230, 720 + 30 * (1 - k), "#FFFFFF", outline=INK, ow=6, a=k)
    if t > V("alive"):
        k = ease_out(seg(t, V("alive"), V("alive") + 0.35))
        text(c, "Watch it come alive.", "pop", 66, W / 2 + 290, 800 + 30 * (1 - k), "#FFE45C", outline=INK, ow=6, a=k)
    if t > V("alive") + 0.6:
        k = ease_out(seg(t, V("alive") + 0.6, V("alive") + 1.0))
        text(c, "by IDEABRO STUDIO", "zen", 30, W / 2, 1010, "#FFFFFF", a=k, tracking=8)
    for i in range(10):
        tw = math.sin(lt * 4 + i * 1.7)
        if tw > 0 and lt > 0.8:
            sparkle(c, 380 + i * 130, 180 + 280 * hrand(i, "y"), 22 * tw, "#FFFFFF", tw)
    flash(c, ease_in(seg(t, 39.65, 40.0)), "#000000")


# ============================================================================= overlays
SUBS = {
    "world1": "In a world drowning in footage...", "world2": "...one editor stood alone.",
    "chibi1": "Three days of cutting and keyframing...", "chibi2": "...and his soul left his body.",
    "spirit1": "Stop fighting the timeline, Kai.", "spirit2": "Just tell me the vibe.",
    "client": "Even the client cried.",
}


def subtitles(c, t):
    for k, s in SUBS.items():
        a0, a1 = V(k) - 0.05, vo_end(k) + 0.25
        if a0 <= t <= a1:
            a = seg(t, a0, a0 + 0.1) * (1 - seg(t, a1 - 0.12, a1))
            col_ = "#FFF27A" if k.startswith("spirit") else "#FFFFFF"
            text(c, s, "pop", 46, W / 2, H - 78, col_, outline="#140A1E", ow=7, a=a)


def style_tag(c, t):
    name, a, b = scene_at(t)
    if name == "title":
        return
    idx = [s[0] for s in SCENES].index(name) + 1
    k = ease_out(seg(t, a + 0.15, a + 0.45))
    lab = f"{idx:02d}  {STYLE_TAG[name]}"
    w = text_width(lab, "zen", 22) + 44
    x = 40 - (1 - k) * (w + 60)
    c.drawRoundRect(skia.Rect.MakeXYWH(x, 36, w, 46), 23, 23, fill("#120A22", 0.55 * k))
    c.drawRoundRect(skia.Rect.MakeXYWH(x, 36, w, 46), 23, 23, stroke("#FFFFFF", 2, 0.5 * k))
    text(c, lab, "zen", 22, x + 22, 59, "#FFFFFF", anchor="l", a=k)


CUT_FLASH = {5.6: ("#FFFFFF", 0.18), 10.4: ("#FFFFFF", 0.14), 14.8: ("#FFFFFF", 0.45), 19.6: ("#FFFFFF", 0.2),
             25.6: ("#3DF2FF", 0.2), 30.4: ("#FFD6EC", 0.35), 35.2: ("#FFFFFF", 0.3)}


def transitions(c, t):
    for tc, (colr, d) in CUT_FLASH.items():
        if tc <= t < tc + d:
            flash(c, (1 - (t - tc) / d) ** 1.5 * 0.95, colr)
    # whip into the mecha scene
    if 25.35 <= t < 25.6:
        k = seg(t, 25.35, 25.6)
        speed_lines_h(c, t, "#FFFFFF", 0.8 * k, n=60, seed=40, speed=9000)


SCENE_FN = dict(city=scene_city, manga=scene_manga, chibi=scene_chibi, spirit=scene_spirit, power=scene_power,
                mecha=scene_mecha, shojo=scene_shojo, title=scene_title)


def render(c, t):
    name, a, b = scene_at(t)
    c.save()
    SCENE_FN[name](c, t, t - a)
    c.restore()
    subtitles(c, t)
    style_tag(c, t)
    transitions(c, t)
