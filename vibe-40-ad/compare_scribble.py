"""Comparison reel for the scribble edit: raw take next to vibe40_scribble, moment for moment, on its mix.

    python3 compare_scribble.py render   -> out/vibe40_scribble_comparison.mp4  (needs out/vibe40_scribble.mp4 + work/scribble_mix.wav)
    python3 compare_scribble.py sheet 2 10 20

Raw small on the left, the edit bigger on the right, "AI EDITED THIS VIDEO" on top, CTA "LEARN THE WORKFLOW";
everything inside the Instagram Reels safe area, on black. Dressed like the scribble edit (retro windows,
marker type, VT323 counters).
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


# Instagram Reels safe area: clear of the top bar (y < 270), the caption/CTA area (y > 1440) and the
# right-hand buttons (x > 930 in the lower half).  Raw small on the left, the edit ~1.75x bigger on the right.
RAW_BOX = (160, 570, 230, 409)          # inner picture x, y, w, h (9:16)
EDIT_BOX = (470, 570, 405, 720)


def win_pic(c, box, title, img):
    x, y, w, h = box
    S.window(c, x - 12, y - 56, w + 24, h + 68, title, 1.0)
    c.drawImageRect(img, skia.Rect.MakeXYWH(x, y, w, h), S.SAMP)
    S.end_window(c)


def draw(c, t, f):
    src_t = E.src_at(t)
    c.drawRect(skia.Rect.MakeWH(W, H), fill("#000000"))
    # title
    S.marker(c, "AI EDITED", 540, 400, 10, 0, 150, S.YEL)
    S.word_caps(c, "THIS VIDEO", 540, 480, 72, S.WHITE)
    # the two pictures
    win_pic(c, RAW_BOX, "raw.mov", S.Src(src_t).raw())
    win_pic(c, EDIT_BOX, "edited_by_ai.mp4", FINAL.image(f))
    # counters, stacked under the small raw window
    cuts, pauses, rem = C0.stats(t)
    saved = max(0.0, (src_t - E.EDL[0][0]) - t)
    x = RAW_BOX[0] - 12
    for j, (v, lab) in enumerate(((f"{pauses}", "pauses cut"), (f"{rem:.1f}s", "dead air"), (f"{saved:.1f}s", "saved"))):
        y = 1050 + j * 100
        S.bevel(c, x, y, RAW_BOX[2] + 24, 92)
        kit.text(c, v, x + 18, y + 62, "vt", 60, color=S.BLUE, anchor="l")
        kit.text(c, lab, x + RAW_BOX[2] + 8, y + 58, "vt", 30, color=S.INK, anchor="r")
    # call to action
    S.marker(c, "LEARN THE WORKFLOW", 540, 1420, 10, 0, 105, S.YEL, maxw=860)
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
