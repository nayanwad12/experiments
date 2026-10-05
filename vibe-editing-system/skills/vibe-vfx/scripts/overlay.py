"""overlay: lay a transparent graphics overlay (.mov from scene.py / Stage.render(alpha=True)) over footage.

    python3 vibe/overlay.py work/captioned.mp4 work/overlay.mov -o out/final_v1.mp4
    python3 vibe/overlay.py work/cut.mp4 work/lowerthird.mov --at 3.5 -o work/with_name.mp4

The base video's audio is kept. --at starts the overlay that many seconds into the base.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vibelib import composite  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base")
    ap.add_argument("overlay")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--at", type=float, default=0.0)
    a = ap.parse_args()
    composite(a.base, a.overlay, a.out, a.at)
    print(f"done -> {a.out}")


if __name__ == "__main__":
    main()
