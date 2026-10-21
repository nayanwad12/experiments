"""work/edl.json -> work/base.mp4 (1080x1920, 30 fps, the cut at 1.2x) + work/voice.wav (48 kHz, same cut).

One seeked encode per cut (4 at a time), then a stream-copy concat: a single filtergraph with a branch per cut
buffers the whole take in memory.
"""
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
W = HERE / "work"
E = json.loads((W / "edl.json").read_text())
SP, FPS, SR = E["speed"], E["fps"], 48000
PARTS = W / "cut_parts"
PARTS.mkdir(exist_ok=True)


def part(i):
    s, e, o, n = E["cuts"][i]
    d = n / FPS
    pre = min(1.0, s)
    vf = (f"trim=start={pre}:end={pre + e - s + 0.2},setpts=(PTS-STARTPTS)/{SP},fps={FPS},"
          f"tpad=stop_mode=clone:stop=4,trim=end_frame={n},setpts=PTS-STARTPTS")
    af = (f"atrim=start={pre}:end={pre + e - s},asetpts=PTS-STARTPTS,atempo={SP},"
          f"afade=t=in:d=0.012,afade=t=out:st={max(0, d - 0.018):.4f}:d=0.018,"
          f"apad,atrim=end_sample={int(round(d * SR))}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s - pre:.4f}", "-t", f"{e - s + pre + 0.5:.4f}",
                    "-i", str(W / "proxy1080.mp4"), "-map", "0:v:0", "-vf", vf, "-c:v", "libx264", "-preset", "fast",
                    "-crf", "14", "-pix_fmt", "yuv420p", "-r", str(FPS), "-threads", "2",
                    str(PARTS / f"v{i:03d}.mp4")], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s - pre:.4f}", "-t", f"{e - s + pre + 0.5:.4f}",
                    "-i", str(W / "audio48k.wav"), "-af", af, "-c:a", "pcm_s16le", "-ar", str(SR),
                    str(PARTS / f"a{i:03d}.wav")], check=True)
    return i


with ThreadPoolExecutor(4) as ex:
    for i in ex.map(part, range(len(E["cuts"]))):
        print(f"\r  cut {i + 1}/{len(E['cuts'])}", end="", flush=True)
print()
for kind, ext, out in (("v", "mp4", "base.mp4"), ("a", "wav", "voice.wav")):
    lst = W / f"cut_{kind}.txt"
    lst.write_text("".join(f"file '{PARTS / f'{kind}{i:03d}.{ext}'}'\n" for i in range(len(E["cuts"]))))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                    str(W / out)], check=True)
print("frames expected", sum(c[3] for c in E["cuts"]), "duration", E["total"])
