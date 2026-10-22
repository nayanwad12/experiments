"""Comparison reel: the raw take beside the final edit, in sync with the final audio.

    python3 compare.py stills 5 30 ...   -> out/stills/c_*.png
    python3 compare.py render            -> out/vibe_editing_comparison.mp4

The raw panel plays the source frame behind every edited frame (so it jumps where the edit cuts); the strip under
the phones is the whole raw take with every removed stretch in red, and the counters tick up as each cut passes.
"""

import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cut  # noqa: E402
import edit as E  # noqa: E402
from theme import (INK, PINK, RED, SAMP, WHITE, YEL, Sticker, clamp, fill, font, hand, kit, label_sticker,  # noqa: E402
                   measure, paper, pink_word, ink_word, rrect, stroke, tape, type_text)

W, H, FPS = 1080, 1920, 30
OUT = HERE / "out"
EDIT = kit.Layer(OUT / "picture.mp4", fps=FPS)
TOTAL = E.TOTAL
RAW_DUR = 82.37
REMOVED = [(a, b, why) for a, b, why in cut.removed() if b - a > 0.05]
PW, PH = 430, 764                      # each phone screen (9:16)
LX, RX, PY = 82, 568, 530             # screen positions


def raw_frame(ts):
    fi = int(clamp(round(ts * FPS), 0, E.NSRC - 1))
    img = E.frame_rgb(fi)
    small = cv2.resize(img, (PW, PH), interpolation=cv2.INTER_AREA)
    return skia.Image.fromarray(np.dstack([small, np.full((PH, PW), 255, np.uint8)]), colorType=skia.kRGBA_8888_ColorType)


def phone(c, x, y, img, label, bg, fg, rot):
    c.save()
    c.translate(x + PW / 2, y + PH / 2)
    c.rotate(rot)
    c.translate(-PW / 2, -PH / 2)
    with Sticker(c, (-16, -16, PW + 16, PH + 16), border=10):
        c.drawRRect(rrect(-14, -14, PW + 28, PH + 28, 46), fill("#111114"))
    c.save()
    c.clipRRect(rrect(0, 0, PW, PH, 34), True)
    c.drawImageRect(img, skia.Rect(0, 0, PW, PH), SAMP)
    c.restore()
    c.drawRRect(rrect(PW / 2 - 55, 12, 110, 24, 12), fill("#111114"))
    c.restore()
    label_sticker(c, label, x + PW / 2, y - 44, 44, 99, 0, rot=-rot * 2, bg=bg, fg=fg, name="cond")


def stats(t):
    ts = cut.src_at(min(t, cut.SPEECH_END))
    passed = [r for r in REMOVED if r[1] <= ts + 0.02 and t > 0.05]
    pauses = sum(1 for r in passed if r[2] == "pause")
    starts = sum(1 for r in passed if r[2] != "pause")
    saved = sum(r[1] - r[0] for r in passed)
    cuts = sum(1 for x in cut.CUT_TIMES if x <= t + 1e-6)
    return ts, pauses, starts, saved, cuts


def counter(c, x, y, value, label, color, t_flash):
    c.save()
    k = clamp(1 - t_flash / 0.25) if t_flash >= 0 else 0
    s = 1 + 0.18 * k
    with Sticker(c, (x - 130, y - 82, x + 130, y + 72), border=8):
        c.drawRRect(rrect(x - 125, y - 78, 250, 146, 18), fill(WHITE))
    c.translate(x, y - 6)
    c.scale(s, s)
    v = str(value)
    pink_word(c, v, -measure(v, "pink", 76) / 2, 18, 76, 1.0, color=color)
    c.restore()
    type_text(c, label, x, y + 50, 22, color=INK, anchor="c")


def draw(c, t, f):
    paper(c, "lined")
    # title
    ink_word(c, "Raw take", 110, 330, 92)
    pink_word(c, "vs edit", 110 + measure("Raw take ", "serif", 92), 330, 100, 1.0)
    hand(c, "same take, same audio, in sync", 540, 405, 50, rot=-1.5)
    ts, pauses, starts, saved, cuts = stats(t)
    phone(c, LX, PY, raw_frame(ts), "RAW", WHITE, INK, -1.5)
    phone(c, RX, PY, EDIT.image(f), "EDITED", PINK, WHITE, 1.5)
    # cut flash on the raw panel
    last_cut = max([x for x in cut.CUT_TIMES if x <= t] or [-9])
    if t - last_cut < 0.3:
        k = 1 - (t - last_cut) / 0.3
        c.save()
        c.translate(LX + PW / 2, PY + PH / 2)
        c.rotate(-1.5)
        c.drawRRect(rrect(-PW / 2, -PH / 2, PW, PH, 34), stroke(RED, 14, k))
        label_sticker(c, "CUT", 0, 250, 70, 99, 0, rot=-8, bg=RED, fg=WHITE, name="cond") if k > 0.3 else None
        c.restore()
    # counters
    y0 = 1410
    tc = t - last_cut
    lp = max([r[1] for r in REMOVED if r[1] <= ts + 0.02 and r[2] == "pause"] or [-9])
    counter(c, 205, y0, cuts, "CUTS", PINK, tc)
    counter(c, 475, y0, pauses, "PAUSES CUT", YEL, (ts - lp) if lp > 0 else -1)
    counter(c, 745, y0, f"{saved:.1f}s", "TIME SAVED", "#7FB6D9", tc)
    # raw timeline strip
    x0, x1, yy = 90, 910, 1552
    type_text(c, "RAW TAKE:", x0, yy - 36, 21, color=INK)
    c.drawRect(skia.Rect(x0 + 150, yy - 52, x0 + 168, yy - 34), fill(RED))
    type_text(c, "pause cut", x0 + 176, yy - 36, 21, color=INK)
    c.drawRect(skia.Rect(x0 + 330, yy - 52, x0 + 348, yy - 34), fill(INK))
    type_text(c, "false start cut", x0 + 356, yy - 36, 21, color=INK)
    c.drawRRect(rrect(x0 - 8, yy - 22, x1 - x0 + 16, 44, 10), fill(WHITE))
    for a, b, why in REMOVED:
        xa, xb = x0 + (x1 - x0) * a / RAW_DUR, x0 + (x1 - x0) * b / RAW_DUR
        c.drawRect(skia.Rect(xa, yy - 14, max(xb, xa + 2), yy + 14), fill(RED if why == "pause" else INK, 0.85))
    xp = x0 + (x1 - x0) * ts / RAW_DUR
    c.drawRect(skia.Rect(xp - 3, yy - 30, xp + 3, yy + 30), fill(PINK))
    type_text(c, f"RAW 0:{ts:05.2f}", x0, yy + 54, 22, color=INK)
    type_text(c, f"{starts} FALSE STARTS GONE", x1, yy + 54, 22, color=RED, anchor="r")
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
        out = OUT / "vibe_editing_comparison.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(pic), "-i", str(HERE / "work" / "mix.wav"),
                        "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", "22",
                        "-maxrate", "3000k", "-bufsize", "6000k", "-pix_fmt", "yuv420p", "-profile:v", "high",
                        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", "-shortest",
                        str(out)], check=True)
        print("->", out)


if __name__ == "__main__":
    main()
