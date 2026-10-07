"""Reel 03: "This looks like a fifty thousand dollar product ad. It took one prompt."
A premium, minimal ad for a concept product (Vibe Buds), every pixel drawn in code.

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
from kit import (W, H, INK, LIME, WHITE, Captions, Film, clamp, col, e_back, e_expo, e_io, e_out, endcard,  # noqa: E402
                 fill, hrand, lerp, lin_grad, measure, mixc, prog, prompt_bar, rad_grad, rrect, spring, stroke,
                 text)
from script import LINES, VOICE  # noqa: E402
from voice import Script, narrate  # noqa: E402

vo = narrate(LINES, HERE / "work", VOICE)
S = Script(vo, [("hook", 0.2), ("reveal", 0.25), ("intro", 0.9), ("battery", 0.55), ("noise", 0.5),
                ("feel", 0.5), ("nos", 1.6), ("just", 0.3), ("cta", 0.35)])
END_T = S.end("cta") + 0.45
DUR = END_T + 3.0
FPS = 30

PROMPT = "a premium, minimal product ad for wireless earbuds called Vibe Buds"
REVEAL_T = S.t("reveal") - 0.1
R_TYPE0, R_TYPE1 = S.t("reveal") + 0.05, S.end("reveal") + 0.35
AD_T = S.t("intro") - 0.45                         # the ad itself starts
INTRO_T, BATT_T, NOISE_T, FEEL_T = S.t("intro"), S.t("battery") - 0.2, S.t("noise") - 0.2, S.t("feel") - 0.2
GONE_T = S.find("noise", "disappears")
LINEUP_T = S.end("feel") + 0.35
META_T = S.t("nos") - 0.35
NO_T = [S.w("nos", 0), S.find("nos", "3D") - 0.2, S.find("nos", "AI") - 0.2]
JUST_T = S.t("just") - 0.15
J_TYPE0, J_TYPE1 = S.t("just"), S.end("just") + 0.1
BEAT = 60 / 116

BG = "#F5F5F7"
GREY = "#86868B"
FINISH = {"white": ("#FFFFFF", "#E9E9EE", "#C9C9D2", "#A9A9B5"),
          "black": ("#5A5A62", "#2B2B31", "#141418", "#07070A"),
          "lime": ("#F4FFC7", "#D9F56A", "#B5D53A", "#86A11E")}


# ---------------------------------------------------------------- product
def case_shape(w=440, h=330):
    p = skia.Path()
    p.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h), 150, 150))
    return p


def floor_shadow(c, cx, cy, w, a=1.0, lift=0.0):
    k = 1 / (1 + max(0.0, lift) * 0.004)
    c.drawOval(skia.Rect.MakeXYWH(cx - w * 0.55 * k, cy - 18 * k, w * 1.1 * k, 36 * k), fill("#000000", 0.22 * a * k,
                                                                                         blur=26))
    c.drawOval(skia.Rect.MakeXYWH(cx - w * 0.35 * k, cy - 8 * k, w * 0.7 * k, 16 * k), fill("#000000", 0.25 * a * k,
                                                                                        blur=8))


def bud(c, x, y, s, finish="white", ang=0.0, a=1.0, mirror=False):
    hi, base, mid, dk = FINISH[finish]
    c.save()
    c.translate(x, y)
    c.rotate(ang)
    c.scale(-s if mirror else s, s)
    c.drawOval(skia.Rect.MakeXYWH(-70, -60, 150, 135), fill("#000000", 0.25 * a, blur=18))
    # silicone tip
    c.drawOval(skia.Rect.MakeXYWH(40, -36, 70, 64), rad_grad(70, -12, 60, ["#B9B9C2", "#7D7D86"], a=a))
    c.drawOval(skia.Rect.MakeXYWH(78, -18, 22, 26), fill("#3A3A40", a))
    # shell
    body = skia.Rect.MakeXYWH(-80, -72, 160, 144)
    c.drawOval(body, rad_grad(-28, -38, 150, [hi, base, mid, dk], [0, 0.35, 0.75, 1], a=a))
    c.drawOval(skia.Rect.MakeXYWH(-56, -60, 70, 34), fill(WHITE, 0.55 * a, blur=10))
    # touch pad with lime ring
    c.drawCircle(-6, 4, 40, rad_grad(-16, -8, 48, [mid, base], a=a))
    c.drawCircle(-6, 4, 40, stroke(LIME, 6, a))
    for i in range(3):
        for j in range(3):
            c.drawCircle(-22 + i * 16, -12 + j * 16, 3, fill(dk, 0.6 * a))
    c.restore()


def case(c, cx, cy, s=1.0, finish="white", yaw=0.0, lid=0.0, led=0.0, buds_up=0.0, a=1.0, shadow_y=None,
         bud_finish=None):
    hi, base, mid, dk = FINISH[finish]
    w, h = 440, 330
    sx = 0.82 + 0.18 * math.cos(yaw)
    if shadow_y is not None:
        floor_shadow(c, cx, shadow_y, w * s * sx, a, lift=shadow_y - cy - h * s / 2)
    c.save()
    c.translate(cx, cy)
    c.scale(s * sx, s)
    seam = -h * 0.5 + h * 0.36
    body = case_shape(w, h)
    hx = -90 + 120 * math.sin(yaw)
    # interior + buds when open
    if lid > 0:
        lift = e_out(lid)
        # lid swung back: a tilted disc behind the opening
        lr = skia.Rect.MakeXYWH(-w * 0.47, seam - 40 - 150 * lift, w * 0.94, 150 * lift + 40)
        c.drawOval(lr, lin_grad(0, lr.top(), 0, lr.bottom(), [base, mid, dk], a=a))
        c.drawOval(lr.makeInset(16, 10 * lift + 4), fill(dk, 0.5 * a))
        cav = skia.Rect.MakeXYWH(-w * 0.4, seam - 34 * lid, w * 0.8, 68 * lid)
        c.drawOval(cav, fill("#0C0C0F", a))
        for i, side in enumerate((-1, 1)):
            up = e_back(clamp(buds_up * 1.2 - i * 0.2), 1.6)
            bud(c, side * 105, seam - 20 - (170 + 40 * (side < 0)) * up, 0.72, bud_finish or finish,
                side * 24, a, mirror=side < 0)
    # lower body
    c.save()
    c.clipRect(skia.Rect.MakeLTRB(-w, seam if lid > 0 else -h, w, h))
    c.drawPath(body, lin_grad(0, -h / 2, 0, h / 2, [hi, base, mid, dk], [0, 0.3, 0.75, 1], a=a))
    c.drawPath(body, rad_grad(hx, -60, 300, [WHITE, WHITE], a=0.0))
    c.save()
    c.clipPath(body, skia.ClipOp.kIntersect, True)
    c.drawOval(skia.Rect.MakeXYWH(hx - 130, -h / 2 + 12, 260, 90), fill(WHITE, 0.55 * a, blur=26))
    c.drawPath(body, stroke(dk, 40, 0.35 * a, blur=26))                           # edge falloff
    c.drawRect(skia.Rect.MakeXYWH(-w, h / 2 - 50, 2 * w, 60), fill(dk, 0.25 * a, blur=22))
    c.restore()
    c.restore()
    # seam
    if lid <= 0:
        c.save()
        c.clipPath(body, skia.ClipOp.kIntersect, True)
        c.drawLine(-w, seam, w, seam, stroke(dk, 3, 0.55 * a))
        c.drawLine(-w, seam + 3, w, seam + 3, stroke(WHITE, 2, 0.5 * a))
        c.restore()
    # LED
    lc = LIME if led > 0 else mid
    c.drawRRect(rrect(-14, 46, 28, 10, 5), fill(lc, a))
    if led > 0:
        c.drawRRect(rrect(-22, 40, 44, 22, 11), fill(LIME, 0.5 * led * a, blur=12))
    c.restore()


# ---------------------------------------------------------------- shots
def studio(c, top=BG, bottom="#E4E4EA"):
    c.drawPaint(lin_grad(0, 0, 0, H, [top, bottom]))


def hero(c, t, cx=W / 2, cy=980, s=1.25, dark=False):
    """floating open case, buds hovering, slow orbit + light sweep."""
    if dark:
        c.drawPaint(rad_grad(W / 2, 900, 1200, ["#26262C", "#050507"]))
    else:
        studio(c)
    yaw = 0.5 * math.sin(t * 0.7)
    fl = 14 * math.sin(t * 1.6)
    case(c, cx, cy + fl, s, "black" if dark else "white", yaw, lid=1.0, led=1, buds_up=1.0, shadow_y=cy + 330 * s,
         bud_finish="white")
    # light sweep
    sw = (t * 0.35) % 1.6 - 0.3
    c.save()
    c.rotate(-20)
    c.drawRect(skia.Rect.MakeXYWH(-600 + sw * 2400, -400, 160, 3200), fill(WHITE, 0.10, blur=40))
    c.restore()


def shot_intro(c, t):
    # black -> light up -> closed case rises
    k = e_io(prog(t, AD_T, 0.8))
    c.drawPaint(fill("#000000"))
    c.drawPaint(rad_grad(W / 2, 1050, 1300, [BG, "#D7D7DE"], a=k))
    rise = e_expo(prog(t, AD_T + 0.15, 1.1))
    yaw = lerp(-1.2, 0.0, rise)
    case(c, W / 2, lerp(1500, 1080, rise), 1.35, "white", yaw, led=prog(t, INTRO_T + 0.6, 0.3), a=1,
         shadow_y=1340)
    a1 = e_out(prog(t, INTRO_T - 0.05, 0.5))
    text(c, "Introducing", W / 2, 560 + 20 * (1 - a1), "medium", 54, GREY, a1)
    a2 = e_out(prog(t, S.find("intro", "Vibe") - 0.05, 0.6))
    c.save()
    c.translate(W / 2, 720)
    sc = lerp(1.08, 1, a2)
    c.scale(sc, sc)
    text(c, "Vibe Buds", 0, 0, "heavy", 150, INK, a2, tracking=-0.035)
    c.restore()


def shot_battery(c, t):
    studio(c)
    lt = t - BATT_T
    lid = e_io(prog(t, BATT_T + 0.1, 0.7))
    case(c, W / 2, 1290, 1.2, "white", 0.25 * math.sin(lt * 0.8), lid=lid, led=1,
         buds_up=prog(t, BATT_T + 0.5, 0.6), shadow_y=1500)
    n = int(round(40 * e_out(prog(t, S.t("battery"), 1.0))))
    a = e_out(prog(t, BATT_T, 0.4))
    text(c, f"{n}", W / 2, 590, "heavy", 300, INK, a, tracking=-0.05)
    text(c, "hours of battery", W / 2, 690, "medium", 58, GREY, a)
    # ring
    r = 120
    ring = skia.Rect.MakeXYWH(W / 2 - r, 1690 - r, 2 * r, 2 * r)
    c.drawArc(ring, 0, 360, False, stroke("#DADAE0", 14, a))
    c.drawArc(ring, -90, 360 * n / 40, False, stroke(LIME, 14, a))
    c.drawArc(ring, -90, 360 * n / 40, False, stroke("#9BBF1E", 14, 0.25 * a))


def shot_noise(c, t):
    c.drawPaint(fill("#000000"))
    calm = e_io(prog(t, GONE_T, 1.0))
    for i in range(9):
        p = skia.Path()
        for x in range(0, W + 1, 12):
            u = x / W
            amp = (1 - calm) * (90 + 50 * hrand(i, 3)) * math.sin(math.pi * u) ** 1.5
            y = 1150 + (i - 4) * 14 * (1 - calm) + amp * math.sin(x * (0.02 + 0.01 * i) + t * (6 + i)) \
                * math.sin(x * 0.004 + t * 2 + i)
            if x == 0:
                p.moveTo(x, y)
            else:
                p.lineTo(x, y)
        cc = mixc("#5A5A62", LIME, calm)
        c.drawPath(p, stroke(cc, 3 + 2 * calm, 0.55 + 0.45 * calm))
    if calm > 0:
        p = skia.Path()
        p.moveTo(0, 1150)
        p.lineTo(W, 1150)
        c.drawPath(p, stroke(LIME, 6, calm * 0.6, blur=12))
    a = e_out(prog(t, NOISE_T, 0.4))
    text(c, "Noise that simply", W / 2, 640, "heavy", 96, WHITE, a, tracking=-0.03)
    # "disappears." dissolves letter by letter
    word = "disappears."
    size = 120
    x = W / 2 - measure(word, "heavy", size) / 2
    f = None
    for i, ch in enumerate(word):
        ap = e_out(prog(t, GONE_T - 0.1, 0.3))
        gone = e_io(prog(t, GONE_T + 0.35 + i * 0.05, 0.4))
        aa = ap * (1 - gone)
        p = fill(WHITE, aa, blur=gone * 18)
        text(c, ch, x, 790 - 40 * gone, "heavy", size, paint=p, anchor="l")
        x += measure(ch, "heavy", size)


def shot_feel(c, t):
    c.drawPaint(rad_grad(W / 2, 1100, 1100, ["#1A1A1F", "#000000"]))
    beat0 = FEEL_T
    for k in range(8):
        tb = beat0 + k * BEAT
        if t < tb:
            continue
        r = 200 + (t - tb) * 900
        a = math.exp(-(t - tb) * 2.2)
        c.drawCircle(W / 2, 1100, r, stroke(LIME, 6 * a + 1, 0.8 * a))
    pulse = math.exp(-((t - beat0) % BEAT) * 10) if t > beat0 else 0
    s = lerp(2.6, 2.9, e_out(prog(t, FEEL_T, 1.4))) * (1 + 0.025 * pulse)
    bud(c, W / 2, 1100, s, "black", -12 + 6 * math.sin(t))
    a = e_out(prog(t, FEEL_T, 0.4))
    text(c, "Sound you", W / 2, 520, "heavy", 112, WHITE, a, tracking=-0.03)
    text(c, "can feel.", W / 2, 650, "heavy", 112, LIME, e_out(prog(t, S.find("feel", "feel") - 0.1, 0.4)),
         tracking=-0.03)


def shot_lineup(c, t, a=1.0):
    studio(c)
    for i, (fin, x) in enumerate((("black", 225), ("white", 540), ("lime", 855))):
        k = e_back(prog(t, LINEUP_T + 0.08 * i, 0.5), 1.5)
        y = 1080 + 260 * (1 - k) + 10 * math.sin(t * 1.4 + i)
        case(c, x, y, 0.66, fin, 0.3 * math.sin(t * 0.6 + i), led=1, shadow_y=1200, a=clamp(k * 2))
    a1 = e_out(prog(t, LINEUP_T + 0.3, 0.5))
    text(c, "Vibe Buds", W / 2, 700, "heavy", 140, INK, a1, tracking=-0.035)
    text(c, "Hear the vibe.", W / 2, 800, "italic", 76, GREY, e_out(prog(t, LINEUP_T + 0.55, 0.5)))


def ad(c, t):
    if t < BATT_T:
        shot_intro(c, t)
    elif t < NOISE_T:
        shot_battery(c, t)
    elif t < FEEL_T:
        shot_noise(c, t)
    elif t < LINEUP_T:
        shot_feel(c, t)
    else:
        shot_lineup(c, t)


def framed(c, t, k, draw_fn, cy=760, sc=0.52):
    """draw_fn's full frame shrunk into a rounded 'screen' (the reveal that it's a made video)."""
    s = lerp(1.0, sc, k)
    yc = lerp(H / 2, cy, k)
    c.save()
    c.translate(W / 2, yc)
    c.scale(s, s)
    c.translate(-W / 2, -H / 2)
    r = lerp(0, 70, k)
    if k > 0:
        c.drawRRect(rrect(-14, -14 + 30, W + 28, H + 28, r + 14), fill("#000000", 0.5 * k, blur=50))
    c.clipRRect(rrect(0, 0, W, H, r), True)
    draw_fn(c, t)
    c.restore()
    if k > 0:
        c.save()
        c.translate(W / 2, yc)
        c.scale(s, s)
        c.drawRRect(rrect(-W / 2, -H / 2, W, H, r), stroke("#3A3A42", 10, k))
        c.restore()


def draw(c, t, f):
    if t < REVEAL_T:
        hero(c, t)
        k = e_back(prog(t, S.find("hook", "fifty") - 0.1, 0.45), 1.8)
        if k > 0:
            n = int(50000 * e_out(prog(t, S.find("hook", "fifty"), 0.9)))
            text(c, f"${n:,}", W / 2, 470, "heavy", 150 * clamp(k + 0.001) ** 0.3, INK, clamp(k), tracking=-0.03)
            text(c, "product ad?", W / 2, 570, "medium", 64, GREY, e_out(prog(t, S.find("hook", "product"), 0.4)))
    elif t < AD_T:
        c.drawPaint(fill("#0F0F14"))
        k = e_io(prog(t, REVEAL_T, 0.5))

        def hero_fn(cc, tt):
            hero(cc, tt)
            n = 50000
            text(cc, f"${n:,}", W / 2, 470, "heavy", 150, INK, 1, tracking=-0.03)
            text(cc, "product ad?", W / 2, 570, "medium", 64, GREY, 1)
        framed(c, t, k, hero_fn, cy=700, sc=0.5)
        a = e_out(prog(t, REVEAL_T + 0.3, 0.3))
        prompt_bar(c, t, PROMPT, R_TYPE0, R_TYPE1, cy=1420, w=980, dark=True, size=44, a=a,
                   sent_t=R_TYPE1 + 0.15)
        # zoom back into the frame for the ad
        z = e_in(prog(t, AD_T - 0.35, 0.35)) if False else 0
        if t > R_TYPE1 + 0.2:
            k2 = e_io(prog(t, R_TYPE1 + 0.2, AD_T - R_TYPE1 - 0.2))
            c.drawRect(skia.Rect.MakeWH(W, H), fill("#000000", k2))
    elif t < META_T:
        ad(c, t)
    elif t < JUST_T:
        c.drawPaint(fill("#0F0F14"))
        k = e_io(prog(t, META_T, 0.6))
        framed(c, t, k, shot_lineup, cy=640, sc=0.46)
        items = [("Studio", NO_T[0]), ("3D software", NO_T[1]), ("AI video tool", NO_T[2])]
        for i, (s, ti) in enumerate(items):
            a = e_out(prog(t, ti, 0.3))
            y = 1260 + i * 120
            x0, wdt = text(c, "No " + s, W / 2, y, "heavy", 78, WHITE, a, tracking=-0.02)
            sk = e_io(prog(t, ti + 0.35, 0.3))
            if sk > 0:
                c.drawLine(x0 - 10, y - 26, x0 - 10 + (wdt + 20) * sk, y - 26, stroke("#FF4D5E", 9, a))
    else:
        c.drawPaint(fill("#0F0F14"))
        glow = skia.GradientShader.MakeRadial(skia.Point(W / 2, 1300), 800, [col(LIME, 0.12), col(LIME, 0)])
        c.drawPaint(skia.Paint(Shader=glow))
        framed(c, t, 1.0, shot_lineup, cy=640, sc=0.46)
        a = e_out(prog(t, JUST_T, 0.35))
        prompt_bar(c, t, PROMPT, J_TYPE0, J_TYPE1, cy=1330, w=980, dark=True, size=44, a=a, sent_t=J_TYPE1 + 0.2)
    if t >= END_T:
        endcard(c, t, END_T)
    CAP.draw(c, t)


def e_in(k):
    return clamp(k) ** 3


CAP = Captions(S.words(skip=("intro", "battery", "noise", "feel", "nos")), y=1680, size=80)
CAP.mute(R_TYPE0, AD_T)
film = Film(draw, DUR, FPS, out_dir=HERE / "out")


# ---------------------------------------------------------------- sound
def sound():
    import audio_kit as ak
    from sound import Mix
    m = Mix(DUR)
    m.voice(S.placements())
    bed = ak.music_bed("tech", seconds=DUR + 1, bpm=116, key="E", intro_bars=2, seed=4)
    m.music(bed, gain_db=-15, duck_db=-7, t=0.0)

    def thump():
        n = int(0.5 * ak.SR)
        return ak.norm(np.tanh(2 * ak.sweep_sine(90, 38, 0.5, 5) * ak.env_ad(n, 0.002, 0.4, 3)), 0.9)

    m.sfx("whoosh", 0.0, -14)
    for k in range(12):
        m.sfx("tick", S.find("hook", "fifty") + k * 0.07, -16)
    m.sfx("whoosh", REVEAL_T, -10)
    m.sfx("typing", R_TYPE0, -13, dur=R_TYPE1 - R_TYPE0, cps=30)
    m.sfx("click", R_TYPE1 + 0.15, -5)
    m.sfx("riser", AD_T - 1.2, -14, dur=1.2)
    m.sfx("impact", AD_T + 0.05, -10)
    m.sfx("sparkle", S.find("intro", "Vibe"), -12)
    m.sfx("whoosh", BATT_T - 0.1, -12)
    m.sfx("click", BATT_T + 0.15, -8)
    for k in range(14):
        m.sfx("tick", S.t("battery") + k * 0.07, -18)
    m.sfx("glitch", NOISE_T, -14)
    m.sfx("downlifter", GONE_T, -12, dur=1.0)
    for k in range(4):
        m.sfx(thump(), FEEL_T + k * BEAT, -6)
    m.sfx("whoosh", LINEUP_T - 0.1, -12)
    m.sfx("sparkle", LINEUP_T + 0.3, -12)
    m.sfx("whoosh", META_T, -12)
    for ti in NO_T:
        m.sfx("swish", ti + 0.35, -12)
    m.sfx("typing", J_TYPE0, -14, dur=J_TYPE1 - J_TYPE0, cps=30)
    m.sfx("click", J_TYPE1 + 0.2, -6)
    m.sfx("whoosh", END_T - 0.25, -10)
    m.sfx("ding", END_T + 0.1, -12)
    m.finish(HERE / "out" / "picture.mp4", HERE / "out" / "03_product_ad_one_prompt.mp4", HERE / "work")


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
