"""TIME ad, "blueprint desk" version: the same cut as edit.py, restyled in the cutting-mat design system.

    python3 edit_blueprint.py stills 1.0 8.5 ...   -> out/stills/*.png (half res)
    python3 edit_blueprint.py sheet                -> out/sheet_blueprint.png
    python3 edit_blueprint.py render               -> out/vibe_edit_time_blueprint.mp4

Look (from the reference flyer): a blue self-healing cutting mat with a fine grid, desk props lying on it
(laptop, earbuds case, smartwatch, pencil, phone, tool strip), the speaker as a die-cut sticker with a thick
white border and a soft shadow, and captions as tilted colour blocks (royal blue / yellow / white) set in a
tall condensed face, stacked and staggered. Small die-cut icon stickers, black tape labels and a light
"talk" chip in blue type finish it. The desk whip-pans to a new area at every section change.
Timing, cut list and sound come from edit.py (same words.json, same EDL).
"""

import math
import sys

import numpy as np
import skia

import edit as E
import kit
from edit import (CUTS, DUR, END_A, FACE, H, SAMP, W, Src, apply_cam, camera, check, clamp, col, e_back, e_expo,
                  e_in, e_io, e_out, fill, font, hrand, lerp, measure, prog, spring, src_at, stroke, trim)

MAT = "#2C4C9C"
MAT_D = "#213C80"
GRIDC = "#9FB6EC"
BLUE = "#1F5BFF"
YEL = "#FFE81A"
WHITE = "#FFFFFF"
INK = "#0A0A0B"
RED = "#FF3B30"
CHIP = "#E7EAF1"
CHIPT = "#2563EB"
SILVER = "#C9CDD3"

OUT = E.OUT
FPS = E.FPS

# ================================================================== the desk (world coordinates)
SECTIONS = [0.0, E.WHY.s - 0.06, E.T_FIX, E.T_REC, E.T_FEAT, E.T_READY, E.T_NO, E.T_PROOF, E.T_IFW, E.T_GET, END_A]
STEPS = [(0, 0), (1, 0), (1, 0.6), (0, 0.6), (-1, 0.6), (-1, 1.2), (0, 1.2), (1, 1.2), (1, 1.8), (0, 1.8), (0, 2.4)]
ORIGIN = [(sx * W, sy * H) for sx, sy in STEPS]
PAN = 0.34


def section(t):
    k = max(i for i, s in enumerate(SECTIONS) if t >= s)
    return k


def cam_xy(t):
    """desk camera position (world) + pan speed (px/frame) for motion blur."""
    k = section(t)
    q = e_io(prog(t, SECTIONS[k], PAN)) if k else 1.0
    a = ORIGIN[k - 1] if k else ORIGIN[0]
    b = ORIGIN[k]
    x, y = lerp(a[0], b[0], q), lerp(a[1], b[1], q)
    q2 = e_io(prog(t + 1 / FPS, SECTIONS[k], PAN)) if k else 1.0
    vx, vy = (b[0] - a[0]) * (q2 - q), (b[1] - a[1]) * (q2 - q)
    return x, y, vx, vy


_MAT = None


def mat_tile():
    """one big tile of the cutting mat, periodic in 150 px (major grid)."""
    global _MAT
    if _MAT is None:
        tw, th = W + 150, H + 150
        surf = skia.Surface(tw, th)
        with surf as c:
            c.clear(col(MAT))
            pm = stroke(GRIDC, 1.6, 0.18)
            for x in range(0, tw + 1, 30):
                c.drawLine(x, 0, x, th, pm)
            for y in range(0, th + 1, 30):
                c.drawLine(0, y, tw, y, pm)
            pM = stroke(GRIDC, 3.0, 0.42)
            for x in range(0, tw + 1, 150):
                c.drawLine(x, 0, x, th, pM)
            for y in range(0, th + 1, 150):
                c.drawLine(0, y, tw, y, pM)
        arr = surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType).astype(np.float32)
        rng = np.random.default_rng(5)
        n = rng.standard_normal(arr.shape[:2]).astype(np.float32) * 3.5
        arr[..., :3] += n[..., None]
        _MAT = skia.Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), colorType=skia.kRGBA_8888_ColorType)
    return _MAT


def draw_mat(c, cx, cy):
    ox, oy = cx % 150, cy % 150
    c.drawImage(mat_tile(), -ox, -oy, SAMP)
    # desk light: soft hotspot behind the speaker, darker corners
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=skia.GradientShader.MakeRadial(
        (560, 700), 1300, [col("#FFFFFF", 0.12), col("#FFFFFF", 0.0), col("#0A1640", 0.35)], [0, 0.5, 1])))


def shadowed(c, draw_fn, dx=10, dy=18, blur=18, a=0.38):
    """draw something with a soft drop shadow beneath it (shadow of the whole group)."""
    p = skia.Paint(ImageFilter=skia.ImageFilters.DropShadow(dx, dy, blur, blur, col("#050A20", a)))
    c.saveLayer(None, p)
    draw_fn()
    c.restore()


# ================================================================== props (vector, lying on the mat)
def prop_laptop(c, x, y, rot, s=1.0):
    def body():
        c.save()
        c.translate(x, y)
        c.rotate(rot)
        c.scale(s, s)
        bw, bh = 1100, 760
        rr = kit.rrect(-bw / 2, -bh / 2, bw, bh, 46)
        c.drawRRect(rr, skia.Paint(Shader=skia.GradientShader.MakeLinear(
            [(-bw / 2, -bh / 2), (bw / 2, bh / 2)], [col("#E3E6EA"), col("#B9BDC4")]), AntiAlias=True))
        c.drawRRect(rr, stroke("#8E939B", 3, 0.8))
        c.drawRect(skia.Rect.MakeXYWH(-bw / 2 + 40, -bh / 2 + 6, bw - 80, 16), fill("#2A2B2E", 0.9))
        kx, ky, kw, kh = -bw / 2 + 70, -bh / 2 + 70, bw - 140, 330
        c.drawRRect(kit.rrect(kx - 12, ky - 12, kw + 24, kh + 24, 18), fill("#A9AEB5"))
        cols, rows = 14, 5
        gw, gh = kw / cols, kh / rows
        for r in range(rows):
            for q in range(cols):
                c.drawRRect(kit.rrect(kx + q * gw + 4, ky + r * gh + 4, gw - 8, gh - 8, 8), fill("#1C1C1F"))
                c.drawLine(kx + q * gw + 10, ky + r * gh + 7, kx + (q + 1) * gw - 10, ky + r * gh + 7,
                           stroke("#55565C", 2, 0.7))
        c.drawRRect(kit.rrect(-230, ky + kh + 50, 460, 230, 22), fill("#B3B7BE"))
        c.drawRRect(kit.rrect(-230, ky + kh + 50, 460, 230, 22), stroke("#9DA2A9", 2))
        c.restore()

    shadowed(c, body, 16, 26, 26, 0.45)


def prop_case(c, x, y, rot, s=1.0):
    def body():
        c.save()
        c.translate(x, y)
        c.rotate(rot)
        c.scale(s, s)
        rr = kit.rrect(-130, -110, 260, 220, 90)
        c.drawRRect(rr, skia.Paint(Shader=skia.GradientShader.MakeLinear(
            [(-130, -110), (130, 110)], [col("#FFFFFF"), col("#D9DCE2")]), AntiAlias=True))
        c.drawLine(-128, -30, 128, -30, stroke("#B8BCC4", 3))
        c.drawCircle(0, 10, 7, fill("#C8CCD3"))
        c.restore()

    shadowed(c, body, 10, 18, 16, 0.4)


def prop_watch(c, x, y, rot, s=1.0, t=0.0):
    def body():
        c.save()
        c.translate(x, y)
        c.rotate(rot)
        c.scale(s, s)
        c.drawRRect(kit.rrect(-95, -420, 190, 840, 60), fill("#18191C"))
        for i in range(-6, 7):
            if abs(i) > 2:
                c.drawCircle(0, i * 55, 9, fill("#2C2E33"))
        c.drawRRect(kit.rrect(-150, -175, 300, 350, 80), fill("#2B2D31"))
        c.drawRRect(kit.rrect(-150, -175, 300, 350, 80), stroke("#5C6068", 6))
        c.drawRRect(kit.rrect(-122, -147, 244, 294, 60), fill("#050506"))
        for i in range(12):
            th = i / 12 * 2 * math.pi
            c.drawLine(92 * math.sin(th), -92 * math.cos(th), 108 * math.sin(th), -108 * math.cos(th),
                       stroke(WHITE, 4, 0.8))
        hm = t * 0.5
        c.drawLine(0, 0, 60 * math.sin(hm * 0.08), -60 * math.cos(hm * 0.08), stroke(WHITE, 7))
        c.drawLine(0, 0, 90 * math.sin(hm), -90 * math.cos(hm), stroke(WHITE, 5))
        c.drawLine(0, 0, 96 * math.sin(t * 6.28 / 6), -96 * math.cos(t * 6.28 / 6), stroke("#FF8A00", 3))
        c.drawCircle(0, 0, 7, fill(WHITE))
        c.drawRRect(kit.rrect(146, -40, 20, 80, 8), fill("#5C6068"))
        c.restore()

    shadowed(c, body, 14, 24, 22, 0.45)


def prop_pencil(c, x, y, rot, s=1.0):
    def body():
        c.save()
        c.translate(x, y)
        c.rotate(rot)
        c.scale(s, s)
        L, R = 640, 26
        c.drawRect(skia.Rect.MakeXYWH(-L / 2, -R, L, 2 * R), fill("#FFC21A"))
        c.drawRect(skia.Rect.MakeXYWH(-L / 2, -R, L, R * 0.6), fill("#FFD95A"))
        c.drawRect(skia.Rect.MakeXYWH(-L / 2, R * 0.4, L, R * 0.6), fill("#E0A200"))
        tip = skia.Path()
        tip.moveTo(L / 2, -R)
        tip.lineTo(L / 2 + 110, 0)
        tip.lineTo(L / 2, R)
        tip.close()
        c.drawPath(tip, fill("#F2CFA0"))
        lead = skia.Path()
        lead.moveTo(L / 2 + 75, -8)
        lead.lineTo(L / 2 + 110, 0)
        lead.lineTo(L / 2 + 75, 8)
        lead.close()
        c.drawPath(lead, fill("#2A2A2A"))
        c.drawRect(skia.Rect.MakeXYWH(-L / 2 - 60, -R, 60, 2 * R), fill("#B9BEC6"))
        c.drawRRect(kit.rrect(-L / 2 - 120, -R, 70, 2 * R, 14), fill("#FF8FA3"))
        c.restore()

    shadowed(c, body, 8, 14, 10, 0.4)


def prop_phone(c, x, y, rot, s=1.0, t=0.0):
    def body():
        c.save()
        c.translate(x, y)
        c.rotate(rot)
        c.scale(s, s)
        c.drawRRect(kit.rrect(-170, -350, 340, 700, 56), fill("#111214"))
        c.drawRRect(kit.rrect(-155, -335, 310, 670, 44), fill("#F4F5F7"))
        c.drawRRect(kit.rrect(-50, -322, 100, 26, 13), fill("#111214"))
        cols = ["#FFE81A", "#1F5BFF", "#FF6B6B", "#C4C6FF", "#111214", "#9BE7C4"]
        for i in range(9):
            r, q = divmod(i, 3)
            c.drawRect(skia.Rect.MakeXYWH(-140 + q * 96, -250 + r * 96, 90, 90), fill(cols[(i * 5) % 6], 0.9))
        c.restore()

    shadowed(c, body, 12, 22, 20, 0.45)


TOOL_GLYPHS = ["move", "rect", "lasso", "crop", "brush", "stamp", "text", "pen"]


def prop_tools(c, x, y, rot, s=1.0):
    def body():
        c.save()
        c.translate(x, y)
        c.rotate(rot)
        c.scale(s, s)
        c.drawRRect(kit.rrect(-70, -480, 140, 960, 20), fill("#2A2B2F"))
        p = stroke("#E9EAEE", 4)
        for i, g in enumerate(TOOL_GLYPHS):
            cy = -420 + i * 115
            if g == "move":
                c.drawLine(-22, cy, 22, cy, p)
                c.drawLine(0, cy - 22, 0, cy + 22, p)
            elif g == "rect":
                c.drawRect(skia.Rect.MakeXYWH(-20, cy - 16, 40, 32), stroke("#E9EAEE", 4))
            elif g == "lasso":
                c.drawOval(skia.Rect.MakeXYWH(-24, cy - 16, 48, 28), stroke("#E9EAEE", 4))
            elif g == "crop":
                c.drawLine(-14, cy - 24, -14, cy + 14, p)
                c.drawLine(-24, cy + 14, 14, cy + 14, p)
                c.drawLine(14, cy + 24, 14, cy - 14, p)
            elif g == "brush":
                c.drawLine(-18, cy + 18, 16, cy - 16, stroke("#E9EAEE", 8))
            elif g == "stamp":
                c.drawRect(skia.Rect.MakeXYWH(-20, cy + 6, 40, 12), fill("#E9EAEE"))
                c.drawCircle(0, cy - 10, 12, fill("#E9EAEE"))
            elif g == "text":
                kit.text(c, "T", 0, cy + 16, "black", 46, color="#E9EAEE")
            else:
                c.drawLine(-16, cy + 20, 0, cy - 22, p)
                c.drawLine(0, cy - 22, 16, cy + 20, p)
        c.restore()

    shadowed(c, body, 10, 18, 16, 0.45)


def prop_sticky(c, x, y, rot, txt, s=1.0, color=YEL):
    def body():
        c.save()
        c.translate(x, y)
        c.rotate(rot)
        c.scale(s, s)
        c.drawRect(skia.Rect.MakeXYWH(-150, -150, 300, 300), fill(color))
        c.drawRect(skia.Rect.MakeXYWH(-150, -150, 300, 46), fill("#000000", 0.05))
        for i, line in enumerate(txt.split("\n")):
            kit.text(c, line, 0, -30 + i * 70, "caveat", 66, color=INK)
        c.restore()

    shadowed(c, body, 8, 16, 14, 0.4)


def prop_ruler(c, x, y, rot, s=1.0):
    def body():
        c.save()
        c.translate(x, y)
        c.rotate(rot)
        c.scale(s, s)
        c.drawRect(skia.Rect.MakeXYWH(-700, -60, 1400, 120), fill("#F2F4F8", 0.82))
        for i in range(0, 141):
            L = 40 if i % 10 == 0 else 26 if i % 5 == 0 else 16
            c.drawLine(-700 + i * 10, -60, -700 + i * 10, -60 + L, stroke(INK, 2, 0.7))
            if i % 10 == 0:
                kit.text(c, str(i // 10), -700 + i * 10, 2, "mono", 22, color=INK, a=0.7)
        c.restore()

    shadowed(c, body, 6, 12, 10, 0.3)


# props per section, in section-local screen coordinates (the section's origin is the screen at rest)
def props_for(k, t):
    L = []
    if k == 0:
        L += [(prop_laptop, (90, 120, 14, 0.95)), (prop_case, (1010, 150, -18, 0.95)), (prop_watch, (1010, 1700, 28, 0.85))]
    elif k == 1:
        L += [(prop_phone, (980, 260, 16, 0.9)), (prop_pencil, (120, 1720, -32, 0.9)),
              (prop_sticky, (110, 330, -9, 0.8, "post\ndaily??"))]
    elif k == 2:
        L += [(prop_tools, (30, 980, 4, 0.95)), (prop_case, (1000, 1740, 24, 0.9)), (prop_ruler, (900, 120, -12, 0.8))]
    elif k == 3:
        L += [(prop_laptop, (1060, 110, -12, 0.9)), (prop_pencil, (-40, 1550, 58, 0.9))]
    elif k == 4:
        L += [(prop_watch, (60, 260, -30, 0.8)), (prop_tools, (1060, 1100, -4, 0.9))]
    elif k == 5:
        L += [(prop_pencil, (980, 1760, -24, 0.8))]
    elif k == 6:
        L += [(prop_ruler, (540, 1780, 4, 0.95)), (prop_phone, (1040, 300, -18, 0.85))]
    elif k == 7:
        L += [(prop_case, (80, 200, 12, 0.9))]
    elif k == 8:
        L += [(prop_laptop, (60, 110, 10, 0.9)), (prop_watch, (1040, 1680, -24, 0.8))]
    elif k == 9:
        L += [(prop_laptop, (80, 110, 14, 0.9)), (prop_case, (1010, 160, -16, 0.9)), (prop_watch, (1020, 1730, 28, 0.8)),
              (prop_tools, (20, 1300, 3, 0.85))]
    elif k == 10:
        L += [(prop_laptop, (80, 100, 14, 0.9)), (prop_case, (1010, 150, -18, 0.9)), (prop_watch, (1020, 1740, 28, 0.8)),
              (prop_pencil, (130, 1760, -28, 0.85))]
    return L


def draw_desk(c, t, k_only=None):
    cx, cy, vx, vy = cam_xy(t)
    sp = math.hypot(vx, vy)
    blur = sp > 6
    if blur:
        c.saveLayer(None, skia.Paint(ImageFilter=skia.ImageFilters.Blur(min(40, abs(vx) * 0.5) + 0.01,
                                                                         min(40, abs(vy) * 0.5) + 0.01)))
    draw_mat(c, cx, cy)
    k = section(t)
    for kk in {k, max(0, k - 1)} if k_only is None else {k_only}:
        ox, oy = ORIGIN[kk][0] - cx, ORIGIN[kk][1] - cy
        if abs(ox) > W * 1.2 or abs(oy) > H * 1.2:
            continue
        for fn, args in props_for(kk, t):
            x, y, rot, s, *rest = args
            c.save()
            c.translate(ox, oy)
            if fn in (prop_watch, prop_phone):
                fn(c, x, y, rot, s, t=t)
            elif fn is prop_sticky:
                fn(c, x, y, rot, rest[0], s)
            else:
                fn(c, x, y, rot, s)
            c.restore()
    if blur:
        c.restore()
    return sp


# ================================================================== stickers & labels
def icon_sticker(c, x, y, s, k, glyph, bg=WHITE, fg=INK, rot=0.0, t=0.0):
    """die-cut rounded-square icon sticker. k = slap-in progress."""
    if k <= 0:
        return
    sc = s * (lerp(1.6, 1.0, e_out(clamp(k / 0.5))) if k < 0.5 else 1 + 0.06 * math.sin(clamp((k - 0.5) / 0.4) * math.pi))
    a = clamp(k * 4)

    def body():
        c.save()
        c.translate(x, y)
        c.rotate(rot + (1 - clamp(k * 2)) * 18)
        c.scale(sc / 100, sc / 100)
        c.drawRRect(kit.rrect(-58, -58, 116, 116, 30), fill(WHITE, a))
        c.drawRRect(kit.rrect(-50, -50, 100, 100, 24), fill(bg, a))
        glyph_draw(c, glyph, fg, a, t)
        c.restore()

    shadowed(c, body, 6, 12, 10, 0.4 * a)


def glyph_draw(c, g, fg, a, t):
    p = stroke(fg, 7, a)
    if g == "clock":
        c.drawCircle(0, 0, 32, stroke(fg, 6, a))
        an = t * 4
        c.drawLine(0, 0, 0, -22, p)
        c.drawLine(0, 0, 22 * math.sin(an), -22 * math.cos(an), stroke(fg, 5, a))
    elif g == "scissors":
        c.drawCircle(-16, 20, 11, stroke(fg, 6, a))
        c.drawCircle(16, 20, 11, stroke(fg, 6, a))
        c.drawLine(-8, 12, 20, -30, p)
        c.drawLine(8, 12, -20, -30, p)
    elif g == "aa":
        kit.text(c, "Aa", 0, 17, "black", 50, color=fg, a=a)
    elif g == "clap":
        c.drawRect(skia.Rect.MakeXYWH(-30, -6, 60, 36), fill(fg, a))
        c.save()
        c.rotate(-14)
        c.drawRect(skia.Rect.MakeXYWH(-32, -30, 64, 16), fill(fg, a))
        c.restore()
    elif g == "note":
        c.drawCircle(-14, 22, 11, fill(fg, a))
        c.drawCircle(18, 14, 11, fill(fg, a))
        c.drawLine(-4, 22, -4, -24, stroke(fg, 6, a))
        c.drawLine(28, 14, 28, -32, stroke(fg, 6, a))
        c.drawLine(-4, -24, 28, -32, stroke(fg, 9, a))
    elif g == "spark":
        path = skia.Path()
        for i in range(8):
            r = 34 if i % 2 == 0 else 11
            th = i * math.pi / 4 - math.pi / 2
            (path.moveTo if i == 0 else path.lineTo)(r * math.cos(th), r * math.sin(th))
        path.close()
        c.drawPath(path, fill(fg, a))
    elif g == "play":
        path = skia.Path()
        path.moveTo(-14, -24)
        path.lineTo(26, 0)
        path.lineTo(-14, 24)
        path.close()
        c.drawPath(path, fill(fg, a))
    elif g == "grid":
        for i in range(9):
            r, q = divmod(i, 3)
            c.drawRect(skia.Rect.MakeXYWH(-30 + q * 21, -30 + r * 21, 18, 18), fill(fg, a))
    elif g == "wide":
        c.drawRRect(kit.rrect(-34, -20, 68, 40, 8), stroke(fg, 6, a))
        kit.text(c, "16:9", 0, 8, "monob", 18, color=fg, a=a)
    elif g == "diamond":
        path = skia.Path()
        path.moveTo(0, -30)
        path.lineTo(30, 0)
        path.lineTo(0, 30)
        path.lineTo(-30, 0)
        path.close()
        c.drawPath(path, fill(fg, a))
    elif g == "bars":
        for i, (x0, w) in enumerate(((-30, 34), (-10, 40), (-26, 26))):
            c.drawRRect(kit.rrect(x0, -26 + i * 20, w, 12, 6), fill(fg, a))
    elif g == "user":
        c.drawCircle(0, -12, 14, fill(fg, a))
        c.drawRRect(kit.rrect(-26, 8, 52, 26, 13), fill(fg, a))
    elif g == "cal":
        c.drawRRect(kit.rrect(-30, -24, 60, 54, 8), stroke(fg, 6, a))
        c.drawLine(-30, -8, 30, -8, stroke(fg, 6, a))
        c.drawLine(-14, -32, -14, -18, stroke(fg, 6, a))
        c.drawLine(14, -32, 14, -18, stroke(fg, 6, a))
    elif g == "rec":
        c.drawCircle(0, 0, 22, fill(RED, a))


def tape(c, s, x, y, k, rot=-2.0, size=34, bg=INK, fg=WHITE, name="bold"):
    """black tape label like '@handle' on the reference."""
    if k <= 0:
        return
    sc = lerp(0.6, 1.0, e_back(clamp(k / 0.4)))
    a = clamp(k * 4)
    w = measure(s, name, size) + size * 1.2
    h = size * 1.55

    def body():
        c.save()
        c.translate(x, y)
        c.rotate(rot)
        c.scale(sc, sc)
        c.drawRect(skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h), fill(bg, a))
        kit.text(c, s, 0, size * 0.36, name, size, color=fg, a=a)
        c.restore()

    shadowed(c, body, 4, 8, 6, 0.35 * a)


def talk_chip(c, s, x, y, k, rot=-12.0, size=40):
    """the light 'Let's talk' chip with blue rounded type."""
    if k <= 0:
        return
    sc = lerp(0.5, 1.0, e_back(clamp(k / 0.4)))
    a = clamp(k * 4)
    w = measure(s, "montb", size) + size * 1.0
    h = size * 1.6

    def body():
        c.save()
        c.translate(x, y)
        c.rotate(rot)
        c.scale(sc, sc)
        c.drawRect(skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h), fill(CHIP, a))
        kit.text(c, s, 0, size * 0.36, "montb", size, color=CHIPT, a=a)
        c.restore()

    shadowed(c, body, 4, 10, 8, 0.3 * a)


# pixel hand cursor (1 = black outline, 2 = white)
HAND = [
    "......11.........",
    ".....1221........",
    ".....1221........",
    ".....1221........",
    ".....1221111.....",
    ".....12212211111.",
    ".....122122122121",
    "..11.122122122121",
    ".1221122222222221",
    ".1222122222222221",
    "..122222222222221",
    "..122222222222221",
    "...12222222222221",
    "...1222222222221.",
    "....122222222221.",
    "....12222222221..",
    ".....122222221...",
    ".....111111111...",
]


def hand_cursor(c, x, y, s=6.0, a=1.0):
    def body():
        for r, row in enumerate(HAND):
            for q, ch in enumerate(row):
                if ch != ".":
                    c.drawRect(skia.Rect.MakeXYWH(x + q * s - 6 * s, y + r * s, s + 0.5, s + 0.5),
                               fill(INK if ch == "1" else WHITE, a))

    shadowed(c, body, 4, 8, 6, 0.4 * a)


# ================================================================== captions as colour blocks
PAL = [(BLUE, WHITE, YEL), (YEL, INK, BLUE), (WHITE, INK, BLUE)]
ROTS = [-6.5, -2.0, 3.0, -4.0, 4.5, -3.0, 2.0]
SQ = 0.86            # horizontal squeeze of the condensed face


def ctext(c, s, x, base, size, color, a=1.0):
    c.save()
    c.translate(x, base)
    c.scale(SQ, 1)
    kit.text(c, s, 0, 0, "anton", size, color=color, a=a, anchor="l", tracking=-0.01)
    c.restore()


def cwidth(s, size):
    return measure(s, "anton", size, -0.01) * SQ


def split_lines(g):
    if len(g) <= 2 and sum(len(w["d"]) for w in g) <= 12:
        return [g]
    if len(g) == 1:
        return [g]
    best, bm = None, 1e9
    for k in range(1, len(g)):
        a, b = g[:k], g[k:]
        m = max(sum(len(w["d"]) + 1 for w in a), sum(len(w["d"]) + 1 for w in b))
        if m < bm:
            best, bm = [a, b], m
    return best


LINES = [split_lines(g) for g in E.GROUPS]


def word_s(w):
    return w["d"].strip(",.?").upper()


def block_caps(c, t, ybot=525, scale=1.0):
    k = E.cur_group(t)
    if k is None:
        return
    lines = LINES[k]
    size = 150 * scale
    gap = 0.2 * size
    capH = font("anton", size).getMetrics().fCapHeight
    padx, pady = 0.2 * size, 0.16 * size
    bh = capH + 2 * pady
    # fit width
    widths = [sum(cwidth(word_s(w), size) for w in ln) + gap * (len(ln) - 1) for ln in lines]
    fit = min(1.0, 860 / (max(widths) + 2 * padx))
    n = len(lines)
    for li, ln in enumerate(lines):
        pal = PAL[(k + li) % 3]
        rot = ROTS[(k * 2 + li) % len(ROTS)]
        t0 = ln[0]["os"] - 0.06
        kk = prog(t, t0, 0.42)
        if kk <= 0:
            continue
        sz = size * fit
        g_ = gap * fit
        # width grows with the revealed words
        shown = [w for w in ln if t >= w["os"] - 0.06]
        full_w = sum(cwidth(word_s(w), sz) for w in ln) + g_ * (len(ln) - 1)
        cur_w = sum(cwidth(word_s(w), sz) for w in shown) + g_ * (len(shown) - 1)
        last = shown[-1]
        grow = e_out(prog(t, last["os"] - 0.06, 0.16))
        prev_w = cur_w - cwidth(word_s(last), sz) - (g_ if len(shown) > 1 else 0)
        wnow = lerp(prev_w, cur_w, grow) if len(shown) > 1 else cur_w
        bw = wnow + 2 * padx * fit
        bhh = bh * fit
        cy = ybot - (n - 1 - li) * bhh * 0.98 - bhh / 2
        cx = 540 + (li - (n - 1) / 2) * 110 * (1 if k % 2 == 0 else -1)
        x0 = cx - (full_w + 2 * padx * fit) / 2
        slap = spring(kk * 0.42, w=20, z=0.42)
        sc = lerp(1.35, 1.0, clamp(slap))

        def body(x0=x0, cy=cy, bw=bw, bhh=bhh, pal=pal, ln=ln, sz=sz, g_=g_, rot=rot, sc=sc, cx=cx):
            c.save()
            c.translate(cx, cy)
            c.rotate(rot + (1 - clamp(kk * 2.2)) * 7)
            c.scale(sc, sc)
            c.translate(-cx, -cy)
            c.drawRect(skia.Rect.MakeXYWH(x0, cy - bhh / 2, bw, bhh), fill(pal[0]))
            x = x0 + padx * fit
            base = cy + capH * fit / 2
            for w in ln:
                if t < w["os"] - 0.06:
                    break
                st = E.STYLE.get(w["i"])
                colr = pal[2] if st in ("hot", "lime", "serif") else pal[1]
                wk = e_out(prog(t, w["os"] - 0.06, 0.14))
                ww = cwidth(word_s(w), sz)
                c.save()
                c.translate(x + ww / 2, base)
                c.scale(lerp(0.6, 1, wk), lerp(0.6, 1, wk))
                ctext(c, word_s(w), -ww / 2, 0, sz, colr, a=wk)
                c.restore()
                if st == "strike":
                    sk = e_out(prog(t, w["oe"] - 0.02, 0.2))
                    if sk > 0:
                        p = trim(stroke(RED, sz * 0.12), sk)
                        path = skia.Path()
                        y = base - capH * fit * 0.45
                        path.moveTo(x - 10, y + 8)
                        path.quadTo(x + ww / 2, y - 12, x + ww + 10, y - 2)
                        c.drawPath(path, p)
                x += ww + g_
            c.restore()

        shadowed(c, body, 10, 16, 14, 0.42)


def tagline(c, s, x, y, k, size=40):
    if k <= 0:
        return
    kit.text(c, s, x, y + (1 - e_out(k)) * 20, "medium", size, color=WHITE, a=clamp(k), shadow=10)


# ================================================================== section graphics
def g_hook(c, t):
    if t < E.T_FIX:
        tape(c, "THE PROBLEM", 250, 1575, e_out(prog(t, 0.2, 0.4)), rot=-2, size=30)
    a0 = E.LOSING.w(4) - 0.1
    if a0 <= t < E.WHY.s:
        k = prog(t, a0, 0.5)
        icon_sticker(c, 870, 780, 170, k, "clock", bg="#FF8A00", fg=WHITE, rot=10, t=t * 3)
        secs = 3 * 3600 * e_io(prog(t, E.LOSING.w(4), E.LOSING.e - E.LOSING.w(4) + 0.2))
        hh, mm, ss = int(secs // 3600), int(secs % 3600 // 60), int(secs % 60)
        tape(c, f"{hh:02d}:{mm:02d}:{ss:02d}", 860, 920, prog(t, a0 + 0.1, 0.4), rot=4, size=36, name="monob")


def g_week(c, t, mode):
    a0, a1 = (E.WHY.s - 0.06, E.T_FIX) if mode == "twice" else (E.T_IFW, E.T_GET)
    if not (a0 <= t < a1):
        return
    k = e_back(prog(t, a0 + 0.15, 0.4))
    out = e_in(prog(t, a1 - 0.18, 0.18))
    cw, gap = 104, 12
    tw = 7 * cw + 6 * gap + 60
    x0, y0 = 540 - tw / 2, 1180

    def body():
        c.save()
        c.translate(540, y0 + 110 + out * 400)
        c.rotate(-2.5)
        c.scale(k, k)
        c.translate(-540, -(y0 + 110))
        c.drawRect(skia.Rect.MakeXYWH(x0, y0, tw, 220), fill(WHITE))
        kit.text(c, "THIS WEEK", x0 + 30, y0 + 50, "bold", 28, color=INK, anchor="l")
        for i in range(7):
            x = x0 + 30 + i * (cw + gap)
            if mode == "twice":
                on = i in (1, 4) and t >= E.WHY.w(5)
                miss = i not in (1, 4) and t >= E.WHY.w(8)
            else:
                on = t >= E.IFW.w(5) + 0.07 * i
                miss = False
            rr = kit.rrect(x, y0 + 75, cw, 120, 12)
            c.drawRRect(rr, fill(BLUE if on else "#EEF1F7"))
            kit.text(c, "MTWTFSS"[i], x + cw / 2, y0 + 120, "black", 34, color=WHITE if on else INK, a=1 if on else 0.5)
            if on:
                check(c, x + cw / 2, y0 + 160, 20, YEL, 1)
            if miss:
                mk = e_out(prog(t, E.WHY.w(8) + 0.05 * i, 0.2))
                c.drawLine(x + 28, y0 + 140, x + 28 + 48 * mk, y0 + 140 + 40 * mk, stroke(RED, 8))
                c.drawLine(x + 76, y0 + 140, x + 76 - 48 * mk, y0 + 140 + 40 * mk, stroke(RED, 8))
        lab = "2 / 7 DAYS" if mode == "twice" else "7 / 7 DAYS"
        if (mode == "twice" and t >= E.WHY.w(5) + 0.2) or (mode != "twice" and t >= E.IFW.w(5) + 0.5):
            kit.text(c, lab, x0 + tw - 30, y0 + 50, "bold", 28, color=RED if mode == "twice" else BLUE, anchor="r")
        c.restore()

    shadowed(c, body, 10, 18, 16, 0.4)
    if mode == "twice":
        icon_sticker(c, 165, 1170, 120, prog(t, a0 + 0.3, 0.45), "cal", bg=YEL, fg=INK, rot=-12)


def g_fix(c, t, part):
    a0 = E.T_FIX
    if not (a0 <= t < E.T_REC):
        return
    if part == "logo":
        if t >= E.CALLED.s - 0.1:
            logo_blocks(c, t, E.CALLED.w(3) - 0.08, E.CALLED.w(4) - 0.08, ybot=545)
        return
    # the toggle: OFF -> ON on "fix"
    k = e_back(prog(t, a0 + 0.05, 0.4))
    on = e_io(prog(t, E.FIX.w(4), 0.25))

    def body():
        c.save()
        c.translate(890, 900)
        c.rotate(-8)
        c.scale(k, k)
        c.drawRRect(kit.rrect(-150, -78, 300, 156, 78), fill(WHITE))
        c.drawRRect(kit.rrect(-136, -64, 272, 128, 64), fill(kit.mixc("#E3E6EC", BLUE, on) if hasattr(kit, "mixc") else BLUE))
        kx = lerp(-72, 72, on)
        c.drawCircle(kx, 0, 56, fill("#000000", 0.18, blur=8))
        c.drawCircle(kx, 0, 54, skia.Paint(Shader=skia.GradientShader.MakeRadial((kx - 14, -16), 70,
                                                                                [col("#FFFFFF"), col("#D6D9DF")]),
                                           AntiAlias=True))
        c.restore()

    shadowed(c, body, 8, 16, 14, 0.4)
    talk_chip(c, "the fix ↓", 880, 760, prog(t, E.FIX.w(4) + 0.05, 0.4), rot=-12, size=40)
    tape(c, "THE FIX", 250, 1575, e_out(prog(t, a0 + 0.1, 0.4)), rot=-3, size=30)


def logo_blocks(c, t, t1, t2, ybot=600, small=None, scale=1.0):
    """VIBE / EDITING as two slapped blocks, like YOUR BRAND / DESERVES on the reference."""
    items = [("VIBE", YEL, INK, -6.0, t1, -70, 205), ("EDITING", BLUE, WHITE, 3.0, t2, 70, 165)]
    if small:
        items.append(small)
    for i, (s, bg, fg, rot, t0, dx, size) in enumerate(items):
        size *= scale
        kk = prog(t, t0, 0.45)
        if kk <= 0:
            continue
        capH = font("anton", size).getMetrics().fCapHeight
        w = cwidth(s, size)
        bw, bh = w + 0.4 * size, capH + 0.32 * size
        cy = ybot - (len(items) - 1 - i) * bh * 0.95 - bh / 2
        cx = 540 + dx
        sl = spring(kk * 0.45, w=20, z=0.42)
        sc = lerp(1.5, 1.0, clamp(sl))

        def body(s=s, bg=bg, fg=fg, rot=rot, cx=cx, cy=cy, bw=bw, bh=bh, w=w, size=size, capH=capH, sc=sc, kk=kk):
            c.save()
            c.translate(cx, cy)
            c.rotate(rot + (1 - clamp(kk * 2)) * 10)
            c.scale(sc, sc)
            c.drawRect(skia.Rect.MakeXYWH(-bw / 2, -bh / 2, bw, bh), fill(bg))
            ctext(c, s, -w / 2, capH / 2, size, fg)
            c.restore()

        shadowed(c, body, 12, 20, 16, 0.45)


INSTR = [(E.CUTP, "cut the pauses", "scissors", BLUE), (E.PUNCHY, "punchy captions", "aa", YEL),
         (E.CINE, "cinematic look", "clap", INK), (E.ADDM, "add music", "note", "#FF6B6B")]


def g_how(c, t):
    if not (E.T_REC <= t < E.T_FEAT):
        return
    tape(c, "HOW IT WORKS", 250, 1575, e_out(prog(t, E.T_REC + 0.1, 0.4)), rot=-3, size=30)
    # REC sticker
    if t < E.TELL.s + 0.3:
        icon_sticker(c, 860, 800, 150, prog(t, E.REC.s, 0.45), "rec", bg=WHITE, fg=RED, rot=8)
        tape(c, "REC  00:00:%02d" % int((t - E.REC.s) * 30 % 60), 860, 920, prog(t, E.REC.s + 0.1, 0.4), rot=3,
             size=30, name="monob")
    # spoken directions stack up as chips with icon stickers
    for j, (ph, txt, gly, bgc) in enumerate(INSTR):
        k = prog(t, ph.s - 0.05, 0.45)
        if k <= 0:
            continue
        y = 1130 + j * 118
        x = 540 + (-1) ** j * 40
        rot = [-4, 3, -3, 4][j]
        talk_chip(c, txt, x + 40, y, k, rot=rot, size=48)
        fg = INK if bgc == YEL else WHITE
        icon_sticker(c, x - measure(txt, "montb", 48) / 2 - 40, y - 4, 110, prog(t, ph.s, 0.45), gly, bg=bgc, fg=fg,
                     rot=-rot * 2, t=t)
        if t >= ph.e + 0.05:
            dk = e_back(prog(t, ph.e + 0.05, 0.3))
            cxk = x + 40 + measure(txt, "montb", 48) / 2 + 60
            c.save()
            c.translate(cxk, y)
            c.scale(dk, dk)
            c.drawCircle(0, 0, 30, fill(WHITE))
            c.drawCircle(0, 0, 25, fill(BLUE))
            check(c, 0, 2, 14, WHITE, 1)
            c.restore()
    # render progress tape on "edits the whole thing"
    if t >= E.EDITS.s - 0.05:
        pk = e_io(prog(t, E.EDITS.s, E.EDITS.e - E.EDITS.s))
        k = e_out(prog(t, E.EDITS.s - 0.05, 0.3))
        y = 1620
        c.drawRect(skia.Rect.MakeXYWH(170, y - 22, 740, 44), fill(INK, 0.9 * k))
        c.drawRect(skia.Rect.MakeXYWH(176, y - 16, 728 * pk, 32), fill(YEL, k))
        kit.text(c, ("EDITING… %d%%" % int(pk * 100)) if pk < 1 else "DONE ✓", 540, y + 11, "monob", 26,
                 color=INK if pk > 0.55 else WHITE, a=k)


def letterbox(c, t):
    a0, a1 = E.CINE.w(1) - 0.05, E.T_DROP + 0.25
    if not (a0 <= t < a1):
        return
    k = e_expo(prog(t, a0, 0.35)) * (1 - e_in(prog(t, a1 - 0.2, 0.2)))
    bh = 150 * k
    c.drawRect(skia.Rect.MakeXYWH(0, 0, W, bh), fill("#000000"))
    c.drawRect(skia.Rect.MakeXYWH(0, H - bh, W, bh), fill("#000000"))


def beat_rings(c, t):
    if not (E.T_DROP <= t < E.T_FEAT):
        return
    ph = ((t - E.T_DROP) % E.BEAT) / E.BEAT
    c.drawCircle(540, 760, 430 + 140 * ph, stroke(YEL, 10 * (1 - ph), 0.8 * (1 - ph)))
    c.drawCircle(540, 760, 380 + 90 * ph, stroke(WHITE, 4 * (1 - ph), 0.5 * (1 - ph)))


FEAT_ICONS = [("scissors", BLUE, WHITE, 180, 760, -10), ("aa", YEL, INK, 900, 700, 9), ("spark", WHITE, BLUE, 160, 1080, 7),
              ("note", "#FF6B6B", WHITE, 920, 1060, -8)]


def g_feat(c, t):
    if not (E.T_FEAT <= t < E.T_READY):
        return
    tape(c, "WHAT YOU GET", 250, 1575, e_out(prog(t, E.T_FEAT + 0.1, 0.4)), rot=-3, size=30)
    for j, (gl, bg, fg, x, y, rot) in enumerate(FEAT_ICONS):
        icon_sticker(c, x, y, 150, prog(t, E.FEAT.w(j) - 0.03, 0.45), gl, bg=bg, fg=fg, rot=rot, t=t)


def ready_scene(c, t, src_ts):
    """prints of the same edit in three formats, slapped onto the mat."""
    src = Src(src_ts)
    img = src.bg()
    cards = [(E.READY.w(2) - 0.06, 300, 760, 440, 782, -7, "REELS 9:16", "play", BLUE),
             (E.READY.w(3) - 0.06, 760, 830, 470, 588, 5, "FEED 4:5", "grid", YEL),
             (E.READY.w(5) - 0.06, 540, 1300, 760, 428, -3, "YOUTUBE 16:9", "wide", WHITE)]
    for t0, x, y, w, h, rot, lab, gl, bgc in cards:
        k = prog(t, t0, 0.45)
        if k <= 0:
            continue
        sl = spring(k * 0.45, w=18, z=0.45)
        sc = lerp(1.4, 1.0, clamp(sl))

        def body(x=x, y=y, w=w, h=h, rot=rot, sc=sc, k=k):
            c.save()
            c.translate(x, y)
            c.rotate(rot + (1 - clamp(k * 2)) * 12)
            c.scale(sc, sc)
            c.drawRect(skia.Rect.MakeXYWH(-w / 2 - 16, -h / 2 - 16, w + 32, h + 32), fill(WHITE))
            c.save()
            c.clipRect(skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h))
            s = max(w / W, h / H) * (1.0 if h > w else 1.3)
            hy = h / 2 / s
            fy = clamp(FACE[1] + 40, hy, H - hy)
            c.scale(s, s)
            c.translate(-540, -fy)
            c.drawImage(img, 0, 0, SAMP)
            c.restore()
            c.restore()

        shadowed(c, body, 12, 22, 18, 0.45)
        tape(c, lab, x, y + h / 2 + 36, prog(t, t0 + 0.12, 0.4), rot=rot * 0.6, size=30)
        fg = INK if bgc in (YEL, WHITE) else WHITE
        icon_sticker(c, x + w / 2 - 10, y - h / 2 + 10, 110, prog(t, t0 + 0.08, 0.45), gl, bg=bgc, fg=fg, rot=12, t=t)


NO_ICONS = [("bars", 190, 820, -9), ("diamond", 890, 800, 10), ("user", 200, 1150, 6)]


def g_no(c, t):
    if not (E.T_NO <= t < E.T_PROOF):
        return
    tape(c, "WHAT YOU DON'T NEED", 250, 1575, e_out(prog(t, E.T_NO + 0.1, 0.4)), rot=-3, size=30)
    for j, (gl, x, y, rot) in enumerate(NO_ICONS):
        k = prog(t, E.NO.w(2 * j) - 0.03, 0.45)
        icon_sticker(c, x, y, 140, k, gl, bg=WHITE, fg=INK, rot=rot, t=t)
        sk = e_out(prog(t, E.NO.we(2 * j + 1), 0.2))
        if sk > 0:
            c.drawLine(x - 60, y - 60, x - 60 + 120 * sk, y - 60 + 120 * sk, stroke(RED, 14))
            c.drawLine(x + 60, y - 60, x + 60 - 120 * sk, y - 60 + 120 * sk, stroke(RED, 14))


def g_get(c, t):
    if t < E.T_GET:
        return
    tape(c, "YOUR MOVE", 250, 1575, e_out(prog(t, E.T_GET + 0.1, 0.4)), rot=-3, size=30)
    logo_blocks(c, t, E.GET.w(2) - 0.08, E.GET.w(3) - 0.08, ybot=800,
                small=("SYSTEM", WHITE, INK, 2.0, E.GET.w(4) - 0.08, -20, 130))


def g_tap(c, t):
    a0 = E.TAP.s - 0.12
    if t < a0:
        return
    k = prog(t, a0, 0.45)
    press = 1 - 0.1 * math.sin(math.pi * prog(t, E.TAP.w(1) - 0.02, 0.22))
    talk_chip(c, "Learn more →", 560, 1470, k * press, rot=-8, size=64)
    hk = e_out(prog(t, a0 + 0.1, 0.35))
    hx = lerp(1000, 720, hk)
    hy = lerp(1800, 1480, hk) + 10 * math.sin(math.pi * prog(t, E.TAP.w(1) - 0.02, 0.22))
    if hk > 0:
        hand_cursor(c, hx, hy, 7.0, clamp(hk * 3))
    for t0 in (E.TAP.s, E.TAP.w(1)):
        rk = prog(t, t0, 0.45)
        if 0 < rk < 1:
            c.drawCircle(700, 1480, 30 + 140 * e_out(rk), stroke(WHITE, 8 * (1 - rk), 0.9 * (1 - rk)))


def end_card(c, t):
    a0 = END_A
    draw_desk(c, t)
    logo_blocks(c, t, a0 + 0.05, a0 + 0.2, ybot=1040,
                small=("SYSTEM", WHITE, INK, 2.0, a0 + 0.35, -20, 160), scale=1.25)
    tagline(c, "less editing. more posting.", 540, 1150, prog(t, a0 + 0.6, 0.5), size=50)
    talk_chip(c, "Tap Learn more →", 600, 1340, prog(t, a0 + 0.8, 0.45), rot=-8, size=56)
    icon_sticker(c, 230, 1340, 150, prog(t, a0 + 0.95, 0.45), "play", bg=BLUE, fg=WHITE, rot=-12)
    icon_sticker(c, 900, 470, 140, prog(t, a0 + 1.05, 0.45), "spark", bg=YEL, fg=INK, rot=10, t=t)
    hk = e_out(prog(t, a0 + 1.2, 0.4))
    if hk > 0:
        hand_cursor(c, lerp(1000, 830, hk), lerp(1720, 1380, hk), 7.0, hk)


# ================================================================== the speaker as a die-cut sticker
TILT = [0.0, -1.2, 1.0, -0.8, 1.4, 0.0, -1.0, 0.0, 1.0, -0.6, 0.0]


def sticker_person(c, t, src, cam):
    k = section(t)
    tilt = TILT[k]
    if k:
        q = spring(clamp(t - SECTIONS[k], 0, 0.6), w=16, z=0.4)
        tilt = lerp(TILT[k - 1], TILT[k], q)
    c.save()
    c.translate(FACE[0], FACE[1] + 300)
    c.rotate(tilt)
    c.translate(-FACE[0], -(FACE[1] + 300))
    zo = e_io(prog(t, E.T_GET, 0.45))          # step back for the offer lockup
    if zo > 0:
        z = lerp(1.0, 0.8, zo)
        c.translate(540, 1960)
        c.scale(z, z)
        c.translate(-540, -1960)
    apply_cam(c, cam)
    out = src.outline(13)
    shadow = skia.Paint(ImageFilter=skia.ImageFilters.DropShadowOnly(10, 26, 22, 22, col("#050A20", 0.5)))
    c.drawImage(out, 0, 0, SAMP, shadow)
    c.drawImage(out, 0, 0, SAMP)
    c.drawImage(src.person(), 0, 0, SAMP)
    c.restore()


def proof(c, t, src_ts, src, cam):
    """'recorded on my phone': the raw frame as a print on top of the sticker; it flies off on 'edited'."""
    if not (E.T_PROOF <= t < E.T_IFW):
        return False
    raw = Src(src_ts, "raw")
    fly = e_in(prog(t, E.EDBY.s - 0.05, 0.45))
    k = e_back(prog(t, E.T_PROOF + 0.05, 0.4))
    if fly < 1:
        def body():
            c.save()
            c.translate(540 + fly * 900, 900 - fly * 700)
            c.rotate(-3 + fly * 40)
            sc = 0.8 * k
            c.scale(sc, sc)
            c.drawRect(skia.Rect.MakeXYWH(-W / 2 - 30, -H / 2 - 30, W + 60, H + 60), fill(WHITE))
            c.translate(-W / 2, -H / 2)
            c.drawImage(raw.bg(), 0, 0, SAMP)
            c.restore()

        shadowed(c, body, 14, 26, 24, 0.5)
        tape(c, "RAW · STRAIGHT FROM MY PHONE", 540 + fly * 900, 1700 - fly * 700, prog(t, E.T_PROOF + 0.2, 0.4),
             rot=-3, size=32)
    if t >= E.EDBY.s:
        talk_chip(c, "edited by the system", 560, 1500, prog(t, E.EDBY.s + 0.2, 0.4), rot=-8, size=50)
        icon_sticker(c, 860, 760, 150, prog(t, E.EDBY.s + 0.1, 0.45), "spark", bg=YEL, fg=INK, rot=10, t=t)
    return True


# ================================================================== frame
def draw(c, t, f):
    g = {}
    src_ts = src_at(t)
    if t >= END_A:
        end_card(c, t)
        return g
    sp = draw_desk(c, t)
    if E.T_READY <= t < E.T_NO:
        ready_scene(c, t, src_ts)
        block_caps(c, t, ybot=430, scale=0.8)
        return g
    src = Src(src_ts, "cine" if E.CINE.w(1) <= t < E.T_DROP else "warm")
    cam = camera(t)
    beat_rings(c, t)
    # behind the speaker
    if not (E.CALLED.s - 0.1 <= t < E.T_REC + 0.05) and t < E.T_GET:
        block_caps(c, t, ybot=525)
    g_fix(c, t, "logo")
    g_get(c, t)
    sticker_person(c, t, src, cam)
    g_fix(c, t, "toggle")
    # in front
    g_hook(c, t)
    g_week(c, t, "twice")
    g_week(c, t, "daily")
    g_how(c, t)
    g_feat(c, t)
    g_no(c, t)
    proof(c, t, src_ts, src, cam)
    g_tap(c, t)
    letterbox(c, t)
    if E.T_DROP <= t < E.T_DROP + 0.08:
        g["flash"] = 0.5 * (1 - (t - E.T_DROP) / 0.08)
    if t < 0.1:
        g["flash"] = 1 - t / 0.1
    return g


def post(rgb, g, f):
    out = rgb.astype(np.float32)
    if g.get("flash"):
        out = out + (255 - out) * g["flash"]
    h, w = rgb.shape[:2]
    global _VIG
    if _VIG is None or _VIG.shape[0] != h:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        _VIG = (1 - 0.18 * np.clip(r - 0.65, 0, None) ** 1.6)[..., None].astype(np.float32)
    out *= _VIG
    return kit.grain(np.clip(out, 0, 255).astype(np.uint8), f, amt=0.02)


_VIG = None
FILM = kit.Film(draw, DUR, FPS, post=post, out_dir=OUT)


# ================================================================== audio: same mix + sticker slaps
def build_audio():
    m = E.build_audio()
    for k, g in enumerate(E.GROUPS):
        for li, ln in enumerate(LINES[k]):
            m.sfx("pop", ln[0]["os"] - 0.05, -13, pan=(hrand("bp", k, li) - 0.5) * 0.6)
    for s in SECTIONS[1:]:
        m.sfx("whoosh", s - 0.12, -11)
    return m


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "stills":
        FILM.stills([float(x) for x in sys.argv[2:]])
    elif cmd == "sheet":
        FILM.sheet([round(DUR * (i + 0.5) / 48, 2) for i in range(48)], cols=8, name="sheet_blueprint.png")
    elif cmd == "render":
        pic = FILM.render(OUT / "picture_blueprint.mp4")
        m = build_audio()
        m.finish(pic, OUT / "vibe_edit_time_blueprint.mp4", E.HERE / "work" / "bp")


if __name__ == "__main__":
    main()
