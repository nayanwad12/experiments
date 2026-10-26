"""Comparison reel for the diary edit: the raw take next to vibe40_diary, moment for moment, on its mix.

    python3 compare_diary.py render      -> out/vibe40_diary_comparison.mp4  (needs out/vibe40_diary.mp4 + work/diary_mix.wav)
    python3 compare_diary.py sheet 2 10 20

Same counters as compare.py; dressed like the diary edit: warm blurred room, butter serif words,
polaroid frames with washi tape, paper-note counters.
"""

import sys

import skia

import compare as C0
import core as E
import diary as D
import kit
from kit import fill

W, H = E.W, E.H
FINAL = kit.Layer(E.HERE / "out" / "vibe40_diary.mp4", fps=E.FPS)
SRC1 = C0.SRC1


def frame_card(c, img, x, y, w, h, label, rot, tape):
    c.save()
    c.translate(x + w / 2, y + h / 2)
    c.rotate(rot)
    c.translate(-w / 2, -h / 2)
    pad = 16
    outer = skia.Path()
    outer.addRect(skia.Rect.MakeXYWH(-pad, -pad, w + 2 * pad, h + 2 * pad + 60))
    D.paper(c, outer, "#FBF8EE")
    c.drawImageRect(img, skia.Rect.MakeXYWH(0, 0, w, h), D.SAMP)
    c.drawRect(skia.Rect.MakeXYWH(w / 2 - 60, -pad - 22, 120, 40), fill(tape, 0.85))
    D.word(c, label, w / 2, h + 50, 64, 1.0, "c", D.INKB, w - 20, seed=len(label), shadow=False)
    c.restore()


def draw(c, t, f):
    src_t = E.src_at(t)
    c.clear(D.col("#3A2E22"))
    room = skia.Paint(ImageFilter=skia.ImageFilters.Blur(40, 40))
    room.setAlphaf(0.6)
    c.drawImageRect(D.Src(src_t).img(), skia.Rect.MakeWH(W, H), D.SAMP, room)
    c.drawRect(skia.Rect.MakeWH(W, H), fill("#1A0F05", 0.3))
    D.word(c, "what I recorded", 500, 330, 110, 1.0, "c", D.BUTTER, 860, seed=1)
    D.word(c, "vs the edit", 500, 440, 110, 1.0, "c", D.BUTTER, 860, seed=2)
    D.star(c, 905, 300, 44, D.PINK, 1.0, -10, 3)
    pw, ph = 380, 676
    y0 = 500
    frame_card(c, D.Src(src_t).raw(), 85, y0, pw, ph, "raw", -2.0, D.PINK)
    frame_card(c, FINAL.image(f), 535, y0, pw, ph, "edited", 2.0, D.SKY)
    # timelines (raw kept / removed, edit progress)
    tx, tw = 80, 840
    ty = 1290
    kit.text(c, f"raw take 0:{int(round(SRC1)):02d}", tx, ty - 14, "bold", 24, color=D.CREAM, anchor="l")
    c.drawRRect(kit.rrect(tx, ty, tw, 40, 10), fill("#1A0F05", 0.55))
    for a, b in C0.GAPS:
        c.drawRect(skia.Rect.MakeXYWH(tx + tw * a / SRC1, ty + 4, max(3, tw * (b - a) / SRC1), 32), fill("#E8A0A8"))
    for a, b, o, d, i0, i1 in C0.RUNS:
        x0, x1 = tx + tw * a / SRC1, tx + tw * b / SRC1
        c.drawRect(skia.Rect.MakeXYWH(x0, ty + 4, x1 - x0, 32), fill(D.BUTTER if t >= o / E.SPEED else "#6B5A44"))
    px = tx + tw * src_t / SRC1
    c.drawRect(skia.Rect.MakeXYWH(px - 3, ty - 6, 6, 52), fill("#FFFFFF"))
    ty2 = ty + 80
    ew = tw * E.TOTAL / SRC1
    kit.text(c, f"edit 0:{int(round(E.TOTAL)):02d} at {E.SPEED}x", tx, ty2 - 14, "bold", 24, color=D.CREAM, anchor="l")
    c.drawRRect(kit.rrect(tx, ty2, ew, 40, 10), fill("#1A0F05", 0.55))
    c.drawRRect(kit.rrect(tx, ty2, max(10, ew * t / E.TOTAL), 40, 10), fill(D.BUTTER))
    # counters on paper notes
    cuts, pauses, rem = C0.stats(t)
    saved = max(0.0, (src_t - E.EDL[0][0]) - t)
    vals = [(f"{pauses}", "pauses cut", D.PINK), (f"{rem:.1f}s", "dead air gone", "#FBF8EE"),
            (f"{saved:.1f}s", "time saved", D.SKY)]
    for j, (v, lab, colr) in enumerate(vals):
        cx = 500 + (j - 1) * 285
        cy = 1500
        note = skia.Path()
        note.addRect(skia.Rect.MakeXYWH(cx - 125, cy - 70, 250, 140))
        c.save()
        c.translate(cx, cy)
        c.rotate((j - 1) * 3)
        c.translate(-cx, -cy)
        D.paper(c, note, colr)
        D.word(c, v, cx, cy + 22, 86, 1.0, "c", D.INKB, 220, seed=j, shadow=False)
        kit.text(c, lab, cx, cy + 56, "bold", 20, color="#5A4636")
        c.restore()
    return {}


def post(rgb, g, f):
    return kit.grain(rgb, f, amt=0.015, scale=2)


FILM = kit.Film(draw, E.TOTAL, E.FPS, post=post, out_dir=E.HERE / "out")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "sheet":
        FILM.sheet([float(x) for x in sys.argv[2:]], cols=4, scale=0.4, name="cmp_diary_sheet.png")
    else:
        pic = FILM.render(E.HERE / "out" / "diary_comparison_picture.mp4")
        E.finish(pic, E.HERE / "work" / "diary_mix.wav", E.HERE / "out" / "vibe40_diary_comparison.mp4")
