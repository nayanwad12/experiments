"""ADEX OOH Creative Challenge: the full edit of the raw Hinglish take (1080x1920, 30 fps).

    python3 edit.py info                  cut list + output length
    python3 edit.py stills 1.0 4.2 ...    -> out/stills/*.png  (half res)
    python3 edit.py sheet                 -> out/sheet.png
    python3 edit.py audio                 -> work/mix.wav
    python3 edit.py render [--draft]      -> out/adex_ooh_edit.mp4

Look: minimal. The footage carries the piece; captions are white InterTight Black with the spoken word lit
neon green, keywords in neon (sans) or neon serif italic, and a few word-locked caption gags (a sagging
"boring", struck-through "billboard"/"certificate", requirement pills, giant type behind the speaker,
a register button). Dead air between phrases is cut; shots change with a zoom-whip.
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
import audio_kit as ak  # noqa: E402
import kit  # noqa: E402
from kit import W, H, clamp, col, e_back, e_in, e_io, e_out, fill, font, hrand, lerp, measure, rrect, spring  # noqa: E402
from vibelib import ff, loudnorm_filter  # noqa: E402

FPS = 30
OUT = HERE / "out"
FR = HERE / "work" / "frames"
NSRC = len(list(FR.glob("f_*.jpg")))

WHITE = "#FFFFFF"
NEON = "#39FF14"
INK = "#08090A"

# ================================================================== words + cut list
WORDS = json.loads((HERE / "work" / "words.json").read_text())
SHOTS = [0.0, 8.983, 13.45, 26.933, 34.0, 42.6, 48.85]   # hard cuts in the raw take (frame differencing)
GAP = 0.2                 # pauses longer than this are cut
HOLD_AFTER = {32: 0.45}   # keep the man's reaction after "Yeh kya?"
TAIL_END = 48.45          # hold the group shot for the register button


def shot_of(ts):
    return max(i for i, s in enumerate(SHOTS[:-1]) if s <= ts + 1e-6)


def build_edl():
    """[(src_a, src_b, out_a)] play segments, dead air removed."""
    runs = []
    for i, w in enumerate(WORDS):
        if runs and w["s"] - runs[-1][1] < GAP and shot_of(w["s"]) == shot_of(runs[-1][1] - 0.01):
            runs[-1][1], runs[-1][3] = w["e"], i
        else:
            runs.append([w["s"], w["e"], i, i])
    edl, t = [], 0.0
    for k, (a, b, i0, i1) in enumerate(runs):
        prev_e = runs[k - 1][1] if k else 0.0
        a = max(a - 0.08, (prev_e + a) / 2, SHOTS[shot_of(a)])
        if k + 1 == len(runs):
            b = TAIL_END
        else:
            nxt = runs[k + 1][0]
            b = min(b + 0.12 + HOLD_AFTER.get(i1, 0), (b + nxt) / 2, SHOTS[shot_of(b - 0.02) + 1])
        edl.append((a, b, t))
        t += b - a
    return edl, t


EDL, TOTAL = build_edl()


def seg_at(t):
    for k, (a, b, o) in enumerate(EDL):
        if t < o + (b - a):
            return k
    return len(EDL) - 1


def src_at(t):
    a, b, o = EDL[seg_at(t)]
    return min(a + (t - o), b - 1e-3)


def out_of(ts):
    for a, b, o in EDL:
        if a - 1e-6 <= ts <= b + 1e-6:
            return o + ts - a
    a, b, o = min(EDL, key=lambda s: min(abs(ts - s[0]), abs(ts - s[1])))
    return o + clamp(ts - a, 0, b - a)


for w in WORDS:
    w["os"], w["oe"] = out_of(w["s"]), out_of(w["e"])
    w["k"] = re.sub(r"[^a-z0-9]", "", w["w"].lower())

# output times where the shot changes (zoom-whip transitions)
TRANS = [o for k, (a, b, o) in enumerate(EDL) if k and shot_of(a) != shot_of(EDL[k - 1][0])]


# ================================================================== footage
_cache = {}


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
    x = np.arange(256, dtype=np.float32) / 255
    s = x + 0.05 * np.sin(2 * math.pi * (x - 0.5))          # gentle S-curve
    s = np.clip((s - 0.012) / 0.985, 0, 1)
    return (s * 255).astype(np.uint8)


LUT = _lut()


def grade(rgb, sat=1.1):
    f = cv2.LUT(rgb, LUT).astype(np.float32)
    lum = f @ np.array([0.299, 0.587, 0.114], np.float32)
    f = lum[..., None] + (f - lum[..., None]) * sat
    return np.clip(f, 0, 255).astype(np.uint8)


def rgba_img(rgb, a=None):
    a = np.full(rgb.shape[:2], 255, np.uint8) if a is None else a
    return skia.Image.fromarray(np.ascontiguousarray(np.dstack([rgb, a])), colorType=skia.kRGBA_8888_ColorType)


def _anchors():
    """zoom anchor per shot: the head of the person matte (mid-shot frame)."""
    out = []
    A = np.load(HERE / "work" / "alpha.npy", mmap_mode="r")
    for i in range(len(SHOTS) - 1):
        a = np.asarray(A[int((SHOTS[i] + SHOTS[i + 1]) / 2 * FPS)])
        ys, xs = np.nonzero(a > 128)
        top, hgt = ys.min(), ys.max() - ys.min()
        sel = ys < top + 0.12 * hgt
        out.append((float(xs[sel].mean() * 2), float((top + 0.07 * hgt) * 2)))
    return out


ANCHOR = _anchors()


# ================================================================== camera
PUNCH = []    # (out_t0, out_t1, zoom) emphasis push-ins
SHAKES = []   # (out_t, amplitude px)


def W_(i):
    return WORDS[i]


def camera(t):
    """(zoom, dx, dy, rot, blur) for the footage at output time t."""
    k = seg_at(t)
    a, b, o = EDL[k]
    sh = shot_of(a)
    first = next(j for j, s in enumerate(EDL) if shot_of(s[0]) == sh)
    z = (1.0, 1.085)[(k - first) % 2]                     # alternate framing hides the jump cuts
    z *= 1 + 0.012 * (t - o)                               # slow push inside a run
    if t < 0.45:
        z *= lerp(1.18, 1.0, e_out(t / 0.45))              # opening settle
    for t0, t1, zz in PUNCH:
        if t0 - 0.12 <= t < t1 + 0.18:
            kin = e_out(clamp((t - t0 + 0.12) / 0.16))
            kout = 1 - e_io(clamp((t - t1) / 0.18))
            z *= lerp(1.0, zz, kin * kout)
    blur = 0.0
    for tt in TRANS:                                        # zoom-whip across shot changes
        if tt - 0.13 <= t < tt:
            k_ = e_in((t - (tt - 0.13)) / 0.13)
            z *= 1 + 0.22 * k_
            blur = max(blur, 26 * k_)
        elif tt <= t < tt + 0.16:
            k_ = 1 - e_out((t - tt) / 0.16)
            z *= 1 + 0.22 * k_
            blur = max(blur, 26 * k_)
    dx = dy = rot = 0.0
    for st, amp in SHAKES:
        if st <= t < st + 0.32:
            q = 1 - (t - st) / 0.32
            dx += amp * q * math.sin(t * 95.0)
            dy += amp * q * math.sin(t * 71.0 + 1.3)
            rot += amp * 0.05 * q * math.sin(t * 61.0)
    return z, dx, dy, rot, blur


def apply_cam(c, cam, anchor):
    z, dx, dy, rot, _ = cam
    c.translate(anchor[0] + dx, anchor[1] + dy)
    c.rotate(rot)
    c.scale(z, z)
    c.translate(-anchor[0], -anchor[1])


# ================================================================== captions
# One entry per caption group, in spoken order. Markup per word:
#   *w*  neon keyword (sans)   /w/ neon serif italic (bigger)   ~w~ struck through after it is said
#   ^w^  sags after it is said   |  line break
GROUPS = [
    ("Mind mein ek", {}),
    ("new *creative* /idea/ hai,", {}),
    ("lekin samajh | nahi aa raha", {}),
    ("ki *show* kahan karein?", {}),
    ("Isliye | *ADEX*", {"sizes": [70, 190], "fx": "slam"}),
    ("lekar aaya hai new", {}),
    ("OOH | /Creative/ | Challenge.", {"sizes": [0, 150, 104], "fx": "stack"}),
    ("Make a | ^boring^ brand...", {}),
    ("*Boring* brand?", {"size": 128, "fx": "slam"}),
    ("Yeh kya?", {"size": 150, "fx": "slam"}),
    ("Ruko ruko,", {"size": 132, "fx": "slam"}),
    ("main batati hoon.", {}),
    ("Pick your city,", {}),
    ("pick any brand,", {}),
    ("product or location.", {}),
    ("Then see,", {}),
    ("us city pe,", {}),
    ("us location pe", {}),
    ("*already* kya | chal raha hai.", {}),
    ("Find the /insight/", {}),
    ("and turn | this insight", {}),
    ("into an | *OOH* /idea./", {}),
    ("We're not just | looking for", {}),
    ("a creative | ~billboard,~", {}),
    ("we are | looking for", {}),
    ("observation,", {}),
    ("insight", {}),
    ("and creative | OOH thinking.", {}),
    ("Aur | *winner?*", {"sizes": [70, 0], "fx": "stack"}),
    ("Sirf ~certificate~ | nahi.", {}),
    ("Your /idea/ could", {}),
    ("actually | come *alive*", {}),
    ("on *ADEX* *OOH* | Media,", {}),
    ("and also you", {}),
    ("get a *chance*", {}),
    ("to *work* *with* *us.*", {}),
    ("If you want", {}),
    ("to show your", {}),
    ("/creativity,/", {"size": 150, "fx": "slam"}),
    ("*join* *us*", {"size": 170, "fx": "slam"}),
    ("and register now!", {"fx": "cta"}),
]
CAP_Y = [1330, 1330, 1360, 1350, 1330, 1480]   # caption block centre per shot
BASE = 92


def _parse():
    groups, k = [], 0
    for gi, (mark, opt) in enumerate(GROUPS):
        lines, cur = [], []
        for tok in mark.split():
            if tok == "|":
                lines.append(cur)
                cur = []
                continue
            m = re.match(r"^([*/~^]?)(.+?)([*/~^]?)([.,?!]*)$", tok)
            style = m.group(1) or m.group(3)
            raw = m.group(2) + m.group(4)
            w = WORDS[k]
            assert re.sub(r"[^a-z0-9]", "", raw.lower()) == w["k"], (gi, tok, w["w"])
            disp = re.sub(r"[.,]", "", raw)
            cur.append(dict(i=k, w=w, style=style, disp=disp if style == "/" else disp.upper()))
            k += 1
        lines.append(cur)
        groups.append(dict(i=gi, lines=lines, opt=opt))
    assert k == len(WORDS), (k, len(WORDS))
    for gi, g in enumerate(groups):
        ws = [x for ln in g["lines"] for x in ln]
        g["s"] = ws[0]["w"]["os"] - 0.05
        last = ws[-1]["w"]["oe"]
        nxt = groups[gi + 1]["lines"][0][0]["w"]["os"] - 0.05 if gi + 1 < len(groups) else TOTAL
        cut_at = min([tt for tt in TRANS if tt > g["s"] + 0.05] + [TOTAL])   # never carry over a shot change
        g["e"] = min(nxt, last + 0.7, cut_at)
        g["cut"] = g["e"] >= min(nxt, cut_at) - 1e-6     # replaced by the next group / the whip (no exit anim)
        g["shot"] = shot_of(src_at(ws[0]["w"]["os"] + 0.01))
    return groups


CAPS = _parse()


def word_font(x, size):
    return ("italic", size * 1.32) if x["style"] == "/" else ("black", size)


def _glow(color, a, blur):
    p = fill(color, a)
    p.setImageFilter(skia.ImageFilters.Blur(blur, blur))
    return p


def draw_word(c, s, x, y, name, size, color, a=1.0, glow=False):
    f = font(name, size)
    c.drawString(s, x + 2, y + 6, f, _glow(INK, 0.55 * a, 9))         # soft drop shadow for legibility
    if glow:
        c.drawString(s, x, y, f, _glow(color, 0.55 * a, 16))
    c.drawString(s, x, y, f, fill(color, a))


def draw_caption(c, t, g):
    opt = g["opt"]
    if opt.get("fx") == "cta":
        return
    base = opt.get("size", BASE)
    sizes = opt.get("sizes")
    ws_all = [x for ln in g["lines"] for x in ln]
    # layout
    rows = []
    for li, ln in enumerate(g["lines"]):
        size = sizes[li] if sizes else base
        if size == 0:            # word drawn by a dedicated effect (behind-text), keep it out of the block
            continue
        gap = size * 0.26
        items = []
        for x in ln:
            name, sz = word_font(x, size)
            items.append((x, name, sz, measure(x["disp"], name, sz)))
        width = sum(it[3] for it in items) + gap * (len(items) - 1)
        asc = max(font(n, s_).getMetrics().fCapHeight for _, n, s_, _ in items)
        rows.append((items, width, gap, asc))
    if not rows:
        return
    sc = min(1.0, 960 / max(r[1] for r in rows))
    lead = 0.3
    total_h = sum(r[3] for r in rows) + sum(r[3] * lead for r in rows[:-1])
    variant = ("pop", "rise", "blur")[g["i"] % 3]
    fx = opt.get("fx")
    # group-level entrance / exit
    ga = 1.0
    gs = 1.0
    gy = 0.0
    if fx == "slam":
        k = clamp((t - g["s"]) / 0.32)
        gs = lerp(1.55, 1.0, e_back(k, 2.2)) if k < 1 else 1.0
        ga = clamp(k * 4)
    if not g["cut"]:
        q = clamp((t - (g["e"] - 0.14)) / 0.14)
        ga *= 1 - q
        gy -= 26 * e_in(q)
    c.save()
    c.translate(540, CAP_Y[g["shot"]] + gy)
    c.scale(sc * gs, sc * gs)
    y = -total_h / 2
    for items, width, gap, asc in rows:
        y += asc
        x0 = -width / 2
        for x, name, sz, wd in items:
            w = x["w"]
            if t < w["os"] - 0.06:
                x0 += wd + gap
                continue
            k = clamp((t - w["os"] + 0.06) / 0.26)
            speaking = w["os"] - 0.06 <= t < w["oe"] + 0.02
            keyword = x["style"] in "*/" and x["style"] != ""
            color = NEON if (speaking or keyword) else WHITE
            a = ga * clamp(k * 3)
            c.save()
            c.translate(x0 + wd / 2, y - asc / 2)
            if variant == "pop" or fx == "slam":
                s_ = 0.55 + 0.45 * spring(k * 0.26, w=24, z=0.45)
                c.scale(s_, s_)
            elif variant == "rise":
                c.translate(0, 34 * (1 - e_out(k)))
            else:
                s_ = lerp(1.18, 1.0, e_out(k))
                c.scale(s_, s_)
                a *= e_out(k)
            if speaking and fx != "slam":
                c.scale(1.06, 1.06)
            c.translate(-wd / 2, asc / 2)
            if x["style"] == "^" and t > w["oe"]:
                sag_word(c, x["disp"], name, sz, t - w["oe"], a)
            else:
                strike_k = clamp((t - w["oe"] - 0.05) / 0.22) if x["style"] == "~" else 0
                draw_word(c, x["disp"], 0, 0, name, sz, color, a * (1 - 0.35 * strike_k), glow=color == NEON)
                if strike_k > 0:
                    p = fill(NEON, a)
                    p.setStrokeWidth(sz * 0.11)
                    p.setStyle(skia.Paint.kStroke_Style)
                    p.setStrokeCap(skia.Paint.kRound_Cap)
                    yy = -asc * 0.45
                    c.drawLine(-8, yy + 6, -8 + (wd + 16) * e_out(strike_k), yy - 4, p)
            c.restore()
            x0 += wd + gap
        y += asc * lead
    c.restore()


def sag_word(c, s, name, size, dt, a):
    """'boring': letters lose energy one by one and droop."""
    f = font(name, size)
    x = 0.0
    for j, ch in enumerate(s):
        cw = f.measureText(ch)
        k = e_out(clamp((dt - j * 0.05) / 0.45))
        c.save()
        c.translate(x + cw / 2, 0)
        c.rotate((8 + 10 * hrand(j, 3)) * k * (1 if j % 2 else -1))
        c.translate(-cw / 2, 26 * k * (0.6 + 0.8 * hrand(j, 9)))
        draw_word(c, ch, 0, 0, name, size, lerp_col(WHITE, "#9AA09A", k), a * (1 - 0.25 * k))
        c.restore()
        x += cw


def lerp_col(c0, c1, k):
    a = [int(c0[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{int(lerp(p, q, k)):02X}" for p, q in zip(a, b))


def draw_captions(c, t):
    for g in CAPS:
        if g["s"] <= t < g["e"]:
            draw_caption(c, t, g)


# ================================================================== word-locked graphics
def P(i):
    return WORDS[i]


def pill(c, label, cx, cy, k, a=1.0, check=False):
    """requirement pill: dark glass, neon outline, white label (+ neon tick)."""
    if k <= 0:
        return
    s_ = 0.4 + 0.6 * spring(k * 0.3, w=22, z=0.42)
    size = 46
    tw = measure(label, "heavy", size)
    pw, ph = tw + (118 if check else 70), 92
    c.save()
    c.translate(cx, cy)
    c.scale(s_, s_)
    r = rrect(-pw / 2, -ph / 2, pw, ph, ph / 2)
    c.drawRRect(r, _glow(INK, 0.35 * a, 14))
    c.drawRRect(r, fill("#0B0D0B", 0.62 * a))
    p = fill(NEON, a)
    p.setStyle(skia.Paint.kStroke_Style)
    p.setStrokeWidth(4)
    c.drawRRect(r, p)
    tx = -pw / 2 + (84 if check else 35)
    if check:
        c.drawCircle(-pw / 2 + 46, 0, 22, fill(NEON, a))
        q = fill(INK, a)
        q.setStyle(skia.Paint.kStroke_Style)
        q.setStrokeWidth(6)
        q.setStrokeCap(skia.Paint.kRound_Cap)
        q.setStrokeJoin(skia.Paint.kRound_Join)
        path = skia.Path()
        kk = e_out(clamp(k * 1.6 - 0.3))
        p0, p1, p2 = (-pw / 2 + 35, 1), (-pw / 2 + 43, 9), (-pw / 2 + 58, -8)
        path.moveTo(*p0)
        if kk < 0.4:
            path.lineTo(lerp(p0[0], p1[0], kk / 0.4), lerp(p0[1], p1[1], kk / 0.4))
        else:
            path.lineTo(*p1)
            path.lineTo(lerp(p1[0], p2[0], (kk - 0.4) / 0.6), lerp(p1[1], p2[1], (kk - 0.4) / 0.6))
        c.drawPath(path, q)
    c.drawString(label, tx, cap_mid(size), font("heavy", size), fill(WHITE, a))
    c.restore()


def cap_mid(size):
    return font("heavy", size).getMetrics().fCapHeight / 2


# pick your city / brand / product / location  ->  2x2 pills
PILLS_1 = [(40, "CITY"), (43, "BRAND"), (44, "PRODUCT"), (46, "LOCATION")]
# observation / insight / creative OOH thinking -> stacked ticks
PILLS_2 = [(83, "OBSERVATION"), (84, "INSIGHT"), (88, "OOH THINKING")]


def pills(c, t):
    t0, t1 = P(40)["os"] - 0.1, P(46)["oe"] + 0.55
    if t0 <= t < t1:
        out = e_in(clamp((t - (t1 - 0.2)) / 0.2))
        pos = [(318, 1100), (762, 1100), (318, 1210), (762, 1210)]
        for (wi, label), (x, y) in zip(PILLS_1, pos):
            k = clamp((t - P(wi)["os"] + 0.04) / 0.3)
            pill(c, label, x, y - 30 * out, k * (1 - out) + (out > 0) * 1e-3, a=1 - out)
    t0, t1 = P(83)["os"] - 0.1, P(88)["oe"] + 0.5
    if t0 <= t < t1:
        out = e_in(clamp((t - (t1 - 0.2)) / 0.2))
        for j, (wi, label) in enumerate(PILLS_2):
            k = clamp((t - P(wi)["os"] + 0.04) / 0.3)
            pill(c, label, 540, 980 + j * 112 - 30 * out, k, a=1 - out, check=True)


# giant type behind the speaker
BEHIND = [
    dict(text="OOH", t0=P(22)["os"] - 0.04, t1=P(24)["oe"] + 0.35, size=470, y=None, wi=22),
    dict(text="WINNER?", t0=P(90)["os"] - 0.04, t1=P(93)["oe"] + 0.25, size=228, y=770, wi=90),
]


def behind_active(t):
    for b in BEHIND:
        if b["t0"] <= t < b["t1"]:
            return b
    return None


def draw_behind(c, t, b, anchor):
    k = clamp((t - b["t0"]) / 0.5)
    out = clamp((t - (b["t1"] - 0.18)) / 0.18)
    size = b["size"]
    f = font("black", size)
    total = f.measureText(b["text"])
    sc = min(1.0, 1010 / total)
    y = b["y"] or anchor[1] + 120
    c.save()
    c.translate(540, y)
    c.scale(sc, sc)
    x = -total / 2
    capH = f.getMetrics().fCapHeight
    for j, ch in enumerate(b["text"]):
        cw = f.measureText(ch)
        kj = clamp((t - b["t0"] - j * 0.055) / 0.42)
        a = clamp(kj * 3) * (1 - out)
        c.save()
        c.translate(x, capH / 2 + 140 * (1 - e_out(kj)) + 60 * e_in(out))
        c.drawString(ch, 0, 0, f, _glow(NEON, 0.45 * a, 30))
        c.drawString(ch, 0, 0, f, fill(NEON, a))
        c.restore()
        x += cw
    c.restore()
    return k


# register button (end)
REG = P(124)
NOW = P(125)


def cta(c, t):
    t0 = P(123)["os"] - 0.05
    if t < t0:
        return
    y = 1500
    # kicker
    ka = e_out(clamp((t - t0) / 0.35))
    s = "ADEX  ·  OOH CREATIVE CHALLENGE"
    f = font("bold", 34)
    tw = sum(f.measureText(ch) + 6 for ch in s)
    xx = 540 - tw / 2
    for ch in s:
        c.drawString(ch, xx + 1, y - 118 + 22 * (1 - ka) + 3, f, _glow(INK, 0.5 * ka, 6))
        c.drawString(ch, xx, y - 118 + 22 * (1 - ka), f, fill(WHITE, 0.95 * ka))
        xx += f.measureText(ch) + 6
    # button
    k = clamp((t - REG["os"] + 0.08) / 0.4)
    if k <= 0:
        return
    click = NOW["oe"] - 0.1
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - click) / 0.22))
    s_ = (0.3 + 0.7 * spring(k * 0.4, w=20, z=0.4)) * press
    label = "REGISTER NOW"
    size = 62
    tw = measure(label, "black", size)
    bw, bh = tw + 150, 132
    c.save()
    c.translate(540, y)
    c.scale(s_, s_)
    r = rrect(-bw / 2, -bh / 2, bw, bh, bh / 2)
    pulse = 0.5 + 0.5 * math.sin((t - REG["os"]) * 6)
    c.drawRRect(r, _glow(NEON, 0.35 + 0.25 * pulse, 34))
    c.drawRRect(r, fill(NEON))
    c.drawString(label, -bw / 2 + 52, font("black", size).getMetrics().fCapHeight / 2, font("black", size), fill(INK))
    # arrow
    ax = bw / 2 - 66 + 8 * math.sin((t - REG["os"]) * 7)
    p = fill(INK)
    p.setStyle(skia.Paint.kStroke_Style)
    p.setStrokeWidth(9)
    p.setStrokeCap(skia.Paint.kRound_Cap)
    p.setStrokeJoin(skia.Paint.kRound_Join)
    c.drawLine(ax - 30, 0, ax + 6, 0, p)
    path = skia.Path()
    path.moveTo(ax - 10, -18)
    path.lineTo(ax + 8, 0)
    path.lineTo(ax - 10, 18)
    c.drawPath(path, p)
    c.restore()
    # ripple + cursor
    if t >= click:
        q = clamp((t - click) / 0.5)
        rp = fill(WHITE, 0.7 * (1 - q))
        rp.setStyle(skia.Paint.kStroke_Style)
        rp.setStrokeWidth(6)
        c.drawRRect(rrect(540 - bw / 2 - 40 * q, y - bh / 2 - 40 * q, bw + 80 * q, bh + 80 * q, bh / 2 + 40 * q), rp)
    kc = e_io(clamp((t - (click - 0.55)) / 0.5))
    if kc > 0:
        cx, cy = lerp(900, 640, kc), lerp(1760, y + 22, kc)
        if t >= click:
            cy += 6 * math.sin(math.pi * clamp((t - click) / 0.2))
        cursor(c, cx, cy)


def cursor(c, x, y):
    path = skia.Path()
    pts = [(0, 0), (0, 64), (16, 49), (28, 76), (40, 71), (28, 45), (49, 45)]
    path.moveTo(*pts[0])
    for p in pts[1:]:
        path.close() if False else path.lineTo(*p)
    path.close()
    c.save()
    c.translate(x, y)
    c.drawPath(path, _glow(INK, 0.5, 6))
    c.drawPath(path, fill(WHITE))
    s = fill(INK)
    s.setStyle(skia.Paint.kStroke_Style)
    s.setStrokeWidth(4)
    s.setStrokeJoin(skia.Paint.kRound_Join)
    c.drawPath(path, s)
    c.restore()


# emphasis camera moves + shakes, word-locked
PUNCH += [
    (P(17)["os"], P(17)["oe"] + 0.15, 1.1),        # ADEX
    (P(29)["os"], P(30)["oe"], 1.14),              # Boring brand?
    (P(31)["os"], P(32)["oe"] + 0.4, 1.26),        # Yeh kya?
    (P(55)["os"], P(55)["oe"], 1.07),              # already
    (P(90)["os"], P(90)["oe"] + 0.2, 1.1),         # winner?
    (P(121)["os"], P(122)["oe"], 1.08),            # join us
]
SHAKES += [(P(31)["os"], 9), (P(33)["os"], 7), (P(34)["os"], 7), (P(17)["os"] + 0.03, 6)]


# ================================================================== frame
VIG = None


def draw(c, t, f):
    ts = src_at(t)
    fi = int(round(ts * FPS))
    sh = shot_of(ts)
    anchor = ANCHOR[sh]
    rgb = grade(frame_rgb(fi))
    cam = camera(t)
    paint = skia.Paint()
    if cam[4] > 0.5:
        paint.setImageFilter(skia.ImageFilters.Blur(cam[4] * 0.25, cam[4]))
    c.save()
    apply_cam(c, cam, anchor)
    c.drawImage(rgba_img(rgb), 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear), paint)
    c.restore()
    b = behind_active(t)
    if b:
        draw_behind(c, t, b, anchor)
        a = cv2.resize(alpha_small(fi), (W, H), interpolation=cv2.INTER_LINEAR)
        c.save()
        apply_cam(c, cam, anchor)
        c.drawImage(rgba_img(rgb, a), 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear))
        c.restore()
    pills(c, t)
    draw_captions(c, t)
    cta(c, t)
    # fade in / out
    if t < 0.12 or t > TOTAL - 0.35:
        k = clamp(t / 0.12) if t < 0.12 else clamp((TOTAL - t) / 0.35)
        c.drawRect(skia.Rect.MakeWH(W, H), fill(INK, 1 - k))
    return {}


def post(arr, g, f):
    global VIG
    if VIG is None:
        yy, xx = np.mgrid[0:arr.shape[0], 0:arr.shape[1]].astype(np.float32)
        r = np.sqrt(((xx - arr.shape[1] / 2) / (arr.shape[1] / 2)) ** 2 + ((yy - arr.shape[0] / 2) / (arr.shape[0] / 2)) ** 2)
        VIG = (1 - 0.16 * np.clip(r - 0.55, 0, None) ** 1.6)[..., None].astype(np.float32)
    return np.clip(arr * VIG, 0, 255).astype(np.uint8)


FILM = kit.Film(draw, TOTAL, FPS, post=post, out_dir=OUT)


# ================================================================== audio
def sfx_list():
    S = []

    def a(t, kind, gain=-8, **kw):
        S.append(dict(t=t, kind=kind, gain_db=gain, **kw))

    a(0.0, "swish", -14)
    for tt in TRANS:
        a(tt - 0.2, "whoosh", -13, dur=0.45)
    a(P(17)["os"] - 0.02, "impact", -15)                  # ADEX
    a(P(22)["os"] - 0.05, "swish", -11)                   # OOH rises behind her
    a(P(23)["os"], "sparkle", -17)
    a(P(27)["oe"] + 0.05, "downlifter", -14)              # boring sags
    a(P(29)["os"] - 0.03, "pop", -12)
    a(P(31)["os"] - 0.02, "glitch", -15)                  # Yeh kya?
    a(P(33)["os"], "tick", -10)
    a(P(34)["os"], "tick", -10)
    for wi, _ in PILLS_1 + PILLS_2:
        a(P(wi)["os"], "pop", -11)
    a(P(62)["os"], "sparkle", -18)                        # insight
    a(P(70)["os"], "ding", -17)                           # OOH idea
    a(P(78)["oe"] + 0.05, "swish", -13)                   # billboard struck
    a(P(90)["os"] - 1.0, "riser", -17, dur=1.0)           # into "winner"
    a(P(90)["os"] - 0.03, "impact", -12)
    a(P(92)["oe"] + 0.05, "swish", -13)                   # certificate struck
    a(P(99)["os"], "sparkle", -18)                        # come alive
    a(P(120)["os"], "sparkle", -16)                       # creativity
    a(P(121)["os"] - 0.02, "impact", -14)                 # join us
    a(REG["os"] - 0.05, "pop", -9)
    a(NOW["oe"] - 0.1, "click", -6)
    return S


def build_audio():
    SR = ak.SR
    work = HERE / "work"
    vpath = work / "voice_clean.wav"
    if not vpath.exists():
        ff("-i", str(HERE / "raw" / "take.mp4"), "-vn", "-af",
           "highpass=f=85,afftdn=nf=-30,acompressor=threshold=-21dB:ratio=3:attack=5:release=90:makeup=4,"
           "deesser=i=0.35", "-ar", str(SR), "-ac", "2", str(vpath))
    raw = ak.read_audio(vpath)
    n = int(TOTAL * SR) + 1
    voice = np.zeros((n, 2), np.float32)
    xf = int(0.01 * SR)
    for a, b, o in EDL:
        seg = raw[int(a * SR):int(b * SR)].copy()
        ramp = np.linspace(0, 1, xf, dtype=np.float32)[:, None]
        seg[:xf] *= ramp
        seg[-xf:] *= ramp[::-1]
        i0 = int(o * SR)
        voice[i0:i0 + len(seg)] += seg[: n - i0]
    music = ak.music_bed("upbeat", seconds=TOTAL + 0.5, bpm=120, key="D", intro_bars=1, seed=11)[:n]
    music = np.pad(music, ((0, n - len(music)), (0, 0)))
    duck = ak.duck_gain(voice, depth_db=-9)
    mix = voice + music * ak.db(-15) * duck[:, None]
    for s in sfx_list():
        kind = s["kind"]
        clip = ak.SFX[kind](s["dur"]) if "dur" in s else ak.SFX[kind]()
        ak.place(mix, clip, s["t"], s["gain_db"])
    fo = int(0.5 * SR)
    mix[-fo:] *= np.linspace(1, 0, fo)[:, None]
    peak = np.max(np.abs(mix)) or 1
    if peak > 0.98:
        mix = np.tanh(mix / peak * 1.2) / math.tanh(1.2) * 0.98
    out = work / "mix.wav"
    ak.write_wav(out, mix)
    print("->", out)
    return out


def finish(picture, audio, out):
    """delivery: H.264 high, AAC 48k at -14 LUFS."""
    ln = loudnorm_filter(audio)
    ff("-i", str(picture), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "slow",
       "-crf", "18", "-maxrate", "14M", "-bufsize", "28M", "-pix_fmt", "yuv420p", "-profile:v", "high", "-af", ln,
       "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out))
    print("->", out)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "stills":
        FILM.stills([float(x) for x in sys.argv[2:]])
    elif cmd == "sheet":
        FILM.sheet([round(TOTAL * (i + 0.5) / 40, 2) for i in range(40)], cols=8)
    elif cmd == "audio":
        build_audio()
    elif cmd == "info":
        print(f"total {TOTAL:.2f}s  (raw {NSRC / FPS:.1f}s)   transitions {[round(x, 2) for x in TRANS]}")
        for a, b, o in EDL:
            print(f"  src {a:6.2f}-{b:6.2f}  out {o:6.2f} +{b - a:.2f}  shot {shot_of(a)}")
        print("anchors", [(round(x), round(y)) for x, y in ANCHOR])
    elif cmd == "render":
        draft = "--draft" in sys.argv
        pic = FILM.render(OUT / ("draft_picture.mp4" if draft else "picture.mp4"), draft=draft)
        aud = build_audio()
        finish(pic, aud, OUT / ("draft.mp4" if draft else "adex_ooh_edit.mp4"))


if __name__ == "__main__":
    main()
