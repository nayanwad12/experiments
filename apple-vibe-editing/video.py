"""Render the film.
    python3 video.py stills 0.6 4.5 9.8 ...      -> out/stills/*.png
    python3 video.py sheet                       -> out/sheet.png (contact sheet of key moments)
    python3 video.py render [--draft]            -> out/picture.mp4
"""
import multiprocessing as mp
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import skia

sys.path.insert(0, "vibe")
from vibelib import FrameWriter, concat_videos  # noqa: E402
import scenes  # noqa: E402
from timeline import W, H, FPS, DURATION  # noqa: E402


def frame(t, scale=1.0):
    surf = skia.Surface(int(W * scale), int(H * scale))
    with surf as c:
        c.scale(scale, scale)
        scenes.draw(c, t)
    return surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3]


def chunk(args):
    frames, path, fps, scale = args
    w, h = int(W * scale) // 2 * 2, int(H * scale) // 2 * 2
    with FrameWriter(path, w, h, fps, crf=14, preset="medium") as fw:
        for f in frames:
            fw.write(frame(f / fps, scale)[:h, :w])
    return path


def render(draft=False, out="out/picture.mp4", t0=0.0, t1=DURATION):
    fps = 30 if draft else FPS
    scale = 0.5 if draft else 1.0
    frames = list(range(int(round(t0 * fps)), int(round(t1 * fps))))
    n = os.cpu_count() or 2
    tmp = Path(tempfile.mkdtemp(dir="work"))
    parts = np.array_split(np.array(frames), n * 3)
    jobs = [([int(x) for x in p], str(tmp / f"p{i:03d}.mp4"), fps, scale) for i, p in enumerate(parts) if len(p)]
    with mp.get_context("fork").Pool(n) as pool:
        done = 0
        for _ in pool.imap(chunk, jobs):
            done += 1
            print(f"\r  {done}/{len(jobs)} chunks", end="", flush=True)
    print()
    concat_videos(sorted(tmp.glob("p*.mp4")), out)
    for p in tmp.iterdir():
        p.unlink()
    tmp.rmdir()
    print("->", out)


if __name__ == "__main__":
    from PIL import Image
    cmd = sys.argv[1]
    Path("out/stills").mkdir(parents=True, exist_ok=True)
    if cmd == "stills":
        for a in sys.argv[2:]:
            Image.fromarray(frame(float(a), 0.5)).save(f"out/stills/s_{float(a):06.2f}.png")
    elif cmd == "sheet":
        ts = [float(x) for x in sys.argv[2:]] or [0.3, 0.8, 1.5, 2.6, 3.0, 4.9, 6.9, 7.75, 9.4, 10.6, 11.6, 12.0,
                                                  12.5, 13.8, 14.7, 15.6, 16.2, 16.9, 17.9, 18.6, 19.1, 19.6, 20.1,
                                                  20.5, 21.0, 22.3, 23.7, 25.4, 26.5, 27.5, 28.0, 29.0, 30.5,
                                                  32.2, 33.4, 34.6, 36.4, 38.0, 39.3, 39.9]
        tiles = [frame(t, 0.25) for t in ts]
        cols = 5
        h, w = tiles[0].shape[:2]
        rows = (len(tiles) + cols - 1) // cols
        sheet = np.full((rows * (h + 24), cols * (w + 8), 3), 120, np.uint8)
        from PIL import ImageDraw
        img = Image.fromarray(sheet)
        d = ImageDraw.Draw(img)
        for i, (t, tile) in enumerate(zip(ts, tiles)):
            r, cc = divmod(i, cols)
            img.paste(Image.fromarray(tile), (cc * (w + 8), r * (h + 24) + 20))
            d.text((cc * (w + 8) + 4, r * (h + 24) + 4), f"{t:.2f}s", fill=(255, 255, 255))
        img.save("out/sheet.png")
        print("-> out/sheet.png")
    elif cmd == "render":
        render(draft="--draft" in sys.argv, out="out/draft.mp4" if "--draft" in sys.argv else "out/picture.mp4")
