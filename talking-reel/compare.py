"""Comparison reel: the raw take next to the finished edit, moment for moment, on the final mix.

    python3 compare.py render      -> out/vibe_reel_comparison.mp4   (needs out/vibe_reel.mp4 + work/mix.wav)
    python3 compare.py stills 5 20

Left: the untouched phone frame that the edit is using at that instant. Right: the final edit. Underneath,
the raw take's timeline with every removed pause marked and a playhead, the edit's own timeline, and
running counters (pauses cut, cuts, dead air removed).
"""

import math
import sys

import skia

import edit as E
import kit
from look import (CREAM, INK, OLIVE, OLIVE_D, OLIVE_L, SAMP, TOMATO, caps, clamp, e_out, fill, glow_text, ground,
                  mono, photo_card, pill, prog, serif, smiley)

W, H = E.W, E.H
FINAL = kit.Layer(E.OUT / "vibe_reel.mp4", fps=E.FPS)
SRC1 = E.NSRC / E.FPS
RUNS = sorted(E.EDL, key=lambda r: r[0])          # raw order
GAPS = [(0.0, RUNS[0][0])] + [(a[1], b[0]) for a, b in zip(RUNS, RUNS[1:]) if b[0] - a[1] > 0.02] \
    + [(RUNS[-1][1], SRC1)]
# boundaries in output order: (out time, removed seconds, is-a-pause)
BOUNDS = []
for prev, nxt in zip(E.EDL, E.EDL[1:]):
    gap = nxt[0] - prev[1]
    BOUNDS.append((nxt[2], max(0.0, gap) if gap < 5 else 0.0, 0 < gap < 5))
# the hook was lifted from 1:10 and the first 0.8 s / the "and yes," before it are gone too
REMOVED_TOTAL = SRC1 - E.TOTAL


def stats(t):
    cuts = sum(1 for o, _, _ in BOUNDS if t >= o)
    pauses = sum(1 for o, _, p in BOUNDS if t >= o and p)
    rem = sum(r for o, r, _ in BOUNDS if t >= o)
    return cuts, pauses, rem


def panel(c, img, x, y, w, h, label, bg, fg, seed, src_rect=None):
    photo_card(c, img, x, y, w, h, seed=seed, src_rect=src_rect, burn=0.5)
    pill(c, label, x + w / 2, y - 4, 34, bg, fg, name="mont", rot=-3 if seed % 2 else 3)


def draw(c, t, f):
    ground(c, OLIVE, t=t)
    src_t = E.src_at(t)
    # title
    glow_text(c, "raw", 290, 300, 110, CREAM, rot=-4)
    serif(c, "vs", 500, 290, 60, CREAM)
    glow_text(c, "edited", 700, 300, 110, TOMATO, rot=-4)
    smiley(c, 905, 265, 36, CREAM, rot=-10 + 6 * math.sin(t * 2))
    # panels
    pw, ph = 400, 711
    y0 = 385
    raw = E.Src(src_t)
    panel(c, raw.raw_img(), 75, y0, pw, ph, "RAW", CREAM, INK, 1)
    panel(c, FINAL.image(f), 525, y0, pw, ph, "EDITED", TOMATO, CREAM, 2)
    if t < E.SEC["intro"]:
        pill(c, "HOOK MOVED FROM 1:10 TO 0:00", 500, y0 + ph - 60, 24, INK, CREAM, k=prog(t, 0.1, 0.3))
    if t >= E.END_A:
        pill(c, "SILENT TAIL -> END CARD", 500, y0 + ph - 60, 24, INK, CREAM, k=prog(t, E.END_A, 0.3))
    # raw timeline
    tx, tw = 75, 850
    ty = 1165
    mono(c, f"RAW TAKE  {int(SRC1) // 60}:{int(SRC1) % 60:02d}", tx, ty - 20, 26, CREAM)
    c.drawRRect(kit.rrect(tx, ty, tw, 56, 12), fill(INK))
    for a, b in GAPS:
        c.drawRect(skia.Rect.MakeXYWH(tx + tw * a / SRC1, ty + 4, max(3, tw * (b - a) / SRC1), 48), fill(TOMATO))
    for a, b, o, d, i0, i1 in RUNS:
        x0, x1 = tx + tw * a / SRC1, tx + tw * b / SRC1
        done = t >= o + d
        cur = o <= t < o + d
        c.drawRect(skia.Rect.MakeXYWH(x0, ty + 4, x1 - x0, 48), fill(CREAM if done or cur else OLIVE_L))
    px = tx + tw * src_t / SRC1
    c.drawRect(skia.Rect.MakeXYWH(px - 3, ty - 10, 6, 76), fill(TOMATO))
    c.drawCircle(px, ty - 12, 9, fill(TOMATO))
    lx = tx + tw
    mono(c, "kept", lx, ty - 20, 22, CREAM, anchor="r")
    c.drawRect(skia.Rect.MakeXYWH(lx - 82, ty - 38, 18, 18), fill(CREAM))
    mono(c, "removed", lx - 100, ty - 20, 22, CREAM, anchor="r")
    c.drawRect(skia.Rect.MakeXYWH(lx - 218, ty - 38, 18, 18), fill(TOMATO))
    # edit timeline
    ty2 = ty + 112
    ew = tw * E.TOTAL / SRC1
    mono(c, f"EDIT  {int(E.TOTAL) // 60}:{int(E.TOTAL) % 60:02d}", tx, ty2 - 20, 26, CREAM)
    c.drawRRect(kit.rrect(tx, ty2, ew, 56, 12), fill(INK))
    c.drawRRect(kit.rrect(tx, ty2, max(12, ew * t / E.TOTAL), 56, 12), fill(TOMATO))
    for o, _, _ in BOUNDS:
        c.drawRect(skia.Rect.MakeXYWH(tx + ew * o / E.TOTAL - 1, ty2 + 4, 2, 48), fill(INK, 0.6))
    # counters
    cuts, pauses, rem = stats(t)
    k = e_out(prog(t, 0, 0.4))
    vals = [(f"{pauses}", "PAUSES CUT"), (f"{cuts}", "CUTS"), (f"{rem:.1f}s", "DEAD AIR GONE")]
    for j, (v, lab) in enumerate(vals):
        cx = 500 + (j - 1) * 290
        cy = 1405
        rr = kit.rrect(cx - 135, cy - 68, 270, 136, 24)
        c.drawRRect(rr.makeOffset(5, 10), fill("#000000", 0.3, blur=12))
        c.drawRRect(rr, fill(TOMATO if j == 0 else OLIVE_D))
        kit.text(c, v, cx, cy + 14, "mont", 64, color=CREAM, a=k)
        mono(c, lab, cx, cy + 50, 19, CREAM, k, anchor="c")
    return {}


def post(rgb, g, f):
    return kit.grain(rgb, f, amt=0.022)


FILM = kit.Film(draw, E.TOTAL, E.FPS, post=post, out_dir=E.OUT)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "stills":
        FILM.stills([float(x) for x in sys.argv[2:]])
    else:
        pic = FILM.render(E.OUT / "comparison_picture.mp4")
        E.finish(pic, E.HERE / "work" / "mix.wav", E.OUT / "vibe_reel_comparison.mp4")
