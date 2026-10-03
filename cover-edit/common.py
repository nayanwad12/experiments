"""Shared constants, edit decision list, word timings and easing for the "boring to editorial cover" edit."""

import json
import math
import os

import imageio_ffmpeg
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
OUT = os.path.join(HERE, "out")
FONTS = os.path.join(HERE, "fonts")
RAW = os.path.join(HERE, "raw", "raw.mp4")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

W, H, FPS = 1080, 1920, 30
SW, SH = 720, 1280               # decoded source (vertical)
S0 = W / SW

# (src_start, src_end, base_zoom): dead air removed, short holds kept where a style needs a beat to land
SEGS = [
    (0.50, 4.85, 1.00),     # boring: "hi, this is a normal video..."
    (5.05, 9.62, 1.00),     # "okay Claude, cut the pauses. see? faster already"
    (9.86, 13.05, 1.06),    # captions + pop
    (13.42, 17.52, 1.00),   # caption styles x3
    (18.40, 22.95, 1.00),   # cut me out + magazine cover
    (23.12, 27.20, 1.00),   # notes around me
    (27.75, 32.45, 1.00),   # frames + best clips
    (32.78, 36.42, 1.00),   # music + sound effects
    (36.68, 40.60, 1.00),   # paper cut + move
    (41.22, 46.75, 1.00),   # no premiere ... just Claude
    (46.78, 51.45, 1.00),   # from boring to this + CTA
]
OFFS = np.cumsum([0] + [e - s for s, e, _ in SEGS])
DUR = float(OFFS[-1])            # edit time
SPEED = 1.05                     # plays 5% faster, voice time-stretched with pitch kept
OUT_DUR = DUR / SPEED
NFRAMES = int(round(OUT_DUR * FPS))


def ot(t):
    return t / SPEED


def seg_of_out(t):
    i = int(np.searchsorted(OFFS, t, side="right") - 1)
    return min(max(i, 0), len(SEGS) - 1)


def src_of_out(t):
    i = seg_of_out(t)
    return SEGS[i][0] + (t - OFFS[i]), i


def out_of_src(s):
    for i, (a, b, _) in enumerate(SEGS):
        if a - 1e-6 <= s <= b + 1e-6:
            return float(OFFS[i] + (s - a))
    best = min(range(len(SEGS)), key=lambda i: min(abs(s - SEGS[i][0]), abs(s - SEGS[i][1])))
    a, b, _ = SEGS[best]
    return float(OFFS[best] + (min(max(s, a), b) - a))


_W = json.load(open(os.path.join(WORK, "words.json")))
WORDS = [dict(w=w["w"], s=out_of_src(w["s"]), e=out_of_src(w["e"]), ss=w["s"], se=w["e"]) for w in _W]


def wt(text, after=0.0, end=False):
    key = text.lower().strip(".,!?")
    for w in WORDS:
        if w["ss"] >= after - 1e-6 and w["w"].lower().strip(".,!?'\"") == key:
            return w["e"] if end else w["s"]
    raise KeyError((text, after))


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def prog(t, t0, d):
    return clamp((t - t0) / d) if d > 0 else float(t >= t0)


def lerp(a, b, k):
    return a + (b - a) * k


def eio(k):
    k = clamp(k)
    return 4 * k ** 3 if k < 0.5 else 1 - (-2 * k + 2) ** 3 / 2


def eo(k):
    k = clamp(k)
    return 1 - (1 - k) ** 3


def ei(k):
    k = clamp(k)
    return k ** 3


def eob(k, s=1.70158):
    k = clamp(k) - 1
    return 1 + (s + 1) * k ** 3 + s * k ** 2


def spring(k, f=3.2, d=5.0):
    k = max(k, 0.0)
    return 1 - math.exp(-d * k) * math.cos(f * math.pi * k)
