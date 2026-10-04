"""Frame renderer.  python3 video.py stills 3.0 9.5 ...  |  python3 video.py render [out.mp4]"""
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np

import crayon
import scenes

HERE = os.path.dirname(os.path.abspath(__file__))
_surf = None


def render_frame(t):
    global _surf
    if _surf is None:
        _surf = crayon.new_surface()
    c = _surf.getCanvas()
    c.clear(0xFFFFFFFF)
    c.drawImage(crayon.paper_image(), 0, 0)
    scenes.render(crayon.Pen(c, t), t)
    return crayon.frame_to_rgb(_surf)


def _job(i):
    return render_frame(i / crayon.FPS).tobytes()


def stills(times):
    from PIL import Image
    os.makedirs(os.path.join(HERE, "work", "stills"), exist_ok=True)
    for t in times:
        Image.fromarray(render_frame(t)).save(os.path.join(HERE, "work", "stills", f"t{t:05.2f}.png"))
        print("still", t)


def render(out):
    n = int(round(scenes.DUR * crayon.FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{crayon.W}x{crayon.H}",
           "-r", str(crayon.FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-tune", "grain",
           "-pix_fmt", "yuv420p", out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for i, buf in enumerate(pool.imap(_job, range(n), chunksize=4)):
            ff.stdin.write(buf)
            if i % 48 == 0:
                print(f"frame {i}/{n}", flush=True)
    ff.stdin.close()
    ff.wait()


if __name__ == "__main__":
    if sys.argv[1] == "stills":
        stills([float(a) for a in sys.argv[2:]])
    else:
        render(sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "work", "picture.mp4"))
