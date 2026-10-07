"""sting: the sound design for the logo animation, synthesised in numpy (no samples), locked to the picture's key times.

  dark drone -> electric 'draw' of the light trace (pans with the heads) -> riser + scan hum ->
  impact (sub boom, crack, metal clang, braam) -> glassy sweep -> reverse swell -> lock-up chime -> tail
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))
import music as M  # noqa: E402

SR = M.SR
RNG = np.random.default_rng(11)


def put(buf, x, t, gain_db=0.0, pan=0.0):
    x = np.asarray(x, np.float32)
    if x.ndim == 1:
        x = M.pan2(x, pan) * 0.7071
    i = int(round(t * SR))
    if i >= len(buf):
        return
    x = x[: len(buf) - i]
    buf[i:i + len(x)] += x * M.db(gain_db)


def fade(x, a=0.01, r=0.05):
    n = len(x); e = np.ones(n, np.float32)
    na, nr = int(a * SR), int(r * SR)
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[-nr:] *= np.linspace(1, 0, nr)
    return x * (e[:, None] if x.ndim == 2 else e)


def drone(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    x = (M.osc_sin(M.hz(38), n) * 0.5 + M.osc_sin(M.hz(45), n) * 0.2 + M.osc_saw(M.hz(50) * 1.003, n) * 0.08)
    x = M.filt(M.filt(x, "lp", 300), "hp", 55) * (0.75 + 0.25 * np.sin(2 * np.pi * 0.21 * t))
    air = M.sweep(M.noise(n), lambda tb: 250 + 500 * tb / dur, "lp") * 0.12
    return x + air


def draw(dur, f0, f1, seed):
    """the light trace: an electric, crackling tone gliding up, with spark ticks."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR); t = np.arange(n) / SR; k = t / dur
    k2 = 0.5 - 0.5 * np.cos(np.pi * k)                       # the heads ease in and out like the picture
    f = f0 * (f1 / f0) ** k2
    mod = M.osc_sin(f * 2.01, n) * (1.5 + 2 * k2)
    ph = 2 * np.pi * np.cumsum(f / SR)
    x = np.sin(ph + mod) * (0.78 + 0.22 * np.sin(2 * np.pi * np.cumsum(31 + 24 * k2) / SR))   # soft electric flutter
    x = M.filt(x, "bp", (500, 7000)) * 0.25
    ticks = np.zeros(n, np.float32)
    for _ in range(int(dur * 22)):
        i = int(rng.random() * (n - 800)); ticks[i:i + 400] += rng.uniform(0.2, 1) * np.exp(-np.arange(400) / 40)
    ticks = M.filt(ticks * M.noise(n), "hp", 4500) * 0.22
    swell = np.sin(np.pi * np.clip(k, 0, 1)) ** 0.6
    return fade((x + ticks) * swell, 0.02, 0.15)


def ignite():
    n = int(0.6 * SR); t = np.arange(n) / SR
    zap = M.osc_sin(3200 * np.exp(-t * 18) + 400, n) * np.exp(-t * 14) * 0.5
    snap = M.filt(M.noise(n), "hp", 2500) * np.exp(-t * 60)
    return zap + snap


def scan_hum(dur):
    n = int(dur * SR); t = np.arange(n) / SR; k = t / dur
    x = M.osc_saw(M.hz(38), n) + M.osc_saw(M.hz(38) * 1.006, n) + 0.6 * M.osc_saw(M.hz(50), n)
    x = M.sweep(x, lambda tb: 150 + 4200 * (tb / dur) ** 2, "lp") * (k ** 1.5) * 0.25
    return fade(x, 0.05, 0.03)


def clang(f=176.0, dur=3.5):
    n = int(dur * SR); t = np.arange(n) / SR
    ratios = [(1, 1, 2.2), (2.76, 0.6, 3.0), (5.40, 0.4, 4.5), (8.93, 0.25, 6), (13.3, 0.15, 9)]
    x = sum(a * np.sin(2 * np.pi * f * r * t + 0.3 * np.sin(2 * np.pi * 3 * t)) * np.exp(-t * d) for r, a, d in ratios)
    return (x * 0.18).astype(np.float32)


def crack():
    n = int(0.5 * SR); t = np.arange(n) / SR
    return M.filt(M.noise(n), "bp", (900, 9000)) * np.exp(-t * 22) * 0.9


def swish(dur, l2r=True):
    n = int(dur * SR); t = np.arange(n) / SR; k = t / dur
    x = M.sweep(M.noise(n), lambda tb: 2000 + 9000 * np.sin(np.pi * tb / dur), "lp")
    x = M.filt(x, "hp", 1500) * np.sin(np.pi * k) ** 2 * 0.35
    p = (k * 2 - 1) * (1 if l2r else -1)
    a = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], 1) * 1.414


def chime(notes, dur=4.0):
    return sum(M.bell(m, dur) * g for m, g in zip(notes, (1, 0.8, 0.6, 0.45, 0.35)))


def reverse_swell(notes, dur):
    x = chime(notes, dur + 1.5)
    x = M.conv_reverb(np.stack([x, x], 1), M.reverb_ir(2.8, 2.0, 7000))
    x = x[: int(dur * SR)][::-1].copy()
    k = np.linspace(0, 1, len(x)) ** 2
    return x * k[:, None] * 1.6


def build(T, dur, out):
    n = int(dur * SR)
    dry = np.zeros((n, 2), np.float32)
    wet = np.zeros((n, 2), np.float32)          # goes through the big hall
    imp, lock = T["impact"], T["flat1"]

    put(dry, fade(drone(imp + 0.2), 0.8, 0.25), 0.0, -17)
    put(dry, M.downlifter(3.0), imp + 0.05, -20)
    # trace: two voices, one per direction round the outline, spread left/right
    tr = T["trace1"] - T["trace0"]
    put(dry, ignite(), T["trace0"] - 0.03, -10, -0.3)
    put(wet, ignite(), T["trace0"] - 0.03, -14, -0.3)
    put(dry, draw(tr, 700, 1650, 1), T["trace0"], -16, -0.55)
    put(dry, draw(tr, 705, 1680, 2), T["trace0"], -16, 0.55)
    put(wet, draw(tr, 700, 1650, 3), T["trace0"], -22, 0.0)
    # build to the impact
    put(dry, M.riser(imp - 1.0, 11000), 1.0, -12)
    put(dry, M.reverse_crash(1.4), imp - 1.4, -10)
    put(dry, scan_hum(imp - T["scan0"]), T["scan0"], -11)
    # impact
    put(dry, M.filt(M.impact(3.5, 31), "hp", 32), imp, 0)
    put(dry, crack(), imp, -4)
    put(wet, crack(), imp, -6)
    cl = clang(176.0)
    put(dry, cl, imp, -7, -0.15)
    put(wet, cl, imp, -7, 0.15)
    put(wet, M.crash(3.0), imp, -14)
    put(dry, M.filt(M.brass_braam(38, 2.6), "lp", 2200), imp, -11)
    # hero light sweep (left -> right, like the picture)
    put(dry, swish(T["sweep1"] - T["sweep0"]), T["sweep0"], -11)
    put(wet, chime([86, 93], 3.0), T["sweep0"] + 0.55, -17, 0.4)
    # lock-up: reverse swell into a clean chime + soft thump
    notes = [74, 81, 86, 90, 93]                   # D major add9 voicing, bright resolution
    put(dry, reverse_swell(notes, lock - T["flat0"]), T["flat0"], -11)
    put(dry, M.downlifter(1.2)[::-1].copy() * 0.6, lock - 1.2, -18)
    put(dry, chime(notes, dur - lock), lock, -9)
    put(wet, chime(notes, dur - lock), lock, -8)
    tick = M.filt(M.noise(int(0.08 * SR)), "hp", 4000) * np.exp(-np.arange(int(0.08 * SR)) / SR * 90)
    put(dry, tick, lock, -10)
    put(dry, M.impact(2.0, 38) * 0.6, lock, -12)
    put(dry, fade(M.pad([62, 69, 74, 78], dur - lock + 0.3, cutoff=1400, a=0.25, r=1.0), 0.2, 1.0), lock - 0.15, -22)

    hall = M.reverb_ir(3.2, 1.6, 7500, 0.02)
    mix = dry + M.conv_reverb(wet, hall) * 0.9 + M.conv_reverb(dry, M.reverb_ir(1.0, 5, 6000)) * 0.12
    mix = M.filt(mix, "hp", 22)
    mix = M.compressor(mix, -10, 1.6, 0.02, 0.25, 0.0, knee=6)   # gentle: keep the hit's dynamics
    k = int(0.9 * SR); mix[-k:] *= np.linspace(1, 0, k)[:, None] ** 1.5
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.89
    import soundfile as sf
    raw = Path(out).with_name("sting_raw.wav")
    sf.write(raw, mix, SR, subtype="FLOAT")
    from vibelib import ff, loudnorm_filter
    ff("-i", raw, "-af", loudnorm_filter(raw, -14.0, -1.0, 11), "-ar", str(SR), "-c:a", "pcm_s24le", out)
    print("->", out)
