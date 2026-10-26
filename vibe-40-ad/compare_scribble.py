"""Comparison reel for the scribble edit: raw take next to vibe40_scribble, moment for moment, on its mix.

    python3 compare_scribble.py render   -> out/vibe40_scribble_comparison.mp4  (needs out/vibe40_scribble.mp4 + work/scribble_mix.wav)
    python3 compare_scribble.py sheet 2 10 20

Same counters as compare.py; dressed like the scribble edit: retro desktop, raw.mov / edited.mp4 windows,
a marker title, VT323 counters.
"""

import sys

import skia

import compare as C0
import core as E
import kit
import scribble as S
from kit import fill

W, H = E.W, E.H
FINAL = kit.Layer(E.HERE / "out" / "vibe40_scribble.mp4", fps=E.FPS)
SRC1 = C0.SRC1


def draw(c, t, f):
    src_t = E.src_at(t)
    c.drawRect(skia.Rect.MakeWH(W, H), fill(S.DESK))
    S.word_caps(c, "WHAT I RECORDED VS", 540, 205, 60, S.WHITE)
    S.marker(c, "THE EDIT", 540, 340, 10, 0, 150, S.YEL)
    pw, ph = 400, 711
    for x, title, img in ((60, "raw.mov", S.Src(src_t).raw()), (560, "edited.mp4", FINAL.image(f))):
        S.window(c, x, 400, pw + 24, ph + 68, title, 1.0)
        c.drawImageRect(img, skia.Rect.MakeXYWH(x + 12, 456, pw, ph), S.SAMP)
        S.end_window(c)
    # timelines
    tx, tw = 80, 920
    ty = 1240
    kit.text(c, f"raw take 0:{int(round(SRC1)):02d}", tx, ty - 12, "vt", 38, color=S.WHITE, anchor="l")
    S.bevel(c, tx, ty, tw, 46, up=False)
    for a, b in C0.GAPS:
        c.drawRect(skia.Rect.MakeXYWH(tx + tw * a / SRC1, ty + 6, max(3, tw * (b - a) / SRC1), 34), fill(S.RED))
    for a, b, o, d, i0, i1 in C0.RUNS:
        x0, x1 = tx + tw * a / SRC1, tx + tw * b / SRC1
        c.drawRect(skia.Rect.MakeXYWH(x0, ty + 6, x1 - x0, 34), fill(S.BLUE if t >= o / E.SPEED else "#7B7B7B"))
    px = tx + tw * src_t / SRC1
    c.drawRect(skia.Rect.MakeXYWH(px - 3, ty - 6, 6, 58), fill(S.YEL))
    ty2 = ty + 90
    ew = tw * E.TOTAL / SRC1
    kit.text(c, f"edit 0:{int(round(E.TOTAL)):02d} at {E.SPEED}x", tx, ty2 - 12, "vt", 38, color=S.WHITE, anchor="l")
    S.bevel(c, tx, ty2, ew, 46, up=False)
    n = int(20 * t / E.TOTAL)
    for j in range(n):
        c.drawRect(skia.Rect.MakeXYWH(tx + 6 + j * (ew - 12) / 20, ty2 + 6, (ew - 12) / 20 - 4, 34), fill(S.BLUE))
    cuts, pauses, rem = C0.stats(t)
    saved = max(0.0, (src_t - E.EDL[0][0]) - t)
    for j, (v, lab) in enumerate(((f"{pauses}", "pauses cut"), (f"{rem:.1f}s", "dead air"), (f"{saved:.1f}s", "saved"))):
        x = 80 + j * 315
        S.bevel(c, x, 1440, 290, 130)
        kit.text(c, v, x + 145, 1510, "vt", 72, color=S.BLUE)
        kit.text(c, lab, x + 145, 1556, "vt", 34, color=S.INK)
    return {}


def post(rgb, g, f):
    return kit.grain(rgb, f, amt=0.012, scale=2)


FILM = kit.Film(draw, E.TOTAL, E.FPS, post=post, out_dir=E.HERE / "out")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "sheet":
        FILM.sheet([float(x) for x in sys.argv[2:]], cols=4, scale=0.4, name="cmp_scribble_sheet.png")
    else:
        pic = FILM.render(E.HERE / "out" / "scribble_comparison_picture.mp4")
        E.finish(pic, E.HERE / "work" / "scribble_mix.wav", E.HERE / "out" / "vibe40_scribble_comparison.mp4")
