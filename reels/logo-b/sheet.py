"""contact sheet of rendered stills: python3 sheet.py out/stills/16x9 [cols]"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
d = Path(sys.argv[1]); cols = int(sys.argv[2]) if len(sys.argv) > 2 else 2
fs = sorted(d.glob("w_*.png"), key=lambda p: float(p.stem[2:]))
ims = [Image.open(f).convert("RGB") for f in fs]
w = 960 if ims[0].width >= ims[0].height else 400
ims = [i.resize((w, round(i.height * w / i.width)), Image.LANCZOS) for i in ims]
h = ims[0].height; rows = -(-len(ims) // cols)
sheet = Image.new("RGB", (cols * w + (cols - 1) * 6, rows * h + (rows - 1) * 6), (60, 60, 60))
for k, (im, f) in enumerate(zip(ims, fs)):
    x, y = (k % cols) * (w + 6), (k // cols) * (h + 6); sheet.paste(im, (x, y))
    ImageDraw.Draw(sheet).text((x + 8, y + 6), f.stem[2:], fill=(255, 80, 80))
sheet.save(d / "sheet.png"); print(d / "sheet.png")
