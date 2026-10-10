"""timeline: the single source of truth for join-vibe-editing (the 'Join Vibe Editing' pool reel).

Picture (scene.py) and sound (cues in make_audio.py) both read from here.
All times are OUTPUT seconds on work/cut.mp4 (after cut_silence).
"""
import json
import os
import re

W, H = 1080, 1920
if os.environ.get("VIBE_SIZE"):
    W, H = (int(v) for v in os.environ["VIBE_SIZE"].lower().split("x"))
FPS = 30
VIDEO = "work/cut.mp4"
MATTE = "work/matte/cut_alpha.mp4"
VIDEO_DUR = 32.096
END_DUR = 3.5
DURATION = VIDEO_DUR + END_DUR
BPM = 128
BEAT = 60.0 / BPM
MOOD = "hype"

WHITE, BLUE, NAVY, INK, PAPER = "#FFFFFF", "#1F5BFF", "#0A1E66", "#0B0B0D", "#F2EEE3"

# section cuts (match the EDL joins, so the paper hides the jump)
SECTIONS = [0.0, 1.656, 7.852, 17.088, 23.608, 28.296, VIDEO_DUR]
# (time of full cover, kind): "wipe" = full torn-paper sheets, "strips" = torn bands across the middle
TRANSITIONS = [(1.656, "strips"), (7.852, "wipe"), (17.088, "wipe"), (23.608, "wipe"), (28.296, "strips"),
               (VIDEO_DUR, "end")]

# ---------------------------------------------------------------- words + caption chunks
WORDS = json.load(open("work/words_cut.json"))
for w in WORDS:
    w["k"] = re.sub(r"[^\w'’]", "", w["w"]).upper()

EMPHASIS = {"SETUP", "DON'T", "EDIT", "SYSTEM", "ONE", "LINE", "SWIMMING", "PAUSES", "MISTAKES", "TEXT", "MUSIC",
            "EVERYTHING", "DONE", "SINGLE", "SECOND", "COMMENT", "VIDEO"}
STRIKE = {(4.6, 5.6): "EDIT"}           # "I don't EDIT anymore": strike-through
# caption phrases, in order (each must match the next words exactly)
PHRASES = ["THIS IS MY", "VIDEO EDITING", "SETUP", "RIGHT NOW", "I'M SUPPOSED", "TO BE EDITING", "VIDEOS",
           "BUT I DON'T", "EDIT ANYMORE", "I BUILT", "A SYSTEM", "THAT DOES IT", "FOR ME", "HERE'S HOW", "IT WORKS",
           "BEFORE I", "JUMPED IN", "I RECORDED", "ONE VIDEO", "ON MY PHONE", "I TOLD", "MY SYSTEM", "WHAT I WANTED",
           "IN ONE LINE", "AND THEN", "CAME HERE", "WHILE I'M", "SWIMMING", "IT CUTS", "THE PAUSES", "REMOVES",
           "MY MISTAKES", "ADDS", "THE TEXT", "THE MUSIC", "EVERYTHING", "AND IT'S", "DONE", "THE VIDEO", "YOU JUST",
           "WATCHED", "SAME", "SYSTEM", "I DIDN'T", "EDIT", "A SINGLE", "SECOND", "OF IT", "WANT TO SEE", "HOW MY",
           "SYSTEM WORKS", "COMMENT", "SYSTEM", "AND I WILL", "SEND YOU", "THE DETAILS"]


def chunks():
    out, i = [], 0
    for ph in PHRASES:
        n = len(ph.split())
        got = [w["k"] for w in WORDS[i:i + n]]
        assert got == ph.split(), (ph, got)
        out.append(WORDS[i:i + n])
        i += n
    assert i == len(WORDS), WORDS[i:]
    res = []
    for j, ch in enumerate(out):
        s = ch[0]["s"] - 0.04
        e = out[j + 1][0]["s"] - 0.04 if j + 1 < len(out) else ch[-1]["e"] + 0.5
        res.append({"s": s, "e": min(e, ch[-1]["e"] + 0.7), "words": ch})
    return res


CHUNKS = chunks()


def W_(key, after=0.0):
    """start time of the first word == key at/after `after`."""
    for w in WORDS:
        if w["k"] == key.upper() and w["s"] >= after - 1e-3:
            return w["s"]
    raise KeyError(key)


# ---------------------------------------------------------------- graphics events (front layer, white)
EV = {
    "arrow": (0.05, 1.6),
    "phone": (W_("RECORDED") - 0.1, W_("I", 12.5) - 0.05),
    "prompt": (W_("I", 12.5) - 0.05, W_("AND", 15.5) + 0.9),
    "chips": [("PAUSES CUT", W_("PAUSES")), ("MISTAKES GONE", W_("MISTAKES")), ("TEXT ADDED", W_("TEXT")),
              ("MUSIC ADDED", W_("MUSIC"))],
    "chips_end": 23.5,
    "done": W_("DONE"),
    "edittime": (W_("DIDN'T") - 0.1, 28.2),
    "comment": (W_("COMMENT") - 0.1, VIDEO_DUR + 0.2),
}

if __name__ == "__main__":
    for c in CHUNKS:
        print(f"{c['s']:6.2f}-{c['e']:6.2f}  " + " ".join(w["k"] for w in c["words"]))
    print(EV)
