"""Comparison reel for the creator-style edit: raw take next to vibe_reel_v2, moment for moment, on its mix.

    python3 compare_v2.py render      -> out/vibe_reel_v2_comparison.mp4   (needs out/vibe_reel_v2.mp4 + work/v2_mix.wav)
    python3 compare_v2.py stills 5 20

Same counters as compare.py (pauses cut, cuts, dead air removed); dressed like the reference: moody room
ground, hand-lettered line + wide italic yellow word, white-on-black label boxes, clean white UI cards.
"""

import math
import sys

import skia

import compare as C0
import creator as CR
import edit as E
import kit
from kit import clamp, e_out, fill, prog

W, H = E.W, E.H
FINAL = kit.Layer(E.OUT / "vibe_reel_v2.mp4", fps=E.FPS)
SRC1 = C0.SRC1
YEL, WHITE, INK, GREEN = CR.YEL, CR.WHITE, CR.INK, CR.GREEN


def label(c, s, x, y, size=34, bg="#000000", fg=WHITE):
    w = kit.measure(s, "bold", size)
    c.drawRect(skia.Rect.MakeXYWH(x - w / 2 - 14, y - size - 8, w + 28, size + 24), fill(bg))
    kit.text(c, s, x, y + 2, "bold", size, color=fg)


def panel(c, img, x, y, w, h, src_rect=None):
    rr = kit.rrect(x, y, w, h, 24)
    c.drawRRect(rr.makeOffset(0, 10), fill("#000000", 0.45, blur=18))
    c.save()
    c.clipRRect(rr, skia.ClipOp.kIntersect, True)
    if src_rect is None:
        c.drawImageRect(img, skia.Rect.MakeXYWH(x, y, w, h), CR.SAMP)
    else:
        c.drawImageRect(img, src_rect, skia.Rect.MakeXYWH(x, y, w, h), CR.SAMP)
    c.restore()
    c.drawRRect(rr, kit.stroke(WHITE, 3, 0.9))


def draw(c, t, f):
    src_t = E.src_at(t)
    # moody room ground: a blurred, relit frame of the take
    c.clear(CR.col("#2E3738"))
    room = skia.Paint(ImageFilter=skia.ImageFilters.Blur(40, 40))
    room.setAlphaf(0.55)
    c.drawImageRect(CR.Src(src_t).img(), skia.Rect.MakeWH(W, H), CR.SAMP, room)
    c.drawRect(skia.Rect.MakeWH(W, H), fill("#000000", 0.35))
    # title, reference style
    cap = CR.fit("EDITED", 900, 130)[1]
    CR.hand(c, "WHAT I RECORDED  VS", 500, 350 - cap - 34, 36, 1.0)
    CR.big_type(c, "EDITED", 500, 350, 10, 0, maxw=800, size=130)
    # panels
    pw, ph = 400, 711
    y0 = 420
    panel(c, CR.Src(src_t).raw(), 75, y0, pw, ph)
    panel(c, FINAL.image(f), 525, y0, pw, ph)
    label(c, "RAW", 275, y0 + 50)
    label(c, "EDITED", 725, y0 + 50, bg=YEL, fg=INK)
    if t < CR.at(E.I_HERE):
        label(c, "hook moved from 1:10 to 0:00", 500, y0 + ph - 30, 26)
    if t >= CR.END_A:
        label(c, "silent tail -> end card", 500, y0 + ph - 30, 26)
    # raw timeline
    tx, tw = 75, 850
    ty = 1210
    kit.text(c, f"raw take  {int(SRC1) // 60}:{int(SRC1) % 60:02d}", tx, ty - 18, "bold", 26, color=WHITE, anchor="l")
    c.drawRRect(kit.rrect(tx, ty, tw, 50, 10), fill("#000000", 0.6))
    for a, b in C0.GAPS:
        c.drawRect(skia.Rect.MakeXYWH(tx + tw * a / SRC1, ty + 4, max(3, tw * (b - a) / SRC1), 42), fill("#FF4D3D"))
    for a, b, o, d, i0, i1 in C0.RUNS:
        x0, x1 = tx + tw * a / SRC1, tx + tw * b / SRC1
        on = t >= o
        c.drawRect(skia.Rect.MakeXYWH(x0, ty + 4, x1 - x0, 42), fill(WHITE if on else "#5A6466"))
    px = tx + tw * src_t / SRC1
    c.drawRect(skia.Rect.MakeXYWH(px - 3, ty - 8, 6, 66), fill(YEL))
    kit.text(c, "kept", tx + tw, ty - 18, "medium", 22, color=WHITE, anchor="r")
    c.drawRect(skia.Rect.MakeXYWH(tx + tw - 70, ty - 36, 16, 16), fill(WHITE))
    kit.text(c, "removed", tx + tw - 90, ty - 18, "medium", 22, color=WHITE, anchor="r")
    c.drawRect(skia.Rect.MakeXYWH(tx + tw - 200, ty - 36, 16, 16), fill("#FF4D3D"))
    ty2 = ty + 100
    ew = tw * E.TOTAL / SRC1
    kit.text(c, f"edit  {int(E.TOTAL) // 60}:{int(E.TOTAL) % 60:02d}", tx, ty2 - 18, "bold", 26, color=WHITE,
             anchor="l")
    c.drawRRect(kit.rrect(tx, ty2, ew, 50, 10), fill("#000000", 0.6))
    c.drawRRect(kit.rrect(tx, ty2, max(10, ew * t / E.TOTAL), 50, 10), fill(YEL))
    for o, _, _ in C0.BOUNDS:
        c.drawRect(skia.Rect.MakeXYWH(tx + ew * o / E.TOTAL - 1, ty2 + 4, 2, 42), fill(INK, 0.5))
    # counters, as clean white UI cards
    cuts, pauses, rem = C0.stats(t)
    vals = [(f"{pauses}", "pauses cut"), (f"{cuts}", "cuts"), (f"{rem:.1f}s", "dead air gone")]
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


FILM = kit.Film(draw, E.TOTAL, E.FPS, post=post, out_dir=E.OUT)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "stills":
        FILM.stills([float(x) for x in sys.argv[2:]])
    elif cmd == "sheet":
        FILM.sheet([float(x) for x in sys.argv[2:]], cols=4, scale=0.4, name="cmp_v2_sheet.png")
    else:
        pic = FILM.render(E.OUT / "v2_comparison_picture.mp4")
        E.finish(pic, E.HERE / "work" / "v2_mix.wav", E.OUT / "vibe_reel_v2_comparison.mp4")
