# Vibe Editing reel renderer: scenes, captions, motion graphics, camera.
import numpy as np, json, cv2, math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont

cv2.setNumThreads(1)
ROOT = os.path.dirname(os.path.abspath(__file__)) + "/.."
W, H, FPS = 1080, 1920, 30
FD = ROOT + "/fonts/"
E = json.load(open(ROOT + "/work/edl.json"))
SEGS, WORDS, DUR = E["segs"], E["words"], E["dur"]
END0 = 66.62
TOTAL = 69.90
NF = int(round(TOTAL * FPS))
SRC = np.load(ROOT + "/work/src30.npy", mmap_mode="r")
ALPHA = np.load(ROOT + "/work/alpha.npy", mmap_mode="r")
HEAD = np.load(ROOT + "/work/head.npy")

# ---------------------------------------------------------------- palette
PAPER = (236, 232, 225); PAPER2 = (233, 231, 227); INK = (17, 17, 17)
GREEN = (30, 91, 53); GREEN_D = (19, 58, 34); CREAM = (246, 241, 232)
ORANGE = (201, 87, 58); ORANGE_L = (240, 132, 92); GOLD = (244, 220, 170)
WOOD = (122, 88, 58); WOOD_D = (74, 52, 35); MUTE = (118, 112, 104)
LGREEN = (110, 196, 134)
PAL = {
    "paper": dict(i=INK, a=GREEN, b=ORANGE, m=INK),
    "paper2": dict(i=INK, a=GREEN, b=ORANGE, m=INK),
    "grid": dict(i=INK, a=GREEN, b=ORANGE, m=INK),
    "green": dict(i=CREAM, a=GOLD, b=ORANGE_L, m=CREAM),
    "dark": dict(i=CREAM, a=LGREEN, b=ORANGE_L, m=CREAM),
    "black": dict(i=CREAM, a=LGREEN, b=ORANGE_L, m=CREAM),
    "orange": dict(i=CREAM, a=INK, b=INK, m=INK),
}

def f3(c): return np.array(c, np.float32) / 255.0

# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def eoc(p): p = clamp(p); return 1 - (1 - p) ** 3
def eic(p): p = clamp(p); return p ** 3
def eio(p): p = clamp(p); return 4 * p ** 3 if p < .5 else 1 - (-2 * p + 2) ** 3 / 2
def eob(p, s=1.9):
    p = clamp(p); return 1 + (s + 1) * (p - 1) ** 3 + s * (p - 1) ** 2

# ---------------------------------------------------------------- fonts / text
FONTS = {"black": ("InterTight%5Bwght%5D.ttf", 900), "xbold": ("InterTight%5Bwght%5D.ttf", 800),
         "bold": ("InterTight%5Bwght%5D.ttf", 700), "semi": ("InterTight%5Bwght%5D.ttf", 600),
         "serif": ("DMSerifDisplay-Regular.ttf", None), "serifi": ("InstrumentSerif-Italic.ttf", None),
         "mono": ("JetBrainsMono%5Bwght%5D.ttf", 700), "monor": ("JetBrainsMono%5Bwght%5D.ttf", 500),
         "monox": ("JetBrainsMono%5Bwght%5D.ttf", 800)}

@lru_cache(None)
def font(key, size):
    fn, wg = FONTS[key]
    f = ImageFont.truetype(FD + fn, int(size))
    if wg: f.set_variation_by_axes([wg])
    return f

def to_np(im): return np.asarray(im, dtype=np.float32) / 255.0

def paste(cv, im, x, y, op=1.0):
    if op <= 0.003: return
    if isinstance(im, Image.Image): im = to_np(im)
    h, w = im.shape[:2]; x = int(round(x)); y = int(round(y))
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0: return
    s = im[y0 - y:y1 - y, x0 - x:x1 - x]
    a = s[..., 3:4] * op
    cv[y0:y1, x0:x1] = cv[y0:y1, x0:x1] * (1 - a) + s[..., :3] * a

def paste_c(cv, im, cx, cy, scale=1.0, op=1.0, rot=0.0):
    """Paste PIL RGBA centred at (cx,cy) with scale/rotation."""
    if scale <= 0.01 or op <= 0.003: return
    if rot: im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if abs(scale - 1) > 0.004:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    paste(cv, im, cx - im.width / 2, cy - im.height / 2, op)

@lru_cache(4096)
def word_img(text, fk, size, color):
    f = font(fk, size)
    l, t, r, b = f.getbbox(text, anchor="ls")
    pad = int(size * 0.12) + 4
    im = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=f, fill=tuple(color) + (255,), anchor="ls")
    return im, pad - l, pad - t   # baseline origin inside image

def text_img(text, fk, size, color, track=0):
    """Tight RGBA of a text run (optional letter tracking)."""
    f = font(fk, size)
    if not track:
        return word_img(text, fk, size, tuple(color))[0]
    w = int(sum(f.getlength(c) + track for c in text)) + 20
    l, t, r, b = f.getbbox("Hg", anchor="ls")
    im = Image.new("RGBA", (w, b - t + 12), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = 6
    for c in text:
        d.text((x, 6 - t), c, font=f, fill=tuple(color) + (255,), anchor="ls"); x += f.getlength(c) + track
    return im

def ss(w, h):  # 2x supersampled canvas
    im = Image.new("RGBA", (int(w * 2), int(h * 2)), (0, 0, 0, 0)); return im, ImageDraw.Draw(im)
def down(im): return im.resize((im.width // 2, im.height // 2), Image.LANCZOS)

def card(w, h, fill=CREAM, border=INK, bw=3, r=22, shadow=INK, sh=9, op=255):
    im, d = ss(w + sh, h + sh)
    if sh: d.rounded_rectangle([sh * 2, sh * 2, (w + sh) * 2 - 1, (h + sh) * 2 - 1], r * 2, fill=tuple(shadow) + (op,))
    d.rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 1], r * 2, fill=tuple(fill) + (op,),
                        outline=tuple(border) + (255,) if border else None, width=bw * 2)
    return im, d

# ---------------------------------------------------------------- icons (drawn at 2x on a draw ctx)
def icon(d, name, x, y, s, col, bg=None, lw=None):
    """Draw icon in box (x,y,s,s) - coordinates already in 2x space."""
    c = tuple(col) + (255,); lw = lw or max(2, int(s * 0.075))
    P = lambda u, v: (x + u * s, y + v * s)
    if name == "check":
        d.line([P(.18, .55), P(.42, .77), P(.84, .27)], fill=c, width=int(s * .14), joint="curve")
    elif name == "x":
        d.line([P(.2, .2), P(.8, .8)], fill=c, width=int(s * .14)); d.line([P(.8, .2), P(.2, .8)], fill=c, width=int(s * .14))
    elif name == "camera":
        d.rounded_rectangle([P(.08, .3), P(.92, .85)], int(s * .1), outline=c, width=lw)
        d.rectangle([P(.33, .18), P(.62, .3)], fill=c)
        d.ellipse([P(.32, .38), P(.68, .74)], outline=c, width=lw)
    elif name == "laptop":
        d.rounded_rectangle([P(.16, .2), P(.84, .68)], int(s * .05), outline=c, width=lw)
        d.polygon([P(.04, .74), P(.96, .74), P(.88, .84), P(.12, .84)], fill=c)
    elif name == "phone":
        d.rounded_rectangle([P(.26, .05), P(.74, .95)], int(s * .1), outline=c, width=lw)
        d.rounded_rectangle([P(.42, .1), P(.58, .15)], int(s * .02), fill=c)
        d.line([P(.4, .88), P(.6, .88)], fill=c, width=lw)
    elif name == "sparkle":
        pts = []
        for k in range(8):
            a = k * math.pi / 4; rr = .46 if k % 2 == 0 else .13
            pts.append(P(.5 + rr * math.sin(a), .5 - rr * math.cos(a)))
        d.polygon(pts, fill=c)
    elif name == "play":
        d.ellipse([P(.05, .05), P(.95, .95)], outline=c, width=lw)
        d.polygon([P(.4, .3), P(.4, .7), P(.72, .5)], fill=c)
    elif name == "reel":
        d.rounded_rectangle([P(.25, .04), P(.75, .96)], int(s * .08), outline=c, width=lw)
        d.polygon([P(.43, .38), P(.43, .62), P(.62, .5)], fill=c)
    elif name == "shapes":
        d.ellipse([P(.05, .1), P(.45, .5)], fill=c)
        d.polygon([P(.55, .5), P(.95, .5), P(.75, .12)], outline=c, width=lw)
        d.rectangle([P(.3, .58), P(.7, .92)], outline=c, width=lw)
    elif name == "bottle":
        d.rounded_rectangle([P(.28, .35), P(.72, .95)], int(s * .1), outline=c, width=lw)
        d.rectangle([P(.4, .12), P(.6, .35)], outline=c, width=lw)
        d.rectangle([P(.36, .04), P(.64, .13)], fill=c)
        d.line([P(.34, .6), P(.66, .6)], fill=c, width=lw)
    elif name == "blob":
        pts = [P(.5 + .38 * math.cos(a) * (1 + .12 * math.sin(3 * a)), .52 + .36 * math.sin(a) * (1 + .1 * math.cos(2 * a)))
               for a in np.linspace(0, 2 * math.pi, 40)]
        d.polygon(pts, fill=c)
        if bg: d.ellipse([P(.35, .38), P(.45, .5)], fill=tuple(bg) + (255,)); d.ellipse([P(.55, .38), P(.65, .5)], fill=tuple(bg) + (255,))
    elif name == "burst":
        for k in range(8):
            a = k * math.pi / 4; r0, r1 = (.14, .46) if k % 2 == 0 else (.18, .32)
            d.line([P(.5 + r0 * math.cos(a), .5 + r0 * math.sin(a)), P(.5 + r1 * math.cos(a), .5 + r1 * math.sin(a))], fill=c, width=lw)
    elif name == "mic":
        d.rounded_rectangle([P(.36, .05), P(.64, .6)], int(s * .14), fill=c)
        d.arc([P(.22, .3), P(.78, .74)], 0, 180, fill=c, width=lw)
        d.line([P(.5, .74), P(.5, .92)], fill=c, width=lw); d.line([P(.32, .93), P(.68, .93)], fill=c, width=lw)
    elif name == "cursor":
        d.polygon([P(.1, .05), P(.1, .82), P(.32, .62), P(.48, .95), P(.6, .9), P(.45, .58), P(.75, .58)], fill=c,
                  outline=tuple(bg or CREAM) + (255,))
    elif name == "music":
        d.line([P(.38, .78), P(.38, .15), P(.82, .06), P(.82, .68)], fill=c, width=lw)
        d.ellipse([P(.14, .66), P(.42, .9)], fill=c); d.ellipse([P(.58, .58), P(.86, .8)], fill=c)
    elif name == "text":
        d.line([P(.15, .2), P(.85, .2)], fill=c, width=int(lw * 1.6)); d.line([P(.5, .2), P(.5, .85)], fill=c, width=int(lw * 1.6))
    elif name == "scissors":
        d.ellipse([P(.08, .58), P(.4, .9)], outline=c, width=lw); d.ellipse([P(.6, .58), P(.92, .9)], outline=c, width=lw)
        d.line([P(.33, .62), P(.75, .08)], fill=c, width=lw); d.line([P(.67, .62), P(.25, .08)], fill=c, width=lw)
    elif name == "film":
        d.rectangle([P(.08, .18), P(.92, .82)], outline=c, width=lw)
        d.line([P(.08, .5), P(.92, .5)], fill=c, width=lw)

def icon_img(name, s, col, bg=None):
    im, d = ss(s, s); icon(d, name, 0, 0, s * 2, col, bg); return down(im)

# ---------------------------------------------------------------- backgrounds (static, cached)
rng0 = np.random.default_rng(7)
_paper_noise = cv2.GaussianBlur(rng0.normal(0, 1, (H // 2, W // 2)).astype(np.float32), (0, 0), 0.8)
_paper_noise = cv2.resize(_paper_noise, (W, H))[..., None]
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)

def radial(cx, cy, r): return np.clip(1 - np.sqrt((XX - cx) ** 2 + (YY - cy) ** 2) / r, 0, 1)[..., None]

@lru_cache(None)
def bg_static(kind):
    if kind in ("paper", "grid", "paper2"):
        base = f3(PAPER if kind != "paper2" else PAPER2)
        im = np.ones((H, W, 3), np.float32) * base
        im *= 0.93 + 0.09 * radial(540, 760, 1500) ** 1.3
        im *= 1 - 0.06 * np.clip((YY[..., None] - 1300) / 620, 0, 1)
        im += _paper_noise * 0.012
        if kind == "grid":
            g = np.zeros((H, W), np.float32)
            for yy in range(20, H, 44):
                for xx in range(20, W, 44): cv2.circle(g, (xx, yy), 2, 1.0, -1, cv2.LINE_AA)
            im = im * (1 - 0.13 * g[..., None])
    elif kind == "green":
        im = np.ones((H, W, 3), np.float32) * f3(GREEN_D)
        im = im + (f3((40, 112, 68)) - f3(GREEN_D)) * radial(540, 820, 1350) ** 1.2
        im += _paper_noise * 0.012
    elif kind in ("dark", "black"):
        im = np.ones((H, W, 3), np.float32) * f3((16, 16, 15) if kind == "dark" else (10, 10, 10))
        if kind == "dark":
            gl = np.zeros((H, W), np.float32)
            for v in range(0, W, 60): gl[:, v] = 1
            for v in range(0, H, 60): gl[v, :] = 1
            im += gl[..., None] * 0.035
            im += f3((30, 91, 53)) * 0.55 * radial(540, 760, 900) ** 2
        else:
            im += f3((201, 87, 58)) * 0.22 * radial(540, 900, 1000) ** 2.2
        im += _paper_noise * 0.01
    elif kind == "orange":
        im = np.ones((H, W, 3), np.float32) * f3((176, 70, 44))
        im = im + (f3((214, 100, 66)) - f3((176, 70, 44))) * radial(540, 820, 1300) ** 1.1
        g = np.zeros((H, W), np.float32)   # halftone dots fading downward
        for yy in range(14, H, 28):
            for xx in range(14, W, 28):
                rr = 5.5 * clamp(1 - yy / 1150)
                if rr > .6: cv2.circle(g, (xx, yy), int(rr + .5), 1.0, -1, cv2.LINE_AA)
        im = im * (1 - 0.10 * g[..., None])
        im += _paper_noise * 0.012
    return np.clip(im, 0, 1).astype(np.float32)

VIGN = (1 - 0.20 * np.clip(np.sqrt(((XX - 540) / 760) ** 2 + ((YY - 900) / 1150) ** 2), 0, 1.4) ** 2.4)[..., None].astype(np.float32)
_g = np.random.default_rng(3)
GRAIN = [cv2.resize(_g.normal(0, 1, (H // 2, W // 2)).astype(np.float32), (W, H), interpolation=cv2.INTER_NEAREST)[..., None] for _ in range(6)]

# ---------------------------------------------------------------- footage
def src_time(t):
    for a, b, o in SEGS:
        if t < o + (b - a): return a + max(0.0, t - o)
    a, b, o = SEGS[-1]; return min(b + (t - (o + b - a)), 82.0)
def src_idx(t): return min(int(round(src_time(t) * 30)), SRC.shape[0] - 1)

def _lut():
    wall = SRC[::40, 60:420, 30:200].reshape(-1, 3).mean(0)
    tgt = np.array([214, 210, 203], np.float32)
    gain = tgt / wall
    x = np.arange(256, dtype=np.float32) / 255
    lut = np.zeros((256, 1, 3), np.uint8)
    for c in range(3):
        y = np.clip(x * gain[c], 0, 1.2)
        y = y / (1 + 0.18 * np.maximum(y - 0.75, 0) * 4)          # soft highlight roll-off
        s = 1 / (1 + np.exp(-6.5 * (y - 0.5))); s = (s - s.min()) / (s.max() - s.min())
        y = 0.62 * y + 0.38 * s                                   # gentle S-curve
        y = 0.022 + 0.968 * np.clip(y, 0, 1)                      # lifted blacks, filmic
        lut[:, 0, c] = np.clip(y * 255 + .5, 0, 255).astype(np.uint8)
    return lut
LUT = _lut()

@lru_cache(64)
def graded(i):
    f = cv2.LUT(np.ascontiguousarray(SRC[i]), LUT).astype(np.float32) / 255
    l = (f @ np.array([.299, .587, .114], np.float32))[..., None]
    f = l + (f - l) * 1.07
    f[..., 0] *= 1.01; f[..., 2] *= 0.985
    bl = cv2.GaussianBlur(f, (0, 0), 1.3)
    f = f + (f - bl) * 0.55                                       # sharpen before upscale
    return np.clip(f, 0, 1)

def head(i):
    top, cx = HEAD[min(i, len(HEAD) - 1)]
    return top, cx

# ---------------------------------------------------------------- spec: sections
SEC = [
    dict(n="hook", t0=0.0, t1=3.13, kind="cut", bg="paper", label="01 / THE SHIFT", zb=1.04, alt=1.12),
    dict(n="old", t0=3.13, t1=11.73, kind="tv", bg="paper2", label="02 / THE OLD WAY"),
    dict(n="turn", t0=11.73, t1=15.40, kind="cut", bg="green", label="03 / VIBE EDITING", zb=1.06, alt=1.15, pump=1),
    dict(n="direct", t0=15.40, t1=20.40, kind="cut", bg="grid", label="04 / YOU DIRECT", zb=1.0, alt=1.09, pump=1),
    dict(n="brief", t0=20.40, t1=29.10, kind="cut", bg="paper", label="04 / THE BRIEF", zb=1.0, alt=1.08, pump=1),
    dict(n="code", t0=29.10, t1=34.87, kind="cut", bg="dark", label="05 / MADE IN CODE", zb=1.02, alt=1.10, pump=1),
    dict(n="formats", t0=34.87, t1=45.53, kind="cut", bg="orange", label="06 / NOT JUST REELS", zb=1.0, alt=1.08, pump=1),
    dict(n="need", t0=45.53, t1=50.40, kind="cut", bg="paper", label="07 / WHAT YOU NEED", zb=1.03, alt=1.10, pump=1),
    dict(n="system", t0=50.40, t1=56.20, kind="cut", bg="green", label="07 / THE SYSTEM", zb=1.0, alt=1.08, pump=1),
    dict(n="no", t0=56.20, t1=59.07, kind="cut", bg="black", label="08 / NO SOFTWARE", zb=1.08, alt=1.16),
    dict(n="proof", t0=59.07, t1=END0, kind="tv", bg="paper2", label="09 / PROOF"),
    dict(n="end", t0=END0, t1=TOTAL, kind="end", bg="green", label=""),
]
TRANS = {1: ("glitch", 3), 2: ("flip", 5), 3: ("whip", 4), 4: ("push", 4), 5: ("glitch", 3), 6: ("whip", 4),
         7: ("iris", 6), 8: ("push", 4), 9: ("flash", 2), 10: ("glitch", 2), 11: ("push", 5)}

def sec_at(t):
    for i, s in enumerate(SEC):
        if t < s["t1"]: return i
    return len(SEC) - 1

# ---------------------------------------------------------------- spec: caption pages
DISP = {77: "music", 109: "CLAYMATION", 31: "60-SECOND", 53: "you", 32: "reel."}
PAGES_RAW = [
    (0, [("L", [0]), ("L", [1]), ("S", [2, (3, "!z#")], "a")]),
    (0, [("M", [4, 5, 6]), ("L", [7, (8, "a!#")]), ("S", [9], "a")]),
    (1, [("I", [10, 11]), ("M", [12, 13]), ("L", [14, (15, "!")], "a")]),
    (1, [("M", [16, 17, 18, 19]), ("L", [(20, "!")])]),
    (1, [("L", [21, 22]), ("S", [23, 24], "a")]),
    (1, [("M", [25, 26]), ("L", [(27, "!"), 28], "b")]),
    (1, [("M", [29, 30]), ("L", [31]), ("S", [32], "a")]),
    (2, [("L", [(33, "!z#")]), ("L", [34]), ("S", [(35, "f"), 36], "b")]),
    (2, [("M", [37, 38]), ("L", [(39, "x")]), ("I", [40], "b")]),
    (2, [("M", [41]), ("L", [(42, "!z#")], "b")]),
    (3, [("M", [43, 44, 45, 46]), ("M", [47, 48]), ("L", [(49, "!")], "a")]),
    (3, [("M", [50, 51, 52, 53, 54]), ("L", [(55, "!")])]),
    (3, [("M", [56, 57]), ("L", [(58, "!z")], "a")]),
    (4, [("M", [59, 60]), ("L", [(61, "!")])]),
    (4, [("M", [62, 63, 64]), ("L", [(65, "!")], "b")]),
    (4, [("M", [66, 67]), ("L", [(68, "!z")]), ("S", [69, 70], "a")]),
    (4, [("M", [71, 72, 73]), ("L", [74]), ("S", [75], "a")]),
    (4, [("M", [76, 77, 78]), ("L", [79], "a")]),
    (4, [("M", [80, 81]), ("L", [(82, "!z#"), 83])]),
    (5, [("M", [84]), ("L", [(85, "!")])]),
    (5, [("M", [86]), ("L", [(87, "!")])]),
    (5, [("M", [88]), ("L", [(89, "!")])]),
    (5, [("M", [90, 91]), ("X", [(92, "!z")], "a")]),
    (5, [("M", [93, 94, 95]), ("L", [96])]),
    (6, [("M", [97, 98, 99], "m"), ("L", [(100, "!z")])]),
    (6, [("M", [101, 102], "m"), ("L", [103]), ("S", [104], "a")]),
    (6, [("L", [(105, "!")]), ("S", [106], "a")]),
    (6, [("L", [(107, "!")]), ("S", [108], "a")]),
    (6, [("L", [(109, "!")])]),
    (6, [("L", [(110, "!")])]),
    (6, [("L", [(111, "!")]), ("S", [112], "a")]),
    (6, [("M", [113], "m"), ("L", [(114, "!z"), 115]), ("S", [116, 117, 118], "a")]),
    (6, [("M", [119, 120, 121], "m"), ("L", [(122, "!")]), ("S", [123, 124], "a")]),
    (7, [("M", [125, 126, 127, 128]), ("L", [(129, "!")]), ("S", [130], "a")]),
    (7, [("L", [131, (132, "!")]), ("S", [133, 134], "a")]),
    (7, [("M", [135, 136]), ("L", [137, (138, "!z")], "a"), ("S", [139])]),
    (8, [("M", [140, 141]), ("L", [(142, "!")])]),
    (8, [("M", [143, 144]), ("L", [145, (146, "!z")], "b")]),
    (8, [("M", [147, 148, 149, 150, 151]), ("L", [(152, "!")], "b"), ("S", [153, 154, 155, 156])]),
    (9, [("M", [157], "b"), ("L", [(158, "x"), (159, "!x#")])]),
    (9, [("M", [160], "b"), ("L", [(161, "x"), (162, "!x#")])]),
    (9, [("M", [163], "b"), ("L", [(164, "!x#z")])]),
    (10, [("M", [165, 166, 167]), ("M", [168, 169]), ("L", [(170, "!")])]),
    (10, [("M", [171, 172, 173, 174]), ("L", [(175, "!")], "b"), ("S", [176, 177], "a")]),
    (10, [("M", [178, 179, 180, 181]), ("L", [(182, "!z")])]),
    (10, [("M", [183, 184, 185, 186]), ("L", [187, (188, "!")], "a")]),
]
STY = {"L": ("black", 190), "M": ("xbold", 70), "S": ("serif", 112), "I": ("serifi", 124), "X": ("monox", 170)}

def wtime(i): return WORDS[i][0] - 0.04

def disp(i, st):
    w = DISP.get(i, WORDS[i][2])
    if st in ("L", "X"):
        w = w.upper().rstrip(",.:")
    return w

PAGES = []
for si, lines in PAGES_RAW:
    L = []
    for ln in lines:
        st, ws = ln[0], ln[1]; col = ln[2] if len(ln) > 2 else ("i" if st in "LMX" else "a")
        L.append((st, [(w, "") if isinstance(w, int) else w for w in ws], col))
    t0 = min(wtime(w) for l in L for w, _ in l[1])
    PAGES.append(dict(sec=si, lines=L, t0=t0))
for k, p in enumerate(PAGES):
    nxt = PAGES[k + 1] if k + 1 < len(PAGES) and PAGES[k + 1]["sec"] == p["sec"] else None
    p["t1"] = nxt["t0"] if nxt else SEC[p["sec"]]["t1"] + 0.5

# ---------------------------------------------------------------- camera
def sec_events(si):
    s = SEC[si]; ev = []
    for a, b, o in SEGS:
        if s["t0"] + 0.05 < o < s["t1"] - 0.05: ev.append((o, "cut"))
    for p in PAGES:
        if p["sec"] != si: continue
        for st, ws, col in p["lines"]:
            for w, fx in ws:
                if "z" in fx: ev.append((wtime(w), "punch"))
    return sorted(ev)
EVS = [sec_events(i) for i in range(len(SEC))]
SHAKES, GLITCHES = [], []
for p in PAGES:
    for st, ws, col in p["lines"]:
        for w, fx in ws:
            if "!" in fx: SHAKES.append((wtime(w) + 0.03, 11 if "z" in fx else 7))
            if "#" in fx: GLITCHES.append((wtime(w) + 0.02, 0.13))
BEAT0, BEAT = 11.82 - 12.0, 0.5

def zoom_level(si, t):
    s = SEC[si]; zb, alt = s.get("zb", 1.0), s.get("alt", 1.08)
    lvl, prev, tch, wide = zb, zb, -9, True
    for te, kind in EVS[si]:
        if te > t: break
        prev = lvl
        if kind == "cut":
            wide = not wide; lvl = zb if wide else zb * alt; tch = -9   # hard snap on cut
        else:
            lvl = lvl * 1.07; tch = te
    if t - tch < 0.14: return prev + (lvl - prev) * eoc((t - tch) / 0.14)
    return lvl

def cam(si, t):
    s = SEC[si]
    z = zoom_level(si, t) * (1 + 0.010 * (t - s["t0"]))
    if s.get("pump") and t > 11.82:
        ph = (t - BEAT0) % BEAT; z *= 1 + 0.007 * math.exp(-ph / 0.07)
    return z

def shake(t):
    dx = dy = 0.0
    for ts, a in SHAKES:
        u = t - ts
        if 0 <= u < 0.35:
            e = a * math.exp(-u / 0.085)
            dx += e * math.sin(2 * math.pi * 23 * u + ts * 7); dy += e * math.cos(2 * math.pi * 17 * u + ts * 3)
    return dx, dy

def cut_M(si, t, i):
    top, cx = head(i)
    ax, ay = cx * 1.5, (top + 210) * 1.5
    z = cam(si, t); s = 1.5 * z
    return np.array([[s, 0, ax * (1 - z) + (540 - ax) * 0.35], [0, s, ay * (1 - z)]], np.float32), top, z

# TV geometry
TV_SCR = (128, 826, 952, 1252); TV_P = (540.0, 1040.0)
def tv_M(t, i, k=1.0):
    top, cx = head(i)
    fx, fy = cx, top + 210
    zl = 1.0 + 0.012 * (t - 3.13 if t < 20 else t - 59.07)
    si = sec_at(t) if sec_at(t) in (1, 10) else (1 if t < 20 else 10)
    zl *= zoom_level(si, t) if SEC[si].get("zb") else 1.0
    for te, kind in EVS[si]:
        pass
    # alternate tightness on internal cuts
    n = sum(1 for te, kd in EVS[si] if kd == "cut" and te <= t)
    zl *= 1.07 if n % 2 else 1.0
    s = 1.62 * zl
    tx, ty = 540 - s * fx, 1010 - s * fy
    # pose k around TV_P
    M = np.array([[s * k, 0, TV_P[0] + k * (tx - TV_P[0])], [0, s * k, TV_P[1] + k * (ty - TV_P[1])]], np.float32)
    return M, top, s * k

# ---------------------------------------------------------------- TV prop (static layers)
def build_tv():
    S2 = 2
    im = Image.new("RGBA", (W * S2, H * S2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    R = lambda *v: [x * S2 for x in v]
    # antenna
    for (x2, y2) in [(250, 452), (858, 412)]:
        d.line(R(540, 742, x2, y2), fill=(70, 70, 72, 255), width=9 * S2)
        d.line(R(540 - 1, 740, x2 - 1, y2), fill=(175, 175, 178, 255), width=3 * S2)
        d.ellipse(R(x2 - 9, y2 - 9, x2 + 9, y2 + 9), fill=(60, 60, 62, 255))
    d.rounded_rectangle(R(450, 716, 630, 768), 16 * S2, fill=(52, 50, 50, 255))
    d.rounded_rectangle(R(458, 720, 622, 732), 6 * S2, fill=(95, 93, 92, 255))
    # legs
    for x0 in (150, 850):
        d.polygon(R(x0, 1530, x0 + 80, 1530, x0 + 66, 1596, x0 + 14, 1596), fill=WOOD_D + (255,))
    # cabinet
    d.rounded_rectangle(R(46, 756, 1034, 1546), 44 * S2, fill=WOOD_D + (255,))
    d.rounded_rectangle(R(52, 760, 1028, 1538), 40 * S2, fill=WOOD + (255,))
    # bezel (orange) + screen hole
    d.rounded_rectangle(R(80, 790, 1000, 1290), 30 * S2, fill=(160, 64, 40, 255))
    d.rounded_rectangle(R(84, 792, 996, 1284), 28 * S2, fill=ORANGE + (255,))
    d.rounded_rectangle(R(118, 816, 962, 1262), 74 * S2, fill=(222, 214, 200, 255))      # chrome lip
    d.rounded_rectangle(R(TV_SCR[0], TV_SCR[1], TV_SCR[2], TV_SCR[3]), 66 * S2, fill=(0, 0, 0, 0))
    # control panel
    for x0 in (92, 788):
        d.rounded_rectangle(R(x0, 1304, x0 + 200, 1506), 18 * S2, fill=(160, 64, 40, 255))
        d.rounded_rectangle(R(x0 + 3, 1306, x0 + 197, 1502), 16 * S2, fill=ORANGE + (255,))
        cx, cy = x0 + 100, 1405
        d.ellipse(R(cx - 64, cy - 64, cx + 64, cy + 64), fill=(60, 58, 56, 255))
        d.ellipse(R(cx - 58, cy - 58, cx + 58, cy + 58), fill=(214, 210, 202, 255))
        for a in range(0, 360, 20):
            r0, r1 = 46, 56
            d.line(R(cx + r0 * math.cos(math.radians(a)), cy + r0 * math.sin(math.radians(a)),
                     cx + r1 * math.cos(math.radians(a)), cy + r1 * math.sin(math.radians(a))), fill=(150, 146, 140, 255), width=2 * S2)
        d.ellipse(R(cx - 38, cy - 38, cx + 38, cy + 38), fill=(236, 232, 226, 255))
        d.line(R(cx, cy, cx + 26, cy - 22), fill=INK + (255,), width=5 * S2)
    d.rounded_rectangle(R(310, 1318, 770, 1492), 16 * S2, fill=(38, 36, 34, 255))
    d.rounded_rectangle(R(326, 1332, 754, 1478), 10 * S2, fill=(18, 18, 17, 255))     # dial window / LED
    for k in range(9):
        y = 1338 + k * 16
        d.line(R(800 - 0, 0, 0, 0), fill=(0, 0, 0, 0))
    im = down(im)
    a = to_np(im)
    # wood grain texture on cabinet area
    gr = cv2.resize(np.random.default_rng(5).normal(0, 1, (H // 6, 8)).astype(np.float32), (W, H))
    gr = cv2.GaussianBlur(gr, (0, 0), 1.2)[..., None]
    wood = (np.abs(a[..., :3] - f3(WOOD)).sum(-1, keepdims=True) < 0.05).astype(np.float32)
    a[..., :3] *= 1 + 0.06 * gr * wood
    # top highlight / bottom shade on cabinet
    a[..., :3] *= (1 + 0.10 * np.clip(1 - (YY[..., None] - 760) / 120, 0, 1) * (YY[..., None] > 760))
    a[..., :3] *= (1 - 0.18 * np.clip((YY[..., None] - 1430) / 110, 0, 1))
    return np.clip(a, 0, 1).astype(np.float32)

def rr_mask(x0, y0, x1, y1, r):
    m = np.zeros((H, W), np.uint8)
    cv2.rectangle(m, (x0 + r, y0), (x1 - r, y1), 255, -1); cv2.rectangle(m, (x0, y0 + r), (x1, y1 - r), 255, -1)
    for cx, cy in [(x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)]:
        cv2.circle(m, (cx, cy), r, 255, -1, cv2.LINE_AA)
    return cv2.GaussianBlur(m, (0, 0), 0.8).astype(np.float32) / 255

TV = build_tv()
SCR_M = rr_mask(*TV_SCR, 66)
def build_glass():
    g = np.zeros((H, W, 4), np.float32)
    sl = ((YY.astype(int) % 4) < 1).astype(np.float32)
    x0, y0, x1, y1 = TV_SCR
    nx = (XX - (x0 + x1) / 2) / ((x1 - x0) / 2); ny = (YY - (y0 + y1) / 2) / ((y1 - y0) / 2)
    vig = np.clip((nx ** 2 + ny ** 2) ** 1.6 / 2.2, 0, 1)
    dark = np.clip(sl * 0.10 + vig * 0.55, 0, 0.8)
    glare = np.clip(1 - np.sqrt(((XX - 330) / 330) ** 2 + ((YY - 900) / 120) ** 2), 0, 1) ** 2 * 0.10
    a = np.clip(dark + glare, 0, 1)
    col = (glare[..., None] * 1.0 + 0) / np.maximum(a[..., None], 1e-4)
    g[..., :3] = np.clip(col, 0, 1); g[..., 3] = a * SCR_M
    return g
GLASS = build_glass()

def warp_rgba(im, k, P=TV_P):
    if abs(k - 1) < 1e-3: return im
    M = np.array([[k, 0, P[0] * (1 - k)], [0, k, P[1] * (1 - k)]], np.float32)
    return cv2.warpAffine(im, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)

# ---------------------------------------------------------------- captions
def line_layout(st, ws, maxw=930, scale=1.0):
    fk, size = STY[st]; size = int(size * scale)
    texts = [disp(w, st) for w, _ in ws]
    def width(sz):
        f = font(fk, sz); return sum(f.getlength(x) for x in texts) + f.getlength(" ") * (len(texts) - 1)
    if st in ("L", "X"):
        while width(size) > maxw and size > 60: size -= 4
    else:
        while width(size) > maxw and size > 36: size -= 3
    f = font(fk, size)
    sp = f.getlength(" ") * (0.8 if st in "LX" else 1.0)
    xs, x = [], 0.0
    for tx in texts: xs.append(x); x += f.getlength(tx) + sp
    tot = x - sp
    tops = [f.getbbox(tx, anchor="ls")[1] for tx in texts]; bots = [f.getbbox(tx, anchor="ls")[3] for tx in texts]
    top = min(tops)
    if st in ("L", "X"):
        bot = font(fk, size).getbbox("H", anchor="ls")[3]
    else:
        bot = max(bots) if st == "M" else max(min(bots), int(size * 0.05))
    return dict(st=st, fk=fk, size=size, texts=texts, xs=xs, w=tot, top=top, bot=bot)

@lru_cache(None)
def page_layout(pi):
    p = PAGES[pi]; si = p["sec"]; s = SEC[si]
    lines = [line_layout(st, ws) for st, ws, col in p["lines"]]
    gap = 20
    # target block bottom: just tucked behind the head top
    tops = []
    for k in range(9):
        t = p["t0"] + (min(p["t1"], s["t1"]) - p["t0"]) * k / 8
        i = src_idx(t)
        if s["kind"] == "tv":
            M, top, sc = tv_M(t, i); tops.append(M[1, 1] * top + M[1, 2])
        else:
            M, top, z = cut_M(si, t, i); tops.append(M[1, 1] * top + M[1, 2])
    htop = min(tops)
    # wide last line tucks behind the hair; a narrow one would vanish behind the head, so keep it clear
    bottom = htop + 30 if (lines[-1]["w"] > 560 and lines[-1]["st"] in "LX") else htop - 8
    lim_top = 300
    def total(ls): return sum(l["bot"] - l["top"] for l in ls) + gap * (len(ls) - 1)
    fs = 1.0
    for _ in range(8):
        if total(lines) <= bottom - lim_top: break
        fs *= max(0.8, (bottom - lim_top) / total(lines))
        lines = [line_layout(st, ws, maxw=int(930 * fs), scale=fs) for st, ws, col in p["lines"]]
    y = bottom - total(lines)
    out = []
    for (st, ws, col), l in zip(p["lines"], lines):
        base = y - l["top"]; x0 = 540 - l["w"] / 2
        out.append((l, base, x0, ws, col)); y = base + l["bot"] + gap
    return out

def draw_captions(cv, t, si, pal):
    for pi, p in enumerate(PAGES):
        if p["sec"] != si or t < p["t0"] - 0.01: continue
        if t >= p["t1"] + 0.07: continue
        exit_p = clamp((t - p["t1"]) / 0.07) if t >= p["t1"] else 0.0
        dy_exit = -26 * eic(exit_p); op_page = 1 - exit_p
        if si == 10 and t > 66.30: op_page *= 1 - clamp((t - 66.30) / 0.12)
        for l, base, x0, ws, col in page_layout(pi):
            for (w, fx), tx, wx in zip(ws, l["texts"], l["xs"]):
                tw = wtime(w); u = t - tw
                if u < 0: continue
                c = pal["b"] if "b" in fx else pal["a"] if ("a" in fx) else pal[col] if col in pal else pal["i"]
                if fx and "a" in fx and col == "a": c = pal["a"]
                im, ox, oy = word_img(tx, l["fk"], l["size"], tuple(c))
                if l["st"] in "LX":
                    sc = 1 + 0.42 * (1 - eoc(u / 0.16)); op = clamp(u / 0.05)
                    yo = 0
                else:
                    sc = 0.55 + 0.45 * eob(u / 0.17); op = clamp(u / 0.06); yo = 16 * (1 - eoc(u / 0.17))
                if "f" in fx:   # flip: vertical scale through -1 -> 1
                    fl = math.cos(math.pi * clamp(u / 0.3)) if u < 0.3 else 1
                    sy = abs(-fl) if u < 0.3 else 1
                    im2 = im.resize((im.width, max(1, int(im.height * max(sy, .04)))), Image.BILINEAR)
                    if u < 0.15: im2 = im2.transpose(Image.FLIP_TOP_BOTTOM)
                    cx = x0 + wx + im.width / 2 - ox; cy = base - oy + im.height / 2 + yo + dy_exit
                    paste_c(cv, im2, cx, cy, sc, op * op_page)
                    continue
                cx = x0 + wx - ox + im.width / 2; cy = base - oy + im.height / 2 + yo + dy_exit
                if "#" in fx and u < 0.2:   # pixel reveal
                    k = int(2 + 16 * (1 - u / 0.2))
                    a = np.asarray(im); sm = Image.fromarray(a).resize((max(1, im.width // k), max(1, im.height // k)), Image.BILINEAR)
                    im = sm.resize(im.size, Image.NEAREST)
                paste_c(cv, im, cx, cy, sc, op * op_page)
                if "x" in fx and u > 0.22:   # strike-through
                    q = eoc((u - 0.22) / 0.18)
                    wpx = (im.width - 2 * ox * 0 - 20) * q
                    y = int(cy + 6); x1 = int(cx - im.width / 2 + 8)
                    cv2.rectangle(cv, (x1, y - 6), (int(x1 + wpx), y + 6), tuple(float(v) for v in f3(ORANGE_L if si != 2 else ORANGE_L)), -1)

def draw_label(cv, si, t, pal):
    s = SEC[si]
    if not s["label"]: return
    u = t - s["t0"]
    n = int(clamp(u / 0.35) * len(s["label"]))
    if n <= 0: return
    tx = s["label"][:n]
    col = pal["m"]
    im = text_img(tx, "mono", 26, col, track=3)
    sq = 14
    cv2.rectangle(cv, (62, 251), (62 + sq, 251 + sq), tuple(float(v) for v in f3(pal["a"] if s["bg"] != "orange" else CREAM)), -1)
    paste(cv, im, 88, 238, 0.92)

# ---------------------------------------------------------------- person compositing
def person_layers(M, i):
    f = graded(i)
    fg = cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    al = cv2.warpAffine(np.ascontiguousarray(ALPHA[i]), M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    al = al.astype(np.float32) / 255
    return np.clip(fg, 0, 1), al

def comp_person(cv, fg, al, kind):
    a = np.clip((al - 0.06) / 0.9, 0, 1)
    if kind in ("green", "dark", "black", "orange"):
        a = np.clip((al - 0.18) / 0.8, 0, 1) ** 1.1
    small = cv2.resize(a, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    sh = cv2.GaussianBlur(small, (0, 0), 6)
    sh = cv2.warpAffine(sh, np.float32([[1, 0, 5], [0, 1, 6]]), (W // 4, H // 4))
    sh = cv2.resize(sh, (W, H))[..., None]
    so = {"paper": .30, "paper2": .30, "grid": .30, "green": .40, "dark": .5, "black": .5, "orange": .35}[kind]
    cv *= 1 - so * sh
    a3 = a[..., None]
    edge = 0.82 + 0.18 * a3
    cv[:] = cv * (1 - a3) + fg * edge * a3

# ---------------------------------------------------------------- glitch fx
def glitch_blocks(cv, seed, inten, face=None):
    r = np.random.default_rng(seed)
    n = int(4 + 8 * inten)
    for _ in range(n):
        h = int(r.integers(16, 90)); w = int(r.integers(120, 520))
        x = int(r.integers(0, W - w)); y = int(r.integers(240, H - 420 - h))
        if face and not (x + w < face[0] or x > face[2] or y + h < face[1] or y > face[3]): continue
        blk = cv[y:y + h, x:x + w]
        k = int(r.integers(8, 22))
        sm = cv2.resize(blk, (max(1, w // k), max(1, h // k)), interpolation=cv2.INTER_AREA)
        pix = cv2.resize(sm, (w, h), interpolation=cv2.INTER_NEAREST)
        sh = int(r.integers(-40, 40) * inten)
        cv[y:y + h, x:x + w] = np.roll(pix, sh, axis=1)

def rgb_split(cv, px):
    px = int(px)
    if px < 1: return cv
    out = cv.copy()
    out[:, px:, 0] = cv[:, :-px, 0]; out[:, :-px, 2] = cv[:, px:, 2]
    return out

# ---------------------------------------------------------------- front graphics per section
GFX_EV = []   # (t, sfx, gain_db)
def ev(t, name, g=-20): GFX_EV.append((t, name, g))

def w_(i): return wtime(i)

# section 1: timeline card + clock + reel badge
T_TL = w_(20)
ev(T_TL, "swoosh", -24); ev(T_TL + 0.18, "pop", -22)
ev(w_(21) + 0.05, "drag", -22)
for k in range(4): ev(w_(24) + 0.06 + k * 0.08, "click", -22)
ev(w_(27), "pop", -19); ev(w_(27) + 0.05, "ticks", -24)
ev(w_(31), "pop", -19)
def gfx_old(cv, t):
    u = t - T_TL
    if u >= 0:
        cw, ch = 880, 196
        im, d = card(cw, ch, CREAM, INK, 3, 20, GREEN, 10)
        S2 = 2
        f = font("mono", 22 * S2); fb = font("monox", 22 * S2)
        d.text((22 * S2, 18 * S2), "TIMELINE — SEQ 01", font=fb, fill=INK + (255,))
        # timecode
        if t < w_(27): tc = t - 3.13
        else: tc = 6 * 3600 * eio((t - w_(27)) / 0.6) + (t - 3.13)
        hh, mm, sc = int(tc // 3600), int(tc % 3600 // 60), int(tc % 60)
        d.text(((cw - 22) * S2, 18 * S2), "%02d:%02d:%02d" % (hh, mm, sc), font=fb,
               fill=(ORANGE if t >= w_(27) else INK) + (255,), anchor="ra")
        tx0, tw = 86, cw - 110
        for r_, lab in enumerate(["V2", "V1", "A1"]):
            yy = 58 + r_ * 44
            d.text((22 * S2, (yy + 8) * S2), lab, font=f, fill=MUTE + (255,))
            d.rounded_rectangle([tx0 * S2, yy * S2, (tx0 + tw) * S2, (yy + 34) * S2], 6 * S2, fill=(228, 222, 210, 255))
        clips = [(0, 150, GREEN), (160, 300, ORANGE), (310, 470, INK), (480, 640, GREEN), (650, 760, WOOD)]
        drag_u = clamp((t - w_(21) - 0.05) / 0.5)
        for k, (a_, b_, c_) in enumerate(clips):
            yy = 58 + 44
            xs = a_
            if k == 1:
                yy = 102 - 44 * eio(drag_u); xs = a_ + 150 * eio(drag_u)
            d.rounded_rectangle([(tx0 + xs) * S2, (yy + 3) * S2, (tx0 + xs + b_ - a_) * S2, (yy + 31) * S2], 6 * S2, fill=tuple(c_) + (255,))
            if k == 1 and 0 < drag_u < 1.0 + (t < w_(23)):
                icon(d, "cursor", (tx0 + xs + 60) * S2, (yy + 12) * S2, 34 * S2, INK, CREAM)
        for x in range(0, tw, 9):   # audio waveform
            hgt = 4 + 12 * abs(math.sin(x * 0.13) * math.sin(x * 0.031 + 1))
            d.line([(tx0 + x) * S2, (58 + 88 + 17 - hgt) * S2, (tx0 + x) * S2, (58 + 88 + 17 + hgt) * S2], fill=INK + (200,), width=3 * S2)
        for k in range(4):
            ku = t - (w_(24) + 0.06 + k * 0.08)
            if ku > 0:
                kx, ky = tx0 + 330 + k * 95, 58 + 17; r_ = 13 * eob(ku / 0.15)
                d.polygon([((kx) * S2, (ky - r_) * S2), ((kx + r_) * S2, ky * S2), (kx * S2, (ky + r_) * S2), ((kx - r_) * S2, ky * S2)],
                          fill=ORANGE + (255,), outline=INK + (255,))
        ph = tx0 + (tw - 4) * clamp((t - T_TL) / (11.73 - T_TL))
        d.line([ph * S2, 50 * S2, ph * S2, (ch - 8) * S2], fill=ORANGE + (255,), width=3 * S2)
        d.polygon([((ph - 8) * S2, 46 * S2), ((ph + 8) * S2, 46 * S2), (ph * S2, 58 * S2)], fill=ORANGE + (255,))
        im = down(im)
        paste(cv, im, 98, 1160 + 70 * (1 - eoc(u / 0.3)), clamp(u / 0.12))
    u = t - w_(27)
    if u >= 0:   # clock badge
        im, d = ss(190, 190); S2 = 2
        d.ellipse([8 * S2, 8 * S2, 188 * S2, 188 * S2], fill=GREEN + (255,))
        d.ellipse([0, 0, 180 * S2, 180 * S2], fill=CREAM + (255,), outline=INK + (255,), width=4 * S2)
        for k in range(12):
            a = k * math.pi / 6; d.line([(90 + 70 * math.sin(a)) * S2, (90 - 70 * math.cos(a)) * S2,
                                         (90 + 80 * math.sin(a)) * S2, (90 - 80 * math.cos(a)) * S2], fill=INK + (255,), width=3 * S2)
        sp = eio(u / 0.6)
        am = 2 * math.pi * 6 * sp * 12 / 12; ah = 2 * math.pi * 6 * sp / 12
        d.line([90 * S2, 90 * S2, (90 + 62 * math.sin(am * 12 / 6)) * S2, (90 - 62 * math.cos(am * 12 / 6)) * S2], fill=INK + (255,), width=5 * S2)
        d.line([90 * S2, 90 * S2, (90 + 42 * math.sin(ah)) * S2, (90 - 42 * math.cos(ah)) * S2], fill=ORANGE + (255,), width=8 * S2)
        d.ellipse([82 * S2, 82 * S2, 98 * S2, 98 * S2], fill=INK + (255,))
        im = down(im)
        paste_c(cv, im, 868, 960, eob(u / 0.25), clamp(u / 0.08), rot=-6)
        lab = text_img("6 HRS", "monox", 30, CREAM, track=2)
        pl, _ = card(lab.width + 28, 50, INK, None, 0, 25, ORANGE, 0); pl = down(pl); pl.alpha_composite(lab, (14, (50 - lab.height) // 2))
        paste_c(cv, pl, 868, 1080, eob((u - .15) / .2), clamp((u - .15) / .1))
    u = t - w_(31)
    if u >= 0:   # 60s reel badge
        im, d = card(124, 210, CREAM, INK, 4, 18, GREEN, 8); S2 = 2
        icon(d, "play", 32 * S2, 56 * S2, 60 * S2, INK)
        fb = font("monox", 28 * S2)
        d.text((62 * S2, 150 * S2), "0:60", font=fb, fill=ORANGE + (255,), anchor="mm")
        im = down(im)
        paste_c(cv, im, 212, 970, eob(u / 0.25), clamp(u / 0.08), rot=5)

# section 2: clapper
ev(w_(42), "clap", -16)
def gfx_turn(cv, t):
    u = t - w_(42)
    if u < -0.15: return
    uu = u + 0.15
    im, d = ss(250, 230); S2 = 2
    d.rounded_rectangle([10 * S2, 80 * S2, 240 * S2, 225 * S2], 12 * S2, fill=INK + (255,))
    d.text((125 * S2, 152 * S2), "ACTION", font=font("monox", 34 * S2), fill=CREAM + (255,), anchor="mm")
    d.line([20 * S2, 186 * S2, 230 * S2, 186 * S2], fill=CREAM + (120,), width=2 * S2)
    d.text((125 * S2, 206 * S2), "SCENE 01  TAKE 01", font=font("mono", 15 * S2), fill=CREAM + (200,), anchor="mm")
    arm = Image.new("RGBA", (240 * S2, 50 * S2), (0, 0, 0, 0)); ad = ImageDraw.Draw(arm)
    ad.rounded_rectangle([0, 0, 230 * S2, 44 * S2], 8 * S2, fill=CREAM + (255,), outline=INK + (255,), width=4 * S2)
    for k in range(5):
        x = k * 50 * S2
        ad.polygon([(x + 10 * S2, 4 * S2), (x + 34 * S2, 4 * S2), (x + 14 * S2, 40 * S2), (x - 10 * S2, 40 * S2)], fill=INK + (255,))
    ang = 28 * (1 - eoc((uu - 0.12) / 0.08)) if uu > 0.12 else 28
    arm = arm.rotate(ang, resample=Image.BICUBIC, center=(8 * S2, 44 * S2), expand=False)
    im.alpha_composite(arm, (10 * S2, 32 * S2))
    im = down(im)
    paste_c(cv, im, 220, 1330, 0.6 + 0.4 * eob(uu / 0.2), clamp(uu / 0.06), rot=-8)
    if u > 0.1:
        ch = text_img("DIRECTOR MODE: ON", "monox", 30, CREAM, track=2)
        pill, pd = card(ch.width + 40, 64, INK, CREAM, 2, 32, ORANGE_L, 6)
        pill = down(pill); pill.alpha_composite(ch, (20, 14))
        paste(cv, pill, 380, 1390 + 30 * (1 - eoc((u - .1) / .2)), clamp((u - .1) / .1))

# section 3: prompt bar
PROMPT = "make it feel like a top editor cut it"
T_PR0, T_PR1 = SEC[3]["t0"] + 0.25, w_(58) + 0.3
ev(T_PR0, "pop", -24); ev(T_PR0 + 0.05, "typing:%.2f" % (T_PR1 - T_PR0 - 0.1), -27); ev(T_PR1 + 0.1, "click", -20)
def gfx_direct(cv, t):
    u = t - T_PR0
    if u < 0: return
    bw, bh = 890, 112
    im, d = card(bw, bh, INK, None, 0, 56, GREEN, 8); S2 = 2
    icon(d, "sparkle", 30 * S2, 30 * S2, 52 * S2, LGREEN)
    n = int(len(PROMPT) * clamp((t - T_PR0 - 0.05) / (T_PR1 - T_PR0 - 0.1)))
    txt = PROMPT[:n] + ("▍" if (int(t * 3) % 2 == 0 or n < len(PROMPT)) else " ")
    d.text((100 * S2, 57 * S2), txt, font=font("monor", 31 * S2), fill=CREAM + (255,), anchor="lm")
    sendp = clamp((t - T_PR1 - 0.1) / 0.15)
    rr = 36 * (1 + 0.15 * math.sin(math.pi * sendp))
    d.ellipse([(bw - 64 - rr) * S2, (56 - rr) * S2, (bw - 64 + rr) * S2, (56 + rr) * S2], fill=(LGREEN if sendp > 0 else (70, 70, 70)) + (255,))
    d.line([(bw - 64) * S2, 70 * S2, (bw - 64) * S2, 42 * S2], fill=INK + (255,), width=6 * S2)
    d.line([(bw - 76) * S2, 54 * S2, (bw - 64) * S2, 41 * S2, (bw - 52) * S2, 54 * S2], fill=INK + (255,), width=6 * S2)
    im = down(im)
    paste(cv, im, 66, 1360 + 60 * (1 - eoc(u / 0.3)), clamp(u / 0.12))

# section 4: checklist card, letterbox, EQ, stamp
ITEMS = [(59, "Cut the pauses", "scissors"), (62, "Punchy captions", "text"), (66, "Title behind me", "film"),
         (71, "Cinematic look", "camera"), (76, "Music that builds", "music")]
T_CHK = [w_(80) + 0.0 + k * 0.1 for k in range(5)]
T_STAMP = w_(82) + 0.1
for w, _, _ in ITEMS: ev(w_(w) + 0.02, "pop", -23)
for tt in T_CHK: ev(tt, "click", -21)
ev(T_STAMP, "stamp", -15)
ev(w_(74), "swoosh", -24)
T_LB0, T_LB1 = w_(74) - 0.05, w_(76) - 0.05
def gfx_brief(cv, t):
    u = t - w_(59)
    if u >= 0:
        cw, ch = 610, 336
        im, d = card(cw, ch, CREAM, INK, 3, 22, GREEN, 10); S2 = 2
        d.text((24 * S2, 22 * S2), "THE BRIEF", font=font("monox", 24 * S2), fill=INK + (255,))
        d.text(((cw - 24) * S2, 22 * S2), "%d/5" % sum(1 for w, _, _ in ITEMS if t >= w_(w)), font=font("mono", 24 * S2), fill=MUTE + (255,), anchor="ra")
        d.line([24 * S2, 60 * S2, (cw - 24) * S2, 60 * S2], fill=INK + (60,), width=2 * S2)
        for k, (w, lab, ic) in enumerate(ITEMS):
            iu = t - w_(w)
            if iu < 0: continue
            yy = 74 + k * 52; op = int(255 * clamp(iu / .1)); xo = int(-20 * (1 - eoc(iu / .2)))
            done = t >= T_CHK[k]
            bx = 24 + xo
            d.rounded_rectangle([bx * S2, (yy + 4) * S2, (bx + 34) * S2, (yy + 38) * S2], 8 * S2,
                                fill=(GREEN if done else CREAM) + (op,), outline=INK + (op,), width=3 * S2)
            if done: icon(d, "check", (bx + 3) * S2, (yy + 7) * S2, 28 * S2, CREAM)
            icon(d, ic, (bx + 52) * S2, (yy + 6) * S2, 30 * S2, INK)
            d.text(((bx + 98) * S2, (yy + 22) * S2), lab, font=font("xbold", 30 * S2), fill=INK + (op,), anchor="lm")
            if done:
                d.line([(bx + 96) * S2, (yy + 23) * S2, (bx + 98 + font("xbold", 30).getlength(lab) * eoc((t - T_CHK[k]) / .15)) * S2, (yy + 23) * S2],
                       fill=GREEN + (200,), width=3 * S2)
        im = down(im)
        paste(cv, im, 60 + -80 * (1 - eoc(u / 0.3)), 1150, clamp(u / 0.1))
        su = t - T_STAMP
        if su >= 0:
            st = text_img("BUILT ✓", "black", 64, GREEN)
            bx_, bd = ss(st.width + 40, st.height + 24)
            bd.rounded_rectangle([0, 0, bx_.width - 1, bx_.height - 1], 18, outline=GREEN + (255,), width=10)
            bx_ = down(bx_); bx_.alpha_composite(st, (20, 12))
            paste_c(cv, bx_, 470, 1300, 1 + 0.9 * (1 - eoc(su / 0.14)), clamp(su / .05) * 0.95, rot=-12)
    u = t - (w_(77))
    if u >= 0:   # EQ bars
        n = 6; bw_ = 30; x0 = 712
        grow = clamp((t - w_(77)) / 2.0)
        for k in range(n):
            ph = (t - BEAT0) / BEAT
            hgt = 30 + (60 + 130 * grow) * (0.5 + 0.5 * abs(math.sin(math.pi * ph + k * 0.9))) * clamp(u / .2)
            x = x0 + k * (bw_ + 10)
            cv[int(1470 - hgt):1470, x:x + bw_] = f3(GREEN if k % 2 == 0 else ORANGE)
        paste(cv, text_img("BUILD ↑", "monox", 26, INK, track=2), 712, 1484, clamp(u / .2))

def letterbox(cv, t):
    if T_LB0 - 0.2 < t < T_LB1 + 0.2:
        p = min(eoc((t - T_LB0) / 0.18), 1 - eic((t - T_LB1) / 0.18)) if t > T_LB0 else 0
        hh = int(215 * clamp(p))
        if hh > 0:
            cv[:hh] = 0.02; cv[H - hh:] = 0.02
            # cinematic grade push
            return p
    return 0

# section 5: code card + laptop
CODE = [(85, [("cut", LGREEN), ("(pauses=", CREAM), ("True", ORANGE_L), (")", CREAM)]),
        (87, [("caption", LGREEN), ("(style=", CREAM), ("'punchy'", GOLD), (")", CREAM)]),
        (89, [("sound", LGREEN), ("(sfx=", CREAM), ("True", ORANGE_L), (", music=", CREAM), ("'build'", GOLD), (")", CREAM)]),
        (92, [("render", LGREEN), ("()", CREAM), ("  # made in code", (120, 120, 110))])]
for w, parts in CODE:
    n = sum(len(p) for p, _ in parts); ev(w_(w), "typing:%.2f" % (n / 34), -26)
ev(SEC[5]["t0"] + 0.15, "pop", -22); ev(w_(96), "pop", -18); ev(w_(96) + 0.2, "ding", -24)
def gfx_code(cv, t):
    u = t - SEC[5]["t0"] - 0.15
    if u < 0: return
    cw, ch = 890, 330
    im, d = card(cw, ch, (24, 24, 22), CREAM, 2, 20, GREEN, 10); S2 = 2
    for k, c in enumerate([ORANGE_L, GOLD, LGREEN]):
        d.ellipse([(24 + k * 30) * S2, 22 * S2, (40 + k * 30) * S2, 38 * S2], fill=c + (255,))
    d.text((130 * S2, 30 * S2), "vibe_edit.py", font=font("mono", 22 * S2), fill=(160, 155, 145, 255), anchor="lm")
    d.line([0, 58 * S2, cw * S2, 58 * S2], fill=(60, 60, 56, 255), width=2 * S2)
    fm = font("mono", 30 * S2)
    for k, (w, parts) in enumerate(CODE):
        cu = t - w_(w)
        if cu < 0: continue
        n = int(cu * 34)
        x = 70; yy = 92 + k * 56
        d.text((26 * S2, yy * S2), str(k + 1), font=font("monor", 24 * S2), fill=(90, 90, 84, 255), anchor="lm")
        for txt, c in parts:
            if n <= 0: break
            s_ = txt[:n]; n -= len(txt)
            d.text((x * S2, yy * S2), s_, font=fm, fill=tuple(c) + (255,), anchor="lm")
            x += fm.getlength(s_) / S2
        last = max(k for k, (w2, _) in enumerate(CODE) if t >= w_(w2))
        if k == last and int(t * 3) % 2 == 0:
            d.rectangle([x * S2, (yy - 16) * S2, (x + 14) * S2, (yy + 16) * S2], fill=CREAM + (220,))
    lu = t - w_(96)
    if lu > 0:
        sc = eob(lu / .25)
        icon(d, "laptop", (cw - 190) * S2, (ch - 180 - 10 * (1 - sc)) * S2, 160 * S2 * sc, CREAM)
        if lu > .2:
            d.ellipse([(cw - 70) * S2, (ch - 170) * S2, (cw - 26) * S2, (ch - 126) * S2], fill=LGREEN + (255,))
            icon(d, "check", (cw - 66) * S2, (ch - 166) * S2, 36 * S2, INK)
    im = down(im)
    paste(cv, im, 58, 1150 + 60 * (1 - eoc(u / .3)), clamp(u / .1))

# section 6: format tiles, 50 grid, winner
TILES = [(100, "REELS", "reel"), (105, "MOTION GFX", "shapes"), (107, "PRODUCT ADS", "bottle"),
         (109, "CLAYMATION", "blob"), (110, "VFX", "burst"), (111, "PODCAST CLIPS", "mic")]
for w, _, _ in TILES: ev(w_(w), "pop", -20)
T_OUT = w_(113); T_G0 = w_(114); T_G1 = T_G0 + 0.9; T_TEST = w_(122); T_WIN = w_(124)
ev(T_OUT, "swoosh", -24); ev(T_G0, "riser_s:0.9", -26)
for k in range(50):
    if k % 3 == 0: ev(T_G0 + 0.9 * k / 50, "tick", -30)
for k in range(6): ev(T_TEST + k * 0.1, "tick", -24)
ev(T_WIN, "ding", -18)
_tr = np.random.default_rng(11)
THUMB_COL = [tuple(int(v) for v in c) for c in _tr.choice(np.array([CREAM, INK, GREEN, WOOD, GOLD, (232, 225, 214)]), 50)]
WIN_K = 23
SCAN = [7, 31, 14, 42, 3, 27]
def gfx_formats(cv, t):
    u_out = t - T_OUT
    if u_out < 0.25:
        sc_out = 1 - eic(clamp(u_out / 0.25)) if u_out > 0 else 1
        for k, (w, lab, ic) in enumerate(TILES):
            u = t - w_(w)
            if u < 0: continue
            im, d = card(258, 148, CREAM, INK, 3, 18, INK, 7); S2 = 2
            icon(d, ic, 18 * S2, 20 * S2, 70 * S2, INK if ic != "blob" else ORANGE, CREAM)
            d.text((18 * S2, 118 * S2), lab, font=font("monox", 22 * S2), fill=INK + (255,), anchor="lm")
            d.text((240 * S2, 30 * S2), "%02d" % (k + 1), font=font("mono", 20 * S2), fill=MUTE + (255,), anchor="ra")
            if k == 0:
                d.ellipse([196 * S2, 68 * S2, 238 * S2, 110 * S2], fill=GREEN + (255,)); icon(d, "check", 200 * S2, 72 * S2, 34 * S2, CREAM)
            im = down(im)
            col, row = k % 3, k // 3
            cx, cy = 60 + col * 282 + 132, 1165 + row * 170 + 77
            paste_c(cv, im, cx, cy, eob(u / .22) * sc_out, clamp(u / .06), rot=(-3 if k % 2 else 3) * (1 - eoc(u / .3)))
    if t >= T_G0:
        n = int(50 * clamp((t - T_G0) / 0.9)) + 1
        win = t >= T_WIN
        scan = SCAN[int((t - T_TEST) / 0.1)] if T_TEST <= t < T_WIN and int((t - T_TEST) / 0.1) < len(SCAN) else None
        for k in range(min(n, 50)):
            col, row = k % 10, k // 10
            x, y = 62 + col * 87, 1172 + row * 62
            dim = 0.35 if (win and k != WIN_K) else 1.0
            c = THUMB_COL[k]
            sub = cv[y:y + 54, x:x + 78]
            sub[:] = sub * (1 - dim) + f3(c) * dim
            cv2.rectangle(cv, (x, y), (x + 77, y + 53), tuple(float(v) for v in f3(INK)), 2)
            tc = f3(INK) if sum(c) > 400 else f3(CREAM)
            sub[36:42, 8:52] = sub[36:42, 8:52] * (1 - dim) + tc * dim
            sub[10:28, 8:30] = sub[10:28, 8:30] * (1 - dim) + f3(ORANGE) * dim
            if k == scan:
                cv2.rectangle(cv, (x - 4, y - 4), (x + 81, y + 57), tuple(float(v) for v in f3(CREAM)), 5)
        paste(cv, text_img("×%02d" % min(n, 50), "monox", 34, INK, track=1), 62, 1490 - 8, 0.9 if not win else 0.0)
        if win:
            wu = t - T_WIN
            k = WIN_K; col, row = k % 10, k // 10
            x, y = 62 + col * 87, 1172 + row * 62
            sc = 1 + 0.5 * eob(wu / .25)
            im, d = card(78, 54, THUMB_COL[k], GREEN, 4, 6, GREEN, 0)
            im = down(im)
            paste_c(cv, im, x + 39, y + 27, sc)
            badge = text_img("WINNER", "monox", 26, CREAM, track=1)
            b, bd = card(badge.width + 24, 46, GREEN, INK, 2, 23, INK, 4); b = down(b); b.alpha_composite(badge, (12, 6))
            paste_c(cv, b, x + 39, y - 40, eob(wu / .2), clamp(wu / .06))

# section 7: big ? and needs checklist
NEEDS = [(131, 132, "Your footage", "camera"), (133, 134, "Your laptop", "laptop"), (137, 139, "Vibe Editing system", "sparkle")]
for a, b, _, _ in NEEDS: ev(w_(a), "pop", -21); ev(w_(b) + 0.25, "click", -20)
def back_need(cv, t):
    u = t - (SEC[7]["t0"] + 0.1)
    if u < 0: return
    q = word_img("?", "serif", 1300, GREEN)[0]
    paste_c(cv, q, 560, 820, 1.25 - 0.25 * eoc(u / 0.5) + 0.01 * u, 0.10 * clamp(u / .2))
def gfx_need(cv, t):
    u = t - w_(131)
    if u < 0: return
    cw, ch = 820, 296
    im, d = card(cw, ch, CREAM, INK, 3, 22, GREEN, 10); S2 = 2
    for k, (a, b, lab, ic) in enumerate(NEEDS):
        iu = t - w_(a)
        if iu < 0: continue
        yy = 22 + k * 90; op = int(255 * clamp(iu / .1))
        d.rounded_rectangle([22 * S2, yy * S2, 92 * S2, (yy + 70) * S2], 14 * S2, fill=(INK if k < 2 else GREEN) + (op,))
        icon(d, ic, 33 * S2, (yy + 11) * S2, 48 * S2, CREAM)
        d.text((116 * S2, (yy + 36) * S2), lab, font=font("black", 40 * S2), fill=(INK if k < 2 else GREEN) + (op,), anchor="lm")
        cu = t - (w_(b) + 0.25)
        cx = cw - 60
        d.ellipse([(cx - 26) * S2, (yy + 9) * S2, (cx + 26) * S2, (yy + 61) * S2], outline=INK + (op,), width=3 * S2,
                  fill=(GREEN if cu > 0 else CREAM) + (op,))
        if cu > 0: icon(d, "check", (cx - 20) * S2, (yy + 15) * S2, 40 * S2 * min(1, eob(cu / .2)), CREAM)
        if k < 2: d.line([22 * S2, (yy + 82) * S2, (cw - 22) * S2, (yy + 82) * S2], fill=INK + (40,), width=2 * S2)
    im = down(im)
    paste(cv, im, 60, 1172 + 60 * (1 - eoc(u / .3)), clamp(u / .1))

# section 8: the kit card
MODS = ["01  Captions & titles", "02  Motion graphics", "03  Sound & music", "04  Ads at scale"]
T_SK, T_CO, T_M0 = w_(141), w_(145), w_(147)
ev(T_SK, "pop", -20); ev(T_CO, "pop", -20)
for k in range(4): ev(T_M0 + k * 0.45, "click", -23)
def gfx_system(cv, t):
    u = t - T_SK
    if u < 0: return
    cw, ch = 870, 338
    im, d = card(cw, ch, CREAM, INK, 3, 22, ORANGE, 10); S2 = 2
    d.rounded_rectangle([0, 0, cw * S2 - 1, 62 * S2], 22 * S2, fill=INK + (255,))
    d.rectangle([0, 30 * S2, cw * S2 - 1, 62 * S2], fill=INK + (255,))
    d.text((24 * S2, 31 * S2), "VIBE EDITING", font=font("black", 30 * S2), fill=CREAM + (255,), anchor="lm")
    d.text(((cw - 24) * S2, 31 * S2), "THE SYSTEM", font=font("mono", 22 * S2), fill=GOLD + (255,), anchor="rm")
    # skills grid
    d.text((24 * S2, 92 * S2), "EDITING SKILLS", font=font("monox", 22 * S2), fill=INK + (255,), anchor="lm")
    ics = ["scissors", "text", "music", "shapes", "camera", "sparkle"]
    for k, ic in enumerate(ics):
        ku = t - (T_SK + 0.06 * k)
        if ku < 0: continue
        cx, cy = 24 + (k % 3) * 104, 116 + (k // 3) * 104
        s = 92 * min(1, eob(ku / .2))
        d.rounded_rectangle([cx * S2, cy * S2, (cx + s) * S2, (cy + s) * S2], 14 * S2, fill=(GREEN if k % 2 == 0 else INK) + (255,))
        icon(d, ic, (cx + s * .2) * S2, (cy + s * .2) * S2, s * .6 * S2, CREAM)
    cu = t - T_CO
    if cu >= 0:
        op = int(255 * clamp(cu / .1))
        d.line([352 * S2, 80 * S2, 352 * S2, (ch - 20) * S2], fill=INK + (50,), width=2 * S2)
        d.text((376 * S2, 92 * S2), "+ FULL COURSE", font=font("monox", 22 * S2), fill=ORANGE + (op,), anchor="lm")
        icon(d, "play", (cw - 70) * S2, 74 * S2, 40 * S2, ORANGE)
        for k, m in enumerate(MODS):
            mu = t - (T_M0 + k * 0.45)
            if mu < 0: continue
            yy = 128 + k * 50; o2 = int(255 * clamp(mu / .12))
            d.rounded_rectangle([376 * S2, yy * S2, (cw - 24) * S2, (yy + 40) * S2], 10 * S2, fill=(232, 226, 214, o2))
            d.text((392 * S2, (yy + 20) * S2), m, font=font("bold", 25 * S2), fill=INK + (o2,), anchor="lm")
            pr = clamp((t - (T_M0 + k * 0.45)) / 0.5)
            d.rounded_rectangle([(cw - 80) * S2, (yy + 15) * S2, (cw - 36) * S2, (yy + 25) * S2], 5 * S2, fill=(200, 192, 180, o2))
            d.rounded_rectangle([(cw - 80) * S2, (yy + 15) * S2, (cw - 80 + 44 * pr) * S2, (yy + 25) * S2], 5 * S2, fill=GREEN + (o2,))
    im = down(im)
    paste(cv, im, 60, 1150 + 60 * (1 - eoc(u / .3)), clamp(u / .1))

# section 10: LED dial + phone
T_LED = w_(175); T_PH = w_(182); T_DONE = w_(185)
ev(T_LED, "blip", -20); ev(T_PH, "pop", -19); ev(T_DONE, "ding", -20)
def gfx_proof(cv, t, k):
    if k > 1.01: return
    if t >= T_LED:
        u = t - T_LED
        if t < T_DONE:
            l1, l2, c = "EDITING APPS OPENED", "0" if u > 0.35 else str(9 - int(u / 0.04) % 10), ORANGE_L
        else:
            l1, l2, c = "STATUS", "DONE", LGREEN
        im1 = text_img(l1, "mono", 22, c, track=2); im2 = word_img(l2, "monox", 72, tuple(c))[0]
        op = 0.95 if (int(t * 10) % 7 or u > 0.5) else 0.6
        paste_c(cv, im1, 540, 1360, 1, op); paste_c(cv, im2, 540, 1432, 1, op)
    else:
        im1 = text_img("CH 09  ·  PROOF", "mono", 22, (120, 116, 110), track=2)
        paste_c(cv, im1, 540, 1404, 1, 0.9)
    u = t - T_PH
    if 0 <= u and t < 66.3:
        im, d = card(118, 210, INK, CREAM, 3, 22, GREEN, 7); S2 = 2
        d.rounded_rectangle([12 * S2, 14 * S2, 106 * S2, 196 * S2], 14 * S2, fill=(40, 40, 38, 255))
        d.ellipse([46 * S2, 84 * S2, 72 * S2, 110 * S2], fill=(ORANGE_L if int(t * 2) % 2 == 0 else (90, 40, 30)) + (255,))
        d.text((59 * S2, 140 * S2), "REC", font=font("monox", 20 * S2), fill=CREAM + (255,), anchor="mm")
        d.rounded_rectangle([44 * S2, 20 * S2, 74 * S2, 28 * S2], 4 * S2, fill=INK + (255,))
        im = down(im)
        paste_c(cv, im, 238, 1010, eob(u / .25), clamp(u / .06), rot=8)

# ---------------------------------------------------------------- section renderers
def render_cut(si, t):
    s = SEC[si]; pal = PAL[s["bg"]]
    cv = bg_static(s["bg"]).copy()
    if si == 7: back_need(cv, t)
    draw_label(cv, si, t, pal)
    i = src_idx(t)
    M, top, z = cut_M(si, t, i)
    draw_captions(cv, t, si, pal)
    fg, al = person_layers(M, i)
    if si == 4:   # cinematic grade during "cinematic look"
        p = clamp(min((t - T_LB0) / .18, 1 - (t - T_LB1) / .18)) if T_LB0 - .2 < t < T_LB1 + .2 else 0
        if p > 0:
            l = fg.mean(-1, keepdims=True)
            cg = np.clip((fg - 0.5) * 1.18 + 0.5, 0, 1)
            cg = cg * (1 - 0.12 * (1 - l)) + f3((10, 20, 30)) * 0.12 * (1 - l) + f3((40, 20, 0)) * 0.10 * l
            fg = fg * (1 - p) + cg * p
    comp_person(cv, fg, al, s["bg"])
    {1: None}.get(si)
    if si == 2: gfx_turn(cv, t)
    elif si == 3: gfx_direct(cv, t)
    elif si == 4: gfx_brief(cv, t); letterbox(cv, t)
    elif si == 5: gfx_code(cv, t)
    elif si == 6: gfx_formats(cv, t)
    elif si == 7: gfx_need(cv, t)
    elif si == 8: gfx_system(cv, t)
    return cv, M, top

def render_tv(si, t):
    s = SEC[si]; pal = PAL[s["bg"]]
    cv = bg_static(s["bg"]).copy()
    k = 1.0
    if si == 10:
        k = 1 + 1.45 * (1 - eoc((t - s["t0"]) / 0.55))
    # floor shadow
    sh = np.zeros((H // 4, W // 4), np.float32)
    cv2.ellipse(sh, (135, int(TV_P[1] / 4 + k * (1600 - TV_P[1]) / 4)), (int(125 * k), int(10 * k)), 0, 0, 360, 1, -1)
    sh = cv2.resize(cv2.GaussianBlur(sh, (0, 0), 5), (W, H))[..., None]
    cv *= 1 - 0.35 * sh
    if k < 1.02:
        draw_label(cv, si, t, pal)
        draw_captions(cv, t, si, pal)
    i = src_idx(t)
    M, top, sc = tv_M(t, i, k)
    fg, al = person_layers(M, i)
    scr = warp_rgba(SCR_M, k)[..., None] if k != 1 else SCR_M[..., None]
    # CRT power-off at the end of the proof section
    crt = 0.0
    if si == 10 and t > 66.30:
        crt = clamp((t - 66.30) / 0.26)
        sy = max(0.006, 1 - eic(clamp(crt / 0.6)))
        sx = 1 - eic(clamp((crt - 0.55) / 0.45))
        Mc = np.float32([[sx, 0, 540 * (1 - sx)], [0, sy, 1039 * (1 - sy)]])
        fg = cv2.warpAffine(fg, Mc, (W, H), borderValue=(0, 0, 0))
        fg = np.clip(fg * (1 + 2.5 * crt), 0, 1)
        if crt >= 1: fg[:] = 0.03
        lit = cv2.warpAffine(np.ones((H, W), np.float32), Mc, (W, H))[..., None]
        fg = fg * lit + 0.04 * (1 - lit)
    cv[:] = cv * (1 - scr) + fg * scr
    g = warp_rgba(GLASS, k) if k != 1 else GLASS
    a = g[..., 3:4]; cv[:] = cv * (1 - a) + g[..., :3] * a
    tvl = warp_rgba(TV, k) if k != 1 else TV
    a = tvl[..., 3:4]; cv[:] = cv * (1 - a) + tvl[..., :3] * a
    # pop-out: the head breaks out over the bezel
    st = TV_P[1] + k * (TV_SCR[1] + 30 - TV_P[1])
    if crt == 0:
        m = np.clip((st - YY) / 10, 0, 1)
        ap = np.clip((al - 0.06) / 0.9, 0, 1) * m
        small = cv2.resize(ap, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        shd = cv2.resize(cv2.GaussianBlur(cv2.warpAffine(small, np.float32([[1, 0, 3], [0, 1, 4]]), (W // 4, H // 4)), (0, 0), 3), (W, H))[..., None]
        cv *= 1 - 0.35 * shd
        a3 = ap[..., None]; cv[:] = cv * (1 - a3) + fg * a3
    if si == 1: gfx_old(cv, t)
    if si == 10: gfx_proof(cv, t, k)
    return cv, M, top

def render_end(t):
    cv = bg_static("green").copy()
    u = t - END0 - 0.05
    pal = PAL["green"]
    # mini TV
    tvs = cv2.resize(TV[600:1620], (W * 2 // 5, 1020 * 2 // 5), interpolation=cv2.INTER_AREA)
    im = Image.fromarray((tvs * 255).astype(np.uint8), "RGBA")
    scr = Image.new("RGBA", im.size, (0, 0, 0, 0)); sd = ImageDraw.Draw(scr)
    sd.rounded_rectangle([TV_SCR[0] * 2 // 5 + 2, (TV_SCR[1] - 600) * 2 // 5 + 2, TV_SCR[2] * 2 // 5 - 2, (TV_SCR[3] - 600) * 2 // 5 - 2], 26, fill=(18, 18, 17, 255))
    icon(sd, "play", W // 5 - 40, (1039 - 600) * 2 // 5 - 40, 80, LGREEN)
    scr.alpha_composite(im); im = scr
    paste_c(cv, im, 540, 600, eob(u / .35), clamp(u / .1))
    v = word_img("VIBE", "black", 250, CREAM)[0]
    paste_c(cv, v, 540, 880, 1 + 0.4 * (1 - eoc((u - .12) / .18)), clamp((u - .12) / .05))
    e = word_img("Editing", "serifi", 210, ORANGE_L)[0]
    paste_c(cv, e, 560, 1075, 0.6 + 0.4 * eob((u - .3) / .25), clamp((u - .3) / .08))
    cu = u - 0.6
    if cu > 0:
        pulse = 1 + 0.025 * math.sin(max(0, cu - .4) * 2 * math.pi * 1.4)
        tx = text_img("COMMENT “VIBE”", "black", 60, INK)
        pw = tx.width + 150
        p, pd = card(pw, 118, CREAM, INK, 3, 59, ORANGE, 9)
        p = down(p); p.alpha_composite(tx, (44, (118 - tx.height) // 2))
        arr = icon_img("play", 64, GREEN); p.alpha_composite(arr, (pw - 90, 27))
        paste_c(cv, p, 540, 1310, eob(cu / .25) * pulse, clamp(cu / .06))
        sub = text_img("GET THE SYSTEM + THE FULL COURSE", "mono", 26, GOLD, track=2)
        paste_c(cv, sub, 540, 1430, 1, clamp((cu - .25) / .2))
    return cv

def render_section(si, t):
    s = SEC[si]
    if s["kind"] == "cut": cv, M, top = render_cut(si, t)
    elif s["kind"] == "tv": cv, M, top = render_tv(si, t)
    else: return render_end(t), None
    face = (int(M[0, 0] * (head(src_idx(t))[1] - 130) + M[0, 2]), int(M[1, 1] * top + M[1, 2]),
            int(M[0, 0] * (head(src_idx(t))[1] + 130) + M[0, 2]), int(M[1, 1] * (top + 330) + M[1, 2]))
    for tg, d in GLITCHES:
        if s["t0"] <= tg < s["t1"] and 0 <= t - tg < d:
            inten = 1 - (t - tg) / d
            glitch_blocks(cv, int(tg * 1000), inten, face)
            cv = rgb_split(cv, 6 * inten)
    dx, dy = shake(t)
    if abs(dx) + abs(dy) > 0.3:
        cv = cv2.warpAffine(cv, np.float32([[1, 0, dx], [0, 1, dy]]), (W, H), borderMode=cv2.BORDER_REFLECT)
    return cv, face

# ---------------------------------------------------------------- transitions + frame
def boundary(t):
    for k, (typ, hw) in TRANS.items():
        tb = SEC[k]["t0"]
        if abs(t - tb) <= hw / FPS + 1e-6: return k, typ, hw, tb
    return None

def hblur(im, k):
    k = int(k)
    return cv2.blur(im, (k, 1)) if k > 2 else im
def vblur(im, k):
    k = int(k)
    return cv2.blur(im, (1, k)) if k > 2 else im

def render_frame(fi):
    t = fi / FPS
    b = boundary(t)
    si = sec_at(t)
    if not b:
        cv, face = render_section(si, t)
    else:
        k, typ, hw, tb = b
        p = clamp((t - (tb - hw / FPS)) / (2 * hw / FPS))
        if typ == "glitch":
            cv, face = render_section(k - 1 if t < tb else k, t)
            inten = 1 - abs(t - tb) / (hw / FPS + 1e-6)
            bs = int(4 + 40 * inten)
            sm = cv2.resize(cv, (W // bs, H // bs), interpolation=cv2.INTER_AREA)
            pix = cv2.resize(sm, (W, H), interpolation=cv2.INTER_NEAREST)
            cv = cv * (1 - 0.8 * inten) + pix * 0.8 * inten
            glitch_blocks(cv, fi, inten); cv = rgb_split(cv, 14 * inten)
        elif typ == "flip":
            A = render_section(k - 1, t)[0] if p < .5 else render_section(k, t)[0]
            sx = abs(math.cos(math.pi * p)) ** 0.8
            cv = np.ones((H, W, 3), np.float32) * f3(GREEN_D)
            wpx = max(2, int(W * sx))
            sq = cv2.resize(A, (wpx, H), interpolation=cv2.INTER_AREA)
            x0 = (W - wpx) // 2; cv[:, x0:x0 + wpx] = sq
            cv = cv + (1 - sx) * 0.35
        elif typ in ("whip", "push"):
            A = render_section(k - 1, t)[0]; B = render_section(k, t)[0]
            e = eio(p); sp = math.sin(math.pi * p)
            if typ == "whip":
                off = int(W * e); bl = 10 + 140 * sp
                cv = np.zeros_like(A)
                cv[:, :W - off] = hblur(A, bl)[:, off:]
                cv[:, W - off:] = hblur(B, bl)[:, :off]
            else:
                off = int(H * e); bl = 10 + 160 * sp
                cv = np.zeros_like(A)
                cv[:H - off] = vblur(A, bl)[off:]
                cv[H - off:] = vblur(B, bl)[:off]
        elif typ == "iris":
            A = render_section(k - 1, t)[0]; B = render_section(k, t)[0]
            r = 1500 * eic(p) ** 0.9
            m = ((XX - 560) ** 2 + (YY - 980) ** 2 < r * r).astype(np.float32)
            m = cv2.GaussianBlur(m, (0, 0), 2)[..., None]
            ring = (np.abs(np.sqrt((XX - 560) ** 2 + (YY - 980) ** 2) - r) < 7).astype(np.float32)[..., None]
            cv = A * (1 - m) + B * m
            cv = cv * (1 - ring) + f3(GREEN) * ring
        elif typ == "flash":
            cv, face = render_section(k - 1 if t < tb else k, t)
            if t >= tb: cv = cv + (1 - cv) * 0.85 * (1 - clamp((t - tb) / (hw / FPS + 0.04)))
    # global finish: cinematic letterbox stays on top, grain + vignette
    cv = cv * VIGN
    cv += GRAIN[fi % 6] * 0.022
    return (np.clip(cv, 0, 1) * 255 + 0.5).astype(np.uint8)

# ---------------------------------------------------------------- sfx event export
def all_events():
    evs = list(GFX_EV)
    for p in PAGES:
        evs.append((p["t0"], "pop_soft", -27))
        for st, ws, col in p["lines"]:
            for w, fx in ws:
                if "!" in fx: evs.append((wtime(w), "hit", -21 if "z" in fx else -24))
                if "#" in fx: evs.append((wtime(w), "glitch_s", -25))
                if "x" in fx: evs.append((wtime(w) + 0.22, "swipe", -24))
                if "f" in fx: evs.append((wtime(w), "flip_s", -22))
    for k, (typ, hw) in TRANS.items():
        tb = SEC[k]["t0"]
        nm = {"glitch": "glitch", "flip": "whoosh", "whip": "whoosh", "push": "whoosh", "iris": "whoosh_soft", "flash": "impact"}[typ]
        evs.append((tb - 0.12 if nm.startswith("whoosh") else tb, nm, -18))
    for tb in [SEC[k]["t0"] for k in range(1, len(SEC))]:
        pass
    for a, b, o in SEGS[1:]:   # subtle tick on internal jump cuts not covered by transitions
        if all(abs(o - SEC[k]["t0"]) > 0.1 for k in range(len(SEC))):
            evs.append((o, "cut_tick", -31))
    evs.append((10.0, "riser:1.80", -17)); evs.append((11.82, "impact", -13))
    evs.append((59.07, "zoom_out", -20)); evs.append((66.30, "crt_off", -16))
    evs.append((END0 + 0.12, "hit", -17)); evs.append((END0 + 0.62, "pop", -18))
    return sorted(evs)

if __name__ == "__main__":
    import multiprocessing as mp, subprocess
    mode = sys.argv[1]
    if mode == "stills":
        ts = [float(x) for x in sys.argv[3].split(",")]
        os.makedirs(sys.argv[2], exist_ok=True)
        for tt in ts:
            Image.fromarray(render_frame(int(round(tt * FPS)))).save(f"{sys.argv[2]}/s_{tt:06.2f}.jpg", quality=88)
    elif mode == "events":
        json.dump(all_events(), open(sys.argv[2], "w"))
    elif mode == "video":
        out = sys.argv[2]; a, b = 0, NF
        if len(sys.argv) > 4: a, b = int(sys.argv[3]), int(sys.argv[4])
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                              "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
        with mp.Pool(4) as pool:
            for k, fr in enumerate(pool.imap(render_frame, range(a, b), chunksize=4)):
                p.stdin.write(fr.tobytes())
                if k % 150 == 0: print("frame", a + k, flush=True)
        p.stdin.close(); p.wait()
