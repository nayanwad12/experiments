"""RobustVideoMatting over the whole take at 30 fps -> alpha.npy (N,H,W uint8) + frames.npy (N,H,W,3 uint8)."""
import subprocess, time
import numpy as np, onnxruntime as ort, imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H = 824, 464   # crop 832x464 -> 824x464 (16:9-ish), 4px each side
p = subprocess.Popen([FF, "-v", "error", "-i", "../raw/raw.mp4", "-vf", f"fps=30,crop={W}:{H}", "-f", "rawvideo",
                      "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
N = int(85.87 * 30) + 2
frames = np.lib.format.open_memmap("frames.npy", mode="w+", dtype=np.uint8, shape=(N, H, W, 3))
alpha = np.lib.format.open_memmap("alpha.npy", mode="w+", dtype=np.uint8, shape=(N, H, W))
so = ort.SessionOptions(); so.intra_op_num_threads = 4
s = ort.InferenceSession("/home/user/models/rvm_resnet50_fp32.onnx", so, providers=["CPUExecutionProvider"])
rec = [np.zeros((1, 1, 1, 1), np.float32)] * 4
dr = np.array([0.5], np.float32)
t0 = time.time(); i = 0
while True:
    b = p.stdout.read(W * H * 3)
    if len(b) < W * H * 3: break
    f = np.frombuffer(b, np.uint8).reshape(H, W, 3)
    frames[i] = f
    src = (f.astype(np.float32) / 255).transpose(2, 0, 1)[None]
    fgr, pha, *rec = s.run(None, {"src": src, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2], "r4i": rec[3], "downsample_ratio": dr})
    alpha[i] = (pha[0, 0] * 255 + 0.5).astype(np.uint8)
    i += 1
    if i % 150 == 0: print(i, round(time.time() - t0, 1), flush=True)
open("nframes.txt", "w").write(str(i))
frames.flush(); alpha.flush()
print("done", i, round(time.time() - t0, 1))
