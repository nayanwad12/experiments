"""Shared timing for picture and sound. 120 BPM: 1 beat = 0.5 s, 1 bar = 2 s, 40 s = 20 bars."""

import json
import os

BPM = 120
BEAT = 60 / BPM
BAR = BEAT * 4
DUR = 40.0

SCENES = [  # (name, start, end)
    ("title", 0.0, 4.0),       # farm, clay title drops in, Woolly pops up behind the wall
    ("grind", 4.0, 12.0),      # barn edit suite: day turns to night, mess piles up
    ("idea", 12.0, 14.5),      # close-up: lightbulb
    ("prompt", 14.5, 18.0),    # over-the-shoulder: types the vibe, smashes Enter
    ("magic", 18.0, 28.0),     # clips hop into place, morning, dance party
    ("screening", 28.0, 34.0),  # the flock watches the cozy edit
    ("endcard", 34.0, 40.0),   # sunset title card, wink, iris out
]

# --- title
LAND_VIBE = [0.75 + 0.25 * i for i in range(4)]
LAND_EDITING = [1.875 + 0.125 * i for i in range(7)]
POPUP1, BAA1 = 2.9, 3.3

# --- grind
MUGS = [5.0, 6.5, 8.0, 9.5]
CRUMPLE, TOSS, TOSS_LAND = 7.2, 7.7, 8.2
BLOCK_FALL, BLOCK_LAND = 9.0, 9.4
GRUMBLE = 10.8

# --- idea / prompt
WAKE, DING = 12.3, 12.8
PROMPT = "make it cozy"
TYPE_T0, TYPE_DT = 14.9, 0.13
SPARKLE_T = 16.75
ENTER = 17.5

# --- magic
MAGIC = 18.0
RETRACT = (18.3, 19.2)
MUG_POP = [19.3, 19.5, 19.7, 19.9]
BALL_HOP = [20.0, 20.25]
HOP_T0, HOP_DT, HOP_LEN = 20.25, 0.375, 0.25   # hops land on a 16th grid: 20.5, 20.875 ...
HEN_WAKE = 21.0
PLAYHEAD = (24.2, 25.8)
DANCE = 24.5
BAA_HAPPY = None   # the narrator has the floor here now
ROOSTER_CROW = 23.25   # morning punctuation once the last clip lands

# --- screening
POPS = [28.6, 29.3, 29.9, 30.4, 31.0, 32.2, 32.9, 33.5]
TURN, WINK1, FLOCK_AWW = 31.4, 31.9, 32.4

# --- end card
END_DROP = 34.25
TAG_WORDS = [35.0, 35.35, 35.7, 36.05]   # replaced below by the narrator's word timings
SIGN = 36.5
POPUP2, WINK2, BAA2 = 37.2, 37.9, 38.35
IRIS = (38.95, 39.55)
SHAVE = [36.5, 37.0, 37.25, 37.5, 38.0, 39.0, 39.5]   # "shave and a haircut... two bits"


# --- narration: (cue, max length, caption, what the narrator actually reads, speed)
NARRATOR = "bm_fable"
NARRATION = [
    (0.25, 3.0, "Ever spent a whole night editing... one video?", "Ever spent a whole night, editing... one video?", 1.1),
    (4.25, 2.9, "Meet Woolly. Woolly's been editing since lunch.", "Meet Woolly. Woolly's been editing since lunch.", 1.05),
    (7.55, 2.0, "Click. Cut. Drag. Repeat.", "Click. Cut. Drag. Repeat.", 1.15),
    (9.6, 1.15, "Three a.m.", "Three A.M.", 1.2),
    (12.95, 1.6, "Then... a bright idea!", "Then... a bright idea!", 1.2),
    (14.6, 2.15, "What if you could just say the vibe?", "What if you could just... say the vibe?", 1.05),
    (18.45, 0.75, "Ta-da!", "Ta-daa!", 1.0),
    (19.3, 1.8, "Clips? Sorted. Mess? Gone.", "Clips? Sorted. Mess? Gone.", 1.1),
    (21.35, 1.9, "Every cut lands on the beat.", "Every cut lands on the beat.", 1.05),
    (24.2, 1.65, "That's vibe editing!", "That's vibe editing!", 1.05),
    (25.95, 2.4, "You bring the vibe. AI does the clicking.", "You bring the vibe. A.I. does the clicking.", 1.05),
    (28.9, 1.8, "Even the flock is hooked.", "Even the flock is hooked.", 1.0),
    (34.35, 2.15, "Vibe Editing... just say the vibe.", "Vibe editing! ... Just say the vibe.", 1.05),
    (36.5, 1.8, "From Ideabro Studio.", "From, Idea-bro Studio!", 1.1),
]
CAPTION_UNTIL = 34.0     # the end card already spells its words out on screen

_lines = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice", "lines.json")
VOICE = json.load(open(_lines)) if os.path.exists(_lines) else []
for _ln in VOICE:
    if _ln["text"].endswith("just say the vibe."):
        TAG_WORDS = [_ln["t"] + w[1] for w in _ln["words"][-4:]]


def scene_at(t):
    for name, a, b in SCENES:
        if a <= t < b:
            return name, a, b
    return SCENES[-1]
