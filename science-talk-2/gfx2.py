"""Mature/editorial drawing kit for the gut -> psoriasis explainer (skia, 1080x1920).

No emoji, no stickers: thin-line icons (Tabler, MIT) that draw on stroke by stroke, mono lower-third tags,
serif italic quotes, hairline diagrams, museum-plate photo cards. Captions stay white. Palette is mostly
monochrome with one calm accent (teal) and one warning tone used sparingly.
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
sys.path.insert(0, str(HERE.parent / "science-talk"))
from kit import (H, W, clamp, col, e_back, e_in, e_io, e_out, fill, font, hrand, lerp,  # noqa: E402,F401
                 measure, prog, rrect, spring, stroke, text)
from gfx import lin_grad, rad_grad, draw_image_cover, mixh, tcell, molecule  # noqa: E402,F401

WHITE = "#FFFFFF"
INK = "#07080A"
MUTED = "#A7AFBA"
TEAL = "#5ED6C1"
WARN = "#EF5F5A"
GOLD = "#E3BF72"
PANEL = "#0E1116"
SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)
CAP_FONT = "heavy"          # Inter Tight 800
TAG_FONT = "monob"          # JetBrains Mono 500


def trim(paint, k):
    """stroke only the first k (0..1) of each path."""
    if 0 < k < 0.999:
        pe = skia.TrimPathEffect.Make(0, k)
        if pe is not None:
            paint.setPathEffect(pe)
    return paint


# ------------------------------------------------------------------ assets
@lru_cache(None)
def img(name):
    return skia.Image.open(str(HERE / "assets" / "img" / f"{name}.png"))


@lru_cache(None)
def icon_paths(name):
    """Tabler outline icon -> list of skia.Path in its 24x24 box (curves flattened)."""
    import svgelements as se
    svg = se.SVG.parse(str(HERE / "assets" / "lineicons" / f"{name}.svg"))
    out = []
    for el in svg.elements():
        if not isinstance(el, se.Shape):
            continue
        if str(el.values.get("stroke", "")) == "none":
            continue
        sp = se.Path(el)
        p = skia.Path()
        for sub in sp.as_subpaths():
            first = True
            for seg in sub:
                if isinstance(seg, se.Move):
                    p.moveTo(seg.end.x, seg.end.y)
                    first = False
                elif isinstance(seg, se.Close):
                    p.close()
                elif isinstance(seg, se.Line):
                    if first:
                        p.moveTo(seg.start.x, seg.start.y)
                        first = False
                    p.lineTo(seg.end.x, seg.end.y)
                else:
                    if first:
                        p.moveTo(seg.start.x, seg.start.y)
                        first = False
                    for i in range(1, 13):
                        q = seg.point(i / 12)
                        p.lineTo(q.x, q.y)
        out.append(p)
    return out


def line_icon(c, name, cx, cy, size, k=1.0, color=WHITE, a=1.0, width=1.6, ring=False, glow=0.0):
    """draw-on line icon (k: 0..1 stroke progress)."""
    if k <= 0 or a <= 0:
        return
    s = size / 24
    c.save()
    c.translate(cx - size / 2, cy - size / 2)
    c.scale(s, s)
    if ring:
        rp = stroke(color, width * 0.7, a * 0.55)
        c.drawArc(skia.Rect.MakeXYWH(-6, -6, 36, 36), -90, 360 * e_out(k), False, rp)
    p = trim(stroke(color, width, a), e_out(k))
    if glow > 0:
        g = trim(stroke(color, width * 3, a * 0.35 * glow, blur=1.2), e_out(k))
        for path in icon_paths(name):
            c.drawPath(path, g)
    for path in icon_paths(name):
        c.drawPath(path, p)
    c.restore()


# ------------------------------------------------------------------ timing helpers
def win(t, t0, t1, fin=0.35, fout=0.25):
    """(in-progress k, alpha) for an element living in [t0, t1]."""
    if t < t0 or t > t1 + fout:
        return 0.0, 0.0
    k = e_out(clamp((t - t0) / fin))
    a = clamp((t - t0) / 0.15) * (1 - clamp((t - t1) / fout))
    return k, a


# ------------------------------------------------------------------ type
def tag(c, s, x, y, t, t0, t1, color=WHITE, size=30, anchor="c", dark=True, accent=None):
    """mono lower-third tag: thin frame + text, revealed by a horizontal wipe."""
    k, a = win(t, t0, t1, fin=0.45)
    if a <= 0:
        return
    tw = measure(s, TAG_FONT, size, 0.12)
    padx, h = size * 0.8, size * 1.9
    w = tw + padx * 2 + (size * 0.9 if accent else 0)
    x0 = x - w / 2 if anchor == "c" else (x - w if anchor == "r" else x)
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(x0 - 4, y - h / 2 - 4, (w + 8) * k, h + 8))
    if dark:
        c.drawRect(skia.Rect.MakeXYWH(x0, y - h / 2, w, h), fill(INK, 0.72 * a))
    c.drawRect(skia.Rect.MakeXYWH(x0, y - h / 2, w, h), stroke(color, 1.6, 0.85 * a, cap="butt"))
    tx = x0 + padx
    if accent:
        c.drawCircle(x0 + padx * 0.75 + 4, y, size * 0.2, fill(accent, a))
        tx += size * 0.9
    text(c, s, tx, y + size * 0.36, TAG_FONT, size, color=color, a=a, anchor="l", tracking=0.12)
    c.restore()
    return w


def headline(c, s, cx, y, size, t, t0, t1, color=WHITE, name="anton", stagger=0.025, maxw=1000, shadow=True):
    """letters rise out of a mask line (editorial reveal), sink back at t1."""
    if t < t0 or t > t1 + 0.4:
        return
    w = measure(s, name, size)
    if w > maxw:
        size *= maxw / w
        w = maxw
    f = font(name, size)
    m = f.getMetrics()
    top = y + m.fAscent * 1.02
    c.save()
    c.clipRect(skia.Rect.MakeLTRB(0, top - 10, W, y + m.fDescent + 6))
    x = cx - w / 2
    for i, ch in enumerate(s):
        cw = f.measureText(ch)
        k = e_out(clamp((t - t0 - i * stagger) / 0.5))
        ko = e_in(clamp((t - t1 - i * stagger * 0.5) / 0.3)) if t > t1 else 0
        yy = y + (1 - k) * size * 1.05 + ko * size * 1.05
        if k > 0 and ch != " ":
            if shadow:
                c.drawString(ch, x, yy + size * 0.03, f, fill(INK, 0.35, blur=size * 0.05))
            c.drawString(ch, x, yy, f, fill(color, 1.0))
        x += cw
    c.restore()


def quote(c, s, x, y, t, t0, t1, size=64, color=WHITE, maxw=860, anchor="l"):
    """serif italic quote with a hairline rule; words fade up one by one."""
    k, a = win(t, t0, t1)
    if a <= 0:
        return
    words = s.split()
    lines, cur = [], ""
    for wd in words:
        tryl = (cur + " " + wd).strip()
        if measure(tryl, "italic", size) <= maxw or not cur:
            cur = tryl
        else:
            lines.append(cur)
            cur = wd
    lines.append(cur)
    lh = size * 1.12
    hgt = lh * len(lines)
    x0 = x if anchor == "l" else x - max(measure(l_, "italic", size) for l_ in lines) / 2
    c.drawRect(skia.Rect.MakeXYWH(x0 - 30, y - size * 0.85, 3, hgt * e_out(k)), fill(TEAL, a))
    wi = 0
    for li, line in enumerate(lines):
        xx = x0
        for wd in line.split():
            kw = e_out(clamp((t - t0 - 0.06 * wi) / 0.35))
            text(c, wd, xx, y + li * lh + (1 - kw) * 14, "italic", size, color=color, a=a * kw, anchor="l")
            xx += measure(wd + " ", "italic", size)
            wi += 1


# ------------------------------------------------------------------ captions (white, editorial kinetic)
class Captions:
    def __init__(self, groups, y=1560, size=72, name=CAP_FONT):
        self.groups, self.y, self.size, self.name = groups, y, size, name
        self.off = []

    def mute(self, a, b):
        self.off.append((a, b))

    def draw(self, c, t, y=None, a=1.0, size=None):
        if any(x <= t < y_ for x, y_ in self.off):
            return
        y = self.y if y is None else y
        S = size or self.size
        for gi, g in enumerate(self.groups):
            g0, g1 = g["words"][0]["s"], g["words"][-1]["e"]
            nxt = self.groups[gi + 1]["words"][0]["s"] if gi + 1 < len(self.groups) else 1e9
            end = min(g1 + 0.35, nxt - 0.02)
            if not (g0 - 0.03 <= t < end):
                continue
            ws = g["words"]
            sizes = [S * (1.18 if w.get("big") else 1.0) for w in ws]
            space = S * 0.3
            widths = [measure(w["w"], self.name, s) for w, s in zip(ws, sizes)]
            lines, cur, cw = [], [], 0
            for i, wd in enumerate(widths):
                if cur and cw + space + wd > 960:
                    lines.append(cur)
                    cur, cw = [], 0
                cur.append(i)
                cw += wd + (space if len(cur) > 1 else 0)
            lines.append(cur)
            lh = S * 1.16
            yy0 = y - (len(lines) - 1) * lh / 2
            ko = clamp((t - (end - 0.08)) / 0.08) if nxt > g1 + 0.37 else 0.0
            for li, line in enumerate(lines):
                tot = sum(widths[i] for i in line) + space * (len(line) - 1)
                x = W / 2 - tot / 2
                for i in line:
                    w = ws[i]
                    k = clamp((t - w["s"] + 0.03) / 0.14)
                    if k <= 0:
                        x += widths[i] + space
                        continue
                    kk = e_out(k)
                    aa = a * kk * (1 - ko)
                    f = font(self.name, sizes[i])
                    yy = yy0 + li * lh + (1 - kk) * 18
                    c.drawString(w["w"], x, yy + 5, f, fill(INK, 0.6 * aa, blur=12))
                    c.drawString(w["w"], x, yy, f, stroke(INK, sizes[i] * 0.05, 0.4 * aa))
                    c.drawString(w["w"], x, yy, f, fill(WHITE, aa))
                    if w.get("big"):
                        uk = e_out(clamp((t - w["s"]) / 0.35))
                        c.drawRect(skia.Rect.MakeXYWH(x, yy + 14, widths[i] * uk, 5), fill(WHITE, aa))
                    x += widths[i] + space


# ------------------------------------------------------------------ giant words behind the speaker
def behind(c, s, cx, y, size, t, t0, t1, color=WHITE, name="anton", stagger=0.035, maxw=1020, alpha=1.0):
    if t < t0 or t > t1 + 0.4:
        return
    w = measure(s, name, size)
    if w > maxw:
        size *= maxw / w
        w = maxw
    f = font(name, size)
    x = cx - w / 2
    for i, ch in enumerate(s):
        cw = f.measureText(ch)
        k = e_out(clamp((t - t0 - i * stagger) / 0.5))
        if k > 0 and ch != " ":
            yy = y + (1 - k) * size * 0.35
            a = k * alpha
            if t > t1:
                ko = clamp((t - t1 - i * stagger * 0.4) / 0.3)
                yy += e_in(ko) * size * 0.25
                a *= 1 - ko
            c.drawString(ch, x, yy + size * 0.03, f, fill(INK, 0.3 * a, blur=size * 0.05))
            c.drawString(ch, x, yy, f, fill(color, a))
        x += cw


# ------------------------------------------------------------------ photo plate
def plate(c, name, cx, cy, w, h, t, t0, t1, caption=None, credit=None, zoom0=1.0, zoom1=1.1, fx=0.5, fy=0.5,
          tint=None):
    """museum-plate photo: hairline frame, vertical mask reveal, slow push, mono caption underneath."""
    k, a = win(t, t0, t1, fin=0.6)
    if a <= 0:
        return
    zk = clamp((t - t0) / max(0.1, t1 - t0))
    x, y = cx - w / 2, cy - h / 2
    c.drawRect(skia.Rect.MakeXYWH(x, y + 18, w, h), fill(INK, 0.45 * a, blur=30))
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(x, y + h * (1 - k), w, h * k))
    draw_image_cover(c, img(name), x, y, w, h, lerp(zoom0, zoom1, e_io(zk)), fx, fy, a)
    if tint:
        c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), fill(tint, 0.18 * a))
    c.restore()
    c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), stroke(WHITE, 2, 0.9 * a, cap="butt"))
    if caption:
        ck = e_out(clamp((t - t0 - 0.35) / 0.4))
        c.drawRect(skia.Rect.MakeXYWH(x, y + h + 22, 40 * ck, 2), fill(TEAL, a))
        text(c, caption, x + 56, y + h + 34, TAG_FONT, 26, color=WHITE, a=a * ck, anchor="l", tracking=0.1)
        if credit:
            text(c, credit, x + w, y + h + 34, TAG_FONT, 20, color=MUTED, a=a * ck * 0.8, anchor="r",
                 tracking=0.08)


# ------------------------------------------------------------------ studio backdrop
def studio_bg(c, t, a=1.0):
    c.drawRect(skia.Rect.MakeWH(W, H), lin_grad(0, 0, 0, H, ["#13171D", "#0B0D11", "#050608"], [0, 0.6, 1], a=a))
    c.drawCircle(W / 2, 600, 900, rad_grad(W / 2, 600, 900, ["#1D2530", "#00000000"], a=0.55 * a))
    dp = fill(WHITE, 0.07 * a)
    for gy in range(60, H, 60):
        for gx in range(30, W, 60):
            c.drawCircle(gx, gy, 1.4, dp)


# ------------------------------------------------------------------ diagram parts
def box_node(c, s, cx, cy, t, t0, t1=None, icon=None, color=WHITE, w=None, size=34, sub=None, active=0.0):
    """thin-bordered node with a line icon and a mono/heavy label; draws on."""
    k, a = win(t, t0, 1e9 if t1 is None else t1, fin=0.5)
    if a <= 0:
        return
    tw = measure(s, "heavy", size)
    ww = w or tw + (130 if icon else 70)
    hh = size * 2.4 + (size * 0.8 if sub else 0)
    x, y = cx - ww / 2, cy - hh / 2
    c.drawRect(skia.Rect.MakeXYWH(x, y, ww, hh), fill(PANEL, 0.88 * a))
    if active > 0:
        c.drawRect(skia.Rect.MakeXYWH(x - 3, y - 3, ww + 6, hh + 6), stroke(color, 6, 0.35 * active * a, blur=8))
    pr = trim(stroke(color, 2, a, cap="butt"), k)
    path = skia.Path()
    path.addRect(skia.Rect.MakeXYWH(x, y, ww, hh))
    c.drawPath(path, pr)
    tx = cx + (32 if icon else 0)
    if icon:
        line_icon(c, icon, x + 56, cy - (size * 0.4 if sub else 0), size * 1.35, k=k, color=color, a=a, width=1.7)
    text(c, s, tx, cy + size * 0.36 - (size * 0.4 if sub else 0), "heavy", size, color=WHITE, a=a * k)
    if sub:
        text(c, sub, tx, cy + size * 0.36 + size * 0.75, TAG_FONT, size * 0.6, color=MUTED, a=a * k, tracking=0.1)


def arrow(c, x0, y0, x1, y1, k, color=WHITE, a=1.0, width=2.5, head=16):
    if k <= 0 or a <= 0:
        return
    xe, ye = lerp(x0, x1, k), lerp(y0, y1, k)
    c.drawLine(x0, y0, xe, ye, stroke(color, width, a))
    ang = math.atan2(y1 - y0, x1 - x0)
    for d in (2.6, -2.6):
        c.drawLine(xe, ye, xe + math.cos(ang + d) * head, ye + math.sin(ang + d) * head, stroke(color, width, a))


def ring_loop(c, t, cx, cy, R, items, t0, t1, phase=0.0, broken=None, reverse=False, color=WHITE, amul=1.0):
    """hairline circle, small nodes + labels outside, travelling pulse. items = [(label, icon, t_on, colour)]"""
    if t < t0 or t > t1 + 0.4:
        return
    a = clamp((t - t0) / 0.3) * (1 - clamp((t - t1) / 0.3)) * amul
    rk = e_out(clamp((t - t0) / 0.9))
    rect = skia.Rect.MakeXYWH(cx - R, cy - R, 2 * R, 2 * R)
    c.drawArc(rect, -90, 360 * rk, False, stroke(color, 2, 0.5 * a))
    n = len(items)
    sgn = -1 if reverse else 1
    angs = [-math.pi / 2 + sgn * i * math.tau / n for i in range(n)]
    gap = 0.0 if broken is None else e_out(clamp((t - broken) / 0.35))
    for i in range(n):
        mid = angs[i] + sgn * math.pi / n
        hx, hy = cx + math.cos(mid) * R, cy + math.sin(mid) * R
        tang = mid + sgn * math.pi / 2
        if broken is not None and i == 0 and gap > 0:
            continue
        for d in (2.5, -2.5):
            c.drawLine(hx + math.cos(tang) * 9, hy + math.sin(tang) * 9,
                       hx + math.cos(tang) * 9 + math.cos(tang + d) * 18, hy + math.sin(tang) * 9 + math.sin(tang + d) * 18,
                       stroke(color, 2.5, a * rk))
    if broken is None or t < broken:
        ang = -math.pi / 2 + sgn * (phase % 1.0) * math.tau
        px, py = cx + math.cos(ang) * R, cy + math.sin(ang) * R
        c.drawCircle(px, py, 18, fill(color, 0.35 * a, blur=10))
        c.drawCircle(px, py, 7, fill(WHITE, a))
    else:
        ga = angs[0] + sgn * math.pi / n
        bx, by = cx + math.cos(ga) * R, cy + math.sin(ga) * R
        c.drawCircle(bx, by, 46 * gap, fill(INK, a))
        c.drawCircle(bx, by, 46 * gap, stroke(WARN, 2.5, a))
        s_ = 15 * gap
        c.drawLine(bx - s_, by - s_, bx + s_, by + s_, stroke(WARN, 3, a))
        c.drawLine(bx + s_, by - s_, bx - s_, by + s_, stroke(WARN, 3, a))
    for i, (lab, ic, ton, colr) in enumerate(items):
        k = e_out(clamp((t - ton) / 0.45))
        if k <= 0:
            continue
        x, y = cx + math.cos(angs[i]) * R, cy + math.sin(angs[i]) * R
        lit = math.exp(-max(0, t - ton) * 2.0)
        c.drawCircle(x, y, 52, fill(PANEL, a))
        c.drawCircle(x, y, 52, stroke(colr, 2, a * k))
        if lit > 0.02:
            c.drawCircle(x, y, 60, stroke(colr, 8, a * 0.4 * lit, blur=8))
        line_icon(c, ic, x, y, 54, k=k, color=colr, a=a, width=1.7)
        ox, oy = math.cos(angs[i]), math.sin(angs[i])
        lx, ly = x + ox * 92, y + oy * 92 + 11
        anc = "c" if abs(ox) < 0.3 else ("l" if ox > 0 else "r")
        if abs(ox) < 0.3:
            ly = y + oy * 88 + (11 if oy > 0 else 0) + (14 if oy > 0 else -4)
        text(c, lab, lx, ly, TAG_FONT, 30, color=WHITE, a=a * k, anchor=anc, tracking=0.1)


def rank_rows(c, t, rows, x, y0, gap, wmax):
    """rows = [(n, label, frac, t_on, t_off, colour)] - serif numerals + hairline bars."""
    for i, (n, lab, frac, ton, toff, colr) in enumerate(rows):
        k, a = win(t, ton, toff)
        if a <= 0:
            continue
        y = y0 + i * gap
        text(c, f"{n:02d}", x, y + 26, "serif", 84, color=WHITE, a=a * 0.85, anchor="l")
        text(c, lab, x + 140, y - 8, "heavy", 48, color=WHITE, a=a, anchor="l")
        c.drawRect(skia.Rect.MakeXYWH(x + 140, y + 22, wmax - 140, 4), fill(WHITE, 0.15 * a))
        c.drawRect(skia.Rect.MakeXYWH(x + 140, y + 22, (wmax - 140) * frac * e_out(clamp((t - ton - 0.15) / 0.8)), 4),
                   fill(colr, a))


def comment_cta(c, t, t0, t1, cx, cy, typed, t_type):
    k, a = win(t, t0, t1, fin=0.5)
    if a <= 0:
        return
    w, h = 820, 128
    x, y = cx - w / 2, cy - h / 2
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(x - 4, y - 4, (w + 8) * k, h + 8))
    c.drawRRect(rrect(x, y, w, h, 18), fill(INK, 0.78 * a))
    c.drawRRect(rrect(x, y, w, h, 18), stroke(WHITE, 2, 0.9 * a))
    line_icon(c, "message-circle", x + 68, cy, 56, k=k, a=a, width=1.6)
    text(c, "COMMENT", x + 128, cy - 14, TAG_FONT, 22, color=MUTED, a=a, anchor="l", tracking=0.14)
    n = int(clamp((t - t_type) / 0.6) * len(typed) + 0.001)
    s = typed[:n]
    text(c, s, x + 128, cy + 34, "heavy", 50, color=WHITE, a=a, anchor="l")
    if n < len(typed) or (t * 2) % 1 < 0.5:
        cw = measure(s, "heavy", 50)
        c.drawRect(skia.Rect.MakeXYWH(x + 134 + cw, cy - 4, 3, 46), fill(WHITE, a))
    line_icon(c, "send", x + w - 70, cy, 50, k=clamp((t - t_type - 0.6) / 0.4), color=TEAL, a=a, width=1.8)
    c.restore()


def big_number(c, s, cx, y, size, t, t0, t1, unit=None, color=WHITE):
    headline(c, s, cx, y, size, t, t0, t1, color=color, name="anton")
    if unit:
        tag(c, unit, cx, y + 60, t, t0 + 0.25, t1, size=28)


def scrim(c, x, y, w, h, a, strength=0.62):
    """soft dark panel behind text placed over busy footage."""
    if a <= 0:
        return
    c.drawRRect(rrect(x, y, w, h, 28), fill(INK, strength * a, blur=40))
