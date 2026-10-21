"""Procedural SEM-style micrograph of gut bacteria (rods + cocci) -> assets/img/bacteria.png (1200x900).

Grayscale, edge-lit like a scanning electron microscope, shallow depth of field, a faint false-colour tint.
"""
import math
from pathlib import Path

import numpy as np
import skia

HERE = Path(__file__).resolve().parent
Wd, Hd = 1200, 900
rng = np.random.default_rng(21)


def capsule(c, x, y, L, r, ang, shade, blur):
    c.save()
    c.translate(x, y)
    c.rotate(math.degrees(ang))
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-L / 2, -r, L, 2 * r), r, r)
    body = skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeLinear(
        [skia.Point(0, -r), skia.Point(0, r)],
        [skia.Color4f(shade * 1.15, shade * 1.15, shade * 1.18, 1), skia.Color4f(shade * 0.55, shade * 0.56, shade * 0.6, 1),
         skia.Color4f(shade * 0.25, shade * 0.26, shade * 0.3, 1)], [0, 0.55, 1]))
    if blur:
        body.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    shadow = skia.Paint(AntiAlias=True, Color=skia.Color4f(0, 0, 0, 0.55))
    shadow.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, r * 0.6 + blur))
    c.save()
    c.translate(r * 0.25, r * 0.45)
    c.drawRRect(rr, shadow)
    c.restore()
    c.drawRRect(rr, body)
    rim = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=max(1.0, r * 0.12),
                     Color=skia.Color4f(min(1, shade * 1.5), min(1, shade * 1.5), min(1, shade * 1.55), 0.55))
    if blur:
        rim.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    c.drawRRect(rr, rim)
    c.restore()


def main():
    s = skia.Surface(Wd, Hd)
    with s as c:
        c.clear(skia.Color4f(0.05, 0.055, 0.06, 1))
        # mucus / substrate texture
        for _ in range(900):
            x, y = rng.uniform(0, Wd), rng.uniform(0, Hd)
            p = skia.Paint(AntiAlias=True, Color=skia.Color4f(0.2, 0.21, 0.22, rng.uniform(0.03, 0.09)))
            p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, rng.uniform(4, 20)))
            c.drawCircle(x, y, rng.uniform(6, 40), p)
        items = []
        for _ in range(170):
            depth = rng.uniform(0, 1)
            items.append((depth, "rod"))
        for _ in range(45):
            items.append((rng.uniform(0, 1), "coccus"))
        for depth, kind in sorted(items):
            x, y = rng.uniform(-40, Wd + 40), rng.uniform(-40, Hd + 40)
            sc = 0.55 + 0.9 * depth
            blur = abs(depth - 0.7) * 5.5
            shade = 0.35 + 0.55 * depth
            if kind == "rod":
                capsule(c, x, y, rng.uniform(70, 150) * sc, rng.uniform(11, 16) * sc, rng.uniform(0, math.pi), shade, blur)
            else:
                r = rng.uniform(10, 16) * sc
                for j in range(int(rng.integers(1, 4))):
                    capsule(c, x + j * r * 1.8, y + j * r * 0.4, 2 * r, r, 0, shade, blur)
    arr = s.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3].astype(np.float32)
    g = arr.mean(-1, keepdims=True)
    tint = np.array([0.92, 1.0, 1.02], np.float32)
    out = np.clip(g * tint + rng.normal(0, 3.5, g.shape), 0, 255).astype(np.uint8)
    yy, xx = np.mgrid[0:Hd, 0:Wd]
    vig = 1 - 0.35 * (((xx - Wd / 2) / (Wd / 2)) ** 2 + ((yy - Hd / 2) / (Hd / 2)) ** 2)
    out = np.clip(out * vig[..., None], 0, 255).astype(np.uint8)
    from PIL import Image
    Image.fromarray(out).save(HERE / "assets" / "img" / "bacteria.png")
    print("-> assets/img/bacteria.png")


if __name__ == "__main__":
    main()
