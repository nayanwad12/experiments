"""Glassmorphism Reel for ideabro studio: "This video was edited by the Vibe Editing System."
Hook -> what it can make -> the 4-step process -> CTA (comment VIBE) -> brand lockup. 9:16, ~36 s.

Every frame is HTML/CSS glass (backdrop blur, gradient borders, specular sheens) rendered headlessly in Chromium;
music, SFX and narration are synthesised locally (music.py, audio_kit.py, Kokoro).

    python3 build.py prep        # narration + music grid -> work/timeline.json
    python3 build.py web 1 9 20  # stills -> out/web/ + out/webrow.png
    python3 build.py sheet       # contact sheet of 12 stills -> out/sheet.png
    python3 build.py layer       # render the picture -> work/layer.mp4
    python3 build.py sound       # music + voice + sfx -> out/ideabro_vibe_editing_glass.mp4
    python3 build.py all
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REELS = HERE.parent
sys.path.insert(0, str(REELS / "common"))
sys.path.insert(0, str(HERE))
from script import LINES, VOICE  # noqa: E402
from voice import Script, narrate  # noqa: E402

FPS, BPM = 30, 120
BAR = 240 / BPM                         # 2.0 s
vo = narrate(LINES, HERE / "work", VOICE)
S = Script(vo, [("hook", "@", 0.30), ("hook2", "@", 1.95), ("no", "@", 5.05), ("any", "@", 4 * BAR + 0.05),
                ("list", "@", 11.25), ("proc", "@", 16.15), ("s1", "@", 9 * BAR), ("s2", "@", 10 * BAR),
                ("s3", "@", 11 * BAR), ("s4", "@", 12 * BAR), ("cta", "@", 13 * BAR + 0.35),
                ("cta2", "@", 14 * BAR + 0.2), ("brand", "@", 15 * BAR + 0.75)])
END_T = S.end("brand")
DUR = round(END_T + 3.4, 2)
OUT = HERE / "out" / "ideabro_vibe_editing_glass.mp4"
MARKS = {"drop": 4 * BAR, "break": 8 * BAR, "drop2": 12 * BAR}


def song():
    from music import future_bass
    return future_bass(DUR, BPM, "F", MARKS, seed=21)


def prep():
    sg = song()
    sg.master()
    words = {lid: [[w, round(S.start[lid] + s, 3), round(S.start[lid] + e, 3)] for w, s, e in vo[lid]["words"]]
             for lid in S.order}
    tl = dict(DUR=DUR, FPS=FPS, BAR=BAR, END=END_T, lines={lid: [S.t(lid), S.end(lid)] for lid in S.order},
              words=words, kicks=sorted(set(round(k, 3) for k in sg.kicks)), **{k.upper(): v for k, v in MARKS.items()})
    (HERE / "work").mkdir(exist_ok=True)
    (HERE / "work" / "timeline.json").write_text(json.dumps(tl, indent=1))
    print(f"timeline ok  dur {DUR:.2f}s")


def node(args):
    subprocess.run(["node", str(REELS / "batch2" / "render3d.mjs"), str(HERE / "scene.html"), "--fps", str(FPS),
                    "--dur", f"{DUR:.3f}"] + args, check=True)


def web(ts):
    node(["--stills", ",".join(ts), "-o", str(HERE / "out" / "web")])
    from PIL import Image
    ims = [Image.open(HERE / "out" / "web" / f"w_{float(a):.2f}.png").resize((360, 640)) for a in ts]
    row = Image.new("RGB", (360 * len(ims), 640))
    for i, im in enumerate(ims):
        row.paste(im, (i * 360, 0))
    row.save(HERE / "out" / "webrow.png")
    print("->", HERE / "out" / "webrow.png")


def sheet():
    from PIL import Image
    ts = [0.6, 2.6, 4.2, 6.6, 9.4, 12.6, 16.6, 18.9, 21.0, 25.2, 29.4, 33.4]
    node(["--stills", ",".join(map(str, ts)), "-o", str(HERE / "out" / "web")])
    sh = Image.new("RGB", (6 * 270, 2 * 480))
    for i, t in enumerate(ts):
        im = Image.open(HERE / "out" / "web" / f"w_{t:.2f}.png").resize((270, 480))
        sh.paste(im, ((i % 6) * 270, (i // 6) * 480))
    sh.save(HERE / "out" / "sheet.png")
    print("->", HERE / "out" / "sheet.png")


def layer():
    node(["--workers", "2", "-o", str(HERE / "work" / "layer.mp4")])


def sound():
    from sound import Mix
    import audio_kit as ak
    sg = song()
    bed = sg.master()
    m = Mix(DUR)
    m.voice(S.placements())
    m.music(bed, gain_db=-11, duck_db=-10, fade_out=2.2)
    w = {lid: vo[lid]["words"] for lid in S.order}
    # hook: card blooms, the badge lands
    m.sfx("riser", 0.0, -20, dur=1.2)
    m.sfx("sparkle", S.find("hook2", "Vibe") - 0.05, -12)
    m.sfx("ding", S.find("hook2", "System"), -16)
    # "No timeline / keyframes / After Effects": a glass tink as each tile lands, a swish as it falls
    for i in range(3):
        t = S.start["no"] + [x for x in w["no"] if x[0] == "No"][i][1]
        m.sfx("pop", t, -14)
        m.sfx("swish", t + 0.55, -16)
    m.sfx("whoosh", MARKS["drop"] - 0.45, -10, dur=0.6)
    # the five formats flip by in the coverflow
    for word in ("Kinetic", "Product", "3D", "Explainers", "Logo"):
        m.sfx("swish", S.find("list", word) - 0.08, -13)
    m.sfx("whoosh", S.t("proc") - 0.25, -12, dur=0.6)
    # steps
    for lid in ("s1", "s2", "s3", "s4"):
        m.sfx("tick", S.t(lid) - 0.06, -10)
    m.sfx("typing", S.t("s1") + 0.25, -15, dur=1.45)
    m.sfx("click", S.t("s1") + 1.85, -10)
    m.sfx("typing", S.t("s2") + 0.15, -19, dur=1.5)
    m.sfx("ding", S.t("s4") + 1.55, -14)
    # CTA: the button tap, comments popping in
    m.sfx("whoosh", S.t("cta") - 0.3, -12, dur=0.6)
    m.sfx("click", S.find("cta2", "VIBE") + 0.05, -8)
    for i in range(6):
        m.sfx("pop", S.find("cta2", "VIBE") + 0.45 + 0.22 * i, -20 - i)
    # brand: impact + shimmer
    m.sfx("whoosh", S.t("brand") - 0.55, -11, dur=0.6)
    m.sfx("impact", S.t("brand") - 0.1, -9)
    m.sfx("sparkle", S.t("brand") + 0.55, -13)
    del ak
    m.finish(HERE / "work" / "layer.mp4", OUT, HERE / "work")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    print(f"duration {DUR:.2f}s")
    if cmd == "prep":
        prep()
    elif cmd == "web":
        web(sys.argv[2:])
    elif cmd == "sheet":
        sheet()
    elif cmd == "layer":
        layer()
    elif cmd == "sound":
        sound()
    elif cmd == "all":
        prep()
        layer()
        sound()
