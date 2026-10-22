"""tile check stills: python3 montage.py out.jpg a.png b.png ... (6 per row, labelled)"""
import sys
from PIL import Image, ImageDraw
files = sys.argv[2:]
tw, th = 360, 640
cols = min(6, len(files)); rows = (len(files) + cols - 1) // cols
img = Image.new("RGB", (cols * (tw + 4), rows * (th + 24)), (60, 60, 60))
d = ImageDraw.Draw(img)
for i, f in enumerate(files):
    r, c = divmod(i, cols)
    img.paste(Image.open(f).convert("RGB").resize((tw, th)), (c * (tw + 4), r * (th + 24) + 22))
    d.text((c * (tw + 4) + 4, r * (th + 24) + 4), f.split("/")[-1], fill=(255, 255, 0))
img.save(sys.argv[1], quality=88)
