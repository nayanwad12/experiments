"""SYSTEM reel, "record study" cut: the same edit (cuts, timing, voice) restyled as an animated
torn-paper editorial poster.

Aged paper, the speaker cut out on torn white paper with a grimy print treatment, a black ink smear
breaking into halftone behind them, live ASCII art sampled from the footage, Space Mono editorial
type (title, "REC. STUDY 0X", three-line verse), red barcode ladder as the progress bar, crosshair
registration marks, torn-strip glitches. All text sits inside the Instagram Reels safe area.

    python3 poster.py stills 3.2 20     -> out/stills (half res)
    python3 poster.py render            -> out/system_reel_poster.mp4
"""

import math
import sys

import cv2
import numpy as np
import skia

import edit as E
import kit
import audio_kit as ak
from theme import clamp, e_back, e_in, e_io, e_out, hrand, lerp, prog

W, H, FPS = E.W, E.H, E.FPS
P = E   # phrases live on the edit module (E.HOOK, E.STEPS, ...)

# ================================================================== palette + type
PAPER = np.array([232, 225, 210], np.float32)
WHITE_P = np.array([246, 242, 233], np.float32)
INK = np.array([26, 24, 22], np.float32)
INK_C = "#1A1816"
RED_C = "#D8522E"
PAPER_C = "#F6F2E9"
kit.FONTS["sm"] = "SpaceMono-Regular.ttf"
kit.FONTS["smb"] = "SpaceMono-Bold.ttf"

# safe area for text (Reels UI: top bar, caption block, right icon column)
SX0, SX1, SY0, SY1 = 90, 960, 250, 1490


def col(c, a=1.0):
    return kit.col(c, a)


def fill(c, a=1.0, blur=0):
    return kit.fill(c, a, blur)


def stroke(c, w, a=1.0):
    return kit.stroke(c, w, a, cap="butt")


def mono(c, s, x, y, size, color=INK_C, a=1.0, bold=False, anchor="l", tracking=0.0):
    return kit.text(c, s, x, y, "smb" if bold else "sm", size, color=color, a=a, anchor=anchor, tracking=tracking)


# ================================================================== textures (built once, shared by fork)
def _fbm(h, w, seed, sigmas=(2, 5, 12, 30), amps=(0.35, 0.3, 0.25, 0.3)):
    g = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    for s, a in zip(sigmas, amps):
        n = g.standard_normal((h, w)).astype(np.float32)
        n = cv2.GaussianBlur(n, (0, 0), s)
        out += a * n / (n.std() + 1e-6)
    return out / (out.std() + 1e-6)


def _up(m, interp=cv2.INTER_LINEAR):
    return cv2.resize(m, (W, H), interpolation=interp)


def _make_paper():
    h, w = H // 2, W // 2
    g = np.random.default_rng(21)
    blot = _fbm(h, w, 1, (18, 40, 90), (0.4, 0.35, 0.3))
    fib = cv2.GaussianBlur(g.standard_normal((h, w)).astype(np.float32), (0, 0), sigmaX=7, sigmaY=0.7)
    fib /= fib.std() + 1e-6
    tex = 1 + 0.035 * blot + 0.012 * fib
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    for k in range(4):                                   # coffee-ring stains
        cx, cy, R = g.uniform(0, w), g.uniform(0, h), g.uniform(40, 120)
        r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        tex -= 0.05 * np.exp(-((r - R) / 4) ** 2) + 0.018 * (r < R)
    for k in range(3):                                   # creases
        a, b = g.uniform(0, w), g.uniform(0, w)
        d = (xx - (a + (b - a) * yy / h))
        tex -= 0.05 * np.exp(-(d / 1.2) ** 2)
        tex += 0.025 * np.exp(-((d - 3) / 2.0) ** 2)
    rx, ry = (xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2)
    edge = np.clip(np.maximum(abs(rx), abs(ry)) - 0.72, 0, None)
    tex -= 0.55 * edge ** 1.6 * (1 + 0.5 * blot)
    tex = _up(tex)
    return np.clip(tex, 0.55, 1.1).astype(np.float32)


PAPER_TEX = _make_paper()                                       # (H, W) multiplier
PAPER_RGB = (PAPER_TEX[..., None] * PAPER).astype(np.float32)
_g = np.random.default_rng(5)
GRAIN = [(_g.standard_normal((H // 2, W // 2)).astype(np.float32)) for _ in range(4)]
TORN = [_fbm(H // 2, W // 2, 30 + i, (1.2, 3, 7), (0.45, 0.35, 0.3)) for i in range(3)]
SMEAR = [_fbm(H // 2, W // 2, 40 + i, (6, 16, 40), (0.3, 0.4, 0.4)) for i in range(3)]
DIRT = np.clip(1 - 0.5 * (_up(np.random.default_rng(9).random((H // 4, W // 4)).astype(np.float32),
                              cv2.INTER_NEAREST) > 0.985) - 0.06 * _up(_fbm(H // 2, W // 2, 50, (3, 10), (0.5, 0.5))),
               0.4, 1.1).astype(np.float32)


def _dot_field(cell):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u, v = (xx + yy) / math.sqrt(2), (xx - yy) / math.sqrt(2)
    du, dv = (u % cell) - cell / 2, (v % cell) - cell / 2
    return (np.sqrt(du ** 2 + dv ** 2) / (cell * 0.7071)).astype(np.float32)


DOTS = _dot_field(11)


def halftone(v):
    """coverage (0..1, full res) -> AM halftone dot mask."""
    return (DOTS < np.sqrt(np.clip(v, 0, 1)) * 0.98).astype(np.float32)


def boil(t, n=3, fps=8):
    return int(t * fps) % n


# ================================================================== the print treatment
P_S = 0.88
P_TX = W * (1 - P_S) / 2 + 70
P_TY = H * (1 - P_S) + 30
FACE_P = (P_TX + E.FACE[0] * P_S, P_TY + E.FACE[1] * P_S)
ZLEVELS = [1.0, 1.05, 1.02, 1.08]
_ZP = E.ZOOMS


def zoom(t):
    k = max([i for i, s in enumerate(E.RUN_STARTS) if s <= t + 1e-6] or [0])
    z = ZLEVELS[k % len(ZLEVELS)]
    if _ZP.s - 0.02 <= t < E.TEXT.s:
        z = lerp(z, 1.4, e_out(prog(t, _ZP.s - 0.02, 0.2)))
    if E.FRZ_A <= t < E.FRZ_B:
        z = 1.0 + 0.06 * e_out(prog(t, E.FRZ_A, 0.3))
    if t >= E.CTA_A:
        z = 1.0
    return z


def place_matrix(t, extra=1.0):
    z = zoom(t) * extra
    fx, fy = FACE_P
    s = P_S * z
    tx = fx + (P_TX - fx) * z
    ty = fy + (P_TY - fy) * z
    return np.array([[s, 0, tx], [0, s, ty]], np.float32)


def treat(rgb):
    """muted, contrasty, grimy print look."""
    f = rgb.astype(np.float32)
    lum = f @ np.array([0.299, 0.587, 0.114], np.float32)
    f = lum[..., None] + (f - lum[..., None]) * 0.7
    f = (f - 128) * 1.14 + 124
    f *= np.array([1.03, 1.0, 0.93], np.float32)
    return f


def compose_person(t, src, base, bg_noise_k=0):
    """paper base (H,W,3 float) -> + ink smear/halftone, torn white backing, treated person."""
    M = place_matrix(t)
    rgb = cv2.warpAffine(src.rgb, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    al = cv2.warpAffine(src.alpha, M, (W, H), flags=cv2.INTER_LINEAR).astype(np.float32) / 255
    a_s = cv2.resize(al, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    b = boil(t)
    # ink smear around the figure, heavier low down, breaking up into halftone dots
    near = cv2.GaussianBlur(cv2.dilate((a_s > 0.5).astype(np.float32), np.ones((81, 81), np.uint8)), (0, 0), 26)
    yy = np.linspace(0, 1, H // 2, dtype=np.float32)[:, None]
    low = np.clip((yy - 0.38) / 0.3, 0, 1)
    v = near * (0.42 + 0.35 * low + 0.75 * np.clip(SMEAR[b], -2.5, 2.5)) - 0.4 + bg_noise_k * near
    ink = _up(np.clip(v * 5, 0, 1))
    dots = halftone(_up(np.clip((v + 0.4) / 0.4, 0, 1) ** 1.3 * (v < 0)) * 0.95)
    cover = np.maximum(ink, dots)[..., None]
    out = base * (1 - cover) + INK * cover
    # torn white backing paper
    torn = cv2.GaussianBlur(cv2.dilate((a_s > 0.4).astype(np.float32), np.ones((15, 15), np.uint8)), (0, 0), 1.6)
    tm = _up(((torn + TORN[b] * 0.33 * (torn > 0.05)) > 0.55).astype(np.float32))
    sh = np.roll(np.roll(tm, 7, 0), 5, 1)
    out *= (1 - 0.35 * sh * (1 - tm))[..., None]
    out = out * (1 - tm[..., None]) + (WHITE_P * PAPER_TEX[..., None] ** 0.5) * tm[..., None]
    # the person, printed: muted + paper texture + dirt
    pr = treat(rgb) * (PAPER_TEX ** 0.8 * DIRT)[..., None]
    a3 = al[..., None]
    out = out * (1 - a3) + pr * a3
    return out, al


# ================================================================== ASCII art from the live footage
RAMP = " .:-=+*#%@"
AC_W, AC_H, AC_SIZE = 12, 21, 19.5
A_COLS, A_ROWS = W // AC_W, H // AC_H
REGIONS = [(600, 250, 1010, 860), (170, 860, 470, 1460), (880, 880, 1060, 1340)]


def ascii_grid(src_rgb):
    small = cv2.resize(src_rgb, (A_COLS, A_ROWS), interpolation=cv2.INTER_AREA).astype(np.float32)
    lum = small @ np.array([0.299, 0.587, 0.114], np.float32) / 255
    lum = ((lum - lum.min()) / (np.ptp(lum) + 1e-6)) ** 1.8
    return np.clip(((1 - lum) * (len(RAMP) - 1)).round(), 0, len(RAMP) - 1).astype(int)


_AMASK = {}


def ascii_mask(t, full=False):
    if full:
        return np.ones((A_ROWS, A_COLS), bool)
    b = int(t * 2.5) % 4
    if b not in _AMASK:
        n = _fbm(A_ROWS, A_COLS, 70 + b, (1.0, 2.5), (0.5, 0.5))
        m = np.zeros((A_ROWS, A_COLS), bool)
        for x0, y0, x1, y1 in REGIONS:
            m[y0 // AC_H:y1 // AC_H, x0 // AC_W:x1 // AC_W] = True
        _AMASK[b] = m & (n > -0.15)
    return _AMASK[b]


def draw_ascii(c, t, src_rgb, full=False, color=INK_C, a=0.85, bars=None):
    idx = ascii_grid(src_rgb)
    m = ascii_mask(t, full)
    f = kit.font("sm", AC_SIZE)
    p = fill(color, a)
    for r in range(A_ROWS):
        row = "".join(RAMP[idx[r, cc]] if m[r, cc] else " " for cc in range(A_COLS))
        if row.strip():
            c.drawString(row, 0, (r + 1) * AC_H - 4, f, p)


# ================================================================== sections: title, label, verse
def _secs():
    S = E
    return [
        (0.0, "AI EDITED", "THIS VIDEO", "REC. TAKE 01",
         [("I didn't edit it.", S.DIDNT.s), ("My system did.", S.SYSDID.s), ("Same take, no app.", S.SAME.s)]),
        (S.BUILT.s - 0.1, "MY OWN", "SYSTEM", "REC. STUDY 00",
         [("Built for my videos.", S.BUILT.w(5)), ("Four simple steps.", S.FOUR.w(3)), ("", 99)]),
        (S.STEPS[0].s - 0.06, "STEP 01", "RECORD", "REC. STUDY 01",
         [("One take.", S.ONETAKE.w(1)), ("Mistakes allowed.", S.MOK1.s), ("Nothing reshot.", S.MOK2.s)]),
        (S.STEPS[1].s - 0.06, "STEP 02", "TELL IT", "REC. STUDY 02",
         [("> make it short", S.SHORT.w(1)), ("> add big text", S.BIG.s), ("> add music", S.MUSIC.s)]),
        (S.STEPS[2].s - 0.06, "STEP 03", "IT EDITS", "REC. STUDY 03",
         [("[x] cuts the pauses", S.CUTS.s), ("[x] zooms in", S.ZOOMS.s), ("[x] text + music", S.TEXT.s)]),
        (S.STEPS[3].s - 0.06, "STEP 04", "CHECK", "REC. STUDY 04",
         [("I check it.", S.CHECK.s), ("> make it pop more", S.SAYIT.w(2)), ("Ready anywhere.", S.READY.s)]),
        (S.GRID_A, "EVERY", "VIDEO", "CONTACT SHEET",
         [("This whole video.", S.MADE.w(2)), ("Every video", S.EVERY.s), ("on my page.", S.EVERY.w(3))]),
        (S.CTA_A, "COMMENT", "\"SYSTEM\"", "REC. END",
         [("Want to see how", S.WANT.s), ("my system works?", S.WANT.w(3)), ("I'll send the details.", S.SEND.s)]),
    ]


SECS = _secs()
TITLE_X, TITLE_Y = SX0, 330


def section(t):
    cur = SECS[0]
    for s in SECS:
        if t >= s[0]:
            cur = s
    return cur


def typed(s, t, t0, cps=26):
    n = int(clamp((t - t0) * cps, 0, len(s)))
    return s[:n], n < len(s)


def draw_title_block(c, t, dark=False, short=False):
    t0, t1, t2, lab, verse = section(t)
    if short:
        lab, verse = "", []
    colr = PAPER_C if dark else INK_C
    big = 86
    s1, _ = typed(t1, t, t0, 30)
    s2, cur2 = typed(t2, t, t0 + len(t1) / 30, 30)
    mono(c, s1, TITLE_X, TITLE_Y, big, colr, bold=True, tracking=0.01)
    mono(c, s2, TITLE_X, TITLE_Y + 96, big, colr, bold=True, tracking=0.01)
    if cur2 and int(t * 6) % 2 == 0:
        x2 = TITLE_X + kit.measure(s2, "smb", big, 0.01)
        c.drawRect(skia.Rect.MakeXYWH(x2 + 6, TITLE_Y + 96 - 62, 38, 70), fill(RED_C))
    c.drawRect(skia.Rect.MakeXYWH(TITLE_X, TITLE_Y + 148, 40, 7), fill(colr))
    # label + dashed rule
    ly = TITLE_Y + 262
    mono(c, lab, TITLE_X, ly, 32, colr, bold=True, tracking=0.06)
    for i in range(14):
        c.drawRect(skia.Rect.MakeXYWH(TITLE_X + i * 22, ly + 20, 13, 3), fill(colr))
    # verse
    for j, (line, tl) in enumerate(verse):
        s, cur = typed(line, t, tl, 34)
        if not s:
            continue
        y = ly + 86 + j * 50
        lc = RED_C if line.startswith(("[x]", ">")) and not cur and t - tl < 0.6 else colr
        mono(c, s, TITLE_X, y, 34, lc, tracking=0.0)
        if cur:
            xx = TITLE_X + kit.measure(s, "sm", 34)
            c.drawRect(skia.Rect.MakeXYWH(xx + 3, y - 27, 18, 34), fill(RED_C))


def crosshair(c, x, y, r=26, a=1.0, rot=0.0, color=INK_C):
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    p = stroke(color, 3, a)
    c.drawCircle(0, 0, r * 0.62, p)
    c.drawLine(-r, 0, r, 0, p)
    c.drawLine(0, -r, 0, r, p)
    c.restore()


def red_ladder(c, t, x=SX0 + 4, y0=1010, y1=1450, w=40):
    n = int((y1 - y0) / 9)
    k = clamp(t / E.TOTAL)
    for i in range(n):
        y = y1 - i * 9
        on = i / n < k
        c.drawRect(skia.Rect.MakeXYWH(x, y - 5, w, 5), fill(RED_C, 1.0 if on else 0.22))
    c.drawRect(skia.Rect.MakeXYWH(x - 2, y0 - 6, w + 4, y1 - y0 + 8), stroke(RED_C, 2, 0.5))


def torn_tape_path(x, y, w, h, seed):
    p = skia.Path()
    n = 9
    p.moveTo(x, y)
    p.lineTo(x + w, y)
    for i in range(n + 1):
        p.lineTo(x + w + (hrand(seed, i) - 0.5) * 14, y + h * i / n)
    p.lineTo(x, y + h)
    for i in range(n, -1, -1):
        p.lineTo(x + (hrand(seed, i, 2) - 0.5) * 14, y + h * i / n)
    p.close()
    return p


def caption(c, t, red=RED_C):
    """typewriter caption on a torn paper strip; spoken word in red."""
    if E.in_any(t, [(E.REW_A, E.REW_B), (E.FRZ_A, E.FRZ_B), (E.COMMENT.s - 0.05, E.TOTAL)]):
        return
    g = None
    for k, grp in enumerate(E.CAPS):
        nxt = E.CAPS[k + 1][0]["os"] if k + 1 < len(E.CAPS) else grp[-1]["oe"] + 0.4
        if grp[0]["os"] - 0.04 <= t < min(nxt - 0.02, grp[-1]["oe"] + 0.45):
            g = grp
    if not g:
        return
    size = 56 if t < E.SAYIT.e else 62
    words = [E.cap_text(w) for w in g]
    full = " ".join(words)
    tw = kit.measure(full, "smb", size)
    w = tw + 70
    x = (SX0 + SX1) / 2 - w / 2 + 40
    y = 1352
    c.save()
    c.translate(x + w / 2, y + 40)
    c.rotate(-1.2 + 2.4 * (hrand(g[0]["i"]) - 0.5))
    c.translate(-(x + w / 2), -(y + 40))
    path = torn_tape_path(x, y, w, 84, g[0]["i"])
    c.save()
    c.translate(5, 7)
    c.drawPath(path, fill("#000000", 0.25, blur=6))
    c.restore()
    c.drawPath(path, fill(PAPER_C))
    xx = x + 35
    for j, (wd, s) in enumerate(zip(g, words)):
        if t < wd["os"] - 0.04:
            break
        cur = wd["os"] - 0.04 <= t < wd["oe"] + 0.04 or (j == len(g) - 1 and t >= wd["os"])
        mono(c, s, xx, y + 58, size, red if cur else INK_C, bold=True)
        xx += kit.measure(s + " ", "smb", size)
    c.restore()


def marker_check(c, x, y, s, k, color=RED_C, w=12):
    if k <= 0:
        return
    p = skia.Path()
    p.moveTo(x - 0.5 * s, y)
    p.lineTo(x - 0.15 * s, y + 0.38 * s)
    p.lineTo(x + 0.6 * s, y - 0.55 * s)
    pt = kit.stroke(color, w)
    if k < 1:
        pt.setPathEffect(skia.TrimPathEffect.Make(0, clamp(k)))
    c.drawPath(p, pt)


def outline_num(c, s, x, y, size, a=1.0, color=INK_C):
    f = kit.font("smb", size)
    w = f.measureText(s)
    c.drawString(s, x - w / 2, y, f, stroke(color, 3, a))


# ================================================================== torn prints (split screen, contact sheet)
def print_card(c, img, x, y, w, h, rot, seed, border=14, tape=True):
    c.save()
    c.translate(x + w / 2, y + h / 2)
    c.rotate(rot)
    c.translate(-w / 2, -h / 2)
    outer = skia.Path()
    n = 14
    pts = []
    for i in range(n):
        pts.append((-border + (w + 2 * border) * i / n, -border + (hrand(seed, i) - 0.5) * 10))
    for i in range(n):
        pts.append((w + border + (hrand(seed, i, 1) - 0.5) * 10, -border + (h + 2 * border) * i / n))
    for i in range(n):
        pts.append((w + border - (w + 2 * border) * i / n, h + border + (hrand(seed, i, 2) - 0.5) * 10))
    for i in range(n):
        pts.append((-border + (hrand(seed, i, 3) - 0.5) * 10, h + border - (h + 2 * border) * i / n))
    outer.moveTo(*pts[0])
    for p_ in pts[1:]:
        outer.lineTo(*p_)
    outer.close()
    c.drawPath(outer, fill("#000000", 0.3, blur=12))
    c.drawPath(outer, fill(PAPER_C))
    c.drawImageRect(img, skia.Rect.MakeXYWH(0, 0, w, h), E.SAMP)
    if tape:
        for tx in (w * 0.18, w * 0.82):
            c.save()
            c.translate(tx, -border)
            c.rotate((hrand(seed, tx) - 0.5) * 16)
            c.drawRect(skia.Rect.MakeXYWH(-46, -18, 92, 36), fill("#E9E1C8", 0.85))
            c.restore()
    c.restore()


def np_img(arr):
    a = np.clip(arr, 0, 255).astype(np.uint8)
    return skia.Image.fromarray(np.dstack([a, np.full(a.shape[:2], 255, np.uint8)]), colorType=skia.kRGBA_8888_ColorType)


def mini_print(src_rgb, w, h, raw=False):
    small = cv2.resize(src_rgb, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32)
    if raw:
        return np_img(small)
    pt = cv2.resize(PAPER_TEX, (w, h))
    return np_img(treat(small) * (pt ** 0.8)[..., None])


def draw_split(c, t, src_ts):
    raw = E.Src(src_ts, graded=False)
    ed = E.Src(src_ts)
    c.drawImage(np_img(PAPER_RGB), 0, 0)
    ka = e_out(prog(t, E.SPLIT_A, 0.35))
    kb = e_in(prog(t, E.SPLIT_B - 0.3, 0.3))
    pw, ph = 384, 682
    y = 560
    lx = lerp(-500, 110, ka) - kb * 700
    rx = lerp(1200, 560, ka) + kb * 700
    print_card(c, mini_print(raw.rgb, pw, ph, raw=True), lx, y, pw, ph, -3, 11)
    print_card(c, mini_print(ed.rgb, pw, ph), rx, y + 20, pw, ph, 2.5, 12)
    if kb == 0:
        mono(c, "FIG. A  from my phone", lx + 4, y + ph + 50, 24, bold=True, a=ka)
        mono(c, "FIG. B  what you see", rx + 4, y + ph + 70, 24, bold=True, a=ka)
        if t >= E.SAME.s:
            k = prog(t, E.SAME.s, 0.2)
            for dy in (-14, 14):
                c.drawRect(skia.Rect.MakeXYWH(510, y + ph / 2 + dy - 4, 44 * k, 8), fill(RED_C))
        if t >= E.NOAPP.s:
            k = e_back(prog(t, E.NOAPP.s, 0.3))
            c.save()
            c.translate(720, 470)
            c.rotate(-4)
            c.scale(k, k)
            mono(c, "[ NO EDITING APP ]", 0, 0, 30, RED_C, bold=True, anchor="c")
            c.drawRect(skia.Rect.MakeXYWH(-170, -12, 340 * clamp((t - E.NOAPP.w(2)) * 4), 4), fill(RED_C))
            c.restore()


def draw_grid(c, t, src_ts):
    c.drawImage(np_img(PAPER_RGB), 0, 0)
    k_in = e_io(prog(t, E.GRID_A, 0.6))
    k_more = e_io(prog(t, E.EVERY.s - 0.05, 0.6))
    k_out = e_in(prog(t, E.GRID_B - 0.3, 0.3))
    z = lerp(lerp(1.0, 0.42, k_in), 0.27, k_more)
    z = lerp(z, 1.0, k_out)
    looks = [2.0, 14.6, 18.4, 32.6, None, 41.8, 43.5, 10.5, 55.3]
    gap = 120
    c.save()
    c.translate(W / 2, H / 2 + 60 * k_in * (1 - k_out))
    c.scale(z, z)
    c.translate(-W / 2, -H / 2)
    for j in range(9):
        r, cc = divmod(j, 3)
        x = (cc - 1) * (W + gap)
        y = (r - 1) * (H + gap)
        if j != 4 and z > 0.97:
            continue
        ts = src_ts if j == 4 else looks[j] + ((t - E.GRID_A) % 2.0)
        s = E.Src(ts)
        img = mini_print(s.rgb, W // 3, H // 3)
        print_card(c, img, x, y, W, H, [-2, 1.5, -1, 2, 0, -2.5, 1, -1.5, 2][j] * (1 - k_out), 40 + j, border=40,
                   tape=False)
        mono(c, f"{j + 1:02d}A", x + 10, y + H + 120, 90, bold=True, a=k_in)
        if t >= E.EVERY.w(1) and j != 4:
            marker_check(c, x + W - 160, y + 180, 220, prog(t, E.EVERY.w(1) + j * 0.04, 0.25), w=40)
    c.restore()
    if k_in > 0.95 and k_out == 0:
        cw, ch = W * z, H * z
        x0, y0 = W / 2 - cw / 2, H / 2 + 60 - ch / 2
        k = prog(t, E.MADE.w(3), 0.4)
        p = kit.stroke(RED_C, 8)
        if k < 1:
            p.setPathEffect(skia.TrimPathEffect.Make(0, k))
        c.drawOval(skia.Rect.MakeXYWH(x0 - 40, y0 - 40, cw + 80, ch + 80), p)


# ================================================================== frame
def draw(c, t, f):
    g = {}
    src_ts, kind = E.src_at(t)
    if E.SPLIT_A <= t < E.SPLIT_B:
        draw_split(c, t, src_ts)
        overlays(c, t, g)
        return g
    if E.GRID_A <= t < E.GRID_B:
        draw_grid(c, t, src_ts)
        overlays(c, t, g)
        return g
    src = E.Src(src_ts)
    # behind layer: ASCII field, outline numerals, big type
    beh = skia.Surface(W, H)
    with beh as bc:
        bc.clear(skia.ColorTRANSPARENT)
        rew = E.REW_A <= t < E.REW_B
        frz = E.FRZ_A <= t < E.FRZ_B
        draw_ascii(bc, t, src.rgb, full=frz, a=0.92 if not frz else 0.6)
        behind_type(bc, t)
    barr = beh.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType).astype(np.float32)
    ba = barr[..., 3:4] / 255
    base = PAPER_RGB * (1 - ba) + barr[..., :3] * ba
    out, al = compose_person(t, src, base, bg_noise_k=0.25 if frz else 0.0)
    if rew:                                               # the take dissolves into ASCII while it rewinds
        out = PAPER_RGB.copy()
    c.drawImage(np_img(out), 0, 0)
    if rew:
        draw_ascii(c, t, src.rgb, full=True, color=INK_C, a=1.0)
    overlays(c, t, g)
    # looks
    if E.SORRY.s <= t < E.SORRY.s + 0.3:
        g["tear"] = 1 - (t - E.SORRY.s) / 0.3
    if E.FRZ_A <= t < E.FRZ_A + 0.5:
        g["tear"] = 1 - (t - E.FRZ_A) / 0.5
        g["flash"] = 0.7 * max(0, 1 - (t - E.FRZ_A) / 0.12)
    for st in [E.chapter_iv(n)[0] for n in range(4)] + [E.SYSDID.w(1), E.BIG.w(1), E.CTA_A]:
        if st <= t < st + 0.16:
            g["tear"] = max(g.get("tear", 0), 0.6 * (1 - (t - st) / 0.16))
    if t < 0.15:
        g["flash"] = 1 - t / 0.15
    return g


def behind_type(c, t):
    for n in range(4):
        a, b = E.chapter_iv(n)
        end = E.STEP_ENDS[n] if n < 3 else E.READY.e
        if a <= t < end and not (E.BIG.w(1) - 0.05 <= t < E.BIG.e + 0.4):
            k = e_out(prog(t, a, 0.4))
            outline_num(c, f"0{n + 1}", 700, 1180, 760, a=0.9 * k * (1 - prog(t, end - 0.3, 0.3)))
    if E.FOUR.w(3) - 0.05 <= t < E.STEPS[0].s:
        outline_num(c, "4", 720, 1250, 1100, a=e_out(prog(t, E.FOUR.w(3) - 0.05, 0.3)))
    if E.BIG.w(1) - 0.05 <= t < E.BIG.e + 0.4:
        k = e_back(prog(t, E.BIG.w(1) - 0.05, 0.3))
        c.save()
        c.translate(700, 880)
        c.scale(k, k)
        f = kit.font("smb", 300)
        for s, yy in (("BIG", 0), ("TEXT", 300)):
            c.drawString(s, -f.measureText(s) / 2, yy, f, fill(INK_C))
        c.restore()
    if E.FRZ_A <= t < E.FRZ_B:
        f = kit.font("smb", 250)
        for s, yy in (("EVEN", 820), ("THIS.", 1080)):
            k = e_out(prog(t, E.FRZ_A + (0 if s == "EVEN" else 0.12), 0.25))
            c.drawString(s, 600 - f.measureText(s) / 2 + (1 - k) * 300, yy, f, fill(RED_C, k))
    if E.MUSIC.w(1) <= t < E.STEPS[2].s:              # ASCII-bar equaliser
        beat = 60 / 124
        for i in range(18):
            ph = ((t - E.MUSIC.w(1)) % beat) / beat
            hgt = int((4 + 12 * hrand("eq", i, int((t - E.MUSIC.w(1)) / (beat / 2)))) * (0.55 + 0.45 * (1 - ph) ** 2))
            for j in range(hgt):
                c.drawRect(skia.Rect.MakeXYWH(610 + i * 22, 836 - j * 30, 16, 24),
                           fill(RED_C if j > hgt - 3 else INK_C, 0.9))
    if t >= E.CTA_A:
        f = kit.font("smb", 150)
        for r in range(6):
            off = ((t * 120 * (1 if r % 2 else -1)) + r * 90) % 800
            c.drawString("SYSTEM SYSTEM SYSTEM", -off, 960 + r * 150, f, stroke(INK_C, 2.5, 0.8))


def overlays(c, t, g):
    split = E.SPLIT_A <= t < E.SPLIT_B
    if E.GRID_A <= t < E.GRID_B:          # paper card so the title reads over the contact sheet
        path = torn_tape_path(SX0 - 30, SY0 - 10, 600, 600, 91)
        c.drawPath(path, fill("#000000", 0.25, blur=10))
        c.drawPath(path, fill(PAPER_C))
    draw_title_block(c, t, short=split)
    crosshair(c, SX1 - 30, SY0 + 40, rot=t * 20)
    crosshair(c, SX0 + 26, SY1 - 20, rot=-t * 20)
    red_ladder(c, t)
    # step 1: recording tag + the stumble
    if E.REC.s - 0.05 <= t < E.MOK1.e + 0.2:
        if int(t * 2.5) % 2 == 0:
            c.drawCircle(SX1 - 200, SY0 + 120, 11, fill(RED_C))
        mono(c, "REC  00:00:%02d" % int(t - E.REC.s + 12), SX1 - 180, SY0 + 131, 28, RED_C, bold=True)
    if E.SORRY.s <= t < E.REW_A:
        k = e_back(prog(t, E.SORRY.s, 0.25))
        c.save()
        c.translate(SX1 - 190, SY0 + 160)
        c.rotate(-5)
        c.scale(k, k)
        mono(c, "ERR. TAKE 01", 0, 0, 34, RED_C, bold=True, anchor="c")
        c.drawRect(skia.Rect.MakeXYWH(-130, 12, 260, 4), fill(RED_C))
        c.restore()
    if E.REW_A <= t < E.REW_B:
        mono(c, "<< REWIND", SX1, SY0 + 140, 40, RED_C, bold=True, anchor="r")
        mono(c, "cutting the mistake", SX1, SY0 + 184, 26, INK_C, anchor="r")
    if E.MOK2.w(2) <= t < E.STEPS[1].s:
        marker_check(c, SX1 - 120, SY0 + 170, 120, prog(t, E.MOK2.w(2), 0.25))
    # step 3: crosshair lock on "zooms in"
    if E.ZOOMS.s - 0.05 <= t < E.TEXT.s + 0.2:
        k = e_io(prog(t, E.ZOOMS.s - 0.05, 0.35))
        fx, fy = FACE_P[0], FACE_P[1] - 70
        x, y = lerp(SX1 - 30, fx, k), lerp(SY0 + 40, fy, k)
        crosshair(c, x, y, r=lerp(26, 120, k), rot=k * 90, color=RED_C)
        if k >= 1:
            mono(c, "LOCK", x + 130, y - 90, 26, RED_C, bold=True)
    if E.TEXT.s <= t < E.THEMUSIC.s + 0.2:
        for j, s in enumerate(["TYPE", "TEXT", "WORDS", "BOLD"]):
            st = E.TEXT.s + j * 0.08
            if t >= st:
                x = [620, 820, 650, 840][j]
                y = [520, 600, 700, 760][j]
                mono(c, f"[{s}]", x, y, 32, RED_C if j % 2 else INK_C, bold=True, a=clamp((t - st) * 8))
    # step 4
    if E.CHECK.w(1) <= t < E.CHANGE.s + 0.3:
        marker_check(c, SX1 - 130, SY0 + 170, 150, prog(t, E.CHECK.w(1), 0.3))
    if E.READY.w(4) - 0.05 <= t < E.GRID_A:
        for j, (s, ts) in enumerate((("-> INSTAGRAM", E.READY.w(4)), ("-> YOUTUBE", E.READY.w(5)),
                                      ("-> ANYWHERE", E.READY.w(6)))):
            if t >= ts:
                mono(c, s, SX1, SY0 + 140 + j * 46, 30, RED_C if j == 2 else INK_C, bold=True, anchor="r",
                     a=clamp((t - ts) * 8))
        k = prog(t, E.READY.s, E.READY.w(6) - E.READY.s + 0.3)
        bar = "#" * int(14 * e_io(k))
        mono(c, f"[{bar:<14}] {int(100 * e_io(k)):3d}%", SX1, SY0 + 300, 26, INK_C, anchor="r")
    # CTA comment input on the tape
    if t >= E.COMMENT.s - 0.05:
        k = e_back(prog(t, E.COMMENT.s - 0.05, 0.3))
        typed_s = "SYSTEM"[:int(clamp((t - E.COMMENT.w(1)) / 0.35) * 6)]
        sent = t >= E.COMMENT.e + 0.08
        w = 640
        x, y = (SX0 + SX1) / 2 - w / 2 + 40, 1352
        c.save()
        c.translate(x + w / 2, y + 42)
        c.scale(k, k)
        c.rotate(-1.2)
        c.translate(-(x + w / 2), -(y + 42))
        path = torn_tape_path(x, y, w, 88, 77)
        c.drawPath(path, fill("#000000", 0.25, blur=6))
        c.drawPath(path, fill(PAPER_C))
        mono(c, "> " + (typed_s if not sent else "SYSTEM"), x + 34, y + 62, 56, INK_C, bold=True)
        if not sent and int(t * 6) % 2 == 0:
            xx = x + 34 + kit.measure("> " + typed_s, "smb", 56)
            c.drawRect(skia.Rect.MakeXYWH(xx + 4, y + 18, 30, 52), fill(RED_C))
        if sent:
            mono(c, "SENT", x + w - 40, y + 60, 34, RED_C, bold=True, anchor="r")
        c.restore()
        if t >= E.SEND.e + 0.1:
            marker_check(c, SX1 - 110, 1250, 140, prog(t, E.SEND.e + 0.1, 0.3))
    caption(c, t)


# ================================================================== post
_TEAR = {}


def _tear_mask(seed):
    if seed not in _TEAR:
        g = np.random.default_rng(seed)
        xs = np.sort(g.uniform(80, W - 80, 6)).astype(int)
        offs = g.integers(-140, 140, len(xs) + 1)
        yy = np.arange(H)
        band = np.zeros((H, W), np.float32)
        for b in xs:
            jit = (np.sin(yy * 0.05 + b) * 4 + g.standard_normal(H).cumsum() * 0.3).astype(int)
            wid = (4 + 3 * np.abs(np.sin(yy * 0.13 + b))).astype(int)
            for y in range(0, H, 2):
                x0 = int(clamp(b + jit[y] - wid[y], 0, W - 1))
                x1 = int(clamp(b + jit[y] + wid[y], 0, W - 1))
                band[y:y + 2, x0:x1] = 1
        _TEAR[seed] = (xs, offs, band)
    return _TEAR[seed]


def post(rgb, g, f):
    out = rgb.astype(np.float32)
    s = rgb.shape[1] / W
    if g.get("tear", 0) > 0.02:
        xs, offs, band = _tear_mask(f // 6)
        k = g["tear"]
        edges = [0] + [int(x * s) for x in xs] + [rgb.shape[1]]
        for i in range(len(edges) - 1):
            out[:, edges[i]:edges[i + 1]] = np.roll(out[:, edges[i]:edges[i + 1]], int(offs[i] * k * s), axis=0)
        bm = cv2.resize(band, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_NEAREST)[..., None]
        out = out * (1 - bm) + WHITE_P * bm
    if g.get("flash"):
        out = out + (WHITE_P - out) * g["flash"]
    gr = cv2.resize(GRAIN[(f // 2) % 4], (rgb.shape[1], rgb.shape[0]))
    out += gr[..., None] * 7
    return np.clip(out, 0, 255).astype(np.uint8)


FILM = kit.Film(draw, E.TOTAL, FPS, post=post, out_dir=E.OUT)


# ================================================================== audio
def tear_sfx(dur=0.32, seed=0):
    g = np.random.default_rng(seed)
    n = int(dur * ak.SR)
    x = g.standard_normal(n).astype(np.float32)
    x = ak.filt(ak.filt(x, "hp", 900), "lp", 6000)
    crackle = (g.random(n) > 0.985).astype(np.float32)
    crackle = np.convolve(crackle, np.ones(120) / 40, "same")
    env = np.minimum(1, np.linspace(0, 6, n)) * np.exp(-np.linspace(0, 4, n))
    return (x * (0.35 + crackle) * env * 0.6).astype(np.float32)


def sfx_list():
    S = []

    def a(t, kind=None, gain=-10, **kw):
        S.append(dict(t=t, kind=kind, gain_db=gain, **kw))

    a(0.0, "shutter", -8)
    for s in SECS[1:]:
        a(s[0], "typing", -16, dur=0.45)
    a(0.02, "typing", -16, dur=0.5)
    a(E.SYSDID.w(1), clip=tear_sfx(seed=1), gain=-6)
    a(E.SPLIT_A, "whoosh", -12)
    a(E.SAME.s, "click", -10)
    a(E.NOAPP.s, "pop", -14)
    a(E.SPLIT_B - 0.3, "whoosh", -12)
    for n in range(4):
        a(E.chapter_iv(n)[0], clip=tear_sfx(seed=10 + n), gain=-8)
    a(E.REC.s, "shutter", -10)
    a(E.SORRY.s, "glitch", -7)
    a(E.SORRY.s + 0.02, clip=tear_sfx(seed=3), gain=-6)
    a(E.REW_A, "downlifter", -9)
    a(E.REW_B - 0.05, "click", -6)
    a(E.MOK2.w(2), "tick", -10)
    for P_, w0 in ((E.SHORT, 1), (E.BIG, 0), (E.MUSIC, 0)):
        a(P_.w(w0), "typing", -15, dur=max(0.3, P_.e - P_.w(w0)))
    a(E.BIG.w(1), "impact", -10)
    a(E.MUSIC.w(1), "bass_drop", -6)
    for tk in (E.CUTS.s, E.ZOOMS.s, E.TEXT.s):
        a(tk, "tick", -10)
    a(E.ZOOMS.s, "shutter", -12)
    a(E.EVEN.s - 0.6, "riser", -11, dur=0.6 + E.FRZ_A - E.EVEN.s)
    a(E.FRZ_A, "impact", -6)
    a(E.FRZ_A, clip=tear_sfx(0.45, seed=7), gain=-4)
    a(E.FRZ_B - 0.08, "whoosh", -11)
    a(E.CHECK.w(1), "tick", -9)
    a(E.SAYIT.w(2), "typing", -15, dur=0.4)
    for j in range(3):
        a(E.READY.w(4 + j), "click", -12)
    a(E.GRID_A, "whoosh", -10)
    a(E.EVERY.w(1), "shutter", -12)
    a(E.GRID_B - 0.3, "whoosh", -10)
    a(E.CTA_A, clip=tear_sfx(seed=9), gain=-7)
    a(E.COMMENT.w(1), "typing", -13, dur=0.35)
    a(E.COMMENT.e + 0.08, "click", -7)
    a(E.SEND.e + 0.1, "tick", -9)
    return S


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "stills":
        FILM.stills([float(x) for x in sys.argv[2:]])
    elif cmd == "audio":
        E.build_audio(sfx_list(), mood="tech", name="mix_poster.wav", seed=5)
    else:
        pic = FILM.render(E.OUT / "poster_picture.mp4")
        aud = E.build_audio(sfx_list(), mood="tech", name="mix_poster.wav", seed=5)
        E.finish(pic, aud, E.OUT / "system_reel_poster.mp4")
