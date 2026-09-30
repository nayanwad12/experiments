"""The raw take cut with the same EDL and speed-up as the edit — no effects, captions, grade or music — for
side-by-side comparison. Uses the exact frame mapping of render.py, so it lines up frame-for-frame with out/final.mp4.

    python3 trim_raw.py  ->  out/trimmed_raw.mp4 (1920x1080, 30 fps)
"""

import os
import subprocess

import cv2
import numpy as np
from scipy.io import wavfile

from common import DUR, FFMPEG, FPS, NFRAMES, OUT, RAW, SEGS, SPEED, WORK, H, W, src_of_out

SR = 44100


def audio(path):
    p = subprocess.run([FFMPEG, "-v", "error", "-i", RAW, "-ac", "2", "-ar", str(SR), "-f", "s16le", "-"],
                       capture_output=True, check=True)
    src = np.frombuffer(p.stdout, np.int16).reshape(-1, 2).astype(np.float32)
    out, xf = [], int(0.012 * SR)
    ramp = np.linspace(0, 1, xf)[:, None]
    for a, b, _ in SEGS:
        x = src[int(a * SR):int(b * SR)].copy()
        x[:xf] *= ramp
        x[-xf:] *= ramp[::-1]
        out.append(x)
    tmp = path + ".cut.wav"
    wavfile.write(tmp, SR, np.concatenate(out)[: int(DUR * SR)].astype(np.int16))
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", tmp, "-af", f"atempo={SPEED}", path], check=True)
    os.remove(tmp)


def main():
    os.makedirs(OUT, exist_ok=True)
    wav = os.path.join(OUT, "trimmed_raw.wav")
    audio(wav)
    frames = np.load(os.path.join(WORK, "frames.npy"), mmap_mode="r")
    nf = int(open(os.path.join(WORK, "nframes.txt")).read())
    out = os.path.join(OUT, "trimmed_raw.mp4")
    p = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "libx264",
                          "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                          "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for i in range(NFRAMES):
        s, _ = src_of_out(i / FPS * SPEED)
        f = frames[int(np.clip(round(s * FPS), 0, nf - 1))]
        p.stdin.write(cv2.resize(np.ascontiguousarray(f), (W, H), interpolation=cv2.INTER_LANCZOS4).tobytes())
    p.stdin.close()
    p.wait()
    os.remove(wav)
    print("wrote", out)


if __name__ == "__main__":
    main()
