"""Shared constants, the edit decision list (EDL), word timings and easing helpers."""

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

W, H, FPS = 1920, 1080, 30
SW, SH = 824, 464            # source after a 4px side crop (832x464 -> ~16:9)
S0 = W / SW                  # source px -> output px at zoom 1
FACE = (412.0, 150.0)        # face centre in source px
HAND = (195.0, 318.0)        # open palm (top surface) in source px, at ~7s

# ------------------------------------------------------------------ EDL
# (src_start, src_end, base_zoom). Silences are trimmed, but pauses where an effect needs room to play stay.
SEGS = [
    (0.40, 6.15, 1.00),    # hook, "watch this", "zoom in on my hand"
    (6.50, 9.62, 1.00),    # "now put my logo right here, in 3D"
    (10.02, 13.85, 1.00),  # "nice" + "make me grab the logo and throw it"
    (13.95, 16.05, 1.00),  # "straight at the camera" + glass crack hold
    (16.62, 18.33, 1.08),  # "okay, harder one" (punch-in)
    (18.33, 23.85, 1.00),  # layers
    (24.35, 27.05, 1.00),  # "now remove me" + empty room
    (27.72, 29.20, 1.00),  # "bring me back"
    (33.55, 45.00, 1.00),  # frame on the right + anatomy of a viral reel
    (47.00, 48.65, 1.00),  # "back to the full screen"
    (49.92, 55.05, 1.00),  # floating videos + "perfect"
    (56.75, 57.95, 1.10),  # "last one"
    (62.55, 74.85, 1.00),  # cinematic documentary
    (76.48, 79.95, 1.07),  # "all of this was edited with AI"
    (80.45, 83.60, 1.00),  # CTA
]
OFFS = np.cumsum([0] + [e - s for s, e, _ in SEGS])
DUR = float(OFFS[-1])          # "edit time": the cut, before the global speed-up
SPEED = 1.10                   # whole edit plays 10% faster (voice time-stretched, pitch kept)
OUT_DUR = DUR / SPEED          # final running time
NFRAMES = int(round(OUT_DUR * FPS))


def ot(t_edit):
    """edit time -> final (output) time"""
    return t_edit / SPEED


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


def cut_points():
    return [float(o) for o in OFFS[1:-1]]


# ------------------------------------------------------------------ words
_W = json.load(open(os.path.join(WORK, "words.json")))
WORDS = []
for w in _W:
    WORDS.append(dict(w=w["w"], s=out_of_src(w["s"]), e=out_of_src(w["e"]), ss=w["s"], se=w["e"]))


def wt(text, after=0.0, end=False):
    """Output time of the first word matching `text` whose SOURCE start is >= `after`."""
    key = text.lower().strip(".,!?")
    for w in WORDS:
        if w["ss"] >= after - 1e-6 and w["w"].lower().strip(".,!?'\"") == key:
            return w["e"] if end else w["s"]
    raise KeyError((text, after))


# ------------------------------------------------------------------ easing
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


def window(t, t0, t1, fi=0.2, fo=0.2):
    """0..1 envelope: fade in at t0, out at t1."""
    return min(prog(t, t0, fi), 1 - prog(t, t1 - fo, fo))
