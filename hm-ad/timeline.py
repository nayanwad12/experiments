"""timeline: the single source of truth for hm-ad.

Picture (scene.py) and sound (audio cues) both read from here, so a change of timing
moves the cut, the animation and the sound effect together. Never hard-code a time
anywhere else.

128 BPM -> beat 0.469 s, bar 1.875 s, 16 bars = exactly 30 s. Every cut sits on a bar line.
"""

import os

W, H = 1080, 1920          # 9:16
# render other formats without editing: VIBE_SIZE=1080x1080 python3 scene.py render
if os.environ.get("VIBE_SIZE"):
    W, H = (int(v) for v in os.environ["VIBE_SIZE"].lower().split("x"))
FPS = 30
BPM = 128                     # music tempo; cuts land on beats
BEAT = 60.0 / BPM
BAR = 4 * BEAT
DURATION = 16 * BAR           # 30.0 s
MOOD = "hype"


def beat(n):
    """time of beat n (0-based)."""
    return n * BEAT


b = beat

# (start, end, scene name). All on bar lines.
SCENES = [
    (b(0), b(8), "hook"),         # 0.00  kinetic word slams
    (b(8), b(16), "problem"),     # 3.75  "nothing to wear?" -> "everything"
    (b(16), b(20), "reveal"),     # 7.50  red flood + H&M wordmark
    (b(20), b(36), "app"),        # 9.38  interactive site: tap, scroll, love, add, checkout
    (b(36), b(48), "montage"),    # 16.88 category cuts every beat + brand promise
    (b(48), b(56), "outfit"),     # 22.50 mix & match outfit builder
    (b(56), DURATION, "endcard"),  # 26.25 logo, SHOP NOW tap
]

# on-screen copy lives here too
COPY = {
    "hook_a": ["NEW", "SEASON."],
    "hook_b": ["NEW", "YOU."],
    "hook_c": ["STYLE", "THAT", "MOVES", "FAST."],
    "problem": ["NOTHING", "TO", "WEAR?"],
    "problem_fix": "EVERYTHING",
    "reveal_sub": "NEW ARRIVALS",
    # app captions: (local beat, word)
    "app_caps": [(0, "SHOP."), (2, "TAP."), (4, "SCROLL."), (6, "LOVE IT."), (7, "ADD."), (10, "BAG."),
                 (12, "CHECKOUT."), (13, "DONE.")],
    "tabs": ["WOMEN", "MEN", "KIDS", "HOME", "BEAUTY"],
    "products": ["Peplum twill jacket", "Tiered maxi dress", "Wide-leg jeans", "Printed T-shirt"],
    "categories": ["WOMEN", "MEN", "DENIM", "JACKETS", "PRINTS", "NEW IN"],
    # promise words: (local beat inside the second half of montage, lines)
    "promise": [(0, ["FASHION"]), (1, ["&"]), (2, ["QUALITY"]), (3, ["AT THE"]), (4, ["BEST", "PRICE."])],
    "outfit_caps": [(0, "MIX."), (2, "MATCH."), (4, "OWN IT."), (6, "YOUR STYLE.")],
    "end_sub": "NEW ARRIVALS ARE IN",
    "cta": "SHOP NOW",
    "url": "hm.com",
}

# big hits: camera shake + white flash
HITS = [b(0), b(2), b(4), b(13), b(16), b(42), b(44), b(46), b(56)]

# sound effects: (time, kind, gain_db[, dur])
SFX = (
    # hook: a hit on every beat
    [(b(0), "impact", -3), (b(1), "swish", -10), (b(2), "impact", -5), (b(3), "swish", -10),
     (b(4), "glitch", -9), (b(5), "pop", -9), (b(6), "pop", -9), (b(7), "impact", -7)]
    # problem
    + [(b(8) - 0.3, "whoosh", -9), (b(8), "pop", -10), (b(9), "pop", -10), (b(10), "pop", -10),
       (b(12), "swish", -7), (b(13), "impact", -5)]
    + [(b(14) + i * 0.08, "pop", -11) for i in range(5)]
    + [(b(14), "riser", -11, 2 * 0.46875)]
    # reveal
    + [(b(16), "bass_drop", -3), (b(16), "impact", -4), (b(18), "sparkle", -10)]
    # app: every tap is a click, results get a pop/ding
    + [(b(20) - 0.3, "whoosh", -8), (b(22), "click", -5), (b(22) + 0.05, "swish", -12),
       (b(24) - 0.1, "swish", -9), (b(26), "click", -6), (b(26) + 0.04, "pop", -8),
       (b(27), "click", -5), (b(27) + 0.05, "ding", -11), (b(28), "click", -5), (b(28) + 0.05, "pop", -9),
       (b(29), "click", -5), (b(29) + 0.05, "pop", -9), (b(30), "click", -5), (b(30) + 0.1, "swish", -11),
       (b(32), "click", -5), (b(33), "sparkle", -8), (b(33), "ding", -8)]
    # montage: a cut on every beat, then hits on the promise
    + [(b(36) - 0.3, "whoosh", -8)]
    + [(b(36 + i), "shutter" if i % 2 else "swish", -9) for i in range(6)]
    + [(b(42), "impact", -5), (b(43), "pop", -9), (b(44), "impact", -5), (b(45), "pop", -9),
       (b(46), "bass_drop", -5)]
    # outfit builder: a click on every swap
    + [(b(48) - 0.3, "whoosh", -8)]
    + [(b(48 + i), "click", -9) for i in range(8)]
    + [(b(48), "pop", -10), (b(50), "pop", -10), (b(52), "pop", -10), (b(54), "sparkle", -10),
       (b(54), "riser", -10, 2 * 0.46875)]
    # end card
    + [(b(56), "bass_drop", -3), (b(56), "impact", -4), (b(57), "pop", -9), (b(58), "pop", -8),
       (b(60), "click", -4), (b(60) + 0.05, "ding", -8), (b(61), "sparkle", -10)]
)


def scene_at(t):
    for s, e, name in SCENES:
        if s <= t < e:
            return name, t - s, e - s
    s, e, name = SCENES[-1]
    return name, t - s, e - s


def cues(voice=None, music="work/music.wav"):
    """cues.json payload for: python3 vibe/audio_kit.py mix work/cues.json"""
    sfx = []
    for cue in SFX:
        tt, k, g = cue[:3]
        d = {"t": round(tt, 3), "kind": k, "gain_db": g}
        if len(cue) > 3:
            d["dur"] = cue[3]
        sfx.append(d)
    c = {"duration": DURATION, "music": {"file": music, "gain_db": -8, "duck_db": -10, "fade_out": 0.8},
         "sfx": sfx}
    if voice:
        c["voice"] = {"file": voice, "gain_db": 0}
    return c
