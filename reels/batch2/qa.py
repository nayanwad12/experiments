"""QA strip of a finished Reel: python3 qa.py <mp4> <out.png> [n]"""
import subprocess, sys, numpy as np
from PIL import Image
f, out = sys.argv[1], sys.argv[2]; n = int(sys.argv[3]) if len(sys.argv) > 3 else 12
dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]))
tiles = []
for k in range(n):
    t = dur * (k + 0.5) / n
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", f, "-frames:v", "1", "-vf", "scale=270:480",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    tiles.append(np.frombuffer(raw, np.uint8).reshape(480, 270, 3))
rows = [np.concatenate(tiles[i:i + 6], 1) for i in range(0, n, 6)]
Image.fromarray(np.concatenate(rows, 0)).save(out)
r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", f, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
import re
print(f"{dur:.1f}s", re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1], "LUFS, peak", re.findall(r"Peak:\s+(-?[\d.]+)", r)[-1])
