"""The 14 shots of the promo. Each scene draws one full frame for local time t (already
quantised to the 12 fps stop-motion grid)."""

import math

import skia

from paper import (BLUSH, BLUSH_D, BRAND, ICE, ICE_D, INK, LIME, LIME_D, PAPER, PERI, PERI_D, R, beat_pulse,
                   bg, circ_pts, clamp, draw_text, eic, ellipse_pts, eob, eoc, fill_bg, lerp, paper, paper_paint,
                   path_of, pop, rect_pts, rough, rrect_pts, smooth, sparkle_pts, star_pts, text_width, torn)
from timeline import H, W


# ---------------------------------------------------------------- small props
def play_btn(ctx, x, y, r, seed, col=INK, tri=PAPER, depth=1.2):
    paper(ctx, circ_pts(x, y, r, 32), col, seed, depth=depth, amp=1.5)
    paper(ctx, [(x - r * 0.3, y - r * 0.45), (x + r * 0.5, y), (x - r * 0.3, y + r * 0.45)], tri, seed + 1,
          depth=0, amp=0.8)


def sparkle(ctx, x, y, r, col, seed, rot=0.0, depth=1.2):
    ctx.push(x, y, rot, 1.0, wob=1, seed=seed)
    paper(ctx, sparkle_pts(0, 0, r), col, seed, depth=depth, amp=1.2, seg=25)
    ctx.pop()


def confetti(ctx, t, t0, x, y, n, seed, spread=900, grav=2600, size=26):
    if t < t0:
        return
    dt = t - t0
    for i in range(n):
        r = R("conf", seed, i)
        a = r.uniform(-math.pi, 0) if r.random() < 0.8 else r.uniform(0, math.pi)
        v = r.uniform(0.4, 1.0) * spread
        px = x + math.cos(a) * v * dt
        py = y + math.sin(a) * v * dt + 0.5 * grav * dt * dt
        if py > H + 60:
            continue
        s = size * r.uniform(0.6, 1.3)
        ctx.push(px, py, r.uniform(0, 360) + dt * r.uniform(-600, 600))
        shape = rect_pts(0, 0, s, s * 0.6) if i % 3 else circ_pts(0, 0, s * 0.4, 10)
        paper(ctx, shape, BRAND[i % 4] if i % 5 else PAPER, seed + i, depth=0.8, amp=0.8)
        ctx.pop()


def phone(ctx, x, y, w, h, screen, seed, rot=0.0, sc=1.0):
    """Push a phone cut-out; caller draws screen content in local coords then calls ctx.pop()."""
    ctx.push(x, y, rot, sc, wob=1, seed=seed)
    paper(ctx, rrect_pts(0, 0, w + 36, h + 36, 70), INK, seed, depth=3, amp=1.5)
    paper(ctx, rrect_pts(0, 0, w, h, 50), screen, seed + 1, depth=0, amp=1.0)
    paper(ctx, rrect_pts(0, -h / 2 + 4, 150, 34, 17), INK, seed + 2, depth=0, amp=0.5)


# ---------------------------------------------------------------- 1. HOOK
def s_hook(ctx, t):
    bg(ctx, PERI, ICE, BLUSH, seed=10, layout=0)
    cx, cy = 540, 900
    k = smooth((t - 1.3) / 0.7)             # crumple progress
    enter = (1 - eoc(t / 0.3)) * 1100
    tl_w, tl_h = 1000, 340

    # timeline strip
    if k < 0.85:
        ctx.push(cx, cy + enter, (R("tl", ctx.step).uniform(-1, 1) * 2.5 * k), (1 - 0.8 * k, 1 - 0.55 * k),
                 wob=1 + 4 * k, seed=11)
        paper(ctx, rrect_pts(0, 0, tl_w + 24, tl_h + 24, 30), INK, 12, depth=3, amp=1.5)
        paper(ctx, rrect_pts(0, 0, tl_w, tl_h, 24), PAPER, 13, depth=0, amp=1.2)
        # ruler ticks
        for i in range(25):
            x = -480 + i * 40
            paper(ctx, rect_pts(x, -tl_h / 2 + 22, 3, 14 if i % 5 else 24), INK, 14 + i, depth=0, amp=0.3)
        ctx.pop()

    # 100 clips: 4 tracks x 25
    cols = [LIME, BLUSH, ICE, PERI_D]
    for row in range(4):
        for i in range(25):
            idx = row * 25 + i
            r = R("clip", idx)
            ox = -480 + i * 38.4 + 17
            oy = -95 + row * 64
            jig = math.sin(t * 20 + idx) * 3 * (t > 0.3)
            px = cx + ox * (1 - k) + r.uniform(-60, 60) * k * (1 - k) * 2
            py = cy + oy * (1 - k) + enter + jig + r.uniform(-60, 60) * k * (1 - k) * 2
            sc = 1 - 0.6 * k
            if k >= 0.99:
                continue
            ctx.push(px, py, r.uniform(-1, 1) * 400 * k, sc)
            paper(ctx, rrect_pts(0, 0, 34, 54, 6), cols[(row + i * 3) % 4], 20 + idx, depth=0.7, amp=0.8,
                  outline=(INK, 2.5))
            ctx.pop()

    # frantic playhead
    if k < 0.5 and t > 0.15:
        px = cx + math.sin(t * 9.0) * 420
        ctx.push(px, cy + enter, 0, 1, wob=1, seed=15)
        paper(ctx, rect_pts(0, 0, 8, tl_h + 40), BLUSH_D, 16, depth=1, amp=0.5, outline=(INK, 3))
        paper(ctx, [(-26, -tl_h / 2 - 50), (26, -tl_h / 2 - 50), (0, -tl_h / 2 - 16)], BLUSH_D, 17, depth=1,
              amp=0.5, outline=(INK, 3))
        ctx.pop()

    # paper ball
    if k > 0.45:
        rb = 190 * smooth((k - 0.45) / 0.55)
        bx, by, brot = cx, cy, k * 180
        if t > 2.0:
            dt = t - 2.0
            by -= abs(math.sin(dt * math.pi / 0.35)) * 110 * math.exp(-dt * 2.5)
            brot += dt * 90
        if t > 2.75:
            dt = t - 2.75
            bx += dt * dt * 9000 + dt * 600
            by -= dt * 1800
            brot += dt * 1400
        ctx.push(bx, by, brot, 1, wob=2, seed=18)
        outline = rough(circ_pts(0, 0, rb, 22), 19, rb * 0.09, 400)
        p = paper(ctx, outline, PAPER, 19, depth=3, amp=0, seg=999)
        ctx.c.save()
        ctx.c.clipPath(p, doAntiAlias=True)
        shades = [0xEDEBF7, 0xF6F4EE, 0xE3E4F8, 0xFFFFFF, 0xDADCF6, 0xF1EFEA]
        r = R("facet")
        for i in range(9):
            a0 = r.uniform(0, math.tau)
            a1 = a0 + r.uniform(0.5, 1.4)
            ox, oy = r.uniform(-0.4, 0.4) * rb, r.uniform(-0.4, 0.4) * rb
            tri = [(ox, oy), (math.cos(a0) * rb * 1.3, math.sin(a0) * rb * 1.3),
                   (math.cos(a1) * rb * 1.3, math.sin(a1) * rb * 1.3)]
            ctx.c.drawPath(path_of(tri), paper_paint(shades[i % 6], 30 + i, 200))
        crease = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3,
                            Color=skia.Color(17, 17, 17, 90))
        for i in range(7):
            pts = [(r.uniform(-1, 1) * rb, r.uniform(-1, 1) * rb) for _ in range(3)]
            ctx.c.drawPath(path_of(pts, closed=False), crease)
        ctx.c.restore()
        ctx.pop()

    # type
    draw_text(ctx, "STILL", 540, 300, 210, rot=-4, sc=pop(t, 0.05), seed=101, under=LIME)
    draw_text(ctx, "EDITING", 540, 520, 200, rot=3, sc=pop(t, 0.3), seed=102, under=BLUSH)
    draw_text(ctx, "LIKE IT'S", 540, 1270, 130, rot=-2, sc=pop(t, 1.2), seed=103)
    s = 0 if t < 1.6 else lerp(1.7, 1.0, eic((t - 1.6) / 0.1)) if t < 1.7 else 1.0
    draw_text(ctx, "2015?", 540, 1490, 250, fill=LIME, back=INK, under=BLUSH, rot=-6, sc=s, seed=104, pad=0.12)


# ---------------------------------------------------------------- 2. PROBLEM
def s_problem(ctx, t):
    bg(ctx, BLUSH, PERI, LIME, seed=20, layout=1)
    panic = 1 + 3 * smooth((t - 3.1) / 0.6)

    # pile of clip cards falling in, one every half beat
    cols = [PERI, LIME, ICE, PAPER, BLUSH_D]
    for i in range(18):
        t0 = 0.2 + i * 0.2
        if t < t0:
            break
        r = R("card", i)
        tx = 180 + (i % 3) * 360 + r.uniform(-60, 60)
        ty = 1830 - (i // 3) * 68 + r.uniform(-20, 20)
        f = (t - t0) / 0.25
        y = lerp(-250, ty, eic(f)) if f < 1 else ty - abs(math.sin((t - t0 - 0.25) * 12)) * 22 * math.exp(
            -(t - t0 - 0.25) * 8)
        ctx.push(tx, y, r.uniform(-28, 28) + (1 - clamp(f)) * 90, 1, wob=panic, seed=200 + i)
        paper(ctx, rrect_pts(0, 0, 310, 200, 22), PAPER, 210 + i, depth=2, amp=1.5)
        paper(ctx, rrect_pts(0, -10, 280, 150, 14), cols[i % 5], 230 + i, depth=0, amp=1.2)
        play_btn(ctx, 0, -10, 34, 250 + i, depth=0.6)
        paper(ctx, rect_pts(-40, 82, 200, 8), INK, 270 + i, depth=0, amp=0.5)
        ctx.pop()

    # clock
    s = pop(t, 0.0, 0.3)
    ctx.push(540, 560, math.sin(t * 7) * 3 * panic, s, wob=panic, seed=21)
    paper(ctx, circ_pts(0, 0, 295, 60), INK, 22, depth=3, amp=1.5)
    paper(ctx, circ_pts(0, 0, 265, 60), PAPER, 23, depth=0, amp=1.2)
    paper(ctx, circ_pts(0, 0, 225, 50), ICE, 24, depth=0, amp=1.2, alpha=150)
    for i in range(12):
        a = math.radians(i * 30)
        ctx.push(math.cos(a) * 232, math.sin(a) * 232, i * 30 + 90)
        paper(ctx, rect_pts(0, 0, 12 if i % 3 else 18, 30 if i % 3 else 44), INK, 40 + i, depth=0, amp=0.4)
        ctx.pop()
    speed = 900 * (1 + 1.5 * smooth((t - 3.1) / 0.6))
    for (L, wdt, ang, seed) in ((200, 24, t * speed, 60), (130, 34, t * speed / 12 + 40, 61)):
        ctx.push(0, 0, ang)
        paper(ctx, rrect_pts(0, -L / 2 + 20, wdt, L, wdt / 2), INK, seed, depth=1, amp=0.8)
        ctx.pop()
    paper(ctx, circ_pts(0, 0, 30, 20), LIME, 62, depth=1, amp=0.6, outline=(INK, 4))
    # bells
    for sx in (-1, 1):
        ctx.push(sx * 190, -250, sx * 35 + math.sin(t * 40) * 6 * panic)
        paper(ctx, ellipse_pts(0, 0, 70, 44, 24), INK, 63 + sx, depth=1.5, amp=1)
        ctx.pop()
    ctx.pop()

    # hours tag
    hrs = min(12, 1 + int(max(0.0, t - 0.4) / 0.4))
    label = f"{hrs} HR" + ("S" if hrs > 1 else "")
    draw_text(ctx, label, 850, 330, 96, fill=INK, back=LIME, rot=12, sc=pop(t, 0.4), seed=301, pad=0.18,
              wob=panic)

    draw_text(ctx, "HOURS", 540, 1040, 270, rot=-3, sc=pop(t, 0.8), seed=302, under=PERI, wob=panic)
    draw_text(ctx, "PER REEL.", 540, 1265, 150, rot=2, sc=pop(t, 1.6), seed=303, fill=PAPER, back=INK,
              wob=panic)


# ---------------------------------------------------------------- 3. REVEAL
def s_reveal(ctx, t):
    bg(ctx, ICE, PERI, LIME, seed=30, layout=2)
    build = smooth((t - 3.0) / 1.0)

    # pop-up book
    if t > 1.5:
        base_s = pop(t, 1.5, 0.25)
        ctx.push(540, 1170, 0, base_s, wob=1 + 2 * build, seed=31)
        # open book pages
        paper(ctx, [(-470, -30), (0, 0), (0, 70), (-470, 40)], PAPER, 32, depth=3, amp=1.5, outline=(INK, 5))
        paper(ctx, [(470, -30), (0, 0), (0, 70), (470, 40)], PAPER, 33, depth=3, amp=1.5, outline=(INK, 5))
        paper(ctx, [(-440, -18), (-10, 8), (-10, 40), (-440, 18)], PERI, 34, depth=0, amp=1)
        paper(ctx, [(440, -18), (10, 8), (10, 40), (440, 18)], LIME, 35, depth=0, amp=1)
        ctx.pop()

        # side pop-ups
        for (px, py, t0, kind, seed) in ((190, 820, 1.8, "star", 36), (890, 800, 1.95, "bolt", 37),
                                         (120, 1060, 2.05, "spark", 38), (960, 1050, 2.1, "spark", 39)):
            sy = pop(t, t0, 0.3)
            if sy <= 0:
                continue
            ctx.push(px, 1150, 0, (1, sy), wob=1 + 2 * build, seed=seed)
            paper(ctx, rect_pts(0, (py - 1150) / 2, 10, abs(py - 1150)), PAPER, seed + 100, depth=0.5, amp=0.5)
            ctx.c.translate(0, py - 1150)
            if kind == "star":
                paper(ctx, star_pts(0, 0, 120, 55, 5), LIME, seed, depth=2, amp=1.5, outline=(INK, 5))
            elif kind == "bolt":
                bolt = [(-20, -130), (70, -130), (20, -20), (80, -20), (-50, 140), (-10, 20), (-70, 20)]
                paper(ctx, bolt, BLUSH, seed, depth=2, amp=1.2, outline=(INK, 5))
            else:
                paper(ctx, sparkle_pts(0, 0, 60), PAPER, seed, depth=1.5, amp=1, outline=(INK, 4))
            ctx.pop()

        # the video panel unfolding from the hinge
        sy = pop(t, 1.6, 0.4)
        if sy > 0:
            ctx.push(540, 1150, 0, (1, sy), wob=1 + 2 * build, seed=40)
            pw, ph = 560, 620
            paper(ctx, rrect_pts(0, -ph / 2, pw + 26, ph + 26, 30), INK, 41, depth=3, amp=1.5)
            paper(ctx, rrect_pts(0, -ph / 2, pw, ph, 22), PERI, 42, depth=0, amp=1.2)
            ctx.c.save()
            ctx.c.clipPath(path_of(rrect_pts(0, -ph / 2, pw, ph, 22)), doAntiAlias=True)
            paper(ctx, circ_pts(130, -470, 90, 30), LIME, 43, depth=1, amp=1.5)
            torn(ctx, [(-320, -220), (-60, -330), (200, -250), (320, -300), (320, 20), (-320, 20)], ICE, 44,
                 depth=1.5, amp=7)
            torn(ctx, [(-320, -120), (-120, -170), (120, -110), (320, -180), (320, 20), (-320, 20)], BLUSH, 45,
                 depth=1.5, amp=7)
            ctx.c.restore()
            play_btn(ctx, 0, -330, 70, 46, depth=2)
            paper(ctx, rrect_pts(0, -50, 480, 14, 7), INK, 47, depth=0, amp=0.5)
            paper(ctx, rrect_pts(-240 + 480 * clamp((t - 1.8) / 2.0) / 2, -50, 480 * clamp((t - 1.8) / 2.0),
                                 14, 7), LIME, 48, depth=0, amp=0.5)
            ctx.pop()
        confetti(ctx, t, 1.62, 540, 850, 34, 49)

    # chat bubble
    if t < 1.4:
        by = lerp(1500, 830, eob(t / 0.28))
        bsc = 1.0
    else:
        by = lerp(830, 300, eob((t - 1.4) / 0.3))
        bsc = lerp(1.0, 0.82, eoc((t - 1.4) / 0.3))
    ctx.push(540, by, -2, bsc, wob=1 + 2 * build, seed=50)
    paper(ctx, rrect_pts(0, 0, 880, 210, 70) , INK, 51, depth=3, amp=1.2)
    paper(ctx, [(250, 90), (380, 170), (330, 80)], INK, 52, depth=0, amp=0.8)
    paper(ctx, rrect_pts(0, 0, 856, 186, 60), PAPER, 53, depth=0, amp=1.0)
    paper(ctx, [(262, 80), (362, 150), (322, 70)], PAPER, 54, depth=0, amp=0.6)
    n = clamp(int((t - 0.3) * 12) + 1, 0, 11) if t >= 0.3 else 0
    typed = "make it pop"[:int(n)]
    draw_text(ctx, typed, -370, 0, 96, fill=INK, back=None, font="bold", align="l", seed=55, depth=0, wob=0.4,
              maxw=0)
    cw =text_width(typed, 96, "bold") if typed else 0
    if t < 1.4 and (ctx.step // 3) % 2 == 0:
        paper(ctx, rect_pts(-370 + cw + 16, 0, 10, 90), PERI_D, 56, depth=0, amp=0.3)
    ss = 1 + 0.35 * math.exp(-max(0.0, t - 1.4) / 0.06) * (t >= 1.4)
    ctx.push(335, 0, 0, ss)
    paper(ctx, circ_pts(0, 0, 55, 28), LIME, 57, depth=1.2, amp=1, outline=(INK, 5))
    paper(ctx, [(-22, -26), (30, 0), (-22, 26), (-10, 0)], INK, 58, depth=0, amp=0.5)
    ctx.pop()
    ctx.pop()
    if t < 1.4:
        draw_text(ctx, "YOU:", 250, by - 175, 60, fill=PAPER, back=INK, seed=59, pad=0.2, rot=-4,
                  sc=pop(t, 0.1))

    # title
    tb = 1 + 0.08 * build * math.sin(t * 60)
    draw_text(ctx, "VIBE", 540, 1400, 270, rot=-4, sc=pop(t, 2.4, 0.22) * tb, seed=401, under=LIME,
              wob=1 + 2 * build)
    draw_text(ctx, "EDITING.", 540, 1615, 190, rot=2, sc=pop(t, 2.6, 0.22) * tb, seed=402, fill=PAPER,
              back=INK, under=PERI_D, wob=1 + 2 * build)


# ---------------------------------------------------------------- 4a. CAPTIONS
def s_captions(ctx, t):
    bg(ctx, LIME, PERI, BLUSH, seed=40, layout=0)
    x = lerp(1500, 540, eob(t / 0.25))
    phone(ctx, x, 760, 600, 950, PERI, 41, rot=-3)
    # talking head
    paper(ctx, circ_pts(0, -80, 230, 40), ICE, 42, depth=0, amp=2)
    paper(ctx, rrect_pts(0, 330, 420, 360, 150), INK, 43, depth=2, amp=1.5)
    paper(ctx, rrect_pts(0, 170, 90, 90, 20), BLUSH_D, 44, depth=0, amp=1)
    paper(ctx, circ_pts(0, -60, 125, 36), BLUSH, 45, depth=2, amp=1.5)
    paper(ctx, [(-135, -70), (-120, -170), (-40, -205), (60, -200), (130, -150), (138, -70), (90, -130),
                (-60, -140)], INK, 46, depth=1, amp=1.5)
    for ex in (-45, 45):
        paper(ctx, circ_pts(ex, -50, 12, 12), INK, 47 + ex, depth=0, amp=0.4)
    mo = 8 + 22 * abs(math.sin(ctx.step * 1.7))
    paper(ctx, ellipse_pts(0, 10, 32, mo, 20), INK, 48, depth=0, amp=0.5)
    # captions
    words = [("THIS", 0.15), ("IS", 0.35), ("SO", 0.55), ("EASY", 0.75)]
    cur = max([i for i, (_, t0) in enumerate(words) if t >= t0], default=-1)
    lines = [(words[:2], 205), (words[2:], 330)]
    for li, (ws, ly) in enumerate(lines):
        widths = [text_width(w, 110) + 50 for w, _ in ws]
        xx = -sum(widths) / 2
        for j, (w, t0) in enumerate(ws):
            i = li * 2 + j
            cx = xx + widths[j] / 2
            xx += widths[j]
            if t < t0:
                continue
            fly = 1 - eoc((t - t0) / 0.15)
            draw_text(ctx, w, cx + fly * (300 if j else -300), ly, 110, fill=INK,
                      back=LIME if i == cur else PAPER, rot=(-6 if i % 2 else 5) * (1 + fly * 4),
                      sc=pop(t, t0, 0.18) * (1.15 if i == cur else 1.0), seed=500 + i, pad=0.14, depth=1.5)
    ctx.pop()
    draw_text(ctx, "CAPTIONS.", 540, 1480, 175, rot=-3, sc=pop(t, 0.05), seed=510, under=PERI)


# ---------------------------------------------------------------- 4b. MOTION
def s_motion(ctx, t):
    bg(ctx, PERI, ICE, BLUSH, seed=50, layout=1)
    # orbiting shapes
    for i in range(6):
        a = t * 2.2 + i * math.tau / 6
        ox, oy = 540 + math.cos(a) * 430, 880 + math.sin(a) * 560
        ctx.push(ox, oy, t * 300 + i * 60, 1, wob=1, seed=520 + i)
        shape = [circ_pts(0, 0, 55, 26), star_pts(0, 0, 70, 30, 3), sparkle_pts(0, 0, 70),
                 rrect_pts(0, 0, 100, 60, 20)][i % 4]
        paper(ctx, shape, [LIME, BLUSH, PAPER, ICE][i % 4], 530 + i, depth=2, amp=1.2, outline=(INK, 4))
        ctx.pop()
    letters = "MOTION"
    cols = [LIME, BLUSH, ICE, PAPER, LIME, BLUSH]
    for i, ch in enumerate(letters):
        r = R("mot", i)
        tx, ty = 540 + (i - 2.5) * 152, 880
        t0 = 0.08 + i * 0.06
        f = eob((t - t0) / 0.25) if t >= t0 else 0
        sx, sy = r.choice([-300, 1380]), r.uniform(-300, 2200)
        x, y = lerp(sx, tx, f), lerp(sy, ty, f)
        hop = 0.0
        for b in (0.4, 0.8, 1.2):
            d = t - b - i * 0.035
            if 0 <= d < 0.25:
                hop = -110 * math.sin(math.pi * d / 0.25)
        rot = lerp(r.uniform(-200, 200), r.uniform(-8, 8), f) + hop * 0.12 * (1 if i % 2 else -1)
        if t < t0:
            continue
        ctx.push(x, y + hop, rot, 1, wob=1, seed=540 + i)
        paper(ctx, rrect_pts(0, 0, 138, 190, 22), cols[i], 550 + i, depth=2.5, amp=1.4, outline=(INK, 5))
        draw_text(ctx, ch, 0, 0, 132,back=None, seed=560 + i, depth=0, wob=0.5)
        ctx.pop()
    draw_text(ctx, "KINETIC TYPE", 540, 1260, 80, fill=PAPER, back=INK, rot=-2, sc=pop(t, 0.5), seed=570,
              pad=0.2)


# ---------------------------------------------------------------- 4c. ANIMATION
def s_anim(ctx, t):
    bg(ctx, BLUSH, LIME, PERI, seed=60, layout=2)
    cx, cy = 540, 800
    spin = t * 200
    bump = 1 + 0.12 * beat_pulse(t, 0.4, 0.1)
    ctx.push(cx, cy, spin, bump, wob=1, seed=61)
    for i in range(8):
        f = pop(t, 0.03 + i * 0.04, 0.25)
        if f <= 0:
            continue
        ctx.push(0, 0, i * 45, f)
        paper(ctx, ellipse_pts(0, -175, 75, 165, 30), [PERI, LIME, ICE, PAPER][i % 4], 62 + i, depth=2,
              amp=1.5, outline=(INK, 5))
        ctx.pop()
    cs = pop(t, 0.3, 0.25)
    if cs > 0:
        ctx.push(0, 0, -spin, cs)
        paper(ctx, circ_pts(0, 0, 125, 36), INK, 70, depth=3, amp=1.2)
        paper(ctx, sparkle_pts(0, 0, 85), LIME, 71, depth=0, amp=0.8)
        ctx.pop()
    ctx.pop()
    for i in range(10):
        a = -t * 3 + i * math.tau / 10
        s = pop(t, 0.4 + i * 0.03, 0.2)
        if s > 0:
            sparkle(ctx, cx + math.cos(a) * 440, cy + math.sin(a) * 440, 30 * s, [PAPER, LIME, PERI][i % 3],
                    580 + i, rot=t * 200)
    draw_text(ctx, "ANIMATION.", 540, 1430, 170, rot=-3, sc=pop(t, 0.1), seed=590, under=LIME)
    draw_text(ctx, "ANIMATED LOGOS", 540, 1600, 64, fill=PAPER, back=INK, rot=2, sc=pop(t, 0.5), seed=591,
              pad=0.2)


# ---------------------------------------------------------------- 4d. ADS
def s_ads(ctx, t):
    fill_bg(ctx, ICE, 70)
    cx, cy = 540, 960
    # sunburst
    rays = skia.Path()
    for i in range(16):
        a0 = math.radians(t * 45 + i * 22.5)
        a1 = a0 + math.radians(11.25)
        rays.moveTo(cx, cy)
        rays.lineTo(cx + math.cos(a0) * 1500, cy + math.sin(a0) * 1500)
        rays.lineTo(cx + math.cos(a1) * 1500, cy + math.sin(a1) * 1500)
        rays.close()
    ctx.c.drawPath(rays, paper_paint(PAPER, 71, 170))
    torn(ctx, [(-90, H - 330), (W + 90, H - 420), (W + 90, H + 90), (-90, H + 90)], PERI, 72)
    # bottle
    y = lerp(2300, cy, eob(t / 0.28))
    hop = -60 * max(0.0, math.sin(math.pi * clamp(((t - 0.4) % 0.4) / 0.2))) if t > 0.4 else 0
    ctx.push(cx, y + hop, lerp(-30, -4, eoc(t / 0.3)), 1, wob=1, seed=73)
    paper(ctx, rrect_pts(0, 60, 300, 560, 80), PERI_D, 74, depth=3, amp=1.5, outline=(INK, 6))
    paper(ctx, rrect_pts(0, -265, 120, 110, 20), PERI_D, 75, depth=1, amp=1, outline=(INK, 6))
    paper(ctx, rrect_pts(0, -345, 160, 80, 18), INK, 76, depth=1.5, amp=1)
    paper(ctx, rrect_pts(0, 90, 300, 220, 6), LIME, 77, depth=1, amp=1.2, outline=(INK, 5))
    draw_text(ctx, "GLOW", 0, 70, 80,back=None, seed=78, depth=0, wob=0.4)
    draw_text(ctx, "SERUM", 0, 150, 44, back=None, seed=79, depth=0, wob=0.4, font="bold")
    paper(ctx, rrect_pts(-80, -60, 36, 200, 18), PAPER, 80, depth=0, amp=0.8, alpha=150)
    ctx.pop()
    # price burst
    s = pop(t, 0.4, 0.22) * (1 + 0.1 * beat_pulse(t, 0.4, 0.1, 0.4))
    if s > 0:
        ctx.push(830, 660, 12 + t * 30, s, wob=1, seed=81)
        paper(ctx, star_pts(0, 0, 185, 145, 14), INK, 82, depth=3, amp=1.2)
        ctx.pop()
        draw_text(ctx, "50%", 830, 630, 104, fill=LIME, back=None, rot=12, sc=s, seed=83, depth=0)
        draw_text(ctx, "OFF", 830, 725, 70, fill=PAPER, back=None, rot=12, sc=s, seed=84, depth=0)
    draw_text(ctx, "ADS.", 540, 300, 280, rot=-4, sc=pop(t, 0.05), seed=85, under=LIME)
    draw_text(ctx, "NEW DROP", 300, 1480, 76, fill=PAPER, back=INK, rot=-6, sc=pop(t, 0.6), seed=86, pad=0.2)


# ---------------------------------------------------------------- 4e. TRANSITIONS
def s_trans(ctx, t):
    seq = [PERI, LIME, BLUSH, ICE, PERI]
    b = min(3, int(t / 0.4))
    lt = t - b * 0.4
    fill_bg(ctx, seq[b], 90 + b)
    k = eoc((lt - 0.1) / 0.25)
    col = seq[b + 1]
    if k > 0:
        kind = b % 4
        if kind == 0:     # stripes from alternating sides
            for i in range(8):
                hgt = H / 8
                d = 1 if i % 2 else -1
                x = lerp(d * 1300, 0, clamp(k * 1.3 - i * 0.04))
                paper(ctx, rect_pts(W / 2 + x, hgt * i + hgt / 2, W + 40, hgt + 6), col, 100 + i, depth=2,
                      amp=3, seg=30)
        elif kind == 1:   # iris
            paper(ctx, circ_pts(540, 960, k * 1250, 60), col, 110, depth=3, amp=12, seg=20)
        elif kind == 2:   # diagonal torn sheet
            off = lerp(-2400, 0, k)
            torn(ctx, [(-400 + off, -400), (1500 + off + 900, -400), (1500 + off, 2400), (-400 + off, 2400)],
                 col, 120, edge=(-10, 0), amp=16)
        else:             # blinds
            for i in range(6):
                wdt = W / 6
                sx = clamp(k * 1.4 - i * 0.07)
                if sx > 0:
                    paper(ctx, rect_pts(wdt * i + wdt / 2, 960, (wdt + 4) * sx, H + 40), col, 130 + i, depth=2,
                          amp=2)
    rr = R("trr", b)
    draw_text(ctx, "TRANSITIONS", 540, 960, 170, rot=rr.uniform(-7, 7), sc=1 + 0.1 * beat_pulse(t, 0.4, 0.08),
              seed=140 + b, under=[BLUSH, PERI, LIME, BLUSH][b], maxw=880)
    draw_text(ctx, "SMOOTH AF", 540, 1160, 70, fill=PAPER, back=INK, rot=-3, sc=pop(t, 0.3), seed=150, pad=0.2)


# ---------------------------------------------------------------- 4f. RECAP (strobe of the montage)
def s_recap(ctx, t):
    k = min(7, int(t / 0.2))
    fn = [s_captions, s_motion, s_anim, s_ads][k % 4]
    fn(ctx, 1.0 + (t - k * 0.2) + (k // 4) * 0.25)


# ---------------------------------------------------------------- 4g. ALL / WITH / AI
def s_all(ctx, t):
    fill_bg(ctx, INK, 160)
    for i in range(8):
        r = R("allsp", i)
        sparkle(ctx, r.uniform(80, 1000), r.uniform(200, 1700), r.uniform(20, 50) * pop(t, 0.05 * i, 0.2),
                [LIME, PERI, BLUSH, ICE][i % 4], 161 + i, rot=t * 90)
    draw_text(ctx, "ALL", 540, 960, 520, fill=INK, back=LIME, under=PERI, rot=-6, sc=pop(t, 0.0, 0.18),
              seed=170, pad=0.09, maxw=900)


def s_with(ctx, t):
    bg(ctx, LIME, PERI, BLUSH, seed=175, layout=2)
    draw_text(ctx, "WITH", 540, 960, 380, rot=6, sc=lerp(1.4, 1.0, eoc(t / 0.12)), seed=176, under=BLUSH,
              maxw=880)


def s_ai(ctx, t):
    fill_bg(ctx, PERI, 180)
    cx, cy = 540, 900
    rays = skia.Path()
    for i in range(12):
        a0 = math.radians(-t * 60 + i * 30)
        a1 = a0 + math.radians(15)
        rays.moveTo(cx, cy)
        rays.lineTo(cx + math.cos(a0) * 1500, cy + math.sin(a0) * 1500)
        rays.lineTo(cx + math.cos(a1) * 1500, cy + math.sin(a1) * 1500)
        rays.close()
    ctx.c.drawPath(rays, paper_paint(PERI_D, 181))
    for i in range(16):
        r = R("aisp", i)
        a = r.uniform(0, math.tau)
        d = eoc(t / 0.5) * r.uniform(350, 800)
        sparkle(ctx, cx + math.cos(a) * d, cy + math.sin(a) * d, r.uniform(30, 70) * pop(t, 0.02, 0.2),
                [LIME, PAPER, BLUSH, ICE][i % 4], 182 + i, rot=t * r.uniform(-300, 300), depth=2)
    s = lerp(1.8, 1.0, eic(t / 0.09)) if t < 0.09 else 1 + 0.08 * beat_pulse(t, 0.4, 0.1)
    draw_text(ctx, "AI", 540, cy, 640, rot=-5, sc=s, seed=190, under=LIME, pad=0.08)
    draw_text(ctx, "DOES THE GRIND", 540, 1450, 80, fill=PAPER, back=INK, rot=3, sc=pop(t, 0.4), seed=191,
              pad=0.2)


# ---------------------------------------------------------------- 5. PAYOFF
def s_payoff(ctx, t):
    fill_bg(ctx, PAPER, 200)
    # top panel
    xo = lerp(-1300, 0, eoc(t / 0.25))
    ctx.push(xo, 0)
    torn(ctx, [(-100, -100), (W + 100, -100), (W + 100, 960), (-100, 1010)], LIME, 201, edge=(0, -10), amp=12)
    # clapperboard
    ctx.push(540, 400, -6, 1, wob=1, seed=202)
    paper(ctx, rrect_pts(0, 70, 480, 300, 16), INK, 203, depth=3, amp=1.2)
    for i in range(3):
        paper(ctx, rect_pts(0, 10 + i * 70, 420, 5), PAPER, 204 + i, depth=0, amp=0.3, alpha=140)
    draw_text(ctx, "TAKE 1", -70, 60, 58, fill=PAPER, back=None, seed=208, depth=0, wob=0.4)
    draw_text(ctx, "SCENE 01", 50, 150, 44, fill=LIME, back=None, seed=209, depth=0, wob=0.4, font="bold")
    # arm: open, snaps shut on every other beat
    ang = -28.0
    for c0 in (0.4, 1.2, 2.0, 2.8):
        d = t - c0
        if -0.1 <= d < 0:
            ang = -28.0 * (-d / 0.1)
        elif 0 <= d < 0.15:
            ang = 0.0
        elif 0.15 <= d < 0.3:
            ang = -28.0 * (d - 0.15) / 0.15
    ctx.push(-240, -85, ang)
    arm = rect_pts(240, -35, 480, 70)
    p = paper(ctx, arm, PAPER, 210, depth=2, amp=1)
    ctx.c.save()
    ctx.c.clipPath(p, doAntiAlias=True)
    for i in range(7):
        x = i * 80
        ctx.c.drawPath(path_of([(x, -70), (x + 40, -70), (x + 10, 0), (x - 30, 0)]), paper_paint(INK, 211 + i))
    ctx.c.restore()
    ctx.pop()
    base = rect_pts(0, -45, 480, 70)
    p = paper(ctx, base, PAPER, 220, depth=1, amp=1)
    ctx.c.save()
    ctx.c.clipPath(p, doAntiAlias=True)
    for i in range(7):
        x = -240 + i * 80
        ctx.c.drawPath(path_of([(x + 30, -80), (x + 70, -80), (x + 40, -10), (x, -10)]), paper_paint(INK, 221))
    ctx.c.restore()
    ctx.pop()
    draw_text(ctx, "YOU DIRECT.", 540, 790, 150, rot=-3, sc=pop(t, 0.2), seed=230, under=PERI, maxw=980)
    ctx.pop()

    # bottom panel
    xo = lerp(1300, 0, eoc((t - 0.4) / 0.25)) if t >= 0.4 else 1400
    ctx.push(xo, 0)
    torn(ctx, [(-100, 990), (W + 100, 940), (W + 100, H + 100), (-100, H + 100)], PERI, 240, edge=(0, 10),
         amp=12)
    draw_text(ctx, "AI EDITS.", 540, 1150, 175, rot=2, sc=pop(t, 0.6), seed=241, fill=PAPER, back=INK,
              under=LIME)
    # film strip moving left
    fy = 1450
    snips = [c for c in (0.8, 1.6, 2.4, 3.2) if t >= c]
    shift = (t * 420) % 200
    ctx.push(0, fy, -4, 1, wob=1, seed=242)
    paper(ctx, rect_pts(540, 0, 1400, 190), INK, 243, depth=2.5, amp=1)
    for i in range(-1, 8):
        x = i * 200 - shift
        paper(ctx, rrect_pts(x + 100, 0, 150, 110, 10), BRAND[(i + int(t * 420 // 200)) % 4], 244 + (i % 4),
              depth=0, amp=0.8)
        for sx in (40, 100, 160):
            for sy in (-78, 78):
                paper(ctx, rrect_pts(x + sx, sy, 22, 14, 4), PAPER, 250, depth=0, amp=0.2)
    ctx.pop()
    # clipped-off pieces falling
    for j, c in enumerate(snips):
        d = t - c
        r = R("piece", j)
        ctx.push(640 + d * 300, fy + 40 + 0.5 * 3000 * d * d, d * r.uniform(200, 500))
        paper(ctx, rect_pts(0, 0, 180, 190), INK, 260 + j, depth=2, amp=1)
        paper(ctx, rrect_pts(0, 0, 150, 110, 10), BRAND[j % 4], 265 + j, depth=0, amp=0.8)
        ctx.pop()
    # scissors
    open_a = 22.0
    for c in (0.8, 1.6, 2.4, 3.2):
        d = t - c
        if -0.12 <= d < 0:
            open_a = 22.0 * (-d / 0.12)
        elif 0 <= d < 0.1:
            open_a = 0.0
        elif 0.1 <= d < 0.25:
            open_a = 22.0 * (d - 0.1) / 0.15
    ctx.push(610, fy + 120, -90, 1.0, wob=1, seed=270)
    for side in (-1, 1):
        ctx.push(0, 0, side * open_a / 2)
        paper(ctx, [(0, -14 * side), (240, -4 * side), (240, 4 * side), (0, 14 * side)], PAPER, 271 + side,
              depth=2, amp=0.6, outline=(INK, 5))
        paper(ctx, ellipse_pts(-150, 55 * side, 75, 48, 26), BLUSH, 273 + side, depth=2, amp=1,
              outline=(INK, 5))
        paper(ctx, ellipse_pts(-150, 55 * side, 40, 20, 20), PERI, 275 + side, depth=0, amp=0.6)
        paper(ctx, [(-10, 12 * side), (-100, 45 * side), (-90, 30 * side), (0, -8 * side)], BLUSH, 277 + side,
              depth=0, amp=0.6, outline=(INK, 4))
        ctx.pop()
    paper(ctx, circ_pts(0, 0, 16, 14), LIME, 279, depth=1, amp=0.4, outline=(INK, 4))
    ctx.pop()


# ---------------------------------------------------------------- 6. CTA
def s_cta(ctx, t):
    fill_bg(ctx, PAPER, 300)
    e = eoc(t / 0.3)
    torn(ctx, offset_pts([(-100, -100), (W + 100, -100), (W + 100, 330), (-100, 270)], 0, -500 * (1 - e)),
         PERI, 301, edge=(0, -10))
    torn(ctx, offset_pts([(-100, -100), (W + 100, -100), (W + 100, 180), (-100, 230)], 0, -500 * (1 - e)),
         LIME, 302, edge=(0, -10))
    torn(ctx, offset_pts([(-100, 1700), (W + 100, 1640), (W + 100, H + 100), (-100, H + 100)], 0, 500 * (1 - e)),
         BLUSH, 303)
    torn(ctx, offset_pts([(-100, 1790), (W + 100, 1820), (W + 100, H + 100), (-100, H + 100)], 0, 500 * (1 - e)),
         ICE, 304)
    for i in range(6):
        r = R("ctasp", i)
        sparkle(ctx, r.choice([r.uniform(60, 200), r.uniform(880, 1020)]), r.uniform(380, 1550),
                r.uniform(22, 44) * pop(t, 0.5 + i * 0.05, 0.2), [PERI, LIME, BLUSH][i % 3], 305 + i,
                rot=t * 120, depth=1.5)

    # logo stamp
    if t >= 0.4:
        d = t - 0.4
        s = lerp(1.9, 1.0, eic(d / 0.1)) if d < 0.1 else 1 + 0.04 * math.exp(-(d - 0.1) / 0.1) * math.cos(
            (d - 0.1) * 40)
        ctx.push(540, 800, -3, s, wob=1, seed=310)
        paper(ctx, rrect_pts(0, 0, 920, 640, 40), INK, 311, depth=4, amp=2)
        paper(ctx, rrect_pts(0, 0, 880, 600, 30), INK, 312, depth=0, amp=1.5)
        draw_text(ctx, "VIBE", 0, -150, 270, fill=LIME, back=None, under=PERI_D, seed=313, depth=0, wob=0.6)
        draw_text(ctx, "EDITING", 0, 70, 175, fill=PAPER, back=None, under=BLUSH_D, seed=314, depth=0, wob=0.6)
        draw_text(ctx, "by IDEABRO STUDIO", 0, 225, 62, fill=INK, back=BLUSH, seed=315, depth=1, pad=0.22,
                  rot=2, font="black")
        ctx.pop()
        confetti(ctx, t, 0.42, 540, 800, 40, 316, spread=1300, grav=2200, size=24)

    # enroll button
    s = pop(t, 1.2, 0.25) * (1 + 0.07 * beat_pulse(t, 0.4, 0.1, 1.6))
    press = 1.0 if 2.0 <= t < 2.2 else 0.0
    if s > 0:
        ctx.push(540, 1310, -2, s, wob=1, seed=320)
        sh = 16 * (1 - press)
        paper(ctx, rrect_pts(sh, sh, 760, 190, 95), INK, 321, depth=1, amp=1.2)
        ctx.push(16 - sh, 16 - sh)
        paper(ctx, rrect_pts(0, 0, 760, 190, 95), LIME, 322, depth=0, amp=1.2, outline=(INK, 7))
        draw_text(ctx, "ENROLL NOW", 0, 0, 104, back=None, seed=323, depth=0, wob=0.5, maxw=640)
        ctx.pop()
        ctx.pop()
    draw_text(ctx, "LINK IN BIO", 540, 1510, 64, fill=PAPER, back=INK, rot=2, sc=pop(t, 1.6), seed=330,
              pad=0.22)
    # cursor hand/arrow clicks the button
    if t > 1.6:
        f = eoc((t - 1.6) / 0.35)
        ax, ay = lerp(1000, 760, f), lerp(1800, 1350, f)
        cs = 0.85 if 2.0 <= t < 2.15 else 1.0
        ctx.push(ax, ay, -18, cs, wob=1, seed=340)
        arrow = [(0, 0), (0, 120), (30, 92), (55, 145), (80, 133), (56, 82), (95, 80)]
        paper(ctx, arrow, PAPER, 341, depth=2.5, amp=0.8, outline=(INK, 6))
        ctx.pop()


def offset_pts(pts, dx, dy):
    return [(x + dx, y + dy) for x, y in pts]


SCENE_FNS = {
    "hook": s_hook, "problem": s_problem, "reveal": s_reveal, "captions": s_captions, "motion": s_motion,
    "anim": s_anim, "ads": s_ads, "trans": s_trans, "recap": s_recap, "all": s_all, "with": s_with, "ai": s_ai,
    "payoff": s_payoff, "cta": s_cta,
}

SCENE_BG = {
    "hook": PERI, "problem": BLUSH, "reveal": ICE, "captions": LIME, "motion": PERI, "anim": BLUSH, "ads": ICE,
    "trans": PERI, "recap": LIME, "all": INK, "with": LIME, "ai": PERI, "payoff": LIME, "cta": PAPER,
}
