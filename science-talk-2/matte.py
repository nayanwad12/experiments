"""Person matte for work/base.mp4 -> work/alpha.npy  uint8 (N, 960, 540), RobustVideoMatting mobilenetv3 (CPU).
The recurrent state is reset at every cut of the edit."""
import json
import subprocess
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort

HERE = Path(__file__).resolve().parent
W = HERE / "work"
E = json.loads((W / "edl.json").read_text())
N = sum(c[3] for c in E["cuts"])
CUT_STARTS = {int(round(c[2] * E["fps"])) for c in E["cuts"]}
w, h = 540, 960

so = ort.SessionOptions()
so.intra_op_num_threads = 4
sess = ort.InferenceSession("/home/user/models/rvm_mobilenetv3_fp32.onnx", so, providers=["CPUExecutionProvider"])
out = np.lib.format.open_memmap(W / "alpha.npy", mode="w+", dtype=np.uint8, shape=(N, h, w))
p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(W / "base.mp4"), "-vf", f"scale={w}:{h}:flags=area",
                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
dr = np.array([0.5], np.float32)
t0 = time.time()
for i in range(N):
    buf = p.stdout.read(w * h * 3)
    if len(buf) < w * h * 3:
        out[i:] = out[i - 1]
        break
    if i in CUT_STARTS:
        rec = [np.zeros((1, 1, 1, 1), np.float32)] * 4
        warm = 3
    src = (np.frombuffer(buf, np.uint8).reshape(h, w, 3).astype(np.float32) / 255).transpose(2, 0, 1)[None]
    for _ in range(warm):          # settle the recurrent state on the first frame of a cut
        _, _, *rec = sess.run(None, {"src": src, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2], "r4i": rec[3],
                                     "downsample_ratio": dr})
    warm = 1
    fgr, pha, *rec = sess.run(None, {"src": src, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2], "r4i": rec[3],
                                     "downsample_ratio": dr})
    out[i] = np.clip(pha[0, 0] * 255 + 0.5, 0, 255).astype(np.uint8)
    if i % 300 == 0:
        print(f"matte {i}/{N} {time.time() - t0:.0f}s", flush=True)
out.flush()
print("matte done", N, f"{time.time() - t0:.0f}s")
