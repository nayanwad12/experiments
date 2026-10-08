"""scene: premium pitch edit. Dark cinematic grade, white + neon type, kinetic text behind the subject,
magazine layouts. Every frame is a pure function of time t.

    python3 scene.py prep                 # matte -> work/matte.u8, head track -> work/track.json
    python3 scene.py stills 1.0 5.0       # check frames -> out/stills/
    python3 scene.py audio                # voice + music + sfx -> work/mix.wav
    python3 scene.py render               # picture -> out/pitch_picture.mp4
    python3 scene.py compare              # before/after -> out/pitch_compare_picture.mp4
"""

import json
import math
import sys
from pathlib import Path

import numpy as np
import skia

sys.path.insert(0, str(Path(__file__).resolve().parent / "vibe"))
from motion_kit import (Stage, clamp, ease_in_cubic, ease_in_out_cubic, ease_out_back, ease_out_cubic,  # noqa: E402
                        ease_out_expo, ease_out_quart, lerp, noise1, prog, text, text_width)

import timeline as TL  # noqa: E402

W, H, FPS = TL.W, TL.H, TL.FPS
C = TL.CUE
S = Stage(W, H, fps=FPS, duration=TL.DURATION)
SW, SH = 720, 1280

WHITE = skia.Color(255, 255, 255)
NEON = skia.Color(212, 255, 63)
INK = skia.Color(11, 11, 13)
SERIF = "InstrumentSerif-Italic.ttf"
BIG = "impact"          # Anton
CAP = "InterTight-700.ttf"


def col(c, a):
    return skia.Color(skia.ColorGetR(c), skia.ColorGetG(c), skia.ColorGetB(c), int(255 * clamp(a)))


# ------------------------------------------------------------------ footage + matte
def _load():
    fr = np.memmap("work/frames.rgb", np.uint8, "r").reshape(-1, SH, SW, 3)
    mt = np.memmap("work/matte.u8", np.uint8, "r").reshape(-1, SH, SW) if Path("work/matte.u8").exists() else None
    tr = np.array(json.load(open("work/track.json"))) if Path("work/track.json").exists() else None
    return fr, mt, tr


FR, MT, TRACK = _load()
NF = len(FR)
WORDS = json.load(open("work/words_cut.json"))


def fidx(t):
    return int(clamp(min(t, TL.SPEECH_END) * FPS, 0, NF - 1))


def head(t):
    if TRACK is None:
        return 360.0, 600.0
    x, y = TRACK[fidx(t)]
    return float(x), float(y)


def layers(t, dim=0.0):
    """(background image, person image) for frame t. dim darkens + desaturates only the background."""
    i = fidx(t)
    rgb = FR[i].astype(np.float32)
    if MT is None or dim <= 0.001:
        bgimg = skia.Image.fromarray(np.ascontiguousarray(np.dstack([FR[i], np.full((SH, SW), 255, np.uint8)])),
                                     colorType=skia.kRGBA_8888_ColorType)
        return bgimg, None
    m = MT[i].astype(np.float32)[..., None] / 255.0
    gray = rgb.mean(-1, keepdims=True)
    bg = (rgb * (1 - 0.45 * dim) + gray * 0.45 * dim) * (1 - 0.72 * dim)
    bg = np.dstack([np.clip(bg, 0, 255).astype(np.uint8), np.full((SH, SW), 255, np.uint8)])
    pa = np.empty((SH, SW, 4), np.uint8)
    pa[..., :3] = (rgb * m).astype(np.uint8)
    pa[..., 3] = (m[..., 0] * 255).astype(np.uint8)
    bgimg = skia.Image.fromarray(np.ascontiguousarray(bg), colorType=skia.kRGBA_8888_ColorType)
    pimg = skia.Image.fromarray(pa, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)
    return bgimg, pimg


SAMP = skia.SamplingOptions(skia.CubicResampler.CatmullRom())


def place(c, t, zoom, dx=0.0, dy=0.0, rect=None):
    """canvas transform mapping source pixels onto the dest rect (default full frame), centred on the head."""
    x, y, w, h = rect or (0, 0, W, H)
    hx, hy = head(t)
    a = w / h
    sh = min(SH, SW / a) / zoom
    sw = sh * a
    sx = clamp(hx - sw / 2, 0, SW - sw) if zoom > 1.0001 or abs(a - SW / SH) > 0.01 else (SW - sw) / 2
    sy = clamp(hy + 120 - sh * 0.42, 0, SH - sh) if zoom > 1.0001 or abs(a - SW / SH) > 0.01 else (SH - sh) / 2
    k = w / sw
    c.translate(x + dx, y + dy)
    c.scale(k, k)
    c.translate(-sx, -sy)


def footage(c, t, zoom=1.0, dim=0.0, behind=None, dx=0.0, dy=0.0):
    bgimg, pimg = layers(t, dim if behind else dim * 0.7)
    c.save()
    place(c, t, zoom, dx, dy)
    c.drawImage(bgimg, 0, 0, SAMP)
    c.restore()
    if behind and pimg is not None:
        behind(c, t)
        c.save()
        place(c, t, zoom, dx, dy)
        c.drawImage(pimg, 0, 0, SAMP)
        c.restore()


def to_screen(t, zoom, sx_, sy_):
    """source pixel -> screen pixel for the full-frame placement."""
    m = skia.Matrix()
    c = skia.Canvas(skia.Bitmap())
    place(c, t, zoom)
    m = c.getTotalMatrix()
    p = m.mapXY(sx_, sy_)
    return p.x(), p.y()


# ------------------------------------------------------------------ type
def kinetic(c, t, t0, s, cx, cy, size, color=WHITE, outline=False, per=0.035, dur=0.42, out_t=None, tracking=0.0):
    """letters rise out of a mask line by line (kinetic headline)."""
    if t < t0:
        return
    font = BIG
    tw = text_width(s, size, font, tracking)
    x = cx - tw / 2
    f = skia.Font(None, size)
    k_out = ease_in_cubic(prog(t, out_t, 0.25)) if out_t is not None else 0.0
    c.save()
    c.clipRect(skia.Rect.MakeLTRB(-200, cy - size * 0.62, W + 200, cy + size * 0.62))
    for i, ch in enumerate(s):
        k = ease_out_expo(prog(t, t0 + i * per, dur))
        yy = cy + (1 - k) * size * 1.05 - k_out * size * 1.1
        if outline:
            text(c, ch, x, yy, size=size, font=font, fill=col(WHITE, 0), align="left", stroke=4,
                 stroke_col=color)
        else:
            text(c, ch, x, yy, size=size, font=font, fill=color, align="left")
        x += text_width(ch, size, font) + tracking * size
    c.restore()


def mono(c, s, x, y, size=26, color=WHITE, align="left", alpha=1.0, tracking=0.12):
    text(c, s, x, y, size=size, font="mono", fill=color, align=align, alpha=alpha, tracking=tracking)


def serif(c, s, x, y, size=72, color=WHITE, align="center", alpha=1.0):
    text(c, s, x, y, size=size, font=SERIF, fill=color, align=align, alpha=alpha)


def fade_up(t, t0, dur=0.4):
    return ease_out_cubic(prog(t, t0, dur))


def tag(c, t, t0, s, x, y):
    """magazine section tag: neon square + mono label + hairline."""
    k = fade_up(t, t0, 0.45)
    if k <= 0:
        return
    c.drawRect(skia.Rect.MakeXYWH(x, y - 9, 18, 18), skia.Paint(Color=col(NEON, k)))
    mono(c, s, x + 34, y, 26, WHITE, alpha=k)
    lw = 220 * k
    c.drawRect(skia.Rect.MakeXYWH(x + 40 + text_width(s, 26, "mono", 0.12) + 14, y - 1, lw, 2),
               skia.Paint(Color=col(WHITE, 0.5 * k)))


def pill(c, t, t0, s, x, y, check=True, small=False):
    k = ease_out_back(prog(t, t0 - 0.03, 0.35))
    if k <= 0.01:
        return
    size = 28 if small else 36
    w = text_width(s, size, CAP, 0.04) + (110 if check else 60)
    c.save()
    c.translate(x, y)
    c.scale(k * (0.8 if small else 1), k * (0.8 if small else 1))
    r = skia.Rect.MakeXYWH(0, -38, w, 76)
    c.drawRRect(skia.RRect.MakeRectXY(r, 38, 38), skia.Paint(Color=skia.Color(11, 11, 13, 200), AntiAlias=True))
    c.drawRRect(skia.RRect.MakeRectXY(r, 38, 38), skia.Paint(Color=col(WHITE, 0.25), AntiAlias=True,
                                                              Style=skia.Paint.kStroke_Style, StrokeWidth=2))
    if check:
        c.drawCircle(40, 0, 20, skia.Paint(Color=NEON, AntiAlias=True))
        kk = clamp((t - t0) / 0.3)
        p = skia.Path()
        p.moveTo(30, 1)
        p.lineTo(37, 8)
        if kk > 0.4:
            p.lineTo(51, -8)
        c.drawPath(p, skia.Paint(Color=INK, AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=5,
                                 StrokeCap=skia.Paint.kRound_Cap))
    text(c, s, 80 if check else 30, 0, size=size, font=CAP, fill=WHITE, align="left", tracking=0.04)
    c.restore()


def settle(t, t0, amt=0.07, dur=0.6):
    return 1.0 + amt * (1 - ease_out_cubic(prog(t, t0, dur)))


def dim_ramp(t, t_on, t_off=None, level=0.55):
    k = ease_in_out_cubic(prog(t, t_on - 0.15, 0.3))
    if t_off is not None:
        k *= 1 - ease_in_out_cubic(prog(t, t_off, 0.3))
    return level * k


# ------------------------------------------------------------------ backgrounds for graphic scenes
def dark_bg(c, t, big_num=None):
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Color=INK))
    # faint editorial grid
    p = skia.Paint(Color=skia.Color(255, 255, 255, 14), StrokeWidth=1)
    for x in (90, 540, 990):
        c.drawLine(x, 0, x, H, p)
    for y in (240, 1500):
        c.drawLine(0, y, W, y, p)
    if big_num:
        text(c, big_num, W - 60, 1420, size=520, font=BIG, fill=skia.Color(255, 255, 255, 10), align="right")


# ------------------------------------------------------------------ scenes
BAND = 500          # centre line of the behind-the-head type band
KICK = 300          # serif kicker line above it


def fit(s, size, font=BIG, max_w=W - 110):
    return min(size, size * max_w / max(1.0, text_width(s, size, font)))


def big(c, t, t0, s, color=WHITE, size=320, out_t=None, outline=False):
    kinetic(c, t, t0, s, W / 2, BAND, fit(s, size), color, outline=outline, out_t=out_t, per=0.03)


def kicker(c, t, t0, s, t_out=None):
    k = fade_up(t, t0, 0.4) * (1 - (fade_up(t, t_out, 0.25) if t_out is not None else 0))
    serif(c, s, W / 2, KICK + (1 - fade_up(t, t0, 0.4)) * 20, 66, WHITE, alpha=k)


def sc_hook(c, t, a, b):
    def behind(c, t):
        big(c, t, C["fully"], "FULLY", WHITE, out_t=C["edited"] - 0.12)
        big(c, t, C["edited"], "EDITED.", NEON)
    footage(c, t, zoom=settle(t, a, 0.06, 1.0), dim=dim_ramp(t, C["fully"]), behind=behind)
    kicker(c, t, C["fully"], "this video is")


def sc_forever(c, t, a, b):
    def behind(c, t):
        big(c, t, C["forever"] - 0.05, "FOREVER.", NEON)
    footage(c, t, zoom=settle(t, a), dim=0.55, behind=behind)
    kicker(c, t, a + 0.02, "editing takes")


def sc_pain(c, t, a, b):
    dark_bg(c, t, "01")
    tag(c, t, a + 0.05, "THE OLD WAY", 90, 320)
    items = [("CUTTING", C["cutting"]), ("CAPTIONS", C["captions"]), ("MUSIC", C["music"]), ("ZOOMS", C["zooms"])]
    for i, (s, ts) in enumerate(items):
        y = 540 + i * 178
        kinetic(c, t, ts - 0.05, s, 90 + text_width(s, 168, BIG) / 2, y, 168, WHITE, per=0.025)
        # strike-through when "it eats your whole day"
        sk = ease_out_quart(prog(t, C["day"] + i * 0.12, 0.35))
        if sk > 0:
            c.drawRect(skia.Rect.MakeXYWH(80, y - 6, (text_width(s, 168, BIG) + 30) * sk, 14),
                       skia.Paint(Color=NEON))
    # hours counter
    hk = fade_up(t, C["cutting"], 0.3)
    hrs = clamp((t - C["cutting"]) / (C["day"] + 1.0 - C["cutting"])) * 9.75
    hh, mm = int(hrs), int((hrs % 1) * 60)
    mono(c, "TIME SPENT", W - 90, 320, 24, WHITE, align="right", alpha=0.6 * hk)
    text(c, f"{hh:02d}:{mm:02d}", W - 90, 400, size=96, font=BIG, fill=col(NEON, hk), align="right")
    k = fade_up(t, C["day"] + 0.35, 0.5)
    serif(c, "your whole day, gone.", W / 2, 1270, 92, WHITE, alpha=k)


def sc_built(c, t, a, b):
    def behind(c, t):
        big(c, t, C["my_own"] - 0.05, "MY OWN", WHITE, out_t=C["system"] - 0.15)
        big(c, t, C["system"] - 0.05, "SYSTEM.", NEON)
    footage(c, t, zoom=settle(t, a), dim=dim_ramp(t, C["my_own"]), behind=behind)
    kicker(c, t, a + 0.05, "so I built")


def sc_step1(c, t, a, b):
    rec = C["record"] - 0.05

    def behind(c, t):
        if t < rec:
            kinetic(c, t, a + 0.08, "01", W / 2, BAND, 360, WHITE, outline=True, out_t=rec - 0.2)
        big(c, t, rec, "RECORD.", NEON)
    footage(c, t, zoom=settle(t, a), dim=0.55, behind=behind)
    kicker(c, t, a + 0.05, "step one")
    pill(c, t, C["one_take"], "ONE TAKE", 90, 1170)
    pill(c, t, C["mistakes"], "MISTAKES ARE FINE", 90, 1265)


def sc_step2(c, t, a, b):
    dark_bg(c, t, "02")
    tag(c, t, a + 0.05, "STEP 02", 90, 320)
    kinetic(c, t, a + 0.2, "SAY IT.", 90 + text_width("SAY IT.", 200, BIG) / 2, 470, 200, WHITE)
    serif(c, "in plain words", 590, 505, 64, NEON, align="left", alpha=fade_up(t, C["normal"] - 0.05))
    # video window
    k = ease_out_expo(prog(t, a + 0.35, 0.7))
    x, y, w, h = 190, lerp(1300, 630, k), 700, 600
    if k > 0:
        rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), 36, 36)
        c.save()
        c.clipRRect(rr, True)
        bgimg, _ = layers(t, 0.0)
        c.save()
        place(c, t, 1.08, rect=(x, y, w, h))
        c.drawImage(bgimg, 0, 0, SAMP)
        c.restore()
        c.restore()
        c.drawRRect(rr, skia.Paint(Color=col(NEON, 0.9), AntiAlias=True, Style=skia.Paint.kStroke_Style,
                                   StrokeWidth=4))
        c.drawCircle(x + 40, y + 40, 9, skia.Paint(Color=skia.Color(255, 70, 60, 230 if (t * 2) % 1 < .6 else 60),
                                                   AntiAlias=True))
        mono(c, "LIVE", x + 60, y + 40, 22, WHITE)
    # prompt bar (glass)
    kb = ease_out_expo(prog(t, a + 0.6, 0.6))
    bx, by, bw, bh = 70, lerp(1500, 1160, kb), 940, 170
    if kb > 0:
        r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(bx, by, bw, bh), 40, 40)
        c.drawRRect(r, skia.Paint(Color=skia.Color(28, 28, 32, 235), AntiAlias=True))
        c.drawRRect(r, skia.Paint(Color=col(WHITE, 0.22), AntiAlias=True, Style=skia.Paint.kStroke_Style,
                                  StrokeWidth=2))
        mono(c, "MY SYSTEM", bx + 44, by + 38, 20, NEON)
        words = [wd for wd in WORDS if C["type_start"] - 0.05 <= wd["s"] <= C["type_end"]]
        shown = ""
        for wd in words:
            if t >= wd["s"]:
                frac = clamp((t - wd["s"]) / max(0.12, (wd["e"] - wd["s"]) * 0.8))
                tok = wd["w"].lower().replace(".", ",")
                shown += tok[:int(round(len(tok) * frac))]
                if frac >= 1:
                    shown += " "
        shown = shown.strip().rstrip(",")
        size = 31
        ty = by + 102
        if not shown:
            text(c, "describe the vibe...", bx + 44, ty, size=size, font="mono", fill=col(WHITE, 0.35), align="left")
        else:
            while text_width(shown, size, "mono") > bw - 200:
                shown = shown[1:]
            text(c, shown, bx + 44, ty, size=size, font="mono", fill=WHITE, align="left")
        if (t * 2.2) % 1 < 0.55 and t < C["send"]:
            cx_ = bx + 44 + (text_width(shown, size, "mono") + 6 if shown else 0)
            c.drawRect(skia.Rect.MakeXYWH(cx_, ty - 24, 4, 48), skia.Paint(Color=NEON))
        sk = prog(t, C["send"], 0.3)
        s_ = 1 - 0.15 * math.sin(math.pi * sk)
        c.save()
        c.translate(bx + bw - 85, by + bh / 2)
        c.scale(s_, s_)
        c.drawCircle(0, 0, 46, skia.Paint(Color=NEON if t >= C["send"] else col(WHITE, 0.15), AntiAlias=True))
        p = skia.Path()
        p.moveTo(0, 20)
        p.lineTo(0, -18)
        p.moveTo(-15, -4)
        p.lineTo(0, -19)
        p.lineTo(15, -4)
        c.drawPath(p, skia.Paint(Color=INK if t >= C["send"] else WHITE, AntiAlias=True,
                                 Style=skia.Paint.kStroke_Style, StrokeWidth=6, StrokeCap=skia.Paint.kRound_Cap))
        c.restore()


def sc_step3(c, t, a, b):
    z = settle(t, a)
    if t >= C["s3_cuts"]:
        z = 1.12
    if t >= C["s3_zooms"]:
        z = lerp(1.12, 1.32, ease_out_expo(prog(t, C["s3_zooms"], 0.3)))
    if t >= C["s3_zoom_back"]:
        z = lerp(1.32, 1.1, ease_in_out_cubic(prog(t, C["s3_zoom_back"], 0.25)))
    if t >= C["s3_music"]:
        z *= 1 + 0.045 * math.exp(-(t - C["s3_music"]) * 4) * abs(math.cos((t - C["s3_music"]) * 13))
    dim = dim_ramp(t, C["it_edits"], C["s3_cuts"] - 0.1)

    def behind(c, t):
        big(c, t, C["it_edits"] - 0.05, "IT EDITS.", NEON, out_t=C["s3_cuts"] - 0.15)
    footage(c, t, zoom=z, dim=dim, behind=behind if t < C["s3_cuts"] + 0.2 else None)
    kicker(c, t, a + 0.05, "step three", t_out=C["s3_cuts"] - 0.2)
    fk = 1 - prog(t, C["s3_cuts"], 0.14)
    if t >= C["s3_cuts"] and fk > 0:
        c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Color=skia.Color(255, 255, 255, int(170 * fk))))
    mk = t - C["s3_music"]
    if 0 <= mk < 0.8:
        env = math.sin(math.pi * mk / 0.8)
        for i in range(16):
            hh = (120 + 300 * (noise1(i * 2.7 + math.floor(mk * 18), 4) + 1) / 2) * env
            c.drawRoundRect(skia.Rect.MakeXYWH(36 + i * 64, 1500 - hh, 40, hh), 20, 20,
                            skia.Paint(Color=col(NEON, 0.9), AntiAlias=True))
    x = 64
    for i, (s, ts) in enumerate([("CUTS", C["s3_cuts"]), ("CAPTIONS", C["s3_captions"]), ("ZOOMS", C["s3_zooms"]),
                                 ("MUSIC", C["s3_music"])]):
        pill(c, t, ts, s, x, 330, small=True)
        x += text_width(s, 28, CAP, 0.04) + 100


def sc_nos(c, t, a, b):
    dark_bg(c, t)
    tag(c, t, a + 0.05, "WHAT YOU NEED", 90, 320)
    rows = [("EDITING APP", C["no1"], 640), ("EDITOR", C["no2"], 860), ("SKILLS", C["no3"], 1080)]
    for s, ts, y in rows:
        size = 170
        wn = text_width("NO ", size, BIG)
        ws = text_width(s, size, BIG)
        x0 = W / 2 - (wn + ws) / 2
        kinetic(c, t, ts - 0.06, "NO", x0 + text_width("NO", size, BIG) / 2, y, size, NEON, per=0.03)
        kinetic(c, t, ts, s, x0 + wn + ws / 2, y, size, WHITE, per=0.025)


def sc_talk(c, t, a, b):
    def behind(c, t):
        big(c, t, C["talk"] - 0.05, "TALK.", NEON, size=360)
    footage(c, t, zoom=settle(t, a), dim=dim_ramp(t, C["talk"]), behind=behind)
    kicker(c, t, a + 0.05, "if you can")


def sc_cover(c, t, a, b):
    k0 = ease_out_expo(prog(t, a, 0.6))

    def behind(c, t):
        # the masthead sits behind the head, like a real magazine cover
        kinetic(c, t, a + 0.05, "VIBE", W / 2, 560, 470, WHITE, per=0.05, tracking=0.02)
    footage(c, t, zoom=settle(t, a, 0.1, 0.8), dim=0.35, behind=behind)
    mono(c, "THE EDIT ISSUE", 90, 300, 24, WHITE, alpha=k0)
    mono(c, "NO. 01  /  2026", W - 90, 300, 24, WHITE, align="right", alpha=k0)
    c.drawRect(skia.Rect.MakeXYWH(90, 330, (W - 180) * k0, 2), skia.Paint(Color=col(WHITE, 0.6)))
    # cover lines
    k1 = ease_out_expo(prog(t, C["exactly"] - 0.1, 0.5))
    if k1 > 0:
        x = 90 - (1 - k1) * 60
        c.drawRect(skia.Rect.MakeXYWH(x, 860, 10, 196), skia.Paint(Color=col(NEON, k1)))
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
        c.drawCircle(0, 0, 112, skia.Paint(Color=NEON, AntiAlias=True))
        text(c, "EDITED", 0, -26, size=46, font=BIG, fill=INK)
        text(c, "BY MY SYSTEM", 0, 26, size=26, font="mono", fill=INK, tracking=0.04)
        c.restore()
    # barcode
    kb = fade_up(t, a + 0.3, 0.5)
    for i in range(34):
        w_ = 3 if noise1(i * 1.9, 5) > 0 else 6
        c.drawRect(skia.Rect.MakeXYWH(W - 300 + i * 6.2, 1452, w_ * 0.8, 44), skia.Paint(Color=col(WHITE, 0.85 * kb)))


def sc_open(c, t, a, b):
    def behind(c, t):
        big(c, t, C["creators"] - 0.08, "CREATORS.", NEON)
    footage(c, t, zoom=settle(t, a), dim=dim_ramp(t, C["few"] - 0.1), behind=behind)
    kicker(c, t, C["few"] - 0.5, "opening it up to a few")


def sc_cta(c, t, a, b):
    dim = max(dim_ramp(t, C["how"], level=0.3), dim_ramp(t, C["comment"], level=0.8))

    def behind(c, t):
        big(c, t, C["cta_system"] - 0.08, "SYSTEM", NEON, size=340)
    footage(c, t, zoom=settle(t, a), dim=dim, behind=behind)
    kicker(c, t, C["how"] - 0.2, "want to see how it works?", t_out=C["comment"] - 0.25)
    kicker(c, t, C["comment"] - 0.05, "comment")
    kt = ease_out_back(prog(t, C["tap"] - 0.05, 0.4))
    if kt > 0.01:
        s = "TAP THE LINK BELOW"
        size = 40
        w = text_width(s, size, CAP, 0.06) + 140
        c.save()
        c.translate(W / 2, 1290)
        c.scale(kt, kt)
        r = skia.Rect.MakeXYWH(-w / 2, -44, w, 88)
        c.drawRRect(skia.RRect.MakeRectXY(r, 44, 44), skia.Paint(Color=WHITE, AntiAlias=True))
        text(c, s, -w / 2 + 50, 0, size=size, font=CAP, fill=INK, align="left", tracking=0.06)
        bob = math.sin((t - C["tap"]) * 7) * 5
        p = skia.Path()
        p.moveTo(w / 2 - 70, -10 + bob)
        p.lineTo(w / 2 - 55, 6 + bob)
        p.lineTo(w / 2 - 40, -10 + bob)
        c.drawPath(p, skia.Paint(Color=INK, AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=6,
                                 StrokeCap=skia.Paint.kRound_Cap))
        c.restore()
    ke = fade_up(t, C["tap"] + 0.7, 0.5)
    mono(c, "THE VIBE EDITING SYSTEM", W / 2, 1440, 26, WHITE, align="center", alpha=ke, tracking=0.2)


FN = dict(hook=sc_hook, forever=sc_forever, pain=sc_pain, built=sc_built, step1=sc_step1, step2=sc_step2,
          step3=sc_step3, nos=sc_nos, talk=sc_talk, cover=sc_cover, open=sc_open, cta=sc_cta)


# ------------------------------------------------------------------ persistent layers
def chunks():
    out, cur = [], []
    for wd in WORDS:
        cur.append(wd)
        txt = " ".join(x["w"] for x in cur)
        if wd["w"][-1] in ".,:;!?" or len(cur) >= 3 or len(txt) >= 14:
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
        if s0 - 0.03 <= t < min(nxt, ch[-1]["e"] + 0.5):
            break
    else:
        return
    size = 62
    ws = [x["w"].upper().strip(".,:;!?") for x in ch]
    sp = text_width(" ", size, CAP)
    widths = [text_width(s, size, CAP, 0.01) for s in ws]
    total = sum(widths) + sp * (len(ws) - 1)
    k = ease_out_cubic(prog(t, s0 - 0.03, 0.16))
    boost = 1.0
    if C["s3_captions"] - 0.05 <= t < C["s3_captions"] + 0.7:
        boost = lerp(1.0, 1.4, ease_out_back(prog(t, C["s3_captions"] - 0.05, 0.25)))
    c.save()
    c.translate(W / 2, 1400 + (1 - k) * 24)
    c.scale(boost, boost)
    x = -total / 2
    shadow = skia.Paint(Color=skia.Color(0, 0, 0, 150), AntiAlias=True)
    shadow.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14))
    c.drawRoundRect(skia.Rect.MakeXYWH(-total / 2 - 30, -50, total + 60, 100), 50, 50, shadow)
    for wd, s, ww in zip(ch, ws, widths):
        active = wd["s"] - 0.03 <= t
        now = active and (t < wd["e"] + 0.12 or wd is ch[-1])
        fillc = NEON if now else (WHITE if active else col(WHITE, 0.45))
        text(c, s, x, 0, size=size, font=CAP, fill=col(fillc, k * skia.ColorGetA(fillc) / 255), align="left",
             tracking=0.01)
        x += ww + sp
    c.restore()


def hud(c, t):
    p = skia.Paint(Color=col(WHITE, 0.55), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3)
    m, L = 44, 56
    for (x, y, sx, sy) in [(m, m + 200, 1, 1), (W - m, m + 200, -1, 1), (m, H - m - 260, 1, -1),
                           (W - m, H - m - 260, -1, -1)]:
        path = skia.Path()
        path.moveTo(x, y + sy * L)
        path.lineTo(x, y)
        path.lineTo(x + sx * L, y)
        c.drawPath(path, p)
    f = int(t * FPS)
    tc = f"{f // (FPS * 60):02d}:{(f // FPS) % 60:02d}:{f % FPS:02d}"
    mono(c, tc, W - 90, 1585, 20, WHITE, align="right", alpha=0.7, tracking=0.08)
    c.drawCircle(W - 90 - text_width(tc, 20, "mono", 0.08) - 22, 1585, 7,
                 skia.Paint(Color=col(NEON, 0.6 + 0.4 * math.cos(t * 5)), AntiAlias=True))


def _grain_images():
    rng = np.random.default_rng(3)
    ims = []
    for _ in range(6):
        n = rng.normal(128, 40, (H // 2, W // 2)).clip(0, 255).astype(np.uint8)
        rgba = np.dstack([n, n, n, np.full_like(n, 22)])
        ims.append(skia.Image.fromarray(np.ascontiguousarray(rgba), colorType=skia.kRGBA_8888_ColorType))
    return ims


GRAIN = _grain_images()
VIG = skia.Paint(Shader=skia.GradientShader.MakeRadial(
    skia.Point(W / 2, H * 0.45), H * 0.72, [skia.Color(0, 0, 0, 0), skia.Color(0, 0, 0, 0), skia.Color(0, 0, 0, 120)],
    [0.0, 0.55, 1.0]))


def finish(c, t):
    c.drawRect(skia.Rect.MakeWH(W, H), VIG)
    g = GRAIN[int(t * 24) % len(GRAIN)]
    p = skia.Paint()
    p.setBlendMode(skia.BlendMode.kOverlay)
    c.drawImageRect(g, skia.Rect.MakeWH(W, H), skia.SamplingOptions(), p)


# ------------------------------------------------------------------ frame + transitions
def scene_at(t):
    for i, (a, b, *_ ) in enumerate(TL.SCENES):
        if a <= t < b:
            return i
    return len(TL.SCENES) - 1


def wipe(c, t, T):
    """an ink panel with a neon leading edge sweeps across; the cut happens under it."""
    k = prog(t, T - TL.WIPE / 2, TL.WIPE)
    if not 0 < k < 1:
        return
    e = ease_in_out_cubic(k)
    x = lerp(-W * 1.3, W * 1.3, e)
    c.save()
    c.translate(x, 0)
    c.skew(-0.18, 0)
    c.translate(0, 0)
    c.drawRect(skia.Rect.MakeXYWH(-W * 0.65 + 200, -100, W * 1.3, H + 200), skia.Paint(Color=INK))
    c.drawRect(skia.Rect.MakeXYWH(W * 0.65 + 200, -100, 22, H + 200), skia.Paint(Color=NEON))
    c.restore()


def draw(c, t):
    i = scene_at(t)
    a, b, name, kind = TL.SCENES[i]
    FN[name](c, t, a, b)
    if name not in ("cover",):
        captions(c, t)
    else:
        captions(c, t)
    hud(c, t)
    for (a2, *_ ) in TL.SCENES[1:]:
        if abs(t - a2) < TL.WIPE:
            wipe(c, t, a2)
    finish(c, t)


# ------------------------------------------------------------------ prep / audio / compare
def prep():
    import subprocess
    import cv2
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", "work/matte/cut_alpha.mp4", "-vf", f"scale={SW}:{SH}",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    m = np.frombuffer(raw, np.uint8).reshape(-1, SH, SW)
    n = min(len(m), NF)
    out = np.memmap("work/matte.u8", np.uint8, "w+", shape=(NF, SH, SW))
    tr = []
    for i in range(NF):
        mm = m[min(i, n - 1)]
        mm = cv2.GaussianBlur(mm, (5, 5), 0)
        out[i] = mm
        cols = mm[:, 160:560] > 128
        rows = np.nonzero(cols.any(1))[0]
        top = rows[0] if len(rows) else 380
        band = mm[top:top + 200] > 128
        xs = np.nonzero(band.any(0))[0]
        xc = (xs[0] + xs[-1]) / 2 if len(xs) else 360
        tr.append((xc, top + 230))
    out.flush()
    tr = np.array(tr, float)
    k = np.ones(21) / 21
    sm = np.stack([np.convolve(np.pad(tr[:, j], 10, mode="edge"), k, "valid") for j in range(2)], 1)
    json.dump(sm.round(1).tolist(), open("work/track.json", "w"))
    print("prep done", NF, n, sm.min(0), sm.max(0))


def build_audio():
    import audio_kit as ak
    ak.voice_chain("work/cut.mp4", "work/voice.wav", denoise=True)
    sr = ak.SR
    n = int(TL.DURATION * sr)
    bed = ak.music_bed(TL.MOOD, seconds=TL.DURATION + 2, seed=TL.SEED)[:n]
    if len(bed) < n:
        bed = np.pad(bed, ((0, n - len(bed)), (0, 0)))
    tt = np.arange(n) / sr
    env = np.where(tt < C["s3_music"], 0.6, 1.0)
    env = np.convolve(env, np.ones(800) / 800, mode="same")
    env *= np.clip((TL.DURATION - tt) / 1.4, 0, 1)
    ak.write_wav("work/music.wav", (bed * env[:, None]).astype(np.float32))
    sfx = []
    for (a2, *_ ) in TL.SCENES[1:]:
        sfx.append({"t": a2 - 0.2, "kind": "whoosh", "gain_db": -13, "dur": 0.4})
    for key in ("fully", "edited", "forever", "my_own", "system", "record", "it_edits", "talk", "few", "creators",
                "cta_system"):
        sfx.append({"t": C[key] - 0.03, "kind": "impact", "gain_db": -15})
    for key in ("cutting", "captions", "music", "zooms", "one_take", "mistakes", "exactly", "every", "page", "tap"):
        sfx.append({"t": C[key], "kind": "click", "gain_db": -12})
    sfx += [
        {"t": C["day"], "kind": "glitch", "gain_db": -16},
        {"t": C["type_start"], "kind": "typing", "gain_db": -15, "dur": C["type_end"] - C["type_start"]},
        {"t": C["send"], "kind": "pop", "gain_db": -10},
        {"t": C["s3_cuts"] - 0.02, "kind": "shutter", "gain_db": -9},
        {"t": C["s3_zooms"] - 0.05, "kind": "whoosh", "gain_db": -12, "dur": 0.3},
        {"t": C["s3_music"] - 1.2, "kind": "riser", "gain_db": -17, "dur": 1.2},
        {"t": C["s3_music"] - 0.02, "kind": "bass_drop", "gain_db": -7},
        {"t": C["no1"] - 0.03, "kind": "impact", "gain_db": -11}, {"t": C["no2"] - 0.03, "kind": "impact", "gain_db": -11},
        {"t": C["no3"] - 0.03, "kind": "impact", "gain_db": -11},
        {"t": C["tap"] + 0.7, "kind": "sparkle", "gain_db": -15},
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
        S.render(draw, "out/pitch_picture.mp4", crf=15)
