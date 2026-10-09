"""ADEX OOH Creative Challenge: premium kinetic edit (v2). White + orange, one motion-graphics system.

    python3 premium.py stills 1.0 4.2 ...    -> out/stills_v2/*.png  (half res)
    python3 premium.py sheet                 -> out/sheet_v2.png
    python3 premium.py render [--draft]      -> out/adex_ooh_premium.mp4

Same cut, words and person matte as edit.py (v1). The design system:
  colour   white type, orange (#FF6B1A) for the spoken word, keywords and every graphic accent;
           near-black glass panels behind graphics
  type     Anton for big kinetic / behind-the-speaker type, InterTight Black for captions,
           Instrument Serif italic for orange accents, JetBrains Mono for labels and the HUD
  motion   every word rises through a mask and leaves upward; icons draw themselves on (trim paths);
           orange slab wipes carry the shot changes; a constant HUD (brand, chapter, progress line)
Graphics are word-locked and sit in each shot's free space (or behind the speaker via the matte).
"""

import math
import re
import sys
from pathlib import Path

import cv2
import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import edit as V1  # noqa: E402  (cut list, words, footage, matte, anchors)
from edit import (ANCHOR, EDL, SHOTS, TOTAL, TRANS, WORDS, alpha_small, apply_cam, frame_rgb, rgba_img,  # noqa: E402
                  seg_at, shot_of, src_at)
import audio_kit as ak  # noqa: E402
import kit  # noqa: E402
from kit import W, H, clamp, e_back, e_in, e_io, e_out, e_expo, font, hrand, lerp, measure, rrect, spring  # noqa: E402
from vibelib import ff, loudnorm_filter  # noqa: E402

FPS = 30
OUT = HERE / "out"
WHITE = "#FFFFFF"
ORANGE = "#FF6B1A"
INK = "#0A0A0B"
GLASS = "#0D0E10"


def col(c, a=1.0):
    return skia.Color(int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16), int(255 * clamp(a)))


def paint(c, a=1.0, blur=0.0, stroke=0.0, cap=True):
    p = skia.Paint(Color=col(c, a), AntiAlias=True)
    if blur:
        p.setImageFilter(skia.ImageFilters.Blur(blur, blur))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        if cap:
            p.setStrokeCap(skia.Paint.kRound_Cap)
            p.setStrokeJoin(skia.Paint.kRound_Join)
    return p


def trim(p, k):
    """draw-on: keep the first k of the path (k<=0 draws nothing, k>=1 the whole path)."""
    k = clamp(k)
    if k <= 0.001:
        p.setAlpha(0)
    elif k < 0.999:
        p.setPathEffect(skia.TrimPathEffect.Make(0, k))
    return p


def os_(i):
    return WORDS[i]["os"]


def oe_(i):
    return WORDS[i]["oe"]


def e_out5(k):
    return 1 - (1 - clamp(k)) ** 5


# ================================================================== kinetic type primitives
def metrics(name, size):
    m = font(name, size).getMetrics()
    return -m.fAscent, m.fDescent, m.fCapHeight


def mword(c, s, x, base, name, size, color, kin, kout=0.0, a=1.0, glow=False, outline=0, shadow=True):
    """one word revealed through a mask: rises from below its baseline, leaves upward."""
    if kin <= 0 or kout >= 1 or a <= 0:
        return
    f = font(name, size)
    asc, desc, capH = metrics(name, size)
    w = f.measureText(s)
    hgt = asc + desc
    c.save()
    c.clipRect(skia.Rect.MakeLTRB(x - 40, base - asc - 18, x + w + 40, base + desc + 22))
    y = base + hgt * 1.05 * (1 - e_out5(kin)) - hgt * 1.05 * e_in(kout)
    if shadow:
        c.drawString(s, x + 2, y + 5, f, paint(INK, 0.5 * a, blur=10))
    if glow:
        c.drawString(s, x, y, f, paint(color, 0.45 * a, blur=18))
    if outline:
        c.drawString(s, x, y, f, paint(color, a, stroke=outline, cap=False))
    else:
        c.drawString(s, x, y, f, paint(color, a))
    c.restore()


def kblock(c, t, lines, cx, cy, t_out=None, align="c", lead=0.96, out_dur=0.16, a=1.0):
    """kinetic type block. lines: [[dict(s, t, name, size, color, outline?, glow?), ...], ...]
    each word rises in at its own time t; the whole block leaves upward at t_out (staggered)."""
    rows = []
    for ln in lines:
        gap = max(tk["size"] for tk in ln) * 0.22
        ws = [measure(tk["s"], tk["name"], tk["size"]) for tk in ln]
        asc = max(metrics(tk["name"], tk["size"])[2] for tk in ln)
        rows.append((ln, ws, gap, sum(ws) + gap * (len(ws) - 1), asc))
    total = sum(r[4] for r in rows) + sum(r[4] * (lead - 1 + 0.32) for r in rows[:-1])
    y = cy - total / 2
    j = 0
    for ln, ws, gap, width, asc in rows:
        y += asc
        x = cx - width / 2 if align == "c" else cx if align == "l" else cx - width
        for tk, wd in zip(ln, ws):
            kin = clamp((t - tk["t"]) / tk.get("dur", 0.34))
            kout = clamp((t - t_out - j * 0.025) / out_dur) if t_out is not None else 0
            mword(c, tk["s"], x, y, tk["name"], tk["size"], tk["color"], kin, kout, a,
                  glow=tk.get("glow", False), outline=tk.get("outline", 0))
            x += wd + gap
            j += 1
        y += asc * (lead - 1 + 0.32)


def T(s, t, size, color=WHITE, name="anton", **kw):
    return dict(s=s, t=t, size=size, color=color, name=name, **kw)


# ================================================================== icons (unit box 0..100, stroked)
def _icon_paths():
    P = {}
    p = skia.Path()                                   # bulb
    p.addArc(skia.Rect.MakeLTRB(22, 8, 78, 64), 140, 260)
    p.moveTo(36, 61)
    p.lineTo(38, 76)
    p.lineTo(62, 76)
    p.lineTo(64, 61)
    p.moveTo(41, 86)
    p.lineTo(59, 86)
    p.moveTo(43, 60)
    p.lineTo(46, 44)
    p.lineTo(50, 52)
    p.lineTo(54, 44)
    p.lineTo(57, 60)
    P["bulb"] = p
    p = skia.Path()                                   # map pin
    p.moveTo(50, 94)
    p.cubicTo(36, 74, 20, 58, 20, 38)
    p.cubicTo(20, 20, 34, 8, 50, 8)
    p.cubicTo(66, 8, 80, 20, 80, 38)
    p.cubicTo(80, 58, 64, 74, 50, 94)
    p.addCircle(50, 38, 11)
    P["pin"] = p
    p = skia.Path()                                   # city skyline
    for pts in ([(6, 90), (6, 50), (26, 50), (26, 28), (46, 28), (46, 90)],
                [(46, 90), (46, 58), (60, 58), (60, 12), (82, 12), (82, 44), (94, 44), (94, 90)],
                [(4, 90), (96, 90)]):
        p.moveTo(*pts[0])
        for q in pts[1:]:
            p.lineTo(*q)
    for wx, wy in ((14, 62), (34, 40), (34, 58), (68, 26), (68, 44), (68, 62)):
        p.moveTo(wx, wy)
        p.lineTo(wx + 5, wy)
    P["city"] = p
    p = skia.Path()                                   # price tag (brand)
    p.moveTo(12, 14)
    p.lineTo(52, 14)
    p.lineTo(90, 52)
    p.lineTo(54, 88)
    p.lineTo(12, 50)
    p.close()
    p.addCircle(32, 34, 7)
    P["tag"] = p
    p = skia.Path()                                   # product box
    for pts in ([(50, 8), (90, 28), (90, 72), (50, 92), (10, 72), (10, 28), (50, 8)],
                [(10, 28), (50, 48), (90, 28)], [(50, 48), (50, 92)], [(30, 18), (70, 38)]):
        p.moveTo(*pts[0])
        for q in pts[1:]:
            p.lineTo(*q)
    P["box"] = p
    p = skia.Path()                                   # eye
    p.moveTo(4, 50)
    p.quadTo(50, 4, 96, 50)
    p.quadTo(50, 96, 4, 50)
    p.addCircle(50, 50, 15)
    P["eye"] = p
    p = skia.Path()                                   # billboard
    p.addRect(skia.Rect.MakeLTRB(6, 10, 94, 60))
    for x in (30, 70):
        p.moveTo(x, 60)
        p.lineTo(x, 90)
    p.moveTo(14, 90)
    p.lineTo(86, 90)
    P["billboard"] = p
    return P


ICONS = _icon_paths()


def icon(c, name, cx, cy, size, k, color=ORANGE, a=1.0, width=6.5):
    if k <= 0:
        return
    s = size / 100
    c.save()
    c.translate(cx - size / 2, cy - size / 2)
    c.scale(s, s)
    p = paint(color, a, stroke=width)
    trim(p, e_io(k))
    c.drawPath(ICONS[name], p)
    c.restore()


def glass(c, x, y, w, h, r=26, a=1.0, border=WHITE, border_a=0.22, bw=2.0):
    rr = rrect(x, y, w, h, r)
    c.drawRRect(rr, paint(INK, 0.35 * a, blur=22))
    c.drawRRect(rr, paint(GLASS, 0.72 * a))
    if border:
        c.drawRRect(rr, paint(border, border_a * a, stroke=bw, cap=False))


def pop(k):
    """scale for a springy pop-in, 0..1 -> ~0.6..1 with overshoot."""
    return 0.6 + 0.4 * spring(k * 0.32, w=22, z=0.45)


# ================================================================== bottom captions
# markup: *w* orange   /w/ orange serif italic   #w# white on an orange box   ~w~ struck after it's said
#         ^w^ drains and sags after it's said   |  line break.  opt hide: the words live in a graphic instead.
GROUPS = [
    ("Mind mein ek", {}),
    ("new *creative* /idea/ hai,", {}),
    ("lekin samajh | nahi aa raha", {}),
    ("ki show *kahan* karein?", {}),
    ("Isliye ADEX", {"hide": True}),
    ("lekar aaya hai new", {}),
    ("OOH | /Creative/ | Challenge.", {"sizes": [0, 124, 92]}),
    ("Make a | ^boring^ brand...", {}),
    ("Boring brand?", {"hide": True}),
    ("Yeh kya?", {"hide": True}),
    ("Ruko ruko,", {"hide": True}),
    ("main batati hoon.", {}),
    ("Pick your *city,*", {}),
    ("pick any *brand,*", {}),
    ("*product* or | *location.*", {}),
    ("Then see,", {}),
    ("us *city* pe,", {}),
    ("us *location* pe", {}),
    ("#already# kya | chal raha hai.", {}),
    ("Find the /insight/", {}),
    ("and turn | this insight", {}),
    ("into an | *OOH* /idea./", {}),
    ("We're not just | looking for", {}),
    ("a creative | ~billboard,~", {}),
    ("we are | looking for", {}),
    ("observation,", {"hide": True}),
    ("insight", {"hide": True}),
    ("and creative | *OOH* thinking.", {}),
    ("Aur winner?", {"hide": True}),
    ("Sirf ~certificate~ | nahi.", {}),
    ("Your /idea/ could", {}),
    ("actually | come *alive*", {}),
    ("on #ADEX# #OOH# | Media,", {}),
    ("and also you", {}),
    ("get a /chance/", {}),
    ("to work with us.", {"hide": True}),
    ("If you want", {}),
    ("to show your", {}),
    ("creativity,", {"hide": True}),
    ("join us", {"hide": True}),
    ("and register now!", {"hide": True}),
]
CAP_Y = [1390, 1430, 1410, 1430, 1440, 1450]
BASE = 84


def _parse():
    groups, k = [], 0
    for gi, (mark, opt) in enumerate(GROUPS):
        lines, cur = [], []
        for tok in mark.split():
            if tok == "|":
                lines.append(cur)
                cur = []
                continue
            m = re.match(r"^([*/~^#]?)(.+?)([*/~^#]?)([.,?!]*)$", tok)
            style = m.group(1) or m.group(3)
            raw = m.group(2) + m.group(4)
            w = WORDS[k]
            assert re.sub(r"[^a-z0-9]", "", raw.lower()) == w["k"], (gi, tok, w["w"])
            disp = re.sub(r"[.,]", "", raw)
            cur.append(dict(w=w, style=style, disp=disp if style == "/" else disp.upper()))
            k += 1
        lines.append(cur)
        groups.append(dict(i=gi, lines=lines, opt=opt))
    assert k == len(WORDS)
    for gi, g in enumerate(groups):
        ws = [x for ln in g["lines"] for x in ln]
        g["s"] = ws[0]["w"]["os"] - 0.06
        nxt = groups[gi + 1]["lines"][0][0]["w"]["os"] - 0.06 if gi + 1 < len(groups) else TOTAL
        cut_at = min([tt for tt in TRANS if tt > g["s"] + 0.05] + [TOTAL])
        g["e"] = min(nxt, ws[-1]["w"]["oe"] + 0.6, cut_at)
        g["shot"] = shot_of(src_at(ws[0]["w"]["os"] + 0.01))
    return groups


CAPS = _parse()


def draw_caption(c, t, g):
    opt = g["opt"]
    if opt.get("hide"):
        return
    sizes = opt.get("sizes")
    rows = []
    for li, ln in enumerate(g["lines"]):
        size = sizes[li] if sizes else BASE
        if size == 0:
            continue
        items = []
        for x in ln:
            name, sz = ("italic", size * 1.34) if x["style"] == "/" else ("black", size)
            items.append((x, name, sz, measure(x["disp"], name, sz)))
        gap = size * 0.27
        width = sum(it[3] for it in items) + gap * (len(items) - 1)
        capH = max(metrics(n, s_)[2] for _, n, s_, _ in items)
        rows.append((items, width, gap, capH))
    sc = min(1.0, 940 / max(r[1] for r in rows))
    lead = 0.42
    total = sum(r[3] for r in rows) + sum(r[3] * lead for r in rows[:-1])
    c.save()
    c.translate(540, CAP_Y[g["shot"]])
    c.scale(sc, sc)
    y = -total / 2
    j = 0
    for items, width, gap, capH in rows:
        y += capH
        x0 = -width / 2
        for x, name, sz, wd in items:
            w = x["w"]
            kin = clamp((t - (w["os"] - 0.07)) / 0.3)
            kout = clamp((t - (g["e"] - 0.13) - j * 0.015) / 0.13)
            j += 1
            speaking = w["os"] - 0.07 <= t < w["oe"] + 0.02
            st = x["style"]
            color = ORANGE if (speaking or st in ("*", "/")) else WHITE
            if st == "#":
                bk = e_out(clamp((t - w["os"] + 0.07) / 0.28)) * (1 - e_in(kout))
                if bk > 0:
                    pad = 16
                    c.drawRRect(rrect(x0 - pad, y - capH - pad * 0.9, (wd + 2 * pad) * bk, capH + pad * 1.9, 10),
                                paint(ORANGE, 0.96))
                color = WHITE
            if st == "^" and t > w["oe"]:
                sag(c, x["disp"], x0, y, name, sz, t - w["oe"], kout)
            else:
                strike = clamp((t - w["oe"] - 0.04) / 0.22) if st == "~" else 0
                mword(c, x["disp"], x0, y, name, sz, color, kin, kout, 1 - 0.4 * strike)
                if strike > 0 and kout < 1:
                    yy = y - capH * 0.42
                    c.drawLine(x0 - 10, yy + 5, x0 - 10 + (wd + 20) * e_out(strike), yy - 5,
                               paint(ORANGE, 1 - kout, stroke=sz * 0.1))
            if speaking and st not in ("#",) and kin > 0.5 and kout == 0:
                # thin orange underline tracks the spoken word
                uk = e_out(clamp((t - w["os"] + 0.07) / 0.22))
                c.drawRRect(rrect(x0, y + 14, wd * uk, 6, 3), paint(ORANGE, 0.95))
            x0 += wd + gap
        y += capH * lead
    c.restore()


def sag(c, s, x0, base, name, size, dt, kout):
    f = font(name, size)
    x = x0
    for j, ch in enumerate(s):
        cw = f.measureText(ch)
        k = e_out(clamp((dt - j * 0.05) / 0.45))
        c.save()
        c.translate(x + cw / 2, base)
        c.rotate((7 + 9 * hrand(j, 3)) * k * (1 if j % 2 else -1))
        c.translate(-cw / 2, 24 * k * (0.6 + 0.8 * hrand(j, 9)))
        g = int(lerp(255, 120, k))
        c.drawString(ch, 2, 5, f, paint(INK, 0.5 * (1 - kout), blur=10))
        c.drawString(ch, 0, 0, f, paint(f"#{g:02X}{g:02X}{g:02X}", 1 - kout))
        c.restore()
        x += cw


def draw_captions(c, t):
    for g in CAPS:
        if g["s"] <= t < g["e"]:
            draw_caption(c, t, g)


# ================================================================== HUD (constant frame)
CHAPTERS = ["THE IDEA", "WAIT, WHAT?", "THE BRIEF", "WHAT WE WANT", "THE REWARD", "YOUR TURN"]
HUD_Y = 168


def hud(c, t, sh):
    a = e_out(clamp((t - 0.25) / 0.5)) * (1 - clamp((t - (TOTAL - 0.4)) / 0.3))
    if a <= 0:
        return
    f1, f2 = font("monob", 26), font("mono", 22)
    c.drawRect(skia.Rect.MakeXYWH(64, HUD_Y - 19, 14, 14), paint(ORANGE, a))
    c.drawString("ADEX", 90, HUD_Y - 4, f1, paint(WHITE, a))
    c.drawString("OOH CREATIVE CHALLENGE", 90 + f1.measureText("ADEX") + 14, HUD_Y - 4, f2, paint(WHITE, 0.62 * a))
    # chapter, right-aligned, re-reveals on every shot change
    t_ch = 0.25 if sh == 0 else TRANS[sh - 1]
    num, name = f"0{sh + 1}", CHAPTERS[sh]
    wn, wl = f1.measureText(num), f2.measureText(name)
    x = 1016 - wn - 14 - wl
    kin = clamp((t - t_ch - 0.08) / 0.4)
    nxt = TRANS[sh] if sh < len(TRANS) else None
    kout = clamp((t - (nxt - 0.16)) / 0.14) if nxt else 0
    mword(c, num, x, HUD_Y - 4, "monob", 26, ORANGE, kin, kout, a, shadow=False)
    mword(c, name, x + wn + 14, HUD_Y - 4, "mono", 22, WHITE, clamp(kin * 1.2 - 0.15), kout, a, shadow=False)
    # progress hairline
    c.drawRect(skia.Rect.MakeLTRB(64, HUD_Y + 18, 1016, HUD_Y + 21), paint(WHITE, 0.2 * a))
    c.drawRect(skia.Rect.MakeLTRB(64, HUD_Y + 18, 64 + 952 * clamp(t / TOTAL), HUD_Y + 21), paint(ORANGE, a))


# ================================================================== word-locked motion graphics
def fade_io(t, t0, t1, din=0.25, dout=0.18):
    return e_out(clamp((t - t0) / din)) * (1 - e_in(clamp((t - (t1 - dout)) / dout)))


# ---- shot 1 (idea, where, ADEX, OOH billboard)
def g_bulb(c, t):
    t0, t1 = os_(5) - 0.08, os_(8)
    if not t0 <= t < t1:
        return
    k = clamp((t - t0) / 0.55)
    a = 1 - e_in(clamp((t - (t1 - 0.2)) / 0.2))
    cx, cy = 830, 360
    s_ = pop(clamp((t - t0) / 0.4))
    c.save()
    c.translate(cx, cy)
    c.scale(s_, s_)
    c.drawCircle(0, 0, 118, paint(ORANGE, 0.16 * a, blur=30))
    glass(c, -98, -98, 196, 196, r=98, a=a, border=ORANGE, border_a=0.85, bw=3)
    icon(c, "bulb", 0, -2, 124, k, ORANGE, a, width=6)
    c.restore()
    rk = clamp((t - t0 - 0.35) / 0.4)                  # rays burst once
    if 0 < rk < 1:
        for j in range(8):
            ang = j * math.pi / 4 - math.pi / 8
            r0, r1 = lerp(120, 150, e_out(rk)), lerp(130, 190, e_out(rk))
            c.drawLine(cx + r0 * math.cos(ang), cy + r0 * math.sin(ang), cx + r1 * math.cos(ang),
                       cy + r1 * math.sin(ang), paint(ORANGE, (1 - rk) * a, stroke=6))
    kblock(c, t, [[T("IDEA", os_(5), 56, WHITE, "monob")]], cx, cy + 150, t_out=t1 - 0.2)


PINS = [(760, 330, 0.0, 120), (950, 560, 0.12, 96), (790, 790, 0.24, 108)]


def g_pins(c, t):
    t0, t1 = os_(13) - 0.05, os_(16) - 0.06
    if not t0 <= t < t1:
        return
    a = 1 - e_in(clamp((t - (t1 - 0.16)) / 0.16))
    for j, (x, y, d, s) in enumerate(PINS):
        k = clamp((t - t0 - d) / 0.4)
        if k <= 0:
            continue
        drop = (1 - e_back(k, 2.0)) * -120
        c.drawOval(skia.Rect.MakeXYWH(x - 26, y + s * 0.45, 52, 12), paint(INK, 0.4 * a * k, blur=6))
        c.save()
        c.translate(x, y + drop)
        c.drawCircle(0, -s * 0.12, s * 0.42, paint(GLASS, 0.6 * a))
        icon(c, "pin", 0, 0, s, 1.0, ORANGE, a, width=7)
        c.restore()
        q = clamp((t - t0 - d - 0.3) / 0.3)            # little "?" above each pin
        if q > 0:
            f = font("anton", 64)
            c.save()
            c.translate(x + s * 0.32, y - s * 0.55 + drop)
            sc = pop(q)
            c.scale(sc, sc)
            c.drawString("?", 0, 0, f, paint(INK, 0.5 * a, blur=8))
            c.drawString("?", 0, 0, f, paint(WHITE, a * clamp(q * 3)))
            c.restore()


def g_adex(c, t):                                       # behind the speaker
    t0, t1 = os_(16) - 0.08, os_(21) - 0.02
    if not t0 <= t < t1:
        return
    kblock(c, t, [[T("isliye", os_(16) - 0.05, 120, ORANGE, "italic")],
                  [T("ADEX", os_(17) - 0.06, 270, WHITE)]], 770, 390, t_out=t1 - 0.18)


def billboard(c, x, y, w, h, k, a=1.0, legs=None, lit=0.0, flicker=1.0):
    """big OOH billboard: frame draws itself on, panel fades in, optional legs down to y=legs."""
    if k <= 0:
        return
    pk = clamp(k * 1.6 - 0.5)
    c.drawRRect(rrect(x, y, w, h, 18), paint(INK, 0.35 * a * pk, blur=28))
    c.drawRRect(rrect(x, y, w, h, 18), paint(GLASS, 0.78 * a * pk))
    if lit > 0:
        c.drawRRect(rrect(x - 6, y - 6, w + 12, h + 12, 22), paint(ORANGE, 0.45 * lit * a * flicker, blur=36))
    path = skia.Path()
    path.addRRect(rrect(x, y, w, h, 18))
    if legs:
        for lx in (x + w * 0.28, x + w * 0.72):
            path.moveTo(lx, y + h)
            path.lineTo(lx, legs)
    p = paint(ORANGE, a, stroke=6)
    trim(p, e_io(clamp(k)))
    c.drawPath(path, p)
    # spotlight lamps on top
    if pk > 0:
        for lx in (x + w * 0.2, x + w * 0.5, x + w * 0.8):
            c.drawRRect(rrect(lx - 18, y - 22, 36, 12, 4), paint(WHITE, 0.8 * a * pk))


def g_ooh(c, t):                                        # behind the speaker, right of her head
    t0, t1 = os_(21) + 0.05, os_(25) - 0.04
    if not t0 <= t < t1:
        return
    k = clamp((t - t0) / 0.5)
    a = 1 - e_in(clamp((t - (t1 - 0.18)) / 0.18))
    x, y, w, h = 420, 230, 610, 330
    billboard(c, x, y, w, h, k, a, legs=820, lit=clamp((t - os_(22)) / 0.3) * (0.7 + 0.3 * math.sin(t * 9)))
    kblock(c, t, [[T("OOH", os_(22) - 0.04, 250, ORANGE, glow=True)]], x + w * 0.6, y + h / 2, t_out=t1 - 0.18)


# ---- shot 2 (the man)
def g_man(c, t):
    t0, t1 = os_(29) - 0.08, TRANS[1]
    if not t0 <= t < t1:
        return
    mid = os_(31) - 0.08
    if t < mid:
        kblock(c, t, [[T("BORING", os_(29) - 0.06, 190, WHITE)], [T("BRAND?", os_(30) - 0.06, 190, ORANGE)]],
               540, 330, t_out=mid - 0.16)
    else:
        kblock(c, t, [[T("YEH", os_(31) - 0.06, 250, WHITE), T("KYA?", os_(32) - 0.06, 250, ORANGE, glow=True)]],
               540, 400, t_out=t1 - 0.16)
        # reaction burst around his head
        k = clamp((t - os_(31)) / 0.35)
        hx, hy = ANCHOR[1][0], ANCHOR[1][1] - 40
        for j, ang in enumerate((-160, -132, -48, -20)):
            r = math.radians(ang)
            kk = clamp(k * 1.4 - j * 0.08)
            if kk <= 0:
                continue
            r0, r1 = 210 + 20 * e_out(kk), 210 + 90 * e_out(kk)
            c.drawLine(hx + r0 * math.cos(r), hy + r0 * math.sin(r), hx + r1 * math.cos(r), hy + r1 * math.sin(r),
                       paint(ORANGE, 1 - clamp((t - t1 + 0.2) / 0.2), stroke=10))


# ---- shot 3 (the brief)
def g_ruko(c, t):
    t0, t1 = os_(33) - 0.08, os_(35) + 0.12
    if not t0 <= t < t1:
        return
    kblock(c, t, [[T("RUKO", os_(33) - 0.06, 230, WHITE)],
                  [T("RUKO,", os_(34) - 0.06, 230, ORANGE, glow=True)]], 540, 400, t_out=t1 - 0.16)


CARDS = [(40, "CITY", "city"), (43, "BRAND", "tag"), (44, "PRODUCT", "box"), (46, "LOCATION", "pin")]


def g_cards(c, t):
    t0, t1 = os_(40) - 0.12, os_(47) - 0.02
    if not t0 <= t < t1:
        return
    out = clamp((t - (t1 - 0.22)) / 0.22)
    for j, (wi, label, ic) in enumerate(CARDS):
        x, y = (70, 555)[j % 2], (200, 418)[j // 2]
        k = clamp((t - (os_(wi) - 0.1)) / 0.35)
        if k <= 0:
            continue
        a = clamp(k * 3) * (1 - e_in(clamp(out * 1.3 - j * 0.08)))
        c.save()
        c.translate(x + 227, y + 98 + 40 * (1 - e_out5(k)) - 40 * e_in(out))
        sc = lerp(0.92, 1.0, e_out5(k))
        c.scale(sc, sc)
        glass(c, -227, -98, 455, 196, a=a, border=ORANGE if os_(wi) - 0.1 <= t < oe_(wi) + 0.2 else WHITE,
              border_a=0.9 if os_(wi) - 0.1 <= t < oe_(wi) + 0.2 else 0.22)
        c.drawString(f"0{j + 1}", -195, -50, font("monob", 26), paint(ORANGE, a))
        icon(c, ic, -138, 18, 92, clamp(k * 1.3), ORANGE, a, width=7)
        c.drawString(label, -70, 42, font("anton", 78), paint(WHITE, a))
        c.restore()


def g_radar(c, t):
    t0, t1 = os_(47) - 0.08, os_(60) - 0.06
    if not t0 <= t < t1:
        return
    a = fade_io(t, t0, t1, 0.3, 0.2)
    cx, cy, R = 540, 390, 200
    c.drawCircle(cx, cy, R + 30, paint(GLASS, 0.55 * a))
    for r in (R, R * 0.66, R * 0.33):
        c.drawCircle(cx, cy, r, paint(WHITE, 0.22 * a, stroke=2))
    c.drawLine(cx - R, cy, cx + R, cy, paint(WHITE, 0.14 * a, stroke=2))
    c.drawLine(cx, cy - R, cx, cy + R, paint(WHITE, 0.14 * a, stroke=2))
    for j in range(2):                                  # pulse rings
        q = ((t - t0) * 0.9 + j * 0.5) % 1
        c.drawCircle(cx, cy, R * q, paint(ORANGE, 0.55 * (1 - q) * a, stroke=4))
    if t >= os_(55) - 0.1:                              # "already kya chal raha hai": sweep + live blips
        ang = (t - os_(55)) * 4.2
        sweep = skia.Path()
        sweep.moveTo(cx, cy)
        sweep.arcTo(skia.Rect.MakeLTRB(cx - R, cy - R, cx + R, cy + R), math.degrees(ang) - 40, 40, False)
        sweep.close()
        c.drawPath(sweep, paint(ORANGE, 0.28 * a))
        c.drawLine(cx, cy, cx + R * math.cos(ang), cy + R * math.sin(ang), paint(ORANGE, a, stroke=4))
        for j, (bx, by) in enumerate(((-110, -60), (80, -120), (130, 70), (-60, 120), (20, 40))):
            q = clamp((t - os_(55) - j * 0.12) / 0.25)
            if q > 0:
                c.drawCircle(cx + bx, cy + by, 10 + 8 * math.sin(t * 8 + j) ** 2, paint(ORANGE, 0.35 * a * q, blur=6))
                c.drawCircle(cx + bx, cy + by, 8 * pop(q), paint(WHITE, a * q))
    # pin drops on "city", relabels on "location"
    k = clamp((t - (os_(50) - 0.06)) / 0.4)
    if k > 0:
        c.save()
        c.translate(cx, cy - 46 + (1 - e_back(k, 2.0)) * -90)
        icon(c, "pin", 0, 0, 104, 1.0, ORANGE, a, width=8)
        c.restore()
        lab = "LOCATION" if t >= os_(53) - 0.06 else "CITY"
        tl = os_(53) - 0.06 if lab == "LOCATION" else os_(50) - 0.06
        kblock(c, t, [[T(lab, tl, 44, WHITE, "monob")]], cx, cy + R + 66,
               t_out=(os_(53) - 0.2) if lab == "CITY" else t1 - 0.2)
    kl = clamp((t - os_(55) + 0.1) / 0.3)
    if kl > 0:
        c.drawCircle(cx - R - 4, cy - R + 12, 9, paint(ORANGE, a * (0.6 + 0.4 * math.sin(t * 10))))
        mword(c, "LIVE", cx - R + 16, cy - R + 21, "monob", 28, WHITE, kl, 0, a, shadow=False)


def pill(c, cx, cy, w, h, label, ic, k, active, a=1.0):
    if k <= 0:
        return
    c.save()
    c.translate(cx, cy + 30 * (1 - e_out5(k)))
    sc = pop(k)
    c.scale(sc, sc)
    glass(c, -w / 2, -h / 2, w, h, r=h / 2, a=a * clamp(k * 3), border=ORANGE if active else WHITE,
          border_a=0.95 if active else 0.25, bw=3)
    icon(c, ic, -w / 2 + h * 0.55, 0, h * 0.6, clamp(k * 1.4), ORANGE, a, width=8)
    f = font("anton", h * 0.42)
    c.drawString(label, -w / 2 + h * 1.0, h * 0.15, f, paint(WHITE, a * clamp(k * 3)))
    c.restore()


def g_flow(c, t):
    t0, t1 = os_(60) - 0.06, TRANS[2]
    if not t0 <= t < t1:
        return
    a = 1 - e_in(clamp((t - (t1 - 0.2)) / 0.2))
    y = 400
    pill(c, 285, y, 400, 140, "INSIGHT", "bulb", clamp((t - os_(62) + 0.1) / 0.35),
         os_(62) - 0.1 <= t < os_(67), a)
    ka = clamp((t - os_(64)) / 0.6)                      # "turn ... into": arrow draws across
    if ka > 0:
        x0, x1 = 497, 590
        c.drawLine(x0, y, lerp(x0, x1, e_io(ka)), y, paint(ORANGE, a, stroke=8))
        if ka >= 1:
            path = skia.Path()
            path.moveTo(x1 - 22, y - 20)
            path.lineTo(x1 + 2, y)
            path.lineTo(x1 - 22, y + 20)
            c.drawPath(path, paint(ORANGE, a, stroke=8))
    pill(c, 810, y, 420, 140, "OOH IDEA", "billboard", clamp((t - os_(69) + 0.1) / 0.35), t >= os_(69) - 0.1, a)
    if t >= os_(70):                                     # "idea": glow pulse
        q = clamp((t - os_(70)) / 0.5)
        c.drawRRect(rrect(600 - 10 * q, y - 70 - 10 * q, 420 + 20 * q, 140 + 20 * q, 80), paint(ORANGE, (1 - q) * a, stroke=5))


# ---- shot 4 (what we want)
def g_billboard_x(c, t):
    t0, t1 = os_(76) - 0.05, os_(79) + 0.25
    if not t0 <= t < t1:
        return
    a = 1 - e_in(clamp((t - (t1 - 0.18)) / 0.18))
    k = clamp((t - t0) / 0.5)
    c.save()
    c.translate(540, 290)
    c.scale(1.0, 1.0)
    path = ICONS["billboard"]
    c.translate(-150, -100)
    c.scale(3.0, 2.0)
    p = paint(WHITE, a, stroke=3)
    trim(p, e_io(k))
    c.drawRect(skia.Rect.MakeLTRB(6, 10, 94, 60), paint(GLASS, 0.6 * a * k))
    c.drawPath(path, p)
    c.restore()
    s = clamp((t - oe_(78) + 0.12) / 0.22)               # crossed out as "billboard" lands
    if s > 0:
        c.drawLine(380, 200, lerp(380, 700, e_out(s)), lerp(200, 350, e_out(s)), paint(ORANGE, a, stroke=12))
        s2 = clamp(s * 1.4 - 0.4)
        if s2 > 0:
            c.drawLine(700, 200, lerp(700, 380, e_out(s2)), lerp(200, 350, e_out(s2)), paint(ORANGE, a, stroke=12))


TRIO = [(83, "OBSERVATION", "eye"), (84, "INSIGHT", "bulb"), (87, "OOH THINKING", "billboard")]


def g_trio(c, t):
    t0, t1 = os_(83) - 0.1, TRANS[3]
    if not t0 <= t < t1:
        return
    a = 1 - e_in(clamp((t - (t1 - 0.2)) / 0.2))
    for j, (wi, label, ic) in enumerate(TRIO):
        cx = 190 + j * 350
        k = clamp((t - (os_(wi) - 0.1)) / 0.4)
        if k <= 0:
            continue
        active = os_(wi) - 0.1 <= t < oe_(wi) + 0.15
        c.save()
        c.translate(cx, 236)
        sc = pop(k)
        c.scale(sc, sc)
        c.drawCircle(0, 0, 56, paint(GLASS, 0.75 * a))
        c.drawCircle(0, 0, 56, paint(ORANGE if active else WHITE, (0.95 if active else 0.3) * a, stroke=3))
        icon(c, ic, 0, 0, 64, clamp(k * 1.3), ORANGE, a, width=7.5)
        c.restore()
        kblock(c, t, [[T(label, os_(wi) - 0.05, 40, WHITE)]], cx, 330, t_out=t1 - 0.2)


# ---- shot 5 (the reward)
def g_winner(c, t):
    t0, t1 = os_(89) - 0.08, os_(91) - 0.04
    if not t0 <= t < t1:
        return
    kblock(c, t, [[T("aur", os_(89) - 0.06, 130, ORANGE, "italic")],
                  [T("WINNER", os_(90) - 0.06, 290, WHITE), T("?", os_(90) + 0.2, 290, ORANGE, glow=True)]],
           540, 520, t_out=t1 - 0.16)


def g_certificate(c, t):
    t0, t1 = os_(91) - 0.06, os_(94) - 0.04
    if not t0 <= t < t1:
        return
    k = clamp((t - (os_(92) - 0.12)) / 0.45)
    if k <= 0:
        return
    out = clamp((t - (t1 - 0.2)) / 0.2)
    a = 1 - e_in(out)
    c.save()
    c.translate(540, 470 + (1 - e_out5(k)) * 160 - 120 * e_in(out))
    c.rotate(-4 + 8 * e_in(out))
    c.drawRRect(rrect(-270, -180, 540, 360, 14), paint(INK, 0.4 * a, blur=26))
    c.drawRRect(rrect(-270, -180, 540, 360, 14), paint("#F6F3EE", 0.97 * a * clamp(k * 3)))
    c.drawRRect(rrect(-250, -160, 500, 320, 8), paint(ORANGE, 0.8 * a, stroke=3))
    f = font("monob", 30)
    s = "CERTIFICATE"
    c.drawString(s, -f.measureText(s) / 2, -86, f, paint(INK, a))
    for j, ww in enumerate((330, 260, 300)):
        c.drawRRect(rrect(-ww / 2, -36 + j * 40, ww, 10, 5), paint("#C9C4BB", a))
    c.drawCircle(150, 104, 44, paint(ORANGE, a))
    c.drawCircle(150, 104, 30, paint(WHITE, 0.6 * a, stroke=3))
    c.restore()
    s = clamp((t - os_(93) + 0.04) / 0.22)               # "nahi": crossed out
    if s > 0:
        yy = 470 - 120 * e_in(out)
        c.drawLine(250, yy - 150, lerp(250, 830, e_out(s)), lerp(yy - 150, yy + 150, e_out(s)), paint(ORANGE, a, stroke=16))


def g_alive(c, t):                                      # billboard rises behind her and powers on
    t0, t1 = os_(94) - 0.06, os_(104) - 0.06
    if not t0 <= t < t1:
        return
    k = clamp((t - t0) / 0.6)
    a = 1 - e_in(clamp((t - (t1 - 0.2)) / 0.2))
    x, y, w, h = 110, 220 + 80 * (1 - e_out5(k)), 860, 420
    on = clamp((t - (os_(99) - 0.05)) / 0.35)
    flick = 1.0 if on >= 1 else (0.3 if int(t * 30) % 3 == 0 else 1.0)
    billboard(c, x, y, w, h, k, a, legs=900, lit=on, flicker=flick)
    dim = 0.35 + 0.65 * on * flick
    kblock(c, t, [[T("YOUR", os_(94) - 0.04, 170, WHITE), T("IDEA", os_(95) - 0.04, 170, ORANGE, glow=on > 0)]],
           x + w / 2, y + h / 2 - 20, t_out=t1 - 0.18, a=dim)
    if t >= os_(101) - 0.08:                             # "on ADEX OOH Media": the media plate
        kp = clamp((t - os_(101) + 0.08) / 0.3)
        pw = 560
        c.drawRRect(rrect(540 - pw / 2 * e_out(kp), y + h + 26, pw * e_out(kp), 64, 32), paint(ORANGE, a))
        if kp > 0.5:
            f = font("monob", 30)
            s = "ADEX OOH MEDIA"
            c.drawString(s, 540 - f.measureText(s) / 2, y + h + 69, f, paint(INK, a * clamp(kp * 2 - 1)))


def g_work(c, t):
    t0, t1 = os_(110) - 0.08, TRANS[4]
    if not t0 <= t < t1:
        return
    kblock(c, t, [[T("to", os_(110) - 0.05, 110, ORANGE, "italic"), T("WORK", os_(111) - 0.05, 250, WHITE)],
                  [T("WITH", os_(112) - 0.05, 250, WHITE), T("US", os_(113) - 0.05, 250, ORANGE, glow=True)]],
           540, 470, t_out=t1 - 0.18)


# ---- shot 6 (your turn)
def g_creativity(c, t):
    t0, t1 = os_(120) - 0.08, os_(121) - 0.04
    if not t0 <= t < t1:
        return
    kblock(c, t, [[T("creativity", os_(120) - 0.06, 230, ORANGE, "italic", glow=True)]], 540, 520, t_out=t1 - 0.14)
    for j, (sx, sy) in enumerate(((180, 380), (900, 430), (820, 650), (250, 640))):
        q = clamp((t - os_(120) - 0.15 - j * 0.1) / 0.45)
        if 0 < q < 1:
            r = 26 * math.sin(math.pi * q)
            path = skia.Path()
            path.moveTo(sx, sy - r)
            path.quadTo(sx, sy, sx + r, sy)
            path.quadTo(sx, sy, sx, sy + r)
            path.quadTo(sx, sy, sx - r, sy)
            path.quadTo(sx, sy, sx, sy - r)
            c.drawPath(path, paint(WHITE if j % 2 else ORANGE))


def g_join(c, t):
    t0, t1 = os_(121) - 0.08, os_(123) - 0.02
    if not t0 <= t < t1:
        return
    kblock(c, t, [[T("JOIN", os_(121) - 0.06, 330, WHITE), T("US", os_(122) - 0.06, 330, ORANGE, glow=True)]],
           540, 560, t_out=t1 - 0.16)


REG, NOW = WORDS[124], WORDS[125]


def g_cta(c, t):
    t0 = os_(123) - 0.06
    if t < t0:
        return
    kblock(c, t, [[T("ADEX", t0, 190, WHITE)],
                  [T("OOH CREATIVE CHALLENGE", t0 + 0.12, 44, ORANGE, "monob")]], 540, 520, lead=0.9)
    k = clamp((t - REG["os"] + 0.1) / 0.4)
    if k <= 0:
        return
    y = 1470
    click = NOW["oe"] - 0.1
    press = 1 - 0.07 * math.sin(math.pi * clamp((t - click) / 0.22))
    label = "REGISTER NOW"
    f = font("black", 60)
    tw = f.measureText(label)
    bw, bh = tw + 170, 136
    c.save()
    c.translate(540, y)
    sc = pop(k) * press
    c.scale(sc, sc)
    r = rrect(-bw / 2, -bh / 2, bw, bh, bh / 2)
    pulse = 0.5 + 0.5 * math.sin((t - REG["os"]) * 6)
    c.drawRRect(r, paint(ORANGE, 0.3 + 0.25 * pulse, blur=34))
    c.drawRRect(r, paint(ORANGE))
    c.drawString(label, -bw / 2 + 56, metrics("black", 60)[2] / 2, f, paint(WHITE))
    ax = bw / 2 - 70 + 8 * math.sin((t - REG["os"]) * 7)
    c.drawLine(ax - 30, 0, ax + 6, 0, paint(WHITE, stroke=9))
    path = skia.Path()
    path.moveTo(ax - 12, -18)
    path.lineTo(ax + 7, 0)
    path.lineTo(ax - 12, 18)
    c.drawPath(path, paint(WHITE, stroke=9))
    c.restore()
    if t >= click:
        q = clamp((t - click) / 0.5)
        c.drawRRect(rrect(540 - bw / 2 - 40 * q, y - bh / 2 - 40 * q, bw + 80 * q, bh + 80 * q, bh / 2 + 40 * q),
                    paint(WHITE, 0.7 * (1 - q), stroke=6))
    kc = e_io(clamp((t - (click - 0.55)) / 0.5))
    if kc > 0:
        cx, cy = lerp(920, 650, kc), lerp(1780, y + 22, kc)
        if t >= click:
            cy += 6 * math.sin(math.pi * clamp((t - click) / 0.2))
        cursor(c, cx, cy)


def cursor(c, x, y):
    path = skia.Path()
    pts = [(0, 0), (0, 64), (16, 49), (28, 76), (40, 71), (28, 45), (49, 45)]
    path.moveTo(*pts[0])
    for p in pts[1:]:
        path.lineTo(*p)
    path.close()
    c.save()
    c.translate(x, y)
    c.drawPath(path, paint(INK, 0.5, blur=6))
    c.drawPath(path, paint(WHITE))
    c.drawPath(path, paint(INK, stroke=4))
    c.restore()


BEHIND = [g_adex, g_ooh, g_billboard_x, g_trio, g_winner, g_alive]          # under the person matte
FRONT = [g_bulb, g_pins, g_man, g_ruko, g_cards, g_radar, g_flow, g_certificate, g_work, g_creativity, g_join, g_cta]
BEHIND_SPANS = [(os_(16) - 0.1, os_(25)), (os_(76) - 0.1, os_(79) + 0.3), (os_(83) - 0.12, TRANS[3]),
                (os_(89) - 0.1, os_(91)), (os_(94) - 0.1, os_(104))]


# ================================================================== camera
PUNCH = [
    (os_(17), oe_(17) + 0.15, 1.08),          # ADEX
    (os_(29), oe_(30), 1.12),                 # Boring brand?
    (os_(31), oe_(32) + 0.4, 1.22),           # Yeh kya?
    (os_(55), oe_(55), 1.06),                 # already
    (os_(90), oe_(90) + 0.2, 1.08),           # winner?
    (os_(121), oe_(122), 1.07),               # join us
]
SHAKES = [(os_(31), 8), (os_(33), 6), (os_(34), 6)]


def camera(t):
    k = seg_at(t)
    a, b, o = EDL[k]
    sh = shot_of(a)
    first = next(j for j, s in enumerate(EDL) if shot_of(s[0]) == sh)
    z = (1.0, 1.075)[(k - first) % 2]
    z *= 1 + 0.01 * (t - o)
    if t < 0.5:
        z *= lerp(1.12, 1.0, e_out(t / 0.5))
    for tt in TRANS:                                       # settle after each slab wipe
        if tt <= t < tt + 0.45:
            z *= lerp(1.07, 1.0, e_out((t - tt) / 0.45))
    for t0, t1, zz in PUNCH:
        if t0 - 0.12 <= t < t1 + 0.18:
            z *= lerp(1.0, zz, e_out(clamp((t - t0 + 0.12) / 0.16)) * (1 - e_io(clamp((t - t1) / 0.18))))
    dx = dy = rot = 0.0
    for st, amp in SHAKES:
        if st <= t < st + 0.3:
            q = 1 - (t - st) / 0.3
            dx += amp * q * math.sin(t * 95.0)
            dy += amp * q * math.sin(t * 71.0 + 1.3)
            rot += amp * 0.05 * q * math.sin(t * 61.0)
    return z, dx, dy, rot, 0.0


def slab(c, t):
    """orange slab wipe across each shot change: rises to cover, then exits through the top."""
    for tt in TRANS:
        if tt - 0.17 <= t < tt:
            p = e_in((t - (tt - 0.17)) / 0.17)
            y0, y1 = H * (1 - p), H
        elif tt <= t < tt + 0.2:
            p = e_out((t - tt) / 0.2)
            y0, y1 = 0, H * (1 - p)
        else:
            continue
        c.drawRect(skia.Rect.MakeLTRB(0, y0, W, y1), paint(ORANGE))
        edge = y0 if t < tt else y1
        c.drawRect(skia.Rect.MakeLTRB(0, edge - 5, W, edge + 5), paint(WHITE, 0.9))


# ================================================================== frame
def _lut():
    x = np.arange(256, dtype=np.float32) / 255
    s = x + 0.06 * np.sin(2 * math.pi * (x - 0.5))
    s = np.clip((s - 0.015) / 0.98, 0, 1)
    r = np.clip(s * 1.025, 0, 1)
    b = np.clip(s * 0.965 + 0.012, 0, 1)
    return np.stack([(np.clip(ch, 0, 1) * 255).astype(np.uint8) for ch in (r, s, b)], -1)[:, None, :]


LUT = _lut()


def grade(rgb, sat=1.06):
    f = cv2.LUT(rgb, LUT).astype(np.float32)
    lum = f @ np.array([0.299, 0.587, 0.114], np.float32)
    f = lum[..., None] + (f - lum[..., None]) * sat
    return np.clip(f, 0, 255).astype(np.uint8)


def draw(c, t, f):
    ts = src_at(t)
    fi = int(round(ts * FPS))
    sh = shot_of(ts)
    anchor = ANCHOR[sh]
    rgb = grade(frame_rgb(fi))
    cam = camera(t)
    samp = skia.SamplingOptions(skia.FilterMode.kLinear)
    c.save()
    apply_cam(c, cam, anchor)
    c.drawImage(rgba_img(rgb), 0, 0, samp)
    c.restore()
    if any(a <= t < b for a, b in BEHIND_SPANS):
        for g in BEHIND:
            g(c, t)
        al = cv2.resize(alpha_small(fi), (W, H), interpolation=cv2.INTER_LINEAR)
        c.save()
        apply_cam(c, cam, anchor)
        c.drawImage(rgba_img(rgb, al), 0, 0, samp)
        c.restore()
    for g in FRONT:
        g(c, t)
    draw_captions(c, t)
    hud(c, t, sh)
    slab(c, t)
    if t < 0.1 or t > TOTAL - 0.35:
        k = clamp(t / 0.1) if t < 0.1 else clamp((TOTAL - t) / 0.35)
        c.drawRect(skia.Rect.MakeWH(W, H), paint(INK, 1 - k))
    return {}


VIG = None


def post(arr, g, f):
    global VIG
    if VIG is None:
        yy, xx = np.mgrid[0:arr.shape[0], 0:arr.shape[1]].astype(np.float32)
        r = np.sqrt(((xx - arr.shape[1] / 2) / (arr.shape[1] / 2)) ** 2 + ((yy - arr.shape[0] / 2) / (arr.shape[0] / 2)) ** 2)
        VIG = (1 - 0.2 * np.clip(r - 0.5, 0, None) ** 1.5)[..., None].astype(np.float32)
    return kit.grain(np.clip(arr * VIG, 0, 255).astype(np.uint8), f, amt=0.014)


FILM = kit.Film(draw, TOTAL, FPS, post=post, out_dir=OUT)


# ================================================================== audio
def sfx_list():
    S = []

    def a(t, kind, gain=-8, **kw):
        S.append(dict(t=t, kind=kind, gain_db=gain, **kw))

    a(0.0, "swish", -14)
    for tt in TRANS:
        a(tt - 0.24, "whoosh", -11, dur=0.42)
    a(os_(5) + 0.25, "sparkle", -17)                     # bulb
    for j, (_, _, d, _) in enumerate(PINS):
        a(os_(13) + d + 0.15, "pop", -13)
    a(os_(16) - 0.05, "swish", -14)                      # isliye
    a(os_(17) - 0.04, "impact", -14)                     # ADEX
    a(os_(21) + 0.05, "swish", -13)                      # billboard draws
    a(os_(22), "ding", -18)                              # lamps on
    a(oe_(27) + 0.05, "downlifter", -15)                 # boring drains
    a(os_(29) - 0.05, "swish", -11)
    a(os_(30) - 0.05, "pop", -12)
    a(os_(31) - 0.03, "glitch", -16)
    a(os_(33) - 0.04, "tick", -9)
    a(os_(34) - 0.04, "tick", -9)
    for wi, _, _ in CARDS:
        a(os_(wi) - 0.08, "pop", -12)
    a(os_(50) - 0.04, "pop", -12)                        # pin drop
    for j in range(4):
        a(os_(55) + j * 0.32, "tick", -19)               # radar sweep
    a(os_(62) - 0.08, "pop", -12)
    a(os_(64), "whoosh", -17, dur=0.5)                   # arrow
    a(os_(69) - 0.08, "pop", -12)
    a(os_(70), "ding", -17)
    a(oe_(78) - 0.1, "swish", -12)                       # billboard crossed
    for wi, _, _ in TRIO:
        a(os_(wi) - 0.08, "pop", -12)
    a(os_(90) - 1.0, "riser", -17, dur=1.0)
    a(os_(90) - 0.05, "impact", -12)                     # WINNER
    a(os_(92) - 0.1, "swish", -13)                       # certificate drops
    a(os_(93) - 0.02, "swish", -12)                      # crossed
    a(os_(94) - 0.05, "whoosh", -15, dur=0.6)            # billboard rises
    a(os_(99) - 0.05, "glitch", -19)                     # power-on flicker
    a(os_(99) + 0.25, "sparkle", -16)
    a(os_(101) - 0.06, "pop", -13)                       # media plate
    a(os_(111) - 0.05, "swish", -13)
    a(os_(113) - 0.05, "impact", -16)
    a(os_(120), "sparkle", -15)
    a(os_(121) - 0.05, "impact", -13)                    # JOIN US
    a(os_(123) - 0.05, "swish", -13)
    a(REG["os"] - 0.08, "pop", -9)
    a(NOW["oe"] - 0.1, "click", -6)
    return S


def build_audio():
    SR = ak.SR
    work = HERE / "work"
    vpath = work / "voice_clean.wav"
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
    music = ak.music_bed("tech", seconds=TOTAL + 0.5, bpm=120, key="A", intro_bars=1, seed=5)[:n]
    music = np.pad(music, ((0, n - len(music)), (0, 0)))
    mix = voice + music * ak.db(-16) * ak.duck_gain(voice, depth_db=-9)[:, None]
    for s in sfx_list():
        clip = ak.SFX[s["kind"]](s["dur"]) if "dur" in s else ak.SFX[s["kind"]]()
        ak.place(mix, clip, s["t"], s["gain_db"])
    fo = int(0.5 * SR)
    mix[-fo:] *= np.linspace(1, 0, fo)[:, None]
    peak = np.max(np.abs(mix)) or 1
    if peak > 0.98:
        mix = np.tanh(mix / peak * 1.2) / math.tanh(1.2) * 0.98
    out = work / "mix_v2.wav"
    ak.write_wav(out, mix)
    print("->", out)
    return out


def finish(picture, audio, out):
    ln = loudnorm_filter(audio)
    ff("-i", str(picture), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "slow",
       "-crf", "18", "-maxrate", "14M", "-bufsize", "28M", "-pix_fmt", "yuv420p", "-profile:v", "high", "-af", ln,
       "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out))
    print("->", out)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "stills":
        FILM.out_dir = OUT / "v2"
        FILM.stills([float(x) for x in sys.argv[2:]])
    elif cmd == "sheet":
        FILM.sheet([round(TOTAL * (i + 0.5) / 40, 2) for i in range(40)], cols=8, name="sheet_v2.png")
    elif cmd == "audio":
        build_audio()
    elif cmd == "render":
        draft = "--draft" in sys.argv
        pic = FILM.render(OUT / ("draft_v2_picture.mp4" if draft else "picture_v2.mp4"), draft=draft)
        aud = build_audio()
        finish(pic, aud, OUT / ("draft_v2.mp4" if draft else "adex_ooh_premium.mp4"))


if __name__ == "__main__":
    main()
