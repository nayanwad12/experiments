"""B2-06 Audio-led: "This entire song is code. Watch it build." A future-house track assembled layer by layer
(kick, hats, bass, chords, melody, build, drop), each layer driving its own part of a 3D audio-reactive visualiser,
with a live track panel metered from the real stems.

    python3 build.py prep | web 4 18 | layer | sheet | stills 4 | render | sound | all
"""
import json
import sys
from pathlib import Path

import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(HERE))
from b2 import Reel  # noqa: E402
from kit import (W, H, INK, LIME, WHITE, Captions, Film, Layer, clamp, e_back, e_out, endcard, fill, lerp,  # noqa: E402
                 prog, rrect, stroke, text)
from script import LINES, VOICE  # noqa: E402
from voice import Script, narrate  # noqa: E402

FPS, BPM = 30, 124
BAR = 240 / BPM
L = {"kick": 2, "hats": 3, "bass": 4, "chords": 5, "lead": 6, "build": 7, "drop": 9}
LT = {k: v * BAR for k, v in L.items()}
vo = narrate(LINES, HERE / "work", VOICE)
S = Script(vo, [("hook", "@", 0.12), ("kick", "@", LT["kick"] + 0.04), ("hats", "@", LT["hats"] + 0.04),
                ("bass", "@", LT["bass"] + 0.04), ("chords", "@", LT["chords"] + 0.04), ("lead", "@", LT["lead"] + 0.04),
                ("build", "@", LT["build"] + 1.4), ("nos", "@", LT["drop"] + 2 * BAR), ("cta", 0.4)])
END_T = 13.5 * BAR
DUR = END_T + 2.9
R = Reel(__file__, DUR, FPS)
TRACKS = [("kick", "KICK", "#D4FF3F"), ("hats", "HATS", "#4FE3FF"), ("bass", "BASS", "#FF4FD8"),
          ("chords", "CHORDS", "#FFB547"), ("lead", "MELODY", "#9D7BFF")]


def song():
    from music import edm_layers, riser, sweep, noise, SR
    sg = edm_layers(DUR, BPM, "F", {"kick": LT["kick"], "hats": LT["hats"], "bass": LT["bass"], "chords": LT["chords"],
                                    "lead": LT["lead"], "build": LT["build"], "drop": LT["drop"]}, seed=11)
    sg.add("fx", riser(LT["kick"]) * 0.6, 0.0, -6)                       # intro swell into the first kick
    return sg


_FEAT = None


def features():
    """per-frame RMS of each stem (0..1) + 24-band log spectrum of the master."""
    global _FEAT
    if _FEAT:
        return _FEAT
    import music as M
    sg = song()
    mix = sg.master()
    n = int(DUR * FPS)
    hop = M.SR // FPS
    env = {}
    for name in ("kick", "hats", "bass", "chords", "lead", "snare"):
        x = sg.stems.get(name)
        if x is None:
            env[name] = [0.0] * n
            continue
        m = np.abs(x).mean(1)
        v = np.array([np.sqrt((m[i * hop:(i + 1) * hop] ** 2).mean()) if i * hop < len(m) else 0 for i in range(n)])
        env[name] = np.clip(v / (np.percentile(v[v > 0], 97) + 1e-9), 0, 1.2).round(3).tolist() if (v > 0).any() else [0.0] * n
    mono = mix.mean(1)
    spec = []
    edges = np.geomspace(2, 1024, 25).astype(int)
    for i in range(n):
        seg = mono[i * hop: i * hop + 2048]
        if len(seg) < 2048:
            spec.append([0] * 24)
            continue
        mag = np.abs(np.fft.rfft(seg * np.hanning(2048)))
        b = [float(np.log1p(mag[a:max(a + 1, e)].mean())) for a, e in zip(edges[:-1], edges[1:])]
        spec.append(b)
    spec = np.array(spec)
    spec = np.clip(spec / (np.percentile(spec, 98) + 1e-9), 0, 1).round(3).tolist()
    _FEAT = dict(env=env, spec=spec, kicks=sorted(set(round(k, 3) for k in sg.kicks)), mix=mix, stems=sg.stems)
    return _FEAT


def prep():
    F = features()
    R.write_timeline(dict(DUR=DUR, BAR=BAR, END=END_T, L=LT, ENV=F["env"], SPEC=F["spec"], KICKS=F["kicks"], FPS=FPS))
    print("timeline ok", {k: round(v, 2) for k, v in LT.items()})


BG = Layer(HERE / "work" / "layer.mp4", fps=FPS)
_ENV = None


def env_at(name, f):
    global _ENV
    if _ENV is None:
        _ENV = json.loads((HERE / "work" / "timeline.json").read_text())["ENV"]
    e = _ENV.get(name, [])
    return e[f] if 0 <= f < len(e) else 0.0


def track_panel(c, t, f):
    if t < LT["kick"] - 0.3 or t >= END_T:
        return
    a = e_out(prog(t, LT["kick"] - 0.3, 0.4)) * (1 - prog(t, END_T - 0.3, 0.3))
    x0, y0, rw, rh = 60, 1270, W - 120, 74
    c.drawRRect(rrect(x0 - 20, y0 - 70, rw + 40, rh * 5 + 100, 28), fill("#07070c", 0.72 * a))
    text(c, "TRACKS · all synthesised in code", x0, y0 - 26, "mono", 26, "#8a8a96", a, anchor="l")
    for i, (key, name, col) in enumerate(TRACKS):
        y = y0 + i * rh
        on = t >= LT[key]
        e = env_at(key, f) if on else 0
        k = e_out(prog(t, LT[key], 0.25)) if on else 0
        c.drawRRect(rrect(x0, y + 8, rw, rh - 16, 14), fill("#15151d", a))
        text(c, name, x0 + 24, y + rh / 2 + 12, "monob", 32, col if on else "#3a3a44", a, anchor="l")
        mx, mw = x0 + 230, rw - 260
        c.drawRRect(rrect(mx, y + 26, mw, rh - 52, 8), fill("#22222c", a))
        if on:
            c.drawRRect(rrect(mx, y + 26, max(8, mw * min(1, e) * k), rh - 52, 8), fill(col, a))
        if on and t < LT[key] + 0.35:
            c.drawRRect(rrect(x0, y + 8, rw, rh - 16, 14), stroke(col, 4, a * (1 - prog(t, LT[key], 0.35))))


def draw(c, t, f):
    c.drawImage(BG.image(f), 0, 0)
    # the called-out layer name, big
    for key, name, col in TRACKS:
        if LT[key] <= t < LT[key] + BAR:
            k = e_back(prog(t, LT[key], 0.3), 2.2)
            ko = e_out(prog(t, LT[key] + BAR - 0.25, 0.25))
            c.save()
            c.translate(W / 2, 470)
            s = lerp(1.4, 1, clamp(k))
            c.scale(s, s)
            text(c, name, 0, 0, "unbounded", 150, col, clamp(k) * (1 - ko), shadow=24)
            c.restore()
    if LT["build"] + 1.3 <= t < LT["drop"]:
        k = e_out(prog(t, LT["build"] + 1.3, 0.4))
        text(c, "THE DROP", W / 2, 470, "unbounded", 120, WHITE, k * (0.6 + 0.4 * ((t * 8) % 1 > 0.5)), shadow=24)
    track_panel(c, t, f)
    if t >= END_T:
        endcard(c, t, END_T)
    CAP.draw(c, t)


CAP = Captions(S.words(skip=("kick", "hats", "bass", "chords", "lead")), y=1060, size=84).mute(END_T, DUR)
film = Film(draw, DUR, FPS, out_dir=HERE / "out")


def sound():
    from sound import Mix
    F = features()
    m = Mix(DUR)
    m.target_db = 6.0                 # music-led: the song stays big, the callouts sit just on top
    m.voice(S.placements())
    m.music(F["mix"], gain_db=-1, duck_db=-6, fade_out=2.0)
    m.sfx("whoosh", END_T - 0.25, -12)
    m.finish(HERE / "out" / "picture.mp4", HERE / "out" / "B2_06_audio_build.mp4", HERE / "work")


if __name__ == "__main__":
    R.cli(film, sound, prep)
