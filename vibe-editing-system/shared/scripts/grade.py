"""grade: one-command colour looks (and LUTs) so mixed footage feels like one film.

    python3 vibe/grade.py work/cut.mp4 --look cinematic -o work/graded.mp4
    python3 vibe/grade.py work/cut.mp4 --look warm --strength 0.6 --grain 6 --vignette
    python3 vibe/grade.py work/cut.mp4 --lut assets/brand.cube --letterbox 2.39
    python3 vibe/grade.py work/cut.mp4 --look teal-orange --compare      # before|after check video
    python3 vibe/grade.py --list

Looks: natural, warm, cool, teal-orange, cinematic, moody, clean-bright, pastel, punchy, vintage, bw, noir
Grade every clip with the SAME look and strength. Grade before adding text/graphics.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vibelib import ff, probe  # noqa: E402

LOOKS = {
    "natural": "eq=contrast=1.04:saturation=1.06",
    "warm": "colorbalance=rs=0.05:bs=-0.05:rm=0.04:bm=-0.04:rh=0.02:bh=-0.03,eq=saturation=1.08:contrast=1.03",
    "cool": "colorbalance=rs=-0.04:bs=0.05:rm=-0.03:bm=0.04,eq=saturation=0.95:contrast=1.04",
    "teal-orange": "colorbalance=rs=-0.08:gs=0.0:bs=0.09:rh=0.08:gh=0.01:bh=-0.08,eq=contrast=1.08:saturation=1.12",
    "cinematic": "colorbalance=rs=-0.06:bs=0.07:rh=0.06:bh=-0.06,"
                 "curves=all='0/0.03 0.25/0.21 0.5/0.5 0.75/0.79 1/0.96',eq=saturation=0.92",
    "moody": "eq=brightness=-0.03:contrast=1.12:saturation=0.82,colorbalance=rs=-0.03:bs=0.05",
    "clean-bright": "eq=brightness=0.02:contrast=0.98:saturation=1.05,curves=all='0/0.02 0.5/0.53 1/1',"
                    "colorbalance=rh=0.02:bh=-0.01",
    "pastel": "eq=contrast=0.9:saturation=0.82:brightness=0.03,curves=all='0/0.06 1/0.97'",
    "punchy": "eq=contrast=1.12:saturation=1.25,unsharp=5:5:0.4",
    "vintage": "curves=preset=vintage,eq=saturation=0.85",
    "bw": "hue=s=0,eq=contrast=1.12",
    "noir": "hue=s=0,curves=all='0/0 0.3/0.18 0.7/0.82 1/1',eq=contrast=1.2",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", nargs="?")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--look", default=None, choices=sorted(LOOKS))
    ap.add_argument("--lut", default=None, help=".cube LUT file")
    ap.add_argument("--strength", type=float, default=1.0, help="0..1 mix with the original")
    ap.add_argument("--grain", type=float, default=0, help="film grain, 4-10 is subtle")
    ap.add_argument("--vignette", action="store_true")
    ap.add_argument("--letterbox", type=float, default=None, help="cinema bars, e.g. 2.39 or 2.0")
    ap.add_argument("--compare", action="store_true", help="also write a before|after video")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list or not a.video:
        for k, v in LOOKS.items():
            print(f"  {k:13s} {v}")
        return
    if not a.look and not a.lut:
        sys.exit("choose --look or --lut")

    info = probe(a.video)
    W, H = info["width"], info["height"]
    chain = []
    if a.look:
        chain.append(LOOKS[a.look])
    if a.lut:
        lut = Path(a.lut).resolve().as_posix().replace(":", r"\:")
        chain.append(f"lut3d='{lut}'")
    g = ",".join(chain)
    if a.strength < 1:
        graph = f"[0:v]format=gbrp,split[o][x];[x]{g}[g];[o][g]blend=all_mode=normal:all_opacity={a.strength:.3f}"
    else:
        graph = f"[0:v]{g}"
    if a.grain:
        graph += f",noise=alls={a.grain:g}:allf=t"
    if a.vignette:
        graph += ",vignette=PI/5"
    if a.letterbox:
        bar = max(0, int((H - W / a.letterbox) / 2))
        if H >= W:      # true 2.39 bars would hide most of a vertical frame; use thin cinematic bars
            bar = int(H * 0.07)
            print("vertical video: using thin cinematic bars (7% top and bottom)")
        if bar:
            graph += f",drawbox=x=0:y=0:w=iw:h={bar}:color=black:t=fill,drawbox=x=0:y=ih-{bar}:w=iw:h={bar}:color=black:t=fill"
    graph += ",format=yuv420p[v]"
    out = Path(a.out) if a.out else Path(a.video).with_name(Path(a.video).stem + f"_{a.look or 'lut'}.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    maps = ["-map", "[v]"] + (["-map", "0:a?", "-c:a", "copy"] if info["has_audio"] else [])
    ff("-i", a.video, "-filter_complex", graph, *maps, "-c:v", "libx264", "-crf", "17", "-preset", "medium",
       "-movflags", "+faststart", out)
    print(f"graded -> {out}")
    if a.compare:
        cmp_ = out.with_name(out.stem + "_compare.mp4")
        stack = "hstack" if H >= W else "vstack"
        ff("-i", a.video, "-i", out, "-filter_complex",
           f"[0:v]scale={W // 2 * 2}:{H // 2 * 2}[a];[1:v]scale={W // 2 * 2}:{H // 2 * 2}[b];[a][b]{stack},"
           f"scale='min(1920,iw)':-2,format=yuv420p[v]", "-map", "[v]", "-c:v", "libx264", "-crf", "20", cmp_)
        print(f"before|after -> {cmp_}")


if __name__ == "__main__":
    main()
