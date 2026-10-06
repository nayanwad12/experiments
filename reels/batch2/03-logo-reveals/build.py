"""B2-03 Motion graphics: "Five logo animations. One prompt each." Liquid chrome, particle storm, neon sign,
glitch and heavy metal reveals of the Vibe Editing logo, cut to drift phonk.

    python3 build.py prep | web 2 5 | layer | sheet | stills 4 | render | sound | all
"""
import sys
from pathlib import Path

import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(HERE))
from b2 import Reel  # noqa: E402
from kit import (W, H, INK, LIME, WHITE, Captions, Film, Layer, clamp, e_back, e_out, endcard, fill, lerp,  # noqa: E402
                 prog, text)
from script import LINES, VOICE  # noqa: E402
from voice import Script, narrate  # noqa: E402

FPS, BPM = 30, 130
BAR = 240 / BPM
REV = [2 * BAR + i * 1.5 * BAR for i in range(5)]
RECAP = 2 * BAR + 7.5 * BAR
vo = narrate(LINES, HERE / "work", VOICE)
S = Script(vo, [("hook", "@", 0.12), ("hook2", 0.12), ("l1", "@", REV[0] + 0.08), ("l2", "@", REV[1] + 0.08),
                ("l3", "@", REV[2] + 0.08), ("l4", "@", REV[3] + 0.08), ("l5", "@", REV[4] + 0.08),
                ("nos", "@", RECAP + 0.1), ("cta", 0.3)])
END_T = S.end("cta") + 0.45
DUR = END_T + 2.9
R = Reel(__file__, DUR, FPS)
NAMES = ["LIQUID CHROME", "PARTICLE STORM", "NEON SIGN", "GLITCH", "HEAVY METAL"]


def song():
    from music import phonk
    return phonk(DUR, BPM, "C#", {"drop": 2 * BAR, "hits": REV[1:] + [RECAP]}, seed=13)


def prep():
    sg = song()
    sg.master()
    R.write_timeline(dict(DUR=DUR, BPM=BPM, BAR=BAR, REV=REV, RECAP=RECAP, END=END_T,
                          KICKS=sorted(set(round(k, 3) for k in sg.kicks))))
    print("timeline ok")


BG = Layer(HERE / "work" / "layer.mp4", fps=FPS)


def draw(c, t, f):
    if t < RECAP:
        c.drawImage(BG.image(f), 0, 0)
    else:
        # recap: five bands, each a slice of its reveal's hold, sliding in
        band = H / 5
        for i in range(5):
            src = int(round((REV[i] + min(2.6, 1.9 + (t - RECAP) * 0.12)) * FPS))
            img = BG.image(src)
            k = e_out(prog(t, RECAP + 0.06 * i, 0.4))
            c.save()
            c.clipRect(skia.Rect.MakeXYWH(0, i * band, W, band))
            c.translate((1 - k) * (W if i % 2 else -W), 0)
            # the whole frame, shrunk so the logo (y ~ 330..1400 of the frame) fits the band, on the right
            c.translate(760, i * band + band / 2)
            c.scale(0.33, 0.33)
            c.translate(-W / 2, -880)
            c.drawImage(img, 0, 0)
            c.restore()
            text(c, f"0{i + 1}", 60, i * band + band / 2 - 20, "monob", 48, LIME, k, anchor="l")
            text(c, NAMES[i], 60, i * band + band / 2 + 50, "black", 50, WHITE, k, anchor="l")
            c.drawRect(skia.Rect.MakeXYWH(0, i * band - 3, W, 6), fill(INK))
        dim = 0.3 * e_out(prog(t, S.t("nos"), 0.3))
        c.drawRect(skia.Rect.MakeWH(W, H), fill(INK, dim))
    # hook title
    if t < REV[0]:
        k1 = e_back(prog(t, 0.1, 0.35), 2)
        text(c, "5 LOGO", W / 2, 690, "unbounded", 150, WHITE, clamp(k1), outline=12, shadow=20)
        k2 = e_back(prog(t, 0.45, 0.35), 2)
        text(c, "ANIMATIONS", W / 2, 840, "unbounded", 102, LIME, clamp(k2), outline=10, shadow=20)
    # technique label per reveal
    for i, r0 in enumerate(REV):
        if r0 <= t < min(r0 + 1.5 * BAR, RECAP):
            k = e_out(prog(t, r0 + 0.05, 0.3))
            text(c, f"0{i + 1} / 05", W / 2, 215, "monob", 40, LIME, k)
            c.save()
            c.clipRect(skia.Rect.MakeLTRB(0, 1600, W, 1760))
            text(c, NAMES[i], W / 2, 1720 + 120 * (1 - k), "unbounded", 82, WHITE, 1, shadow=16)
            c.restore()
    if t >= END_T:
        endcard(c, t, END_T)
    CAP.draw(c, t)


CAP = Captions(S.words(skip=("hook", "hook2", "l1", "l2", "l3", "l4", "l5")), y=1060, size=80, box=True).mute(END_T, DUR)
film = Film(draw, DUR, FPS, out_dir=HERE / "out")


def sound():
    import music as M
    from sound import Mix
    bed = song().master()
    m = Mix(DUR)
    m.voice(S.placements())
    m.music(bed, gain_db=-2, duck_db=-7, fade_out=1.5)
    sr = M.SR
    tt = np.arange(int(1.2 * sr)) / sr
    # set-specific sfx
    liquid = M.filt(M.noise(len(tt)), "lp", 900) * np.sin(2 * np.pi * 3 * tt) ** 2 * np.exp(-tt * 2)
    m.sfx(liquid.astype(np.float32), REV[0] + 0.3, -8)
    m.sfx("riser", REV[1] - 0.05, -10, dur=1.5)
    m.sfx("sparkle", REV[1] + 1.45, -8)
    buzz = (np.sign(np.sin(2 * np.pi * 120 * tt)) * 0.3 + M.filt(M.noise(len(tt)), "hp", 4000) * 0.2) * np.exp(-tt * 3)
    for k, dt in enumerate((0.15, 0.55, 0.85)):
        m.sfx(buzz.astype(np.float32), REV[2] + dt, -14)
        m.sfx("click", REV[2] + dt, -8)
    for k in range(6):
        m.sfx("glitch", REV[3] + 0.05 + k * 0.2, -10)
    for k, dt in enumerate((0.45, 0.95, 1.45)):
        m.sfx(M.impact(1.2, 30 + 2 * k) * 0.8, REV[4] + dt, -3)
    m.sfx("whoosh", RECAP - 0.2, -10)
    m.sfx("whoosh", END_T - 0.25, -10)
    m.sfx("ding", END_T + 0.1, -12)
    m.finish(HERE / "out" / "picture.mp4", HERE / "out" / "B2_03_logo_reveals.mp4", HERE / "work")


if __name__ == "__main__":
    R.cli(film, sound, prep)
