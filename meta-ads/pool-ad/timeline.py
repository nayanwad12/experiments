"""timeline: the single source of truth for pool-ad.

Picture (scene.py) and sound (audio cues) both read from here, so a change of timing
moves the cut, the animation and the sound effect together. Never hard-code a time
anywhere else.
"""

import os

W, H = 1080, 1920          # 9:16
# render other formats without editing: VIBE_SIZE=1080x1080 python3 scene.py render
# (Windows PowerShell: $env:VIBE_SIZE="1080x1080"; py scene.py render)
if os.environ.get("VIBE_SIZE"):
    W, H = (int(v) for v in os.environ["VIBE_SIZE"].lower().split("x"))
FPS = 30
DURATION = 30       # seconds
BPM = 120                     # music tempo; cuts land on beats
BEAT = 60.0 / BPM
BAR = 4 * BEAT
MOOD = "upbeat"               # audio_kit moods: upbeat, hype, chill, corporate, cinematic, playful, tech


def beat(n):
    """time of beat n (0-based)."""
    return n * BEAT


# (start, end, scene name). Keep scenes on bar lines when there is music.
SCENES = [
    (0.0, beat(4), "hook"),
    (beat(4), beat(8), "message"),
    (beat(8), DURATION, "endcard"),
]

# on-screen copy lives here too, so Claude edits words in one place
COPY = {
    "hook": ["DIRECT", "THE", "VIBE"],
    "chips": ["CUTS", "CAPTIONS", "MOTION", "MUSIC"],
    "end_title": "VIBE EDITING",
    "cta": "ENROLL NOW",
}

# sound effects: (time, kind, gain_db). Kinds: python3 vibe/audio_kit.py sfx --list
SFX = [
    (0.0, "impact", -4),
    (beat(4) - 0.35, "whoosh", -8),
] + [(beat(4) + 0.25 + i * BEAT / 2, "pop", -9) for i in range(4)] + [
    (beat(8) - 0.35, "whoosh", -8),
    (beat(8) + 0.1, "sparkle", -10),
]


def scene_at(t):
    for s, e, name in SCENES:
        if s <= t < e:
            return name, t - s, e - s
    s, e, name = SCENES[-1]
    return name, t - s, e - s


def cues(voice=None, music="work/music.wav"):
    """cues.json payload for: python3 vibe/audio_kit.py mix work/cues.json"""
    c = {"duration": DURATION, "music": {"file": music, "gain_db": -9, "duck_db": -10, "fade_out": 1.2},
         "sfx": [{"t": round(t, 3), "kind": k, "gain_db": g} for t, k, g in SFX]}
    if voice:
        c["voice"] = {"file": voice, "gain_db": 0}
    return c
