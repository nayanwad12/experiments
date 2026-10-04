"""The six beats of the explainer. Every cue time is locked to the narration (see narration.py)."""
import math

import numpy as np

from crayon import (BLUE, BLUSH, BROWN, GREEN, GREY, INK, LIME, ORANGE, PERI, PINK, PURPLE, RED, SKY, TAN,
                    TEAL, WHITE, YELLOW, H, W, M_about, M_translate, Pen, back_out, bezier, clamp01, cloud,
                    ease_in_out, ease_out, ellipse, heart, hrand, pop, rrect, seg, star)

# narration line starts (s) and word cues (absolute s), from the pauses in each Kokoro take
VO = {"hook": 0.5, "reveal": 8.35, "describe": 11.75, "prompt": 17.15, "ai": 19.75, "director": 25.85,
      "outro": 33.0}
CUE = {
    "remember": 0.5, "hours": 2.35, "cutting": 2.8, "dragging": 3.45, "keyframing": 4.05, "clip": 4.95,
    "square": 7.3,
    "newway": 8.35, "vibe_title": 10.15,
    "fighting": 12.3, "timeline": 12.75, "describe": 14.4, "plain": 15.7,
    "make": 17.15, "warm": 17.65, "punchy": 18.05, "dreamy": 18.65,
    "heavy": 20.6, "cuts": 22.05, "colors": 22.6, "captions": 23.15, "music": 23.75, "beat": 24.3,
    "weekend": 26.5, "coffee": 27.55, "director": 29.2, "keyframes": 31.2,
    "outro_title": 33.0, "say": 34.14, "life": 35.0,
}
DUR = 40.0
CUTS = [("old", 0.0, 8.1), ("reveal", 8.1, 11.55), ("describe", 11.55, 19.45), ("ai", 19.45, 25.55),
        ("director", 25.55, 32.75), ("outro", 32.75, DUR)]
WIPES = [  # (t0, dur, style, colour) -- the cut happens at the midpoint
    (7.8, 0.6, "zig", YELLOW), (11.3, 0.5, "spiral", PERI), (19.2, 0.5, "zig", PINK),
    (25.3, 0.5, "spiral", ORANGE), (32.5, 0.5, "zig", SKY)]


def drawn(t, t0, dur=0.6):
    """(stroke_draw, fill_draw) for a shape being sketched on: outline first, then colour it in."""
    a = seg(t, t0, t0 + dur * 0.55)
    b = seg(t, t0 + dur * 0.4, t0 + dur)
    return ease_out(a), ease_out(b)


# ----------------------------------------------------------------------------- characters & props
def person(p, x, y, s=1.0, t=0.0, eyes="dot", mouth="smile", hair="messy", shirt=BLUE, look=(4, 0),
           arm_l=None, arm_r=None, seed="me", beret=False):
    """Front-facing kid-drawing person. (x, y) = top of the shirt."""
    with p.push(M_about(x, y, s)):
        # arms (behind body): lists of points from the shoulder
        for side, arm in ((-1, arm_l), (1, arm_r)):
            if arm is None:
                arm = [(x + side * 62, y + 30), (x + side * 95, y + 110), (x + side * 80, y + 165)]
            p.line(arm, shirt, width=26, pressure=0.85, seed=(seed, "arm", side))
            hx, hy = arm[-1]
            p.shape(ellipse(hx, hy, 17, 17, 24), fill=TAN, seed=(seed, "hand", side), width=4.5, gap=6)
        p.shape(rrect(x - 72, y, 144, 200, 55), fill=shirt, seed=(seed, "body"), hatch=60)
        hx, hy = x, y - 78
        p.shape(ellipse(hx, hy, 74, 78), fill=TAN, seed=(seed, "head"), hatch=30, gap=8)
        p.shape(ellipse(hx - 46, hy + 18, 13, 8, 20), fill=BLUSH, stroke=None, seed=(seed, "ch1"), alpha=0.8)
        p.shape(ellipse(hx + 46, hy + 18, 13, 8, 20), fill=BLUSH, stroke=None, seed=(seed, "ch2"), alpha=0.8)
        if hair == "messy":
            for i in range(9):
                a = math.pi * (1.05 + i * 0.11)
                bx, by = hx + 70 * math.cos(a), hy + 72 * math.sin(a)
                tip = (hx + 110 * math.cos(a) + 12 * math.sin(i * 3 + t * 6),
                       hy + 112 * math.sin(a) - 8 * math.cos(i * 2.3 + t * 7))
                p.line([(bx, by), ((bx + tip[0]) / 2 + 10, (by + tip[1]) / 2 - 8), tip], BROWN, width=11,
                       seed=(seed, "hair", i))
        else:
            p.shape(np.vstack([ellipse(hx, hy - 4, 78, 80, 40, math.pi * 1.0, math.pi * 2.0),
                               [(hx + 60, hy - 30), (hx + 10, hy - 42), (hx - 40, hy - 34), (hx - 74, hy - 12)]]),
                    fill=BROWN, seed=(seed, "hair"), hatch=-20, gap=7)
        if beret:
            p.shape(ellipse(hx - 6, hy - 74, 72, 26, 40), fill=RED, seed=(seed, "beret"), hatch=10)
            p.line([(hx - 6, hy - 100), (hx - 2, hy - 116)], INK, width=7, seed=(seed, "stalk"))
        lx, ly = look
        for side in (-1, 1):
            ex, ey = hx + side * 27, hy - 8
            if eyes == "dot":
                p.shape(ellipse(ex, ey, 15, 17, 24), fill=WHITE, seed=(seed, "ew", side), width=4, gap=5, under=0.7)
                p.dot(ex + lx, ey + ly, 7, INK, seed=(seed, "ep", side))
            elif eyes == "square":
                p.shape(rrect(ex - 17, ey - 17, 34, 34, 3, 2), fill=WHITE, seed=(seed, "es", side), width=5,
                        gap=5, under=0.7)
                p.shape(rrect(ex - 7 + lx, ey - 7, 14, 14, 2, 2), fill=INK, stroke=None, seed=(seed, "esp", side),
                        under=0.9, gap=4)
            elif eyes == "happy":
                p.line(ellipse(ex, ey + 6, 13, 12, 14, math.pi * 1.1, math.pi * 1.9), INK, width=6,
                       seed=(seed, "eh", side))
            elif eyes == "tired":
                p.shape(ellipse(ex, ey, 15, 17, 24), fill=WHITE, seed=(seed, "ew", side), width=4, gap=5, under=0.7)
                p.dot(ex + lx, ey + 4 + ly, 7, INK, seed=(seed, "ep", side))
                p.line([(ex - 16, ey - 3), (ex + 16, ey - 3)], INK, width=5, seed=(seed, "lid", side))
                p.line(ellipse(ex, ey + 17, 12, 6, 10, 0.2, math.pi - 0.2), PURPLE, width=4, seed=(seed, "bag", side),
                       alpha=0.7)
        if mouth == "smile":
            p.line(ellipse(hx, hy + 26, 26, 18, 16, 0.25, math.pi - 0.25), INK, width=6, seed=(seed, "m"))
        elif mouth == "big":
            p.shape(np.vstack([ellipse(hx, hy + 22, 30, 28, 20, 0, math.pi)]), fill=RED, seed=(seed, "m"),
                    width=5, gap=5)
        elif mouth == "wavy":
            xs = np.linspace(hx - 24, hx + 24, 14)
            p.line(np.stack([xs, hy + 36 + 4 * np.sin((xs - hx) / 5)], 1), INK, width=5, seed=(seed, "m"))
        elif mouth == "o":
            p.shape(ellipse(hx, hy + 36, 10, 12, 20), fill=INK, seed=(seed, "m"), width=4)


def robot(p, x, y, s=1.0, t=0.0, arm_l=None, arm_r=None, seed="bot", eyes="dot", bounce=0.0):
    """Friendly crayon robot. (x, y) = centre of the body."""
    with p.push(M_about(x, y, s, dy=-bounce)):
        for side, arm in ((-1, arm_l), (1, arm_r)):
            if arm is None:
                arm = [(x + side * 95, y - 50), (x + side * 150, y + 10), (x + side * 160, y + 80)]
            p.line(arm, GREY, width=14, seed=(seed, "arm", side), pressure=0.75)
            hx, hy = arm[-1]
            p.shape(ellipse(hx, hy, 22, 22, 24), fill=ORANGE, seed=(seed, "hand", side), width=5, gap=6)
        # legs
        for side in (-1, 1):
            p.line([(x + side * 45, y + 110), (x + side * 48, y + 175)], GREY, width=16, seed=(seed, "leg", side))
            p.shape(rrect(x + side * 48 - 32, y + 165, 64, 30, 12), fill=INK, seed=(seed, "foot", side), gap=6)
        p.shape(rrect(x - 105, y - 85, 210, 200, 34), fill=TEAL, seed=(seed, "body"), hatch=55)
        p.shape(rrect(x - 60, y - 45, 120, 90, 18), fill=WHITE, seed=(seed, "panel"), width=5, gap=7)
        beat = 1 + 0.12 * max(0.0, math.sin(t * 2 * math.pi * 1.6)) ** 6
        with p.push(M_about(x, y, beat)):
            p.shape(heart(x, y + 2, 34), fill=RED, seed=(seed, "heart"), width=5, gap=6)
        # head
        hx, hy = x, y - 175
        p.line([(hx, hy - 75), (hx + 4, hy - 120)], INK, width=7, seed=(seed, "ant"))
        blink = 0.6 + 0.4 * (math.sin(t * 9) > 0)
        p.shape(ellipse(hx + 4, hy - 130, 16, 16, 20), fill=YELLOW if blink > 0.9 else ORANGE, seed=(seed, "bulb"),
                width=5)
        p.shape(rrect(hx - 120, hy - 78, 240, 160, 40), fill=PERI, seed=(seed, "head"), hatch=35)
        for side in (-1, 1):
            p.shape(rrect(hx + side * 120 - (12 if side > 0 else 14), hy - 25, 26, 50, 10), fill=ORANGE,
                    seed=(seed, "ear", side), width=5, gap=6)
        for side in (-1, 1):
            ex, ey = hx + side * 48, hy - 10
            if eyes == "dot":
                p.shape(ellipse(ex, ey, 26, 26, 28), fill=WHITE, seed=(seed, "ew", side), width=5, gap=5, under=0.75)
                p.dot(ex + 3, ey + 2, 11, INK, seed=(seed, "ep", side))
            else:
                p.line(ellipse(ex, ey + 8, 20, 16, 14, math.pi * 1.1, math.pi * 1.9), INK, width=7,
                       seed=(seed, "eh", side))
        p.line(ellipse(hx, hy + 36, 34, 18, 18, 0.2, math.pi - 0.2), INK, width=7, seed=(seed, "mouth"))


def clock(p, x, y, r, t, speed=0.0, seed="clock"):
    p.shape(ellipse(x, y, r, r), fill=WHITE, seed=(seed, "f"), width=7, gap=8, under=0.5)
    for i in range(12):
        a = i * math.pi / 6
        p.line([(x + 0.78 * r * math.cos(a), y + 0.78 * r * math.sin(a)),
                (x + 0.9 * r * math.cos(a), y + 0.9 * r * math.sin(a))], INK, width=4, seed=(seed, i), double=False)
    am = -math.pi / 2 + speed * 2 * math.pi
    ah = -math.pi / 2 + speed * 2 * math.pi / 12 + 1.0
    p.line([(x, y), (x + 0.7 * r * math.cos(am), y + 0.7 * r * math.sin(am))], RED, width=7, seed=(seed, "m"))
    p.line([(x, y), (x + 0.45 * r * math.cos(ah), y + 0.45 * r * math.sin(ah))], INK, width=9, seed=(seed, "h"))
    p.dot(x, y, 8, INK, seed=(seed, "c"))


def mug(p, x, y, s=1.0, color=RED, steam=0.0, t=0.0, seed="mug"):
    """(x, y) = bottom centre."""
    with p.push(M_about(x, y, s)):
        p.line(ellipse(x + 42, y - 50, 22, 24, 20, -math.pi / 2, math.pi / 2), INK, width=8, seed=(seed, "h"))
        p.shape(rrect(x - 45, y - 100, 90, 100, 14), fill=color, seed=(seed, "b"), hatch=70)
        for i in range(3):
            if steam <= 0:
                continue
            sx = x - 22 + i * 22
            ys = np.linspace(0, 1, 16)
            pts = np.stack([sx + 9 * np.sin(ys * 7 + t * 5 + i), y - 115 - ys * 90], 1)
            p.line(pts, GREY, width=6, seed=(seed, "s", i), alpha=steam * 0.8, draw=clamp01(steam * 1.5))


def scissors(p, x, y, s=1.0, open_=0.3, seed="sc", color=RED):
    with p.push(M_about(x, y, s)):
        for side in (-1, 1):
            a = side * open_
            ca, sa = math.cos(a), math.sin(a)
            tip = (x + 120 * ca, y + 120 * sa)
            p.line([(x - 10 * ca, y - 10 * sa), tip], GREY, width=22, seed=(seed, "bl", side), pressure=0.7)
            hx, hy = x - 55 * math.cos(-a), y - 55 * math.sin(-a)
            p.shape(ellipse(hx, hy + side * 6, 24, 18, 24), fill=None, stroke=color, width=11, seed=(seed, "hd", side))
        p.dot(x, y, 6, INK, seed=(seed, "piv"))


def note(p, x, y, s=1.0, color=PURPLE, seed="note"):
    with p.push(M_about(x, y, s)):
        p.shape(ellipse(x - 30, y + 40, 22, 16, 24), fill=color, seed=(seed, "a"), width=5, gap=5)
        p.shape(ellipse(x + 40, y + 28, 22, 16, 24), fill=color, seed=(seed, "b"), width=5, gap=5)
        p.line([(x - 10, y + 38), (x - 10, y - 50)], INK, width=7, seed=(seed, "s1"))
        p.line([(x + 60, y + 26), (x + 60, y - 62)], INK, width=7, seed=(seed, "s2"))
        p.line([(x - 10, y - 50), (x + 60, y - 62)], INK, width=13, seed=(seed, "bar"))


def palette(p, x, y, s=1.0, seed="pal"):
    with p.push(M_about(x, y, s)):
        blob = ellipse(x, y, 95, 72, 60)
        blob[:, 0] += 8 * np.sin(np.linspace(0, 6 * math.pi, 60))
        p.shape(blob, fill=TAN, seed=(seed, "b"), hatch=20)
        p.shape(ellipse(x + 45, y + 30, 16, 14, 20), fill=WHITE, seed=(seed, "hole"), width=4, gap=5)
        for i, (dx, dy, c) in enumerate(((-55, -10, RED), (-25, -42, YELLOW), (15, -45, GREEN), (52, -20, BLUE),
                                         (-35, 30, PURPLE))):
            p.dot(x + dx, y + dy, 15, c, seed=(seed, i))


def captions_icon(p, x, y, s=1.0, seed="cc"):
    with p.push(M_about(x, y, s)):
        p.shape(rrect(x - 95, y - 62, 190, 124, 22), fill=INK, seed=(seed, "b"), gap=7, under=0.6)
        p.text("CC", "title", 80, x, y + 4, hatch=True, colors=[YELLOW], outline_w=3, seed=(seed, "t"))


def keyframe(p, x, y, r=18, color=YELLOW, seed="kf", rot=0.0):
    with p.push(M_about(x, y, 1.0, rot)):
        p.shape(np.array([(x, y - r), (x + r, y), (x, y + r), (x - r, y)]), fill=color, seed=seed, width=5, gap=5)


def sparkle(p, x, y, r, color=YELLOW, seed="spk", rot=0.0):
    with p.push(M_about(x, y, 1.0, rot)):
        p.shape(star(x, y, r, r * 0.35, 4, 0.0), fill=color, seed=seed, width=4.5, gap=5)


def lightbulb(p, x, y, s, glow, t, seed="bulb", draw=(1.0, 1.0)):
    with p.push(M_about(x, y, s)):
        if glow > 0:
            for i in range(10):
                a = i * 2 * math.pi / 10 + 0.15
                r0, r1 = 150, 150 + 60 * glow + 10 * math.sin(t * 8 + i)
                p.line([(x + r0 * math.cos(a), y - 20 + r0 * math.sin(a)),
                        (x + r1 * math.cos(a), y - 20 + r1 * math.sin(a))], ORANGE, width=11,
                       seed=(seed, "ray", i), draw=glow)
        bulb = np.vstack([ellipse(x, y - 30, 100, 105, 50, math.pi * 0.72, math.pi * 2.28),
                          [(x + 45, y + 95), (x - 45, y + 95)]])
        p.shape(bulb, fill=YELLOW, seed=(seed, "g"), stroke_draw=draw[0], fill_draw=draw[1], hatch=40)
        p.shape(rrect(x - 48, y + 92, 96, 62, 12), fill=GREY, seed=(seed, "base"), stroke_draw=draw[0],
                fill_draw=draw[1])
        for k in range(2):
            p.line([(x - 46, y + 112 + k * 20), (x + 46, y + 112 + k * 20)], INK, width=5, seed=(seed, "th", k),
                   draw=draw[0])
        p.line([(x - 26, y + 90), (x - 18, y + 10), (x, y + 40), (x + 18, y + 10), (x + 26, y + 90)], ORANGE,
               width=7, seed=(seed, "fil"), draw=draw[1])


# ----------------------------------------------------------------------------- scene 1: the old way
CLIPS = []
_rng = np.random.default_rng(11)
for row in range(4):
    x = 880.0
    while x < 1650:
        w = float(_rng.uniform(22, 70))
        CLIPS.append((row, x, min(w, 1655 - x), [PINK, SKY, LIME, ORANGE, PERI, YELLOW][int(_rng.integers(6))]))
        x += w + float(_rng.uniform(2, 8))
_order = np.argsort([_rng.uniform() + c[1] / 2000 for c in CLIPS])
CLIP_ORDER = {int(i): k for k, i in enumerate(_order)}


def clip_count(t):
    """Clips pile up: slowly, then frantically on 'one tiny clip at a time'."""
    n = len(CLIPS)
    a = 0.45 * ease_in_out(seg(t, 0.4, CUE["clip"])) + 0.55 * seg(t, CUE["clip"], 7.2) ** 1.4
    return int(n * a)


def scene_old(p, t):
    cam = 1.0 + 0.06 * ease_in_out(seg(t, 0.0, 8.1))
    shake = 0.0
    if t > CUE["square"]:
        e = math.exp(-(t - CUE["square"]) * 6)
        shake = 10 * e * math.sin(t * 70)
    with p.push(M_about(1000, 520, cam, dx=shake)):
        # wall clock: hours fly by
        spin = 0.15 * t + 3.5 * ease_in_out(seg(t, CUE["hours"] - 0.3, 8.0))
        with p.push(M_about(150, 160, pop(t, 0.15))):
            clock(p, 150, 160, 85, t, spin)
        # "remember editing?"
        p.text("remember editing?", "hand", 60, 290, 150, INK, anchor="l", reveal=seg(t, CUE["remember"], 1.6),
               seed="rem")
        # verb tags above the monitor
        for i, (word, cue, c) in enumerate((("cutting", "cutting", RED), ("dragging", "dragging", BLUE),
                                            ("keyframing", "keyframing", PURPLE))):
            k = pop(t, CUE[cue], 0.4)
            if k > 0:
                x = 990 + i * 280
                with p.push(M_about(x, 140, k, (hrand("vt", i) - 0.5) * 0.15)):
                    p.text(word, "hand", 54, x, 140, c, seed=("verb", i))
                    p.line([(x - 95, 180), (x + 95, 176)], c, width=6, seed=("vu", i), draw=seg(t, CUE[cue] + 0.2, CUE[cue] + 0.5))
        # monitor
        p.shape(rrect(1220, 720, 60, 50, 6), fill=GREY, seed="stand")
        p.shape(rrect(1130, 755, 240, 22, 8), fill=GREY, seed="foot")
        p.shape([rrect(830, 215, 870, 520, 28), rrect(858, 240, 814, 470, 14)[::-1]], fill=INK, seed="mon", gap=8,
                under=0.7, hatch=20)
        # preview window with a doodled landscape
        p.shape(rrect(1080, 258, 370, 140, 8), fill=SKY, seed="pv", gap=8)
        p.shape(np.array([(1090, 388), (1180, 300), (1250, 360), (1300, 320), (1440, 388)]), fill=GREEN, seed="mtn",
                gap=7, width=4)
        p.dot(1395, 295, 20, YELLOW, seed="pvsun")
        # track lines
        for row in range(4):
            y = 455 + row * 62
            p.line([(870, y + 50), (1660, y + 50)], GREY, width=3, seed=("trk", row), double=False, alpha=0.6)
        n = clip_count(t)
        for i, (row, x, w, c) in enumerate(CLIPS):
            k = CLIP_ORDER[i]
            if k >= n:
                continue
            y = 455 + row * 62
            appear = clamp01((n - k) / 3.0)
            with p.push(M_about(x + w / 2, y + 22, back_out(appear))):
                p.shape(rrect(x, y, w, 44, 6, 3), fill=c, seed=("clip", i), width=4, gap=6, wob=0.6)
        # keyframes
        kk = seg(t, CUE["keyframing"], CUE["keyframing"] + 0.8)
        for j in range(9):
            if kk * 9 > j:
                keyframe(p, 900 + j * 88, 425, 13, YELLOW, seed=("kf", j))
        # playhead
        ph = 880 + (t * 140) % 780
        p.line([(ph, 412), (ph, 700)], RED, width=6, seed="ph")
        p.shape(np.array([(ph - 14, 404), (ph + 14, 404), (ph, 422)]), fill=RED, seed="phh", width=4)
        # cursor scurrying around + action icons
        cx = 1250 + 260 * math.sin(t * 2.3) + 60 * math.sin(t * 7.1)
        cy = 560 + 90 * math.sin(t * 3.1 + 1)
        k = pop(t, CUE["cutting"]) * (1 - seg(t, CUE["dragging"] + 0.1, CUE["dragging"] + 0.35))
        if k > 0:
            with p.push(M_about(cx + 70, cy - 40, 0.55 * k, 0.5)):
                scissors(p, cx + 70, cy - 40, 1.0, 0.25 + 0.2 * abs(math.sin(t * 14)), seed="sc1")
        k = pop(t, CUE["dragging"]) * (1 - seg(t, CUE["keyframing"] + 0.1, CUE["keyframing"] + 0.35))
        if k > 0:
            with p.push(M_about(cx + 60, cy, k)):
                p.line([(cx + 20, cy + 10), (cx + 130, cy + 10)], BLUE, width=9, seed="drag")
                p.line([(cx + 105, cy - 12), (cx + 132, cy + 10), (cx + 105, cy + 32)], BLUE, width=9, seed="draghd")
        p.shape(np.array([(cx, cy), (cx, cy + 52), (cx + 13, cy + 40), (cx + 24, cy + 62), (cx + 33, cy + 57),
                          (cx + 22, cy + 36), (cx + 39, cy + 36)]), fill=WHITE, seed="cur", width=5, gap=5, under=0.8)
        # mugs pile up on the desk
        for j, tm in enumerate((0.3, 3.0, 5.6)):
            k = pop(t, tm)
            if k > 0:
                mug(p, 610 + j * 85, 768, 0.75 * k, (RED, ORANGE, PURPLE)[j], steam=0.0 if j < 2 else 1.0, t=t,
                    seed=("mug", j))
        # the editor
        sq = t >= CUE["square"]
        lookx = 6 + 3 * math.sin(t * 9)
        bob = 3 * math.sin(t * 2)
        arm_r = [(380 + 62, 520 + 30), (380 + 130, 520 + 120), (530, 700)]
        person(p, 380, 520 + bob, 1.0, t, eyes="square" if sq else "tired", mouth="wavy" if not sq else "o",
               hair="messy", shirt=BLUE, look=(lookx, 0), arm_r=arm_r, seed="ed")
        if sq:  # sweat drops
            for j in range(2):
                k = pop(t, CUE["square"] + 0.1 + j * 0.15)
                if k > 0:
                    dx, dy = (470, 330) if j == 0 else (300, 350)
                    dy += 40 * seg(t, CUE["square"], 8.1)
                    with p.push(M_about(dx, dy, k)):
                        p.shape(np.vstack([[(dx, dy - 30)], ellipse(dx, dy, 14, 16, 20, -0.2, math.pi + 0.2)]),
                                fill=SKY, seed=("sw", j), width=4, gap=5)
        # desk (in front of the body)
        p.shape(rrect(60, 765, 1800, 46, 10), fill=BROWN, seed="desk", hatch=5, gap=10)
        p.line([(140, 811), (150, 1070)], BROWN, width=22, seed="dleg1")
        p.line([(1780, 811), (1770, 1070)], BROWN, width=22, seed="dleg2")


# ----------------------------------------------------------------------------- scene 2: a new way
def scene_reveal(p, t):
    t0 = CUE["newway"]
    # lightbulb sketched on, then lights up
    sd, fd = drawn(t, t0, 0.8)
    glow = ease_out(seg(t, t0 + 0.8, t0 + 1.2))
    k_up = ease_in_out(seg(t, CUE["vibe_title"] - 0.35, CUE["vibe_title"] + 0.1))
    by = 520 - 240 * k_up
    bs = 1.25 - 0.45 * k_up
    lightbulb(p, 960, by, bs, glow, t, draw=(sd, fd))
    p.text("a new way...", "hand", 70, 960, 860, INK, reveal=seg(t, t0 + 0.2, t0 + 1.0) * (1 - k_up), seed="nw")
    # title
    tt = CUE["vibe_title"]
    s = "VIBE EDITING"
    pops = [tt + i * 0.055 for i in range(len(s))]
    p.text(s, "title", 190, 960, 640, hatch=True, colors=[PURPLE, LIME, ORANGE, PINK, SKY, YELLOW, RED, TEAL],
           outline_w=7, pop_t=pops, seed="title", wave=4 * seg(t, tt + 0.8, tt + 1.4))
    p.line(bezier((520, 760), (800, 800), (1100, 730), (1400, 770), n=60), RED, width=12,
           draw=seg(t, tt + 0.55, tt + 0.95), seed="ul")
    for i, (x, y, r, c) in enumerate(((420, 470, 34, YELLOW), (1500, 470, 40, PINK), (1580, 760, 28, SKY),
                                      (360, 780, 26, LIME), (700, 320, 22, ORANGE), (1230, 330, 26, PURPLE))):
        k = pop(t, tt + 0.5 + i * 0.08)
        if k > 0:
            sparkle(p, x, y, r * k * (1 + 0.15 * math.sin(t * 6 + i)), c, seed=("sp", i), rot=0.4 * math.sin(t + i))


# ----------------------------------------------------------------------------- scene 3: describe the vibe
PROMPT = "make it warm, punchy, and a little dreamy"
P_WORDS = {"warm": PROMPT.index("warm"), "punchy": PROMPT.index("punchy"), "dreamy": PROMPT.index("dreamy")}


def prompt_reveal(t):
    """Letters typed in step with the spoken prompt (word starts pinned to the cues)."""
    keys = [(CUE["make"], 0), (CUE["warm"], P_WORDS["warm"]), (CUE["punchy"], P_WORDS["punchy"]),
            (CUE["dreamy"] - 0.25, P_WORDS["dreamy"] - 9), (CUE["dreamy"], P_WORDS["dreamy"]),
            (CUE["dreamy"] + 0.45, len(PROMPT))]
    ts = [k[0] for k in keys]
    ns = [k[1] for k in keys]
    return float(np.interp(t, ts, ns)) / len(PROMPT)


def scene_describe(p, t):
    # (a) the timeline gets scribbled out and tossed
    ta = 11.6
    k_out = ease_in_out(seg(t, 13.45, 13.95))
    if k_out < 1:
        with p.push(M_about(960, 470, 1.3 * (1 - k_out) * pop(t, ta, 0.4), -1.2 * k_out, dx=700 * k_out,
                            dy=90 - 290 * k_out)):
            p.shape(rrect(460, 380, 1000, 180, 18), fill=WHITE, seed="tl", gap=10, under=0.5)
            rng = np.random.default_rng(5)
            x = 480.0
            i = 0
            while x < 1430:
                w = float(rng.uniform(40, 110))
                for row in range(2):
                    p.shape(rrect(x, 400 + row * 75, min(w, 1440 - x), 60, 8, 3),
                            fill=[PINK, SKY, LIME, ORANGE, PERI][(i + row * 2) % 5], seed=("tlc", i, row), width=4,
                            gap=7)
                x += w + 6
                i += 1
            # the fight: a tangle of red scribble, then a big X
            fx = seg(t, CUE["fighting"], CUE["fighting"] + 0.5)
            p.line(bezier((440, 360), (1500, 600), (420, 600), (1480, 350), n=60), RED, width=12, draw=fx,
                   seed="x1")
            p.line([(440, 340), (1480, 600)], RED, width=16, draw=seg(t, CUE["timeline"], CUE["timeline"] + 0.2),
                   seed="x2")
            p.line([(1480, 340), (440, 600)], RED, width=16, draw=seg(t, CUE["timeline"] + 0.15, CUE["timeline"] + 0.35),
                   seed="x3")
        p.text("no more fighting the timeline", "hand", 72, 960, 250, INK, reveal=seg(t, 11.8, 12.9) * (1 - k_out),
               seed="nomore")
    # (b) just say it
    tb = 13.8
    if t >= tb:
        person(p, 260, 820 + 4 * math.sin(t * 2.4), 0.9 * pop(t, tb, 0.45), t, eyes="happy", mouth="big",
               hair="neat", shirt=GREEN, seed="me2",
               arm_r=[(260 + 62, 850), (260 + 120, 800), (260 + 150, 740)])
        sd, fd = drawn(t, tb + 0.15, 0.7)
        bubble = np.vstack([rrect(420, 330, 900, 300, 60, 10)])
        # tail toward the speaker
        tail = np.array([(500, 600), (420, 720), (600, 625)])
        p.shape(tail, fill=WHITE, seed="tail", stroke_draw=sd, fill_draw=fd, gap=9)
        p.shape(bubble, fill=WHITE, seed="bub", stroke_draw=sd, fill_draw=fd, gap=10, under=0.5)
        p.text("describe the vibe", "hand", 64, 870, 245, PURPLE, reveal=seg(t, CUE["describe"], CUE["describe"] + 0.6),
               seed="dtv")
        kp = pop(t, CUE["plain"], 0.4)
        if kp > 0:
            with p.push(M_about(1150, 690, kp, -0.06)):
                p.text("in plain words", "hand", 50, 1150, 690, GREY, seed="plain")
        rv = prompt_reveal(t)
        lines = ["make it warm, punchy,", "and a little dreamy"]
        n = rv * len(PROMPT)
        n1 = len(lines[0]) + 1
        p.text(lines[0], "brush", 84, 470, 425, INK, anchor="l", reveal=clamp01(n / len(lines[0])), seed="pl1")
        p.text(lines[1], "brush", 84, 470, 530, INK, anchor="l", reveal=clamp01((n - n1) / len(lines[1])), seed="pl2")
        if rv <= 0.0 or rv >= 1.0:  # blinking cursor
            if (t * 2.5) % 1 < 0.6:
                cx = 480 if rv <= 0 else 1135
                cy = 425 if rv <= 0 else 530
                p.line([(cx, cy - 38), (cx, cy + 38)], PURPLE, width=7, seed="caret", double=False)
        # word doodles
        k = pop(t, CUE["warm"], 0.45)
        if k > 0:
            with p.push(M_about(1560, 250, k, 0.3 * t)):
                for i in range(10):
                    a = i * math.pi / 5
                    p.line([(1560 + 92 * math.cos(a), 250 + 92 * math.sin(a)),
                            (1560 + 130 * math.cos(a), 250 + 130 * math.sin(a))], ORANGE, width=11, seed=("ray", i))
                p.shape(ellipse(1560, 250, 75, 75), fill=YELLOW, seed="sun", hatch=30)
            p.line(ellipse(1560, 260, 30, 18, 14, 0.3, math.pi - 0.3), INK, width=6, seed="sunsmile", alpha=k)
        k = pop(t, CUE["punchy"], 0.4)
        if k > 0:
            with p.push(M_about(1640, 560, k * (1 + 0.06 * math.sin(t * 20)), -0.1)):
                burst = star(1640, 560, 150, 85, 9, 0.2)
                p.shape(burst, fill=RED, seed="pow", hatch=20)
                p.text("POW!", "title", 76, 1640, 562, YELLOW, seed="powt", hatch=True, colors=[YELLOW], outline_w=5)
        k = pop(t, CUE["dreamy"], 0.5)
        if k > 0:
            fl = 10 * math.sin(t * 2.2)
            with p.push(M_about(1500, 870 + fl, k)):
                p.shape(cloud(1500, 870, 330, 150), fill=WHITE, stroke=BLUE, seed="cl", gap=9)
                p.shape(np.vstack([ellipse(1640, 800, 50, 50, 40, -math.pi * 0.6, math.pi * 0.6),
                                   ellipse(1615, 800, 36, 40, 40, math.pi * 0.55, -math.pi * 0.55)]),
                        fill=YELLOW, seed="moon", gap=6)
                for j in range(3):
                    sparkle(p, 1340 + j * 70, 760 - j * 30, 14 + 3 * j, PERI, seed=("zz", j), rot=t)


# ----------------------------------------------------------------------------- scene 4: AI does the work
CARDS = [("cuts", "cuts", 470, 300, RED), ("colors", "colors", 1450, 300, ORANGE),
         ("captions", "captions", 470, 760, BLUE), ("music", "music", 1450, 760, PURPLE)]


def beat_bounce(t):
    tb = CUE["beat"]
    if t < tb:
        return 0.0
    ph = (t - tb) / 0.3
    return 22 * abs(math.sin(ph * math.pi)) * math.exp(-0.05 * (t - tb))


def scene_ai(p, t):
    t0 = 19.6
    bb = beat_bounce(t)
    lift = ease_in_out(seg(t, CUE["heavy"] - 0.35, CUE["heavy"] + 0.25))
    drop = ease_in_out(seg(t, 21.6, 22.0))
    # robot with barbell
    ks = pop(t, t0, 0.5)
    rx, ry = 960, 600
    hand_y = ry + 60 - 300 * lift + 260 * drop
    if drop < 1:
        arm_l = [(rx - 95, ry - 50), (rx - 170, ry - 20 - 120 * lift), (rx - 175, hand_y)]
        arm_r = [(rx + 95, ry - 50), (rx + 170, ry - 20 - 120 * lift), (rx + 175, hand_y)]
    else:  # wave hello / conducting on the beat
        sw = math.sin(t * 6)
        arm_l = [(rx - 95, ry - 50), (rx - 170, ry - 100), (rx - 200, ry - 170 + 30 * sw)]
        arm_r = [(rx + 95, ry - 50), (rx + 170, ry - 100), (rx + 200, ry - 170 - 30 * sw)]
    robot(p, rx, ry, 0.95 * ks, t, arm_l=arm_l, arm_r=arm_r, eyes="happy" if lift > 0.5 else "dot", bounce=bb)
    if drop < 1 and ks > 0:
        by = hand_y + 900 * drop ** 2 - bb
        with p.push(M_about(rx, by, ks)):
            p.line([(rx - 300, by), (rx + 300, by)], GREY, width=16, seed="bar")
            for side in (-1, 1):
                p.shape(rrect(rx + side * 260 - 32, by - 85, 64, 170, 14), fill=INK, seed=("plate", side), gap=7)
            p.text("HOURS", "title", 44, rx, by - 60, RED, hatch=True, colors=[RED], outline_w=4, seed="hrs")
    p.text("heavy lifting", "hand", 62, 960, 120, INK, reveal=seg(t, 20.2, 21.0) * (1 - seg(t, 21.7, 22.0)),
           seed="hl")
    if t > 22.0:
        p.text("all on the beat!", "hand", 70, 960, 120, PURPLE, reveal=seg(t, CUE["beat"], CUE["beat"] + 0.6),
               seed="otb", wave=3)
    # four cards, each on its word
    for i, (label, cue, x, y, c) in enumerate(CARDS):
        k = pop(t, CUE[cue], 0.4)
        if k <= 0:
            continue
        b = beat_bounce(t + 0.075 * i)
        with p.push(M_about(x, y, k, (hrand("card", i) - 0.5) * 0.12, dy=-b)):
            p.shape(rrect(x - 170, y - 150, 340, 300, 30), fill=WHITE, stroke=c, width=8, seed=("card", i), gap=10,
                    under=0.55)
            if label == "cuts":
                scissors(p, x - 10, y - 30, 0.9, 0.25 + 0.15 * abs(math.sin(t * 10)), seed="sc2")
            elif label == "colors":
                palette(p, x, y - 30, 0.95, seed="pal")
            elif label == "captions":
                captions_icon(p, x, y - 30, 0.9, seed="cc")
            else:
                note(p, x - 10, y - 40, 0.95, seed="nt")
            p.text(label, "hand", 56, x, y + 100, c, seed=("cl", i))
    # musical notes float off on the beat
    if t > CUE["beat"]:
        for j in range(5):
            ph = (t - CUE["beat"] - j * 0.18)
            if ph <= 0:
                continue
            x = 700 + j * 130 + 30 * math.sin(ph * 4 + j)
            y = 520 - ph * 180
            with p.push(M_about(x, y, 0.45)):
                note(p, x, y, 1.0, [PINK, ORANGE, TEAL, PURPLE, RED][j], seed=("fn", j))


# ----------------------------------------------------------------------------- scene 5: weekend -> coffee; director
def calendar(p, x, y, s, t, seed="cal"):
    with p.push(M_about(x, y, s)):
        p.shape(rrect(x - 210, y - 170, 420, 340, 24), fill=WHITE, seed=(seed, "pg"), gap=10, under=0.5)
        p.shape(rrect(x - 210, y - 170, 420, 80, 20), fill=RED, seed=(seed, "hd"), gap=8)
        for j in range(2):
            p.dot(x - 120 + j * 240, y - 175, 13, INK, seed=(seed, "ring", j))
        p.text("WEEKEND", "title", 50, x, y - 128, hatch=True, colors=[WHITE], outline_w=3, seed=(seed, "t"))
        for j, d in enumerate(("SAT", "SUN")):
            cx = x - 100 + j * 200
            p.text(d, "print", 70, cx, y - 20, INK, seed=(seed, "d", j))
            fill = seg(t, CUE["weekend"] - 0.3 + j * 0.2, CUE["weekend"] + 0.1 + j * 0.2)
            if fill > 0:  # scribbled in = a weekend gone
                p.shape(rrect(cx - 80, y + 25, 160, 120, 14), fill=GREY, stroke=INK, seed=(seed, "box", j),
                        fill_draw=fill, stroke_draw=1.0, gap=9, hatch=60 + j * 50)
            else:
                p.shape(rrect(cx - 80, y + 25, 160, 120, 14), fill=None, seed=(seed, "box", j))


def director_chair(p, x, y, seed="chair"):
    """(x, y) = seat centre."""
    p.line([(x - 120, y), (x + 120, y + 260)], BROWN, width=18, seed=(seed, "l1"))
    p.line([(x + 120, y), (x - 120, y + 260)], BROWN, width=18, seed=(seed, "l2"))
    p.line([(x - 125, y - 210), (x - 125, y + 10)], BROWN, width=18, seed=(seed, "p1"))
    p.line([(x + 125, y - 210), (x + 125, y + 10)], BROWN, width=18, seed=(seed, "p2"))
    p.shape(rrect(x - 135, y - 10, 270, 30, 8), fill=RED, seed=(seed, "seat"), gap=8)


def scene_director(p, t):
    # (a) a whole weekend -> a coffee break
    split = 28.55
    if t < split + 0.5:
        out = ease_in_out(seg(t, split, split + 0.45))
        with p.push(M_translate(-1400 * out, 0)):
            kc = pop(t, 25.65, 0.45)
            calendar(p, 560, 520, 1.2 * kc, t)
            ka = seg(t, CUE["coffee"] - 0.3, CUE["coffee"] + 0.1)
            p.line(bezier((830, 520), (930, 420), (1060, 420), (1160, 520), n=40), INK, width=10, draw=ka, seed="arr")
            if ka >= 1:
                p.line([(1120, 470), (1162, 522), (1100, 540)], INK, width=10, seed="arrh")
            km = pop(t, CUE["coffee"], 0.45)
            if km > 0:
                mug(p, 1400, 700, 1.9 * km, ORANGE, steam=seg(t, CUE["coffee"] + 0.2, CUE["coffee"] + 0.8), t=t,
                    seed="bigmug")
                p.text("coffee break", "hand", 64, 1400, 800, BROWN, reveal=seg(t, CUE["coffee"] + 0.2, CUE["coffee"] + 0.8),
                       seed="cb")
    # (b) you direct, AI keyframes
    if t > split:
        inn = ease_in_out(seg(t, split, split + 0.45))
        with p.push(M_translate(1400 * (1 - inn), 0)):
            kd = pop(t, 28.75, 0.45)
            dx = 520
            with p.push(M_about(dx, 650, kd)):
                director_chair(p, dx, 650)
                p.shape(rrect(dx - 125, 445, 250, 70, 10), fill=INK, seed="backrest", gap=8, under=0.6)
                arm_r = [(dx + 62, 470), (dx + 130, 420), (dx + 170, 360)]
                person(p, dx, 440, 1.0, t, eyes="dot", mouth="big", hair="neat", shirt=PURPLE, look=(5, -2),
                       arm_r=arm_r, seed="dir", beret=True)
                # megaphone
                with p.push(M_about(dx + 175, 350, 1.0, -0.5)):
                    p.shape(np.array([(dx + 165, 335), (dx + 290, 285), (dx + 290, 415), (dx + 165, 365)]),
                            fill=YELLOW, seed="mega", gap=8)
                    shout = (t * 3) % 1
                    for j in range(3):
                        p.line(ellipse(dx + 300, 350, 30 + 25 * j + 20 * shout, 50 + 25 * j + 20 * shout, 12, -0.6,
                                       0.6), ORANGE, width=7, seed=("sh", j), alpha=1 - shout * 0.6)
            p.text("YOU: the vibe", "hand", 64, 520, 980, PURPLE, reveal=seg(t, CUE["director"], CUE["director"] + 0.6),
                   seed="you")
            kr = pop(t, 30.1, 0.45)
            if kr > 0:
                robot(p, 1400, 640, 0.85 * kr, t, eyes="happy",
                      arm_l=[(1400 - 95, 590), (1400 - 160, 520), (1400 - 150 + 25 * math.sin(t * 9), 440)],
                      arm_r=[(1400 + 95, 590), (1400 + 160, 520), (1400 + 150 - 25 * math.sin(t * 9), 440)])
                # juggling keyframes
                for j in range(5):
                    ph = (t * 1.1 + j / 5) % 1
                    jx = 1400 + 190 * math.cos(ph * 2 * math.pi)
                    jy = 300 - 150 * abs(math.sin(ph * math.pi * 2)) * 0.9 - 40 * math.sin(ph * 2 * math.pi)
                    keyframe(p, jx, jy, 28 * kr, [YELLOW, ORANGE, PINK, LIME, SKY][j], seed=("jk", j), rot=t * 3 + j)
            p.text("AI: the keyframes", "hand", 64, 1400, 980, TEAL,
                   reveal=seg(t, CUE["keyframes"] - 0.4, CUE["keyframes"] + 0.3), seed="aik")


# ----------------------------------------------------------------------------- scene 6: outro
def scene_outro(p, t):
    tt = CUE["outro_title"]
    s = "VIBE EDITING"
    pops = [tt + i * 0.05 for i in range(len(s))]
    alive = seg(t, CUE["life"], CUE["life"] + 0.6)
    p.text(s, "title", 200, 960, 440, hatch=True, colors=[PURPLE, LIME, ORANGE, PINK, SKY, YELLOW, RED, TEAL],
           outline_w=7, pop_t=pops, seed="title2", wave=3 + 5 * alive)
    p.text("say the vibe.", "brush", 74, 960, 610, INK, reveal=seg(t, CUE["say"], CUE["say"] + 0.6), seed="say")
    p.text("watch it come to life.", "brush", 74, 960, 700, RED, reveal=seg(t, CUE["life"] - 0.1, CUE["life"] + 0.9),
           seed="life")
    p.text("by Ideabro Studio", "print", 46, 960, 900, GREY, reveal=seg(t, 37.0, 37.8), seed="by")
    # doodles drawn on, then they come alive and bob around
    items = [("sun", 250, 230), ("cloud", 1660, 220), ("heart", 300, 830), ("note", 1640, 830),
             ("star", 640, 170), ("star2", 1310, 160), ("kf", 1500, 600), ("kf2", 420, 560)]
    for i, (kind, x, y) in enumerate(items):
        d0 = tt + 0.4 + i * 0.12
        sd, fd = drawn(t, d0, 0.6)
        if sd <= 0:
            continue
        bob = alive * (18 * math.sin(t * 3.2 + i * 1.3))
        rot = alive * 0.15 * math.sin(t * 2.4 + i)
        sc = 1 + alive * 0.08 * math.sin(t * 5 + i)
        with p.push(M_about(x, y, sc, rot, dy=bob)):
            if kind == "sun":
                for j in range(9):
                    a = j * 2 * math.pi / 9 + t * 0.8 * alive
                    p.line([(x + 80 * math.cos(a), y + 80 * math.sin(a)), (x + 115 * math.cos(a), y + 115 * math.sin(a))],
                           ORANGE, width=10, seed=("osr", j), draw=fd)
                p.shape(ellipse(x, y, 65, 65), fill=YELLOW, seed="osun", stroke_draw=sd, fill_draw=fd)
            elif kind == "cloud":
                p.shape(cloud(x, y, 260, 120), fill=WHITE, stroke=BLUE, seed="ocl", stroke_draw=sd, fill_draw=fd)
            elif kind == "heart":
                p.shape(heart(x, y, 80), fill=PINK, seed="oh", stroke_draw=sd, fill_draw=fd)
            elif kind == "note":
                if fd > 0:
                    note(p, x, y, 1.1 * fd, PURPLE, seed="onote")
            elif kind.startswith("star"):
                p.shape(star(x, y, 55, 24), fill=YELLOW if kind == "star" else LIME, seed=("ost", kind),
                        stroke_draw=sd, fill_draw=fd)
            else:
                if fd > 0:
                    keyframe(p, x, y, 32 * fd, ORANGE if kind == "kf" else SKY, seed=("okf", kind), rot=alive * t)


SCENES = {"old": scene_old, "reveal": scene_reveal, "describe": scene_describe, "ai": scene_ai,
          "director": scene_director, "outro": scene_outro}


def wipe_path(style):
    if style == "zig":
        pts = []
        for i in range(16):
            x = -150 + i * 150
            pts.append((x, -140) if i % 2 == 0 else (x + 60, H + 140))
        return np.array(pts, float)
    a = np.linspace(0, 1, 400)
    r = 1250 * (1 - a) + 10
    th = a * 2 * math.pi * 4.2
    return np.stack([W / 2 + r * np.cos(th), H / 2 + r * np.sin(th) * 0.75], 1)


def draw_wipes(p, t):
    for t0, dur, style, c in WIPES:
        u = seg(t, t0, t0 + dur)
        if u <= 0 or u >= 1:
            continue
        pts = wipe_path(style)
        if u < 0.5:
            a, b = 0.0, ease_in_out(u * 2)
        else:
            a, b = ease_in_out((u - 0.5) * 2), 1.0
        for k in range(2):
            p.line(pts, c, width=240 if style == "zig" else 230, pressure=0.92, draw=b, start=a,
                   seed=("wipe", t0, k), double=False, wob=3.0, scale_width=False)


def render(p, t):
    for name, a, b in CUTS:
        if a <= t < b or (name == "outro" and t >= a):
            SCENES[name](p, t)
            break
    draw_wipes(p, t)
