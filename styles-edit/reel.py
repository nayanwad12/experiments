"""9:16 Instagram Reel: the untouched take above the AI edit, frame-for-frame in sync, with the edit's sound.
All content sits inside the Reels safe zone (220 px top, 420 px bottom, 35 px left, 120 px right).

    python3 reel.py  ->  out/comparison_reel.mp4 (1080x1920, 30 fps)
"""

import os
import subprocess

import cv2
import numpy as np
import skia

from common import FFMPEG, FONTS, FPS, OUT, H, W

RW, RH = 1080, 1920
# Instagram Reels safe zone (1080x1920): 220 px clear at the top, 420 px at the bottom (caption/username),
# 35 px at the left and 120 px at the right (like/comment/share column) -> content lives in x 35..960, y 220..1500
SAFE_L, SAFE_R = 35, RW - 120
SAFE_T, SAFE_B = 220, RH - 420
ZX = (SAFE_L + SAFE_R) / 2                                # horizontal centre of the safe zone
CW = SAFE_R - SAFE_L                                      # 925
CH = round(CW * H / W)                                    # 16:9 card -> 520
CX = SAFE_L
GAP = 22
BOT = (CX, SAFE_B - CH)                                   # vibe edited, ends exactly on the safe line
TOP = (CX, BOT[1] - GAP - CH)                             # original
HEAD = (SAFE_T, TOP[1])                                   # headline band 220 .. 438
RAD = 30
INK, YEL, WHITE = (17, 17, 20), (255, 210, 63), (255, 255, 255)


def c4(rgb, a=1.0):
    return skia.Color4f(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, a)


def tf(name):
    return skia.Typeface.MakeFromFile(os.path.join(FONTS, name + ".ttf"))


def text(c, s, x, y, face, size, fill, align="c", track=0.0):
    f = skia.Font(face, size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    glyphs = f.textToGlyphs(s)
    widths = f.getWidths(glyphs)
    w = sum(widths) + track * size * (len(s) - 1)
    x0 = x - w / 2 if align == "c" else x
    b = skia.TextBlobBuilder()
    pos, xx = [], 0.0
    for gw in widths:
        pos.append(skia.Point(xx, 0))
        xx += gw + track * size
    b.allocRunPos(f, glyphs, pos)
    c.drawTextBlob(b.make(), x0, y, skia.Paint(AntiAlias=True, Color4f=c4(fill)))
    return w


def sparkle(c, x, y, r, rgb):
    p = skia.Path()
    for i in range(8):
        import math
        a = math.radians(-90 + 45 * i)
        rr = r if i % 2 == 0 else r * 0.28
        (p.moveTo if i == 0 else p.lineTo)(x + rr * math.cos(a), y + rr * math.sin(a))
    p.close()
    c.drawPath(p, skia.Paint(AntiAlias=True, Color4f=c4(rgb)))


def background():
    arr = np.zeros((RH, RW, 4), np.uint8)
    s = skia.Surface(arr)
    c = s.getCanvas()
    c.drawPaint(skia.Paint(Shader=skia.GradientShader.MakeRadial(
        skia.Point(RW * 0.5, RH * 0.42), RH * 0.75,
        [skia.Color4f(0.13, 0.11, 0.22, 1).toColor(), skia.Color4f(0.03, 0.03, 0.06, 1).toColor()])))
    dot = skia.Paint(AntiAlias=True, Color4f=c4(WHITE, 0.07))
    for x in range(0, RW + 1, 40):
        for y in range(0, RH + 1, 40):
            c.drawCircle(x, y, 1.5, dot)
    # headline
    black = tf("Montserrat-Black")
    fs = 80
    band0, band1 = HEAD
    block = 58 + 92 + 50                                   # line1 cap + line gap + subtitle
    top = band0 + (band1 - band0 - block) / 2              # centre the headline block in its band
    y1 = top + 58
    y = y1 + 92
    text(c, "Fully Edited", ZX, y1, black, fs, WHITE)
    fnt = skia.Font(black, fs)
    x0 = ZX - fnt.measureText("by AI") / 2
    wb = fnt.measureText("by ")
    wai = fnt.measureText("AI")
    text(c, "by ", x0, y, black, fs, WHITE, "l")
    hl = skia.RRect.MakeRectXY(skia.Rect(x0 + wb - 11, y - 66, x0 + wb + wai + 11, y + 12), 12, 12)
    c.drawRRect(hl, skia.Paint(AntiAlias=True, Color4f=c4(YEL)))
    text(c, "AI", x0 + wb, y, black, fs, INK, "l")
    sparkle(c, x0 + wb + wai + 36, y - 60, 20, YEL)
    sparkle(c, x0 - 30, y - 74, 12, WHITE)
    text(c, "5 STYLES  ·  ZERO EDITING", ZX, y + 48, tf("SpaceGrotesk-Bold"), 24, (185, 180, 215), track=0.08)
    # card shadows
    for (x, yy) in (TOP, BOT):
        sh = skia.Paint(AntiAlias=True, Color4f=c4((0, 0, 0), 0.6))
        sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 24))
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, yy + 14, CW, CH), RAD, RAD), sh)
    return arr[..., :3].copy()


def overlay():
    """Borders + tags drawn over the cards (RGBA)."""
    arr = np.zeros((RH, RW, 4), np.uint8)
    s = skia.Surface(arr)
    c = s.getCanvas()
    for (x, y), fill, fg, label, border in ((TOP, (236, 236, 240), INK, "ORIGINAL", (255, 255, 255, 0.35)),
                                            (BOT, YEL, INK, "VIBE EDITED", (255, 210, 63, 1.0))):
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, CW, CH), RAD, RAD),
                    skia.Paint(AntiAlias=True, Color4f=c4(border[:3], border[3]), Style=skia.Paint.kStroke_Style,
                               StrokeWidth=4 if label == "VIBE EDITED" else 2.5))
        face = tf("Montserrat-Black")
        size = 25
        f = skia.Font(face, size)
        tw = f.measureText(label) + 0.08 * size * (len(label) - 1)
        extra = 30 if label == "VIBE EDITED" else 0
        chip = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x + 22, y + 22, tw + 36 + extra, 46), 23, 23)
        sh = skia.Paint(AntiAlias=True, Color4f=c4((0, 0, 0), 0.45))
        sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8))
        c.drawRRect(chip, sh)
        c.drawRRect(chip, skia.Paint(AntiAlias=True, Color4f=c4(fill)))
        if extra:
            sparkle(c, x + 22 + 26, y + 45, 11, INK)
        text(c, label, x + 22 + 18 + extra, y + 22 + 33, face, size, fg, "l", track=0.08)
    return arr


def card_mask():
    m = np.zeros((CH, CW), np.uint8)
    s = skia.Surface(np.zeros((CH, CW, 4), np.uint8))
    arr = np.zeros((CH, CW, 4), np.uint8)
    s = skia.Surface(arr)
    s.getCanvas().drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeWH(CW, CH), RAD, RAD),
                            skia.Paint(AntiAlias=True, Color4f=c4(WHITE)))
    m = arr[..., 3].astype(np.float32) / 255
    return m[..., None]


def reader(path):
    return subprocess.Popen([FFMPEG, "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                            stdout=subprocess.PIPE)


def main():
    bg = background().astype(np.float32)
    ov = overlay()
    oa = ov[..., 3:4].astype(np.float32) / 255
    ovc = ov[..., :3].astype(np.float32)
    m = card_mask()
    raw = reader(os.path.join(OUT, "trimmed_raw.mp4"))
    edt = reader(os.path.join(OUT, "final.mp4"))
    out = os.path.join(OUT, "comparison_reel.mp4")
    enc = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{RW}x{RH}",
                            "-r", str(FPS), "-i", "-", "-i", os.path.join(OUT, "final.mp4"), "-map", "0:v", "-map", "1:a",
                            "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-maxrate", "14M", "-bufsize", "28M",
                            "-profile:v", "high", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                            "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    n = 0
    fsz = W * H * 3
    while True:
        a = raw.stdout.read(fsz)
        b = edt.stdout.read(fsz)
        if len(a) < fsz or len(b) < fsz:
            break
        fr = bg.copy()
        for buf, (x, y) in ((a, TOP), (b, BOT)):
            img = cv2.resize(np.frombuffer(buf, np.uint8).reshape(H, W, 3), (CW, CH), interpolation=cv2.INTER_AREA)
            reg = fr[y:y + CH, x:x + CW]
            fr[y:y + CH, x:x + CW] = reg * (1 - m) + img.astype(np.float32) * m
        fr = fr * (1 - oa) + ovc * oa
        enc.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
        n += 1
    enc.stdin.close()
    enc.wait()
    print("wrote", out, n, "frames")


if __name__ == "__main__":
    main()
