"""b2: shared build plumbing for the batch-2 Reels (3D layer in headless Chromium + skia overlays + mix).

    from b2 import Reel
    R = Reel(__file__, dur=DUR, fps=30)
    R.write_timeline(dict(...))           # -> work/timeline.json, read by scene.js
    R.cli(film, sound, prep)              # prep | web t.. | layer | sheet | stills t.. | render | sound | all
"""
import json
import subprocess
import sys
from pathlib import Path

B2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(B2.parent / "common"))


class Reel:
    def __init__(self, file, dur, fps=30):
        self.dir = Path(file).resolve().parent
        self.dur, self.fps = dur, fps
        (self.dir / "work").mkdir(exist_ok=True)
        (self.dir / "out").mkdir(exist_ok=True)

    def write_timeline(self, d):
        (self.dir / "work" / "timeline.json").write_text(json.dumps(d, indent=1))

    def web(self, args, layer=False):
        cmd = ["node", str(B2 / "render3d.mjs"), str(self.dir / "scene.html"), "--fps", str(self.fps),
               "--dur", f"{self.dur:.3f}"]
        if layer:
            cmd += ["-o", str(self.dir / "work" / "layer.mp4")] + args
        else:
            cmd += ["--stills", ",".join(args), "-o", str(self.dir / "out" / "web")]
            subprocess.run(cmd, check=True)
            from PIL import Image
            ims = [Image.open(self.dir / "out" / "web" / f"w_{float(a):.2f}.png").resize((360, 640)) for a in args]
            row = Image.new("RGB", (360 * len(ims), 640))
            for i, im in enumerate(ims):
                row.paste(im, (i * 360, 0))
            row.save(self.dir / "out" / "webrow.png")
            print("->", self.dir / "out" / "webrow.png")
            return
        subprocess.run(cmd, check=True)

    def cli(self, film, sound, prep=None):
        cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
        a = sys.argv[2:]
        print(f"duration {self.dur:.2f}s")
        if cmd == "prep" and prep:
            prep()
        elif cmd == "web":
            self.web(a)
        elif cmd == "layer":
            self.web(a, layer=True)
        elif cmd == "sheet":
            film.sheet()
        elif cmd == "stills":
            film.stills([float(x) for x in a])
        elif cmd == "render":
            film.render()
        elif cmd == "sound":
            sound()
        elif cmd == "all":
            if prep:
                prep()
            self.web([], layer=True)
            film.render()
            sound()
