"""The seven shots. Each scene draws one exposure at (stepped) time t and returns a grade dict for post."""

import math

import numpy as np
import skia

import sets
from chars import hen, sheep, sparkle
from lib import (W, H, back_out, blob, bounce_land, clamp, clay, clay_stroke, ease_in, ease_io, ease_out,
                 heart_path, lerp, paint, prog, squash_at, star_path, font, mix)
from sets import (BOARD, CLIPS, board_track_rect, bubble, clay_text, clip_block, clock, cloud_path, crate,
                  farm_back, farm_field, film_strip, hay_bale, kernel, laptop_back, mug, music_note, paper_ball,
                  popcorn_bucket, projector_screen, signpost, stone_wall, timeline_board, window_sky)
from timeline import *

TITLE_COLS = ["#F2C84B", "#E8573E", "#5BB0E8", "#7BC96F"]


def beat_phase(t):
    return (t / BEAT) % 1.0


def on_beat(t, width=0.18):
    """1 right on a beat, decaying to 0 within `width` of a beat."""
    return clamp(1 - beat_phase(t) / width)


# ================================================================ shared bits
def clouds(c, t, f, warm=0.0):
    col_ = mix("#FFFFFF", "#FFD2C2", warm)
    for i, (x, y, s) in enumerate([(300, 135, 0.85), (1470, 120, 0.62), (1830, 330, 0.5), (720, 80, 0.45)]):
        bob = 6 * math.sin(t * 1.6 + i * 1.7)
        sway = 4 * math.sin(t * 1.1 + i)
        cx, cy = x + sway, y + bob
        c.drawLine(cx, 0, cx, cy - 50 * s, paint("#ffffff", 0.45, stroke=1.6))   # the fishing line
        clay(c, cloud_path(cx, cy, s, 300 + i * 10, f, 0.5), col_, 300 + i * 10, gloss=0.15, cast_alpha=0.18,
             cast_off=(14, 18), cast_blur=14)


def popup_sheep(c, t, x, t_pop, f, **pose):
    """Woolly popping up from behind the stone wall."""
    u = prog(t, t_pop, t_pop + 0.33)
    if u <= 0:
        return None
    y = 1000 + 420 * (1 - back_out(u, 2.2))
    sq = squash_at(t, t_pop + 0.2, 0.4, 0.12)
    sheep(c, x, y, 1.0, f, seed=1, squash=sq, ground_shadow=False, legs=False, **pose)
    return x, y


def baa_bubble(c, t, t0, x, y, f, text="BAA!", tail=(70, 60), dur=0.75, w=250, h=140, heart=False):
    u = prog(t, t0, t0 + 0.17)
    if u <= 0 or t > t0 + dur:
        return
    s = back_out(u, 2.5)
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    bubble(c, 0, 0, w, h, tail, 230, f)
    if heart:
        hp = heart_path(0, 0, 38 + 4 * on_beat(t))
        clay(c, hp, "#E8573E", 231, cast_alpha=0.2, gloss=0.4)
    else:
        clay_text(c, text, 0, 22, 62, "#3A2414", seed=232, depth=4)
    c.restore()


# ================================================================ 1. TITLE
def s_title(c, t, f):
    farm_back(c, 0.0)
    clouds(c, t, f)
    farm_field(c, 0.0)
    look = (0, 0)
    if t < POPUP1 + 0.6:
        look = (-0.9, -0.6)
    elif t < BAA1 + 0.3:
        look = (0.8, -0.7)
    pos = popup_sheep(c, t, 1240, POPUP1, f, look=look, mouth="o" if BAA1 <= t < BAA1 + 0.5 else "smile",
                      lid=0.0, boil=0.6)
    stone_wall(c, 905)
    baa_bubble(c, t, BAA1, 1500, 500, f, tail=(-110, 60))
    _title_drop(c, t, "VIBE", 300, 210, LAND_VIBE, 0)
    _title_drop(c, t, "EDITING", 500, 165, LAND_EDITING, 4)
    return {"iris": (960, 540, 1300 * ease_out(prog(t, 0.0, 0.55)) + 1)}


def _title_drop(c, t, text, y, size, lands, ci):
    from lib import clay_letter
    gl = sets.glyph_paths(text, "Unbounded-Black.ttf", size, 8, ci, lump=size / 110)
    for i, (p, xc) in enumerate(gl):
        tl = lands[i]
        D = 0.6
        u = prog(t, tl - 0.55 * D, tl + 0.45 * D)
        if u <= 0:
            continue
        dy = -(1 - bounce_land(u)) * (y + 260)
        sx, sy = squash_at(t, tl, 0.4, 0.3) if t >= tl else (0.9, 1.15)
        c.save()
        c.translate(960 + xc, y + dy)
        c.scale(sx, sy)
        c.translate(-xc, 0)
        clay_letter(c, p, TITLE_COLS[(i + ci) % 4], i + ci * 10, 12)
        c.restore()


# ================================================================ 2–4. BARN
SHEEP_X, SHEEP_Y, SHEEP_S = 860, 772, 1.15
_rng = np.random.default_rng(7)
MESSY = []
for _i, (_tr, _s0, _ln, _c) in enumerate(CLIPS):
    _x, _y, _w, _h = board_track_rect(_tr, _s0, _ln)
    MESSY.append((_x + _w / 2 + _rng.uniform(-110, 110), _y + _h + _rng.uniform(-55, 50), _rng.uniform(-28, 28)))
MESSY[3] = (330, 1012, -9)
MESSY[8] = (1330, 1045, -14)
FALL_FROM = MESSY[5]
FALL_TO = (1190, 1050, 98)

STRIP_R = [(990, 640), (1050, 596), (1102, 628), (1076, 668), (1140, 690), (1176, 760), (1186, 860), (1228, 958),
           (1300, 1000), (1385, 978), (1350, 1045), (1262, 1028), (1320, 985), (1430, 1028), (1500, 1062)]
STRIP_L = [(735, 645), (668, 606), (615, 640), (650, 676), (575, 700), (540, 790), (512, 890), (470, 985),
           (398, 1040), (318, 1002), (372, 960), (300, 1058), (220, 1030)]


def _partial(pts, r):
    if r <= 0:
        return []
    k = r * (len(pts) - 1)
    i = int(k)
    out = pts[:i + 1]
    if i < len(pts) - 1:
        a, b = pts[i], pts[i + 1]
        u = k - i
        out = out + [(a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)]
    return out


def _block_pose(i, t):
    """Bottom-centre x, y, rotation, squash for clip i at time t."""
    tr, s0, ln, colr = CLIPS[i]
    x, y, w, h = board_track_rect(tr, s0, ln)
    neat = (x + w / 2, y + h, 0.0)
    mess = MESSY[i]
    if i == 5:
        u = prog(t, BLOCK_FALL, BLOCK_LAND)
        if u > 0:
            mess = (lerp(FALL_FROM[0], FALL_TO[0], u), lerp(FALL_FROM[1], FALL_TO[1], ease_in(u)),
                    lerp(FALL_FROM[2], FALL_TO[2], u))
    th = HOP_T0 + i * HOP_DT
    u = prog(t, th, th + HOP_LEN)
    if u <= 0:
        return mess + ((1, 1),), w, h, colr, tr == 2
    arc = 300 if mess[1] > 900 else 150
    bx = lerp(mess[0], neat[0], ease_io(u))
    by = lerp(mess[1], neat[1], u) - arc * math.sin(math.pi * u)
    rot = lerp(mess[2], neat[2] + (360 if i % 3 == 0 else 0), ease_out(u))
    sq = squash_at(t, th + HOP_LEN, 0.35, 0.28) if u >= 1 else (0.92, 1.1)
    return (bx, by, rot % 360 if u >= 1 else rot, sq), w, h, colr, tr == 2


def _blocks(c, t, f, playhead_x=None):
    for i in range(len(CLIPS)):
        (bx, by, rot, sq), w, h, colr, aud = _block_pose(i, t)
        if playhead_x is not None and bx - w / 2 < playhead_x < bx + w / 2:
            sq = (1.05, 0.93)
        clip_block(c, bx - w / 2, by - h, w, h, colr, 400 + i * 7, rot, sq, f, aud)


def _barn_back(c, t, f, tod, clock_speed):
    window_sky(c, tod)
    sets.barn_wall(c)
    am = t * clock_speed
    clock(c, 640, 190, 62, am, am / 12 + 1.2, f)
    timeline_board(c)


def _hen(c, t, f, sleeping):
    hay_bale(c, 1480, 845, 290, 128)
    if sleeping:
        hen(c, 1640, 862, 1.0, f, sleep=1.0, bob=2 * math.sin(t * 2.5), face=-1)
        for k in range(3):   # zzz
            u = ((t * 0.6 + k / 3) % 1.0)
            clay_text(c, "z", 1600 - 40 * u - k * 8, 730 - 120 * u, 26 + 18 * u, "#F4EFE3", seed=600 + k, depth=3)
    else:
        woke = prog(t, HEN_WAKE, HEN_WAKE + 0.4)
        flap = math.sin(woke * math.pi * 3) ** 2 if woke < 1 else 0
        peck = on_beat(t, 0.3) if t > HEN_WAKE + 1 else 0
        hen(c, 1640, 862, 1.0, f, sleep=0.0 if woke > 0 else 1.0, flap=flap, peck=peck, bob=10 * peck, face=-1)


def s_grind(c, t, f):
    tod = clamp((t - 4.0) / 7.5) * 2.2
    _barn_back(c, t, f, tod, 6.0)
    _blocks(c, t, f)
    _hen(c, t, f, True)

    # Woolly's pose through the grind
    typing = True
    frizz = 0.2 + 1.1 * prog(t, 4.0, 11.0)
    lid, mouth, look, brows, lean, sweat = 0.4, "frown", (0.0, 0.35), 6, 0.0, 0.0
    if t < 5.0:
        look = (0.9, -0.6)
    elif 5.5 <= t < 6.6:
        sweat = prog(t, 5.5, 6.6)
    elif 6.6 <= t < 7.2:
        lid, mouth, lean = 0.62, "wavy", -3
    if CRUMPLE <= t < TOSS + 0.1:
        typing = False
    if TOSS <= t < TOSS_LAND + 0.3:
        look = (-1.0, 0.7)
    if 8.6 <= t < 9.0:
        look = (-0.9, -0.9)
    if BLOCK_FALL <= t < BLOCK_FALL + 0.7:
        lid, mouth, look = 0.0, "o", (1.0, 0.25)
    if t >= GRUMBLE:
        brows, mouth, lean = 20, "frown", (3 if f % 2 else -3)
        lid = 0.25
    jit = (f % 2) * 2 - 1
    hands = [(-62, -82 - 9 * jit), (62, -82 + 9 * jit)] if typing else [(-120, -205), (62, -82)]
    if TOSS <= t < TOSS + 0.25:
        hands = [(-150, -250), (62, -82)]
    sheep(c, SHEEP_X, SHEEP_Y, SHEEP_S, f, look=look, lid=lid, mouth=mouth, brows=brows, lean=lean, frizz=frizz,
          sweat=sweat, hands=hands, ground_shadow=False)
    if CRUMPLE <= t < TOSS:     # ball in hoof
        paper_ball(c, SHEEP_X - 122 * SHEEP_S, SHEEP_Y - 218 * SHEEP_S, 26 + 6 * prog(t, CRUMPLE, CRUMPLE + 0.3), 601, f)
    crate(c, 560, 700, 600, 200)
    laptop_back(c, SHEEP_X, 690, 270, 135, glow=0.8, f=f)
    for i, tm in enumerate(MUGS):
        u = prog(t, tm, tm + 0.25)
        if u > 0:
            mx = [610, 680, 1050, 1115][i]
            mug(c, mx, 700, 0.85 * back_out(u), ["#E86F68", "#5BB0E8", "#F2C84B", "#7BC96F"][i], 190 + i, 1.0, f)
    r = 0.3 + 0.7 * prog(t, 4.0, 11.0)
    film_strip(c, _partial(STRIP_R, r), 30, 210)
    film_strip(c, _partial(STRIP_L, r * 0.95), 30, 211)
    paper_ball(c, 440, 1012, 30, 602, f)
    paper_ball(c, 1255, 1048, 26, 603, f)
    if t >= TOSS:
        u = prog(t, TOSS, TOSS_LAND)
        x0, y0 = SHEEP_X - 150 * SHEEP_S, SHEEP_Y - 268 * SHEEP_S
        bx, by = lerp(x0, 270, u), lerp(y0, 1000, u) - 260 * math.sin(math.pi * u)
        paper_ball(c, bx, by, 32, 601, f)
    if t >= GRUMBLE:
        _grumble(c, t, f)
    night = prog(t, 6.0, 11.5)
    return {"cool": 0.55 * night, "dim": 0.22 * night}


def _grumble(c, t, f):
    u = back_out(prog(t, GRUMBLE, GRUMBLE + 0.17), 2.5)
    c.save()
    c.translate(560, 380)
    c.scale(u, u)
    bubble(c, 0, 0, 300, 170, (150, 70), 240, f)
    rng = np.random.default_rng(f)
    pts = [(-90 + i * 14, -38 + rng.uniform(-18, 18)) for i in range(14)]
    clay_stroke(c, pts, 6, "#E8573E", f, cast=False, tex=0.2)
    clay_text(c, "#@!", 0, 45, 60, "#3A2414", seed=241, depth=4)
    c.restore()


# ---------------------------------------------------------------- 3a. IDEA (close-up)
def s_idea(c, t, f):
    sets.DIRECT = True
    c.save()
    k = 1.8
    c.translate(960, 640)
    c.scale(k, k)
    c.translate(-SHEEP_X, -470)
    sets.blurred_layer(c, 3.5)
    _barn_back(c, t, f, 2.2, 1.0)
    _blocks(c, t, f)
    c.restore()
    woke = t >= WAKE
    lid = 0.0 if woke else 0.78
    look = (0, -1.0) if WAKE <= t < DING + 0.4 else (0, 0)
    mouth = "o" if WAKE <= t < DING + 0.25 else ("grin" if woke else "frown")
    brows = -14 if woke else 10
    hands = [(-62, -90), (62, -90)]
    if t > 13.4:
        j = 1 if f % 2 else -1
        hands = [(-24 + 5 * j, -232 + 6 * j), (24 + 5 * j, -232 - 6 * j)]
        brows = -12 + 6 * (f % 2)
    if not woke:
        lean = 6 * prog(t, 12.0, WAKE)
    else:
        lean = 0
    sheep(c, SHEEP_X, SHEEP_Y, SHEEP_S, f, look=look, lid=lid, mouth=mouth, brows=brows, lean=-lean, head_tilt=lean,
          frizz=1.0 if not woke else 0.6, hands=hands, ground_shadow=False)
    if t >= DING:
        u = prog(t, DING, DING + 0.2)
        on = 1.0 if (t > DING + 0.25 or f % 2 == 0) else 0.2
        sets.bulb(c, SHEEP_X, 235, 0.8 * back_out(u, 2.6), on, f)
    crate(c, 560, 700, 600, 200)
    laptop_back(c, SHEEP_X, 690, 270, 135, glow=0.8, f=f)
    c.restore()
    sets.DIRECT = False
    return {"cool": 0.45 * (1 - prog(t, DING, DING + 0.4)), "dim": 0.15, "warm": 0.35 * prog(t, DING, DING + 0.3)}


# ---------------------------------------------------------------- 3b. PROMPT (over the shoulder)
KEY_ROWS = 4


def _key_rect(row, col_, ncol):
    x0, y0 = 300, 845
    kw, kh, gap = 96, 70, 14
    off = row * 28
    return x0 + off + col_ * (kw + gap), y0 + row * (kh + gap), kw, kh


def s_prompt(c, t, f):
    sets.DIRECT = True
    c.save()
    c.translate(960, 400)
    c.scale(1.6, 1.6)
    c.translate(-1000, -300)
    sets.blurred_layer(c, 7)
    window_sky(c, 2.2)
    sets.barn_wall(c)
    timeline_board(c)
    c.restore()
    c.restore()
    sets.DIRECT = False

    # keyboard deck
    n_typed = int(clamp((t - TYPE_T0) / TYPE_DT + 1, 0, len(PROMPT))) if t >= TYPE_T0 else 0
    deck = sets.lumpy_rrect(200, 800, 1520, 420, 40, 700, 2)
    clay(c, deck, "#8E969F", 700, gloss=0.2)
    pressed = None
    if TYPE_T0 <= t < TYPE_T0 + len(PROMPT) * TYPE_DT:
        pressed = (ord(PROMPT[min(n_typed - 1, len(PROMPT) - 1)]) % 3, (n_typed * 7 + 3) % 10)
    for row in range(KEY_ROWS):
        for cc in range(10 if row < 3 else 9):
            x, y, w, h = _key_rect(row, cc, 12)
            if row == 3 and cc == 2:
                w = w * 5 + 4 * 14   # space bar
            if row == 3 and cc > 2 and cc < 7:
                continue
            down = pressed == (row, cc)
            p = sets.lumpy_rrect(x, y + (6 if down else 0), w, h, 14, 710 + row * 20 + cc, 1.0)
            clay(c, p, "#EEEAE0" if not down else "#D8D2C4", 710 + row * 20 + cc, gloss=0.25, cast_alpha=0.3 if not down else 0.15,
                 cast_off=(4, 6) if not down else (2, 2), cast_blur=4)
    # big ENTER key
    ent_down = ENTER <= t < ENTER + 0.3
    ex, ey = 1470, 845 + 84
    ep = sets.lumpy_rrect(ex, ey + (12 if ent_down else 0), 190, 150, 26, 790, 1.5)
    clay(c, ep, "#E8573E", 790, gloss=0.35, cast_alpha=0.35)
    clay_text(c, "ENTER", ex + 95, ey + 92 + (12 if ent_down else 0), 34, "#FFF4E0", seed=791, depth=3)

    # screen
    bez = sets.lumpy_rrect(330, 40, 1260, 740, 40, 720, 2.5)
    clay(c, bez, "#3F444C", 720, gloss=0.25, cast_alpha=0.45)
    sx, sy, sw, sh = 375, 85, 1170, 650
    scr = skia.Path()
    scr.addRoundRect(skia.Rect.MakeXYWH(sx, sy, sw, sh), 18, 18)
    flash = clamp(1 - (t - ENTER) / 0.35) if t >= ENTER else 0.0
    c.save()
    c.clipPath(scr, skia.ClipOp.kIntersect, True)
    grad = skia.GradientShader.MakeLinear([skia.Point(0, sy), skia.Point(0, sy + sh)],
                                          [sets.col("#FBF6EC"), sets.col("#EFE6D4")])
    c.drawPaint(skia.Paint(Shader=grad))
    for i, cc in enumerate(("#E8573E", "#F2C84B", "#7BC96F")):
        c.drawCircle(sx + 34 + i * 30, sy + 30, 9, paint(cc))
    c.drawRect(skia.Rect.MakeXYWH(sx, sy + 58, sw, 3), paint("#D8CDB8"))
    fb = font("Montserrat-Black.ttf", 66)
    title = "what's the vibe?"
    c.drawString(title, sx + sw / 2 - fb.measureText(title) / 2, sy + 210, fb, paint("#3A2414"))
    # prompt box
    bx, by, bw, bh = sx + 90, sy + 300, sw - 180, 140
    box = sets.lumpy_rrect(bx, by, bw, bh, 34, 730, 1.0)
    c.drawPath(box, paint("#000000", 0.12, blur=10))
    c.drawPath(box, paint("#FFFFFF"))
    c.drawPath(box, paint("#E8573E" if n_typed else "#CFC4AE", 1, stroke=5))
    ft = font("Montserrat-Black.ttf", 64)
    typed = PROMPT[:n_typed]
    tx = bx + 50
    if not typed:
        c.drawString("describe it...", tx, by + 92, ft, paint("#BDB3A1"))
    else:
        c.drawString(typed, tx, by + 92, ft, paint("#2A1C12"))
    cur_x = tx + ft.measureText(typed) + 8
    if t < SPARKLE_T and (int(t * 4) % 2 == 0 or TYPE_T0 <= t):
        c.drawRect(skia.Rect.MakeXYWH(cur_x, by + 34, 7, 72), paint("#E8573E"))
    # send button
    sb = (bx + bw - 75, by + bh / 2)
    c.drawCircle(*sb, 46 + (6 if ent_down else 0), paint("#E8573E"))
    arr = skia.Path()
    arr.moveTo(sb[0] - 16, sb[1] - 20)
    arr.lineTo(sb[0] + 22, sb[1])
    arr.lineTo(sb[0] - 16, sb[1] + 20)
    arr.close()
    c.drawPath(arr, paint("#FFFFFF"))
    if flash > 0:
        c.drawPaint(paint("#FFFBEA", flash))
    c.restore()
    c.drawPath(scr, paint("#ffffff", 0.08, stroke=6))
    # the sparkle emoji is a clay star that pops off the screen
    if t >= SPARKLE_T:
        u = back_out(prog(t, SPARKLE_T, SPARKLE_T + 0.2), 2.6)
        sparkle(c, cur_x + 40, by + 70, 44 * u, 0.15 * math.sin(t * 9))
        sparkle(c, cur_x + 90, by + 30, 22 * u, -0.2)
    if t >= ENTER:
        u = prog(t, ENTER, 18.0)
        rng = np.random.default_rng(31)
        for i in range(14):
            a = rng.uniform(0, 2 * math.pi)
            d = 80 + 700 * ease_out(u) * rng.uniform(0.6, 1.0)
            sparkle(c, 960 + d * math.cos(a), 420 + d * math.sin(a) * 0.7, rng.uniform(16, 34) * (1 - u * 0.5),
                    a, ["#FFE27A", "#FFFFFF", "#F7A8C4"][i % 3])

    # hooves: whichever hoof is nearer the key does the pressing
    lh, rh = (600, 905), (1300, 905)
    if pressed and t < ENTER - 0.4:
        kx, ky, kw, kh = _key_rect(*pressed, 10)
        if kx + kw / 2 < 880:
            lh = (kx + kw / 2, ky + 18)
        else:
            rh = (kx + kw / 2, ky + 18)
    elif t >= ENTER - 0.4:
        wind = prog(t, ENTER - 0.4, ENTER)
        rh = (lerp(1300, ex + 95, ease_in(wind)), lerp(905, ey + 40, ease_in(wind)) - 160 * math.sin(math.pi * wind))
        if t >= ENTER:
            rh = (ex + 95, ey + 52)
    for i, (hx, hy) in enumerate((lh, rh)):
        sx0 = 560 if i == 0 else 1360
        sets.clay_stroke(c, [(sx0, 1180), ((sx0 + hx) / 2, (1180 + hy) / 2 + 20), (hx, hy + 40)], 58, "#3A2E29",
                         800 + i, tex=0.3)
        clay(c, blob(hx, hy + 30, 38, 30, 810 + i, 0.06), "#1E1612", 810 + i, gloss=0.3)
    # over-the-shoulder wool + ear, out of focus
    sets.blurred_layer(c, 14)
    clay(c, blob(70, 1090, 300, 230, 820, 0.06), "#F4EFE3", 820, cast=False, gloss=0.1)
    clay(c, blob(150, 820, 120, 48, 821, 0.05, rot=-0.6), "#E7BF93", 821, cast=False)
    c.restore()
    return {"cool": 0.35 * (1 - flash), "dim": 0.1, "flash": flash * 0.5}


# ---------------------------------------------------------------- 4. MAGIC
def s_magic(c, t, f):
    tod = 2.2 + 0.8 * prog(t, MAGIC, 19.6)
    _barn_back(c, t, f, tod, 0.4)
    ph = None
    if t >= PLAYHEAD[0]:
        u = ((t - PLAYHEAD[0]) / (PLAYHEAD[1] - PLAYHEAD[0])) % 1.0
        x, y, w, h = BOARD
        ph = x + 40 + (w - 80) * u
    _blocks(c, t, f, ph)
    if ph is not None:
        x, y, w, h = BOARD
        clay_stroke(c, [(ph, y + 70), (ph, y + h - 20)], 8, "#E8573E", 650, tex=0.2)
        clay(c, star_path(ph, y + 62, 18, 0.6, 3, math.pi), "#E8573E", 651)
    _hen(c, t, f, False)

    # Woolly
    surprise = MAGIC <= t < MAGIC + 0.8
    frizz = 1.2 * (1 - prog(t, MAGIC + 0.3, 19.2))
    dance = t >= DANCE
    look = (0, -0.2)
    if HOP_T0 <= t < HOP_T0 + 10 * HOP_DT:
        i = min(9, int((t - HOP_T0) / HOP_DT))
        (bx, by, _, _), *_ = _block_pose(i, t)
        look = (clamp((bx - SHEEP_X) / 500, -1, 1), clamp((by - 450) / 300, -1, 1))
    if BALL_HOP[0] <= t < BALL_HOP[0] + 0.5:
        look = (-1, 0.6)
    mouth = "o" if surprise else "grin" if t > 19 else "smile"
    lean, bob, hands = (-6 if surprise else 0), 0, [(-62, -86), (62, -86)]
    if dance:
        side = 1 if int(t / BEAT) % 2 else -1
        lean = 7 * side
        bob = 18 * on_beat(t, 0.35)
        up = int(t / BEAT) % 2
        hands = [(-170, -330 - 30 * up), (170, -330 - 30 * (1 - up))]
        look = (side * 0.5, -0.2)
    sheep(c, SHEEP_X, SHEEP_Y, SHEEP_S, f, look=look, lid=0.0, mouth=mouth, brows=-10 if surprise else -4,
          lean=lean, bob=bob, frizz=frizz, hands=hands, ground_shadow=False, blush=0.6 if dance else 0)
    crate(c, 560, 700, 600, 200)
    laptop_back(c, SHEEP_X, 690, 270, 135, glow=1.0, glow_col="#FFD98A", f=f)
    for i, tm in enumerate(MUG_POP):
        if t < tm:
            mx = [610, 680, 1050, 1115][i]
            mug(c, mx, 700, 0.85, ["#E86F68", "#5BB0E8", "#F2C84B", "#7BC96F"][i], 190 + i, 1.0, f)
        elif t < tm + 0.25:
            u = prog(t, tm, tm + 0.25)
            mx = [610, 680, 1050, 1115][i]
            for k in range(6):
                a = k * math.pi / 3
                c.drawCircle(mx + 50 * u * math.cos(a), 660 + 50 * u * math.sin(a), 14 * (1 - u), paint("#FFFFFF", 0.9))
    r = 1 - prog(t, *RETRACT)
    film_strip(c, _partial(STRIP_R, r), 30, 210)
    film_strip(c, _partial(STRIP_L, r * 0.95), 30, 211)
    for i, (x0, y0, r_, dx) in enumerate([(440, 1012, 30, -600), (1255, 1048, 26, 900)]):
        u = prog(t, BALL_HOP[i], BALL_HOP[i] + 0.55)
        if u < 1:
            paper_ball(c, x0 + dx * u, y0 - 330 * math.sin(math.pi * min(u * 1.3, 1)) + 200 * max(0, u * 1.3 - 1),
                       r_, 602 + i, f)
    u = prog(t, BALL_HOP[0] - 0.2, BALL_HOP[0] + 0.5)
    if u < 1:   # the tossed ball rolls away too
        paper_ball(c, 270 - 500 * ease_in(u), 1000, 32, 601, f)
    # magic burst
    if t < MAGIC + 1.0:
        u = prog(t, MAGIC, MAGIC + 1.0)
        rng = np.random.default_rng(41)
        for i in range(18):
            a = rng.uniform(0, 2 * math.pi)
            d = 60 + 900 * ease_out(u) * rng.uniform(0.5, 1.0)
            sparkle(c, SHEEP_X + d * math.cos(a), 600 + d * math.sin(a) * 0.6, rng.uniform(14, 34) * (1 - u * 0.7), a,
                    ["#FFE27A", "#FFFFFF", "#F7A8C4", "#9FD8FF"][i % 4])
    # music notes drift up from the laptop
    if t >= DANCE - 0.5:
        for k in range(8):
            t0 = DANCE - 0.5 + k * 0.45
            u = (t - t0) / 2.2
            if 0 <= u < 1:
                x = SHEEP_X + (k % 2 * 2 - 1) * (120 + 260 * u) + 25 * math.sin(u * 9)
                music_note(c, x, 600 - 470 * u, 1.0 + 0.3 * u, ["#E8573E", "#5BB0E8", "#7BC96F", "#9B8BE0"][k % 4],
                           900 + k, 0.3 * math.sin(u * 6))
    flash = clamp(1 - (t - MAGIC) / 0.4)
    return {"warm": 0.5 * prog(t, MAGIC, 19.5), "cool": 0.35 * (1 - prog(t, MAGIC, 19.0)), "flash": 0.6 * flash}


# ---------------------------------------------------------------- 5. SCREENING
SEATS = [330, 750, 1170, 1590]


def _projection(c, t, sheet):
    b = sheet.computeTightBounds()
    x, y, w, h = b.left() + 14, b.top() + 14, b.width() - 28, b.height() - 28
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(x, y, w, h))
    u = prog(t, 28.0, 34.0)
    sh = skia.GradientShader.MakeLinear([skia.Point(0, y), skia.Point(0, y + h)],
                                        [sets.col(mix("#F59E62", "#C9628A", u)), sets.col("#FFE0A6")])
    c.drawPaint(skia.Paint(Shader=sh))
    sx, sy = x + w * 0.66, y + h * (0.48 + 0.2 * u)
    c.drawCircle(sx, sy, 110, paint("#FFE9B0", 0.5, blur=30))
    c.drawCircle(sx, sy, 70, paint("#FFD25E"))
    c.drawPath(blob(x + w * 0.3, y + h + 70, w * 0.55, 210, 61, 0.02), paint("#C86A4E"))
    c.drawPath(blob(x + w * 0.85, y + h + 110, w * 0.5, 230, 62, 0.02), paint("#A9524A"))
    hx, hy = x + w * 0.24, y + h * 0.62     # cottage
    c.drawRect(skia.Rect.MakeXYWH(hx - 50, hy - 60, 100, 70), paint("#6E3B34"))
    roof = skia.Path()
    roof.moveTo(hx - 65, hy - 58)
    roof.lineTo(hx, hy - 115)
    roof.lineTo(hx + 65, hy - 58)
    c.drawPath(roof, paint("#4A2826"))
    c.drawRect(skia.Rect.MakeXYWH(hx - 14, hy - 40, 26, 24), paint("#FFD25E"))
    c.drawRect(skia.Rect.MakeXYWH(hx + 22, hy - 120, 18, 40), paint("#4A2826"))
    for k in range(4):
        v = ((t * 0.5 + k / 4) % 1.0)
        c.drawCircle(hx + 31 + 30 * v + 8 * math.sin(v * 7), hy - 130 - 150 * v, 10 + 22 * v, paint("#FFF4E0", 0.75 * (1 - v)))
    for k in range(3):    # tiny sheep silhouettes grazing
        gx, gy = x + w * (0.5 + 0.08 * k), y + h * 0.78 - 10 * k
        c.drawOval(skia.Rect.MakeXYWH(gx - 26, gy - 18, 52, 34), paint("#FFF1DE"))
        c.drawOval(skia.Rect.MakeXYWH(gx + 18, gy - 22, 18, 22), paint("#5A3028"))
    for k in range(5):
        v = ((t * 0.35 + k / 5) % 1.0)
        hp = heart_path(x + w * (0.12 + 0.18 * k), y + h * (0.9 - 0.7 * v), 14)
        c.drawPath(hp, paint("#FF8FA3", 0.8 * math.sin(math.pi * v)))
    c.drawRect(skia.Rect.MakeXYWH(x + 30, y + h - 26, w - 60, 8), paint("#000000", 0.25))
    c.drawRect(skia.Rect.MakeXYWH(x + 30, y + h - 26, (w - 60) * u, 8), paint("#FFFFFF", 0.85))
    c.restore()


def s_screening(c, t, f):
    window_sky(c, 2.0)
    sets.barn_wall(c)
    sheet = projector_screen(c, 370, 110, 1180, 560)
    _projection(c, t, sheet)
    # lights down: darken everything except the projected sheet
    dark = skia.Path()
    dark.addRect(skia.Rect(0, 0, W, H))
    dark.addPath(sheet)
    dark.setFillType(skia.PathFillType.kEvenOdd)
    c.drawPath(dark, paint("#0E0A14", 0.5))
    # projector beam
    beam = skia.Path()
    beam.moveTo(930, 1100)
    beam.lineTo(370, 120)
    beam.lineTo(1550, 120)
    beam.lineTo(990, 1100)
    beam.close()
    sh = skia.GradientShader.MakeLinear([skia.Point(0, 1100), skia.Point(0, 120)],
                                        [sets.col("#FFF3D6", 0.25), sets.col("#FFF3D6", 0.04)])
    c.drawPath(beam, skia.Paint(Shader=sh, AntiAlias=True))
    rng = np.random.default_rng(f // 2)
    for _ in range(26):   # dust in the beam
        v = rng.uniform(0, 1)
        x = lerp(960, lerp(380, 1540, rng.uniform()), v)
        c.drawCircle(x, lerp(1080, 130, v), rng.uniform(1, 2.6), paint("#FFF8E0", 0.6))

    for i, sx in enumerate(SEATS):
        hay_bale(c, sx - 175, 880, 350, 150, 180 + i)
    popcorn_bucket(c, 960, 905, 0.9)
    for k, tp in enumerate(POPS):
        u = prog(t, tp, tp + 0.55)
        if 0 < u < 1:
            kx = 960 + (k % 2 * 2 - 1) * (40 + 120 * u)
            kernel(c, kx, 780 - 240 * math.sin(math.pi * u) + 200 * u * u, 14, 950 + k)
    for i, sx in enumerate(SEATS):
        bob = 10 * on_beat(t + i * 0.25, 0.4)
        lean = 3 * math.sin(t * math.pi + i)
        if i == 1 and t >= TURN:
            u = prog(t, TURN, TURN + 0.17)
            wink = 1.0 if WINK1 <= t < WINK1 + 0.5 else 0.0
            sheep(c, sx, 935, 0.88, f, seed=1, look=(0.2, 0.1), wink=wink, mouth="grin", blush=0.8,
                  squash=(1.08, 0.92) if u < 1 else (1, 1), legs=False, ground_shadow=False,
                  hands=[(-150, -170), (165, -350 - 20 * on_beat(t, 0.3))], brows=-8)
            if WINK1 <= t < WINK1 + 0.5:
                sparkle(c, sx - 60, 935 - 0.88 * 330, 30, t * 3)
        else:
            sheep(c, sx, 935, 0.88, f, seed=1 + i * 11, back=True, bob=bob, lean=lean, legs=False, ground_shadow=False)
    if t >= FLOCK_AWW:
        for k in range(10):
            t0 = FLOCK_AWW + k * 0.16
            u = (t - t0) / 1.4
            if 0 <= u < 1:
                hx = SEATS[k % 4] + 40 * math.sin(u * 8 + k)
                s = 26 * back_out(min(1, u * 4))
                clay(c, heart_path(hx, 560 - 380 * u, s), "#E8573E", 970 + k, gloss=0.4, cast_alpha=0.2)
    return {"warm": 0.25, "dim": 0.1}


# ---------------------------------------------------------------- 6. END CARD
def s_endcard(c, t, f):
    farm_back(c, 1.0)
    clouds(c, t, f, 1.0)
    farm_field(c, 1.0)
    if t >= SIGN:
        u = prog(t, SIGN, SIGN + 0.45)
        dy = -(1 - bounce_land(u)) * 700
        swing = 6 * math.exp(-4 * max(0, t - SIGN - 0.25)) * math.sin((t - SIGN) * 14)
        c.save()
        c.translate(0, dy)
        signpost(c, 400, 880, [("BY", 30, 52, "Montserrat-Black.ttf"), ("IDEABRO STUDIO", 38, 108, "Montserrat-Black.ttf")],
                 swing=swing)
        c.restore()
    wink = 1.0 if WINK2 <= t < WINK2 + 0.45 else 0.0
    pos = popup_sheep(c, t, 1240, POPUP2, f, look=(0, 0) if t > POPUP2 + 0.5 else (-0.8, -0.8), wink=wink,
                      mouth="o" if BAA2 <= t < BAA2 + 0.45 else "grin", blush=0.7)
    stone_wall(c, 905, 1.0)
    if WINK2 <= t < WINK2 + 0.45:
        sparkle(c, 1150, 640, 34, t * 4)
    baa_bubble(c, t, BAA2, 1500, 500, f, heart=True, tail=(-110, 60), dur=1.4, w=200, h=150)
    # title: all letters slam down together, staggered
    lands = [END_DROP + 0.05 * i for i in range(12)]
    _end_title(c, t, lands)
    words = ["just", "say", "the", "vibe."]
    x = 960 - 470
    fw = font("Unbounded-Black.ttf", 66)
    for i, wd in enumerate(words):
        wdt = fw.measureText(wd)
        u = prog(t, TAG_WORDS[i], TAG_WORDS[i] + 0.2)
        if u > 0:
            s = back_out(u, 2.6)
            c.save()
            c.translate(x + wdt / 2, 420)
            c.scale(s, s)
            clay_text(c, wd, 0, 0, 66, "#FFF6E6" if i < 3 else "#FFE27A", seed=980 + i, depth=6)
            c.restore()
        x += wdt + 36
    cx, cy = (pos[0], pos[1] - 300) if pos else (960, 540)
    a, b = IRIS
    if t < a:
        r = 1500
    elif t < a + 0.35:
        r = lerp(1500, 165, ease_io(prog(t, a, a + 0.35)))
    elif t < b - 0.12:
        r = 165
    else:
        r = 165 * (1 - prog(t, b - 0.12, b))
    return {"warm": 0.3, "iris": (cx, cy, r)}


def _end_title(c, t, lands):
    from lib import clay_letter
    text = "VIBE EDITING"
    gl = sets.glyph_paths(text, "Unbounded-Black.ttf", 150, 6, 21, lump=1.4)
    for i, (p, xc) in enumerate(gl):
        tl = lands[i]
        u = prog(t, tl - 0.3, tl + 0.25)
        if u <= 0:
            continue
        dy = -(1 - bounce_land(u)) * 520
        sy, sx = squash_at(t, tl, 0.4, 0.3)
        bob = 5 * math.sin(t * 4 + i * 0.7) if t > tl + 0.5 else 0
        c.save()
        c.translate(960 + xc, 270 + dy + bob)
        c.scale(sx, sy)
        c.translate(-xc, 0)
        clay_letter(c, p, TITLE_COLS[i % 4], i + 40, 12)
        c.restore()


SCENE_FNS = {"title": s_title, "grind": s_grind, "idea": s_idea, "prompt": s_prompt, "magic": s_magic,
             "screening": s_screening, "endcard": s_endcard}


def draw(c, t, f):
    name, a, b = scene_at(t)
    c.clear(sets.col("#000000"))
    return SCENE_FNS[name](c, t, f) or {}
