"""style: the "floating UI" look, rebuilt from the reference reel's cover frame.

Real room footage with a moody, cool cinematic grade; clean app-UI components (toggles, pill buttons, sliders,
segmented controls, round icon buttons, lime and lavender cards) floating in the space above the speaker; captions
as a white handwritten caps line over a wide heavy italic yellow keyword with a black hand-drawn scribble under it.
Fonts are free stand-ins: Shadows Into Light (widened) for the handwriting, Syne ExtraBold slanted for the wide
keyword, Inter for UI text, JetBrains Mono for code.
"""

import math
import sys
from functools import lru_cache
from pathlib import Path

import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "reels" / "common"))
import kit  # noqa: E402
from kit import clamp, e_in, e_io, e_out, fill, hrand, lerp, prog, rrect, spring, stroke  # noqa: E402,F401

F = HERE / "fonts"
FONT_FILES = {"hand": "ShadowsIntoLight.ttf", "wide": "Syne-ExtraBold.ttf", "ui": "Inter-Medium.ttf",
              "uib": "Inter-Bold.ttf", "mono": "JetBrainsMono-Medium.ttf"}
_TF = {}

# ---------------------------------------------------------------- palette (sampled from the reference)
YEL = "#FFE500"        # keyword yellow
LIME = "#BDF22B"       # lime card
GREEN = "#2FD64A"      # toggle / continue green
LAV = "#C5B4F2"        # lavender card
PURPLE = "#9B7CF0"
BLUE = "#1F6BFF"
INK = "#0B0B0D"
WHITE = "#FFFFFF"
GREYUI = "#8E9196"
RED = "#FF4D4D"
SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNone)


def font(name, size):
    if name not in _TF:
        _TF[name] = skia.Typeface.MakeFromFile(str(F / FONT_FILES[name]))
    f = skia.Font(_TF[name], size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    f.setSubpixel(True)
    f.setLinearMetrics(True)
    if name == "wide":
        f.setSkewX(-0.2)
    if name == "hand":
        f.setScaleX(1.18)
    return f


def measure(s, name, size):
    return font(name, size).measureText(s)


def text(c, s, x, y, name, size, color=WHITE, a=1.0, anchor="l", shadow=False):
    w = measure(s, name, size)
    x0 = x - w / 2 if anchor == "c" else x - w if anchor == "r" else x
    f = font(name, size)
    if shadow:
        c.drawString(s, x0, y + size * 0.04, f, fill("#000000", 0.45 * a, blur=size * 0.12))
    c.drawString(s, x0, y, f, fill(color, a))
    return w


# ---------------------------------------------------------------- the float: pop in, bob, soft shadow
def float_in(c, t, t0, x, y, seed=0, scale=1.0, t_out=None, out_dur=0.2, bob=6.0):
    """transform for a UI element centred at (x, y): spring pop at t0, gentle bob, shrink-fade at t_out.
    Returns alpha (0 means skip drawing)."""
    if t < t0:
        return 0.0
    k = t - t0
    sp = spring(k, w=19, z=0.5) if k < 1.2 else 1.0
    a = clamp(k / 0.08)
    s = scale * (0.55 + 0.45 * sp)
    yy = y + bob * math.sin((t + hrand(seed) * 6) * 1.6) + (1 - min(1.0, sp)) * 30
    if t_out is not None and t > t_out:
        ko = e_in(clamp((t - t_out) / out_dur))
        s *= 1 - 0.35 * ko
        a *= 1 - ko
        yy -= 30 * ko
    if a <= 0:
        return 0.0
    c.translate(x, yy)
    c.scale(s, s)
    return a


def soft_shadow(c, r, a=1.0, radius=None):
    rad = radius if radius is not None else min(r.width(), r.height()) / 2
    c.drawRRect(rrect(r.left(), r.top() + 10, r.width(), r.height(), rad), fill("#000000", 0.32 * a, blur=16))


def _rr(w, h, r=None):
    return rrect(-w / 2, -h / 2, w, h, h / 2 if r is None else r)


# ---------------------------------------------------------------- components (all drawn centred on 0,0)
def pill(c, w, h, color, label="", fg=WHITE, a=1.0, arrow=False, size=None, name="ui", glass=False):
    r = _rr(w, h)
    soft_shadow(c, r.rect(), a, h / 2)
    c.drawRRect(r, fill(color, a))
    if glass:
        c.drawRRect(rrect(-w / 2 + 4, -h / 2 + 3, w - 8, h * 0.45, h * 0.3), fill(WHITE, 0.10 * a))
    size = size or h * 0.36
    if arrow:
        c.drawCircle(w / 2 - h / 2, 0, h * 0.38, fill(INK, a))
        ar = h * 0.16
        cx = w / 2 - h / 2
        c.drawLine(cx - ar, 0, cx + ar, 0, stroke(WHITE, h * 0.06, a))
        c.drawLine(cx + ar * 0.2, -ar * 0.8, cx + ar, 0, stroke(WHITE, h * 0.06, a))
        c.drawLine(cx + ar * 0.2, ar * 0.8, cx + ar, 0, stroke(WHITE, h * 0.06, a))
        if label:
            text(c, label, -h * 0.3, size * 0.36, name, size, fg, a, anchor="c")
    elif label:
        text(c, label, 0, size * 0.36, name, size, fg, a, anchor="c")


def toggle(c, k, w=150, h=76, on=GREEN, off="#2A2C30", knob=WHITE, a=1.0):
    """k: 0 = off, 1 = on (knob slides with a little squash)."""
    r = _rr(w, h)
    soft_shadow(c, r.rect(), a, h / 2)
    col = kit.mixc(off, on, k)
    c.drawRRect(r, fill("#%02x%02x%02x" % col, a))
    pad = h * 0.1
    kr = h / 2 - pad
    x = lerp(-w / 2 + pad + kr, w / 2 - pad - kr, e_io(k))
    squash = 1 + 0.25 * math.sin(math.pi * clamp(k))
    c.drawRRect(rrect(x - kr * squash, -kr, 2 * kr * squash, 2 * kr, kr), fill(knob, a))


def toggle_row(c, label, k, w=560, h=84, a=1.0, on=GREEN, off_label=False):
    r = _rr(w, h, 26)
    soft_shadow(c, r.rect(), a, 26)
    c.drawRRect(r, fill("#16171A", 0.92 * a))
    text(c, label, -w / 2 + 30, 12, "ui", 34, WHITE, a)
    c.save()
    c.translate(w / 2 - 80, 0)
    c.scale(0.72, 0.72)
    toggle(c, k, on=on, a=a)
    c.restore()


def icon_button(c, r, color, glyph, a=1.0, fg=WHITE, k=1.0):
    soft_shadow(c, skia.Rect(-r, -r, r, r), a, r)
    c.drawCircle(0, 0, r, fill(color, a))
    glyph_draw(c, glyph, r * 0.5, fg, a, k)


def glyph_draw(c, g, s, color, a=1.0, k=1.0):
    p = stroke(color, s * 0.16, a)
    f_ = fill(color, a)
    if g == "battery":
        c.drawRRect(rrect(-s * 0.8, -s * 0.42, s * 1.5, s * 0.84, s * 0.16), stroke(color, s * 0.14, a))
        c.drawRect(skia.Rect(-s * 0.62, -s * 0.24, -s * 0.62 + s * 1.1 * k, s * 0.24), f_)
        c.drawRect(skia.Rect(s * 0.74, -s * 0.18, s * 0.88, s * 0.18), f_)
    elif g == "speaker":
        path = skia.Path()
        path.moveTo(-s * 0.7, -s * 0.25)
        path.lineTo(-s * 0.35, -s * 0.25)
        path.lineTo(s * 0.1, -s * 0.65)
        path.lineTo(s * 0.1, s * 0.65)
        path.lineTo(-s * 0.35, s * 0.25)
        path.lineTo(-s * 0.7, s * 0.25)
        path.close()
        c.drawPath(path, f_)
        for i in range(2):
            rr = s * (0.45 + 0.3 * i)
            c.drawArc(skia.Rect(s * 0.1 - rr, -rr, s * 0.1 + rr, rr), -45, 90, False, stroke(color, s * 0.12, a))
    elif g == "lock":
        c.drawRRect(rrect(-s * 0.55, -s * 0.1, s * 1.1, s * 0.8, s * 0.14), f_)
        c.drawArc(skia.Rect(-s * 0.38, -s * 0.72, s * 0.38, s * 0.3), 180, 180, False, stroke(color, s * 0.15, a))
    elif g == "arrow":
        c.drawLine(-s * 0.45, -s * 0.45, s * 0.45, s * 0.45, p)
        c.drawLine(s * 0.45, s * 0.45, s * 0.45, -s * 0.1, p)
        c.drawLine(s * 0.45, s * 0.45, -s * 0.1, s * 0.45, p)
    elif g == "scissors":
        for sg in (-1, 1):
            c.drawCircle(-s * 0.45, sg * s * 0.35, s * 0.22, stroke(color, s * 0.12, a))
            c.drawLine(-s * 0.28, sg * s * 0.25, s * 0.7, -sg * s * 0.3, stroke(color, s * 0.13, a))
    elif g == "cc":
        c.drawRRect(rrect(-s * 0.8, -s * 0.55, s * 1.6, s * 1.1, s * 0.25), stroke(color, s * 0.12, a))
        text(c, "CC", 0, s * 0.27, "uib", s * 0.78, color, a, anchor="c")
    elif g == "sparkle":
        star(c, 0, 0, s * 0.8, color, 4, 0.28, a=a)
        star(c, s * 0.6, -s * 0.55, s * 0.3, color, 4, 0.3, a=a)
    elif g == "play":
        path = skia.Path()
        path.moveTo(-s * 0.3, -s * 0.45)
        path.lineTo(s * 0.5, 0)
        path.lineTo(-s * 0.3, s * 0.45)
        path.close()
        c.drawPath(path, f_)
    elif g == "plus":
        c.drawLine(-s * 0.4, 0, s * 0.4, 0, p)
        c.drawLine(0, -s * 0.4, 0, s * 0.4, p)
    elif g == "check":
        c.drawLine(-s * 0.45, 0, -s * 0.1, s * 0.38, p)
        c.drawLine(-s * 0.1, s * 0.38, s * 0.5, -s * 0.4, p)
    elif g == "x":
        c.drawLine(-s * 0.4, -s * 0.4, s * 0.4, s * 0.4, p)
        c.drawLine(s * 0.4, -s * 0.4, -s * 0.4, s * 0.4, p)
    elif g == "note":
        c.drawOval(skia.Rect(-s * 0.55, s * 0.15, -s * 0.05, s * 0.55), f_)
        c.drawRect(skia.Rect(-s * 0.13, -s * 0.6, -s * 0.03, s * 0.35), f_)
        c.drawLine(-s * 0.08, -s * 0.58, s * 0.45, -s * 0.38, stroke(color, s * 0.14, a))
    elif g == "clock":
        c.drawCircle(0, 0, s * 0.65, stroke(color, s * 0.13, a))
        ang = k * 2 * math.pi
        c.drawLine(0, 0, s * 0.45 * math.sin(ang), -s * 0.45 * math.cos(ang), p)
        c.drawLine(0, 0, 0, -s * 0.3, p)
    elif g == "dots":
        for i in (-1, 0, 1):
            c.drawCircle(i * s * 0.45, 0, s * 0.13, f_)
    elif g == "laptop":
        c.drawRRect(rrect(-s * 0.6, -s * 0.5, s * 1.2, s * 0.75, s * 0.08), stroke(color, s * 0.12, a))
        c.drawLine(-s * 0.85, s * 0.42, s * 0.85, s * 0.42, stroke(color, s * 0.14, a))
    elif g == "phone":
        c.drawRRect(rrect(-s * 0.35, -s * 0.65, s * 0.7, s * 1.3, s * 0.14), stroke(color, s * 0.12, a))


def star(c, x, y, r, color, n=5, inner=0.45, rot=0.0, a=1.0):
    path = skia.Path()
    for i in range(2 * n):
        rr = r if i % 2 == 0 else r * inner
        ang = rot + math.pi * i / n - math.pi / 2
        (path.moveTo if i == 0 else path.lineTo)(x + rr * math.cos(ang), y + rr * math.sin(ang))
    path.close()
    c.drawPath(path, fill(color, a))


def slider(c, v, w=300, h=78, a=1.0, label=None):
    r = _rr(w, h, 18)
    soft_shadow(c, r.rect(), a, 18)
    c.drawRRect(r, fill("#16171A", a))
    x0, x1 = -w / 2 + 34, w / 2 - 34
    yy = 10 if label else 0
    c.drawLine(x0, yy, x1, yy, stroke("#3A3D42", 6, a))
    xv = lerp(x0, x1, clamp(v))
    c.drawLine(x0, yy, xv, yy, stroke(GREEN, 6, a))
    c.drawCircle(xv, yy, 13, fill(WHITE, a))
    if label:
        text(c, label, x0, -12, "ui", 20, GREYUI, a)


def segmented(c, items, sel, w=420, h=74, a=1.0, size=26):
    """sel: float index of the selected segment (animates)."""
    r = _rr(w, h, 10)
    soft_shadow(c, r.rect(), a, 10)
    c.drawRRect(r, fill("#1A1B1E", a))
    n = len(items)
    sw = w / n
    x = -w / 2 + sw * sel
    c.drawRRect(rrect(x + 4, -h / 2 + 4, sw - 8, h - 8, 8), fill(WHITE, a))
    for i, it in enumerate(items):
        d = abs(sel - i)
        colr = "#%02x%02x%02x" % kit.mixc(INK, "#BFC2C7", clamp(d))
        text(c, it, -w / 2 + sw * (i + 0.5), size * 0.36, "ui", size, colr, a, anchor="c")


def card(c, w, h, color, title="", body="", a=1.0, plus=False, shape=None, fg=INK, t=0.0, radius=26):
    r = rrect(-w / 2, -h / 2, w, h, radius)
    soft_shadow(c, r.rect(), a, radius)
    c.drawRRect(r, fill(color, a))
    if title:
        text(c, title, -w / 2 + 26, -h / 2 + 46, "uib", 30, fg, a)
    if body:
        for i, line in enumerate(body.split("\n")):
            text(c, line, -w / 2 + 26, -h / 2 + 84 + i * 30, "ui", 22, fg, 0.7 * a)
    if plus:
        c.save()
        c.translate(w / 2 - 44, h / 2 - 44)
        icon_button(c, 26, INK, "plus", a)
        c.restore()
    if shape == "sun":
        c.save()
        c.translate(w / 2 - 80, h / 2 - 30)
        c.rotate(t * 30)
        star(c, 0, 0, 70, PURPLE, 9, 0.78, a=0.7 * a)
        c.restore()


def scribble(c, cx, y, w, k, color=INK, width=9, seed=0, a=1.0):
    """the reference's hand-drawn loopy underline, drawn on by k."""
    if k <= 0.01:
        return
    pts = []
    n = 90
    loops = 4
    for i in range(n + 1):
        u = i / n
        x = cx - w / 2 + w * u
        ph = u * loops * 2 * math.pi
        yy = y + 18 * math.sin(ph) * (0.6 + 0.4 * math.sin(u * 3 + seed))
        x += 26 * math.cos(ph) * (0.4 + 0.6 * u * (1 - u) * 4)
        pts.append((x, yy))
    path = skia.Path()
    path.moveTo(*pts[0])
    for p_ in pts[1:]:
        path.lineTo(*p_)
    pnt = stroke(color, width, a)
    eff = skia.TrimPathEffect.Make(0, clamp(k)) if k < 1 else None
    if eff is not None:
        pnt.setPathEffect(eff)
    c.drawPath(path, pnt)


def wave_pill(c, t, w, h, energy, a=1.0, color=GREEN):
    r = _rr(w, h)
    soft_shadow(c, r.rect(), a, h / 2)
    c.drawRRect(r, fill("#16171A", a))
    n = 26
    for i in range(n):
        x = -w / 2 + h * 0.6 + i * (w - h * 1.2) / (n - 1)
        hh = h * 0.65 * energy * (0.25 + 0.75 * abs(math.sin(t * (5 + i * 0.37) + i)))
        c.drawRRect(rrect(x - 3, -hh / 2, 6, max(hh, 4), 3), fill(color if i % 5 else YEL, a))
