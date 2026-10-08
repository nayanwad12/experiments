"""mixdown.py: voice (broadcast chain) + original future-bass track + SFX on every graphic -> final mp4.

    python3 mixdown.py work/picture.mp4 out/pool_ad_v1.mp4

Music and SFX are synthesised in numpy (reels/common), so there is nothing to clear for ads.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "reels" / "common"))
import audio_kit as ak  # noqa: E402
import music as M  # noqa: E402
from sound import Mix  # noqa: E402

E = json.load(open("work/edl.json"))
W = E["words"]
CUT = E["duration"]
DUR = round(CUT + 2.9, 3)


def at(phrase, n=1):
    p = phrase.split()
    hits = 0
    for i in range(len(W) - len(p) + 1):
        if [w["w"] for w in W[i:i + len(p)]] == p:
            hits += 1
            if hits == n:
                return W[i]["s"]
    raise KeyError(phrase)


def splash(seed=2):
    """water splash: a filtered noise burst with bubbly amplitude flutter + a low plunk."""
    rng = np.random.default_rng(seed)
    n = int(0.9 * ak.SR)
    t = np.arange(n) / ak.SR
    x = rng.normal(0, 1, n).astype(np.float32)
    x = M.filt(x, "bp", (350, 5200))
    env = np.minimum(t / 0.004, 1) * np.exp(-t * 6.5)
    flutter = 0.6 + 0.4 * np.abs(np.sin(2 * np.pi * (18 + 30 * t) * t))
    plunk = np.sin(2 * np.pi * (220 * np.exp(-t * 9) + 70) * t) * np.exp(-t * 14) * 0.6
    y = x * env * flutter * 0.5 + plunk
    return (y / (np.abs(y).max() + 1e-9) * 0.9).astype(np.float32)


def main(picture, out):
    T_PAPER = at("here's how") - 0.12
    T_STEP1 = at("before i jumped") - 0.12
    T_STEP2 = at("told my system") - 0.10
    T_CAME = at("and came here") - 0.06
    T_SWIM = at("while i'm swimming") - 0.15
    SPLIT_A = at("and this video") - 0.06
    T_CTA = at("want to see") - 0.12
    T_COMMENT = at("comment system")
    T_SYS = at("system", 5)

    m = Mix(DUR)
    m.voice([("work/voice.wav", 0.0)], gain_db=0.0)

    song = M.GENRES["future_bass"](DUR + 1.0, bpm=140, key="F#",
                                   marks={"drop": T_CAME, "break": SPLIT_A, "drop2": T_COMMENT})
    bed = song.master()[: int(DUR * ak.SR)]
    m.music(bed, gain_db=-15, duck_db=-11, fade_in=0.05, fade_out=0.8)

    fx = [
        ("whoosh", 0.0, -12), ("impact", at("editing setup") - 0.02, -13), ("pop", at("setup") - 0.02, -12),
        ("swish", at("supposed") - 0.1, -15), ("swish", at("don't") - 0.12, -12), ("whoosh", at("don't") + 0.12, -16),
        ("impact", at("edit anymore") - 0.02, -11),
        ("pop", at("system", 1) - 0.08, -13),
        ("whoosh", T_PAPER, -10), ("swish", at("works") - 0.1, -17),
        ("pop", T_STEP1 + 0.15, -13), ("swish", at("one video") - 0.05, -17), ("swish", T_STEP1, -16),
        ("swish", T_STEP2, -16), ("pop", T_STEP2 + 0.25, -14), ("swish", at("what i wanted") - 0.05, -17),
        ("click", at("one line") + 0.05, -10), ("swish", at("in one line"), -15),
        ("whoosh", T_CAME - 0.05, -10),
        ("pop", T_SWIM + 0.05, -13),
        ("tick", at("cuts the pauses"), -8), ("tick", at("removes"), -8), ("tick", at("adds the text"), -8),
        ("tick", at("the music"), -8), ("tick", at("everything"), -8), ("sparkle", at("everything") + 0.25, -14),
        ("ding", at("it's done") - 0.02, -8), ("impact", at("done") - 0.04, -10),
        ("whoosh", SPLIT_A, -11), ("shutter", at("didn't edit") - 0.05, -11), ("whoosh", T_CTA - 0.3, -13),
        ("pop", T_COMMENT - 0.05, -12), ("impact", T_SYS - 0.03, -10), ("click", T_SYS + 0.3, -9),
        ("pop", at("and i'll send") - 0.05, -14),
        ("impact", CUT, -9), ("sparkle", CUT + 1.25, -12), ("pop", CUT + 1.6, -11),
    ]
    for kind, t, g in fx:
        m.sfx(kind, t, g)
    m.sfx(ak.SFX["typing"](at("in one line") - 0.15 - (at("told my") + 0.35), 15), at("told my") + 0.35, -17)
    m.sfx(ak.SFX["typing"](0.3, 18), T_SYS - 0.08, -14)
    m.sfx(ak.SFX["typing"](1.0, 11), CUT + 0.05, -18)                  # receipt printer
    m.sfx(splash(), T_CAME + 0.12, -9)
    m.finish(picture, out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "work/picture.mp4", sys.argv[2] if len(sys.argv) > 2 else "out/pool_ad.mp4")
