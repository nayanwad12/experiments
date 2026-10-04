"""Render the picture: 480 unique exposures at 12 fps ("on twos"), delivered at 24 fps.

    python3 video.py                     -> out/video_noaudio.mp4
    python3 video.py stills 3.4 9.1 ...  -> out/stills/*.png
"""

import multiprocessing as mp
import os
import shutil
import subprocess
import sys
import time

import numpy as np
import skia

import scenes
from lib import FPS, H, W, texture
from timeline import DUR

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
NFRAMES = int(DUR * FPS)

_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / (W / 2)) ** 2 + ((_yy - H / 2) / (H / 2)) ** 2)
VIGNETTE = (1 - 0.32 * np.clip(_r - 0.45, 0, None) ** 1.6)[..., None].astype(np.float32)
_grng = np.random.default_rng(99)
GRAIN = [_grng.standard_normal((H // 2, W // 2)).astype(np.float32) for _ in range(6)]


def post(rgba, g, f):
    a = rgba[..., :3].astype(np.float32) * (1 / 255)
    warm, cool, dim, flash = (g.get(k, 0.0) for k in ("warm", "cool", "dim", "flash"))
    gain = np.array([1 + 0.09 * warm - 0.10 * cool, 1 + 0.025 * warm - 0.03 * cool, 1 - 0.11 * warm + 0.12 * cool],
                    np.float32)
    a *= gain * (1 - dim)
    if flash:
        a += flash * (1 - a)
    rng = np.random.default_rng(f * 31 + 7)
    flicker = 1 + 0.014 * rng.standard_normal()           # stop-motion exposure flicker
    a *= VIGNETTE * flicker
    gr = np.repeat(np.repeat(GRAIN[f % len(GRAIN)], 2, 0), 2, 1)
    gr = np.roll(gr, (int(rng.integers(0, H)), int(rng.integers(0, W))), (0, 1))
    a += gr[..., None] * 0.016
    if "iris" in g:
        cx, cy, r = g["iris"]
        d = np.sqrt((_xx - cx) ** 2 + (_yy - cy) ** 2)
        a *= np.clip((r - d) / 2.0, 0, 1)[..., None]
    return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)


def render_frame(f):
    t = f / FPS
    surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))
    c = surf.getCanvas()
    g = scenes.draw(c, t, f)
    rgba = surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
    return post(rgba, g, f)


def _init():
    texture()


def _job(f):
    return f, render_frame(f).tobytes()


def render(path=None, workers=None):
    os.makedirs(OUT, exist_ok=True)
    path = path or os.path.join(OUT, "video_noaudio.mp4")
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-framerate", str(FPS), "-i", "-", "-r", "24", "-c:v", "libx264", "-preset", "slow", "-crf", "20",
           "-pix_fmt", "yuv420p", "-tune", "animation", path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    with mp.Pool(workers or os.cpu_count(), initializer=_init) as pool:
        for k, (f, buf) in enumerate(pool.imap(_job, range(NFRAMES), chunksize=2)):
            proc.stdin.write(buf)
            if k % 24 == 0:
                el = time.time() - t0
                print(f"frame {k}/{NFRAMES}  {el:.0f}s elapsed, ~{el / (k + 1) * (NFRAMES - k - 1):.0f}s left", flush=True)
    proc.stdin.close()
    proc.wait()
    print("wrote", path)


def stills(times):
    d = os.path.join(OUT, "stills")
    os.makedirs(d, exist_ok=True)
    texture()
    for ts in times:
        f = int(round(float(ts) * FPS))
        img = render_frame(f)
        p = os.path.join(d, f"still_{float(ts):05.2f}.png")
        skia.Image.fromarray(np.dstack([img, np.full(img.shape[:2], 255, np.uint8)]),
                             colorType=skia.kRGBA_8888_ColorType).save(p)
        print("wrote", p)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stills":
        stills(sys.argv[2:])
    else:
        render()
