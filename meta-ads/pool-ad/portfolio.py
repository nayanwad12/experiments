"""portfolio.py: the finished ad as a portfolio card on white, with a funky "AI EDITED THIS VIDEO" headline.

Everything sits inside the Instagram Reels safe zone (1080x1920): top 250 px, bottom 420 px and ~60 px at
the sides are kept clear for the app UI.

    python3 portfolio.py stills 0.4 1.2 10
    python3 portfolio.py render            -> out/pool_ad_portfolio.mp4 (audio from the ad's mix)
"""
import math
import subprocess
import sys

import numpy as np
import skia

sys.path.insert(0, "vibe")
from motion_kit import Stage, clamp, ease_out_back, ease_out_cubic, ease_out_expo, prog, text, text_width  # noqa: E402

SRC = "out/pool_ad_v2.mp4"
DUR = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", SRC],
                           capture_output=True, text=True).stdout)
FPS = 30
S = Stage(1080, 1920, fps=FPS, duration=DUR)

SAFE_TOP, SAFE_BOTTOM, SAFE_SIDE = 250, 1920 - 420, 60

# card: 9:16, bottom edge on the safe line
CARD_Y = SAFE_TOP + 158                     # right under the one-line headline
CARD_H = (SAFE_BOTTOM - 20 - CARD_Y) // 2 * 2
CARD_W = CARD_H * 9 / 16
CARD_X = (1080 - CARD_W) / 2
RADIUS = 46

CW, CH = int(round(CARD_W)) // 2 * 2, int(round(CARD_H)) // 2 * 2
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", SRC, "-vf", f"fps={FPS},scale={CW}:{CH}:flags=lanczos",
                      "-f", "rawvideo", "-pix_fmt", "rgba", "-"], capture_output=True, check=True).stdout
FRAMES = np.frombuffer(raw, np.uint8).reshape(-1, CH, CW, 4)

INK, LIME, ORANGE, PERI = (skia.Color(11, 11, 13), skia.Color(212, 255, 63), skia.Color(255, 90, 31),
                           skia.Color(196, 198, 255))
F_DISPLAY, F_SERIF, F_HAND, F_MONO = "Unbounded-900.ttf", "InstrumentSerif-Italic.ttf", "CaveatBrush-Regular.ttf", \
    "JetBrainsMono-700.ttf"


def rrect(c, x, y, w, h, r, color, stroke=None, blur=0):
    p = skia.Paint(Color=color, AntiAlias=True)
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), p)


def sparkle(c, x, y, r, color, rot=0.0):
    """4-point star."""
    p = skia.Path()
    for i in range(8):
        a = rot + i * math.pi / 4
        rr = r if i % 2 == 0 else r * 0.28
        (p.moveTo if i == 0 else p.lineTo)(x + rr * math.cos(a), y + rr * math.sin(a))
    p.close()
    c.drawPath(p, skia.Paint(Color=color, AntiAlias=True))


def squiggle(c, x0, x1, y, k, color, width=9, amp=10, waves=5):
    if k <= 0:
        return
    p = skia.Path()
    n = 80
    for i in range(int(n * k) + 1):
        u = i / n
        xx = x0 + (x1 - x0) * u
        yy = y + amp * math.sin(u * waves * 2 * math.pi)
        (p.moveTo if i == 0 else p.lineTo)(xx, yy)
    pt = skia.Paint(Color=color, AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=width)
    pt.setStrokeCap(skia.Paint.kRound_Cap)
    pt.setStrokeJoin(skia.Paint.kRound_Join)
    c.drawPath(p, pt)


def bouncy_word(c, t, s, x, y, size, font, fill, t0, offset_col=None, offset=(0, 0), tracking=0.0, stagger=0.05,
                stroke=None):
    """letters drop in one by one with a bounce, then bob gently. (x, y) = left, middle."""
    f = skia.Font(None, size)
    cx = x
    for i, ch in enumerate(s):
        k = ease_out_back(prog(t, t0 + i * stagger, 0.38), 2.2)
        if k > 0:
            bob = 5 * math.sin(t * 2.6 + i * 0.8) * clamp((t - t0 - 1.0) / 0.5)
            rot = 6 * math.sin(t * 1.7 + i * 1.3) * clamp((t - t0 - 1.0) / 0.5)
            w = text_width(ch, size, font)
            c.save()
            c.translate(cx + w / 2, y + (1 - k) * -90 + bob)
            c.rotate(rot)
            if offset_col is not None:
                text(c, ch, offset[0], offset[1], size=size, font=font, fill=offset_col, alpha=clamp(k))
            text(c, ch, 0, 0, size=size, font=font, fill=fill, alpha=clamp(k), stroke=stroke,
                 stroke_col=INK if stroke else None)
            c.restore()
        cx += text_width(ch, size, font) + tracking * size
    return cx - x


def dot_grid(c):
    p = skia.Paint(Color=skia.Color(0, 0, 0, 20), AntiAlias=True)
    for yy in range(30, 1920, 44):
        for xx in range(30, 1080, 44):
            c.drawCircle(xx, yy, 2.2, p)


def draw(c, t):
    c.clear(skia.ColorWHITE)
    dot_grid(c)

    # ---------------- headline: one compact line inside the top safe line  [AI] EDITED this video
    ai_w, ai_h, ed_size, tv_size, gap = 150, 108, 78, 104, 20
    ed_w = text_width("EDITED", ed_size, F_DISPLAY)
    tv_w = text_width("this video", tv_size, F_SERIF)
    total = ai_w + gap + ed_w + gap + tv_w
    sc = min(1.0, (1080 - 2 * SAFE_SIDE - 20) / total)
    ai_w, ai_h, ed_size, tv_size, gap = ai_w * sc, ai_h * sc, ed_size * sc, tv_size * sc, gap * sc
    ed_w, tv_w = ed_w * sc, tv_w * sc
    x0 = (1080 - (ai_w + gap + ed_w + gap + tv_w)) / 2
    y1 = SAFE_TOP + 72
    k_ai = ease_out_back(prog(t, 0.05, 0.45), 2.0)
    if k_ai > 0:
        c.save()
        c.translate(x0 + ai_w / 2, y1)
        c.rotate(-8 + 3 * math.sin(t * 2.0) * clamp(t - 1.2))
        c.scale(k_ai, k_ai)
        rrect(c, -ai_w / 2 + 7, -ai_h / 2 + 9, ai_w, ai_h, 30, INK)              # offset shadow
        rrect(c, -ai_w / 2, -ai_h / 2, ai_w, ai_h, 30, LIME)
        rrect(c, -ai_w / 2, -ai_h / 2, ai_w, ai_h, 30, INK, stroke=6)
        text(c, "AI", 0, 3, size=74 * sc, font=F_DISPLAY, fill=INK)
        c.restore()
    xe = x0 + ai_w + gap
    bouncy_word(c, t, "EDITED", xe, y1, ed_size, F_DISPLAY, INK, 0.25, offset_col=LIME, offset=(5, 6))
    xt = xe + ed_w + gap
    bouncy_word(c, t, "this video", xt, y1 + 4, tv_size, F_SERIF, INK, 0.55, stagger=0.035)
    squiggle(c, xt + 6, xt + tv_w - 6, y1 + 52, ease_out_cubic(prog(t, 1.0, 0.5)), ORANGE, width=7, amp=7, waves=4)

    # sparkles around the card, in the side margins
    for i, (sx, sy, r, colr) in enumerate([(120, CARD_Y + 420, 26, ORANGE), (975, CARD_Y + 230, 24, PERI),
                                           (965, CARD_Y + 760, 30, LIME), (110, CARD_Y + 900, 18, INK)]):
        k = ease_out_back(prog(t, 0.9 + i * 0.12, 0.35), 2.5)
        if k > 0:
            tw = 0.8 + 0.2 * math.sin(t * 4 + i * 1.7)
            sparkle(c, sx, sy, r * k * tw, colr, t * 0.6 + i)

    # ---------------- the card
    kc = ease_out_expo(prog(t, 0.0, 0.7))
    cy = CARD_Y + (1 - kc) * 120
    rrect(c, CARD_X + 6, cy + 26, CARD_W, CARD_H, RADIUS, skia.Color(0, 0, 0, int(55 * kc)), blur=34)
    rrect(c, CARD_X, cy + 4, CARD_W, CARD_H, RADIUS, skia.Color(0, 0, 0, int(30 * kc)), blur=8)
    c.save()
    c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(CARD_X, cy, CARD_W, CARD_H), RADIUS, RADIUS), True)
    fr = FRAMES[int(clamp(round(t * FPS), 0, len(FRAMES) - 1))]
    img = skia.Image.fromarray(np.ascontiguousarray(fr), colorType=skia.kRGBA_8888_ColorType)
    c.drawImageRect(img, skia.Rect.MakeXYWH(CARD_X, cy, CARD_W, CARD_H),
                    skia.SamplingOptions(skia.CubicResampler.Mitchell()))
    c.restore()
    rrect(c, CARD_X, cy, CARD_W, CARD_H, RADIUS, skia.Color(0, 0, 0, 28), stroke=2)

    # hand-drawn note + arrow pointing at the card (left side, inside the safe margins)
    ka = prog(t, 1.4, 0.5)
    if ka > 0:
        c.save()
        c.translate((SAFE_SIDE + CARD_X) / 2 - 4, CARD_Y + 110)
        c.rotate(-10)
        text(c, "no", 0, -40, size=40, font=F_HAND, fill=ORANGE, alpha=clamp(ka * 2))
        text(c, "timeline", 0, 0, size=40, font=F_HAND, fill=ORANGE, alpha=clamp(ka * 2))
        text(c, "opened!", 0, 40, size=40, font=F_HAND, fill=ORANGE, alpha=clamp(ka * 2))
        c.restore()
        p = skia.Path()
        pts = [((SAFE_SIDE + CARD_X) / 2 + 10 + (CARD_X - (SAFE_SIDE + CARD_X) / 2 - 22) * u,
                CARD_Y + 190 + 90 * u - 30 * math.sin(u * math.pi)) for u in
               np.linspace(0, ease_out_cubic(ka), 30)]
        p.moveTo(*pts[0])
        for q in pts[1:]:
            p.lineTo(*q)
        pt = skia.Paint(Color=ORANGE, AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=6)
        pt.setStrokeCap(skia.Paint.kRound_Cap)
        c.drawPath(p, pt)
        if ka >= 1:
            ex, ey = pts[-1]
            c.drawPath(skia.Path().moveTo(ex - 22, ey - 10).lineTo(ex, ey).lineTo(ex - 8, ey - 24), pt)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stills"
    if cmd == "stills":
        S.stills(draw, [float(x) for x in sys.argv[2:]] or [0.4, 1.0, 2.5, 12.0], out_dir="out/stills/portfolio")
    else:
        S.render(draw, "out/pool_ad_portfolio.mp4", audio="work/mix.wav", crf=16)
