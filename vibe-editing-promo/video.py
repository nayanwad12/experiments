"""Render the promo frames: scenes at 12 fps stop-motion, camera/transition FX at 30 fps.

    python3 video.py stills 0.5 2.0 ...     # preview PNGs into ./out/stills
    python3 video.py render                 # full 30 s video -> ./out/video_noaudio.mp4
"""

import math
import os
import subprocess
import sys
from multiprocessing import Pool

import imageio_ffmpeg
import skia

import scenes
from paper import INK, PAPER, Ctx, R, lerp, paper, paper_paint, rgb, rough, path_of, eoc
from timeline import BEAT, DUR, FLASHES, FPS, H, PUNCH, SCENES, SHAKES, STEP_FPS, W

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def scene_at(t):
    for i, (s, e, name, tr) in enumerate(SCENES):
        if s <= t < e:
            return i, s, e, name, tr
    s, e, name, tr = SCENES[-1]
    return len(SCENES) - 1, s, e, name, tr


class Renderer:
    def __init__(self):
        self.scene_surf = skia.Surface(W, H)
        self.out_surf = skia.Surface(W, H)
        self.cache_key = None
        self.cache_img = None

    def scene_image(self, t):
        idx, s, e, name, _ = scene_at(t)
        lstep = int((t - s) * STEP_FPS + 1e-6)
        key = (idx, lstep)
        if key != self.cache_key:
            tl = lstep / STEP_FPS
            c = self.scene_surf.getCanvas()
            c.clear(rgb(PAPER))
            ctx = Ctx(c, idx * 1000 + lstep, t)
            n = c.getSaveCount()
            scenes.SCENE_FNS[name](ctx, tl)
            c.restoreToCount(n)  # never let a scene's transform leak into the next frame
            self.cache_img = self.scene_surf.makeImageSnapshot()
            self.cache_key = key
        return self.cache_img

    def camera(self, t):
        sc, dx, dy, rot = 1.045, 0.0, 0.0, 0.0
        for (a, b) in PUNCH:
            if a <= t < b:
                sc += 0.035 * math.exp(-((t - a) % BEAT) / 0.09)
        idx, s, e, name, _ = scene_at(t)
        if name == "recap":
            k = int((t - s) / 0.2)
            sc += [0.0, 0.12, 0.05, 0.16, 0.02, 0.1, 0.07, 0.18][k]
            rot += [-2, 2, -1.5, 1.5, -2.5, 2.5, -1, 1][k]
        if name == "reveal" and t - s > 2.8:   # build-up creep
            sc += 0.06 * (t - s - 2.8) / 1.2
        for (t0, amp, dec) in SHAKES:
            d = t - t0
            if 0 <= d < dec * 4:
                a = amp * math.exp(-d / dec)
                dx += a * math.sin(d * 97 + t0)
                dy += a * math.cos(d * 83 + t0 * 2)
                rot += a * 0.04 * math.sin(d * 71)
        return sc, dx, dy, rot

    def frame(self, t):
        img = self.scene_image(t)
        c = self.out_surf.getCanvas()
        c.clear(rgb(INK))
        sc, dx, dy, rot = self.camera(t)
        c.save()
        c.translate(W / 2 + dx, H / 2 + dy)
        c.rotate(rot)
        c.scale(sc, sc)
        c.translate(-W / 2, -H / 2)
        c.drawImage(img, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear))
        c.restore()
        self.transition(c, t)
        # flashes
        for (t0, a, d) in FLASHES:
            if t0 <= t < t0 + d:
                p = skia.Paint(Color=rgb(PAPER, int(255 * a * (1 - (t - t0) / d))))
                c.drawPaint(p)
        # vignette
        v = skia.Paint()
        v.setShader(skia.GradientShader.MakeRadial(
            (W / 2, H / 2), 1150, [skia.Color(255, 255, 255, 255), skia.Color(255, 255, 255, 255),
                                   skia.Color(150, 145, 160, 255)], [0.0, 0.62, 1.0]))
        v.setBlendMode(skia.BlendMode.kMultiply)
        c.drawPaint(v)
        return self.out_surf.makeImageSnapshot()

    def transition(self, c, t):
        """Torn sheet of the previous shot's colour ripping away to reveal the new one."""
        idx, s, e, name, tr = scene_at(t)
        d = t - s
        if not tr or idx == 0 or d >= 0.2:
            return
        prev = scenes.SCENE_BG[SCENES[idx - 1][2]]
        k = eoc(d / 0.2)
        ctx = Ctx(c, idx, t)
        if tr == "tear_up":
            pts = [(-200, -200), (W + 200, -200), (W + 200, H + 60), (-200, H + 140)]
            dx, dy, rt = 0, -k * 2300, -k * 8
        elif tr == "tear_left":
            pts = [(-200, -200), (W + 60, -200), (W + 140, H + 200), (-200, H + 200)]
            dx, dy, rt = -k * 1700, 0, k * 6
        else:
            pts = [(-300, -300), (W + 200, -300), (W - 200, H + 300), (-300, H + 300)]
            dx, dy, rt = -k * 1500, -k * 1500, -k * 10
        ctx.push(W / 2 + dx, H / 2 + dy, rt)
        pts = [(x - W / 2, y - H / 2) for x, y in pts]
        white = path_of(rough(pts, idx * 7, 14, 14))
        p = paper_paint(PAPER, idx)
        p.setImageFilter(ctx.shadow(5))
        c.drawPath(white, p)
        c.drawPath(path_of(rough([(x - 8, y - 8) for x, y in pts], idx * 7 + 1, 12, 14)), paper_paint(prev, idx))
        ctx.pop()


def render_chunk(args):
    f0, f1, path = args
    r = Renderer()
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r",
           str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
           "-profile:v", "high", path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        img = r.frame(f / FPS)
        proc.stdin.write(img.toarray(colorType=skia.kRGBA_8888_ColorType).tobytes())
    proc.stdin.close()
    proc.wait()
    return path


def render():
    os.makedirs(OUT, exist_ok=True)
    total = int(round(DUR * FPS))
    n = os.cpu_count() or 4
    # contiguous chunks so each worker reuses its 12 fps cache
    bounds = [round(total * i / n) for i in range(n + 1)]
    jobs = [(bounds[i], bounds[i + 1], os.path.join(OUT, f"chunk{i}.mp4")) for i in range(n)]
    with Pool(n) as pool:
        parts = pool.map(render_chunk, jobs)
    lst = os.path.join(OUT, "chunks.txt")
    with open(lst, "w") as fh:
        for p in parts:
            fh.write(f"file '{p}'\n")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    os.path.join(OUT, "video_noaudio.mp4")], check=True)
    for p in parts:
        os.remove(p)
    os.remove(lst)


def stills(times):
    d = os.path.join(OUT, "stills")
    os.makedirs(d, exist_ok=True)
    r = Renderer()
    for t in times:
        img = r.frame(t)
        p = os.path.join(d, f"t{t:05.2f}.png")
        img.save(p, skia.kPNG)
        print(p)


if __name__ == "__main__":
    if sys.argv[1] == "stills":
        stills([float(x) for x in sys.argv[2:]])
    else:
        render()
