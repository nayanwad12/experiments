"""scene.py: the pool ad, every frame as a function of time.

Layers per frame:  graded footage (camera moves) -> big text -> the cut-out person (so the text sits BEHIND them)
-> cards / UI / captions.  "How it works" is a Vox-style paper explainer with a live cut-out sticker of the speaker.
Timings come from work/edl.json (every word re-timed to the cut), so cues land on the spoken word.

    python3 scene.py stills 0.5 5.4 10 ...     check frames -> out/stills/
    python3 scene.py draft                     half-res draft -> out/draft.mp4
    python3 scene.py render                    full render (picture only) -> work/picture.mp4
"""
import json
import math
import subprocess
import sys

import numpy as np
import skia

sys.path.insert(0, "vibe")
from motion_kit import (Stage, clamp, ease_in_cubic, ease_in_out_cubic, ease_out_back, ease_out_cubic,  # noqa: E402
                        ease_out_expo, lerp, prog, spring, text, text_width)

E = json.load(open("work/edl.json"))
WORDS = E["words"]
CUT = E["duration"]
END_CARD = 2.9
DUR = round(CUT + END_CARD, 3)
FPS = 30
S = Stage(1080, 1920, fps=FPS, duration=DUR)
SW, SH = 720, 1280            # A-roll size; drawn at 1.5x = 1080x1920
K0 = 1.5

# ---------------------------------------------------------------- palette + fonts
HEX = {"ink": "#0B0B0D", "paper": "#F2EEE3", "white": "#FFFFFF", "lime": "#D4FF3F", "peri": "#C4C6FF",
       "blush": "#FFCFD8", "ice": "#C8F0EC", "orange": "#FF5A1F", "red": "#FF3B30"}


def col(name, a=1.0):
    h = HEX[name].lstrip("#")
    return skia.Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(255 * clamp(a)))


F_IMPACT = "Anton-400.ttf"
F_DISPLAY = "Unbounded-900.ttf"
F_SERIF = "InstrumentSerif-Italic.ttf"
F_BODY = "InterTight-800.ttf"
F_BOLD = "InterTight-700.ttf"
F_MONO = "JetBrainsMono-700.ttf"
F_HAND = "CaveatBrush-Regular.ttf"
CUBIC = skia.SamplingOptions(skia.CubicResampler.Mitchell())
LIN = skia.SamplingOptions(skia.FilterMode.kLinear)


# ---------------------------------------------------------------- footage
def _decode(path, pix, w=SW, h=SH, ss=None, to=None):
    args = ["ffmpeg", "-v", "error"]
    if ss is not None:
        args += ["-ss", str(ss), "-to", str(to)]
    args += ["-i", path, "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", pix, "-"]
    raw = subprocess.run(args, capture_output=True, check=True).stdout
    ch = {"rgba": 4, "gray": 1}[pix]
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, ch) if ch > 1 else np.frombuffer(raw, np.uint8).reshape(-1, h, w)


ROLL = _decode("work/a_roll.mp4", "rgba")
MATTE = _decode("work/a_matte.mp4", "gray")


def _keep_speaker(m):
    """drop matte blobs that aren't the speaker (other swimmers, the ball): keep the largest component."""
    import cv2
    out = np.empty_like(m)
    for i, f in enumerate(m):
        n, lab, st, _ = cv2.connectedComponentsWithStats((f[::4, ::4] > 60).astype(np.uint8), 8)
        if n <= 2:
            out[i] = f
            continue
        big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        keep = cv2.resize((lab == big).astype(np.uint8), (f.shape[1], f.shape[0]), interpolation=cv2.INTER_NEAREST)
        keep = cv2.dilate(keep, np.ones((9, 9), np.uint8))
        out[i] = f * keep
    return out


MATTE = _keep_speaker(MATTE)
RAW_MINI = _decode("work/a_raw.mp4", "rgba", 300, 534)                       # inside the phone graphic
SPLIT_A, SPLIT_B = 22.95, 27.95
RAW_SPLIT = _decode("work/a_raw.mp4", "rgba", ss=SPLIT_A - 0.5, to=SPLIT_B + 0.5)   # RAW side of before/after
NF = len(ROLL)


def fidx(t, n=NF):
    return int(clamp(round(t * FPS), 0, n - 1))


def frame_img(t):
    return skia.Image.fromarray(np.ascontiguousarray(ROLL[fidx(t)]), colorType=skia.kRGBA_8888_ColorType)


def person_img(t, feather=True):
    a = MATTE[fidx(t)]
    rgba = ROLL[fidx(t)].copy()
    k = a.astype(np.uint16)
    rgba[..., :3] = (rgba[..., :3].astype(np.uint16) * k[..., None] // 255).astype(np.uint8)
    rgba[..., 3] = a
    return skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)


# head track (source px) from the matte -> smoothed, used to place text behind the head and to anchor zooms
def _track():
    tops, xs = [], []
    for f in MATTE:
        mk = f > 128
        rows = np.where(mk[:, 100:620].any(1))[0]
        top = rows[0] if len(rows) else 540
        cols = np.where(mk[top:top + 120].any(0))[0]
        tops.append(top)
        xs.append(cols.mean() if len(cols) else 300)
    k = np.ones(21) / 21
    pad = lambda v: np.convolve(np.pad(np.array(v, float), 10, mode="edge"), k, mode="valid")
    return pad(tops), pad(xs)


HEAD_TOP, HEAD_X = _track()


def head(t):
    i = fidx(t)
    return HEAD_X[i] * K0, HEAD_TOP[i] * K0          # screen px at zoom 1


# ---------------------------------------------------------------- word timing helpers
DISPLAY = ("This is my video editing setup. Right now, I'm supposed to be editing videos. But I don't edit anymore. "
           "I built a system that does it for me. Here's how it works. Before I jumped in, I recorded one video on my "
           "phone. Told my system what I wanted, in one line. And came here. While I'm swimming, it cuts the pauses, "
           "removes my mistakes, adds the text, the music, everything. And it's done. And this video you just "
           "watched? Same system. I didn't edit a single second of it. Want to see how my system works? Comment "
           "SYSTEM and I'll send you the details.").split()
assert len(DISPLAY) == len(WORDS), (len(DISPLAY), len(WORDS))
for w, d in zip(WORDS, DISPLAY):
    w["d"] = d


def at(phrase, n=1):
    """start time of the n-th occurrence of a phrase (lowercase, spaces)."""
    p = phrase.split()
    hits = 0
    for i in range(len(WORDS) - len(p) + 1):
        if [w["w"] for w in WORDS[i:i + len(p)]] == p:
            hits += 1
            if hits == n:
                return WORDS[i]["s"]
    raise KeyError(phrase)


def end_of(phrase, n=1):
    p = phrase.split()
    s = at(phrase, n)
    i = next(i for i, w in enumerate(WORDS) if abs(w["s"] - s) < 1e-6)
    return WORDS[i + len(p) - 1]["e"]


# ---------------------------------------------------------------- sections (seconds on the cut)
T_TODO = at("right now")
T_DONT = at("but i don't") - 0.05
T_BUILT = at("i built") - 0.08
T_PAPER = at("here's how") - 0.12
T_STEP1 = at("before i jumped") - 0.12
T_STEP2 = at("told my system") - 0.10
T_CAME = at("and came here") - 0.06
T_SWIM = at("while i'm swimming") - 0.15
T_DONE = at("and it's done") - 0.10
T_CTA = at("want to see") - 0.12
T_COMMENT = at("comment system")
T_SYS = at("system", 5)                     # the spoken word SYSTEM in the CTA
assert abs(T_SYS - (T_COMMENT + 0.3)) < 0.6
SPLIT_A = at("and this video") - 0.06
SPLIT_B = T_CTA


# ---------------------------------------------------------------- camera
def keyz(t, keys):
    """step-wise zoom keys [(t, z_from, z_to, dur)] -> zoom at t (each key eases from z_from to z_to)."""
    z = keys[0][1]
    for (t0, a, b, d) in keys:
        if t >= t0:
            z = lerp(a, b, ease_out_expo(prog(t, t0, d)) if d < 1.0 else ease_in_out_cubic(prog(t, t0, d)))
    return z


ZOOM = [(0.0, 1.22, 1.0, 0.55), (0.55, 1.0, 1.03, 1.3),
        (T_TODO, 1.08, 1.11, T_DONT - T_TODO),
        (T_DONT, 1.0, 1.03, T_BUILT - T_DONT),
        (T_BUILT, 1.06, 1.10, T_PAPER - T_BUILT),
        (T_CAME, 1.18, 1.03, 0.45),
        (T_SWIM, 1.0, 1.03, 1.0),
        (at("cuts the pauses"), 1.12, 1.12, 0.12), (at("removes"), 1.02, 1.02, 0.12),
        (at("adds the text"), 1.10, 1.10, 0.12), (at("the music"), 1.04, 1.04, 0.12),
        (at("everything"), 1.0, 1.02, 0.6),
        (T_DONE, 1.0, 1.03, 0.9),
        (SPLIT_A, 1.0, 1.0, 0.1),
        (T_CTA, 1.10, 1.07, 0.5), (T_COMMENT - 0.05, 1.0, 1.03, 2.0)]


# Framing: never show below the collarbones. The visible source window always ends above this line
# (source px, per take: take 1 sits higher in the water than take 2).
BOTTOM_LIMIT = {1: 1045, 2: 1095}
BASE_Z = 1.25


def take_at(t):
    for sgm in E["segments"]:
        if sgm["out_in"] <= t < sgm["out_out"]:
            return sgm["take"]
    return E["segments"][-1]["take"]


def camera(t):
    """-> (zoom, left, top): the source window shown full-frame. Face-centred, clamped above the chest."""
    z = BASE_Z * keyz(t, ZOOM)
    i = fidx(t)
    hx, ht = HEAD_X[i], HEAD_TOP[i]
    wh, ww = SH / z, SW / z
    top = ht + 210 - 0.56 * wh
    top = max(0.0, min(top, BOTTOM_LIMIT[take_at(t)] - wh))
    left = clamp(hx - ww / 2, 0, SW - ww)
    return z, left, top


def cam_xform(c, z, left, top):
    c.scale(K0 * z, K0 * z)
    c.translate(-left, -top)


def to_screen(px, py, z, left, top):
    return (px - left) * K0 * z, (py - top) * K0 * z


def draw_footage(c, t, img=None, paint=None):
    z, ax, ay = camera(t)
    c.save()
    cam_xform(c, z, ax, ay)
    c.drawImage(img or frame_img(t), 0, 0, CUBIC, paint)
    c.restore()


def draw_person(c, t):
    z, ax, ay = camera(t)
    c.save()
    cam_xform(c, z, ax, ay)
    c.drawImage(person_img(t), 0, 0, CUBIC)
    c.restore()


def head_screen_top(t):
    z, left, top = camera(t)
    i = fidx(t)
    return to_screen(HEAD_X[i], HEAD_TOP[i], z, left, top)


# ---------------------------------------------------------------- generic drawing helpers
def font(name, size):
    from motion_kit import typeface
    f = skia.Font(typeface(name), size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


def rr(c, x, y, w, h, r, color, stroke=None, blur=0):
    p = skia.Paint(Color=color, AntiAlias=True)
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), p)


def soft_shadow(c, x, y, w, h, r, a=0.28, blur=26, dy=14):
    rr(c, x, y + dy, w, h, r, skia.Color(0, 0, 0, int(255 * a)), blur=blur)


def pop(t, t0, d=0.22):
    """0->1 with a little overshoot (UI pops)."""
    return ease_out_back(prog(t, t0, d))


def stroke_path(c, pts, k, color, width, cap=True):
    """draw a polyline progressively (k = 0..1 of its length)."""
    if k <= 0 or len(pts) < 2:
        return
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(seg) * k
    path = skia.Path()
    path.moveTo(*pts[0])
    for i, L in enumerate(seg):
        if total <= 0:
            break
        f = min(1, total / L) if L else 1
        x = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f
        y = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f
        path.lineTo(x, y)
        total -= L
    p = skia.Paint(Color=color, AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=width)
    p.setStrokeCap(skia.Paint.kRound_Cap)
    p.setStrokeJoin(skia.Paint.kRound_Join)
    c.drawPath(path, p)


def quad_pts(p0, p1, p2, n=40):
    return [((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0],
             (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1]) for u in np.linspace(0, 1, n)]


def ellipse_pts(cx, cy, rx, ry, n=80, wobble=0.04, seed=3, turns=1.08):
    rng = np.random.default_rng(seed)
    j = rng.normal(0, wobble, n).cumsum() * 0.15
    return [(cx + rx * (1 + j[i]) * math.cos(-math.pi * 0.62 + turns * 2 * math.pi * i / (n - 1)),
             cy + ry * (1 + j[i]) * math.sin(-math.pi * 0.62 + turns * 2 * math.pi * i / (n - 1))) for i in range(n)]


def highlighter(c, x, y, w, h, k, color=None, seed=1, a=1.0):
    """marker swipe behind a word, drawn left -> right."""
    if k <= 0:
        return
    rng = np.random.default_rng(seed)
    ww = w * ease_out_cubic(k)
    path = skia.Path()
    path.moveTo(x, y + rng.uniform(-4, 4))
    path.lineTo(x + ww, y + rng.uniform(-6, 2))
    path.lineTo(x + ww + rng.uniform(-6, 6), y + h + rng.uniform(-2, 6))
    path.lineTo(x - rng.uniform(0, 8), y + h + rng.uniform(-4, 4))
    path.close()
    c.drawPath(path, skia.Paint(Color=color or col("lime", 0.9 * a), AntiAlias=True))


def check_icon(c, x, y, r, k, fill="lime", ink="ink"):
    if k <= 0:
        return
    s = ease_out_back(clamp(k))
    c.drawCircle(x, y, r * s, skia.Paint(Color=col(fill), AntiAlias=True))
    stroke_path(c, [(x - r * 0.42, y + r * 0.02), (x - r * 0.1, y + r * 0.34), (x + r * 0.45, y - r * 0.32)],
                clamp((k - 0.25) / 0.6), col(ink), r * 0.24)


# ---------------------------------------------------------------- big text behind the subject
def big_stack(c, t, lines, bottom, fade_out_at=None):
    """lines: [(text, font, size_max, color, t_in, tracking)], stacked upward from `bottom` (screen y).
    Each line slams in on its word. Returns nothing; draw the person afterwards to put it behind them."""
    out = 1.0 if fade_out_at is None else 1 - ease_in_cubic(prog(t, fade_out_at, 0.16))
    if out <= 0:
        return
    y = bottom
    for (s, fnt, smax, color, t_in, trk) in reversed(lines):
        size = min(smax, 990 / max(1, text_width(s, 1, fnt, trk)))
        f = font(fnt, size)
        m = f.getMetrics()
        cap = m.fCapHeight if m.fCapHeight else size * 0.7
        h = cap if fnt != F_SERIF else size * 0.78
        cy = y - h / 2
        y -= h + size * (0.10 if fnt != F_SERIF else 0.05)
        k = prog(t, t_in, 0.2)
        if k <= 0:
            continue
        sc = lerp(1.35, 1.0, ease_out_expo(k))
        a = clamp(k * 3) * out
        c.save()
        c.translate(540, cy)
        c.scale(sc, sc)
        text(c, s, 0, 0, size=size, font=fnt, fill=color, align="center", tracking=trk, alpha=a)
        c.restore()


# ---------------------------------------------------------------- captions
def _groups():
    gs, cur = [], []
    for i, w in enumerate(WORDS):
        cur.append(w)
        nxt = WORDS[i + 1] if i + 1 < len(WORDS) else None
        brk = (w["d"][-1] in ".,?!" or w["d"] == "SYSTEM" or len(cur) >= 3 or nxt is None or nxt["s"] - w["e"] > 0.28)
        if brk:
            gs.append(cur)
            cur = []
    return gs


GROUPS = _groups()


def caption_hidden(t):
    hide = [(0.0, T_TODO - 0.02),           # hook big text
            (at("i don't edit") - 0.05, at("i built") - 0.02),           # I DON'T EDIT big text
            (T_PAPER, T_CAME), (T_DONE, SPLIT_A - 0.02),           # paper explainer, DONE
            (T_COMMENT - 0.05, DUR)]
    return any(a <= t < b for a, b in hide)


CAP_Y = 790          # above the head: Meta Reels ads cover the bottom 35% with UI


def draw_captions(c, t, y=CAP_Y, scale=1.0):
    if caption_hidden(t):
        return
    for gi, g in enumerate(GROUPS):
        g_end = GROUPS[gi + 1][0]["s"] - 0.02 if gi + 1 < len(GROUPS) else g[-1]["e"] + 0.4
        g_end = min(g_end, g[-1]["e"] + 0.45)
        if not (g[0]["s"] - 0.04 <= t < g_end):
            continue
        size = 74 * scale
        f = font(F_BODY, size)
        words = [w["d"] for w in g]
        sp = size * 0.26
        widths = [f.measureText(s) for s in words]
        total = sum(widths) + sp * (len(words) - 1)
        x = 540 - total / 2
        k_in = ease_out_back(prog(t, g[0]["s"] - 0.04, 0.16))
        for w, s, wd in zip(g, words, widths):
            active = w["s"] - 0.02 <= t < w["e"] + 0.05
            said = t >= w["s"] - 0.02
            big = 1.0
            if w["w"] == "text" and active:                          # "adds the TEXT" -> the text pops big
                big = 1.0 + 0.55 * math.sin(math.pi * clamp(prog(t, w["s"], w["e"] - w["s"] + 0.05)))
            k = pop(t, w["s"] - 0.03, 0.14) if said else 0.0
            sc = (0.86 + 0.14 * k) * k_in * big
            color = col("lime") if active else col("white", 1.0 if said else 0.72)
            c.save()
            c.translate(x + wd / 2, y)
            c.scale(sc, sc)
            # soft dark halo for legibility on bright water
            p = skia.Paint(Color=skia.Color(0, 0, 0, 120), AntiAlias=True)
            p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14))
            m = f.getMetrics()
            yb = -(m.fAscent + m.fDescent) / 2
            c.drawString(s, -wd / 2, yb + 4, f, p)
            stroke = skia.Paint(Color=skia.Color(0, 0, 0, 150), AntiAlias=True, Style=skia.Paint.kStroke_Style,
                                StrokeWidth=7, StrokeJoin=skia.Paint.kRound_Join)
            c.drawString(s, -wd / 2, yb, f, stroke)
            c.drawString(s, -wd / 2, yb, f, skia.Paint(Color=color, AntiAlias=True))
            c.restore()
            x += wd + sp


# ---------------------------------------------------------------- glass card (frosted water behind it)
def glass(c, t, x, y, w, h, r=40, a=1.0):
    if a <= 0.01:
        return
    c.save()
    c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), True)
    c.saveLayerAlpha(skia.Rect.MakeXYWH(x, y, w, h), int(255 * clamp(a)))
    blur = skia.Paint(ImageFilter=skia.ImageFilters.Blur(10, 10))       # in source px (x1.5 on screen)
    draw_footage(c, t, paint=blur)
    c.drawColor(skia.Color(255, 255, 255, 70))
    c.drawColor(skia.Color(10, 30, 60, 40))
    c.restore()
    c.restore()
    rr(c, x, y, w, h, r, skia.Color(255, 255, 255, int(110 * a)), stroke=2.5)


# ---------------------------------------------------------------- paper world (Vox-style explainer)
def _paper():
    rng = np.random.default_rng(11)
    h, w = 1920, 1080
    base = np.array([242, 238, 227], np.float32)
    n = rng.normal(0, 1, (h // 4, w // 4)).astype(np.float32)
    n = np.kron(n, np.ones((4, 4), np.float32))[:h, :w]
    fine = rng.normal(0, 1, (h, w)).astype(np.float32)
    img = base[None, None, :] + (n * 3.5 + fine * 4.0)[..., None]
    # fibres
    for _ in range(900):
        x0, y0 = rng.uniform(0, w), rng.uniform(0, h)
        ang, ln = rng.uniform(0, math.pi), rng.uniform(6, 26)
        for s in np.linspace(0, ln, int(ln)):
            xi, yi = int(x0 + s * math.cos(ang)), int(y0 + s * math.sin(ang))
            if 0 <= xi < w and 0 <= yi < h:
                img[yi, xi] -= 9
    yy, xx = np.mgrid[0:h, 0:w]
    v = 1 - 0.10 * (((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    img = np.clip(img * v[..., None], 0, 255).astype(np.uint8)
    rgba = np.dstack([img, np.full((h, w), 255, np.uint8)])
    return skia.Image.fromarray(np.ascontiguousarray(rgba), colorType=skia.kRGBA_8888_ColorType)


PAPER = _paper()
_EDGE = np.random.default_rng(5).uniform(-1, 1, 60)


def torn_path(y_top, flip=False):
    """paper sheet from y_top downwards, with a torn top edge."""
    p = skia.Path()
    xs = np.linspace(-20, 1100, len(_EDGE))
    p.moveTo(-20, 2100)
    for x, e in zip(xs, _EDGE):
        p.lineTo(x, y_top + e * 16)
    p.lineTo(1100, 2100)
    p.close()
    return p


STICKER_K, STICKER_DX, STICKER_DY = 1.5, 0, 360       # sticker bottom stays above the chest


def draw_sticker(c, t, y_off):
    """live cut-out of the speaker as a paper sticker: white outline + soft shadow."""
    img = person_img(t)
    c.save()
    c.translate(STICKER_DX, STICKER_DY + y_off)
    c.scale(STICKER_K, STICKER_K)
    dil = skia.ImageFilters.Dilate(7, 7)
    white = skia.ImageFilters.ColorFilter(skia.ColorFilters.Blend(skia.ColorWHITE, skia.BlendMode.kSrcIn), dil)
    shadow = skia.ImageFilters.DropShadowOnly(6, 10, 9, 9, skia.Color(40, 30, 10, 90), dil)
    c.drawImage(img, 0, 0, LIN, skia.Paint(ImageFilter=shadow))
    c.drawImage(img, 0, 0, LIN, skia.Paint(ImageFilter=white))
    c.drawImage(img, 0, 0, CUBIC)
    c.restore()


def pill(c, x, y, s, fill, ink, size=30, pad=22, fnt=F_MONO, a=1.0):
    w = text_width(s, size, fnt, 0.08) + pad * 2
    h = size * 1.75
    rr(c, x, y, w, h, h / 2, col(fill, a))
    text(c, s, x + w / 2, y + h / 2, size=size, font=fnt, fill=col(ink), tracking=0.08, alpha=a)
    return w


def slide_in(t, t0, t1, dist=120):
    """(alpha, dy) for a sub-scene that lives in [t0, t1): enters from below, leaves upward."""
    ki = ease_out_cubic(prog(t, t0, 0.3))
    ko = ease_in_cubic(prog(t, t1 - 0.2, 0.2))
    return clamp(ki - ko), (1 - ki) * dist - ko * dist


def phone(c, t, x, y, w, h, k):
    if k <= 0:
        return
    c.save()
    s = ease_out_back(clamp(k))
    c.translate(x + w / 2, y + h / 2)
    c.rotate(6 * s - 6 + 6)
    c.scale(s, s)
    c.translate(-w / 2, -h / 2)
    soft_shadow(c, 0, 0, w, h, 56, 0.30, 30, 22)
    rr(c, 0, 0, w, h, 56, col("ink"))
    inset = 14
    c.save()
    c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(inset, inset, w - 2 * inset, h - 2 * inset), 44, 44), True)
    fr = RAW_MINI[fidx(t - T_STEP1 + 0.6, len(RAW_MINI))]
    img = skia.Image.fromarray(np.ascontiguousarray(fr), colorType=skia.kRGBA_8888_ColorType)
    sw, shh = w - 2 * inset, h - 2 * inset
    src_h = 534 * 1000 / 1280                                   # crop above the chest
    src_w = src_h * sw / shh
    src = skia.Rect.MakeXYWH(max(0, 122 - src_w / 2), 0, src_w, src_h)
    c.drawImageRect(img, src, skia.Rect.MakeXYWH(inset, inset, sw, shh), LIN)
    # REC overlay
    blink = 1 if int(t * 2) % 2 == 0 else 0.25
    rr(c, inset + 22, inset + 26, 150, 46, 23, skia.Color(0, 0, 0, 140))
    c.drawCircle(inset + 46, inset + 49, 9, skia.Paint(Color=col("red", blink), AntiAlias=True))
    secs = max(0, t - T_STEP1)
    text(c, f"REC 00:{int(secs):02d}", inset + 112, inset + 50, size=22, font=F_MONO, fill=col("white"))
    c.restore()
    rr(c, w / 2 - 60, 26, 120, 30, 15, col("ink"))                      # dynamic island
    c.restore()


def paper_scene(c, t):
    """Vox-style 'how it works' on paper. y_off animates the sheet in/out."""
    k_in = ease_in_out_cubic(prog(t, T_PAPER, 0.34))
    k_out = ease_in_cubic(prog(t, T_CAME - 0.02, 0.34))
    y_off = (1 - k_in) * 2000 + k_out * 2050
    if y_off >= 1990:
        return
    c.save()
    c.clipPath(torn_path(y_off - 30), skia.ClipOp.kIntersect, True)
    c.drawImage(PAPER, 0, 0)
    # torn edge shadow line
    c.restore()
    sh = skia.Paint(Color=skia.Color(0, 0, 0, 60), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=8)
    sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8))
    edge = skia.Path()
    xs = np.linspace(-20, 1100, len(_EDGE))
    edge.moveTo(xs[0], y_off - 30 + _EDGE[0] * 16)
    for x, e in zip(xs[1:], _EDGE[1:]):
        edge.lineTo(x, y_off - 30 + e * 16)
    c.drawPath(edge, sh)

    c.save()
    c.translate(0, y_off)
    # --- E: "HERE'S HOW it works"
    a, dy = slide_in(t, T_PAPER + 0.05, T_STEP1 + 0.04)
    if a > 0:
        c.save()
        c.translate(0, dy)
        text(c, "HERE'S HOW", 540, 470, size=104, font=F_DISPLAY, fill=col("ink"), alpha=a)
        wsz = 190
        ww = text_width("it works.", wsz, F_SERIF)
        highlighter(c, 540 - ww / 2 - 10, 580, ww + 20, 120, prog(t, at("works") - 0.1, 0.35), seed=2, a=a)
        text(c, "it works.", 540, 640, size=wsz, font=F_SERIF, fill=col("ink"), alpha=a)
        c.restore()
    # --- F: STEP 01 record one video on my phone
    a, dy = slide_in(t, T_STEP1 + 0.04, T_STEP2 + 0.04)
    if a > 0:
        c.save()
        c.translate(0, dy)
        pill(c, 70, 300, "STEP 01", "orange", "white", a=a)
        text(c, "Record", 70, 450, size=96, font=F_DISPLAY, fill=col("ink"), align="left", alpha=a)
        sz = 150
        ww = text_width("one video", sz, F_SERIF)
        highlighter(c, 62, 545, ww + 16, 110, prog(t, at("one video") - 0.05, 0.3), seed=4, a=a)
        text(c, "one video", 70, 600, size=sz, font=F_SERIF, fill=col("ink"), align="left", alpha=a)
        text(c, "on my phone.", 74, 735, size=58, font=F_BODY, fill=col("ink"), align="left", alpha=a)
        phone(c, t, 690, 290, 320, 600, prog(t, T_STEP1 + 0.2, 0.45) * a)
        # hand-drawn arrow from the words to the phone
        stroke_path(c, quad_pts((470, 760), (600, 860), (690, 720)), prog(t, at("on my phone") - 0.1, 0.4),
                    col("ink", a), 7)
        k = prog(t, at("on my phone") + 0.25, 0.15)
        if k > 0:
            stroke_path(c, [(662, 712), (692, 718), (684, 748)], k, col("ink", a), 7)
        c.restore()
    # --- G: STEP 02 tell my system what I want, in one line
    a, dy = slide_in(t, T_STEP2 + 0.04, T_CAME + 0.3)
    if a > 0:
        c.save()
        c.translate(0, dy)
        pill(c, 70, 300, "STEP 02", "orange", "white", a=a)
        text(c, "Tell my system", 70, 440, size=78, font=F_DISPLAY, fill=col("ink"), align="left", alpha=a)
        sz = 150
        ww = text_width("what I want.", sz, F_SERIF)
        highlighter(c, 62, 530, ww + 16, 110, prog(t, at("what i wanted") - 0.05, 0.35), seed=6, a=a)
        text(c, "what I want.", 70, 585, size=sz, font=F_SERIF, fill=col("ink"), align="left", alpha=a)
        # prompt card
        kc = ease_out_back(prog(t, T_STEP2 + 0.25, 0.4))
        if kc > 0:
            cy = 690 + (1 - kc) * 60
            soft_shadow(c, 60, cy, 960, 170, 44, 0.3 * a, 26, 18)
            rr(c, 60, cy, 960, 170, 44, col("ink", a))
            text(c, ">", 112, cy + 85, size=50, font=F_MONO, fill=col("lime", a))
            msg = "make it punchy, big text, add music"
            t0, t1 = at("told my") + 0.35, at("in one line") - 0.15
            n = int(len(msg) * clamp(prog(t, t0, t1 - t0)))
            typed = msg[:n]
            text(c, typed, 150, cy + 85, size=40, font=F_BOLD, fill=col("white", a), align="left")
            if (int(t * 3) % 2 == 0 or n < len(msg)) and t < t1 + 0.6:
                cx = 150 + text_width(typed, 40, F_BOLD) + 6
                rr(c, cx, cy + 62, 4, 46, 2, col("lime", a))
            sent = pop(t, at("one line") + 0.05, 0.25)
            c.drawCircle(955, cy + 85, 40 * (1 + 0.15 * math.sin(math.pi * clamp(prog(t, at("one line"), 0.3)))),
                         skia.Paint(Color=col("lime", a), AntiAlias=True))
            stroke_path(c, [(955, cy + 104), (955, cy + 66)], 1, col("ink", a), 7)
            stroke_path(c, [(939, cy + 81), (955, cy + 64), (971, cy + 81)], 1, col("ink", a), 7)
            # "in one line" -> marker circle + note
            stroke_path(c, ellipse_pts(540, cy + 85, 530, 120, seed=8), prog(t, at("in one line"), 0.45),
                        col("orange", a), 8)
            if sent > 0:
                c.save()
                c.translate(800, cy + 255)
                c.rotate(-6)
                c.scale(sent, sent)
                text(c, "just 1 line.", 0, 0, size=72, font=F_HAND, fill=col("orange", a))
                c.restore()
        c.restore()
    draw_sticker(c, t, 0)
    c.restore()


# ---------------------------------------------------------------- footage-section graphics
def todo_card(c, t):
    k = spring(max(0, t - (at("supposed") - 0.1)), 2.4, 0.42) if t >= at("supposed") - 0.1 else 0
    t_off = at("don't") + 0.12
    ko = ease_in_cubic(prog(t, t_off, 0.32))
    if k <= 0 or ko >= 1:
        return
    x, y, w, h = 600, 290, 400, 360
    c.save()
    c.translate(x + w / 2 + ko * 700, y + h / 2 - (1 - min(k, 1)) * 120 - ko * 120)
    c.rotate(-5 + ko * 40)
    c.scale(0.9 + 0.1 * min(k, 1.05), 0.9 + 0.1 * min(k, 1.05))
    c.translate(-w / 2, -h / 2)
    soft_shadow(c, 0, 0, w, h, 10, 0.35, 22, 16)
    c.save()
    c.clipRect(skia.Rect.MakeWH(w, h))
    c.drawImage(PAPER, -200, -200)
    c.restore()
    rr(c, w / 2 - 70, -22, 140, 44, 4, skia.Color(250, 240, 200, 200))     # tape
    text(c, "TODAY", 40, 62, size=54, font=F_HAND, fill=col("orange"), align="left")
    items = ["Edit videos", "Cut the pauses", "Add captions"]
    for i, s in enumerate(items):
        yy = 140 + i * 64
        ki = prog(t, at("supposed") + 0.15 + i * 0.12, 0.2)
        rr(c, 40, yy - 18, 34, 34, 6, col("ink", ki), stroke=4)
        text(c, s, 92, yy, size=40, font=F_HAND, fill=col("ink", ki), align="left")
    text(c, "~ 5 hrs", 40, 330, size=40, font=F_HAND, fill=col("red", prog(t, at("editing videos"), 0.2)), align="left")
    # strike on "don't"
    for i in range(3):
        yy = 140 + i * 64
        stroke_path(c, [(30, yy + 4), (360, yy - 6)], prog(t, at("don't") - 0.15 + i * 0.05, 0.14), col("red"), 8)
    c.restore()


def progress_card(c, t):
    """'my system' at work: frosted card rising from the water."""
    t0 = at("system", 1) - 0.08
    k = ease_out_back(prog(t, t0, 0.42))
    if k <= 0 or t >= T_PAPER + 0.3:
        return
    x, w, h = 110, 860, 200
    y = 300 + (1 - k) * 80
    a = clamp(k)
    glass(c, t, x, y, w, h, 42, a)
    c.drawCircle(x + 48, y + 52, 10, skia.Paint(Color=col("lime", a), AntiAlias=True))
    text(c, "VIBE EDITING SYSTEM", x + 72, y + 54, size=28, font=F_MONO, fill=col("white", a), align="left",
         tracking=0.06)
    text(c, "running", x + w - 40, y + 54, size=28, font=F_MONO, fill=col("lime", a), align="right")
    text(c, "Editing  video_014.mp4", x + 40, y + 112, size=40, font=F_BOLD, fill=col("white", a), align="left")
    pct = 12 * ease_out_cubic(prog(t, t0 + 0.3, 1.2))
    rr(c, x + 40, y + 150, w - 80, 16, 8, col("white", 0.25 * a))
    rr(c, x + 40, y + 150, (w - 80) * pct / 100 + 16, 16, 8, col("lime", a))
    text(c, f"{pct:.0f}%", x + w - 40, y + 112, size=40, font=F_BOLD, fill=col("white", a), align="right")


CHECKS = [("cuts the pauses", "Cut the pauses"), ("removes my mistakes", "Remove my mistakes"),
          ("adds the text", "Add the text"), ("the music", "Add the music"), ("everything", "Everything else")]


def checklist_card(c, t):
    k = ease_out_back(prog(t, T_SWIM + 0.05, 0.45))
    ko = ease_in_cubic(prog(t, T_DONE - 0.12, 0.25))
    if k <= 0 or ko >= 1:
        return
    x, w = 110, 860
    rowh = 52
    h = 96 + rowh * len(CHECKS) + 62
    y = 276 + (1 - k) * 90 - ko * 700
    a = clamp(k) * (1 - ko)
    glass(c, t, x, y, w, h, 44, a)
    pulse = 0.6 + 0.4 * math.sin(t * 8)
    c.drawCircle(x + 48, y + 54, 10, skia.Paint(Color=col("lime", a * pulse), AntiAlias=True))
    text(c, "VIBE EDITING SYSTEM", x + 72, y + 56, size=28, font=F_MONO, fill=col("white", a), align="left",
         tracking=0.06)
    text(c, "editing while you swim", x + w - 40, y + 56, size=24, font=F_MONO, fill=col("lime", a), align="right")
    done = 0
    for i, (cue, label) in enumerate(CHECKS):
        tc = at(cue) if cue != "the music" else at("the music")
        yy = y + 96 + i * rowh + rowh / 2
        kk = prog(t, tc, 0.3)
        done += kk >= 1
        check_icon(c, x + 64, yy, 19, kk if kk > 0 else 0)
        if kk <= 0:
            c.drawCircle(x + 64, yy, 17, skia.Paint(Color=col("white", 0.45 * a), AntiAlias=True,
                                                    Style=skia.Paint.kStroke_Style, StrokeWidth=3))
        text(c, label, x + 100, yy, size=36, font=F_BOLD, fill=col("white", a * (1 if kk > 0 else 0.6)), align="left")
        if label == "Add the music" and kk > 0:                      # little live equaliser
            for b in range(5):
                hb = 8 + 24 * abs(math.sin(t * (7 + b * 1.7) + b))
                rr(c, x + w - 150 + b * 20, yy - hb / 2, 12, hb, 4, col("lime", a))
    # progress
    marks = [0] + [at(cu) for cu, _ in CHECKS]
    pct = sum(20 * ease_out_cubic(prog(t, tc, 0.4)) for tc in marks[1:])
    yb = y + h - 42
    rr(c, x + 40, yb, w - 200, 16, 8, col("white", 0.25 * a))
    rr(c, x + 40, yb, (w - 200) * pct / 100 + 16, 16, 8, col("lime", a))
    text(c, f"{pct:.0f}%", x + w - 40, yb + 8, size=34, font=F_BOLD, fill=col("white", a), align="right")


def notification(c, t):
    t0 = at("it's done") - 0.02
    k = ease_out_back(prog(t, t0, 0.38))
    ko = ease_in_cubic(prog(t, SPLIT_A - 0.05, 0.25))
    if k <= 0 or ko >= 1:
        return
    x, w, h = 60, 960, 150
    y = 285 - (1 - k) * 300 - ko * 320
    c.save()
    soft_shadow(c, x, y, w, h, 44, 0.3, 30, 16)
    glass(c, t, x, y, w, h, 44, 1)
    rr(c, x, y, w, h, 44, col("white", 0.82))
    rr(c, x + 26, y + 30, 90, 90, 22, col("lime"))
    text(c, "V", x + 71, y + 77, size=56, font=F_DISPLAY, fill=col("ink"))
    text(c, "Vibe Editing System", x + 140, y + 54, size=36, font=F_BODY, fill=col("ink"), align="left")
    text(c, "now", x + w - 34, y + 54, size=28, font=F_BOLD, fill=skia.Color(110, 110, 115), align="right")
    text(c, "Your video is ready.", x + 140, y + 104, size=36, font=F_BOLD, fill=skia.Color(60, 60, 65), align="left")
    check_icon(c, x + 140 + text_width("Your video is ready.", 36, F_BOLD) + 34, y + 102, 18,
               prog(t, t0 + 0.25, 0.3))
    c.restore()


def comment_bar(c, t):
    k = ease_out_back(prog(t, T_COMMENT - 0.05, 0.38))
    if k <= 0:
        return
    ko = ease_in_cubic(prog(t, CUT - 0.15, 0.2))
    x, w, h = 70, 940, 112
    y = 285 - (1 - k) * 300
    a = clamp(k) * (1 - ko)
    soft_shadow(c, x, y, w, h, 60, 0.35 * a, 28, 14)
    rr(c, x, y, w, h, 60, col("white", 0.96 * a))
    c.drawCircle(x + 62, y + 60, 38, skia.Paint(Color=col("lime", a), AntiAlias=True))
    text(c, "V", x + 62, y + 62, size=40, font=F_DISPLAY, fill=col("ink", a))
    typed_t = at("system", 5)
    n = int(6 * clamp(prog(t, typed_t - 0.08, 0.3)))
    if n == 0:
        text(c, "Add a comment...", x + 124, y + 62, size=42, font=F_BOLD, fill=skia.Color(150, 150, 155, int(255 * a)),
             align="left")
    else:
        text(c, "SYSTEM"[:n], x + 124, y + 62, size=50, font=F_BODY, fill=col("ink", a), align="left", tracking=0.04)
        if int(t * 3) % 2 == 0:
            cx = x + 124 + text_width("SYSTEM"[:n], 50, F_BODY, 0.04) + 8
            rr(c, cx, y + 36, 4, 50, 2, col("ink", a))
    sp = pop(t, typed_t + 0.3, 0.3)
    kr = pop(t, at("and i'll send") - 0.05, 0.3) * a
    if kr > 0:
        msg = "I'll DM you the details"
        ww = text_width(msg, 30, F_BOLD) + 70
        rr(c, x + 110, y + h + 18, ww * kr, 56, 28, col("ink", 0.85 * kr))
        text(c, msg, x + 145, y + h + 46, size=30, font=F_BOLD, fill=col("lime", kr), align="left")
    text(c, "Post", x + w - 50, y + 62, size=40, font=F_BODY, fill=col("orange" if sp > 0 else "ink", a * (0.4 + 0.6 * clamp(sp))),
         align="right")


def split_scene(c, t):
    """before / after: RAW (straight from the phone) next to FINAL (this edit)."""
    ki = ease_in_out_cubic(prog(t, SPLIT_A, 0.42))
    ko = ease_in_out_cubic(prog(t, SPLIT_B - 0.30, 0.34))
    k = ki * (1 - ko)
    z, left, top = camera(t)
    hx = to_screen(HEAD_X[fidx(t)], 0, z, left, top)[0]        # head x on screen, full-frame
    # FINAL panel: right side, width 1080 -> 540, head kept centred in the panel
    wR = lerp(1080, 540, k)
    xR = 1080 - wR
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(xR, 0, wR, 1920))
    c.translate(lerp(0, xR + wR / 2 - hx, k), 0)
    draw_footage(c, t)
    c.restore()
    if k <= 0:
        return
    # RAW panel slides in from the left
    xL = lerp(-540, 0, k)
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(xL, 0, 540, 1920))
    i = int(clamp(round((t - (SPLIT_A - 0.5)) * FPS), 0, len(RAW_SPLIT) - 1))
    img = skia.Image.fromarray(np.ascontiguousarray(RAW_SPLIT[i]), colorType=skia.kRGBA_8888_ColorType)
    c.translate(xL + 270 - hx, 0)
    cam_xform(c, z, left, top)                                  # same chest-safe framing as the edit
    c.drawImage(img, 0, 0, CUBIC)
    c.restore()
    c.save()
    c.translate(xL, 0)
    # raw-camera overlay: REC + timecode, desaturated look handled by the source (ungraded)
    blink = 1 if int(t * 2) % 2 == 0 else 0.3
    c.drawCircle(56, 468, 10, skia.Paint(Color=col("red", blink), AntiAlias=True))
    tc = 25.70 + (t - SPLIT_A)
    text(c, f"00:00:{int(tc):02d}:{int((tc % 1) * 30):02d}", 78, 470, size=26, font=F_MONO, fill=col("white"),
         align="left")
    c.restore()
    # divider
    rr(c, 537, 0, 6, 1920, 3, col("white", k))
    # labels
    a = clamp(prog(t, SPLIT_A + 0.25, 0.25)) * (1 - ko)
    if a > 0:
        wl = pill(c, xL + 40, 300, "RAW", "white", "ink", size=34, a=a)
        text(c, "straight from my phone", xL + 44, 400, size=30, font=F_BOLD, fill=col("white", a), align="left")
        pulse = 1 + 0.12 * math.sin(math.pi * clamp(prog(t, at("same system"), 0.5)))
        c.save()
        c.translate(580, 300)
        c.scale(pulse, pulse)
        pill(c, 0, 0, "FINAL", "lime", "ink", size=34, a=a)
        c.restore()
        text(c, "edited by my system", 584, 400, size=30, font=F_BOLD, fill=col("white", a), align="left")
    # "my editing time" badge on "didn't edit"
    kb = ease_out_back(prog(t, at("didn't edit") - 0.05, 0.35)) * (1 - ko)
    if kb > 0:
        c.save()
        c.translate(540, 560)
        c.scale(kb, kb)
        soft_shadow(c, -300, -80, 600, 170, 34, 0.35, 26, 14)
        rr(c, -300, -80, 600, 170, 34, col("ink"))
        text(c, "MY EDITING TIME", 0, -36, size=28, font=F_MONO, fill=col("lime"), tracking=0.1)
        colon = ":" if int(t * 2) % 2 == 0 else " "
        text(c, f"00{colon}00{colon}00", 0, 36, size=78, font=F_DISPLAY, fill=col("white"))
        c.restore()
    c.save()
    c.translate(0, 0)
    c.restore()


# ---------------------------------------------------------------- end card: the receipt
RECEIPT = [("Raw footage", "77.2 s"), ("Final cut", f"{CUT:.1f} s"), ("Takes combined", "2"),
           ("Pauses & retakes cut", f"{77.2 - CUT:.1f} s"), ("Timeline opened", "0")]


def end_card(c, t):
    te = t - CUT
    c.drawColor(col("ink"))
    c.save()
    c.translate(540, 282)
    c.scale(0.84, 0.84)
    c.translate(-540, -300)
    # receipt prints down from a slot
    slot_y = 300
    rr(c, 150, slot_y - 18, 780, 36, 18, skia.Color(40, 40, 44))
    kp = ease_out_cubic(clamp(te / 1.1))
    rh = 860
    shown = rh * kp
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(0, slot_y, 1080, 1700))
    y0 = slot_y - rh + shown
    p = skia.Path()
    p.moveTo(190, y0)
    p.lineTo(890, y0)
    p.lineTo(890, y0 + rh)
    for i in range(28):
        xx = 890 - (i + 0.5) * 25
        p.lineTo(xx, y0 + rh + (14 if i % 2 == 0 else 0))
    p.lineTo(190, y0 + rh)
    p.close()
    c.drawPath(p, skia.Paint(Color=col("paper"), AntiAlias=True))
    text(c, "RECEIPT", 540, y0 + 90, size=58, font=F_DISPLAY, fill=col("ink"))
    text(c, "THIS VIDEO", 540, y0 + 150, size=26, font=F_MONO, fill=col("ink"), tracking=0.2)
    dash = "- " * 23
    text(c, dash, 540, y0 + 200, size=24, font=F_MONO, fill=col("ink", 0.5))
    for i, (k_, v) in enumerate(RECEIPT):
        yy = y0 + 270 + i * 74
        text(c, k_, 230, yy, size=32, font=F_MONO, fill=col("ink"), align="left")
        text(c, v, 850, yy, size=32, font=F_MONO, fill=col("ink"), align="right")
    text(c, dash, 540, y0 + 650, size=24, font=F_MONO, fill=col("ink", 0.5))
    text(c, "EDITED BY ME", 230, y0 + 720, size=38, font=F_DISPLAY, fill=col("ink"), align="left")
    text(c, "0:00", 850, y0 + 720, size=46, font=F_DISPLAY, fill=col("ink"), align="right")
    hk = prog(te, 1.05, 0.35)
    highlighter(c, 214, y0 + 685, 650, 72, hk, col("lime", 0.95), seed=9)
    if hk > 0:
        text(c, "EDITED BY ME", 230, y0 + 720, size=38, font=F_DISPLAY, fill=col("ink"), align="left")
        text(c, "0:00", 850, y0 + 720, size=46, font=F_DISPLAY, fill=col("ink"), align="right")
    c.restore()
    c.restore()
    # lockup + CTA
    kl = ease_out_expo(prog(te, 1.25, 0.5))
    if kl > 0:
        text(c, "THE", 540, 1062 + (1 - kl) * 40, size=34, font=F_MONO, fill=col("white", kl), tracking=0.3)
        text(c, "VIBE EDITING", 540, 1136 + (1 - kl) * 40, size=86, font=F_DISPLAY, fill=col("lime", kl))
        text(c, "SYSTEM", 540, 1226 + (1 - kl) * 40, size=86, font=F_DISPLAY, fill=col("white", kl))
    kc = pop(te, 1.6, 0.35)
    if kc > 0:
        c.save()
        c.translate(540, 1345)
        c.scale(kc, kc)
        w = text_width('Comment "SYSTEM"', 40, F_BODY) + 80
        rr(c, -w / 2, -42, w, 84, 42, col("white"))
        text(c, 'Comment "SYSTEM"', 0, 0, size=40, font=F_BODY, fill=col("ink"))
        c.restore()


# ---------------------------------------------------------------- the frame
def draw(c, t):
    c.clear(col("ink"))
    if t >= CUT:
        end_card(c, t)
        # flash into the end card
        fl = 1 - prog(t, CUT, 0.18)
        if fl > 0:
            c.drawColor(skia.Color(255, 255, 255, int(200 * fl)))
        return

    if SPLIT_A <= t < SPLIT_B:
        split_scene(c, t)
        draw_captions(c, t, y=CAP_Y)
        return

    paper_full = T_PAPER + 0.36 <= t < T_CAME - 0.02
    if not paper_full:
        draw_footage(c, t)
        # ----- big text behind the person
        ht = head_screen_top(t)[1]
        bottom = min(ht + 95, 1050)
        drew = False
        if t < T_TODO + 0.1:
            big_stack(c, t, [("this is my video", F_SERIF, 112, col("white"), at("this is my") - 0.02, 0),
                             ("EDITING", F_IMPACT, 280, col("white"), at("editing setup") - 0.02, 0.01),
                             ("SETUP.", F_IMPACT, 300, col("lime"), at("setup") - 0.02, 0.01)],
                      bottom, fade_out_at=T_TODO - 0.12)
            drew = True
        elif T_DONT - 0.02 <= t < T_BUILT + 0.1:
            big_stack(c, t, [("I DON'T", F_IMPACT, 200, col("white"), at("i don't edit") - 0.02, 0.02),
                             ("EDIT.", F_IMPACT, 380, col("lime"), at("edit anymore") - 0.02, 0.02)],
                      bottom, fade_out_at=T_BUILT - 0.1)
            drew = True
        elif T_DONE <= t < SPLIT_A:
            big_stack(c, t, [("DONE.", F_IMPACT, 420, col("lime"), at("done") - 0.04, 0.02)], bottom)
            drew = True
        elif t >= T_COMMENT - 0.1:
            big_stack(c, t, [("SYSTEM", F_IMPACT, 380, col("lime"), T_SYS - 0.03, 0.02)],
                      bottom, fade_out_at=CUT - 0.12)
            drew = True
        if drew:
            draw_person(c, t)
        # ----- section graphics
        if T_TODO - 0.2 <= t < T_BUILT:
            todo_card(c, t)
        if T_BUILT <= t < T_PAPER + 0.4:
            progress_card(c, t)
        if T_SWIM - 0.1 <= t < SPLIT_A:
            checklist_card(c, t)
        if T_DONE <= t < SPLIT_A + 0.3:
            notification(c, t)
        if t >= T_CTA:
            comment_bar(c, t)
        # flash + punch on the cut back from paper
        if T_CAME <= t < T_CAME + 0.4:
            pass
        draw_captions(c, t, y=CAP_Y)
    if T_PAPER <= t < T_CAME + 0.4:
        paper_scene(c, t)


# ---------------------------------------------------------------- finishing: light grain (precomputed)
_GR = [np.random.default_rng(i).normal(0, 4.2, (1920 // 2, 1080 // 2)).astype(np.float32) for i in range(6)]


def post(arr, t):
    g = _GR[int(t * FPS) % len(_GR)]
    g = np.kron(g, np.ones((2, 2), np.float32))[:, :, None]
    return np.clip(arr.astype(np.float32) + g, 0, 255).astype(np.uint8)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stills"
    if cmd == "stills":
        ts = [float(x) for x in sys.argv[2:]] or [0.5, 1.4, 3.2, 5.6, 7.5, 9.0, 11.5, 14.5, 15.9, 19.0, 22.6, 25.0,
                                                    27.0, 30.4, 33.8]
        S.stills(draw, ts, post=post)
    elif cmd == "draft":
        S.render(draw, "out/draft.mp4", draft=True, post=post)
    elif cmd == "render":
        a = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
        b = float(sys.argv[3]) if len(sys.argv) > 3 else None
        S.render(draw, "work/picture.mp4", post=post, start=a, end=b, crf=14)
