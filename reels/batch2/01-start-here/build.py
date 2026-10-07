"""B2-01 "Start Here": the Vibe Editing System trailer. One skill -> every kind of video.
3D (Three.js, headless) for the worlds, skia for type/captions, music-first edit at 140 BPM.

    python3 build.py prep      # narration, music, timeline.json, screen textures
    python3 build.py web 1 4.4 # 3D stills (fast look)
    python3 build.py layer     # render the 3D layer (slow: ~12 min)
    python3 build.py sheet | stills 3 9 | render | sound | all
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import skia

HERE = Path(__file__).resolve().parent
REELS = HERE.parent.parent
sys.path.insert(0, str(REELS / "common"))
sys.path.insert(0, str(HERE))
from kit import (W, H, INK, LIME, WHITE, Captions, Film, Layer, clamp, e_back, e_out, endcard, fill, lerp,  # noqa: E402
                 prog, text)
from script import LINES, VOICE  # noqa: E402
from voice import Script, narrate  # noqa: E402

FPS = 30
BPM = 140
BAR = 240 / BPM
vo = narrate(LINES, HERE / "work", VOICE)
S = Script(vo, [("hook", "@", 0.12), ("skill", 0.08), ("c1", "@", 3.45), ("c2", "@", 4.35), ("c3", "@", 5.25),
                ("c4", "@", 6.15), ("nos", "@", 7.1), ("type", "@", 10.75), ("builds", "@", 13.85),
                ("this", "@", 16.95), ("cta", "@", 18.75)])
END_T = 21.1
DUR = END_T + 2.9
DROP, BREAK, DROP2, LOGO = 2 * BAR, 6 * BAR, 8 * BAR, 10 * BAR
CATS = [S.t(k) for k in ("c1", "c2", "c3", "c4")]
PROMPT = "a cinematic trailer for my page — fast, neon, 3D"

# footage on the screens: (name, file, t0, t1, vertical)
SRC = [
    ("clay", REELS / "01-claymation/work/nocap.mp4", 9.4, 16.0, True),
    ("styles", REELS / "02-five-styles/work/nocap.mp4", 7.0, 23.0, True),
    ("ad", REELS / "03-product-ad/work/nocap.mp4", 4.6, 14.0, True),
    ("kinetic", REELS / "04-kinetic-quote/work/nocap.mp4", 0.4, 13.0, True),
    ("pixel", REELS / "05-pixel-cutscene/work/nocap.mp4", 1.5, 17.0, True),
    ("asmr", REELS / "06-asmr-marbles/out/06_asmr_marbles.mp4", 6.0, 19.0, True),
    ("paper", REELS.parent / "vibe-editing-promo/out/vibe_editing_promo.mp4", 2.0, 26.0, True),
    ("claysheep", REELS.parent / "clay-vibes/out/vibe_editing_claymation.mp4", 4.0, 32.0, False),
    ("crayon", REELS.parent / "crayon-explainer/out/vibe_editing_crayon_explainer.mp4", 3.0, 34.0, False),
    ("reel", REELS.parent / "showreel/out/vibe_editing_showreel.mp4", 1.0, 27.0, False),
    ("light", REELS.parent / "evolution-light/evolution_of_light.mp4", 8.0, 80.0, False),
    ("apple", REELS.parent / "apple-vibe-editing/out/vibe_editing_apple.mp4", 1.0, 36.0, False),
]
NTEX = 24
# full-res featured clips (category beats): source, start time inside it
FEAT = [("clay", 11.2), ("ad", 7.4), ("kinetic", 3.0), ("pixel", 13.6)]
FEAT_HOLD = (0.30, 0.80)             # hero screen fills the frame between Tc+0.30 and Tc+0.80


def song():
    from music import future_bass
    return future_bass(DUR, BPM, "F#", {"drop": DROP, "break": BREAK, "drop2": DROP2}, seed=21)


def prep():
    tex = HERE / "work" / "tex"
    for name, f, t0, t1, vert in SRC:
        d = tex / name
        if d.exists() and len(list(d.glob("*.jpg"))) >= NTEX:
            continue
        d.mkdir(parents=True, exist_ok=True)
        size = "270:480" if vert else "480:270"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t0), "-t", str(t1 - t0), "-i", str(f), "-vf",
                        f"fps={NTEX / (t1 - t0):.5f},scale={size}:force_original_aspect_ratio=increase,crop={size.replace(':', ':')}",
                        "-frames:v", str(NTEX), "-start_number", "0", "-q:v", "3", str(d / "%04d.jpg")], check=True)
        print("tex", name, len(list(d.glob("*.jpg"))))
    sg = song()
    sg.master()
    words = {lid: [(w, round(S.t(lid) + s, 3)) for w, s, e in vo[lid]["words"]] for lid in S.order}
    tl = dict(DUR=DUR, BPM=BPM, BAR=BAR, DROP=DROP, BREAK=BREAK, DROP2=DROP2, LOGO=LOGO, END=END_T, CATS=CATS,
              FEAT=[f[0] for f in FEAT], HOLD=FEAT_HOLD, PROMPT=PROMPT, NTEX=NTEX,
              SRC=[dict(name=n, vertical=v) for n, _, _, _, v in SRC],
              NO=[S.find("nos", "After"), S.find("nos", "Premiere"), S.find("nos", "AI")],
              TYPE0=S.t("type") - 0.25, TYPE1=DROP2 - 0.55, ENTER=DROP2 - 0.02,
              FRAME_W=S.find("builds", "frame"), SOUND_W=S.find("builds", "sound"),
              VIBE=S.find("this", "Vibe"), KICKS=[round(k, 3) for k in sorted(set(sg.kicks))], words=words)
    (HERE / "work" / "timeline.json").write_text(json.dumps(tl, indent=1))
    print("timeline ->", HERE / "work" / "timeline.json", f"DUR {DUR:.2f}s")


def web(args, layer=False):
    cmd = ["node", str(HERE.parent / "render3d.mjs"), str(HERE / "scene.html"), "--fps", str(FPS), "--dur", f"{DUR:.3f}"]
    if layer:
        cmd += ["-o", str(HERE / "work" / "layer.mp4")] + args
    else:
        cmd += ["--stills", ",".join(args), "-o", str(HERE / "out" / "web")]
    subprocess.run(cmd, check=True)


# ---------------------------------------------------------------- 2D on top of the 3D layer
BG = Layer(HERE / "work" / "layer.mp4", fps=FPS)
PATCH = (17.0, 17.8)                      # re-rendered slice (softer logo flash): work/patch.mp4
PG = Layer(HERE / "work" / "patch.mp4", fps=FPS)
FEATV = {name: Layer(dict((n, f) for n, f, *_ in SRC)[name], fps=FPS) for name, _ in FEAT}


def draw(c, t, f):
    p0 = int(round(PATCH[0] * FPS))
    if PATCH[0] <= t < PATCH[1] and (HERE / "work" / "patch.mp4").exists():
        c.drawImage(PG.image(f - p0), 0, 0)
    else:
        c.drawImage(BG.image(f), 0, 0)
    # full-res footage while a hero screen fills the frame (the 3D layer has the low-res copy underneath)
    for (name, st), tc in zip(FEAT, CATS):
        a, b = tc + FEAT_HOLD[0], tc + FEAT_HOLD[1]
        if a <= t < b:
            k = clamp(min((t - a) / 0.07, (b - t) / 0.05))
            src_f = int(round((st + (t - a)) * FPS))
            img = FEATV[name].image(src_f)
            p = skia.Paint(Alphaf=k)
            c.drawImage(img, 0, 0, skia.SamplingOptions(), p)
            # tag
            text(c, ["CLAYMATION", "PRODUCT AD", "KINETIC TYPE", "RETRO GAME"][CATS.index(tc)], 60, 300,
                 "monob", 40, LIME, k, anchor="l")
    # logo lockup type
    lk = e_out(prog(t, S.find("this", "Vibe") - 0.05, 0.45))
    if lk > 0 and t < END_T:
        a = lk * (1 - prog(t, END_T - 0.25, 0.2))
        c.save()
        c.translate(W / 2, 1440)
        s = lerp(1.15, 1.0, lk)
        c.scale(s, s)
        text(c, "VIBE EDITING", 0, 0, "unbounded", 104, WHITE, a, tracking=0.02, shadow=18)
        c.restore()
        a2 = e_out(prog(t, S.t("cta"), 0.4)) * (1 - prog(t, END_T - 0.25, 0.2))
        text(c, "follow · learn it before everyone else", W / 2, 1530, "mono", 36, LIME, a2)
    if t >= END_T:
        endcard(c, t, END_T)
    CAP.draw(c, t)


CAP = Captions(S.words(), y=1560, size=86).mute(S.t("this"), DUR)
CAP.mute(S.t("nos") - 0.05, S.end("nos") + 0.3)
film = Film(draw, DUR, FPS, out_dir=HERE / "out")


# ---------------------------------------------------------------- sound
def sound():
    import music as M
    from sound import Mix
    sg = song()
    bed = sg.master()
    m = Mix(DUR)
    m.voice(S.placements(), gain_db=0)
    m.music(bed, gain_db=-3, duck_db=-8, fade_out=1.5)
    T = json.loads((HERE / "work" / "timeline.json").read_text())
    for tc in CATS:
        m.sfx(M.impact(0.8, 33) * 0.6, tc + FEAT_HOLD[0] - 0.02, -8)
        m.sfx("whoosh", tc - 0.1, -12, dur=0.45)
    for tn in T["NO"]:
        glass = M.filt(M.noise(int(0.5 * M.SR)), "hp", 3000) * np.exp(-np.arange(int(0.5 * M.SR)) / M.SR * 9)
        ting = sum(np.sin(2 * np.pi * f * np.arange(int(0.6 * M.SR)) / M.SR) * np.exp(-np.arange(int(0.6 * M.SR)) / M.SR * k)
                   for f, k in ((2900, 9), (4300, 12), (6100, 16)))
        clip = np.zeros(int(0.6 * M.SR), np.float32)
        clip[: len(glass)] += glass
        clip += 0.25 * ting
        m.sfx(clip, tn + 0.15, -6)
        m.sfx(M.impact(1.0, 31) * 0.5, tn + 0.15, -10)
    m.sfx("typing", T["TYPE0"] + 0.2, -14, dur=T["TYPE1"] - T["TYPE0"] - 0.2, cps=22)
    m.sfx("click", T["ENTER"], -4)
    m.sfx("whoosh", END_T - 0.25, -10)
    m.sfx("ding", END_T + 0.1, -12)
    m.finish(HERE / "out" / "picture.mp4", HERE / "out" / "B2_01_start_here.mp4", HERE / "work")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    print(f"duration {DUR:.2f}s")
    if cmd == "prep":
        prep()
    elif cmd == "web":
        web(sys.argv[2:])
    elif cmd == "layer":
        web(sys.argv[2:], layer=True)
    elif cmd == "sheet":
        film.sheet()
    elif cmd == "stills":
        film.stills([float(x) for x in sys.argv[2:]])
    elif cmd == "render":
        film.render()
    elif cmd == "sound":
        sound()
    elif cmd == "all":
        film.render()
        sound()
