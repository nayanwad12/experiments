"""Reel 01: "This claymation has no clay." Prompt -> a stop-motion clay film, all in code.

    python3 build.py sheet | stills 1 5 9 | draft | render | sound | all
"""
import math
import sys
from pathlib import Path

import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
sys.path.insert(0, str(HERE))
import clay as C  # noqa: E402
from kit import (W, H, INK, LIME, WHITE, Captions, Film, clamp, e_back, e_out, endcard, fill, lerp,  # noqa: E402
                 prog, prompt_bar, rrect, stroke, text, vignette)
from script import LINES, VOICE  # noqa: E402
from voice import Script, narrate  # noqa: E402

vo = narrate(LINES, HERE / "work", VOICE)
S = Script(vo, [("hook", 0.25), ("nos", 0.3), ("one", 0.45), ("code", "@", 9.45), ("detail", 0.55),
                ("this", "@", 16.35), ("cta", 0.4)])
END_T = S.end("cta") + 0.45
DUR = END_T + 3.0
FPS = 30
SFPS = 12                                    # stop-motion exposures per second

# ---------------------------------------------------------------- timeline
NO_ICONS = [(S.find("nos", "camera"), "camera"), (S.find("nos", "studio"), "light"), (S.find("nos", "AI"), "ai")]
NO_POPS = [S.w("nos", 0), S.w("nos", 2), S.w("nos", 4)]
PROMPT = "a clay robot watering a tiny plant at sunrise, cozy stop-motion"
UI_T0 = S.t("one") - 0.25
TYPE_T0, TYPE_T1 = S.t("one") + 0.15, S.t("one") + 2.55
SEND_T = TYPE_T1 + 0.3
BUILD_T = SEND_T + 0.35                       # the clay world starts assembling
SLAB_T, HILLS_T, POT_T, ROBOT_T = BUILD_T, BUILD_T + 0.3, BUILD_T + 0.75, BUILD_T + 1.2
SUN_T0, SUN_T1 = BUILD_T + 0.2, BUILD_T + 2.2
THUMB_T = S.t("detail")
WOBBLE_T = S.find("detail", "wobble")
JITTER_T = S.find("detail", "jitter")
WATER_T0, WATER_T1 = JITTER_T - 0.3, S.t("this") + 0.2
GROW_T0, GROW_T1 = S.end("detail") - 0.2, S.t("this") + 0.5
BLOOM_T = S.find("this", "vibe")
TITLE_T = BLOOM_T - 0.15
WAVE_T = S.t("cta") + 0.3
HOOK_TITLE = [S.find("hook", "no"), S.find("hook", "clay")]
SCENE_NOS = S.t("nos") - 0.12
Z0, FOC = 1.3, (560, 1250)        # base camera: the diorama fills the 9:16 frame

# ---------------------------------------------------------------- palette
SKY_TOP, SKY_MID, SKY_LOW = "#8FC9EE", "#FFD9B8", "#FFB48A"
GRASS, GRASS_DK, SOIL = "#7DBE5A", "#5E9B43", "#5B3A29"
TEAL, TEAL_LT, SCREEN = "#3BB5A7", "#69D2C3", "#1F2B33"
ORANGE, POT, POT_DK = "#F28C38", "#D46C46", "#B65537"
LEAF, PINK, YOLK, RED = "#62B947", "#FF8FB3", "#FFD34D", "#E84B4B"


def step(t):
    """stop-motion clock: animation advances in 1/12 s exposures."""
    return math.floor(t * SFPS) / SFPS, int(t * SFPS)


# ---------------------------------------------------------------- set pieces
def backdrop(c, ts, f, sun_k=1.0):
    sh = skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, 1300)],
                                        [C.col(SKY_TOP), C.col(SKY_MID), C.col(SKY_LOW)], [0.0, 0.62, 1.0])
    c.drawPaint(skia.Paint(Shader=sh))
    c.save()
    c.clipRect(skia.Rect.MakeWH(W, H))
    c.drawPaint(C.tex_paint(3, 0.22, 1.6))
    c.restore()
    # sun
    sy = lerp(1200, 600, e_out(sun_k))
    glow = skia.GradientShader.MakeRadial(skia.Point(780, sy), 360, [C.col("#FFF2B0", 0.7), C.col("#FFF2B0", 0)])
    c.drawCircle(780, sy, 360, skia.Paint(Shader=glow))
    C.clay(c, C.blob(780, sy, 120, 118, 5, 0.03, 1.2, f), "#FFC93C", 5, cast=False, gloss=0.3)
    # clouds drift (stepped)
    for i, (x0, y, s) in enumerate(((150, 420, 1.0), (640, 300, 0.75), (930, 520, 0.85))):
        x = (x0 + ts * 14 * (1 + i * 0.3)) % 1400 - 160
        parts = [C.blob(x + dx * s, y + dy * s, r * s, r * 0.82 * s, 40 + i * 7 + j, 0.05, 1.0, f, n=24)
                 for j, (dx, dy, r) in enumerate(((-70, 10, 62), (0, -18, 80), (75, 8, 58)))]
        C.clay(c, C.union(parts), "#FFFFFF", 40 + i, cast=True, cast_alpha=0.12, tex=0.3)


def hills(c, f, k=1.0):
    if k <= 0:
        return
    rise = (1 - C.back_out(clamp(k), 1.4)) * 300
    C.clay(c, C.blob(230, 1220 + rise, 420, 190, 11, 0.04, 1.5, f), GRASS_DK, 11, cast=False, tex=0.45)
    C.clay(c, C.blob(900, 1240 + rise * 1.2, 380, 160, 12, 0.04, 1.5, f), "#6AAE4E", 12, cast=False, tex=0.45)


def slab(c, f, k=1.0):
    if k <= 0:
        return
    y = lerp(-900, 0, C.bounce_land(clamp(k)))
    p = C.lumpy_rrect(-60, 1235 + y, W + 120, 900, 60, 21, 3.0, 1.2, f)
    C.clay(c, p, GRASS, 21, cast=False, tex=0.5, gloss=0.08)
    # little clay flowers in the grass
    for i in range(7):
        x = 60 + i * 160 + 30 * math.sin(i * 3)
        yy = 1500 + 120 * ((i * 37) % 3) + y
        C.clay(c, C.blob(x, yy, 13, 11, 60 + i, 0.08, 0.8, f, n=16), ("#FFFFFF", YOLK, PINK)[i % 3], 60 + i,
               cast=True, cast_alpha=0.2, tex=0.2)


def robot(c, x, y, s, f, arm=0.0, can_tilt=0.0, blink=False, wave=0.0, hop=0.0, sq=(1, 1), boil=1.0):
    c.save()
    c.translate(x, y - hop)
    c.scale(s * sq[0], s * sq[1])
    b = boil
    # ground shadow
    c.drawOval(skia.Rect.MakeXYWH(-120, -16, 240, 34), C.paint("#1a1208", 0.28 * (1 - min(hop / 200, 0.7)), blur=10))
    # feet
    for sx in (-1, 1):
        C.clay(c, C.blob(sx * 48, -22, 38, 26, 70 + sx, 0.05, b, f), "#3A3A44", 70 + sx, cast=False, gloss=0.2)
    # body
    C.clay(c, C.lumpy_rrect(-88, -215, 176, 190, 46, 80, 2.2, b, f), TEAL, 80)
    C.clay(c, C.lumpy_rrect(-52, -170, 104, 92, 22, 81, 1.4, b, f), "#E7F4EF", 81, cast=False, tex=0.35)
    for i, cc in enumerate((RED, YOLK, "#4C8DFF")):
        C.clay(c, C.blob(-28 + i * 28, -124, 11, 11, 82 + i, 0.06, b * 0.5, f, n=14), cc, 82 + i, cast=False,
               gloss=0.4, tex=0.2)
    # arm on the far side (waving arm)
    wa = math.sin(wave * 2 * math.pi * 2) * 0.6 if wave > 0 else 0
    sx0, sy0 = -88, -175
    ex = sx0 - 70 * math.cos(0.9 + wa * 0.8 * (wave > 0))
    ey = sy0 + 60 - 140 * (wave > 0) * min(1, wave * 4)
    C.clay_stroke(c, [(sx0 + 10, sy0), ((sx0 + ex) / 2 - 12, (sy0 + ey) / 2 + 8), (ex, ey)], 26, TEAL_LT, 90,
                  cast=False, tex=0.35)
    C.clay(c, C.blob(ex, ey, 22, 20, 91, 0.06, b, f), "#3A3A44", 91, cast=False)
    # head
    C.clay(c, C.lumpy_rrect(-100, -360, 200, 150, 58, 100, 2.2, b, f), TEAL_LT, 100)
    C.clay(c, C.lumpy_rrect(-72, -333, 144, 96, 32, 101, 1.4, b, f), SCREEN, 101, cast=False, tex=0.25, gloss=0.3)
    if blink:
        for sx in (-1, 1):
            C.clay_stroke(c, [(sx * 30 - 13, -290), (sx * 30, -284), (sx * 30 + 13, -290)], 7, "#7FF2E0", 102,
                          cast=False, tex=0.1)
    else:
        for sx in (-1, 1):
            C.clay(c, C.blob(sx * 30, -293, 15, 19, 103 + sx, 0.05, b * 0.5, f, n=16), "#7FF2E0", 103 + sx,
                   cast=False, gloss=0.5, tex=0.1)
    C.clay_stroke(c, [(-20, -262), (0, -254), (20, -262)], 7, "#7FF2E0", 105, cast=False, tex=0.1)
    # cheeks
    for sx in (-1, 1):
        c.drawOval(skia.Rect.MakeXYWH(sx * 52 - 11, -268, 22, 12), C.paint(PINK, 0.65, blur=2))
    # antenna
    C.clay_stroke(c, [(0, -358), (5, -392), (10, -420)], 9, "#3A3A44", 106, cast=False, tex=0.2)
    C.clay(c, C.blob(10, -430, 19, 19, 107, 0.05, b, f, n=16), RED, 107, cast=False, gloss=0.45)
    # near arm + watering can
    ang = lerp(0.25, -0.55, arm)
    sx1, sy1 = 84, -170
    hx, hy = sx1 + 95 * math.cos(ang), sy1 + 95 * math.sin(ang) + 40
    C.clay_stroke(c, [(sx1 - 6, sy1), ((sx1 + hx) / 2, (sy1 + hy) / 2 + 12), (hx, hy)], 28, TEAL_LT, 108,
                  cast=False, tex=0.35)
    c.save()
    c.translate(hx + 26, hy + 8)
    c.rotate(math.degrees(can_tilt))
    C.clay_stroke(c, [(-30, -36), (0, -70), (32, -36)], 13, "#C96A22", 110, cast=False, tex=0.3)   # handle
    C.clay(c, C.lumpy_rrect(-42, -42, 88, 78, 22, 111, 1.6, b, f), ORANGE, 111)
    C.clay_stroke(c, [(40, -10), (82, -34), (112, -58)], 15, ORANGE, 112, cast=False, tex=0.3)     # spout
    C.clay(c, C.blob(116, -62, 15, 11, 113, 0.06, b, f, rot=-0.6), "#C96A22", 113, cast=False)
    c.restore()
    C.clay(c, C.blob(hx, hy, 23, 21, 109, 0.06, b, f), "#3A3A44", 109, cast=False)
    c.restore()
    # spout tip in world space (for water)
    ca, sa = math.cos(can_tilt), math.sin(can_tilt)
    tx, ty = 116 * ca + 62 * sa, 116 * sa - 62 * ca
    return x + s * (hx + 26 + tx), y - hop + s * (hy + 8 + ty)


def plant(c, x, y, f, grow=0.0, bloom=0.0, pot_k=1.0, boil=1.0):
    if pot_k <= 0:
        return
    drop = lerp(-1100, 0, C.bounce_land(clamp(pot_k)))
    sq = C.squash_at(pot_k * 0.6, 0.33, 0.25, 0.25) if pot_k < 1 else (1, 1)
    c.save()
    c.translate(x, y + drop)
    c.scale(sq[0], sq[1])
    c.drawOval(skia.Rect.MakeXYWH(-100, -14, 200, 30), C.paint("#1a1208", 0.28, blur=9))
    # stem + leaves + flower (behind the rim)
    g = clamp(grow)
    if g > 0:
        top = -150 - 260 * g
        pts = [(0, -140), (-12 + 6 * math.sin(f * 0.7) * 0.2, (-140 + top) / 2), (6, top)]
        C.clay_stroke(c, pts, 14 + 4 * g, LEAF, 200, cast=False, tex=0.3)
        for i, (fr, side) in enumerate(((0.45, -1), (0.7, 1), (0.25, 1))):
            if g < fr * 0.8:
                continue
            k = clamp((g - fr * 0.8) / 0.3)
            ly = -140 + (top + 140) * fr
            C.clay(c, C.blob(side * 46 * k, ly - 4, 50 * k + 1, 22 * k + 1, 210 + i, 0.06, boil, f,
                             rot=side * -0.5), LEAF, 210 + i, cast=False, tex=0.4)
        if bloom > 0:
            bk = C.back_out(clamp(bloom), 2.2)
            for i in range(6):
                a = i * math.pi / 3 + 0.3
                px, py = 6 + 44 * bk * math.cos(a), top + 44 * bk * math.sin(a)
                C.clay(c, C.blob(px, py, 34 * bk + 1, 24 * bk + 1, 220 + i, 0.07, boil, f, rot=a), PINK, 220 + i,
                       cast=False, tex=0.35)
            C.clay(c, C.blob(6, top, 28 * bk + 1, 28 * bk + 1, 230, 0.06, boil, f), YOLK, 230, cast=False, gloss=0.4)
        elif g > 0.9:
            C.clay(c, C.blob(6, top, 18, 22, 231, 0.06, boil, f), "#8FD06E", 231, cast=False)
    # pot
    C.clay(c, C.lumpy_poly([(-80, -150), (80, -150), (62, 0), (-62, 0)], 240, 1.8, boil=boil, f=f), POT, 240)
    C.clay(c, C.lumpy_rrect(-96, -178, 192, 46, 18, 241, 1.5, boil, f), POT_DK, 241, cast=False)
    C.clay(c, C.blob(0, -168, 78, 14, 242, 0.05, boil * 0.5, f), SOIL, 242, cast=False, tex=0.6, gloss=0)
    c.restore()


def water(c, sx, sy, tx, ty, ts, k):
    """falling clay droplets from the spout to the soil."""
    if k <= 0:
        return
    for i in range(7):
        ph = (ts * 1.4 + i / 7) % 1.0
        x = lerp(sx, tx, ph) + 10 * math.sin(i * 2.1)
        y = sy + (ty - sy) * ph ** 1.6
        C.clay(c, C.blob(x, y, 9, 13, 300 + i, 0.08, 0.6, i), "#6EC8FF", 300 + i, cast=False, gloss=0.6, tex=0.15)


def clay_title(c, words, f, t, t_land, y=360, size=170, color=LIME, dy_line=190):
    """hand-rolled clay letters dropping in one by one."""
    for li, (word, wc) in enumerate(words):
        gl = C.glyph_paths(word, "Montserrat-Black.ttf", size, tracking=6, seed=li * 11 + 3, lump=1.6)
        for gi, (p, cx) in enumerate(gl):
            tl = t_land + li * 0.25 + gi * 0.06
            k = clamp((t - tl + 0.35) / 0.35)
            if k <= 0:
                continue
            yy = y + li * dy_line + lerp(-700, 0, C.bounce_land(k))
            sq = C.squash_at(t, tl, 0.3, 0.22)
            q = C.xform(p, W / 2 + 0 * cx, yy, sq[0], sq[1], (gi % 2 * 2 - 1) * 2.5, cx, 0)
            C.clay_letter(c, q, wc, li * 13 + gi, depth=12)


# ---------------------------------------------------------------- icons for "no camera / studio / AI video"
def icon(c, kind, cx, cy, s, f):
    c.save()
    c.translate(cx, cy)
    c.scale(s, s)
    if kind == "camera":
        C.clay(c, C.lumpy_rrect(-150, -95, 300, 200, 40, 400, 2.4, 1, f), "#3D3F4A", 400)
        C.clay(c, C.lumpy_rrect(-70, -140, 120, 60, 20, 401, 1.6, 1, f), "#2C2E36", 401)
        C.clay(c, C.blob(0, 5, 78, 78, 402, 0.03, 1, f), "#1D1E24", 402, cast=False)
        C.clay(c, C.blob(0, 5, 50, 50, 403, 0.03, 1, f), "#5BA8FF", 403, cast=False, gloss=0.6)
        C.clay(c, C.blob(105, -60, 18, 14, 404, 0.05, 1, f), RED, 404, cast=False)
    elif kind == "light":
        for a in (-0.35, 0, 0.35):
            C.clay_stroke(c, [(0, -10), (math.sin(a) * 170, 170)], 13, "#3A3A44", 410, cast=False)
        C.clay(c, C.lumpy_poly([(-150, -170), (150, -170), (95, -10), (-95, -10)], 411, 2.0, f=f), "#3D3F4A", 411)
        C.clay(c, C.lumpy_poly([(-118, -150), (118, -150), (80, -30), (-80, -30)], 412, 1.6, f=f), "#FFF3C4", 412,
               cast=False, gloss=0.5)
    else:  # AI video generator: film frame + sparkle
        C.clay(c, C.lumpy_rrect(-160, -110, 320, 220, 34, 420, 2.4, 1, f), "#8B6CF0", 420)
        for i in range(5):
            for sy in (-88, 88):
                C.clay(c, C.lumpy_rrect(-135 + i * 60, sy - 10, 32, 20, 6, 421 + i, 0.8, 0, f), "#2A1F55", 421,
                       cast=False, tex=0.2, gloss=0)
        for gi, (p, cx) in enumerate(C.glyph_paths("AI", "Montserrat-Black.ttf", 120, 4, seed=9, lump=1.2)):
            C.clay_letter(c, C.xform(p, 0, 42, 1, 1, 0, cx, 0), WHITE, 430 + gi, depth=6, cast=False)
        C.clay(c, C.star_path(118, -70, 44, 0.36, 4, 0.2), YOLK, 440, cast=False, gloss=0.5)
    c.restore()


def red_x(c, cx, cy, k, f, s=1.0):
    if k <= 0:
        return
    L = 170 * s * C.back_out(clamp(k), 1.8)
    C.clay_stroke(c, [(cx - L, cy - L), (cx + L, cy + L)], 34 * s, RED, 500, cast=True)
    if k > 0.35:
        L2 = 170 * s * C.back_out(clamp((k - 0.35) / 0.65), 1.8)
        C.clay_stroke(c, [(cx + L2, cy - L2), (cx - L2, cy + L2)], 34 * s, RED, 501, cast=True)


# ---------------------------------------------------------------- the world
def world(c, t, ts, f, built=True):
    """The diorama. built=False -> assembles on the BUILD_T clock; True -> finished (hook)."""
    if built:
        slab_k = hills_k = pot_k = robot_k = sun_k = 1.0
        grow, bloom, arm, tilt = 1.0, 1.0, 0.2, 0.0
    else:
        hills_k = prog(ts, HILLS_T, 0.5)
        slab_k = prog(ts, SLAB_T, 0.5)
        pot_k = prog(ts, POT_T, 0.5)
        robot_k = prog(ts, ROBOT_T, 0.6)
        sun_k = prog(ts, SUN_T0, SUN_T1 - SUN_T0)
        grow = e_out(prog(ts, GROW_T0, GROW_T1 - GROW_T0))
        bloom = prog(ts, BLOOM_T, 0.5)
        pour = prog(ts, WATER_T0, 0.5) * (1 - prog(ts, WATER_T1, 0.4))
        arm, tilt = pour, -0.65 * pour
    backdrop(c, ts, f, sun_k)
    hills(c, f, hills_k)
    slab(c, f, slab_k)
    wob = 1.0 + (2.6 if (not built and WOBBLE_T <= ts < JITTER_T) else 0)
    plant(c, 720, 1395, f, grow, bloom, pot_k, boil=wob)
    if robot_k > 0:
        # hop in from the left: two hops
        hk = clamp(robot_k)
        x = lerp(-200, 360, e_out(hk))
        hop = abs(math.sin(hk * math.pi * 2)) * 140 * (1 - hk)
        land = ROBOT_T + 0.6
        sq = C.squash_at(ts, land, 0.35, 0.2)
        blink = (int(ts * 12) % 40) in (0, 1)
        wave = prog(ts, WAVE_T, 1.2) if not built else 0
        sx, sy = robot(c, x, 1420, 1.05, f, arm, tilt, blink, wave * (wave < 1), hop, sq, boil=wob)
        if not built and arm > 0.6:
            water(c, sx, sy, 715, 1225, ts, arm)


def scene_nos(c, t, ts, f):
    sh = skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, H)],
                                        [C.col("#D9D2FF"), C.col("#B9B0F2")])
    c.drawPaint(skia.Paint(Shader=sh))
    c.drawPaint(C.tex_paint(17, 0.3, 1.4))
    ys = [430, 860, 1290]
    for i, ((tx, kind), tp, y) in enumerate(zip(NO_ICONS, NO_POPS, ys)):
        k = prog(ts, tp - 0.05, 0.35)
        if k <= 0:
            continue
        s = 0.95 * C.back_out(k, 2.4)
        icon(c, kind, W / 2, y, s, f)
        red_x(c, W / 2, y, prog(ts, tx + 0.1, 0.3), f, 0.95)


def scene_prompt(c, t):
    c.drawRect(skia.Rect.MakeWH(W, H), fill("#0F0F14"))
    glow = skia.GradientShader.MakeRadial(skia.Point(W / 2, 880), 700, [C.col(LIME, 0.10), C.col(LIME, 0)])
    c.drawPaint(skia.Paint(Shader=glow))
    a = e_out(prog(t, UI_T0, 0.3))
    text(c, "one prompt", W / 2, 640, "italic", 92, "#FFFFFF", a * 0.9)
    prompt_bar(c, t, PROMPT, TYPE_T0, TYPE_T1, cy=900, w=980, dark=True, size=54, scale=lerp(0.92, 1, e_out(a)), a=a,
               sent_t=SEND_T)


def draw(c, t, f):
    ts, f12 = step(t)
    g = {"flick": f12}
    if t < SCENE_NOS:
        # hook: the finished film, slow push-in, clay "NO CLAY" drops in
        z = Z0 * (1.0 + 0.03 * ts)
        c.save()
        c.translate(W / 2, 1150)
        c.scale(z, z)
        c.translate(-FOC[0], -FOC[1])
        world(c, t, ts, f12, built=True)
        c.restore()
        clay_title(c, [("NO", WHITE), ("CLAY.", LIME)], f12, ts, HOOK_TITLE[0], y=330, size=190, dy_line=200)
    elif t < UI_T0:
        scene_nos(c, t, ts, f12)
    elif t < BUILD_T:
        scene_prompt(c, t)
        g["clean"] = True
    else:
        # build, then camera push to the robot for the detail lines, then pull back for the title
        zin = e_out(prog(t, THUMB_T - 0.1, 0.8)) * (1 - e_out(prog(t, GROW_T0 + 0.3, 0.9)))
        z = Z0 * (1 + 0.42 * zin)
        fx, fy = lerp(FOC[0], 500, zin), lerp(FOC[1], 1200, zin)
        c.save()
        c.translate(W / 2, 1150)
        c.scale(z, z)
        c.translate(-fx, -fy)
        world(c, t, ts, f12, built=False)
        c.restore()
        if t >= TITLE_T:
            clay_title(c, [("VIBE", WHITE), ("EDITING", LIME)], f12, ts, TITLE_T, y=330, size=170)
        # flash on the build start
        fl = math.exp(-max(0, t - BUILD_T) * 8)
        if fl > 0.02:
            c.drawRect(skia.Rect.MakeWH(W, H), fill(WHITE, 0.6 * fl))
    if t >= END_T:
        endcard(c, t, END_T)
        g["clean"] = True
    CAP.draw(c, t)
    return g


CAP = Captions(S.words(), y=1610, size=84)

_V = None


def post(arr, g, f):
    global _V
    if g.get("clean"):
        return arr
    if _V is None:
        hh, ww = arr.shape[:2]
        yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
        r = np.sqrt(((xx - ww / 2) / (ww / 2)) ** 2 + ((yy - hh / 2) / (hh / 2)) ** 2)
        _V = (1 - 0.3 * np.clip(r - 0.55, 0, None) ** 1.6)[..., None].astype(np.float32)
    rng = np.random.default_rng(g.get("flick", 0) * 31 + 7)
    a = arr.astype(np.float32) * _V[: arr.shape[0], : arr.shape[1]] * (1 + 0.016 * rng.standard_normal())
    a += rng.standard_normal(arr.shape[:2]).astype(np.float32)[..., None] * 3.0
    return np.clip(a, 0, 255).astype(np.uint8)


def warm():
    C.texture()


film = Film(draw, DUR, FPS, post=post, out_dir=HERE / "out", warm=warm)


# ---------------------------------------------------------------- sound
def sound():
    import audio_kit as ak
    from sound import Mix
    ak.RNG = np.random.default_rng(3)
    m = Mix(DUR)
    m.voice(S.placements())
    bed = ak.music_bed("playful", seconds=DUR + 1, bpm=110, key="F", intro_bars=1, seed=5)
    m.music(bed, gain_db=-15, duck_db=-8, fade_out=1.5)

    def squish(pitch=1.0):
        n = int(0.22 * ak.SR)
        x = ak.filt(ak.noise(0.22), "lp", 900 * pitch) * ak.env_ad(n, 0.004, 0.16, 4)
        x += 0.6 * ak.sweep_sine(260 * pitch, 90 * pitch, 0.22, 4) * ak.env_ad(n, 0.002, 0.12, 4)
        return ak.norm(x, 0.8)

    def drip(p=1.0):
        n = int(0.12 * ak.SR)
        return ak.norm(ak.sweep_sine(500 * p, 1500 * p, 0.12, 3) * ak.env_ad(n, 0.002, 0.07, 4), 0.6)

    for i, w in enumerate(HOOK_TITLE):
        m.sfx(squish(0.9 + 0.2 * i), w, -6)
    for tp, (tx, _) in zip(NO_POPS, NO_ICONS):
        m.sfx("pop", tp, -9)
        m.sfx(squish(0.8), tx + 0.12, -5)
        m.sfx(squish(1.1), tx + 0.24, -7)
    m.sfx("whoosh", UI_T0 - 0.2, -12)
    m.sfx("typing", TYPE_T0, -12, dur=TYPE_T1 - TYPE_T0, cps=24)
    m.sfx("click", SEND_T, -4)
    m.sfx("riser", SEND_T - 0.4, -16, dur=0.8)
    m.sfx("impact", SLAB_T + 0.25, -12)
    m.sfx(squish(0.7), HILLS_T + 0.3, -6)
    m.sfx(squish(0.9), POT_T + 0.28, -4)
    for k in range(2):
        m.sfx(squish(1.2), ROBOT_T + 0.15 + 0.3 * k, -6)
    m.sfx(squish(1.3), WOBBLE_T, -8)
    for k in range(10):
        m.sfx(drip(0.9 + 0.3 * ((k * 7) % 3)), WATER_T0 + 0.5 + k * 0.22, -16)
    m.sfx("sparkle", BLOOM_T, -8)
    m.sfx("pop", BLOOM_T + 0.05, -8)
    for k in range(11):
        m.sfx(squish(1.0 + 0.04 * k), TITLE_T + 0.06 * k, -12)
    m.sfx("whoosh", END_T - 0.25, -10)
    m.sfx("ding", END_T + 0.1, -12)
    m.finish(HERE / "out" / "picture.mp4", HERE / "out" / "01_claymation_no_clay.mp4", HERE / "work")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    print(f"duration {DUR:.2f}s")
    if cmd == "sheet":
        film.sheet()
    elif cmd == "stills":
        film.stills([float(x) for x in sys.argv[2:]])
    elif cmd == "draft":
        film.render(draft=True)
    elif cmd == "render":
        film.render()
    elif cmd == "sound":
        sound()
    elif cmd == "all":
        film.render()
        sound()
