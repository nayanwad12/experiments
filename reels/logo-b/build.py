"""B monogram logo animation: 3D light-trace reveal -> solid ceramic/chrome B -> exact flat logo.

    python3 build.py stills 1.0 3.3 7.5 [--fmt 16x9]   frames -> out/stills/<fmt>/
    python3 build.py layer --fmt 16x9                   picture -> work/<fmt>/layer.mp4 (60 fps)
    python3 build.py sound                              sound design -> work/sting.wav
    python3 build.py final --fmt 16x9                   picture + sound -> out/
    python3 build.py all                                every format
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WORK, OUT = HERE / "work", HERE / "out"
FPS, DUR = 60, 8.0

# key times (s): everything in the picture and the sound hangs off these
T = {"trace0": 0.35, "trace1": 2.25, "scan0": 1.95, "impact": 3.3, "sweep0": 3.9, "sweep1": 5.3,
     "flat0": 5.6, "flat1": 6.55, "end": DUR}

FORMATS = {   # name: (w, h)   16x9 is the 4K master
    "16x9": (3840, 2160),
    "9x16": (1080, 1920),
    "1x1": (1080, 1080),
}


def prep():
    WORK.mkdir(exist_ok=True)
    subprocess.run([sys.executable, str(HERE / "geom.py")], check=True)
    (WORK / "timeline.json").write_text(json.dumps(T))


def render3d(fmt, *extra):
    w, h = FORMATS[fmt]
    cmd = ["node", str(ROOT / "batch2" / "render3d.mjs"), str(HERE / "scene.html"), "--w", str(w), "--h", str(h),
           "--fps", str(FPS), "--dur", str(DUR), *extra]
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


if __name__ == "__main__":
    what = sys.argv[1]
    fmt = arg("--fmt", "16x9")
    prep()
    if what == "stills":
        ts = ",".join(a for a in sys.argv[2:] if a[0].isdigit() and "x" not in a)
        render3d(fmt, "--stills", ts, "-o", str(OUT / "stills" / fmt))
    elif what == "layer":
        render3d(fmt, "--png", "--crf", arg("--crf", "10"), "--preset", "slow", "--workers", arg("--workers", "4"),
                 "-o", str(WORK / fmt / "layer.mp4"))
    elif what == "sound":
        import sting
        sting.build(T, DUR, WORK / "sting.wav")
    elif what == "final":
        import deliver
        deliver.final(fmt, WORK / fmt / "layer.mp4", WORK / "sting.wav", OUT, FPS, DUR)
