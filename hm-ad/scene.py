"""scene: H&M 30 s launch ad (spec). Every frame is a pure function of time t.

    python3 scene.py stills 0.6 2.4 4.4 6.0     # check frames -> out/stills/
    python3 scene.py audio                      # music + sfx -> work/mix.wav
    python3 scene.py draft                      # half-res, half-fps preview -> out/draft.mp4
    python3 scene.py render                     # final -> out/hm-ad_v1.mp4
"""

import json
import math
import os
import sys
from pathlib import Path

import skia

sys.path.insert(0, str(Path(__file__).resolve().parent / "vibe"))
import audio_kit as ak  # noqa: E402
from motion_kit import (Stage, clamp, ease_in_back, ease_in_cubic, ease_in_out_cubic, ease_out_back,  # noqa: E402
                        ease_out_bounce, ease_out_cubic, ease_out_expo, lerp, noise1, prog, pulse, rgb, rrect,
                        shadow, text, text_width)

import timeline as TL  # noqa: E402

S = Stage(TL.W, TL.H, fps=TL.FPS, duration=TL.DURATION)
B = S.brand
W, H = TL.W, TL.H
U = min(W, H) / 1080
BEAT = TL.BEAT
HEX = B["colors"]

WHITE, INK, RED = rgb(HEX["paper"]), rgb(HEX["ink"]), rgb(HEX["red"])
STONE, SAND, GREY = rgb(HEX["stone"]), rgb(HEX["sand"]), rgb(HEX["grey"])
REGULAR = "InterTight-400.ttf"      # body regular; "body" is the 700 weight


# ------------------------------------------------------------------ helpers
def shade(hexcol, k):
    """darken (k<0) or lighten (k>0) a hex colour -> skia colour."""
    h = hexcol.lstrip("#")
    r, g, b_ = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    if k < 0:
        r, g, b_ = (int(v * (1 + k)) for v in (r, g, b_))
    else:
        r, g, b_ = (int(v + (255 - v) * k) for v in (r, g, b_))
    return skia.Color(r, g, b_)


def fit(s, font, max_w, max_size, tracking=0.0):
    return min(max_size, max_w / max(1, text_width(s, 100, font, tracking)) * 100)


def slam(c, s, x, y, k, size, font="display", fill=INK, from_scale=1.9, rot=0.0, alpha=1.0, tracking=0.0):
    """kinetic slam: scale from_scale -> 1 with expo ease, quick fade in."""
    if k <= 0:
        return
    e = ease_out_expo(k)
    sc = lerp(from_scale, 1.0, e)
    c.save()
    c.translate(x, y)
    c.rotate(rot * (1 - e))
    c.scale(sc, sc)
    text(c, s, 0, 0, size=size, font=font, fill=fill, alpha=clamp(k * 4) * alpha, tracking=tracking)
    c.restore()


def beat_of(lt):
    i = int(lt / BEAT + 1e-6)
    return i, lt - i * BEAT


def fpaint(col, corner=0.0, stroke=None):
    p = skia.Paint(Color=col, AntiAlias=True)
    if corner:
        p.setPathEffect(skia.CornerPathEffect.Make(corner))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    return p


def poly(pts, cx, cy, s):
    p = skia.Path()
    p.moveTo(cx + pts[0][0] * s, cy + pts[0][1] * s)
    for x, y in pts[1:]:
        p.lineTo(cx + x * s, cy + y * s)
    p.close()
    return p


def line(c, cx, cy, s, pts, col, w):
    p = skia.Path()
    p.moveTo(cx + pts[0][0] * s, cy + pts[0][1] * s)
    for x, y in pts[1:]:
        p.lineTo(cx + x * s, cy + y * s)
    c.drawPath(p, fpaint(col, stroke=w))


# ------------------------------------------------------------------ garments (vector, unit box -0.5..0.5)
TEE = [(-0.17, -0.42), (-0.07, -0.42), (0, -0.35), (0.07, -0.42), (0.17, -0.42), (0.45, -0.24), (0.36, -0.07),
       (0.25, -0.13), (0.25, 0.45), (-0.25, 0.45), (-0.25, -0.13), (-0.36, -0.07), (-0.45, -0.24)]
BLAZER = [(-0.15, -0.45), (0, -0.25), (0.15, -0.45), (0.32, -0.38), (0.45, 0.25), (0.35, 0.27), (0.29, -0.05),
          (0.29, 0.45), (-0.29, 0.45), (-0.29, -0.05), (-0.35, 0.27), (-0.45, 0.25), (-0.32, -0.38)]
HOODIE = [(-0.16, -0.38), (0.16, -0.38), (0.34, -0.3), (0.46, 0.3), (0.35, 0.32), (0.27, -0.02), (0.27, 0.45),
          (-0.27, 0.45), (-0.27, -0.02), (-0.35, 0.32), (-0.46, 0.3), (-0.34, -0.3)]
DRESS = [(-0.11, -0.45), (-0.07, -0.45), (0, -0.36), (0.07, -0.45), (0.11, -0.45), (0.15, -0.18), (0.12, -0.04),
         (0.36, 0.45), (-0.36, 0.45), (-0.12, -0.04), (-0.15, -0.18)]
JEANS = [(-0.24, -0.45), (0.24, -0.45), (0.3, 0.45), (0.05, 0.45), (0, -0.12), (-0.05, 0.45), (-0.3, 0.45)]
SKIRT = [(-0.2, -0.45), (0.2, -0.45), (0.34, 0.08), (-0.34, 0.08)]
SNEAKER = [(-0.45, 0.05), (-0.42, -0.18), (-0.12, -0.2), (0.02, -0.04), (0.3, 0.0), (0.44, 0.08), (0.46, 0.18),
           (-0.46, 0.18)]


def garment(c, kind, cx, cy, s, hexcol):
    col = rgb(hexcol)
    dk = shade(hexcol, -0.22)
    r = 0.025 * s
    if kind in ("tee", "kids"):
        c.drawPath(poly(TEE, cx, cy, s), fpaint(col, r))
        line(c, cx, cy, s, [(-0.07, -0.42), (0, -0.33), (0.07, -0.42)], dk, 0.014 * s)
        line(c, cx, cy, s, [(-0.25, -0.13), (-0.27, -0.3)], dk, 0.008 * s)
        line(c, cx, cy, s, [(0.25, -0.13), (0.27, -0.3)], dk, 0.008 * s)
        if kind == "kids":                           # a star print
            pts = []
            for i in range(10):
                a = -math.pi / 2 + i * math.pi / 5
                rr = 0.12 if i % 2 == 0 else 0.05
                pts.append((math.cos(a) * rr, 0.08 + math.sin(a) * rr))
            c.drawPath(poly(pts, cx, cy, s), fpaint(RED, 0.004 * s))
    elif kind == "blazer":
        c.drawPath(poly(BLAZER, cx, cy, s), fpaint(col, r))
        line(c, cx, cy, s, [(-0.15, -0.45), (-0.08, -0.05), (0, 0.1)], dk, 0.012 * s)
        line(c, cx, cy, s, [(0.15, -0.45), (0.08, -0.05), (0, 0.1)], dk, 0.012 * s)
        line(c, cx, cy, s, [(0, 0.1), (0, 0.45)], dk, 0.008 * s)
        for yy in (0.18, 0.3):
            c.drawCircle(cx + 0.03 * s, cy + yy * s, 0.018 * s, fpaint(dk))
        line(c, cx, cy, s, [(-0.22, 0.15), (-0.1, 0.15)], dk, 0.008 * s)
        line(c, cx, cy, s, [(0.1, 0.15), (0.22, 0.15)], dk, 0.008 * s)
    elif kind == "hoodie":
        c.drawPath(poly([(-0.18, -0.36), (-0.14, -0.5), (0.14, -0.5), (0.18, -0.36)], cx, cy, s), fpaint(dk, r))
        c.drawPath(poly(HOODIE, cx, cy, s), fpaint(col, r))
        line(c, cx, cy, s, [(-0.13, -0.38), (0, -0.25), (0.13, -0.38)], dk, 0.014 * s)
        line(c, cx, cy, s, [(-0.04, -0.3), (-0.05, -0.12)], dk, 0.008 * s)
        line(c, cx, cy, s, [(0.04, -0.3), (0.05, -0.12)], dk, 0.008 * s)
        rrect(c, cx - 0.16 * s, cy + 0.12 * s, 0.32 * s, 0.16 * s, 0.03 * s, dk)
        rrect(c, cx - 0.27 * s, cy + 0.38 * s, 0.54 * s, 0.07 * s, 0.01 * s, dk)
    elif kind == "dress":
        c.drawPath(poly(DRESS, cx, cy, s), fpaint(col, r))
        line(c, cx, cy, s, [(-0.12, -0.04), (0.12, -0.04)], dk, 0.012 * s)
        line(c, cx, cy, s, [(-0.06, 0.05), (-0.16, 0.45)], dk, 0.006 * s)
        line(c, cx, cy, s, [(0.06, 0.05), (0.16, 0.45)], dk, 0.006 * s)
    elif kind == "jeans":
        c.drawPath(poly(JEANS, cx, cy, s), fpaint(col, r * 0.6))
        line(c, cx, cy, s, [(-0.24, -0.37), (0.24, -0.37)], dk, 0.012 * s)
        line(c, cx, cy, s, [(0.0, -0.37), (0.0, -0.18)], dk, 0.008 * s)
        line(c, cx, cy, s, [(-0.22, -0.3), (-0.12, -0.26), (-0.1, -0.37)], dk, 0.008 * s)
        line(c, cx, cy, s, [(0.22, -0.3), (0.12, -0.26), (0.1, -0.37)], dk, 0.008 * s)
    elif kind == "skirt":
        skin = rgb(HEX["skin"])
        rrect(c, cx - 0.16 * s, cy, 0.1 * s, 0.45 * s, 0.04 * s, skin)
        rrect(c, cx + 0.06 * s, cy, 0.1 * s, 0.45 * s, 0.04 * s, skin)
        c.drawPath(poly(SKIRT, cx, cy, s), fpaint(col, r))
        line(c, cx, cy, s, [(-0.2, -0.37), (0.2, -0.37)], dk, 0.012 * s)
        for xx in (-0.1, 0.0, 0.1):
            line(c, cx, cy, s, [(xx * 0.8, -0.3), (xx * 1.3, 0.06)], dk, 0.006 * s)
    elif kind == "sneaker":
        c.drawPath(poly(SNEAKER, cx, cy, s), fpaint(col, r))
        rrect(c, cx - 0.47 * s, cy + 0.13 * s, 0.94 * s, 0.1 * s, 0.03 * s, WHITE)
        rrect(c, cx - 0.47 * s, cy + 0.13 * s, 0.94 * s, 0.1 * s, 0.03 * s, dk, stroke=0.008 * s)
        for i in range(4):
            xx = -0.2 + i * 0.07
            line(c, cx, cy, s, [(xx, -0.16 + i * 0.03), (xx + 0.05, -0.08 + i * 0.03)], dk, 0.012 * s)
        line(c, cx, cy, s, [(-0.36, 0.04), (0.2, 0.06)], RED, 0.02 * s)
    elif kind == "lipstick":
        rrect(c, cx - 0.12 * s, cy - 0.02 * s, 0.24 * s, 0.45 * s, 0.03 * s, INK)
        rrect(c, cx - 0.1 * s, cy - 0.12 * s, 0.2 * s, 0.12 * s, 0.01 * s, rgb(HEX["camel"]))
        c.drawPath(poly([(-0.08, -0.12), (-0.08, -0.32), (0.08, -0.44), (0.08, -0.12)], cx, cy, s), fpaint(col, r))
    elif kind == "vase":
        p = skia.Path()
        p.moveTo(cx - 0.08 * s, cy - 0.2 * s)
        p.cubicTo(cx - 0.08 * s, cy - 0.05 * s, cx - 0.3 * s, cy + 0.05 * s, cx - 0.22 * s, cy + 0.45 * s)
        p.lineTo(cx + 0.22 * s, cy + 0.45 * s)
        p.cubicTo(cx + 0.3 * s, cy + 0.05 * s, cx + 0.08 * s, cy - 0.05 * s, cx + 0.08 * s, cy - 0.2 * s)
        p.close()
        sage = shade(HEX["sage"], -0.25)
        for a in (-0.35, 0.0, 0.3):
            ex, ey = math.sin(a) * 0.32, -0.5 + abs(a) * 0.2
            line(c, cx, cy, s, [(0, -0.18), (ex, ey)], sage, 0.012 * s)
            c.drawOval(skia.Rect.MakeXYWH(cx + (ex - 0.05) * s, cy + (ey - 0.03) * s, 0.1 * s, 0.06 * s),
                       fpaint(rgb(HEX["sage"])))
        c.drawPath(p, fpaint(col))
        rrect(c, cx - 0.09 * s, cy - 0.23 * s, 0.18 * s, 0.04 * s, 0.01 * s, dk)


# ------------------------------------------------------------------ global FX
def shake_offset(t):
    a = 0.0
    for hit in TL.HITS:
        d = t - hit
        if 0 <= d < 0.4:
            a += 16 * U * math.exp(-10 * d)
    return a * noise1(t * 40, 1), a * noise1(t * 40, 2)


def flash(c, t):
    for hit in TL.HITS:
        d = t - hit
        if 0 <= d < 0.1:
            c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Color=skia.Color(255, 255, 255, int(150 * (1 - d / 0.1)))))


# ------------------------------------------------------------------ scenes
def s_hook(c, t, lt, dur):
    bi, bl = beat_of(lt)
    if bi < 4:
        first = bi < 2
        c.clear(WHITE if first else RED)
        words = TL.COPY["hook_a"] if first else TL.COPY["hook_b"]
        base = 0 if first else 2
        size = min(fit(w, "display", W * 0.86, 260 * U) for w in words)
        for i, w in enumerate(words):
            k = prog(lt, (base + i) * BEAT, 0.18)
            y = H / 2 - size * 0.55 + i * size * 1.1
            col = (INK if i == 0 else RED) if first else WHITE
            slam(c, w, W / 2, y, k, size, fill=col, rot=-6 if i else 6)
        if not first:                                       # underline sweeps in under "YOU."
            kk = ease_out_expo(prog(lt, 3 * BEAT + 0.12, 0.25))
            bw = text_width(words[1], size, "display") * kk
            c.drawRect(skia.Rect.MakeXYWH(W / 2 - bw / 2, H / 2 + size * 1.25, bw, 18 * U), skia.Paint(Color=WHITE))
    else:
        i = min(3, bi - 4)
        c.clear(INK if i % 2 == 0 else RED)
        w = TL.COPY["hook_c"][i]
        size = fit(w, "display", W * 0.8, 340 * U)
        k = prog(bl, 0, 0.16)
        bump = 1 + 0.03 * pulse(t, TL.BPM)
        c.save()
        c.translate(W / 2, H / 2)
        c.rotate(-4 if i % 2 else 4)
        c.scale(bump, bump)
        # echo outlines behind the word for speed
        for j in range(3, 0, -1):
            text(c, w, 0, -j * size * 0.95 * (1 - ease_out_expo(k)) - j * 8 * U, size=size, font="display",
                 fill=skia.ColorTRANSPARENT, stroke=3 * U, stroke_col=WHITE, alpha=0.18 * j / 3 + 0.08)
        slam(c, w, 0, 0, k, size, fill=WHITE, from_scale=1.5)
        c.restore()


def hanger(c, x, y, swing):
    c.save()
    c.translate(x, y)
    c.rotate(swing)
    p = fpaint(INK, stroke=6 * U)
    hook = skia.Path()
    hook.moveTo(0, 30 * U)
    hook.lineTo(0, 12 * U)
    hook.arcTo(skia.Rect.MakeXYWH(-14 * U, -16 * U, 28 * U, 28 * U), 90, -270, False)
    c.drawPath(hook, p)
    tri = skia.Path()
    tri.moveTo(-95 * U, 85 * U)
    tri.lineTo(0, 30 * U)
    tri.lineTo(95 * U, 85 * U)
    tri.close()
    c.drawPath(tri, p)
    c.restore()


def s_problem(c, t, lt, dur):
    c.clear(STONE)
    bi, bl = beat_of(lt)
    rail_y = 380 * U
    c.drawRect(skia.Rect.MakeXYWH(60 * U, rail_y - 6 * U, W - 120 * U, 12 * U), skia.Paint(Color=INK, AntiAlias=True))
    kinds = [("tee", HEX["camel"]), ("dress", HEX["red"]), ("blazer", HEX["ink"]), ("hoodie", HEX["sage"]),
             ("jeans", HEX["denim"])]
    n = len(kinds)
    for i, (kind, col) in enumerate(kinds):
        x = W / 2 + (i - (n - 1) / 2) * 196 * U
        swing = 5 * math.sin(t * 5 + i)
        hanger(c, x, rail_y + 14 * U, swing)
        kd = prog(lt, 6 * BEAT + i * 0.08, 0.5)
        if kd > 0:
            drop = (1 - ease_out_bounce(kd)) * -600 * U
            c.save()
            c.translate(x, rail_y + 14 * U)
            c.rotate(swing)
            garment(c, kind, 0, 230 * U + drop, 300 * U, col)
            c.restore()
    # words
    words = TL.COPY["problem"]
    size = 170 * U
    y0 = 960 * U
    fix = prog(lt, 5 * BEAT, 0.2)
    for i, w in enumerate(words):
        y = y0 + i * size * 1.08
        k = prog(lt, i * BEAT, 0.18)
        if i == 0 and fix > 0:
            fall = ease_in_cubic(prog(lt, 5 * BEAT, 0.35))
            c.save()
            c.translate(W / 2, y - fall * 500 * U)
            c.rotate(-fall * 25)
            text(c, w, 0, 0, size=fit(w, "display", W * 0.86, size), font="display", fill=GREY,
                 alpha=clamp(1 - fall * 5))
            c.restore()
            sz = fit(TL.COPY["problem_fix"], "display", W * 0.86, size)
            slam(c, TL.COPY["problem_fix"], W / 2, y, fix, sz, fill=RED, from_scale=2.2)
            continue
        if i == 2 and fix > 0:
            w = "WEAR."
        slam(c, w, W / 2, y, k, fit(w, "display", W * 0.86, size), fill=INK)
        if i == 0:                                         # red strike-through on beat 4
            ks = ease_out_expo(prog(lt, 4 * BEAT, 0.22))
            if ks > 0:
                tw = text_width(w, fit(w, "display", W * 0.86, size), "display") + 40 * U
                c.drawRect(skia.Rect.MakeXYWH(W / 2 - tw / 2, y - 10 * U, tw * ks, 22 * U), skia.Paint(Color=RED))


def logo(c, x, y, size, col, alpha=1.0):
    text(c, "H&M", x, y, size=size, font="serif", fill=col, alpha=alpha)


def s_reveal(c, t, lt, dur):
    c.clear(STONE)
    k = ease_out_expo(prog(lt, 0, 0.3))
    c.drawCircle(W / 2, H / 2, k * math.hypot(W, H) * 0.6, fpaint(RED))
    kl = prog(lt, 0.02, 0.22)
    bump = 1 + 0.04 * pulse(t, TL.BPM)
    c.save()
    c.translate(W / 2, H / 2 - 60 * U)
    c.scale(bump, bump)
    slam(c, "H&M", 0, 0, kl, 360 * U, font="serif", fill=WHITE, from_scale=2.6)
    c.restore()
    sub = TL.COPY["reveal_sub"]
    ks = ease_out_cubic(prog(lt, 2 * BEAT, 0.3))
    if ks > 0:
        sz = 54 * U
        text(c, sub, W / 2, H / 2 + 200 * U + (1 - ks) * 40 * U, size=sz, font="body", fill=WHITE, alpha=ks,
             tracking=0.3)
        lw = ease_out_expo(prog(lt, 2 * BEAT + 0.1, 0.4)) * 300 * U
        c.drawRect(skia.Rect.MakeXYWH(W / 2 - lw / 2, H / 2 + 260 * U, lw, 4 * U), skia.Paint(Color=WHITE))


# ---------- the interactive site (phone)
PX, PW = (W - 720 * U) / 2, 720 * U
PY_REST = 560 * U
SX_IN, SY_IN = 18 * U, 18 * U
SW = PW - 2 * SX_IN
NAV_TOP, CONTENT_TOP = 150 * U, 220 * U         # inside the screen
HERO_H = 520 * U
GAP = 16 * U
TILE_W = (SW - 3 * GAP) / 2
TILE_IMG = 330 * U
TILE_H = TILE_IMG + 70 * U
SCROLL = HERO_H + 8 * U
PRODUCTS = [("blazer", HEX["camel"]), ("dress", HEX["red"]), ("jeans", HEX["denim"]), ("tee", HEX["cream"])]


def tile_xy(i):
    """top-left of product image i in content coords."""
    col, row = i % 2, i // 2
    return GAP + col * (TILE_W + GAP), HERO_H + 24 * U + row * (TILE_H + 8 * U)


def heart(c, x, y, s, filled, col):
    p = skia.Path()
    p.moveTo(x, y + s * 0.35)
    p.cubicTo(x - s * 0.9, y - s * 0.25, x - s * 0.35, y - s * 0.85, x, y - s * 0.3)
    p.cubicTo(x + s * 0.35, y - s * 0.85, x + s * 0.9, y - s * 0.25, x, y + s * 0.35)
    p.close()
    c.drawPath(p, fpaint(col) if filled else fpaint(col, stroke=3 * U))


def bag_icon(c, x, y, s, col):
    rrect(c, x - s * 0.45, y - s * 0.25, s * 0.9, s * 0.75, 3 * U, col, stroke=3.5 * U)
    c.drawArc(skia.Rect.MakeXYWH(x - s * 0.22, y - s * 0.55, s * 0.44, s * 0.6), 180, 180, False,
              fpaint(col, stroke=3.5 * U))


def app_layout(py):
    """absolute tap targets for the current phone position."""
    sx, sy = PX + SX_IN, py + SY_IN
    tabs = TL.COPY["tabs"]
    tx = sx + 28 * U
    tab_x = []
    for tb in tabs:
        tw = text_width(tb, 24 * U, "body", 0.06)
        tab_x.append((tx, tw))
        tx += tw + 34 * U
    ct = sy + CONTENT_TOP - SCROLL

    def plus(i):
        x, y = tile_xy(i)
        return sx + x + TILE_W - 38 * U, ct + y + TILE_IMG - 38 * U

    def heart_xy(i):
        x, y = tile_xy(i)
        return sx + x + TILE_W - 38 * U, ct + y + 38 * U

    return {
        "women": (tab_x[0][0] + tab_x[0][1] / 2, sy + NAV_TOP + 34 * U),
        "heart0": heart_xy(0), "plus1": plus(1), "plus2": plus(2), "plus3": plus(3),
        "bag": (sx + SW - 50 * U, sy + 100 * U),
        "checkout": (sx + SW / 2, sy + 1030 * U),
        "tab_x": tab_x,
    }


# (local beat, target) for the finger
TAPS = [(2, "women"), (6, "heart0"), (7, "plus1"), (8, "plus2"), (9, "plus3"), (10, "bag"), (12, "checkout")]


def tapped(lt, beat_n):
    return lt >= beat_n * BEAT


def draw_screen(c, lt, sx, sy):
    """the H&M site UI inside the phone screen (absolute coords)."""
    c.drawRect(skia.Rect.MakeXYWH(sx, sy, SW, 2000 * U), skia.Paint(Color=WHITE))
    lay = app_layout(sy - SY_IN)
    # content (clipped under the header)
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(sx, sy + CONTENT_TOP, SW, 2000 * U))
    page = ease_in_out_cubic(prog(lt, 2 * BEAT + 0.05, 0.3))            # landing -> WOMEN page
    scroll = ease_in_out_cubic(prog(lt, 4 * BEAT, 0.55)) * SCROLL
    # landing page (slides out left)
    if page < 1:
        ox = -page * SW
        hx, hy = sx + ox, sy + CONTENT_TOP
        c.drawRect(skia.Rect.MakeXYWH(hx, hy, SW, HERO_H + 600 * U), skia.Paint(Color=rgb(HEX["blush"])))
        garment(c, "hoodie", hx + SW * 0.68, hy + 280 * U, 360 * U, HEX["sage"])
        garment(c, "kids", hx + SW * 0.25, hy + 330 * U, 230 * U, HEX["cream"])
        text(c, "The new season", hx + 36 * U, hy + 80 * U, size=46 * U, font="body", fill=INK, align="left")
        text(c, "is here", hx + 36 * U, hy + 132 * U, size=46 * U, font="body", fill=INK, align="left")
    # WOMEN page (slides in from right), scrolls
    ox = (1 - page) * SW
    cx0, cy0 = sx + ox, sy + CONTENT_TOP - scroll
    c.drawRect(skia.Rect.MakeXYWH(cx0, cy0, SW, HERO_H), skia.Paint(Color=rgb(HEX["sand"])))
    garment(c, "dress", cx0 + SW * 0.3, cy0 + 300 * U, 420 * U, HEX["red"])
    garment(c, "blazer", cx0 + SW * 0.72, cy0 + 290 * U, 400 * U, HEX["ink"])
    text(c, "Women", cx0 + 36 * U, cy0 + 70 * U, size=28 * U, font=REGULAR, fill=INK, align="left")
    text(c, "New Arrivals", cx0 + 36 * U, cy0 + 118 * U, size=50 * U, font="body", fill=INK, align="left")
    bx, by = cx0 + 36 * U, cy0 + HERO_H - 100 * U
    c.drawRect(skia.Rect.MakeXYWH(bx, by, 200 * U, 64 * U), skia.Paint(Color=INK))
    text(c, "Shop now", bx + 100 * U, by + 32 * U, size=26 * U, font="body", fill=WHITE)
    names = TL.COPY["products"]
    for i, (kind, col) in enumerate(PRODUCTS):
        x, y = tile_xy(i)
        x, y = cx0 + x, cy0 + y
        c.drawRect(skia.Rect.MakeXYWH(x, y, TILE_W, TILE_IMG), skia.Paint(Color=rgb(HEX["sand"])))
        garment(c, kind, x + TILE_W / 2, y + TILE_IMG / 2 + 6 * U, TILE_IMG * 0.8, col)
        text(c, names[i], x + 4 * U, y + TILE_IMG + 30 * U, size=24 * U, font=REGULAR, fill=INK, align="left")
        # colour dots
        for j, dc in enumerate((col, HEX["ink"], HEX["cream"])):
            c.drawCircle(x + 14 * U + j * 26 * U, y + TILE_IMG + 60 * U, 8 * U, fpaint(rgb(dc)))
        # heart (tile 0 gets loved)
        hx, hy = x + TILE_W - 38 * U, y + 38 * U
        loved = i == 0 and tapped(lt, 6)
        kp = ease_out_back(prog(lt, 6 * BEAT, 0.3)) if loved else 1
        heart(c, hx, hy, 22 * U * (0.6 + 0.4 * kp + 0.25 * math.sin(math.pi * clamp(kp))), loved,
              RED if loved else INK)
        # quick-add +
        px, py = x + TILE_W - 62 * U, y + TILE_IMG - 62 * U
        added = i > 0 and tapped(lt, 6 + i)
        c.drawRect(skia.Rect.MakeXYWH(px, py, 48 * U, 48 * U), skia.Paint(Color=INK if added else WHITE))
        pc = WHITE if added else INK
        if added:
            line(c, px, py, U, [(13, 25), (21, 33), (35, 16)], pc, 4 * U)
        else:
            c.drawRect(skia.Rect.MakeXYWH(px + 14 * U, py + 22 * U, 20 * U, 4 * U), skia.Paint(Color=pc))
            c.drawRect(skia.Rect.MakeXYWH(px + 22 * U, py + 14 * U, 4 * U, 20 * U), skia.Paint(Color=pc))
    c.restore()

    # header: status bar, menu, logo, icons
    c.drawRect(skia.Rect.MakeXYWH(sx, sy, SW, CONTENT_TOP), skia.Paint(Color=WHITE))
    text(c, "9:41", sx + 60 * U, sy + 34 * U, size=24 * U, font="body", fill=INK)
    for i in range(3):
        c.drawRect(skia.Rect.MakeXYWH(sx + 28 * U, sy + 82 * U + i * 13 * U, 34 * U, 4 * U), skia.Paint(Color=INK))
    logo(c, sx + SW / 2, sy + 100 * U, 64 * U, RED)
    c.drawCircle(sx + SW - 160 * U, sy + 96 * U, 13 * U, fpaint(INK, stroke=3.5 * U))
    line(c, sx + SW - 160 * U, sy + 96 * U, U, [(9, 9), (19, 19)], INK, 3.5 * U)
    heart(c, sx + SW - 105 * U, sy + 98 * U, 17 * U, tapped(lt, 6), RED if tapped(lt, 6) else INK)
    bxc, byc = sx + SW - 50 * U, sy + 98 * U
    bag_icon(c, bxc, byc, 36 * U, INK)
    count = sum(1 for n in (7, 8, 9) if tapped(lt, n))
    if count:
        last = max(n for n in (7, 8, 9) if tapped(lt, n))
        kb = ease_out_back(prog(lt, last * BEAT + 0.05, 0.3))
        r = 15 * U * (0.5 + 0.5 * kb + 0.3 * math.sin(math.pi * clamp(kb)))
        c.drawCircle(bxc + 18 * U, byc - 18 * U, r, fpaint(RED))
        text(c, str(count), bxc + 18 * U, byc - 18 * U, size=r * 1.3, font="body", fill=WHITE)
    # nav tabs + active underline
    for i, (tx, tw) in enumerate(lay["tab_x"]):
        active = i == 0 and page > 0.5
        text(c, TL.COPY["tabs"][i], tx, sy + NAV_TOP + 34 * U, size=24 * U, font="body" if active else REGULAR,
             fill=INK, align="left", tracking=0.06)
    ku = ease_out_expo(prog(lt, 2 * BEAT, 0.3))
    if ku > 0:
        tx, tw = lay["tab_x"][0]
        c.drawRect(skia.Rect.MakeXYWH(tx, sy + NAV_TOP + 56 * U, tw * ku, 4 * U), skia.Paint(Color=INK))
    c.drawRect(skia.Rect.MakeXYWH(sx, sy + CONTENT_TOP - 2 * U, SW, 2 * U), skia.Paint(Color=SAND))

    # toast "Added to bag"
    kt = prog(lt, 7 * BEAT + 0.05, 0.25)
    kt_out = prog(lt, 10 * BEAT - 0.2, 0.2)
    if 0 < kt and kt_out < 1:
        ty = sy + 860 * U + (1 - ease_out_back(kt)) * 200 * U + ease_in_cubic(kt_out) * 300 * U
        c.drawRect(skia.Rect.MakeXYWH(sx + 24 * U, ty, SW - 48 * U, 84 * U), skia.Paint(Color=INK))
        line(c, sx + 50 * U, ty + 26 * U, U, [(0, 16), (10, 26), (30, 4)], WHITE, 4 * U)
        text(c, f"Added to bag ({count})", sx + 100 * U, ty + 42 * U, size=28 * U, font="body", fill=WHITE,
             align="left")

    # bag drawer
    kd = ease_out_expo(prog(lt, 10 * BEAT + 0.08, 0.4))
    if kd > 0:
        dy = sy + 120 * U + (1 - kd) * 1300 * U
        c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Color=skia.Color(0, 0, 0, int(90 * kd))))
        c.drawRect(skia.Rect.MakeXYWH(sx, dy, SW, 2000 * U), skia.Paint(Color=WHITE))
        text(c, "Shopping bag (3)", sx + 36 * U, dy + 70 * U, size=36 * U, font="body", fill=INK, align="left")
        for j, i in enumerate((1, 2, 3)):
            kind, col = PRODUCTS[i]
            ry = dy + 130 * U + j * 190 * U
            c.drawRect(skia.Rect.MakeXYWH(sx + 36 * U, ry, 140 * U, 170 * U), skia.Paint(Color=SAND))
            garment(c, kind, sx + 106 * U, ry + 88 * U, 140 * U, col)
            text(c, names[i], sx + 200 * U, ry + 50 * U, size=28 * U, font="body", fill=INK, align="left")
            text(c, "Size M  ·  Qty 1", sx + 200 * U, ry + 94 * U, size=24 * U, font=REGULAR, fill=GREY,
                 align="left")
        # checkout button (presses on beat 12)
        press = tapped(lt, 12)
        bw, bh = SW - 72 * U, 92 * U
        bx, by = sx + 36 * U, sy + 1030 * U - bh / 2 + (1 - kd) * 1300 * U
        c.drawRect(skia.Rect.MakeXYWH(bx, by, bw, bh), skia.Paint(Color=RED if press else INK))
        text(c, "Continue to checkout", bx + bw / 2, by + bh / 2, size=30 * U, font="body", fill=WHITE)

    # success
    ks = prog(lt, 13 * BEAT, 0.35)
    if ks > 0:
        c.drawRect(skia.Rect.MakeXYWH(sx, sy, SW, 2000 * U), skia.Paint(Color=skia.Color(255, 255, 255,
                                                                                          int(255 * clamp(ks * 3)))))
        ccx, ccy = sx + SW / 2, sy + 520 * U
        c.drawCircle(ccx, ccy, 120 * U * ease_out_back(ks), fpaint(RED))
        kc = ease_out_cubic(prog(lt, 13 * BEAT + 0.15, 0.3))
        if kc > 0:
            p = skia.Path()
            pts = [(-52, 2), (-14, 40), (56, -36)]
            p.moveTo(ccx + pts[0][0] * U, ccy + pts[0][1] * U)
            seg = kc * 2
            p.lineTo(ccx + lerp(pts[0][0], pts[1][0], min(1, seg)) * U, ccy + lerp(pts[0][1], pts[1][1], min(1, seg)) * U)
            if seg > 1:
                p.lineTo(ccx + lerp(pts[1][0], pts[2][0], seg - 1) * U, ccy + lerp(pts[1][1], pts[2][1], seg - 1) * U)
            c.drawPath(p, fpaint(WHITE, stroke=16 * U))
        kt2 = ease_out_cubic(prog(lt, 13 * BEAT + 0.25, 0.3))
        text(c, "Order confirmed", ccx, ccy + 200 * U + (1 - kt2) * 30 * U, size=44 * U, font="body", fill=INK,
             alpha=kt2)
        text(c, "Thanks for shopping with us", ccx, ccy + 260 * U, size=26 * U, font=REGULAR, fill=GREY, alpha=kt2)
    return lay


def finger(c, lt, lay):
    """tap indicator: glides between targets, ripples on each tap."""
    pos = None
    for j, (bn, key) in enumerate(TAPS):
        tt = bn * BEAT
        x, y = lay[key]
        if j == 0:
            if lt < tt - 0.35:
                return
            k = ease_out_cubic(prog(lt, tt - 0.35, 0.3))
            pos = (lerp(W * 0.9, x, k), lerp(H * 0.95, y, k))
        if lt >= tt - 0.3:
            if j > 0:
                px_, py_ = lay[TAPS[j - 1][1]]
                k = ease_in_out_cubic(prog(lt, tt - 0.3, 0.25))
                pos = (lerp(px_, x, k), lerp(py_, y, k))
        d = lt - tt
        if 0 <= d < 0.4:                                  # ripple
            r = lerp(20, 90, ease_out_cubic(d / 0.4)) * U
            c.drawCircle(x, y, r, fpaint(skia.Color(229, 0, 16, int(200 * (1 - d / 0.4))), stroke=6 * U))
    if pos is None or lt > TAPS[-1][0] * BEAT + 0.5:
        return
    press = any(0 <= lt - bn * BEAT < 0.12 for bn, _ in TAPS)
    r = (30 if press else 36) * U
    c.drawCircle(pos[0], pos[1], r, fpaint(skia.Color(34, 34, 34, 120)))
    c.drawCircle(pos[0], pos[1], r, fpaint(WHITE, stroke=4 * U))


def caption(c, lt, caps, y, max_size=170 * U, last_red=True, color=INK):
    """big kinetic caption track: each word slams on its beat and replaces the last."""
    cur = None
    for i, (bn, w) in enumerate(caps):
        if lt >= bn * BEAT:
            cur = (i, bn, w)
    if cur is None:
        return
    i, bn, w = cur
    k = prog(lt, bn * BEAT, 0.18)
    size = fit(w, "display", W * 0.86, max_size)
    col = RED if (last_red and i == len(caps) - 1) else color
    bump = 1 + 0.035 * pulse(lt, TL.BPM)
    c.save()
    c.translate(W / 2, y)
    c.scale(bump, bump)
    slam(c, w, 0, 0, k, size, fill=col, rot=-5 if i % 2 else 5)
    c.restore()


def s_app(c, t, lt, dur):
    c.clear(STONE)
    # moving brand stripes in the background
    off = (lt * 120 * U) % (160 * U)
    for i in range(-2, 16):
        y = i * 160 * U + off
        c.drawRect(skia.Rect.MakeXYWH(0, y, W, 2 * U), skia.Paint(Color=SAND))
    kin = ease_out_expo(prog(lt, 0, 0.5))
    kout = ease_in_back(prog(lt, dur - 0.25, 0.25))
    py = lerp(H, PY_REST, kin) + kout * 300 * U
    # gentle push-in on the screen during interaction
    zoom = 1 + 0.04 * ease_in_out_cubic(prog(lt, 4 * BEAT, 8 * BEAT))
    c.save()
    c.translate(W / 2, py + 500 * U)
    c.scale(zoom, zoom)
    c.translate(-W / 2, -(py + 500 * U))
    shadow(c, PX, py, PW, 1600 * U, 90 * U, blur=40 * U, dy=30 * U, alpha=0.25)
    rrect(c, PX, py, PW, 1600 * U, 90 * U, INK)
    c.save()
    c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(PX + SX_IN, py + SY_IN, SW, 1600 * U), 72 * U, 72 * U))
    lay = draw_screen(c, lt, PX + SX_IN, py + SY_IN)
    c.restore()
    rrect(c, W / 2 - 80 * U, py + 34 * U, 160 * U, 36 * U, 18 * U, INK)            # notch
    finger(c, lt, lay)
    c.restore()
    caption(c, lt, TL.COPY["app_caps"], 400 * U, max_size=160 * U)


MONTAGE = [  # (bg, fg, garment, colour)
    (SAND, INK, "dress", HEX["red"]),
    (INK, WHITE, "blazer", HEX["camel"]),
    (RED, WHITE, "kids", HEX["cream"]),
    (STONE, INK, "vase", HEX["cream"]),
    (INK, WHITE, "lipstick", HEX["red"]),
    (RED, WHITE, "sneaker", HEX["paper"]),
]


def s_montage(c, t, lt, dur):
    bi, bl = beat_of(lt)
    if bi < 6:
        bg, fg, kind, col = MONTAGE[bi]
        c.clear(bg)
        word = TL.COPY["categories"][bi]
        k = prog(bl, 0, 0.16)
        size = fit(word, "display", W * 0.88, 260 * U)
        # giant garment punches in from below
        kg = ease_out_back(prog(bl, 0.02, 0.3))
        c.save()
        c.translate(W / 2, 1150 * U + (1 - kg) * 500 * U)
        c.rotate((1 - kg) * (12 if bi % 2 else -12) + 3 * math.sin(lt * 8))
        garment(c, kind, 0, 0, 640 * U * (0.9 + 0.1 * kg) * (1.45 if kind == "lipstick" else 1), col)
        c.restore()
        slam(c, word, W / 2, 560 * U, k, size, fill=fg, from_scale=1.7)
        text(c, f"0{bi + 1} / 06", 80 * U, 330 * U, size=30 * U, font="body", fill=fg, align="left", tracking=0.1)
        text(c, "SHOP →", W - 80 * U, 330 * U, size=30 * U, font="body", fill=fg, align="right", tracking=0.1)
    else:
        j = bi - 6
        cur = None
        for idx, (bn, lines) in enumerate(TL.COPY["promise"]):
            if j >= bn:
                cur = (idx, bn, lines)
        idx, bn, lines = cur
        bgs = [WHITE, RED, INK, WHITE, RED]
        bg = bgs[idx]
        fg = WHITE if bg != WHITE else INK
        c.clear(bg)
        kloc = lt - (6 + bn) * BEAT
        size = min(fit(w, "display", W * 0.86, 330 * U) for w in lines)
        for li, w in enumerate(lines):
            y = H / 2 - (len(lines) - 1) * size * 0.55 + li * size * 1.1
            k = prog(kloc, li * BEAT * 0.5, 0.16)
            slam(c, w, W / 2, y, k, size, fill=fg, rot=-6 if li else 6, from_scale=2.0)


OUT_TOPS = [("tee", HEX["camel"]), ("blazer", HEX["ink"]), ("hoodie", HEX["sage"]), ("tee", HEX["red"]),
            ("blazer", HEX["camel"]), ("hoodie", HEX["blush"]), ("tee", HEX["paper"]), ("blazer", HEX["red"])]
OUT_BOTS = [("jeans", HEX["denim"]), ("skirt", HEX["ink"]), ("jeans", HEX["camel"]), ("jeans", HEX["ink"])]


def s_outfit(c, t, lt, dur):
    c.clear(STONE)
    bi, bl = beat_of(lt)
    bi = min(bi, 7)
    cx = W / 2
    # stage disc
    c.drawOval(skia.Rect.MakeXYWH(cx - 300 * U, 1370 * U, 600 * U, 70 * U), fpaint(SAND))
    # mannequin
    skin = rgb(HEX["skin"])
    c.drawCircle(cx, 600 * U, 62 * U, fpaint(skin))
    rrect(c, cx - 22 * U, 640 * U, 44 * U, 60 * U, 10 * U, skin)
    # bottoms swap every 2 beats, tops every beat; new piece slides in sideways
    bk, bc = OUT_BOTS[(bi // 2) % len(OUT_BOTS)]
    kb = ease_out_expo(prog(lt, (bi // 2) * 2 * BEAT, 0.22))
    dirb = 1 if (bi // 2) % 2 else -1
    garment(c, bk, cx + (1 - kb) * dirb * 700 * U, 1150 * U, 500 * U, bc)
    garment(c, "sneaker", cx - 70 * U, 1395 * U, 150 * U, HEX["paper"])
    garment(c, "sneaker", cx + 80 * U, 1395 * U, 150 * U, HEX["paper"])
    tk, tc = OUT_TOPS[bi]
    kt = ease_out_expo(prog(bl, 0, 0.2))
    dirt = 1 if bi % 2 else -1
    if kt < 1 and bi > 0:                                  # previous top leaves
        pk, pc = OUT_TOPS[bi - 1]
        garment(c, pk, cx - kt * dirt * 900 * U, 900 * U, 540 * U, pc)
    garment(c, tk, cx + (1 - kt) * dirt * 900 * U, 900 * U, 540 * U, tc)
    # arrow controls with a tap on every beat
    for side in (-1, 1):
        ax = cx + side * 430 * U
        hit = (side == 1) == (bi % 2 == 0)
        pr = 0.85 if hit and bl < 0.1 else 1.0
        c.drawCircle(ax, 900 * U, 48 * U * pr, fpaint(WHITE))
        c.drawCircle(ax, 900 * U, 48 * U * pr, fpaint(INK, stroke=3 * U))
        line(c, ax, 900 * U, U, [(-8 * side, -16), (8 * side, 0), (-8 * side, 16)], INK, 5 * U)
        if hit and bl < 0.35:
            r = lerp(48, 110, ease_out_cubic(bl / 0.35)) * U
            c.drawCircle(ax, 900 * U, r, fpaint(skia.Color(229, 0, 16, int(200 * (1 - bl / 0.35))), stroke=5 * U))
    # swatches showing the current colour
    sw = [c_ for _, c_ in OUT_TOPS[:6]]
    for i, sc in enumerate(sw):
        x = cx + (i - 2.5) * 86 * U
        c.drawCircle(x, 1490 * U, 26 * U, fpaint(rgb(sc)))
        c.drawCircle(x, 1490 * U, 26 * U, fpaint(SAND, stroke=2 * U))
        if OUT_TOPS[bi][1] == sc:
            c.drawCircle(x, 1490 * U, 36 * U, fpaint(INK, stroke=4 * U))
    caption(c, lt, TL.COPY["outfit_caps"], 380 * U, max_size=170 * U)


def s_endcard(c, t, lt, dur):
    c.clear(WHITE)
    bump = 1 + 0.03 * pulse(t, TL.BPM)
    kl = prog(lt, 0.0, 0.22)
    c.save()
    c.translate(W / 2, 760 * U)
    c.scale(bump, bump)
    slam(c, "H&M", 0, 0, kl, 330 * U, font="serif", fill=RED, from_scale=3.0)
    c.restore()
    ks = ease_out_cubic(prog(lt, BEAT, 0.3))
    sub = TL.COPY["end_sub"]
    text(c, sub, W / 2, 1000 * U + (1 - ks) * 30 * U, size=fit(sub, "body", W * 0.8, 54 * U, 0.2), font="body",
         fill=INK, alpha=ks, tracking=0.2)
    # SHOP NOW button: pops in, finger taps on beat 4, inverts to red
    kb = ease_out_back(prog(lt, 2 * BEAT, 0.35))
    if kb > 0:
        press = lt >= 4 * BEAT
        bw, bh = 520 * U * kb, 130 * U
        bx, by = W / 2 - bw / 2, 1130 * U
        sq = 0.94 if press and lt < 4 * BEAT + 0.1 else 1.0
        c.save()
        c.translate(W / 2, by + bh / 2)
        c.scale(sq, sq)
        c.drawRect(skia.Rect.MakeXYWH(-bw / 2, -bh / 2, bw, bh), skia.Paint(Color=RED if press else INK))
        text(c, TL.COPY["cta"], 0, 0, size=52 * U * kb, font="body", fill=WHITE, tracking=0.16)
        c.restore()
        # finger
        fk = ease_out_cubic(prog(lt, 4 * BEAT - 0.4, 0.35))
        if lt > 4 * BEAT - 0.4 and lt < 5.5 * BEAT:
            fx, fy = lerp(W * 0.85, W / 2 + 150 * U, fk), lerp(H * 0.85, by + bh / 2, fk)
            c.drawCircle(fx, fy, 36 * U, fpaint(skia.Color(34, 34, 34, 120)))
            c.drawCircle(fx, fy, 36 * U, fpaint(WHITE, stroke=4 * U))
        d = lt - 4 * BEAT
        if 0 <= d < 0.5:
            r = lerp(40, 220, ease_out_cubic(d / 0.5)) * U
            c.drawCircle(W / 2 + 150 * U, by + bh / 2, r,
                         fpaint(skia.Color(229, 0, 16, int(200 * (1 - d / 0.5))), stroke=6 * U))
    ku = ease_out_cubic(prog(lt, 5 * BEAT, 0.3))
    text(c, TL.COPY["url"], W / 2, 1360 * U, size=40 * U, font=REGULAR, fill=GREY, alpha=ku, tracking=0.05)


SCENES = {"hook": s_hook, "problem": s_problem, "reveal": s_reveal, "app": s_app, "montage": s_montage,
          "outfit": s_outfit, "endcard": s_endcard}


def draw(c, t):
    name, lt, dur = TL.scene_at(t)
    dx, dy = shake_offset(t)
    c.save()
    c.translate(dx, dy)
    SCENES[name](c, t, lt, dur)
    c.restore()
    flash(c, t)


def build_audio():
    Path("work").mkdir(exist_ok=True)
    ak.write_wav("work/music.wav", ak.music_bed(TL.MOOD, seconds=TL.DURATION, bpm=TL.BPM, intro_bars=0))
    Path("work/cues.json").write_text(json.dumps(TL.cues(), indent=1))
    import subprocess
    subprocess.run([sys.executable, "vibe/audio_kit.py", "mix", "work/cues.json", "-o", "work/mix.wav"], check=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stills"
    if cmd == "stills":
        times = [float(x) for x in sys.argv[2:]] or [s + (e - s) * 0.6 for s, e, _ in TL.SCENES]
        S.stills(draw, times)
    elif cmd == "audio":
        build_audio()
    elif cmd == "draft":
        S.render(draw, "out/draft.mp4", audio="work/mix.wav", draft=True)
    elif cmd == "render":
        if not Path("work/mix.wav").exists():
            build_audio()
        suffix = f"_{TL.W}x{TL.H}" if os.environ.get("VIBE_SIZE") else ""
        S.render(draw, f"out/hm-ad_v1{suffix}.mp4", audio="work/mix.wav")
    else:
        sys.exit(__doc__)
