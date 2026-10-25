"""creator: the second edit of the same take, in the style of the Pinterest creator-tutorial reference.

Reference look, measured from the clip:
    moody low-key grade, dark teal-grey room (~#475152), warm skin, heavy vignette; speaker full frame
    two-tier titles above the head: a small white hand-lettered caps line + one huge wide italic yellow
        word (#F8E20A) typed on letter by letter, with doodles (scribble underline, speech bubble, arrows)
    plain small white subtitles, 1-3 words, low in frame; white-on-black boxes on the split line
    split screen: clean white app UI on top (cursor, clicks, green highlight boxes, a giant word on a
        yellow card, a 96 % export), speaker below; RGB glitch-block transitions; PIP phone card + arrow CTA

    python3 creator.py stills 1.0 4.2 ...    -> out/stills/*.png
    python3 creator.py sheet                 -> out/creator_sheet.png
    python3 creator.py render                -> out/vibe_reel_v2.mp4
"""

import math
import sys
from pathlib import Path

import cv2
import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import edit as E  # noqa: E402  (words, cut list, phrases, matte, voice)
import audio_kit as ak  # noqa: E402
import kit  # noqa: E402
from kit import clamp, e_back, e_in, e_io, e_out, fill, font, hrand, lerp, measure, prog, spring, stroke  # noqa: E402
from vibelib import ff, loudnorm_filter  # noqa: E402

cv2.setNumThreads(1)
kit.FONTS.update(wide="ArchivoExpanded-BlackItalic.ttf", hand="RockSalt.ttf")
W, H, FPS = 1080, 1920, 30
OUT = HERE / "out"
TOTAL = E.TOTAL
SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNone)
CTA_WORD = E.CTA_WORD

YEL = "#F8E20A"
WHITE = "#FFFFFF"
INK = "#0B0C0C"
UI_LINE = "#E6E7EA"
UI_SOFT = "#F3F4F6"
UI_TXT = "#15161A"
UI_SUB = "#8A8D96"
LIME = "#B8F230"
GREEN = "#1FD12E"
PURPLE = "#9B7BFF"
BLUE = "#2F7BFF"
SKY = "#D8ECFF"
RED = "#FF4D3D"


def col(c, a=1.0):
    r, g, b = kit.rgb(c)
    return skia.Color(r, g, b, int(255 * clamp(a)))


# ================================================================== grade: moody room relight
def _luts():
    x = np.arange(256, dtype=np.float32) / 255
    s = np.clip(x + 0.07 * np.sin(2 * math.pi * (x - 0.5)), 0, 1)
    person = [0.03 + 0.86 * s ** 1.08, 0.035 + 0.83 * s ** 1.1, 0.04 + 0.78 * s ** 1.12]
    return np.ascontiguousarray(np.stack([(np.clip(c, 0, 1) * 255).astype(np.uint8) for c in person], 1)
                                .reshape(256, 1, 3))


PLUT = _luts()
ROOM = np.array([0.30, 0.355, 0.37], np.float32)      # cream wall (~228) -> ~ (68, 81, 84) teal-grey
_LIGHT = None


def room_light():
    """soft window light from the upper left on the wall, falling off to the floor."""
    global _LIGHT
    if _LIGHT is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - 200) / 900) ** 2 + ((yy - 350) / 1100) ** 2)
        _LIGHT = (1.2 - 0.45 * np.clip(r, 0, 1.4)).astype(np.float32)
    return _LIGHT


def kit_img(rgb, a=None):
    out = cv2.cvtColor(rgb, cv2.COLOR_RGB2RGBA)
    if a is not None:
        out[..., 3] = a
    return skia.Image.fromarray(out, colorType=skia.kRGBA_8888_ColorType)


class Src:
    """one source frame relit: person warm, room dark teal-grey."""
    _cache = {}

    def __new__(cls, ts):
        fi = int(clamp(round(ts * FPS), 0, E.NSRC - 1))
        if fi in cls._cache:
            return cls._cache[fi]
        o = super().__new__(cls)
        if len(cls._cache) > 14:
            cls._cache.pop(next(iter(cls._cache)))
        cls._cache[fi] = o
        o.fi, o.ts, o._m = fi, ts, {}
        return o

    def _memo(self, k, fn):
        if k not in self._m:
            self._m[k] = fn()
        return self._m[k]

    def graded(self):
        def make():
            raw = E.frame_rgb(self.fi)
            p = cv2.LUT(raw, PLUT)
            gray = cv2.cvtColor(cv2.cvtColor(p, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB)
            p = cv2.addWeighted(p, 0.88, gray, 0.12, 0)
            a = cv2.resize(E.alpha_small(self.fi), (W, H)).astype(np.float32) / 255
            a = a * a * (3 - 2 * a)                                  # firmer edge: no bright halo
            m = (1 - a) * room_light()
            fac = cv2.merge([a + m * ROOM[ch] for ch in range(3)])
            return cv2.multiply(p, fac, dtype=cv2.CV_8U), (a * 255).astype(np.uint8), p
        return self._memo("g", make)

    def img(self):
        return self._memo("img", lambda: kit_img(self.graded()[0]))

    def person(self):
        return self._memo("person", lambda: kit_img(self.graded()[2], self.graded()[1]))

    def raw(self):
        return self._memo("raw", lambda: kit_img(E.frame_rgb(self.fi)))


# ================================================================== timing
def at(p):
    """the cut point that opens phrase p (or just before it, when p starts mid-run)."""
    rs = E.run_start(p)
    return rs if p.s - rs < 0.3 else p.s - 0.05


P = E.P
H_THIS, H_WENT, H_SIX = E.H_THIS, E.H_WENT, E.H_SIX
I_HERE, I_STEP = E.I_HERE, E.I_STEP
S1, DROP, ONE, MIST = E.S1, E.DROP, E.ONE, E.MIST
S2, WATCH, TRANS, FINDS, MOVES, FIRST = E.S2, E.WATCH, E.TRANS, E.FINDS, E.MOVES, E.FIRST
S3, STORY, PUR, GONE, EXACT = E.S3, E.STORY, E.PUR, E.GONE, E.EXACT
S4, LOOK, CAPS, BEHIND, SWAP, ZOOMS = E.S4, E.LOOK, E.CAPS, E.BEHIND, E.SWAP, E.ZOOMS
S5, SOUND, MUSIC, WHOOSH, HITS, SCRATCH, CLAIMS = E.S5, E.SOUND, E.MUSIC, E.WHOOSH, E.HITS, E.SCRATCH, E.CLAIMS
S6, PART, PROOF, STILLS, SAY, EXPORT, REELS, FEEDS = E.S6, E.PART, E.PROOF, E.STILLS, E.SAY, E.EXPORT, E.REELS, \
    E.FEEDS
VE, TASTE, KEYF, SOIF, REC = E.VE, E.TASTE, E.KEYF, E.SOIF, E.REC
END_A = REC.e + 0.3

SPLITS = [("landing", at(I_STEP), at(S1)), ("upload", DROP.s - 0.05, at(S2)), ("analyze", at(WATCH), at(FIRST)),
          ("card2s", at(FIRST), at(S3)), ("timeline", PUR.s - 0.05, at(S4)), ("look", at(CAPS), at(ZOOMS)),
          ("sound", at(MUSIC), at(CLAIMS)), ("claims", at(CLAIMS), at(S6)), ("stills", at(STILLS), at(SAY)),
          ("prompt", at(SAY), at(EXPORT)), ("export", at(EXPORT), at(VE))]


def split_now(t):
    for name, a, b in SPLITS:
        if a <= t < b:
            return name, a, b
    return None


GLITCHES = sorted({a for _, a, _ in SPLITS} | {b for _, _, b in SPLITS} | {at(I_HERE), at(SOIF), END_A})


# ================================================================== framing
BASE_Z, BASE_DY = 1.12, 95          # tighter medium close-up: head top at ~36 % like the reference
SPLIT_DY = 360                      # in split screen the speaker sits in the lower half
SHAKES = []


def cam(t, ts, split=False):
    fx, fy = E.face(ts)
    k = max([i for i, s in enumerate(E.RUN_STARTS) if s <= t + 1e-6] or [0])
    z = BASE_Z * (1.0, 1.05, 1.02, 1.07)[k % 4] * (1 + 0.008 * (t - E.RUN_STARTS[k]))
    if t < 0.3:
        z *= lerp(1.2, 1.0, e_out(t / 0.3))
    if ZOOMS.s - 0.03 <= t < at(S5):
        z *= lerp(1.0, 1.3, e_out(prog(t, ZOOMS.s - 0.03, 0.22)))
        if t >= ZOOMS.w(3):
            z *= lerp(1.0, 1.08, e_io(prog(t, ZOOMS.w(3), 0.5)))
    dy = BASE_DY + (SPLIT_DY if split else 0)
    dx = 0.0
    for st, amp in SHAKES:
        if st <= t < st + 0.25:
            kk = 1 - (t - st) / 0.25
            dx += amp * kk * math.sin(t * 95)
            dy += amp * kk * math.sin(t * 81 + 1)
    return z, fx, fy, dx, dy


def apply(c, cm):
    z, fx, fy, dx, dy = cm
    c.translate(fx + dx, fy + dy)
    c.scale(z, z)
    c.translate(-fx, -fy)


def head_top(t, ts, split=False):
    z, fx, fy, dx, dy = cam(t, ts, split)
    top = E.TRACK[int(clamp(round(ts * FPS), 0, len(E.TRACK) - 1)), 0]
    return fy + dy + z * (top - fy)


# ================================================================== type
def txt(c, s, x, y, name, size, color=WHITE, a=1.0, anchor="l", paint=None):
    return kit.text(c, s, x, y, name, size, color=color, a=a, anchor=anchor, paint=paint)


def hand(c, s, x, y, size, k=1.0, color=WHITE, anchor="c", a=1.0):
    """small hand-lettered caps line, written on left to right by k."""
    if k <= 0:
        return
    w = measure(s, "hand", size)
    x0 = x - w / 2 if anchor == "c" else x - w if anchor == "r" else x
    c.save()
    c.clipRect(skia.Rect.MakeLTRB(x0 - 20, y - size * 2, x0 + (w + 40) * e_out(k), y + size))
    kit.text(c, s, x0 + 2, y + 3, "hand", size, color="#000000", a=0.35 * a, anchor="l",
             paint=fill("#000000", 0.35 * a, blur=4))
    kit.text(c, s, x0, y, "hand", size, color=color, a=a, anchor="l")
    c.restore()


def fit(s, maxw=960, size=150):
    """font size for the big word so it fits maxw, and its cap height."""
    w = measure(s, "wide", size)
    if w > maxw:
        size *= maxw / w
    return size, font("wide", size).getMetrics().fCapHeight


def big_type(c, s, x, y, t, t0, maxw=960, size=150, anchor="c", color=YEL, stagger=0.045, a=1.0, t_out=None):
    """huge wide italic word, typed on letter by letter; each letter flies in big and settles."""
    if t < t0 or a <= 0:
        return 0
    w = measure(s, "wide", size)
    if w > maxw:
        size *= maxw / w
        w = measure(s, "wide", size)
    f = font("wide", size)
    x0 = x - w / 2 if anchor == "c" else x
    xx = x0
    for i, ch in enumerate(s):
        cw = f.measureText(ch)
        k = clamp((t - t0 - i * stagger) / 0.2)
        if k > 0:
            sp = e_out(k)
            sc = lerp(1.7, 1.0, sp)
            dx = lerp(size * 0.35, 0, sp)
            dy = lerp(size * 0.2, 0, sp)
            aa = a * clamp(k * 4)
            if t_out is not None and t > t_out:
                ko = clamp((t - t_out - i * 0.015) / 0.12)
                aa *= 1 - ko
                dy -= ko * size * 0.3
            c.save()
            c.translate(xx + cw / 2 + dx, y + dy)
            c.scale(sc, sc)
            c.drawString(ch, -cw / 2 + 3, 5, f, fill("#000000", 0.35 * aa, blur=6))
            c.drawString(ch, -cw / 2, 0, f, fill(color, aa))
            c.restore()
        xx += cw
    return w


def scribble(c, x0, x1, y, k, color=INK, width=7, seed=1):
    """loose hand-drawn loop underline (the reference's black scribble)."""
    if k <= 0:
        return
    pts = []
    n = 60
    for i in range(n + 1):
        u = i / n
        xx = lerp(x0, x1, u)
        yy = y + 10 * math.sin(u * 7 + seed) + (hrand(seed, i) - 0.5) * 3
        if 0.35 < u < 0.5:
            th = (u - 0.35) / 0.15 * 2 * math.pi
            xx += 26 * math.sin(th)
            yy -= 22 * (1 - math.cos(th)) / 2
        pts.append((xx, yy))
    path = skia.Path()
    path.moveTo(*pts[0])
    for p in pts[1:]:
        path.lineTo(*p)
    p = stroke(color, width)
    if k < 1:
        p.setPathEffect(skia.TrimPathEffect.Make(0, clamp(k)))
    c.drawPath(path, p)


def bubble_doodle(c, x, y, s, k, color=INK):
    if k <= 0:
        return
    path = skia.Path()
    path.addOval(skia.Rect.MakeXYWH(x - s, y - s * 0.8, 2 * s, 1.6 * s))
    path.moveTo(x - s * 0.45, y + s * 0.65)
    path.lineTo(x - s * 0.75, y + s * 1.15)
    path.lineTo(x - s * 0.05, y + s * 0.78)
    p = stroke(color, 8)
    if k < 1:
        p.setPathEffect(skia.TrimPathEffect.Make(0, clamp(k)))
    c.drawPath(path, p)


def arrow_doodle(c, pts, k, color=WHITE, width=7):
    if k <= 0:
        return
    path = skia.Path()
    path.moveTo(*pts[0])
    for i in range(1, len(pts) - 1):
        mx, my = (pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2
        path.quadTo(pts[i][0], pts[i][1], mx, my)
    path.lineTo(*pts[-1])
    p = stroke(color, width)
    if k < 0.8:
        p.setPathEffect(skia.TrimPathEffect.Make(0, clamp(k / 0.8)))
    c.drawPath(path, p)
    if k > 0.8:
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        ang = math.atan2(y1 - y0, x1 - x0)
        hk = e_out((k - 0.8) / 0.2) * 40
        for sg in (-1, 1):
            a2 = ang + math.pi + sg * 0.55
            c.drawLine(x1, y1, x1 + hk * math.cos(a2), y1 + hk * math.sin(a2), stroke(color, width))


# ================================================================== titles (full frame)
TITLE_Y = 634          # big word baseline (reference: 30-33 % of the frame)
TITLES = [
    # small line, big word, t small, t big, t end
    ("THIS EXACT VIDEO", "6 STEPS", H_THIS.s - 0.05, H_SIX.s - 0.06, at(I_HERE)),
    ("WHAT HAPPENS INSIDE A", "VIBE EDIT", I_HERE.s - 0.03, I_HERE.w(7) - 0.06, at(I_STEP)),
    ("STEP ONE", "RAW", S1.s - 0.03, S1.w(1) - 0.04, DROP.s - 0.05),
    ("STEP TWO", "LISTEN", S2.s - 0.03, S2.w(1) - 0.04, at(WATCH)),
    ("STEP THREE", "STORY CUT", S3.s - 0.03, STORY.w(1) - 0.05, PUR.s - 0.05),
    ("STEP FOUR", "THE LOOK", S4.s - 0.03, LOOK.s - 0.05, at(CAPS)),
    ("ZOOMS ON THE LINES", "THAT MATTER", ZOOMS.s - 0.03, ZOOMS.w(3) - 0.05, at(S5)),
    ("STEP FIVE", "SOUND", S5.s - 0.03, SOUND.s - 0.05, at(MUSIC)),
    ("STEP SIX", "", S6.s - 0.03, 1e9, PART.s - 0.03),
    ("WHAT EDITORS NEVER GIVE YOU", "PROOF", PART.s - 0.03, PROOF.w(2) - 0.05, at(STILLS)),
    ("THAT'S", "VIBE EDITING", VE.s - 0.03, VE.w(2) - 0.05, TASTE.s - 0.03),
    ("YOU BRING THE", "TASTE", TASTE.s - 0.03, TASTE.w(3) - 0.05, KEYF.s - 0.03),
    ("THE SYSTEM DOES THE", "KEYFRAMES", KEYF.s - 0.03, KEYF.w(4) - 0.05, at(SOIF)),
]


def draw_titles(c, t, ht):
    for small, big, ts_, tb, te in TITLES:
        if not ts_ <= t < te:
            continue
        # keep the big word clear of the head when a punch-in lifts it
        y = min(TITLE_Y, ht - 40)
        cap = fit(big)[1] if big else 0
        hand(c, small, 540, y - cap - 36, 40, prog(t, ts_, 0.3))
        w = big_type(c, big, 540, y, t, tb) if big else 0
        if small.startswith("THIS EXACT"):
            scribble(c, 540 - w / 2 + 60, 540 + w / 2 - 40, y + 46, prog(t, tb + 0.3, 0.45), INK, 7, 3)
    # hook: floating UI pieces above the title, as in the reference
    if H_WENT.s - 0.05 <= t < at(I_HERE):
        ui_float(c, t, H_WENT.s - 0.05)


def ui_float(c, t, t0):
    items = [(150, 290, "toggle"), (300, 280, "dots"), (470, 290, "pill"), (690, 290, "lime"), (880, 290, "purple"),
             (150, 385, "slider"), (420, 385, "wave"), (700, 395, "chip")]
    for j, (x, y, kind) in enumerate(items):
        k = prog(t, t0 + j * 0.06, 0.3)
        if k <= 0:
            continue
        s = e_back(k)
        c.save()
        c.translate(x, y + 6 * math.sin(t * 2 + j))
        c.scale(s, s)
        if kind == "toggle":
            c.drawRRect(kit.rrect(-50, -26, 100, 52, 26), fill(GREEN))
            c.drawCircle(22, 0, 20, fill(WHITE))
        elif kind == "dots":
            for q, cc in enumerate((BLUE, LIME, PURPLE)):
                c.drawCircle(-40 + q * 40, 0, 16, fill(cc))
        elif kind == "pill":
            c.drawRRect(kit.rrect(-95, -26, 190, 52, 26), fill(INK))
            txt(c, "Auto-edit", 0, 9, "bold", 24, WHITE, anchor="c")
        elif kind == "lime":
            c.drawRRect(kit.rrect(-90, -55, 180, 110, 16), fill(LIME))
            txt(c, "6 steps", -70, -20, "bold", 22, INK)
            c.drawCircle(60, 32, 14, fill(INK))
        elif kind == "purple":
            c.drawRRect(kit.rrect(-80, -55, 160, 110, 16), fill("#C9B8FF"))
            for q in range(3):
                c.drawRRect(kit.rrect(-60, -35 + q * 26, 90 - q * 20, 12, 6), fill(WHITE, 0.8))
        elif kind == "slider":
            c.drawRRect(kit.rrect(-90, -4, 180, 8, 4), fill(WHITE, 0.6))
            c.drawRRect(kit.rrect(-90, -4, 120, 8, 4), fill(WHITE))
            c.drawCircle(30, 0, 14, fill(WHITE))
        elif kind == "wave":
            for q in range(14):
                hh = 12 + 26 * abs(math.sin(q * 1.3 + t * 6))
                c.drawRRect(kit.rrect(-100 + q * 15, -hh / 2, 8, hh, 4), fill(WHITE))
        elif kind == "chip":
            c.drawRRect(kit.rrect(-90, -26, 180, 52, 12), fill("#2B2E33"))
            txt(c, "cut  0:02", 0, 9, "monob", 22, WHITE, anchor="c")
        c.restore()


# ================================================================== subtitles
def _groups():
    used = sorted([w for w in E.WORDS if w["os"] is not None], key=lambda w: w["os"])
    groups, cur = [], []
    for w in used:
        if cur and (len(cur) >= 3 or sum(len(x["d"]) + 1 for x in cur) + len(w["d"]) > 18
                    or w["os"] - cur[-1]["oe"] > 0.3 or cur[-1]["d"][-1] in ".,?"):
            groups.append(cur)
            cur = []
        cur.append(w)
    groups.append(cur)
    return groups


SUBS = _groups()


def draw_subs(c, t, split):
    g = None
    for k, grp in enumerate(SUBS):
        nxt = SUBS[k + 1][0]["os"] if k + 1 < len(SUBS) else grp[-1]["oe"] + 0.5
        if grp[0]["os"] - 0.04 <= t < min(nxt - 0.02, grp[-1]["oe"] + 0.5):
            g = grp
    if not g:
        return
    s = " ".join(w["d"] for w in g)
    if g[0]["k"] == "this" and g[0]["os"] < 0.1:
        s = s[0].upper() + s[1:]
    if split:
        size = 40
        w = measure(s, "medium", size)
        y = 958
        c.drawRect(skia.Rect.MakeXYWH(540 - w / 2 - 10, y - 44, w + 20, 54), fill("#000000"))
        txt(c, s, 540, y - 4, "medium", size, WHITE, anchor="c")
    else:
        size = 46
        txt(c, s, 540, 1404, "medium", size, "#000000", anchor="c", paint=fill("#000000", 0.55, blur=8))
        txt(c, s, 540, 1400, "medium", size, WHITE, anchor="c")


# ================================================================== UI kit (B-roll panel, 1080 x 960)
PANEL = 960


def cursor(c, x, y, click_k=0.0, s=1.0):
    if click_k > 0:
        r = 18 + 50 * e_out(click_k)
        c.drawCircle(x, y, r, fill(BLUE, 0.25 * (1 - click_k)))
    p = skia.Path()
    pts = [(0, 0), (0, 46), (12, 35), (21, 55), (29, 51), (20, 32), (36, 32)]
    p.moveTo(x + pts[0][0] * s, y + pts[0][1] * s)
    for px, py in pts[1:]:
        p.lineTo(x + px * s, y + py * s)
    p.close()
    c.drawPath(p, fill("#000000", 0.25, blur=4))
    c.drawPath(p, fill(INK))
    c.drawPath(p, stroke(WHITE, 3))


def card(c, x, y, w, h, bg=WHITE, r=22, border=UI_LINE, shadow=0.08, bw=2):
    rr = kit.rrect(x, y, w, h, r)
    if shadow:
        c.drawRRect(rr.makeOffset(0, 6), fill("#000000", shadow, blur=14))
    c.drawRRect(rr, fill(bg))
    if border:
        c.drawRRect(rr, stroke(border, bw))
    return rr


def green_box(c, x, y, w, h, k, width=10):
    """the reference's bright green highlight rectangle."""
    if k <= 0:
        return
    c.drawRRect(kit.rrect(x, y, w, h, 8), stroke(GREEN, width * e_out(k), clamp(k * 3)))


def check(c, x, y, s, k, color=GREEN):
    if k <= 0:
        return
    p = skia.Path()
    p.moveTo(x - 0.5 * s, y)
    p.lineTo(x - 0.12 * s, y + 0.38 * s)
    p.lineTo(x + 0.55 * s, y - 0.45 * s)
    st = stroke(color, s * 0.18)
    if k < 1:
        st.setPathEffect(skia.TrimPathEffect.Make(0, clamp(k)))
    c.drawPath(p, st)


def nav(c, title="vibe editing system"):
    c.drawRRect(kit.rrect(50, 40, 44, 44, 12), fill(INK))
    txt(c, "v", 72, 72, "black", 32, LIME, anchor="c")
    txt(c, title, 110, 72, "bold", 28, UI_TXT)
    for j, s in enumerate(("Steps", "Pricing", "Docs")):
        txt(c, s, 560 + j * 120, 72, "medium", 24, UI_SUB)
    c.drawRRect(kit.rrect(890, 40, 140, 46, 23), fill(INK))
    txt(c, "Open app", 960, 71, "bold", 22, WHITE, anchor="c")


def wave(c, x, y, w, h, n, seed, color, a=1.0, k=1.0, bars=True):
    for q in range(int(n * clamp(k))):
        lv = abs(math.sin(q * 0.7 + seed)) * (0.5 + 0.5 * abs(math.sin(q * 0.23 + seed * 3)))
        hh = max(4, h * lv)
        c.drawRRect(kit.rrect(x + q * w / n, y - hh / 2, w / n * 0.6, hh, 3), fill(color, a))


def thumb_rect(ts, aspect=1.0, zoom=1.0):
    """source crop rect around the face for a thumbnail of the given aspect (w/h)."""
    fx, fy = E.face(ts)
    h = 1000 / zoom
    w = min(W, h * aspect)
    h = w / aspect
    return skia.Rect.MakeXYWH(clamp(fx - w / 2, 0, W - w), clamp(fy - h * 0.42, 0, H - h), w, h)


def img_card(c, img, x, y, w, h, sr, r=16, a=1.0):
    rr = kit.rrect(x, y, w, h, r)
    c.save()
    c.clipRRect(rr, skia.ClipOp.kIntersect, True)
    c.drawImageRect(img, sr, skia.Rect.MakeXYWH(x, y, w, h), SAMP, skia.Paint(Alphaf=a))
    c.restore()


# ---------------------------------------------------------------- the scenes
def sc_landing(c, t, a, b):
    nav(c)
    k = prog(t, a, 0.3)
    pill_w = measure("New  ·  one-take editing", "medium", 22) + 40
    c.drawRRect(kit.rrect(540 - pill_w / 2, 170, pill_w, 44, 22), fill("#EFE9FF"))
    txt(c, "New  ·  one-take editing", 540, 200, "medium", 22, "#6B4DFF", anchor="c")
    txt(c, "Edit videos by", 540, 320, "heavy", 86, UI_TXT, anchor="c")
    txt(c, "talking to them.", 540, 420, "heavy", 86, UI_TXT, anchor="c")
    c.drawRRect(kit.rrect(400, 470, 280, 64, 32), fill(PURPLE))
    txt(c, "Drop your take", 540, 511, "bold", 26, WHITE, anchor="c")
    names = ["Raw in", "Listen", "Story cut", "The look", "Sound", "Proof"]
    for j, nm in enumerate(names):
        kj = prog(t, I_STEP.s + j * 0.11, 0.25)
        if kj <= 0:
            continue
        x = 70 + (j % 3) * 320
        y = 600 + (j // 3) * 120
        c.save()
        c.translate(x + 145, y + 45)
        s = e_back(kj)
        c.scale(s, s)
        c.translate(-x - 145, -y - 45)
        card(c, x, y, 290, 90, WHITE, 18)
        c.drawCircle(x + 45, y + 45, 24, fill([LIME, SKY, "#FFE1DC", "#EFE9FF", YEL, "#DFF7E2"][j]))
        txt(c, str(j + 1), x + 45, y + 55, "black", 26, UI_TXT, anchor="c")
        txt(c, nm, x + 85, y + 55, "bold", 28, UI_TXT)
        c.restore()


def sc_upload(c, t, a, b):
    nav(c)
    txt(c, "New edit", 70, 175, "heavy", 48, UI_TXT)
    dz = kit.rrect(70, 215, 940, 400, 28)
    kd = prog(t, DROP.w(1) + 0.25, 0.2)
    c.drawRRect(dz, fill("#F6FFF0" if kd > 0 else UI_SOFT))
    p = skia.Path()
    p.addRRect(dz)
    st = stroke(GREEN if kd > 0 else "#C5C8CF", 4)
    st.setPathEffect(skia.DashPathEffect.Make([18, 12], 0))
    c.drawPath(p, st)
    # upload arrow + label
    if kd <= 0:
        c.drawLine(540, 340, 540, 420, stroke(UI_SUB, 8))
        c.drawLine(510, 370, 540, 340, stroke(UI_SUB, 8))
        c.drawLine(570, 370, 540, 340, stroke(UI_SUB, 8))
        txt(c, "Drop your raw take here", 540, 480, "bold", 32, UI_SUB, anchor="c")
    # the file card, dragged by the cursor
    kf = e_io(prog(t, a + 0.1, DROP.w(1) + 0.25 - a - 0.1))
    fx, fy = lerp(140, 380, kf), lerp(820, 300, kf)
    src = Src(E.src_at(t))
    card(c, fx, fy, 320, 120, WHITE, 16, shadow=0.18)
    img_card(c, src.raw(), fx + 14, fy + 14, 70, 92, thumb_rect(src.ts, 70 / 92), 10)
    txt(c, "take_01.mov", fx + 100, fy + 52, "bold", 28, UI_TXT)
    txt(c, "1:20  ·  1 take", fx + 100, fy + 88, "medium", 22, UI_SUB)
    if kd <= 0:
        cursor(c, fx + 250, fy + 70)
    else:
        bar = clamp((t - DROP.w(1) - 0.3) / 1.0)
        c.drawRRect(kit.rrect(380, 460, 560, 14, 7), fill(UI_LINE))
        c.drawRRect(kit.rrect(380, 460, 560 * e_io(bar), 14, 7), fill(GREEN))
        txt(c, "Uploaded" if bar >= 1 else f"Uploading… {int(100 * e_io(bar))}%", 380, 520, "bold", 26, UI_TXT)
        check(c, 920, 510, 40, prog(t, DROP.w(1) + 1.3, 0.25))
    # one take + mistakes
    if t >= ONE.w(1) - 0.05:
        kk = e_back(prog(t, ONE.w(1) - 0.05, 0.3))
        c.drawRRect(kit.rrect(70, 650, 200 * kk, 64, 32), fill(LIME))
        if kk > 0.6:
            txt(c, "1 take", 170, 692, "bold", 28, INK, anchor="c")
    if t >= MIST.s - 0.05:
        km = prog(t, MIST.s - 0.05, 0.25)
        card(c, 300, 640, 710, 90, WHITE, 18)
        txt(c, "Mistakes, ums, retakes", 330, 696, "bold", 28, UI_TXT)
        on = prog(t, MIST.w(2) - 0.05, 0.2)
        c.drawRRect(kit.rrect(880, 662, 100, 48, 24), fill(GREEN if on > 0.5 else "#D3D6DC"))
        c.drawCircle(lerp(905, 955, e_out(on)), 686, 19, fill(WHITE))
        txt(c, "keep: system fixes them", 330, 780, "medium", 24, UI_SUB, a=km)


TRANSCRIPT = ["Here is what actually happens inside a vibe edit.", "Step by step. Step one, you drop in your raw",
              "footage. One take, mistakes and all. Step two…", "This exact video went through all six steps."]


def sc_analyze(c, t, a, b):
    nav(c)
    src = Src(E.src_at(t))
    if t < TRANS.s - 0.05:
        txt(c, "Analyzing your take", 70, 175, "heavy", 48, UI_TXT)
        card(c, 70, 220, 440, 560, INK, 22, border=None)
        img_card(c, src.img(), 70, 220, 440, 560, thumb_rect(src.ts, 440 / 560, 0.9), 22)
        c.drawRRect(kit.rrect(90, 240, 190, 44, 22), fill("#000000", 0.6))
        c.drawCircle(115, 262, 8, fill(RED if int(t * 3) % 2 else "#FF9A8F"))
        txt(c, "watching", 132, 271, "bold", 22, WHITE)
        card(c, 540, 220, 470, 560, WHITE, 22)
        txt(c, "Listening", 570, 275, "bold", 30, UI_TXT)
        n = 40
        for q in range(n):
            lv = E.VOICE_ENV(src.ts + (q - n) * 0.04)
            hh = max(6, 300 * lv)
            c.drawRRect(kit.rrect(570 + q * 10.5, 500 - hh / 2, 6, hh, 3), fill(BLUE if q > n - 3 else "#AFC8FF"))
        check(c, 960, 265, 34, prog(t, WATCH.w(4), 0.3))
        txt(c, "voice · 0 noise", 570, 740, "medium", 24, UI_SUB)
        return
    txt(c, "Transcript", 70, 175, "heavy", 48, UI_TXT)
    nw = sum(1 for w in E.WORDS if w["os"] is not None)
    cnt = int(nw * clamp((t - TRANS.s) / max(0.3, TRANS.e - TRANS.s)))
    txt(c, f"{cnt} words", 1010, 175, "bold", 26, UI_SUB, anchor="r")
    card(c, 70, 215, 940, 400, WHITE, 22)
    total = sum(len(s) for s in TRANSCRIPT)
    nch = int(total * clamp((t - TRANS.s) / max(0.3, TRANS.e - TRANS.s + 0.2)))
    km = e_io(prog(t, MOVES.w(2), 0.5))
    for j, ln in enumerate(TRANSCRIPT):
        shown = ln[:max(0, nch - sum(len(s) for s in TRANSCRIPT[:j]))]
        row = (j + km) if j < 3 else 3 - 3 * km
        y = 290 + row * 84
        txt(c, shown, 100, y, "medium", 31, UI_TXT if j == 3 or t < FINDS.w(2) else UI_SUB)
        if j == 3 and t >= FINDS.w(2) - 0.05:
            green_box(c, 84, y - 46, measure(ln, "medium", 31) + 34, 66, prog(t, FINDS.w(2) - 0.05, 0.2))
    if FINDS.s - 0.3 <= t < MOVES.w(2):
        k = e_io(prog(t, FINDS.s - 0.3, 0.6))
        cursor(c, lerp(800, 600, k), lerp(760, 560, k), prog(t, FINDS.w(2) - 0.05, 0.3))
    if t >= FINDS.w(2):
        c.drawRRect(kit.rrect(760, 228, 230, 44, 22), fill(GREEN, prog(t, FINDS.w(2), 0.2)))
        txt(c, "strongest line", 875, 258, "bold", 22, WHITE, anchor="c", a=prog(t, FINDS.w(2), 0.2))
    # mini timeline: the line becomes the opening clip
    if t >= MOVES.s - 0.05:
        kt = prog(t, MOVES.s - 0.05, 0.3)
        card(c, 70, 650, 940, 150, UI_SOFT, 18, border=None, shadow=0)
        txt(c, "0:00", 90, 690, "monob", 20, UI_SUB)
        for q in range(6):
            c.drawRRect(kit.rrect(170 + q * 140, 705, 128, 70, 10), fill("#C9D6E8", kt))
        kh = e_io(prog(t, MOVES.w(2), 0.55))
        hx = lerp(870, 170, kh)
        c.drawRRect(kit.rrect(hx - 4 * (1 - kh), 700, 136, 80, 12), fill(GREEN, kt))
        txt(c, "HOOK", hx + 68, 750, "black", 24, WHITE, anchor="c", a=kt)


def big_card(c, t, words, ts_list):
    """a giant black word on a yellow gradient card, sliding (the reference's 'Smooth' card)."""
    x, y, w, h = 40, 150, 1000, 640
    rr = kit.rrect(x, y, w, h, 34)
    p = skia.Paint(Shader=skia.GradientShader.MakeLinear([skia.Point(x, y), skia.Point(x, y + h)],
                                                         [col(YEL), col("#FFFBD2")]), AntiAlias=True)
    c.drawRRect(rr, p)
    cur = 0
    for j, tj in enumerate(ts_list):
        if t >= tj:
            cur = j
    s = words[cur]
    t0 = ts_list[cur]
    c.save()
    c.clipRRect(rr, skia.ClipOp.kIntersect, True)
    size = 330
    tw = measure(s, "anton", size)
    k = prog(t, t0, 0.35)
    xx = lerp(x + w + 40, x + 70, e_out(k)) - (t - t0) * 60
    kit.text(c, s, xx, y + h / 2 + 125, "anton", size, color=INK, anchor="l")
    c.restore()


def sc_card2s(c, t, a, b):
    big_card(c, t, ["2 SECONDS", "EVERYTHING."], [a, FIRST.w(6) - 0.05])


def sc_claims(c, t, a, b):
    big_card(c, t, ["NO COPYRIGHT", "0 CLAIMS."], [a, CLAIMS.w(4) - 0.05])


BLOCKS = [("clip", 1.2), ("PAUSE", 0.55), ("clip", 0.9), ("UM", 0.4), ("clip", 1.3), ("RETAKE", 0.8), ("clip", 0.7),
          ("PAUSE", 0.5), ("clip", 1.0)]


def sc_timeline(c, t, a, b):
    nav(c)
    txt(c, "Story cut", 70, 175, "heavy", 48, UI_TXT)
    src = Src(E.src_at(t))
    img_card(c, src.img(), 340, 205, 400, 300, thumb_rect(src.ts, 4 / 3, 0.9), 18)
    card(c, 50, 540, 980, 360, "#16181C", 22, border=None)
    if t < EXACT.s - 0.05:
        kg = e_io(prog(t, GONE.s, 0.4))
        tot0 = sum(d for _, d in BLOCKS)
        tot1 = sum(d for n, d in BLOCKS if n == "clip")
        x = 80
        tw = 920
        for j, (nm, d) in enumerate(BLOCKS):
            bad = nm != "clip"
            dd = d * (1 - kg) if bad else d
            bw = tw * dd / lerp(tot0, tot1, kg)
            if bw > 1:
                if bad:
                    hot = t >= PUR.w({"PAUSE": 0, "UM": 1, "RETAKE": 2}[nm]) - 0.05
                    c.drawRRect(kit.rrect(x + 2, 600, bw - 4, 120, 10), fill(RED, 0.5 + 0.5 * hot))
                    if bw > 70:
                        txt(c, nm, x + bw / 2, 670, "black", 20, WHITE, anchor="c", a=1 - kg)
                    if hot and kg <= 0:
                        c.drawRRect(kit.rrect(x, 596, bw, 128, 12), stroke(GREEN, 6))
                else:
                    c.drawRRect(kit.rrect(x + 2, 600, bw - 4, 120, 10), fill("#3D7BFF"))
                    wave(c, x + 10, 660, bw - 20, 70, int(bw / 12), j * 1.7, "#BFD3FF")
                c.drawRRect(kit.rrect(x + 2, 745, bw - 4, 60, 8), fill("#2A2D33"))
            x += bw
        if kg > 0:
            txt(c, f"−{2.25 * kg:.1f}s dead air", 1000, 860, "bold", 26, GREEN, anchor="r")
        c.drawRect(skia.Rect.MakeXYWH(80 + 920 * clamp((t - a) / (b - a)), 585, 4, 230), fill(WHITE))
        if PUR.e - 0.2 <= t < GONE.s + 0.4:
            cursor(c, 700, 790, prog(t, GONE.s - 0.05, 0.3))
            c.drawRRect(kit.rrect(80, 830, 120, 52, 12), fill(WHITE, prog(t, GONE.s - 0.1, 0.15)))
            txt(c, "delete", 140, 865, "bold", 22, INK, anchor="c", a=prog(t, GONE.s - 0.1, 0.15))
    else:
        words = ["down", "to", "the", "exact", "word"]
        x = 90
        for j, wd in enumerate(words):
            kj = prog(t, EXACT.w(j) - 0.04, 0.2)
            ww = measure(wd, "bold", 34) + 50
            c.drawRRect(kit.rrect(x, 600, ww, 80, 14), fill("#3D7BFF" if kj > 0 else "#2A2D33"))
            txt(c, wd, x + ww / 2, 652, "bold", 34, WHITE, anchor="c")
            wave(c, x, 760, ww, 70, int(ww / 10), j * 2.1, "#BFD3FF")
            if j == 3:
                cut_x = x - 11
            x += ww + 22
        kc = e_back(prog(t, EXACT.w(3) - 0.05, 0.3))
        if kc > 0:
            c.drawRect(skia.Rect.MakeXYWH(cut_x - 3, 580, 6, 290 * kc), fill(GREEN))
            c.drawCircle(cut_x, 580, 12 * kc, fill(GREEN))
            txt(c, "cut point · frame accurate", 90, 870, "bold", 24, GREEN, a=clamp(kc))


PRESETS = [("Aa", "wide", YEL), ("Aa", "medium", WHITE), ("Aa", "black", WHITE), ("Aa", "hand", WHITE),
           ("Aa", "anton", LIME), ("Aa", "italic", WHITE)]


def preview_tile(c, t, x, y, w, h, bgc, text_behind=None, k_text=1.0):
    """live mini preview: background colour, optional word behind the person, the cut-out person."""
    src = Src(E.src_at(t))
    sr = thumb_rect(src.ts, w / h, 0.85)
    rr = kit.rrect(x, y, w, h, 20)
    c.save()
    c.clipRRect(rr, skia.ClipOp.kIntersect, True)
    if bgc is None:
        c.drawImageRect(src.img(), sr, skia.Rect.MakeXYWH(x, y, w, h), SAMP)
    else:
        c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), fill(bgc))
    if text_behind and k_text > 0:
        size = w * 0.36
        kit.text(c, text_behind, x + w / 2, y + h * 0.36, "wide", size * 0.6, color=YEL, a=k_text)
    c.drawImageRect(src.person(), sr, skia.Rect.MakeXYWH(x, y, w, h), SAMP)
    c.restore()
    c.drawRRect(rr, stroke(UI_LINE, 2))


def sc_look(c, t, a, b):
    nav(c)
    if t < BEHIND.s - 0.05:
        txt(c, "Caption style", 70, 175, "heavy", 48, UI_TXT)
        pick = 0
        for j, (s, fn, cc) in enumerate(PRESETS):
            x = 70 + (j % 3) * 320
            y = 220 + (j // 3) * 280
            kj = prog(t, a + j * 0.06, 0.25)
            c.save()
            c.translate(x + 145, y + 125)
            c.scale(e_back(kj), e_back(kj))
            c.translate(-x - 145, -y - 125)
            card(c, x, y, 290, 250, "#1A1C20", 20, border=None)
            txt(c, s, x + 145, y + 150, fn, 90 if fn != "hand" else 64, cc, anchor="c")
            c.restore()
            if j == pick and t >= CAPS.w(2) - 0.05:
                green_box(c, x - 8, y - 8, 306, 266, prog(t, CAPS.w(2) - 0.05, 0.2))
        km = e_io(prog(t, a + 0.2, CAPS.w(2) - 0.05 - a - 0.2))
        cursor(c, lerp(700, 230, km), lerp(820, 380, km), prog(t, CAPS.w(2) - 0.05, 0.3))
        if t >= CAPS.w(2):
            txt(c, "word-synced to your voice", 70, 800, "bold", 28, GREEN)
        return
    if t < SWAP.s - 0.05:
        txt(c, "Layers", 70, 175, "heavy", 48, UI_TXT)
        kd = e_io(prog(t, BEHIND.w(1) - 0.1, 0.45))
        rows = [("T", "Captions"), ("●", "You (cut-out)"), ("▢", "Background")]
        ys = [240, 360, 480]
        order_y = {0: lerp(ys[0], ys[1], kd), 1: lerp(ys[1], ys[0], kd), 2: ys[2]}
        for j, (ic, nm) in enumerate(rows):
            y = order_y[j]
            card(c, 70, y, 470, 100, GREEN if (j == 0 and 0 < kd < 1) else WHITE, 16,
                 border=GREEN if j == 0 and kd > 0 else UI_LINE)
            c.drawRRect(kit.rrect(95, y + 25, 50, 50, 10), fill(UI_SOFT))
            txt(c, ["T", "P", "B"][j], 120, y + 62, "black", 26, UI_TXT, anchor="c")
            txt(c, nm, 165, y + 62, "bold", 28, UI_TXT)
        if kd < 1:
            cursor(c, 450, order_y[0] + 50, prog(t, BEHIND.w(1) - 0.15, 0.25))
        preview_tile(c, t, 580, 220, 430, 600, "#2B3436", "TEXT", prog(t, BEHIND.w(1), 0.3))
        if t >= BEHIND.w(2):
            txt(c, "text behind you", 70, 680, "bold", 28, GREEN)
            check(c, 330, 670, 34, prog(t, BEHIND.w(2), 0.3))
        return
    txt(c, "Background", 70, 175, "heavy", 48, UI_TXT)
    swatches = [None, "#FF4D3D", LIME, PURPLE, "#2F7BFF", "#2B3436"]
    n = int(clamp((t - SWAP.w(1)) / 0.16, 0, len(swatches) - 1)) if t >= SWAP.w(1) else 0
    # colour picker like the reference: saturation square + hue strip
    sq = skia.Rect.MakeXYWH(70, 220, 440, 440)
    hue = kit.rgb(swatches[n] or "#6A7F80")
    p = skia.Paint(Shader=skia.GradientShader.MakeLinear([skia.Point(70, 0), skia.Point(510, 0)],
                                                         [col(WHITE), col("#%02x%02x%02x" % hue)]))
    c.drawRRect(kit.rrect(70, 220, 440, 440, 16), p)
    p2 = skia.Paint(Shader=skia.GradientShader.MakeLinear([skia.Point(0, 220), skia.Point(0, 660)],
                                                          [col("#000000", 0), col("#000000")]))
    c.drawRRect(kit.rrect(70, 220, 440, 440, 16), p2)
    hues = ["#FF0000", "#FFFF00", "#00FF00", "#00FFFF", "#0000FF", "#FF00FF", "#FF0000"]
    p3 = skia.Paint(Shader=skia.GradientShader.MakeLinear([skia.Point(70, 0), skia.Point(510, 0)],
                                                          [col(h_) for h_ in hues]))
    c.drawRRect(kit.rrect(70, 690, 440, 30, 15), p3)
    c.drawCircle(lerp(120, 480, n / 5), 705, 20, stroke(WHITE, 6))
    c.drawCircle(420, 300, 18, stroke(WHITE, 6))
    for j, sw in enumerate(swatches[1:]):
        c.drawCircle(100 + j * 75, 790, 26, fill(sw))
        if j + 1 == n:
            c.drawCircle(100 + j * 75, 790, 34, stroke(GREEN, 5))
    preview_tile(c, t, 580, 220, 430, 600, swatches[n] if n else None)


TRACKS = [("Original score", PURPLE, MUSIC.s), ("Whooshes", BLUE, WHOOSH.s), ("Hits", RED, HITS.s)]


def sc_sound(c, t, a, b):
    nav(c)
    txt(c, "Sound", 70, 175, "heavy", 48, UI_TXT)
    txt(c, "0 samples · 0 licences", 1010, 175, "bold", 24, UI_SUB, anchor="r")
    for j, (nm, cc, tj) in enumerate(TRACKS):
        y = 225 + j * 150
        kj = prog(t, tj - 0.05, 0.3)
        card(c, 70, y, 940, 125, WHITE, 18)
        c.drawCircle(125, y + 62, 30, fill(cc, 0.15 + 0.85 * clamp(kj * 2)))
        p = skia.Path()
        p.moveTo(117, y + 47)
        p.lineTo(117, y + 77)
        p.lineTo(140, y + 62)
        p.close()
        c.drawPath(p, fill(WHITE))
        txt(c, nm, 175, y + 52, "bold", 28, UI_TXT)
        if kj > 0:
            if j == 0:
                wave(c, 175, y + 92, 800, 34, 90, 1.3, cc, k=clamp((t - tj) / 1.2))
            elif j == 1:
                for q in range(5):
                    xq = 200 + q * 160
                    ww = 120 * clamp((t - tj - q * 0.05) / 0.25)
                    c.drawRRect(kit.rrect(xq, y + 84, ww, 16, 8), fill(cc, 0.8))
            else:
                for q in range(9):
                    if t - tj > q * 0.04:
                        c.drawRRect(kit.rrect(200 + q * 90, y + 70, 10, 46, 5), fill(cc))
    ks = prog(t, SCRATCH.s - 0.05, 0.25)
    bx = kit.rrect(70, 690, 940, 100, 50)
    c.drawRRect(bx, fill(INK if ks <= 0 else GREEN))
    txt(c, "Generate from scratch" if ks <= 0 else "Generated from scratch", 540, 752, "bold", 32, WHITE, anchor="c")
    if SCRATCH.s - 0.6 <= t < SCRATCH.s + 0.5:
        km = e_io(prog(t, SCRATCH.s - 0.6, 0.5))
        cursor(c, lerp(900, 560, km), lerp(880, 740, km), prog(t, SCRATCH.s - 0.05, 0.3))


STILL_TS = [3.0, 12.0, 20.0, 31.0, 40.0, 52.0]


def sc_stills(c, t, a, b):
    nav(c)
    txt(c, "Preview", 70, 175, "heavy", 48, UI_TXT)
    txt(c, "before anything renders", 300, 175, "medium", 28, UI_SUB)
    for j, ts in enumerate(STILL_TS):
        tj = STILLS.w(6) - 0.4 + j * 0.15
        kj = prog(t, tj, 0.3)
        x = 70 + (j % 3) * 320
        y = 215 + (j // 3) * 330
        if kj <= 0:
            c.drawRRect(kit.rrect(x, y, 290, 300, 18), fill(UI_SOFT))
            continue
        s = Src(ts)
        c.save()
        c.translate(x + 145, y + 150)
        c.scale(e_back(kj), e_back(kj))
        c.translate(-x - 145, -y - 150)
        img_card(c, s.img(), x, y, 290, 300, thumb_rect(ts, 290 / 300, 0.95), 18)
        c.restore()
        c.drawCircle(x + 255, y + 35, 22, fill(WHITE, clamp(kj * 2)))
        check(c, x + 255, y + 36, 26, prog(t, tj + 0.25, 0.25))
    if t >= STILLS.e - 0.3:
        c.drawRRect(kit.rrect(700, 880, 310, 60, 30), fill(INK))
        txt(c, "Looks good?", 855, 919, "bold", 26, WHITE, anchor="c")


def sc_prompt(c, t, a, b):
    nav(c)
    txt(c, "Make a change", 70, 175, "heavy", 48, UI_TXT)
    energy = prog(t, SAY.w(3), 0.3)
    clean = prog(t, SAY.w(6), 0.3)
    src = Src(E.src_at(t))
    sr = thumb_rect(src.ts, 380 / 640, 0.85)
    c.save()
    c.clipRRect(kit.rrect(70, 220, 380, 640, 20), skia.ClipOp.kIntersect, True)
    z = 1 + 0.12 * energy
    c.translate(260, 540)
    c.scale(z, z)
    c.translate(-260, -540)
    m = skia.ColorMatrix() if False else None
    paint = skia.Paint()
    sat = 1 + 0.5 * energy - 0.35 * clean
    cm = _sat_matrix(sat, 1 + 0.08 * energy)
    paint.setColorFilter(skia.ColorFilters.Matrix(cm))
    c.drawImageRect(src.img(), sr, skia.Rect.MakeXYWH(70, 220, 380, 640), SAMP, paint)
    c.restore()
    for j, (s, tj) in enumerate((("more energy", SAY.w(2)), ("cleaner", SAY.w(5)))):
        if t < tj - 0.1:
            continue
        y = 260 + j * 170
        n = int(clamp((t - tj + 0.1) / 0.35) * len(s))
        card(c, 490, y, 520, 100, WHITE, 18)
        txt(c, s[:n], 520, y + 63, "bold", 34, UI_TXT)
        green_box(c, 482, y - 8, 536, 116, prog(t, tj - 0.1, 0.2))
        if t >= tj + 0.35:
            c.drawRRect(kit.rrect(880, y + 25, 110, 50, 25), fill(INK))
            txt(c, "enter", 935, y + 58, "bold", 22, WHITE, anchor="c")
    if t >= SAY.w(8) - 0.05:
        k = e_back(prog(t, SAY.w(8) - 0.05, 0.3))
        c.drawRRect(kit.rrect(490, 640, 300 * k, 80, 40), fill(GREEN))
        if k > 0.7:
            txt(c, "changed", 640, 692, "bold", 30, WHITE, anchor="c")


def _sat_matrix(s, gain=1.0):
    lr, lg, lb = 0.299 * (1 - s), 0.587 * (1 - s), 0.114 * (1 - s)
    return [gain * (lr + s), gain * lg, gain * lb, 0, 0,
            gain * lr, gain * (lg + s), gain * lb, 0, 0,
            gain * lr, gain * lg, gain * (lb + s), 0, 0,
            0, 0, 0, 1, 0]


FORMATS = [("Reels", "9:16", 9 / 16, REELS.w(2)), ("Feed", "4:5", 4 / 5, FEEDS.w(0)),
           ("YouTube", "16:9", 16 / 9, FEEDS.w(1)), ("Square", "1:1", 1.0, FEEDS.w(2))]


def sc_export(c, t, a, b):
    nav(c)
    if t < REELS.w(2) - 0.12:
        cmd = "/export --all"
        card(c, 70, 160, 940, 100, INK, 50, border=None)
        n = int(clamp((t - EXPORT.w(1)) / 0.5) * len(cmd))
        txt(c, cmd[:n] + ("|" if int(t * 4) % 2 else ""), 120, 225, "monob", 36, WHITE)
        if t >= EXPORT.w(3) - 0.05:
            k = prog(t, EXPORT.w(3) - 0.05, 0.3)
            card(c, 70, 300, 940, 560, SKY, 26, border=None, shadow=0)
            pct = int(100 * clamp((t - EXPORT.w(3)) / 1.6))
            txt(c, f"{pct}%", 120, 620, "light", 240, BLUE, a=k)
            txt(c, "export", 130, 700, "bold", 30, BLUE, a=k)
            c.drawRRect(kit.rrect(130, 760, 820, 14, 7), fill(WHITE, k))
            c.drawRRect(kit.rrect(130, 760, 820 * pct / 100, 14, 7), fill(BLUE, k))
        return
    txt(c, "Every format", 70, 175, "heavy", 48, UI_TXT)
    src = Src(E.src_at(t))
    boxes = [(70, 230, 236, 420), (340, 230, 336, 420), (710, 230, 300, 169), (710, 480, 170, 170)]
    for j, (nm, ar, asp, tj) in enumerate(FORMATS):
        kj = prog(t, tj - 0.05, 0.3)
        if kj <= 0:
            continue
        x, y, ww, hh = boxes[j]
        c.save()
        c.translate(x + ww / 2, y + hh / 2)
        c.scale(e_back(kj), e_back(kj))
        c.translate(-x - ww / 2, -y - hh / 2)
        img_card(c, src.img(), x, y, ww, hh, thumb_rect(src.ts, asp, 0.8 if asp > 1 else 1.0), 14)
        c.restore()
        txt(c, f"{nm}  {ar}", x, y + hh + 38, "bold", 24, UI_TXT, a=clamp(kj * 2))
        check(c, x + ww - 26, y + 30, 30, prog(t, FEEDS.w(3) + j * 0.06, 0.25))


SCENES = dict(landing=sc_landing, upload=sc_upload, analyze=sc_analyze, card2s=sc_card2s, timeline=sc_timeline,
              look=sc_look, sound=sc_sound, claims=sc_claims, stills=sc_stills, prompt=sc_prompt, export=sc_export)


# ================================================================== CTA
def cta(c, t):
    if not at(SOIF) <= t < END_A:
        return
    # PIP card of the raw take, the arrow and the hand-lettered line (reference 41-44 s)
    kc = prog(t, REC.s - 0.1, 0.35)
    if kc > 0:
        x, y, w, h = 590, 210, 300, 534
        s = lerp(0.6, 1.0, e_back(kc))
        c.save()
        c.translate(x + w / 2, y + h / 2)
        c.scale(s, s)
        c.translate(-x - w / 2, -y - h / 2)
        rr = kit.rrect(x, y, w, h, 26)
        c.drawRRect(rr.makeOffset(0, 10), fill("#000000", 0.4, blur=18))
        src = Src(E.src_at(t))
        c.save()
        c.clipRRect(rr, skia.ClipOp.kIntersect, True)
        c.drawImageRect(src.raw(), skia.Rect.MakeXYWH(60, 120, 960, 1707), skia.Rect.MakeXYWH(x, y, w, h), SAMP)
        c.restore()
        c.drawRRect(rr, stroke(WHITE, 4))
        hand(c, "MY RAW TAKE", x + w / 2, y + 70, 26, 1.0)
        c.restore()
    hand(c, "WHAT I ACTUALLY", 70, 1270 - fit("RECORDED", 640, 110)[1] - 36, 40, prog(t, REC.s - 0.05, 0.3),
         anchor="l")
    big_type(c, "RECORDED", 70, 1270, t, REC.w(2) - 0.05, maxw=640, size=110, anchor="l")
    arrow_doodle(c, [(260, 1080), (230, 950), (320, 860), (480, 760), (575, 640)], prog(t, REC.s + 0.1, 0.5))


def end_card(c, t):
    if t < END_A:
        return
    t0 = END_A
    cap = fit(CTA_WORD, 960, 160)[1]
    bubble_doodle(c, 540, TITLE_Y - cap - 140, 50, prog(t, t0, 0.35), INK)
    hand(c, "COMMENT", 540, TITLE_Y - cap - 36, 40, prog(t, t0 + 0.1, 0.3))
    big_type(c, CTA_WORD, 540, TITLE_Y, t, t0 + 0.25, size=160)
    if t >= t0 + 0.9:
        s = "and I'll send you the raw take."
        txt(c, s, 540, 1404, "medium", 46, "#000000", anchor="c", paint=fill("#000000", 0.55, blur=8))
        txt(c, s, 540, 1400, "medium", 46, WHITE, anchor="c", a=prog(t, t0 + 0.9, 0.2))


# ================================================================== glitch
GL_COLS = [LIME, PURPLE, BLUE, GREEN, WHITE, YEL]


def glitch_k(t):
    for tg in GLITCHES:
        if tg - 0.05 <= t < tg + 0.1:
            return tg, 1 - abs(t - tg - 0.02) / 0.1
    return None, 0.0


def glitch_blocks(c, t, tg, k):
    f = int(t * FPS)
    for j in range(7):
        r = hrand(tg, f, j)
        x = hrand(tg, f, j, 1) * W
        y = hrand(tg, f, j, 2) * H * 0.8
        w = 80 + 300 * hrand(tg, f, j, 3)
        h = 40 + 220 * hrand(tg, f, j, 4)
        c.drawRect(skia.Rect.MakeXYWH(x - w / 2, y, w, h), fill(GL_COLS[int(r * len(GL_COLS)) % len(GL_COLS)],
                                                                 0.9 * clamp(k * 1.5)))


# ================================================================== draw
def draw(c, t, f):
    g = {}
    ts = E.src_at(t)
    src = Src(ts)
    c.clear(col("#30393A"))
    sp = split_now(t) if t < END_A else None
    split = sp is not None
    cm = cam(t, ts, split)
    c.save()
    apply(c, cm)
    c.drawImage(src.img(), 0, 0, SAMP)
    c.restore()
    if split:
        name, a, b = sp
        c.save()
        c.clipRect(skia.Rect.MakeWH(W, PANEL))
        c.drawRect(skia.Rect.MakeWH(W, PANEL), fill(WHITE))
        z = 1 + 0.045 * e_io(prog(t, a, b - a))                   # slow push into the UI
        c.translate(540, 480)
        c.scale(z, z)
        c.translate(-540, -480)
        SCENES[name](c, t, a, b)
        c.restore()
    else:
        draw_titles(c, t, head_top(t, ts))
        cta(c, t)
        end_card(c, t)
    draw_subs(c, t, split)
    tg, k = glitch_k(t)
    if k > 0:
        glitch_blocks(c, t, tg, k)
        g["glitch"] = k
    if t < 0.08:
        g["flash"] = 0.5 * (1 - t / 0.08)
    return g


SHAKES += [(H_SIX.s, 10), (GONE.s, 8), (SOUND.s, 12), (PROOF.w(2), 10), (END_A + 0.3, 8)]

_VIG = None


def post(rgb, g, f):
    global _VIG
    if _VIG is None or _VIG.shape[:2] != rgb.shape[:2]:
        h, w = rgb.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h * 0.45) / (h / 2)) ** 2)
        _VIG = (1 - 0.42 * np.clip(r - 0.45, 0, None) ** 1.4)[..., None].astype(np.float32)
    s = rgb.shape[1] / W
    out = rgb.astype(np.float32)
    k = g.get("glitch", 0)
    if k:
        sh = int(14 * k * s)
        out[..., 0] = np.roll(out[..., 0], sh, axis=1)
        out[..., 2] = np.roll(out[..., 2], -sh, axis=1)
        rng = np.random.default_rng(f)
        for _ in range(6):
            y0 = int(rng.uniform(0, out.shape[0] - 60 * s))
            hh = int(rng.uniform(10, 70) * s)
            out[y0:y0 + hh] = np.roll(out[y0:y0 + hh], int(rng.uniform(-80, 80) * s * k), axis=1)
    if g.get("flash"):
        out = out + (255 - out) * g["flash"]
    out *= _VIG
    out = np.clip(out, 0, 255).astype(np.uint8)
    return kit.grain(out, f, amt=0.014, scale=2)


FILM = kit.Film(draw, TOTAL, FPS, post=post, out_dir=OUT)


# ================================================================== audio
def sfx_list():
    S = []

    def a(t, kind, gain=-10, **kw):
        S.append(dict(t=t, kind=kind, gain_db=gain, **kw))

    for small, big, ts_, tb, te in TITLES:
        if big:
            a(tb, "typing", -17, dur=0.045 * len(big) + 0.1)
            a(tb + 0.045 * len(big), "pop", -15)
        a(ts_, "swish", -17)
    for tg in GLITCHES:
        a(tg - 0.05, "glitch", -13)
        a(tg - 0.12, "whoosh", -15, dur=0.25)
    a(0.0, "impact", -9)
    for j in range(8):
        a(H_WENT.s + j * 0.06, "pop", -19, pan=(j - 3.5) / 5)
    a(H_SIX.s, "impact", -11)
    # app interactions
    for j in range(6):
        a(I_STEP.s + j * 0.11, "tick", -16)
    a(DROP.w(1) + 0.25, "click", -9)
    a(DROP.w(1) + 1.3, "ding", -16)
    a(ONE.w(1) - 0.05, "pop", -13)
    a(MIST.w(2) - 0.05, "click", -11)
    a(WATCH.w(4), "ding", -17)
    a(TRANS.s, "typing", -18, dur=max(0.4, TRANS.e - TRANS.s))
    a(FINDS.w(2) - 0.05, "click", -9)
    a(MOVES.w(2), "whoosh", -15, dur=0.45)
    a(FIRST.w(6) - 0.05, "impact", -12)
    for j in range(3):
        a(PUR.w(j) - 0.05, "tick", -12)
    a(GONE.s - 0.05, "click", -9)
    a(GONE.s, "swish", -12)
    a(EXACT.w(3) - 0.05, "click", -10)
    a(CAPS.w(2) - 0.05, "click", -9)
    a(BEHIND.w(1) - 0.15, "click", -11)
    a(BEHIND.w(1) + 0.3, "pop", -14)
    for j in range(5):
        a(SWAP.w(1) + j * 0.16, "tick", -13)
    a(ZOOMS.s - 0.05, "whoosh", -13, dur=0.3)
    a(S5.s - 0.5, "riser", -13, dur=0.5 + SOUND.s - S5.s)
    a(SOUND.s, "bass_drop", -12)
    a(WHOOSH.e - 0.12, "whoosh", -9, dur=0.45)
    a(HITS.e - 0.06, "impact", -9)
    a(SCRATCH.s - 0.05, "click", -9)
    a(SCRATCH.s, "sparkle", -14)
    a(CLAIMS.w(4) - 0.05, "impact", -12)
    a(PROOF.w(2) - 0.05, "impact", -10)
    for j in range(6):
        a(STILLS.w(6) - 0.4 + j * 0.15, "shutter", -17, pan=(j - 2.5) / 4)
    for tj in (SAY.w(2), SAY.w(5)):
        a(tj - 0.1, "typing", -16, dur=0.35)
        a(tj + 0.35, "click", -12)
    a(SAY.w(8) - 0.05, "ding", -13)
    a(EXPORT.w(1), "typing", -15, dur=0.5)
    a(EXPORT.w(3) + 1.6, "ding", -13)
    for _, _, _, tj in FORMATS:
        a(tj - 0.05, "pop", -13)
    a(REC.s - 0.1, "pop", -11)
    a(REC.s + 0.1, "swish", -14)
    a(END_A + 0.25, "typing", -15, dur=0.3)
    a(END_A + 0.5, "pop", -11)
    return S


MUSIC_DB, SFX_DB, DUCK_DB = -10, 0, -7


def build_audio():
    SR = ak.SR
    work = HERE / "work"
    voice = ak.read_audio(work / "stem_voice.wav")             # the cleaned, cut voice from edit.py (same EDL)
    n = int(TOTAL * SR) + 1
    voice = np.pad(voice, ((0, max(0, n - len(voice))), (0, 0)))[:n]
    drop = int(SOUND.s * SR)
    bed_a = ak.music_bed("retro_a", seconds=SOUND.s + 2, intro_bars=0, seed=21)
    bed_b = ak.music_bed("retro_b", seconds=TOTAL - SOUND.s + 2, intro_bars=0, seed=23)
    mus = np.zeros((n, 2), np.float32)
    mus[:drop] = bed_a[:drop] * ak.db(-3)
    k = int(0.3 * SR)
    mus[drop - k:drop] *= np.linspace(1, 0.4, k)[:, None]
    lb = bed_b[: n - drop] * ak.db(-1)
    mus[drop:drop + len(lb)] = lb
    fi = int(0.4 * SR)
    mus[:fi] *= np.linspace(0, 1, fi)[:, None]
    mus *= ak.duck_gain(voice, DUCK_DB)[:, None]
    end = int((TOTAL - 0.05) * SR)
    fo = int(1.2 * SR)
    mus[end - fo:end] *= np.linspace(1, 0, fo)[:, None]
    mus[end:] = 0
    mus *= ak.db(MUSIC_DB)
    fx = np.zeros_like(voice)
    for s in sfx_list():
        kind = s["kind"]
        clip = ak.SFX[kind](s["dur"]) if "dur" in s and kind in ("whoosh", "riser", "typing") else ak.SFX[kind]()
        ak.place(fx, clip, max(0.0, s["t"]), s["gain_db"] + SFX_DB, s.get("pan", 0.0))
    for name, x in (("voice", voice), ("music", mus), ("sfx", fx)):
        ak.write_wav(work / f"v2_stem_{name}.wav", x)
    out = voice + mus + fx
    peak = np.max(np.abs(out)) or 1
    if peak > 0.98:
        out = np.tanh(out / peak * 1.2) / math.tanh(1.2) * 0.98
    path = work / "v2_mix.wav"
    ak.write_wav(path, out)
    print("->", path)
    return path


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "stills":
        FILM.stills([float(x) for x in sys.argv[2:]])
    elif cmd == "sheet":
        ts = [float(x) for x in sys.argv[2:]] or [round(TOTAL * (i + 0.5) / 48, 2) for i in range(48)]
        FILM.sheet(ts, cols=8, scale=0.25, name="creator_sheet.png")
    elif cmd == "audio":
        build_audio()
    elif cmd == "render":
        pic = FILM.render(OUT / "v2_picture.mp4")
        aud = build_audio()
        E.finish(pic, aud, OUT / "vibe_reel_v2.mp4")


if __name__ == "__main__":
    main()
