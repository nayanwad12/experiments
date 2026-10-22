"""Vibe Editing System reel: the full edit of the raw take (work/frames + work/alpha.npy + work/words.json).

    python3 edit.py info                  the cut list
    python3 edit.py stills 1.0 4.2 ...    -> out/stills/*.png  (half res)
    python3 edit.py sheet                 -> out/sheet.png
    python3 edit.py render [--draft]      -> out/vibe_reel.mp4
    python3 edit.py audio                 -> work/mix.wav

Everything is cued off the spoken words. The strongest line ("this exact video went through all six steps")
is lifted to the front as the hook, every pause between phrases is cut to a breath, and each of the six
steps gets its own ground, layout and graphics, all in the olive / cream / tomato look of the reference.
"""

import json
import math
import re
import sys
from pathlib import Path

import cv2
import numpy as np
import skia

cv2.setNumThreads(1)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "reels" / "common"))
import audio_kit as ak  # noqa: E402
import kit  # noqa: E402
from look import (CREAM, INK, OLIVE, OLIVE_D, OLIVE_L, PAPER, PINK, SAMP, TOMATO, WHITE, arrow,  # noqa: E402
                  caps, caps_block, check_mark, clamp, col, e_back, e_in, e_io, e_out, fill, font, glow_text,
                  ground, hilite, hrand, lerp, marker, measure, mono, photo_card, pill, pop_in, prog,
                  scribble_ellipse, serif, smiley, spring, stamp, stroke, torn_path, ui_card)
from vibelib import ff, loudnorm_filter  # noqa: E402

W, H, FPS = 1080, 1920, 30
OUT = HERE / "out"
FR = HERE / "work" / "frames"
NSRC = len(list(FR.glob("f_*.jpg")))
CTA_WORD = "VIBE"
BRAND = "VIBE EDITING SYSTEM"

# ================================================================== words + edit decision list
WORDS = json.loads((HERE / "work" / "words.json").read_text())
for i, w in enumerate(WORDS):
    w["i"] = i
    w["k"] = re.sub(r"[^a-z0-9']", "", w["d"].lower())
    w["os"] = w["oe"] = None
NPH = max(w["ph"] for w in WORDS) + 1
PH = [[w["i"] for w in WORDS if w["ph"] == k] for k in range(NPH)]
I_HOOK = next(i for i in PH[38] if WORDS[i]["k"] == "this")

# output order: the strongest line first, then the take in order, minus "and yes, ..." (now the hook)
ORDER = [(I_HOOK, PH[38][-1])] + [(PH[k][0], PH[k][-1]) for k in range(38)] + [(PH[39][0], PH[39][-1]),
                                                                                (PH[40][0], PH[40][-1])]
SECTION_PH = {2, 4, 10, 14, 19, 26, 35, 39}     # phrases that open a section get a slightly longer breath
END_HOLD = 3.3                                    # end card over the silent tail of the take


def build_edl():
    """[(src_a, src_b, out_a, dur, i0, i1)] play runs."""
    edl, t = [], 0.0
    for n, (i0, i1) in enumerate(ORDER):
        s, e = WORDS[i0]["s"], WORDS[i1]["e"]
        pre = 0.03 if i0 == I_HOOK else (0.12 if WORDS[i0]["ph"] in SECTION_PH else 0.07)
        a = s - pre
        if i0 > 0 and i0 != I_HOOK:
            a = max(a, (WORDS[i0 - 1]["e"] + s) / 2)
        if n == len(ORDER) - 1:
            b = e + END_HOLD
        else:
            b = e + 0.1
            if i1 + 1 < len(WORDS):
                b = min(b, (e + WORDS[i1 + 1]["s"]) / 2)
        b = min(b, NSRC / FPS - 0.05)
        edl.append((a, b, t, b - a, i0, i1))
        for j in range(i0, i1 + 1):
            WORDS[j]["os"] = t + WORDS[j]["s"] - a
            WORDS[j]["oe"] = t + WORDS[j]["e"] - a
        t += b - a
    return edl, t


EDL, TOTAL = build_edl()
RUN_STARTS = [r[2] for r in EDL]


def src_at(t):
    for a, b, o, d, _, _ in EDL:
        if t < o + d:
            return a + max(0.0, t - o)
    return EDL[-1][1]


def _find(seq, n=1):
    toks = re.sub(r"[^a-z0-9' ]", "", seq.lower()).split()
    hits = 0
    for i in range(len(WORDS) - len(toks) + 1):
        if WORDS[i]["os"] is None:
            continue
        if all(WORDS[i + j]["k"] == toks[j] for j in range(len(toks))):
            hits += 1
            if hits == n:
                return i, i + len(toks) - 1
    raise KeyError(seq)


class P:
    """a spoken phrase on the output clock: .s .e, .w(j) word start, .we(j) word end"""

    def __init__(self, seq, n=1):
        self.i0, self.i1 = _find(seq, n)
        self.s, self.e = WORDS[self.i0]["os"], WORDS[self.i1]["oe"]

    def w(self, j):
        return WORDS[self.i0 + j]["os"]

    def we(self, j):
        return WORDS[self.i0 + j]["oe"]


H_THIS, H_WENT, H_SIX = P("this exact video"), P("went through all"), P("six steps")
I_HERE, I_STEP = P("here is what actually happens inside a vibe edit"), P("step by step")
S1, DROP, ONE, MIST = P("step one"), P("you drop in your raw footage"), P("one take"), P("mistakes and all")
S2, WATCH, TRANS = P("step two"), P("the system watches and listens"), P("it transcribes every word")
FINDS, MOVES, FIRST = P("finds your strongest line"), P("moves it into the front"), \
    P("because the first two seconds decides everything")
S3, STORY, PUR, GONE, EXACT = P("step three"), P("the story cut"), P("pauses ums retakes"), P("gone"), \
    P("down to the exact word")
S4, LOOK, CAPS, BEHIND = P("step four"), P("the look"), P("captions that hit on your voice"), P("text behind you")
SWAP, ZOOMS = P("your background swapped"), P("zooms on the lines that matters")
S5, SOUND, MUSIC, WHOOSH, HITS = P("step five"), P("sound"), P("original music"), P("whooshes"), P("hits")
SCRATCH, CLAIMS = P("generated from scratch"), P("so no copyright claims ever")
S6, PART, PROOF = P("and the step six"), P("the part most editors never give you"), P("which is proof")
STILLS = P("before anything renders it shows you the stills of every key moment")
SAY, EXPORT, REELS, FEEDS = P("you say more energy or cleaner and it changes"), P("then one command exports"), \
    P("it for reels"), P("feeds youtube every format")
VE, TASTE, KEYF = P("that's the vibe editing"), P("you bring the taste"), P("the system does the key frames")
SOIF, REC = P("so if you want to see"), P("what i actually recorded")


def run_start(p):
    """output time where the run holding phrase p begins (the cut point)."""
    return max(r[2] for r in EDL if r[2] <= p.s + 1e-6)


SEC = dict(hook=0.0, intro=run_start(I_HERE), s1=run_start(S1), s2=run_start(S2), s3=run_start(S3),
           s4=run_start(S4), s5=run_start(S5), s6=run_start(S6), pay=run_start(VE), cta=run_start(SOIF))
END_A = REC.e + 0.3                                   # end card in
STEP_SECS = ["s1", "s2", "s3", "s4", "s5", "s6"]
STEP_NAMES = ["RAW IN", "LISTEN", "STORY CUT", "THE LOOK", "SOUND", "PROOF"]
DROP_T = SOUND.s                                      # the music drop
BPM = 96
BEAT = 60 / BPM


def sec_of(t):
    cur = "hook"
    for k, v in SEC.items():
        if t >= v - 1e-6:
            cur = k
    return cur


# ================================================================== source frames
_cache = {}
TRACK = np.load(HERE / "work" / "track.npy")
_k = np.ones(31) / 31
FACE_X = np.convolve(np.pad(TRACK[:, 1], 15, mode="edge"), _k, "valid")
FACE_Y = np.convolve(np.pad(TRACK[:, 0], 15, mode="edge"), _k, "valid") + 235


def face(ts):
    fi = int(clamp(round(ts * FPS), 0, len(FACE_X) - 1))
    return 0.5 * FACE_X[fi] + 0.5 * 540, FACE_Y[fi]


def frame_rgb(fi):
    fi = int(clamp(fi, 0, NSRC - 1))
    if fi not in _cache:
        if len(_cache) > 12:
            _cache.pop(next(iter(_cache)))
        _cache[fi] = cv2.imread(str(FR / f"f_{fi + 1:05d}.jpg"))[..., ::-1]
    return _cache[fi]


_ALPHA = None


def alpha_small(fi):
    global _ALPHA
    if _ALPHA is None:
        _ALPHA = np.load(HERE / "work" / "alpha.npy", mmap_mode="r")
    return np.asarray(_ALPHA[int(clamp(fi, 0, len(_ALPHA) - 1))])


def _lut():
    """warm film: soft S, lifted olive-black, cream highlights, a little less blue."""
    x = np.arange(256, dtype=np.float32) / 255
    s = x + 0.06 * np.sin(2 * math.pi * (x - 0.5))
    s = np.clip(s, 0, 1)
    r = 0.05 + 0.93 * s ** 0.97
    g = 0.055 + 0.91 * s
    b = 0.03 + 0.84 * s ** 1.04
    return [(np.clip(c, 0, 1) * 255).astype(np.uint8) for c in (r, g, b)]


LUT = np.ascontiguousarray(np.stack(_lut(), 1).reshape(256, 1, 3))
WALL_TINT = np.array([0.50, 0.58, 0.30], np.float32)       # cream wall * this -> olive room


def grade(rgb, sat=1.08):
    o = cv2.LUT(rgb, LUT)
    gray = cv2.cvtColor(cv2.cvtColor(o, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB)
    return cv2.addWeighted(o, sat, gray, 1 - sat, 0)


def rgba(arr, a=None):
    out = cv2.cvtColor(arr, cv2.COLOR_RGB2RGBA)
    if a is not None:
        out[..., 3] = a
    return skia.Image.fromarray(out, colorType=skia.kRGBA_8888_ColorType)


_SRC = {}


def Src(ts, sat=1.08):
    """cached source frame wrapper (one per frame index + saturation)."""
    key = (int(clamp(round(ts * FPS), 0, NSRC - 1)), sat)
    if key not in _SRC:
        if len(_SRC) > 16:
            _SRC.pop(next(iter(_SRC)))
        _SRC[key] = _Src(ts, sat)
    return _SRC[key]


class _Src:
    """one source frame: graded footage, the olive-room version, the cut-out person."""

    def __init__(self, ts, sat=1.08):
        self.ts = ts
        self.fi = int(clamp(round(ts * FPS), 0, NSRC - 1))
        self.raw = frame_rgb(self.fi)
        self.rgb = grade(self.raw, sat)
        self._a = None
        self._memo = {}

    @property
    def alpha(self):
        if self._a is None:
            self._a = cv2.resize(alpha_small(self.fi), (W, H), interpolation=cv2.INTER_LINEAR)
        return self._a

    def _m(self, key, fn):
        if key not in self._memo:
            self._memo[key] = fn()
        return self._memo[key]

    def room(self, strength=0.85):
        """footage with the wall pushed to olive (the person untouched)."""
        def make():
            m = cv2.resize(alpha_small(self.fi), (W, H)).astype(np.float32) * (strength / 255) - strength
            fac = cv2.merge([1 + m * (1 - WALL_TINT[ch]) for ch in range(3)])     # m = -(1 - a) * strength
            return rgba(cv2.multiply(self.rgb, fac, dtype=cv2.CV_8U))
        return self._m(("room", strength), make)

    def bg(self):
        return self._m("bg", lambda: rgba(self.rgb))

    def raw_img(self):
        return self._m("raw", lambda: rgba(self.raw))

    def person(self):
        return self._m("person", lambda: rgba(self.rgb, self.alpha))

    def outline(self, px=7, color=CREAM):
        def make():
            a = alpha_small(self.fi)
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1))
            d = cv2.resize(cv2.dilate(a, k), (W, H), interpolation=cv2.INTER_LINEAR)
            arr = np.zeros((H, W, 3), np.uint8)
            arr[:] = kit.rgb(color)
            return rgba(arr, d)
        return self._m(("outline", px, color), make)


# ================================================================== camera + layout
def in_any(t, ivs):
    return any(a <= t < b for a, b in ivs)


ZLEVELS = [1.0, 1.09, 1.03, 1.14, 1.06, 1.11]
SHAKES = []        # (t, strength) filled after the cue list below
ZOOM_A, ZOOM_B = ZOOMS.s - 0.03, ZOOMS.e + 0.12
LOW = [(DROP.s - 0.1, S2.s), (WATCH.s - 0.1, S3.s), (STILLS.s - 0.1, VE.s)]


def camera(t, ts):
    """footage transform p' = s * p + (ox, oy), rotation rot (deg) about the face. Returns (s, ox, oy, rot)."""
    fx, fy = face(ts)
    k = max([i for i, s in enumerate(RUN_STARTS) if s <= t + 1e-6] or [0])
    z = ZLEVELS[k % len(ZLEVELS)] * (1 + 0.01 * (t - RUN_STARTS[k]))
    if t < 0.35:
        z *= lerp(1.38, 1.0, e_out(t / 0.35))
    if ZOOM_A <= t < ZOOM_B:
        z = lerp(z, 1.42, e_out(prog(t, ZOOM_A, 0.16))) if t < ZOOMS.w(3) else lerp(1.42, 1.62, e_io(prog(t, ZOOMS.w(3), 0.5)))
    if H_SIX.s <= t < SEC["intro"]:
        z *= lerp(1.0, 1.08, e_out(prog(t, H_SIX.s, 0.2)))
    if DROP_T <= t < SEC["s6"]:
        ph = ((t - DROP_T) % BEAT) / BEAT
        z *= 1 + 0.03 * (1 - ph) ** 3
    dx = dy = rot = 0.0
    for st, amp in SHAKES:
        if st <= t < st + 0.32:
            kk = 1 - (t - st) / 0.32
            dx += amp * kk * math.sin(t * 91.0)
            dy += amp * kk * math.sin(t * 77.0 + 1)
            rot += amp * 0.05 * kk * math.sin(t * 63.0)
    s, ox, oy = z, fx * (1 - z) + dx, fy * (1 - z) + dy
    # "low" layout: the person sits lower and smaller, leaving the wall above for graphics
    kl = 0.0
    for a, b in LOW:
        if a <= t < b:
            kl = e_io(prog(t, a, 0.32)) * (1 - e_io(prog(t, b - 0.25, 0.25)))
    if kl:
        s2, ox2, oy2 = 0.8, 108.0, 384.0
        s, ox, oy = lerp(s, s2, kl), lerp(ox, ox2, kl), lerp(oy, oy2, kl)
    return s, ox, oy, rot


def apply_cam(c, cam):
    s, ox, oy, rot = cam
    c.translate(ox, oy)
    c.scale(s, s)
    if rot:
        c.rotate(rot, 540, 900)


def face_out(t, ts):
    """face centre on screen at time t."""
    s, ox, oy, _ = camera(t, ts)
    fx, fy = face(ts)
    return s * fx + ox, s * fy + oy


# card layout (intro and CTA): the footage as a torn retro photo
CARD = (184, 300, 712, 1030)        # x, y, w, h
CARD_S, CARD_SRC_Y = 0.66, 360


def card_mode(t):
    return SEC["intro"] <= t < SEC["s1"] or SEC["cta"] <= t < END_A + 0.35


# ================================================================== backgrounds
def bg_plan():
    """[(t, kind)] ground changes; real = footage with the wall pushed to olive."""
    p = [(0.0, "real"), (SEC["intro"], "olive"), (SEC["s1"], "olived"), (SEC["s2"], "paper"), (SEC["s3"], "real"),
         (SEC["s4"], "tomato"), (SWAP.w(1), "paper"), (SWAP.w(1) + 0.16, "pink"), (SWAP.w(1) + 0.32, "olive"),
         (SWAP.w(2), "olived"), (ZOOMS.s - 0.03, "real"), (SEC["s5"], "olived"), (SEC["s6"], "paper"),
         (STILLS.s - 0.05, "olive"), (EXPORT.s - 0.05, "olived"), (REELS.s - 0.05, "olive"), (SEC["pay"], "real"),
         (SEC["cta"], "olive"), (END_A, "olive")]
    return p


BG_PLAN = bg_plan()
WHIPS = [SEC["intro"], SEC["s1"], SEC["s3"], SEC["pay"], SEC["cta"]]
GROUND = dict(olive=OLIVE, olived=OLIVE_D, paper=PAPER, tomato=TOMATO, pink=PINK)


def bg_now(t):
    cur, prev, t0 = BG_PLAN[0][1], BG_PLAN[0][1], 0.0
    for tt, kind in BG_PLAN:
        if t >= tt:
            prev, cur, t0 = cur, kind, tt
    return prev, cur, t0


def draw_ground(c, kind, t, src, cam):
    if kind == "real":
        c.save()
        apply_cam(c, cam)
        c.drawImage(src.room(), 0, 0, SAMP)
        c.restore()
    else:
        ground(c, GROUND[kind], t=t)
        if kind == "paper":
            c.drawRect(skia.Rect.MakeWH(W, H), fill("#7A6A40", 0.05))


def draw_bg(c, t, src, cam):
    prev, cur, t0 = bg_now(t)
    dur = 0.12 if SWAP.w(1) - 0.01 <= t0 < SWAP.e + 0.2 else 0.3
    k = prog(t, t0, dur)
    if t0 in WHIPS or k >= 1 or prev == cur:
        draw_ground(c, cur, t, src, cam)
        return cur
    draw_ground(c, prev, t, src, cam)
    y = H * (1 - e_out(k)) - 40
    path = torn_path(-40, y, W + 80, H + 200, r=10, seed=int(t0 * 10), rough=14, step=22)
    c.save()
    c.clipPath(path, skia.ClipOp.kIntersect, True)
    draw_ground(c, cur, t, src, cam)
    c.restore()
    c.drawPath(path, stroke(CREAM, 6, 0.8 * (1 - k)))
    return cur


def dark_ground(kind):
    return kind not in ("paper", "pink")


# ================================================================== captions (behind the person)
CAP_Y = 470
CAP_SIZE = 100
CAP_OFF = [(0, SEC["s1"])] + [(p.s - 0.06, p.e + 0.12) for p in (S1, S2, S3, S4, S5, S6)] + [
           (LOOK.s - 0.05, LOOK.e + 0.06), (GONE.s - 0.05, GONE.e + 0.06),
           (SOUND.s - 0.05, SOUND.e + 0.12), (PROOF.w(2) - 0.05, PROOF.e + 0.15), (VE.s - 0.05, VE.e + 0.12),
           (SEC["cta"], TOTAL + 1)]
KEY = {"system", "raw", "one", "take", "mistakes", "every", "word", "strongest", "front", "two", "seconds",
       "everything", "story", "cut", "pauses", "ums", "retakes", "exact", "captions", "voice", "behind",
       "background", "swapped", "zooms", "matters", "original", "music", "whooshes", "scratch", "copyright",
       "never", "stills", "key", "moment", "energy", "cleaner", "changes", "command", "reels", "feeds", "youtube",
       "format", "taste", "frames", "listens", "watches", "transcribes", "lines", "renders"}


def _cap_groups():
    used = [w for w in WORDS if w["os"] is not None]
    used.sort(key=lambda w: w["os"])
    groups, cur = [], []
    for w in used:
        if cur and (len(cur) >= 3 or sum(len(x["d"]) + 1 for x in cur) + len(w["d"]) > 15
                    or w["os"] - cur[-1]["oe"] > 0.25 or cur[-1]["d"][-1] in ".,?"
                    or sec_of(w["os"]) != sec_of(cur[-1]["os"])):
            groups.append(cur)
            cur = []
        cur.append(w)
    groups.append(cur)
    return groups


CAPS_G = _cap_groups()


def cap_text(w):
    return w["d"].upper().strip(",.?")


def cap_front(t):
    return ZOOMS.w(3) - 0.05 <= t < ZOOM_B


def draw_captions(c, t, kind, front=False):
    if in_any(t, CAP_OFF) or cap_front(t) != front:
        return
    g, gi = None, -1
    for k, grp in enumerate(CAPS_G):
        nxt = CAPS_G[k + 1][0]["os"] if k + 1 < len(CAPS_G) else grp[-1]["oe"] + 0.4
        if grp[0]["os"] - 0.05 <= t < min(nxt - 0.03, grp[-1]["oe"] + 0.6):
            g, gi = grp, k
    if not g:
        return
    dark = dark_ground(kind) or front
    size = CAP_SIZE
    words = [cap_text(w) for w in g]
    gap = size * 0.36
    widths = [measure(s, "mont", size) for s in words]
    tot = sum(widths) + gap * (len(words) - 1)
    sc = min(1.0, 900 / tot)
    y = 1430 if front else CAP_Y
    capH = font("mont", size).getMetrics().fCapHeight
    c.save()
    c.translate(540, y)
    c.scale(sc, sc)
    x = -tot / 2
    for j, (w, s, wd) in enumerate(zip(g, words, widths)):
        if t < w["os"] - 0.05:
            break
        k = clamp((t - w["os"] + 0.05) / 0.24)
        sp = spring(k * 0.24, w=24, z=0.5)
        cur = w["os"] - 0.05 <= t < w["oe"] + 0.05
        key = w["k"] in KEY
        c.save()
        c.translate(x + wd / 2, (1 - sp) * 40)
        s_ = (0.55 + 0.45 * sp) * (1.07 if cur else 1.0)
        c.scale(s_, s_)
        c.rotate((hrand(w["i"]) - 0.5) * 4)
        if key:
            hb = INK if kind == "tomato" and not front else TOMATO
            hilite(c, -wd / 2 - 10, -capH - 14, wd + 20, capH + 28, prog(t, w["os"] - 0.06, 0.09), hb,
                   seed=w["i"], rot=-1.2)
            fg = CREAM
        else:
            fg = CREAM if dark else INK
        if dark and not key:
            kit.text(c, s, 0, 6, "mont", size, color="#000000", a=0.45, paint=fill("#000000", 0.45, blur=10))
        kit.text(c, s, 0, 0, "mont", size, color=fg)
        c.restore()
        x += wd + gap
    c.restore()


# ================================================================== pieces
def chapter(c, t, n, color, kind):
    """giant glowing step numeral beside the head + the spoken "step N" as a brush title, behind the person."""
    p = [S1, S2, S3, S4, S5, S6][n]
    a, b = SEC[STEP_SECS[n]], p.e + (0.25 if n in (0, 1) else 0.55)
    if not a <= t < b:
        return
    k = prog(t, a, 0.32)
    ko = prog(t, b - 0.2, 0.2)
    gl = 0.9 if dark_ground(kind) else 0.25
    x = 185 - e_in(ko) * 400
    y = 950 + (1 - e_out(k)) * 120
    glow_text(c, f"0{n + 1}", x, y, 330, color, a=e_out(k) * (1 - ko), glow=gl)
    caps(c, STEP_NAMES[n], x, y - 300, 40, color, a=e_out(k) * (1 - ko), anchor="c", tracking=0.06)
    kt = prog(t, p.s - 0.06, 0.3)
    kto = prog(t, p.e + 0.02, 0.15)
    word = ["one", "two", "three", "four", "five", "six"][n]
    c.save()
    c.translate(540, 500)
    s = lerp(1.35, 1.0, e_out(kt))
    c.scale(s, s)
    glow_text(c, f"step {word}", 0, 0, 200, color, a=clamp(kt * 3) * (1 - kto), rot=-4, glow=gl, maxw=900)
    c.restore()


def step_tracker(c, t, kind):
    """STEP 0N / 06 and six dots, top left."""
    if t < I_STEP.s or t >= SEC["pay"]:
        return
    n = sum(1 for s in STEP_SECS if t >= SEC[s])
    fg = CREAM if dark_ground(kind) else INK
    a = e_out(prog(t, I_STEP.s, 0.3)) * (1 - prog(t, SEC["pay"] - 0.2, 0.2))
    x0, y0 = 70, 262
    if n:
        mono(c, f"STEP 0{n}/06 · {STEP_NAMES[n - 1]}", x0, y0, 26, fg, a)
    for j in range(6):
        kj = prog(t, I_STEP.s + j * 0.07, 0.25) if t < SEC["s1"] else 1
        r = 9 * e_back(kj)
        cx = x0 + 9 + j * 30
        if j < n:
            c.drawCircle(cx, y0 + 30, r, fill(CREAM if kind == "tomato" else TOMATO, a))
        else:
            c.drawCircle(cx, y0 + 30, r, stroke(fg, 2.5, a * 0.8))


def waveform_bars(c, x, y, w, h, ts, n=26, color=CREAM, a=1.0):
    """bars from the real voice level around source time ts."""
    for j in range(n):
        lv = VOICE_ENV(ts + (j - n / 2) * 0.03)
        bh = max(6, h * clamp(lv * 1.1 + 0.04 * math.sin(j * 1.7 + ts * 9)))
        bx = x + j * w / n
        c.drawRRect(kit.rrect(bx, y - bh / 2, w / n * 0.55, bh, 4), fill(color, a))


_VENV = None


def VOICE_ENV(ts):
    global _VENV
    if _VENV is None:
        import wave
        with wave.open(str(HERE / "work" / "audio16k.wav")) as wv:
            x = np.frombuffer(wv.readframes(wv.getnframes()), np.int16).astype(np.float32) / 32768
        hop = 160
        e = np.sqrt(np.convolve(x ** 2, np.ones(400) / 400, "same"))[::hop]
        _VENV = np.clip(e / (np.percentile(e, 98) + 1e-6), 0, 1)
    i = int(ts * 100)
    return float(_VENV[i]) if 0 <= i < len(_VENV) else 0.0


def thumb(img, cx, cy, w, h, src_w, src_h):
    """centre-crop rect from the 1080x1920 frame around (cx, cy) of size src_w x src_h."""
    return skia.Rect.MakeXYWH(clamp(cx - src_w / 2, 0, W - src_w), clamp(cy - src_h / 2, 0, H - src_h), src_w, src_h)


def eq_bars(c, t, a0, a1):
    if not a0 <= t < a1:
        return
    k = e_out(prog(t, a0, 0.3)) * (1 - prog(t, a1 - 0.25, 0.25))
    n = 18
    for j in range(n):
        ph = ((t - DROP_T) % BEAT) / BEAT if t >= DROP_T else 0.6
        lv = 0.35 + 0.35 * abs(math.sin(j * 0.9 + t * 3.1)) + 0.3 * (1 - ph) ** 2 * (j % 3 == 0)
        bh = 900 * lv * k
        x = 30 + j * 1020 / n
        colr = TOMATO if j % 4 == 1 else CREAM
        c.drawRRect(kit.rrect(x, H - 380 - bh, 1020 / n * 0.62, bh, 10), fill(colr, 0.85))


# ---------------------------------------------------------------- hook
def hook_behind(c, t):
    if t >= SEC["intro"]:
        return
    kit_caps_pop(c, "THIS EXACT VIDEO", 540, 400, 92, t, H_THIS.s - 0.06, CREAM)
    kit_caps_pop(c, "WENT THROUGH ALL", 540, 505, 66, t, H_WENT.s - 0.05, CREAM, a=0.92)
    if t >= H_SIX.s - 0.04:
        k = prog(t, H_SIX.s - 0.04, 0.3)
        c.save()
        c.translate(200, 1080)
        s = lerp(1.5, 1.0, e_out(k))
        c.scale(s, s)
        glow_text(c, "6", 0, 0, 760, TOMATO, a=clamp(k * 3), glow=1.2)
        c.restore()
    if t >= H_SIX.w(1) - 0.04:
        k = prog(t, H_SIX.w(1) - 0.04, 0.3)
        glow_text(c, "steps", 915, 610 + (1 - e_out(k)) * 60, 118, CREAM, a=e_out(k), rot=-8)


def kit_caps_pop(c, s, x, y, size, t, t0, color, a=1.0, maxw=940):
    """caps line, letters springing up one by one."""
    if t < t0:
        return
    w = measure(s, "mont", size)
    if w > maxw:
        size *= maxw / w
        w = maxw
    f = font("mont", size)
    xx = x - w / 2
    for i, ch in enumerate(s):
        cw = f.measureText(ch)
        k = clamp((t - t0 - i * 0.018) / 0.25)
        if k > 0:
            sp = spring(k * 0.25, w=24, z=0.5)
            c.drawString(ch, xx, y + (1 - sp) * size * 0.5 + 6, f, fill("#000000", 0.4 * a * clamp(k * 3), blur=9))
            c.drawString(ch, xx, y + (1 - sp) * size * 0.5, f, fill(color, a * clamp(k * 3)))
        xx += cw


# ---------------------------------------------------------------- intro / CTA card scene
def draw_card_scene(c, t, src, g):
    ground(c, OLIVE, t=t)
    x, y, w, h = CARD
    cta = t >= SEC["cta"]
    k = prog(t, SEC["cta"] if cta else SEC["intro"], 0.4)
    rot = lerp(-4, -1.2, e_out(k)) if not cta else lerp(3, 1.0, e_out(k))
    dy = (1 - e_out(k)) * 80
    src_rect = skia.Rect.MakeXYWH((W - w / CARD_S) / 2, CARD_SRC_Y, w / CARD_S, h / CARD_S)
    zz = 1 + 0.03 * prog(t, SEC["cta"] if cta else SEC["intro"], 4)
    sr = skia.Rect.MakeXYWH(src_rect.centerX() - src_rect.width() / zz / 2, src_rect.top() + src_rect.height() * (1 - 1 / zz) * 0.3,
                            src_rect.width() / zz, src_rect.height() / zz)
    photo_card(c, src.bg(), x, y + dy, w, h, seed=3 if cta else 1, src_rect=sr, rot=rot)
    if not cta:
        # title over the chest, the reference's glowing brush lettering
        if t >= I_HERE.w(5) - 0.05:
            kk = prog(t, I_HERE.w(5) - 0.05, 0.3)
            glow_text(c, "inside a", 540, 1095 + (1 - e_out(kk)) * 30, 92, CREAM, a=e_out(kk), rot=-3)
        if t >= I_HERE.w(7) - 0.05:
            kk = prog(t, I_HERE.w(7) - 0.05, 0.35)
            c.save()
            c.translate(540, 1265)
            s = lerp(1.35, 1.0, e_out(kk))
            c.scale(s, s)
            glow_text(c, "vibe edit", 0, 0, 220, CREAM, a=clamp(kk * 2.5), rot=-3, maxw=760)
            c.restore()
        caps_block(c, ["HERE IS WHAT ACTUALLY HAPPENS", "INSIDE A VIBE EDIT,", "STEP BY STEP."], 150, 1400, 40,
                   CREAM, k=clamp((t - I_HERE.s) / max(0.1, I_STEP.e - I_HERE.s)) * 1.15)
        smiley(c, 870, 330, 66, CREAM, k=prog(t, I_HERE.w(4), 0.4), rot=-12 + 6 * math.sin(t * 2))
    else:
        lines = ["SO IF YOU WANT TO SEE", "WHAT I ACTUALLY RECORDED…"]
        caps_block(c, lines, 150, 1400, 44, CREAM, k=clamp((t - SOIF.s) / max(0.1, REC.e - SOIF.s)) * 1.1)
        if t >= REC.s:
            kk = prog(t, REC.s, 0.45)
            rx = lerp(1150, 640, e_out(kk))
            raw = Src(src.ts)
            photo_card(c, raw.raw_img(), rx, 790, 330, 560, seed=9, src_rect=skia.Rect.MakeXYWH(140, 380, 800, 1357),
                       rot=lerp(14, 6, e_out(kk)), burn=0.3)
            pill(c, "RAW · UNEDITED", rx + 165, 790, 26, TOMATO, CREAM, k=prog(t, REC.s + 0.2, 0.3), rot=6)
        smiley(c, 870, 330, 66, CREAM, k=prog(t, SOIF.s + 0.1, 0.4), rot=10 + 6 * math.sin(t * 2))


# ---------------------------------------------------------------- end card
def end_card(c, t):
    k = prog(t, END_A, 0.35)
    if k <= 0:
        return
    path = torn_path(-40, H * (1 - e_out(k)) - 40, W + 80, H + 200, r=10, seed=77, rough=14, step=22)
    c.save()
    c.clipPath(path, skia.ClipOp.kIntersect, True)
    ground(c, OLIVE, t=t)
    t0 = END_A + 0.15
    kk = prog(t, t0, 0.4)
    glow_text(c, "comment", 540, 600 + (1 - e_out(kk)) * 40, 190, CREAM, a=e_out(kk), rot=-4)
    k2 = prog(t, t0 + 0.25, 0.45)
    if k2 > 0:
        c.save()
        c.translate(540, 820)
        s = lerp(1.8, 1.0, e_out(clamp(k2 / 0.5)))
        c.scale(s, s)
        c.rotate(-3)
        bw = measure(CTA_WORD, "mont", 210) + 110
        rr = kit.rrect(-bw / 2, -150, bw, 230, 34)
        c.drawRRect(rr.makeOffset(8, 14), fill("#000000", 0.35 * clamp(k2 * 3), blur=16))
        c.drawRRect(rr, fill(TOMATO, clamp(k2 * 3)))
        kit.text(c, CTA_WORD, 0, 38, "mont", 210, color=CREAM, a=clamp(k2 * 3))
        c.restore()
    caps_block(c, ["AND I'LL SEND YOU THE RAW TAKE", "+ THE WHOLE SYSTEM"], 540, 1010, 40, CREAM,
               k=prog(t, t0 + 0.6, 0.5), anchor="c")
    # comment box typing the word
    k3 = prog(t, t0 + 0.9, 0.35)
    if k3 > 0:
        y = 1170 + (1 - e_out(k3)) * 60
        ui_card(c, 120, y, 840, 110, PAPER, r=55, a=e_out(k3))
        smiley(c, 182, y + 55, 30, INK, a=e_out(k3), width=4)
        n = int(clamp((t - t0 - 1.15) / 0.12, 0, len(CTA_WORD)))
        txt = CTA_WORD[:n] if n else "Add a comment…"
        kit.text(c, txt, 240, y + 70, "montb" if n else "italic", 44 if n else 46, color=INK if n else "#8A8470",
                 a=e_out(k3), anchor="l")
        if n and int(t * 3) % 2 == 0 and n < len(CTA_WORD):
            c.drawRect(skia.Rect.MakeXYWH(240 + measure(txt, "montb", 44) + 4, y + 30, 4, 50), fill(INK))
        sent = prog(t, t0 + 1.15 + 0.12 * len(CTA_WORD) + 0.15, 0.25)
        cc = TOMATO if sent > 0 else OLIVE_L
        c.drawCircle(890, y + 55, 38 * (1 + 0.25 * math.sin(sent * math.pi)), fill(cc, e_out(k3)))
        arrow_up(c, 890, y + 55, 22, CREAM, e_out(k3))
    smiley(c, 880, 420, 70, CREAM, k=prog(t, t0 + 0.4, 0.5), rot=-10 + 8 * math.sin(t * 2.2))
    mono(c, BRAND, 540, 1380, 30, CREAM, e_out(prog(t, t0 + 0.8, 0.4)), anchor="c")
    c.drawRect(skia.Rect.MakeXYWH(390, 1405, 300, 3), fill(TOMATO, e_out(prog(t, t0 + 0.9, 0.4))))
    c.restore()


def arrow_up(c, x, y, s, color, a):
    p = stroke(color, 6, a)
    c.drawLine(x, y + s * 0.7, x, y - s * 0.7, p)
    c.drawLine(x - s * 0.55, y - s * 0.1, x, y - s * 0.7, p)
    c.drawLine(x + s * 0.55, y - s * 0.1, x, y - s * 0.7, p)


# ---------------------------------------------------------------- step 1: raw in
def s1_band(c, t):
    if not DROP.s - 0.1 <= t < S2.s:
        return
    ko = prog(t, S2.s - 0.25, 0.25)
    k = e_out(prog(t, DROP.s + 0.1, 0.35)) * (1 - ko)
    x, y, w, h = 100, 540, 880, 280
    rr = kit.rrect(x, y, w, h, 30)
    c.drawRRect(rr, fill(OLIVE, 0.55 * k))
    pth = skia.Path()
    pth.addRRect(rr)
    p = stroke(CREAM, 4, 0.85 * k)
    p.setPathEffect(skia.DashPathEffect.Make([22, 14], t * 40))
    c.drawPath(pth, p)
    mono(c, "DROP RAW FOOTAGE HERE", x + 30, y - 18, 24, CREAM, k)
    # the raw take drops in
    kd = prog(t, DROP.w(1), 0.4)
    if kd > 0:
        ty = lerp(-350, y + 20, e_out(kd)) + 10 * math.sin(clamp(kd * 2 - 1) * math.pi)
        src = Src(src_at(t))
        photo_card(c, src.raw_img(), x + 40, ty, 140, 240, seed=5, src_rect=skia.Rect.MakeXYWH(150, 300, 780, 1340),
                   rot=lerp(-12, -3, e_out(kd)), burn=0.25, a=k)
    kf = prog(t, DROP.w(5), 0.3)
    if kf > 0:
        mono(c, "take_01.mov", x + 230, y + 80, 40, CREAM, k * e_out(kf))
        mono(c, "1:20 · 4K→1080 · 1 take", x + 230, y + 125, 26, CREAM, 0.75 * k * e_out(kf))
        bar = clamp((t - DROP.w(5)) / 1.0)
        c.drawRRect(kit.rrect(x + 230, y + 165, 580, 18, 9), fill(CREAM, 0.25 * k))
        c.drawRRect(kit.rrect(x + 230, y + 165, 580 * e_io(bar), 18, 9), fill(TOMATO, k))
        mono(c, f"{int(100 * e_io(bar)):3d}%", x + 820, y + 183, 22, CREAM, k, anchor="r")
    if t >= ONE.w(1) - 0.03:
        stamp(c, "ONE TAKE", x + 740, y - 4, 46, prog(t, ONE.w(1) - 0.03, 0.4), TOMATO, rot=-9, fill_bg=CREAM,
              a=1 - ko)
    for j, (lab, bg) in enumerate((("um…", PINK), ("uh", CREAM), ("retake", TOMATO), ("pause", PINK))):
        tj = MIST.w(0) + j * 0.12
        pill(c, lab, x + 300 + j * 150, y + 245, 26, bg, INK if bg != TOMATO else CREAM, k=prog(t, tj, 0.3),
             a=1 - ko, rot=(hrand("m", j) - 0.5) * 14)


# ---------------------------------------------------------------- step 2: listen
TLINES = ["here is what actually happens inside a", "vibe edit. step by step. step one, you", "drop in your raw footage. one take…",
          "this exact video went through all six steps."]


def s2_band(c, t, src):
    if not WATCH.s - 0.1 <= t < S3.s:
        return
    ko = prog(t, S3.s - 0.25, 0.25)
    x, y, w, h = 90, 530, 900, 300
    # watches + listens
    if t < TRANS.s:
        k = e_out(prog(t, WATCH.s, 0.35)) * (1 - prog(t, TRANS.s - 0.15, 0.15))
        sr = skia.Rect.MakeXYWH(140, 520, 800, 700)
        photo_card(c, src.bg(), x, y + 10, 340, 280, seed=11, src_rect=sr, a=k, rot=-2)
        kw = prog(t, WATCH.w(2), 0.3)
        pill(c, "● WATCHING", x + 170, y + 10, 24, TOMATO, CREAM, k=kw, a=k, rot=-2)
        kl = prog(t, WATCH.w(4), 0.3)
        if kl > 0:
            ui_card(c, x + 380, y + 30, 520, 240, INK, a=k * e_out(kl))
            waveform_bars(c, x + 410, y + 150, 460, 150, src.ts, color=CREAM, a=k * e_out(kl))
            mono(c, "LISTENING", x + 410, y + 70, 24, TOMATO, k * e_out(kl))
        return
    # transcript card
    k = e_out(prog(t, TRANS.s, 0.3)) * (1 - prog(t, FIRST.s - 0.1, 0.2))
    if k > 0:
        c.save()
        c.translate(0, (1 - k) * 40)
        ui_card(c, x, y, w, h, WHITE, a=k)
        nwords = sum(1 for wd in WORDS if wd["os"] is not None)
        cnt = int(nwords * clamp((t - TRANS.s) / max(0.2, TRANS.e - TRANS.s)))
        mono(c, f"TRANSCRIPT · {cnt} WORDS", x + 34, y + 50, 22, OLIVE, k)
        nchars = int(clamp((t - TRANS.s) / max(0.2, TRANS.e - TRANS.s + 0.3)) * sum(len(s) for s in TLINES))
        kmove = e_io(prog(t, MOVES.s, 0.6))
        for j, ln in enumerate(TLINES):
            shown = ln[:max(0, nchars - sum(len(s) for s in TLINES[:j]))]
            row = j if j < 3 else 3
            if j < 3:
                row = j + kmove
            else:
                row = 3 - 3 * kmove
            ly = y + 108 + row * 52
            if j == 3 and t >= FINDS.w(2):
                hilite(c, x + 22, ly - 34, measure(ln, "mono", 27) + 26, 46, prog(t, FINDS.w(2), 0.3), TOMATO,
                       seed=3, a=0.9 * k, rot=0)
            kit.text(c, shown, x + 34, ly, "mono", 27, color=CREAM if (j == 3 and t >= FINDS.w(2)) else INK,
                     a=k, anchor="l")
        if t >= FINDS.w(2):
            pill(c, "STRONGEST LINE", x + w - 190, y + 2, 22, TOMATO, CREAM, k=prog(t, FINDS.w(2) + 0.1, 0.3),
                 a=k, rot=3)
        if t >= MOVES.w(3):
            pill(c, "→ 0:00  HOOK", x + 140, y + h, 22, INK, CREAM, k=prog(t, MOVES.w(3), 0.3), a=k, rot=-2)
        c.restore()
    # the first two seconds
    if t >= FIRST.s - 0.1:
        k = e_out(prog(t, FIRST.s - 0.1, 0.3)) * (1 - ko)
        cx, cy, r = 540, 680, 140
        c.drawCircle(cx, cy, r, fill(WHITE, k))
        c.drawCircle(cx, cy, r, stroke(INK, 6, k))
        el = clamp((t - FIRST.w(3)) / 1.1) * 2.0
        sweep = 360 * el / 2.0
        if sweep > 0:
            pth = skia.Path()
            pth.addArc(skia.Rect.MakeXYWH(cx - r + 22, cy - r + 22, 2 * r - 44, 2 * r - 44), -90, sweep)
            c.drawPath(pth, stroke(TOMATO, 26, k, cap="butt"))
        kit.text(c, f"{el:.1f}s", cx, cy + 26, "mont", 72, color=INK, a=k)
        mono(c, "THE HOOK WINDOW", cx, cy + r + 52, 24, INK, k, anchor="c")
        for j, tk in enumerate((FIRST.w(3), FIRST.w(3) + 0.55)):
            pass


# ---------------------------------------------------------------- step 3: story cut (chest UI, in front)
BLOCKS = [("clip", 1.2), ("PAUSE", 0.55), ("clip", 0.9), ("UM", 0.4), ("clip", 1.3), ("RETAKE", 0.8), ("clip", 0.7),
          ("PAUSE", 0.5), ("clip", 1.0)]
BAD_AT = {"PAUSE": 0, "UM": 1, "RETAKE": 2}


def s3_front(c, t):
    if not STORY.s - 0.05 <= t < S4.s:
        return
    ko = prog(t, S4.s - 0.25, 0.25)
    k = e_out(prog(t, STORY.s - 0.05, 0.3)) * (1 - ko)
    x, y, w, h = 80, 1180, 840, 270
    c.save()
    c.translate(0, (1 - k) * 80)
    ui_card(c, x, y, w, h, INK, a=0.93 * k)
    mono(c, "STORY CUT", x + 30, y + 48, 24, TOMATO, k)
    if t < EXACT.s:
        kg = e_io(prog(t, GONE.s, 0.45))
        tot0 = sum(d for _, d in BLOCKS)
        tot1 = sum(d for n, d in BLOCKS if n == "clip")
        tw = w - 60
        xx = x + 30
        removed = 0.0
        for j, (name, d) in enumerate(BLOCKS):
            bad = name != "clip"
            dd = d * (1 - kg) if bad else d
            if bad:
                removed += d * kg
            bw = tw * dd / lerp(tot0, tot1, kg)
            if bw > 1:
                if bad:
                    hot = t >= PUR.w(BAD_AT[name]) - 0.03
                    a_ = k * (0.55 + 0.45 * hot)
                    c.drawRRect(kit.rrect(xx + 2, y + 90, bw - 4, 100, 10), fill(TOMATO, a_))
                    if bw > 60:
                        mono(c, name, xx + bw / 2, y + 148, 18, CREAM, a_ * (1 - kg), anchor="c")
                    if hot and kg <= 0:
                        c.drawRRect(kit.rrect(xx, y + 86, bw, 108, 12), stroke(CREAM, 3, k))
                else:
                    c.drawRRect(kit.rrect(xx + 2, y + 90, bw - 4, 100, 10), fill(OLIVE_L, k))
                    for q in range(int(bw / 14)):
                        hh = 20 + 50 * abs(math.sin(j * 3 + q * 0.8))
                        c.drawRect(skia.Rect.MakeXYWH(xx + 8 + q * 14, y + 140 - hh / 2, 5, hh), fill(CREAM, 0.6 * k))
            xx += bw
        if kg > 0:
            mono(c, f"−{removed:.1f}s dead air", x + w - 30, y + 48, 22, CREAM, k, anchor="r")
            mono(c, "cut on every gap", x + 30, y + 236, 20, CREAM, 0.8 * k * kg)
    else:
        # down to the exact word: word chips + a cut line that snaps between two words
        ke = prog(t, EXACT.s, 0.3)
        words = ["down", "to", "the", "exact", "word"]
        xx = x + 40
        for j, wd in enumerate(words):
            kj = prog(t, EXACT.w(j) - 0.03, 0.2)
            ww = measure(wd, "monob", 30) + 40
            c.drawRRect(kit.rrect(xx, y + 100, ww, 64, 14), fill(CREAM if kj > 0 else OLIVE_L, k))
            kit.text(c, wd, xx + ww / 2, y + 143, "monob", 30, color=INK, a=k)
            if j == 3:
                cut_x = xx - 13
            xx += ww + 26
        kc = e_back(prog(t, EXACT.w(3), 0.3))
        if kc > 0:
            c.drawRect(skia.Rect.MakeXYWH(cut_x - 2.5, y + 82, 5, 100 * kc), fill(TOMATO, k))
            c.drawCircle(cut_x, y + 82, 10 * kc, fill(TOMATO, k))
            mono(c, "cut point ±1 frame", x + 30, y + 236, 20, CREAM, 0.8 * k * ke)
    c.restore()


def s3_behind(c, t):
    if GONE.s - 0.05 <= t < GONE.e + 0.06:
        k = prog(t, GONE.s - 0.05, 0.25)
        ko = prog(t, GONE.e - 0.06, 0.12)
        c.save()
        c.translate(540, 480)
        s = lerp(1.5, 1.0, e_out(k))
        c.scale(s, s)
        glow_text(c, "gone.", 0, 0, 260, CREAM, a=clamp(k * 3) * (1 - ko), rot=-4)
        c.restore()
        marker(c, [(260, 420), (540, 400), (830, 380)], prog(t, GONE.s + 0.1, 0.15), TOMATO, 22, a=1 - ko)


# ---------------------------------------------------------------- step 4: the look
def s4_behind(c, t, kind):
    if LOOK.s - 0.05 <= t < LOOK.e + 0.06:
        k = prog(t, LOOK.s - 0.05, 0.3)
        ko = prog(t, LOOK.e - 0.06, 0.12)
        glow_text(c, "the look", 540, 490 + (1 - e_out(k)) * 50, 230, CREAM, a=e_out(k) * (1 - ko), rot=-4)
    if BEHIND.s - 0.05 <= t < SWAP.w(1):
        ko = prog(t, SWAP.w(1) - 0.15, 0.15)
        for j, (wd, yy) in enumerate((("TEXT", 860), ("BEHIND", 1150), ("YOU", 1440))):
            tj = BEHIND.w(j) - 0.04
            if t < tj:
                continue
            kj = prog(t, tj, 0.25)
            size = 300 if j != 1 else 250
            c.save()
            c.translate(540, yy)
            s = lerp(1.4, 1.0, e_out(kj))
            c.scale(s, s)
            kit.text(c, wd, 0, 0, "mont", size, color=CREAM if j != 1 else INK, a=clamp(kj * 3) * (1 - ko))
            c.restore()
    # captions that hit on your voice: a live voice line under the caption
    if CAPS.s <= t < CAPS.e + 0.2:
        k = e_out(prog(t, CAPS.s, 0.25)) * (1 - prog(t, CAPS.e, 0.2))
        waveform_bars(c, 230, 540, 620, 60, src_at(t), n=34, color=CREAM, a=0.8 * k)


def zoom_brackets(c, t, src_ts):
    if not ZOOM_A <= t < ZOOM_B:
        return
    k = e_back(prog(t, ZOOM_A, 0.25)) * (1 - prog(t, ZOOM_B - 0.12, 0.12))
    fx, fy = face_out(t, src_ts)
    bw, bh = 330 * k, 400 * k
    for sx in (-1, 1):
        for sy in (-1, 1):
            x0, y0 = fx + sx * bw, fy + sy * bh - 20
            p = stroke(CREAM, 9, clamp(k))
            c.drawLine(x0, y0, x0 - sx * 70, y0, p)
            c.drawLine(x0, y0, x0, y0 - sy * 70, p)
    if t >= ZOOMS.w(4):
        pill(c, "PUNCH-IN ×1.6", 200, 330, 26, TOMATO, CREAM, k=prog(t, ZOOMS.w(4), 0.3), rot=-4)


# ---------------------------------------------------------------- step 5: sound
def s5_front(c, t):
    if not MUSIC.s - 0.05 <= t < S6.s:
        return
    ko = prog(t, S6.s - 0.25, 0.25)
    x, y, w, h = 100, 1200, 820, 250
    if t < WHOOSH.s:
        k = e_out(prog(t, MUSIC.s - 0.05, 0.3)) * (1 - prog(t, WHOOSH.s - 0.1, 0.1))
        ui_card(c, x, y, w, h, PAPER, a=k)
        cx, cy = x + 125, y + h / 2
        c.save()
        c.translate(cx, cy)
        c.rotate(t * 200)
        c.drawCircle(0, 0, 92, fill(INK, k))
        for rr in (80, 66, 52):
            c.drawCircle(0, 0, rr, stroke("#3A3A30", 2, k))
        c.drawCircle(0, 0, 32, fill(TOMATO, k))
        c.drawCircle(0, -18, 5, fill(CREAM, k))
        c.restore()
        caps(c, "ORIGINAL SCORE", x + 250, y + 95, 46, INK, k)
        mono(c, f"{BPM} BPM · A MAJOR · MADE FOR THIS REEL", x + 252, y + 140, 20, OLIVE, k)
        pr = clamp((t - DROP_T) / 6)
        c.drawRRect(kit.rrect(x + 252, y + 175, 520, 12, 6), fill(INK, 0.15 * k))
        c.drawRRect(kit.rrect(x + 252, y + 175, 520 * pr, 12, 6), fill(TOMATO, k))
        return
    if t < SCRATCH.s:
        k = 1 - prog(t, SCRATCH.s - 0.1, 0.1)
        kw = prog(t, WHOOSH.s - 0.03, 0.3)
        if kw > 0:
            xx = lerp(-300, 330, e_out(kw))
            for j in range(4):
                c.drawRRect(kit.rrect(xx - 330 - j * 50, y + 70 + j * 30, 220, 10, 5), fill(CREAM, 0.6 * k * (1 - j / 4)))
            stamp(c, "WHOOSH", xx, y + 110, 70, 1, CREAM, rot=-6, fill_bg=INK, fg=CREAM, a=k)
        if t >= HITS.s - 0.03:
            kh = prog(t, HITS.s - 0.03, 0.4)
            star(c, 760, y + 120, 150 * e_back(kh), TOMATO, k)
            kit.text(c, "HIT!", 760, y + 145, "mont", 74, color=CREAM, a=k * clamp(kh * 3))
        return
    if t < CLAIMS.s:
        k = e_out(prog(t, SCRATCH.s, 0.25)) * (1 - prog(t, CLAIMS.s - 0.1, 0.1))
        ui_card(c, x, y, w, h, INK, a=k)
        mono(c, "SYNTH · GENERATED FROM SCRATCH · 0 SAMPLES", x + 30, y + 48, 20, TOMATO, k)
        kd = clamp((t - SCRATCH.s) / 0.9)
        pts = []
        for q in range(int(161 * kd)):
            xx = x + 30 + q * (w - 60) / 160
            ph = q / 160
            yy = y + 150 + 70 * math.sin(ph * 24 + t * 8) * math.sin(ph * math.pi) * (0.6 + 0.4 * math.sin(ph * 5))
            pts.append((xx, yy))
        if len(pts) > 2:
            marker(c, pts, 1, CREAM, 6, a=k)
        return
    # no copyright claims
    k = e_out(prog(t, CLAIMS.s, 0.3)) * (1 - ko)
    cx, cy = 290, y + 125
    c.drawCircle(cx, cy, 95, fill(PAPER, k))
    c.drawCircle(cx, cy, 95, stroke(INK, 10, k))
    kit.text(c, "C", cx, cy + 40, "mont", 120, color=INK, a=k)
    kx = prog(t, CLAIMS.w(2) - 0.05, 0.25)
    marker(c, [(cx - 80, cy - 80), (cx + 80, cy + 80)], kx, TOMATO, 20, a=1 - ko)
    stamp(c, "0 CLAIMS", 650, cy, 74, prog(t, CLAIMS.w(4) - 0.1, 0.4), TOMATO, rot=-7, fill_bg=PAPER, a=1 - ko)


def star(c, x, y, r, color, a):
    if r <= 0:
        return
    p = skia.Path()
    n = 12
    for i in range(2 * n):
        rr = r if i % 2 == 0 else r * 0.62
        th = i * math.pi / n
        p.lineTo(x + rr * math.cos(th), y + rr * math.sin(th)) if i else p.moveTo(x + rr, y)
    p.close()
    c.drawPath(p, fill(color, a))


def s5_behind(c, t):
    eq_bars(c, t, DROP_T - 0.02, S6.s)
    if SOUND.s - 0.05 <= t < SOUND.e + 0.3:
        k = prog(t, SOUND.s - 0.05, 0.25)
        ko = prog(t, SOUND.e + 0.1, 0.2)
        c.save()
        c.translate(540, 500)
        s = lerp(1.6, 1.0, e_out(k))
        c.scale(s, s)
        glow_text(c, "sound.", 0, 0, 270, CREAM, a=clamp(k * 3) * (1 - ko), rot=-4)
        c.restore()


# ---------------------------------------------------------------- step 6: proof
STILL_TS = [(3.0, "HOOK"), (12.0, "RAW IN"), (20.0, "LISTEN"), (31.0, "CUT"), (40.0, "LOOK"), (52.0, "SOUND")]


def s6_front(c, t):
    if PROOF.w(2) - 0.05 <= t < STILLS.s:
        k = prog(t, PROOF.w(2) - 0.05, 0.4)
        stamp(c, "PROOF", 520, 1320, 150, k, TOMATO, rot=-7, fill_bg=PAPER, a=1 - prog(t, STILLS.s - 0.15, 0.15))


def s6_band(c, t):
    x, y = 90, 520
    # contact sheet of stills
    if STILLS.s - 0.05 <= t < SAY.s + 0.2:
        ko = prog(t, SAY.s - 0.05, 0.25)
        pill(c, "PREVIEW · BEFORE RENDER", 540, y + 10, 22, CREAM, INK, k=prog(t, STILLS.s, 0.3), a=1 - ko)
        for j, (ts, lab) in enumerate(STILL_TS):
            tj = STILLS.w(6) + j * 0.17 - 0.3
            kj = prog(t, tj, 0.35)
            if kj <= 0:
                continue
            cx = x + 75 + j * 150
            cy = y + 180 - ko * 400
            src = Src(ts)
            fx, fy = face(ts)
            sr = skia.Rect.MakeXYWH(clamp(fx - 330, 0, W - 660), fy - 420, 660, 1170)
            photo_card(c, src.room(0.85), cx - 65, lerp(cy - 600, cy - 115, e_out(kj)), 130, 230, seed=20 + j,
                       src_rect=sr, rot=(hrand("st", j) - 0.5) * 10, burn=0.4, a=1 - ko)
            mono(c, lab, cx, cy + 148, 18, CREAM, (1 - ko) * clamp(kj * 2), anchor="c")
            if t >= tj + 0.35:
                check_mark(c, cx + 40, cy - 100, 40, prog(t, tj + 0.35, 0.2), TOMATO, 9)
    # you say -> it changes
    if SAY.s - 0.05 <= t < EXPORT.s:
        ko = prog(t, EXPORT.s - 0.2, 0.2)
        bubble(c, 120, y + 40, "more energy", prog(t, SAY.w(2) - 0.05, 0.3), "YOU", CREAM, INK, 1 - ko)
        bubble(c, 120, y + 160, "cleaner", prog(t, SAY.w(5) - 0.05, 0.3), "YOU", CREAM, INK, 1 - ko)
        bubble(c, 520, y + 260, "done, updated", prog(t, SAY.w(8) - 0.05, 0.3), "SYSTEM", TOMATO, CREAM, 1 - ko, right=True)
    # one command exports
    if EXPORT.s - 0.05 <= t < REELS.s:
        k = e_out(prog(t, EXPORT.s - 0.05, 0.3))
        ui_card(c, x + 20, y + 40, 860, 240, INK, a=k)
        for j, cc in enumerate((TOMATO, CREAM, OLIVE_L)):
            c.drawCircle(x + 60 + j * 30, y + 75, 9, fill(cc, k))
        cmd = "$ vibe export --all"
        n = int(clamp((t - EXPORT.w(1)) / 0.6) * len(cmd))
        kit.text(c, cmd[:max(2, n)], x + 60, y + 150, "monob", 42, color=CREAM, a=k, anchor="l")
        bar = clamp((t - EXPORT.w(3)) / 0.8)
        c.drawRRect(kit.rrect(x + 60, y + 200, 760, 22, 11), fill(CREAM, 0.2 * k))
        c.drawRRect(kit.rrect(x + 60, y + 200, 760 * e_io(bar), 22, 11), fill(TOMATO, k))
    # every format
    if REELS.s - 0.05 <= t < VE.s:
        ko = prog(t, VE.s - 0.25, 0.25)
        frames = [("REELS", "9:16", 9, 16, REELS.w(2)), ("FEED", "4:5", 4, 5, FEEDS.w(0)),
                  ("YOUTUBE", "16:9", 16, 9, FEEDS.w(1)), ("SQUARE", "1:1", 1, 1, FEEDS.w(2))]
        xs = [95, 290, 520, 830]
        src = Src(src_at(t))
        for j, (lab, ar, aw, ah, tj) in enumerate(frames):
            kj = prog(t, tj - 0.05, 0.3)
            if kj <= 0:
                continue
            hh = 240 if aw <= ah else 240 * ah / aw * 1.45
            ww = hh * aw / ah
            cx, cy = xs[j], y + 170
            sr = skia.Rect.MakeXYWH(0, 0, 0, 0)
            fx, fy = face(src.ts)
            sw = min(W, 1000 * aw / max(aw, ah) * (1.6 if aw > ah else 1))
            sh = sw * ah / aw
            sr = skia.Rect.MakeXYWH(clamp(fx - sw / 2, 0, W - sw), clamp(fy - sh * 0.42, 0, H - sh), sw, sh)

            def drawf(cc, ww=ww, hh=hh, cx=cx, cy=cy, sr=sr):
                photo_card(cc, src.room(), cx - ww / 2, cy - hh / 2, ww, hh, seed=40 + j, src_rect=sr, burn=0.35,
                           a=1 - ko, shadow=0.3)
            pop_in(c, cx, cy, kj, drawf, rot=8)
            mono(c, f"{lab} {ar}", cx, y + 330, 20, CREAM, (1 - ko) * clamp(kj * 2), anchor="c")
            if t >= FEEDS.w(3):
                check_mark(c, cx + ww / 2 - 10, cy - hh / 2 + 10, 40, prog(t, FEEDS.w(3) + j * 0.06, 0.2), TOMATO, 9)


def bubble(c, x, y, txt, k, who, bg, fg, a=1.0, right=False):
    if k <= 0:
        return
    s = lerp(0.4, 1.0, e_back(clamp(k / 0.6)))
    w = measure(txt, "montb", 46) + 70
    c.save()
    c.translate(x + (w if right else 0), y + 50)
    c.scale(s, s)
    c.translate(-(w if right else 0), -50)
    mono(c, who, 20 if not right else w - 20, -8, 18, CREAM, a * clamp(k * 3), anchor="l" if not right else "r")
    rr = kit.rrect(0, 0, w, 100, 50)
    c.drawRRect(rr.makeOffset(4, 8), fill("#000000", 0.3 * a, blur=8))
    c.drawRRect(rr, fill(bg, a * clamp(k * 3)))
    kit.text(c, txt, w / 2, 66, "montb", 46, color=fg, a=a * clamp(k * 3))
    c.restore()


# ---------------------------------------------------------------- payoff
def pay_behind(c, t):
    if VE.s - 0.05 <= t < VE.e + 0.3:
        k = prog(t, VE.w(2) - 0.08, 0.35)
        ko = prog(t, VE.e + 0.1, 0.2)
        caps(c, "THAT'S", 540, 300, 50, CREAM, a=e_out(prog(t, VE.s - 0.05, 0.2)) * (1 - ko), anchor="c")
        c.save()
        c.translate(540, 490)
        s = lerp(1.4, 1.0, e_out(k))
        c.scale(s, s)
        glow_text(c, "vibe editing", 0, 0, 210, CREAM, a=clamp(k * 3) * (1 - ko), rot=-4, maxw=960)
        c.restore()


def pay_front(c, t):
    if not TASTE.s - 0.05 <= t < SEC["cta"]:
        return
    k = e_out(prog(t, TASTE.s - 0.05, 0.3))
    x, y, w, h = 80, 1200, 840, 250
    ui_card(c, x, y, w, h, INK, a=0.93 * k)
    c.drawLine(x + w / 2, y + 30, x + w / 2, y + h - 30, stroke(CREAM, 2, 0.3 * k))
    mono(c, "YOU", x + 40, y + 55, 22, TOMATO, k)
    smiley(c, x + 100, y + 150, 50, CREAM, a=k, k=prog(t, TASTE.w(1), 0.4), rot=-8)
    if t >= TASTE.w(3) - 0.05:
        glow_text(c, "taste", x + 270, y + 175, 100, CREAM, a=e_out(prog(t, TASTE.w(3) - 0.05, 0.3)), glow=0.6)
    if t >= KEYF.s - 0.05:
        k2 = e_out(prog(t, KEYF.s - 0.05, 0.3))
        mono(c, "SYSTEM", x + w / 2 + 40, y + 55, 22, TOMATO, k2)
        lx0, lx1, ly = x + w / 2 + 50, x + w - 50, y + 165
        c.drawLine(lx0, ly, lx1, ly, stroke(CREAM, 3, 0.5 * k2))
        n = 6
        pts = []
        for j in range(n):
            kj = prog(t, KEYF.w(3) + j * 0.08 - 0.15, 0.25)
            px = lx0 + (lx1 - lx0) * j / (n - 1)
            py = ly - 60 * math.sin(j / (n - 1) * math.pi) * (1 if j % 2 else 0.6)
            pts.append((px, py))
            if kj > 0:
                c.save()
                c.translate(px, py)
                c.rotate(45)
                s = 16 * e_back(kj)
                c.drawRect(skia.Rect.MakeXYWH(-s, -s, 2 * s, 2 * s), fill(TOMATO if j % 2 else CREAM, k2))
                c.restore()
        marker(c, pts, prog(t, KEYF.w(4), 0.5), CREAM, 4, a=0.7 * k2)
        mono(c, "keyframes", lx1, y + 225, 20, CREAM, k2 * 0.8, anchor="r")


# ================================================================== draw
def draw(c, t, f):
    g = {}
    src_ts = src_at(t)
    c.clear(col(OLIVE_D))
    # whip pans between scenes: slide out / in, blur in post
    off = 0.0
    for tw in WHIPS:
        if tw - 0.14 <= t < tw:
            off = -W * 0.55 * e_in(prog(t, tw - 0.14, 0.14))
        elif tw <= t < tw + 0.16:
            off = W * 0.55 * (1 - e_out(prog(t, tw, 0.16)))
    if off:
        g["whip"] = abs(off) / W
        c.save()
        c.translate(off, 0)
    src = Src(src_ts, sat=1.3 if SAY.w(8) <= t < SAY.w(8) + 0.5 else 1.08)
    if card_mode(t):
        draw_card_scene(c, t, src, g)
    else:
        cam = camera(t, src_ts)
        kind = draw_bg(c, t, src, cam)
        # ---- behind the person
        hook_behind(c, t)
        sec = sec_of(t)
        if sec in STEP_SECS:
            n = STEP_SECS.index(sec)
            chapter(c, t, n, CREAM if dark_ground(kind) else OLIVE, kind)
        s1_band(c, t)
        s2_band(c, t, src)
        s3_behind(c, t)
        s4_behind(c, t, kind)
        s5_behind(c, t)
        s6_band(c, t)
        pay_behind(c, t)
        draw_captions(c, t, kind)
        # ---- the person
        c.save()
        apply_cam(c, cam)
        if kind != "real":
            c.drawImage(src.outline(6, CREAM), 0, 0, SAMP, skia.Paint(Alphaf=0.9))
        c.drawImage(src.person(), 0, 0, SAMP)
        c.restore()
        # ---- in front
        s3_front(c, t)
        zoom_brackets(c, t, src_ts)
        s5_front(c, t)
        s6_front(c, t)
        pay_front(c, t)
        draw_captions(c, t, kind, front=True)
        step_tracker(c, t, kind)
    end_card(c, t)
    if off:
        c.restore()
    # looks
    if t < 0.1:
        g["flash"] = 0.8 * (1 - t / 0.1)
    for st in (DROP_T, PROOF.w(2), GONE.s, H_SIX.s, SAY.w(8)):
        if st <= t < st + 0.1:
            g["flash"] = max(g.get("flash", 0), 0.3 * (1 - (t - st) / 0.1))
            g["ca"] = 8
    if SWAP.w(1) <= t < SWAP.w(2) + 0.1:
        g["ca"] = 5
    return g


SHAKES += [(H_SIX.s, 16), (ONE.w(1), 8), (FINDS.w(2), 6), (FIRST.we(6) - 0.2, 10), (GONE.s, 16), (BEHIND.w(1), 8),
           (DROP_T, 20), (HITS.s, 18), (CLAIMS.w(4), 10), (PROOF.w(2), 18), (SAY.w(8), 10), (KEYF.w(4), 6)]


# ================================================================== post
_VIG = None


def post(rgb, g, f):
    global _VIG
    if _VIG is None or _VIG.shape[:2] != rgb.shape[:2]:
        h, w = rgb.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        _VIG = (1 - 0.3 * np.clip(r - 0.55, 0, None) ** 1.5)[..., None].astype(np.float32)
    s = rgb.shape[1] / W
    out = rgb
    if g.get("whip"):
        k = int(max(3, g["whip"] * 160 * s)) | 1
        out = cv2.blur(out, (k, 1))
    out = out.astype(np.float32)
    ca = int(g.get("ca", 0) * s)
    if ca:
        out[..., 0] = np.roll(out[..., 0], ca, axis=1)
        out[..., 2] = np.roll(out[..., 2], -ca, axis=1)
    # soft halation on highlights (the reference's glowing film look)
    small = cv2.resize(out, (out.shape[1] // 8, out.shape[0] // 8), interpolation=cv2.INTER_AREA)
    hi = np.clip(small - 190, 0, None)
    hi = cv2.GaussianBlur(hi, (0, 0), 4)
    hi = cv2.resize(hi, (out.shape[1], out.shape[0]), interpolation=cv2.INTER_LINEAR)
    out = out + hi * np.array([0.55, 0.42, 0.22], np.float32)
    if g.get("flash"):
        out = out + (255 - out) * g["flash"]
    out *= _VIG
    out = np.clip(out, 0, 255).astype(np.uint8)
    return kit.grain(out, f, amt=0.02, scale=3)


FILM = kit.Film(draw, TOTAL, FPS, post=post, out_dir=OUT)


# ================================================================== audio
def sfx_list():
    S = []

    def a(t, kind, gain=-8, **kw):
        S.append(dict(t=t, kind=kind, gain_db=gain, **kw))

    a(0.0, "impact", -6)
    a(0.02, "whoosh", -12, dur=0.4)
    a(H_THIS.s, "pop", -14)
    a(H_WENT.s, "pop", -15)
    a(H_SIX.s, "impact", -5)
    a(H_SIX.w(1), "swish", -10)
    a(H_SIX.w(1) + 0.15, "pop", -12)
    for tw in WHIPS:
        a(tw - 0.16, "whoosh", -8, dur=0.35)
    a(I_HERE.w(7), "sparkle", -12)
    for j in range(6):
        a(I_STEP.s + j * 0.07, "tick", -15, pan=(j - 2.5) / 4)
    for n, p in enumerate((S1, S2, S3, S4, S5, S6)):
        a(SEC[STEP_SECS[n]] + 0.02, "swish" if n % 2 else "click", -10)
        if n not in (0, 2):
            a(SEC[STEP_SECS[n]] - 0.05, "whoosh", -12, dur=0.3)
    # step 1
    a(DROP.s, "whoosh", -12, dur=0.35)
    a(DROP.w(1) + 0.35, "impact", -12)
    a(DROP.w(5), "typing", -18, dur=0.8)
    a(ONE.w(1), "impact", -9)
    for j in range(4):
        a(MIST.w(0) + j * 0.12, "pop", -14, pan=(j - 1.5) / 3)
    # step 2
    a(WATCH.w(2), "shutter", -14)
    a(WATCH.w(4), "pop", -14)
    a(TRANS.s, "typing", -15, dur=max(0.4, TRANS.e - TRANS.s + 0.3))
    a(FINDS.w(2), "ding", -12)
    a(MOVES.s, "whoosh", -13, dur=0.5)
    a(MOVES.w(3), "click", -10)
    a(FIRST.s - 0.1, "pop", -13)
    for j in range(3):
        a(FIRST.w(3) + j * 0.55, "tick", -11)
    a(FIRST.we(6) - 0.2, "impact", -11)
    # step 3
    a(STORY.s, "whoosh", -13, dur=0.3)
    for j in range(3):
        a(PUR.w(j), "tick", -10)
    a(GONE.s - 0.04, "glitch", -10)
    a(GONE.s, "impact", -6)
    a(GONE.s + 0.1, "swish", -11)
    a(EXACT.w(3), "click", -8)
    # step 4
    a(LOOK.s - 0.03, "sparkle", -12)
    for j in range(3):
        a(BEHIND.w(j) - 0.03, "impact" if j == 1 else "pop", -12)
    for j, dt in enumerate((0, 0.16, 0.32)):
        a(SWAP.w(1) + dt, "swish", -11, pan=(j - 1) / 2)
    a(SWAP.w(2), "click", -10)
    a(ZOOMS.s - 0.06, "whoosh", -10, dur=0.3)
    a(ZOOMS.s, "impact", -12)
    a(ZOOMS.w(3), "riser", -14, dur=0.6)
    # step 5: the drop
    a(S5.s - 0.55, "riser", -9, dur=0.55 + DROP_T - S5.s)
    a(DROP_T, "impact", -8)
    a(DROP_T, "bass_drop", -9)
    a(MUSIC.s, "pop", -14)
    a(WHOOSH.e - 0.12, "whoosh", -7, dur=0.45)
    a(HITS.e - 0.06, "impact", -6)
    a(SCRATCH.s, "glitch", -15)
    a(CLAIMS.w(2), "swish", -11)
    a(CLAIMS.w(4) - 0.1, "impact", -9)
    # step 6
    a(PROOF.w(2) - 0.05, "impact", -5)
    a(PROOF.w(2), "shutter", -10)
    a(STILLS.s, "pop", -14)
    for j in range(6):
        a(STILLS.w(6) + j * 0.17 - 0.3, "shutter", -15, pan=(j - 2.5) / 4)
    for j in (2, 5):
        a(SAY.w(j) - 0.05, "pop", -11)
    a(SAY.w(8) - 0.05, "ding", -10)
    a(EXPORT.w(1), "typing", -14, dur=0.6)
    a(EXPORT.w(3) + 0.8, "ding", -13)
    for tj in (REELS.w(2), FEEDS.w(0), FEEDS.w(1), FEEDS.w(2)):
        a(tj - 0.05, "pop", -11)
    a(FEEDS.w(3), "sparkle", -11)
    # payoff + CTA
    a(VE.w(2) - 0.1, "sparkle", -10)
    a(VE.w(2) - 0.05, "impact", -10)
    a(TASTE.s, "pop", -13)
    a(KEYF.s, "pop", -13)
    for j in range(6):
        a(KEYF.w(3) + j * 0.08 - 0.15, "tick", -15)
    a(REC.s, "whoosh", -11, dur=0.4)
    a(REC.s + 0.4, "click", -11)
    a(END_A - 0.1, "whoosh", -9, dur=0.4)
    a(END_A + 0.4, "impact", -8)
    a(END_A + 1.05, "typing", -13, dur=0.12 * len(CTA_WORD) + 0.1)
    a(END_A + 1.15 + 0.12 * len(CTA_WORD) + 0.15, "pop", -8)
    a(END_A + 1.15 + 0.12 * len(CTA_WORD) + 0.2, "sparkle", -10)
    return S


ak.MOODS["retro_a"] = dict(bpm=BPM, scale="major", key="A", prog=[4, 3, 2, 1], drums="lofi", lead="keys", pad=True,
                           sevenths=True)
ak.MOODS["retro_b"] = dict(bpm=BPM, scale="major", key="A", prog=[4, 3, 2, 1], drums="four", lead="pluck", pad=True,
                           sevenths=True, pump=True)


MUSIC_DB, SFX_DB, DUCK_DB = -9, -4, -7


def build_audio():
    SR = ak.SR
    work = HERE / "work"
    vpath = work / "voice_clean.wav"
    if not vpath.exists():
        ff("-i", str(HERE / "raw" / "take.mp4"), "-vn", "-af",
           "highpass=f=85,afftdn=nf=-30:tn=1,equalizer=f=220:t=q:w=1.2:g=-2,equalizer=f=3200:t=q:w=1.5:g=2.5,"
           "equalizer=f=9000:t=h:w=0.7:g=1.5,acompressor=threshold=-21dB:ratio=3.2:attack=5:release=90:makeup=4,"
           "deesser=i=0.35,alimiter=limit=0.95", "-ar", str(SR), "-ac", "2", str(vpath))
    raw = ak.read_audio(vpath)
    n = int(TOTAL * SR) + 1
    voice = np.zeros((n, 2), np.float32)
    xf = int(0.012 * SR)
    speech_end = REC.e + 0.2
    for a, b, o, d, i0, i1 in EDL:
        bb = min(b, WORDS[i1]["e"] + 0.2)                  # the silent tail under the end card stays silent
        seg = raw[int(a * SR):int(bb * SR)].copy()
        if len(seg) > 2 * xf:
            ramp = np.linspace(0, 1, xf, dtype=np.float32)[:, None]
            seg[:xf] *= ramp
            seg[-xf:] *= ramp[::-1]
        i = int(o * SR)
        seg = seg[: max(0, n - i)]
        voice[i:i + len(seg)] += seg
    # music: warm lo-fi bed, muffled, until the drop on "Sound." then the full beat
    drop = int(DROP_T * SR)
    bed_a = ak.music_bed("retro_a", seconds=DROP_T + 2, intro_bars=0, seed=5)
    bed_b = ak.music_bed("retro_b", seconds=TOTAL - DROP_T + 2, intro_bars=0, seed=9)
    mus = np.zeros((n, 2), np.float32)
    la = np.stack([ak.filt(bed_a[:, ch], "low", 1500) for ch in range(2)], 1)
    la = la[:drop]
    la *= np.sqrt(np.mean(bed_a[:drop] ** 2) / (np.mean(la ** 2) + 1e-12)) * ak.db(-1)   # level-match the muffled bed
    mus[:len(la)] = la
    k = int(0.4 * SR)
    mus[drop - k:drop] *= np.linspace(1, 0.3, k)[:, None]
    lb = bed_b[: n - drop]
    mus[drop:drop + len(lb)] = lb
    fi = int(0.5 * SR)
    mus[:fi] *= np.linspace(0, 1, fi)[:, None]
    mus *= ak.duck_gain(voice, DUCK_DB)[:, None]
    end = int((TOTAL - 0.05) * SR)
    fo = int(1.0 * SR)
    mus[end - fo:end] *= np.linspace(1, 0, fo)[:, None]
    mus[end:] = 0
    mus *= ak.db(MUSIC_DB)
    fx = np.zeros_like(voice)
    for s in sfx_list():
        kind = s["kind"]
        clip = ak.SFX[kind](s["dur"]) if "dur" in s and kind in ("whoosh", "riser", "typing") else ak.SFX[kind]()
        ak.place(fx, clip, max(0.0, s["t"]), s["gain_db"] + SFX_DB, s.get("pan", 0.0))
    for name, x in (("voice", voice), ("music", mus), ("sfx", fx)):
        ak.write_wav(work / f"stem_{name}.wav", x)
    out = voice + mus + fx
    peak = np.max(np.abs(out)) or 1
    if peak > 0.98:
        out = np.tanh(out / peak * 1.2) / math.tanh(1.2) * 0.98
    path = work / "mix.wav"
    ak.write_wav(path, out)
    print("->", path, f"(speech ends {speech_end:.1f}s)")
    return path


def finish(picture, audio, out, vbr="2.9M"):
    """delivery file: H.264 high, two-pass ~2.9 Mbps (keeps it < 30 MB with the grain), AAC 48k, -14 LUFS."""
    ln = loudnorm_filter(audio)
    log = str(HERE / "work" / "x264pass")
    common = ["-c:v", "libx264", "-preset", "slow", "-b:v", vbr, "-maxrate", "4.5M", "-bufsize", "9M",
              "-pix_fmt", "yuv420p", "-profile:v", "high", "-r", str(FPS), "-passlogfile", log]
    ff("-i", str(picture), "-map", "0:v:0", *common, "-pass", "1", "-an", "-f", "null", "/dev/null")
    ff("-i", str(picture), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", *common, "-pass", "2", "-af", ln,
       "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out))
    print("->", out)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "stills":
        FILM.stills([float(x) for x in sys.argv[2:]])
    elif cmd == "sheet":
        FILM.sheet([round(TOTAL * (i + 0.5) / 48, 2) for i in range(48)], cols=8)
    elif cmd == "audio":
        build_audio()
    elif cmd == "info":
        print(f"total {TOTAL:.2f}s  (raw {NSRC / FPS:.1f}s)")
        for k, v in SEC.items():
            print(f"  {k:6} {v:6.2f}")
        for a, b, o, d, i0, i1 in EDL:
            txt = " ".join(WORDS[j]["d"] for j in range(i0, i1 + 1))
            print(f"  src {a:6.2f}-{b:6.2f}  out {o:6.2f} +{d:4.2f}  {txt}")
    elif cmd == "render":
        draft = "--draft" in sys.argv
        pic = FILM.render(OUT / ("draft_picture.mp4" if draft else "picture.mp4"), draft=draft)
        aud = build_audio()
        finish(pic, aud, OUT / ("draft.mp4" if draft else "vibe_reel.mp4"))


if __name__ == "__main__":
    main()
