"""Frames + energy FX. Scene boundaries are fast whip-pans under directional motion blur; on top of the
scenes run beat-synced camera punches, impact shakes, flash frames, an RGB-split glitch and paper
confetti bursts on the drops.

    python3 render.py stills 1.0 14.5 ...   # preview PNGs -> out/stills
    python3 render.py video                 # out/video_noaudio.mp4
"""

import math
import os
import subprocess
import sys
from multiprocessing import Pool

import imageio_ffmpeg
import skia

import design
import timeline as TL
from design import (CORAL, CREAM, FPS, H, NAVY, TEAL, W, WHITE, YELLOW, Cam, R, clamp, paper_paint, path_of,
                    rgb, rough_poly, rect_pts, smooth)
from script import BEAT, N

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
WHIP = 0.17                       # seconds of blur on each side of a boundary
DIRS = [(-1, 0), (0, -1), (-1, 0), (0, -1), (-1, 0)]   # travel direction at boundary k -> k+1
SAMP = skia.SamplingOptions(skia.FilterMode.kLinear)
HIT_W = {"impact": 1.0, "stamp": 0.65, "snip": 0.45, "tear": 0.4}


def _hits():
    import scenes
    hits = [(t, 1.0) for t in TL.DROPS] + [(s, 0.55) for s in TL.STARTS[1:]]
    for k in range(N):
        for (t, name, g) in scenes.SFX[k](TL.PHRASES[k]):
            if name in HIT_W:
                hits.append((TL.STARTS[k] + t, HIT_W[name] * min(g, 1.0)))
    return sorted(hits)


HITS = _hits()
BURSTS = [TL.DROP1, TL.DROP2, TL.DROP3, TL.YOU]


def decay(t, tau):
    """Sum of exponential decays from every hit before t (strength-weighted)."""
    v = 0.0
    for (h, s) in HITS:
        d = t - h
        if 0 <= d < tau * 6:
            v += s * math.exp(-d / tau)
    return v


def beat_punch(t):
    sec = TL.section(t)
    b, dt = TL.beat_phase(t)
    if sec == "break":
        return 0.0
    amp = {"intro": 0.008, "drop": 0.02, "build": 0.012 + 0.02 * clamp((t - TL.BUILD) / (TL.DROP2 - TL.BUILD)),
           "drop2": 0.024, "drop3": 0.024}[sec]
    if b % 4 == 0:
        amp *= 1.5
    return amp * math.exp(-dt / 0.085)


class Renderer:
    def __init__(self):
        import scenes
        self.scenes = scenes
        self.surf = [skia.Surface(W, H) for _ in range(4)]

    def scene(self, surf, k, tl):
        c = surf.getCanvas()
        c.save()
        self.scenes.SCENES[k](c, clamp(tl, 0, TL.LENS[k]), TL.PHRASES[k], TL.LENS[k])
        c.restore()
        return surf.makeImageSnapshot()

    def base(self, t):
        """Scene picture, with whip-pans across boundaries. Returns (image, whip intensity, bg colour)."""
        for b in range(1, N):
            B = TL.STARTS[b]
            if abs(t - B) < WHIP:
                u = (t - (B - WHIP)) / (2 * WHIP)
                pos = smooth(u)
                inten = math.sin(math.pi * u) ** 1.5
                blur = 95 * inten
                d = DIRS[b - 1]
                out_img = self.scene(self.surf[0], b - 1, t - TL.STARTS[b - 1])
                in_img = self.scene(self.surf[1], b, t - B)
                o = self.surf[2].getCanvas()
                o.clear(rgb(self.scenes.BG[b]))
                p = skia.Paint()
                p.setImageFilter(skia.ImageFilters.Blur(blur if d[0] else 0.01, blur if d[1] else 0.01,
                                                        skia.TileMode.kClamp))
                o.drawImage(out_img, d[0] * pos * W, d[1] * pos * H, SAMP, p)
                o.drawImage(in_img, -d[0] * (1 - pos) * W, -d[1] * (1 - pos) * H, SAMP, p)
                return self.surf[2].makeImageSnapshot(), inten, self.scenes.BG[b]
        k = TL.scene_at(t)
        return self.scene(self.surf[0], k, t - TL.STARTS[k]), 0.0, self.scenes.BG[k]

    def frame(self, t):
        design.CLOCK[0] = t
        img, whip, bgc = self.base(t)
        o = self.surf[3].getCanvas()
        o.clear(rgb(bgc))
        # camera: beat punch + impact zoom + shake
        hit = decay(t, 0.11)
        sc = 1.045 + beat_punch(t) + 0.045 * min(hit, 1.5)   # 4.5% overscan so shakes never show an edge
        r = R("shake", int(t * FPS))
        amp = 26 * min(decay(t, 0.09), 1.6)
        dx, dy, rot = r.uniform(-1, 1) * amp, r.uniform(-1, 1) * amp, r.uniform(-1, 1) * amp * 0.05
        split = 16 * whip + 12 * min(decay(t, 0.07), 1.2)
        with Cam(o)(W / 2 + dx, H / 2 + dy, rot, sc):
            o.translate(-W / 2, -H / 2)
            if split > 0.6:
                self.rgb_split(o, img, split)
            else:
                o.drawImage(img, 0, 0, SAMP)
        self.confetti(o, t)
        # flash frames
        fl = 0.0
        for (h, s) in HITS:
            if 0 <= t - h < 0.12 and s >= 0.65:
                fl = max(fl, 0.42 * s * (1 - (t - h) / 0.12))
        if fl > 0:
            o.drawPaint(skia.Paint(Color=rgb(0xFFFDF6, int(255 * fl))))
        # soft vignette
        v = skia.Paint()
        v.setShader(skia.GradientShader.MakeRadial((W / 2, H / 2), 1200, [skia.Color(255, 255, 255, 255),
                                                                         skia.Color(255, 255, 255, 255),
                                                                         skia.Color(170, 165, 175, 255)],
                                                   [0.0, 0.6, 1.0]))
        v.setBlendMode(skia.BlendMode.kMultiply)
        o.drawPaint(v)
        return self.surf[3].makeImageSnapshot()

    @staticmethod
    def rgb_split(o, img, m):
        o.drawRect(skia.Rect.MakeXYWH(-50, -50, W + 100, H + 100), skia.Paint(Color=skia.Color(0, 0, 0, 255)))
        for (mx, ox) in (((1, 0, 0), -m), ((0, 1, 0), 0), ((0, 0, 1), m)):
            p = skia.Paint()
            p.setColorFilter(skia.ColorFilters.Matrix([mx[0], 0, 0, 0, 0, 0, mx[1], 0, 0, 0, 0, 0, mx[2], 0, 0,
                                                       0, 0, 0, 1, 0]))
            p.setBlendMode(skia.BlendMode.kPlus)
            o.drawImage(img, ox, ox * 0.3, SAMP, p)

    @staticmethod
    def confetti(o, t):
        cols = [YELLOW, CORAL, TEAL, WHITE, NAVY, CREAM]
        for bi, t0 in enumerate(BURSTS):
            d = t - t0
            if not (0 <= d < 1.6):
                continue
            for i in range(54):
                r = R("conf", bi, i)
                a = r.uniform(-math.pi, 0) if bi != 3 else r.uniform(-math.pi * 0.95, -math.pi * 0.05)
                v = r.uniform(900, 2300)
                x0, y0 = W / 2 + r.uniform(-120, 120), H * (0.62 if bi != 3 else 0.55)
                x = x0 + math.cos(a) * v * d * math.exp(-d * 1.2)
                y = y0 + math.sin(a) * v * d * math.exp(-d * 1.2) + 0.5 * 2600 * d * d
                if y > H + 80:
                    continue
                w, h = r.uniform(26, 54), r.uniform(16, 30)
                spin = r.uniform(-900, 900) * d
                flip = math.cos(r.uniform(4, 12) * d + r.uniform(0, 6))
                with Cam(o)(x, y, spin, (1.0, max(abs(flip), 0.08))):
                    p = paper_paint(cols[i % len(cols)], int(255 * clamp(1.6 - d)))
                    o.drawPath(path_of(rough_poly(rect_pts(0, 0, w, h), i, 1.5, 12)), p)


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
    total = int(round(TL.DUR * FPS))
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
