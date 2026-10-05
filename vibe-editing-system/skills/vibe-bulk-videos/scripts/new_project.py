"""new_project: scaffold a Vibe Editing project folder.

    python3 scripts/new_project.py my-launch-reel --kind launch --format 9:16 --fps 30
    python3 scripts/new_project.py client-film --kind ai-footage --format 16:9 --fps 24 --brand custom

Creates:
    my-launch-reel/
      raw/        your footage, photos, logos, voice takes (never edited in place)
      assets/     cleaned logos, cutouts, music you own
      fonts/      downloaded brand fonts
      work/       intermediate files (transcripts, mattes, drafts, stills)
      out/        final renders only
      brief.md    the creative brief (fill it in with Claude)
      brand.json  palette + fonts (Ideabro house style by default)
      timeline.py single source of truth for every timing
      scene.py    starter animation (frames as a function of time), edit freely
      vibe/       the Vibe Editing toolkit (run tools as: python3 vibe/<tool>.py)
      CLAUDE.md   project rules Claude follows on every turn
      .gitignore  keeps footage and renders out of git
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"
sys.path.insert(0, str(HERE))
from vibelib import FORMATS, IDEABRO  # noqa: E402

KINDS = ["talking-head", "launch", "motion", "animation", "vfx", "ai-footage", "audio", "bulk", "other"]

GITIGNORE = """# Vibe Editing: keep heavy media out of git
raw/
work/
out/
*.mp4
*.mov
*.wav
*.mp3
*.npy
*.npz
*.onnx
__pycache__/
.DS_Store
# keep tiny final stills if you like:
!out/stills/*.png
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name")
    ap.add_argument("--kind", default="other", choices=KINDS)
    ap.add_argument("--format", default="9:16", choices=sorted(FORMATS))
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--duration", type=float, default=30)
    ap.add_argument("--brand", default="ideabro", choices=["ideabro", "custom"])
    ap.add_argument("--no-fonts", action="store_true")
    a = ap.parse_args()

    root = Path(a.name)
    if root.exists() and any(root.iterdir()):
        sys.exit(f"{root} already exists and is not empty; pick a new name")
    for d in ("raw", "assets", "fonts", "work", "out/stills"):
        (root / d).mkdir(parents=True, exist_ok=True)

    w, h = FORMATS[a.format]
    subs = {"{{NAME}}": a.name, "{{KIND}}": a.kind, "{{FORMAT}}": a.format, "{{W}}": str(w), "{{H}}": str(h),
            "{{FPS}}": f"{a.fps:g}", "{{DURATION}}": f"{a.duration:g}"}

    def render_template(src, dst):
        text = (TEMPLATES / src).read_text()
        for k, v in subs.items():
            text = text.replace(k, v)
        (root / dst).write_text(text)

    render_template("brief.md", "brief.md")
    render_template("project-CLAUDE.md", "CLAUDE.md")
    render_template("timeline.py", "timeline.py")
    render_template("scene.py", "scene.py")
    (root / "vibe").mkdir(exist_ok=True)
    for py in HERE.glob("*.py"):
        if py.name != "new_project.py":
            shutil.copy2(py, root / "vibe" / py.name)
    (root / ".gitignore").write_text(GITIGNORE)

    brand = json.loads(json.dumps(IDEABRO))
    if a.brand == "custom":
        brand["name"] = "YOUR BRAND"
        brand["tagline"] = ""
        brand["_todo"] = "Replace colors/fonts with the client's brand. Keep the role names (bg, fg, accent...)."
    (root / "brand.json").write_text(json.dumps(brand, indent=2) + "\n")

    if not a.no_fonts:
        subprocess.run([sys.executable, str(HERE / "fonts.py"), "--brand", "-o", "fonts"], cwd=root)
    else:
        print("skipped fonts; later run: python3 vibe/fonts.py --brand")

    print(f"\nProject ready: {root}/  ({a.kind}, {a.format} = {w}x{h}, {a.fps:g} fps)")
    print("Tools: python3 vibe/<tool>.py  (doctor, transcribe, cut_silence, captions, audio_kit, stills, export ...)")
    print("Next: drop footage into raw/, then fill brief.md together with Claude.")


if __name__ == "__main__":
    main()
