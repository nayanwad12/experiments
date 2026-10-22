"""Make the chair headrest a solid part of the cut-out instead of a ragged fragment.

RVM keeps parts of the mesh headrest behind the head in some frames and drops them in others, which flickers
and looks broken on coloured backgrounds. The camera is locked, so the headrest is a fixed region: pixels that are
dark in most frames (static) around head height. Inside that region, every pixel that is dark in the current
frame (chair or hair) is added to the matte, so the headrest reads as one solid chair behind the speaker.
-> work/alpha.npy (RVM original kept as work/alpha_rvm.npy)
"""
import shutil
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
FR = HERE / "work" / "frames"
src = HERE / "work" / "alpha_rvm.npy"
if not src.exists():
    shutil.copy(HERE / "work" / "alpha.npy", src)
A = np.load(src, mmap_mode="r")
n = len(A)


def small(i):
    return cv2.resize(cv2.imread(str(FR / f"f_{i + 1:05d}.jpg")), (540, 960), interpolation=cv2.INTER_AREA)


dark_p = HERE / "work" / "darkfrac.npy"
if dark_p.exists():
    dark_frac = np.load(dark_p)
else:
    dark_frac = np.mean([small(i).mean(axis=2) < 110 for i in range(0, n, 6)], axis=0)
    np.save(dark_p, dark_frac)
region = np.zeros((960, 540), np.uint8)
region[360:540, 130:410] = (dark_frac[360:540, 130:410] > 0.4)
region = cv2.morphologyEx(region, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
region = cv2.GaussianBlur(region.astype(np.float32), (7, 7), 0)
cv2.imwrite(str(HERE / "work" / "chair_mask.png"), (region * 255).astype(np.uint8))
out = np.lib.format.open_memmap(HERE / "work" / "alpha.npy", mode="w+", dtype=np.uint8, shape=A.shape)
for i in range(n):
    a = np.asarray(A[i]).astype(np.float32)
    lum = cv2.GaussianBlur(small(i).mean(axis=2).astype(np.float32), (5, 5), 0)
    k = np.clip((180 - lum) / 40, 0, 1) * region
    out[i] = np.clip(np.maximum(a, k * 255), 0, 255).astype(np.uint8)
out.flush()
print("done", n)
