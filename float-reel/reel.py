"""Vibe Editing System ad, re-edited in the "floating UI" style of the reference reel.

    python3 reel.py stills 1.0 4.2 ...    -> out/stills/*.png  (half res)
    python3 reel.py render [--draft]      -> out/vibe_float_reel.mp4

Same take, cut list and word clock as ../sticker-reel (cut.py, words.json, matte); a new look: moody graded room,
app-UI components floating above the speaker and acting out each line, two-tier captions (white handwritten caps
over a wide italic yellow keyword with a scribble), everything cued to the spoken words.
"""

import math
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import cv2
import numpy as np
import skia

HERE = Path(__file__).resolve().parent
SR_DIR = HERE.parent / "sticker-reel"
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(SR_DIR))
import cut  # noqa: E402
import edit as SK  # noqa: E402  (the paper-sticker edit: phrases, sections, camera, source frames)
from style import (BLUE, GREEN, GREYUI, INK, LAV, LIME, PURPLE, RED, SAMP, WHITE, YEL, card, clamp, e_in,  # noqa: E402
                   e_io, e_out, fill, float_in, font, glyph_draw, hrand, icon_button, kit, lerp, measure, pill,
                   prog, rrect, scribble, segmented, slider, soft_shadow, spring, star, stroke, text, toggle,
                   toggle_row, wave_pill)

W, H, FPS = 1080, 1920, 30
OUT = HERE / "out"
SHIFT = 170                                  # the shot sits lower than in the take, for headroom like the reference
FACE = (SK.FACE[0], SK.FACE[1] + SHIFT)
HEAD_TOP = SK.HEAD_TOP + SHIFT
TOTAL = SK.TOTAL
P = {k: getattr(SK, k) for k in dir(SK) if isinstance(getattr(SK, k), cut.P)}
globals().update(P)
EVERY, FORMATS = SK.EVERY, SK.FORMATS
SEC = SK.SEC
section = SK.section
DROP = SK.DROP
END_A = SK.END_A


# ================================================================== footage: moody grade, shifted down
def _lut():
    x = np.arange(256, dtype=np.float32) / 255
    s = x + 0.10 * np.sin(2 * math.pi * (x - 0.5)) * (1 - np.abs(2 * x - 1))
    r = np.clip(0.03 + s * 0.97 * 1.02, 0, 1)
    g = np.clip(0.035 + s * 0.96, 0, 1)
    b = np.clip(0.05 + s * 0.92, 0, 1)
    return [(c * 255).astype(np.uint8) for c in (r, g, b)]


LUT = _lut()
_VIG = None


def moody(rgb, alpha, kind="moody"):
    """cool desaturated grade; the room drops a stop and goes grey-teal, the speaker keeps his light."""
    global _VIG
    o = np.empty_like(rgb)
    for ch in range(3):
        o[..., ch] = LUT[ch][rgb[..., ch]]
    f = o.astype(np.float32)
    lum = f @ np.array([0.299, 0.587, 0.114], np.float32)
    sat = {"moody": 0.8, "old": 0.55, "cine": 0.72}[kind]
    f = lum[..., None] + (f - lum[..., None]) * sat
    if _VIG is None:
        yy, xx = np.mgrid[0:H:4, 0:W:4].astype(np.float32)
        r = np.sqrt(((xx - SK.FACE[0]) / 700) ** 2 + ((yy - SK.FACE[1] + 60) / 1050) ** 2)
        _VIG = cv2.resize(np.clip(1.1 - 0.75 * r, 0.3, 1.0), (W, H))[..., None]
    a = alpha.astype(np.float32)[..., None] / 255
    depth = {"moody": 0.52, "old": 0.6, "cine": 0.36}[kind]
    wall = f * depth * _VIG * np.array([0.9, 0.98, 1.06], np.float32)
    person = f * np.array([1.02, 1.0, 0.98], np.float32)
    return np.clip(wall * (1 - a) + person * a, 0, 255).astype(np.uint8)


class Shot:
    """one source frame, graded and shifted: plate (whole frame) + person cut-out (for layering in front)."""

    def __init__(self, ts, kind="moody"):
        self.fi = int(round(ts * FPS))
        a_small = SK.alpha_small(self.fi)
        a = cv2.resize(a_small, (W, H), interpolation=cv2.INTER_LINEAR)
        g = moody(SK.frame_rgb(self.fi), a, kind)
        rgb = np.empty_like(g)
        rgb[SHIFT:] = g[:H - SHIFT]
        ext = np.flipud(g[:SHIFT])
        rgb[:SHIFT] = cv2.GaussianBlur(ext, (0, 0), 18)
        al = np.zeros((H, W), np.uint8)
        al[SHIFT:] = a[:H - SHIFT]
        self.rgb, self.al = rgb, al

    def plate(self):
        return skia.Image.fromarray(np.dstack([self.rgb, np.full((H, W), 255, np.uint8)]),
                                    colorType=skia.kRGBA_8888_ColorType)

    def person(self):
        return skia.Image.fromarray(np.dstack([self.rgb, self.al]), colorType=skia.kRGBA_8888_ColorType)


def shot_kind(t):
    s = section(t)
    return "old" if s in ("years", "old") else "cine" if s == "cine" else "moody"


def apply_cam(c, cam):
    z, dx, dy, rot = cam
    c.translate(FACE[0] + dx, FACE[1] + dy)
    c.rotate(rot)
    c.scale(z, z)
    c.translate(-FACE[0], -FACE[1])


def head_top(cam):
    z, dx, dy, rot = cam
    return FACE[1] + dy - (FACE[1] - HEAD_TOP) * z


UI_LOG = set()          # every element's pop-in time (the sound pass puts a pop on each)


@contextmanager
def ui(c, t, t0, x, y, seed=0, t_out=None, scale=1.0, bob=6.0):
    UI_LOG.add(round(t0, 3))
    c.save()
    a = float_in(c, t, t0, x, y, seed, scale, t_out, bob=bob)
    try:
        yield a
    finally:
        c.restore()


# ================================================================== captions: handwritten caps + wide yellow keyword
ACC = SK.ACC


def _groups():
    groups, cur = [], []
    for i, w in enumerate(SK.WORDS):
        if cur and (len(cur) >= 5 or w["os"] - cur[-1]["oe"] > 0.3 or cur[-1]["p"]
                    or (cur[-1]["i"] in ACC and w["i"] not in ACC)):
            groups.append(cur)
            cur = []
        cur.append(w)
    groups.append(cur)
    out = []
    for i, g in enumerate(groups):
        nxt = groups[i + 1][0]["os"] if i + 1 < len(groups) else TOTAL
        out.append(dict(words=g, s=g[0]["os"] - 0.04, e=min(nxt - 0.03, g[-1]["oe"] + 0.6)))
    return out


GROUPS = _groups()
CAP_OFF = SK.CAP_OFF


def draw_captions(c, t, cam):
    if SK.in_any(t, CAP_OFF):
        return
    g = next((g for g in GROUPS if g["s"] <= t < g["e"]), None)
    if g is None:
        return
    punchy = PUNCHY.s - 0.05 <= t < PUNCHY.e + 0.4
    plain = [w for w in g["words"] if w["i"] not in ACC]
    key = [w for w in g["words"] if w["i"] in ACC]
    base = min(800, head_top(cam) - 50)
    ko = e_in(clamp((t - (g["e"] - 0.1)) / 0.1))
    sh = (1 - ko)
    if key:
        ks = " ".join(w["d"] for w in key).upper()
        size = 150 if punchy else 128
        kw = measure(ks, "wide", size)
        if kw > 960:
            size *= 960 / kw
            kw = 960
        k = t - key[0]["os"] + 0.03
        if k > 0:
            sp = spring(k, w=22 if punchy else 18, z=0.4 if punchy else 0.5)
            c.save()
            c.translate(W / 2, base - size * 0.35 - ko * 20)
            sc = (1.5 if punchy else 1.25) - (0.5 if punchy else 0.25) * min(1.0, sp)
            c.scale(sc, sc)
            c.translate(-kw / 2, size * 0.35)
            al = clamp(k / 0.05) * sh
            c.drawString(ks, 4, 6, font("wide", size), fill("#000000", 0.35 * al, blur=10))
            c.drawString(ks, 0, 0, font("wide", size), fill(YEL, al))
            c.restore()
            scribble(c, W / 2 + 20, base + 26 - ko * 20, kw * 0.62, prog(t, key[0]["os"] + 0.08, 0.3), INK, 8,
                     seed=g["s"], a=0.9 * sh)
            if key[0]["k"] == "edit" and DONTEDIT.s <= key[0]["os"] < DONTEDIT.e:
                kk = prog(t, key[0]["oe"], 0.22)
                c.drawLine(W / 2 - kw / 2 - 10, base - size * 0.32, W / 2 - kw / 2 - 10 + (kw + 20) * kk,
                           base - size * 0.36, stroke(RED, 14, sh))
        pbase = base - size * 0.95
        psize = 70
    else:
        pbase, psize = base - 10, 96 if not punchy else 110
    if plain:
        ps = " ".join(w["d"] for w in plain).upper()
        pw = measure(ps, "hand", psize)
        if pw > 960:
            psize *= 960 / pw
            pw = 960
        x = W / 2 - pw / 2
        for w in plain:
            s = w["d"].upper()
            ww = measure(s + " ", "hand", psize)
            k = t - w["os"] + 0.03
            if k > 0:
                sp = spring(k, w=20, z=0.55)
                al = clamp(k / 0.05) * sh
                yy = pbase + (1 - min(1.0, sp)) * 18 - ko * 20
                c.drawString(s, x + 2, yy + 3, font("hand", psize), fill("#000000", 0.4 * al, blur=6))
                c.drawString(s, x, yy, font("hand", psize), fill(WHITE, al))
            x += ww


def title_behind(c, t):
    if not TITLE.s - 0.02 <= t < TITLE.e + 0.25:
        return
    k = t - TITLE.w(2) + 0.05
    if k < 0:
        return
    sp = spring(k, w=16, z=0.45)
    a = clamp(k / 0.06) * (1 - clamp((t - TITLE.e - 0.1) / 0.15))
    s = 250
    w = measure("TITLE", "wide", s)
    c.save()
    c.translate(W / 2, 930)
    c.scale(0.6 + 0.4 * sp, 0.6 + 0.4 * sp)
    c.drawString("TITLE", -w / 2 + 6, 8, font("wide", s), fill("#000000", 0.4 * a, blur=14))
    c.drawString("TITLE", -w / 2, 0, font("wide", s), fill(YEL, a))
    c.restore()
    text(c, "THE", W / 2, 700, "hand", 90, WHITE, a * clamp(k / 0.1), anchor="c", shadow=True)


# ================================================================== UI per section (the band above his head)
def g_hook(c, t):
    t0, to = HOOK.w(3) - 0.05, YEARS.s - 0.15
    items = [
        (150, 290, lambda a: icon_button(c, 44, GREEN, "battery", a, k=prog(t, t0, 0.8))),
        (255, 290, lambda a: icon_button(c, 44, PURPLE, "speaker", a)),
        (360, 290, lambda a: icon_button(c, 44, "#5E6166", "lock", a)),
        (205, 395, lambda a: toggle(c, e_io(prog(t, NOTICED.w(4), 0.25)), a=a)),
        (240, 500, lambda a: slider(c, 0.2 + 0.7 * e_io(prog(t, t0 + 0.3, 1.2)), 300, 74, a)),
        (560, 290, lambda a: pill(c, 270, 72, INK, "Continue", a=a, glass=True)),
        (560, 395, lambda a: (icon_button(c, 44, LAV, "dots", a, fg=PURPLE))),
        (560, 500, lambda a: pill(c, 290, 74, GREEN, "Continue", INK, a=a, arrow=True)),
        (860, 335, lambda a: card(c, 270, 170, LIME, "Just changed", "most people\nhaven't noticed", a, plus=True)),
        (860, 525, lambda a: card(c, 270, 130, LAV, "", "", a, shape="sun", t=t)),
    ]
    for i, (x, y, fn) in enumerate(items):
        with ui(c, t, t0 + i * 0.045, x, y, i, to) as a:
            if a:
                fn(a)


def g_years(c, t):
    yr = int(lerp(2009, 2025, e_io(prog(t, YEARS.s, 1.2))))
    with ui(c, t, YEARS.s, 540, 420, 1, SIT.s - 0.15) as a:
        if a:
            pill(c, 430, 96, "#16171A", "", a=a)
            c.save()
            c.translate(-150, 0)
            icon_button(c, 34, YEL, "clock", a, fg=INK, k=t * 0.8)
            c.restore()
            text(c, f"since {yr}", 30, 14, "uib", 40, WHITE, a, anchor="c")


def timeline_ui(c, t, a):
    w, h = 900, 240
    r = rrect(-w / 2, -h / 2, w, h, 24)
    soft_shadow(c, r.rect(), a, 24)
    c.drawRRect(r, fill("#16171A", 0.95 * a))
    text(c, "Timeline", -w / 2 + 26, -h / 2 + 38, "uib", 24, WHITE, a)
    text(c, "00:00:47:12", w / 2 - 26, -h / 2 + 38, "mono", 22, GREYUI, a, anchor="r")
    rows = [LAV, BLUE, GREEN, YEL]
    for ri, colr in enumerate(rows):
        yy = -h / 2 + 62 + ri * 40
        xs = -w / 2 + 26
        for j in range(10):
            cw = 40 + 60 * hrand(ri, j)
            off = 0.0
            if ri == 1 and j == 3 and t >= DRAG.s:
                off = 130 * e_io(prog(t, DRAG.s, 0.55)) - 130
            c.drawRRect(rrect(xs + off, yy, cw, 30, 8), fill(colr, 0.9 * a))
            xs += cw + 6
            if xs > w / 2 - 70:
                break
    if t >= KEYS.s:
        for j in range(11):
            tk = KEYS.s + j * 0.06
            if t < tk:
                continue
            k = spring(t - tk, w=26, z=0.45)
            c.save()
            c.translate(-w / 2 + 80 + j * 72, -h / 2 + 77 + (j % 2) * 40)
            c.rotate(45)
            c.scale(k, k)
            c.drawRect(skia.Rect(-10, -10, 10, 10), fill(WHITE, a))
            c.restore()
    ph = -w / 2 + 40 + ((t * 140) % (w - 80))
    c.drawLine(ph, -h / 2 + 52, ph, h / 2 - 12, stroke(RED, 3, a))


def g_old(c, t):
    to = SEC["old"][1] - 0.15
    with ui(c, t, SIT.w(4) - 0.05, 540, 400, 2, to, bob=3) as a:
        if a:
            timeline_ui(c, t, a)
    if t >= HOURS.w(2):
        hrs = 6 * e_io(prog(t, HOURS.w(2), 0.9))
        with ui(c, t, HOURS.w(2), 300, 568, 3, to) as a:
            if a:
                pill(c, 300, 66, "#16171A", "", a=a)
                c.save()
                c.translate(-110, 0)
                glyph_draw(c, "clock", 26, YEL, a, k=hrs)
                c.restore()
                text(c, f"{int(hrs):02d}:{int(hrs % 1 * 60):02d}:00 hrs", 22, 11, "mono", 28, WHITE, a, anchor="c")
    with ui(c, t, REEL60.w(3), 790, 568, 4, to) as a:
        if a:
            pill(c, 230, 66, LAV, "", a=a)
            c.save()
            c.translate(-72, 0)
            glyph_draw(c, "phone", 26, INK, a)
            c.restore()
            text(c, "0:60 reel", 20, 11, "uib", 28, INK, a, anchor="c")


def g_flip(c, t):
    to = SEC["flip"][1] - 0.15
    with ui(c, t, FLIPS.w(2) - 0.05, 540, 300, 5, to) as a:
        if a:
            c.scale(1.2, 1.2)
            toggle(c, e_io(prog(t, FLIPS.w(2) + 0.05, 0.25)), a=a)
    with ui(c, t, DONTEDIT.s - 0.05, 540, 440, 6, to) as a:
        if a:
            segmented(c, ["EDIT", "DIRECT"], e_io(prog(t, DIRECT.w(1) - 0.05, 0.3)), 600, 104, a, size=40)
    if t >= DIRECT.w(1):
        with ui(c, t, DIRECT.w(1) + 0.1, 860, 300, 7, to) as a:
            if a:
                icon_button(c, 44, GREEN, "check", a, fg=INK)


ROWS = [("Cut the pauses", CUTP), ("Punchy captions", PUNCHY), ("Title behind me", TITLE),
        ("Cinematic look", CINE), ("Music that builds", MUSIC)]
SLOTS = [300, 400, 500]


def g_brief(c, t):
    """prompt box, then one toggle row per instruction: appears as it's said, switches on as it happens."""
    t_in = TELL.s - 0.05
    if not t_in <= t < DROP + 0.5:
        return
    if t < ROWS[0][1].s + 0.1:
        n = int(clamp((t - TELL.s) / (BRIEF.e - TELL.s)) * 30)
        msg = "edit it like a top editor would"[:n]
        with ui(c, t, t_in, 540, 330, 8, ROWS[0][1].s - 0.1) as a:
            if a:
                r = rrect(-440, -52, 880, 104, 52)
                soft_shadow(c, r.rect(), a, 52)
                c.drawRRect(r, fill("#16171A", 0.95 * a))
                if msg:
                    text(c, msg, -400, 13, "ui", 34, WHITE, a)
                    if (t * 3) % 1 < 0.6:
                        cx = -400 + measure(msg, "ui", 34) + 4
                        c.drawRect(skia.Rect(cx, -20, cx + 3, 20), fill(GREEN, a))
                else:
                    text(c, "Tell the system what you want...", -400, 13, "ui", 34, GREYUI, a)
                c.save()
                c.translate(388, 0)
                icon_button(c, 36, GREEN if msg else "#3A3D42", "arrow", a, fg=INK)
                c.restore()
    shown = [i for i, (lab, ph) in enumerate(ROWS) if t >= ph.s - 0.05]
    if not shown:
        return
    last_t = ROWS[shown[-1]][1].s - 0.05
    sc = lerp(max(0, len(shown) - 4), max(0, len(shown) - 3), e_io(prog(t, last_t, 0.3)))
    burst = prog(t, DROP, 0.35)
    for i in shown:
        lab, ph = ROWS[i]
        slot = i - sc
        if slot < -0.95:
            continue
        y = 300 + slot * 100
        on = e_io(prog(t, ph.e + 0.08, 0.22))
        fade = clamp(slot + 1)
        with ui(c, t, ph.s - 0.05, 540, y, 10 + i, None, scale=1 + 0.25 * burst, bob=2) as a:
            if a:
                toggle_row(c, lab, on, 620, 86, a * fade * (1 - burst))


def g_lower(c, t):
    """the lower band (over the torso): the snip, the music meter."""
    if CUTP.s <= t < CUTP.e + 0.5:
        with ui(c, t, CUTP.w(2), 760, 1430, 20, CUTP.e + 0.3) as a:
            if a:
                pill(c, 280, 72, RED, "pause  -0.4s", WHITE, a=a, size=28)
    if MUSIC.s <= t < DROP + 0.05:
        energy = lerp(0.3, 1.0, prog(t, MUSIC.s, DROP - MUSIC.s))
        with ui(c, t, MUSIC.s, 540, 1450, 21, DROP - 0.05) as a:
            if a:
                wave_pill(c, t, 640, 110, energy, a)
        with ui(c, t, MUSIC.w(2), 540, 1560, 22, DROP - 0.05) as a:
            if a:
                slider(c, prog(t, MUSIC.w(2), DROP - MUSIC.w(2)), 420, 70, a, "BUILD")


def g_cine(c, t):
    k = e_out(prog(t, SEC["cine"][0], 0.3)) * (1 - e_in(prog(t, SEC["cine"][1] - 0.2, 0.2)))
    bh = 220 * k
    c.drawRect(skia.Rect(0, 0, W, bh), fill("#030303"))
    c.drawRect(skia.Rect(0, H - bh, W, H), fill("#030303"))


def g_drop(c, t):
    if DROP <= t < DROP + 0.12:
        c.drawRect(skia.Rect(0, 0, W, H), fill(WHITE, 0.8 * (1 - (t - DROP) / 0.12)))
    if DROP <= t < DROP + 1.4:
        k = t - DROP
        for i in range(34):
            ang = hrand(5, i) * 2 * math.pi
            sp = 500 + 1200 * hrand(6, i)
            x = W / 2 + math.cos(ang) * sp * k
            y = 520 + math.sin(ang) * sp * k + 700 * k * k
            a = clamp(1.4 - k)
            colr = [YEL, LIME, LAV, GREEN, WHITE][i % 5]
            if i % 3 == 0:
                star(c, x, y, 18, colr, 4, 0.35, a=a)
            elif i % 3 == 1:
                c.drawCircle(x, y, 12, fill(colr, a))
            else:
                c.drawRRect(rrect(x - 20, y - 9, 40, 18, 9), fill(colr, a))


def g_every(c, t):
    to = SEC["every"][1] - 0.15
    icons = [(GREEN, "scissors", INK), (WHITE, "cc", INK), (PURPLE, "sparkle", WHITE), (BLUE, "speaker", WHITE)]
    lap = LAPTOP.w(2) - 0.05
    for i, (ph, (colr, gl, fg)) in enumerate(zip(EVERY, icons)):
        with ui(c, t, ph.w(1) - 0.03, 270 + i * 180, 300, 30 + i, min(to, lap)) as a:
            if a:
                icon_button(c, 62, colr, gl, a, fg=fg)
    with ui(c, t, lap, 540, 300, 34, to) as a:
        if a:
            pill(c, 520, 100, GREEN, "", a=a)
            c.save()
            c.translate(-190, 0)
            glyph_draw(c, "laptop", 40, INK, a)
            c.restore()
            text(c, "Runs on your laptop", 40, 13, "uib", 36, INK, a, anchor="c")
    with ui(c, t, CODE.s - 0.05, 540, 480, 35, to, bob=3) as a:
        if a:
            w, h = 820, 200
            r = rrect(-w / 2, -h / 2, w, h, 24)
            soft_shadow(c, r.rect(), a, 24)
            c.drawRRect(r, fill("#121316", 0.96 * a))
            for i, d in enumerate([RED, YEL, GREEN]):
                c.drawCircle(-w / 2 + 30 + i * 26, -h / 2 + 26, 8, fill(d, a))
            text(c, "vibe.py", w / 2 - 24, -h / 2 + 34, "mono", 22, GREYUI, a, anchor="r")
            lines = [("cut", "(pauses)"), ("captions", ".punch()"), ("title", ".behind(me)"), ("music", ".build()")]
            for i, (fn, rest) in enumerate(lines):
                ts = CODE.s + i * 0.26
                if t < ts:
                    continue
                full = fn + rest
                n = int(clamp((t - ts) / 0.24) * len(full) + 0.999)
                x = -w / 2 + 30
                y = -h / 2 + 76 + i * 36
                s1 = full[:min(n, len(fn))]
                x += text(c, s1, x, y, "mono", 28, LIME, a)
                if n > len(fn):
                    text(c, full[len(fn):n], x, y, "mono", 28, WHITE, a)


FORMAT_CARDS = [("Motion graphics", LIME, INK), ("Product ads", LAV, INK), ("Claymation", "#FF9F6B", INK),
                ("VFX", "#16171A", WHITE), ("Podcast clips", GREEN, INK)]
FORMAT_POS = [(220, 430), (540, 430), (860, 430), (380, 540), (700, 540)]


def g_formats(c, t):
    to = SEC["formats"][1] - 0.12
    sel = 0.0
    for i, ph in enumerate(FORMATS):
        sel = lerp(sel, i + 1, e_io(prog(t, ph.s - 0.05, 0.22)))
    with ui(c, t, NOTJUST.w(4) - 0.1, 540, 305, 40, to) as a:
        if a:
            segmented(c, ["Reels", "Motion", "Ads", "Clay", "VFX", "Pods"], sel, 940, 76, a, size=24)
    for i, (ph, (lab, colr, fg), (x, y)) in enumerate(zip(FORMATS, FORMAT_CARDS, FORMAT_POS)):
        with ui(c, t, ph.s - 0.04, x, y, 41 + i, to) as a:
            if a:
                card(c, 290, 96, colr, "", "", a, radius=22)
                text(c, lab, 0, 11, "uib", 30, fg, a, anchor="c")


def g_fifty(c, t):
    a0, a1 = SEC["fifty"]
    cols, rows, tw, th, gap = 10, 5, 84, 54, 8
    gx0 = (W - (cols * tw + (cols - 1) * gap)) / 2
    gy0 = 262
    kout = e_in(clamp((t - (a1 - 0.2)) / 0.2))
    n = int(clamp((t - a0 - 0.1) / 1.3) * 50 + 0.999)
    win = 27
    pal = [LIME, LAV, YEL, GREEN, "#FF9F6B", WHITE, BLUE, PURPLE]
    for i in range(min(n, 50)):
        r_, cc = divmod(i, cols)
        x, y = gx0 + cc * (tw + gap), gy0 + r_ * (th + gap)
        k = spring(t - (a0 + 0.1 + i * 1.3 / 50), w=24, z=0.5)
        dim = t >= TEST.w(3) and i != win
        c.save()
        c.translate(x + tw / 2, y + th / 2 - 300 * kout)
        c.scale(0.4 + 0.6 * k, 0.4 + 0.6 * k)
        aa = (0.35 if dim else 1.0) * (1 - kout)
        c.drawRRect(rrect(-tw / 2, -th / 2, tw, th, 10), fill(pal[i % 8], aa))
        c.drawRRect(rrect(-tw / 2 + 8, -th / 2 + 10, tw * 0.5, 7, 3), fill(INK, 0.5 * aa))
        c.drawRRect(rrect(-tw / 2 + 8, -th / 2 + 22, tw * 0.3, 7, 3), fill(INK, 0.3 * aa))
        c.restore()
    with ui(c, t, a0 + 0.1, 540, 1460, 50, a1 - 0.2) as a:
        if a:
            pill(c, 380, 76, "#16171A", f"Version {min(n, 50):02d} / 50", WHITE, a=a, size=32, name="uib")
    if t >= TEST.w(3):
        r_, cc = divmod(win, cols)
        x, y = gx0 + cc * (tw + gap) + tw / 2, gy0 + r_ * (th + gap) + th / 2 - 300 * kout
        k = e_out(prog(t, TEST.w(3), 0.3))
        c.drawRRect(rrect(x - tw / 2 - 6, y - th / 2 - 6, tw + 12, th + 12, 14), stroke(GREEN, 6, k * (1 - kout)))
        with ui(c, t, TEST.w(4), x, y - 70, 51, a1 - 0.2) as a:
            if a:
                pill(c, 260, 60, GREEN, "Best performer", INK, a=a, size=26, name="uib")


def g_need(c, t):
    to = SEC["need"][1] - 0.15
    with ui(c, t, NEED.w(5) - 0.05, 540, 420, 60, FOOTAGE.s - 0.1) as a:
        if a:
            icon_button(c, 80, LAV, "none", a, fg=PURPLE)
            text(c, "?", 0, 40, "wide", 120, INK, a, anchor="c")
    with ui(c, t, FOOTAGE.s - 0.1, 540, 425, 61, to, bob=3) as a:
        if a:
            w, h = 700, 300
            r = rrect(-w / 2, -h / 2, w, h, 30)
            soft_shadow(c, r.rect(), a, 30)
            c.drawRRect(r, fill(WHITE, 0.97 * a))
            text(c, "What you need", -w / 2 + 34, -h / 2 + 50, "uib", 28, GREYUI, a)
            for i, (lab, ph) in enumerate([("Your footage", FOOTAGE), ("Your laptop", YLAPTOP),
                                           ("Vibe Editing System", VES)]):
                if t < ph.s - 0.05:
                    continue
                yy = -h / 2 + 108 + i * 70
                k = e_io(prog(t, ph.e, 0.2))
                c.drawRRect(rrect(-w / 2 + 34, yy - 22, 44, 44, 12), fill(kit_mix("#E6E7EA", GREEN, k), a))
                if k > 0.3:
                    c.save()
                    c.translate(-w / 2 + 56, yy)
                    glyph_draw(c, "check", 26, INK, a)
                    c.restore()
                text(c, lab, -w / 2 + 100, yy + 13, "uib" if i == 2 else "ui", 38, INK, a)


def kit_mix(a, b, k):
    return "#%02x%02x%02x" % kit.mixc(a, b, k)


SKILLS_CH = ["Talking head", "Motion gfx", "Product ads", "Claymation", "VFX", "Bulk ads"]


def g_product(c, t):
    to = SEC["product"][1] - 0.15
    with ui(c, t, SKILLS.s - 0.05, 540, 320, 70, to, bob=3) as a:
        if a:
            w, h = 800, 150
            r = rrect(-w / 2, -h / 2, w, h, 34)
            soft_shadow(c, r.rect(), a, 34)
            c.drawRRect(r, fill("#121316", 0.97 * a))
            c.drawRRect(r, stroke(YEL, 2, 0.6 * a))
            text(c, "VIBE EDITING SYSTEM", 0, 4, "wide", 50, YEL, a, anchor="c")
            text(c, "by Ideabro Studio", 0, 52, "hand", 40, WHITE, a, anchor="c")
    for i, nm in enumerate(SKILLS_CH):
        x = [225, 540, 855][i % 3]
        y = 460 if i < 3 else 550
        with ui(c, t, SKILLS.w(2) + i * 0.08, x, y, 71 + i, to) as a:
            if a:
                done = t >= SHOWS.w(7) + i * 0.1
                pill(c, 280, 70, LIME if done else "#16171A", nm, INK if done else WHITE, a=a, size=28, name="uib")
    with ui(c, t, COURSE.w(2), 540, 1450, 77, to) as a:
        if a:
            pill(c, 460, 96, GREEN, "+ Full course", INK, a=a, arrow=True, size=36, name="uib")


NO_ROWS = [("After Effects", NOAE), ("Premiere Pro", NOPR), ("Keyframes", NOKF)]


def g_no(c, t):
    for i, (lab, ph) in enumerate(NO_ROWS):
        y = 330 + i * 110
        with ui(c, t, ph.s - 0.12, 540, y, 80 + i, None, scale=1.15, bob=2) as a:
            if a:
                k = 1 - e_io(prog(t, ph.w(1), 0.22))
                toggle_row(c, lab, k, 640, 92, a, on=GREEN)
                if k < 0.5:
                    c.save()
                    c.translate(-370, 0)
                    icon_button(c, 32, RED, "x", a * clamp((0.5 - k) * 4))
                    c.restore()
    if t >= NOKF.e:
        with ui(c, t, NOKF.e, 540, 1450, 84, None) as a:
            if a:
                pill(c, 420, 84, "#16171A", "0 apps needed", WHITE, a=a, size=34, name="uib")


def g_reveal(c, t, raw_k):
    to = END_A - 0.1
    with ui(c, t, WATCHED.s, 540, 300, 90, to) as a:
        if a:
            segmented(c, ["RAW", "EDITED"], 1 - raw_k, 460, 84, a, size=32)
    with ui(c, t, NOAPP.w(5) - 0.05, 540, 440, 91, RECORDED.s + 0.3) as a:
        if a:
            for j in range(3):
                c.save()
                c.translate(-130 + j * 130, 0)
                c.drawRRect(rrect(-48, -48, 96, 96, 24), fill(["#2A2C30", "#3A2A50", "#203040"][j], a))
                glyph_draw(c, ["play", "sparkle", "clock"][j], 30, WHITE, a)
                k = prog(t, NOAPP.w(5) + 0.15 + j * 0.08, 0.15)
                c.drawLine(-52, -52, -52 + 104 * k, -52 + 104 * k, stroke(RED, 9, a))
                c.restore()
    if raw_k > 0.5:
        with ui(c, t, RECORDED.w(2), 820, 1450, 92, REST.w(2)) as a:
            if a:
                pill(c, 220, 70, "#16171A", "", a=a)
                c.drawCircle(-60, 0, 13, fill(RED, a if (t * 2) % 1 < 0.6 else 0.3 * a))
                text(c, "REC", 20, 12, "uib", 32, WHITE, a, anchor="c")
    if t >= REST.w(4):
        for i in range(6):
            kk = t - REST.w(4) - i * 0.04
            if kk < 0:
                continue
            ang = i * 1.05 + 0.3
            x, y = 540 + 380 * math.cos(ang), 1000 + 520 * math.sin(ang)
            sc = spring(kk, w=20, z=0.4)
            star(c, x, y, 30 * sc, [YEL, LIME, WHITE][i % 3], 4, 0.3)


def g_end(c, t):
    k = t - END_A
    a1 = clamp((k - 0.05) / 0.1)
    text(c, "COMMENT", W / 2, 430, "hand", 110, WHITE, a1, anchor="c", shadow=True)
    if k > 0.25:
        sp = spring(k - 0.25, w=18, z=0.45)
        s = 230
        w = measure("VIBE", "wide", s)
        c.save()
        c.translate(W / 2, 600)
        sc = 1.3 - 0.3 * min(1.0, sp)
        c.scale(sc, sc)
        c.drawString("VIBE", -w / 2 + 6, 10, font("wide", s), fill("#000000", 0.4, blur=14))
        c.drawString("VIBE", -w / 2, 0, font("wide", s), fill(YEL))
        c.restore()
        scribble(c, W / 2 + 20, 660, w * 0.62, prog(t, END_A + 0.4, 0.35), INK, 9, seed=3)
    if k > 0.7:
        text(c, "& I'll send you the details", W / 2, 760, "hand", 54, WHITE, clamp((k - 0.7) / 0.2), anchor="c",
             shadow=True)


def g_end_front(c, t):
    k = t - END_A
    with ui(c, t, END_A + 0.8, 540, 1430, 95, None) as a:
        if a:
            r = rrect(-390, -50, 780, 100, 50)
            soft_shadow(c, r.rect(), a, 50)
            c.drawRRect(r, fill("#16171A", 0.96 * a))
            n = int(clamp((k - 1.1) / 0.5) * 4 + 0.999) if k > 1.1 else 0
            if n:
                text(c, "VIBE"[:n], -340, 13, "uib", 38, WHITE, a)
            else:
                text(c, "Add a comment...", -340, 12, "ui", 34, GREYUI, a)
            c.save()
            c.translate(338, 0)
            icon_button(c, 34, GREEN if k > 1.75 else "#3A3D42", "arrow", a, fg=INK)
            c.restore()
    with ui(c, t, END_A + 0.5, 540, 1545, 96, None) as a:
        if a:
            pill(c, 470, 64, LIME, "Vibe Editing System", INK, a=a, size=28, name="uib")


# ================================================================== the frame
UI = {"hook": g_hook, "years": g_years, "old": g_old, "flip": g_flip, "formats": g_formats, "fifty": g_fifty,
      "need": g_need, "product": g_product, "no": g_no}


def raw_amount(t):
    if section(t) != "reveal":
        return 0.0
    return e_io(prog(t, RECORDED.w(2) - 0.05, 0.12)) * (1 - e_io(prog(t, REST.w(2), 0.12)))


def draw(c, t, f):
    s = section(t)
    ts = SK.src_at(min(t, TOTAL))
    cam = SK.camera(t)
    if s in ("reveal", "end"):
        cam = (cam[0] * (1 + 0.012 * (t - SEC[s][0])), cam[1], cam[2], cam[3])
    raw_k = raw_amount(t)
    if raw_k > 0.5:                  # "I recorded it on my phone": the untouched take, no grade, no graphics
        img = SK.frame_rgb(int(round(ts * FPS)))
        c.drawImage(skia.Image.fromarray(np.dstack([img, np.full((H, W), 255, np.uint8)]),
                                         colorType=skia.kRGBA_8888_ColorType), 0, 0, SAMP)
        g_reveal(c, t, raw_k)
        return {"t": t, "raw": True}
    shot = Shot(ts, shot_kind(t))
    c.save()
    apply_cam(c, cam)
    c.drawImage(shot.plate(), 0, 0, SAMP)
    c.restore()
    # behind the speaker: UI band, captions, the big title
    if s == "end":
        g_end(c, t)
    else:
        UI.get(s, lambda c, t: None)(c, t)
        g_brief(c, t)
        g_every(c, t) if s == "every" else None
        if s == "reveal":
            g_reveal(c, t, raw_k)
        draw_captions(c, t, cam)
        title_behind(c, t)
    c.save()
    apply_cam(c, cam)
    c.drawImage(shot.person(), 0, 0, SAMP)
    c.restore()
    # in front: the lower band over the torso, the drop, the letterbox
    g_lower(c, t)
    if s == "end":
        g_end_front(c, t)
    if s == "cine":
        g_cine(c, t)
    g_drop(c, t)
    return {"t": t}


# ================================================================== post: zoom-blur transitions, vignette, grain
CUTS_FX = [SEC[k][0] for k in ("years", "flip", "brief", "every", "formats", "need", "product", "no", "reveal",
                               "end")]
_grain = None
_vig = {}


def post(rgb, g, f):
    global _grain
    t = g.get("t", f / FPS)
    out = rgb
    h, w = out.shape[:2]
    for T in CUTS_FX:                           # quick zoom-blur punch through each section change
        d = t - T
        if -0.1 <= d < 0.12:
            k = 1 - abs(d) / (0.1 if d < 0 else 0.12)
            z = 1 + 0.18 * k
            M = cv2.getRotationMatrix2D((w / 2, h * 0.45), 0, z)
            zoomed = cv2.warpAffine(out, M, (w, h), borderMode=cv2.BORDER_REFLECT)
            acc = zoomed.astype(np.float32)
            for j in (1, 2, 3):
                M2 = cv2.getRotationMatrix2D((w / 2, h * 0.45), 0, z * (1 + 0.035 * j * k))
                acc += cv2.warpAffine(out, M2, (w, h), borderMode=cv2.BORDER_REFLECT)
            out = np.clip(acc / 4, 0, 255).astype(np.uint8)
    if (h, w) not in _vig:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        _vig[(h, w)] = (1 - 0.28 * np.clip(r - 0.45, 0, None) ** 1.5)[..., None]
    if _grain is None or _grain[0].shape != (h // 2 + 1, w // 2 + 1):
        rng = np.random.default_rng(9)
        _grain = [rng.standard_normal((h // 2 + 1, w // 2 + 1)).astype(np.float32) for _ in range(6)]
    gr = np.repeat(np.repeat(_grain[f % 6], 2, 0), 2, 1)[:h, :w]
    o = out.astype(np.float32) * (_vig[(h, w)] if not g.get("raw") else 1.0) + gr[..., None] * 7.0
    return np.clip(o, 0, 255).astype(np.uint8)


FILM = kit.Film(draw, dur=TOTAL, fps=FPS, post=post, out_dir=str(OUT))


def finish(picture, audio, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(picture), "-i", str(audio), "-map", "0:v", "-map", "1:a",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-maxrate", "3300k", "-bufsize", "6600k",
                    "-pix_fmt", "yuv420p", "-profile:v", "high", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k",
                    "-ar", "48000", "-movflags", "+faststart", "-shortest", str(out)], check=True)
    print("->", out)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stills"
    if cmd == "stills":
        FILM.stills([float(x) for x in sys.argv[2:]])
    elif cmd == "render":
        pic = FILM.render(OUT / "picture.mp4")
        import score
        mix = score.build()
        finish(pic, mix, OUT / "vibe_float_reel.mp4")
    elif cmd == "audio":
        import score
        score.build()


if __name__ == "__main__":
    main()
