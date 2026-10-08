"""scene: "AI edited this" Reel. Paper-cut editorial theme, every frame a pure function of time t.

    python3 scene.py stills 1.0 5.0 12.0     # check frames -> out/stills/
    python3 scene.py audio                   # voice + music + sfx -> work/mix.wav
    python3 scene.py render                  # final -> out/ai_edited_reel.mp4
"""

import json
import math
import sys
from pathlib import Path

import numpy as np
import skia

sys.path.insert(0, str(Path(__file__).resolve().parent / "vibe"))
from motion_kit import (Stage, clamp, ease_in_cubic, ease_in_out_cubic, ease_out_back, ease_out_cubic,  # noqa: E402
                        ease_out_expo, lerp, noise1, prog, rgb, text, text_width, typeface)

import timeline as TL  # noqa: E402

W, H, FPS = TL.W, TL.H, TL.FPS
C = TL.CUE
S = Stage(W, H, fps=FPS, duration=TL.DURATION)
B = S.brand
INK, PAPER, WHITE = rgb(B, "ink"), rgb(B, "paper"), rgb(B, "white")
LIME, PERI, BLUSH, ICE, ORANGE = rgb(B, "lime"), rgb(B, "periwinkle"), rgb(B, "blush"), rgb(B, "ice"), rgb(B, "orange")
SERIF = "InstrumentSerif-Italic.ttf"

# ------------------------------------------------------------------ footage (graded, stabilised, cut)
SW, SH = 720, 1280
FR = np.memmap("work/frames.rgba", np.uint8, "r").reshape(-1, SH, SW, 4)
NF = len(FR)
TRACK = np.array(json.load(open("work/face_track.json")))      # sunglasses centre per frame
WORDS = json.load(open("work/words_cut.json"))


def frame_index(t):
    return int(clamp(min(t, TL.SPEECH_END) * FPS, 0, NF - 1))


def video_img(t):
    return skia.Image.fromarray(np.ascontiguousarray(FR[frame_index(t)]), colorType=skia.kRGBA_8888_ColorType)


def face(t):
    x, y = TRACK[frame_index(t)]
    return float(x), float(y) + 70          # glasses -> face centre


def draw_video(c, t, dx, dy, dw, dh, zoom=1.0, fy_bias=0.0):
    """cover-fit the footage into the dest rect, centred on the face, zoomed."""
    fx, fy = face(t)
    fy += fy_bias
    a = dw / dh
    sh = min(SH, SW / a) / zoom
    sw = sh * a
    if zoom <= 1.0001 and abs(a - SW / SH) < 0.01:
        sx, sy = 0, 0
    else:
        sx = clamp(fx - sw / 2, 0, SW - sw)
        sy = clamp(fy - sh * 0.45, 0, SH - sh)
    c.drawImageRect(video_img(t), skia.Rect.MakeXYWH(sx, sy, sw, sh), skia.Rect.MakeXYWH(dx, dy, dw, dh),
                    skia.SamplingOptions(skia.CubicResampler.CatmullRom()), skia.Paint(AntiAlias=True))


# ------------------------------------------------------------------ paper textures (made once)
def make_paper(hex_col, seed):
    from scipy.ndimage import gaussian_filter
    rng = np.random.default_rng(seed)
    r, g, b = (int(hex_col[i:i + 2], 16) for i in (1, 3, 5))
    base = np.empty((H, W, 3), np.float32)
    base[..., 0], base[..., 1], base[..., 2] = r, g, b
    blot = gaussian_filter(rng.normal(0, 1, (H // 4, W // 4)), 6)
    blot = np.kron(blot / (np.abs(blot).max() + 1e-6), np.ones((4, 4)))[:H, :W]
    fine = rng.normal(0, 1, (H, W))
    fib = gaussian_filter(rng.normal(0, 1, (H, W)), (0.6, 5.0))
    shade = 5.0 * blot + 2.2 * fine + 9.0 * fib / (np.abs(fib).max() + 1e-6)
    arr = np.clip(base + shade[..., None], 0, 255).astype(np.uint8)
    rgba = np.dstack([arr, np.full((H, W), 255, np.uint8)])
    return skia.Image.fromarray(np.ascontiguousarray(rgba), colorType=skia.kRGBA_8888_ColorType)


PAPER_IMG = make_paper(B["colors"]["paper"], 1)
PERI_IMG = make_paper(B["colors"]["periwinkle"], 2)


def bg(c, img):
    c.drawImage(img, 0, 0)


# ------------------------------------------------------------------ helpers
def jit(t, seed, amt=3.0):
    """stop-motion wobble: changes 12x a second like hand-moved paper."""
    k = math.floor(t * 12)
    return noise1(k * 1.7, seed) * amt, noise1(k * 1.3, seed + 50) * amt


def n01(x, seed=0):
    return (noise1(x, seed) + 1) / 2


def rot_about(c, deg, cx, cy):
    c.translate(cx, cy)
    c.rotate(deg)
    c.translate(-cx, -cy)


def paper_shadow(c, rect, r=16, blur=16, dy=10, alpha=0.22):
    p = skia.Paint(Color=skia.Color(0, 0, 0, int(255 * alpha)), AntiAlias=True)
    p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    rr = skia.Rect.MakeXYWH(rect.x(), rect.y() + dy, rect.width(), rect.height())
    c.drawRRect(skia.RRect.MakeRectXY(rr, r, r), p)


def fill(col):
    return skia.Paint(Color=col, AntiAlias=True)


def stroke(col, w):
    return skia.Paint(Color=col, AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=w,
                      StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join)


def label(c, s, cx, cy, size, font="display", bg_col=WHITE, fg_col=INK, rot=0.0, scale=1.0, padx=34, pady=20,
          radius=12, shadow_on=True, alpha=1.0, tracking=0.0):
    """a paper label: text on a cut-out paper rectangle."""
    if scale <= 0.01 or alpha <= 0:
        return
    tw = text_width(s, size, font, tracking)
    w, h = tw + 2 * padx, size + 2 * pady
    c.save()
    c.translate(cx, cy)
    c.rotate(rot)
    c.scale(scale, scale)
    r = skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h)
    if shadow_on:
        paper_shadow(c, r, radius, 10, 7, 0.22 * alpha)
    p = fill(bg_col)
    p.setAlphaf(alpha)
    c.drawRRect(skia.RRect.MakeRectXY(r, radius, radius), p)
    text(c, s, 0, 0, size=size, font=font, fill=fg_col, alpha=alpha, tracking=tracking)
    c.restore()


def check(c, cx, cy, r, k=1.0, col=LIME):
    if k <= 0:
        return
    c.drawCircle(cx, cy, r * ease_out_back(clamp(k * 1.6)), fill(INK))
    path = skia.Path()
    pts = [(cx - r * 0.45, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.38), (cx + r * 0.5, cy - r * 0.32)]
    kk = clamp(k * 1.6 - 0.4)
    path.moveTo(*pts[0])
    if kk < 0.5:
        path.lineTo(lerp(pts[0][0], pts[1][0], kk * 2), lerp(pts[0][1], pts[1][1], kk * 2))
    else:
        path.lineTo(*pts[1])
        path.lineTo(lerp(pts[1][0], pts[2][0], (kk - 0.5) * 2), lerp(pts[1][1], pts[2][1], (kk - 0.5) * 2))
    if kk > 0:
        c.drawPath(path, stroke(col, r * 0.22))


def pop(t, t0, dur=0.3):
    return ease_out_back(prog(t, t0, dur)) if t >= t0 else 0.0


def tape(c, cx, cy, rot, w=150, h=46):
    c.save()
    c.translate(cx, cy)
    c.rotate(rot)
    c.drawRect(skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h), fill(skia.Color(255, 255, 240, 150)))
    c.restore()


def card(c, t, x, y, w, h, rot=0.0, zoom=1.15, border=16, radius=22):
    """the footage as a cut-out photo card with a white paper border, tape on top."""
    cx, cy = x + w / 2, y + h / 2
    c.save()
    rot_about(c, rot, cx, cy)
    outer = skia.Rect.MakeXYWH(x - border, y - border, w + 2 * border, h + 2 * border)
    paper_shadow(c, outer, radius + border, 24, 16, 0.28)
    c.drawRRect(skia.RRect.MakeRectXY(outer, radius + border, radius + border), fill(WHITE))
    c.save()
    c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), radius, radius), True)
    draw_video(c, t, x, y, w, h, zoom=zoom)
    c.restore()
    c.restore()
    tape(c, x + 40, y - 6, -28 + rot)
    tape(c, x + w - 40, y - 6, 26 + rot)


def face_circle(c, t, cx, cy, r, k=1.0, ring=LIME):
    if k <= 0.01:
        return
    c.save()
    c.translate(cx, cy)
    c.scale(k, k)
    c.translate(-cx, -cy)
    sh = skia.Paint(Color=skia.Color(0, 0, 0, 70), AntiAlias=True)
    sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 18))
    c.drawCircle(cx, cy + 12, r + 12, sh)
    c.drawCircle(cx, cy, r + 12, fill(INK))
    c.drawCircle(cx, cy, r + 6, fill(ring))
    path = skia.Path()
    path.addCircle(cx, cy, r)
    c.save()
    c.clipPath(path, skia.ClipOp.kIntersect, True)
    # square crop around the face
    fx, fy = face(t)
    side = 560
    sx, sy = clamp(fx - side / 2, 0, SW - side), clamp(fy - side * 0.48, 0, SH - side)
    c.drawImageRect(video_img(t), skia.Rect.MakeXYWH(sx, sy, side, side),
                    skia.Rect.MakeXYWH(cx - r, cy - r, 2 * r, 2 * r),
                    skia.SamplingOptions(skia.CubicResampler.CatmullRom()), skia.Paint(AntiAlias=True))
    c.restore()
    c.restore()


def headline(c, t, t0, kicker, big, y, big_size=104, hi=None, color=INK, kicker_size=78):
    """magazine headline: italic serif kicker + heavy display line, optional lime marker behind the big line."""
    k1 = ease_out_cubic(prog(t, t0, 0.35))
    k2 = ease_out_back(prog(t, t0 + 0.12, 0.4))
    jx, jy = jit(t, 7, 1.5)
    if kicker:
        text(c, kicker, W / 2 + jx, y + (1 - k1) * 30, size=kicker_size, font=SERIF, fill=color, alpha=k1)
    if big and k2 > 0:
        by = y + kicker_size * 0.5 + big_size * 0.72
        bw = text_width(big, big_size, "display")
        c.save()
        c.translate(W / 2, by)
        c.scale(lerp(0.7, 1, k2), lerp(0.7, 1, k2))
        if hi is not None:
            hk = ease_out_cubic(prog(t, t0 + 0.3, 0.35))
            r = skia.Rect.MakeXYWH(-bw / 2 - 22, -big_size * 0.42, (bw + 44) * hk, big_size * 0.95)
            c.save()
            c.rotate(-1.2)
            c.drawRect(r, fill(hi))
            c.restore()
        text(c, big, 0, 0, size=big_size, font="display", fill=color, alpha=clamp(k2 * 2))
        c.restore()


# ------------------------------------------------------------------ scenes
def sc_hook(c, t, t0, t1):
    z = lerp(1.0, 1.1, ease_in_out_cubic(prog(t, t0, t1 - t0)))
    # little impact shake when the stamp lands
    sk = max(0.0, 1 - (t - C["stamp"]) / 0.35) if t >= C["stamp"] else 0.0
    ox = math.sin(t * 90) * 10 * sk
    oy = math.cos(t * 77) * 8 * sk
    draw_video(c, t, -20 + ox, -20 + oy, W + 40, H + 40, zoom=z)
    # the stamp
    if C["stamp"] <= t < C["stamp_fly"] + 0.4:
        k = ease_out_back(prog(t, C["stamp"], 0.2))
        fly = ease_in_out_cubic(prog(t, C["stamp_fly"], 0.4))
        sc = lerp(2.2, 1.0, k) * lerp(1.0, 0.36, fly)
        cx, cy = lerp(540, BADGE_X, fly), lerp(600, BADGE_Y, fly)
        stamp(c, cx, cy, sc, lerp(-7, 0, fly), alpha=clamp(k * 3))


def stamp(c, cx, cy, sc, rot, alpha=1.0):
    s = "AI EDITED THIS"
    size = 92
    tw = text_width(s, size, "display")
    w, h = tw + 80, size + 64
    c.save()
    c.translate(cx, cy)
    c.rotate(rot)
    c.scale(sc, sc)
    r = skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h)
    paper_shadow(c, r, 18, 20, 12, 0.3 * alpha)
    p = fill(LIME)
    p.setAlphaf(alpha)
    c.drawRRect(skia.RRect.MakeRectXY(r, 18, 18), p)
    ps = stroke(INK, 8)
    ps.setAlphaf(alpha)
    c.drawRRect(skia.RRect.MakeRectXY(r.makeInset(14, 14), 10, 10), ps)
    text(c, s, 0, 0, size=size, font="display", fill=INK, alpha=alpha)
    c.restore()


def sc_pain(c, t, t0, t1):
    bg(c, PAPER_IMG)
    text(c, "the old way", W / 2, 390, size=70, font=SERIF, fill=INK, alpha=ease_out_cubic(prog(t, t0 + 0.05, 0.3)))
    for i, (word, tw_) in enumerate([("EDITING", C["editing"]), ("TAKES", C["takes"]), ("FOREVER.", C["forever"])]):
        k = pop(t, tw_ - 0.04, 0.28)
        if k <= 0:
            continue
        jx, jy = jit(t, 20 + i, 2)
        col = ORANGE if i == 2 else INK
        c.save()
        cx, cy = W / 2 + jx, 500 + i * 112 + jy
        c.translate(cx, cy)
        c.rotate((-2, 1.5, -1)[i])
        c.scale(k, k)
        text(c, word, 0, 0, size=104, font="display", fill=col)
        c.restore()
    # paper timeline panel
    kp = ease_out_cubic(prog(t, C["cutting"] - 0.3, 0.35))
    if kp > 0:
        day_k = ease_in_out_cubic(prog(t, C["day"], 0.35))
        px, py, pw, ph = 80, lerp(1500, 840, kp), 920, 460
        c.save()
        rot_about(c, lerp(0, -3, day_k), W / 2, py + ph / 2)
        r = skia.Rect.MakeXYWH(px, py, pw, ph)
        paper_shadow(c, r, 20, 22, 14, 0.25)
        c.drawRRect(skia.RRect.MakeRectXY(r, 20, 20), fill(WHITE))
        c.drawRRect(skia.RRect.MakeRectXY(r, 20, 20), stroke(INK, 5))
        # playhead ruler
        for i in range(19):
            x = px + 150 + i * 40
            c.drawLine(x, py + 30, x, py + (48 if i % 4 == 0 else 40), stroke(INK, 3))
        tracks = [("CUT", C["cutting"], PERI), ("TXT", C["captions"], LIME), ("SFX", C["music"], ICE),
                  ("ZOOM", C["zooms"], BLUSH)]
        for i, (name, ts, col) in enumerate(tracks):
            ty = py + 76 + i * 92
            text(c, name, px + 70, ty + 38, size=30, font="mono", fill=INK)
            c.drawLine(px + 130, ty + 82, px + pw - 30, ty + 82, stroke(skia.Color(0, 0, 0, 40), 2))
            n = 7 if i != 3 else 5
            for j in range(n):
                kk = ease_out_back(prog(t, ts + j * 0.045, 0.22))
                if kk <= 0:
                    continue
                bw = (pw - 180) / n
                bx = px + 140 + j * bw
                if i == 3:          # zoom keyframes as diamonds
                    cx, cy = bx + bw / 2, ty + 40
                    c.save()
                    c.translate(cx, cy)
                    c.rotate(45)
                    c.scale(kk, kk)
                    c.drawRect(skia.Rect.MakeXYWH(-18, -18, 36, 36), fill(col))
                    c.drawRect(skia.Rect.MakeXYWH(-18, -18, 36, 36), stroke(INK, 4))
                    c.restore()
                    continue
                rr = skia.Rect.MakeXYWH(bx + 4, ty + 12 + (1 - kk) * 40, bw - 8, 58)
                c.drawRRect(skia.RRect.MakeRectXY(rr, 8, 8), fill(col))
                c.drawRRect(skia.RRect.MakeRectXY(rr, 8, 8), stroke(INK, 4))
                if i == 2:          # waveform on the sound track
                    for q in range(6):
                        hh = 8 + 18 * n01(j * 6 + q + 0.5, 3)
                        xx = rr.x() + 14 + q * (rr.width() - 28) / 5
                        c.drawLine(xx, rr.centerY() - hh, xx, rr.centerY() + hh, stroke(INK, 4))
        c.restore()
        # "it eats your whole day": a clock spins over the timeline
        kc = ease_out_back(prog(t, C["day"], 0.35))
        if kc > 0:
            cx, cy, R = W / 2, py + ph / 2 - 10, 170
            c.save()
            c.translate(cx, cy)
            c.scale(kc, kc)
            c.drawCircle(0, 14, R + 10, fill(skia.Color(0, 0, 0, 60)))
            c.drawCircle(0, 0, R, fill(PAPER))
            c.drawCircle(0, 0, R, stroke(INK, 10))
            for i in range(12):
                a = i * math.pi / 6
                c.drawLine(math.sin(a) * (R - 34), -math.cos(a) * (R - 34), math.sin(a) * (R - 18),
                           -math.cos(a) * (R - 18), stroke(INK, 7))
            spin = (t - C["day"]) * 5.5
            c.drawLine(0, 0, math.sin(spin) * (R - 50), -math.cos(spin) * (R - 50), stroke(ORANGE, 12))
            c.drawLine(0, 0, math.sin(spin / 12) * (R - 90), -math.cos(spin / 12) * (R - 90), stroke(INK, 14))
            c.drawCircle(0, 0, 14, fill(INK))
            c.restore()
            hrs = int(clamp((t - C["day"]) / 1.3) * 14) + 9
            lab = f"{(hrs - 1) % 12 + 1} {'AM' if hrs < 12 else 'PM'}"
            label(c, lab, cx + 220, cy - 150, 44, font="mono", bg_col=INK, fg_col=LIME, rot=6, scale=kc)
            label(c, "WHOLE DAY: GONE", cx, cy + 205, 50, bg_col=ORANGE, fg_col=WHITE, rot=-3,
                  scale=pop(t, C["day"] + 0.75, 0.3))


def sc_built(c, t, t0, t1):
    bg(c, PERI_IMG)
    headline(c, t, t0 + 0.12, "so I built my own", "EDITING SYSTEM", 390, big_size=82, hi=LIME)
    z = lerp(1.18, 1.26, prog(t, t0, t1 - t0))
    card(c, t, 150, 680, 780, 640, rot=-2.0, zoom=z)


def phone(c, t, x, y, w, h, t_rec):
    r = skia.Rect.MakeXYWH(x, y, w, h)
    paper_shadow(c, r, 46, 24, 16, 0.3)
    c.drawRRect(skia.RRect.MakeRectXY(r, 46, 46), fill(INK))
    scr = skia.Rect.MakeXYWH(x + 16, y + 16, w - 32, h - 32)
    c.save()
    c.clipRRect(skia.RRect.MakeRectXY(scr, 32, 32), True)
    draw_video(c, t, scr.x(), scr.y(), scr.width(), scr.height(), zoom=1.05)
    c.restore()
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x + w / 2 - 50, y + 26, 100, 26), 13, 13), fill(INK))
    # REC + timer
    blink = 1.0 if (t * 2) % 1 < 0.6 else 0.25
    rr = skia.Rect.MakeXYWH(x + 34, y + 70, 190, 52)
    c.drawRRect(skia.RRect.MakeRectXY(rr, 26, 26), fill(skia.Color(0, 0, 0, 140)))
    c.drawCircle(x + 62, y + 96, 11, fill(skia.Color(255, 60, 50, int(255 * blink))))
    secs = max(0.0, t - t_rec)
    text(c, f"0:{int(secs):02d}", x + 140, y + 96, size=30, font="mono", fill=WHITE)


def step_head(c, t, t0, num, word):
    k = ease_out_back(prog(t, t0 + 0.05, 0.4))
    jx, jy = jit(t, 31, 1.5)
    c.save()
    c.translate(90 + jx, 480 + jy)
    c.scale(k, k)
    text(c, num, 0, 0, size=210, font="display", fill=PAPER, align="left", stroke=10, stroke_col=INK)
    c.restore()
    label(c, word, 90 + text_width(word, 76, "display") / 2 + 34, 660, 76, bg_col=INK, fg_col=LIME, rot=-2,
          scale=ease_out_back(prog(t, t0 + 0.2, 0.35)))


def chip(c, t, t_on, s, x, y, rot=0.0):
    k = ease_out_back(prog(t, t_on - 0.03, 0.3))
    if k <= 0:
        return
    size = 46
    w = text_width(s, size, "display") + 150
    c.save()
    c.translate(x + w / 2, y)
    c.rotate(rot)
    c.scale(k, k)
    r = skia.Rect.MakeXYWH(-w / 2, -50, w, 100)
    paper_shadow(c, r, 50, 14, 8, 0.22)
    c.drawRRect(skia.RRect.MakeRectXY(r, 50, 50), fill(WHITE))
    c.drawRRect(skia.RRect.MakeRectXY(r, 50, 50), stroke(INK, 5))
    check(c, -w / 2 + 52, 0, 30, clamp((t - t_on) / 0.35))
    text(c, s, -w / 2 + 96, 0, size=size, font="display", fill=INK, align="left")
    c.restore()


def sc_step1(c, t, t0, t1):
    bg(c, PAPER_IMG)
    step_head(c, t, t0, "01", "RECORD")
    kp = ease_out_cubic(prog(t, t0 + 0.25, 0.45))
    jx, jy = jit(t, 41, 2)
    c.save()
    rot_about(c, -4, 270, 1000)
    phone(c, t, 110 + jx, lerp(1700, 770, kp) + jy, 310, 550, t0)
    c.restore()
    chip(c, t, C["one_take"], "ONE TAKE", 490, 920, rot=-2)
    chip(c, t, C["mistakes"], "MISTAKES OK", 440, 1070, rot=2)
    text(c, "on my phone", 700, 1210, size=64, font=SERIF, fill=INK, alpha=ease_out_cubic(prog(t, 12.4, 0.3)))


def sc_step2(c, t, t0, t1):
    bg(c, PAPER_IMG)
    step_head(c, t, t0, "02", "SAY IT")
    k = ease_out_cubic(prog(t, t0 + 0.3, 0.45))
    x, y, w, h = 80, lerp(1700, 790, k), 920, 450
    jx, jy = jit(t, 51, 1.5)
    x += jx
    y += jy
    r = skia.Rect.MakeXYWH(x, y, w, h)
    c.drawRRect(skia.RRect.MakeRectXY(r.makeOffset(14, 14), 26, 26), fill(INK))      # hard paper shadow
    c.drawRRect(skia.RRect.MakeRectXY(r, 26, 26), fill(WHITE))
    c.drawRRect(skia.RRect.MakeRectXY(r, 26, 26), stroke(INK, 6))
    c.drawLine(x, y + 84, x + w, y + 84, stroke(INK, 5))
    for i, col in enumerate((ORANGE, LIME, PERI)):
        c.drawCircle(x + 50 + i * 44, y + 42, 14, fill(col))
        c.drawCircle(x + 50 + i * 44, y + 42, 14, stroke(INK, 3))
    text(c, "my editing system", x + w - 40, y + 44, size=30, font="mono", fill=INK, align="right")
    # typed prompt, synced to the spoken words
    full = "make it fun, big captions, upbeat music"
    words = [wd for wd in WORDS if C["type_start"] - 0.05 <= wd["s"] <= C["type_end"]][1:]   # skip "Like"
    shown = ""
    for wd in words:
        if t >= wd["s"]:
            frac = clamp((t - wd["s"]) / max(0.12, (wd["e"] - wd["s"]) * 0.8))
            token = wd["w"].lower()
            shown += token[:int(round(len(token) * frac))]
            if frac >= 1:
                shown += " "
    shown = shown.rstrip() if t > C["type_end"] + 0.2 else shown
    size = 54
    tx, ty = x + 50, y + 170
    if not shown:
        text(c, "tell it the vibe...", tx + 90, ty, size=size, font="mono", fill=skia.Color(0, 0, 0, 90), align="left")
    text(c, ">", tx, ty, size=size, font="mono", fill=ORANGE, align="left")
    lines, cur = [], ""
    for wd in shown.split(" "):
        trial = (cur + " " + wd).strip() if cur else wd
        if text_width(trial, size, "mono") > w - 160 and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = trial
    lines.append(cur)
    for i, ln in enumerate(lines):
        text(c, ln, tx + 50, ty + i * 78, size=size, font="mono", fill=INK, align="left")
    if (t * 2.2) % 1 < 0.55 and t < C["send"]:
        last = lines[-1]
        cxp = tx + 50 + text_width(last, size, "mono") + 8
        c.drawRect(skia.Rect.MakeXYWH(cxp, ty + (len(lines) - 1) * 78 - 30, 26, 60), fill(INK))
    # send button
    kb = prog(t, C["send"], 0.25)
    press = 1 - 0.12 * math.sin(math.pi * kb)
    bx, by = x + w - 190, y + h - 80
    c.save()
    c.translate(bx + 75, by + 30)
    c.scale(press, press)
    br = skia.Rect.MakeXYWH(-80, -36, 160, 72)
    c.drawRRect(skia.RRect.MakeRectXY(br, 36, 36), fill(LIME if t >= C["send"] else PAPER))
    c.drawRRect(skia.RRect.MakeRectXY(br, 36, 36), stroke(INK, 5))
    text(c, "GO", 0, 0, size=40, font="display", fill=INK)
    c.restore()
    label(c, "plain words", x + 230, y - 20, 40, font="display", bg_col=LIME, fg_col=INK, rot=-4,
          scale=pop(t, C["normal_words"], 0.3))


def sc_step3(c, t, t0, t1):
    # the demo: every thing he names happens to the shot
    z = 1.0
    if t >= C["s3_cuts"]:
        z = 1.12                                              # the jump cut
    if t >= C["s3_zooms"]:
        z = lerp(1.12, 1.34, ease_out_expo(prog(t, C["s3_zooms"], 0.3)))
    if t >= C["s3_zoom_back"]:
        z = lerp(1.34, 1.12, ease_in_out_cubic(prog(t, C["s3_zoom_back"], 0.22)))
    if t >= C["s3_music"]:
        z *= 1 + 0.05 * math.exp(-(t - C["s3_music"]) * 5) * abs(math.cos((t - C["s3_music"]) * 12))
    draw_video(c, t, 0, 0, W, H, zoom=z)
    # flash on the cut
    fk = 1 - prog(t, C["s3_cuts"], 0.12)
    if C["s3_cuts"] <= t and fk > 0:
        c.drawRect(skia.Rect.MakeWH(W, H), fill(skia.Color(255, 255, 255, int(200 * fk))))
    # scissors line across the frame on "cuts"
    sk = prog(t, C["s3_cuts"] - 0.08, 0.3)
    if 0 < sk < 1:
        y = 980
        c.drawLine(0, y, W * sk, y, stroke(WHITE, 6))
        dash = skia.Paint(Color=INK, AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=6)
        dash.setPathEffect(skia.DashPathEffect.Make([24, 16], 0))
        c.drawLine(0, y, W * sk, y, dash)
    # beat bars on the music drop
    mk = t - C["s3_music"]
    if 0 <= mk < 0.7:
        for i in range(12):
            hh = (180 + 260 * n01(i * 3.1 + math.floor(mk * 15), 9)) * math.sin(math.pi * mk / 0.7)
            col = (LIME, PERI, BLUSH, ICE)[i % 4]
            rr = skia.Rect.MakeXYWH(30 + i * 87, 1500 - hh, 70, hh)
            c.drawRRect(skia.RRect.MakeRectXY(rr, 12, 12), fill(col))
            c.drawRRect(skia.RRect.MakeRectXY(rr, 12, 12), stroke(INK, 4))
    # step tag + checklist
    label(c, "03 IT EDITS", 60 + text_width("03 IT EDITS", 54, "display") / 2 + 34, 400, 54, bg_col=INK,
          fg_col=LIME, rot=-2, scale=ease_out_back(prog(t, t0 + 0.05, 0.35)))
    items = [("CUTS", C["s3_cuts"]), ("CAPTIONS", C["s3_captions"]), ("ZOOMS", C["s3_zooms"]),
             ("MUSIC", C["s3_music"])]
    for i, (s, ts) in enumerate(items):
        k = ease_out_back(prog(t, ts, 0.3))
        if k <= 0:
            continue
        size = 40
        w = text_width(s, size, "display") + 120
        x, y = 60, 510 + i * 92
        c.save()
        c.translate(x, y)
        c.scale(k, k)
        r = skia.Rect.MakeXYWH(0, -38, w, 76)
        paper_shadow(c, r, 38, 12, 6, 0.25)
        c.drawRRect(skia.RRect.MakeRectXY(r, 38, 38), fill(WHITE))
        check(c, 40, 0, 24, clamp((t - ts) / 0.3))
        text(c, s, 80, 0, size=size, font="display", fill=INK, align="left")
        c.restore()


def no_card(c, t, t_on, s, icon, y, rot):
    k = prog(t, t_on - 0.05, 0.22)
    if k <= 0:
        return
    sc = lerp(1.6, 1.0, ease_out_cubic(k))
    a = clamp(k * 3)
    jx, jy = jit(t, int(y), 2)
    x, w, h = 110, 860, 230
    c.save()
    c.translate(W / 2 + jx, y + h / 2 + jy)
    c.rotate(rot)
    c.scale(sc, sc)
    r = skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h)
    paper_shadow(c, r, 22, 18, 12, 0.25 * a)
    c.drawRRect(skia.RRect.MakeRectXY(r, 22, 22), fill(WHITE))
    c.drawRRect(skia.RRect.MakeRectXY(r, 22, 22), stroke(INK, 6))
    # icon
    ix = -w / 2 + 120
    if icon == "app":
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(ix - 60, -55, 120, 110), 22, 22), fill(PERI))
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(ix - 60, -55, 120, 110), 22, 22), stroke(INK, 5))
        p = skia.Path()
        p.moveTo(ix - 18, -26)
        p.lineTo(ix + 28, 0)
        p.lineTo(ix - 18, 26)
        p.close()
        c.drawPath(p, fill(INK))
    elif icon == "person":
        c.drawCircle(ix, -26, 30, fill(BLUSH))
        c.drawCircle(ix, -26, 30, stroke(INK, 5))
        rr = skia.Rect.MakeXYWH(ix - 55, 12, 110, 60)
        c.drawRRect(skia.RRect.MakeRectXY(rr, 30, 30), fill(BLUSH))
        c.drawRRect(skia.RRect.MakeRectXY(rr, 30, 30), stroke(INK, 5))
    else:
        p = skia.Path()
        p.moveTo(ix - 70, -10)
        p.lineTo(ix, -45)
        p.lineTo(ix + 70, -10)
        p.lineTo(ix, 25)
        p.close()
        c.drawPath(p, fill(ICE))
        c.drawPath(p, stroke(INK, 5))
        c.drawRect(skia.Rect.MakeXYWH(ix - 38, 10, 76, 40), fill(ICE))
        c.drawRect(skia.Rect.MakeXYWH(ix - 38, 10, 76, 40), stroke(INK, 5))
    text(c, "NO", -w / 2 + 235, 0, size=74, font="display", fill=ORANGE, align="left")
    text(c, s, -w / 2 + 400, 0, size=64 if len(s) < 9 else 54, font="display", fill=INK, align="left")
    c.restore()


def sc_nos(c, t, t0, t1):
    bg(c, PAPER_IMG)
    text(c, "what you need", W / 2, 390, size=70, font=SERIF, fill=INK, alpha=ease_out_cubic(prog(t, t0 + 0.05, 0.3)))
    no_card(c, t, C["no1"], "EDITING APP", "app", 480, -2.5)
    no_card(c, t, C["no2"], "EDITOR", "person", 740, 2.0)
    no_card(c, t, C["no3"], "SKILLS", "cap", 1000, -1.5)


def sc_talk(c, t, t0, t1):
    bg(c, PERI_IMG)
    headline(c, t, t0 + 0.05, "if you can talk,", None, 390)
    k = ease_out_back(prog(t, C["make_this"] - 0.1, 0.35))
    if k > 0:
        c.save()
        c.translate(W / 2, 515)
        c.scale(k, k)
        s = "YOU CAN MAKE THIS"
        size = 70
        hk = ease_out_cubic(prog(t, C["this"], 0.3))
        tw = text_width(s, size, "display")
        tw2 = text_width("THIS", size, "display")
        if hk > 0:
            c.save()
            c.rotate(-1.5)
            c.drawRect(skia.Rect.MakeXYWH(tw / 2 - tw2 - 14, -size * 0.45, (tw2 + 28) * hk, size * 0.95), fill(LIME))
            c.restore()
        text(c, s, 0, 0, size=size, font="display", fill=INK)
        c.restore()
    card(c, t, 170, 660, 740, 650, rot=2.0, zoom=lerp(1.2, 1.3, prog(t, t0, t1 - t0)))


def receipt(c, t, t0):
    k = ease_out_cubic(prog(t, t0, 1.8))
    slot_y = 400
    full_h = 800
    h = full_h * k
    x, w = 215, 650
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(0, slot_y + 4, W, h + 30))
    y0 = slot_y - 10                    # unrolls top-down out of the slot
    r = skia.Rect.MakeXYWH(x, y0, w, full_h)
    paper_shadow(c, r, 4, 16, 10, 0.25)
    c.drawRect(r, fill(WHITE))
    # zig-zag bottom edge
    p = skia.Path()
    p.moveTo(x, y0 + full_h)
    for i in range(27):
        p.lineTo(x + (i + 0.5) * w / 27, y0 + full_h + (14 if i % 2 == 0 else 0))
    p.lineTo(x + w, y0 + full_h)
    p.close()
    c.drawPath(p, fill(WHITE))
    text(c, "THE VIBE EDITING SYSTEM", x + w / 2, y0 + 80, size=34, font="display", fill=INK)
    text(c, "receipt for this video", x + w / 2, y0 + 140, size=44, font=SERIF, fill=INK)
    dash = skia.Paint(Color=INK, AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3)
    dash.setPathEffect(skia.DashPathEffect.Make([12, 10], 0))
    c.drawLine(x + 40, y0 + 190, x + w - 40, y0 + 190, dash)
    for i, (k_, v) in enumerate(TL.RECEIPT):
        yy = y0 + 250 + i * 76
        last = i == len(TL.RECEIPT) - 1
        if last:
            c.drawRect(skia.Rect.MakeXYWH(x + 26, yy - 34, w - 52, 68), fill(LIME))
        text(c, k_, x + 44, yy, size=31, font="mono", fill=INK, align="left")
        text(c, v, x + w - 44, yy, size=36 if last else 31, font="mono", fill=INK, align="right")
    c.restore()
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(170, slot_y - 22, 740, 44), 22, 22), fill(INK))


TILE_COLS = [PERI, LIME, BLUSH, ICE, ORANGE, PERI, BLUSH, LIME, ICE]


def grid(c, t, t0):
    text(c, "every video on this page", W / 2, 390, size=66, font=SERIF, fill=INK,
         alpha=ease_out_cubic(prog(t, t0, 0.3)))
    tw, th, gap = 250, 280, 22
    gx = (W - 3 * tw - 2 * gap) / 2
    gy = 450
    for i in range(9):
        k = ease_out_back(prog(t, t0 + 0.05 + i * 0.07, 0.3))
        if k <= 0:
            continue
        col, row = i % 3, i // 3
        x, y = gx + col * (tw + gap), gy + row * (th + gap)
        jx, jy = jit(t, 60 + i, 1.5)
        c.save()
        c.translate(x + tw / 2 + jx, y + th / 2 + jy)
        c.rotate((i * 37 % 5 - 2) * 0.8)
        c.scale(k, k)
        r = skia.Rect.MakeXYWH(-tw / 2, -th / 2, tw, th)
        paper_shadow(c, r, 16, 12, 8, 0.22)
        c.drawRRect(skia.RRect.MakeRectXY(r, 16, 16), fill(TILE_COLS[i]))
        if i == 4:      # this video, live
            c.save()
            c.clipRRect(skia.RRect.MakeRectXY(r, 16, 16), True)
            draw_video(c, t, -tw / 2, -th / 2, tw, th, zoom=1.5)
            c.restore()
        else:           # simple paper-cut thumbnails
            c.drawCircle(0, -30, 60, fill(PAPER))
            c.drawCircle(0, -30, 60, stroke(INK, 5))
            p = skia.Path()
            p.moveTo(-18, -62)
            p.lineTo(34, -30)
            p.lineTo(-18, 2)
            p.close()
            c.drawPath(p, fill(INK))
            c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-90, 55, 180, 22), 12, 12), fill(INK))
            c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-90, 90, 120, 18), 10, 10),
                        fill(skia.Color(0, 0, 0, 90)))
        c.drawRRect(skia.RRect.MakeRectXY(r, 16, 16), stroke(INK, 5))
        tag_k = ease_out_back(prog(t, C["page"] + i * 0.04, 0.25))
        if tag_k > 0:
            label(c, "AI EDITED", tw / 2 - 80, -th / 2 + 34, 22, font="mono", bg_col=INK, fg_col=LIME, rot=4,
                  scale=tag_k, padx=14, pady=10, radius=8, shadow_on=False)
        c.restore()


def sc_proof(c, t, t0, t1):
    bg(c, PAPER_IMG)
    if t < C["every"]:
        receipt(c, t, C["receipt"])
    else:
        out = ease_in_cubic(prog(t, C["every"], 0.3))
        if out < 1:
            c.save()
            c.translate(0, out * 1500)
            receipt(c, t, C["receipt"])
            c.restore()
        grid(c, t, C["every"] + 0.1)


def sc_open(c, t, t0, t1):
    bg(c, PAPER_IMG)
    headline(c, t, t0 + 0.08, "now opening it up to", "A FEW CREATORS", 390, big_size=84, hi=PERI)
    card(c, t, 140, 680, 800, 640, rot=1.5, zoom=lerp(1.15, 1.25, prog(t, t0, t1 - t0)))
    label(c, "how it works?", 790, 1290, 50, font=SERIF, bg_col=LIME, fg_col=INK, rot=-6,
          scale=pop(t, C["how"], 0.3), padx=26, pady=14)


def sc_cta(c, t, t0, t1):
    bg(c, PERI_IMG)
    face_circle(c, t, W / 2, 600, 230, k=ease_out_back(prog(t, t0 + 0.05, 0.4)))
    # comment bubble
    kb = ease_out_back(prog(t, C["comment"] - 0.05, 0.35))
    if kb > 0:
        bx, by, bw, bh = 110, 880, 860, 300
        c.save()
        c.translate(W / 2, by + bh / 2)
        c.rotate(-2)
        c.scale(kb, kb)
        r = skia.Rect.MakeXYWH(-bw / 2, -bh / 2, bw, bh)
        tail = skia.Path()
        tail.moveTo(-bw / 2 + 120, bh / 2 - 6)
        tail.lineTo(-bw / 2 + 90, bh / 2 + 70)
        tail.lineTo(-bw / 2 + 210, bh / 2 - 6)
        tail.close()
        c.drawRRect(skia.RRect.MakeRectXY(r.makeOffset(12, 12), 40, 40), fill(INK))
        c.drawRRect(skia.RRect.MakeRectXY(r, 40, 40), fill(WHITE))
        c.drawPath(tail, fill(WHITE))
        c.drawRRect(skia.RRect.MakeRectXY(r, 40, 40), stroke(INK, 7))
        c.drawPath(tail, stroke(INK, 7))
        c.drawRect(skia.Rect.MakeXYWH(-bw / 2 + 112, bh / 2 - 12, 92, 14), fill(WHITE))
        text(c, "comment", 0, -78, size=70, font=SERIF, fill=INK)
        ks = ease_out_back(prog(t, C["system"] - 0.05, 0.3))
        if ks > 0.01 and t >= C["system"] - 0.05:
            c.save()
            c.translate(0, 45)
            c.rotate(-1.5)
            c.scale(lerp(1.5, 1, ease_out_cubic(prog(t, C["system"] - 0.05, 0.25))), lerp(1.5, 1, ease_out_cubic(
                prog(t, C["system"] - 0.05, 0.25))))
            sw_ = text_width("SYSTEM", 120, "display")
            c.drawRect(skia.Rect.MakeXYWH(-sw_ / 2 - 24, -62, sw_ + 48, 124), fill(LIME))
            text(c, "SYSTEM", 0, 0, size=120, font="display", fill=INK, alpha=clamp(ks * 3))
            c.restore()
        c.restore()
    kl = ease_out_back(prog(t, C["link"] - 0.05, 0.3))
    if kl > 0:
        bob = math.sin((t - C["link"]) * 7) * 8
        label(c, "or tap the link below", W / 2, 1300, 50, font=SERIF, bg_col=INK, fg_col=WHITE, rot=1.5,
              scale=kl, padx=30, pady=16)
        c.save()
        c.translate(W / 2, 1405 + bob)
        c.scale(kl, kl)
        p = skia.Path()
        p.moveTo(-34, -20)
        p.lineTo(0, 22)
        p.lineTo(34, -20)
        c.drawPath(p, stroke(INK, 12))
        c.restore()
    ke = ease_out_cubic(prog(t, C["link"] + 0.6, 0.4))
    text(c, "THE VIBE EDITING SYSTEM", W / 2, 1470, size=36, font="display", fill=INK, alpha=ke, tracking=0.04)


SCENE_FN = dict(hook=sc_hook, pain=sc_pain, built=sc_built, step1=sc_step1, step2=sc_step2, step3=sc_step3,
                nos=sc_nos, talk=sc_talk, proof=sc_proof, open=sc_open, cta=sc_cta)

# ------------------------------------------------------------------ persistent layers
BADGE_X, BADGE_Y = 210, 290


def badge(c, t):
    if t < C["stamp_fly"] + 0.36:
        return
    k = ease_out_back(prog(t, C["stamp_fly"] + 0.36, 0.2))
    s = "AI EDITED THIS"
    size = 30
    w = text_width(s, size, "display") + 86
    c.save()
    c.translate(BADGE_X, BADGE_Y)
    c.scale(k, k)
    r = skia.Rect.MakeXYWH(-w / 2, -32, w, 64)
    paper_shadow(c, r, 32, 10, 5, 0.25)
    c.drawRRect(skia.RRect.MakeRectXY(r, 32, 32), fill(INK))
    blink = 0.45 + 0.55 * (0.5 + 0.5 * math.cos(t * 5))
    c.drawCircle(-w / 2 + 34, 0, 10, fill(skia.Color(212, 255, 63, int(255 * blink))))
    text(c, s, -w / 2 + 56, 0, size=size, font="display", fill=WHITE, align="left")
    c.restore()


def chunks():
    out, cur = [], []
    for wd in WORDS:
        cur.append(wd)
        txt = " ".join(x["w"] for x in cur)
        end_punct = wd["w"][-1] in ".,:;!?"
        if end_punct or len(cur) >= 3 or len(txt) >= 13:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


CHUNKS = chunks()


def captions(c, t):
    if t >= TL.SCENES[-1][0]:            # the end card carries its own words
        return
    for i, ch in enumerate(CHUNKS):
        s0 = ch[0]["s"]
        nxt = CHUNKS[i + 1][0]["s"] if i + 1 < len(CHUNKS) else ch[-1]["e"] + 0.4
        end = min(nxt, ch[-1]["e"] + 0.5)
        if s0 - 0.03 <= t < end:
            break
    else:
        return
    size = 58
    ws = [x["w"].upper().strip(".,:;!?") for x in ch]
    space = text_width(" ", size, "display")
    widths = [text_width(s, size, "display") for s in ws]
    total = sum(widths) + space * (len(ws) - 1)
    k = ease_out_back(prog(t, s0 - 0.03, 0.14))
    boost = 1.0
    if C["s3_captions"] - 0.05 <= t < C["s3_captions"] + 0.7:
        boost = lerp(1.0, 1.35, ease_out_back(prog(t, C["s3_captions"] - 0.05, 0.25)))
    rot = (-1.5, 1.2, -0.8, 1.6)[i % 4]
    padx, pady = 30, 22
    w, h = total + 2 * padx, size + 2 * pady
    c.save()
    c.translate(W / 2, 1410)
    c.rotate(rot)
    c.scale(k * boost, k * boost)
    r = skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h)
    paper_shadow(c, r, 14, 12, 8, 0.28)
    c.drawRRect(skia.RRect.MakeRectXY(r, 14, 14), fill(WHITE))
    x = -total / 2
    for wd, s, ww in zip(ch, ws, widths):
        active = wd["s"] - 0.03 <= t
        if active and (t < wd["e"] + 0.15 or wd is ch[-1]):
            c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x - 10, -size * 0.5, ww + 20, size), 10, 10),
                        fill(LIME))
        text(c, s, x, 0, size=size, font="display", fill=INK if active else skia.Color(11, 11, 13, 110),
             align="left")
        x += ww + space
    c.restore()


def bubble_k(t):
    """face circle scale for the bubble scenes (it stays put across them)."""
    runs = [(a, b) for a, b, _, lay in TL.SCENES if lay == "bubble"]
    a, b = runs[0][0], runs[-1][1]
    if not a <= t < b + 0.2:
        return 0.0
    return ease_out_back(prog(t, a + 0.15, 0.4)) * (1 - ease_in_cubic(prog(t, b - 0.05, 0.2)))


# ------------------------------------------------------------------ frame
def scene_at(t):
    for i, (a, b, name, lay) in enumerate(TL.SCENES):
        if a <= t < b:
            return i
    return len(TL.SCENES) - 1


def draw_scene(c, i, t):
    a, b, name, lay = TL.SCENES[i]
    SCENE_FN[name](c, t, a, b)


def draw(c, t):
    i = scene_at(t)
    a = TL.SCENES[i][0]
    k = prog(t, a, TL.TRANSITION)
    if i > 0 and k < 1:
        draw_scene(c, i - 1, t)
        e = ease_out_cubic(k)
        side = 1 if i % 2 else -1
        c.save()
        c.translate(0, (1 - e) * H * 1.02)
        rot_about(c, side * 4 * (1 - e), W / 2, H)
        paper_shadow(c, skia.Rect.MakeWH(W, H), 0, 40, -10, 0.45)
        c.clipRect(skia.Rect.MakeWH(W, H))
        draw_scene(c, i, t)
        c.restore()
    else:
        draw_scene(c, i, t)
    bk = bubble_k(t)
    if bk > 0:
        face_circle(c, t, 860, 450, 160, k=bk)
    captions(c, t)
    badge(c, t)


# ------------------------------------------------------------------ audio
def build_audio():
    import audio_kit as ak
    from scipy.io import wavfile
    ak.voice_chain("work/cut.mp4", "work/voice.wav", denoise=True)
    sr = ak.SR
    n = int(TL.DURATION * sr)
    bed = ak.music_bed(TL.MOOD, seconds=TL.DURATION + 2, seed=TL.SEED)[:n]
    if len(bed) < n:
        bed = np.pad(bed, ((0, n - len(bed)), (0, 0)))
    tt = np.arange(n) / sr
    env = np.where(tt < C["s3_music"], 0.55, 1.0)            # the drop on "the music"
    env = np.convolve(env, np.ones(800) / 800, mode="same")
    env *= np.clip((TL.DURATION - tt) / 1.2, 0, 1)
    bed = (bed * env[:, None]).astype(np.float32)
    ak.write_wav("work/music.wav", bed)
    sfx = [
        {"t": C["stamp"] - 0.02, "kind": "impact", "gain_db": -4},
        {"t": C["stamp_fly"], "kind": "whoosh", "gain_db": -10, "dur": 0.4},
    ]
    for a, b, name, lay in TL.SCENES[1:]:
        sfx.append({"t": a - 0.05, "kind": "swish", "gain_db": -12})
    for key in ("editing", "takes", "forever", "cutting", "captions", "music", "zooms", "one_take", "mistakes",
                "normal_words", "s3_captions", "this", "how", "link"):
        sfx.append({"t": C[key], "kind": "pop", "gain_db": -11})
    sfx += [
        {"t": C["day"], "kind": "tick", "gain_db": -9}, {"t": C["day"] + 0.4, "kind": "tick", "gain_db": -9},
        {"t": C["day"] + 0.8, "kind": "tick", "gain_db": -9}, {"t": C["day"] + 1.2, "kind": "ding", "gain_db": -12},
        {"t": C["type_start"], "kind": "typing", "gain_db": -14, "dur": C["type_end"] - C["type_start"]},
        {"t": C["send"], "kind": "click", "gain_db": -8},
        {"t": C["s3_cuts"] - 0.02, "kind": "shutter", "gain_db": -8},
        {"t": C["s3_zooms"] - 0.05, "kind": "whoosh", "gain_db": -12, "dur": 0.35},
        {"t": C["s3_music"] - 1.2, "kind": "riser", "gain_db": -16, "dur": 1.2},
        {"t": C["s3_music"] - 0.02, "kind": "bass_drop", "gain_db": -6},
        {"t": C["no1"] - 0.03, "kind": "impact", "gain_db": -9}, {"t": C["no2"] - 0.03, "kind": "impact", "gain_db": -9},
        {"t": C["no3"] - 0.03, "kind": "impact", "gain_db": -9},
        {"t": C["receipt"], "kind": "typing", "gain_db": -15, "dur": 1.8},
        {"t": C["every"] + 0.1, "kind": "sparkle", "gain_db": -13},
        {"t": C["system"] - 0.03, "kind": "impact", "gain_db": -7},
        {"t": C["link"] + 0.6, "kind": "sparkle", "gain_db": -14},
    ]
    cues = {"duration": TL.DURATION, "voice": {"file": "work/voice.wav", "gain_db": 0, "t": 0},
            "music": {"file": "work/music.wav", "gain_db": -10, "duck_db": -9, "fade_out": 1.0}, "sfx": sfx}
    Path("work/cues.json").write_text(json.dumps(cues, indent=1))
    mix = ak.mix(cues)
    ak.write_wav("work/mix.wav", mix)
    print("audio -> work/mix.wav")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stills"
    if cmd == "stills":
        S.stills(draw, [float(x) for x in sys.argv[2:]] or [0.5, 1.7, 5.0, 7.8])
    elif cmd == "audio":
        build_audio()
    elif cmd == "render":
        a = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
        b = float(sys.argv[3]) if len(sys.argv) > 3 else None
        out = "out/ai_edited_reel_picture.mp4" if len(sys.argv) <= 2 else "out/range.mp4"
        S.render(draw, out, start=a, end=b, crf=16)
