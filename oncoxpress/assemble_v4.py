"""Assemble the v4 film from the finished v3 film + new material, add white subtitles.

    python3 assemble_v4.py                  # all frames -> work/frames4/
    python3 assemble_v4.py --stills 30,75   # check frames -> work/stills/v4_*.jpg
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import build
import look
import v4

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
W, H, FPS = 1920, 1080, v4.FPS
OLD = os.path.join(WORK, "film_v3.mp4")   # the v3 film: git show 84d5dda:oncoxpress/out/oncoxpress_brand_film.mp4
if not os.path.exists(OLD):
    with open(OLD, "wb") as fh:
        subprocess.run(["git", "show", "84d5dda:oncoxpress/out/oncoxpress_brand_film.mp4"], cwd=HERE, stdout=fh, check=True)


# ---------------------------------------------------------------- v3 film, read sequentially
class OldReader:
    def __init__(self):
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", OLD, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                                  stdout=subprocess.PIPE)
        self.i, self.cur = -1, None

    def get(self, idx):
        if idx < self.i:
            raise ValueError("old frames must be read in order")
        while self.i < idx:
            buf = self.p.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                return self.cur
            self.cur = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
            self.i += 1
        return self.cur


def crop_preview(fr, t):
    """Doctors preview: crop above the v3 lower-third with a gentle push."""
    k = (t - v4.PREVIEW[0]) / (v4.PREVIEW[1] - v4.PREVIEW[0])
    h = v4.CROP_H - 40 * k
    w = h * 16 / 9
    cx, cy = 985, h / 2
    x0 = int(round(min(max(cx - w / 2, 0), W - w)))
    c = fr[0:int(h), x0:x0 + int(w)]
    out = cv2.resize(c, (W, H), interpolation=cv2.INTER_LANCZOS4)
    bl = cv2.GaussianBlur(out, (0, 0), 1.4)
    return cv2.addWeighted(out, 1.3, bl, -0.3, 0)


# ---------------------------------------------------------------- new section footage (clip 11)
SOON_SHOTS = [  # new t0, t1, src from, src to, zoom in, zoom out, focus
    (74.30, 76.95, 168, 232, 1.03, 1.10, (640, 360)),   # walking together — "And this is just the beginning."
    (81.90, 83.75, 4, 46, 1.04, 1.10, (640, 360)),      # a meal served — diet & nutrition
    (83.75, 85.30, 56, 92, 1.04, 1.10, (640, 340)),     # family on the sofa — emotional well-being
    (85.30, 86.40, 112, 138, 1.03, 1.08, (680, 400)),   # the scanner — diagnostics
]
MG_FULL = [v4.DOCS, (76.95, 81.90), (86.40, 89.0)]
POW_SHOT = (34.60, 37.10, 90, 150, 1.02, 1.08, (640, 330))   # surgeon + circuit tree, src frames 90-150


def soon_shot(t):
    for c, (t0, t1, a, b, z0, z1, (cx, cy)) in [(11, s) for s in SOON_SHOTS] + [(12, POW_SHOT)]:
        if t0 <= t < t1:
            k = (t - t0) / (t1 - t0)
            return build.reframe(build.src_frame(c, a + k * (b - a)), z0 + (z1 - z0) * build.ease(k), cx, cy)
    return None


def mg4(fi):
    p = os.path.join(WORK, "mg4", f"f{fi:05d}.png")
    if not os.path.exists(p):
        return None
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if im.shape[2] == 3:
        im = np.dstack([im, np.full(im.shape[:2], 255, np.uint8)])
    a = im[..., 3:].astype(np.float32) / 255
    return (im[..., 2::-1].astype(np.float32) / 255, a) if a.max() > 0.004 else None


build.LEAKS = [(34.60, 0.8, 0.25), (74.30, 1.0, 0.35), (89.0, 1.1, 0.35)]   # flash in and out of the new section


def new_frame(fi):
    t = fi / FPS
    full = any(a <= t < b for a, b in MG_FULL)
    if full:
        x = np.empty((H, W, 3), np.float32)
        x[:] = build.PAPER
    else:
        x = soon_shot(t)[..., ::-1].astype(np.float32) / 255
        x = look.grade(x, 0.35 if v4.POW[0] <= t < v4.POW[1] else 1.0)   # BigOHealth's own clip keeps its look
    ml = mg4(fi)
    if ml is not None:
        rgb, a = ml
        if full:
            rgb = look.grade(rgb, 0.10)
        x = x * (1 - a) + rgb * a
    if v4.SOON[0] <= t < v4.SOON[1] or v4.POW[0] <= t < v4.POW[1]:
        lk = build.leak(t, fi)
        if lk is not None:
            x = 1 - (1 - x) * (1 - np.clip(lk * 0.85, 0, 1))
    x = look.finish(x, fi, hal=0.5 if full else 1.0, vig=0.6 if full else 1.0)
    return (np.clip(x, 0, 1)[..., ::-1] * 255 + 0.5).astype(np.uint8)


# ---------------------------------------------------------------- subtitles
PHRASES = [
    "In cancer care, every appointment brings questions.", "Every report holds information.", "And every detail matters.",
    "But a patient's journey rarely lives in one place.", "Blood reports on the phone.", "Scans in hospital portals.",
    "Pathology reports in emails.", "Prescriptions and PDFs inside physical folders.", "Different records. Different places.",
    "And they rarely speak to each other.", "That's why we created OncoXpress", "under the leadership of Dr. Shyam Aggarwal",
    "and Dr. Aditya Sarin,", "powered by BigOHealth,", "to bring your entire cancer-care journey", "in one secure place.",
    "Upload your medical records exactly as they are.", "No renaming. No sorting. No complicated folders.",
    "OncoXpress identifies, categorizes and organizes", "all your reports into one clear, chronological timeline.",
    "It tracks tumour marker trends, vital signs,", "treatment history, scans, pathology, and key biomarkers,",
    "giving you a complete picture of your cancer journey,", "all in one place.",
    "With OncoXpress, patients spend less time", "searching for documents,", "while doctors understand years of medical history",
    "in under 60 seconds.",
    # the end card ("OncoXpress, powered by BigOHealth. Faster Care. Trusted Care.") is typeset on screen
]
SOON_PHRASES = ["And this is just the beginning.", "Coming soon, OncoXpress will bring even more",
                "of the cancer-care journey together,", "including diet and nutrition,", "emotional well-being, and diagnostics,",
                "all within the same platform."]
QUIET = [(34.4, 36.1), (61.2, 65.6), (86.4, 99.0)]   # the same words are already typeset on screen there


def subtitle_cues():
    old = json.load(open(os.path.join(WORK, "words.json")))
    def ws(t):   # a word timestamped in the last breath before the inserted pause belongs after it
        return v4.PAUSE_AT if v4.PAUSE_AT - 0.15 <= t < v4.PAUSE_AT else t
    times = [(v4.warp(ws(w["s"] + 1.0)), v4.warp(w["e"] + 1.0)) for w in old]
    cues, k = [], 0
    for ph in PHRASES:
        n = len(ph.split())
        cues.append([ph, times[k][0], times[k + n - 1][1]])
        k += n
    soon = json.load(open(os.path.join(WORK, "words_soon.json")))
    k = 0
    for ph in SOON_PHRASES:
        n = len(ph.split())
        cues.append([ph, soon[k]["s"] + v4.SOON_AT, soon[k + n - 1]["e"] + v4.SOON_AT])
        k += n
    # the two names were re-ordered in the voice (v4.py): retime those two cues to the new audio
    for c in cues:
        if c[0] == "under the leadership of Dr. Shyam Aggarwal":
            c[2] = v4.SHYAM_AT + (v4.SHYAM_1 - v4.SHYAM_0) - 0.08
        elif c[0] == "and Dr. Aditya Sarin,":
            c[1], c[2] = v4.AND_AT, v4.ADITYA_AT + v4.SNIP_LEN
    for i, c in enumerate(cues):            # start a touch early, hold a touch long, never overlap
        c[1] -= 0.08
        nxt = cues[i + 1][1] - 0.08 if i + 1 < len(cues) else c[2] + 1
        c[2] = min(c[2] + 0.35, nxt - 0.04)
    return [c for c in cues if not any(a <= (c[1] + c[2]) / 2 < b for a, b in QUIET)]


FONT = ImageFont.truetype(os.path.join(HERE, "fonts", "Lexend[wght].ttf"), 36)
try:
    FONT.set_variation_by_axes([500])
except Exception:
    pass


def render_cue(text):
    """White text, soft shadow, on a translucent plum pill so it reads on footage and on the light graphics."""
    l, tp, r, b = FONT.getbbox(text)
    tw, th = r - l, b - tp
    pw, ph = tw + 50, th + 26
    im = Image.new("RGBA", (pw + 80, ph + 80), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([40, 46, 40 + pw, 46 + ph], 16, fill=(10, 6, 24, 90))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([40, 40, 40 + pw, 40 + ph], 16, fill=(24, 14, 46, 120))
    tx, ty = 40 + 25 - l, 40 + 13 - tp
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).text((tx, ty + 2), text, font=FONT, fill=(0, 0, 0, 160))
    im = Image.alpha_composite(im, glow.filter(ImageFilter.GaussianBlur(3)))
    ImageDraw.Draw(im).text((tx, ty), text, font=FONT, fill=(255, 255, 255, 255))
    a = np.asarray(im).astype(np.float32) / 255
    return a[..., 2::-1].copy(), a[..., 3:].copy()


CUES = subtitle_cues()
_cue_img = {}


def add_subtitle(fr, t):
    for text, a, b in CUES:
        if a <= t < b:
            if text not in _cue_img:
                _cue_img[text] = render_cue(text)
            rgb, al = _cue_img[text]
            f = min(1.0, (t - a) / 0.12, (b - t) / 0.12)
            h, w = al.shape[:2]
            x0, y0 = (W - w) // 2, H - 30 - h + 40
            h = min(h, H - y0)                      # the soft shadow may hang past the frame edge
            sub = fr[y0:y0 + h, x0:x0 + w].astype(np.float32) / 255
            al2 = al[:h] * f
            fr[y0:y0 + h, x0:x0 + w] = ((sub * (1 - al2) + rgb[:h] * al2) * 255 + 0.5).astype(np.uint8)
            break
    return fr


def frame(fi, reader):
    t = fi / FPS
    src = v4.old_frame_of(fi)
    if src is None:
        fr = new_frame(fi)
    else:
        idx, crop = src
        fr = reader.get(idx).copy()
        if crop:
            fr = crop_preview(fr, t)
    return add_subtitle(fr, t)


if __name__ == "__main__":
    args = sys.argv[1:]
    reader = OldReader()
    if "--stills" in args:
        ts = sorted(float(v) for v in args[args.index("--stills") + 1].split(","))
        os.makedirs(os.path.join(WORK, "stills"), exist_ok=True)
        for tt in ts:
            cv2.imwrite(os.path.join(WORK, "stills", f"v4_{tt:05.2f}.jpg"), frame(int(round(tt * FPS)), reader),
                        [cv2.IMWRITE_JPEG_QUALITY, 92])
        sys.exit(0)
    if "--cues" in args:
        for c in CUES:
            print(f"{c[1]:6.2f}-{c[2]:6.2f}  {c[0]}")
        sys.exit(0)
    od = os.path.join(WORK, "frames4")
    os.makedirs(od, exist_ok=True)
    for fi in range(v4.NF):
        cv2.imwrite(os.path.join(od, f"f{fi:05d}.png"), frame(fi, reader), [cv2.IMWRITE_PNG_COMPRESSION, 1])
        if fi % 120 == 0:
            print("frame", fi, flush=True)
