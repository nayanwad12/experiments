"""Comparison reel: the raw phone take next to the finished edit, moment for moment (Instagram-safe 9:16).

    python3 compare.py render      -> out/vibe_edit_time_comparison.mp4  (needs out/vibe_edit_time.mp4 + work/mix.wav)
    python3 compare.py stills 5 20

Left: the untouched phone frame for the same moment. Right: the final edit. Everything sits inside the Reels
safe area (clear of the top bar, the right-hand buttons and the caption area at the bottom).
"""

import sys

import skia

import edit as E
import kit
from edit import INK, LIME, ORANGE, SAMP, WHITE, clamp, e_back, e_out, fill, measure, prog, stroke

W, H = E.W, E.H
FINAL = kit.Layer(E.OUT / "vibe_edit_time.mp4", fps=E.FPS)
SRC1 = E.NSRC / E.FPS
GAPS = [(0.0, E.EDL[0][0])] + [(a[1], b[0]) for a, b in zip(E.EDL, E.EDL[1:]) if b[0] - a[1] > 0.02]


def removed_until(src_t):
    tot, n = 0.0, 0
    for a, b in GAPS:
        if src_t >= b - 1e-3:
            tot += b - a
            n += 1
    return tot, n


def panel(c, img, x, y, w, h, label, hi, t):
    rr = kit.rrect(x, y, w, h, 30)
    c.drawRRect(rr.makeOffset(0, 18), fill("#000000", 0.5, blur=30))
    c.save()
    c.clipRRect(rr, skia.ClipOp.kIntersect, True)
    c.drawImageRect(img, skia.Rect.MakeXYWH(x, y, w, h), SAMP)
    c.restore()
    c.drawRRect(rr, stroke(hi, 4, 0.9))
    k = e_back(prog(t, 0.1, 0.4))
    wl = measure(label, "black", 40)
    c.save()
    c.translate(x + w / 2, y)
    c.scale(k, k)
    c.drawRRect(kit.rrect(-wl / 2 - 28, -34, wl + 56, 68, 34), fill(hi))
    kit.text(c, label, 0, 15, "black", 40, color=INK)
    c.restore()


def draw(c, t, f):
    src_t = E.src_at(t)
    E.ink_bg(c, t, LIME, 0.10)
    # headline
    k = e_out(prog(t, 0, 0.5))
    kit.text(c, "SAME TAKE.", 540, 300, "black", 92, color=WHITE, a=k)
    w2 = measure("ZERO TIMELINE.", "black", 92)
    c.drawRect(skia.Rect.MakeXYWH(540 - w2 / 2 - 16, 318, (w2 + 32) * e_out(prog(t, 0.3, 0.5)), 96), fill(LIME))
    kit.text(c, "ZERO TIMELINE.", 540, 400, "black", 92, color=INK if t > 0.45 else WHITE, a=k)
    # panels
    pw, ph = 460, 818
    y0 = 500
    raw = E.Src(src_t, "raw")
    panel(c, raw.bg(), 60, y0, pw, ph, "RAW", WHITE, t)
    panel(c, FINAL.image(f), W - 60 - pw, y0, pw, ph, "EDITED", LIME, t)
    kit.text(c, "straight from my phone", 60 + pw / 2, y0 + ph + 56, "italic", 44, color=WHITE, a=0.75)
    kit.text(c, "the Vibe Editing System", W - 60 - pw / 2, y0 + ph + 56, "italic", 44, color=LIME)
    # counters
    rem, n = removed_until(src_t)
    stats = [(f"{rem:3.1f}s", "PAUSES CUT"), (f"{n}", "CUTS MADE"), ("0", "EDITING APPS")]
    for j, (v, lab) in enumerate(stats):
        cx = 220 + j * 320
        cy = 1490
        c.drawRRect(kit.rrect(cx - 140, cy - 62, 280, 124, 24), fill(WHITE, 0.06))
        c.drawRRect(kit.rrect(cx - 140, cy - 62, 280, 124, 24), stroke(WHITE, 2, 0.15))
        kit.text(c, v, cx, cy + 12, "black", 60, color=LIME if j == 2 else WHITE)
        kit.text(c, lab, cx, cy + 46, "monob", 22, color=WHITE, a=0.6, tracking=0.12)
    return {}


def post(rgb, g, f):
    return kit.grain(rgb, f, amt=0.015)


FILM = kit.Film(draw, E.DUR, E.FPS, post=post, out_dir=E.OUT)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "stills":
        FILM.stills([float(x) for x in sys.argv[2:]])
    else:
        pic = FILM.render(E.OUT / "comparison_picture.mp4")
        mix = E.HERE / "work" / "mix.wav"
        E.ff("-i", str(pic), "-i", str(mix), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "slow",
             "-crf", "19", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p", "-profile:v", "high",
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart",
             str(E.OUT / "vibe_edit_time_comparison.mp4"))
        print("->", E.OUT / "vibe_edit_time_comparison.mp4")
