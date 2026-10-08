"""doctor: check (and optionally install) everything a Vibe Editing project needs.

    python3 scripts/doctor.py                     # core check
    python3 scripts/doctor.py --kit talking-head  # core + what that video type needs
    python3 scripts/doctor.py --kit all --install # install every missing Python package

Kits: core, talking-head, launch, motion, animation, vfx, ai-footage, audio, bulk, web, other, all
"""

import argparse
import importlib
import platform
import shutil
import subprocess
import sys

# kit -> list of (import name, pip name, why)
CORE = [
    ("numpy", "numpy", "frames and audio are numpy arrays"),
    ("scipy", "scipy", "audio filters, resampling"),
    ("PIL", "Pillow", "stills, contact sheets, image work"),
    ("imageio_ffmpeg", "imageio-ffmpeg", "bundled ffmpeg fallback"),
]
GRAPHICS = [("skia", "skia-python", "fast 2D vector graphics and text for every frame")]
SPEECH = [("faster_whisper", "faster-whisper", "transcription with word timestamps")]
TTS = [("kokoro_onnx", "kokoro-onnx", "local AI voiceover"), ("soundfile", "soundfile", "wav read/write")]
VISION = [("cv2", "opencv-python-headless", "tracking, optical flow, image ops")]
MATTE = [("rembg", "rembg[cpu]", "background removal / person cutouts")]

KITS = {
    "core": CORE,
    "talking-head": CORE + SPEECH + GRAPHICS,
    "launch": CORE + GRAPHICS,
    "motion": CORE + GRAPHICS,
    "animation": CORE + GRAPHICS + TTS,
    "vfx": CORE + GRAPHICS + VISION + MATTE + SPEECH,
    "ai-footage": CORE + GRAPHICS + VISION + SPEECH,
    "audio": CORE + GRAPHICS + SPEECH + TTS,
    "bulk": CORE + GRAPHICS + TTS,
    "web": CORE,
    "other": CORE,
}
KITS["all"] = list({p[1]: p for kit in KITS.values() for p in kit}.values())


def have_module(name):
    try:
        importlib.import_module(name)
        return True
    except Exception:
        return False


def ffmpeg_hint():
    sysname = platform.system()
    if sysname == "Darwin":
        return "brew install ffmpeg"
    if sysname == "Windows":
        return "winget install Gyan.FFmpeg   (or: choco install ffmpeg)"
    return "sudo apt install ffmpeg   (Fedora: sudo dnf install ffmpeg)"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kit", default="core", choices=sorted(KITS))
    ap.add_argument("--install", action="store_true", help="pip install whatever is missing")
    a = ap.parse_args()

    print("Ideabro Studio · Vibe Editing System · doctor\n")
    ok = True
    v = sys.version_info
    py_ok = v >= (3, 9)
    print(f"  {'OK ' if py_ok else 'BAD'}  Python {v.major}.{v.minor}  (need 3.9+)")
    ok &= py_ok

    sys_ff = shutil.which("ffmpeg")
    if sys_ff:
        print(f"  OK   ffmpeg  {sys_ff}")
    elif have_module("imageio_ffmpeg"):
        print("  OK   ffmpeg  (bundled via imageio-ffmpeg; system ffmpeg optional:", ffmpeg_hint() + ")")
    else:
        print("  ..   ffmpeg  not found yet; imageio-ffmpeg below provides it")

    missing = []
    for mod, pip_name, why in KITS[a.kit]:
        good = have_module(mod)
        print(f"  {'OK ' if good else 'MISS'} {pip_name:24s} {why}")
        if not good:
            missing.append(pip_name)

    if a.kit in ("web", "all", "motion", "launch"):
        node = shutil.which("node")
        print(f"  {'OK ' if node else 'opt'}  node  {'(' + node + ')' if node else '(optional: only for HTML/WebGL rendering with Playwright)'}")

    if missing:
        cmd = [sys.executable, "-m", "pip", "install", *missing]
        if a.install:
            print("\nInstalling:", " ".join(missing))
            r = subprocess.run(cmd)
            if r.returncode != 0:
                print("\npip failed. Try again with:  " + " ".join(cmd) + " --user")
                if platform.system() == "Linux" and "skia-python" in missing:
                    print("skia-python on Linux also needs:  sudo apt install libegl1 libgl1")
                sys.exit(1)
            print("\nDone. Re-run doctor to confirm.")
        else:
            ok = False
            print("\nMissing packages. Install with:\n  " + " ".join(cmd))
            print("or run:  python3 scripts/doctor.py --kit", a.kit, "--install")
    if ok and not missing:
        print("\nAll set. Direct the vibe.")
    sys.exit(0 if ok or a.install else 1)


if __name__ == "__main__":
    main()
