"""Narration: Kokoro TTS (local ONNX, Apache-2.0 weights) -> work/vo_*.wav + work/vo.json.

Model files (GitHub release thewh1teagle/kokoro-onnx model-files-v1.0) live in $MODELS
(default /home/user/models): kokoro-v1.0.onnx, voices-v1.0.bin.
"""
import json
import os

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.environ.get("MODELS", "/home/user/models")

NARRATOR = "af_heart"
PROMPTER = "am_puck"      # the "user" typing their vibe

# (id, voice, speed, text)
LINES = [
    ("hook",    NARRATOR, 1.05, "Remember editing videos? Hours of cutting, dragging, and keyframing, one tiny clip at a time, until your eyes go square."),
    ("reveal",  NARRATOR, 1.0,  "Now there's a new way. It's called Vibe Editing."),
    ("describe", NARRATOR, 1.05, "No more fighting the timeline. You just describe the vibe you want, in plain words."),
    ("prompt",  PROMPTER, 1.0,  "Make it warm, punchy, and a little dreamy."),
    ("ai",      NARRATOR, 1.08, "And A.I. does the heavy lifting. The cuts, the colors, the captions, the music. All on the beat."),
    ("director", NARRATOR, 1.0, "What took a whole weekend, now takes a coffee break. You stay the director. A.I. handles the keyframes."),
    ("outro",   NARRATOR, 1.0,  "Vibe Editing. Say the vibe, and watch it come to life."),
]


def trim(x, sr, thr=0.01, pad=0.04):
    env = np.abs(x)
    idx = np.where(env > thr)[0]
    if len(idx) == 0:
        return x
    a = max(0, idx[0] - int(pad * sr))
    b = min(len(x), idx[-1] + int(pad * sr))
    return x[a:b]


def main():
    k = Kokoro(os.path.join(MODELS, "kokoro-v1.0.onnx"), os.path.join(MODELS, "voices-v1.0.bin"))
    out = {}
    for lid, voice, speed, text in LINES:
        x, sr = k.create(text, voice=voice, speed=speed, lang="en-us")
        x = trim(np.asarray(x, np.float32), sr)
        path = os.path.join(HERE, "work", f"vo_{lid}.wav")
        sf.write(path, x, sr)
        out[lid] = {"wav": path, "sr": sr, "dur": len(x) / sr, "text": text}
        print(f"{lid:9s} {len(x)/sr:5.2f}s  {text}")
    print("total speech", sum(v["dur"] for v in out.values()))
    with open(os.path.join(HERE, "work", "vo.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
