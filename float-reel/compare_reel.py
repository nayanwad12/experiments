"""Comparison reel for the floating-UI cut: raw take beside the edit, in sync with the final audio.

    python3 compare_reel.py stills 5 30 ...   -> out/stills/c_*.png
    python3 compare_reel.py render            -> out/vibe_float_comparison.mp4
"""

import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reel as R  # noqa: E402
from style import (GREEN, GREYUI, INK, LAV, LIME, RED, SAMP, WHITE, YEL, clamp, fill, font, kit, measure,  # noqa: E402
                   pill, rrect, scribble, soft_shadow, stroke, text)

cut = R.cut
W, H, FPS = 1080, 1920, 30
OUT = HERE / "out"
EDIT = kit.Layer(OUT / "picture.mp4", fps=FPS)
TOTAL = R.TOTAL
RAW_DUR = 82.37
REMOVED = [(a, b, why) for a, b, why in cut.removed() if b - a > 0.05]
PW, PH = 430, 764
LX, RX, PY = 82, 568, 540


def bg():
    if not hasattr(bg, "img"):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - 700) / H) ** 2)
        v = np.clip(58 - 40 * r, 18, 60)
        arr = np.dstack([v * 0.92, v * 0.98, v * 1.06, np.full_like(v, 255)]).astype(np.uint8)
        bg.img = skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType)
    return bg.img


def raw_frame(ts):
    img = R.SK.frame_rgb(int(round(ts * FPS)))
    small = cv2.resize(img, (PW, PH), interpolation=cv2.INTER_AREA)
    return skia.Image.fromarray(np.dstack([small, np.full((PH, PW), 255, np.uint8)]), colorType=skia.kRGBA_8888_ColorType)


def phone(c, x, y, img, label, bgc, fg):
    r = rrect(x - 12, y - 12, PW + 24, PH + 24, 44)
    soft_shadow(c, r.rect(), 1.0, 44)
    c.drawRRect(r, fill("#0D0E10"))
    c.save()
    c.clipRRect(rrect(x, y, PW, PH, 34), True)
    c.drawImageRect(img, skia.Rect(x, y, x + PW, y + PH), SAMP)
    c.restore()
    c.drawRRect(rrect(x + PW / 2 - 55, y + 12, 110, 24, 12), fill("#0D0E10"))
    c.save()
    c.translate(x + PW / 2, y - 50)
    pill(c, 210, 64, bgc, label, fg, size=30, name="uib")
    c.restore()


def stats(t):
    ts = cut.src_at(min(t, cut.SPEECH_END))
    passed = [r for r in REMOVED if r[1] <= ts + 0.02 and t > 0.05]
    return (ts, sum(1 for r in passed if r[2] == "pause"), sum(1 for r in passed if r[2] != "pause"),
            sum(r[1] - r[0] for r in passed), sum(1 for x in cut.CUT_TIMES if x <= t + 1e-6))


def counter(c, x, y, value, label, colr, flash):
    k = clamp(1 - flash / 0.25) if flash >= 0 else 0
    c.save()
    c.translate(x, y)
    s = 1 + 0.05 * k
    c.scale(s, s)
    r = rrect(-125, -78, 250, 150, 28)
    soft_shadow(c, r.rect(), 1.0, 28)
    c.drawRRect(r, fill(colr))
    text(c, str(value), 0, 18, "wide", 52, INK, anchor="c")
    text(c, label, 0, 54, "uib", 20, INK, 0.75, anchor="c")
    c.restore()


def draw(c, t, f):
    c.drawImage(bg(), 0, 0)
    text(c, "RAW TAKE", W / 2, 270, "hand", 84, WHITE, anchor="c")
    text(c, "VS EDIT", W / 2, 378, "wide", 110, YEL, anchor="c")
    scribble(c, W / 2 + 20, 414, 360, 1.0, "#000000", 7, seed=2, a=0.8)
    ts, pauses, starts, saved, cuts = stats(t)
    phone(c, LX, PY, raw_frame(ts), "RAW", "#3A3D42", WHITE)
    phone(c, RX, PY, EDIT.image(f), "EDITED", YEL, INK)
    last_cut = max([x for x in cut.CUT_TIMES if x <= t] or [-9])
    if t - last_cut < 0.3:
        k = 1 - (t - last_cut) / 0.3
        c.drawRRect(rrect(LX, PY, PW, PH, 34), stroke(RED, 12, k))
        c.save()
        c.translate(LX + PW / 2, PY + PH * 0.78)
        pill(c, 170, 70, RED, "CUT", WHITE, a=clamp(k * 2), size=36, name="uib")
        c.restore()
    y0 = 1430
    lp = max([r[1] for r in REMOVED if r[1] <= ts + 0.02 and r[2] == "pause"] or [-9])
    counter(c, 225, y0, cuts, "CUTS", LIME, t - last_cut)
    counter(c, 495, y0, pauses, "PAUSES CUT", LAV, (ts - lp) if lp > 0 else -1)
    counter(c, 765, y0, f"{saved:.1f}s", "TIME SAVED", YEL, t - last_cut)
    x0, x1, yy = 100, 900, 1575
    c.drawRRect(rrect(x0 - 14, yy - 20, x1 - x0 + 28, 40, 20), fill("#121316"))
    for a, b, why in REMOVED:
        xa, xb = x0 + (x1 - x0) * a / RAW_DUR, x0 + (x1 - x0) * b / RAW_DUR
        c.drawRRect(rrect(xa, yy - 10, max(xb - xa, 3), 20, 4), fill(RED if why == "pause" else WHITE, 0.9))
    xp = x0 + (x1 - x0) * ts / RAW_DUR
    c.drawRRect(rrect(xp - 4, yy - 26, 8, 52, 4), fill(GREEN))
    c.drawCircle(x0, yy - 50, 8, fill(RED))
    text(c, "pause cut", x0 + 16, yy - 42, "ui", 22, GREYUI)
    c.drawCircle(x0 + 170, yy - 50, 8, fill(WHITE))
    text(c, "false start cut", x0 + 186, yy - 42, "ui", 22, GREYUI)
    text(c, f"{starts} false starts gone", x1, yy - 42, "uib", 22, WHITE, anchor="r")
    return {"t": t}


FILM = kit.Film(draw, dur=TOTAL, fps=FPS, out_dir=str(OUT))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "stills":
        from PIL import Image
        d = OUT / "stills"
        d.mkdir(parents=True, exist_ok=True)
        for t in map(float, sys.argv[2:]):
            Image.fromarray(FILM.frame(t, 0.5)).save(d / f"c_{t:06.2f}.png")
        print("->", d)
    else:
        pic = FILM.render(OUT / "compare_picture.mp4")
        out = OUT / "vibe_float_comparison.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(pic), "-i", str(HERE / "work" / "mix.wav"),
                        "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", "22",
                        "-maxrate", "3000k", "-bufsize", "6000k", "-pix_fmt", "yuv420p", "-profile:v", "high",
                        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", "-shortest",
                        str(out)], check=True)
        print("->", out)


if __name__ == "__main__":
    main()
