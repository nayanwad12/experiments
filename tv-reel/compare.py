# Side-by-side RAW vs EDITED comparison reel, synced to the final edit's audio.
import numpy as np, subprocess, sys, cv2
from PIL import Image, ImageDraw
import reel as R

W, H, FPS = 1080, 1920, 30
edit_path, out_path = sys.argv[1], sys.argv[2]
PW, PH = 416, 740
XR, XE, PY = 96, 548, 492
STUMBLE_O = [23.10, 34.87, 45.53]
CUTS = [o for a, b, o in R.SEGS[1:]]

def txt(d, xy, s, fk, size, col, anchor="la", track=0):
    f = R.font(fk, size)
    if not track: d.text(xy, s, font=f, fill=col, anchor=anchor); return
    x, y = xy
    tw = sum(f.getlength(c) + track for c in s) - track
    if anchor[0] == "m": x -= tw / 2
    elif anchor[0] == "r": x -= tw
    for c in s: d.text((x, y), c, font=f, fill=col, anchor="l" + anchor[1]); x += f.getlength(c) + track

def static_bg():
    im = Image.fromarray((R.bg_static("paper") * 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im)
    d.rectangle([62, 251, 76, 265], fill=R.GREEN)
    txt(d, (88, 258), "VIBE EDITING / BEFORE → AFTER", "mono", 26, R.INK, "lm", 3)
    txt(d, (540, 392), "SAME TAKE.", "black", 92, R.INK, "ms")
    txt(d, (540, 462), "zero editing apps", "serif", 60, R.GREEN, "ms")
    for x, lab, c in ((XR, "RAW", R.INK), (XE, "EDITED", R.GREEN)):
        d.rounded_rectangle([x - 4, PY - 4, x + PW + 4, PY + PH + 4], 22, fill=R.INK)
        d.rounded_rectangle([x + 8, PY + PH + 4, x + PW + 12, PY + PH + 14], 6, fill=c)
    return im

BG = static_bg()

def round_mask(w, h, r):
    m = Image.new("L", (w * 2, h * 2), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 1], r * 2, fill=255)
    return np.asarray(m.resize((w, h), Image.LANCZOS), np.float32)[..., None] / 255
MASK = round_mask(PW, PH, 18)

def fmt(s): return "%d:%04.1f" % (int(s // 60), s % 60)

def frame(fi, ed):
    t = fi / FPS
    im = BG.copy(); d = ImageDraw.Draw(im)
    st = min(R.src_time(t), 82.3)
    raw = np.asarray(R.SRC[min(int(round(st * 30)), R.SRC.shape[0] - 1)])
    raw = cv2.resize(raw, (PW, PH), interpolation=cv2.INTER_AREA)
    edp = cv2.resize(ed, (PW, PH), interpolation=cv2.INTER_AREA)
    a = np.asarray(im).copy()
    for x, p in ((XR, raw), (XE, edp)):
        reg = a[PY:PY + PH, x:x + PW, :3].astype(np.float32)
        a[PY:PY + PH, x:x + PW, :3] = (reg * (1 - MASK) + p.astype(np.float32) * MASK).astype(np.uint8)
    im = Image.fromarray(a); d = ImageDraw.Draw(im)
    # panel labels
    for x, lab, fill, tc in ((XR, "RAW", R.INK, R.CREAM), (XE, "EDITED", R.GREEN, R.CREAM)):
        w = R.font("monox", 28).getlength(lab) + 3 * len(lab) + 34
        d.rounded_rectangle([x + 16, PY + 16, x + 16 + w, PY + 64], 24, fill=fill, outline=R.CREAM, width=2)
        txt(d, (x + 16 + w / 2, PY + 41), lab, "monox", 28, tc, "mm", 3)
    # live counters
    ncut = sum(1 for o in CUTS if o <= t)
    nst = sum(1 for o in STUMBLE_O if o <= t)
    npause = ncut - nst
    y0 = 1258
    cells = [("CUTS", "%02d" % ncut, R.INK), ("PAUSES CUT", "%02d" % npause, R.GREEN), ("RETAKES CUT", "%d" % nst, R.ORANGE)]
    cw = 276
    for k, (lab, val, c) in enumerate(cells):
        x = 96 + k * (cw + 18)
        d.rounded_rectangle([x + 6, y0 + 6, x + cw + 6, y0 + 136], 18, fill=R.INK)
        d.rounded_rectangle([x, y0, x + cw, y0 + 130], 18, fill=R.CREAM, outline=R.INK, width=3)
        txt(d, (x + 20, y0 + 28), lab, "mono", 21, R.MUTE, "lm", 2)
        txt(d, (x + 20, y0 + 114), val, "black", 62, c, "ls")
    # time readout
    y1 = 1422
    txt(d, (96, y1), "RAW  " + fmt(st), "monox", 26, R.INK, "lm", 1)
    txt(d, (964, y1), "EDIT  " + fmt(min(t, R.TOTAL)), "monox", 26, R.GREEN, "rm", 1)
    # raw timeline strip: kept (ink) vs cut (orange) with playhead
    y2, x0, x1 = 1452, 96, 964; L = 82.37
    d.rounded_rectangle([x0, y2, x1, y2 + 30], 8, fill=R.ORANGE)
    for a_, b_, o in R.SEGS:
        d.rectangle([x0 + (x1 - x0) * a_ / L, y2, x0 + (x1 - x0) * b_ / L, y2 + 30], fill=R.INK)
    px = x0 + (x1 - x0) * st / L
    d.polygon([(px - 9, y2 - 14), (px + 9, y2 - 14), (px, y2 - 2)], fill=R.GREEN)
    d.line([px, y2 - 4, px, y2 + 34], fill=R.CREAM, width=3)
    d.rectangle([96, y2 + 45, 112, y2 + 61], fill=R.INK); txt(d, (122, y2 + 53), "KEPT", "mono", 20, R.MUTE, "lm", 1)
    d.rectangle([206, y2 + 45, 222, y2 + 61], fill=R.ORANGE); txt(d, (232, y2 + 53), "CUT", "mono", 20, R.MUTE, "lm", 1)
    txt(d, (964, y2 + 53), "82.4s RAW → %.1fs EDIT" % R.TOTAL, "mono", 20, R.MUTE, "rm", 1)
    return np.asarray(im.convert("RGB"))

if __name__ == "__main__":
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", edit_path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p", out_path], stdin=subprocess.PIPE)
    fi = 0
    while True:
        b = dec.stdout.read(W * H * 3)
        if len(b) < W * H * 3: break
        enc.stdin.write(frame(fi, np.frombuffer(b, np.uint8).reshape(H, W, 3)).tobytes()); fi += 1
        if fi % 300 == 0: print(fi, flush=True)
    enc.stdin.close(); enc.wait(); print("frames", fi)
