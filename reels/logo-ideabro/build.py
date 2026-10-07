"""IDEABRO STUDIO: five logo animations (liquid chrome, particle storm, neon sign, glitch, heavy metal)
plus a showcase reel of all five.

    python3 build.py stills <style 1-5> 1.0 2.5 6.0 [--fmt 16x9]
    python3 build.py layer <style> --fmt 16x9|9x16      picture -> work/<style>/<fmt>.mp4 (60 fps)
    python3 build.py sound [style]                       stings -> work/<style>/sting.wav
    python3 build.py final <style> --fmt 16x9            mux -> out/
    python3 build.py showcase                            out/IDEABRO_5_styles_9x16.mp4
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WORK, OUT = HERE / "work", HERE / "out"
FPS = 60
STYLES = {1: "chrome", 2: "particles", 3: "neon", 4: "glitch", 5: "metal"}
TITLES = {1: "LIQUID CHROME", 2: "PARTICLE STORM", 3: "NEON SIGN", 4: "GLITCH", 5: "HEAVY METAL"}
# key times per style (s): the picture and the sound both read these
T = {
    "chrome": {"dur": 6.5, "melt": 1.25, "form": 1.45, "settle": 2.7},
    "particles": {"dur": 6.5, "go": 0.35, "land": 2.75, "flat": 2.85},
    "neon": {"dur": 6.5, "b": 0.55, "name": 1.4, "studio": 2.1, "full": 2.7},
    "glitch": {"dur": 6.5, "in": 0.2, "settle": 2.35, "blips": [3.7, 5.0]},
    "metal": {"dur": 6.5, "b": 0.85, "name": [round(1.55 + 0.085 * i, 3) for i in range(7)], "studio": 2.45,
              "rise": 2.75, "rise1": 4.3},
}
FORMATS = {"16x9": (1920, 1080), "9x16": (1080, 1920), "1x1": (1080, 1080)}


def prep():
    WORK.mkdir(exist_ok=True)
    subprocess.run([sys.executable, str(ROOT / "logo-b" / "geom.py")], check=True, stdout=subprocess.DEVNULL)
    (WORK / "timeline.json").write_text(json.dumps(T))


def render3d(style, fmt, *extra):
    w, h = FORMATS[fmt]
    cmd = ["node", str(ROOT / "batch2" / "render3d.mjs"), str(HERE / f"s{style}.html"), "--w", str(w), "--h", str(h),
           "--fps", str(FPS), "--dur", str(T[STYLES[style]]["dur"]), *extra]
    subprocess.run(cmd, check=True)


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


if __name__ == "__main__":
    what = sys.argv[1]
    fmt = arg("--fmt", "16x9")
    prep()
    if what == "stills":
        st = int(sys.argv[2])
        ts = ",".join(a for a in sys.argv[3:] if a[0].isdigit() and "x" not in a)
        render3d(st, fmt, "--stills", ts, "-o", str(OUT / "stills" / f"s{st}_{fmt}"))
    elif what == "layer":
        st = int(sys.argv[2])
        render3d(st, fmt, "--png", "--crf", "12", "--preset", "slow", "--workers", arg("--workers", "4"),
                 "-o", str(WORK / STYLES[st] / f"{fmt}.mp4"))
    elif what == "sound":
        import stings
        for st in ([int(sys.argv[2])] if len(sys.argv) > 2 and sys.argv[2].isdigit() else STYLES):
            stings.build(STYLES[st], T[STYLES[st]], WORK / STYLES[st] / "sting.wav")
    elif what == "final":
        import deliver
        st = int(sys.argv[2])
        deliver.final(st, STYLES[st], fmt, WORK, OUT, FPS, T[STYLES[st]]["dur"])
    elif what == "showcase":
        import deliver
        deliver.showcase(STYLES, TITLES, WORK, OUT, FPS, T)
