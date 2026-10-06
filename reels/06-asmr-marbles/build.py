"""Reel 06: oddly satisfying marble sorter. Glass marbles roll down acrylic ramps and drop into
colour-sorted tubes. Every click is synthesised for the exact frame a marble lands.

    python3 build.py sheet | stills 1 5 9 | draft | render | sound | all
"""
import math
import sys
from pathlib import Path

import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
sys.path.insert(0, str(HERE))
from kit import (W, H, WHITE, Captions, Film, clamp, col, e_back, e_io, e_out, endcard, fill, lerp,  # noqa: E402
                 lin_grad, mixc, prog, rad_grad, rrect, stroke)
from script import LINES, VOICE  # noqa: E402
from voice import Script, narrate  # noqa: E402

vo = narrate(LINES, HERE / "work", VOICE)
FPS = 30

# ---------------------------------------------------------------- the machine
R = 40
G = 4200.0                       # px/s^2
V = 820.0                        # rolling speed on ramps
COLORS = ["#FF8FB1", "#FFB27A", "#FFE07A", "#8FE3B0", "#8CC8FF", "#B9A3FF"]
TUBE_X = [140, 300, 460, 620, 780, 940]
TUBE_TOP, TUBE_BOT, TUBE_W = 1240, 1760, 112
RAMPS = [((105, 440), (960, 560)), ((990, 650), (120, 770)), ((90, 860), (960, 980))]
RAIL = ((1010, 1120), (60, 1150))
CHUTE = (150, 300)
N = 36
SPAWN0, GAP = 0.25, 0.43


def on_line(a, b, x):
    k = (x - a[0]) / (b[0] - a[0])
    return a[1] + (b[1] - a[1]) * k


def surface_pt(a, b, x):
    """marble centre resting on line ab at x."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    nx, ny = dy / L, -dx / L
    if ny > 0:
        nx, ny = -nx, -ny
    return x + nx * (R + 7), on_line(a, b, x) + ny * (R + 7)


def build_schedule():
    rng = np.random.default_rng(12)
    order = np.array([i % 6 for i in range(N)])
    rng.shuffle(order)
    marbles = []
    for i in range(N):
        tube = int(order[i])
        t = SPAWN0 + i * GAP
        segs = []
        # fall from the chute onto ramp 1
        x = CHUTE[0]
        p_land = surface_pt(*RAMPS[0], x)
        segs.append(("fall", t, (x, CHUTE[1]), p_land))
        t = segs[-1][1] + math.sqrt(2 * (p_land[1] - CHUTE[1]) / G)
        lands = [t]
        xs = [(150, 930), (930, 150), (150, 930)]
        for ri, (ramp, (x0, x1)) in enumerate(zip(RAMPS, xs)):
            p0, p1 = surface_pt(*ramp, x0), surface_pt(*ramp, x1)
            dur = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) / V
            segs.append(("roll", t, p0, p1, dur))
            t += dur
            nxt = RAMPS[ri + 1] if ri + 1 < len(RAMPS) else RAIL
            p2 = surface_pt(*nxt, x1)
            segs.append(("fall", t, p1, p2))
            t += math.sqrt(2 * max(1, p2[1] - p1[1]) / G)
            lands.append(t)
        # along the rail to its tube
        p0 = surface_pt(*RAIL, 930)
        p1 = surface_pt(*RAIL, TUBE_X[tube])
        dur = abs(p1[0] - p0[0]) / 700
        segs.append(("roll", t, p0, p1, dur))
        t += dur
        k = sum(1 for m in marbles if m["tube"] == tube)
        stack_y = TUBE_BOT - 8 - R - k * (2 * R + 2)
        segs.append(("drop", t, p1, (TUBE_X[tube], stack_y)))
        t_land = t + math.sqrt(2 * (stack_y - p1[1]) / G)
        lands.append(t_land)
        marbles.append(dict(tube=tube, color=COLORS[tube], segs=segs, lands=lands, t0=SPAWN0 + i * GAP,
                            t_land=t_land, stack=k, seed=i))
    return marbles


MARBLES = build_schedule()
LAST_LAND = max(m["t_land"] for m in MARBLES)
CAPS_T = [LAST_LAND + 0.35 + 0.12 * i for i in range(6)]
S = Script(vo, [("hook", 0.4), ("click", 0.8), ("marble", 0.4), ("code", 0.4), ("nos", 0.9), ("one", 0.9),
                ("end", "@", LAST_LAND + 0.4)])
END_T = S.end("end") + 0.9
DUR = END_T + 3.0


def marble_state(m, t):
    """(x, y, spin) or None before spawn."""
    if t < m["t0"]:
        return None
    segs = m["segs"]
    for j, sg in enumerate(segs):
        nxt_t = segs[j + 1][1] if j + 1 < len(segs) else 1e9
        if t < nxt_t:
            kind, t0 = sg[0], sg[1]
            dt = t - t0
            if kind == "fall":
                (x0, y0), (x1, y1) = sg[2], sg[3]
                tf = math.sqrt(2 * max(1, y1 - y0) / G)
                k = clamp(dt / tf)
                return x0 + (x1 - x0) * k, y0 + 0.5 * G * min(dt, tf) ** 2, dt * 3
            if kind == "roll":
                (x0, y0), (x1, y1), dur = sg[2], sg[3], sg[4]
                k = clamp(dt / dur)
                x, y = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
                return x, y, (x - x0) / R
            if kind == "drop":
                (x0, y0), (x1, y1) = sg[2], sg[3]
                tf = math.sqrt(2 * (y1 - y0) / G)
                if dt < tf:
                    return x1, y0 + 0.5 * G * dt * dt, dt * 2
                # little damped bounce after landing
                b = dt - tf
                bounce = 18 * abs(math.sin(b * 22)) * math.exp(-b * 9)
                return x1, y1 - bounce, 0.0
    return None


# ---------------------------------------------------------------- drawing
def marble(c, x, y, colr, spin, seed, r=R):
    base = colr
    c.drawOval(skia.Rect.MakeXYWH(x - r * 0.8, y + r * 0.72, r * 1.6, r * 0.45), fill("#5A3A60", 0.18, blur=8))
    c.drawCircle(x, y + r * 0.9, r * 0.75, fill(base, 0.25, blur=14))          # caustic glow
    c.drawCircle(x, y, r, rad_grad(x - r * 0.25, y - r * 0.3, r * 1.25,
                                   [mixc(base, "#FFFFFF", 0.55), base, mixc(base, "#3A2050", 0.35)], [0, 0.55, 1]))
    # swirl inside the glass, rotating with the roll
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(x - r, y - r, 2 * r, 2 * r))
    path = skia.Path()
    path.addCircle(x, y, r * 0.92)
    c.clipPath(path, skia.ClipOp.kIntersect, True)
    c.translate(x, y)
    c.rotate(math.degrees(spin) + seed * 40)
    p = skia.Path()
    p.moveTo(-r, r * 0.2)
    p.cubicTo(-r * 0.3, -r * 0.6, r * 0.3, r * 0.6, r, -r * 0.2)
    c.drawPath(p, stroke(WHITE, r * 0.22, 0.38, blur=2))
    c.drawPath(p, stroke(mixc(base, "#000000", 0.25), r * 0.08, 0.35))
    c.restore()
    c.drawCircle(x, y, r, stroke(mixc(base, "#2A1A40", 0.4), 2, 0.35))
    c.drawOval(skia.Rect.MakeXYWH(x - r * 0.55, y - r * 0.68, r * 0.55, r * 0.34), fill(WHITE, 0.9, blur=2))
    c.drawCircle(x + r * 0.42, y + r * 0.45, r * 0.09, fill(WHITE, 0.6))


def acrylic(c, a, b, w=16):
    p = skia.Path()
    p.moveTo(*a)
    p.lineTo(*b)
    c.save()
    c.translate(0, 12)
    c.drawPath(p, stroke("#6B4C7A", w, 0.12, blur=10))
    c.restore()
    c.drawPath(p, stroke("#C9B4EA", w + 6, 0.85))
    c.drawPath(p, stroke("#E6DAF7", w, 0.95))
    p2 = skia.Path()
    p2.moveTo(a[0], a[1] - w * 0.3)
    p2.lineTo(b[0], b[1] - w * 0.3)
    c.drawPath(p2, stroke("#FFFFFF", 3, 0.95))


def tube_back(c, x):
    c.drawRRect(rrect(x - TUBE_W / 2, TUBE_TOP + 16, TUBE_W, TUBE_BOT - TUBE_TOP, TUBE_W / 2),
                fill("#8A6AA8", 0.12, blur=14))
    c.drawRRect(rrect(x - TUBE_W / 2, TUBE_TOP, TUBE_W, TUBE_BOT - TUBE_TOP, TUBE_W / 2), fill("#FFFFFF", 0.35))
    c.drawRRect(rrect(x - TUBE_W / 2, TUBE_TOP, TUBE_W, TUBE_BOT - TUBE_TOP, TUBE_W / 2), stroke("#BBA6DA", 4, 0.7))


def tube_front(c, x, t, i, colr):
    c.drawRect(skia.Rect.MakeXYWH(x - TUBE_W / 2 + 12, TUBE_TOP + 30, 10, TUBE_BOT - TUBE_TOP - 80),
               fill(WHITE, 0.55, blur=2))
    c.drawRect(skia.Rect.MakeXYWH(x + TUBE_W / 2 - 18, TUBE_TOP + 40, 5, TUBE_BOT - TUBE_TOP - 100), fill(WHITE, 0.3))
    c.drawOval(skia.Rect.MakeXYWH(x - TUBE_W / 2, TUBE_TOP - 10, TUBE_W, 20), stroke("#FFFFFF", 4, 0.8))
    # cap pops on at the end
    k = e_back(prog(t, CAPS_T[i], 0.35), 2.2)
    if k > 0:
        y = TUBE_TOP - 26 - 60 * (1 - k)
        c.drawRRect(rrect(x - TUBE_W / 2 - 6, y, TUBE_W + 12, 34, 14), fill(colr))
        c.drawRRect(rrect(x - TUBE_W / 2 - 6, y, TUBE_W + 12, 14, 7), fill(WHITE, 0.4))
        g = math.exp(-max(0, t - CAPS_T[i]) * 3)
        c.drawRRect(rrect(x - TUBE_W / 2 - 8, TUBE_TOP - 30, TUBE_W + 16, TUBE_BOT - TUBE_TOP + 40, TUBE_W / 2),
                    fill(colr, 0.35 * g, blur=30))


def scene(c, t):
    c.drawPaint(lin_grad(0, 0, 0, H, ["#FFF4EC", "#FBE3EE", "#EADFF8"]))
    c.drawCircle(W * 0.8, 260, 420, fill("#FFFFFF", 0.35, blur=120))
    # chute
    cx, cy = CHUTE
    c.drawRRect(rrect(cx - 62, cy - 130, 124, 110, 30), fill("#FFFFFF", 0.55))
    c.drawRRect(rrect(cx - 62, cy - 130, 124, 110, 30), stroke("#FFFFFF", 3, 0.9))
    for a, b in RAMPS:
        acrylic(c, a, b)
    acrylic(c, RAIL[0], RAIL[1], 14)
    # gates above the tubes
    for x in TUBE_X:
        y = on_line(*RAIL, x)
        c.drawLine(x - 30, y + 14, x + 30, y + 14, stroke("#D9C8EE", 5, 0.9))
    for i, x in enumerate(TUBE_X):
        tube_back(c, x)
    states = [(m, marble_state(m, t)) for m in MARBLES]
    # marbles in tubes first (behind the glass front), then the moving ones
    for m, st in states:
        if st and t >= m["segs"][-1][1]:
            marble(c, st[0], st[1], m["color"], st[2], m["seed"])
    for i, x in enumerate(TUBE_X):
        tube_front(c, x, t, i, COLORS[i])
    for m, st in states:
        if st and t < m["segs"][-1][1]:
            marble(c, st[0], st[1], m["color"], st[2], m["seed"])
    # marbles waiting in the chute
    waiting = [m for m in MARBLES if m["t0"] > t][:2]
    for j, m in enumerate(waiting):
        marble(c, cx, cy - 72 + j * 0, m["color"], 0, m["seed"], r=R * 0.9) if j == 0 else None


def draw(c, t, f):
    # slow, calm push-in; settles back out for the finale
    z = 1.0 + 0.04 * e_io(prog(t, 0, LAST_LAND)) - 0.04 * e_io(prog(t, LAST_LAND, 1.5))
    c.save()
    c.translate(W / 2, H / 2)
    c.scale(z, z)
    c.translate(-W / 2, -H / 2)
    scene(c, t)
    c.restore()
    if t >= END_T:
        endcard(c, t, END_T)
    CAP.draw(c, t)


CAP = Captions(S.words(), y=210, size=66, name="heavy", box=True)
film = Film(draw, DUR, FPS, out_dir=HERE / "out")


# ---------------------------------------------------------------- sound
def sound():
    import audio_kit as ak
    from sound import Mix, verb
    SR = ak.SR
    m = Mix(DUR)
    m.voice(S.placements(), gain_db=1.5)
    rng = np.random.default_rng(4)

    def clack(pitch=1.0, hard=1.0):
        d = 0.32
        n = int(d * SR)
        t = np.arange(n) / SR
        x = np.zeros(n, np.float32)
        for f, a, k in ((2350, 1.0, 38), (3920, 0.7, 48), (5600, 0.45, 60), (7300, 0.25, 75), (1480, 0.35, 30)):
            x += a * np.sin(2 * np.pi * f * pitch * (1 + rng.uniform(-0.01, 0.01)) * t) * np.exp(-t * k)
        tr = ak.filt(rng.uniform(-1, 1, n).astype(np.float32), "hp", 3000) * np.exp(-t * 400)
        return (0.5 * x + 0.6 * tr) * hard

    def thock(pitch=1.0):
        d = 0.18
        n = int(d * SR)
        t = np.arange(n) / SR
        return 0.6 * np.sin(2 * np.pi * 420 * pitch * t) * np.exp(-t * 45) + \
            0.3 * ak.filt(rng.uniform(-1, 1, n).astype(np.float32), "bp", (800, 3000)) * np.exp(-t * 90)

    fx = np.zeros((int(DUR * SR), 2), np.float32)
    roll = np.zeros(int(DUR * SR), np.float32)
    for mm in MARBLES:
        pan = (mm["segs"][-1][3][0] / W - 0.5) * 1.2
        for j, tl in enumerate(mm["lands"]):
            last = j == len(mm["lands"]) - 1
            if last:
                ak.place(fx, clack(rng.uniform(0.92, 1.12), 1.0), tl, -4, pan)
                ak.place(fx, clack(rng.uniform(1.0, 1.2), 0.35), tl + 0.07, -8, pan)
            else:
                ak.place(fx, thock(rng.uniform(0.9, 1.1)), tl, -12, (0.6 if j % 2 else -0.6))
        for sg in mm["segs"]:
            if sg[0] == "roll":
                a, b = int(sg[1] * SR), int((sg[1] + sg[4]) * SR)
                roll[a:b] += 1
    # rolling rumble: filtered noise scaled by how many marbles are rolling
    nz = ak.filt(rng.uniform(-1, 1, len(roll)).astype(np.float32), "bp", (180, 900))
    nz *= 1 + 0.5 * np.sin(np.arange(len(roll)) / SR * 2 * np.pi * 23)
    sm = np.convolve(roll, np.ones(int(0.05 * SR)) / int(0.05 * SR), mode="same")
    fx += np.stack([nz * sm * 0.05] * 2, 1)
    fx = verb(fx, 0.18)
    m.fx += fx * ak.db(-2)
    for i, tc in enumerate(CAPS_T):
        m.sfx(thock(1.4 + 0.1 * i), tc + 0.1, -6, (i - 2.5) / 3)
    m.sfx("sparkle", CAPS_T[-1] + 0.2, -12)
    # very soft ambient pad
    pad = np.zeros((int((DUR + 1) * SR), 2), np.float32)
    chords = [[57, 61, 64, 68], [54, 57, 61, 64], [50, 54, 57, 61], [52, 56, 59, 64]]
    for k in range(int(DUR / 4) + 1):
        ak.place(pad, ak.pad_chord(chords[k % 4], 4.4, 900), k * 4.0, 0)
    m.music(verb(pad, 0.4), gain_db=-24, duck_db=-4, fade_in=2.0)
    m.sfx("whoosh", END_T - 0.25, -14)
    m.sfx("ding", END_T + 0.1, -14)
    m.finish(HERE / "out" / "picture.mp4", HERE / "out" / "06_asmr_marbles.mp4", HERE / "work")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    print(f"duration {DUR:.2f}s, last marble lands {LAST_LAND:.2f}s, 'end' line at {S.t('end'):.2f}s")
    if cmd == "sheet":
        film.sheet()
    elif cmd == "stills":
        film.stills([float(x) for x in sys.argv[2:]])
    elif cmd == "draft":
        film.render(draft=True)
    elif cmd == "render":
        film.render()
    elif cmd == "sound":
        sound()
    elif cmd == "all":
        film.render()
        sound()
