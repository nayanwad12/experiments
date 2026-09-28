"""'Vibe Editing' claymation promo — 30 s, 1080x1920, shot 'on 12s' (12 fps) like real stop-motion.

    python3 stopmo.py stills 1.2 5.3 ...   -> out/stills
    python3 stopmo.py                      -> out/claymation.mp4
"""

import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
import skia
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

from clay import (BLUSH, BLUSH_D, CREAM, H, ICE, INK, LIME, PERI, R, Set, W, backdrop, circle, clamp_, glyphs,
                  poly, ring, rrect, sparkle, star, union)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "vibe-editing-promo"))
import audio as A  # noqa: E402
import imageio_ffmpeg  # noqa: E402

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
OUT = os.path.join(HERE, "out")
FPS, SPS = 30, 12          # output fps, stop-motion steps per second
BPM = 120
BEAT = 60 / BPM
DUR = 30.0
DARK = (58, 54, 70)

SCENES = [
    (0.0, 4.0, "hook", BLUSH),
    (4.0, 8.0, "say", ICE),
    (8.0, 12.0, "build", LIME),
    (12.0, 14.0, "captions", PERI),
    (14.0, 16.0, "motion", BLUSH),
    (16.0, 18.0, "ads", ICE),
    (18.0, 20.0, "ai", DARK),
    (20.0, 25.0, "direct", PERI),
    (25.0, 30.0, "cta", CREAM),
]
S = {n: s for s, e, n, _ in SCENES}


# ------------------------------------------------------------------ stop-motion moves (evaluated on 12 fps steps)
def land(d):
    """squash & settle after touching down, d = seconds since landing."""
    if d < 0.09:
        return 1.2, 0.8
    if d < 0.17:
        return 0.93, 1.08
    return 1.0, 1.0


def hop(t, t0, i=0, dur=0.34, from_dy=520, height=260):
    if t < t0:
        return None
    k = (t - t0) / dur
    side = -1 if i % 2 else 1
    if k < 1:
        return (0, from_dy * (1 - k) - height * math.sin(math.pi * k), side * 25 * (1 - k), 0.9, 1.15,
                min(1, math.sin(math.pi * k) + (1 - k) * 0.5))
    sx, sy = land(t - t0 - dur)
    return 0, 0, 0, sx, sy, 0


def drop(t, t0, dur=0.3, from_dy=-1100):
    if t < t0:
        return None
    k = (t - t0) / dur
    if k < 1:
        return 0, from_dy * (1 - k) ** 2, 0, 0.88, 1.2, 1 - k
    sx, sy = land(t - t0 - dur)
    return 0, 0, 0, sx, sy, 0


def grow(t, t0):
    """blob-inflate scale steps."""
    if t < t0:
        return 0.0
    d = t - t0
    for lim, s in ((0.09, 0.45), (0.17, 1.18), (0.26, 0.94)):
        if d < lim:
            return s
    return 1.0


# ------------------------------------------------------------------ scenes
def s_hook(st, t):
    st.word("EDITING", 540, 560, 190, [PERI, LIME, INK, ICE], seed=10, anim=lambda i, n: hop(t, 0.1 + i * 0.11, i))
    st.word("TAKES", 540, 800, 130, [INK, PERI, LIME, ICE], seed=20, anim=lambda i, n: hop(t, 1.3 + i * 0.08, i))

    def melt(i, n):
        h = hop(t, 1.9 + i * 0.08, i)
        if h is None or t < 2.6:
            return h
        m = clamp_((t - 2.6 - i * 0.06) / 1.2) * (0.6 + 0.5 * R("melt", i).random())
        return 0, 150 * 0.36 * m, 0, 1 - 0.12 * m, 1 + m, 0

    st.word("FOREVER", 540, 1010, 150, [LIME, ICE, PERI, INK], seed=30, anim=melt)
    s = grow(t, 0.5)
    if s:
        cx, cy = 540, 1500
        st.obj(circle(250), INK, cx, cy, sx=s, sy=s, seed=40)
        st.obj(circle(212), CREAM, cx, cy, sx=s, sy=s, seed=41, shadow=False)
        for k in range(4):
            a = math.radians(k * 90)
            st.obj(rrect(22, 46, 10), INK, cx + math.cos(a) * 170 * s, cy + math.sin(a) * 170 * s, k * 90 + 90, s, s,
                   seed=42 + k, shadow=False)
        step = int(t * 12)
        for (L, wd, ang, sd) in ((170, 26, step * 36, 50), (110, 34, step * 3 + 60, 51)):
            a = math.radians(ang - 90)
            st.obj(rrect(wd, L, wd / 2), INK, cx + math.cos(a) * L / 2 * s, cy + math.sin(a) * L / 2 * s, ang, s, s,
                   seed=sd)
        st.obj(circle(30), LIME, cx, cy, sx=s, sy=s, seed=52)


BUBBLE = union(rrect(880, 320, 130), poly([(210, 110), (340, 260), (80, 150)], 14))


def s_say(st, t):
    st.word("JUST SAY:", 540, 420, 130, [INK, PERI, LIME], seed=60, anim=lambda i, n: hop(t, 0.1 + i * 0.07, i))
    if t < 2.5:
        s = grow(t, 0.3)
        if t >= 2.25:
            s *= 1.08 if t < 2.38 else 1.17
        if s:
            st.obj(BUBBLE, CREAM, 540, 830, sx=s, sy=s, seed=70)

            def typed(i, n):
                if t < 0.7 + i / 12 * 1.2:
                    return None
                g = grow(t, 0.7 + i / 12 * 1.2)
                return 0, 0, 0, g * s, g * s, 0

            st.word("make it pop", 540, 810, 104, [INK], seed=80, anim=typed, soft=5)
    else:  # POP! -> clay crumbs scatter
        d = t - 2.5
        cols = [PERI, LIME, INK, BLUSH_D, CREAM, ICE]
        for i in range(18):
            r = R("crumb", i)
            a = r.uniform(0, math.tau)
            sx0, sy0 = 540 + r.uniform(-380, 380), 830 + r.uniform(-120, 120)
            dist = r.uniform(250, 650) * (1 - math.exp(-d / 0.3))
            st.obj(circle(r.uniform(30, 58)), cols[i % 6], sx0 + math.cos(a) * dist, sy0 + math.sin(a) * dist * 1.4,
                   d * r.uniform(-300, 300), seed=90 + i, lift=max(0, 0.8 - d * 2))
        st.word("POP!", 540, 1000, 300, [LIME, PERI, BLUSH_D, INK], seed=110,
                anim=lambda i, n: (lambda g: (0, 0, (-8, 6, -4, 10)[i], g, g, 0) if g else None)(grow(t, 2.6 + i * 0.07)))


def s_build(st, t):
    cols = [PERI, INK, BLUSH_D, CREAM, ICE]
    if t < 0.8:  # crumbs roll back in and merge
        for i in range(12):
            r = R("back", i)
            a = r.uniform(0, math.tau)
            k = (t / 0.8) ** 1.5
            st.obj(circle(r.uniform(30, 55)), cols[i % 5], 540 + math.cos(a) * 900 * (1 - k),
                   1150 + math.sin(a) * 1100 * (1 - k), t * 400, seed=120 + i)
    s = grow(t, 0.75)
    if s:
        st.obj(rrect(540, 960, 86), INK, 540, 1170, sx=s, sy=s, seed=130)
        g = grow(t, 0.95)
        if g:
            st.obj(rrect(470, 860, 60), PERI, 540, 1170, sx=g, sy=g, seed=131, shadow=False)
        g = grow(t, 1.15)
        if g:
            st.obj(circle(96), LIME, 540, 1110, sx=g, sy=g, seed=132)
            st.obj(poly([(-32, -46), (52, 0), (-32, 46)], 10), CREAM, 550, 1110, sx=g, sy=g, seed=133)
        g = grow(t, 1.45)
        if g:
            st.obj(rrect(360, 64, 32), CREAM, 540, 1420, sx=g, sy=g, seed=134)
            st.obj(rrect(220, 64, 32), LIME, 490, 1510, sx=g, sy=g, seed=135)
    st.word("VIBE", 540, 330, 250, [PERI, INK, BLUSH_D, ICE], seed=140, anim=lambda i, n: drop(t, 1.6 + i * 0.1))
    st.word("EDITING", 540, 565, 170, [INK, PERI, ICE, BLUSH_D], seed=150, anim=lambda i, n: drop(t, 2.1 + i * 0.08))


def s_captions(st, t):
    st.word("CAPTIONS", 540, 380, 150, [INK, LIME, CREAM, ICE], seed=160, anim=lambda i, n: hop(t, 0.02 + i * 0.05, i))
    s = grow(t, 0.0)
    st.obj(rrect(480, 820, 70), INK, 540, 1120, sx=s, sy=s, seed=170)
    st.obj(rrect(416, 750, 50), ICE, 540, 1120, sx=s, sy=s, seed=171, shadow=False)
    st.obj(circle(112), BLUSH, 540, 1020, sx=s, sy=s, seed=172)
    for ex in (-40, 40):
        st.obj(circle(12), INK, 540 + ex, 1000, seed=173 + ex, shadow=False)
    st.obj(rrect(60, 14 + 26 * (int(t * 12) % 2), 10), INK, 540, 1070, seed=175, shadow=False)
    for word, x, w_, col, t0 in (("SO", 440, 150, LIME, 0.5), ("EASY", 625, 240, CREAM, 0.9)):
        g = grow(t, t0)
        if g:
            st.obj(rrect(w_, 88, 44), col, x, 1300, sx=g, sy=g, seed=176 + len(word))
            st.word(word, x, 1300, 58, [INK], seed=180 + len(word), soft=4,
                    anim=lambda i, n, g=g: (0, 0, 0, g, g, 0))


def s_motion(st, t):
    def wave(i, n):
        h = hop(t, 0.02 + i * 0.05, i)
        if h is None or t < 0.5:
            return h
        d = (t - 0.5 - i * 0.04) % BEAT
        up = -90 * math.sin(math.pi * d / 0.25) if d < 0.25 else 0
        sx, sy = land(d - 0.25) if d >= 0.25 else (0.92, 1.1)
        return 0, up, 0, sx, sy, max(0, -up / 90)

    st.word("MOTION", 540, 380, 180, [PERI, LIME, INK, ICE], seed=200, anim=wave)
    shapes = [(circle(90), LIME, 220), (rrect(170, 170, 40), PERI, 540), (poly([(0, -100), (95, 70), (-95, 70)], 16),
                                                                          ICE, 860)]
    for k, (p, col, x) in enumerate(shapes):
        g = grow(t, 0.15 + k * 0.1)
        d = (t - k * BEAT / 3) % BEAT
        up = -160 * math.sin(math.pi * d / 0.3) if d < 0.3 else 0
        sx, sy = land(d - 0.3) if d >= 0.3 else (0.9, 1.12)
        st.obj(p, col, x, 1150 + up, rot=t * 90 * (1 if k % 2 else -1), sx=g * sx, sy=g * sy, seed=210 + k,
               lift=max(0, -up / 160))
    g = grow(t, 0.5)
    if g:
        st.obj(ring(130, 62), INK, 540, 1560, rot=t * 60, sx=g, sy=g, seed=220)


def s_ads(st, t):
    st.word("ADS", 540, 400, 320, [INK, PERI, LIME], seed=230, anim=lambda i, n: drop(t, 0.02 + i * 0.08))
    s = grow(t, 0.15)
    if s:
        rot = (-7 if int(t / BEAT) % 2 else 7) if t > 0.5 else 0
        m = skia.Matrix()
        m.setRotate(rot)

        def part(p, col, lx, ly, seed, shadow=True):
            x, y = m.mapXY(lx * s, ly * s)
            st.obj(p, col, 470 + x, 1230 + y, rot, s, s, seed=seed, shadow=shadow)

        part(rrect(300, 560, 96), PERI, 0, 0, 240)
        part(rrect(130, 130, 30), PERI, 0, -330, 241)
        part(rrect(176, 92, 26), INK, 0, -420, 242)
        part(rrect(300, 210, 20), CREAM, 0, 40, 243, shadow=False)
        gl, _ = glyphs("GLOW", 80)
        for i, (p, cx, wd) in enumerate(gl):
            part(p, INK, cx, 40, 250 + i, shadow=False)
    g = grow(t, 0.45)
    if g:
        st.obj(star(200, 150, 14, 10), BLUSH_D, 810, 860, 8, g, g, seed=260)
        st.word("50%", 810, 830, 96, [INK], seed=261, anim=lambda i, n: (0, 0, 8, g, g, 0))
        st.word("OFF", 810, 920, 64, [CREAM], seed=265, anim=lambda i, n: (0, 0, 8, g, g, 0))


def s_ai(st, t):
    st.word("ALL", 540, 400, 220, [LIME, PERI, ICE], seed=280, anim=lambda i, n: hop(t, 0.02 + i * 0.07, i))
    st.word("WITH", 540, 640, 170, [CREAM, BLUSH_D, LIME, PERI], seed=285,
            anim=lambda i, n: hop(t, 0.3 + i * 0.06, i))

    def big(i, n):
        g = grow(t, 0.6 + i * 0.08)
        if not g:
            return None
        if t > 1.0:
            d = (t - 1.0) % BEAT
            sx, sy = (1.1, 0.9) if d < 0.09 else (1, 1)
            return 0, 0, (-5, 5)[i], sx, sy, 0
        return 0, 0, (-5, 5)[i], g, g, 0

    st.word("AI", 540, 1180, 560, [LIME, PERI], seed=290, anim=big)
    for k in range(8):
        a = t * 1.8 + k * math.tau / 8
        g = grow(t, 0.8 + k * 0.05)
        if g:
            st.obj(sparkle(46), [CREAM, LIME, BLUSH_D, ICE][k % 4], 540 + math.cos(a) * 430,
                   1180 + math.sin(a) * 470, t * 200, g, g, seed=300 + k)


def s_direct(st, t):
    st.word("YOU", 540, 320, 190, [INK, LIME, CREAM], seed=310, anim=lambda i, n: hop(t, 0.1 + i * 0.07, i))
    st.word("DIRECT.", 540, 530, 170, [LIME, INK, CREAM, BLUSH_D], seed=315,
            anim=lambda i, n: hop(t, 0.35 + i * 0.06, i))
    s = grow(t, 0.2)
    if s:
        cx, cy = 540, 1000
        st.obj(rrect(600, 380, 34), INK, cx, cy + 60, sx=s, sy=s, seed=320)
        for k in range(3):
            st.obj(rrect(520, 20, 10), CREAM, cx, cy + 10 + k * 70, sx=s, sy=s, seed=321 + k, shadow=False)
        ang = -28.0
        for c0 in (1.0, 2.0, 3.0, 4.0):
            d = t - c0
            if -0.17 <= d < 0:
                ang = -14.0
            elif 0 <= d < 0.17:
                ang = 0.0
            elif 0.17 <= d < 0.34:
                ang = -12.0
        m = skia.Matrix()
        m.setRotate(ang)
        hx, hy = cx - 300, cy - 130
        for lx, w_, col, sd in ((300, 600, INK, 330),) + tuple((60 + k * 120, 56, CREAM, 331 + k) for k in range(5)):
            x, y = m.mapXY(lx * s, -50 * s)
            p = rrect(w_, 96, 14) if col == INK else poly([(-28, -48), (28, -48), (-2, 48), (-58, 48)], 4)
            st.obj(p, col, hx + x, hy + y, ang, s, s, seed=sd, shadow=(col == INK))
    st.word("AI", 540, 1440, 200, [LIME, PERI], seed=340, anim=lambda i, n: hop(t, 2.3 + i * 0.08, i))
    st.word("EDITS.", 540, 1650, 170, [CREAM, INK, PERI, LIME], seed=345,
            anim=lambda i, n: hop(t, 2.55 + i * 0.06, i))


def s_cta(st, t):
    st.word("VIBE", 540, 400, 270, [PERI, LIME, INK, ICE], seed=360, anim=lambda i, n: drop(t, 0.1 + i * 0.1))
    st.word("EDITING", 540, 660, 190, [LIME, INK, PERI, BLUSH_D], seed=370, anim=lambda i, n: drop(t, 0.55 + i * 0.07))
    st.word("by IDEABRO STUDIO", 540, 860, 66, [INK], seed=380, soft=4,
            anim=lambda i, n: (lambda g: (0, 0, 0, g, g, 0) if g else None)(grow(t, 1.1 + i * 0.03)))
    g = grow(t, 1.4)
    press = 2.5 <= t < 2.68
    if g:
        bs = 0.86 if press else 1.0
        st.obj(rrect(740, 210, 105), LIME, 540, 1260 + (210 * (1 - bs)) / 2, sx=g, sy=g * bs, seed=390)
        st.word("ENROLL NOW", 540, 1260 + (210 * (1 - bs)) / 2, 84, [INK], seed=391, soft=5,
                anim=lambda i, n: (0, 0, 0, g, g * bs, 0))
    if t >= 2.2:  # a clay ball drops onto the button
        d = t - 2.2
        if d < 0.3:
            y, sx, sy, lift = lerp_(-100, 1080, (d / 0.3) ** 2), 0.88, 1.18, 1 - d / 0.3
        else:
            sx, sy = land(d - 0.3)
            y, lift = 1080 + (16 if press else 0) + (1 - sy) * 70, 0
        st.obj(circle(72), BLUSH_D, 760, y, sx=sx, sy=sy, seed=395, lift=lift)
    st.word("LINK IN BIO", 540, 1500, 84, [INK, PERI], seed=400, soft=5,
            anim=lambda i, n: hop(t, 3.0 + i * 0.04, i, from_dy=300, height=120))


def lerp_(a, b, k):
    return a + (b - a) * k


FNS = {"hook": s_hook, "say": s_say, "build": s_build, "captions": s_captions, "motion": s_motion, "ads": s_ads,
       "ai": s_ai, "direct": s_direct, "cta": s_cta}


def scene_at(t):
    for s, e, n, col in SCENES:
        if s <= t < e:
            return s, n, col
    s, e, n, col = SCENES[-1]
    return s, n, col


def render_step(step):
    """One stop-motion exposure."""
    t = step / SPS
    s, n, col = scene_at(t)
    surf = skia.Surface(W, H)
    c = surf.getCanvas()
    r = R("cam", step)
    c.translate(r.uniform(-2.5, 2.5), r.uniform(-2.5, 2.5))       # camera nudge between frames
    c.scale(1.006, 1.006)
    backdrop(c, col, step)
    st = Set(c, step)
    lt = round((t - s) * SPS) / SPS
    FNS[n](st, lt)
    c.resetMatrix()
    v = skia.Paint()
    v.setShader(skia.GradientShader.MakeRadial((W / 2, H * 0.45), 1250, [skia.Color(255, 255, 255),
                skia.Color(255, 255, 255), skia.Color(170, 160, 175)], [0.0, 0.55, 1.0]))
    v.setBlendMode(skia.BlendMode.kMultiply)
    c.drawPaint(v)
    return surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)


def render_chunk(args):
    s0, s1, path = args
    enc = subprocess.Popen([FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s",
                            f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf",
                            "19", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    f0, f1 = math.ceil(s0 * FPS / SPS), math.ceil(s1 * FPS / SPS)
    cur, buf = None, None
    for f in range(f0, min(f1, int(DUR * FPS))):
        step = int(f * SPS / FPS + 1e-9)
        if step != cur:
            buf, cur = render_step(step).tobytes(), step
        enc.stdin.write(buf)
    enc.stdin.close()
    enc.wait()
    return path


# ------------------------------------------------------------------ audio: ukulele + pizzicato + woodblock, clay foley
SR = 44100
rng = np.random.default_rng(12)
CH = [[60, 64, 67, 72], [57, 60, 64, 69], [53, 57, 60, 65], [55, 59, 62, 67]]    # C Am F G
ROOT = [48, 45, 41, 43]


def ks(freq, dur, decay=0.995, bright=0.6):
    """Karplus-Strong plucked string."""
    n = int(dur * SR)
    N = max(2, int(SR / freq))
    burst = rng.uniform(-1, 1, N)
    burst = bright * burst + (1 - bright) * np.convolve(burst, np.ones(4) / 4, "same")
    out = np.zeros(n + N)
    out[:N] = burst
    i = N
    while i < n + N:
        j = min(i + N, n + N)
        prev = out[i - N:j - N]
        prev1 = out[i - N - 1:j - N - 1] if i - N - 1 >= 0 else np.concatenate([[0], out[i - N:j - N - 1]])
        out[i:j] = decay * 0.5 * (prev + prev1)
        i = j
    y = out[:n]
    return y * np.minimum(np.arange(n) / (0.002 * SR), 1)


def strum(chord, dur=0.35, down=True, g=1.0):
    notes = chord if down else chord[::-1]
    n = int(dur * SR) + int(0.05 * SR)
    out = np.zeros(n)
    for k, m in enumerate(notes):
        s = int(k * 0.012 * SR)
        y = ks(A.hz(m), dur, 0.994, 0.7)
        out[s:s + len(y)] += y
    return out * g


def woodblock(f=880):
    n = int(0.08 * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.7 * t)) * np.exp(-t / 0.018)


def glock(m, d=0.6):
    n = int(d * SR)
    t = np.arange(n) / SR
    f = A.hz(m)
    return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.05)) * np.exp(-t / 0.25)


def squish(g=1.0):
    n = int(0.16 * SR)
    t = np.arange(n) / SR
    x = sosfilt(butter(2, [180, 1400], "bandpass", fs=SR, output="sos"), rng.standard_normal(n))
    env = np.minimum(t / 0.01, 1) * np.exp(-t / 0.05)
    return (x * env * (1 + 0.7 * np.sin(2 * np.pi * 38 * t)) + 0.5 * np.sin(2 * np.pi * 110 * t) * env) * g


def plop():
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    f = 150 + 380 * np.exp(-t / 0.02)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.045)


def boing():
    n = int(0.55 * SR)
    t = np.arange(n) / SR
    f = 190 * (1 + 0.45 * np.exp(-t / 0.18) * np.sin(2 * np.pi * 13 * t)) * (1 + 0.3 * np.exp(-t / 0.05))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.22) * 0.8


def creak(d=1.2):
    n = int(d * SR)
    t = np.arange(n) / SR
    f = 70 + 40 * t / d
    ph = np.cumsum(f) / SR
    y = ((ph % 1) * 2 - 1) * (0.5 + 0.5 * np.sin(2 * np.pi * 9 * t))
    y = sosfilt(butter(2, [150, 900], "bandpass", fs=SR, output="sos"), y)
    return y * np.sin(np.pi * t / d) * 0.6


def build_audio():
    N = int(DUR * SR)
    band, perc, fx = np.zeros(N), np.zeros(N), np.zeros(N)
    K, C = A.kick(), A.clap()
    nb = int(DUR / BEAT)
    pattern = [(0.0, True), (0.5, True), (0.75, False), (1.25, False), (1.5, True), (1.75, False)]  # D D U U D U
    for b in range(nb):
        t = b * BEAT
        bar = int(t / (BEAT * 4)) % 4
        chord, root = CH[bar], ROOT[bar]
        if t >= 29.5:
            break
        quiet = 4.0 <= t < 6.5          # hold back while the bubble inflates
        if b % 2 == 0:
            for o, dn in pattern:
                A.place(band, strum(chord, 0.32, dn, 0.9 if dn else 0.6), t + o * BEAT, 0.5 if quiet else 1.0)
        A.place(band, ks(A.hz(root), 0.4, 0.985, 0.4), t, 0.9)                        # pizzicato bass
        if not quiet:
            A.place(perc, K * 0.7, t) if b % 2 == 0 else A.place(perc, C * 0.5, t)
        A.place(perc, woodblock(1200 if b % 2 else 900) * 0.35, t + BEAT / 2)
        if 12.0 <= t < 20.0 or t >= 25.0:
            mel = [72, 76, 79, 76, 74, 72, 67, 69]
            A.place(band, glock(mel[b % 8] + (0 if bar != 2 else -3)) * 0.35, t)
    A.place(band, strum(CH[0], 1.2, True, 1.3), 29.5)
    A.place(perc, K, 29.5)

    F = dict(A.SFX_FNS, squish=squish, plop=plop, boing=boing, creak=creak, glock=lambda: glock(84, 0.8))
    G = dict(A.SFX_GAIN, squish=0.5, plop=0.5, boing=0.45, creak=0.4, glock=0.3)
    cues = []

    def letters(t0, n, gap, dur=0.34):
        for i in range(n):
            cues.append((t0 + i * gap + dur, "squish", 0.55))

    T = S["hook"]
    letters(T + 0.1, 7, 0.11)
    letters(T + 1.3, 5, 0.08)
    letters(T + 1.9, 7, 0.08)
    cues += [(T + 0.5, "plop", 0.8), (T + 2.6, "creak", 1.0)] + [(T + 0.6 + k * 0.25, "tick", 0.4) for k in range(12)]
    T = S["say"]
    letters(T + 0.1, 8, 0.07)
    cues += [(T + 0.3, "plop", 0.8)] + [(T + 0.7 + i / 12 * 1.2, "type", 0.6) for i in range(11)]
    cues += [(T + 2.25, "boing", 0.4), (T + 2.5, "pop", 1.3), (T + 2.5, "impact", 0.5)]
    cues += [(T + 2.6 + i * 0.07, "plop", 0.5) for i in range(4)]
    T = S["build"]
    cues += [(T, "whoosh", 0.6), (T + 0.75, "squish", 0.9), (T + 0.95, "plop", 0.6), (T + 1.15, "plop", 0.6),
             (T + 1.45, "plop", 0.5)]
    cues += [(T + 1.6 + i * 0.1 + 0.3, "squish", 0.6) for i in range(4)]
    cues += [(T + 2.1 + i * 0.08 + 0.3, "squish", 0.5) for i in range(7)]
    T = S["captions"]
    cues += [(T, "whoosh", 0.6), (T + 0.5, "pop", 0.7), (T + 0.9, "pop", 0.7)]
    letters(T + 0.02, 8, 0.05)
    T = S["motion"]
    cues += [(T, "whoosh", 0.6)] + [(T + b * BEAT + k * BEAT / 3 + 0.3, "squish", 0.4) for b in range(4)
                                     for k in range(3)]
    T = S["ads"]
    cues += [(T, "whoosh", 0.6), (T + 0.15, "plop", 0.7), (T + 0.45, "boing", 0.6)]
    cues += [(T + i * 0.08 + 0.3, "squish", 0.6) for i in range(3)]
    T = S["ai"]
    cues += [(T, "whoosh", 0.7), (T + 0.6, "stamp", 0.8), (T + 0.8, "sparkle", 0.8)]
    letters(T + 0.02, 3, 0.07)
    letters(T + 0.3, 4, 0.06)
    T = S["direct"]
    letters(T + 0.1, 3, 0.07)
    letters(T + 0.35, 7, 0.06)
    cues += [(T, "whoosh", 0.7), (T + 0.2, "plop", 0.7)] + [(T + c0, "clack", 1.0) for c0 in (1.0, 2.0, 3.0, 4.0)]
    letters(T + 2.3, 2, 0.08)
    letters(T + 2.55, 6, 0.06)
    T = S["cta"]
    cues += [(T, "whoosh", 0.7)] + [(T + 0.1 + i * 0.1 + 0.3, "squish", 0.6) for i in range(4)]
    cues += [(T + 0.55 + i * 0.07 + 0.3, "squish", 0.5) for i in range(7)]
    cues += [(T + 1.4, "plop", 0.8), (T + 2.5, "squish", 1.2), (T + 2.52, "boing", 0.6), (T + 3.0, "glock", 1.0)]
    for t0, kind, g in cues:
        A.place(fx, F[kind]() * G[kind], t0, g)

    def nrm(x):
        return x / (np.abs(x).max() + 1e-9)

    band = sosfilt(butter(2, 9000, "lp", fs=SR, output="sos"), band)
    mix = 0.75 * nrm(band) + 0.55 * nrm(perc) + 0.7 * nrm(fx)
    mix /= np.abs(mix).max()
    mix = np.tanh(1.5 * mix) / np.tanh(1.5)
    fo = int(0.35 * SR)
    mix[-fo:] *= np.linspace(1, 0, fo) ** 2
    st = np.stack([mix, mix], 1) * 0.93
    path = os.path.join(OUT, "claymation_audio.wav")
    wavfile.write(path, SR, (st * 32767).astype(np.int16))
    return path


def render():
    steps = int(DUR * SPS)
    n = os.cpu_count() or 4
    b = [round(steps * i / n) for i in range(n + 1)]
    jobs = [(b[i], b[i + 1], os.path.join(OUT, f"chunk{i}.mp4")) for i in range(n)]
    with Pool(n) as pool:
        parts = pool.map(render_chunk, jobs)
    lst = os.path.join(OUT, "chunks.txt")
    with open(lst, "w") as fh:
        fh.writelines(f"file '{p}'\n" for p in parts)
    vid = os.path.join(OUT, "claymation_noaudio.mp4")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", vid],
                   check=True)
    for p in parts:
        os.remove(p)
    os.remove(lst)
    return vid


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == "stills":
        d = os.path.join(OUT, "stills")
        os.makedirs(d, exist_ok=True)
        for ts in map(float, sys.argv[2:]):
            arr = render_step(int(ts * SPS))
            skia.Image.fromarray(arr).save(os.path.join(d, f"t{ts:05.2f}.png"), skia.kPNG)
        sys.exit()
    wav = build_audio()
    vid = render()
    final = os.path.join(OUT, "claymation.mp4")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", vid, "-i", wav, "-c:v", "copy", "-c:a", "aac", "-b:a",
                    "192k", "-shortest", "-movflags", "+faststart", final], check=True)
    print("wrote", final)
