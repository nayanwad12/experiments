"""9:16 Instagram Reel: ORIGINAL vs VIBE EDITED as two overlapping phone cards on a dark navy stage,
frame-for-frame in sync, with the edit's sound. "Fully Edited by AI" on top.
Everything sits inside the Reels safe zone (220 px top, 420 px bottom, 35 px left, 120 px right).

    python3 reel.py          ->  out/comparison_reel.mp4 (1080x1920, 30 fps, dark navy stage)
    python3 reel.py --white  ->  out/comparison_reel_white.mp4 (same layout on a white stage)
"""

import math
import os
import subprocess
import sys

import cv2
import numpy as np
import skia

from common import FFMPEG, FONTS, FPS, OUT, H, W

RW, RH = 1080, 1920
SAFE_L, SAFE_R = 35, RW - 120                              # content lives in x 35..960, y 220..1500
SAFE_T, SAFE_B = 220, RH - 420
ZX = (SAFE_L + SAFE_R) / 2
# vibe edited: the big card on the right, in front
BW, BH = 560, round(560 * H / W)                           # 560 x 996
BX, BY = SAFE_R - 6 - BW - (12 if "--white" in sys.argv else 0), 452
# original: smaller, lower, tucked behind on the left, tilted
SW_, SH_ = 432, round(432 * H / W)                         # 432 x 768
SCX, SCY = SAFE_L + 30 + SW_ / 2, SAFE_B - 26 - SH_ / 2    # card centre
TILT = -4.0
RAD = 34
NAVY, NAVY_D = (16, 24, 52), (6, 9, 22)
YEL, WHITE, INK, COBALT = (255, 214, 10), (255, 255, 255), (14, 16, 24), (36, 58, 214)
WHITE_THEME = "--white" in sys.argv
# theme: stage gradient, glows, grid, text colours, label style, shadow strength
T = dict(
    stage=((255, 255, 255), (234, 235, 241)),
    glows=((BX + BW * 0.5, BY + BH * 0.45, 640, COBALT, 0.10), (SCX, SCY + 120, 420, (120, 90, 220), 0.06),
           (BX + BW * 0.9, BY + 40, 320, YEL, 0.22)),
    grid=(INK, 0.045), title=INK, sub=(105, 110, 130), spark2=COBALT, label=INK, arrow=INK,
    small_border=(INK, 0.14), small_wash=(WHITE, 0.0), shadow=(0.28, 0.34),
) if WHITE_THEME else dict(
    stage=(NAVY, NAVY_D),
    glows=((BX + BW * 0.5, BY + BH * 0.45, 640, COBALT, 0.55), (SCX, SCY + 120, 420, (90, 60, 200), 0.25),
           (BX + BW * 0.9, BY + 40, 300, YEL, 0.10)),
    grid=(WHITE, 0.035), title=WHITE, sub=(170, 182, 230), spark2=WHITE, label=YEL, arrow=YEL,
    small_border=(WHITE, 0.30), small_wash=(NAVY_D, 0.12), shadow=(0.65, 0.8),
)


def c4(rgb, a=1.0):
    return skia.Color4f(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, a)


def tf(name):
    return skia.Typeface.MakeFromFile(os.path.join(FONTS, name + ".ttf"))


def text(c, s, x, y, face, size, fill, align="c", track=0.0, a=1.0):
    f = skia.Font(face, size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    glyphs = f.textToGlyphs(s)
    widths = f.getWidths(glyphs)
    w = sum(widths) + track * size * (len(s) - 1)
    x0 = x - w / 2 if align == "c" else x - w if align == "r" else x
    b = skia.TextBlobBuilder()
    pos, xx = [], 0.0
    for gw in widths:
        pos.append(skia.Point(xx, 0))
        xx += gw + track * size
    b.allocRunPos(f, glyphs, pos)
    c.drawTextBlob(b.make(), x0, y, skia.Paint(AntiAlias=True, Color4f=c4(fill, a)))
    return w


def sparkle(c, x, y, r, rgb, a=1.0):
    p = skia.Path()
    for i in range(8):
        ang = math.radians(-90 + 45 * i)
        rr = r if i % 2 == 0 else r * 0.28
        (p.moveTo if i == 0 else p.lineTo)(x + rr * math.cos(ang), y + rr * math.sin(ang))
    p.close()
    c.drawPath(p, skia.Paint(AntiAlias=True, Color4f=c4(rgb, a)))


def layer():
    arr = np.zeros((RH, RW, 4), np.uint8)
    return arr, skia.Surface(arr).getCanvas()


def small_card_matrix():
    """Card pixel coords -> canvas, for the tilted ORIGINAL card."""
    m = skia.Matrix()
    m.setTranslate(SCX, SCY)
    m.preRotate(TILT)
    m.preTranslate(-SW_ / 2, -SH_ / 2)
    return m


def shadow(c, rr, blur, a, dy):
    p = skia.Paint(AntiAlias=True, Color4f=c4((0, 0, 0), a))
    p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    c.save()
    c.translate(0, dy)
    c.drawRRect(rr, p)
    c.restore()


def background():
    arr, c = layer()
    c.drawPaint(skia.Paint(Shader=skia.GradientShader.MakeRadial(
        skia.Point(RW * 0.55, RH * 0.45), RH * 0.8, [c4(T["stage"][0]).toColor(), c4(T["stage"][1]).toColor()])))
    # soft cobalt + yellow glows behind the cards
    for (x, y, r, rgb, a) in T["glows"]:
        c.drawPaint(skia.Paint(Shader=skia.GradientShader.MakeRadial(
            skia.Point(x, y), r, [c4(rgb, a).toColor(), c4(rgb, 0).toColor()])))
    # fine engineering grid
    gp = skia.Paint(AntiAlias=True, Color4f=c4(*T["grid"]), StrokeWidth=1)
    for x in range(0, RW + 1, 54):
        c.drawLine(x, 0, x, RH, gp)
    for y in range(0, RH + 1, 54):
        c.drawLine(0, y, RW, y, gp)
    # header
    black = tf("Montserrat-Black")
    fs = 74
    y1 = SAFE_T + 80
    f = skia.Font(black, fs)
    full = f.measureText("Fully Edited by AI")
    x0 = ZX - (full + 22) / 2
    w = text(c, "Fully Edited by ", x0, y1, black, fs, T["title"], "l")
    wai = f.measureText("AI")
    hl = skia.RRect.MakeRectXY(skia.Rect(x0 + w - 6, y1 - 64, x0 + w + wai + 16, y1 + 14), 12, 12)
    c.drawRRect(hl, skia.Paint(AntiAlias=True, Color4f=c4(YEL)))
    text(c, "AI", x0 + w + 5, y1, black, fs, INK, "l")
    sparkle(c, x0 + w + wai + 34, y1 - 70, 18, YEL if not WHITE_THEME else COBALT)
    sparkle(c, x0 - 18, y1 - 62, 10, T["spark2"], 0.8)
    text(c, "ONE TAKE  ·  ZERO EDITING APPS  ·  JUST CLAUDE", ZX, y1 + 52, tf("SpaceGrotesk-Bold"), 24,
         T["sub"], track=0.08)
    # ORIGINAL card: shadow + label (it sits behind, so it is part of the background)
    c.save()
    c.concat(small_card_matrix())
    shadow(c, skia.RRect.MakeRectXY(skia.Rect.MakeWH(SW_, SH_), RAD, RAD), 26, T["shadow"][0], 18)
    c.restore()
    return arr[..., :3].astype(np.float32)


def highlight(c, x, y, w, size):
    """Yellow marker swipe behind a label (white theme)."""
    c.save()
    c.translate(x, y - size * 0.32)
    c.rotate(-2)
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(-w / 2 - 16, -size * 0.42, w / 2 + 16, size * 0.42), 10, 10),
                skia.Paint(AntiAlias=True, Color4f=c4(YEL, 0.95)))
    c.restore()


def labels(c):
    marker = tf("PermanentMarker-Regular")
    mono = tf("SpaceGrotesk-Bold")
    # VIBE EDITED above the big card
    lx, ly = BX + BW / 2, BY - 30
    if WHITE_THEME:
        highlight(c, lx, ly, skia.Font(marker, 50).measureText("Vibe Edited"), 50)
    text(c, "Vibe Edited", lx, ly, marker, 50, T["label"])
    sparkle(c, lx + 168, ly - 34, 13, YEL if not WHITE_THEME else COBALT)
    # ORIGINAL above the small card (left of the big card)
    ox, oy = SCX - 30, SCY - SH_ / 2 - 40
    if WHITE_THEME:
        highlight(c, ox, oy, skia.Font(marker, 44).measureText("Original"), 44)
    text(c, "Original", ox, oy, marker, 44, T["label"])
    text(c, "RAW TAKE · NO EDITS", ox, oy + 30, mono, 17, T["sub"], track=0.1)
    # hand-drawn arrow from the ORIGINAL label down onto its card
    p = skia.Path()
    p.moveTo(ox - 120, oy - 16)
    p.quadTo(ox - 190, oy + 10, ox - 158, oy + 70)
    pen = skia.Paint(AntiAlias=True, Color4f=c4(T["arrow"]), Style=skia.Paint.kStroke_Style, StrokeWidth=4,
                     StrokeCap=skia.Paint.kRound_Cap)
    c.drawPath(p, pen)
    c.drawLine(ox - 158, oy + 70, ox - 176, oy + 54, pen)
    c.drawLine(ox - 158, oy + 70, ox - 150, oy + 48, pen)


def mid_overlay():
    """Above the ORIGINAL card, below the VIBE EDITED card: its border + the big card's shadow."""
    arr, c = layer()
    c.save()
    c.concat(small_card_matrix())
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeWH(SW_, SH_), RAD, RAD),
                skia.Paint(AntiAlias=True, Color4f=c4(*T["small_border"]), Style=skia.Paint.kStroke_Style, StrokeWidth=3))
    # muted wash so the eye goes to the edit
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeWH(SW_, SH_), RAD, RAD), skia.Paint(AntiAlias=True, Color4f=c4(*T["small_wash"])))
    c.restore()
    big = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(BX, BY, BW, BH), RAD, RAD)
    shadow(c, big, 34, T["shadow"][1], 22)
    if WHITE_THEME:
        # yellow offset "sticker" plate behind the edit
        c.save()
        c.translate(14, 14)
        c.drawRRect(big, skia.Paint(AntiAlias=True, Color4f=c4(YEL)))
        c.drawRRect(big, skia.Paint(AntiAlias=True, Color4f=c4(INK), Style=skia.Paint.kStroke_Style, StrokeWidth=4))
        c.restore()
    return arr


def top_overlay():
    arr, c = layer()
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(BX, BY, BW, BH), RAD, RAD)
    if WHITE_THEME:
        c.drawRRect(rr, skia.Paint(AntiAlias=True, Color4f=c4(INK), Style=skia.Paint.kStroke_Style, StrokeWidth=5))
    else:
        glow = skia.Paint(AntiAlias=True, Color4f=c4(YEL, 0.45), Style=skia.Paint.kStroke_Style, StrokeWidth=10)
        glow.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14))
        c.drawRRect(rr, glow)
        c.drawRRect(rr, skia.Paint(AntiAlias=True, Color4f=c4(YEL), Style=skia.Paint.kStroke_Style, StrokeWidth=5))
    # glass sheen on the big card
    c.save()
    c.clipRRect(rr, True)
    c.drawPaint(skia.Paint(Shader=skia.GradientShader.MakeLinear(
        [skia.Point(BX, BY), skia.Point(BX + BW * 0.6, BY + BH * 0.35)],
        [c4(WHITE, 0.10).toColor(), c4(WHITE, 0.0).toColor()])))
    c.restore()
    labels(c)
    return arr


def rr_mask(w, h):
    arr = np.zeros((h, w, 4), np.uint8)
    skia.Surface(arr).getCanvas().drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeWH(w, h), RAD, RAD),
                                            skia.Paint(AntiAlias=True, Color4f=c4(WHITE)))
    return arr[..., 3].astype(np.float32) / 255


def reader(path):
    return subprocess.Popen([FFMPEG, "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                            stdout=subprocess.PIPE)


def split(ov):
    return ov[..., :3].astype(np.float32), ov[..., 3:4].astype(np.float32) / 255


def main():
    bg = background()
    mid_c, mid_a = split(mid_overlay())
    top_c, top_a = split(top_overlay())
    bm = rr_mask(BW, BH)[..., None]
    # tilted small card: warp card pixels into the canvas with the same matrix the shadow used
    sm = small_card_matrix()
    M = np.array([[sm.getScaleX(), sm.getSkewX(), sm.getTranslateX()],
                  [sm.getSkewY(), sm.getScaleY(), sm.getTranslateY()]], np.float32)
    smask = cv2.warpAffine(rr_mask(SW_, SH_), M, (RW, RH), flags=cv2.INTER_LINEAR)[..., None]
    raw = reader(os.path.join(OUT, "trimmed_raw.mp4"))
    edt = reader(os.path.join(OUT, "final.mp4"))
    out = os.path.join(OUT, "comparison_reel_white.mp4" if WHITE_THEME else "comparison_reel.mp4")
    enc = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{RW}x{RH}",
                            "-r", str(FPS), "-i", "-", "-i", os.path.join(OUT, "final.mp4"), "-map", "0:v", "-map", "1:a",
                            "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-maxrate", "16M", "-bufsize", "32M",
                            "-profile:v", "high", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", "-b:a", "256k",
                            "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    n = 0
    fsz = W * H * 3
    while True:
        a = raw.stdout.read(fsz)
        b = edt.stdout.read(fsz)
        if len(a) < fsz or len(b) < fsz:
            break
        fr = bg.copy()
        small = cv2.resize(np.frombuffer(a, np.uint8).reshape(H, W, 3), (SW_, SH_), interpolation=cv2.INTER_AREA)
        sw = cv2.warpAffine(small, M, (RW, RH), flags=cv2.INTER_LINEAR).astype(np.float32)
        fr = fr * (1 - smask) + sw * smask
        fr = fr * (1 - mid_a) + mid_c * mid_a
        big = cv2.resize(np.frombuffer(b, np.uint8).reshape(H, W, 3), (BW, BH), interpolation=cv2.INTER_AREA)
        reg = fr[BY:BY + BH, BX:BX + BW]
        fr[BY:BY + BH, BX:BX + BW] = reg * (1 - bm) + big.astype(np.float32) * bm
        fr = fr * (1 - top_a) + top_c * top_a
        enc.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
        n += 1
    enc.stdin.close()
    enc.wait()
    print("wrote", out, n, "frames")


if __name__ == "__main__":
    main()
