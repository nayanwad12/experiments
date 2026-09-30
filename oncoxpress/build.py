"""OncoXpress brand film compositor.

Reads the 8 source clips, cleans them (Gemini watermark, stray brand logo), retimes with optical flow,
reframes to 1920x1080, grades, lays the motion graphics (rendered by render_mg.mjs) on top, and
finishes everything with a soft bloom and a light vignette (clean look, no grain).

  python3 build.py                 # all frames -> work/frames/f00000.jpg
  python3 build.py --stills 5,22   # check frames -> work/stills/
  python3 build.py --range 0 400   # frame range
"""
import os
import sys
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
sys.path.insert(0, HERE)
sys.path.insert(0, WORK)
import look  # noqa: E402
import wm  # noqa: E402

W, H, FPS = 1920, 1080, 24
DUR = 80.0
NF = int(DUR * FPS)

# ---------------------------------------------------------------- edit decision list
# (film t0, film t1, clip, src frame in, src frame out, zoom in, zoom out, (cx, cy) focus in source px)
# Narration starts at film 1.0 s. Every shot below avoids the AI morph-dissolves, the self-rotating monitor,
# the phone that grows out of the folder, and the close-ups of garbled screen text.
EDL = [
    (0.00, 4.30, 1, 0, 80, 1.06, 1.14, (640, 330)),     # ward, holding her file — "In cancer care…"
    (4.30, 6.90, 1, 86, 148, 1.04, 1.10, (560, 380)),   # waiting room — "Every report holds information."
    (6.90, 9.25, 1, 157, 204, 1.10, 1.20, (700, 420)),  # the folder, tilt up — "And every detail matters."
    (9.25, 12.45, 3, 74, 150, 1.02, 1.12, (640, 340)),  # overhead desk — "rarely lives in one place."
    (12.45, 14.35, 2, 27, 72, 1.06, 1.12, (700, 300)),  # phone — "Blood reports on the phone."
    (14.35, 16.25, 2, 96, 141, 1.08, 1.16, (560, 330)),  # portal — "Scans in hospital portals."
    (16.25, 18.30, 2, 158, 190, 1.10, 1.18, (580, 330)),  # email — "Pathology reports in emails."
    (18.30, 19.55, 2, 205, 235, 1.10, 1.16, (640, 360)),  # PDF viewer + folder — "Prescriptions and PDFs…"
    (19.55, 21.30, 3, 38, 70, 1.04, 1.10, (640, 400)),  # paper in hand — "…inside physical folders."
    # 21.30-26.20 split-screen: "Different records. Different places. They rarely speak to each other."
    # 26.20-28.75 brand reveal (mg)
    (28.75, 32.60, 4, 72, 142, 1.03, 1.10, (620, 330)),  # the two doctors — leadership
    (32.60, 35.20, 3, 202, 239, 1.04, 1.34, (380, 490)),  # still desk, push in to the phone — "powered by BigOHealth"
    # 35.20-63.70 product sequence (mg): the records gather into one secure place, then upload, organise, track
    # (clip 5's laptop scene was dropped: its screen morphs and the desktop flickers)
    (63.70, 65.60, 8, 44, 78, 1.04, 1.10, (620, 380)),  # consultation — "patients spend less time…"
    # 65.60-67.60 search (mg)
    (67.60, 70.70, 7, 190, 239, 1.02, 1.12, (760, 360)),  # doctor reading — "doctors understand years…"
    # 70.70-72.35 "under 60 seconds" (mg);  72.35-80.00 end card (mg)
]
GRID = (21.30, 26.20)
MG_FULL = [(26.20, 28.75), (35.20, 63.70), (65.60, 67.60), (70.70, 72.35), (72.35, 80.0)]
LEAKS = [(26.20, 1.0, 0.45), (35.20, 0.8, 0.25), (72.35, 1.1, 0.4)]  # soft warm flashes on the big transitions  # centre, width, gain

APPLE = np.load(os.path.join(WORK, "apple_mask.npy"))


# ---------------------------------------------------------------- sources
@lru_cache(maxsize=2)
def clip(c):
    cap = cv2.VideoCapture(os.path.join(HERE, "raw", f"clip{c}B.mp4"))
    fr = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if c in (1, 2):
            f = wm.clean(f)
        if c == 5 and f is not None and len(fr) < 50:
            f = cv2.inpaint(f, APPLE, 6, cv2.INPAINT_TELEA)
        fr.append(f)
    return fr


_dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)


@lru_cache(maxsize=64)
def flows(c, i):
    a = cv2.cvtColor(clip(c)[i], cv2.COLOR_BGR2GRAY)
    b = cv2.cvtColor(clip(c)[i + 1], cv2.COLOR_BGR2GRAY)
    return _dis.calc(a, b, None), _dis.calc(b, a, None)


def src_frame(c, s):
    """Frame at fractional source index s, optical-flow interpolated (Super-SloMo style linear flow model)."""
    fr = clip(c)
    s = min(max(s, 0), len(fr) - 1)
    i = int(np.floor(s))
    a = float(s - i)
    if a < 0.02 or i >= len(fr) - 1:
        return fr[i]
    if a > 0.98:
        return fr[i + 1]
    f01, f10 = flows(c, i)
    ft0 = -(1 - a) * a * f01 + a * a * f10
    ft1 = (1 - a) * (1 - a) * f01 - a * (1 - a) * f10
    h, w = f01.shape[:2]
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    ft0, ft1 = ft0.astype(np.float32), ft1.astype(np.float32)
    i0 = cv2.remap(fr[i], gx + ft0[..., 0], gy + ft0[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    i1 = cv2.remap(fr[i + 1], gx + ft1[..., 0], gy + ft1[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return cv2.addWeighted(i0, 1 - a, i1, a, 0)


SOFT = {2: 1.6, 3: 1.0, 4: 1.2, 5: 1.4, 7: 1.5, 8: 1.4}   # screen defocus strength per clip (source px sigma)


def soften_screens(img, c):
    """Rack the focus off the screens: AI-rendered UI text is gibberish up close, so screens (bright, low
    saturation panels — and the blue desktop in clip 5) are defocused like a shallow depth of field would."""
    sig = SOFT.get(c)
    if not sig:
        return img
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 2] > 195) & (hsv[..., 1] < 45)).astype(np.uint8)
    if c == 5:
        m |= cv2.inRange(hsv, (95, 90, 90), (125, 255, 255)) // 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    keep = np.zeros_like(m)
    for i in range(1, n):
        if st[i][4] > 2500:
            keep[lab == i] = 1
    if not keep.any():
        return img
    keep = cv2.morphologyEx(keep, cv2.MORPH_CLOSE, np.ones((31, 31), np.uint8))
    mk = cv2.GaussianBlur(keep.astype(np.float32), (0, 0), 7)[..., None]
    bl = cv2.GaussianBlur(img, (0, 0), sig)
    return (img * (1 - mk) + bl * mk).astype(np.uint8)


def ease(x):
    return x * x * (3 - 2 * x)


def reframe(img, zoom, cx, cy):
    """Scale 1280x720 source to 1920x1080 with an extra zoom about the focus point, clamped to the frame."""
    sh, sw = img.shape[:2]
    s = W / sw * zoom
    vw, vh = W / s, H / s
    x0 = min(max(cx - vw / 2, 0), sw - vw)
    y0 = min(max(cy - vh / 2, 0), sh - vh)
    M = np.float32([[s, 0, -x0 * s], [0, s, -y0 * s]])
    out = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
    # gentle sharpening to restore detail lost in the 720p -> 1080p scale
    bl = cv2.GaussianBlur(out, (0, 0), 1.6)
    return cv2.addWeighted(out, 1.25, bl, -0.25, 0)


def shot_frame(t):
    for (t0, t1, c, a, b, z0, z1, (cx, cy)) in EDL:
        if t0 <= t < t1:
            k = (t - t0) / (t1 - t0)
            s = a + k * (b - a)
            z = z0 + (z1 - z0) * ease(k)
            return reframe(soften_screens(src_frame(c, s), c), z, cx, cy)
    return None


# ---------------------------------------------------------------- split-screen scene
FONTS = os.path.join(HERE, "fonts")


def _font(name, size, wght=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if wght:
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
    return f


F_T = _font("Lexend[wght].ttf", 30, 560)
F_S = _font("InstrumentSerif-Italic.ttf", 32)
F_C = _font("Lexend[wght].ttf", 17, 500)
TILES = [  # clip, src from, src to, title, subtitle
    (2, 30, 70, "Blood reports", "on the phone"),
    (2, 100, 140, "Scans", "in hospital portals"),
    (2, 160, 188, "Pathology reports", "in emails"),
    (3, 40, 70, "Prescriptions & PDFs", "in physical folders"),
]
TW, TH = 700, 394
PAPER = np.array([0.925, 0.905, 0.868], np.float32)


def _rounded_mask(w, h, r):
    m = np.zeros((h, w), np.uint8)
    cv2.rectangle(m, (r, 0), (w - r, h), 255, -1)
    cv2.rectangle(m, (0, r), (w, h - r), 255, -1)
    for x, y in ((r, r), (w - r, r), (r, h - r), (w - r, h - r)):
        cv2.circle(m, (x, y), r, 255, -1, cv2.LINE_AA)
    return m.astype(np.float32) / 255


@lru_cache(maxsize=4)
def _tile_label(i):
    im = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    _, _, _, title, sub = TILES[i]
    d.text((30, TH - 92), title, font=F_T, fill=(250, 246, 238, 255))
    d.text((30, TH - 54), sub, font=F_S, fill=(235, 230, 220, 235))
    return np.asarray(im).astype(np.float32) / 255


SCRIM = np.clip((np.arange(TH, dtype=np.float32) - TH * 0.45) / (TH * 0.55), 0, 1)[:, None, None] ** 1.4 * 0.62
TMASK = _rounded_mask(TW, TH, 22)


def grid_frame(t):
    t0, t1 = GRID
    bg = np.empty((H, W, 3), np.float32)
    bg[:] = PAPER
    # soft light pool
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    bg *= (0.94 + 0.08 * np.exp(-(((xx - 960) / 900) ** 2 + ((yy - 480) / 600) ** 2)))[..., None]
    appear = [21.35, 21.62, 22.93, 23.15]
    drift = ease(np.clip((t - 23.3) / 2.0, 0, 1))
    gap = 36 + 64 * drift
    collapse = ease(np.clip((t - 25.35) / 0.8, 0, 1))
    centers = []
    layer = bg.copy()
    for i, (c, a, b, _, _) in enumerate(TILES):
        k = np.clip((t - appear[i]) / 0.5, 0, 1)
        if k <= 0:
            centers.append(None)
            continue
        e = 1 - (1 - k) ** 3
        col, row = i % 2, i // 2
        cx = 960 + (col - 0.5) * (TW + gap)
        cy = 540 + (row - 0.5) * (TH + gap)
        cx += (960 - cx) * collapse
        cy += (540 - cy) * collapse
        sc = (0.9 + 0.1 * e) * (1 - 0.75 * collapse)
        op = e * (1 - collapse)
        centers.append((cx, cy, sc, op))
        s = a + (b - a) * np.clip((t - appear[i]) / (t1 - appear[i]), 0, 1)
        fr = soften_screens(src_frame(c, s), c)
        fr = cv2.resize(fr, (TW, TH), interpolation=cv2.INTER_AREA)[..., ::-1].astype(np.float32) / 255
        fr = look.grade(fr, 1.0)
        # they go grey as they fail to connect
        lum = fr @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        fr = fr + (lum[..., None] - fr) * (0.55 * drift)
        fr = fr * (1 - SCRIM) + SCRIM * 0.05
        lab = _tile_label(i)
        fr = fr * (1 - lab[..., 3:]) + lab[..., :3] * lab[..., 3:]
        tw, th = int(TW * sc), int(TH * sc)
        if tw < 8:
            continue
        fr = cv2.resize(fr, (tw, th), interpolation=cv2.INTER_AREA)
        m = cv2.resize(TMASK, (tw, th), interpolation=cv2.INTER_AREA)[..., None] * op
        x0, y0 = int(cx - tw / 2), int(cy - th / 2)
        # shadow
        sh = np.zeros((H, W), np.float32)
        cv2.rectangle(sh, (x0 + 10, y0 + 24), (x0 + tw - 10, y0 + th + 20), 1.0, -1)
        sh = cv2.GaussianBlur(sh, (0, 0), 26) * 0.22 * op
        layer *= (1 - sh[..., None])
        xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + tw, W), min(y0 + th, H)
        sub = layer[ya:yb, xa:xb]
        mm = m[ya - y0:yb - y0, xa - x0:xb - x0]
        layer[ya:yb, xa:xb] = sub * (1 - mm) + fr[ya - y0:yb - y0, xa - x0:xb - x0] * mm
    # connectors that try, and fail, to link the records
    if all(ci is not None for ci in centers):
        draw = np.zeros((H, W), np.float32)
        kd = np.clip((t - 23.35) / 0.8, 0, 1)
        kb = ease(np.clip((t - 24.25) / 0.7, 0, 1))
        fade = 1 - ease(np.clip((t - 24.7) / 0.6, 0, 1))
        pairs = [(0, 1), (1, 3), (3, 2), (2, 0), (0, 3)]
        for j, (p, q) in enumerate(pairs):
            (ax, ay, _, _), (bx, by, _, _) = centers[p], centers[q]
            kk = np.clip(kd * 1.6 - j * 0.15, 0, 1)
            if kk <= 0:
                continue
            L = np.hypot(bx - ax, by - ay)
            n = int(L / 22)
            for s_ in range(n):
                u0, u1 = s_ / n, (s_ + 0.5) / n
                if u1 > kk:
                    break
                mid = abs((u0 + u1) / 2 - 0.5)
                if mid < 0.23 * kb:          # the link breaks open in the middle
                    continue
                pa = (int(ax + (bx - ax) * u0), int(ay + (by - ay) * u0))
                pb = (int(ax + (bx - ax) * u1), int(ay + (by - ay) * u1))
                cv2.line(draw, pa, pb, 1.0, 3, cv2.LINE_AA)
            # node dots
            cv2.circle(draw, (int(ax), int(ay)), 7, 1.0, -1, cv2.LINE_AA)
        draw = draw * fade
        colr = np.array([0.18, 0.47, 0.37], np.float32) * (1 - kb) + np.array([0.62, 0.30, 0.26], np.float32) * kb
        layer = layer * (1 - draw[..., None] * 0.9) + colr * draw[..., None] * 0.9
    # small caption top-left
    return layer


# ---------------------------------------------------------------- light leaks
def leak(t, fi):
    tot = np.zeros((H, W, 3), np.float32)
    any_ = False
    yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)
    for (c, wdt, gain) in LEAKS:
        k = (t - c) / (wdt / 2)
        if abs(k) >= 1:
            continue
        any_ = True
        env = (np.cos(k * np.pi / 2) ** 2) * gain
        acc = np.zeros((H // 4, W // 4, 3), np.float32)
        rng = np.random.default_rng(int(c * 100))
        for b in range(4):
            px = (rng.uniform(-0.2, 1.2) + 0.35 * k * rng.choice([-1, 1])) * W / 4
            py = rng.uniform(0.0, 1.0) * H / 4
            r = rng.uniform(0.25, 0.55) * W / 4
            colr = [np.array([1.0, 0.55, 0.22]), np.array([1.0, 0.36, 0.20]), np.array([1.0, 0.80, 0.50]), np.array([0.95, 0.45, 0.35])][b]
            g = np.exp(-(((xx - px) / r) ** 2 + ((yy - py) / (r * 1.6)) ** 2))
            acc += g[..., None] * colr.astype(np.float32)
        tot += cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * env
    return tot if any_ else None


# ---------------------------------------------------------------- mg overlay
def mg_layer(fi):
    p = os.path.join(WORK, "mg", f"f{fi:05d}.png")
    if not os.path.exists(p):
        return None
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if im.shape[2] == 3:
        im = np.dstack([im, np.full(im.shape[:2], 255, np.uint8)])
    a = im[..., 3:].astype(np.float32) / 255
    if a.max() < 0.004:
        return None
    return im[..., 2::-1].astype(np.float32) / 255, a


def in_ranges(t, rr):
    return any(a <= t < b for a, b in rr)


def frame(fi):
    t = fi / FPS
    full_mg = in_ranges(t, MG_FULL)
    if GRID[0] <= t < GRID[1]:
        x = grid_frame(t)
        x = look.grade(x, 0.30)
        amt = 0.30
    elif full_mg:
        x = np.empty((H, W, 3), np.float32)
        x[:] = PAPER
        amt = 0.30
    else:
        sf = shot_frame(t)
        x = sf[..., ::-1].astype(np.float32) / 255
        x = look.grade(x, 1.0)
        amt = 1.0
    ml = mg_layer(fi)
    if ml is not None:
        rgb, a = ml
        if full_mg:
            rgb = look.grade(rgb, 0.30)
        x = x * (1 - a) + rgb * a
    lk = leak(t, fi)
    if lk is not None:
        x = 1 - (1 - x) * (1 - np.clip(lk * 0.85, 0, 1))      # screen blend
    x = look.finish(x, fi, grain_amt=1.0 if amt == 1.0 else 0.8, hal=1.0 if amt == 1.0 else 0.5,
                    vig=1.0 if amt == 1.0 else 0.6)
    # fades: in from black, out to black
    fade = min(1.0, t / 0.8) * min(1.0, max(0.0, (DUR - 0.05 - t) / 1.0))
    x = x * ease(np.clip(fade, 0, 1))
    return (np.clip(x, 0, 1)[..., ::-1] * 255 + 0.5).astype(np.uint8)


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--stills" in args:
        ts = [float(v) for v in args[args.index("--stills") + 1].split(",")]
        os.makedirs(os.path.join(WORK, "stills"), exist_ok=True)
        for tt in ts:
            cv2.imwrite(os.path.join(WORK, "stills", f"v_{tt:05.2f}.jpg"), frame(int(round(tt * FPS))), [cv2.IMWRITE_JPEG_QUALITY, 92])
            print("still", tt, flush=True)
        sys.exit(0)
    a, b = 0, NF
    if "--range" in args:
        i = args.index("--range")
        a, b = int(args[i + 1]), int(args[i + 2])
    od = os.path.join(WORK, "frames")
    os.makedirs(od, exist_ok=True)
    for fi in range(a, b):
        p = os.path.join(od, f"f{fi:05d}.png")
        if os.path.exists(p) and "--force" not in args:
            continue
        cv2.imwrite(p, frame(fi), [cv2.IMWRITE_PNG_COMPRESSION, 1])
        if fi % 48 == 0:
            print("frame", fi, flush=True)
