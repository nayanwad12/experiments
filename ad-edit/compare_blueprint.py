"""Comparison reel for the blueprint edit: raw take and final edit as two prints on the cutting mat.

    python3 compare_blueprint.py render   -> out/vibe_edit_time_blueprint_comparison.mp4
    python3 compare_blueprint.py stills 5 20

Needs out/vibe_edit_time_blueprint.mp4 and work/bp/mix.wav. Everything sits inside the Reels safe area.
"""

import sys

import skia

import compare as C
import edit as E
import edit_blueprint as B
import kit
from edit import SAMP, W, e_out, prog

FINAL = kit.Layer(E.OUT / "vibe_edit_time_blueprint.mp4", fps=E.FPS)
PROPS = [(B.prop_laptop, (60, 100, 14, 0.8)), (B.prop_case, (1010, 140, -18, 0.8)),
         (B.prop_watch, (1030, 1760, 28, 0.7)), (B.prop_pencil, (120, 1790, -24, 0.75))]


def print_card(c, img, x, y, w, h, rot):
    def body():
        c.save()
        c.translate(x, y)
        c.rotate(rot)
        c.drawRect(skia.Rect.MakeXYWH(-w / 2 - 14, -h / 2 - 14, w + 28, h + 28), B.fill(B.WHITE))
        c.drawImageRect(img, skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h), SAMP)
        c.restore()

    B.shadowed(c, body, 12, 22, 18, 0.45)


def headline(c, t):
    for i, (s, bg, fg, rot, dx, size, t0) in enumerate((("SAME TAKE.", B.BLUE, B.WHITE, -4, -60, 120, 0.05),
                                                        ("ZERO TIMELINE.", B.YEL, B.INK, 2.5, 50, 112, 0.3))):
        kk = prog(t, t0, 0.45)
        if kk <= 0:
            continue
        capH = B.font("anton", size).getMetrics().fCapHeight
        w = B.cwidth(s, size)
        bw, bh = w + 0.4 * size, capH + 0.32 * size
        cy = 300 + i * bh * 0.95
        sc = B.lerp(1.4, 1.0, B.clamp(B.spring(kk * 0.45, w=20, z=0.42)))

        def body(s=s, bg=bg, fg=fg, rot=rot, dx=dx, size=size, capH=capH, w=w, bw=bw, bh=bh, cy=cy, sc=sc):
            c.save()
            c.translate(540 + dx, cy)
            c.rotate(rot)
            c.scale(sc, sc)
            c.drawRect(skia.Rect.MakeXYWH(-bw / 2, -bh / 2, bw, bh), B.fill(bg))
            B.ctext(c, s, -w / 2, capH / 2, size, fg)
            c.restore()

        B.shadowed(c, body, 10, 16, 14, 0.42)


def draw(c, t, f):
    src_t = E.src_at(t)
    B.draw_mat(c, 0, 0)
    for fn, (x, y, rot, s) in PROPS:
        if fn is B.prop_watch:
            fn(c, x, y, rot, s, t=t)
        else:
            fn(c, x, y, rot, s)
    headline(c, t)
    pw, ph = 430, 764
    raw = E.Src(src_t, "raw")
    print_card(c, raw.bg(), 290, 920, pw, ph, -3)
    print_card(c, FINAL.image(f), 790, 935, pw, ph, 2.5)
    B.tape(c, "RAW · MY PHONE", 290, 1335, e_out(prog(t, 0.4, 0.4)), rot=-3, size=30)
    B.tape(c, "EDITED · VIBE EDITING SYSTEM", 760, 1350, e_out(prog(t, 0.5, 0.4)), rot=2, size=30, bg=B.YEL,
           fg=B.INK)
    rem, n = C.removed_until(src_t)
    k = prog(t, 0.7, 0.45)
    B.talk_chip(c, f"{rem:3.1f}s of pauses cut", 300, 1470, k, rot=-6, size=40)
    B.talk_chip(c, f"{n} cut" + ("" if n == 1 else "s"), 700, 1460, prog(t, 0.8, 0.45), rot=5, size=40)
    B.talk_chip(c, "0 editing apps", 540, 1555, prog(t, 0.9, 0.45), rot=-3, size=40)
    return {}


def post(rgb, g, f):
    return kit.grain(rgb, f, amt=0.015)


FILM = kit.Film(draw, E.DUR, E.FPS, post=post, out_dir=E.OUT)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "stills":
        FILM.stills([float(x) for x in sys.argv[2:]])
    else:
        pic = FILM.render(E.OUT / "comparison_blueprint_picture.mp4")
        out = E.OUT / "vibe_edit_time_blueprint_comparison.mp4"
        E.ff("-i", str(pic), "-i", str(E.HERE / "work" / "bp" / "mix.wav"), "-map", "0:v:0", "-map", "1:a:0",
             "-c:v", "libx264", "-preset", "slow", "-b:v", "5.2M", "-maxrate", "7M", "-bufsize", "10M",
             "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
             "-shortest", "-movflags", "+faststart", str(out))
        print("->", out)
