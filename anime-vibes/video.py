"""Frame renderer.  python3 video.py stills 3.0 9.5 ...  |  python3 video.py render [out.mp4]"""
import os
import subprocess
import sys
from multiprocessing import Pool

import anime
import scenes

HERE = os.path.dirname(os.path.abspath(__file__))
_surf = None


def render_frame(t):
    global _surf
    if _surf is None:
        _surf = anime.new_surface()
    c = _surf.getCanvas()
    c.clear(0xFF000000)
    c.save()
    scenes.render(c, t)
    c.restore()
    return anime.frame_to_rgb(_surf)


def _job(i):
    return render_frame(i / anime.FPS).tobytes()


def stills(times):
    from PIL import Image
    os.makedirs(os.path.join(HERE, "work", "stills"), exist_ok=True)
    for t in times:
        Image.fromarray(render_frame(t)).save(os.path.join(HERE, "work", "stills", f"t{t:05.2f}.png"))
        print("still", t)


def render(out, t0=0.0, t1=None):
    t1 = scenes.DUR if t1 is None else t1
    frames = range(int(round(t0 * anime.FPS)), int(round(t1 * anime.FPS)))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{anime.W}x{anime.H}",
           "-r", str(anime.FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
           "-pix_fmt", "yuv420p", out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for i, buf in enumerate(pool.imap(_job, frames, chunksize=4)):
            ff.stdin.write(buf)
            if i % 48 == 0:
                print(f"frame {i}/{len(frames)}", flush=True)
    ff.stdin.close()
    ff.wait()


if __name__ == "__main__":
    if sys.argv[1] == "stills":
        stills([float(a) for a in sys.argv[2:]])
    else:
        out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "work", "picture.mp4")
        a = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
        b = float(sys.argv[4]) if len(sys.argv) > 4 else None
        render(out, a, b)
