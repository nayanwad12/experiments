"""Drawing pieces for the stress -> psoriasis explainer (skia, 1080x1920).

Captions are white (kinetic, word by word). Graphics use a small science palette on top:
amber = cortisol, red = flare / attack, cyan = immune, green = calm / fix.
"""
import json
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "reels" / "common"))
from kit import (H, W, clamp, col, e_back, e_in, e_io, e_out, fill, font, hrand, lerp,  # noqa: E402,F401
                 measure, prog, rrect, spring, stroke, text)

WHITE = "#FFFFFF"
INK = "#06080C"
NAVY = "#0A1020"
AMBER = "#FFB23F"
RED = "#FF4A5C"
CYAN = "#4FD8FF"
GREEN = "#5CF2A0"
VIOLET = "#A08CFF"
SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)


def _gc(c, a):
    """colour with optional #RRGGBBAA alpha (kit.col only reads #RRGGBB)."""
    if isinstance(c, str) and len(c.lstrip("#")) == 8:
        return col(c[:7], a * int(c.lstrip("#")[6:8], 16) / 255)
    return col(c, a)


def lin_grad(x0, y0, x1, y1, cols, pos=None, a=1.0):
    return skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeLinear(
        [skia.Point(x0, y0), skia.Point(x1, y1)], [_gc(c, a) for c in cols], pos))


def rad_grad(cx, cy, r, cols, pos=None, a=1.0):
    return skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeRadial(
        skia.Point(cx, cy), max(r, 1), [_gc(c, a) for c in cols], pos))


# ------------------------------------------------------------------ assets
@lru_cache(None)
def img(name):
    p = HERE / "assets" / ("icons" if (HERE / "assets" / "icons" / f"{name}.png").exists() else "img") / f"{name}.png"
    return skia.Image.open(str(p))


def draw_image_cover(c, im, x, y, w, h, zoom=1.0, fx=0.5, fy=0.5, a=1.0):
    """draw im cropped to fill (x, y, w, h); zoom > 1 pushes in around (fx, fy)."""
    s = max(w / im.width(), h / im.height()) * zoom
    sw, sh = w / s, h / s
    sx = clamp(fx * im.width() - sw / 2, 0, im.width() - sw)
    sy = clamp(fy * im.height() - sh / 2, 0, im.height() - sh)
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(clamp(a))
    c.drawImageRect(im, skia.Rect.MakeXYWH(sx, sy, sw, sh), skia.Rect.MakeXYWH(x, y, w, h), SAMP, p)


def icon(c, name, cx, cy, size, k=1.0, rot=0.0, a=1.0, shadow=True):
    if k <= 0:
        return
    im = img(name)
    sc = size / im.width() * k
    c.save()
    c.translate(cx, cy)
    c.rotate(rot)
    c.scale(sc, sc)
    if shadow:
        c.drawOval(skia.Rect.MakeXYWH(-im.width() * 0.38, im.height() * 0.36, im.width() * 0.76, im.height() * 0.16),
                   fill(INK, 0.35 * a, blur=10))
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(clamp(a))
    c.drawImage(im, -im.width() / 2, -im.height() / 2, SAMP, p)
    c.restore()


def pop_k(t, t0, dur=0.45, t1=None, out=0.22):
    """spring in at t0, ease out at t1 -> (scale k, alpha)."""
    if t < t0:
        return 0.0, 0.0
    k = spring(t - t0, w=16, z=0.42)
    a = clamp((t - t0) / 0.12)
    if t1 is not None and t > t1:
        ko = clamp((t - t1) / out)
        k *= 1 - e_in(ko) * 0.6
        a *= 1 - ko
    return k, a


# ------------------------------------------------------------------ type
def pill(c, s, cx, cy, size=34, bg=WHITE, fg=INK, a=1.0, name="montb", pad=0.55, tracking=0.06, k=1.0):
    if a <= 0 or k <= 0:
        return 0
    w = measure(s, name, size, tracking)
    hh = size * 1.75
    ww = w + size * pad * 2.4
    c.save()
    c.translate(cx, cy)
    c.scale(k, k)
    c.drawRRect(rrect(-ww / 2, -hh / 2 + 6, ww, hh, hh / 2), fill(INK, 0.3 * a, blur=10))
    c.drawRRect(rrect(-ww / 2, -hh / 2, ww, hh, hh / 2), fill(bg, a))
    text(c, s, 0, size * 0.36, name, size, color=fg, a=a, tracking=tracking)
    c.restore()
    return ww


def title(c, s, cx, y, size, t, t0, t1=None, color=WHITE, name="mont", stagger=0.03, maxw=980, shadow=True):
    """kinetic headline: letters rise + unblur one by one, fall away at t1."""
    if t < t0:
        return
    w = measure(s, name, size)
    if w > maxw:
        size *= maxw / w
        w = maxw
    f = font(name, size)
    x = cx - w / 2
    for i, ch in enumerate(s):
        cw = f.measureText(ch)
        k = clamp((t - t0 - i * stagger) / 0.38)
        if k > 0 and ch != " ":
            sp = spring(k * 0.38, w=20, z=0.5)
            yy = y + (1 - sp) * size * 0.45
            a = clamp(k * 3)
            if t1 is not None and t > t1:
                ko = clamp((t - t1 - i * stagger * 0.4) / 0.2)
                yy -= e_in(ko) * size * 0.35
                a *= 1 - ko
            if shadow:
                c.drawString(ch, x, yy + size * 0.04, f, fill(INK, 0.45 * a, blur=size * 0.06))
            c.drawString(ch, x, yy, f, fill(color, a))
        x += cw


# ------------------------------------------------------------------ captions (white, kinetic)
class Captions:
    """1-4 word groups. Each word punches in (scale + rise + unblur); the spoken word is full white,
    upcoming words are not shown yet, finished words stay. Key words get bigger."""

    def __init__(self, groups, y=1530, size=78, name="mont"):
        self.groups, self.y, self.size, self.name = groups, y, size, name
        self.off = []

    def mute(self, a, b):
        self.off.append((a, b))

    def draw(self, c, t, y=None, a=1.0):
        if any(x <= t < y_ for x, y_ in self.off):
            return
        y = self.y if y is None else y
        for gi, g in enumerate(self.groups):
            g0 = g["words"][0]["s"]
            g1 = g["words"][-1]["e"]
            nxt = self.groups[gi + 1]["words"][0]["s"] if gi + 1 < len(self.groups) else 1e9
            end = min(g1 + 0.35, nxt - 0.02)
            if not (g0 - 0.03 <= t < end):
                continue
            ws = g["words"]
            sizes = [self.size * (1.28 if w.get("big") else 1.0) for w in ws]
            space = self.size * 0.42
            widths = [measure(w["w"], self.name, s) for w, s in zip(ws, sizes)]
            lines, cur, cw = [], [], 0
            for i, wd in enumerate(widths):
                if cur and cw + space + wd > 940:
                    lines.append(cur)
                    cur, cw = [], 0
                cur.append(i)
                cw += wd + (space if len(cur) > 1 else 0)
            lines.append(cur)
            lh = self.size * 1.18
            yy0 = y - (len(lines) - 1) * lh / 2
            ko = clamp((t - (end - 0.08)) / 0.08) if nxt > g1 + 0.37 else 0.0   # back-to-back groups: hard switch
            for li, line in enumerate(lines):
                tot = sum(widths[i] for i in line) + space * (len(line) - 1)
                x = W / 2 - tot / 2
                for i in line:
                    w = ws[i]
                    k = clamp((t - w["s"] + 0.03) / 0.16)
                    if k <= 0:
                        x += widths[i] + space
                        continue
                    sp = spring(k * 0.16, w=24, z=0.5)
                    aa = a * clamp(k * 2.2) * (1 - ko)
                    sc = lerp(0.55, 1.0, sp)
                    c.save()
                    c.translate(x + widths[i] / 2, yy0 + li * lh + (1 - sp) * 26)
                    c.scale(sc, sc)
                    f = font(self.name, sizes[i])
                    tx = -widths[i] / 2
                    c.drawString(w["w"], tx, 8, f, fill(INK, 0.55 * aa, blur=14))
                    c.drawString(w["w"], tx, 0, f, stroke(INK, sizes[i] * 0.09, 0.55 * aa))
                    c.drawString(w["w"], tx, 0, f, fill(WHITE, aa))
                    if w.get("big"):
                        uk = e_out(clamp((t - w["s"]) / 0.3))
                        c.drawRRect(rrect(tx, 18, widths[i] * uk, 10, 5), fill(WHITE, aa))
                    c.restore()
                    x += widths[i] + space


# ------------------------------------------------------------------ text behind the speaker
def behind(c, s, cx, y, size, t, t0, t1, color=WHITE, name="anton", stagger=0.04, maxw=1040, outline=False):
    """giant letters that slam up from below; drawn under the person cutout."""
    if t < t0 or t > t1 + 0.4:
        return
    w = measure(s, name, size)
    if w > maxw:
        size *= maxw / w
        w = maxw
    f = font(name, size)
    x = cx - w / 2
    drift = (t - t0) * 6
    for i, ch in enumerate(s):
        cw = f.measureText(ch)
        k = clamp((t - t0 - i * stagger) / 0.42)
        if k > 0 and ch != " ":
            sp = spring(k * 0.42, w=17, z=0.48)
            yy = y + (1 - sp) * size * 0.6
            a = clamp(k * 3)
            if t > t1:
                ko = clamp((t - t1 - i * stagger * 0.4) / 0.25)
                yy += e_in(ko) * size * 0.5
                a *= 1 - ko
            xx = x - drift
            if outline:
                c.drawString(ch, xx, yy, f, stroke(color, 5, a * 0.95))
            else:
                c.drawString(ch, xx, yy + size * 0.03, f, fill(INK, 0.35 * a, blur=size * 0.05))
                c.drawString(ch, xx, yy, f, lin_grad(0, yy - size * 0.9, 0, yy, [color, mixh(color, "#C9D2E0", 0.35)], a=a))
        x += cw


def mixh(a, b, k):
    from kit import mixc
    r, g, bb = mixc(a, b, k)
    return f"#{r:02X}{g:02X}{bb:02X}"


# ------------------------------------------------------------------ image card (science photos)
def photo_card(c, name, cx, cy, w, h, t, t0, t1, label=None, sub=None, tilt=-2.5, zoom0=1.0, zoom1=1.12,
               fx=0.5, fy=0.5, crack=None, from_x=0, accent=WHITE):
    if t < t0 or t > t1 + 0.35:
        return
    k, a = pop_k(t, t0, t1=t1)
    zk = clamp((t - t0) / max(0.1, t1 - t0))
    c.save()
    c.translate(cx + from_x * (1 - clamp(k)), cy)
    c.rotate(tilt * (2 - k))
    c.scale(lerp(0.6, 1.0, k), lerp(0.6, 1.0, k))
    x, y = -w / 2, -h / 2
    c.drawRRect(rrect(x, y + 24, w, h, 34), fill(INK, 0.5 * a, blur=34))
    c.drawRRect(rrect(x - 10, y - 10, w + 20, h + 20, 40), fill(accent, a))
    c.save()
    c.clipRRect(rrect(x, y, w, h, 30), doAntiAlias=True)
    draw_image_cover(c, img(name), x, y, w, h, lerp(zoom0, zoom1, e_io(zk)), fx, fy, a)
    if label:
        c.drawRect(skia.Rect.MakeXYWH(x, y + h * 0.62, w, h * 0.38),
                   lin_grad(0, y + h * 0.62, 0, y + h, ["#00000000", "#000000"], a=a * 0.85))
    if crack is not None and t > crack:
        draw_crack(c, 0, 0, w, h, clamp((t - crack) / 0.35), a)
    c.restore()
    if label:
        text(c, label, x + 40, y + h - (62 if sub else 44), "mont", 50, color=WHITE, a=a, anchor="l")
        if sub:
            text(c, sub, x + 42, y + h - 22, "monob", 26, color=accent if accent != WHITE else "#D7DEE8", a=a,
                 anchor="l", tracking=0.08)
    c.restore()


def draw_crack(c, cx, cy, w, h, k, a):
    """jagged cracks spreading from the centre of a card."""
    rng = np.random.default_rng(11)
    p = skia.Path()
    for br in range(7):
        ang = br / 7 * math.tau + rng.uniform(-0.3, 0.3)
        x, y = cx, cy
        p.moveTo(x, y)
        L = max(w, h) * 0.6 * k
        n = 6
        for j in range(n):
            ang += rng.uniform(-0.5, 0.5)
            x += math.cos(ang) * L / n
            y += math.sin(ang) * L / n
            p.lineTo(x, y)
    c.drawPath(p, stroke(INK, 9, a * 0.9))
    c.drawPath(p, stroke(WHITE, 3, a))
    c.drawCircle(cx, cy, 60 * k, fill(WHITE, 0.5 * a * (1 - k), blur=20))


# ------------------------------------------------------------------ cortisol molecule (RDKit 3D coords)
_MOL = json.loads((HERE / "assets" / "cortisol.json").read_text())
_P = np.array([a["p"] for a in _MOL["atoms"]], np.float32)
_P -= _P.mean(0)
_P /= np.abs(_P).max()
ATOM_C = {"C": ("#C7CFDB", 0.30), "O": (RED, 0.34), "H": ("#FFFFFF", 0.17)}


def molecule(c, cx, cy, R, t, k=1.0, a=1.0, spin=0.7, glow=AMBER):
    if k <= 0 or a <= 0:
        return
    ry, rx = t * spin, 0.35 + 0.15 * math.sin(t * 0.6)
    cy_, sy = math.cos(ry), math.sin(ry)
    cx_, sx = math.cos(rx), math.sin(rx)
    P = _P.copy()
    x = P[:, 0] * cy_ + P[:, 2] * sy
    z = -P[:, 0] * sy + P[:, 2] * cy_
    y = P[:, 1] * cx_ - z * sx
    z = P[:, 1] * sx + z * cx_
    persp = 1 / (1 + z * 0.35)
    X = cx + x * R * persp * k
    Y = cy + y * R * persp * k
    c.drawCircle(cx, cy, R * 1.05 * k, rad_grad(cx, cy, R * 1.1 * k, [glow, "#00000000"], a=0.35 * a))
    items = []
    for b in _MOL["bonds"]:
        i, j = b["a"], b["b"]
        items.append(((z[i] + z[j]) / 2, "b", i, j, b["o"]))
    for i, at in enumerate(_MOL["atoms"]):
        items.append((z[i], "a", i, at["el"], 0))
    for zz, kind, i, j, o in sorted(items, key=lambda q: -q[0]):
        shade = clamp(0.55 + 0.45 * (1 - (zz + 1) / 2))
        if kind == "b":
            wdt = 9 * persp[i] * k
            c.drawLine(X[i], Y[i], X[j], Y[j], stroke(mixh("#5A6474", "#E8EDF5", shade), wdt, a))
            if o >= 2:
                c.drawLine(X[i] + 7, Y[i] + 7, X[j] + 7, Y[j] + 7, stroke(mixh("#5A6474", "#E8EDF5", shade), wdt * 0.6, a))
        else:
            colr, rad = ATOM_C.get(j, ("#C7CFDB", 0.3))
            r = R * rad * 0.24 * persp[i] * k
            hx, hy = X[i] - r * 0.35, Y[i] - r * 0.4
            c.drawCircle(X[i], Y[i], r, rad_grad(hx, hy, r * 1.4, [WHITE, colr, mixh(colr, INK, 0.6)],
                                                  [0, 0.35, 1], a=a * (0.55 + 0.45 * shade)))


# ------------------------------------------------------------------ T-cells (procedural)
def tcell(c, x, y, r, t, seed=0, a=1.0, colr=CYAN, angry=0.0):
    if a <= 0:
        return
    n = 22
    p = skia.Path()
    for i in range(n * 2 + 1):
        ang = i / (n * 2) * math.tau
        wob = 1 + 0.06 * math.sin(ang * 3 + t * 2 + seed)
        rr = r * wob * (1.16 if i % 2 == 0 else 1.0)
        px, py = x + math.cos(ang) * rr, y + math.sin(ang) * rr
        p.moveTo(px, py) if i == 0 else p.lineTo(px, py)
    p.close()
    body = mixh(colr, RED, angry)
    c.drawCircle(x, y, r * 1.6, rad_grad(x, y, r * 1.7, [body, "#00000000"], a=0.35 * a))
    c.drawPath(p, rad_grad(x - r * 0.35, y - r * 0.4, r * 1.5, [WHITE, body, mixh(body, INK, 0.55)], [0, 0.3, 1], a=a))
    c.drawCircle(x + r * 0.15, y + r * 0.1, r * 0.45, fill(mixh(body, VIOLET, 0.5), 0.55 * a))


# ------------------------------------------------------------------ studio background
def studio_bg(c, t, a=1.0, tint=NAVY):
    c.drawRect(skia.Rect.MakeWH(W, H), lin_grad(0, 0, 0, H, [mixh(tint, "#1B2A4A", 0.4), tint, INK], [0, 0.55, 1], a=a))
    gp = stroke(WHITE, 1.2, 0.055 * a)
    off = (t * 18) % 90
    for gx in range(-90, W + 90, 90):
        c.drawLine(gx + off * 0.3, 0, gx + off * 0.3, H, gp)
    for gy in range(-90, H + 90, 90):
        c.drawLine(0, gy + off, W, gy + off, gp)
    for i in range(26):
        px = (hrand("p", i) * W + t * 12 * (hrand("v", i) - 0.5)) % W
        py = (hrand("q", i) * H - t * 30 * (0.4 + hrand("s", i))) % H
        c.drawCircle(px, py, 2 + 3 * hrand("r", i), fill(CYAN, 0.25 * a, blur=2))
    c.drawCircle(W / 2, 560, 700, rad_grad(W / 2, 560, 760, ["#2A4A8A", "#00000000"], a=0.35 * a))


# ------------------------------------------------------------------ flowcharts
def node(c, s, cx, cy, k, a, colr=WHITE, icon_name=None, size=40, glow=0.0, w=None):
    if k <= 0 or a <= 0:
        return
    tw = measure(s, "mont", size)
    ww = w or tw + (150 if icon_name else 80)
    hh = size * 2.3
    c.save()
    c.translate(cx, cy)
    c.scale(k, k)
    if glow > 0:
        c.drawRRect(rrect(-ww / 2 - 6, -hh / 2 - 6, ww + 12, hh + 12, hh / 2 + 6), fill(colr, 0.55 * glow * a, blur=26))
    c.drawRRect(rrect(-ww / 2, -hh / 2 + 10, ww, hh, hh / 2), fill(INK, 0.45 * a, blur=16))
    c.drawRRect(rrect(-ww / 2, -hh / 2, ww, hh, hh / 2), fill("#121A2C", 0.92 * a))
    c.drawRRect(rrect(-ww / 2, -hh / 2, ww, hh, hh / 2), stroke(colr, 4, a))
    tx = (35 if icon_name else 0)
    if icon_name:
        icon(c, icon_name, -ww / 2 + hh * 0.62, 0, hh * 0.78, 1, a=a, shadow=False)
    text(c, s, tx, size * 0.36, "mont", size, color=WHITE, a=a)
    c.restore()


def arrow_line(c, x0, y0, x1, y1, k, colr=WHITE, a=1.0, wdt=7, head=24):
    if k <= 0:
        return
    xe, ye = lerp(x0, x1, k), lerp(y0, y1, k)
    c.drawLine(x0, y0, xe, ye, stroke(colr, wdt, a))
    ang = math.atan2(y1 - y0, x1 - x0)
    p = skia.Path()
    p.moveTo(xe + math.cos(ang) * head * 0.5, ye + math.sin(ang) * head * 0.5)
    p.lineTo(xe + math.cos(ang + 2.5) * head, ye + math.sin(ang + 2.5) * head)
    p.lineTo(xe + math.cos(ang - 2.5) * head, ye + math.sin(ang - 2.5) * head)
    p.close()
    c.drawPath(p, fill(colr, a))


def chain(c, t, items, x, y0, gap, t_out=None, size=40):
    """vertical flowchart: items = [(label, icon, colour, t_on)]."""
    for i, (lab, ic, colr, ton) in enumerate(items):
        k, a = pop_k(t, ton, t1=t_out)
        cy = y0 + i * gap
        if i:
            ak = e_out(clamp((t - ton + 0.25) / 0.3))
            a2 = 1 if t_out is None or t < t_out else 1 - clamp((t - t_out) / 0.2)
            arrow_line(c, x, cy - gap + 62, x, cy - 58, ak, WHITE, a2 * 0.9)
        glow = math.exp(-max(0, t - ton) * 2.5)
        node(c, lab, x, cy, k, a, colr, ic, size, glow)


def loop_ring(c, t, cx, cy, R, items, t0, t1, speed=1.0, broken=None, reverse=False, title_s=None, ring_col=WHITE,
              amul=1.0, phase=None, node_size=34):
    """circular cause-effect loop. items = [(label, icon, colour, t_on)]; a pulse runs round the ring."""
    if t < t0 or t > t1 + 0.4:
        return
    a_all = clamp((t - t0) / 0.25) * (1 - clamp((t - t1) / 0.3)) * amul
    n = len(items)
    angs = [-math.pi / 2 + i * math.tau / n * (-1 if reverse else 1) for i in range(n)]
    rk = e_out(clamp((t - t0) / 0.8))
    rect = skia.Rect.MakeXYWH(cx - R, cy - R, 2 * R, 2 * R)
    gap = 0.0 if broken is None else e_out(clamp((t - broken) / 0.4))
    c.drawArc(rect, -90, 360 * rk, False, stroke(ring_col, 6, 0.35 * a_all))
    # arrows between nodes
    for i in range(n):
        a0, a1 = angs[i], angs[(i + 1) % n]
        if reverse and a1 > a0:
            a1 -= math.tau
        if not reverse and a1 < a0:
            a1 += math.tau
        if broken is not None and i == 0 and gap > 0:
            continue
        mid = (a0 + a1) / 2
        hx, hy = cx + math.cos(mid) * R, cy + math.sin(mid) * R
        d = 1 if not reverse else -1
        tang = mid + d * math.pi / 2
        p = skia.Path()
        p.moveTo(hx + math.cos(tang) * 22, hy + math.sin(tang) * 22)
        p.lineTo(hx + math.cos(tang + 2.4) * 22, hy + math.sin(tang + 2.4) * 22)
        p.lineTo(hx + math.cos(tang - 2.4) * 22, hy + math.sin(tang - 2.4) * 22)
        p.close()
        c.drawPath(p, fill(ring_col, 0.9 * a_all * rk))
    # pulse
    if broken is None or t < broken:
        ph = (((t - t0) * 0.55 * speed) if phase is None else phase) % 1.0
        ang = -math.pi / 2 + ph * math.tau * (-1 if reverse else 1)
        px, py = cx + math.cos(ang) * R, cy + math.sin(ang) * R
        c.drawCircle(px, py, 30, fill(ring_col, 0.5 * a_all, blur=18))
        c.drawCircle(px, py, 11, fill(WHITE, a_all))
    if broken is not None and gap > 0:
        ga = (angs[0] + angs[1]) / 2 if not reverse else (angs[0] + angs[1] - math.tau) / 2
        bx, by = cx + math.cos(ga) * R, cy + math.sin(ga) * R
        sk = spring(t - broken, w=14, z=0.4)
        c.save()
        c.translate(bx, by)
        c.scale(sk, sk)
        c.drawCircle(0, 0, 70, fill(RED, 0.95 * a_all))
        c.drawLine(-28, -28, 28, 28, stroke(WHITE, 12, a_all))
        c.drawLine(28, -28, -28, 28, stroke(WHITE, 12, a_all))
        c.restore()
    for i, (lab, ic, colr, ton) in enumerate(items):
        k, a = pop_k(t, ton)
        x, y = cx + math.cos(angs[i]) * R, cy + math.sin(angs[i]) * R
        glow = math.exp(-max(0, t - ton) * 2.0)
        node(c, lab, x, y, k, a * a_all, colr, ic, node_size, glow)
    if title_s:
        k, a = pop_k(t, t0 + 0.2)
        icon(c, "loop", cx, cy - 10, 150 * k, a=a * a_all, rot=(phase * 360 if phase is not None else (t - t0) * 60) * (-1 if reverse else 1))


# ------------------------------------------------------------------ breathing
def breath(c, t, t0, t1, cx, cy, R, inhale=4.0, exhale=6.0, rate=1.0):
    """circle that grows on the in-breath and shrinks on the out-breath; labels + count."""
    if t < t0 or t > t1 + 0.3:
        return
    a = clamp((t - t0) / 0.3) * (1 - clamp((t - t1) / 0.3))
    cyc = (inhale + exhale) / rate
    ph = ((t - t0) % cyc)
    if ph < inhale / rate:
        k = e_io(ph / (inhale / rate))
        lab, sec = "SAANS ANDAR", int(ph * rate) + 1
    else:
        k = 1 - e_io((ph - inhale / rate) / (exhale / rate))
        lab, sec = "SAANS BAHAR", int((ph - inhale / rate) * rate) + 1
    r = lerp(R * 0.45, R, k)
    for i in range(3):
        c.drawCircle(cx, cy, r * (1 + 0.12 * (i + 1)), stroke(GREEN, 3, a * 0.25 / (i + 1)))
    c.drawCircle(cx, cy, r, rad_grad(cx, cy - r * 0.3, r * 1.3, ["#B8FFD9", GREEN, "#118A55"], [0, 0.45, 1], a=a * 0.92))
    text(c, str(sec), cx, cy + 40, "anton", 130, color=INK, a=a * 0.85)
    text(c, lab, cx, cy + R + 90, "mont", 52, color=WHITE, a=a)


def box_breath(c, t, t0, t1, cx, cy, s):
    if t < t0 or t > t1 + 0.3:
        return
    a = clamp((t - t0) / 0.3) * (1 - clamp((t - t1) / 0.3))
    x, y = cx - s / 2, cy - s / 2
    c.drawRRect(rrect(x, y, s, s, 28), stroke(WHITE, 6, a * 0.5))
    labs = [("ANDAR 4", cx, y - 34), ("ROKO 4", x + s + 30, cy), ("BAHAR 4", cx, y + s + 66), ("ROKO 4", x - 30, cy)]
    ph = ((t - t0) / 1.6) % 4
    side = int(ph)
    f = ph - side
    pts = [(x, y), (x + s, y), (x + s, y + s), (x, y + s), (x, y)]
    px, py = lerp(pts[side][0], pts[side + 1][0], f), lerp(pts[side][1], pts[side + 1][1], f)
    c.drawCircle(px, py, 34, fill(GREEN, 0.5 * a, blur=16))
    c.drawCircle(px, py, 16, fill(WHITE, a))
    for i, (lab, lx, ly) in enumerate(labs):
        on = i == side
        anc = "c" if i in (0, 2) else ("l" if i == 1 else "r")
        text(c, lab, lx, ly, "montb", 40, color=GREEN if on else WHITE, a=a * (1 if on else 0.6), anchor=anc)


# ------------------------------------------------------------------ ranking bars
def rank_bars(c, t, rows, x, y0, gap, wmax, t_out=None):
    """rows = [(rank, label, icon, frac, colour, t_on)]"""
    for i, (rk, lab, ic, frac, colr, ton) in enumerate(rows):
        k, a = pop_k(t, ton, t1=t_out)
        if a <= 0:
            continue
        y = y0 + i * gap
        bk = e_out(clamp((t - ton - 0.1) / 0.7))
        c.drawRRect(rrect(x, y - 52, wmax, 104, 52), fill("#121A2C", 0.85 * a))
        c.drawRRect(rrect(x, y - 52, max(104, wmax * frac * bk), 104, 52), lin_grad(x, 0, x + wmax, 0, [colr, mixh(colr, WHITE, 0.4)], a=a))
        c.drawCircle(x + 52, y, 44, fill(INK, 0.9 * a))
        text(c, f"#{rk}", x + 52, y + 17, "anton", 46, color=WHITE, a=a)
        icon(c, ic, x + 160, y, 86 * k, a=a, shadow=False)
        text(c, lab, x + 220, y + 17, "mont", 46, color=INK if frac * bk > 0.55 else WHITE, a=a, anchor="l")


# ------------------------------------------------------------------ comment box CTA
def comment_box(c, t, t0, t1, cx, cy, typed="PART 3", t_type=None):
    if t < t0 or t > t1 + 0.3:
        return
    k, a = pop_k(t, t0, t1=t1)
    w, h = 900, 150
    c.save()
    c.translate(cx, cy)
    c.scale(k, k)
    c.drawRRect(rrect(-w / 2, -h / 2 + 14, w, h, 40), fill(INK, 0.45 * a, blur=22))
    c.drawRRect(rrect(-w / 2, -h / 2, w, h, 40), fill(WHITE, a))
    c.drawCircle(-w / 2 + 80, 0, 44, lin_grad(-w / 2 + 36, -44, -w / 2 + 124, 44, [AMBER, RED], a=a))
    t_type = t0 + 0.4 if t_type is None else t_type
    n = int(clamp((t - t_type) / 0.6) * len(typed) + 0.001)
    s = typed[:n]
    text(c, "Comment karo...", -w / 2 + 150, -14, "montb", 30, color="#8A93A3", a=a, anchor="l")
    text(c, s, -w / 2 + 150, 46, "mont", 54, color=INK, a=a, anchor="l")
    if n < len(typed) or (t * 2) % 1 < 0.5:
        cw = measure(s, "mont", 54)
        c.drawRect(skia.Rect.MakeXYWH(-w / 2 + 156 + cw, 4, 5, 50), fill(INK, a))
    sk = spring(t - (t_type + 0.8), w=16, z=0.4) if t > t_type + 0.8 else 0
    c.drawCircle(w / 2 - 80, 0, 50 * (0.85 + 0.15 * sk), fill("#2F6BFF", a))
    p = skia.Path()
    p.moveTo(w / 2 - 102, -22); p.lineTo(w / 2 - 52, 0); p.lineTo(w / 2 - 102, 22); p.lineTo(w / 2 - 94, 0); p.close()
    c.drawPath(p, fill(WHITE, a))
    c.restore()


# ------------------------------------------------------------------ stamp
def stamp(c, s, cx, cy, size, t, t0, t1=None, colr=RED, rot=-7, fg=WHITE):
    if t < t0:
        return
    k = spring(t - t0, w=20, z=0.35)
    a = clamp((t - t0) / 0.08)
    if t1 is not None and t > t1:
        a *= 1 - clamp((t - t1) / 0.2)
    if a <= 0:
        return
    sc = lerp(2.2, 1.0, clamp(k))
    w = measure(s, "anton", size) + size * 0.7
    hh = size * 1.35
    c.save()
    c.translate(cx, cy)
    c.rotate(rot)
    c.scale(sc, sc)
    c.drawRRect(rrect(-w / 2, -hh / 2 + 10, w, hh, 18), fill(INK, 0.4 * a, blur=14))
    c.drawRRect(rrect(-w / 2, -hh / 2, w, hh, 18), fill(colr, a))
    text(c, s, 0, size * 0.36, "anton", size, color=fg, a=a)
    c.restore()


def counter(c, t, t0, t1, cx, cy, v0, v1, fmt, size=200, colr=WHITE, dur=0.8):
    if t < t0 or t > t1 + 0.3:
        return
    k, a = pop_k(t, t0, t1=t1)
    v = lerp(v0, v1, e_out(clamp((t - t0) / dur)))
    c.save()
    c.translate(cx, cy)
    c.scale(lerp(0.7, 1, k), lerp(0.7, 1, k))
    text(c, fmt(v), 0, 0, "anton", size, color=colr, a=a, shadow=18)
    c.restore()
