"""Frames + person matte for the raw take.

    work/frames/f_00000.jpg   1080x1920 frames at 30 fps (lanczos upscale + light sharpen from the 720p phone file)
    work/alpha.npy            uint8 (N, 960, 540) person matte, RobustVideoMatting (resnet50, onnx, CPU)
"""
import subprocess
import time
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw" / "take.mp4"
FR = HERE / "work" / "frames"
MODEL = "/home/user/models/rvm_resnet50_fp32.onnx"
FPS = 30


def extract():
    FR.mkdir(parents=True, exist_ok=True)
    if any(FR.iterdir()):
        return
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(RAW), "-vf",
                    f"fps={FPS},scale=1080:1920:flags=lanczos,unsharp=5:5:0.5", "-q:v", "2",
                    "-start_number", "0", str(FR / "f_%05d.jpg")], check=True)


def matte():
    files = sorted(FR.glob("f_*.jpg"))
    n = len(files)
    out = np.lib.format.open_memmap(HERE / "work" / "alpha.npy", mode="w+", dtype=np.uint8, shape=(n, 960, 540))
    so = ort.SessionOptions()
    so.intra_op_num_threads = 4
    sess = ort.InferenceSession(MODEL, so, providers=["CPUExecutionProvider"])
    rec = [np.zeros((1, 1, 1, 1), np.float32)] * 4
    dr = np.array([0.4], np.float32)
    t0 = time.time()
    for i, f in enumerate(files):
        img = cv2.cvtColor(cv2.imread(str(f)), cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (540, 960), interpolation=cv2.INTER_AREA)
        src = (img.astype(np.float32) / 255).transpose(2, 0, 1)[None]
        fgr, pha, *rec = sess.run(None, {"src": src, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2], "r4i": rec[3],
                                         "downsample_ratio": dr})
        out[i] = np.clip(pha[0, 0] * 255 + 0.5, 0, 255).astype(np.uint8)
        if i % 100 == 0:
            print(f"  matte {i}/{n}  {time.time() - t0:.0f}s", flush=True)
    out.flush()
    print("matte done", n, f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    extract()
    print("frames", len(list(FR.glob("f_*.jpg"))), flush=True)
    matte()
