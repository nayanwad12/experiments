"""Global timeline shared by the picture and the music: scene starts/lengths from out/cues.json, the
beat grid, and the energy map (where the track builds, drops and breaks down).

Energy map (all keyed to narration cues):
  intro      0 -> "The cut."                     filtered build, risers
  drop 1     "The cut." -> scene 4 prompt       full groove
  build      prompt typing -> "It happens."     snare roll + riser
  drop 2     "It happens." -> scene 5           full groove + lead
  breakdown  scene 5                            no kick, ticking tension, riser into scene 6
  drop 3     scene 6 -> end                     full groove + lead, final hit on "YOU"
"""

import json
import os

from script import BEAT, N

HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, "out", "cues.json")) as _fh:
    CUES = json.load(_fh)

STARTS = [c["start"] for c in CUES]
LENS = [c["len"] for c in CUES]
PHRASES = [c["phrases"] for c in CUES]
DUR = STARTS[-1] + LENS[-1]


def g(scene, phrase, offset=0.0):
    """Global time of a phrase cue (scene and phrase are 0-based)."""
    return STARTS[scene] + PHRASES[scene][phrase] + offset


DROP1 = g(0, 1)               # "The cut."
BUILD = g(3, 1)               # "You type: ..."
DROP2 = g(3, 2)               # "It happens."
BREAK = STARTS[4]             # "But here's the catch."
DROP3 = STARTS[5]             # "So the cut didn't disappear."
YOU = g(5, 2, 1.0)            # stamp lands on "YOU"
DROPS = [DROP1, DROP2, DROP3, YOU]


def section(t):
    if t < DROP1:
        return "intro"
    if t < BUILD:
        return "drop"
    if t < DROP2:
        return "build"
    if t < BREAK:
        return "drop2"
    if t < DROP3:
        return "break"
    return "drop3"


def scene_at(t):
    for k in range(N - 1, -1, -1):
        if t >= STARTS[k]:
            return k
    return 0


def beat_phase(t):
    """(beat index, seconds since that beat)"""
    b = int(t / BEAT)
    return b, t - b * BEAT
