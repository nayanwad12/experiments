"""B2-04 Stylised animation: a 3D claymation mascot that talks to camera (lip sync from the voice), gets poked by a
giant clay finger, reveals it's made of code, and watches its world build itself. Stop-motion on twos (12 fps).

    python3 build.py prep | web 1 6 | layer | sheet | stills 4 | render | sound | all
"""
import sys
from pathlib import Path

import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(HERE))
from b2 import Reel  # noqa: E402
from kit import (W, H, INK, LIME, WHITE, Captions, Film, Layer, clamp, e_out, endcard, fill, prog, rrect,  # noqa: E402
                 text)
from script import LINES, VOICE  # noqa: E402
from voice import Script, narrate  # noqa: E402

FPS, BPM = 30, 104
vo = narrate(LINES, HERE / "work", VOICE)
S = Script(vo, [("hi", "@", 0.35), ("sortof", 0.3), ("weeks", 0.5), ("nobody", 0.45), ("code", 0.3),
                ("world", 0.75), ("lips", 0.6), ("next", 0.7)])
END_T = S.end("next") + 0.55
DUR = END_T + 2.9
R = Reel(__file__, DUR, FPS)


def mouth_curve():
    """per frame: (open 0..1, wide 0..1) from the voice: RMS -> open, brightness (ZCR) -> wide vs round."""
    import soundfile as sf
    n = int(DUR * FPS) + 1
    op, wd = np.zeros(n), np.full(n, 0.5)
    for lid in S.order:
        x, sr = sf.read(vo[lid]["file"])
        hop = sr // FPS
        for k in range(len(x) // hop):
            seg = x[k * hop:(k + 1) * hop]
            f = int(round(S.t(lid) * FPS)) + k
            if 0 <= f < n:
                op[f] = np.sqrt((seg ** 2).mean())
                wd[f] = np.clip((np.abs(np.diff(np.sign(seg))).mean() - 0.05) * 6, 0, 1)
    op = np.clip(op / (np.percentile(op[op > 0], 92) + 1e-9), 0, 1) ** 0.8
    sm = np.convolve(op, [0.25, 0.5, 0.25], mode="same")
    return [[round(float(a), 3), round(float(b), 3)] for a, b in zip(sm, wd)]


def song():
    from music import whimsical
    return whimsical(DUR, BPM, "D", seed=9)


def prep():
    import clay as C
    from PIL import Image
    tex = C._make_texture(512, seed=11)
    Image.fromarray(tex.toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3]).save(HERE / "work" / "clay_tex.png")
    w = {lid: [(w_, round(S.t(lid) + s, 3)) for w_, s, e in vo[lid]["words"]] for lid in S.order}
    R.write_timeline(dict(
        DUR=DUR, END=END_T, MOUTH=mouth_curve(), FPS=FPS,
        HI=S.t("hi"), SORT=S.t("sortof"), WEEKS=S.t("weeks"), HAND=S.find("weeks", "hand"), NOBODY=S.t("nobody"),
        CODE=S.find("code", "code") - 0.1, CODE_END=S.t("world") - 0.15, WORLD=S.t("world"), LIPS=S.t("lips"),
        NEXT=S.t("next"), COMMENTS=S.find("next", "comments")))
    print("timeline ok")


BG = Layer(HERE / "work" / "layer.mp4", fps=FPS)
CODE = ["const body = clay(sphere(1.0), LIME);", "body.boil(seed = drawing);", "eyes.blink(every = 3.1);",
        "mouth.open = voice.loudness(t);", "mouth.wide = voice.brightness(t);", "arm.wave(on = 'comments');",
        "world.drop(desk, lamp, plant, laptop);", "camera.fps = 12;   // on twos", "light.key.soft = true;",
        "finger.poke(at = word('hand'));"]


def draw(c, t, f):
    c.drawImage(BG.image(f), 0, 0)
    t0, t1 = S.find("code", "code") - 0.05, S.t("world") - 0.1
    if t0 <= t < t1:
        a = e_out(prog(t, t0, 0.25)) * (1 - prog(t, t1 - 0.2, 0.2))
        c.drawRRect(rrect(60, 1180, W - 120, 470, 26), fill("#05070a", 0.8 * a))
        n = int((t - t0) * 9)
        for i, ln in enumerate(CODE[:max(0, n)][-9:]):
            text(c, ln, 100, 1240 + i * 46, "mono", 30, "#D4FF3F" if i % 2 == 0 else "#C9F2FF", a, anchor="l")
    if t >= END_T:
        endcard(c, t, END_T)
    CAP.draw(c, t)


CAP = Captions(S.words(), y=1660, size=84).mute(END_T, DUR)
film = Film(draw, DUR, FPS, out_dir=HERE / "out")


def sound():
    import json
    import music as M
    from sound import Mix
    T = json.loads((HERE / "work" / "timeline.json").read_text())
    bed = song().master()
    m = Mix(DUR)
    m.voice(S.placements(), chain="broadcast")
    m.music(bed, gain_db=-6, duck_db=-10, fade_out=1.5)
    sr = M.SR

    def squish(p=1.0, d=0.22):
        n = int(d * sr)
        x = M.filt(M.noise(n), "lp", 900 * p) * M.env(n, 0.004, d * 0.7, 0, 0.02)
        x += 0.6 * M.osc_sin(np.linspace(260 * p, 90 * p, n), n) * M.env(n, 0.002, d * 0.5, 0, 0.02)
        return x.astype(np.float32)

    m.sfx(squish(1.2), 0.25, -6)                                   # hop in
    m.sfx("swish", T["HAND"] - 0.45, -12)
    m.sfx(squish(0.8, 0.35), T["HAND"], -3)                        # poke
    m.sfx("pop", T["NOBODY"] + 0.05, -8)                           # finger vanishes
    m.sfx("glitch", T["CODE"], -8)
    m.sfx("glitch", T["CODE_END"], -10)
    for i in range(6):
        m.sfx(squish(0.7 + 0.12 * i), T["WORLD"] + 0.12 + i * 0.28, -6)
    m.sfx("sparkle", T["LIPS"], -12)
    m.sfx("pop", T["COMMENTS"], -8)
    m.sfx("whoosh", END_T - 0.25, -10)
    m.sfx("ding", END_T + 0.1, -12)
    m.finish(HERE / "out" / "picture.mp4", HERE / "out" / "B2_04_clay_mascot.mp4", HERE / "work")


if __name__ == "__main__":
    R.cli(film, sound, prep)
