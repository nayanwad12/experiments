"""B2-02 Launch ad: "This app doesn't exist. But its launch ad does."
A premium launch ad for a concept fintech app (Saveo): 3D phone, coins into a glass jar, a chart rising out of the
screen, a wireframe "it's all code" reveal, then the same ad in every format.

    python3 build.py prep | web 2 6 | layer | sheet | stills 4 | render | sound | all
"""
import math
import sys
from pathlib import Path

import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(HERE))
from b2 import Reel  # noqa: E402
from kit import (W, H, LIME, WHITE, Captions, Film, Layer, clamp, e_back, e_out, endcard, fill, lerp,  # noqa: E402
                 measure, prog, rrect, text)
from script import LINES, VOICE  # noqa: E402
from voice import Script, narrate  # noqa: E402

FPS, BPM = 30, 132
BAR = 240 / BPM
vo = narrate(LINES, HERE / "work", VOICE)
S = Script(vo, [("hook", "@", 0.15), ("but", "@", 1.55), ("a1", "@", 2 * BAR + 0.04), ("a2", "@", 3 * BAR),
                ("a3", "@", 4 * BAR), ("a4", "@", 5 * BAR), ("a5", "@", 6.5 * BAR), ("meta", "@", 8 * BAR + 0.05),
                ("fmt", "@", 10 * BAR + 0.07), ("cta", "@", 10 * BAR + 2.4)])
END_T = S.end("cta") + 0.45
DUR = END_T + 2.9
R = Reel(__file__, DUR, FPS)
MINT, VIOLET = "#34E3A0", "#7C5CFF"
HEADLINES = {"a2": "Every purchase,\nrounded up.", "a3": "Every rupee,\nput to work.", "a4": "Watch it grow\non autopilot."}


def song():
    from music import future_bass
    return future_bass(DUR, BPM, "A", {"drop": 2 * BAR, "break": 8 * BAR, "drop2": 10 * BAR}, seed=33)


def prep():
    sg = song()
    sg.master()
    R.write_timeline(dict(
        DUR=DUR, BAR=BAR, BOOT=S.find("but", "does") - 0.05, DROP=2 * BAR, ROUND=3 * BAR, GOALS=4 * BAR,
        GROW=5 * BAR, HERO=6.5 * BAR, WIRE=8 * BAR, FMT=10 * BAR, END=END_T,
        COIN_T=[3 * BAR + 0.55 + 0.11 * i for i in range(11)], KICKS=sorted(set(round(k, 3) for k in sg.kicks)),
        MINT=MINT, VIOLET=VIOLET))
    print("timeline ok")


# ---------------------------------------------------------------- overlays
BG = Layer(HERE / "work" / "layer.mp4", fps=FPS)
CODE = [ln.rstrip() for ln in (HERE / "scene.js").read_text().splitlines() if ln.strip() and not ln.strip().startswith("//")]


def headline(c, t, lid, txt):
    order = list(HEADLINES)
    nxt = order[order.index(lid) + 1] if order.index(lid) + 1 < len(order) else None
    t0, t1 = S.t(lid) - 0.05, S.end(lid) + 0.55
    if nxt:
        t1 = min(t1, S.t(nxt) - 0.35)
    if not (t0 <= t < t1 + 0.3):
        return
    lines = txt.split("\n")
    for li, ln in enumerate(lines):
        k = e_out(prog(t, t0 + li * 0.12, 0.35))
        ko = e_out(prog(t, t1, 0.25))
        y = 330 + li * 118
        c.save()
        c.clipRect(skia.Rect.MakeLTRB(0, y - 110, W, y + 30))
        text(c, ln, W / 2, y + 120 * (1 - k) - 140 * ko, "black", 104, WHITE if li == 0 else MINT, 1, tracking=-0.03,
             shadow=20)
        c.restore()


def code_panel(c, t):
    t0, t1 = S.t("meta") - 0.1, 10 * BAR
    if not (t0 <= t < t1):
        return
    a = e_out(prog(t, t0, 0.35)) * (1 - prog(t, t1 - 0.25, 0.25))
    x0, y0, w, h = 50, 950, W - 100, 560
    c.drawRRect(rrect(x0, y0, w, h, 28), fill("#05060c", 0.78 * a))
    c.drawRRect(rrect(x0, y0, w, 62, 28), fill("#151826", 0.9 * a))
    for i, cc in enumerate(("#FF5F57", "#FEBC2E", "#28C840")):
        c.drawCircle(x0 + 40 + i * 30, y0 + 31, 9, fill(cc, a))
    text(c, "scene.js", x0 + w / 2, y0 + 42, "mono", 28, "#9AA0B4", a)
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(x0, y0 + 70, w, h - 80))
    scroll = (t - t0) * 210
    lh = 36
    first = int(scroll // lh)
    for i in range(first, first + 18):
        ln = CODE[i % len(CODE)][:52]
        y = y0 + 110 + i * lh - scroll
        col = "#C792EA" if ln.lstrip().startswith(("const", "let", "function", "import", "for", "if")) else \
            ("#34E3A0" if "THREE" in ln else "#D6DAE6")
        text(c, f"{i % len(CODE) + 1:>3}", x0 + 30, y, "mono", 24, "#4A5068", a, anchor="l")
        text(c, ln, x0 + 100, y, "mono", 26, col, a, anchor="l")
    c.restore()


def draw(c, t, f):
    c.drawImage(BG.image(f), 0, 0)
    if 2 * BAR - 0.1 <= t < 8 * BAR:
        a = e_out(prog(t, 2 * BAR, 0.3)) * (1 - prog(t, 8 * BAR - 0.3, 0.3))
        text(c, "CONCEPT AD · FICTIONAL APP", 56, 190, "monob", 28, "#9AA0B4", a * 0.9, anchor="l")
    for lid, txt in HEADLINES.items():
        headline(c, t, lid, txt)
    code_panel(c, t)
    if t >= END_T:
        endcard(c, t, END_T)
    CAP.draw(c, t)


CAP = Captions(S.words(skip=("a2", "a3", "a4")), y=1650, size=84).mute(END_T, DUR)
film = Film(draw, DUR, FPS, out_dir=HERE / "out")


# ---------------------------------------------------------------- sound
def sound():
    import json
    import music as M
    from sound import Mix
    T = json.loads((HERE / "work" / "timeline.json").read_text())
    bed = song().master()
    m = Mix(DUR)
    m.voice(S.placements())
    m.music(bed, gain_db=-3, duck_db=-8, fade_out=1.5)
    n = int(0.35 * M.SR)
    tt = np.arange(n) / M.SR
    for i, ct in enumerate(T["COIN_T"]):                       # coin: two inharmonic partials + a tiny land clink
        f0 = 2400 * (1 + 0.04 * (i % 3))
        coin = (np.sin(2 * np.pi * f0 * tt) + 0.6 * np.sin(2 * np.pi * f0 * 1.51 * tt)) * np.exp(-tt * 18) * 0.5
        m.sfx(coin.astype(np.float32), ct, -14, pan=0.4)
        m.sfx(coin.astype(np.float32) * 0.6, ct + 0.55, -16, pan=0.5)
    m.sfx("sparkle", T["BOOT"], -10)
    m.sfx("whoosh", T["DROP"] - 0.25, -10)
    m.sfx("pop", T["ROUND"] + 0.2, -8)
    m.sfx("swish", T["GOALS"] - 0.1, -10)
    for k in range(7):
        m.sfx("pop", T["GROW"] + 0.35 + k * 0.12, -14)
    m.sfx("whoosh", T["HERO"] - 0.2, -10)
    m.sfx("glitch", T["WIRE"], -10)
    m.sfx("typing", T["WIRE"] + 0.1, -18, dur=3.2, cps=26)
    for k in range(4):
        m.sfx("pop", T["FMT"] + 0.12 + k * 0.14, -9)
    m.sfx("whoosh", END_T - 0.25, -10)
    m.sfx("ding", END_T + 0.1, -12)
    m.finish(HERE / "out" / "picture.mp4", HERE / "out" / "B2_02_launch_ad.mp4", HERE / "work")


if __name__ == "__main__":
    R.cli(film, sound, prep)
