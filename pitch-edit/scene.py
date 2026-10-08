"""scene v2: premium pitch edit at 60 fps.
Design system: ink background, glass cards, white + neon type (Anton / Instrument Serif / JetBrains Mono / Inter Tight),
expo-out motion, zoom transitions between every scene, face circle top-right in the explainer scenes,
kinetic type behind the subject in the full-frame scenes.

    python3 scene.py prep                 # graded frames + face track (needs work/stab60.mp4, work/matte60.u8)
    python3 scene.py stills 1.0 5.0       # check frames -> out/stills/
    python3 scene.py audio                # voice + music + sfx -> work/mix.wav
    python3 scene.py render               # picture -> out/pitch_picture.mp4
"""

import json
import math
import sys
from pathlib import Path

import numpy as np
import skia

sys.path.insert(0, str(Path(__file__).resolve().parent / "vibe"))
from motion_kit import (Stage, clamp, ease_in_cubic, ease_in_out_cubic, ease_out_back, ease_out_cubic,  # noqa: E402
                        ease_out_expo, lerp, noise1, prog, text, text_width)

import timeline as TL  # noqa: E402

W, H, FPS = TL.W, TL.H, TL.FPS
C = TL.CUE
S = Stage(W, H, fps=FPS, duration=TL.DURATION)
SW, SH = 720, 1280

WHITE = skia.Color(255, 255, 255)
NEON = skia.Color(212, 255, 63)
INK = skia.Color(11, 11, 13)
SERIF = "InstrumentSerif-Italic.ttf"
BIG = "impact"
CAP = "InterTight-700.ttf"
SAMP = skia.SamplingOptions(skia.CubicResampler.Mitchell())


def col(c, a):
    return skia.Color(skia.ColorGetR(c), skia.ColorGetG(c), skia.ColorGetB(c), int(255 * clamp(a)))


def P(c, a=1.0):
    return skia.Paint(Color=col(c, a), AntiAlias=True)


def SP(c, w, a=1.0):
    return skia.Paint(Color=col(c, a), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=w,
                      StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join)


# ------------------------------------------------------------------ footage, matte, track, edl
EDL = json.load(open("work/edl60.json"))
WORDS = json.load(open("work/words60.json"))


def _mm(path, shape):
    return np.memmap(path, np.uint8, "r").reshape(shape) if Path(path).exists() else None


FR = _mm("work/frames60.rgb", (-1, SH, SW, 3))
NF = len(FR) if FR is not None else 1
MT = _mm("work/matte60.u8", (-1, SH, SW))
HAVE = np.load("work/matte60_have.npy") if Path("work/matte60_have.npy").exists() else None
TRK = np.array(json.load(open("work/track60.json"))) if Path("work/track60.json").exists() else None
import os
JIT_GAIN = float(os.environ.get("JIT_GAIN", "1.0"))


def seg_of(t):
    for i, e in enumerate(EDL):
        if t < e["out_e"]:
            return i, e
    return len(EDL) - 1, EDL[-1]


def src_time(t):
    t = min(t, TL.SPEECH_END)
    i, e = seg_of(t)
    return e["src_s"] + clamp(t - e["out_s"], 0, e["src_e"] - e["src_s"] - 1 / TL.SRC_FPS)


def fidx(t):
    return int(clamp(round(src_time(t) * TL.SRC_FPS), 0, NF - 1))


def face(t):
    """face centre in source px, plus the jitter offset (raw - smooth) for subject stabilisation."""
    if TRK is None:
        return 360.0, 640.0, 0.0, 0.0
    fx, fy, jx, jy = TRK[fidx(t)]
    return fx, fy, jx * JIT_GAIN, jy * JIT_GAIN


def layers(t, dim=0.0, need_person=False):
    i = fidx(t)
    rgb = FR[i]
    if not need_person or MT is None or (HAVE is not None and not HAVE[i]):
        if dim > 0.001:
            f = rgb.astype(np.float32)
            g = f.mean(-1, keepdims=True)
            f = (f * (1 - 0.45 * dim) + g * 0.45 * dim) * (1 - 0.72 * dim)
            rgb = np.clip(f, 0, 255).astype(np.uint8)
        img = skia.Image.fromarray(np.ascontiguousarray(np.dstack([rgb, np.full((SH, SW), 255, np.uint8)])),
                                   colorType=skia.kRGBA_8888_ColorType)
        return img, None
    f = rgb.astype(np.float32)
    m = MT[i].astype(np.float32)[..., None] / 255.0
    g = f.mean(-1, keepdims=True)
    bg = (f * (1 - 0.45 * dim) + g * 0.45 * dim) * (1 - 0.72 * dim)
    bgimg = skia.Image.fromarray(np.ascontiguousarray(np.dstack([np.clip(bg, 0, 255).astype(np.uint8),
                                                                  np.full((SH, SW), 255, np.uint8)])),
                                 colorType=skia.kRGBA_8888_ColorType)
    pa = np.empty((SH, SW, 4), np.uint8)
    pa[..., :3] = (f * m).astype(np.uint8)
    pa[..., 3] = (m[..., 0] * 255).astype(np.uint8)
    pimg = skia.Image.fromarray(pa, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)
    return bgimg, pimg


def place(c, t, zoom, rect=None):
    """map source pixels onto the dest rect, centred on the face, with subject stabilisation."""
    x, y, w, h = rect or (0, 0, W, H)
    fx, fy, jx, jy = face(t)
    a = w / h
    sh = min(SH, SW / a) / zoom
    sw = sh * a
    cx = lerp(SW / 2, fx, clamp((zoom - 1) * 6)) + jx
    cy = lerp(SH / 2, fy + 60, clamp((zoom - 1) * 6)) + jy
    sx = clamp(cx - sw / 2, 0, SW - sw)
    sy = clamp(cy - sh / 2, 0, SH - sh)
    k = w / sw
    c.translate(x, y)
    c.scale(k, k)
    c.translate(-sx, -sy)


def seg_zoom(t, base=1.03, alt=1.10):
    """jump-cut punch: alternate zoom per edit segment, eased so it reads as a quick push, not a jolt."""
    if os.environ.get("NO_PUNCH"):
        return base
    i, e = seg_of(min(t, TL.SPEECH_END))
    z_now = alt if i % 2 else base
    z_prev = base if i % 2 else alt
    k = ease_out_expo(prog(t, e["out_s"], 0.22)) if i > 0 else 1.0
    return lerp(z_prev, z_now, k)


def footage(c, t, zoom, dim=0.0, behind=None):
    bgimg, pimg = layers(t, dim, need_person=behind is not None)
    c.save()
    place(c, t, zoom)
    c.drawImage(bgimg, 0, 0, SAMP)
    c.restore()
    if behind:
        behind(c, t)
        if pimg is not None:
            c.save()
            place(c, t, zoom)
            c.drawImage(pimg, 0, 0, SAMP)
            c.restore()


# ------------------------------------------------------------------ type + design system
def kinetic(c, t, t0, s, cx, cy, size, color=WHITE, outline=False, per=0.03, dur=0.5, out_t=None, align="center"):
    if t < t0:
        return
    tw = text_width(s, size, BIG)
    x = cx - tw / 2 if align == "center" else cx
    k_out = ease_in_cubic(prog(t, out_t, 0.25)) if out_t is not None else 0.0
    c.save()
    c.clipRect(skia.Rect.MakeLTRB(-200, cy - size * 0.62, W + 200, cy + size * 0.62))
    for i, ch in enumerate(s):
        k = ease_out_expo(prog(t, t0 + i * per, dur))
        yy = cy + (1 - k) * size * 1.05 - k_out * size * 1.1
        if outline:
            text(c, ch, x, yy, size=size, font=BIG, fill=col(WHITE, 0), align="left", stroke=4, stroke_col=color)
        else:
            text(c, ch, x, yy, size=size, font=BIG, fill=color, align="left")
        x += text_width(ch, size, BIG)
    c.restore()


def fit(s, size, max_w=W - 120, font=BIG):
    return min(size, size * max_w / max(1.0, text_width(s, size, font)))


def fade(t, t0, d=0.45):
    return ease_out_expo(prog(t, t0, d))


def mono(c, s, x, y, size=24, color=WHITE, align="left", alpha=1.0, tracking=0.14):
    text(c, s, x, y, size=size, font="mono", fill=color, align=align, alpha=alpha, tracking=tracking)


def serif(c, s, x, y, size=70, color=WHITE, align="center", alpha=1.0):
    text(c, s, x, y, size=size, font=SERIF, fill=color, align=align, alpha=alpha)


def glass(c, x, y, w, h, r=36, a=1.0, glow=False):
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r)
    if glow:
        g = skia.Paint(Color=col(NEON, 0.16 * a), AntiAlias=True)
        g.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 40))
        c.drawRRect(rr, g)
    c.drawRRect(rr, P(skia.Color(24, 24, 28), 0.92 * a))
    grad = skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeLinear(
        [skia.Point(x, y), skia.Point(x, y + h)], [col(WHITE, 0.07 * a), col(WHITE, 0.0)]))
    c.drawRRect(rr, grad)
    c.drawRRect(rr, SP(WHITE, 2, 0.14 * a))


def check_icon(c, cx, cy, r, k, fillc=NEON, ink=INK):
    if k <= 0:
        return
    c.drawCircle(cx, cy, r * ease_out_back(clamp(k * 1.5)), P(fillc))
    p = skia.Path()
    p.moveTo(cx - r * 0.42, cy + r * 0.02)
    p.lineTo(cx - r * 0.1, cy + r * 0.34)
    if k > 0.4:
        p.lineTo(cx + r * 0.45, cy - r * 0.3)
    c.drawPath(p, SP(ink, r * 0.2))


def pill(c, t, t0, s, x, y, size=34, center=False):
    k = ease_out_back(prog(t, t0 - 0.03, 0.4))
    if k <= 0.01:
        return
    w = text_width(s, size, CAP, 0.04) + 120
    c.save()
    c.translate(x - (w / 2 if center else 0), y)
    c.scale(k, k)
    r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(0, -size * 1.05, w, size * 2.1), size * 1.05, size * 1.05)
    c.drawRRect(r, P(INK, 0.82))
    c.drawRRect(r, SP(WHITE, 2, 0.22))
    check_icon(c, size * 1.15, 0, size * 0.58, clamp((t - t0) / 0.35))
    text(c, s, size * 2.05, 0, size=size, font=CAP, fill=WHITE, align="left", tracking=0.04)
    c.restore()


def explainer_bg(c, t):
    c.drawRect(skia.Rect.MakeWH(W, H), P(INK))
    glow = skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeRadial(
        skia.Point(W / 2 + 120 * math.sin(t * 0.4), 900), 760, [col(NEON, 0.07), col(NEON, 0.0)]))
    c.drawRect(skia.Rect.MakeWH(W, H), glow)
    p = SP(WHITE, 1, 0.05)
    off = (t * 18) % 90
    for gx in range(0, W + 90, 90):
        c.drawLine(gx, 0, gx, H, p)
    for gy in range(-90, H + 90, 90):
        c.drawLine(0, gy + off, W, gy + off, p)


def section(c, t, t0, label):
    """the section label every explainer scene opens with."""
    k = fade(t, t0)
    c.drawRect(skia.Rect.MakeXYWH(90, 335, 16, 16), P(NEON, k))
    mono(c, label, 122, 343, 24, WHITE, alpha=k)


# face circle (explainer scenes)
FC_X, FC_Y, FC_R = 885, 392, 108


def face_circle(c, t, k):
    if k <= 0.01:
        return
    fx, fy, jx, jy = face(t)
    c.save()
    c.translate(FC_X, FC_Y)
    c.scale(k, k)
    sh = skia.Paint(Color=skia.Color(0, 0, 0, 140), AntiAlias=True)
    sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 22))
    c.drawCircle(0, 14, FC_R + 8, sh)
    path = skia.Path()
    path.addCircle(0, 0, FC_R)
    c.save()
    c.clipPath(path, skia.ClipOp.kIntersect, True)
    side = 520
    sx = clamp(fx + jx - side / 2, 0, SW - side)
    sy = clamp(fy + jy - side * 0.5, 0, SH - side)
    img, _ = layers(t)
    c.drawImageRect(img, skia.Rect.MakeXYWH(sx, sy, side, side),
                    skia.Rect.MakeXYWH(-FC_R, -FC_R, 2 * FC_R, 2 * FC_R), SAMP, skia.Paint(AntiAlias=True))
    c.restore()
    c.drawCircle(0, 0, FC_R + 3, SP(NEON, 5))
    # speaking indicator
    lv = 0.5 + 0.5 * math.sin(t * 9)
    c.drawCircle(FC_R * 0.72, FC_R * 0.72, 14, P(INK))
    c.drawCircle(FC_R * 0.72, FC_R * 0.72, 9, P(NEON, 0.6 + 0.4 * lv))
    c.restore()


def circle_k(t):
    """the face circle pops in at the start of an explainer run and out at its end."""
    for a, b, name, lay in TL.SCENES:
        if lay == "explainer" and a <= t < b:
            runs_a = a
            for a2, b2, n2, l2 in TL.SCENES:
                if b2 == runs_a and l2 == "explainer":
                    runs_a = a2
            return ease_out_back(prog(t, runs_a + 0.1, 0.45))
    return 0.0


# pipeline header shared by the steps
def pipeline(c, t, t0, active):
    k = fade(t, t0)
    labels = ["RECORD", "SAY IT", "EDIT"]
    x0, x1, y = 110, 700, 470
    c.drawLine(x0, y, x0 + (x1 - x0) * k, y, SP(WHITE, 2, 0.2))
    for i, lb in enumerate(labels):
        x = x0 + i * (x1 - x0) / 2
        kk = ease_out_back(prog(t, t0 + 0.08 * i, 0.4))
        if kk <= 0.01:
            continue
        on = i == active
        done = i < active
        c.save()
        c.translate(x, y)
        c.scale(kk, kk)
        c.drawCircle(0, 0, 30, P(NEON if (on or done) else INK))
        c.drawCircle(0, 0, 30, SP(NEON if (on or done) else WHITE, 3, 1 if (on or done) else 0.35))
        text(c, f"0{i + 1}", 0, 0, size=24, font="mono", fill=INK if (on or done) else WHITE)
        c.restore()
        mono(c, lb, x, y + 58, 20, NEON if on else WHITE, align="center", alpha=kk * (1 if on else 0.5))
    if active >= 0:
        ax = x0 + active * (x1 - x0) / 2
        pk = 0.5 + 0.5 * math.sin(t * 5)
        c.drawCircle(ax, y, 30 + 10 + 8 * pk, SP(NEON, 2, 0.5 * (1 - pk)))


# ------------------------------------------------------------------ scenes
BAND, KICK = 470, 292


def big(c, t, t0, s, color=WHITE, size=320, out_t=None, outline=False):
    kinetic(c, t, t0, s, W / 2, BAND, fit(s, size), color, outline=outline, out_t=out_t)


def kicker(c, t, t0, s, t_out=None):
    k = fade(t, t0) * (1 - (fade(t, t_out, 0.25) if t_out is not None else 0))
    serif(c, s, W / 2, KICK + (1 - fade(t, t0)) * 20, 66, WHITE, alpha=k)


def sc_hook(c, t, a, b):
    def behind(c, t):
        big(c, t, C["fully"], "FULLY", WHITE, out_t=C["edited"] - 0.12)
        big(c, t, C["edited"], "EDITED.", NEON)
    footage(c, t, seg_zoom(t), dim=0.55 * ease_in_out_cubic(prog(t, C["fully"] - 0.2, 0.3)), behind=behind)
    kicker(c, t, C["fully"] - 0.1, "this video is")


def sc_forever(c, t, a, b):
    explainer_bg(c, t)
    section(c, t, a, "THE OLD WAY")
    for i, (w_, ts, colr) in enumerate([("EDITING", C["editing"], WHITE), ("TAKES", C["takes"], WHITE),
                                        ("FOREVER.", C["forever"], NEON)]):
        kinetic(c, t, ts - 0.06, w_, W / 2, 660 + i * 205, 225, colr)
    # a render bar that never finishes
    k = fade(t, a + 0.1)
    bw = 700
    x, y = (W - bw) / 2, 1225
    c.drawRoundRect(skia.Rect.MakeXYWH(x, y, bw, 14), 7, 7, P(WHITE, 0.12 * k))
    pr = 0.92 + 0.07 * (1 - math.exp(-(t - a) * 1.5))
    c.drawRoundRect(skia.Rect.MakeXYWH(x, y, bw * pr * k, 14), 7, 7, P(NEON, k))
    mono(c, f"RENDERING... {int(pr * 100)}%", x, y - 30, 22, WHITE, alpha=0.6 * k, tracking=0.1)


def sc_pain(c, t, a, b):
    explainer_bg(c, t)
    section(c, t, a, "THE OLD WAY")
    rows = [("CUTTING", C["cutting"], "02:10"), ("CAPTIONS", C["captions"], "01:45"), ("MUSIC", C["music"], "00:50"),
            ("ZOOMS", C["zooms"], "01:20")]
    for i, (s, ts, hrs) in enumerate(rows):
        k = ease_out_expo(prog(t, ts - 0.05, 0.5))
        if k <= 0:
            continue
        y = 560 + i * 170
        x = 90 + (1 - k) * 80
        c.save()
        c.translate(x, 0)
        glass(c, 0, y - 70, W - 180, 140, 28, a=k)
        text(c, f"0{i + 1}", 46, y, size=26, font="mono", fill=col(NEON, k))
        text(c, s, 110, y + 4, size=96, font=BIG, fill=col(WHITE, k), align="left")
        text(c, hrs, W - 180 - 40, y, size=34, font="mono", fill=col(WHITE, 0.6 * k), align="right")
        sk = ease_in_out_cubic(prog(t, C["day"] + i * 0.1, 0.35))
        if sk > 0:
            c.drawRect(skia.Rect.MakeXYWH(100, y - 4, (text_width(s, 96, BIG) + 30) * sk, 10), P(NEON))
        c.restore()
    # total
    kt = fade(t, C["day"] + 0.3)
    if kt > 0:
        y = 560 + 4 * 170 - 20
        mono(c, "TOTAL / ONE VIDEO", 90, y, 24, WHITE, alpha=0.6 * kt)
        hrs = clamp((t - C["day"] - 0.3) / 0.6) * 5.75
        text(c, f"{int(hrs):02d}:{int(hrs % 1 * 60):02d} HRS", W - 90, y + 6, size=88, font=BIG, fill=col(NEON, kt),
             align="right")


def sc_built(c, t, a, b):
    explainer_bg(c, t)
    section(c, t, a, "SO I BUILT")
    k = ease_out_expo(prog(t, C["my_own"] - 0.15, 0.6))
    cx, cy = W / 2, 800
    # orbit rings + core
    for i, r in enumerate((300, 230, 160)):
        kk = ease_out_expo(prog(t, C["my_own"] - 0.15 + i * 0.08, 0.6))
        c.save()
        c.translate(cx, cy)
        c.rotate((t * (18 + i * 14)) * (1 if i % 2 else -1))
        dash = SP(WHITE if i else NEON, 2, 0.35 * kk)
        dash.setPathEffect(skia.DashPathEffect.Make([18, 14], 0))
        c.drawCircle(0, 0, r * kk, dash)
        c.drawCircle(r * kk, 0, 7, P(NEON, kk))
        c.restore()
    g = skia.Paint(Color=col(NEON, 0.35 * k), AntiAlias=True)
    g.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 60))
    c.drawCircle(cx, cy, 120 * k, g)
    c.drawCircle(cx, cy, 110 * k, P(NEON, k))
    text(c, "MY", cx, cy - 22, size=44 * k + 0.1, font=BIG, fill=INK)
    text(c, "SYSTEM", cx, cy + 24, size=44 * k + 0.1, font=BIG, fill=INK)
    kinetic(c, t, C["system"] - 0.05, "MY OWN SYSTEM.", W / 2, 1230, fit("MY OWN SYSTEM.", 140), WHITE)


def phone(c, t, x, y, w, h):
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), 54, 54)
    sh = skia.Paint(Color=skia.Color(0, 0, 0, 160), AntiAlias=True)
    sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 30))
    c.drawRRect(rr, sh)
    c.drawRRect(rr, P(skia.Color(30, 30, 34)))
    c.drawRRect(rr, SP(WHITE, 2, 0.25))
    scr = skia.Rect.MakeXYWH(x + 14, y + 14, w - 28, h - 28)
    c.save()
    c.clipRRect(skia.RRect.MakeRectXY(scr, 42, 42), True)
    img, _ = layers(t)
    c.save()
    place(c, t, 1.12, rect=(scr.x(), scr.y(), scr.width(), scr.height()))
    c.drawImage(img, 0, 0, SAMP)
    c.restore()
    c.restore()
    c.drawRoundRect(skia.Rect.MakeXYWH(x + w / 2 - 48, y + 28, 96, 26), 13, 13, P(INK))
    on = (t * 2) % 1 < 0.6
    c.drawRoundRect(skia.Rect.MakeXYWH(x + 36, y + 76, 150, 46), 23, 23, P(INK, 0.6))
    c.drawCircle(x + 62, y + 99, 9, P(skia.Color(255, 64, 56), 1 if on else 0.3))
    mono(c, "REC", x + 82, y + 99, 20, WHITE)


def sc_step1(c, t, a, b):
    explainer_bg(c, t)
    section(c, t, a, "STEP 01")
    pipeline(c, t, a + 0.05, 0)
    kinetic(c, t, C["record"] - 0.08, "RECORD.", 90, 640, 150, NEON, align="left")
    k = ease_out_expo(prog(t, a + 0.25, 0.7))
    phone(c, t, 560 + (1 - k) * 500, 600, 400, 720)
    serif(c, "on my phone", 90, 770, 64, WHITE, align="left", alpha=fade(t, C["phone"] - 0.1))
    pill(c, t, C["one_take"], "ONE TAKE", 90, 940)
    pill(c, t, C["mistakes"], "MISTAKES", 90, 1060)
    pill(c, t, C["mistakes"] + 0.3, "ARE FINE", 90, 1180)


def sc_step2(c, t, a, b):
    explainer_bg(c, t)
    section(c, t, a, "STEP 02")
    pipeline(c, t, a + 0.05, 1)
    kinetic(c, t, C["tell"] - 0.1, "SAY IT.", 90, 650, 150, NEON, align="left")
    serif(c, "in plain words", 90 + text_width("SAY IT.", 150, BIG) + 24, 670, 64, WHITE, align="left",
          alpha=fade(t, C["normal"] - 0.1))
    k = ease_out_expo(prog(t, a + 0.3, 0.7))
    x, y, w, h = 90, 780 + (1 - k) * 200, W - 180, 470
    glass(c, x, y, w, h, 40, a=k, glow=True)
    mono(c, "MY SYSTEM", x + 50, y + 60, 22, NEON, alpha=k)
    for i in range(3):
        c.drawCircle(x + w - 60 - i * 34, y + 60, 9, P(WHITE, 0.25 * k))
    c.drawLine(x + 40, y + 108, x + w - 40, y + 108, SP(WHITE, 1, 0.12 * k))
    words = [wd for wd in WORDS if C["type_start"] - 0.05 <= wd["s"] <= C["type_end"]]
    shown = ""
    for wd in words:
        if t >= wd["s"]:
            frac = clamp((t - wd["s"]) / max(0.1, (wd["e"] - wd["s"]) * 0.6))
            tok = wd["w"].lower().replace(".", "")
            shown += tok[:int(round(len(tok) * frac))]
            if frac >= 1:
                shown += " "
    shown = shown.strip()
    size = 52
    lines, cur = [], ""
    for wd in shown.split(" ") if shown else []:
        trial = (cur + " " + wd).strip()
        if text_width(trial, size, "mono") > w - 120 and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = trial
    if cur:
        lines.append(cur)
    ty = y + 190
    if not lines:
        text(c, "describe the vibe...", x + 50, ty, size=size, font="mono", fill=col(WHITE, 0.3 * k), align="left")
    for i, ln in enumerate(lines):
        text(c, ln, x + 50, ty + i * 76, size=size, font="mono", fill=WHITE, align="left")
    if (t * 2.2) % 1 < 0.55:
        last = lines[-1] if lines else ""
        cx_ = x + 50 + (text_width(last, size, "mono") + 8 if last else 0)
        c.drawRect(skia.Rect.MakeXYWH(cx_, ty + max(0, len(lines) - 1) * 76 - 30, 5, 60), P(NEON))
    sk = prog(t, C["send"], 0.3)
    s_ = 1 - 0.15 * math.sin(math.pi * sk)
    c.save()
    c.translate(x + w - 90, y + h - 80)
    c.scale(s_ * k, s_ * k)
    c.drawCircle(0, 0, 46, P(NEON if t >= C["send"] else WHITE, 1 if t >= C["send"] else 0.15))
    p = skia.Path()
    p.moveTo(0, 20)
    p.lineTo(0, -18)
    p.moveTo(-15, -4)
    p.lineTo(0, -19)
    p.lineTo(15, -4)
    c.drawPath(p, SP(INK if t >= C["send"] else WHITE, 6))
    c.restore()


def sc_step3(c, t, a, b):
    z = seg_zoom(t)
    if t >= C["s3_zooms"]:
        z = lerp(z, 1.36, ease_out_expo(prog(t, C["s3_zooms"], 0.3)) * (1 - ease_in_out_cubic(
            prog(t, C["s3_zoom_back"], 0.25))))
    if t >= C["s3_music"]:
        z *= 1 + 0.04 * math.exp(-(t - C["s3_music"]) * 4) * abs(math.cos((t - C["s3_music"]) * 13))
    dim = 0.55 * ease_in_out_cubic(prog(t, C["it_edits"] - 0.2, 0.3)) * (1 - ease_in_out_cubic(
        prog(t, C["s3_cuts"] - 0.1, 0.25)))

    def behind(c, t):
        big(c, t, C["it_edits"] - 0.05, "IT EDITS.", NEON, out_t=C["s3_cuts"] - 0.15)
    footage(c, t, z, dim, behind=behind if t < C["s3_cuts"] + 0.1 else None)
    kicker(c, t, a + 0.05, "step three", t_out=C["s3_cuts"] - 0.2)
    fk = 1 - prog(t, C["s3_cuts"], 0.12)
    if t >= C["s3_cuts"] and fk > 0:
        c.drawRect(skia.Rect.MakeWH(W, H), P(WHITE, 0.6 * fk))
    mk = t - C["s3_music"]
    if 0 <= mk < 0.8:
        env = math.sin(math.pi * mk / 0.8)
        for i in range(16):
            hh = (120 + 280 * (noise1(i * 2.7 + math.floor(mk * 24), 4) + 1) / 2) * env
            c.drawRoundRect(skia.Rect.MakeXYWH(36 + i * 64, 1240 - hh, 40, hh), 20, 20, P(NEON, 0.9))
    x = 70
    for s, ts in [("CUTS", C["s3_cuts"]), ("CAPTIONS", C["s3_captions"]), ("ZOOMS", C["s3_zooms"]),
                  ("MUSIC", C["s3_music"])]:
        pill(c, t, ts, s, x, 330, size=26)
        x += text_width(s, 26, CAP, 0.04) + 120 * 26 / 34 + 18


def sc_nos(c, t, a, b):
    explainer_bg(c, t)
    section(c, t, a, "WHAT YOU NEED")
    rows = [("EDITING APP", C["no1"]), ("EDITOR", C["no2"]), ("SKILLS", C["no3"])]
    for i, (s, ts) in enumerate(rows):
        k = ease_out_expo(prog(t, ts - 0.06, 0.5))
        if k <= 0:
            continue
        y = 640 + i * 220
        c.save()
        c.translate((1 - k) * 120, 0)
        glass(c, 90, y - 85, W - 180, 170, 34, a=k)
        text(c, "NO", 150, y + 4, size=120, font=BIG, fill=col(NEON, k), align="left")
        text(c, s, 150 + text_width("NO ", 120, BIG), y + 4, size=fit(s, 120, 620), font=BIG, fill=col(WHITE, k),
             align="left")
        # cross icon
        cx_, cy_ = W - 170, y
        xk = ease_out_expo(prog(t, ts + 0.1, 0.3))
        c.drawCircle(cx_, cy_, 34, SP(WHITE, 2, 0.3 * k))
        c.drawLine(cx_ - 14 * xk, cy_ - 14 * xk, cx_ + 14 * xk, cy_ + 14 * xk, SP(NEON, 5))
        c.drawLine(cx_ + 14 * xk, cy_ - 14 * xk, cx_ - 14 * xk, cy_ + 14 * xk, SP(NEON, 5))
        c.restore()


def sc_talk(c, t, a, b):
    def behind(c, t):
        big(c, t, C["talk"] - 0.05, "TALK.", NEON, size=320)
    footage(c, t, seg_zoom(t), dim=0.55 * ease_in_out_cubic(prog(t, C["talk"] - 0.25, 0.3)), behind=behind)
    kicker(c, t, a + 0.05, "if you can")


def sc_cover(c, t, a, b):
    k0 = ease_out_expo(prog(t, a, 0.6))

    def behind(c, t):
        kinetic(c, t, a + 0.05, "VIBE", W / 2, 520, 440, WHITE, per=0.05)
    footage(c, t, 1.02 + 0.03 * prog(t, a, b - a), dim=0.35, behind=behind)
    mono(c, "THE EDIT ISSUE", 90, 300, 24, WHITE, alpha=k0)
    mono(c, "NO. 01  /  2026", W - 90, 300, 24, WHITE, align="right", alpha=k0)
    c.drawRect(skia.Rect.MakeXYWH(90, 330, (W - 180) * k0, 2), P(WHITE, 0.6))
    k1 = ease_out_expo(prog(t, C["exactly"] - 0.1, 0.5))
    if k1 > 0:
        x = 90 - (1 - k1) * 60
        c.drawRect(skia.Rect.MakeXYWH(x, 860, 10, 196), P(NEON, k1))
        text(c, "MADE", x + 34, 890, size=74, font=BIG, fill=col(WHITE, k1), align="left")
        text(c, "EXACTLY", x + 34, 960, size=74, font=BIG, fill=col(NEON, k1), align="left")
        text(c, "LIKE THAT", x + 34, 1030, size=74, font=BIG, fill=col(WHITE, k1), align="left")
    k2 = ease_out_expo(prog(t, C["every"] - 0.1, 0.5))
    if k2 > 0:
        x = W - 90 + (1 - k2) * 60
        serif(c, "every video", x, 1080, 70, WHITE, align="right", alpha=k2)
        text(c, "ON MY PAGE", x, 1150, size=74, font=BIG, fill=col(NEON, k2), align="right")
    k3 = ease_out_back(prog(t, C["page"], 0.4))
    if k3 > 0.01:
        c.save()
        c.translate(870, 720)
        c.rotate(-12)
        c.scale(k3, k3)
        c.drawCircle(0, 0, 112, P(NEON))
        text(c, "EDITED", 0, -26, size=46, font=BIG, fill=INK)
        text(c, "BY MY SYSTEM", 0, 26, size=26, font="mono", fill=INK, tracking=0.04)
        c.restore()


def sc_open(c, t, a, b):
    explainer_bg(c, t)
    section(c, t, a, "NOW OPENING")
    serif(c, "opening it up to", W / 2, 640, 72, WHITE, alpha=fade(t, a + 0.1))
    kinetic(c, t, C["few"] - 0.1, "A FEW", W / 2, 800, 200, WHITE)
    kinetic(c, t, C["creators"] - 0.05, "CREATORS.", W / 2, 1000, fit("CREATORS.", 210), NEON)
    # seats: a row of avatars, a few light up
    n = 7
    for i in range(n):
        k = ease_out_back(prog(t, a + 0.3 + i * 0.05, 0.4))
        if k <= 0.01:
            continue
        x = W / 2 + (i - (n - 1) / 2) * 120
        y = 1230
        lit = i in (1, 3, 4) and t > C["creators"] + 0.1 + i * 0.05
        c.save()
        c.translate(x, y)
        c.scale(k, k)
        c.drawCircle(0, 0, 44, P(NEON if lit else WHITE, 1 if lit else 0.08))
        c.drawCircle(0, 0, 44, SP(WHITE, 2, 0.25))
        c.drawCircle(0, -10, 14, P(INK if lit else WHITE, 1 if lit else 0.35))
        c.drawRoundRect(skia.Rect.MakeXYWH(-22, 8, 44, 22), 11, 11, P(INK if lit else WHITE, 1 if lit else 0.35))
        c.restore()


def sc_cta(c, t, a, b):
    dim = max(0.3 * ease_in_out_cubic(prog(t, C["how"] - 0.2, 0.3)),
              0.8 * ease_in_out_cubic(prog(t, C["comment"] - 0.2, 0.3)))

    def behind(c, t):
        big(c, t, C["cta_system"] - 0.08, "SYSTEM", NEON, size=340)
    footage(c, t, seg_zoom(t), dim, behind=behind)
    kicker(c, t, C["how"] - 0.15, "want to see how it works?", t_out=C["comment"] - 0.25)
    kicker(c, t, C["comment"] - 0.05, "comment")
    kt = ease_out_back(prog(t, C["tap"] - 0.05, 0.4))
    if kt > 0.01:
        s = "TAP THE LINK BELOW"
        size = 44
        w = text_width(s, size, CAP, 0.06) + 150
        c.save()
        c.translate(W / 2, 1300)
        c.scale(kt, kt)
        c.drawRoundRect(skia.Rect.MakeXYWH(-w / 2, -48, w, 96), 48, 48, P(WHITE))
        text(c, s, -w / 2 + 50, 0, size=size, font=CAP, fill=INK, align="left", tracking=0.06)
        bob = math.sin((t - C["tap"]) * 7) * 5
        p = skia.Path()
        p.moveTo(w / 2 - 74, -10 + bob)
        p.lineTo(w / 2 - 58, 6 + bob)
        p.lineTo(w / 2 - 42, -10 + bob)
        c.drawPath(p, SP(INK, 6))
        c.restore()
    mono(c, "THE VIBE EDITING SYSTEM", W / 2, 1440, 26, WHITE, align="center", alpha=fade(t, C["tap"] + 0.6),
         tracking=0.2)


FN = dict(hook=sc_hook, forever=sc_forever, pain=sc_pain, built=sc_built, step1=sc_step1, step2=sc_step2,
          step3=sc_step3, nos=sc_nos, talk=sc_talk, cover=sc_cover, open=sc_open, cta=sc_cta)


# ------------------------------------------------------------------ captions (big) + hud + finish
def chunks():
    out, cur = [], []
    for wd in WORDS:
        cur.append(wd)
        txt = " ".join(x["w"] for x in cur)
        if wd["w"][-1] in ".,:;!?" or len(cur) >= 2 or len(txt) >= 11:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


CHUNKS = chunks()


def captions(c, t):
    if t >= C["comment"] - 0.05:
        return
    for i, ch in enumerate(CHUNKS):
        s0 = ch[0]["s"]
        nxt = CHUNKS[i + 1][0]["s"] if i + 1 < len(CHUNKS) else ch[-1]["e"] + 0.4
        if s0 - 0.04 <= t < min(nxt, ch[-1]["e"] + 0.45):
            break
    else:
        return
    size = 96
    ws = [x["w"].upper().strip(".,:;!?") for x in ch]
    sp = text_width(" ", size, CAP)
    widths = [text_width(s, size, CAP) for s in ws]
    total = sum(widths) + sp * (len(ws) - 1)
    if total > W - 120:
        size *= (W - 120) / total
        widths = [w * size / 96 for w in widths]
        sp *= size / 96
        total = W - 120
    k = ease_out_back(prog(t, s0 - 0.04, 0.18))
    boost = 1.0
    if C["s3_captions"] - 0.05 <= t < C["s3_captions"] + 0.6:
        boost = lerp(1.0, 1.25, ease_out_back(prog(t, C["s3_captions"] - 0.05, 0.25)))
    c.save()
    full = TL.SCENES[scene_at(t)][3] == "full"
    c.translate(W / 2, 1440 if full else 1385)
    c.scale(lerp(0.85, 1, k) * boost, lerp(0.85, 1, k) * boost)
    sh = skia.Paint(Color=skia.Color(0, 0, 0, 150), AntiAlias=True)
    sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 22))
    c.drawRoundRect(skia.Rect.MakeXYWH(-total / 2 - 30, -60, total + 60, 120), 60, 60, sh)
    x = -total / 2
    for wd, s, ww in zip(ch, ws, widths):
        active = wd["s"] - 0.04 <= t
        now = active and (t < wd["e"] + 0.1 or wd is ch[-1])
        fc = NEON if now else (WHITE if active else col(WHITE, 0.5))
        text(c, s, x, 0, size=size, font=CAP, fill=fc, align="left", stroke=6, stroke_col=col(INK, 0.55))
        x += ww + sp
    c.restore()


def hud(c, t):
    p = SP(WHITE, 3, 0.45)
    m, L = 44, 52
    for (x, y, sx, sy) in [(m, 246, 1, 1), (W - m, 246, -1, 1), (m, H - 300, 1, -1), (W - m, H - 300, -1, -1)]:
        path = skia.Path()
        path.moveTo(x, y + sy * L)
        path.lineTo(x, y)
        path.lineTo(x + sx * L, y)
        c.drawPath(path, p)


def _grain():
    rng = np.random.default_rng(3)
    out = []
    for _ in range(8):
        n = rng.normal(128, 40, (H // 2, W // 2)).clip(0, 255).astype(np.uint8)
        out.append(skia.Image.fromarray(np.ascontiguousarray(np.dstack([n, n, n, np.full_like(n, 20)])),
                                        colorType=skia.kRGBA_8888_ColorType))
    return out


GRAIN = _grain()
VIG = skia.Paint(Shader=skia.GradientShader.MakeRadial(
    skia.Point(W / 2, H * 0.45), H * 0.72, [skia.Color(0, 0, 0, 0), skia.Color(0, 0, 0, 0), skia.Color(0, 0, 0, 110)],
    [0.0, 0.55, 1.0]))


def finish(c, t):
    c.drawRect(skia.Rect.MakeWH(W, H), VIG)
    p = skia.Paint()
    p.setBlendMode(skia.BlendMode.kOverlay)
    c.drawImageRect(GRAIN[int(t * 24) % len(GRAIN)], skia.Rect.MakeWH(W, H), skia.SamplingOptions(), p)


# ------------------------------------------------------------------ zoom transitions
def scene_at(t):
    for i, (a, b, *_ ) in enumerate(TL.SCENES):
        if a <= t < b:
            return i
    return len(TL.SCENES) - 1


_SURF = {}


def snapshot(i, t):
    s = _SURF.get("s") or skia.Surface(W, H)
    _SURF["s"] = s
    with s as cc:
        cc.clear(INK)
        a, b, name, lay = TL.SCENES[i]
        FN[name](cc, t, a, b)
    return s.makeImageSnapshot()


def zoom_blit(c, img, scale, alpha=1.0, blur_amt=0.0):
    """draw a full-frame image scaled about the centre, with a cheap radial motion blur (stacked scales)."""
    n = 5 if blur_amt > 0.01 else 1
    for j in range(n):
        s = scale * (1 + blur_amt * j / max(1, n - 1))
        p = skia.Paint(Alphaf=alpha if j == 0 else alpha * 0.35 / j)
        c.save()
        c.translate(W / 2, H * 0.46)
        c.scale(s, s)
        c.translate(-W / 2, -H * 0.46)
        c.drawImage(img, 0, 0, SAMP, p)
        c.restore()


def draw(c, t):
    i = scene_at(t)
    a = TL.SCENES[i][0]
    half = TL.ZOOM_T / 2
    if i > 0 and t < a + half:
        k = (t - (a - half)) / TL.ZOOM_T          # 0.5 .. 1 here (incoming)
        e = (k - 0.5) * 2
        img = snapshot(i, t)
        c.drawRect(skia.Rect.MakeWH(W, H), P(INK))
        zoom_blit(c, img, lerp(1.35, 1.0, ease_out_expo(e)), 1.0, blur_amt=0.10 * (1 - e))
        c.drawRect(skia.Rect.MakeWH(W, H), P(WHITE, 0.10 * (1 - e) ** 2))
    elif i + 1 < len(TL.SCENES) and t >= TL.SCENES[i + 1][0] - half:
        nxt = TL.SCENES[i + 1][0]
        e = (t - (nxt - half)) / half            # 0 .. 1 (outgoing)
        img = snapshot(i, t)
        c.drawRect(skia.Rect.MakeWH(W, H), P(INK))
        zoom_blit(c, img, lerp(1.0, 1.4, ease_in_cubic(e)), 1.0, blur_amt=0.10 * e)
        c.drawRect(skia.Rect.MakeWH(W, H), P(WHITE, 0.10 * e ** 2))
    else:
        a, b, name, lay = TL.SCENES[i]
        FN[name](c, t, a, b)
    face_circle(c, t, circle_k(t))
    captions(c, t)
    hud(c, t)
    finish(c, t)


# ------------------------------------------------------------------ prep / audio
def prep():
    import subprocess
    G = ("eq=contrast=1.08:saturation=0.98:gamma=1.02,colorbalance=rs=-0.03:bs=0.04:rh=0.04:gh=0.01:bh=-0.04,"
         "curves=master='0/0.03 0.2/0.18 0.5/0.5 0.85/0.88 1/0.96'")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "work/stab60.mp4", "-vf", G, "-f", "rawvideo", "-pix_fmt",
                    "rgb24", "work/frames60.rgb"], check=True)
    fr = np.memmap("work/frames60.rgb", np.uint8, "r").reshape(-1, SH, SW, 3)
    n = len(fr)
    pts = []
    for i in range(n):
        g = fr[i, 380:1000:4, 100:620:4].mean(-1)
        ys, xs = np.nonzero(g < 40)
        if len(xs) > 40:
            pts.append((100 + xs.mean() * 4, 380 + ys.mean() * 4))
        else:
            pts.append(pts[-1] if pts else (360, 640))
    pts = np.array(pts)

    def smooth(x, n_):
        k = np.ones(n_) / n_
        return np.convolve(np.pad(x, n_ // 2, mode="edge"), k, "valid")[:len(x)]
    raw = np.stack([smooth(pts[:, j], 5) for j in range(2)], 1)
    slow = np.stack([smooth(pts[:, j], 61) for j in range(2)], 1)
    jit = np.clip(raw - slow, -40, 40) * 0.85
    track = np.hstack([slow[:, :1], slow[:, 1:] + 90, jit])
    json.dump(track.round(2).tolist(), open("work/track60.json", "w"))
    print("prep done", n, "jitter rms", np.sqrt((jit ** 2).mean(0)).round(2))


def build_audio():
    import subprocess
    import audio_kit as ak
    ak.voice_chain("work/voice_cut_raw.wav", "work/voice.wav", denoise=True)
    sr = ak.SR
    n = int(TL.DURATION * sr)
    bed = ak.music_bed(TL.MOOD, seconds=TL.DURATION + 2, seed=TL.SEED)[:n]
    if len(bed) < n:
        bed = np.pad(bed, ((0, n - len(bed)), (0, 0)))
    tt = np.arange(n) / sr
    env = np.where(tt < C["s3_music"], 0.6, 1.0)
    env = np.convolve(env, np.ones(800) / 800, mode="same")
    env *= np.clip((TL.DURATION - tt) / 1.3, 0, 1)
    ak.write_wav("work/music.wav", (bed * env[:, None]).astype(np.float32))
    sfx = []
    for (a2, *_ ) in TL.SCENES[1:]:
        sfx.append({"t": a2 - 0.2, "kind": "whoosh", "gain_db": -12, "dur": 0.4})
    for key in ("fully", "edited", "forever", "system", "record", "it_edits", "talk", "creators", "cta_system"):
        sfx.append({"t": C[key] - 0.03, "kind": "impact", "gain_db": -16})
    for key in ("cutting", "captions", "music", "zooms", "one_take", "mistakes", "exactly", "every", "page", "tap",
                "no1", "no2", "no3"):
        sfx.append({"t": C[key], "kind": "click", "gain_db": -12})
    sfx += [
        {"t": C["day"], "kind": "glitch", "gain_db": -16},
        {"t": C["type_start"], "kind": "typing", "gain_db": -15, "dur": C["type_end"] - C["type_start"]},
        {"t": C["send"], "kind": "pop", "gain_db": -10},
        {"t": C["s3_cuts"] - 0.02, "kind": "shutter", "gain_db": -9},
        {"t": C["s3_zooms"] - 0.05, "kind": "whoosh", "gain_db": -12, "dur": 0.3},
        {"t": C["s3_music"] - 1.0, "kind": "riser", "gain_db": -17, "dur": 1.0},
        {"t": C["s3_music"] - 0.02, "kind": "bass_drop", "gain_db": -7},
        {"t": C["tap"] + 0.6, "kind": "sparkle", "gain_db": -15},
    ]
    cues = {"duration": TL.DURATION, "voice": {"file": "work/voice.wav", "gain_db": 0, "t": 0},
            "music": {"file": "work/music.wav", "gain_db": -11, "duck_db": -9, "fade_out": 1.2}, "sfx": sfx}
    Path("work/cues.json").write_text(json.dumps(cues, indent=1))
    ak.write_wav("work/mix.wav", ak.mix(cues))
    print("audio -> work/mix.wav")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stills"
    if cmd == "prep":
        prep()
    elif cmd == "stills":
        S.stills(draw, [float(x) for x in sys.argv[2:]] or [1.5, 6.0, 10.8, 13.0])
    elif cmd == "audio":
        build_audio()
    elif cmd == "render":
        a_ = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
        b_ = float(sys.argv[3]) if len(sys.argv) > 3 else None
        S.render(draw, sys.argv[4] if len(sys.argv) > 4 else "out/pitch_picture.mp4", crf=16, start=a_, end=b_)
