"""Narration: Kokoro TTS (local ONNX, Apache-2.0 weights) -> work/vo_*.wav + work/vo.json.

Model files (GitHub release thewh1teagle/kokoro-onnx model-files-v1.0) live in $MODELS
(default /home/user/models): kokoro-v1.0.onnx, voices-v1.0.bin.

Cast: a deep anime-trailer narrator, Kai (the young editor), the Vibe spirit, and the client, who
gets a Japanese voice fed hand-written phonemes (espeak's Japanese drops sounds).
"""
import json
import os

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.environ.get("MODELS", "/home/user/models")

NARR = "am_onyx"
KAI = "am_puck"
SPIRIT = "af_sky"
CLIENT = "jf_alpha"

# (id, voice, speed, text, phonemes-or-None). Each phrase is its own take so timeline.py can
# place it on a cue with dramatic anime-trailer pauses in between.
LINES = [
    ("world1",  NARR,   0.95, "In a world drowning in footage...", None),
    ("world2",  NARR,   0.92, "one editor stood alone.", None),
    ("dead",    NARR,   1.0,  "Deadline: tomorrow.", None),
    ("clips",   NARR,   1.0,  "Clips: one thousand.", None),
    ("sleep",   NARR,   1.0,  "Sleep: zero.", None),
    ("chibi1",  NARR,   1.1,  "Three days of cutting and keyframing...", None),
    ("chibi2",  NARR,   1.05, "and his soul left his body.", None),
    ("spirit1", SPIRIT, 1.0,  "Stop fighting the timeline, Kai.", None),
    ("spirit2", SPIRIT, 0.95, "Just tell me the vibe.", None),
    ("epic",    KAI,    1.1,  "Make it epic!", None),
    ("emo",     KAI,    1.1,  "Emotional!", None),
    ("beat",    KAI,    1.1,  "On the beat!", None),
    ("vibe",    KAI,    0.85, "Vibe...", None),
    ("edit",    KAI,    1.0,  "EDIT!", None),
    ("cuts",    NARR,   1.0,  "Cuts.", None),
    ("color",   NARR,   1.0,  "Color.", None),
    ("caps",    NARR,   1.0,  "Captions.", None),
    ("music",   NARR,   1.0,  "Music.", None),
    ("synced",  NARR,   1.0,  "Synced in seconds.", None),
    ("sugoi",   CLIENT, 1.0,  "Sugoi!", "sɯɡˈoi!"),
    ("client",  NARR,   1.0,  "Even the client cried.", None),
    ("title",   NARR,   0.95, "Vibe Editing.", None),
    ("say",     NARR,   1.0,  "Say the vibe...", None),
    ("alive",   NARR,   1.0,  "watch it come alive.", None),
]


def trim(x, sr, thr=0.01, pad=0.04):
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return x
    return x[max(0, idx[0] - int(pad * sr)):min(len(x), idx[-1] + int(pad * sr))]


def main():
    k = Kokoro(os.path.join(MODELS, "kokoro-v1.0.onnx"), os.path.join(MODELS, "voices-v1.0.bin"))
    os.makedirs(os.path.join(HERE, "work"), exist_ok=True)
    out = {}
    for lid, voice, speed, text, ph in LINES:
        if ph:
            x, sr = k.create(ph, voice=voice, speed=speed, is_phonemes=True)
        else:
            x, sr = k.create(text, voice=voice, speed=speed, lang="en-us")
        x = trim(np.asarray(x, np.float32), sr)
        path = os.path.join(HERE, "work", f"vo_{lid}.wav")
        sf.write(path, x, sr)
        out[lid] = {"wav": path, "sr": sr, "dur": len(x) / sr, "text": text}
        print(f"{lid:7s} {len(x)/sr:5.2f}s  {text}")
    print("total speech", round(sum(v["dur"] for v in out.values()), 2))
    with open(os.path.join(HERE, "work", "vo.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
