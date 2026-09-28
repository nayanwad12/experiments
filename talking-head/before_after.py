"""Before/after cut: 6 s of the untouched raw clip, a paper tear, then the edited reel."""

import os
import subprocess

import numpy as np
import skia

import edit as E
from paper import BLUSH, INK, LIME, PAPER, Ctx, draw_text, eoc, path_of, paper_paint, pop, rgb, rough

BEFORE = 6.0   # raw seconds shown ("...thirty seconds of content")
TEAR = 0.35


def render_before(path):
    n = int(BEFORE * E.FPS)
    dec = subprocess.Popen([E.FFMPEG, "-loglevel", "error", "-i", E.RAW, "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen([E.FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s",
                            f"{E.W}x{E.H}", "-r", str(E.FPS), "-i", "-", "-i", E.RAW, "-t", str(BEFORE), "-map", "0:v",
                            "-map", "1:a", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac",
                            "-ar", "44100", "-ac", "2", "-b:a", "192k", path], stdin=subprocess.PIPE)
    surf = skia.Surface(E.W, E.H)
    dull = skia.Paint()
    s = 0.25  # washed-out "raw" look
    lr, lg, lb = 0.2126, 0.7152, 0.0722
    m = []
    for i in range(3):
        row = [(1 - s) * lr, (1 - s) * lg, (1 - s) * lb]
        row[i] += s
        m += [v * 0.92 for v in row] + [0, 0.03]
    dull.setColorFilter(skia.ColorFilters.Matrix(m + [0, 0, 0, 1, 0]))
    fsz = E.SW * E.SH * 4
    for f in range(n):
        t = f / E.FPS
        buf = dec.stdout.read(fsz)
        img = skia.Image.fromarray(np.frombuffer(buf, np.uint8).reshape(E.SH, E.SW, 4))
        c = surf.getCanvas()
        c.save()
        c.scale(E.W / E.SW, E.H / E.SH)
        c.drawImage(img, 0, 0, skia.SamplingOptions(skia.CubicResampler.Mitchell()), dull)
        c.restore()
        ctx = Ctx(c, int(t * 12), t)
        st = int(t * 12) / 12
        draw_text(ctx, "BEFORE", 540, 330, 190, fill=PAPER, back=INK, under=BLUSH, rot=-5, sc=pop(st, 0.0, 0.25),
                  seed=11, pad=0.1)
        draw_text(ctx, "RAW CLIP  ·  NO EDITS", 540, 520, 62, fill=INK, back=PAPER, rot=2, sc=pop(st, 0.4, 0.25),
                  seed=12, pad=0.2)
        # REC dot + timecode, like a camera screen
        if (f // 15) % 2 == 0:
            c.drawCircle(120, 1560, 22, skia.Paint(AntiAlias=True, Color=rgb(0xE8453C)))
        draw_text(ctx, f"REC  00:{int(t):02d}", 330, 1560, 58, fill=PAPER, back=None, seed=13, depth=1, wob=0)
        if t > BEFORE - TEAR:   # lime sheet tears across, into the edited reel
            k = eoc((t - (BEFORE - TEAR)) / (TEAR - 0.04))
            y = E.H + 200 - k * (E.H + 500)
            pts = [(-200, y), (E.W + 200, y - 180), (E.W + 200, E.H + 400), (-200, E.H + 400)]
            ctx.push(0, 0)
            p = paper_paint(PAPER)
            p.setImageFilter(ctx.shadow(5))
            c.drawPath(path_of(rough(pts, 3, 16, 14)), p)
            c.drawPath(path_of(rough([(x, yy + 14) for x, yy in pts], 4, 14, 14)), paper_paint(LIME))
            if k > 0.55:
                draw_text(ctx, "AFTER", 540, 960, 230, fill=INK, back=PAPER, under=LIME, rot=4,
                          sc=pop(st, BEFORE - TEAR * 0.45, 0.15), seed=14)
            ctx.pop()
        enc.stdin.write(surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType).tobytes())
    enc.stdin.close()
    enc.wait()
    dec.kill()


if __name__ == "__main__":
    before = os.path.join(E.OUT, "before.mp4")
    render_before(before)
    out = os.path.join(E.OUT, "before_after.mp4")
    subprocess.run([E.FFMPEG, "-y", "-loglevel", "error", "-i", before, "-i", os.path.join(E.OUT, "reel.mp4"),
                    "-filter_complex", "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-b:a", "160k", "-movflags", "+faststart", out], check=True)
    print("wrote", out)
