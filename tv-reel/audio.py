# Voice cut + clean, original music, synthesized SFX, mix to -14 LUFS.
import numpy as np, json, subprocess, sys, os
from scipy.signal import butter, sosfilt, sosfiltfilt
import pyloudnorm as pyln

ROOT = os.path.dirname(os.path.abspath(__file__)) + "/.."
SR = 48000
E = json.load(open(ROOT + "/work/edl.json"))
EV = json.load(open(ROOT + "/work/events.json"))
TOTAL = 69.90
N = int(TOTAL * SR)
rng = np.random.default_rng(1)

def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], "bandpass", fs=SR, output="sos"), x)
def lp(x, f, o=2): return sosfilt(butter(o, f, "lowpass", fs=SR, output="sos"), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, "highpass", fs=SR, output="sos"), x)
def env(n, a, d):  # attack/decay exp envelope
    t = np.arange(n) / SR
    return np.minimum(t / max(a, 1e-4), 1) * np.exp(-np.maximum(t - a, 0) / d)
def sweep(f0, f1, dur, curve="exp"):
    n = int(dur * SR); t = np.linspace(0, 1, n)
    f = f0 * (f1 / f0) ** t if curve == "exp" else f0 + (f1 - f0) * t
    return np.sin(2 * np.pi * np.cumsum(f) / SR)
def noise(d): return rng.normal(0, 1, int(d * SR))
def norm(x): return x / (np.abs(x).max() + 1e-9)
def sweep_bp(x, f0, f1, q=1.5, blocks=48):
    out = np.zeros_like(x); n = len(x); B = max(1, n // blocks)
    for k in range(0, n, B):
        fr = k / n; fc = f0 * (f1 / f0) ** fr
        lo, hi = fc / (1 + 1 / q), min(fc * (1 + 1 / q), SR / 2 - 100)
        seg = x[max(0, k - 2048):k + B]
        y = bp(seg, lo, hi)
        out[k:k + B] = y[-len(x[k:k + B]):]
    return out

# ------------------------------------------------------------ voice
def voice():
    raw = ROOT + "/work/voice48.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", ROOT + "/src/raw.mp4", "-ac", "1", "-ar", str(SR),
                    "-af", "highpass=f=75,afftdn=nf=-32:nr=8,equalizer=f=220:t=o:w=1.2:g=-2.5,equalizer=f=3400:t=o:w=1.5:g=2.5,"
                           "equalizer=f=6800:t=o:w=1:g=-1.5,highshelf=f=10500:g=1.5,"
                           "acompressor=threshold=-21dB:ratio=3:attack=6:release=140:makeup=3",
                    "-f", "f32le", raw], check=True)
    x = np.fromfile(raw, np.float32).astype(np.float64)
    out = np.zeros(N); xf = int(0.008 * SR)
    for a, b, o in E["segs"]:
        s = x[int(a * SR):int(b * SR)].copy()
        s[:xf] *= np.linspace(0, 1, xf); s[-xf:] *= np.linspace(1, 0, xf)
        i = int(o * SR); out[i:i + len(s)] += s[:N - i]
    return out

# ------------------------------------------------------------ music
BPM = 120; BEAT = 60 / BPM; G0 = 11.82 - 12.0
DROP = 11.82
def bt(k): return G0 + k * BEAT  # time of beat k
NOTE = lambda m: 440 * 2 ** ((m - 69) / 12)
CH = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]   # Am F C G
ROOTS = [45, 41, 48, 43]

def kick():
    d = 0.42; n = int(d * SR); t = np.arange(n) / SR
    f = 48 + 90 * np.exp(-t / 0.035)
    k = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
    k[:200] += hp(noise(200 / SR), 2000) * 0.3 * np.linspace(1, 0, 200)
    return k
def clap():
    d = 0.25; x = bp(noise(d), 900, 3500) ; e = np.zeros(len(x)); t = np.arange(len(x)) / SR
    for o in (0, 0.011, 0.022): e += (t >= o) * np.exp(-np.maximum(t - o, 0) / (0.012 if o < .02 else 0.09))
    return norm(x * e)
def hat(open_=False):
    d = 0.18 if open_ else 0.05; x = hp(noise(d), 7500, 4)
    return norm(x * env(len(x), 0.001, 0.07 if open_ else 0.014))
def saw(f, d, det=0.0):
    t = np.arange(int(d * SR)) / SR
    return 2 * ((t * f * (1 + det)) % 1) - 1
def pad_note(chord, d):
    x = sum(saw(NOTE(m), d, dt) for m in chord for dt in (-0.004, 0.0, 0.005))
    x = lp(x, 1400)
    n = len(x); e = np.minimum(np.arange(n) / (0.35 * SR), 1) * np.minimum((n - np.arange(n)) / (0.3 * SR), 1)
    return x * e / 9
def pluck(m, d=0.35, bright=2600):
    x = saw(NOTE(m), d) + 0.5 * saw(NOTE(m + 12), d)
    x = lp(x, bright) * env(len(x), 0.002, 0.12)
    return x
def bass(m, d):
    t = np.arange(int(d * SR)) / SR
    x = np.sin(2 * np.pi * NOTE(m) * t) + 0.35 * np.tanh(3 * np.sin(2 * np.pi * NOTE(m) * t))
    return x * env(len(x), 0.004, d * 0.6)

def place(buf, x, t, g=1.0, pan=0.0):
    i = int(t * SR)
    if i >= len(buf) or i + len(x) <= 0: return
    if i < 0: x = x[-i:]; i = 0
    x = x[:len(buf) - i]
    l, r = np.sqrt(0.5 * (1 - pan)), np.sqrt(0.5 * (1 + pan))
    buf[i:i + len(x), 0] += x * g * l * 1.414; buf[i:i + len(x), 1] += x * g * r * 1.414

def music():
    drums = np.zeros((N, 2)); syn = np.zeros((N, 2)); padb = np.zeros((N, 2)); bas = np.zeros((N, 2))
    K, C, Hc, Ho = kick(), clap(), hat(), hat(True)
    def state(t):
        if t < 3.13: return "intro"
        if t < DROP: return "old"
        if 56.20 <= t < 59.07: return "no"
        if 45.53 <= t < 50.40: return "break"
        if 59.07 <= t < 66.30: return "proof"
        if t >= 66.30: return "end"
        return "full"
    kb = int(np.floor((0 - G0) / BEAT))
    for k in range(kb - 1, int((TOTAL - G0) / BEAT) + 2):
        t = bt(k)
        if t < -0.5 or t > TOTAL: continue
        st = state(t); bar = int(np.floor(k / 4)); ch = bar % 4; inb = k % 4
        # pad: one chord per bar
        if inb == 0 and st not in ("no",):
            g = {"intro": 1.1, "old": .5, "full": .55, "break": 1.5, "proof": .55, "end": .9}.get(st, .5)
            place(padb, pad_note(CH[ch], BEAT * 4 + 0.3), t, g, 0)
        if st in ("full", "proof"):
            place(drums, K, t, 1.0)
            if inb in (1, 3) and st == "full": place(drums, C, t, 0.55, 0.1)
            for h in range(2):
                place(drums, Hc if h == 0 else Ho * 0.6, t + h * BEAT / 2, 0.22 if h == 0 else 0.16, 0.35)
            for h in range(4):  # bass 8ths w/ sidechain feel (offbeat accents)
                place(bas, bass(ROOTS[ch], BEAT / 2 * 0.9), t + h * BEAT / 2, 0.55 if h % 2 else 0.3)
                break
            place(bas, bass(ROOTS[ch], BEAT * 0.45), t + BEAT / 2, 0.6)
            arp = [CH[ch][0] + 12, CH[ch][1] + 12, CH[ch][2] + 12, CH[ch][1] + 12]
            br = 4200 if 29.1 <= t < 34.87 else 2600
            for h in range(2):
                place(syn, pluck(arp[(inb * 2 + h) % 4], 0.3, br), t + h * BEAT / 2, 0.22, -0.3 if h else 0.3)
        elif st == "old":
            place(drums, lp(K, 900), t, 0.7)
            if inb in (1, 3): place(drums, lp(C, 1200), t, 0.3)
            place(bas, lp(bass(ROOTS[ch], BEAT * 0.8), 500), t, 0.35)
        elif st == "intro":
            if inb in (0, 2): place(drums, lp(K, 600), t, 0.45)
            place(syn, lp(pluck(CH[ch][inb % 3] + 12, 0.4), 1500), t, 0.4, 0.2)
        elif st == "break":
            place(syn, pluck(CH[ch][inb % 3] + 12, 0.45, 2000), t, 0.45, 0.25 * (-1) ** k)
            place(syn, pluck(CH[ch][(inb + 1) % 3] + 24, 0.3, 2200), t + BEAT / 2, 0.28)
    # snare roll into the drop + into the system reveal
    for t0, t1 in ((DROP - 1.0, DROP), (49.4, 50.40)):
        n = 16
        for j in range(n):
            tt = t0 + (t1 - t0) * (1 - (1 - j / n) ** 1.5) - 0.0
            place(drums, lp(C, 2500), tt, 0.12 + 0.35 * j / n)
    # second drop / system
    place(drums, K, 50.40, 1.2)
    # NO section: sub hits under each "No"
    W = E["words"]
    for wi in (157, 160, 163):
        t = W[wi][0]
        place(bas, bass(33, 0.6) * 1.0, t, 0.9); place(drums, K, t, 1.1)
    # ending: final stab
    place(padb, pad_note([57, 60, 64, 69], 3.0), 66.62, 1.0)
    place(bas, bass(33, 2.2), 66.62, 0.9); place(drums, K, 66.62, 1.2)
    place(syn, pluck(69, 1.2, 3000), 66.62, 0.35)
    # gap right before the drop for impact
    m = drums * 1.0 + syn + padb * 0.8 + bas * 0.9
    g = np.ones(N)
    i0, i1 = int((DROP - 0.16) * SR), int(DROP * SR); g[i0:i1] = np.linspace(1, 0.05, i1 - i0)
    # tape-stop feel on CRT off: fade 66.3 -> 66.6
    i0, i1 = int(66.30 * SR), int(66.60 * SR); g[i0:i1] *= np.linspace(1, 0.1, i1 - i0)
    m *= g[:, None]
    # fade out tail
    i0 = int((TOTAL - 1.2) * SR); m[i0:] *= np.linspace(1, 0, N - i0)[:, None] ** 1.5
    return m

# ------------------------------------------------------------ SFX
def sfx(name):
    if ":" in name: name, arg = name.split(":"); arg = float(arg)
    else: arg = None
    if name in ("pop", "pop_soft"):
        f0, f1, d = (900, 380, 0.07) if name == "pop" else (1200, 700, 0.045)
        x = sweep(f0, f1, d) * env(int(d * SR), 0.001, d / 3)
        return norm(x), 0
    if name == "hit":
        d = 0.35; n = int(d * SR); t = np.arange(n) / SR
        x = np.sin(2 * np.pi * np.cumsum(45 + 120 * np.exp(-t / .03)) / SR) * np.exp(-t / .11)
        x[:1500] += lp(noise(1500 / SR), 3000) * np.exp(-np.arange(1500) / 300) * 0.6
        return norm(x), 0
    if name == "impact":
        d = 1.6; n = int(d * SR); t = np.arange(n) / SR
        x = np.sin(2 * np.pi * np.cumsum(32 + 80 * np.exp(-t / .06)) / SR) * np.exp(-t / .45)
        x += lp(noise(d), 1800) * np.exp(-t / .35) * 0.5
        return norm(np.tanh(1.5 * x)), 0
    if name in ("whoosh", "whoosh_soft", "swoosh", "zoom_out"):
        d = {"whoosh": .42, "whoosh_soft": .55, "swoosh": .28, "zoom_out": .5}[name]
        x = noise(d); n = len(x)
        f0, f1 = (350, 4200) if name != "zoom_out" else (3500, 250)
        x = sweep_bp(x, f0, f1, 2.0)
        e = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
        return norm(x * e), 1
    if name in ("glitch", "glitch_s"):
        d = .2 if name == "glitch" else .09; n = int(d * SR); x = np.zeros(n); k = 0
        while k < n:
            L = int(rng.integers(300, 1600)); f = rng.choice([220, 440, 880, 1760, 3520]) * rng.uniform(.9, 1.1)
            seg = np.sign(np.sin(2 * np.pi * f * np.arange(L) / SR)) if rng.random() < .5 else rng.normal(0, 1, L)
            seg = np.round(seg * 4) / 4
            x[k:k + L] = seg[:n - k] * rng.uniform(.3, 1); k += L + int(rng.integers(0, 400))
        return norm(hp(x, 300) * env(n, 0.001, d)), 0
    if name in ("click", "tick", "cut_tick"):
        d = 0.03; n = int(d * SR)
        f = {"click": 2200, "tick": 3400, "cut_tick": 2800}[name]
        x = np.sin(2 * np.pi * f * np.arange(n) / SR) * env(n, 0.0005, 0.006) + hp(noise(d), 3000) * env(n, 0.0002, 0.002) * 0.5
        return norm(x), 0
    if name == "typing":
        d = arg; n = int(d * SR) + 4000; x = np.zeros(n); t = 0.0
        while t < d:
            c, _ = sfx("click"); c = bp(c + hp(noise(0.03), 1500) * env(len(c), .0003, .004) * .8, 800, 6000)
            i = int(t * SR); x[i:i + len(c)] += c[:n - i] * rng.uniform(.4, 1); t += rng.uniform(.045, .09)
        return norm(x), 0
    if name == "drag":
        d = .45; x = lp(noise(d), 900) * np.sin(np.pi * np.linspace(0, 1, int(d * SR))); return norm(x), 0
    if name == "ticks":
        d = .7; n = int(d * SR); x = np.zeros(n)
        for j in range(14):
            c, _ = sfx("tick"); i = int(d * (j / 14) ** 1.3 * SR); x[i:i + len(c)] += c[:n - i]
        return norm(x), 0
    if name == "ding":
        d = 1.1; n = int(d * SR); t = np.arange(n) / SR
        x = sum(a * np.sin(2 * np.pi * 1318 * r * t) * np.exp(-t / (0.5 / r)) for r, a in ((1, 1), (2.76, .4), (5.4, .2)))
        return norm(x * np.minimum(t / .002, 1)), 0
    if name == "stamp":
        h, _ = sfx("hit"); s = lp(noise(.09), 2200) * env(int(.09 * SR), .0005, .02)
        x = h.copy(); x[:len(s)] += s * 0.8; return norm(x), 0
    if name == "clap":
        d = .18; n = int(d * SR); t = np.arange(n) / SR
        x = bp(noise(d), 1200, 5000) * np.exp(-t / .012) + np.sin(2 * np.pi * 190 * t) * np.exp(-t / .04) * .7
        return norm(x), 0
    if name == "swipe":
        d = .18; x = sweep_bp(noise(d), 1500, 7000, 2.5) * np.sin(np.pi * np.linspace(0, 1, int(d * SR))); return norm(x), 0
    if name == "flip_s":
        a, _ = sfx("click"); w, _ = sfx("swoosh"); x = w * 0.6; x[:len(a)] += a; x[3000:3000 + len(a)] += a; return norm(x), 0
    if name == "blip":
        d = .09; n = int(d * SR); t = np.arange(n) / SR
        x = np.sign(np.sin(2 * np.pi * 880 * t)) * (t < .04) + np.sign(np.sin(2 * np.pi * 1320 * t)) * (t >= .05)
        return norm(lp(x, 4000) * 0.5), 0
    if name in ("riser", "riser_s"):
        d = arg; n = int(d * SR); t = np.linspace(0, 1, n)
        x = sweep_bp(noise(d), 300, 6000, 3) * t ** 2 + sweep(180, 1400 if name == "riser" else 900, d) * 0.25 * t ** 2.5
        return norm(x), 1
    if name == "crt_off":
        d = .45; n = int(d * SR); t = np.arange(n) / SR
        x = sweep(1800, 90, .3); x = np.concatenate([x, np.zeros(n - len(x))]) * np.exp(-t / .2)
        x += np.sin(2 * np.pi * 60 * t) * np.exp(-t / .08) * .8
        return norm(x), 0
    raise ValueError(name)

def sfx_bus():
    bus = np.zeros((N, 2)); cache = {}
    for t, name, g in EV:
        if name not in cache: cache[name] = sfx(name)
        x, wide = cache[name]
        gain = 10 ** (g / 20)
        if wide:
            n = len(x); pan = np.linspace(-.6, .6, n)
            i = int(t * SR)
            if i >= N: continue
            seg = x[:N - i]; p = pan[:len(seg)]
            bus[i:i + len(seg), 0] += seg * gain * np.sqrt(.5 * (1 - p)) * 1.41
            bus[i:i + len(seg), 1] += seg * gain * np.sqrt(.5 * (1 + p)) * 1.41
        else:
            place(bus, x, t, gain, float(rng.uniform(-.15, .15)))
    return bus

if __name__ == "__main__":
    v = voice()
    meter = pyln.Meter(SR)
    v *= 10 ** ((-16 - meter.integrated_loudness(v)) / 20)
    m = music()
    m *= 10 ** ((-23.0 - meter.integrated_loudness(m)) / 20)
    # sidechain duck music under voice
    e = np.sqrt(np.convolve(v ** 2, np.ones(1440) / 1440, "same"))
    sm = np.zeros_like(e); a_, r_ = np.exp(-1 / (0.015 * SR)), np.exp(-1 / (0.35 * SR)); acc = 0.0
    for i in range(0, len(e), 48):   # block-rate smoothing
        x_ = e[i]; c = a_ ** 48 if x_ > acc else r_ ** 48; acc = c * acc + (1 - c) * x_; sm[i:i + 48] = acc
    ref = np.percentile(sm[sm > 1e-4], 70)
    duck = 1 - 0.58 * np.clip(sm / ref, 0, 1)
    m *= duck[:, None]
    s = sfx_bus()
    mix = v[:, None] + m + s * 0.9
    mix = mix.astype(np.float32)
    out = ROOT + "/work/mix_pre.wav"
    import wave
    pcm = np.clip(mix / max(1.0, np.abs(mix).max() / 0.9), -1, 1)
    with wave.open(out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((pcm * 32767).astype(np.int16).tobytes())
    if np.abs(mix).max() > 1: print("pre-mix clipped", np.abs(mix).max())
    for nm, arr in (("voice", v), ("music", m[:, 0]), ("sfx", s[:, 0])):
        np.save(ROOT + f"/work/stem_{nm}.npy", arr.astype(np.float32))
    print("pre loudness", meter.integrated_loudness(mix), "peak", np.abs(mix).max())
