"""Frames. Scene boundaries are hidden in whip-pans with directional motion blur (the fake-oner).

    python3 render.py stills 1.0 14.5 ...   # preview PNGs -> out/stills
    python3 render.py video                 # out/video_noaudio.mp4
"""

import json
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import imageio_ffmpeg
import skia

from design import FPS, H, W, clamp, rgb, smooth
from script import N, SCENE

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
WHIP = 0.28                       # seconds of blur on each side of a boundary
DIRS = [(-1, 0), (0, -1), (-1, 0), (0, -1), (-1, 0)]   # travel direction at boundary k -> k+1
DUR = N * SCENE


def load_cues():
    with open(os.path.join(OUT, "cues.json")) as fh:
        return [c["phrases"] for c in json.load(fh)]


class Renderer:
    def __init__(self):
        import scenes
        self.scenes = scenes
        self.cues = load_cues()
        self.s1 = skia.Surface(W, H)
        self.s2 = skia.Surface(W, H)
        self.s3 = skia.Surface(W, H)

    def scene(self, surf, k, tl):
        c = surf.getCanvas()
        c.save()
        self.scenes.SCENES[k](c, clamp(tl, 0, SCENE), self.cues[k])
        c.restore()
        return surf.makeImageSnapshot()

    def frame(self, t):
        b = int(round(t / SCENE))   # nearest boundary
        if 0 < b < N and abs(t - b * SCENE) < WHIP:
            # whip-pan: outgoing and incoming scenes travel together under one motion blur
            u = (t - (b * SCENE - WHIP)) / (2 * WHIP)
            pos = smooth(u)
            blur = 85 * math.sin(math.pi * u) ** 1.5
            d = DIRS[b - 1]
            out_img = self.scene(self.s1, b - 1, t - (b - 1) * SCENE)
            in_img = self.scene(self.s2, b, t - b * SCENE)
            o = self.s3.getCanvas()
            o.clear(rgb(self.scenes.BG[b]))
            p = skia.Paint()
            p.setImageFilter(skia.ImageFilters.Blur(blur if d[0] else 0.01, blur if d[1] else 0.01,
                                                    skia.TileMode.kClamp))
            s = skia.SamplingOptions(skia.FilterMode.kLinear)
            o.drawImage(out_img, d[0] * pos * W, d[1] * pos * H, s, p)
            o.drawImage(in_img, -d[0] * (1 - pos) * W, -d[1] * (1 - pos) * H, s, p)
            return self.s3.makeImageSnapshot()
        k = min(int(t / SCENE), N - 1)
        return self.scene(self.s1, k, t - k * SCENE)


def render_chunk(args):
    f0, f1, path = args
    r = Renderer()
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r",
           str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        proc.stdin.write(r.frame(f / FPS).toarray(colorType=skia.kRGBA_8888_ColorType).tobytes())
    proc.stdin.close()
    proc.wait()
    return path


def video():
    total = int(round(DUR * FPS))
    n = os.cpu_count() or 4
    bounds = [round(total * i / n) for i in range(n + 1)]
    jobs = [(bounds[i], bounds[i + 1], os.path.join(OUT, f"chunk{i}.mp4")) for i in range(n)]
    with Pool(n) as pool:
        parts = pool.map(render_chunk, jobs)
    lst = os.path.join(OUT, "chunks.txt")
    with open(lst, "w") as fh:
        fh.writelines(f"file '{p}'\n" for p in parts)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    os.path.join(OUT, "video_noaudio.mp4")], check=True)
    for p in parts + [lst]:
        os.remove(p)


def stills(times):
    d = os.path.join(OUT, "stills")
    os.makedirs(d, exist_ok=True)
    r = Renderer()
    for t in times:
        p = os.path.join(d, f"t{t:05.2f}.png")
        r.frame(t).save(p, skia.kPNG)
        print(p)


if __name__ == "__main__":
    if sys.argv[1] == "stills":
        stills([float(x) for x in sys.argv[2:]])
    else:
        video()
