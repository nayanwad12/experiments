"""Evolution, drawn by a single point of light.

A lone point of light paints the story of life as one continuous trail that
hangs in 3D space. The virtual camera follows it and is "exposed" like a
long-exposure photograph: trails accumulate, lenses breathe with depth of
field, light scatters into haze, and everything is mirrored in a wet floor.

    python render.py                       # full 1080p mp4
    python render.py --stills 120,900      # preview single frames as PNG
"""
import argparse
import math
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, gaussian_filter1d

from figures import FIGURES, catmull_rom

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1920, 1080, 30
DS = 0.004            # trail sample spacing, metres
INTRO, OUTRO = 1.2, 9.0
V_REF = 1.2           # speed at which a trail has "normal" exposure

# ------------------------------------------------------------------ palette
C = dict(
    spark=(0.55, 0.80, 1.00), life=(0.40, 0.78, 1.00), sea=(0.22, 0.52, 1.00),
    land=(0.30, 1.00, 0.55), apes=(1.00, 0.82, 0.35), up=(1.00, 0.58, 0.24),
    fire=(1.00, 0.40, 0.12), flame=(1.00, 0.62, 0.20), sapiens=(1.00, 0.90, 0.78),
    sky=(0.70, 0.86, 1.00),
)


def smoothstep(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def resample(p, ds=DS):
    p = np.asarray(p, float)
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    n = max(2, int(s[-1] / ds) + 1)
    si = np.linspace(0, s[-1], n)
    return np.stack([np.interp(si, s, p[:, k]) for k in range(3)], 1)


def spline3(pts, n=32):
    return catmull_rom(np.asarray(pts, float), samples_per_seg=n)


# =================================================================== story
class Story:
    def __init__(self):
        self.pieces = []
        self.cur = None

    def add(self, pts, e=1.0, speed=1.2, color=None, cam=None, focus=None,
            chapter=None, hold=0.0):
        pts = resample(pts)
        if color is None:
            color = self.pieces[-1]["color"][1] if self.pieces else C["spark"]
        if not isinstance(color[0], (tuple, list)):
            color = (color, color)
        self.pieces.append(dict(pts=pts, e=e, speed=speed, color=color, cam=cam,
                                focus=focus, chapter=chapter, hold=hold))
        self.cur = pts[-1]

    def link(self, target, sway=0.6, e=0.32, speed=2.8, color=None, lift=0.04):
        a, b = np.asarray(self.cur), np.asarray(target)
        d = np.sign(b[0] - a[0]) or 1.0
        wps = [a, (a[0] + 0.45 * d, lift, a[2]),
               ((a[0] + b[0]) / 2, lift + 0.03, (a[2] + b[2]) / 2 + sway),
               (b[0] - 0.45 * d, lift, b[2]), b]
        c0 = self.pieces[-1]["color"][1]
        self.add(spline3(wps), e=e, speed=speed, color=(c0, color or c0))

    def hop(self, target, speed=2.0):
        """Move with the light covered."""
        a, b = np.asarray(self.cur), np.asarray(target)
        mid = (a + b) / 2 + np.array([0, 0.05, 0.12])
        self.add(spline3([a, mid, b]), e=0.0, speed=speed)

    def figure(self, strokes, origin, yaw=0.0, speed=1.15, color=None, cam=None,
               chapter=None, hold=0.5):
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        ox, oy, oz = origin
        placed = []
        for st in strokes:
            p2 = catmull_rom(st["pts"])
            p3 = np.stack([ox + p2[:, 0] * c, oy + p2[:, 1], oz - p2[:, 0] * s], 1)
            placed.append((p3, st["e"]))
        ys = np.concatenate([p[:, 1] for p, _ in placed])
        focus = np.array([ox, 0.5 * (ys.min() + ys.max()) + 0.1, oz])
        for i, (p3, e) in enumerate(placed):
            if i > 0 and np.linalg.norm(p3[0] - self.cur) > 1e-3:
                self.hop(p3[0])
                self.pieces[-1]["focus"] = focus
                self.pieces[-1]["cam"] = cam
            col = C["flame"] if e > 2 else color
            self.add(p3, e=e, speed=speed * (0.8 if e > 2 else 1.0), color=col,
                     cam=cam, focus=focus, chapter=chapter if i == 0 else None,
                     hold=hold if i == len(placed) - 1 else 0.0)
        return placed[0][0][0]

    @staticmethod
    def first_point(strokes, origin, yaw=0.0):
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        x, y = strokes[0]["pts"][0]
        return np.array([origin[0] + x * c, origin[1] + y, origin[2] - x * s])


def build_story():
    S = Story()
    # ---- a spark wakes on the floor and drifts toward the first molecule
    helix_c = np.array([0.0, 0.0, 0.0])
    r, y0, y1, turns = 0.32, 0.12, 2.25, 2.25

    def strand(u, phase):
        th = math.pi + 2 * math.pi * turns * u + phase
        return np.stack([helix_c[0] + r * np.cos(th), y0 + (y1 - y0) * u,
                         helix_c[2] + r * np.sin(th)], -1)

    start_helix = strand(np.array([0.0]), 0)[0]
    spark = [(-3.4, 0.05, 0.9), (-3.15, 0.14, 1.1), (-2.85, 0.30, 0.95), (-2.9, 0.22, 0.65),
             (-2.55, 0.12, 0.55), (-2.1, 0.20, 0.75), (-1.6, 0.10, 0.55), (-1.0, 0.06, 0.2),
             (-0.6, 0.08, 0.05), tuple(start_helix)]
    S.add(spline3(spark), e=lambda u: 0.05 + 0.55 * smoothstep(u * 1.3), speed=0.75,
          color=C["spark"], cam=(2.6, 38, 50, 0.38), focus=None)
    S.pieces[-1]["ramp_head"] = True

    # ---- LIFE: a double helix, up one strand, down the other with its rungs
    u = np.linspace(0, 1, 900)
    focus = np.array([0.0, 1.2, 0.0])
    cam = (4.8, 42, -14, 1.05)
    S.add(strand(u, 0), e=1.0, speed=1.9, color=C["life"], cam=cam, focus=focus,
          chapter=("Life", "3.8 BILLION YEARS AGO"))
    top_a, top_b = strand(np.array([1.0]), 0)[0], strand(np.array([1.0]), math.pi)[0]
    S.add(spline3([top_a, (top_a + top_b) / 2 + np.array([0, 0.22, 0]), top_b]), e=1.0,
          speed=1.6, cam=cam, focus=focus)
    n_rungs = 12
    uk = np.linspace(1, 0, n_rungs + 2)
    for k in range(len(uk) - 1):
        seg = strand(np.linspace(uk[k], uk[k + 1], 60), math.pi)
        S.add(seg, e=1.0, speed=1.9, cam=cam, focus=focus)
        if k < len(uk) - 2:
            b_pt, a_pt = seg[-1], strand(np.array([uk[k + 1]]), 0)[0]
            S.add(np.array([b_pt, a_pt, b_pt]), e=0.55, speed=3.2, cam=cam, focus=focus)
    S.pieces[-1]["hold"] = 0.4

    # ---- THE SEA
    o = (5.6, 0.0, 0.55)
    S.link(Story.first_point(FIGURES["fish"], o, 30), sway=0.9, color=C["sea"])
    S.figure(FIGURES["fish"], o, yaw=30, speed=1.05, color=C["sea"], cam=(4.2, 44, 22, 1.05),
             chapter=("The Sea", "500 MILLION YEARS AGO"))

    # ---- ONTO LAND
    o = (10.6, 0.0, -0.35)
    S.link(Story.first_point(FIGURES["lizard"], o, 36), sway=-0.8, color=C["land"])
    S.figure(FIGURES["lizard"], o, yaw=36, speed=1.0, color=C["land"], cam=(3.4, 52, 30, 0.62),
             chapter=("Onto Land", "375 MILLION YEARS AGO"))

    # ---- THE APES
    o = (15.2, 0.0, 0.3)
    S.link(Story.first_point(FIGURES["chimp"], o, 30), sway=0.8, color=C["apes"])
    S.figure(FIGURES["chimp"], o, yaw=30, speed=1.1, color=C["apes"], cam=(4.0, 18, 46, 0.85),
             chapter=("The Apes", "7 MILLION YEARS AGO"))

    # ---- STANDING UP
    o = (19.4, 0.0, -0.2)
    S.link(Story.first_point(FIGURES["lucy"], o, 34), sway=-0.7, color=C["up"])
    S.figure(FIGURES["lucy"], o, yaw=34, speed=1.0, color=C["up"], cam=(3.6, 48, 30, 0.75),
             chapter=("Standing Up", "3.2 MILLION YEARS AGO"))

    # ---- FIRE
    o = (23.6, 0.0, 0.25)
    S.link(Story.first_point(FIGURES["erectus"], o, 32), sway=0.7, color=C["fire"])
    S.figure(FIGURES["erectus"], o, yaw=32, speed=1.1, color=C["fire"], cam=(4.3, 22, 50, 1.0),
             chapter=("Fire", "1.5 MILLION YEARS AGO"))

    # ---- HOMO SAPIENS
    o = (28.0, 0.0, 0.0)
    S.link(Story.first_point(FIGURES["sapiens"], o, 34), sway=-0.6, color=C["sapiens"])
    S.figure(FIGURES["sapiens"], o, yaw=34, speed=1.1, color=C["sapiens"],
             cam=(4.5, 52, 26, 0.95), chapter=("Homo sapiens", "300,000 YEARS AGO"), hold=0.7)

    # ---- LOOKING UP: the light leaves the floor and climbs into the sky
    hc = np.array([31.6, 0.0, -0.4])
    S.link(hc + np.array([-1.1, 0.05, 0.0]), sway=0.4, e=0.45, speed=2.4, color=C["sapiens"])
    u = np.linspace(0, 1, 1400)
    th = math.pi + 2 * math.pi * 2.4 * u
    rad = 1.1 + 0.9 * u
    spiral = np.stack([hc[0] + rad * np.cos(th), 0.05 + 5.4 * u ** 1.15,
                       hc[2] + rad * np.sin(th)], 1)
    up = np.linspace(0, 1, 200)
    tail = np.stack([np.full_like(up, spiral[-1, 0]) + 0.6 * up, spiral[-1, 1] + 6.0 * up,
                     np.full_like(up, spiral[-1, 2]) - 0.3 * up], 1)
    S.add(spiral, e=1.0, speed=2.3, color=(C["sapiens"], C["sky"]), cam=(7.0, 38, 52, 1.4),
          focus=hc + np.array([0, 2.6, 0]), chapter=("Looking Up", "TODAY"))
    S.add(tail, e=lambda u: 1.0 - smoothstep(u), speed=3.2, color=C["sky"],
          cam=(8.0, 52, 56, 2.0), focus=hc + np.array([0, 3.2, 0]))
    return S


# ============================================================ flatten story
class Timeline:
    def __init__(self, S):
        P, E, COL, SPD, CAM, FOC, HOLD, PID = [], [], [], [], [], [], [], []
        self.chapters = []
        prev_cam_end = None
        for pi, pc in enumerate(S.pieces):
            p = pc["pts"] if pi == 0 else pc["pts"][1:]
            n = len(p)
            u = np.linspace(0, 1, n)
            e = pc["e"](u) if callable(pc["e"]) else np.full(n, float(pc["e"]))
            c0, c1 = np.array(pc["color"][0]), np.array(pc["color"][1])
            col = c0[None] * (1 - smoothstep(u))[:, None] + c1[None] * smoothstep(u)[:, None]
            P.append(p); E.append(e); COL.append(col)
            SPD.append(np.full(n, pc["speed"]))
            CAM.append(np.full((n, 3), np.nan))
            FOC.append(np.tile(pc["focus"], (n, 1)) if pc["focus"] is not None else p.copy())
            h = np.zeros(n); h[-1] = pc["hold"]; HOLD.append(h)
            PID.append(np.full(n, pi))
        self.P = np.vstack(P)
        self.E = np.concatenate(E)
        self.COL = np.vstack(COL)
        spd = gaussian_filter1d(np.concatenate(SPD), 70, mode="nearest")
        cam = np.vstack(CAM)
        # a camera move (d, az0, az1, height) spans every consecutive piece sharing it
        start, gi = 0, 0
        spans = []
        for pi, pc in enumerate(S.pieces):
            n = len(pc["pts"]) - (0 if pi == 0 else 1)
            spans.append((start, start + n))
            start += n
        pi = 0
        while pi < len(S.pieces):
            spec = S.pieces[pi]["cam"]
            pj = pi
            while pj + 1 < len(S.pieces) and S.pieces[pj + 1]["cam"] is spec:
                pj += 1
            if spec is not None:
                a, b = spans[pi][0], spans[pj][1]
                u = np.linspace(0, 1, b - a)
                d, a0, a1, y = spec
                cam[a:b] = np.stack([np.full(b - a, d), a0 + (a1 - a0) * u, np.full(b - a, y)], 1)
            pi = pj + 1
        # links inherit the camera by interpolating between their neighbours
        idx = np.arange(len(cam))
        for k in range(3):
            ok = ~np.isnan(cam[:, k])
            cam[:, k] = np.interp(idx, idx[ok], cam[ok, k])
        self.CAM = cam
        self.FOC = np.vstack(FOC)
        self.PID = np.concatenate(PID)
        dt = DS / spd + np.concatenate(HOLD)
        self.T = np.concatenate([[0], np.cumsum(dt[1:])]) + INTRO
        # exposure: the slower the light moves, the brighter its trail
        self.EXP = self.E * np.minimum(DS / spd, DS / 0.45) / (DS / V_REF)
        # chapters
        start = 0
        for pi, pc in enumerate(S.pieces):
            n = len(pc["pts"]) - (0 if pi == 0 else 1)
            if pc["chapter"]:
                self.chapters.append((self.T[start], pc["chapter"]))
            if pc.get("ramp_head"):
                self.ramp_end = self.T[start + n - 1]
            start += n
        self.t_end = self.T[-1]
        self.duration = self.t_end + OUTRO
        self.nframes = int(self.duration * FPS)
        self._camera()

    def head_index(self, t):
        return int(np.clip(np.searchsorted(self.T, t, side="right") - 1, 0, len(self.T) - 1))

    def _camera(self):
        n = self.nframes
        t = np.arange(n) / FPS
        hi = np.array([self.head_index(x) for x in t])
        head = self.P[hi]
        foc = self.FOC[hi]
        cam = self.CAM[hi].copy()
        # outro: pull back to reveal the whole trail hanging in space
        w = smoothstep((t - self.t_end + 0.5) / 6.5)[:, None]
        reveal_target = np.array([16.5, 1.7, 0.0])
        reveal_cam = np.array([18.5, 60.0, 2.4])
        foc = foc * (1 - w) + reveal_target * w
        head = head * (1 - w) + reveal_target * w
        cam = cam * (1 - w) + reveal_cam * w
        s = FPS
        head_s = gaussian_filter1d(head, 0.45 * s, axis=0, mode="nearest")
        foc_s = gaussian_filter1d(foc, 0.9 * s, axis=0, mode="nearest")
        cam_s = gaussian_filter1d(cam, 1.1 * s, axis=0, mode="nearest")
        wf = 0.65 + 0.35 * w
        target = foc_s * wf + head_s * (1 - wf)
        target = gaussian_filter1d(target, 0.35 * s, axis=0, mode="nearest")
        d, az, cy = cam_s[:, 0], np.radians(cam_s[:, 1] + 2.5 * np.sin(t * 0.23)), cam_s[:, 2]
        pos = np.stack([target[:, 0] + d * np.sin(az),
                        cy + 0.03 * np.sin(t * 0.41),
                        target[:, 2] + d * np.cos(az)], 1)
        self.cam_pos, self.cam_tgt = pos, target
        self.head_idx = hi


# ================================================================ textures
def fractal_noise(h, w, scales, seed):
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp = 1.0
    for sc in scales:
        n = rng.standard_normal((h, w)).astype(np.float32)
        n = gaussian_filter(n, sc, mode="wrap")  # periodic, so it can scroll
        n /= n.std() + 1e-6
        out += amp * n
        amp *= 0.55
    out -= out.min()
    out /= out.max()
    return out


FX0, FZ0, CELL = -8.0, -14.0, 0.04          # floor texture domain
FNX, FNZ = 1300, 700

PUDDLE = smoothstep((fractal_noise(FNZ, FNX, [40, 16, 6], 7) - 0.42) / 0.16).astype(np.float32)
GRIT = fractal_noise(FNZ, FNX, [1.2, 3, 8], 11).astype(np.float32)
WISP = fractal_noise(256, 512, [22, 9, 4], 3).astype(np.float32)
RIPPLE = fractal_noise(256, 256, [5, 2], 5).astype(np.float32)


def load_font(name, size):
    return ImageFont.truetype(os.path.join(HERE, "fonts", name), size)


def text_layer(lines, anchor="left"):
    """lines: [(text, font, tracking, gap_after)] -> float alpha image."""
    img = Image.new("L", (W, 320), 0)
    dr = ImageDraw.Draw(img)
    y = 10
    widths = []
    for text, font, track, gap in lines:
        wsum = sum(dr.textlength(ch, font=font) + track for ch in text) - track
        widths.append(wsum)
    for (text, font, track, gap), wsum in zip(lines, widths):
        x = 10 if anchor == "left" else (W - wsum) / 2
        for ch in text:
            dr.text((x, y), ch, font=font, fill=255)
            x += dr.textlength(ch, font=font) + track
        asc, desc = font.getmetrics()
        y += asc + desc + gap
    a = np.asarray(img, np.float32) / 255.0
    return cv2.GaussianBlur(a, (0, 0), 0.6), y


def build_captions(tl):
    date_f, title_f = load_font("Jost-Light.ttf", 22), load_font("Cormorant-Light.ttf", 78)
    caps = []
    for t0, (title, date) in tl.chapters:
        a, _ = text_layer([(date, date_f, 6, 2), (title, title_f, 1, 0)])
        caps.append(dict(t0=t0 + 0.7, t1=t0 + 5.6, img=a, x=110, y=H - 238))
    end_title = load_font("Cormorant-Light.ttf", 120)
    end_sub = load_font("Jost-Light.ttf", 22)
    a, _ = text_layer([("Evolution", end_title, 4, 6),
                       ("ONE POINT OF LIGHT  ·  FOUR BILLION YEARS", end_sub, 7, 0)], "center")
    caps.append(dict(t0=tl.t_end + 2.6, t1=tl.duration + 5, img=a, x=0, y=150))
    return caps


# ================================================================ renderer
SIGMAS = np.array([0.75, 1.8, 4.0, 8.5, 16.0])
RSIGMAS = np.array([1.2, 4.0, 11.0])
GAIN = 7.0
F_PX = (W / 2) / math.tan(math.radians(70) / 2)


def blur(img, sig, sy=None):
    sy = sig if sy is None else sy
    m = max(sig, sy)
    if m < 0.3:
        return img
    if m <= 4:
        return cv2.GaussianBlur(img, (0, 0), sig, sigmaY=sy)
    k = 2 if m < 10 else 4 if m < 32 else 8
    hh, ww = img.shape[:2]
    small = cv2.resize(img, (ww // k, hh // k), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), max(sig / k, 0.3), sigmaY=max(sy / k, 0.3))
    return cv2.resize(small, (ww, hh), interpolation=cv2.INTER_LINEAR)


def camera_basis(pos, tgt):
    fwd = tgt - pos
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, [0, 1, 0])
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    return fwd, right, up


def project(P, pos, basis):
    fwd, right, up = basis
    rel = P - pos
    zc = rel @ fwd
    zs = np.maximum(zc, 1e-3)
    u = W / 2 + F_PX * (rel @ right) / zs
    v = H / 2 - F_PX * (rel @ up) / zs
    return u, v, zc


def densify(u, v, level, w3, ok):
    """Insert in-between samples wherever consecutive samples are >0.7px apart."""
    if len(u) < 2:
        return u, v, level, w3
    du, dv = np.diff(u), np.diff(v)
    dist = np.hypot(du, dv)
    good = ok[:-1] & ok[1:] & (dist < 300)
    m = np.where(good, np.clip(np.ceil(dist / 0.7), 1, 24), 1).astype(np.int64)
    m = np.append(m, 1)
    rep = np.repeat(np.arange(len(u)), m)
    k = np.arange(len(rep)) - np.repeat(np.cumsum(m) - m, m)
    f = (k / m[rep])
    nxt = np.minimum(rep + 1, len(u) - 1)
    lerp = lambda a: a[rep] + (a[nxt] - a[rep]) * f
    return lerp(u), lerp(v), lerp(level), w3[rep] / m[rep][:, None]


def splat_layers(u, v, level, w3, L, head=0):
    """Bilinear splat into L depth-of-field layers; level is fractional."""
    ok0 = np.isfinite(u) & np.isfinite(v)
    n = len(u) - head
    if n > 1:
        du, dv, dl, dw = densify(u[:n], v[:n], level[:n], w3[:n], ok0[:n] & (w3[:n].sum(1) > 0))
        u = np.concatenate([du, u[n:]]); v = np.concatenate([dv, v[n:]])
        level = np.concatenate([dl, level[n:]]); w3 = np.vstack([dw, w3[n:]])
    ok = (u > 0) & (u < W - 2) & (v > 0) & (v < H - 2) & np.isfinite(level)
    u, v, level, w3 = u[ok], v[ok], level[ok], w3[ok]
    x0, y0 = np.floor(u).astype(np.int64), np.floor(v).astype(np.int64)
    fx, fy = (u - x0), (v - y0)
    l0 = np.clip(np.floor(level).astype(np.int64), 0, L - 1)
    fl = np.clip(level - l0, 0, 1)
    l1 = np.minimum(l0 + 1, L - 1)
    idx, wt = [], []
    for ll, wl in ((l0, 1 - fl), (l1, fl)):
        base = ll * (H * W)
        for dx, dy, ww in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)),
                           (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
            idx.append(base + (y0 + dy) * W + x0 + dx)
            wt.append(wl * ww)
    idx, wt = np.concatenate(idx), np.concatenate(wt)
    out = np.empty((L, H, W, 3), np.float32)
    for c in range(3):
        wc = wt * np.tile(w3[:, c], 8)
        out[..., c] = np.bincount(idx, weights=wc, minlength=L * H * W).reshape(L, H, W)
    return out


class FloorLight:
    """World-space accumulation of light the moving point cast on the floor."""
    R = 2.2

    def __init__(self, tl):
        self.tl = tl
        self.tex = np.zeros((FNZ, FNX, 3), np.float32)
        step = int(0.03 / DS)
        idx = np.arange(0, len(tl.P), step)
        self.idx = idx[tl.EXP[idx] > 0.02]
        self.done = 0
        n = int(self.R / CELL)
        g = (np.arange(-n, n + 1) * CELL)
        self.gx, self.gz = np.meshgrid(g, g)
        self.n = n

    def advance(self, head_i):
        tl = self.tl
        while self.done < len(self.idx) and self.idx[self.done] <= head_i:
            i = self.idx[self.done]
            self.done += 1
            p = tl.P[i]
            h = max(p[1], 0.0) + 0.12
            k = h / (self.gx ** 2 + self.gz ** 2 + h * h) ** 1.5
            cx, cz = int(round((p[0] - FX0) / CELL)), int(round((p[2] - FZ0) / CELL))
            x0, x1, z0, z1 = cx - self.n, cx + self.n + 1, cz - self.n, cz + self.n + 1
            if x0 < 0 or z0 < 0 or x1 > FNX or z1 > FNZ:
                continue
            amt = tl.EXP[i] * (0.03 / DS)
            self.tex[z0:z1, x0:x1] += (k * amt)[..., None] * tl.COL[i][None, None]


def ray_grid(scale=2):
    hs, ws = H // scale, W // scale
    ys, xs = np.mgrid[0:hs, 0:ws].astype(np.float32)
    return (xs + 0.5) * scale, (ys + 0.5) * scale


GRID_U, GRID_V = ray_grid(2)


def render_frame(fi, tl, floor, caps):
    t = fi / FPS
    pos, tgt = tl.cam_pos[fi], tl.cam_tgt[fi]
    basis = camera_basis(pos, tgt)
    fwd, right, upv = basis
    zf = float(np.linalg.norm(tgt - pos))

    # ---------------------------------------------------- the trail so far
    hi = tl.head_idx[fi]
    live = tl.T[hi] <= t and t < tl.t_end + 0.05
    n = hi + 1 if t >= INTRO else 0
    # interpolate the head between samples for smooth motion
    if n > 0 and hi + 1 < len(tl.T):
        a = np.clip((t - tl.T[hi]) / max(tl.T[hi + 1] - tl.T[hi], 1e-6), 0, 1)
        head = tl.P[hi] * (1 - a) + tl.P[hi + 1] * a
    else:
        head = tl.P[min(hi, len(tl.P) - 1)]
    P, w, col = tl.P[:n], tl.EXP[:n], tl.COL[:n]

    head_e = 0.0
    if live and t >= INTRO:
        head_e = 0.25 + 0.75 * tl.E[hi]
        if t < tl.ramp_end:
            head_e *= smoothstep((t - INTRO) / (tl.ramp_end - INTRO) * 1.4)
        head_e *= 1.0 + 0.08 * math.sin(t * 37.0) * math.sin(t * 13.0)
    head_col = tl.COL[min(hi, len(tl.COL) - 1)] * 0.5 + 0.5

    def dof_level(zc, sig):
        coc = 15.0 * np.abs(1.0 - zf / np.maximum(zc, 0.05))
        return np.interp(np.maximum(coc, sig[0]), sig, np.arange(len(sig)))

    nh = 1 if head_e > 0 else 0
    Pall = np.vstack([P, head[None]]) if nh else P
    colors = np.vstack([col, head_col[None]]) if nh else col

    def expose(Pts, sig):
        """Project, weight and splat the trail into depth-of-field layers."""
        L = len(sig)
        if len(Pts) == 0:
            return np.zeros((H, W, 3), np.float32)
        u, v, zc = project(Pts, pos, basis)
        zs = np.maximum(zc, 0.15)
        # each sample covers DS*f/z pixels of screen, so a trail's brightness
        # per pixel is independent of distance, like a real line of light
        mass = np.empty(len(Pts))
        mass[:len(P)] = w * DS * F_PX / zs[:len(P)]
        if nh:
            mass[-1] = 3.2 * head_e
        mass *= GAIN * np.exp(-0.035 * zs) * (zc > 0.15)
        w3 = colors * mass[:, None]
        layers = splat_layers(u, v, dof_level(zc, sig), w3, L, head=nh)
        out = np.zeros((H, W, 3), np.float32)
        for k, sg in enumerate(sig):
            out += blur(layers[k], sg)
        return out

    direct = expose(Pall, SIGMAS)
    # reflection in the wet floor: the same trail mirrored through y = 0
    refl = expose(Pall * np.array([1.0, -1.0, 1.0]), RSIGMAS)

    # ------------------------------------------------------- floor geometry
    du = (GRID_U - W / 2) / F_PX
    dv = -(GRID_V - H / 2) / F_PX
    ray = fwd[None, None] + du[..., None] * right[None, None] + dv[..., None] * upv[None, None]
    ray /= np.linalg.norm(ray, axis=-1, keepdims=True)
    ry = ray[..., 1]
    hit = ry < -1e-4
    tt = np.where(hit, -pos[1] / np.where(hit, ry, -1), 0)
    fx = pos[0] + tt * ray[..., 0]
    fz = pos[2] + tt * ray[..., 2]
    mx = ((fx - FX0) / CELL).astype(np.float32)
    mz = ((fz - FZ0) / CELL).astype(np.float32)
    puddle = cv2.remap(PUDDLE, mx, mz, cv2.INTER_LINEAR, borderValue=0.0)
    grit = cv2.remap(GRIT, mx, mz, cv2.INTER_LINEAR, borderValue=0.5)
    acc = cv2.remap(floor.tex, mx, mz, cv2.INTER_LINEAR, borderValue=0.0)
    cos_t = np.clip(-ry, 0, 1)
    dist_fade = np.exp(-0.045 * tt) * hit
    fres = (0.04 + 0.96 * (1 - cos_t) ** 5)
    r_pud = (0.35 + 0.65 * fres) * puddle * dist_fade
    r_rough = (0.18 + 0.5 * fres) * (1 - puddle) * dist_fade * (0.7 + 0.6 * grit)
    albedo = 0.05 * (0.25 + 1.5 * grit ** 2) * (1 - 0.5 * puddle) * dist_fade
    lit = acc * 0.0028
    if head_e > 0:
        hx, hz = fx - head[0], fz - head[2]
        hh = max(head[1], 0.0) + 0.06
        lit = lit + (0.7 * head_e * hh / (hx * hx + hz * hz + hh * hh) ** 1.5)[..., None] * head_col
    diffuse = albedo[..., None] * lit
    up2 = lambda a: cv2.resize(a.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
    r_pud, r_rough, diffuse = up2(r_pud), up2(r_rough), up2(diffuse)

    # ripples bend the mirror; micro-roughness smears it into vertical streaks
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32) if not hasattr(render_frame, "_g") else render_frame._g
    render_frame._g = (ys, xs)
    rp = cv2.resize(RIPPLE, (W // 4, H // 4))
    rp = np.roll(rp, int(t * 6) % rp.shape[0], axis=0)
    rp = cv2.resize(rp, (W, H), interpolation=cv2.INTER_CUBIC) - 0.5
    sharp = cv2.GaussianBlur(cv2.remap(refl, xs + 3.0 * rp, ys + 1.5 * rp, cv2.INTER_LINEAR), (0, 0), 0.8, sigmaY=2.2)
    rough = blur(refl, 3.0, 16.0)
    reflection = sharp * r_pud[..., None] + rough * r_rough[..., None]

    # ------------------------------------------------------------ atmosphere
    hdir = np.array([fwd[0], 0.0, fwd[2]])
    hdir /= np.linalg.norm(hdir)
    horizon_v = H / 2 - F_PX * (hdir @ upv) / max(hdir @ fwd, 1e-3)
    vv = np.arange(H, dtype=np.float32)[:, None, None]
    sky = np.exp(-np.abs(vv - horizon_v) / 260.0)
    bg = (np.array([0.0004, 0.0006, 0.0010]) + np.array([0.0022, 0.0030, 0.0046]) * sky).astype(np.float32)
    bg = np.broadcast_to(bg, (H, W, 3))

    wp = cv2.resize(WISP, (W // 4, H // 4))
    shift = int(t * 9) % wp.shape[1]
    wp = np.roll(wp, shift, axis=1) * 0.6 + np.roll(wp[::-1], -int(t * 5) % wp.shape[1], axis=1) * 0.4
    wisp = cv2.resize(wp, (W, H), interpolation=cv2.INTER_CUBIC)[..., None]
    lightfield = direct + 0.5 * reflection
    haze = (blur(lightfield, 50) * 0.5 + blur(lightfield, 140) * 0.6) * (0.28 + 1.6 * wisp)
    bloom = blur(direct, 5) * 0.22 + blur(direct, 18) * 0.16

    img = bg + direct + reflection + diffuse + haze + bloom

    if head_e > 0:
        hu, hv, hz = project(head[None], pos, basis)
        if hz[0] > 0.2:
            yy, xx = GRID_V, GRID_U
            r2 = ((xx - hu[0]) ** 2 + (yy - hv[0]) ** 2) / (60.0 * 3.5 / hz[0]) ** 2
            glow = up2(head_e * 0.10 / (1 + r2)) [..., None] * head_col
            img += glow * (0.6 + 0.8 * wisp)
            # a faint anamorphic streak through the point
            st = np.exp(-((ys - hv[0]) ** 2) / (2 * 1.6 ** 2)) * np.exp(-np.abs(xs - hu[0]) / 170.0)
            img += (st * head_e * 0.018)[..., None] * np.array([0.55, 0.75, 1.0], np.float32)

    # ------------------------------------------------------------ develop
    exposure = 1.0
    out = 1.0 - np.exp(-img * exposure)
    out = np.power(np.clip(out, 0, 1), 1 / 2.2)
    # vignette
    if not hasattr(render_frame, "_vig"):
        r = np.sqrt(((xs - W / 2) / (W / 2)) ** 2 + ((ys - H / 2) / (H / 2)) ** 2)
        render_frame._vig = (1 - 0.32 * smoothstep(r / 1.35) ** 1.3)[..., None].astype(np.float32)
    out *= render_frame._vig
    # captions
    for c in caps:
        if c["t0"] - 0.1 < t < c["t1"] + 1.4:
            a = smoothstep((t - c["t0"]) / 1.1) * (1 - smoothstep((t - c["t1"]) / 1.3))
            if a > 0:
                im = c["img"]
                hh, ww = im.shape
                y0, x0 = c["y"], c["x"]
                region = out[y0:y0 + hh, x0:x0 + ww]
                aa = (im[:region.shape[0], :region.shape[1]] * a * 0.88)[..., None]
                region[:] = region * (1 - aa) + np.array([0.93, 0.92, 0.9], np.float32) * aa
    # fade in / out
    fade = smoothstep(t / 0.8) * (1 - smoothstep((t - (tl.duration - 1.6)) / 1.5))
    out *= fade
    rng = np.random.default_rng(fi)
    grain = rng.standard_normal((H // 2, W // 2)).astype(np.float32)
    grain = cv2.resize(grain, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    out += grain * 0.011
    return np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8)


# ============================================================== pipeline
TL = FLOOR = CAPS = None


def setup():
    global TL, CAPS
    TL = Timeline(build_story())
    CAPS = build_captions(TL)
    return TL


def render_chunk(args):
    f0, f1, path = args
    floor = FloorLight(TL)
    ff = __import__("imageio_ffmpeg").get_ffmpeg_exe()
    proc = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                             "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
                             "-x264-params", "keyint=60", path], stdin=subprocess.PIPE)
    t0 = time.time()
    for fi in range(f0, f1):
        floor.advance(TL.head_idx[fi])
        proc.stdin.write(render_frame(fi, TL, floor, CAPS).tobytes())
        if (fi - f0) % 50 == 0:
            print(f"  chunk {f0}: frame {fi} ({(time.time() - t0) / (fi - f0 + 1):.2f}s/f)", flush=True)
    proc.stdin.close()
    proc.wait()
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", default="")
    ap.add_argument("--out", default=os.path.join(HERE, "evolution_of_light.mp4"))
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    ap.add_argument("--tmp", default=os.environ.get("TMPDIR", "/tmp"))
    args = ap.parse_args()
    tl = setup()
    print(f"trail samples {len(tl.P)}, duration {tl.duration:.1f}s, frames {tl.nframes}")
    for t0, ch in tl.chapters:
        print(f"  {t0:6.1f}s  {ch[0]}")
    if args.stills:
        for fs in args.stills.split(","):
            fi = int(float(fs) * FPS) if "." in fs else int(fs)
            floor = FloorLight(tl)
            floor.advance(tl.head_idx[fi])
            t0 = time.time()
            img = render_frame(fi, tl, floor, CAPS)
            out = os.path.join(args.tmp, f"still_{fi:05d}.png")
            cv2.imwrite(out, img[..., ::-1])
            print(out, f"{time.time() - t0:.2f}s")
        return
    n = tl.nframes
    k = args.workers * 2
    bounds = np.linspace(0, n, k + 1).astype(int)
    jobs = [(bounds[i], bounds[i + 1], os.path.join(args.tmp, f"chunk_{i:02d}.mp4")) for i in range(k)]
    with Pool(args.workers) as pool:
        parts = pool.map(render_chunk, jobs, chunksize=1)
    lst = os.path.join(args.tmp, "chunks.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    ff = __import__("imageio_ffmpeg").get_ffmpeg_exe()
    subprocess.check_call([ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                           "-c", "copy", "-movflags", "+faststart", args.out])
    print("wrote", args.out)


if __name__ == "__main__":
    main()
