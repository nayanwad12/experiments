"""Comparison reel: the raw phone take next to the finished edit, moment for moment.

    python3 compare.py render      -> out/system_reel_comparison.mp4   (needs out/system_reel.mp4 + work/mix.wav)
    python3 compare.py stills 5 20

Left: the untouched phone frame for the same moment. Right: the final edit. Underneath, the raw take's
timeline with every removed pause marked, a playhead on each, and running counters.
"""

import os
import sys

import skia

import edit as E
import kit
from theme import INK, PAPER, RED, SAMP, WHITE, YEL, block_text, card, e_back, e_out, fill, halftone, hilite, measure, \
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


# Instagram Reels safe area: clear of the top bar, the caption/username/audio block at the bottom
# and the like/comment/share column on the right (which starts around y=1080).
SX0, SX1, SY0, SY1 = 80, 950, 230, 1490
ICONS_Y = 1070


def panel(c, img, x, y, w, h, label, hi, r=30, tape_size=34):
    card(c, x - 8, y - 8, w + 16, h + 16, INK, r=r + 8, shadow=0.4)
    c.save()
    c.clipRRect(kit.rrect(x, y, w, h, r), skia.ClipOp.kIntersect, True)
    c.drawImageRect(img, skia.Rect.MakeXYWH(x, y, w, h), SAMP)
    c.restore()
    tape(c, label, x + w / 2, y + 2, tape_size, 1, rot=-3 if hi == PAPER else 2, bg=hi, seed=len(label), name="anton")


def title_card(c, t):
    """compact one-line title pill."""
    k = e_back(prog(t, 0, 0.4))
    txt, size = "AI EDITED THIS VIDEO", 74
    tw = measure(txt, "anton", size)
    w, h = tw + 64, 108
    cx, cy = (SX0 + SX1) / 2, SY0 + h / 2
    c.save()
    c.translate(cx, cy)
    c.rotate(-1.5)
    c.scale(k, k)
    rr = kit.rrect(-w / 2, -h / 2, w, h, 22)
    c.drawRRect(rr.makeOffset(8, 9), fill(YEL))
    c.drawRRect(rr, fill(INK))
    aw = measure("AI ", "anton", size)
    x0 = -tw / 2
    block_text(c, "AI ", x0, 27, size, color=YEL, shadow=None, anchor="l")
    block_text(c, "EDITED THIS VIDEO", x0 + aw, 27, size, color=WHITE, shadow=None, anchor="l")
    c.restore()


def stat(c, x, y, w, value, label, bg):
    card(c, x, y, w, 118, bg, r=18, shadow=0.3, border=INK, bw=4)
    block_text(c, value, x + w / 2, y + 70, 62, color=INK, shadow=None)
    kit.text(c, label, x + w / 2, y + 102, "monob", 20, color=INK)


def draw(c, t, f):
    src_t, kind = E.src_at(t)
    paper_bg(c)
    halftone(c, 540, 1950, 1300, "#D9CFBC", spacing=30, dot=11, a=0.8)
    title_card(c, t)
    # big final edit on the left, small raw take in the right column (above the icon column)
    fy = SY0 + 156
    fh = 1040
    fw = round(fh * 9 / 16)
    fx = SX0
    panel(c, FINAL.image(f), fx, fy, fw, fh, "FINAL EDIT", YEL, tape_size=40)
    rx = fx + fw + 34
    rw = SX1 - rx
    rh = round(rw * 16 / 9)
    raw = E.Src(src_t, graded=False)
    panel(c, raw.bg(), rx, fy + 10, rw, rh, "RAW", PAPER, r=20, tape_size=28)
    kit.text(c, "from my phone", rx + rw / 2, fy + rh + 52, "italic", 32, color=INK)
    tag = None
    if kind == "rev":
        tag = ("REWIND: CUTTING THE MISTAKE", RED, WHITE)
    elif kind == "freeze":
        tag = ("FREEZE FRAME + EFFECTS", INK, YEL)
    if tag:
        tape(c, tag[0], fx + fw / 2, fy + fh / 2, 34, 1, rot=-4, bg=tag[1], fg=tag[2], seed=9)
    # live counters under the raw take, kept above the icon column
    rem, n = removed_until(src_t)
    sy = fy + rh + 80
    stat(c, rx, sy, rw, f"{rem:.1f}s", "DEAD SPACE CUT", YEL)
    if sy + 136 + 118 <= ICONS_Y:
        stat(c, rx, sy + 136, rw, f"{n}", "CUTS", WHITE)
    # raw timeline under the final edit: removed pauses in red, kept in yellow as they play
    tx, tw = fx, fw
    ty, bh = fy + fh + 30, 34
    c.drawRRect(kit.rrect(tx, ty, tw, bh, 9), fill(INK))
    for a, b in GAPS:
        c.drawRect(skia.Rect.MakeXYWH(tx + tw * a / SRC1, ty + 3, max(3, tw * (b - a) / SRC1), bh - 6), fill(RED))
    for s in PLAYS:
        x0, x1 = tx + tw * s[1] / SRC1, tx + tw * s[2] / SRC1
        c.drawRect(skia.Rect.MakeXYWH(x0, ty + 3, x1 - x0, bh - 6), fill("#3A3A3A"))
        if src_t >= s[1]:
            c.drawRect(skia.Rect.MakeXYWH(x0, ty + 3, tx + tw * min(src_t, s[2]) / SRC1 - x0, bh - 6), fill(YEL))
    c.drawRect(skia.Rect.MakeXYWH(tx + tw * src_t / SRC1 - 3, ty - 6, 6, bh + 12), fill(INK))
    if os.environ.get("IG_UI"):
        ig_ui(c)
    return {}


def ig_ui(c):
    """rough Reels UI mock, for checking the layout only (IG_UI=1 python3 compare.py stills ...)."""
    p = fill("#FF00FF", 0.3)
    c.drawRect(skia.Rect.MakeXYWH(0, 0, W, 200), p)
    c.drawRect(skia.Rect.MakeXYWH(0, 1540, W, 380), p)
    c.drawRect(skia.Rect.MakeXYWH(975, ICONS_Y, 105, 1920 - ICONS_Y), p)


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
