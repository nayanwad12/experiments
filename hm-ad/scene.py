"""scene: H&M 30 s launch ad (spec), built on the site's own design system:
black UI, red H&M script logo, uppercase nav, red promo bar, CAMPUS CLASSICS hero, footer member offer + payments.
Every frame is a pure function of time t.

    python3 scene.py stills 0.6 2.4 4.4 6.0     # check frames -> out/stills/
    python3 scene.py audio                      # music + sfx -> work/mix.wav
    python3 scene.py draft                      # half-res, half-fps preview -> out/draft.mp4
    python3 scene.py render                     # final -> out/hm-ad_v3.mp4

Needs (local, not in git): assets/products/*.png (product cutouts) and assets/site/* (logo, hero, payments).
"""

import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import skia

sys.path.insert(0, str(Path(__file__).resolve().parent / "vibe"))
import audio_kit as ak  # noqa: E402
from motion_kit import (Stage, clamp, ease_in_back, ease_in_cubic, ease_in_out_cubic,  # noqa: E402
                        ease_out_back, ease_out_bounce, ease_out_cubic, ease_out_expo, image as load_image, lerp,
                        noise1, paint, prog, pulse, rgb, rrect, text, text_width)

import timeline as TL  # noqa: E402

S = Stage(TL.W, TL.H, fps=TL.FPS, duration=TL.DURATION)
B = S.brand
W, H = TL.W, TL.H
U = min(W, H) / 1080
BEAT = TL.BEAT
HEX = B["colors"]

BLACK, WHITE, RED = rgb(HEX["black"]), rgb(HEX["paper"]), rgb(HEX["red"])
NAVGREY, DIVIDER, PANEL = rgb(HEX["navgrey"]), rgb(HEX["divider"]), rgb(HEX["panel"])
PACK = rgb(HEX["packshot"])
REGULAR = "InterTight-400.ttf"      # site-style regular; "body" is the 700 weight
SITE = Path("assets/site")
PROD_DIR = Path("assets/products")
HQ = skia.SamplingOptions(skia.CubicResampler.Mitchell())


# ------------------------------------------------------------------ helpers
def fit(s, font, max_w, max_size, tracking=0.0):
    return min(max_size, max_w / max(1, text_width(s, 100, font, tracking)) * 100)


def slam(c, s, x, y, k, size, font="display", fill=None, from_scale=1.9, rot=0.0, alpha=1.0, tracking=0.0):
    """kinetic slam: scale from_scale -> 1 with expo ease, quick fade in."""
    if k <= 0:
        return
    e = ease_out_expo(k)
    sc = lerp(from_scale, 1.0, e)
    c.save()
    c.translate(x, y)
    c.rotate(rot * (1 - e))
    c.scale(sc, sc)
    text(c, s, 0, 0, size=size, font=font, fill=WHITE if fill is None else fill, alpha=clamp(k * 4) * alpha,
         tracking=tracking)
    c.restore()


def beat_of(lt):
    i = int(lt / BEAT + 1e-6)
    return i, lt - i * BEAT


def fpaint(col, stroke=None):
    p = skia.Paint(Color=col, AntiAlias=True)
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    return p


def line(c, cx, cy, s, pts, col, w):
    p = skia.Path()
    p.moveTo(cx + pts[0][0] * s, cy + pts[0][1] * s)
    for x, y in pts[1:]:
        p.lineTo(cx + x * s, cy + y * s)
    c.drawPath(p, fpaint(col, stroke=w))


def rect(c, x, y, w, h, col):
    c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), skia.Paint(Color=col, AntiAlias=True))


def with_alpha(col, a):
    return skia.Color(skia.ColorGetR(col), skia.ColorGetG(col), skia.ColorGetB(col), int(255 * clamp(a)))


def blit(c, img, src, dst, alpha=1.0):
    c.drawImageRect(img, src, dst, HQ, skia.Paint(AntiAlias=True, Alphaf=clamp(alpha)))


# ------------------------------------------------------------------ real site + product assets
def logo(c, cx, cy, h, red=True, alpha=1.0, scale=1.0):
    """the H&M script logo (extracted from the site footer), h = height in px, centred on (cx, cy)."""
    if alpha <= 0:
        return 0
    img = load_image(str(SITE / ("logo_red.png" if red else "logo_white.png")))
    h *= scale
    w = img.width() * h / img.height()
    blit(c, img, skia.Rect.MakeWH(img.width(), img.height()), skia.Rect.MakeXYWH(cx - w / 2, cy - h / 2, w, h), alpha)
    return w


def prod(c, name, cx, cy, max_w, max_h, alpha=1.0, drop_shadow=False):
    """a product cutout fitted inside max_w x max_h, centred on (cx, cy)."""
    img = load_image(str(PROD_DIR / f"{name}.png"))
    s = min(max_w / img.width(), max_h / img.height())
    w, h = img.width() * s, img.height() * s
    if drop_shadow and alpha > 0:
        c.drawOval(skia.Rect.MakeXYWH(cx - w * 0.38, cy + h * 0.44, w * 0.76, h * 0.08),
                   paint(skia.Color(0, 0, 0, int(80 * alpha)), blur=10 * U))
    blit(c, img, skia.Rect.MakeWH(img.width(), img.height()), skia.Rect.MakeXYWH(cx - w / 2, cy - h / 2, w, h), alpha)
    return w, h


_SWATCH = {}


def swatch(name):
    """the product's main colour (median of opaque pixels) for colour dots."""
    if name not in _SWATCH:
        from PIL import Image
        a = np.asarray(Image.open(PROD_DIR / f"{name}.png").convert("RGBA")).reshape(-1, 4)
        a = a[a[:, 3] > 200][:, :3]
        r, g, b_ = (int(v) for v in np.median(a, axis=0))
        _SWATCH[name] = skia.Color(r, g, b_)
    return _SWATCH[name]


def hero_photo(c, x, y, w, h, zoom=1.0, fx=0.5, fy=0.42):
    """CAMPUS CLASSICS hero photo, cover-cropped into (x, y, w, h) around focus (fx, fy) of the source."""
    img = load_image(str(SITE / "hero_campus_classics.jpg"))
    iw, ih = img.width(), img.height()
    s = max(w / iw, h / ih) * zoom
    sw_, sh_ = w / s, h / s
    sx = clamp(fx * iw - sw_ / 2, 0, iw - sw_)
    sy = clamp(fy * ih - sh_ / 2, 0, ih - sh_)
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(x, y, w, h))
    blit(c, img, skia.Rect.MakeXYWH(sx, sy, sw_, sh_), skia.Rect.MakeXYWH(x, y, w, h))
    c.restore()


def payments(c, cx, cy, h, alpha=1.0):
    """the footer's payment badges (cash on delivery, Visa, Mastercard, UPI)."""
    img = load_image(str(SITE / "payments.png"))
    w = img.width() * h / img.height()
    blit(c, img, skia.Rect.MakeWH(img.width(), img.height()), skia.Rect.MakeXYWH(cx - w / 2, cy - h / 2, w, h), alpha)


def promo_bar(c, x, y, w, h, size, alpha=1.0):
    """the red-on-black member-prices bar from the top of the site."""
    rect(c, x, y, w, h, BLACK)
    text(c, TL.COPY["promo"], x + size * 0.9, y + h / 2, size=size, font=REGULAR, fill=RED, align="left", alpha=alpha)
    pl = size * 0.42
    px, py = x + w - size * 1.2, y + h / 2
    col = with_alpha(RED, alpha)
    c.drawLine(px - pl, py, px + pl, py, fpaint(col, stroke=size * 0.09))
    c.drawLine(px, py - pl, px, py + pl, fpaint(col, stroke=size * 0.09))
    rect(c, x, y + h - max(1, 1.5 * U), w, max(1, 1.5 * U), DIVIDER)


# ---------- site icons (white line icons, like the header)
def ic_search(c, x, y, s, col):
    c.drawCircle(x - s * 0.08, y - s * 0.08, s * 0.3, fpaint(col, stroke=s * 0.09))
    c.drawLine(x + s * 0.13, y + s * 0.13, x + s * 0.4, y + s * 0.4, fpaint(col, stroke=s * 0.1))


def ic_user(c, x, y, s, col):
    c.drawCircle(x, y - s * 0.18, s * 0.2, fpaint(col, stroke=s * 0.09))
    c.drawArc(skia.Rect.MakeXYWH(x - s * 0.38, y + s * 0.1, s * 0.76, s * 0.6), 180, 180, False,
              fpaint(col, stroke=s * 0.09))


def heart(c, x, y, s, filled, col):
    p = skia.Path()
    p.moveTo(x, y + s * 0.35)
    p.cubicTo(x - s * 0.9, y - s * 0.25, x - s * 0.35, y - s * 0.85, x, y - s * 0.3)
    p.cubicTo(x + s * 0.35, y - s * 0.85, x + s * 0.9, y - s * 0.25, x, y + s * 0.35)
    p.close()
    c.drawPath(p, fpaint(col) if filled else fpaint(col, stroke=max(2.5 * U, s * 0.14)))


def ic_bag(c, x, y, s, col):
    p = skia.Path()
    p.addRect(skia.Rect.MakeXYWH(x - s * 0.38, y - s * 0.18, s * 0.76, s * 0.62))
    c.drawPath(p, fpaint(col, stroke=s * 0.09))
    c.drawArc(skia.Rect.MakeXYWH(x - s * 0.18, y - s * 0.46, s * 0.36, s * 0.5), 180, 180, False,
              fpaint(col, stroke=s * 0.09))


# ------------------------------------------------------------------ global FX
def shake_offset(t):
    a = 0.0
    for hit in TL.HITS:
        d = t - hit
        if 0 <= d < 0.4:
            a += 16 * U * math.exp(-10 * d)
    return a * noise1(t * 40, 1), a * noise1(t * 40, 2)


def flash(c, t):
    for hit in TL.HITS:
        d = t - hit
        if 0 <= d < 0.1:
            rect(c, 0, 0, W, H, skia.Color(255, 255, 255, int(130 * (1 - d / 0.1))))


def caption(c, lt, caps, y, max_size=170 * U, last_red=True, color=None):
    """big kinetic caption track: each word slams on its beat and replaces the last."""
    cur = None
    for i, (bn, w) in enumerate(caps):
        if lt >= bn * BEAT:
            cur = (i, bn, w)
    if cur is None:
        return
    i, bn, w = cur
    k = prog(lt, bn * BEAT, 0.18)
    size = fit(w, "display", W * 0.86, max_size)
    col = RED if (last_red and i == len(caps) - 1) else (color or WHITE)
    bump = 1 + 0.035 * pulse(lt, TL.BPM)
    c.save()
    c.translate(W / 2, y)
    c.scale(bump, bump)
    slam(c, w, 0, 0, k, size, fill=col, rot=-5 if i % 2 else 5)
    c.restore()


# ------------------------------------------------------------------ scenes
HOOK_PRODUCTS = ["men_02_black_varsity_jacket", "women_07_yellow_tiered_maxi_dress",
                 "men_10_houndstooth_varsity_jacket", "women_04_yellow_boat_neck_top"]


def s_hook(c, t, lt, dur):
    bi, bl = beat_of(lt)
    if bi < 4:
        first = bi < 2
        c.clear(BLACK if first else RED)
        if first:                                           # the site's promo bar flickers on at the top
            promo_bar(c, 0, 0, W, 110 * U, 34 * U, alpha=clamp(prog(lt, 0.1, 0.15) * 3))
        words = TL.COPY["hook_a"] if first else TL.COPY["hook_b"]
        base = 0 if first else 2
        size = min(fit(w, "display", W * 0.86, 260 * U) for w in words)
        for i, w in enumerate(words):
            k = prog(lt, (base + i) * BEAT, 0.18)
            y = H / 2 - size * 0.55 + i * size * 1.1
            col = (WHITE if i == 0 else RED) if first else (WHITE if i == 0 else BLACK)
            slam(c, w, W / 2, y, k, size, fill=col, rot=-6 if i else 6)
        if not first:                                       # underline sweeps in under "YOU."
            kk = ease_out_expo(prog(lt, 3 * BEAT + 0.12, 0.25))
            bw = text_width(words[1], size, "display") * kk
            rect(c, W / 2 - bw / 2, H / 2 + size * 1.25, bw, 18 * U, BLACK)
    else:
        i = min(3, bi - 4)
        c.clear(BLACK if i % 2 == 0 else RED)
        kp = ease_out_back(prog(bl, 0, 0.25))
        c.save()
        c.translate(W / 2, H / 2 + 330 * U + (1 - kp) * 400 * U)
        c.rotate((1 - kp) * (15 if i % 2 else -15) + (4 if i % 2 else -4))
        prod(c, HOOK_PRODUCTS[i], 0, 0, 720 * U, 760 * U * (0.85 + 0.15 * kp))
        c.restore()
        w = TL.COPY["hook_c"][i]
        size = fit(w, "display", W * 0.8, 340 * U)
        k = prog(bl, 0, 0.16)
        bump = 1 + 0.03 * pulse(t, TL.BPM)
        c.save()
        c.translate(W / 2, H / 2 - 330 * U)
        c.rotate(-4 if i % 2 else 4)
        c.scale(bump, bump)
        for j in range(3, 0, -1):                          # echo outlines behind the word for speed
            text(c, w, 0, -j * size * 0.95 * (1 - ease_out_expo(k)) - j * 8 * U, size=size, font="display",
                 fill=skia.ColorTRANSPARENT, stroke=3 * U, stroke_col=WHITE, alpha=0.18 * j / 3 + 0.08)
        slam(c, w, 0, 0, k, size, fill=WHITE, from_scale=1.5)
        c.restore()


def hanger(c, x, y, swing, col):
    c.save()
    c.translate(x, y)
    c.rotate(swing)
    p = fpaint(col, stroke=6 * U)
    hook = skia.Path()
    hook.moveTo(0, 30 * U)
    hook.lineTo(0, 12 * U)
    hook.arcTo(skia.Rect.MakeXYWH(-14 * U, -16 * U, 28 * U, 28 * U), 90, -270, False)
    c.drawPath(hook, p)
    tri = skia.Path()
    tri.moveTo(-95 * U, 85 * U)
    tri.lineTo(0, 30 * U)
    tri.lineTo(95 * U, 85 * U)
    tri.close()
    c.drawPath(tri, p)
    c.restore()


def s_problem(c, t, lt, dur):
    c.clear(BLACK)
    rail_y = 380 * U
    rect(c, 60 * U, rail_y - 6 * U, W - 120 * U, 12 * U, WHITE)
    kinds = ["women_01_archives_sweatshirt", "men_02_black_varsity_jacket", "women_03_teal_boat_neck_top",
             "men_06_green_rugby_shirt", "women_06_tie_neck_blouse"]
    n = len(kinds)
    for i, kind in enumerate(kinds):
        x = W / 2 + (i - (n - 1) / 2) * 196 * U
        swing = 5 * math.sin(t * 5 + i)
        hanger(c, x, rail_y + 14 * U, swing, WHITE)
        kd = prog(lt, 6 * BEAT + i * 0.08, 0.5)
        if kd > 0:
            drop = (1 - ease_out_bounce(kd)) * -600 * U
            c.save()
            c.translate(x, rail_y + 14 * U)
            c.rotate(swing)
            prod(c, kind, 0, 205 * U + drop, 200 * U, 280 * U)
            c.restore()
    words = TL.COPY["problem"]
    size = 170 * U
    y0 = 960 * U
    fix = prog(lt, 5 * BEAT, 0.2)
    for i, w in enumerate(words):
        y = y0 + i * size * 1.08
        k = prog(lt, i * BEAT, 0.18)
        if i == 0 and fix > 0:
            fall = ease_in_cubic(prog(lt, 5 * BEAT, 0.35))
            c.save()
            c.translate(W / 2, y - fall * 500 * U)
            c.rotate(-fall * 25)
            text(c, w, 0, 0, size=fit(w, "display", W * 0.86, size), font="display", fill=NAVGREY,
                 alpha=clamp(1 - fall * 5))
            c.restore()
            sz = fit(TL.COPY["problem_fix"], "display", W * 0.86, size)
            slam(c, TL.COPY["problem_fix"], W / 2, y, fix, sz, fill=RED, from_scale=2.2)
            continue
        if i == 2 and fix > 0:
            w = "WEAR."
        slam(c, w, W / 2, y, k, fit(w, "display", W * 0.86, size), fill=WHITE)
        if i == 0:                                         # red strike-through on beat 4
            ks = ease_out_expo(prog(lt, 4 * BEAT, 0.22))
            if ks > 0:
                tw = text_width(w, fit(w, "display", W * 0.86, size), "display") + 40 * U
                rect(c, W / 2 - tw / 2, y - 10 * U, tw * ks, 22 * U, RED)


def s_reveal(c, t, lt, dur):
    c.clear(BLACK)
    if lt < 2 * BEAT:
        # beat 0: the real red logo slams in on black, a red ring blasts out
        kr = ease_out_expo(prog(lt, 0, 0.45))
        c.drawCircle(W / 2, H / 2, kr * 900 * U, fpaint(with_alpha(RED, 1 - kr), stroke=60 * U * (1 - kr) + 2 * U))
        kl = prog(lt, 0.02, 0.22)
        bump = 1 + 0.04 * pulse(t, TL.BPM)
        logo(c, W / 2, H / 2, 380 * U, red=True, alpha=clamp(kl * 4), scale=lerp(2.6, 1.0, ease_out_expo(kl)) * bump)
        kp = ease_out_cubic(prog(lt, BEAT, 0.25))
        if kp > 0:
            promo_bar(c, 0, 0, W, 110 * U, 34 * U, alpha=kp)
    else:
        # beat 2: cut to the site's hero campaign, full bleed, slow push
        ll = lt - 2 * BEAT
        hero_photo(c, 0, 0, W, H, zoom=lerp(1.12, 1.0, ease_out_cubic(clamp(ll / (2 * BEAT)))), fx=0.5, fy=0.45)
        ks = ease_out_expo(prog(ll, 0.05, 0.3))             # bottom label strip, like the site
        by = 1380 * U
        rect(c, 0, by, W * ks, 120 * U, BLACK)
        if ks > 0.3:
            a = clamp((ks - 0.3) * 3)
            text(c, TL.COPY["reveal_sub"], 70 * U, by + 60 * U, size=46 * U, font=REGULAR, fill=WHITE, align="left",
                 tracking=0.06, alpha=a)
            ax = W - 90 * U
            line(c, ax, by + 60 * U, U, [(-40, 0), (0, 0)], with_alpha(WHITE, a), 4 * U)
            line(c, ax, by + 60 * U, U, [(-14, -14), (0, 0), (-14, 14)], with_alpha(WHITE, a), 4 * U)
        promo_bar(c, 0, 0, W, 110 * U, 34 * U)
        rect(c, 0, 110 * U, W, 150 * U, BLACK)
        logo(c, 120 * U, 185 * U, 84 * U, red=True)


# ---------- the interactive site (phone), rebuilt from the real header / nav / hero
PX, PW = (W - 720 * U) / 2, 720 * U
PY_REST = 560 * U
SX_IN, SY_IN = 18 * U, 18 * U
SW = PW - 2 * SX_IN
PROMO_TOP, HEADER_TOP, NAV_TOP, CONTENT_TOP = 54 * U, 104 * U, 184 * U, 246 * U   # inside the screen
HERO_H = 540 * U
GAP = 16 * U
TILE_W = (SW - 3 * GAP) / 2
TILE_IMG = 330 * U
TILE_H = TILE_IMG + 70 * U
SCROLL = HERO_H + 8 * U
PRODUCTS = ["men_02_black_varsity_jacket", "men_10_houndstooth_varsity_jacket", "men_12_navy_denim_jacket",
            "men_06_green_rugby_shirt"]
LANDING = ["women_07_yellow_tiered_maxi_dress", "women_08_khaki_peplum_jacket", "women_01_archives_sweatshirt"]


def tile_xy(i):
    """top-left of product image i in content coords."""
    col, row = i % 2, i // 2
    return GAP + col * (TILE_W + GAP), HERO_H + 24 * U + row * (TILE_H + 8 * U)


def tab_positions(sx):
    xs, x = [], sx + 26 * U
    for tb in TL.COPY["tabs"]:
        tw = text_width(tb, 23 * U, "body", 0.04)
        xs.append((x, tw))
        x += tw + 30 * U
    return xs


def app_layout(py):
    """absolute tap targets for the current phone position."""
    sx, sy = PX + SX_IN, py + SY_IN
    tabs = tab_positions(sx)
    ct = sy + CONTENT_TOP - SCROLL

    def plus(i):
        x, y = tile_xy(i)
        return sx + x + TILE_W - 38 * U, ct + y + TILE_IMG - 38 * U

    def heart_xy(i):
        x, y = tile_xy(i)
        return sx + x + TILE_W - 38 * U, ct + y + 38 * U

    return {
        "men": (tabs[1][0] + tabs[1][1] / 2, sy + NAV_TOP + 30 * U),
        "heart0": heart_xy(0), "plus1": plus(1), "plus2": plus(2), "plus3": plus(3),
        "bag": (sx + SW - 44 * U, sy + HEADER_TOP + 40 * U),
        "checkout": (sx + SW / 2, sy + 1000 * U),
        "tab_x": tabs,
    }


# (local beat, target) for the finger
TAPS = [(2, "men"), (6, "heart0"), (7, "plus1"), (8, "plus2"), (9, "plus3"), (10, "bag"), (12, "checkout")]


def tapped(lt, beat_n):
    return lt >= beat_n * BEAT


def draw_screen(c, lt, sx, sy):
    """the H&M site UI inside the phone screen (absolute coords)."""
    rect(c, sx, sy, SW, 2000 * U, BLACK)
    lay = app_layout(sy - SY_IN)
    names = TL.COPY["products"]
    # ---- page content (clipped under the header)
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(sx, sy + CONTENT_TOP, SW, 2000 * U))
    page = ease_in_out_cubic(prog(lt, 2 * BEAT + 0.05, 0.3))            # LADIES landing -> MEN page
    scroll = ease_in_out_cubic(prog(lt, 4 * BEAT, 0.55)) * SCROLL
    if page < 1:                                                        # LADIES landing slides out left
        hx, hy = sx - page * SW, sy + CONTENT_TOP
        rect(c, hx, hy, SW, HERO_H, PACK)
        prod(c, LANDING[0], hx + SW * 0.22, hy + 240 * U, 200 * U, 390 * U)
        prod(c, LANDING[1], hx + SW * 0.55, hy + 220 * U, 240 * U, 260 * U)
        prod(c, LANDING[2], hx + SW * 0.82, hy + 300 * U, 200 * U, 220 * U)
        rect(c, hx, hy + HERO_H - 70 * U, SW, 70 * U, BLACK)
        text(c, "NEW ARRIVALS", hx + 24 * U, hy + HERO_H - 35 * U, size=24 * U, font=REGULAR, fill=WHITE,
             align="left", tracking=0.06)
    # MEN page (slides in from right) with the real CAMPUS CLASSICS hero, then the product grid
    cx0, cy0 = sx + (1 - page) * SW, sy + CONTENT_TOP - scroll
    hero_photo(c, cx0, cy0, SW, HERO_H - 70 * U, zoom=1.0, fx=0.5, fy=0.48)
    rect(c, cx0, cy0 + HERO_H - 70 * U, SW, 70 * U, BLACK)
    text(c, TL.COPY["reveal_sub"], cx0 + 24 * U, cy0 + HERO_H - 35 * U, size=24 * U, font=REGULAR, fill=WHITE,
         align="left", tracking=0.06)
    line(c, cx0 + SW - 30 * U, cy0 + HERO_H - 35 * U, U, [(-22, 0), (0, 0)], WHITE, 3 * U)
    line(c, cx0 + SW - 30 * U, cy0 + HERO_H - 35 * U, U, [(-8, -8), (0, 0), (-8, 8)], WHITE, 3 * U)
    for i, pname in enumerate(PRODUCTS):
        x, y = tile_xy(i)
        x, y = cx0 + x, cy0 + y
        rect(c, x, y, TILE_W, TILE_IMG, PACK)
        prod(c, pname, x + TILE_W / 2, y + TILE_IMG / 2, TILE_W * 0.8, TILE_IMG * 0.84)
        text(c, names[i], x + 2 * U, y + TILE_IMG + 30 * U, size=22 * U, font=REGULAR, fill=WHITE, align="left")
        c.drawCircle(x + 10 * U, y + TILE_IMG + 58 * U, 7 * U, fpaint(swatch(pname)))
        c.drawCircle(x + 10 * U, y + TILE_IMG + 58 * U, 7 * U, fpaint(DIVIDER, stroke=1.5 * U))
        hx, hy = x + TILE_W - 38 * U, y + 38 * U                       # heart (tile 0 gets loved)
        loved = i == 0 and tapped(lt, 6)
        kp = ease_out_back(prog(lt, 6 * BEAT, 0.3)) if loved else 1
        heart(c, hx, hy, 20 * U * (0.6 + 0.4 * kp + 0.25 * math.sin(math.pi * clamp(kp))), loved,
              RED if loved else BLACK)
        px, py = x + TILE_W - 62 * U, y + TILE_IMG - 62 * U            # quick-add
        added = i > 0 and tapped(lt, 6 + i)
        rect(c, px, py, 48 * U, 48 * U, BLACK if added else WHITE)
        pc = WHITE if added else BLACK
        if added:
            line(c, px, py, U, [(13, 25), (21, 33), (35, 16)], pc, 4 * U)
        else:
            rect(c, px + 14 * U, py + 22 * U, 20 * U, 4 * U, pc)
            rect(c, px + 22 * U, py + 14 * U, 4 * U, 20 * U, pc)
    c.restore()

    # ---- fixed top: status bar, promo bar, header (logo + icons), nav
    rect(c, sx, sy, SW, CONTENT_TOP, BLACK)
    text(c, "9:41", sx + 60 * U, sy + 30 * U, size=22 * U, font="body", fill=WHITE)
    promo_bar(c, sx, sy + PROMO_TOP, SW, HEADER_TOP - PROMO_TOP, 19 * U)
    logo(c, sx + 58 * U, sy + HEADER_TOP + 40 * U, 46 * U, red=True)
    iy = sy + HEADER_TOP + 40 * U
    ic_search(c, sx + SW - 206 * U, iy, 34 * U, WHITE)
    ic_user(c, sx + SW - 152 * U, iy, 34 * U, WHITE)
    heart(c, sx + SW - 98 * U, iy + 2 * U, 15 * U, tapped(lt, 6), RED if tapped(lt, 6) else WHITE)
    bxc = sx + SW - 44 * U
    ic_bag(c, bxc, iy, 34 * U, WHITE)
    count = sum(1 for n in (7, 8, 9) if tapped(lt, n))
    if count:
        last = max(n for n in (7, 8, 9) if tapped(lt, n))
        kb = ease_out_back(prog(lt, last * BEAT + 0.05, 0.3))
        r = 13 * U * (0.5 + 0.5 * kb + 0.3 * math.sin(math.pi * clamp(kb)))
        c.drawCircle(bxc + 16 * U, iy - 16 * U, r, fpaint(RED))
        text(c, str(count), bxc + 16 * U, iy - 16 * U, size=r * 1.3, font="body", fill=WHITE)
    men_active = page > 0.5
    for i, (tx, tw) in enumerate(lay["tab_x"]):
        active = (i == 1) if men_active else (i == 0)
        text(c, TL.COPY["tabs"][i], tx, sy + NAV_TOP + 30 * U, size=23 * U, font="body" if active else REGULAR,
             fill=WHITE if active else NAVGREY, align="left", tracking=0.04)
    rect(c, sx, sy + CONTENT_TOP - 1.5 * U, SW, 1.5 * U, DIVIDER)

    # ---- toast "Added to bag"
    count_txt = f"Added to bag ({count})"
    kt = prog(lt, 7 * BEAT + 0.05, 0.25)
    kt_out = prog(lt, 10 * BEAT - 0.2, 0.2)
    if 0 < kt and kt_out < 1:
        ty = sy + 860 * U + (1 - ease_out_back(kt)) * 200 * U + ease_in_cubic(kt_out) * 300 * U
        rect(c, sx + 24 * U, ty, SW - 48 * U, 84 * U, WHITE)
        line(c, sx + 50 * U, ty + 26 * U, U, [(0, 16), (10, 26), (30, 4)], BLACK, 4 * U)
        text(c, count_txt, sx + 100 * U, ty + 42 * U, size=27 * U, font="body", fill=BLACK, align="left")

    # ---- shopping bag drawer (dark, like the site), real payment badges under the button
    kd = ease_out_expo(prog(lt, 10 * BEAT + 0.08, 0.4))
    if kd > 0:
        off = (1 - kd) * 1300 * U
        dy = sy + 120 * U + off
        rect(c, 0, 0, W, H, skia.Color(0, 0, 0, int(120 * kd)))
        rect(c, sx, dy, SW, 2000 * U, PANEL)
        rect(c, sx, dy, SW, 1.5 * U, DIVIDER)
        text(c, "SHOPPING BAG (3)", sx + 36 * U, dy + 66 * U, size=30 * U, font="body", fill=WHITE, align="left",
             tracking=0.04)
        for j, i in enumerate((1, 2, 3)):
            ry = dy + 120 * U + j * 190 * U
            rect(c, sx + 36 * U, ry, 140 * U, 170 * U, PACK)
            prod(c, PRODUCTS[i], sx + 106 * U, ry + 85 * U, 120 * U, 150 * U)
            text(c, names[i], sx + 200 * U, ry + 50 * U, size=27 * U, font="body", fill=WHITE, align="left")
            text(c, "Size M  ·  Qty 1", sx + 200 * U, ry + 92 * U, size=23 * U, font=REGULAR, fill=NAVGREY,
                 align="left")
            rect(c, sx + 36 * U, ry + 180 * U, SW - 72 * U, 1.5 * U, DIVIDER)
        press = tapped(lt, 12)
        bw, bh = SW - 72 * U, 88 * U
        bx, by = sx + 36 * U, sy + 1000 * U - bh / 2 + off
        rect(c, bx, by, bw, bh, RED if press else WHITE)
        text(c, "CONTINUE TO CHECKOUT", bx + bw / 2, by + bh / 2, size=26 * U, font="body",
             fill=WHITE if press else BLACK, tracking=0.06)
        payments(c, sx + SW / 2, by + bh + 52 * U, 30 * U)

    # ---- success
    ks = prog(lt, 13 * BEAT, 0.35)
    if ks > 0:
        rect(c, sx, sy, SW, 2000 * U, skia.Color(0, 0, 0, int(255 * clamp(ks * 3))))
        ccx, ccy = sx + SW / 2, sy + 480 * U
        c.drawCircle(ccx, ccy, 120 * U * ease_out_back(ks), fpaint(RED))
        kc = ease_out_cubic(prog(lt, 13 * BEAT + 0.15, 0.3))
        if kc > 0:
            p = skia.Path()
            pts = [(-52, 2), (-14, 40), (56, -36)]
            p.moveTo(ccx + pts[0][0] * U, ccy + pts[0][1] * U)
            seg = kc * 2
            p.lineTo(ccx + lerp(pts[0][0], pts[1][0], min(1, seg)) * U, ccy + lerp(pts[0][1], pts[1][1], min(1, seg)) * U)
            if seg > 1:
                p.lineTo(ccx + lerp(pts[1][0], pts[2][0], seg - 1) * U, ccy + lerp(pts[1][1], pts[2][1], seg - 1) * U)
            c.drawPath(p, fpaint(WHITE, stroke=16 * U))
        kt2 = ease_out_cubic(prog(lt, 13 * BEAT + 0.25, 0.3))
        text(c, "ORDER CONFIRMED", ccx, ccy + 200 * U + (1 - kt2) * 30 * U, size=40 * U, font="body", fill=WHITE,
             alpha=kt2, tracking=0.06)
        text(c, "Thanks for shopping with us", ccx, ccy + 256 * U, size=25 * U, font=REGULAR, fill=NAVGREY, alpha=kt2)
        logo(c, ccx, ccy + 400 * U, 60 * U, red=True, alpha=kt2)
    return lay


def finger(c, lt, lay):
    """tap indicator: glides between targets, ripples on each tap."""
    pos = None
    for j, (bn, key) in enumerate(TAPS):
        tt = bn * BEAT
        x, y = lay[key]
        if j == 0:
            if lt < tt - 0.35:
                return
            k = ease_out_cubic(prog(lt, tt - 0.35, 0.3))
            pos = (lerp(W * 0.9, x, k), lerp(H * 0.95, y, k))
        if lt >= tt - 0.3 and j > 0:
            px_, py_ = lay[TAPS[j - 1][1]]
            k = ease_in_out_cubic(prog(lt, tt - 0.3, 0.25))
            pos = (lerp(px_, x, k), lerp(py_, y, k))
        d = lt - tt
        if 0 <= d < 0.4:                                  # ripple
            r = lerp(20, 90, ease_out_cubic(d / 0.4)) * U
            c.drawCircle(x, y, r, fpaint(with_alpha(RED, 0.85 * (1 - d / 0.4)), stroke=6 * U))
    if pos is None or lt > TAPS[-1][0] * BEAT + 0.5:
        return
    press = any(0 <= lt - bn * BEAT < 0.12 for bn, _ in TAPS)
    r = (30 if press else 36) * U
    c.drawCircle(pos[0], pos[1], r, fpaint(skia.Color(255, 255, 255, 110)))
    c.drawCircle(pos[0], pos[1], r, fpaint(WHITE, stroke=4 * U))


def s_app(c, t, lt, dur):
    c.clear(BLACK)
    off = (lt * 120 * U) % (160 * U)
    for i in range(-2, 16):
        rect(c, 0, i * 160 * U + off, W, 2 * U, PANEL)
    kin = ease_out_expo(prog(lt, 0, 0.5))
    kout = ease_in_back(prog(lt, dur - 0.25, 0.25))
    py = lerp(H, PY_REST, kin) + kout * 300 * U
    zoom = 1 + 0.04 * ease_in_out_cubic(prog(lt, 4 * BEAT, 8 * BEAT))
    c.save()
    c.translate(W / 2, py + 500 * U)
    c.scale(zoom, zoom)
    c.translate(-W / 2, -(py + 500 * U))
    rrect(c, PX, py, PW, 1600 * U, 90 * U, rgb("#1E1E1E"))
    rrect(c, PX, py, PW, 1600 * U, 90 * U, DIVIDER, stroke=3 * U)
    c.save()
    c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(PX + SX_IN, py + SY_IN, SW, 1600 * U), 72 * U, 72 * U))
    lay = draw_screen(c, lt, PX + SX_IN, py + SY_IN)
    c.restore()
    rrect(c, W / 2 - 80 * U, py + 30 * U, 160 * U, 34 * U, 17 * U, rgb("#1E1E1E"))           # notch
    finger(c, lt, lay)
    c.restore()
    caption(c, lt, TL.COPY["app_caps"], 400 * U, max_size=160 * U)


MONTAGE = [  # (bg, fg, product) - one per category in TL.COPY["categories"]
    (BLACK, WHITE, "women_07_yellow_tiered_maxi_dress"),
    (WHITE, BLACK, "men_02_black_varsity_jacket"),
    (RED, WHITE, "men_12_navy_denim_jacket"),
    (BLACK, WHITE, "men_10_houndstooth_varsity_jacket"),
    (RED, WHITE, "women_12_espresso_club_tee"),
    (WHITE, BLACK, "women_08_khaki_peplum_jacket"),
]


def s_montage(c, t, lt, dur):
    bi, bl = beat_of(lt)
    if bi < 6:
        bg, fg, pname = MONTAGE[bi]
        c.clear(bg)
        word = TL.COPY["categories"][bi]
        k = prog(bl, 0, 0.16)
        size = fit(word, "display", W * 0.88, 260 * U)
        kg = ease_out_back(prog(bl, 0.02, 0.3))
        c.save()
        c.translate(W / 2, 1150 * U + (1 - kg) * 500 * U)
        c.rotate((1 - kg) * (12 if bi % 2 else -12) + 3 * math.sin(lt * 8))
        sc = 0.9 + 0.1 * kg
        prod(c, pname, 0, 0, 700 * U * sc, 760 * U * sc, drop_shadow=True)
        c.restore()
        slam(c, word, W / 2, 560 * U, k, size, fill=fg, from_scale=1.7)
        text(c, f"0{bi + 1} / 06", 80 * U, 330 * U, size=30 * U, font=REGULAR, fill=fg, align="left", tracking=0.1)
        text(c, "SHOP →", W - 80 * U, 330 * U, size=30 * U, font=REGULAR, fill=fg, align="right", tracking=0.1)
    else:
        j = bi - 6
        cur = None
        for idx, (bn, lines) in enumerate(TL.COPY["promise"]):
            if j >= bn:
                cur = (idx, bn, lines)
        idx, bn, lines = cur
        bg = [BLACK, RED, BLACK, WHITE, RED][idx]
        fg = BLACK if bg == WHITE else WHITE
        c.clear(bg)
        kloc = lt - (6 + bn) * BEAT
        size = min(fit(w, "display", W * 0.86, 330 * U) for w in lines)
        for li, w in enumerate(lines):
            y = H / 2 - (len(lines) - 1) * size * 0.55 + li * size * 1.1
            slam(c, w, W / 2, y, prog(kloc, li * BEAT * 0.5, 0.16), size, fill=fg, rot=-6 if li else 6,
                 from_scale=2.0)


OUT_TOPS = ["women_01_archives_sweatshirt", "women_03_teal_boat_neck_top", "women_06_tie_neck_blouse",
            "women_04_yellow_boat_neck_top", "women_11_green_pocket_tee", "women_12_espresso_club_tee",
            "men_06_green_rugby_shirt", "men_01_pinstripe_shirt"]
OUT_BOTS = ["women_02_wide_leg_jeans", "women_05_olive_barrel_trousers", "women_10_striped_pull_on_trousers",
            "men_05_cream_trousers"]


def s_outfit(c, t, lt, dur):
    c.clear(BLACK)
    bi, bl = beat_of(lt)
    bi = min(bi, 7)
    cx = W / 2
    rect(c, cx - 330 * U, 560 * U, 660 * U, 880 * U, PACK)
    bk = OUT_BOTS[(bi // 2) % len(OUT_BOTS)]                 # bottoms every 2 beats, tops every beat
    kb = ease_out_expo(prog(lt, (bi // 2) * 2 * BEAT, 0.22))
    dirb = 1 if (bi // 2) % 2 else -1
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(cx - 330 * U, 560 * U, 660 * U, 880 * U))
    prod(c, bk, cx + (1 - kb) * dirb * 700 * U, 1130 * U, 360 * U, 560 * U)
    kt = ease_out_expo(prog(bl, 0, 0.2))
    dirt = 1 if bi % 2 else -1
    if kt < 1 and bi > 0:
        prod(c, OUT_TOPS[bi - 1], cx - kt * dirt * 900 * U, 800 * U, 560 * U, 470 * U)
    prod(c, OUT_TOPS[bi], cx + (1 - kt) * dirt * 900 * U, 800 * U, 560 * U, 470 * U)
    c.restore()
    for side in (-1, 1):                                     # arrows, tapped on every beat
        ax = cx + side * 430 * U
        hit = (side == 1) == (bi % 2 == 0)
        pr = 0.85 if hit and bl < 0.1 else 1.0
        c.drawCircle(ax, 900 * U, 48 * U * pr, fpaint(BLACK))
        c.drawCircle(ax, 900 * U, 48 * U * pr, fpaint(WHITE, stroke=3 * U))
        line(c, ax, 900 * U, U, [(-8 * side, -16), (8 * side, 0), (-8 * side, 16)], WHITE, 5 * U)
        if hit and bl < 0.35:
            r = lerp(48, 110, ease_out_cubic(bl / 0.35)) * U
            c.drawCircle(ax, 900 * U, r, fpaint(with_alpha(RED, 0.85 * (1 - bl / 0.35)), stroke=5 * U))
    for i, nm in enumerate(OUT_TOPS):                        # colour swatches
        x = cx + (i - 3.5) * 78 * U
        c.drawCircle(x, 1500 * U, 24 * U, fpaint(swatch(nm)))
        c.drawCircle(x, 1500 * U, 24 * U, fpaint(DIVIDER, stroke=2 * U))
        if i == bi:
            c.drawCircle(x, 1500 * U, 34 * U, fpaint(WHITE, stroke=4 * U))
    caption(c, lt, TL.COPY["outfit_caps"], 380 * U, max_size=170 * U)


STRIP = ["women_07_yellow_tiered_maxi_dress", "men_02_black_varsity_jacket", "women_01_archives_sweatshirt",
         "men_12_navy_denim_jacket", "women_06_tie_neck_blouse", "men_10_houndstooth_varsity_jacket",
         "women_03_teal_boat_neck_top", "men_11_olive_utility_coat", "women_08_khaki_peplum_jacket"]


def s_endcard(c, t, lt, dur):
    """footer-style end card: promo bar, product strip, red logo, CTA tap, member offer, payments."""
    c.clear(BLACK)
    promo_bar(c, 0, 0, W, 110 * U, 34 * U, alpha=ease_out_cubic(prog(lt, 0.1, 0.3)))
    ks = ease_out_expo(prog(lt, 0.1, 0.5))
    step = 230 * U
    off = lt * 160 * U
    for i, nm in enumerate(STRIP * 2):                       # product strip on packshot tiles
        x = 140 * U + i * step - off
        if -step < x < W + step:
            yy = 400 * U + (1 - ks) * -300 * U
            rect(c, x - 100 * U, yy - 125 * U, 200 * U, 250 * U, with_alpha(PACK, ks))
            prod(c, nm, x, yy, 170 * U, 220 * U, alpha=ks)
    kl = prog(lt, 0.0, 0.22)
    bump = 1 + 0.03 * pulse(t, TL.BPM)
    logo(c, W / 2, 770 * U, 230 * U, red=True, alpha=clamp(kl * 4), scale=lerp(3.0, 1.0, ease_out_expo(kl)) * bump)
    ksub = ease_out_cubic(prog(lt, BEAT, 0.3))
    sub = TL.COPY["end_sub"]
    text(c, sub, W / 2, 960 * U + (1 - ksub) * 30 * U, size=fit(sub, REGULAR, W * 0.8, 48 * U, 0.2), font=REGULAR,
         fill=WHITE, alpha=ksub, tracking=0.2)
    kb = ease_out_back(prog(lt, 2 * BEAT, 0.35))           # SHOP NOW pops, finger taps on beat 4
    by, bh = 1050 * U, 120 * U
    if kb > 0:
        press = lt >= 4 * BEAT
        bw = 500 * U * kb
        sq = 0.94 if press and lt < 4 * BEAT + 0.1 else 1.0
        c.save()
        c.translate(W / 2, by + bh / 2)
        c.scale(sq, sq)
        rect(c, -bw / 2, -bh / 2, bw, bh, RED if press else WHITE)
        text(c, TL.COPY["cta"], 0, 0, size=46 * U * kb, font="body", fill=WHITE if press else BLACK, tracking=0.12)
        c.restore()
        fk = ease_out_cubic(prog(lt, 4 * BEAT - 0.4, 0.35))
        if 4 * BEAT - 0.4 < lt < 5.5 * BEAT:
            fx, fy = lerp(W * 0.85, W / 2 + 150 * U, fk), lerp(H * 0.85, by + bh / 2, fk)
            c.drawCircle(fx, fy, 36 * U, fpaint(skia.Color(255, 255, 255, 110)))
            c.drawCircle(fx, fy, 36 * U, fpaint(WHITE, stroke=4 * U))
        d = lt - 4 * BEAT
        if 0 <= d < 0.5:
            r = lerp(40, 220, ease_out_cubic(d / 0.5)) * U
            c.drawCircle(W / 2 + 150 * U, by + bh / 2, r, fpaint(with_alpha(RED, 0.85 * (1 - d / 0.5)), stroke=6 * U))
    km = ease_out_cubic(prog(lt, 5 * BEAT, 0.3))             # member offer + payments, like the footer
    if km > 0:
        text(c, TL.COPY["member"], W / 2, 1250 * U, size=fit(TL.COPY["member"], REGULAR, W * 0.84, 34 * U),
             font=REGULAR, fill=WHITE, alpha=km)
        mc = TL.COPY["member_cta"]
        mw = text_width(mc, 30 * U, REGULAR)
        text(c, mc, W / 2, 1305 * U, size=30 * U, font=REGULAR, fill=WHITE, alpha=km)
        rect(c, W / 2 - mw / 2, 1325 * U, mw, 2 * U, with_alpha(WHITE, km))
        payments(c, W / 2, 1400 * U, 52 * U, alpha=km)
        text(c, TL.COPY["url"], W / 2, 1470 * U, size=28 * U, font=REGULAR, fill=NAVGREY, alpha=km, tracking=0.05)


SCENES = {"hook": s_hook, "problem": s_problem, "reveal": s_reveal, "app": s_app, "montage": s_montage,
          "outfit": s_outfit, "endcard": s_endcard}


def draw(c, t):
    name, lt, dur = TL.scene_at(t)
    dx, dy = shake_offset(t)
    c.save()
    c.translate(dx, dy)
    SCENES[name](c, t, lt, dur)
    c.restore()
    flash(c, t)


def build_audio():
    Path("work").mkdir(exist_ok=True)
    ak.write_wav("work/music.wav", ak.music_bed(TL.MOOD, seconds=TL.DURATION, bpm=TL.BPM, intro_bars=0))
    Path("work/cues.json").write_text(json.dumps(TL.cues(), indent=1))
    import subprocess
    subprocess.run([sys.executable, "vibe/audio_kit.py", "mix", "work/cues.json", "-o", "work/mix.wav"], check=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stills"
    if cmd == "stills":
        times = [float(x) for x in sys.argv[2:]] or [s + (e - s) * 0.6 for s, e, _ in TL.SCENES]
        S.stills(draw, times)
    elif cmd == "audio":
        build_audio()
    elif cmd == "draft":
        S.render(draw, "out/draft.mp4", audio="work/mix.wav", draft=True)
    elif cmd == "render":
        if not Path("work/mix.wav").exists():
            build_audio()
        suffix = f"_{TL.W}x{TL.H}" if os.environ.get("VIBE_SIZE") else ""
        S.render(draw, f"out/hm-ad_v3{suffix}.mp4", audio="work/mix.wav")
    else:
        sys.exit(__doc__)
