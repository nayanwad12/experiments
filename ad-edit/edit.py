"""TIME ad: the full edit of the raw take ("You're not bad at content...").

    python3 edit.py info                  -> the cut list
    python3 edit.py stills 1.0 4.2 ...    -> out/stills/*.png (half res)
    python3 edit.py sheet                 -> out/sheet.png
    python3 edit.py render [--draft]      -> out/vibe_edit_time.mp4
    python3 edit.py audio                 -> work/mix.wav

Look: "gallery white" editorial. Warm paper, ink black, signature lime, alert orange. Inter Tight Black for
kinetic type behind the speaker (person matte), Instrument Serif italic for asides, JetBrains Mono for UI.
Every cue is read off the spoken words (work/words.json), so pauses are cut and graphics land on the word.
"""

import json
import math
import re
import sys
from pathlib import Path

import cv2
import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "reels" / "common"))
import kit  # noqa: E402
from kit import clamp, e_back, e_in, e_io, e_out, fill, font, hrand, lerp, measure, prog, spring, stroke  # noqa: E402
from vibelib import ff, loudnorm_filter  # noqa: E402

W, H, FPS = 1080, 1920, 30
OUT = HERE / "out"
FR = HERE / "work" / "frames"
NSRC = len(list(FR.glob("f_*.jpg")))
FACE = (540, 820)
SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNone)

PAPER = "#F3F0E8"
PAPER2 = "#E9E4D8"
INK = "#0B0B0D"
INK2 = "#17171B"
LIME = "#D4FF3F"
ORANGE = "#FF5A1F"
WHITE = "#FFFFFF"
GREY = "#8C8A84"
PERI = "#C4C6FF"


def col(c, a=1.0):
    r, g, b = kit.rgb(c)
    return skia.Color(r, g, b, int(255 * clamp(a)))


def trim(p, k):
    """draw-on: keep the first k (0..1) of the stroke (k <= 0 hides it)."""
    if k <= 0:
        p.setAlphaf(0)
    elif k < 1:
        p.setPathEffect(skia.TrimPathEffect.Make(0, float(k)))
    return p


def e_expo(k):
    k = clamp(k)
    return 1 if k >= 1 else 1 - 2 ** (-10 * k)


# ================================================================== words + edit decision list
WORDS = json.loads((HERE / "work" / "words.json").read_text())
for i, w in enumerate(WORDS):
    w["i"] = i
    w["k"] = re.sub(r"[^a-z0-9']", "", w["d"].lower())
SRC_END = 41.7


def _find(seq, n=1):
    toks = re.sub(r"[^a-z0-9' ]", "", seq.lower()).split()
    hits = 0
    for i in range(len(WORDS) - len(toks) + 1):
        if all(WORDS[i + j]["k"] == toks[j] for j in range(len(toks))):
            hits += 1
            if hits == n:
                return i, i + len(toks) - 1
    raise KeyError(seq)


def build_edl():
    runs = []
    for w in WORDS:
        if runs and w["s"] - runs[-1][1] < 0.16:
            runs[-1][1] = w["e"]
        else:
            runs.append([w["s"], w["e"]])
    edl, t = [], 0.0
    for k, (a, b) in enumerate(runs):
        pe = runs[k - 1][1] if k else 0.0
        ns = runs[k + 1][0] if k + 1 < len(runs) else SRC_END
        a = max(a - 0.06, (pe + a) / 2)
        b = min(b + 0.09, (b + ns) / 2) if k + 1 < len(runs) else SRC_END
        edl.append((a, b, t))
        t += b - a
    return edl, t


EDL, TOTAL = build_edl()


def src_at(t):
    for a, b, o in EDL:
        if t < o + (b - a):
            return a + (t - o)
    a, b, o = EDL[-1]
    return b


def out_of(ts):
    for a, b, o in EDL:
        if a - 1e-6 <= ts <= b + 1e-6:
            return o + ts - a
    best = min(EDL, key=lambda s: min(abs(ts - s[0]), abs(ts - s[1])))
    return best[2] + clamp(ts - best[0], 0, best[1] - best[0])


for w in WORDS:
    w["os"], w["oe"] = out_of(w["s"]), out_of(w["e"])
CUTS = [o for a, b, o in EDL[1:]]


class P:
    """a spoken phrase on the output clock."""

    def __init__(self, seq, n=1):
        self.i0, self.i1 = _find(seq, n)
        self.s, self.e = WORDS[self.i0]["os"], WORDS[self.i1]["oe"]

    def w(self, j):
        return WORDS[self.i0 + j]["os"]

    def we(self, j):
        return WORDS[self.i0 + j]["oe"]


NOTBAD = P("you are not bad at content")
LOSING = P("you are just losing three hours editing every single reel")
WHY = P("and that's why you post twice a week instead of every day")
FIX = P("and here is the fix")
CALLED = P("it's called the vibe editing")
REC = P("you record")
TELL = P("you tell the system what you want")
CUTP = P("cut the pauses")
PUNCHY = P("punchy captions")
CINE = P("cinematic look")
ADDM = P("add music")
EDITS = P("and it edits the whole thing for you")
FEAT = P("cuts captions effects sound")
READY = P("ready for reels feed and youtube")
NO = P("no timeline no keyframes no editor")
PROOF = P("this video recorded on my phone")
EDBY = P("edited by the system")
IFW = P("and if you want to post every day without editing every day")
GET = P("get the vibe editing system")
TAP = P("tap learn more")
END_A = TAP.e + 0.35

# section boundaries (output clock)
T_FIX = FIX.s - 0.05
T_REC = REC.s - 0.05
T_DROP = ADDM.w(1)
T_FEAT = FEAT.s - 0.06
T_READY = READY.s - 0.06
T_NO = NO.s - 0.06
T_PROOF = PROOF.s - 0.06
T_IFW = IFW.s - 0.06
T_GET = GET.s - 0.06

# ================================================================== source frames
_cache = {}


def frame_rgb(fi):
    fi = int(clamp(fi, 0, NSRC - 1))
    if fi not in _cache:
        if len(_cache) > 16:
            _cache.pop(next(iter(_cache)))
        _cache[fi] = cv2.imread(str(FR / f"f_{fi + 1:05d}.jpg"))[..., ::-1].copy()
    return _cache[fi]


_ALPHA = None


def alpha_small(fi):
    global _ALPHA
    if _ALPHA is None:
        _ALPHA = np.load(HERE / "work" / "alpha.npy", mmap_mode="r")
    return np.asarray(_ALPHA[int(clamp(fi, 0, len(_ALPHA) - 1))])


def _curve(x, lift=0.0, gamma=1.0, gain=1.0, s=0.0):
    y = np.clip(x, 0, 1) ** gamma
    y = y + s * np.sin(2 * math.pi * (y - 0.5)) / (2 * math.pi) * -1
    return np.clip(lift + y * (gain - lift), 0, 1)


def _luts():
    x = np.arange(256, dtype=np.float32) / 255
    warm = [np.clip(_curve(x, 0.015, 0.9, 1.06, 0.5) * k, 0, 1) for k in (1.0, 1.0, 1.035)]
    cine = [_curve(x, 0.045, 1.06, 0.97, 0.9) * 1.03,
            _curve(x, 0.05, 1.04, 0.98, 0.9),
            np.clip(_curve(x, 0.075, 1.02, 0.95, 0.9) * 1.0 + 0.012 * (1 - x), 0, 1)]
    return {k: [(np.clip(c, 0, 1) * 255).astype(np.uint8) for c in v] for k, v in (("warm", warm), ("cine", cine))}


LUTS = _luts()


def grade(rgb, look="warm"):
    if look == "raw":
        return rgb
    lut = LUTS[look]
    o = np.empty_like(rgb)
    for ch in range(3):
        o[..., ch] = lut[ch][rgb[..., ch]]
    f = o.astype(np.float32)
    lum = f @ np.array([0.299, 0.587, 0.114], np.float32)
    sat = 1.12 if look == "warm" else 0.92
    f = lum[..., None] + (f - lum[..., None]) * sat
    if look == "cine":       # teal shadows, warm highlights
        t = (lum / 255.0)[..., None]
        f += (1 - t) ** 2 * np.array([-6, 4, 10], np.float32) + t ** 2 * np.array([8, 3, -6], np.float32)
    return np.clip(f, 0, 255).astype(np.uint8)


_KER = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))


class Src:
    def __init__(self, ts, look="warm"):
        self.fi = int(round(ts * FPS))
        self.rgb = grade(frame_rgb(self.fi), look)
        self._a = None

    @property
    def alpha(self):
        if self._a is None:
            a = cv2.erode(alpha_small(self.fi), _KER)
            a = cv2.GaussianBlur(a, (3, 3), 0)
            self._a = cv2.resize(a, (W, H), interpolation=cv2.INTER_LINEAR)
        return self._a

    def bg(self):
        return skia.Image.fromarray(np.dstack([self.rgb, np.full((H, W), 255, np.uint8)]),
                                    colorType=skia.kRGBA_8888_ColorType)

    def person(self):
        return skia.Image.fromarray(np.dstack([self.rgb, self.alpha]), colorType=skia.kRGBA_8888_ColorType)

    def outline(self, px=10, color=(255, 255, 255)):
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1))
        d = cv2.resize(cv2.dilate(alpha_small(self.fi), k), (W, H), interpolation=cv2.INTER_LINEAR)
        arr = np.zeros((H, W, 4), np.uint8)
        arr[..., :3] = color
        arr[..., 3] = d
        return skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType)


# ================================================================== camera
ZL = [1.0, 1.07, 1.03, 1.09, 1.01, 1.06]
SHAKES = []


def camera(t):
    k = max([i for i, s in enumerate([0.0] + CUTS) if s <= t + 1e-6] or [0])
    starts = [0.0] + CUTS
    z = ZL[k % len(ZL)] * (1 + 0.014 * (t - starts[k]))
    if t < 0.45:
        z *= lerp(1.32, 1.0, e_expo(t / 0.45))
    if T_DROP <= t < T_FEAT:                                     # pump on the beat after the drop
        ph = ((t - T_DROP) % BEAT) / BEAT
        z *= 1 + 0.03 * (1 - ph) ** 3
    if GET.s <= t < END_A:
        z = lerp(z, 1.0, e_out(prog(t, GET.s, 0.3)))
    dx = dy = rot = 0.0
    for st, amp in SHAKES:
        if st <= t < st + 0.3:
            q = 1 - (t - st) / 0.3
            dx += amp * q * math.sin(t * 93.0)
            dy += amp * q * math.sin(t * 71.0 + 1)
            rot += amp * 0.05 * q * math.sin(t * 57.0)
    return z, dx, dy, rot


def apply_cam(c, cam, anchor=FACE):
    z, dx, dy, rot = cam
    c.translate(anchor[0] + dx, anchor[1] + dy)
    c.rotate(rot)
    c.scale(z, z)
    c.translate(-anchor[0], -anchor[1])


BEAT = 60 / 140.0     # replaced by the song's real tempo in music_plan()

# ================================================================== kinetic captions (behind the speaker)
STYLE = {}


def style(seq, s, n=1, words=None):
    i0, i1 = _find(seq, n)
    for i in range(i0, i1 + 1):
        if words is None or WORDS[i]["k"] in words:
            STYLE[i] = s


style("you are not bad at content", "serif", words={"content"})
style("not bad", "hot")
style("three hours", "hot")
style("every single reel", "serif", words={"reel"})
style("twice a week", "hot")
style("every day", "serif")
style("and here is the fix", "lime", words={"fix"})
style("you record", "serif", words={"record"})
style("what you want", "serif", words={"want"})
style("cut the pauses", "lime", words={"pauses"})
style("punchy captions", "lime", words={"punchy"})
style("cinematic look", "serif", words={"cinematic"})
style("add music", "lime", words={"music"})
style("the whole thing for you", "serif", words={"you"})
style("cuts captions effects sound", "ink")
style("no timeline no keyframes no editor", "strike", words={"timeline", "keyframes", "editor"})
style("every day", "lime", n=2)
style("without editing every day", "strike", words={"editing"})


GROUP_TEXT = ["you are not bad", "at content", "you are just losing", "three hours", "editing every single reel",
              "and that's why you post", "twice a week", "instead of every day", "and here is the fix",
              "it's called the", "vibe editing", "you record", "you tell the system", "what you want",
              "cut the pauses", "punchy captions", "cinematic look", "add music", "and it edits", "the whole thing",
              "for you", "cuts", "captions", "effects", "sound", "ready for reels", "feed and youtube",
              "no timeline", "no keyframes", "no editor", "this video", "recorded on my phone", "edited by the system",
              "and if you want", "to post every day", "without editing", "every day", "get the vibe editing system",
              "tap", "learn more"]


def _groups():
    gs, i = [], 0
    for txt in GROUP_TEXT:
        n = len(txt.split())
        assert [w["k"] for w in WORDS[i:i + n]] == re.sub(r"[^a-z0-9' ]", "", txt).split(), txt
        gs.append(WORDS[i:i + n])
        i += n
    assert i == len(WORDS)
    return gs


GROUPS = _groups()


def wtxt(w):
    s = w["d"].strip(",.?")
    if STYLE.get(w["i"]) == "serif":
        return s.lower()
    return s.upper()


def wfont(w):
    return "italic" if STYLE.get(w["i"]) == "serif" else "black"


def wsize(w, size):
    return size * 1.22 if STYLE.get(w["i"]) == "serif" else size


def layout(g, max_w=960):
    """-> (size, lines[[w..]])"""
    gap = 0.22
    for size in (230, 210, 190, 172, 156, 142):
        tot = sum(measure(wtxt(w), wfont(w), wsize(w, size)) for w in g) + gap * size * (len(g) - 1)
        if tot <= max_w:
            return size, [g]
    size = 150
    # two lines: best split
    best = None
    for k in range(1, len(g)):
        a, b = g[:k], g[k:]
        wa = sum(measure(wtxt(w), wfont(w), wsize(w, size)) for w in a) + gap * size * (len(a) - 1)
        wb = sum(measure(wtxt(w), wfont(w), wsize(w, size)) for w in b) + gap * size * (len(b) - 1)
        m = max(wa, wb)
        if best is None or m < best[0]:
            best = (m, [a, b])
    m, lines = best
    if m > max_w:
        size *= max_w / m
    return size, lines


LAYOUT = [layout(g) for g in GROUPS]


def cur_group(t):
    for k, g in enumerate(GROUPS):
        nxt = GROUPS[k + 1][0]["os"] - 0.03 if k + 1 < len(GROUPS) else g[-1]["oe"] + 0.6
        if g[0]["os"] - 0.05 <= t < nxt:
            if t > g[-1]["oe"] + 0.9:
                return None
            return k
    return None


def draw_word(c, w, x, base, size, t, color, accent):
    """one kinetic word: masked slide-up reveal + its accent."""
    s, fn, sz = wtxt(w), wfont(w), wsize(w, size)
    st = STYLE.get(w["i"])
    k = e_expo(prog(t, w["os"] - 0.05, 0.32))
    if k <= 0:
        return
    wd = measure(s, fn, sz)
    capH = font(fn, sz).getMetrics().fCapHeight
    c.save()
    c.clipRect(skia.Rect.MakeLTRB(x - 30, base - capH * 1.35, x + wd + 30, base + sz * 0.3))
    dy = (1 - k) * sz * 0.95
    c.translate(0, dy)
    tc = color
    if st == "lime":
        hk = e_expo(prog(t, w["os"], 0.3))
        r = skia.Rect.MakeLTRB(x - 16, base - capH - 18, x - 16 + (wd + 32) * hk, base + 18)
        c.drawRect(r, fill(LIME))
        tc = INK
    elif st == "hot":
        tc = ORANGE
    elif st == "serif":
        tc = accent
    kit.text(c, s, x, base, fn, sz, color=tc, anchor="l")
    c.restore()
    if st == "strike":
        sk = e_out(prog(t, w["oe"] - 0.02, 0.22))
        if sk > 0:
            y = base - capH * 0.45
            p = stroke(ORANGE, sz * 0.11)
            path = skia.Path()
            path.moveTo(x - 14, y + 6)
            path.quadTo(x + wd * 0.5, y - 10, x + wd + 14, y - 2)
            trim(p, sk)
            c.drawPath(path, p)


def behind_caps(c, t, color=INK, accent=ORANGE, y0=None, a=1.0):
    k = cur_group(t)
    if k is None:
        return
    g = GROUPS[k]
    size, lines = LAYOUT[k]
    gap = 0.22 * size
    lh = size * 0.98
    base0 = (y0 or 495) - (len(lines) - 1) * lh
    if a < 1:
        c.saveLayerAlpha(None, int(255 * a))
    for li, line in enumerate(lines):
        ws = [measure(wtxt(w), wfont(w), wsize(w, size)) for w in line]
        tot = sum(ws) + gap * (len(line) - 1)
        x = 540 - tot / 2
        base = base0 + li * lh
        for w, wd in zip(line, ws):
            draw_word(c, w, x, base, size, t, color, accent)
            x += wd + gap
    if a < 1:
        c.restore()


def front_caps(c, t, y=1500, size=74):
    """small pill captions in front (used when the top of the frame is busy)."""
    k = cur_group(t)
    if k is None:
        return
    g = GROUPS[k]
    words = [w["d"].strip(",.?").upper() for w in g]
    gap = size * 0.26
    ws = [measure(s, "black", size) for s in words]
    tot = sum(ws) + gap * (len(ws) - 1)
    sc = min(1.0, 900 / tot)
    c.save()
    c.translate(540, y)
    c.scale(sc, sc)
    x = -tot / 2
    capH = font("black", size).getMetrics().fCapHeight
    for w, s, wd in zip(g, words, ws):
        if t < w["os"] - 0.04:
            break
        kk = spring(clamp(t - w["os"] + 0.04, 0, 0.4), w=24, z=0.55)
        on = w["os"] - 0.04 <= t < w["oe"] + 0.05 or w is g[-1]
        c.save()
        c.translate(x + wd / 2, -capH / 2)
        c.scale(0.7 + 0.3 * kk, 0.7 + 0.3 * kk)
        if on:
            c.drawRRect(kit.rrect(-wd / 2 - 16, -capH / 2 - 16, wd + 32, capH + 32, 14), fill(LIME))
        kit.text(c, s, 0, capH / 2, "black", size, color=INK if on else WHITE, anchor="c",
                 shadow=0 if on else 10)
        c.restore()
        x += wd + gap
    c.restore()


# ================================================================== backgrounds
def paper_bg(c, color=PAPER, grid=False, a=1.0):
    c.drawRect(skia.Rect.MakeWH(W, H), fill(color, a))
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=skia.GradientShader.MakeRadial(
        (540, 760), 1250, [col(WHITE, 0.55), col(WHITE, 0.0), col("#000000", 0.10)], [0, 0.55, 1])))
    if grid:
        p = stroke("#000000", 1.5, 0.07)
        for x in range(0, W + 1, 60):
            c.drawLine(x, 0, x, H, p)
        for y in range(0, H + 1, 60):
            c.drawLine(0, y, W, y, p)


def ink_bg(c, t, glow=LIME, ga=0.18):
    c.drawRect(skia.Rect.MakeWH(W, H), fill(INK))
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=skia.GradientShader.MakeRadial(
        (540, 700), 900, [col(glow, ga), col(glow, 0.0)], [0, 1])))
    # fine dot grid
    p = fill(WHITE, 0.07)
    path = skia.Path()
    for y in range(30, H, 54):
        for x in range(27, W, 54):
            path.addCircle(x, y, 1.8)
    c.drawPath(path, p)


def lime_bg(c, t):
    c.drawRect(skia.Rect.MakeWH(W, H), fill(LIME))
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=skia.GradientShader.MakeRadial(
        (540, 760), 1200, [col(WHITE, 0.35), col(WHITE, 0.0), col("#5A7000", 0.25)], [0, 0.6, 1])))


def halftone(c, cx, cy, r_max, color, spacing=26, dot=10, a=1.0):
    path = skia.Path()
    n = int(r_max / spacing) + 2
    for iy in range(-n, n + 1):
        for ix in range(-n, n + 1):
            x, y = ix * spacing + (spacing / 2 if iy % 2 else 0), iy * spacing
            d = math.hypot(x, y) / r_max
            if d < 1:
                rr = dot * (1 - d) ** 0.8
                if rr > 0.6:
                    path.addCircle(cx + x, cy + y, rr)
    c.drawPath(path, fill(color, a))


def bg_kind(t):
    """(kind, start of this kind, transition style)"""
    plan = [(0.0, "wall", None), (WHY.s - 0.06, "paper", "slide"), (T_FIX, "ink", "flash"),
            (T_REC, "wall", "iris"), (T_DROP, "inkbars", "flash"),
            (T_FEAT, "lime", "wipe"), (T_READY, "ready", "scale"), (T_NO, "vox", "slide"),
            (T_PROOF, "wall", "iris"), (T_IFW, "paper", "wipe"), (T_GET, "ink", "flash")]
    cur = plan[0]
    prev = None
    for p in plan:
        if t >= p[0]:
            prev, cur = cur, p
    return cur, prev


def draw_bg(c, kind, t, src):
    if kind == "wall":
        c.drawImage(src.bg(), 0, 0, SAMP)
    elif kind == "paper":
        paper_bg(c, PAPER)
    elif kind == "ink":
        ink_bg(c, t)
    elif kind == "inkbars":
        ink_bg(c, t, LIME, 0.12)
    elif kind == "lime":
        lime_bg(c, t)
    elif kind == "vox":
        paper_bg(c, PAPER2, grid=True)
        halftone(c, 900, 260, 520, "#CFC6B2", 28, 11, 0.9)
        halftone(c, 120, 1500, 640, "#CFC6B2", 30, 12, 0.9)
    else:
        ink_bg(c, t)


def reveal_mask(c, style_, k):
    """clip to the revealed part of the incoming background."""
    if style_ == "iris":
        c.clipPath(skia.Path().addCircle(540, 780, 1400 * e_io(k)), skia.ClipOp.kIntersect, True)
    elif style_ == "wipe":
        x = W * 1.4 * e_io(k)
        path = skia.Path()
        path.moveTo(-300, 0)
        path.lineTo(x, 0)
        path.lineTo(x - 300, H)
        path.lineTo(-300, H)
        path.close()
        c.clipPath(path, skia.ClipOp.kIntersect, True)
    elif style_ == "slide":
        c.clipRect(skia.Rect.MakeLTRB(0, H * (1 - e_io(k)), W, H))
    # flash / scale: hard switch


# ================================================================== scene graphics
def halo_clock(c, t):
    """an orange clock ring around the head while "three hours editing every single reel" plays."""
    a0, a1 = LOSING.w(4) - 0.15, WHY.s - 0.06
    if not (a0 <= t < a1):
        return
    k = e_out(prog(t, a0, 0.4)) * (1 - e_in(prog(t, a1 - 0.2, 0.2)))
    cx, cy, r = 540, 770, 380 + 30 * (1 - k)
    c.drawCircle(cx, cy, r, stroke(INK, 3, 0.25 * k))
    for i in range(60):
        th = i / 60 * 2 * math.pi
        L = 26 if i % 5 == 0 else 12
        p = stroke(INK, 5 if i % 5 == 0 else 2.5, 0.55 * k)
        c.drawLine(cx + (r - L) * math.sin(th), cy - (r - L) * math.cos(th), cx + r * math.sin(th),
                   cy - r * math.cos(th), p)
    sw = 360 * e_io(prog(t, LOSING.w(4), LOSING.e - LOSING.w(4) + 0.2))
    rect = skia.Rect.MakeLTRB(cx - r - 22, cy - r - 22, cx + r + 22, cy + r + 22)
    c.drawArc(rect, -90, sw, False, stroke(ORANGE, 16, 0.95 * k))


def timer_chip(c, t):
    a0, a1 = LOSING.w(4) - 0.15, WHY.s - 0.06
    if not (a0 <= t < a1):
        return
    k = e_back(prog(t, a0, 0.35)) * (1 - e_in(prog(t, a1 - 0.2, 0.2)))
    secs = 3 * 3600 * e_io(prog(t, LOSING.w(4), LOSING.e - LOSING.w(4) + 0.2))
    hh, mm, ss = int(secs // 3600), int(secs % 3600 // 60), int(secs % 60)
    c.save()
    c.translate(540, 1300)
    c.scale(clamp(k, 0, 1.2), clamp(k, 0, 1.2))
    c.drawRRect(kit.rrect(-190, -44, 380, 88, 44), fill(WHITE, 0.96))
    c.drawCircle(-140, 0, 11, fill(ORANGE, 0.4 + 0.6 * (int(t * 4) % 2)))
    kit.text(c, f"{hh:02d}:{mm:02d}:{ss:02d}", 20, 16, "monob", 46, color=INK)
    c.restore()


def week(c, t, a0, a1, mode):
    """seven day cells. mode 'twice': 2 posted, 5 empty. mode 'daily': all seven fill lime."""
    if not (a0 <= t < a1):
        return
    k = e_out(prog(t, a0, 0.35)) * (1 - e_in(prog(t, a1 - 0.2, 0.2)))
    days = "MTWTFSS"
    cw, gap = 108, 12
    x0 = 540 - (7 * cw + 6 * gap) / 2
    y = 1200 + (1 - k) * 80
    card_r = kit.rrect(x0 - 26, y - 70, 7 * cw + 6 * gap + 52, 236, 30)
    c.drawRRect(card_r.makeOffset(0, 14), fill("#000000", 0.3 * k, blur=24))
    c.drawRRect(card_r, fill(PAPER, 0.97 * k))
    kit.text(c, "THIS WEEK", x0, y - 22, "monob", 26, color=INK, a=0.7 * k, anchor="l", tracking=0.12)
    for i in range(7):
        x = x0 + i * (cw + gap)
        pk = e_back(prog(t, a0 + 0.04 * i, 0.3))
        c.save()
        c.translate(x + cw / 2, y + 76)
        c.scale(0.6 + 0.4 * pk, 0.6 + 0.4 * pk)
        rr = kit.rrect(-cw / 2, -62, cw, 124, 20)
        if mode == "twice":
            on = i in (1, 4) and t >= WHY.w(5) + 0.06 * (i == 4)
            miss = i not in (1, 4) and t >= WHY.w(8)
            c.drawRRect(rr, fill(INK if on else WHITE, k))
            c.drawRRect(rr, stroke(INK, 3, 0.25 * k))
            kit.text(c, days[i], 0, -16, "black", 40, color=WHITE if on else INK, a=k * (1 if on else 0.6))
            if on:
                check(c, 0, 34, 26, LIME, k)
            if miss:
                mk = e_out(prog(t, WHY.w(8) + 0.05 * i, 0.2))
                p = stroke(ORANGE, 8, k)
                trim(p, mk)
                c.drawLine(-28, 16, 28, 56, p)
                p2 = stroke(ORANGE, 8, k)
                trim(p2, mk)
                c.drawLine(28, 16, -28, 56, p2)
        else:
            on = t >= IFW.w(5) + 0.07 * i
            ok = e_back(prog(t, IFW.w(5) + 0.07 * i, 0.25))
            c.drawRRect(rr, fill(WHITE, k))
            if on:
                c.save()
                c.scale(ok, ok)
                c.drawRRect(rr, fill(LIME, k))
                c.restore()
            c.drawRRect(rr, stroke(INK, 3, 0.25 * k))
            kit.text(c, days[i], 0, -16, "black", 40, color=INK, a=k)
            if on:
                check(c, 0, 34, 26, INK, k * ok)
        c.restore()
    if mode == "twice":
        sk = e_back(prog(t, WHY.w(5) + 0.2, 0.3))
        if sk > 0:
            kit.text(c, "2 / 7 DAYS", x0 + 7 * cw + 6 * gap, y - 22, "monob", 28, color=ORANGE, a=k * clamp(sk),
                     anchor="r")
    else:
        sk = e_back(prog(t, IFW.w(5) + 0.6, 0.3))
        if sk > 0:
            kit.text(c, "7 / 7 DAYS", x0 + 7 * cw + 6 * gap, y - 22, "monob", 28, color=INK, a=k * clamp(sk),
                     anchor="r")


def check(c, x, y, s, color, a):
    path = skia.Path()
    path.moveTo(x - s * 0.8, y)
    path.lineTo(x - s * 0.2, y + s * 0.6)
    path.lineTo(x + s * 0.9, y - s * 0.6)
    c.drawPath(path, stroke(color, s * 0.32, a))


def logo_reveal(c, t):
    """VIBE EDITING wordmark behind the head on "it's called the vibe editing"."""
    a0, a1 = CALLED.s - 0.1, T_REC
    if not (a0 <= t < a1 + 0.25):
        return
    out = e_in(prog(t, a1 - 0.05, 0.3))
    # light streak
    sk = e_out(prog(t, CALLED.w(3) - 0.1, 0.5))
    if sk > 0:
        c.drawRect(skia.Rect.MakeXYWH(540 - 700 * sk, 418, 1400 * sk, 6), fill(LIME, 0.9 * (1 - out), blur=6))
        c.drawRect(skia.Rect.MakeXYWH(540 - 520 * sk, 419, 1040 * sk, 3), fill(WHITE, 1 - out))
    kit.text(c, "IT'S CALLED", 540, 190, "monob", 38, color=WHITE, a=e_out(prog(t, a0, 0.3)) * 0.8 * (1 - out),
             tracking=0.3)
    for li, (word, t0, y) in enumerate((("VIBE", CALLED.w(3), 400), ("EDITING", CALLED.w(4), 560))):
        size = 250 if li == 0 else 200
        wd = measure(word, "unbounded", size)
        if wd > 1000:
            size *= 1000 / wd
            wd = 1000
        x = 540 - wd / 2
        f = font("unbounded", size)
        for i, ch in enumerate(word):
            cw = f.measureText(ch)
            kk = e_expo(prog(t, t0 - 0.08 + i * 0.035, 0.45))
            if kk > 0:
                c.save()
                c.translate(x + cw / 2, y + (1 - kk) * (90 if li else -90) - out * 200)
                sc = lerp(1.6, 1.0, kk)
                c.scale(sc, sc)
                a = clamp(kk * 2) * (1 - out)
                kit.text(c, ch, 0, 0, "unbounded", size, paint=fill(LIME, 0.45 * a, blur=26))
                kit.text(c, ch, 0, 0, "unbounded", size, color=LIME if li == 0 else WHITE, a=a)
                c.restore()
            x += cw


def viewfinder(c, t, a0, a1):
    if not (a0 <= t < a1):
        return
    k = e_out(prog(t, a0, 0.25)) * (1 - prog(t, a1 - 0.2, 0.2))
    m, L = 64 + 30 * (1 - k), 80
    top, bot = 250, 1660
    p = stroke(WHITE, 7, k)
    for (x, y, sx, sy) in [(m, top, 1, 1), (W - m, top, -1, 1), (m, bot, 1, -1), (W - m, bot, -1, -1)]:
        c.drawLine(x, y, x + sx * L, y, p)
        c.drawLine(x, y, x, y + sy * L, p)
    if int(t * 2.5) % 2 == 0:
        c.drawCircle(m + 36, top + 60, 14, fill("#FF2D2D", k))
    kit.text(c, "REC", m + 62, top + 72, "monob", 32, color=WHITE, a=k, anchor="l", shadow=6)
    tc = t - a0 + 3.0
    kit.text(c, f"00:00:{int(tc):02d}:{int((tc % 1) * 30):02d}", W - m - 16, top + 72, "monob", 32, color=WHITE,
             a=k, anchor="r", shadow=6)


PROMPTS = [(CUTP, "cut the pauses"), (PUNCHY, "punchy captions"), (CINE, "cinematic look"), (ADDM, "add music")]


def prompt_card(c, t):
    """glass prompt panel in front: the spoken directions type in and tick off."""
    a0, a1 = TELL.s - 0.1, EDITS.e + 0.3
    if not (a0 <= t < a1):
        return
    k = e_expo(prog(t, a0, 0.4)) * (1 - e_in(prog(t, a1 - 0.25, 0.25)))
    x, y, w, h = 80, 1060 + (1 - k) * 200, 840, 520
    c.save()
    rr = kit.rrect(x, y, w, h, 36)
    c.drawRRect(rr.makeOffset(0, 18), fill("#000000", 0.35 * k, blur=30))
    c.drawRRect(rr, fill(INK2, 0.9 * k))
    c.drawRRect(rr, stroke(WHITE, 2, 0.14 * k))
    # header
    c.drawCircle(x + 44, y + 50, 9, fill(ORANGE, k))
    c.drawCircle(x + 72, y + 50, 9, fill("#FFC23F", k))
    c.drawCircle(x + 100, y + 50, 9, fill(LIME, k))
    kit.text(c, "VIBE EDITING SYSTEM", x + w - 36, y + 61, "monob", 26, color=WHITE, a=0.55 * k, anchor="r",
             tracking=0.15)
    c.drawLine(x, y + 94, x + w, y + 94, stroke(WHITE, 2, 0.1 * k))
    # lines
    for j, (ph, txt) in enumerate(PROMPTS):
        ly = y + 160 + j * 72
        if t < ph.s - 0.05:
            if j == 0 or t >= PROMPTS[j - 1][0].e:
                if int(t * 3) % 2 == 0:
                    c.drawRect(skia.Rect.MakeXYWH(x + 96, ly - 34, 4, 42), fill(LIME, k))
            break
        n = int(len(txt) * clamp((t - ph.s + 0.05) / max(0.25, ph.e - ph.s)))
        done = t >= ph.e + 0.05
        kit.text(c, "›", x + 50, ly, "monob", 40, color=LIME, a=k, anchor="l")
        kit.text(c, txt[:n], x + 96, ly, "mono", 40, color=WHITE, a=k, anchor="l")
        if done:
            dk = e_back(prog(t, ph.e + 0.05, 0.3))
            c.save()
            c.translate(x + w - 70, ly - 14)
            c.scale(dk, dk)
            c.drawCircle(0, 0, 24, fill(LIME, k))
            check(c, 0, 2, 13, INK, k)
            c.restore()
    # render bar
    if t >= EDITS.s - 0.05:
        pk = e_io(prog(t, EDITS.s, EDITS.e - EDITS.s))
        by = y + h - 70
        c.drawRRect(kit.rrect(x + 50, by - 14, w - 100, 28, 14), fill(WHITE, 0.1 * k))
        c.drawRRect(kit.rrect(x + 50, by - 14, (w - 100) * pk, 28, 14), fill(LIME, k))
        lab = "EDITING…" if pk < 1 else "DONE"
        kit.text(c, f"{lab}  {int(pk * 100):3d}%", x + 50, by - 34, "monob", 26, color=WHITE, a=0.8 * k, anchor="l")
    c.restore()


def letterbox(c, t):
    a0, a1 = CINE.w(1) - 0.05, T_DROP + 0.25
    if not (a0 <= t < a1):
        return 0
    k = e_expo(prog(t, a0, 0.35)) * (1 - e_in(prog(t, a1 - 0.2, 0.2)))
    bh = 150 * k
    c.drawRect(skia.Rect.MakeXYWH(0, 0, W, bh), fill("#000000"))
    c.drawRect(skia.Rect.MakeXYWH(0, H - bh, W, bh), fill("#000000"))
    kit.text(c, "2.39 : 1   ·   CINEMATIC", 540, H - bh + 90, "monob", 26, color=WHITE, a=0.6 * k, tracking=0.2)
    return k


def eq_bars(c, t):
    """lime equaliser behind the speaker after the drop."""
    a0, a1 = T_DROP - 0.02, T_FEAT
    if not (a0 <= t < a1):
        return
    k = e_out(prog(t, a0, 0.2))
    n = 18
    bw = W / n
    ph = ((t - T_DROP) % BEAT) / BEAT
    for i in range(n):
        lv = 0.35 + 0.65 * abs(math.sin(t * (3.1 + hrand("eq", i) * 4) + i))
        lv *= 0.55 + 0.45 * (1 - ph) ** 2
        hh = 900 * lv * k
        x = i * bw + 6
        c.drawRRect(kit.rrect(x, H - hh, bw - 12, hh + 30, 12), fill(LIME, 0.22 + 0.5 * (1 - ph) ** 3))
    # ring pulse
    c.drawCircle(540, 760, 420 + 120 * ph, stroke(LIME, 6 * (1 - ph), 0.6 * (1 - ph) * k))


FEATS = ["CUTS", "CAPTIONS", "EFFECTS", "SOUND"]


def feature_chips(c, t):
    a0, a1 = FEAT.s - 0.05, T_READY
    if not (a0 <= t < a1):
        return
    out = e_in(prog(t, a1 - 0.15, 0.15))
    ch_w, ch_h, gap = 330, 92, 16
    for j, name in enumerate(FEATS):
        kk = e_back(prog(t, FEAT.w(j) - 0.04, 0.3))
        if kk <= 0:
            continue
        x = 540 + (j % 2 - 1) * (ch_w + gap) + gap / 2
        y = 1250 + (j // 2) * (ch_h + gap)
        a = clamp(kk) * (1 - out)
        c.save()
        c.translate(x + ch_w / 2, y + (1 - kk) * 40)
        c.scale(0.8 + 0.2 * kk, 0.8 + 0.2 * kk)
        rr = kit.rrect(-ch_w / 2, -ch_h / 2, ch_w, ch_h, ch_h / 2)
        c.drawRRect(rr.makeOffset(0, 10), fill("#000000", 0.25 * a, blur=16))
        c.drawRRect(rr, fill(INK, a))
        c.drawCircle(-ch_w / 2 + 46, 0, 22, fill(LIME, a))
        check(c, -ch_w / 2 + 46, 2, 11, INK, a)
        kit.text(c, name, 26, 13, "black", 38, color=WHITE, a=a)
        c.restore()


def ready_scene(c, t, src_ts):
    """the edit morphs through platform frames: Reels 9:16 -> Feed 4:5 -> YouTube 16:9."""
    a0 = T_READY
    ink_bg(c, t, PERI, 0.16)
    marks = [(a0, 560, 996, "REELS", "9:16"), (READY.w(3) - 0.05, 720, 900, "FEED", "4:5"),
             (READY.w(5) - 0.05, 960, 540, "YOUTUBE", "16:9")]
    cur = 0
    for i, m in enumerate(marks):
        if t >= m[0]:
            cur = i
    pw, ph = marks[cur][1], marks[cur][2]
    if cur > 0:
        q = e_expo(prog(t, marks[cur][0], 0.32))
        pw = lerp(marks[cur - 1][1], pw, q)
        ph = lerp(marks[cur - 1][2], ph, q)
    intro = e_expo(prog(t, a0, 0.35))
    pw *= lerp(1.9, 1, intro)
    ph *= lerp(1.9, 1, intro)
    cx, cy = 540, 860
    src = Src(src_ts)
    rect = skia.Rect.MakeXYWH(cx - pw / 2, cy - ph / 2, pw, ph)
    rr = skia.RRect.MakeRectXY(rect, 34, 34)
    c.drawRRect(rr.makeOffset(0, 24), fill("#000000", 0.55, blur=40))
    c.save()
    c.clipRRect(rr, skia.ClipOp.kIntersect, True)
    # content: footage covering the frame, centred on the face where it can be
    sc = max(pw / W, ph / H) * (1.0 if ph >= pw else 1.35)
    hy = ph / 2 / sc
    fy = clamp(FACE[1] + 40, hy, H - hy)
    c.translate(cx, cy)
    c.scale(sc, sc)
    c.translate(-540, -fy)
    c.drawImage(src.bg(), 0, 0, SAMP)
    c.restore()
    c.drawRRect(rr, stroke(WHITE, 4, 0.9))
    # labels
    lab, ratio = marks[cur][3], marks[cur][4]
    lk = e_back(prog(t, marks[cur][0], 0.3))
    y = cy + ph / 2 + 92
    c.save()
    c.translate(540, y)
    c.scale(0.7 + 0.3 * lk, 0.7 + 0.3 * lk)
    wl = measure(lab, "black", 64)
    c.drawRRect(kit.rrect(-wl / 2 - 30, -58, wl + 30 + 150, 82, 41), fill(LIME))
    kit.text(c, lab, -wl / 2, 2, "black", 64, color=INK, anchor="l")
    kit.text(c, ratio, wl / 2 + 30, -4, "monob", 34, color=INK, anchor="l")
    c.restore()
    # format dots
    for i in range(3):
        c.drawCircle(540 + (i - 1) * 40, 300, 10, fill(LIME if i == cur else WHITE, 1 if i == cur else 0.3))
    kit.text(c, "ONE EDIT · EVERY FORMAT", 540, 250, "monob", 30, color=WHITE, a=0.7 * intro, tracking=0.2)


def no_scene_extras(c, t):
    """Vox collage bits behind the speaker in the "no timeline, no keyframes, no editor" beat."""
    a0, a1 = T_NO, T_PROOF
    if not (a0 <= t < a1):
        return
    k = e_out(prog(t, a0, 0.3))
    # tape label
    c.save()
    c.translate(540, 1210)
    c.rotate(-3)
    lab = "WHAT YOU DON'T NEED"
    wl = measure(lab, "monob", 30)
    c.drawRect(skia.Rect.MakeXYWH(-wl / 2 - 26, -36, wl + 52, 62), fill("#F7F1D9", 0.95 * k))
    kit.text(c, lab, 0, 8, "monob", 30, color=INK, a=k)
    c.restore()


def wipe_compare(c, t, src_ts, g):
    """recorded on my phone (raw) | edited by the system: a wipe across the same frame."""
    raw = Src(src_ts, "raw")
    fin = Src(src_ts, "warm")
    cam = camera(t)
    # edited side = wall + caption, raw side = untouched
    x = lerp(W, W * 0.5, e_io(prog(t, PROOF.w(2), 0.5)))
    x = lerp(x, 0, e_io(prog(t, EDBY.s, 0.55)))
    paper_bg(c, PAPER)
    halftone(c, 540, 1900, 900, "#DCD5C6", 30, 12, 0.9)
    behind_caps(c, t, INK, ORANGE, y0=495)
    c.save()
    apply_cam(c, cam)
    shadow = skia.Paint(ImageFilter=skia.ImageFilters.DropShadowOnly(0, 26, 30, 30, col("#000000", 0.28)))
    c.drawImage(fin.person(), 0, 0, SAMP, shadow)
    c.drawImage(fin.person(), 0, 0, SAMP)
    c.restore()
    c.save()
    c.clipRect(skia.Rect.MakeLTRB(0, 0, x, H))
    c.drawImage(raw.bg(), 0, 0, SAMP)
    c.restore()
    if 2 < x < W - 2:
        c.drawRect(skia.Rect.MakeXYWH(x - 3, 0, 6, H), fill(WHITE))
        c.drawCircle(x, 960, 36, fill(WHITE))
        kit.text(c, "‹ ›", x, 972, "monob", 34, color=INK)
    ka = e_out(prog(t, T_PROOF, 0.3)) * (1 - e_in(prog(t, T_IFW - 0.2, 0.2)))
    if x > 120:
        pill(c, "RAW · PHONE", clamp(x - 30, 330, W - 70), 1460, WHITE, INK, ka, anchor="r")
    if x < W - 120:
        pill(c, "EDITED · SYSTEM", clamp(x + 30, 70, W - 400), 1460, LIME, INK, ka, anchor="l")


def pill(c, s, x, y, bg, fg, a=1.0, anchor="c", size=30):
    wl = measure(s, "monob", size, 0.06)
    x0 = x - wl / 2 - 26 if anchor == "c" else x - wl - 52 if anchor == "r" else x
    c.drawRRect(kit.rrect(x0, y - size - 12, wl + 52, size * 2 + 6, size + 3), fill(bg, a))
    kit.text(c, s, x0 + 26, y + 6, "monob", size, color=fg, a=a, anchor="l", tracking=0.06)


def product(c, t):
    """the offer behind the speaker: rotating rays + VIBE EDITING SYSTEM lockup."""
    a0 = T_GET
    if t < a0:
        return
    k = e_expo(prog(t, a0, 0.5))
    rot = (t - a0) * 9
    path = skia.Path()
    cx, cy = 540, 760
    for i in range(16):
        th0 = math.radians(rot + i * 22.5)
        th1 = th0 + math.radians(9)
        path.moveTo(cx, cy)
        path.lineTo(cx + 2400 * math.cos(th0), cy + 2400 * math.sin(th0))
        path.lineTo(cx + 2400 * math.cos(th1), cy + 2400 * math.sin(th1))
        path.close()
    c.drawPath(path, fill(LIME, 0.06 * k))
    c.drawCircle(cx, cy, 470 * k, fill(LIME, 0.12 * k, blur=60))
    c.drawCircle(cx, cy, 440 * k, stroke(LIME, 5, 0.8 * k))
    for li, (word, size, y, color) in enumerate((("VIBE EDITING", 128, 360, WHITE), ("SYSTEM", 170, 540, LIME))):
        wd = measure(word, "unbounded", size)
        if wd > 980:
            size *= 980 / wd
        kk = e_expo(prog(t, a0 + 0.12 * li + (GET.w(2) - a0) * li, 0.45))
        c.save()
        c.translate(0, (1 - kk) * 80)
        kit.text(c, word, 540, y, "unbounded", size, paint=fill(color, 0.35 * kk, blur=22))
        kit.text(c, word, 540, y, "unbounded", size, color=color, a=kk)
        c.restore()


def tap_button(c, t):
    a0 = TAP.s - 0.12
    if t < a0:
        return
    k = e_back(prog(t, a0, 0.35))
    press = 1 - 0.08 * math.sin(math.pi * prog(t, TAP.w(1) - 0.02, 0.22))
    bw, bh = 640, 150
    c.save()
    c.translate(540, 1500)
    c.scale(k * press, k * press)
    rr = kit.rrect(-bw / 2, -bh / 2, bw, bh, bh / 2)
    c.drawRRect(rr.makeOffset(0, 16), fill("#000000", 0.4, blur=24))
    c.drawRRect(rr, fill(LIME))
    kit.text(c, "Learn More", -40, 24, "black", 70, color=INK)
    c.drawCircle(bw / 2 - 80, 0, 46, fill(INK))
    p = stroke(LIME, 9)
    c.drawLine(bw / 2 - 100, 0, bw / 2 - 60, 0, p)
    c.drawLine(bw / 2 - 76, -16, bw / 2 - 60, 0, p)
    c.drawLine(bw / 2 - 76, 16, bw / 2 - 60, 0, p)
    c.restore()
    # tap ripple + finger dot
    for t0 in (TAP.s, TAP.w(1)):
        rk = prog(t, t0, 0.5)
        if 0 < rk < 1:
            c.drawCircle(700, 1520, 40 + 160 * e_out(rk), stroke(WHITE, 8 * (1 - rk), 0.9 * (1 - rk)))
            c.drawCircle(700, 1520, 34, fill(WHITE, 0.55 * (1 - rk)))


def end_card(c, t):
    a0 = END_A
    k = e_expo(prog(t, a0, 0.5))
    ink_bg(c, t, LIME, 0.14)
    c.save()
    c.translate(0, (1 - k) * 60)
    kit.text(c, "VIBE", 540, 760, "unbounded", 230, paint=fill(LIME, 0.35 * k, blur=26))
    kit.text(c, "VIBE", 540, 760, "unbounded", 230, color=LIME, a=k)
    kit.text(c, "EDITING", 540, 930, "unbounded", 168, color=WHITE, a=k)
    c.restore()
    k2 = e_out(prog(t, a0 + 0.3, 0.45))
    pill(c, "SYSTEM", 540, 1070, WHITE, INK, k2, size=44)
    k3 = e_out(prog(t, a0 + 0.55, 0.5))
    kit.text(c, "Direct the vibe.", 540, 1230, "italic", 86, color=WHITE, a=k3)
    kit.text(c, "Let AI do the keyframes.", 540, 1320, "italic", 86, color=WHITE, a=0.6 * k3)
    k4 = e_back(prog(t, a0 + 0.8, 0.4))
    if k4 > 0:
        c.save()
        c.translate(540, 1520)
        c.scale(k4, k4)
        bw, bh = 600, 124
        c.drawRRect(kit.rrect(-bw / 2, -bh / 2, bw, bh, bh / 2), fill(LIME))
        kit.text(c, "TAP LEARN MORE", 0, 16, "black", 50, color=INK)
        c.restore()


# ================================================================== frame
def draw(c, t, f):
    g = {}
    src_ts = src_at(t)
    c.clear(col(INK))
    if t >= END_A:
        end_card(c, t)
        return g
    if T_READY <= t < T_NO:
        ready_scene(c, t, src_ts)
        front_caps(c, t, y=1620, size=68)
        if t < T_READY + 0.08:
            g["flash"] = 0.6 * (1 - (t - T_READY) / 0.08)
        return g
    if T_PROOF <= t < T_IFW:
        wipe_compare(c, t, src_ts, g)
        return g
    look = "cine" if CINE.w(1) <= t < T_DROP else "warm"
    src = Src(src_ts, look)
    cam = camera(t)
    (t0, kind, sty), prev = bg_kind(t)
    rk = prog(t, t0, 0.32) if sty in ("iris", "wipe", "slide") else 1.0
    c.save()
    apply_cam(c, cam) if kind == "wall" else None
    if rk < 1 and prev is not None:
        draw_bg(c, prev[1], t, src)
        c.restore()
        c.save()
        reveal_mask(c, sty, rk)
        apply_cam(c, cam) if kind == "wall" else None
    draw_bg(c, kind, t, src)
    c.restore()
    if sty == "flash" and t0 <= t < t0 + 0.1:
        g["flash"] = 0.7 * (1 - (t - t0) / 0.1)
    if sty in ("flash", "scale") and t0 <= t < t0 + 0.12:
        g["whip"] = 1 - (t - t0) / 0.12

    # ---- behind the speaker
    dark = kind in ("ink", "inkbars")
    halo_clock(c, t)
    eq_bars(c, t)
    logo_reveal(c, t)
    no_scene_extras(c, t)
    product(c, t)
    caps_on = not (CALLED.s - 0.1 <= t < T_REC + 0.1) and t < T_GET
    if caps_on:
        if dark:
            behind_caps(c, t, WHITE, LIME, y0=495)
        elif kind == "lime":
            behind_caps(c, t, INK, INK, y0=495)
        else:
            behind_caps(c, t, INK, ORANGE, y0=495)
    # ---- the speaker
    c.save()
    apply_cam(c, cam)
    if kind != "wall":
        shadow = skia.Paint(ImageFilter=skia.ImageFilters.DropShadowOnly(0, 26, 30, 30, col("#000000", 0.45 if dark else 0.28)))
        c.drawImage(src.person(), 0, 0, SAMP, shadow)
    if kind == "vox":
        c.drawImage(src.outline(11), 0, 0, SAMP)
    if dark:
        rim = skia.Paint(ImageFilter=skia.ImageFilters.DropShadowOnly(0, 0, 10, 10, col(LIME, 0.32)))
        c.drawImage(src.person(), 0, 0, SAMP, rim)
    c.drawImage(src.person(), 0, 0, SAMP)
    c.restore()
    # ---- in front
    viewfinder(c, t, T_REC, TELL.s + 0.4)
    prompt_card(c, t)
    if WHY.s - 0.06 <= t < T_FIX:
        week(c, t, WHY.s - 0.06, T_FIX + 0.05, "twice")
    if T_IFW <= t < T_GET:
        week(c, t, T_IFW, T_GET + 0.05, "daily")
    letterbox(c, t)
    feature_chips(c, t)
    timer_chip(c, t)
    tap_button(c, t)
    if GET.s - 0.05 <= t < TAP.s - 0.1:
        front_caps(c, t, y=1500, size=74)
    # looks
    for st in (NOTBAD.w(2), FIX.w(4), T_DROP, FEAT.w(0), NO.w(1), NO.w(3), NO.w(5), EDBY.s, GET.w(2), TAP.s):
        if st <= t < st + 0.07:
            g["ca"] = 7
    if t < 0.1:
        g["flash"] = 1 - t / 0.1
    return g


SHAKES += [(NOTBAD.w(2), 10), (LOSING.w(4), 8), (FIX.w(4), 14), (CALLED.w(3), 10), (T_DROP, 18),
           (FEAT.w(0), 8), (FEAT.w(3), 8), (NO.w(1), 7), (NO.w(3), 7), (NO.w(5), 9), (GET.w(2), 10)]

# ================================================================== post
_VIG = None


def post(rgb, g, f):
    global _VIG
    h, w = rgb.shape[:2]
    if _VIG is None or _VIG.shape[0] != h:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        _VIG = (1 - 0.22 * np.clip(r - 0.6, 0, None) ** 1.6)[..., None].astype(np.float32)
    out = rgb.astype(np.float32)
    s = w / W
    if g.get("whip"):
        k = g["whip"]
        acc = out.copy()
        for d in (1, 2, 3, 4):
            acc += np.roll(out, int(d * 14 * k * s), axis=0)
        out = acc / 5
    ca = int(g.get("ca", 0) * s)
    if ca:
        out[..., 0] = np.roll(out[..., 0], ca, axis=1)
        out[..., 2] = np.roll(out[..., 2], -ca, axis=1)
    if g.get("flash"):
        out = out + (255 - out) * g["flash"]
    out *= _VIG
    out = np.clip(out, 0, 255).astype(np.uint8)
    return kit.grain(out, f, amt=0.022)


FILM = kit.Film(draw, END_A + 2.6, FPS, post=post, out_dir=OUT)
DUR = END_A + 2.6


# ================================================================== audio
def music_plan():
    """bpm chosen so the drop lands exactly on "music"."""
    bar0 = 4 * 60 / 140.0
    nb = max(2, round(T_DROP / bar0))
    bpm = nb * 4 * 60 / T_DROP
    return bpm, nb


BPM, DROP_BARS = music_plan()
BEAT = 60 / BPM


def sfx_cues():
    S = []

    def a(t, kind, gain=-8, **kw):
        S.append((kind, t, gain, kw))

    a(0.0, "impact", -8)
    a(NOTBAD.w(2) - 0.03, "pop", -10)
    a(NOTBAD.w(5), "swish", -14)
    a(LOSING.w(4) - 0.1, "whoosh", -12)
    for j in range(10):
        a(LOSING.w(4) + j * 0.17, "tick", -16)
    a(WHY.s - 0.1, "whoosh", -11)
    a(WHY.w(5), "pop", -10)
    a(WHY.w(5) + 0.06, "pop", -12)
    a(WHY.w(8), "glitch", -16)
    a(T_FIX - 0.25, "riser", -12, dur=0.3)
    a(FIX.w(4), "impact", -6)
    a(FIX.w(4), "sparkle", -12)
    a(CALLED.w(3) - 0.1, "whoosh", -10)
    a(CALLED.w(3), "impact", -9)
    a(CALLED.w(4), "sparkle", -10)
    a(T_REC, "shutter", -9)
    a(TELL.s - 0.05, "pop", -12)
    for ph, txt in PROMPTS:
        a(ph.s, "typing", -17, dur=max(0.25, ph.e - ph.s))
        a(ph.e + 0.05, "click", -10)
    a(CUTP.e + 0.05, "swish", -13)
    a(CINE.w(1), "whoosh", -11)
    a(EDITS.s, "riser", -14, dur=EDITS.e - EDITS.s)
    a(EDITS.e + 0.05, "ding", -11)
    a(T_FEAT - 0.08, "whoosh", -10)
    for j in range(4):
        a(FEAT.w(j), "pop", -9, pan=(j - 1.5) * 0.3)
    a(T_READY - 0.1, "whoosh", -9)
    a(READY.w(3) - 0.05, "swish", -10)
    a(READY.w(5) - 0.05, "swish", -10)
    a(T_NO - 0.05, "whoosh", -11)
    for j in (1, 3, 5):
        a(NO.we(j) - 0.02, "swish", -9)
        a(NO.we(j), "click", -10)
    a(T_PROOF, "shutter", -9)
    a(PROOF.w(2), "whoosh", -12)
    a(EDBY.s, "whoosh", -10)
    a(EDBY.e, "sparkle", -12)
    a(T_IFW - 0.05, "swish", -11)
    for i in range(7):
        a(IFW.w(5) + 0.07 * i, "pop", -15)
    a(IFW.w(10), "glitch", -16)
    a(T_GET - 0.3, "riser", -12, dur=0.35)
    a(GET.w(2), "impact", -7)
    a(GET.w(4), "sparkle", -10)
    a(TAP.s, "click", -6)
    a(TAP.w(1), "pop", -8)
    a(END_A - 0.1, "whoosh", -9)
    a(END_A + 0.05, "impact", -8)
    a(END_A + 0.8, "ding", -12)
    return S


def build_audio():
    import audio_kit as ak
    import music as M
    from sound import Mix, broadcast
    SR = M.SR
    work = HERE / "work"
    vpath = work / "voice_clean.wav"
    if not vpath.exists():
        ff("-i", str(HERE / "raw" / "take.mp4"), "-vn", "-af",
           "highpass=f=80,afftdn=nf=-30,acompressor=threshold=-20dB:ratio=3:attack=5:release=90:makeup=3,"
           "deesser=i=0.35", "-ar", str(SR), "-ac", "2", str(vpath))
    raw = ak.read_audio(vpath)
    n = int(DUR * SR) + 1
    voice = np.zeros((n, 2), np.float32)
    xf = int(0.012 * SR)
    for a, b, o in EDL:
        seg = raw[int(a * SR):int(b * SR)].copy()
        if len(seg) > 2 * xf:
            ramp = np.linspace(0, 1, xf, dtype=np.float32)[:, None]
            seg[:xf] *= ramp
            seg[-xf:] *= ramp[::-1]
        i0 = int(o * SR)
        seg = seg[: max(0, n - i0)]
        voice[i0:i0 + len(seg)] += seg
    voice = broadcast(voice, room=0.03)
    vtmp = work / "voice_edit.wav"
    ak.write_wav(vtmp, voice)

    song = M.future_bass(DUR + 1, bpm=BPM, key="F#",
                         marks={"drop": T_DROP, "break": T_NO, "drop2": T_GET}, seed=7)
    bed = song.master()[:n]
    # before the drop: keep it low and filtered (the pads), the drop hits on "music"
    m = Mix(DUR)
    m.voice([(vtmp, 0.0)], chain=None, warmth=False)
    m.music(bed, gain_db=-2, duck_db=-9, fade_out=1.6)
    for kind, t, gain, kw in sfx_cues():
        m.sfx(kind, t, gain, **kw)
    return m


def finish_all(pic, out):
    m = build_audio()
    m.finish(pic, out, HERE / "work")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "info":
        print(f"total {DUR:.2f}s (speech {TOTAL:.2f}s, raw {NSRC / FPS:.1f}s), bpm {BPM:.1f} drop bar {DROP_BARS}")
        for a, b, o in EDL:
            print(f"  src {a:6.2f}-{b:6.2f}  out {o:6.2f} +{b - a:.2f}")
        for g in GROUPS:
            print(f"  {g[0]['os']:6.2f}  " + " ".join(w['d'] for w in g))
    elif cmd == "stills":
        FILM.stills([float(x) for x in sys.argv[2:]])
    elif cmd == "sheet":
        FILM.sheet([round(DUR * (i + 0.5) / 48, 2) for i in range(48)], cols=8)
    elif cmd == "audio":
        m = build_audio()
        ak_path = HERE / "work" / "mix_preview.wav"
        import audio_kit as ak
        ak.write_wav(ak_path, m.render())
        print("->", ak_path)
    elif cmd == "render":
        draft = "--draft" in sys.argv
        pic = FILM.render(OUT / ("draft_picture.mp4" if draft else "picture.mp4"), draft=draft)
        finish_all(pic, OUT / ("draft.mp4" if draft else "vibe_edit_time.mp4"))


if __name__ == "__main__":
    main()
