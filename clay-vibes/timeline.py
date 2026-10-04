"""Shared timing for picture and sound. 120 BPM: 1 beat = 0.5 s, 1 bar = 2 s, 40 s = 20 bars."""

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
GRUMBLE = 10.5

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
BAA_HAPPY = 27.3

# --- screening
POPS = [28.6, 29.3, 29.9, 30.4, 31.0, 32.2, 32.9, 33.5]
TURN, WINK1, FLOCK_AWW = 31.4, 31.9, 32.4

# --- end card
END_DROP = 34.25
TAG_WORDS = [35.0, 35.35, 35.7, 36.05]
SIGN = 36.5
POPUP2, WINK2, BAA2 = 37.2, 37.9, 38.2
IRIS = (38.95, 39.55)
SHAVE = [36.5, 37.0, 37.25, 37.5, 38.0, 39.0, 39.5]   # "shave and a haircut... two bits"


def scene_at(t):
    for name, a, b in SCENES:
        if a <= t < b:
            return name, a, b
    return SCENES[-1]
