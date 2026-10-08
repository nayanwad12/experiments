"""Comparison reel: the raw phone take next to the finished edit, moment for moment.

    python3 compare.py render      -> out/system_reel_comparison.mp4   (needs out/system_reel.mp4 + work/mix.wav)
    python3 compare.py stills 5 20

Left: the untouched phone frame for the same moment. Right: the final edit. Underneath, the raw take's
timeline with every removed pause marked, a playhead on each, and running counters.
"""

import sys

import skia

import edit as E
import kit
from theme import INK, PAPER, RED, SAMP, WHITE, YEL, block_text, card, e_out, fill, halftone, hilite, measure, \
    paper_bg, prog, stroke, tape

W, H = E.W, E.H
FINAL = kit.Layer(E.OUT / "system_reel.mp4", fps=E.FPS)
PLAYS = [s for s in E.EDL if s[0] == "play"]
SRC0, SRC1 = 0.0, E.NSRC / E.FPS
GAPS = [(0.0, PLAYS[0][1])] + [(a[2], b[1]) for a, b in zip(PLAYS, PLAYS[1:]) if b[1] - a[2] > 0.02] \
    + [(PLAYS[-1][2], SRC1)]


def removed_until(src_t):
    """dead space removed so far, and how many cuts passed."""
    tot, n = 0.0, 0
    for a, b in GAPS[:-1]:
        if src_t >= b - 1e-3:
            tot += b - a
            n += 1
    return tot, n


def panel(c, img, x, y, w, h, label, sub, hi):
    card(c, x - 10, y - 10, w + 20, h + 20, INK, r=44, shadow=0.4)
    c.save()
    c.clipRRect(kit.rrect(x, y, w, h, 34), skia.ClipOp.kIntersect, True)
    c.drawImageRect(img, skia.Rect.MakeXYWH(x, y, w, h), SAMP)
    c.restore()
    tape(c, label, x + w / 2, y - 6, 40, 1, rot=-3 if hi == PAPER else 3, bg=hi, seed=len(label), name="anton")
    kit.text(c, sub, x + w / 2, y + h + 64, "monob", 26, color=INK)


def draw(c, t, f):
    src_t, kind = E.src_at(t)
    paper_bg(c)
    halftone(c, 540, 1950, 1300, "#D9CFBC", spacing=30, dot=11, a=0.8)
    # title
    size = 104
    w1 = measure("PHONE", "anton", size)
    w2 = measure("MY SYSTEM", "anton", size)
    wv = measure(" vs ", "italic", 90)
    x = 540 - (w1 + wv + w2) / 2
    block_text(c, "PHONE", x, 205, size, color=INK, shadow=None, anchor="l")
    kit.text(c, " vs ", x + w1, 200, "italic", 90, color=INK, anchor="l")
    hilite(c, x + w1 + wv - 14, 112, w2 + 28, 112, 1, YEL, seed=3, rot=-1)
    block_text(c, "MY SYSTEM", x + w1 + wv, 205, size, color=INK, shadow=None, anchor="l")
    # panels
    pw, ph = 492, 875
    y0 = 320
    raw = E.Src(src_t, graded=False)
    panel(c, raw.bg(), 34, y0, pw, ph, "RAW TAKE", "straight from the phone", PAPER)
    final = FINAL.image(f)
    panel(c, final, W - 34 - pw, y0, pw, ph, "FINAL EDIT", "edited by my system", YEL)
    # what's happening right now
    tag = None
    if kind == "rev":
        tag = ("REWIND: CUTTING THE MISTAKE", RED, WHITE)
    elif kind == "freeze":
        tag = ("FREEZE FRAME + EFFECTS", INK, YEL)
    if tag:
        tape(c, tag[0], 540, y0 + ph / 2, 38, prog(t, 0, 1), rot=-4, bg=tag[1], fg=tag[2], seed=9)
    # timelines
    tx, tw = 70, 940
    ty = 1370
    kit.text(c, "RAW  0:%02d" % round(SRC1), tx, ty - 22, "monob", 28, color=INK, anchor="l")
    c.drawRRect(kit.rrect(tx, ty, tw, 64, 12), fill(INK))
    for a, b in GAPS:
        x0 = tx + tw * a / SRC1
        c.drawRect(skia.Rect.MakeXYWH(x0, ty + 4, max(3, tw * (b - a) / SRC1), 56), fill(RED))
    for s in PLAYS:
        x0, x1 = tx + tw * s[1] / SRC1, tx + tw * s[2] / SRC1
        c.drawRect(skia.Rect.MakeXYWH(x0, ty + 4, x1 - x0, 56), fill("#3A3A3A"))
        if src_t >= s[1]:
            done = min(src_t, s[2])
            c.drawRect(skia.Rect.MakeXYWH(x0, ty + 4, tx + tw * done / SRC1 - x0, 56), fill(YEL))
    px = tx + tw * src_t / SRC1
    c.drawRect(skia.Rect.MakeXYWH(px - 3, ty - 10, 6, 84), fill(INK))
    ty2 = ty + 140
    ew = tw * E.TOTAL / SRC1
    kit.text(c, "EDIT 0:%02d" % round(E.TOTAL), tx, ty2 - 22, "monob", 28, color=INK, anchor="l")
    c.drawRRect(kit.rrect(tx, ty2, ew, 64, 12), fill(INK))
    c.drawRRect(kit.rrect(tx, ty2, ew * t / E.TOTAL, 64, 12), fill(YEL))
    c.drawRect(skia.Rect.MakeXYWH(tx + ew * t / E.TOTAL - 3, ty2 - 10, 6, 84), fill(INK))
    # counters
    rem, n = removed_until(src_t)
    k = e_out(prog(t, 0, 0.4))
    stats = [(f"{rem:4.1f}s", "DEAD SPACE CUT"), (f"{n}", "CUTS"), ("0", "EDITING APPS")]
    for j, (v, lab) in enumerate(stats):
        cx = 190 + j * 350
        cy = 1710
        card(c, cx - 150, cy - 70, 300, 140, WHITE if j else YEL, r=22, shadow=0.3, border=INK, bw=4)
        block_text(c, v, cx, cy + 14, 76, color=INK, shadow=None, a=k)
        kit.text(c, lab, cx, cy + 52, "monob", 22, color=INK, a=k)
    ly, lx = ty - 30, tx + tw
    kit.text(c, "kept", lx, ly, "mono", 24, color=INK, anchor="r")
    c.drawRect(skia.Rect.MakeXYWH(lx - 90, ly - 18, 20, 20), fill(YEL))
    kit.text(c, "removed", lx - 110, ly, "mono", 24, color=INK, anchor="r")
    c.drawRect(skia.Rect.MakeXYWH(lx - 238, ly - 18, 20, 20), fill(RED))
    return {}


def post(rgb, g, f):
    return kit.grain(rgb, f, amt=0.018)


FILM = kit.Film(draw, E.TOTAL, E.FPS, post=post, out_dir=E.OUT)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "stills":
        FILM.stills([float(x) for x in sys.argv[2:]])
    else:
        pic = FILM.render(E.OUT / "comparison_picture.mp4")
        E.finish(pic, E.HERE / "work" / "mix.wav", E.OUT / "system_reel_comparison.mp4")
