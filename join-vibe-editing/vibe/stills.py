"""stills: pull frames from any video and lay them out on a labelled contact sheet.

    python3 scripts/stills.py out/draft.mp4 --at 0.5,3.2,7.9      # exact moments
    python3 scripts/stills.py out/draft.mp4 --count 12             # evenly spaced
    python3 scripts/stills.py out/draft.mp4 --every 2              # one every 2 s

Writes out/stills/<name>_<t>.png and out/stills/<name>_sheet.png.
Claude: open the sheet with the Read tool and LOOK at it before calling a render finished.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vibelib import ff, fmt_time, probe  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--at", default=None, help="comma list of seconds")
    ap.add_argument("--count", type=int, default=None)
    ap.add_argument("--every", type=float, default=None)
    ap.add_argument("-o", "--out-dir", default="out/stills")
    ap.add_argument("--cols", type=int, default=None)
    ap.add_argument("--thumb", type=int, default=480, help="thumbnail width on the sheet")
    a = ap.parse_args()

    from PIL import Image, ImageDraw, ImageFont

    info = probe(a.video)
    dur = info["duration"]
    if a.at:
        times = [float(t) for t in a.at.split(",") if t.strip()]
    elif a.every:
        n = int(dur // a.every) + 1
        times = [min(dur - 0.05, i * a.every) for i in range(n)]
    else:
        n = a.count or 9
        times = [dur * (i + 0.5) / n for i in range(n)]
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = Path(a.video).stem
    paths = []
    for t in times:
        t = max(0.0, min(t, dur - 0.04))
        p = out / f"{stem}_{t:07.2f}.png"
        ff("-ss", f"{t:.3f}", "-i", a.video, "-frames:v", "1", p)
        paths.append((t, p))
        print("  still", p)

    ims = [(t, Image.open(p).convert("RGB")) for t, p in paths if p.exists()]
    if not ims:
        return
    tw = a.thumb
    th = int(ims[0][1].height * tw / ims[0][1].width)
    if a.cols:
        cols = a.cols
    elif len(ims) > 4:
        cols = 4 if th < tw * 0.7 else 5      # landscape thumbs: 4 across, portrait: 5
    else:
        cols = len(ims)
    cols = min(cols, len(ims))
    rows = -(-len(ims) // cols)
    pad, lab = 12, 34
    sheet = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + lab + pad) + pad), (11, 11, 13))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    for i, (t, im) in enumerate(ims):
        x = pad + (i % cols) * (tw + pad)
        y = pad + (i // cols) * (th + lab + pad)
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y + lab))
        d.rectangle([x - 1, y + lab - 1, x + tw, y + lab + th], outline=(90, 90, 96))
        d.text((x + 2, y + 6), f"{fmt_time(t)}  ({t:.2f}s)", fill=(212, 255, 63), font=font)
    sp = out / f"{stem}_sheet.png"
    sheet.save(sp)
    print(f"contact sheet -> {sp}")


if __name__ == "__main__":
    main()
