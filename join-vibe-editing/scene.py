"""scene: the 'Join Vibe Editing' pool reel.

Layers per frame (back to front):
  footage -> kinetic captions (BEHIND the speaker) -> speaker cut-out (matte) -> white motion graphics
  -> paper-cut transitions -> end card.

    python3 scene.py stills 0.6 5.3 13.5 ...   # check frames -> out/stills/
    python3 scene.py render                     # full render -> work/picture.mp4 (silent)
    python3 scene.py render 17 24               # a range, for quick checks
"""
import math
import multiprocessing as mp
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "vibe")
import numpy as np  # noqa: E402
import skia  # noqa: E402
from motion_kit import (clamp, ease_in_out_cubic, ease_out_back, ease_out_cubic, lerp, noise1, prog,  # noqa: E402
                        pulse, rgb, text_width, typeface)
from toon_kit import paper_texture, stepped  # noqa: E402
from vibelib import FrameWriter, concat_videos, ffmpeg_bin  # noqa: E402

import timeline as TL  # noqa: E402

W, H, FPS = TL.W, TL.H, TL.FPS
WHITE, BLUE, NAVY, INK = rgb(TL.WHITE), rgb(TL.BLUE), rgb(TL.NAVY), rgb(TL.INK)
SHADOW = skia.Color(0, 0, 0, 90)

# ---------------------------------------------------------------- textures (built once)
TEX = {k: paper_texture(W, H, base=v, grain=0.07, seed=i) for i, (k, v) in
       enumerate({"blue": TL.BLUE, "white": "#FBFAF6", "navy": TL.NAVY}.items())}


def font(name, size):
    f = skia.Font(typeface(name), size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


def fill(col, alpha=1.0):
    c4 = skia.Color4f(col)
    c4.fA *= clamp(alpha)
    return skia.Paint(Color4f=c4, AntiAlias=True)


def stroke(col, w, alpha=1.0):
    p = fill(col, alpha)
    p.setStyle(skia.Paint.kStroke_Style)
    p.setStrokeWidth(w)
    p.setStrokeCap(skia.Paint.kRound_Cap)
    p.setStrokeJoin(skia.Paint.kRound_Join)
    return p


def blurred(col, sigma, alpha=1.0):
    p = fill(col, alpha)
    p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, sigma))
    return p


def scaled(c, cx, cy, s):
    c.translate(cx, cy)
    c.scale(s, s)
    c.translate(-cx, -cy)


# ---------------------------------------------------------------- torn paper
def torn_line(x0, x1, y, seed, amp=16, step=22):
    rng = np.random.default_rng(seed)
    n = max(2, int(abs(x1 - x0) / step))
    xs = np.linspace(x0, x1, n + 1)
    ys = y + rng.uniform(-amp, amp, n + 1) + amp * 0.6 * np.sin(np.arange(n + 1) * 0.7 + seed)
    return list(zip(xs, ys))


def torn_rect(x, y, w, h, seed, amp=14):
    """Rectangle with torn top and bottom edges and slightly ragged sides."""
    top = torn_line(x, x + w, y, seed, amp)
    bot = torn_line(x + w, x, y + h, seed + 7, amp)
    p = skia.Path()
    p.moveTo(*top[0])
    for q in top[1:]:
        p.lineTo(*q)
    for q in torn_line(y, y + h, x + w, seed + 3, amp * 0.3, 60):
        p.lineTo(x + w + (q[1] - (x + w)), q[0])
    for q in bot:
        p.lineTo(*q)
    for q in torn_line(y + h, y, x, seed + 5, amp * 0.3, 60):
        p.lineTo(x + (q[1] - x), q[0])
    p.close()
    return p


def paper(c, path, tex, depth=18):
    """Paper-cut piece: soft drop shadow + textured flat fill."""
    c.save()
    c.translate(depth * 0.35, depth)
    c.drawPath(path, blurred(skia.ColorBLACK, depth * 0.6, 0.35))
    c.restore()
    p = skia.Paint(AntiAlias=True)
    p.setShader(TEX[tex].makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat, skia.SamplingOptions()))
    c.drawPath(path, p)


SHEET = {s: torn_rect(-200, -1250, W + 400, 2500, seed=s, amp=26) for s in range(1, 13)}
BAND = {s: torn_rect(-300, -210, W + 600, 420, seed=s, amp=18) for s in range(20, 30)}


def wipe(c, t, t0, seeds=(1, 2), dur=0.72, angle=-7):
    """Two torn sheets (blue then white) sweep bottom -> top, fully covering at t0."""
    ts = stepped(t, 15)
    for i, (tex, seed) in enumerate((("blue", seeds[0]), ("white", seeds[1]))):
        k = (ts - (t0 - dur / 2) + (0.05 if i == 0 else -0.03)) / dur
        if not 0 < k < 1:
            continue
        cy = lerp(H + 1450, -1450, ease_in_out_cubic(k))
        c.save()
        c.translate(W / 2, cy)
        c.rotate(angle + 2 * noise1(ts * 7, seed))
        c.translate(-W / 2, 0)
        paper(c, SHEET[seed], tex, 26)
        c.restore()


def strips(c, t, t0, dur=0.6):
    """Two torn bands cross the face area in opposite directions, centred on the cut."""
    ts = stepped(t, 15)
    k = (ts - (t0 - dur / 2)) / dur
    if not 0 < k < 1:
        return
    e = ease_in_out_cubic(k)
    for i, (tex, y, d, ang) in enumerate((("blue", 900, 1, -4), ("white", 1290, -1, 3))):
        x = lerp(-W * 1.35, W * 1.35, e) * d
        c.save()
        c.translate(W / 2 + x, y)
        c.rotate(ang)
        c.translate(-W / 2, 0)
        paper(c, BAND[20 + i], tex, 18)
        c.restore()


# ---------------------------------------------------------------- captions (behind the speaker)
CAP_Y = 765            # centre of the last caption line
BASE, EMPH = 172, 212
GAP = 0.22


def _layout(chunk):
    items = []
    for w in chunk["words"]:
        size = EMPH if w["k"] in TL.EMPHASIS else BASE
        items.append([w, size, font("impact", size).measureText(w["k"])])
    lines, cur, cw = [], [], 0
    for it in items:
        add = it[2] + (GAP * it[1] if cur else 0)
        if cur and cw + add > 960:
            lines.append(cur)
            cur, cw = [], 0
            add = it[2]
        cur.append(it)
        cw += add
    lines.append(cur)
    out, lh = [], 0
    heights = [max(i[1] for i in ln) * 0.98 for ln in lines]
    y = CAP_Y - sum(heights[1:])
    for ln, lh in zip(lines, heights):
        width = sum(i[2] for i in ln) + sum(GAP * i[1] for i in ln[1:])
        x = W / 2 - width / 2
        for j, (w, size, tw) in enumerate(ln):
            if j:
                x += GAP * size
            out.append({"w": w, "size": size, "x": x, "cx": x + tw / 2, "y": y, "tw": tw})
            x += tw
        y += lh
    return out


LAYOUT = [_layout(ch) for ch in TL.CHUNKS]
BURST_WORDS = {"SETUP", "SWIMMING", "DONE", "SECOND", "COMMENT"}


def draw_word(c, it, t):
    w, size = it["w"], it["size"]
    k = prog(t, w["s"] - 0.05, 0.16)
    if k <= 0:
        return
    f = font("impact", size)
    cap = f.getMetrics().fCapHeight
    base_y = it["y"] + cap / 2
    active = w["s"] <= t < w["e"] + 0.05
    s = (0.35 + 0.65 * ease_out_back(k)) * (1.07 if active else 1.0)
    lift = (1 - ease_out_cubic(k)) * 40 + (6 if active else 0)
    emph = w["k"] in TL.EMPHASIS
    c.save()
    scaled(c, it["cx"], it["y"], s)
    c.translate(0, -lift)
    c.drawString(w["k"], it["x"] + 4, base_y + 10, f, blurred(skia.ColorBLACK, 14, 0.6 * k))
    c.drawString(w["k"], it["x"] + 2, base_y + 4, f, blurred(NAVY, 4, 0.45 * k))
    if emph:
        c.drawString(w["k"], it["x"], base_y, f, stroke(WHITE, 14, k))
        c.drawString(w["k"], it["x"], base_y, f, fill(BLUE, k))
    else:
        c.drawString(w["k"], it["x"], base_y, f, fill(WHITE, k))
    # strike-through ("I don't EDIT anymore")
    for (a, b), key in TL.STRIKE.items():
        if key == w["k"] and a <= w["s"] <= b:
            ks = ease_out_cubic(prog(t, w["s"] + 0.25, 0.18))
            if ks > 0:
                x0, x1 = it["x"] - 14, it["x"] - 14 + (it["tw"] + 28) * ks
                c.drawLine(x0, base_y - cap * 0.42, x1, base_y - cap * 0.55, stroke(WHITE, 16))
    c.restore()
    # burst of white strokes on hero words
    if w["k"] in BURST_WORDS:
        kb = prog(t, w["s"], 0.35)
        if 0 < kb < 1:
            e = ease_out_cubic(kb)
            r0, r1 = it["tw"] * 0.55 + 20 + 50 * e, it["tw"] * 0.55 + 60 + 70 * e
            for i in range(10):
                a = i / 10 * 2 * math.pi + 0.3
                c.drawLine(it["cx"] + r0 * math.cos(a), it["y"] + r0 * 0.6 * math.sin(a),
                           it["cx"] + r1 * math.cos(a), it["y"] + r1 * 0.6 * math.sin(a), stroke(WHITE, 7, 1 - kb))


def captions(c, t):
    if t >= TL.VIDEO_DUR:
        return
    for ch, lay in zip(TL.CHUNKS, LAYOUT):
        if ch["s"] <= t < ch["e"]:
            for it in lay:
                draw_word(c, it, t)


# ---------------------------------------------------------------- white motion graphics (front)
L, T, R, B = 56, 252, W - 56, 1492


def brackets(c, t):
    k = ease_out_cubic(prog(t, 0.0, 0.45))
    if k <= 0:
        return
    p = pulse(t, TL.BPM, decay=9) * 8
    ln = 92 * k
    pen = stroke(WHITE, 7)
    for (x, y, dx, dy) in ((L - p, T - p, 1, 1), (R + p, T - p, -1, 1), (L - p, B + p, 1, -1), (R + p, B + p, -1, -1)):
        pth = skia.Path()
        pth.moveTo(x, y + dy * ln)
        pth.lineTo(x, y)
        pth.lineTo(x + dx * ln, y)
        c.drawPath(pth, pen)
    if t < TL.VIDEO_DUR:
        a = clamp(prog(t, 0.2, 0.3))
        if int(t * 2) % 2 == 0:
            c.drawCircle(L + 44, T + 48, 11, fill(WHITE, a))
        c.drawString("REC", L + 66, T + 60, font("mono", 32), fill(WHITE, a))
        tc = f"00:{int(t):02d}:{int(t * FPS) % FPS:02d}"
        f = font("mono", 32)
        c.drawString(tc, R - 30 - f.measureText(tc), T + 60, f, fill(WHITE, a))
        # progress line along the bottom
        y = T + 96
        c.drawLine(L + 40, y, R - 40, y, stroke(WHITE, 5, 0.35 * a))
        c.drawLine(L + 40, y, lerp(L + 40, R - 40, t / TL.VIDEO_DUR), y, stroke(WHITE, 5, a))


def arrow(c, t):
    a, b = TL.EV["arrow"]
    k = ease_out_cubic(prog(t, a + 0.15, 0.45))
    out = prog(t, b - 0.2, 0.2)
    if k <= 0 or out >= 1:
        return
    pth = skia.Path()
    pth.moveTo(930, 1330)
    pth.cubicTo(990, 1210, 930, 1120, 800, 1080)
    meas = skia.PathMeasure(pth, False)
    seg = skia.Path()
    meas.getSegment(0, meas.getLength() * k, seg, True)
    al = 1 - out
    c.drawPath(seg, stroke(WHITE, 9, al))
    if k > 0.95:
        c.drawLine(800, 1080, 850, 1060, stroke(WHITE, 9, al))
        c.drawLine(800, 1080, 832, 1124, stroke(WHITE, 9, al))
    f = font("mono", 34)
    lbl = "MY OFFICE"
    c.drawString(lbl, 930 - f.measureText(lbl) / 2 - 30, 1385, f, fill(WHITE, al * clamp(k * 2)))


def pop_scale(t, a, b, d=0.28):
    return ease_out_back(prog(t, a, d)) * (1 - ease_in_out_cubic(prog(t, b - 0.18, 0.18)))


def phone(c, t):
    a, b = TL.EV["phone"]
    s = pop_scale(t, a, b)
    if s <= 0.01:
        return
    cx, cy = 900, 1010
    c.save()
    scaled(c, cx, cy, s)
    c.rotate(0)
    r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - 80, cy - 145, 160, 290), 28, 28)
    c.drawRRect(r, stroke(WHITE, 8))
    c.drawLine(cx - 22, cy - 120, cx + 22, cy - 120, stroke(WHITE, 7))
    if int(t * 3) % 2 == 0:
        c.drawCircle(cx, cy, 24, fill(WHITE))
    c.drawCircle(cx, cy, 38, stroke(WHITE, 5))
    f = font("mono", 30)
    c.drawString("1 TAKE", cx - f.measureText("1 TAKE") / 2, cy + 200, f, fill(WHITE))
    c.restore()


PROMPT = "Edit this into a reel"


def prompt(c, t):
    a, b = TL.EV["prompt"]
    s = pop_scale(t, a, b)
    if s <= 0.01:
        return
    x, y, w, h = 70, 1350, W - 140, 120
    c.save()
    scaled(c, W / 2, y + h / 2, s)
    c.drawString("YOUR PROMPT", x + 10, y - 22, font("mono", 30), fill(WHITE))
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), 62, 62)
    c.save()
    c.translate(0, 12)
    c.drawRRect(rr, blurred(skia.ColorBLACK, 16, 0.3))
    c.restore()
    c.drawRRect(rr, fill(WHITE))
    n = int(len(PROMPT) * clamp(prog(t, a + 0.25, TL.W_("WANTED") - a - 0.1)))
    f = font("body", 50)
    shown = PROMPT[:n]
    c.drawString(shown, x + 50, y + h / 2 + 18, f, fill(INK))
    if int(t * 2.5) % 2 == 0 and n < len(PROMPT):
        cx = x + 54 + f.measureText(shown)
        c.drawLine(cx, y + 34, cx, y + h - 34, stroke(BLUE, 5))
    # send button: pulses on "line"
    sp = 1 + 0.25 * math.exp(-max(0, t - TL.W_("LINE")) * 8) * (t >= TL.W_("LINE"))
    bx, by = x + w - 64, y + h / 2
    c.drawCircle(bx, by, 44 * sp, fill(BLUE))
    c.drawLine(bx, by + 18, bx, by - 18, stroke(WHITE, 7))
    c.drawLine(bx - 15, by - 4, bx, by - 19, stroke(WHITE, 7))
    c.drawLine(bx + 15, by - 4, bx, by - 19, stroke(WHITE, 7))
    c.restore()


CHIP_W = 350
CHIP_PATHS = [torn_rect(0, 0, CHIP_W, 72, seed=40 + i, amp=6) for i in range(4)]


def chips(c, t):
    end = TL.EV["chips_end"]
    if t > end + 0.15:
        return
    for i, (label, at) in enumerate(TL.EV["chips"]):
        ts = stepped(t, 12)
        k = prog(ts, at - 0.05, 0.25)
        if k <= 0:
            continue
        e = ease_out_back(k)
        x = lerp(W + 60, W - 40 - CHIP_W, e)
        y = 930 + i * 84
        c.save()
        c.translate(x, y)
        c.rotate((-2.5 if i % 2 else 2.0) + 0.6 * noise1(ts * 12, i))
        paper(c, CHIP_PATHS[i], "white", 10)
        c.drawCircle(40, 36, 21, fill(BLUE))
        c.drawLine(31, 37, 38, 45, stroke(WHITE, 5))
        c.drawLine(38, 45, 50, 28, stroke(WHITE, 5))
        c.drawString(label, 74, 53, font("impact", 42), fill(INK))
        c.restore()
    # big white check on DONE
    kd = ease_out_cubic(prog(t, TL.EV["done"], 0.3))
    if kd > 0 and t < end + 0.2:
        pth = skia.Path()
        pth.moveTo(760, 1330)
        pth.lineTo(830, 1400)
        pth.lineTo(990, 1270)
        meas = skia.PathMeasure(pth, False)
        seg = skia.Path()
        meas.getSegment(0, meas.getLength() * kd, seg, True)
        c.drawPath(seg, stroke(WHITE, 22))


def edittime(c, t):
    a, b = TL.EV["edittime"]
    s = pop_scale(t, a, b)
    if s <= 0.01:
        return
    w, h = 700, 124
    x, y = (W - w) / 2, 1350
    c.save()
    scaled(c, W / 2, y + h / 2, s)
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), 65, 65)
    c.save()
    c.translate(0, 12)
    c.drawRRect(rr, blurred(skia.ColorBLACK, 16, 0.3))
    c.restore()
    c.drawRRect(rr, fill(WHITE))
    c.drawString("EDIT TIME", x + 56, y + h / 2 + 14, font("mono", 42), fill(INK))
    # the counter tries to tick, then snaps to zero
    k = prog(t, a + 0.3, 0.6)
    val = "0:00" if k >= 1 or k <= 0 else f"0:{int(noise1(t * 20, 3) * 30 + 30) % 60:02d}"
    f = font("impact", 92)
    c.drawString(val, x + w - 56 - f.measureText(val), y + h / 2 + 34, f, fill(BLUE))
    c.restore()


def comment(c, t):
    a, b = TL.EV["comment"]
    s = pop_scale(t, a, b + 0.3)
    if s <= 0.01:
        return
    w, h = 760, 150
    x, y = (W - w) / 2, 1330
    c.save()
    scaled(c, W / 2, y + h / 2, s * (1 + 0.03 * pulse(t, TL.BPM, decay=10)))
    c.drawString("COMMENT", x + 14, y - 24, font("mono", 32), fill(WHITE))
    bub = skia.Path()
    bub.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), 46, 46))
    tail = skia.Path()
    tail.moveTo(x + 120, y + h - 4)
    tail.lineTo(x + 92, y + h + 52)
    tail.lineTo(x + 190, y + h - 4)
    tail.close()
    bub = skia.Op(bub, tail, skia.PathOp.kUnion_PathOp)
    c.save()
    c.translate(0, 12)
    c.drawPath(bub, blurred(skia.ColorBLACK, 16, 0.3))
    c.restore()
    c.drawPath(bub, fill(WHITE))
    c.drawCircle(x + 84, y + h / 2, 44, fill(BLUE))
    c.drawCircle(x + 84, y + h / 2 - 10, 15, fill(WHITE))
    c.drawCircle(x + 84, y + h / 2 + 30, 24, fill(WHITE))
    word = "SYSTEM"
    n = int(len(word) * clamp(prog(t, TL.W_("SYSTEM", 30.0), 0.35)))
    f = font("impact", 104)
    c.drawString(word[:n], x + 160, y + h / 2 + 38, f, fill(BLUE))
    if n < len(word) and int(t * 2.5) % 2 == 0:
        cx = x + 166 + f.measureText(word[:n])
        c.drawLine(cx, y + 36, cx, y + h - 36, stroke(INK, 5))
    c.restore()


# ---------------------------------------------------------------- end card
STICKER = None


def _sticker():
    """Cut-out of the speaker with a thick white paper border (made once)."""
    import cv2
    from motion_kit import with_alpha  # noqa: F401
    t = 29.2
    rgbf = read_frames(TL.VIDEO, t, 1, 3).__next__()
    a = read_frames(TL.MATTE, t, 1, 1).__next__()[..., 0]
    a = (a > 110).astype(np.uint8) * 255
    border = cv2.dilate(a, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (37, 37)))
    ys, xs = np.where(border > 0)
    y0, y1, x0, x1 = ys.min(), H, xs.min(), xs.max() + 1
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = 255
    rgba[..., 3] = border
    k = a[..., None] > 0
    rgba[..., :3] = np.where(k, rgbf, rgba[..., :3])
    crop = np.ascontiguousarray(rgba[y0:y1, x0:x1])
    return skia.Image.fromarray(crop, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType)


PANEL = torn_rect(0, 0, 860, 600, seed=77, amp=14)
STRIP = {s: torn_rect(-200, 0, W + 400, 170, seed=s, amp=16) for s in (60, 61)}


def star(cx, cy, r, ts, seed):
    p = skia.Path()
    rot = noise1(ts * 12, seed) * 0.15
    for i in range(8):
        rr = r if i % 2 == 0 else r * 0.32
        a = i / 8 * 2 * math.pi + rot
        (p.moveTo if i == 0 else p.lineTo)(cx + rr * math.sin(a), cy - rr * math.cos(a))
    p.close()
    return p


def endcard(c, t):
    global STICKER
    t0 = TL.VIDEO_DUR
    # blue sheet slides up and stays as the background
    ts = stepped(t, 15)
    k = clamp((ts - (t0 - 0.36)) / 0.36)
    if k <= 0:
        return
    cy = lerp(H + 1300, H / 2, ease_out_cubic(k))
    c.save()
    c.translate(W / 2, cy)
    c.rotate(-7 * (1 - k))
    c.translate(-W / 2, 0)
    paper(c, SHEET[9], "blue", 26)
    c.restore()
    if t < t0:
        return
    u = t - t0
    us = stepped(u, 12)
    # navy torn strips
    for i, (seed, y, ang, d) in enumerate(((60, 300, -6, -1), (61, 1500, 5, 1))):
        kk = ease_out_cubic(clamp(us / 0.35))
        c.save()
        c.translate(W / 2 + d * (1 - kk) * W * 1.3, y)
        c.rotate(ang + noise1(us * 12, seed) * 0.6)
        c.translate(-W / 2, -85)
        paper(c, STRIP[seed], "navy", 14)
        c.restore()
    # white panel with the message
    kp = ease_out_back(clamp((us - 0.1) / 0.3))
    if kp > 0:
        c.save()
        c.translate(W / 2, 830)
        c.rotate(-3 + noise1(us * 12, 5) * 0.7)
        c.scale(kp, kp)
        c.translate(-430, -300)
        paper(c, PANEL, "white", 22)
        for j, (word, fnt, size, y, col, at) in enumerate((("JOIN", "impact", 110, 140, BLUE, 0.3),
                                                            ("VIBE", "impact", 220, 375, INK, 0.45),
                                                            ("EDITING", "impact", 220, 565, INK, 0.6))):
            kw = ease_out_back(clamp((us - at) / 0.22))
            if kw <= 0:
                continue
            f = font(fnt, size)
            tw = f.measureText(word)
            c.save()
            scaled(c, 430, y - size * 0.35, kw)
            c.rotate(noise1(us * 12, 10 + j) * 0.8)
            c.drawString(word, 430 - tw / 2, y, f, fill(col))
            c.restore()
        c.restore()
    # speaker sticker
    if STICKER is None:
        STICKER = _sticker()
    ks = ease_out_back(clamp((us - 0.35) / 0.35))
    if ks > 0:
        sc = 0.56
        sw, sh = STICKER.width() * sc, STICKER.height() * sc
        x = W / 2 - sw / 2 + 20
        y = lerp(H + 50, H - sh + 30, ks)
        c.save()
        c.translate(x + sw / 2, y + sh)
        c.rotate(3 + noise1(us * 12, 9) * 0.6)
        c.translate(-sw / 2, -sh)
        c.save()
        c.translate(10, 16)
        c.drawImageRect(STICKER, skia.Rect.MakeWH(sw, sh), skia.SamplingOptions(skia.FilterMode.kLinear),
                        skia.Paint(Alphaf=0.35, ImageFilter=skia.ImageFilters.ColorFilter(
                            skia.ColorFilters.Blend(skia.ColorBLACK, skia.BlendMode.kSrcIn),
                            skia.ImageFilters.Blur(10, 10))))
        c.restore()
        c.drawImageRect(STICKER, skia.Rect.MakeWH(sw, sh), skia.SamplingOptions(skia.FilterMode.kLinear))
        c.restore()
    # white paper stars
    for i, (sx, sy, r, at) in enumerate(((150, 470, 46, 0.7), (950, 1180, 40, 0.8), (930, 430, 30, 0.9),
                                         (130, 1240, 34, 1.0))):
        kk = ease_out_back(clamp((us - at) / 0.25))
        if kk > 0:
            paper(c, star(sx, sy, r * kk, us, i), "white", 8)


# ---------------------------------------------------------------- frame assembly
def read_frames(path, start, n, ch):
    pix = {1: "gray", 3: "rgb24"}[ch]
    p = subprocess.Popen([ffmpeg_bin(), "-v", "error", "-ss", f"{start:.4f}", "-i", str(path), "-frames:v", str(n),
                          "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", pix, "-"], stdout=subprocess.PIPE)
    size = W * H * ch
    while True:
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        yield np.frombuffer(buf, np.uint8).reshape(H, W, ch)
    p.wait()


def compose(t, frame, matte):
    surf = skia.Surface(W, H)
    with surf as c:
        c.clear(skia.ColorBLACK)
        if frame is not None and t < TL.VIDEO_DUR + 0.5:
            rgba = np.dstack([frame, np.full((H, W, 1), 255, np.uint8)])
            c.drawImage(skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType), 0, 0)
            captions(c, t)
            a = matte[..., 0].astype(np.float32) / 255
            a = np.clip((a - 0.25) / 0.6, 0, 1)
            person = np.empty((H, W, 4), np.uint8)
            person[..., :3] = (frame * a[..., None]).astype(np.uint8)
            person[..., 3] = (a * 255).astype(np.uint8)
            c.drawImage(skia.Image.fromarray(person, colorType=skia.kRGBA_8888_ColorType,
                                             alphaType=skia.kPremul_AlphaType), 0, 0)
            arrow(c, t)
            phone(c, t)
            prompt(c, t)
            chips(c, t)
            edittime(c, t)
            comment(c, t)
        for t0, kind in TL.TRANSITIONS:
            if kind == "wipe":
                wipe(c, t, t0, seeds=(int(t0) % 6 + 1, int(t0) % 6 + 7))
            elif kind == "strips":
                strips(c, t, t0)
        endcard(c, t)
        brackets(c, t)
    return surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3]


def _chunk(args):
    f0, f1, path = args
    n_video = max(0, min(f1, int(TL.VIDEO_DUR * FPS) + 1) - f0)
    vid = read_frames(TL.VIDEO, f0 / FPS, n_video, 3) if n_video else iter(())
    mat = read_frames(TL.MATTE, f0 / FPS, n_video, 1) if n_video else iter(())
    last = (None, None)
    with FrameWriter(path, W, H, FPS, crf=16) as fw:
        for f in range(f0, f1):
            fr, ma = next(vid, None), next(mat, None)
            if fr is not None and ma is not None:
                last = (fr, ma)
            fw.write(compose(f / FPS, *last))
    return path


def render(start=0.0, end=None, out="work/picture.mp4", workers=4):
    end = TL.DURATION if end is None else end
    f0, f1 = int(round(start * FPS)), int(round(end * FPS))
    bounds = np.linspace(f0, f1, workers + 1).astype(int)
    tmp = Path(tempfile.mkdtemp(prefix="render_", dir="work"))
    jobs = [(int(a), int(b), str(tmp / f"part_{i:02d}.mp4")) for i, (a, b) in enumerate(zip(bounds, bounds[1:]))
            if b > a]
    print(f"rendering {f1 - f0} frames on {len(jobs)} workers ...")
    with mp.get_context("fork").Pool(len(jobs)) as pool:
        parts = pool.map(_chunk, jobs)
    concat_videos(parts, out)
    for p in tmp.iterdir():
        p.unlink()
    tmp.rmdir()
    print("done ->", out)


def stills(times, out_dir="out/stills"):
    from PIL import Image
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    for t in times:
        if t < TL.VIDEO_DUR:
            fr = next(read_frames(TL.VIDEO, t, 1, 3))
            ma = next(read_frames(TL.MATTE, t, 1, 1))
        else:
            fr = ma = None
        p = Path(out_dir) / f"scene_{t:06.2f}.png"
        Image.fromarray(compose(t, fr, ma)).save(p)
        print("  still", p)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stills"
    if cmd == "stills":
        stills([float(x) for x in sys.argv[2:]] or [0.9, 5.4, 13.5, 20.5, 27.4, 30.6, 34.5])
    elif cmd == "render":
        a = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
        b = float(sys.argv[3]) if len(sys.argv) > 3 else None
        render(a, b, out="work/picture.mp4" if len(sys.argv) <= 2 else f"work/picture_{a:g}-{b:g}.mp4")
