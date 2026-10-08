"""Frames + person matte for the raw take.

    work/frames/f_00000.jpg   1080x1920 frames at 30 fps (from the 60 fps phone file)
    work/alpha.npy            uint8 (N, 960, 540) person matte, RobustVideoMatting (mobilenetv3, onnx, CPU)
"""
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
import skia

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw" / "take.mp4"
FR = HERE / "work" / "frames"
FPS = 30


def extract():
    FR.mkdir(parents=True, exist_ok=True)
    if any(FR.iterdir()):
        return
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(RAW), "-vf",
                    f"fps={FPS}", "-q:v", "2",
                    str(FR / "f_%05d.jpg")], check=True)


def matte():
    files = sorted(FR.glob("f_*.jpg"))
    n = len(files)
    out = np.lib.format.open_memmap(HERE / "work" / "alpha.npy", mode="w+", dtype=np.uint8, shape=(n, 960, 540))
    so = ort.SessionOptions()
    so.intra_op_num_threads = 4
    sess = ort.InferenceSession(str("/home/user/models/rvm_mobilenetv3_fp32.onnx"), so)
    rec = [np.zeros((1, 1, 1, 1), np.float32)] * 4
    dr = np.array([0.4], np.float32)
    t0 = time.time()
    for i, f in enumerate(files):
        img = skia.Image.open(str(f)).resize(540, 960, skia.SamplingOptions(skia.FilterMode.kLinear))
        src = img.toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3].astype(np.float32) / 255
        src = src.transpose(2, 0, 1)[None]
        fgr, pha, *rec = sess.run(None, {"src": src, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2], "r4i": rec[3],
                                         "downsample_ratio": dr})
        out[i] = np.clip(pha[0, 0] * 255 + 0.5, 0, 255).astype(np.uint8)
        if i % 100 == 0:
            print(f"  matte {i}/{n}  {time.time() - t0:.0f}s", flush=True)
    out.flush()
    print("matte done", n, f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    extract()
    print("frames", len(list(FR.glob('f_*.jpg'))))
    matte()
