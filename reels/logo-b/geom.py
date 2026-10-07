"""geom: the B monogram as exact vector outlines, measured from logo.webp (2000x2000 px).

Two closed contours: the slanted left stem and the bowl body. Output is in logo units:
x right, y up, origin at the centre of the logo's bounding box, 200 px = 1 unit.
"""
import json
import math
from pathlib import Path

CX, CY, U = 1035.5, 999.5, 200.0       # bbox centre (px) and px per unit

# measured geometry (px, y down)
STEM = [(674, 642), (792, 760), (792, 1238), (674, 1356)]
TOP_C, BOT_C = (1189, 851), (1189, 1148.5)
R_OUT_T, R_OUT_B, R_IN_T, R_IN_B = 208, 208.5, 91, 90.5


def arc(c, r, a0, a1, n):
    """points on a circle (px, y down), angles in degrees measured in y-up maths convention."""
    out = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        out.append((c[0] + r * math.cos(a), c[1] - r * math.sin(a)))
    return out


def waist():
    # where the two outer bowls meet
    yc = (TOP_C[1] + BOT_C[1]) / 2
    dx = math.sqrt(R_OUT_T ** 2 - (yc - TOP_C[1]) ** 2)
    a_top = math.degrees(math.atan2(-(yc - TOP_C[1]), dx))       # below the top centre -> negative
    a_bot = math.degrees(math.atan2(BOT_C[1] - yc, dx))
    return a_top, a_bot


def body(n=96):
    a_top, a_bot = waist()
    p = [(804, 643), (1189, 643)]
    p += arc(TOP_C, R_OUT_T, 90, a_top, n)[1:]
    p += arc(BOT_C, R_OUT_B, a_bot, -90, n)[1:]
    p += [(920, 1357), (920, 1239)]
    p += arc(BOT_C, R_IN_B, -90, 90, n)
    p += [(801, 1058), (801, 942)]
    p += arc(TOP_C, R_IN_T, -90, 90, n)
    p += [(921, 760)]
    return p


def to_units(pts):
    return [[round((x - CX) / U, 5), round(-(y - CY) / U, 5)] for x, y in pts]


def contours(n=96):
    return {"stem": to_units(STEM), "body": to_units(body(n))}


if __name__ == "__main__":
    import sys
    import numpy as np
    from PIL import Image, ImageDraw
    out = Path(__file__).with_name("work") / "logo.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(contours()))
    print("->", out)
    if "check" in sys.argv:          # overlap with the supplied logo
        img = Image.new("L", (2000, 2000), 0)
        d = ImageDraw.Draw(img)
        d.polygon(STEM, fill=255)
        d.polygon(body(), fill=255)
        a = np.array(Image.open(Path(__file__).with_name("logo.webp")).convert("L")) > 128
        b = np.array(img) > 128
        print(f"IoU {(a & b).sum() / (a | b).sum():.4f}  only-original {(a & ~b).sum()}  only-vector {(b & ~a).sum()}")
        diff = np.zeros((2000, 2000, 3), np.uint8)
        diff[a & ~b] = (255, 0, 0); diff[b & ~a] = (0, 160, 255); diff[a & b] = (60, 60, 60)
        Image.fromarray(diff[600:1400, 640:1440]).save(out.with_name("check.png"))
