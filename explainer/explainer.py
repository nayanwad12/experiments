"""'How Vibe Editing works' — 47 s neo-brutalist explainer (1080x1920, 30 fps, 120 BPM).

    python3 explainer.py stills 2 7 ...   -> out/stills/*.png
    python3 explainer.py                  -> out/explainer.mp4
"""

import math
import os
import random
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
import skia
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

from brut import (BLUSH, BLUSH_D, CREAM, H, ICE, INK, LIME, PERI, PERI_D, W, WHITE, arrow, box, check, circle, clamp,
                  col, cursor, eio, eob, eoc, grid_bg, label, lerp, paint, poly, pop, popc, push, slide, text, tw,
                  window, xmark)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "vibe-editing-promo"))
import audio as A  # noqa: E402
import imageio_ffmpeg  # noqa: E402

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
OUT = os.path.join(HERE, "out")
FPS = 30
BPM = 120
BEAT = 60 / BPM
DUR = 47.0

# (start, end, name, wipe colour)
SCENES = [
    (0.0, 4.0, "title", None),
    (4.0, 10.0, "oldway", BLUSH),
    (10.0, 15.5, "record", LIME),
    (15.5, 25.5, "describe", PERI),
    (25.5, 33.0, "direct", ICE),
    (33.0, 38.5, "result", LIME),
    (38.5, 42.5, "make", BLUSH),
    (42.5, 47.0, "cta", PERI),
]
S = {n: s for s, e, n, _ in SCENES}


def rnd(*k):
    return random.Random(":".join(map(str, k)))


# ------------------------------------------------------------------ shared bits
def step_header(c, t, num, title, color):
    s = pop(t, 0.0, 0.35)
    push(c, 160, 290, -6 * (1 - s), s)
    circle(c, 0, 0, 82, color, sh=10)
    text(c, str(num), 0, 4, 110, INK, "black")
    popc(c)
    k = slide(t, 0.12, 0.35)
    push(c, lerp(1300, 0, k), 0)
    text(c, f"STEP {num} OF 3", 272, 232, 30, INK, "mono", align="l")
    text(c, title, 270, 312, 86, INK, "head", align="l")
    popc(c)


def progress(c, t):
    x0, x1, y = 60, W - 60, 70
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(x0, y - 9, x1, y + 9), 9, 9), paint(WHITE))
    k = clamp(t / DUR)
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(x0, y - 9, lerp(x0 + 18, x1, k), y + 9), 9, 9),
                paint(INK))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(x0, y - 9, x1, y + 9), 9, 9), paint(INK, stroke=4))


# ------------------------------------------------------------------ 1 TITLE
def s_title(c, t):
    grid_bg(c, t)
    s = pop(t, 0.0, 0.45)
    push(c, 540, 860, 0, lerp(0.7, 1.0, s) if s < 1 else s)
    window(c, 0, 0, 920, 900, "explainer.mp4", bar=LIME)
    popc(c)
    for word, y, t0, size in (("HOW", 620, 0.25, 160), ("WORKS", 1040, 0.75, 160)):
        sc = pop(t, t0, 0.3)
        if sc > 0:
            push(c, 540, y, 0, sc)
            text(c, word, 0, 0, size, INK, "black")
            popc(c)
    k = eoc((t - 0.45) / 0.3) if t > 0.45 else 0
    if k > 0:
        wdt = (tw("VIBE EDITING", 112, "black") + 70) * k
        push(c, 540, 830, -2)
        box(c, -((tw("VIBE EDITING", 112, "black") + 70) - wdt) / 2, 0, wdt, 170, PERI, r=16, sh=10)
        if k > 0.6:
            text(c, "VIBE EDITING", 0, 2, 112, INK, "black")
        popc(c)
    if t > 1.0:  # hand-drawn underline
        k = eoc((t - 1.0) / 0.35)
        p = skia.Path()
        pts = [(300 + i * 20, 1135 + math.sin(i * 1.3) * 10) for i in range(int(25 * k) + 1)]
        p.moveTo(*pts[0])
        for q in pts[1:]:
            p.lineTo(*q)
        c.drawPath(p, paint(BLUSH_D, stroke=14))
    label(c, "IN 3 STEPS", 790, 1235, 54, BLUSH, rot=7, sc=pop(t, 1.2, 0.3))
    names = ["RECORD", "DESCRIBE", "DIRECT"]
    cols = [LIME, BLUSH, ICE]
    for i in range(3):
        x = 220 + i * 320
        s = pop(t, 1.6 + i * 0.15, 0.3)
        if s <= 0:
            continue
        push(c, x, 1480, 0, s)
        circle(c, 0, 0, 72, cols[i], sh=9)
        text(c, str(i + 1), 0, 4, 90, INK, "black")
        text(c, names[i], 0, 125, 40, INK, "mono")
        popc(c)
        if i < 2 and t > 2.1 + i * 0.12:
            k = eoc((t - 2.1 - i * 0.12) / 0.25)
            arrow(c, [(x + 90, 1480), (x + 90 + 140 * k, 1480)], INK, 9, 26)


# ------------------------------------------------------------------ 2 OLD WAY
def s_oldway(c, t):
    grid_bg(c, t)
    label(c, "THE OLD WAY", 540, 230, 64, BLUSH, sc=pop(t, 0.0, 0.3), rot=-2)
    s = pop(t, 0.12, 0.4)
    if s > 0:
        push(c, 540, 690, 0, lerp(0.8, 1.0, min(s, 1)) * (s if s < 1 else 1))
        window(c, 0, 0, 960, 620, "final_FINAL_v7.prproj", bar=BLUSH)
        c.save()
        c.clipRect(skia.Rect.MakeLTRB(-470, -230, 470, 300))
        cols = [PERI, LIME, ICE, BLUSH]
        for r in range(4):
            y = -170 + r * 115
            for i in range(-1, 20):
                x = -300 + i * 70 - (t * 160 * (1 + r * 0.3)) % 70
                wdt = 40 + (i * 37 + r * 11) % 40
                box(c, x, y, wdt, 80, cols[(i + r) % 4], r=8, sh=0, sw=4)
            box(c, -410, y, 90, 80, WHITE, r=8, sh=0, sw=4)
            text(c, ["V1", "V2", "A1", "A2"][r], -410, y, 34, INK, "mono")
        for i in range(8):  # keyframe diamonds
            x = -250 + i * 95 - (t * 160) % 95
            push(c, x, -225 + 115 * 0.5, 45)
            box(c, 0, 0, 22, 22, INK, r=3, sh=0, sw=0)
            popc(c)
        px = math.sin(t * 5) * 320
        c.drawLine(px, -230, px, 300, paint(BLUSH_D, stroke=7))
        poly(c, [(px - 20, -240), (px + 20, -240), (px, -210)], BLUSH_D, sh=0, sw=4)
        c.restore()
        popc(c)
    # clock counter
    k = eio((t - 0.6) / 3.0) if t > 0.6 else 0
    secs = int(4 * 3600 * k)
    s = pop(t, 0.4, 0.3)
    if s > 0:
        push(c, 540, 1140, 0, s)
        box(c, 0, 0, 640, 170, WHITE, r=20)
        text(c, f"{secs // 3600:02d}:{secs // 60 % 60:02d}:{secs % 60:02d}", 30, 0, 104, INK, "mono")
        circle(c, -255, 0, 40, ICE, sh=0, sw=5)
        a = t * 8
        c.drawLine(-255, 0, -255 + math.cos(a) * 26, math.sin(a) * 26, paint(INK, stroke=6))
        popc(c)
    for i, item in enumerate(["200 MANUAL CUTS", "EVERY CAPTION BY HAND", "KEYFRAME HELL"]):
        k = slide(t, 1.4 + i * 0.45, 0.35)
        if k <= 0:
            continue
        push(c, lerp(-900, 0, k), 0)
        xmark(c, 150, 1370 + i * 115, 1.1)
        text(c, item, 205, 1370 + i * 115, 56, INK, "head", align="l")
        popc(c)
    if t > 3.8:
        d = t - 3.8
        s = lerp(1.7, 1.0, eoc(d / 0.12)) if d < 0.12 else 1.0
        label(c, "4 HRS PER REEL", 540, 690, 100, INK, LIME, "black", rot=-8, sc=s, sh=14, sw=0, r=26)


# ------------------------------------------------------------------ 3 RECORD
def s_record(c, t):
    grid_bg(c, t)
    step_header(c, t, 1, "RECORD RAW", LIME)
    y = lerp(1900, 950, eob((t - 0.15) / 0.45)) if t > 0.15 else 3000
    push(c, 540, y, -3 * math.sin(t * 1.5))
    box(c, 0, 0, 500, 900, INK, r=64, sh=16, sw=0)
    box(c, 0, 0, 450, 830, PERI, r=46, sh=0, sw=0)
    c.save()
    c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-225, -415, 450, 830), 46, 46), doAntiAlias=True)
    circle(c, 0, 380, 230, ICE, sh=0, sw=5)       # shoulders
    circle(c, 0, 20, 115, BLUSH, sh=0, sw=5)       # head
    poly(c, [(-120, -10), (-100, -110), (0, -140), (100, -110), (120, -10), (80, -70), (-80, -70)], INK, sh=0, sw=0)
    for ex in (-42, 42):
        circle(c, ex, 20, 10, INK, sh=0, sw=0)
    mo = 6 + 20 * abs(math.sin(t * 13))
    c.drawOval(skia.Rect.MakeXYWH(-26, 60 - mo / 2, 52, mo), paint(INK))
    c.restore()
    if int(t * 2) % 2 == 0:
        circle(c, -170, -360, 14, BLUSH_D, sh=0, sw=0)
    text(c, f"REC 00:{int(t * 7) % 60:02d}", -145, -360, 32, INK, "mono", align="l")
    for i in range(15):  # live waveform
        hh = 14 + 60 * abs(math.sin(t * 9 + i * 0.9) * math.sin(t * 4.3 + i * 0.4))
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-175 + i * 25, 330 - hh / 2, 14, hh), 7, 7),
                    paint(INK))
    popc(c)
    label(c, "MISTAKES? FINE.", 790, 1470, 50, LIME, rot=6, sc=pop(t, 1.0))
    label(c, "LONG PAUSES? FINE.", 320, 1590, 50, BLUSH, rot=-5, sc=pop(t, 1.6))
    label(c, "ZERO EDITING SKILLS", 580, 1715, 50, WHITE, rot=2, sc=pop(t, 2.2))


# ------------------------------------------------------------------ 4 DESCRIBE
MSGS = [("you", "cut the silences", 0.5, 0.7),
        ("ai", "removed 42 pauses", 1.8, 0.0),
        ("you", "add captions, word by word", 2.6, 1.0),
        ("ai", "134 captions synced", 4.1, 0.0),
        ("you", "make the hook POP", 4.9, 0.8),
        ("ai", "zooms + stickers + sfx added", 6.2, 0.0)]


def s_describe(c, t):
    grid_bg(c, t)
    step_header(c, t, 2, "DESCRIBE IT", BLUSH)
    s = pop(t, 0.1, 0.4)
    wx, wy, ww, wh = 540, 1000, 960, 1060
    push(c, wx, wy, 0, lerp(0.85, 1, min(s, 1)) * (s if s < 1 else 1))
    window(c, 0, 0, ww, wh, "vibe-editor / chat", bar=PERI)
    popc(c)
    if s < 0.9:
        return
    top, bottom = wy - wh / 2 + 76, wy + wh / 2 - 150
    # bubbles
    items = []
    for role, msg, t0, dur in MSGS:
        shown = t0 + dur
        if t >= shown:
            items.append((role, msg, shown))
    gap, bh = 34, 104
    total = len(items) * (bh + gap)
    scroll = max(0.0, total - (bottom - top - 40))
    c.save()
    c.clipRect(skia.Rect.MakeLTRB(wx - ww / 2 + 6, top + 4, wx + ww / 2 - 6, bottom))
    for i, (role, msg, shown) in enumerate(items):
        y = top + 40 + i * (bh + gap) + bh / 2 - scroll
        sc = pop(t, shown, 0.3)
        size = 42
        if role == "you":
            bw = tw(msg, size, "mono") + 70
            push(c, wx + ww / 2 - 50 - bw / 2, y, 0, sc)
            box(c, 0, 0, bw, bh, LIME, r=26, sh=8, sw=5)
            text(c, msg, 0, 0, size, INK, "mono")
        else:
            bw = tw(msg, size, "mono") + 130
            push(c, wx - ww / 2 + 130 + bw / 2, y, 0, sc)
            box(c, 0, 0, bw, bh, WHITE, r=26, sh=8, sw=5)
            check(c, -bw / 2 + 48, 0, 1.0)
            text(c, msg, -bw / 2 + 90, 0, size, INK, "mono", align="l")
        popc(c)
        if role == "ai":
            circle(c, wx - ww / 2 + 62, y, 36, ICE, sh=0, sw=5)
            text(c, "AI", wx - ww / 2 + 62, y, 30, INK, "black")
    # typing indicator before each AI reply
    for role, msg, t0, dur in MSGS:
        if role == "ai" and t0 - 0.6 <= t < t0:
            y = top + 40 + len(items) * (bh + gap) + bh / 2 - scroll
            box(c, wx - ww / 2 + 200, y, 140, 80, WHITE, r=40, sh=6, sw=5)
            for k in range(3):
                circle(c, wx - ww / 2 + 160 + k * 40, y - 12 * abs(math.sin(t * 9 + k)), 9, INK, sh=0, sw=0)
    c.restore()
    # input bar
    iy = wy + wh / 2 - 80
    box(c, wx - 60, iy, ww - 180, 96, CREAM, r=48, sh=0, sw=5)
    typing = ""
    for role, msg, t0, dur in MSGS:
        if role == "you" and t0 <= t < t0 + dur:
            typing = msg[:int(len(msg) * (t - t0) / dur) + 1]
    if typing:
        w_ = text(c, typing, wx - ww / 2 + 80, iy, 40, INK, "mono", align="l")
        if int(t * 4) % 2 == 0:
            c.drawRect(skia.Rect.MakeXYWH(wx - ww / 2 + 86 + w_, iy - 24, 5, 48), paint(INK))
    else:
        text(c, "describe your edit...", wx - ww / 2 + 80, iy, 40, 0x9A948A, "mono", align="l")
    circle(c, wx + ww / 2 - 75, iy, 44, INK, sh=0, sw=0)
    arrow(c, [(wx + ww / 2 - 95, iy), (wx + ww / 2 - 60, iy)], LIME, 7, 18)
    label(c, "NO TIMELINE. JUST WORDS.", 540, 1690, 60, INK, LIME, "head", rot=-3, sc=pop(t, 7.2, 0.3), sw=0,
          sh=12)


# ------------------------------------------------------------------ 5 DIRECT
def s_direct(c, t):
    grid_bg(c, t)
    step_header(c, t, 3, "REVIEW & DIRECT", ICE)
    cx, cy, R = 540, 1000, 320
    nodes = [(-90, "YOU DESCRIBE", LIME), (30, "AI EDITS", PERI), (150, "YOU REVIEW", BLUSH)]
    # arcs
    for i in range(3):
        a0 = nodes[i][0] + 24
        a1 = nodes[(i + 1) % 3][0] - 24 + (360 if i == 2 else 0)
        k = eoc((t - 0.8 - i * 0.25) / 0.35) if t > 0.8 + i * 0.25 else 0
        if k <= 0:
            continue
        n = 24
        pts = [(cx + R * math.cos(math.radians(lerp(a0, a1, j / n * k))),
                cy + R * math.sin(math.radians(lerp(a0, a1, j / n * k)))) for j in range(n + 1)]
        arrow(c, pts, INK, 10, 30)
    if t > 1.7:
        a = math.radians(-90 + (t - 1.7) * 150)
        circle(c, cx + R * math.cos(a), cy + R * math.sin(a), 20, LIME_DOT, sh=4, sw=5)
    for i, (ang, name, colr) in enumerate(nodes):
        s = pop(t, 0.3 + i * 0.2, 0.3)
        if s <= 0:
            continue
        a = math.radians(ang)
        label(c, name, cx + R * math.cos(a), cy + R * math.sin(a), 46, colr, sc=s, r=20)
    s = pop(t, 1.9, 0.3)
    if s > 0:
        push(c, cx, cy, -3, s)
        box(c, 0, 0, 330, 160, WHITE, r=20, sh=8)
        text(c, "LOOP UNTIL", 0, -30, 40, INK, "head")
        text(c, "IT SLAPS", 0, 28, 52, INK, "black")
        popc(c)
    for i, fb in enumerate(['"bigger captions"', '"faster cuts"', '"warmer colour"']):
        t0 = 3.0 + i * 0.8
        k = slide(t, t0, 0.35)
        if k <= 0:
            continue
        y = 1490 + i * 110
        push(c, lerp(1200, 0, k), 0)
        box(c, 470, y, 620, 92, WHITE, r=46, sh=8, sw=5)
        text(c, fb, 200, y, 40, INK, "mono", align="l")
        if t > t0 + 0.4:
            check(c, 725, y, pop(t, t0 + 0.4, 0.25))
        popc(c)


LIME_DOT = LIME


# ------------------------------------------------------------------ 6 RESULT
def s_result(c, t):
    grid_bg(c, t)
    label(c, "THE RESULT", 540, 250, 70, LIME, sc=pop(t, 0.0), rot=-2)
    base = 1330
    c.drawLine(120, base, 960, base, paint(INK, stroke=8))
    # old way bar
    ka = eio((t - 0.4) / 1.0) if t > 0.4 else 0
    ha = 820 * ka
    if ha > 1:
        box(c, 330, base - ha / 2, 260, ha, BLUSH, r=14, sh=12)
    text(c, "OLD WAY", 330, base + 60, 44, INK, "mono")
    if ka > 0:
        mins = int(240 * ka)
        text(c, f"{mins // 60} HRS" if ka >= 1 else f"{mins // 60}h {mins % 60:02d}m", 330, base - ha - 60, 72,
             INK, "black")
    kb = eio((t - 1.5) / 0.4) if t > 1.5 else 0
    hb = 52 * kb
    if hb > 1:
        box(c, 750, base - hb / 2, 260, hb, LIME, r=10, sh=10)
    text(c, "VIBE EDITING", 750, base + 60, 44, INK, "mono")
    if kb > 0:
        text(c, f"{int(15 * kb)} MIN", 750, base - hb - 60, 72, INK, "black")
    if t > 2.4:
        d = t - 2.4
        s = lerp(1.7, 1.0, eoc(d / 0.12)) if d < 0.12 else 1.0
        label(c, "16× FASTER", 540, 1620, 120, INK, LIME, "black", rot=-5, sc=s, sw=0, sh=14, r=30)


# ------------------------------------------------------------------ 7 WHAT YOU'LL MAKE
def tile_icon(c, kind, t):
    if kind == 0:   # captions
        box(c, 0, -30, 250, 44, WHITE, r=10, sh=0, sw=4)
        box(c, -40, 40, 150, 50, LIME, r=10, sh=4, sw=4)
        box(c, 85, 40, 80, 44, WHITE, r=10, sh=0, sw=4)
    elif kind == 1:  # motion graphics
        a = t * 90
        push(c, -70, 0, a)
        box(c, 0, 0, 70, 70, LIME, r=8, sh=5, sw=4)
        popc(c)
        circle(c, 30, -20 + 15 * math.sin(t * 5), 36, BLUSH, sh=5, sw=4)
        push(c, 95, 20, -a)
        poly(c, [(0, -40), (36, 26), (-36, 26)], WHITE, sh=5, sw=4)
        popc(c)
    elif kind == 2:  # kinetic type
        for i, ch in enumerate("Aa"):
            dy = -18 * abs(math.sin(t * 4 + i))
            text(c, ch, -40 + i * 90, dy, 120, INK, "black")
    elif kind == 3:  # animated logo
        push(c, 0, 0, t * 120)
        pts = []
        for i in range(10):
            r = 70 if i % 2 == 0 else 30
            a = math.radians(-90 + i * 36)
            pts.append((r * math.cos(a), r * math.sin(a)))
        poly(c, pts, LIME, sh=5, sw=4)
        popc(c)
    elif kind == 4:  # product ad
        box(c, -40, 10, 90, 150, PERI, r=26, sh=5, sw=4)
        box(c, -40, -80, 44, 36, INK, r=6, sh=0, sw=0)
        push(c, 70, -30, 12 + 8 * math.sin(t * 6))
        label(c, "-50%", 0, 0, 34, BLUSH_D, INK, "black", sh=4, sw=4)
        popc(c)
    else:            # transitions
        k = (t * 0.8) % 1
        box(c, -30, 0, 150, 110, PERI, r=10, sh=5, sw=4)
        box(c, 30 + 60 * math.sin(k * math.pi), 20, 150, 110, LIME, r=10, sh=5, sw=4)


def s_make(c, t):
    grid_bg(c, t)
    label(c, "WHAT YOU'LL MAKE", 540, 250, 64, PERI, sc=pop(t, 0.0), rot=2)
    names = ["CAPTIONS", "MOTION GFX", "KINETIC TYPE", "ANIMATED LOGOS", "PRODUCT ADS", "TRANSITIONS"]
    cols = [ICE, CREAM, BLUSH, PERI, LIME, WHITE]
    for i, name in enumerate(names):
        x = 295 + (i % 2) * 490
        y = 610 + (i // 2) * 390
        s = pop(t, 0.15 + i * 0.12, 0.3)
        if s <= 0:
            continue
        bounce = 1 + 0.03 * math.exp(-((t - 0.15 - i * 0.12) % BEAT) / 0.1) * (t > 1.2)
        push(c, x, y, [-2, 2, 1, -1, 2, -2][i], s * bounce)
        box(c, 0, 0, 440, 340, cols[i], r=26, sh=12)
        push(c, 0, -30)
        tile_icon(c, i, t)
        popc(c)
        text(c, name, 0, 120, 40, INK, "head")
        popc(c)


# ------------------------------------------------------------------ 8 CTA
def s_cta(c, t):
    grid_bg(c, t, PERI, 0xB5B7F7)
    s = pop(t, 0.0, 0.45)
    push(c, 540, 780, 0, lerp(0.75, 1, min(s, 1)) * (s if s < 1 else 1))
    window(c, 0, 0, 940, 820, "enroll.now", bar=LIME)
    text(c, "VIBE", 0, -140, 210, INK, "black")
    k = eoc((t - 0.3) / 0.3) if t > 0.3 else 0
    ew = tw("EDITING", 150, "black") + 70
    if k > 0:
        push(c, 0, 60, -2)
        box(c, -(ew - ew * k) / 2, 0, ew * k, 175, LIME, r=16, sh=10)
        popc(c)
    text(c, "EDITING", 0, 62, 150, INK, "black")
    text(c, "by IDEABRO STUDIO", 0, 250, 50, INK, "mono")
    popc(c)
    press = 2.2 <= t < 2.4
    s = pop(t, 0.8, 0.3) * (1 + 0.04 * math.exp(-((t - 0.8) % BEAT) / 0.1) * (t > 1.2))
    if s > 0:
        push(c, 540, 1395, 0, s)
        off = 4 if press else 0
        box(c, off, off, 720, 180, LIME, r=90, sh=14 - off * 3, sw=7)
        text(c, "ENROLL NOW", -45 + off, off, 72, INK, "black")
        arrow(c, [(218 + off, off), (282 + off, off)], INK, 12, 30)
        popc(c)
    label(c, "LINK IN BIO", 540, 1630, 56, WHITE, sc=pop(t, 1.2), rot=-2)
    if t > 1.4:
        f = eoc((t - 1.4) / 0.7)
        cursor(c, lerp(980, 700, f), lerp(1850, 1420, f), 0.85 if press else 1.0)
    if t > 2.2:  # confetti squares
        d = t - 2.2
        for i in range(36):
            r = rnd("cf", i)
            a = r.uniform(-math.pi * 0.95, -math.pi * 0.05)
            v = r.uniform(500, 1300)
            x = 540 + math.cos(a) * v * d
            y = 1395 + math.sin(a) * v * d + 1600 * d * d
            push(c, x, y, d * r.uniform(-500, 500))
            box(c, 0, 0, 26, 18, [LIME, BLUSH, ICE, WHITE, PERI_D][i % 5], r=3, sh=0, sw=3)
            popc(c)


FNS = {"title": s_title, "oldway": s_oldway, "record": s_record, "describe": s_describe, "direct": s_direct,
       "result": s_result, "make": s_make, "cta": s_cta}
SHAKES = [(S["oldway"] + 3.8, 18, 0.2), (S["result"] + 2.4, 20, 0.2), (S["cta"] + 2.2, 10, 0.15)]


# ------------------------------------------------------------------ compositor
def scene_at(t):
    for i, (s, e, n, wc) in enumerate(SCENES):
        if s <= t < e:
            return i, s, n
    return len(SCENES) - 1, SCENES[-1][0], SCENES[-1][2]


def frame(surf, t):
    c = surf.getCanvas()
    i, s, n = scene_at(t)
    c.save()
    dx = dy = 0.0
    for t0, amp, dec in SHAKES:
        d = t - t0
        if 0 <= d < dec * 4:
            a = amp * math.exp(-d / dec)
            dx += a * math.sin(d * 90)
            dy += a * math.cos(d * 70)
    z = 1 + 0.012 * math.exp(-(t % BEAT) / 0.1)
    c.translate(W / 2 + dx, H / 2 + dy)
    c.scale(z, z)
    c.translate(-W / 2, -H / 2)
    FNS[n](c, t - s)
    c.restore()
    progress(c, t)
    # block wipe centred on each cut
    for j in range(1, len(SCENES)):
        tc, wc = SCENES[j][0], SCENES[j][3]
        k = (t - (tc - 0.2)) / 0.4
        if 0 <= k <= 1:
            y = lerp(H * 1.5 + 60, -H * 0.5 - 60, eio(k))
            box(c, W / 2, y, W + 80, H + 40, wc, r=0, sh=0, sw=0)
            c.drawLine(-10, y - (H + 40) / 2, W + 10, y - (H + 40) / 2, paint(INK, stroke=10))
            c.drawLine(-10, y + (H + 40) / 2, W + 10, y + (H + 40) / 2, paint(INK, stroke=10))
    return surf.makeImageSnapshot()


def render_chunk(args):
    f0, f1, path = args
    surf = skia.Surface(W, H)
    enc = subprocess.Popen([FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s",
                            f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf",
                            "18", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for f in range(f0, f1):
        enc.stdin.write(frame(surf, f / FPS).toarray(colorType=skia.kRGBA_8888_ColorType).tobytes())
    enc.stdin.close()
    enc.wait()
    return path


# ------------------------------------------------------------------ audio (120 BPM, C major, marimba house)
SR = 44100
CH = [[60, 64, 67, 71], [57, 60, 64, 67], [53, 57, 60, 64], [55, 59, 62, 65]]   # Cmaj7 Am7 Fmaj7 G7
ROOT = [36, 33, 29, 31]


def marimba(m, d=0.35):
    n = int(d * SR)
    t = np.arange(n) / SR
    f = A.hz(m)
    y = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t / 0.03)
    return y * np.exp(-t / 0.13) * np.minimum(t / 0.002, 1)


def bass(m, d=0.3):
    n = int(d * SR)
    t = np.arange(n) / SR
    f = A.hz(m + 12)
    y = np.sin(2 * np.pi * f * t) + 0.25 * A.saw(f, n)
    return y * np.exp(-t / 0.18) * np.minimum(t / 0.004, 1) * np.minimum((d - t) / 0.02, 1)


def ding():
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 1047 * t) + 0.6 * np.sin(2 * np.pi * 1319 * t) * (t > 0.06)) * np.exp(-t / 0.15)


def click():
    n = int(0.03 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * 3200 * t) * np.exp(-t / 0.003)


def build_audio():
    N = int(DUR * SR)
    drums, mus, sfx = np.zeros(N), np.zeros(N), np.zeros(N)
    K, C, HC = A.kick(), A.clap(), A.hat()
    kicks = []
    nb = int(DUR / BEAT)
    for b in range(nb):
        t = b * BEAT
        bar = int(t / (BEAT * 4)) % 4
        chord, root = CH[bar], ROOT[bar]
        end = t >= 46.0
        if end:
            continue
        if t >= 4.0:
            A.place(drums, K, t, 0.8)
            kicks.append(t)
            if b % 2 == 1:
                A.place(drums, C, t, 0.5)
        for s in range(4):
            A.place(drums, HC, t + s * BEAT / 4 + (0.02 if s % 2 else 0), 0.14 if s % 2 else 0.22)
        if t >= 4.0:
            for o, g in ((0.0, 1.0), (0.75, 0.7)):
                A.place(mus, bass(root), t + o * BEAT, 0.6 * g)
        pat = [0, 1, 2, 3, 2, 1, 2, 3]
        for s in range(2):
            m = chord[pat[(b * 2 + s) % 8]] + 12
            A.place(mus, marimba(m), t + s * BEAT / 2, 0.35)
        if b % 4 == 0:
            for m in chord:
                A.place(mus, A.pad([m], BEAT * 4) * 0.25, t, 0.25)
    # ending: marimba roll + final chord
    for i, m in enumerate([60, 64, 67, 71, 72, 76]):
        A.place(mus, marimba(m, 0.8), 46.0 + i * 0.05, 0.5)
    A.place(drums, K, 46.0, 0.9)
    sc = np.ones(N)
    curve = 1 - 0.45 * np.exp(-np.arange(int(0.25 * SR)) / SR / 0.06)
    for tk in kicks:
        i = int(tk * SR)
        j = min(N, i + len(curve))
        sc[i:j] = np.minimum(sc[i:j], curve[: j - i])
    mus = sosfilt(butter(2, 7000, "lp", fs=SR, output="sos"), mus) * sc

    F = dict(A.SFX_FNS, ding=ding, click=click)
    G = dict(A.SFX_GAIN, ding=0.35, click=0.4)
    cues = []
    for s, e, n, wc in SCENES[1:]:
        cues.append((s - 0.2, "whoosh", 0.9))
    T = S["title"]
    cues += [(T + 0.25, "pop", 0.7), (T + 0.45, "whoosh", 0.4), (T + 0.75, "pop", 0.7), (T + 1.2, "pop", 0.6)]
    cues += [(T + 1.6 + i * 0.15, "pop", 0.5) for i in range(3)]
    T = S["oldway"]
    cues += [(T + 0.4 + i * 0.25, "tick", 0.5) for i in range(13)]
    cues += [(T + 1.4 + i * 0.45, "slap", 0.6) for i in range(3)] + [(T + 3.8, "stamp", 1.0)]
    T = S["record"]
    cues += [(T + 0.15, "whoosh", 0.5)] + [(T + x, "pop", 0.6) for x in (1.0, 1.6, 2.2)]
    T = S["describe"]
    for role, msg, t0, dur in MSGS:
        if role == "you":
            cues += [(T + t0 + k * dur / len(msg) * 2, "type", 0.35) for k in range(len(msg) // 2)]
            cues.append((T + t0 + dur, "whoosh", 0.35))
        else:
            cues.append((T + t0, "ding", 0.8))
    cues.append((T + 7.2, "stamp", 0.7))
    T = S["direct"]
    cues += [(T + 0.3 + i * 0.2, "pop", 0.5) for i in range(3)] + [(T + 1.9, "pop", 0.6)]
    cues += [(T + 3.0 + i * 0.8, "whoosh", 0.35) for i in range(3)] + [(T + 3.4 + i * 0.8, "ding", 0.6)
                                                                        for i in range(3)]
    T = S["result"]
    cues += [(T + 0.4 + i * 0.1, "tick", 0.3) for i in range(10)] + [(T + 1.5, "pop", 0.6), (T + 2.4, "stamp", 1.0)]
    T = S["make"]
    cues += [(T + 0.15 + i * 0.12, "pop", 0.55) for i in range(6)]
    T = S["cta"]
    cues += [(T + 0.3, "whoosh", 0.4), (T + 0.8, "pop", 0.7), (T + 1.2, "pop", 0.5), (T + 2.2, "click", 1.0),
             (T + 2.22, "sparkle", 0.8)]
    for t0, kind, g in cues:
        A.place(sfx, F[kind]() * G[kind], t0, g)

    def nrm(x):
        return x / (np.abs(x).max() + 1e-9)

    mix = 0.8 * nrm(drums) + 0.7 * nrm(mus) + 0.75 * nrm(sfx)
    mix /= np.abs(mix).max()
    mix = np.tanh(1.5 * mix) / np.tanh(1.5)
    fo = int(0.4 * SR)
    mix[-fo:] *= np.linspace(1, 0, fo) ** 2
    st = np.stack([mix, mix], 1) * 0.93
    path = os.path.join(OUT, "explainer_audio.wav")
    wavfile.write(path, SR, (st * 32767).astype(np.int16))
    return path


def render():
    total = int(round(DUR * FPS))
    n = os.cpu_count() or 4
    b = [round(total * i / n) for i in range(n + 1)]
    jobs = [(b[i], b[i + 1], os.path.join(OUT, f"chunk{i}.mp4")) for i in range(n)]
    with Pool(n) as pool:
        parts = pool.map(render_chunk, jobs)
    lst = os.path.join(OUT, "chunks.txt")
    with open(lst, "w") as fh:
        fh.writelines(f"file '{p}'\n" for p in parts)
    vid = os.path.join(OUT, "explainer_noaudio.mp4")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", vid],
                   check=True)
    for p in parts:
        os.remove(p)
    os.remove(lst)
    return vid


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == "stills":
        d = os.path.join(OUT, "stills")
        os.makedirs(d, exist_ok=True)
        surf = skia.Surface(W, H)
        for ts in map(float, sys.argv[2:]):
            frame(surf, ts).save(os.path.join(d, f"t{ts:05.2f}.png"), skia.kPNG)
        sys.exit()
    wav = build_audio()
    vid = render()
    final = os.path.join(OUT, "explainer.mp4")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", vid, "-i", wav, "-c:v", "copy", "-c:a", "aac", "-b:a",
                    "192k", "-shortest", "-movflags", "+faststart", final], check=True)
    print("wrote", final)
