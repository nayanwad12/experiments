"""Science image plates for the cutaways -> assets/img/*.png (from scikit-image's open sample data).

skin        histology, normal epidermis + dermis (H&E, 10x)
ihc         immunohistochemistry stain (immune markers in tissue)
mitosis     human cell nuclei mid-division (fluorescence, coloured)
cells       cell membranes + nuclei (confocal, 2 channels)
brain       MRI slice
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

D = Path(__file__).resolve().parent / "assets" / "img"


def norm(x, lo=1, hi=99.6):
    x = x.astype(np.float32)
    a, b = np.percentile(x, lo), np.percentile(x, hi)
    return np.clip((x - a) / (b - a + 1e-6), 0, 1)


def tint(ch, rgb):
    return ch[..., None] * np.array(rgb, np.float32)[None, None] / 255


def save(name, arr, size=None):
    im = Image.fromarray(np.clip(arr * 255 if arr.dtype != np.uint8 else arr, 0, 255).astype(np.uint8))
    if size:
        im = im.resize(size, Image.LANCZOS)
    im.save(D / f"{name}.png")
    print(name, im.size)


skin = np.load(D / "skin.npy")
save("skin", skin[40:940, 80:1240])

save("ihc", np.load(D / "immunohistochemistry.npy"), (900, 900))

m = norm(np.load(D / "human_mitosis.npy"), 1, 99.8) ** 0.8
glow = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6)), np.float32) / 255
save("mitosis", np.clip(tint(m, (90, 200, 255)) + tint(glow, (120, 60, 255)) * 0.7, 0, 1), (900, 900))

c3 = np.load(D / "cells3d.npy")[30]
mem, nuc = norm(c3[0], 2, 99.7), norm(c3[1], 2, 99.7)
save("cells", np.clip(tint(mem, (60, 255, 140)) + tint(nuc, (255, 60, 200)), 0, 1), (900, 900))

br = np.load(D / "brain.npy")[6].astype(np.float32)      # CT: window on soft tissue, keep the skull white
tissue = br[(br > 6000) & (br < 9000)]
lo, hi = np.percentile(tissue, [2, 99.5])
g = np.clip((br - lo) / (hi - lo), 0, 1) ** 0.9
g[br > 12000] = 0.96
save("brain_ct", np.stack([g, g, g], -1), (900, 900))
