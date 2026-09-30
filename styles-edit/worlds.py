"""The two built worlds: a glossy 3D-cartoon landscape and an 8-bit side-scrolling platformer.
Both are drawn behind the matte, so he stands inside them."""

import math
from functools import lru_cache

import cv2
import numpy as np
import skia

W, H = 1920, 1080


def c4(rgb, a=1.0):
    return skia.Color4f(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, max(0.0, min(1.0, a)))


def cint(rgb, a=1.0):
    return c4(rgb, a).toColor()


def mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


# ================================================================== 3D cartoon world
def sphere(c, x, y, r, base, a=1.0, light=(-0.38, -0.42), shade=0.55):
    hi = mix(base, (255, 255, 255), 0.55)
    lo = mix(base, (20, 30, 60), shade)
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeRadial(skia.Point(x + light[0] * r, y + light[1] * r), r * 1.45,
                                               [cint(hi, a), cint(base, a), cint(lo, a)], [0.0, 0.45, 1.0]))
    c.drawCircle(x, y, r, p)
    sp = skia.Paint(AntiAlias=True, Color4f=c4((255, 255, 255), 0.55 * a))
    sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, max(1.0, r * 0.08)))
    c.drawOval(skia.Rect.MakeXYWH(x - r * 0.52, y - r * 0.62, r * 0.42, r * 0.26), sp)


def cloud(c, x, y, s, a=1.0):
    sh = skia.Paint(AntiAlias=True, Color4f=c4((90, 140, 200), 0.18 * a))
    sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 18 * s))
    c.drawOval(skia.Rect.MakeXYWH(x - 150 * s, y + 30 * s, 300 * s, 50 * s), sh)
    for dx, dy, r in ((-95, 10, 55), (-40, -25, 75), (35, -35, 85), (100, 5, 60), (0, 20, 70)):
        sphere(c, x + dx * s, y + dy * s, r * s, (245, 250, 255), a, shade=0.25)


def hill_path(y0, amp, period, phase, x0=-200, x1=W + 200):
    p = skia.Path()
    p.moveTo(x0, H + 50)
    xs = np.linspace(x0, x1, 60)
    for i, x in enumerate(xs):
        y = y0 - amp * (0.6 * math.sin(x / period + phase) + 0.4 * math.sin(x / (period * 0.53) + phase * 1.7))
        p.lineTo(x, y)
    p.lineTo(x1, H + 50)
    p.close()
    return p


def fill_hill(c, path, top, bottom, y0, y1, blur=0.0, rim=True):
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeLinear([skia.Point(0, y0), skia.Point(0, y1)], [cint(top), cint(bottom)]))
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    c.drawPath(path, p)
    if rim:
        r = skia.Paint(AntiAlias=True, Color4f=c4(mix(top, (255, 255, 230), 0.5), 0.6), Style=skia.Paint.kStroke_Style, StrokeWidth=6)
        r.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 4 + blur))
        c.drawPath(path, r)


@lru_cache(None)
def toon_static():
    """Sky, sun and far hills (never move)."""
    arr = np.zeros((H, W, 4), np.uint8)
    s = skia.Surface(arr)
    c = s.getCanvas()
    sky = skia.Paint()
    sky.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, 700)],
                                                 [cint((74, 160, 255)), cint((150, 210, 255)), cint((214, 240, 255))], [0, 0.6, 1]))
    c.drawRect(skia.Rect(0, 0, W, H), sky)
    glow = skia.Paint(AntiAlias=True)
    glow.setShader(skia.GradientShader.MakeRadial(skia.Point(1640, 170), 420,
                                                  [cint((255, 250, 210), 0.9), cint((255, 240, 180), 0.0)]))
    c.drawCircle(1640, 170, 420, glow)
    sphere(c, 1640, 170, 95, (255, 226, 110), shade=0.15)
    fill_hill(c, hill_path(640, 60, 260, 0.4), (150, 205, 170), (110, 170, 150), 520, 760, blur=3, rim=False)
    fill_hill(c, hill_path(700, 70, 200, 2.1), (120, 215, 110), (70, 170, 90), 600, 820, blur=1.5)
    return arr


def tree(c, x, y, s, sway, a=1.0):
    trunk = skia.Paint(AntiAlias=True)
    trunk.setShader(skia.GradientShader.MakeLinear([skia.Point(x - 18 * s, 0), skia.Point(x + 18 * s, 0)],
                                                   [cint((170, 110, 60)), cint((120, 70, 40))]))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x - 16 * s, y - 120 * s, 32 * s, 130 * s), 12 * s, 12 * s), trunk)
    c.save()
    c.rotate(sway, x, y - 110 * s)
    for dx, dy, r, colr in ((-55, -150, 70, (70, 175, 80)), (55, -155, 72, (70, 175, 80)), (0, -215, 88, (90, 200, 95)),
                            (-10, -150, 75, (85, 195, 90))):
        sphere(c, x + dx * s, y + dy * s, r * s, colr, a)
    c.restore()


def balloon(c, x, y, r, colr, t, i):
    sw = 10 * math.sin(t * 1.3 + i)
    str_ = skia.Paint(AntiAlias=True, Color4f=c4((255, 255, 255), 0.7), Style=skia.Paint.kStroke_Style, StrokeWidth=2)
    path = skia.Path()
    path.moveTo(x, y + r)
    path.cubicTo(x + sw, y + r + 60, x - sw, y + r + 110, x + sw * 0.5, y + r + 170)
    c.drawPath(path, str_)
    c.save()
    c.scale(1, 1.18)
    sphere(c, x, (y) / 1.18, r, colr, shade=0.45)
    c.restore()
    k = skia.Path()
    k.addPoly([skia.Point(x - 8, y + r + 4), skia.Point(x + 8, y + r + 4), skia.Point(x, y + r - 6)], True)
    c.drawPath(k, skia.Paint(AntiAlias=True, Color4f=c4(mix(colr, (0, 0, 0), 0.25))))


def toon_world(t, lt, enter):
    """Full 3D-cartoon background (RGB float) + a foreground layer (RGBA) that sits in front of him."""
    bg = toon_static().copy()
    s = skia.Surface(bg)
    c = s.getCanvas()
    for i, (x0, y, sc, sp) in enumerate(((200, 150, 0.9, 18), (900, 90, 0.7, 12), (1350, 260, 0.6, 24), (-300, 300, 0.8, 20))):
        x = (x0 + sp * t) % (W + 600) - 300
        cloud(c, x, y, sc)
    # mid hills with trees
    mid = hill_path(820, 45, 230, 3.7)
    fill_hill(c, mid, (140, 230, 100), (80, 185, 80), 740, 1000)
    for x, y, sc, ph in ((170, 860, 1.25, 0.0), (430, 800, 0.8, 1.3), (1560, 830, 1.1, 2.1), (1800, 800, 0.8, 0.7)):
        tree(c, x, y, sc, 3.0 * math.sin(t * 1.7 + ph))
    # balloons rising behind him
    cols = [(255, 80, 90), (255, 200, 60), (80, 170, 255), (255, 120, 200), (130, 220, 120)]
    for i in range(5):
        bx = [330, 620, 1320, 1600, 1100][i]
        by = 1000 - ((t * 60 + i * 230) % 1300)
        balloon(c, bx + 18 * math.sin(t + i), by, 42, cols[i], t, i)
    # front grass + bushes (drawn later, in front of him)
    fg = np.zeros((H, W, 4), np.uint8)
    fs = skia.Surface(fg)
    f = fs.getCanvas()
    grass = hill_path(1040, 18, 160, 1.0)
    fill_hill(f, grass, (120, 220, 90), (60, 160, 70), 1000, 1080)
    for x, y, r in ((60, 1010, 110), (190, 1050, 90), (1760, 1020, 120), (1880, 980, 90), (1640, 1070, 80)):
        sphere(f, x, y, r, (70, 180, 80))
    for x, y, colr in ((250, 990, (255, 90, 120)), (1690, 975, (255, 210, 60)), (120, 950, (255, 255, 255))):
        for k in range(5):
            a = k * 2 * math.pi / 5 + t * 0.6
            sphere(f, x + 14 * math.cos(a), y + 14 * math.sin(a), 11, colr, shade=0.3)
        sphere(f, x, y, 8, (255, 220, 80), shade=0.2)
    return bg[..., :3].astype(np.float32), fg


def pixar_person(img, al):
    """Smooth, saturated, softly lit 'animated movie' look for him."""
    small = cv2.resize(np.clip(img, 0, 255).astype(np.uint8), (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    for _ in range(3):
        small = cv2.bilateralFilter(small, 9, 38, 9)
    sm = cv2.resize(small, (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32)
    out = sm * 0.72 + img * 0.28
    g = out.mean(2, keepdims=True)
    out = g + (out - g) * 1.32
    out = out * np.array([1.05, 1.02, 0.97], np.float32) + 6
    rim = np.clip(al - cv2.GaussianBlur(np.roll(al, 10, axis=1), (0, 0), 4), 0, 1)[..., None]
    rim2 = np.clip(al - cv2.GaussianBlur(np.roll(al, -10, axis=1), (0, 0), 4), 0, 1)[..., None]
    return out + rim * np.array([255, 220, 150], np.float32) * 0.55 + rim2 * np.array([140, 200, 255], np.float32) * 0.5


def text_path(txt, font, x, y):
    glyphs = font.textToGlyphs(txt)
    xs = font.getXPos(glyphs)
    path = skia.Path()
    for g, gx in zip(glyphs, xs):
        gp = font.getPath(g)
        if gp is not None:
            gp.offset(x + gx, y)
            path.addPath(gp)
    return path


def text3d(c, txt, x, y, font, face, side=None, depth=14, a=1.0, align="c", outline=(255, 255, 255)):
    """Chunky extruded 'balloon' lettering with a glossy face."""
    w = font.measureText(txt)
    x0 = x - w / 2 if align == "c" else x
    path = text_path(txt, font, x0, y)
    side = side or mix(face, (0, 0, 40), 0.45)
    sh = skia.Paint(AntiAlias=True, Color4f=c4((0, 0, 0), 0.35 * a))
    sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 12))
    p0 = skia.Path(path)
    p0.offset(0, depth + 12)
    c.drawPath(p0, sh)
    for k in range(depth, 0, -1):
        pk = skia.Path(path)
        pk.offset(0, k)
        c.drawPath(pk, skia.Paint(AntiAlias=True, Color4f=c4(mix(side, (0, 0, 0), 0.25 * k / depth), a)))
    c.drawPath(path, skia.Paint(AntiAlias=True, Color4f=c4(outline, a), Style=skia.Paint.kStroke_Style, StrokeWidth=font.getSize() * 0.08,
                                StrokeJoin=skia.Paint.kRound_Join))
    b = path.getBounds()
    fp = skia.Paint(AntiAlias=True)
    fp.setShader(skia.GradientShader.MakeLinear([skia.Point(0, b.top()), skia.Point(0, b.bottom())],
                                                [cint(mix(face, (255, 255, 255), 0.45), a), cint(face, a), cint(mix(face, (0, 0, 0), 0.15), a)],
                                                [0, 0.55, 1]))
    c.drawPath(path, fp)
    gl = skia.Paint(AntiAlias=True)
    gl.setShader(skia.GradientShader.MakeLinear([skia.Point(0, b.top()), skia.Point(0, b.top() + b.height() * 0.5)],
                                                [cint((255, 255, 255), 0.55 * a), cint((255, 255, 255), 0.0)]))
    c.save()
    c.clipPath(path, skia.ClipOp.kIntersect, True)
    c.drawRect(skia.Rect(b.left(), b.top(), b.right(), b.top() + b.height() * 0.45), gl)
    c.restore()
    return w


# ================================================================== 8-bit platformer world
PX = 4                      # one world pixel = 4 output pixels (480x270 world)
BW, BH = W // PX, H // PX
SKY = (92, 148, 252)
GROUND_Y = BH - 32          # two 16px tile rows at the bottom

CLOUD = ["....XXXX........",
         "..XXWWWWXX.XXX..",
         ".XWWWWWWWWXWWWX.",
         "XWWWWWWWWWWWWWWX",
         "XWWWWWWWWWWWWWBX",
         ".XBBWWWBBWWWBBX.",
         "..XXXXXXXXXXXX.."]
BUSH = ["....XXXX....XXXX....",
        "..XXGGGGXXXXGGGGXX..",
        ".XGGGLGGGGGGGGLGGGX.",
        "XGGGGGGGGGGGGGGGGGGX"]
HILL = ["........XXXX........",
        "......XXGGGGXX......",
        ".....XGGGGGGGGX.....",
        "....XGGDGGGGDGGX....",
        "...XGGGGGGGGGGGGX...",
        "..XGGGDGGGGGGDGGGX..",
        ".XGGGGGGGGGGGGGGGGX.",
        "XGGGGGGGGGGGGGGGGGGX"]
PAL = {"X": (0, 0, 0), "W": (252, 252, 252), "B": (160, 200, 252), "G": (0, 168, 0), "L": (128, 208, 16),
       "D": (0, 100, 0)}


def blit(img, pattern, x, y, scale=1, pal=PAL):
    for r, row in enumerate(pattern):
        for q, ch in enumerate(row):
            if ch in pal:
                x0, y0 = int(x + q * scale), int(y + r * scale)
                if 0 <= x0 < img.shape[1] and 0 <= y0 < img.shape[0]:
                    img[y0:y0 + scale, x0:x0 + scale] = pal[ch]


def brick(img, x, y):
    x, y = int(x), int(y)
    if x <= -16 or x >= img.shape[1]:
        return
    tile = np.zeros((16, 16, 3), np.uint8)
    tile[:] = (200, 76, 12)
    tile[0, :] = (252, 152, 56)
    for yy in (0, 4, 8, 12):
        tile[yy + 3, :] = (0, 0, 0)
        off = 0 if (yy // 4) % 2 == 0 else 8
        tile[yy:yy + 4, (off + 7) % 16] = (0, 0, 0)
        tile[yy:yy + 3, (off + 0) % 16] = (252, 152, 56) if off == 0 else tile[yy:yy + 3, 0]
    paste(img, tile, x, y)


def ground_tile(img, x, y):
    x, y = int(x), int(y)
    if x <= -16 or x >= img.shape[1]:
        return
    tile = np.zeros((16, 16, 3), np.uint8)
    tile[:] = (200, 76, 12)
    tile[:, 0] = tile[0, :] = (252, 188, 176)
    tile[:, 15] = tile[15, :] = (0, 0, 0)
    tile[7, 1:10] = (0, 0, 0)
    tile[1:15, 9] = (0, 0, 0)
    paste(img, tile, x, y)


def qblock(img, x, y, used=False, blink=0):
    x, y = int(x), int(y)
    tile = np.zeros((16, 16, 3), np.uint8)
    tile[:] = (136, 112, 0) if used else ((252, 152, 56) if blink else (228, 128, 40))
    tile[0, :] = tile[:, 0] = (0, 0, 0) if used else (252, 216, 168)
    tile[15, :] = tile[:, 15] = (0, 0, 0)
    for (px, py) in ((2, 2), (13, 2), (2, 13), (13, 13)):
        tile[py, px] = (0, 0, 0)
    if not used:
        q = ["0110", "1001", "0010", "0100", "0000", "0100"]
        for r, row in enumerate(q):
            for k, b in enumerate(row):
                if b == "1":
                    tile[4 + r * 1:5 + r * 1, 6 + k:7 + k] = (0, 0, 0)
    paste(img, tile, x, y)


def pipe(img, x, top):
    x, top = int(x), int(top)
    h = GROUND_Y - top
    body = np.zeros((h, 28, 3), np.uint8)
    body[:] = (0, 168, 0)
    body[:, 4:7] = (128, 208, 16)
    body[:, 0] = body[:, 27] = (0, 0, 0)
    body[:, 20:24] = (0, 110, 0)
    body[:10, :] = (0, 168, 0)
    body[:10, 3:6] = (128, 208, 16)
    body[0, :] = body[9, :] = (0, 0, 0)
    paste(img, body, x, top)
    lip = np.zeros((10, 32, 3), np.uint8)
    lip[:] = (0, 168, 0)
    lip[:, 4:8] = (128, 208, 16)
    lip[0, :] = lip[9, :] = lip[:, 0] = lip[:, 31] = (0, 0, 0)
    paste(img, lip, x - 2, top)


def coin(img, x, y, t):
    w = abs(math.cos(t * 6)) * 5 + 1
    x, y = int(x), int(y)
    cx = x + 3
    for r in range(12):
        half = int(w * math.sqrt(max(0.0, 1 - ((r - 5.5) / 6) ** 2)))
        if half <= 0:
            continue
        y0 = y + r
        if 0 <= y0 < img.shape[0]:
            a, b = max(0, cx - half), min(img.shape[1], cx + half + 1)
            if a < b:
                img[y0, a:b] = (252, 188, 60)
                img[y0, a] = (0, 0, 0)
                img[y0, b - 1] = (0, 0, 0)


def paste(img, tile, x, y):
    h, w = tile.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(img.shape[1], x + w), min(img.shape[0], y + h)
    if x0 < x1 and y0 < y1:
        img[y0:y1, x0:x1] = tile[y0 - y:y1 - y, x0 - x:x1 - x]


def platformer(t, lt, level_t, person_rgb, person_a):
    """480x270 world with him as an 8-bit sprite, upscaled x4 (nearest). Returns RGB float + block/coin state."""
    img = np.zeros((BH, BW, 3), np.uint8)
    img[:] = SKY
    scroll = lt * 14.0
    for i, (x0, y) in enumerate(((20, 62), (190, 50), (330, 72), (430, 56))):
        x = (x0 - scroll * 0.35) % (BW + 40) - 30
        blit(img, CLOUD, x, y, 2)
    for x0 in (-10, 260):
        x = (x0 - scroll * 0.6) % (BW + 60) - 50
        blit(img, HILL, x, GROUND_Y - 16, 2)
    for x0 in (120, 400):
        x = (x0 - scroll) % (BW + 60) - 40
        blit(img, BUSH, x, GROUND_Y - 8, 2)
    # floating brick rows with ? blocks and coins
    for bx0, row in ((10, "BQBQB"), (360, "BBQB")):
        base = (bx0 - scroll) % (BW + 140) - 100
        for k, ch in enumerate(row):
            if ch == "B":
                brick(img, base + k * 16, 118)
            else:
                qblock(img, base + k * 16, 118, blink=int(t * 4) % 2)
        for k in range(len(row)):
            coin(img, base + k * 16 + 4, 96 - 3 * math.sin(t * 3 + k), t + k * 0.3)
    pipe(img, (430 - scroll) % (BW + 120) - 60, GROUND_Y - 44)
    # ? block above his head: bumps on "Level up"
    d = t - level_t
    bump = -6 * math.sin(math.pi * min(1.0, max(0.0, d / 0.18))) if 0 <= d < 0.18 else 0
    qx = BW / 2 + 34
    qblock(img, qx - 8, 34 + bump, used=d >= 0, blink=int(t * 4) % 2)
    if 0 <= d < 0.7:
        coin(img, qx - 3, 20 - 26 * math.sin(math.pi * d / 0.7), t)
    # him, as a sprite: 4x4 blocks, reduced palette, 1px black outline
    small = cv2.resize(np.clip(person_rgb, 0, 255).astype(np.uint8), (BW, BH), interpolation=cv2.INTER_AREA)
    small = cv2.bilateralFilter(small, 5, 40, 5).astype(np.float32)
    small = (small - 128) * 1.15 + 138
    sa = cv2.resize(person_a, (BW, BH), interpolation=cv2.INTER_AREA) > 0.5
    q = (np.clip(small, 0, 255) // 48 * 48 + 24).astype(np.float32)
    g = q.mean(2, keepdims=True)
    q = np.clip(g + (q - g) * 1.35, 0, 255)
    if 0 <= d < 0.9:                                    # star-power flash
        hue = int((d * 18) % 3)
        q = np.roll(q, hue, axis=2) * 1.1
    q = q.astype(np.uint8)
    outline = cv2.dilate(sa.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~sa
    outline[GROUND_Y - 2:] = False
    img[outline] = (0, 0, 0)
    img[sa] = q[sa]
    # ground in front of him
    for gx in range(-16, BW + 16, 16):
        x = gx - (scroll % 16)
        ground_tile(img, x, GROUND_Y)
        ground_tile(img, x, GROUND_Y + 16)
    big = cv2.resize(img, (W, H), interpolation=cv2.INTER_NEAREST)
    return big.astype(np.float32)
