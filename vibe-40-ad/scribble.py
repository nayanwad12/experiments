"""scribble: the ad take re-edited in the "hand-made text / retro computer" creator style (third reference).

Reference, measured: fisheye opening shot with a black ring vignette, punchy cool grade; ONE white condensed
word at a time as captions; two-tier titles = small white condensed caps + a big hand-drawn marker word
(red-orange #EE4B20 or yellow #F9D514) written letter by letter with a stop-motion "boil", the yellow ones
behind the head; split screens with the speaker in a rounded card: a retro Windows-style desktop (teal-blue,
"System message" dialogs in blue handwriting, OK/Cancel, a media player) and a light canvas with royal-blue
UI bars (#2553C6), a font dropdown, a blue handwritten word, a colour picker; CTA "COMMENT 'SCRIBBLE'".
Same cut and 1.15x as reel.py (core.py); Meta-ad safe (nothing in the top 14 % or the bottom 35 %).

    python3 scribble.py sheet [t ...]    -> out/scribble_sheet.png
    python3 scribble.py render           -> out/vibe40_scribble.mp4
"""

import math
import sys
from pathlib import Path

import cv2
import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "reels" / "common"))
import audio_kit as ak  # noqa: E402
import core as E  # noqa: E402
import kit  # noqa: E402
from kit import clamp, e_back, e_in, e_io, e_out, fill, hrand, lerp, measure, prog, stroke  # noqa: E402

cv2.setNumThreads(1)
kit.FONTS.update(bebas="BebasNeue-Regular.ttf", marker="PermanentMarker.ttf", gaegu="Gaegu.ttf",
                 vt="VT323-Regular.ttf")
W, H, FPS = 1080, 1920, 30
OUT = HERE / "out"
TOTAL = E.TOTAL
SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNone)

RED = "#EE4B20"
YEL = "#F9D514"
BLUE = "#2553C6"
CANVAS = "#F2EFF3"
DESK = "#006B99"
DARK = "#000F19"
WHITE = "#FFFFFF"
INK = "#101114"
GREY = "#C3C3C3"
NAVY = "#0A1E7A"


def col(c, a=1.0):
    r, g, b = kit.rgb(c)
    return skia.Color(r, g, b, int(255 * clamp(a)))


# ================================================================== grade + fisheye
def _lut():
    x = np.arange(256, dtype=np.float32) / 255
    s = np.clip(x + 0.08 * np.sin(2 * math.pi * (x - 0.5)), 0, 1)
    r = 0.02 + 0.97 * s ** 1.02
    g = 0.025 + 0.95 * s
    b = 0.04 + 0.95 * s ** 0.96
    return np.ascontiguousarray(np.stack([(np.clip(c, 0, 1) * 255).astype(np.uint8) for c in (r, g, b)], 1)
                                .reshape(256, 1, 3))


LUT = _lut()
WALL = np.array([0.80, 0.88, 0.98], np.float32)          # the white wall pushed cool, like the reference room
_MAPS = {}


def fish_maps(k):
    """barrel-distortion remap (fisheye look) of strength k for the full 1080x1920 frame."""
    if k not in _MAPS:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        cx, cy = W / 2, H * 0.47
        nx, ny = (xx - cx) / (W / 2), (yy - cy) / (W / 2)
        r2 = nx * nx + ny * ny
        f = 1 / (1 + k * r2)                                   # sample further out -> bulge in the centre
        f = f / f[int(cy), int(cx)]
        _MAPS[k] = ((cx + nx * f * (W / 2)).astype(np.float32), (cy + ny * f * (W / 2)).astype(np.float32))
    return _MAPS[k]


def sk_img(rgb, a=None):
    out = cv2.cvtColor(rgb, cv2.COLOR_RGB2RGBA)
    if a is not None:
        out[..., 3] = a
    return skia.Image.fromarray(out, colorType=skia.kRGBA_8888_ColorType)


class Src:
    _cache = {}

    def __new__(cls, ts, fish=0.0):
        fi = int(clamp(round(ts * E.SRC_FPS), 0, E.NSRC - 1))
        key = (fi, fish)
        if key in cls._cache:
            return cls._cache[key]
        o = super().__new__(cls)
        if len(cls._cache) > 14:
            cls._cache.pop(next(iter(cls._cache)))
        cls._cache[key] = o
        o.fi, o.ts, o.fish, o._m = fi, ts, fish, {}
        return o

    def _memo(self, k, fn):
        if k not in self._m:
            self._m[k] = fn()
        return self._m[k]

    def _graded(self):
        def make():
            raw = E.frame_rgb(self.fi)
            p = cv2.LUT(raw, LUT)
            gray = cv2.cvtColor(cv2.cvtColor(p, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB)
            p = cv2.addWeighted(p, 1.18, gray, -0.18, 0)                       # punchier colour
            a8 = cv2.resize(E.alpha_small(self.fi), (W, H))
            a = a8.astype(np.float32) / 255
            a = a * a * (3 - 2 * a)
            fac = cv2.merge([a + (1 - a) * WALL[ch] for ch in range(3)])
            room = cv2.multiply(p, fac, dtype=cv2.CV_8U)
            a8 = (a * 255).astype(np.uint8)
            if self.fish:
                mx, my = fish_maps(self.fish)
                room = cv2.remap(room, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
                p = cv2.remap(p, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
                a8 = cv2.remap(a8, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            return room, a8, p
        return self._memo("g", make)

    def img(self):
        return self._memo("img", lambda: sk_img(self._graded()[0]))

    def person(self):
        return self._memo("person", lambda: sk_img(self._graded()[2], self._graded()[1]))

    def raw(self):
        return self._memo("raw", lambda: sk_img(E.frame_rgb(self.fi)))


# ================================================================== timing
P = E.P
HOOK = P("the video you are watching right now i didn't edit it")
DID = P("my vibe editing system did")
REC1 = P("i recorded one take on my phone")
PME = P("pauses mistakes everything")
TOLD = P("then i told it what i want in simple words")
CUT = P("it cut every pause down to the exact word")
CAPS = P("it added these captions")
BEH = P("put text behind me")
BG = P("and changed my background")
MUS = P("even the music and sound effects made from scratch no copyright")
STL = P("and before exporting it showed me every key moment")
CMD = P("one command and it's ready for every platform")
NOT = P("no timeline no editing app just my system")
CTA = P("so if you want to learn my system tap the link below")
DROP_T = MUS.w(2)
NOCOPY = MUS.w(9) - 0.06


def at(p):
    rs = E.run_start(p)
    return rs if p.s - rs < 0.3 else p.s - 0.05


SPLITS = [("desk_rec", at(REC1), at(TOLD)), ("canvas_prompt", at(TOLD), at(CUT)), ("desk_cut", at(CUT), at(CAPS)),
          ("desk_sound", at(MUS), NOCOPY), ("canvas_stills", at(STL), at(CMD)), ("desk_export", at(CMD), at(NOT))]


def split_now(t):
    for name, a, b in SPLITS:
        if a <= t < b:
            return name, a, b
    return None


# ================================================================== framing
BASE_DY = 60


def cam(t, ts):
    fx, fy = E.face(ts)
    k = max([i for i, s in enumerate(E.RUN_STARTS) if s <= t + 1e-6] or [0])
    z = (1.0, 1.1)[k % 2] * (1 + 0.008 * (t - E.RUN_STARTS[k]))
    if t < 0.3:
        z *= lerp(1.15, 1.0, e_out(t / 0.3))
    return z, fx, fy, BASE_DY


def apply(c, cm):
    z, fx, fy, dy = cm
    c.translate(fx, fy + dy)
    c.scale(z, z)
    c.translate(-fx, -fy)


def fish_amount(t):
    return 0.32 if t < at(REC1) else 0.12


# ================================================================== type
def word_caps(c, s, x, y, size, color=WHITE, a=1.0, anchor="c", glow=True):
    if glow:
        kit.text(c, s, x, y, "bebas", size, color=color, a=a, anchor=anchor, paint=fill(color, 0.45 * a, blur=size * 0.12))
        kit.text(c, s, x + 2, y + 4, "bebas", size, color="#000000", a=a, anchor=anchor,
                 paint=fill("#000000", 0.45 * a, blur=6))
    kit.text(c, s, x, y, "bebas", size, color=color, a=a, anchor=anchor)


def marker(c, s, x, y, t, t0, size=170, color=RED, maxw=980, stagger=0.06, anchor="c"):
    """big hand-drawn marker word: written letter by letter, then boiling (stop motion, 8 fps)."""
    if t < t0:
        return 0
    w = measure(s, "marker", size)
    if w > maxw:
        size *= maxw / w
        w = measure(s, "marker", size)
    f = kit.font("marker", size)
    x0 = x - w / 2 if anchor == "c" else x
    boil = int(t * 8)
    xx = x0
    for i, ch in enumerate(s):
        cw = f.measureText(ch)
        k = clamp((t - t0 - i * stagger) / 0.1)
        if k > 0:
            jx = (hrand(s, i, boil) - 0.5) * size * 0.04
            jy = (hrand(s, i, boil, 1) - 0.5) * size * 0.05
            rot = (hrand(s, i, boil, 2) - 0.5) * 6
            sc = lerp(1.35, 1.0, e_out(k))
            c.save()
            c.translate(xx + cw / 2 + jx, y + jy)
            c.rotate(rot)
            c.scale(sc, sc)
            c.drawString(ch, -cw / 2 + 4, 6, f, fill("#000000", 0.35 * clamp(k * 3), blur=6))
            c.drawString(ch, -cw / 2, 0, f, fill(color, clamp(k * 3)))
            c.restore()
        xx += cw
    return w


def hand_arrow(c, pts, k, color=WHITE, width=9):
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
        p.setPathEffect(skia.TrimPathEffect.Make(0, k / 0.8))
    c.drawPath(path, p)
    if k > 0.8:
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        ang = math.atan2(y1 - y0, x1 - x0)
        hk = e_out((k - 0.8) / 0.2) * 44
        for sg in (-1, 1):
            a2 = ang + math.pi + sg * 0.55
            c.drawLine(x1, y1, x1 + hk * math.cos(a2), y1 + hk * math.sin(a2), stroke(color, width))


# ================================================================== titles (full frame)
TITLE_Y = 535          # front titles sit above the head (head top ~555 in full frame)
BEHIND_Y = 640         # behind-the-head titles: the head covers their middle, like the reference
# small line, big marker word, colour, t small, t big, t end, behind the head?
TITLES = [
    ("THE VIDEO YOU'RE WATCHING", "I DIDN'T EDIT IT", RED, HOOK.s - 0.03, HOOK.w(7) - 0.05, DID.s - 0.03, False),
    ("MY", "VIBE EDITING SYSTEM", YEL, DID.s - 0.03, DID.w(1) - 0.05, at(REC1), True),
    ("IT ADDED", "THESE CAPTIONS", RED, CAPS.s - 0.03, CAPS.w(2) - 0.05, BEH.s - 0.03, False),
    ("PUT", "TEXT", YEL, BEH.s - 0.03, BEH.w(1) - 0.05, BG.s - 0.03, True),
    ("AND CHANGED MY", "BACKGROUND", RED, BG.s - 0.03, BG.w(3) - 0.05, at(MUS), False),
    ("NO", "COPYRIGHT", RED, NOCOPY, NOCOPY + 0.05, at(STL), False),
    ("NO TIMELINE. NO EDITING APP.", "JUST MY SYSTEM", RED, NOT.s - 0.03, NOT.w(5) - 0.05, CTA.s - 0.03, False),
    ("WANT TO LEARN", "MY SYSTEM?", YEL, CTA.s - 0.03, CTA.w(6) - 0.05, CTA.w(8) - 0.04, True),
    ("TAP THE LINK", "BELOW", RED, CTA.w(8) - 0.04, CTA.w(11) - 0.05, TOTAL + 1, False),
]


def titles(c, t, behind):
    for small, big, colr, ts_, tb, te, beh in TITLES:
        if beh != behind or not ts_ <= t < te:
            continue
        size = 200 if len(big) <= 6 else 160
        y = BEHIND_Y if behind else (455 if t < at(REC1) else TITLE_Y)    # the fisheye opening makes the head bigger
        if not behind:
            k = prog(t, ts_, 0.2)
            word_caps(c, small, 540, y - cap_h(big, size) - 34, 60, WHITE, a=clamp(k * 2))
        marker(c, big, 540, y, t, tb, size, colr)
        if big == "BELOW":
            hand_arrow(c, [(860, 700), (930, 830), (910, 960), (870, 1080)], prog(t, tb + 0.15, 0.4), WHITE, 9)


def cap_h(big, size, maxw=980):
    w = measure(big, "marker", size)
    if w > maxw:
        size *= maxw / w
    return kit.font("marker", size).getMetrics().fCapHeight


def titles_small_behind(c, t):
    """the small white line of a behind-the-head title still sits in front."""
    for small, big, colr, ts_, tb, te, beh in TITLES:
        if beh and ts_ <= t < te:
            size = 200 if len(big) <= 6 else 160
            word_caps(c, small, 540, 390 if t < at(REC1) else 430, 60, WHITE, a=clamp(prog(t, ts_, 0.2) * 2))


# ================================================================== captions: one word at a time
SUB_Y = 1238
SPLIT_SUB_Y = 948
WORDS = sorted([w for w in E.WORDS if w.get("os") is not None], key=lambda w: w["os"])


def caption(c, t, split, on_canvas=False):
    cur = None
    for i, w in enumerate(WORDS):
        nxt = WORDS[i + 1]["os"] if i + 1 < len(WORDS) else w["oe"] + 0.5
        if w["os"] - 0.03 <= t < min(nxt - 0.02, w["oe"] + 0.45):
            cur = w
    if not cur:
        return
    s = cur["d"].upper().strip(".,?")
    k = prog(t, cur["os"] - 0.03, 0.08)
    if split:
        word_caps(c, s, 540, SPLIT_SUB_Y, 62, INK if on_canvas else WHITE, a=clamp(k * 3), glow=not on_canvas)
    else:
        word_caps(c, s, 540, SUB_Y, 66, WHITE, a=clamp(k * 3))


# ================================================================== retro desktop kit
PANEL = 900


def bevel(c, x, y, w, h, up=True):
    c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), fill(GREY))
    hi, lo = (WHITE, "#7B7B7B") if up else ("#7B7B7B", WHITE)
    c.drawLine(x, y, x + w, y, stroke(hi, 3, cap="butt"))
    c.drawLine(x, y, x, y + h, stroke(hi, 3, cap="butt"))
    c.drawLine(x, y + h, x + w, y + h, stroke(lo, 3, cap="butt"))
    c.drawLine(x + w, y, x + w, y + h, stroke(lo, 3, cap="butt"))


def window(c, x, y, w, h, title, k=1.0):
    if k <= 0:
        return False
    s = lerp(0.85, 1.0, e_back(clamp(k / 0.5)))
    c.save()
    c.translate(x + w / 2, y + h / 2)
    c.scale(s, s)
    c.translate(-x - w / 2, -y - h / 2)
    c.drawRect(skia.Rect.MakeXYWH(x + 8, y + 10, w, h), fill("#000000", 0.35, blur=10))
    bevel(c, x, y, w, h)
    tb = skia.Paint(Shader=skia.GradientShader.MakeLinear([skia.Point(x, 0), skia.Point(x + w, 0)],
                                                          [col(NAVY), col("#1084D0")]))
    c.drawRect(skia.Rect.MakeXYWH(x + 6, y + 6, w - 12, 44), tb)
    kit.text(c, title, x + 18, y + 38, "vt", 34, color=WHITE, anchor="l")
    for j in range(3):
        bevel(c, x + w - 46 - j * 40, y + 12, 34, 32)
    c.drawLine(x + w - 38, y + 20, x + w - 20, y + 38, stroke(INK, 3))
    c.drawLine(x + w - 20, y + 20, x + w - 38, y + 38, stroke(INK, 3))
    return True


def end_window(c):
    c.restore()


def button(c, x, y, w, h, label, pressed=False):
    bevel(c, x, y, w, h, up=not pressed)
    kit.text(c, label, x + w / 2, y + h / 2 + 11, "vt", 34, color=INK)


def cursor(c, x, y, click_k=0.0):
    if click_k > 0:
        c.drawCircle(x, y, 16 + 40 * e_out(click_k), fill(YEL, 0.35 * (1 - click_k)))
    p = skia.Path()
    pts = [(0, 0), (0, 46), (12, 35), (21, 55), (29, 51), (20, 32), (36, 32)]
    p.moveTo(x, y)
    for px, py in pts[1:]:
        p.lineTo(x + px, y + py)
    p.close()
    c.drawPath(p, fill(WHITE))
    c.drawPath(p, stroke(INK, 3))


def desktop(c, t):
    c.drawRect(skia.Rect.MakeWH(W, PANEL), fill(DESK))
    for j, (lab, ic) in enumerate((("My edit", "pc"), ("take_01", "film"), ("Recycle", "bin"))):
        x, y = 60, 60 + j * 150
        if ic == "pc":
            c.drawRect(skia.Rect.MakeXYWH(x + 14, y, 60, 46), fill(GREY))
            c.drawRect(skia.Rect.MakeXYWH(x + 20, y + 6, 48, 32), fill("#1F7FB7"))
            c.drawRect(skia.Rect.MakeXYWH(x + 30, y + 48, 28, 10), fill(GREY))
        elif ic == "film":
            c.drawRect(skia.Rect.MakeXYWH(x + 16, y, 56, 58), fill(WHITE))
            c.drawRect(skia.Rect.MakeXYWH(x + 26, y + 14, 36, 26), fill(INK))
        else:
            c.drawRect(skia.Rect.MakeXYWH(x + 22, y + 6, 44, 52), stroke(WHITE, 4))
        kit.text(c, lab, x + 44, y + 92, "vt", 30, color=WHITE)
    c.drawRect(skia.Rect.MakeXYWH(0, PANEL - 56, W, 56), fill(GREY))
    bevel(c, 8, PANEL - 50, 130, 44)
    kit.text(c, "Start", 73, PANEL - 18, "vt", 34, color=INK)
    kit.text(c, "vibe editing system", W - 20, PANEL - 18, "vt", 30, color=INK, anchor="r")


def blue_hand(c, s, x, y, size, k=1.0, color=BLUE, anchor="c", boil_t=None):
    if k <= 0:
        return
    n = int(len(s) * clamp(k))
    jy = (hrand(s, int((boil_t or 0) * 8)) - 0.5) * 3 if boil_t is not None else 0
    kit.text(c, s[:n], x, y + jy, "gaegu", size, color=color, anchor=anchor)


def dialog(c, x, y, w, h, title, text, t, t0, ok_t=None):
    k = prog(t, t0, 0.2)
    if not window(c, x, y, w, h, title, k):
        return
    blue_hand(c, text, x + w / 2, y + h / 2 + 14, 76, prog(t, t0 + 0.05, 0.35), boil_t=t)
    pressed = ok_t is not None and ok_t <= t < ok_t + 0.15
    button(c, x + w / 2 - 170, y + h - 80, 150, 54, "Ok", pressed)
    button(c, x + w / 2 + 20, y + h - 80, 150, 54, "Cancel")
    end_window(c)


def img_rect(c, img, x, y, w, h, sr):
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(x, y, w, h))
    c.drawImageRect(img, sr, skia.Rect.MakeXYWH(x, y, w, h), SAMP)
    c.restore()


def thumb_rect(ts, aspect):
    fx, fy = E.face(ts)
    h = 1100
    w = min(W, h * aspect)
    h = w / aspect
    return skia.Rect.MakeXYWH(clamp(fx - w / 2, 0, W - w), clamp(fy - h * 0.42, 0, H - h), w, h)


# ---------------------------------------------------------------- canvas kit (light, royal blue UI)
def canvas_bg(c):
    c.drawRect(skia.Rect.MakeWH(W, PANEL), fill(CANVAS))


def blue_bar(c, x, y, w, h, labels, k=1.0):
    if k <= 0:
        return
    c.drawRRect(kit.rrect(x, y, w * e_out(k), h, 8), fill(BLUE))
    if k > 0.6:
        n = len(labels)
        for j, lab in enumerate(labels):
            kit.text(c, lab, x + (j + 0.5) * w / n, y + h / 2 + 10, "vt", 30, color=WHITE)


def dropdown(c, x, y, label, value, open_k=0.0, options=()):
    c.drawRRect(kit.rrect(x, y, 330, 70, 8), fill(BLUE))
    kit.text(c, label, x + 20, y + 46, "vt", 32, color=WHITE, anchor="l")
    c.drawRRect(kit.rrect(x + 120, y + 10, 190, 50, 6), fill(WHITE))
    kit.text(c, value, x + 135, y + 45, "vt", 32, color=BLUE, anchor="l")
    if open_k > 0:
        for j, o in enumerate(options):
            yy = y + 70 + j * 46
            c.drawRect(skia.Rect.MakeXYWH(x + 120, yy, 190, 46 * e_out(open_k)), fill(WHITE))
            kit.text(c, o, x + 135, yy + 33, "vt", 30, color=BLUE, anchor="l", a=clamp(open_k * 2))


# ---------------------------------------------------------------- the split scenes
def sc_desk_rec(c, t, a, b):
    desktop(c, t)
    src = Src(E.src_at(t))
    if t < PME.s - 0.05:
        k = prog(t, a + 0.05, 0.25)
        x, y, w, h = 230, 70, 790, 640
        if window(c, x, y, w, h, "media player - take_01.mov", k):
            img_rect(c, src.raw(), x + 12, y + 56, w - 24, h - 150, thumb_rect(src.ts, (w - 24) / (h - 150)))
            c.drawRect(skia.Rect.MakeXYWH(x + 12, y + h - 90, w - 24, 78), fill(GREY))
            for j in range(5):
                button(c, x + 24 + j * 64, y + h - 80, 54, 54, ["|<", "<<", ">", ">>", ">|"][j])
            c.drawCircle(x + 60, y + 100, 12, fill(RED if int(t * 3) % 2 else "#FF9A86"))
            kit.text(c, "REC", x + 84, y + 111, "vt", 34, color=WHITE, anchor="l")
            if t >= REC1.w(2) - 0.05:
                blue_hand(c, "1 take", x + w / 2, y + 300, 110, prog(t, REC1.w(2) - 0.05, 0.3), color=YEL,
                          boil_t=t)
            end_window(c)
        return
    # pauses, mistakes, everything: system messages cascade
    for j, (s, tj) in enumerate((("pauses", PME.w(0)), ("mistakes", PME.w(1)), ("everything", PME.w(2)))):
        dialog(c, 180 + j * 70, 110 + j * 150, 640, 330, "System message", s, t, tj - 0.05,
               ok_t=PME.e + 0.1 if j == 2 else None)
    if t >= PME.e - 0.2:
        km = e_io(prog(t, PME.e - 0.2, 0.3))
        cursor(c, lerp(980, 410, km), lerp(860, 690, km), prog(t, PME.e + 0.1, 0.25))


def sc_canvas_prompt(c, t, a, b):
    canvas_bg(c)
    blue_bar(c, 210, 40, 660, 56, ["FX", "COLOR", "PROMPT", "VHS"], prog(t, a, 0.25))
    dropdown(c, 375, 130, "STYLE:", "PREMIUM", prog(t, TOLD.w(4), 0.2), ("PREMIUM", "CLEAN", "LOUD"))
    msg = ["make it premium.", "cut the pauses.", "add captions + music."]
    total = sum(len(m) for m in msg)
    n = int(total * clamp((t - TOLD.w(2)) / max(0.3, TOLD.e - TOLD.w(2))))
    c.drawRRect(kit.rrect(110, 420, 860, 330, 18), fill(WHITE))
    c.drawRRect(kit.rrect(110, 420, 860, 330, 18), stroke(BLUE, 6))
    used = 0
    for j, m in enumerate(msg):
        shown = m[:max(0, n - used)]
        used += len(m)
        blue_hand(c, shown, 150, 510 + j * 90, 80, 1.0, anchor="l", boil_t=t)
    if t >= TOLD.w(8) - 0.05:
        k = prog(t, TOLD.w(8) - 0.05, 0.2)
        c.drawRRect(kit.rrect(760, 770, 210, 70, 10), fill(BLUE, k))
        kit.text(c, "SEND", 865, 818, "vt", 40, color=WHITE, a=k)
        cursor(c, 900, 800, prog(t, TOLD.e - 0.1, 0.3))


BLOCKS = [("clip", 1.2), ("gap", 0.55), ("clip", 0.9), ("gap", 0.6), ("clip", 1.3), ("gap", 0.5), ("clip", 0.7),
          ("gap", 0.65), ("clip", 1.0)]


def sc_desk_cut(c, t, a, b):
    desktop(c, t)
    x, y, w, h = 70, 70, 940, 560
    if not window(c, x, y, w, h, "timeline.exe", prog(t, a, 0.2)):
        return
    src = Src(E.src_at(t))
    img_rect(c, src.img(), x + 300, y + 66, 340, 240, thumb_rect(src.ts, 340 / 240))
    if t < CUT.w(4) - 0.05:
        kg = e_io(prog(t, CUT.w(2) - 0.05, 0.4))
        tot0 = sum(d for _, d in BLOCKS)
        tot1 = sum(d for n, d in BLOCKS if n == "clip")
        xx = x + 30
        for j, (nm, d) in enumerate(BLOCKS):
            bw = (w - 60) * (d * (1 - kg) if nm == "gap" else d) / lerp(tot0, tot1, kg)
            if bw > 1:
                c.drawRect(skia.Rect.MakeXYWH(xx + 2, y + 360, bw - 4, 110), fill(RED if nm == "gap" else BLUE))
            xx += bw
        if kg > 0:
            blue_hand(c, "-2.3s of pauses", x + w - 40, y + 530, 50, 1.0, anchor="r", boil_t=t)
    else:
        words = ["down", "to", "the", "exact", "word"]
        xx = x + 50
        cut_x = 0
        for j, wd in enumerate(words):
            kj = prog(t, CUT.w(4 + j) - 0.04, 0.2)
            ww = measure(wd, "gaegu", 60) + 40
            bevel(c, xx, y + 370, ww, 90, up=kj <= 0)
            kit.text(c, wd, xx + ww / 2, y + 432, "gaegu", 60, color=BLUE)
            if j == 3:
                cut_x = xx - 10
            xx += ww + 20
        kc = e_back(prog(t, CUT.w(7) - 0.05, 0.3))
        if kc > 0:
            c.drawRect(skia.Rect.MakeXYWH(cut_x - 3, y + 340, 6, 150 * kc), fill(RED))
    end_window(c)


def sc_desk_sound(c, t, a, b):
    desktop(c, t)
    x, y, w, h = 120, 60, 840, 430
    if window(c, x, y, w, h, "media player - original_score.wav", prog(t, a, 0.2)):
        c.drawRect(skia.Rect.MakeXYWH(x + 14, y + 60, w - 28, h - 150), fill(INK))
        n = 32
        live = t >= DROP_T
        for j in range(n):
            lv = (0.25 + 0.7 * abs(math.sin(j * 0.7 + t * 9))) if live else 0.08
            bh = (h - 190) * lv
            c.drawRect(skia.Rect.MakeXYWH(x + 30 + j * (w - 60) / n, y + h - 100 - bh, (w - 60) / n * 0.7, bh),
                       fill(YEL if j % 5 == 0 else "#36D16B"))
        for j in range(5):
            button(c, x + 24 + j * 64, y + h - 80, 54, 54, ["|<", "<<", ">", ">>", ">|"][j])
        end_window(c)
    if t >= MUS.w(4) - 0.05:
        k = prog(t, MUS.w(4) - 0.05, 0.2)
        x2, y2 = 300, 470
        if window(c, x2, y2, 640, 330, "sound effects", k):
            for j, f_ in enumerate(("whoosh.wav", "pop.wav", "hit.wav")):
                kk = prog(t, MUS.w(5) + j * 0.08, 0.2)
                blue_hand(c, f_, x2 + 60, y2 + 120 + j * 64, 54, kk, anchor="l", boil_t=t)
            if t >= MUS.w(6) - 0.05:
                blue_hand(c, "made from scratch", x2 + 320, y2 + 300, 50, prog(t, MUS.w(6) - 0.05, 0.3), color=RED,
                          boil_t=t)
            end_window(c)


def sc_canvas_stills(c, t, a, b):
    canvas_bg(c)
    blue_bar(c, 210, 40, 660, 56, ["PREVIEW", "STILLS", "CHECK", "VHS"], prog(t, a, 0.25))
    for j, ts in enumerate(STILL_SRC):
        tj = STL.w(4) - 0.05 + j * 0.13
        kj = prog(t, tj, 0.25)
        x = 80 + (j % 3) * 315
        y = 140 + (j // 3) * 340
        c.drawRect(skia.Rect.MakeXYWH(x - 8, y - 8, 300, 316), fill(BLUE))
        if kj > 0:
            s = Src(ts)
            img_rect(c, s.img(), x, y, 284, 300, thumb_rect(ts, 284 / 300))
            if t >= STL.w(6) + j * 0.1:
                blue_hand(c, "ok!", x + 230, y + 60, 60, 1.0, color=YEL, boil_t=t)
    if t >= STL.w(6):
        blue_hand(c, "every key moment", 540, 860, 70, prog(t, STL.w(6), 0.3), boil_t=t)


FILES = [("reels.mp4", CMD.w(6)), ("feed.mp4", CMD.w(6) + 0.12), ("youtube.mp4", CMD.w(6) + 0.24),
         ("square.mp4", CMD.w(6) + 0.36)]


def sc_desk_export(c, t, a, b):
    desktop(c, t)
    x, y, w, h = 200, 60, 820, 360
    if window(c, x, y, w, h, "MS-DOS prompt", prog(t, a, 0.2)):
        c.drawRect(skia.Rect.MakeXYWH(x + 12, y + 56, w - 24, h - 68), fill("#000000"))
        cmd = "C:\\> vibe export --all"
        n = int(clamp((t - CMD.w(0)) / 0.45) * len(cmd))
        kit.text(c, cmd[:n] + ("_" if int(t * 4) % 2 else ""), x + 30, y + 120, "vt", 46, color="#C8C8C8", anchor="l")
        if t >= CMD.w(2):
            pct = int(100 * clamp((t - CMD.w(2)) / max(0.3, CMD.w(6) - CMD.w(2) - 0.1)))
            kit.text(c, f"exporting ... {pct}%", x + 30, y + 190, "vt", 46, color="#C8C8C8", anchor="l")
            for j in range(20):
                if j < pct / 5:
                    c.drawRect(skia.Rect.MakeXYWH(x + 30 + j * 36, y + 230, 30, 40), fill(BLUE))
        end_window(c)
    for j, (nm, tj) in enumerate(FILES):
        kj = prog(t, tj - 0.05, 0.25)
        if kj <= 0:
            continue
        fx, fy = 240 + j * 190, 520
        s = e_back(kj)
        c.save()
        c.translate(fx, fy)
        c.scale(s, s)
        c.drawRect(skia.Rect.MakeXYWH(-40, -50, 80, 100), fill(WHITE))
        c.drawRect(skia.Rect.MakeXYWH(-28, -30, 56, 40), fill(INK))
        kit.text(c, ">", 0, 0, "vt", 40, color=WHITE)
        kit.text(c, nm, 0, 90, "vt", 32, color=WHITE)
        c.restore()


SCENES = dict(desk_rec=sc_desk_rec, canvas_prompt=sc_canvas_prompt, desk_cut=sc_desk_cut, desk_sound=sc_desk_sound,
              canvas_stills=sc_canvas_stills, desk_export=sc_desk_export)
STILL_SRC = []


# ================================================================== draw
CARD = (70, 975, 940, 1000)          # speaker card in split screens (x, y, w, h); bottom runs off-frame


def draw_card(c, t, ts, canvas):
    x, y, w, h = CARD
    c.drawRect(skia.Rect.MakeXYWH(0, PANEL, W, H - PANEL), fill(CANVAS if canvas else DARK))
    rr = kit.rrect(x, y, w, h, 40)
    c.save()
    c.clipRRect(rr, skia.ClipOp.kIntersect, True)
    src = Src(ts)
    z = 0.92
    fx, fy = E.face(ts)
    c.translate(540, y + 290)
    c.scale(z, z)
    c.translate(-fx, -fy)
    c.drawImage(src.img(), 0, 0, SAMP)
    c.restore()


def bg_swap(t):
    if not BG.w(1) - 0.04 <= t < at(MUS):
        return None
    n = int((t - BG.w(1) + 0.04) / 0.2)
    return [BLUE, YEL, DESK, "#17171B"][n % 4]          # every swap colour keeps the red marker readable


def draw(c, t, f):
    g = {}
    ts = E.src_at(t)
    sp = split_now(t)
    c.clear(col(DARK))
    if sp:
        name, a, b = sp
        canvas = name.startswith("canvas")
        draw_card(c, t, ts, canvas)
        c.save()
        c.clipRect(skia.Rect.MakeWH(W, PANEL))
        SCENES[name](c, t, a, b)
        c.restore()
        caption(c, t, True, canvas)
        g["light"] = canvas
        return g
    fish = fish_amount(t)
    src = Src(ts, fish)
    cm = cam(t, ts)
    sw = bg_swap(t)
    if sw:
        c.drawRect(skia.Rect.MakeWH(W, H), fill(sw))
    else:
        c.save()
        apply(c, cm)
        c.drawImageRect(src.img(), skia.Rect.MakeXYWH(0, 0, W, 24), skia.Rect.MakeXYWH(0, -400, W, 412), SAMP)
        c.drawImage(src.img(), 0, 0, SAMP)
        c.restore()
    titles(c, t, behind=True)
    c.save()
    apply(c, cm)
    c.drawImage(src.person(), 0, 0, SAMP)
    c.restore()
    titles_small_behind(c, t)
    titles(c, t, behind=False)
    if CAPS.w(2) <= t < BEH.s - 0.03:
        word_caps(c, "THESE ONES", 860, SUB_Y - 230, 50, WHITE, a=prog(t, CAPS.w(2), 0.2))
        hand_arrow(c, [(860, SUB_Y - 210), (870, SUB_Y - 140), (780, SUB_Y - 70)], prog(t, CAPS.w(2), 0.4), YEL, 8)
    caption(c, t, False)
    if t < at(REC1):
        g["ring"] = 1.0
    return g


_VIG = {}


def post(rgb, g, f):
    key = (rgb.shape[:2], bool(g.get("ring")))
    if key not in _VIG:
        h, w = rgb.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        if g.get("ring"):                        # the fisheye's black ring
            r = np.sqrt(((xx - w / 2) / (w * 0.62)) ** 2 + ((yy - h * 0.47) / (h * 0.56)) ** 2)
            v = np.clip(1 - (r - 0.86) / 0.12, 0, 1) ** 1.5
        else:
            r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h * 0.45) / (h / 2)) ** 2)
            v = 1 - 0.4 * np.clip(r - 0.45, 0, None) ** 1.3
        _VIG[key] = v[..., None].astype(np.float32)
    out = rgb.astype(np.float32) * _VIG[key]
    out = np.clip(out, 0, 255).astype(np.uint8)
    return kit.grain(out, f, amt=0.007 if g.get("light") else 0.016, scale=2)


FILM = kit.Film(draw, TOTAL, FPS, post=post, out_dir=OUT)
STILL_SRC += [E.src_at(x) for x in (HOOK.w(3), DID.w(2), REC1.w(3), CAPS.w(3), BEH.w(2), MUS.w(2))]


# ================================================================== audio
def sfx_list():
    S = []

    def a(t, kind, gain=-12, **kw):
        S.append(dict(t=t, kind=kind, gain_db=gain, **kw))

    for small, big, colr, ts_, tb, te, beh in TITLES:
        a(tb, "swish", -15)
        a(tb + 0.06 * len(big), "pop", -15)
    for name, a_, b_ in SPLITS:
        a(a_ - 0.03, "click", -10)
    a(0.0, "impact", -10)
    a(at(REC1) + 0.05, "ding", -15)                      # the window opens
    for j in range(3):
        a(PME.w(j) - 0.05, "ding", -13)                  # system-message chimes
    a(PME.e + 0.1, "click", -10)
    a(TOLD.w(2), "typing", -16, dur=max(0.4, TOLD.e - TOLD.w(2)))
    a(TOLD.e - 0.1, "click", -10)
    a(CUT.w(2) - 0.05, "swish", -13)
    a(CUT.w(7) - 0.05, "click", -11)
    for j in range(4):
        a(BG.w(1) - 0.04 + j * 0.2, "tick", -14)
    a(DROP_T - 0.5, "riser", -16, dur=0.5)
    a(DROP_T, "bass_drop", -14)
    a(MUS.we(5) - 0.08, "whoosh", -10, dur=0.4)
    a(MUS.we(5) + 0.2, "impact", -11)
    for j in range(6):
        a(STL.w(4) - 0.05 + j * 0.13, "shutter", -18)
    a(CMD.w(0), "typing", -14, dur=0.45)
    for _, tj in FILES:
        a(tj - 0.05, "pop", -14)
    return S


def build_audio():
    SR = ak.SR
    work = HERE / "work"
    voice = E.build_voice()
    n = len(voice)
    ak.MOODS.setdefault("retro_b", dict(bpm=96, scale="major", key="A", prog=[4, 3, 2, 1], drums="four",
                                        lead="pluck", pad=True, sevenths=True, pump=True))
    bed = ak.music_bed("retro_b", seconds=TOTAL + 2, intro_bars=0, seed=51)[:n]
    bed = np.pad(bed, ((0, max(0, n - len(bed))), (0, 0)))
    low = np.stack([ak.filt(bed[:, ch], "low", 800) for ch in range(2)], 1)
    low *= np.sqrt(np.mean(bed ** 2) / (np.mean(low ** 2) + 1e-12)) * ak.db(-5)
    env = np.zeros(n, np.float32)
    d0 = int(DROP_T * SR)
    k = int(0.25 * SR)
    env[d0:] = 1
    env[d0 - k:d0] = np.linspace(0, 1, k)
    mus = low * (1 - env[:, None]) + bed * env[:, None]
    fi = int(0.3 * SR)
    mus[:fi] *= np.linspace(0, 1, fi)[:, None]
    mus *= ak.duck_gain(voice, -7)[:, None]
    end = int((TOTAL - 0.05) * SR)
    fo = int(1.0 * SR)
    mus[end - fo:end] *= np.linspace(1, 0, fo)[:, None]
    mus[end:] = 0
    mus *= ak.db(-9)
    fx = np.zeros_like(voice)
    for s in sfx_list():
        kind = s["kind"]
        clip = ak.SFX[kind](s["dur"]) if "dur" in s and kind in ("whoosh", "riser", "typing") else ak.SFX[kind]()
        ak.place(fx, clip, max(0.0, s["t"]), s["gain_db"], s.get("pan", 0.0))
    for name, x in (("voice", voice), ("music", mus), ("sfx", fx)):
        ak.write_wav(work / f"scribble_stem_{name}.wav", x)
    out = voice + mus + fx
    peak = np.max(np.abs(out)) or 1
    if peak > 0.98:
        out = np.tanh(out / peak * 1.2) / math.tanh(1.2) * 0.98
    path = work / "scribble_mix.wav"
    ak.write_wav(path, out)
    print("->", path)
    return path


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "sheet":
        ts = [float(x) for x in sys.argv[2:]] or [round(TOTAL * (i + 0.5) / 40, 2) for i in range(40)]
        FILM.sheet(ts, cols=8, scale=0.25, name="scribble_sheet.png")
    elif cmd == "audio":
        build_audio()
    elif cmd == "render":
        pic = FILM.render(OUT / "scribble_picture.mp4")
        aud = build_audio()
        E.finish(pic, aud, OUT / "vibe40_scribble.mp4")


if __name__ == "__main__":
    main()
