"""stings: sound design for the five IDEABRO STUDIO logo animations, synthesised in numpy (no samples).

Neon flicker and glitch frames are re-derived here with the same hash the picture uses (stage.js E.hash),
so every buzz and stutter lands on the exact frame it is seen.
"""
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
sys.path.insert(0, str(HERE.parent / "logo-b"))
import music as M  # noqa: E402
from sting import chime, clang, crack, fade, put, reverse_swell, swish  # noqa: E402

SR = M.SR
U32 = 0xFFFFFFFF


def jhash(*k):
    """stage.js E.hash, bit for bit."""
    h = 2166136261
    for v in k:
        h = (h ^ (math.floor(v * 1000) & U32)) & U32
        h = (h * 16777619) & U32
    h ^= h >> 13
    h = (h * 0x5BD1E995) & U32
    h ^= h >> 15
    return h / 4294967295


def tone(f, dur, decay=4.0, kind="sin"):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) if kind == "sin" else M.osc_saw(f, n)
    return (x * np.exp(-t * decay)).astype(np.float32)


def thud(f=55, dur=0.8, drop=2.0):
    n = int(dur * SR); t = np.arange(n) / SR
    return M.osc_sin(f * (1 + drop * np.exp(-t * 25)), n) * np.exp(-t * 6)


def whoosh(dur=0.5, lo=300, hi=6000):
    n = int(dur * SR); t = np.arange(n) / SR; k = t / dur
    x = M.sweep(M.noise(n), lambda tb: lo + (hi - lo) * (tb / dur) ** 1.5, "lp")
    return x * np.sin(np.pi * k) ** 2 * 0.6


def drip(f):
    n = int(0.12 * SR); t = np.arange(n) / SR
    return M.osc_sin(f * (1 + 1.2 * np.exp(-t * 60)), n) * np.exp(-t * 40) * 0.6


def master(dry, wet, out, hall=(2.6, 1.8, 7500)):
    mix = dry + M.conv_reverb(wet, M.reverb_ir(*hall, 0.02)) * 0.9 + M.conv_reverb(dry, M.reverb_ir(0.9, 5, 6000)) * 0.1
    mix = M.filt(mix, "hp", 28)
    mix = M.compressor(mix, -10, 1.6, 0.02, 0.25, 0.0, knee=6)
    k = int(0.7 * SR); mix[-k:] *= np.linspace(1, 0, k)[:, None] ** 1.5
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.89
    import soundfile as sf
    from vibelib import ff, loudnorm_filter
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    raw = Path(out).with_name("sting_raw.wav")
    sf.write(raw, mix, SR, subtype="FLOAT")
    ff("-i", raw, "-af", loudnorm_filter(raw, -14.0, -1.0, 11), "-ar", str(SR), "-c:a", "pcm_s24le", out)
    print("->", out)


# ---------------------------------------------------------------- 1 liquid chrome
def chrome(T, dry, wet, dur):
    rng = np.random.default_rng(1)
    n = int(T["melt"] * SR + 0.6 * SR); t = np.arange(n) / SR
    # the blob: a slow gloopy wobble (resonant noise + a wobbling low tone)
    gl = M.sweep(M.noise(n), lambda tb: 250 + 450 * (0.5 + 0.5 * np.sin(2 * np.pi * 1.7 * tb)) + 300 * tb, "lp")
    wob = M.osc_sin(90 * (1 + 0.15 * np.sin(2 * np.pi * 2.3 * t)), n) * 0.5
    put(dry, fade((gl * 0.35 + wob) * np.minimum(1, t / 0.4), 0.05, 0.3), 0.1, -14)
    for k in range(9):                                     # bubbles
        put(dry, drip(rng.uniform(300, 700)), 0.2 + 1.2 * rng.random(), -18, rng.uniform(-0.6, 0.6))
    put(dry, M.reverse_crash(1.0), T["form"] - 1.0, -14)
    put(dry, whoosh(0.7, 200, 8000), T["form"] - 0.35, -12)
    # the splash + form
    put(dry, M.filt(M.impact(2.5, 31), "hp", 32), T["form"], -2)
    put(dry, M.filt(M.noise(int(0.6 * SR)), "bp", (800, 9000)) * np.exp(-np.arange(int(0.6 * SR)) / SR * 9) * 0.7, T["form"], -8)
    put(wet, crack(), T["form"], -9)
    for k in range(14):                                    # droplets landing
        put(dry, drip(rng.uniform(900, 2600)), T["form"] + 0.3 + 1.6 * rng.random() ** 1.3, -15 - 6 * rng.random(), rng.uniform(-0.8, 0.8))
    cl = clang(392.0, 3.5)
    put(dry, cl, T["form"] + 0.02, -14, 0.2); put(wet, cl, T["form"] + 0.02, -12)
    put(wet, chime([86, 93, 98], 3.5), T["form"] + 0.25, -13)
    put(dry, swish(1.6), T["form"] + 0.8, -15)
    put(dry, fade(M.pad([50, 57, 62, 66], dur - T["form"], cutoff=1200, a=0.4, r=1.2), 0.3, 1.2), T["form"], -17)


# ---------------------------------------------------------------- 2 particle storm
def particles(T, dry, wet, dur):
    rng = np.random.default_rng(2)
    span = T["land"] + 0.1
    n = int(span * SR); t = np.arange(n) / SR; k = t / span
    # swirling wind: band-limited noise whose colour and pan circle around
    x = M.sweep(M.noise(n), lambda tb: 500 + 3500 * (tb / span) ** 1.5 + 600 * np.sin(2 * np.pi * 1.3 * tb), "lp")
    x = M.filt(x, "hp", 250) * (0.25 + 0.75 * k ** 1.2)
    pan = np.sin(2 * np.pi * (0.6 + 1.4 * k) * t)
    a = (pan + 1) * np.pi / 4
    put(dry, fade(np.stack([x * np.cos(a), x * np.sin(a)], 1) * 1.2, 0.3, 0.05), 0.0, -10)
    # sparkle grains, denser as they converge
    for _ in range(260):
        tt = span * rng.random() ** 0.7
        g = tone(rng.uniform(2500, 7000), 0.05, 70) * 0.5
        put(dry, g, tt, -22 + 6 * tt / span, rng.uniform(-0.9, 0.9))
    put(dry, M.riser(span - 0.6, 12000), 0.6, -14)
    put(dry, M.reverse_crash(1.3), T["flat"] - 1.3, -11)
    # lock
    put(dry, M.filt(M.impact(2.8, 33), "hp", 32), T["flat"], -2)
    put(wet, crack(), T["flat"], -10)
    notes = [74, 81, 86, 90, 93]
    put(dry, chime(notes, dur - T["flat"]), T["flat"], -10); put(wet, chime(notes, dur - T["flat"]), T["flat"], -9)
    put(dry, fade(M.pad([62, 69, 74, 78], dur - T["flat"] + 0.3, cutoff=1500, a=0.3, r=1.2), 0.2, 1.2), T["flat"] - 0.1, -17)
    for _ in range(40):                                    # settling glitter
        put(wet, tone(rng.uniform(3000, 8000), 0.08, 40) * 0.4, T["flat"] + 0.1 + 2.5 * rng.random() ** 1.5, -22, rng.uniform(-1, 1))


# ---------------------------------------------------------------- 3 neon sign
def flick(t, t0, seed):
    """s3-neon.js flick(), same hash."""
    if t < t0:
        return 0.0
    dt, f = t - t0, math.floor(t * 40)
    if dt < 0.6:
        return 1.0 if jhash(f, seed) > 0.62 - dt * 1.0 else 0.08 * jhash(f, seed + 9)
    return 0.35 if jhash(f, seed + 4) > 0.992 else 1.0


def neon(T, dry, wet, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    room = M.filt(M.noise(n), "lp", 500) * 0.08
    put(dry, np.stack([room, M.filt(M.noise(n), "lp", 500) * 0.08], 1), 0.0, -12)
    signs = [(T["b"], 1, 1.0, 0.0), (T["name"], 2, 0.8, -0.15), (T["studio"], 3, 0.6, 0.15)]
    for t0, seed, lvl, pan in signs:
        # gate per 1/40 s frame, exactly as the picture
        fr = np.array([flick(i / 40, t0, seed) for i in range(int(dur * 40) + 1)])
        gate = np.repeat(fr, SR // 40)[:n]
        gate = np.convolve(gate, np.ones(48) / 48, mode="same")          # 1 ms edges, no clicks
        hum = (M.osc_saw(120, n) * 0.5 + M.osc_saw(240.7, n) * 0.25 + M.osc_sin(60, n) * 0.6)
        settle = np.interp(t, [t0 + 0.6, t0 + 1.2], [1.0, 0.4])            # steady hum sits back once it's lit
        buzz = M.filt(hum, "bp", (90, 3200)) * gate * settle * 0.35 * lvl
        put(dry, buzz, 0.0, -14, pan)
        # a zap on every off->on edge, a relay clunk on the first
        on = (fr[1:] > 0.5) & (fr[:-1] <= 0.5)
        for i in np.nonzero(on)[0]:
            z = M.filt(M.noise(int(0.04 * SR)), "hp", 2000) * np.exp(-np.arange(int(0.04 * SR)) / SR * 120)
            put(dry, z, (i + 1) / 40, -15, pan)
        put(dry, thud(70, 0.4, 1.0) * 0.7, t0, -10, pan)
        put(dry, M.filt(M.noise(int(0.02 * SR)), "hp", 1500), t0, -12, pan)
    # warm resolve once everything is lit
    put(dry, fade(M.pad([50, 57, 62, 66, 69], dur - T["full"] + 0.6, cutoff=1300, a=0.5, r=1.2), 0.4, 1.2), T["full"] - 0.6, -17)
    put(dry, M.sub(38, dur - T["full"]) * 0.5, T["full"], -18)
    put(wet, chime([74, 78, 81, 86], 3.0), T["full"], -16)


# ---------------------------------------------------------------- 4 glitch
def glitch_amt(t, T):
    """s4-glitch.js glitch amount, same hash."""
    io = lambda k: 4 * k ** 3 if k < 0.5 else 1 - (-2 * k + 2) ** 3 / 2
    prog = lambda t, t0, d: min(1, max(0, (t - t0) / d))
    boot = 1 - io(prog(t, T["in"], T["settle"] - T["in"]))
    burst = 0.5 if jhash(math.floor(t * 14), 5) > 0.72 else 0
    amt = 0 if t < T["in"] else min(1, boot * (0.55 + burst + 0.45 * jhash(math.floor(t * 30), 2)))
    for b in T["blips"]:
        dt = t - b
        if 0 < dt < 0.22:
            amt = max(amt, 0.75 * (1 if jhash(math.floor(t * 30), 8) > 0.3 else 0.2))
    return amt


def glitch(T, dry, wet, dur):
    rng = np.random.default_rng(4)
    fl = SR // 30
    for i in range(int(dur * 30)):
        t = i / 30 + 1e-4
        a = glitch_amt(t, T)
        if a < 0.05:
            continue
        kind = jhash(i, 77)
        if kind < 0.4:      # data chirp
            f0 = 200 + 3000 * jhash(i, 78)
            x = M.osc_sq(f0 * (1 + 0.5 * np.sin(np.arange(fl) / fl * 6)), fl) * 0.3
        elif kind < 0.75:   # bitcrushed noise
            x = M.noise(fl); step = int(4 + 40 * jhash(i, 79)); x = np.repeat(x[::step], step)[:fl] * 0.5
        else:               # stuttered low buzz
            x = M.osc_saw(55 * (1 + int(jhash(i, 80) * 4)), fl) * 0.4
        x = x * np.hanning(fl) ** 0.2
        put(dry, x, i / 30, -10 - 8 * (1 - a), rng.uniform(-0.7, 0.7))
    put(dry, M.riser(T["settle"] - T["in"], 9000), T["in"], -18)
    # the snap into focus
    put(dry, M.filt(M.impact(2.2, 33), "hp", 32), T["settle"], -3)
    tick = M.filt(M.noise(int(0.06 * SR)), "hp", 3000) * np.exp(-np.arange(int(0.06 * SR)) / SR * 80)
    put(dry, tick, T["settle"], -6)
    put(wet, chime([81, 86, 93], 3.0), T["settle"], -12)
    put(dry, fade(M.pad([57, 64, 69, 73], dur - T["settle"], cutoff=1600, a=0.2, r=1.0), 0.1, 1.0), T["settle"], -21)
    put(dry, M.sub(33, dur - T["settle"]) * 0.4, T["settle"], -16)


# ---------------------------------------------------------------- 5 heavy metal
def metal(T, dry, wet, dur):
    rng = np.random.default_rng(5)
    def land(t0, size, f):
        put(dry, whoosh(0.32, 150, 3000 + 3000 * size), t0 - 0.3, -16 + 4 * size)
        put(dry, M.filt(thud(48 + 20 * (1 - size), 1.0, 2.5), "hp", 30), t0, -4 - 8 * (1 - size))
        cl = clang(f, 1.2 + 2.5 * size)
        put(dry, cl, t0, -9 - 6 * (1 - size), rng.uniform(-0.3, 0.3)); put(wet, cl, t0, -12)
        deb = M.filt(M.noise(int(0.5 * SR)), "bp", (300, 5000)) * np.exp(-np.arange(int(0.5 * SR)) / SR * (8 / size))
        put(dry, deb * 0.6, t0 + 0.01, -12 - 6 * (1 - size))
    land(T["b"], 1.0, 110.0)
    sizz = M.filt(M.noise(int(0.9 * SR)), "hp", 5000) * np.exp(-np.arange(int(0.9 * SR)) / SR * 4) * 0.5
    put(dry, sizz, T["b"] + 0.02, -12)                                # sparks
    put(dry, M.filt(M.impact(3.0, 29), "hp", 30), T["b"], -3)
    for i, t0 in enumerate(T["name"]):
        land(t0, 0.45, 150.0 * 2 ** (i / 12 * 2))
    land(T["studio"], 0.6, 210.0)
    # crane up: low brass swell into the hero view
    put(dry, M.filt(M.brass_braam(38, T["rise1"] - T["rise"] + 1.5), "lp", 1800), T["rise"], -14)
    put(dry, M.riser(T["rise1"] - T["rise"], 6000), T["rise"], -18)
    put(dry, M.filt(M.impact(2.0, 33), "hp", 30) * 0.6, T["rise1"], -10)
    put(wet, chime([62, 69, 74, 81], 2.5), T["rise1"], -16)
    put(dry, fade(M.pad([50, 57, 62, 65], dur - T["rise"], cutoff=1100, a=0.8, r=1.0), 0.5, 1.0), T["rise"], -22)


DESIGN = {"chrome": chrome, "particles": particles, "neon": neon, "glitch": glitch, "metal": metal}


def build(style, T, out):
    dur = T["dur"]
    n = int(dur * SR)
    dry = np.zeros((n, 2), np.float32)
    wet = np.zeros((n, 2), np.float32)
    DESIGN[style](T, dry, wet, dur)
    master(dry, wet, out)
