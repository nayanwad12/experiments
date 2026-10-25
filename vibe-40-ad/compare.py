"""Comparison reel: the raw take next to the finished edit, moment for moment, on the final mix.

    python3 compare.py render      -> out/vibe40_ad_comparison.mp4   (needs out/vibe40_ad.mp4 + work/mix.wav)
    python3 compare.py sheet 2 10 20

Left: the untouched phone frame the edit is using at that instant (it runs 1.15x, like the edit).
Right: the final edit. Under them the raw timeline (kept / removed), the edit timeline, and live counters.
"""

import math
import sys

import skia

import core as E
import kit
import reel as R
from kit import fill

W, H = E.W, E.H
FINAL = kit.Layer(E.HERE / "out" / "vibe40_ad.mp4", fps=E.FPS)
SRC1 = E.NSRC / E.SRC_FPS
RUNS = sorted(E.EDL, key=lambda r: r[0])
GAPS = [(0.0, RUNS[0][0])] + [(a[1], b[0]) for a, b in zip(RUNS, RUNS[1:]) if b[0] - a[1] > 0.02] \
    + [(RUNS[-1][1], SRC1)]
YEL, WHITE, INK = R.YEL, R.WHITE, R.INK


def _silence(a, b):
    if b <= a:
        return 0.0
    speech = sum(max(0.0, min(b, w["e"]) - max(a, w["s"])) for w in E.WORDS)
    return max(0.0, (b - a) - speech)


BOUNDS = []                                  # (output time, dead air removed, is a pause)
for prev, nxt in zip(E.EDL, E.EDL[1:]):
    sil = _silence(prev[1], nxt[0])
    BOUNDS.append((nxt[2] / E.SPEED, sil, sil > 0.05))


def stats(t):
    cuts = sum(1 for o, _, _ in BOUNDS if t >= o)
    pauses = sum(1 for o, _, p in BOUNDS if t >= o and p)
    rem = sum(r for o, r, _ in BOUNDS if t >= o)
    return cuts, pauses, rem


def label(c, s, x, y, size=34, bg="#000000", fg=WHITE):
    w = kit.measure(s, "bold", size)
    c.drawRect(skia.Rect.MakeXYWH(x - w / 2 - 14, y - size - 8, w + 28, size + 24), fill(bg))
    kit.text(c, s, x, y + 2, "bold", size, color=fg)


def panel(c, img, x, y, w, h):
    rr = kit.rrect(x, y, w, h, 24)
    c.drawRRect(rr.makeOffset(0, 10), fill("#000000", 0.45, blur=18))
    c.save()
    c.clipRRect(rr, skia.ClipOp.kIntersect, True)
    c.drawImageRect(img, skia.Rect.MakeXYWH(x, y, w, h), R.SAMP)
    c.restore()
    c.drawRRect(rr, kit.stroke(WHITE, 3, 0.9))


def draw(c, t, f):
    src_t = E.src_at(t)
    c.clear(R.col("#2E3738"))
    room = skia.Paint(ImageFilter=skia.ImageFilters.Blur(40, 40))
    room.setAlphaf(0.55)
    c.drawImageRect(R.Src(src_t).img(), skia.Rect.MakeWH(W, H), R.SAMP, room)
    c.drawRect(skia.Rect.MakeWH(W, H), fill("#000000", 0.35))
    cap = R.fit("EDITED", 800, 130)[1]
    R.hand(c, "WHAT I RECORDED  VS", 500, 350 - cap - 34, 36, 1.0)
    R.big_type(c, "EDITED", 500, 350, 10, 0, maxw=800, size=130)
    pw, ph = 400, 711
    y0 = 420
    panel(c, R.Src(src_t).raw(), 75, y0, pw, ph)
    panel(c, FINAL.image(f), 525, y0, pw, ph)
    label(c, "RAW", 275, y0 + 50)
    label(c, "EDITED", 725, y0 + 50, bg=YEL, fg=INK)
    if t >= E.SPEECH_END + 0.3:
        label(c, "end card", 725, y0 + ph - 30, 26)
    # raw timeline
    tx, tw = 75, 850
    ty = 1210
    kit.text(c, f"raw take  0:{int(round(SRC1)):02d}", tx, ty - 18, "bold", 26, color=WHITE, anchor="l")
    c.drawRRect(kit.rrect(tx, ty, tw, 50, 10), fill("#000000", 0.6))
    for a, b in GAPS:
        c.drawRect(skia.Rect.MakeXYWH(tx + tw * a / SRC1, ty + 4, max(3, tw * (b - a) / SRC1), 42), fill("#FF4D3D"))
    for a, b, o, d, i0, i1 in RUNS:
        x0, x1 = tx + tw * a / SRC1, tx + tw * b / SRC1
        c.drawRect(skia.Rect.MakeXYWH(x0, ty + 4, x1 - x0, 42), fill(WHITE if t >= o / E.SPEED else "#5A6466"))
    px = tx + tw * src_t / SRC1
    c.drawRect(skia.Rect.MakeXYWH(px - 3, ty - 8, 6, 66), fill(YEL))
    kit.text(c, "kept", tx + tw, ty - 18, "medium", 22, color=WHITE, anchor="r")
    c.drawRect(skia.Rect.MakeXYWH(tx + tw - 70, ty - 36, 16, 16), fill(WHITE))
    kit.text(c, "removed", tx + tw - 90, ty - 18, "medium", 22, color=WHITE, anchor="r")
    c.drawRect(skia.Rect.MakeXYWH(tx + tw - 200, ty - 36, 16, 16), fill("#FF4D3D"))
    ty2 = ty + 100
    ew = tw * E.TOTAL / SRC1
    kit.text(c, f"edit  0:{int(round(E.TOTAL)):02d}  at {E.SPEED}x", tx, ty2 - 18, "bold", 26, color=WHITE,
             anchor="l")
    c.drawRRect(kit.rrect(tx, ty2, ew, 50, 10), fill("#000000", 0.6))
    c.drawRRect(kit.rrect(tx, ty2, max(10, ew * t / E.TOTAL), 50, 10), fill(YEL))
    for o, _, _ in BOUNDS:
        c.drawRect(skia.Rect.MakeXYWH(tx + ew * o / E.TOTAL - 1, ty2 + 4, 2, 42), fill(INK, 0.5))
    # counters
    cuts, pauses, rem = stats(t)
    saved = (src_t - E.EDL[0][0]) - t + 0.0           # raw seconds covered minus edit seconds elapsed
    vals = [(f"{pauses}", "pauses cut"), (f"{rem:.1f}s", "dead air gone"), (f"{max(0.0, saved):.1f}s", "time saved")]
    for j, (v, lab) in enumerate(vals):
        cx = 500 + (j - 1) * 290
        cy = 1420
        rr = kit.rrect(cx - 135, cy - 70, 270, 140, 22)
        c.drawRRect(rr.makeOffset(0, 8), fill("#000000", 0.35, blur=14))
        c.drawRRect(rr, fill(YEL if j == 0 else WHITE))
        kit.text(c, v, cx, cy + 14, "wide", 58, color=INK)
        kit.text(c, lab, cx, cy + 50, "bold", 22, color="#55585F")
    return {}


def post(rgb, g, f):
    return kit.grain(rgb, f, amt=0.012, scale=2)


FILM = kit.Film(draw, E.TOTAL, E.FPS, post=post, out_dir=E.HERE / "out")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "sheet":
        FILM.sheet([float(x) for x in sys.argv[2:]], cols=4, scale=0.4, name="cmp_sheet.png")
    else:
        pic = FILM.render(E.HERE / "out" / "comparison_picture.mp4")
        E.finish(pic, E.HERE / "work" / "mix.wav", E.HERE / "out" / "vibe40_ad_comparison.mp4")
