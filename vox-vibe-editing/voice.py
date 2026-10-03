"""Narration with Kokoro (open-weights neural TTS, runs offline on CPU).

    python3 voice.py   ->  out/voice/scene01.wav ... + out/cues.json (phrase start times per scene)

Model files go in ./models (kokoro-v1.0.onnx, voices-v1.0.bin) from
https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
"""

import json
import os

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

from script import LINES, SCENE, SPEED, VOICE, VOICE_IN

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
MAX_TAKE = SCENE - VOICE_IN - 0.3   # leave a breath before the next scene


def trim(x, thr=0.004):
    idx = np.where(np.abs(x) > thr)[0]
    if not len(idx):
        return x
    return x[max(idx[0] - 200, 0): idx[-1] + 1200]


def main():
    k = Kokoro(os.path.join(HERE, "models/kokoro-v1.0.onnx"), os.path.join(HERE, "models/voices-v1.0.bin"))
    os.makedirs(os.path.join(OUT, "voice"), exist_ok=True)
    cues = []
    for i, line in enumerate(LINES):
        speed = SPEED
        while True:
            parts, starts, t = [], [], 0.0
            for text, pause in line:
                s, sr = k.create(text, voice=VOICE, speed=speed, lang="en-us")
                s = trim(s)
                starts.append(round(VOICE_IN + t, 3))
                parts.append(s)
                t += len(s) / sr
                parts.append(np.zeros(int(pause * sr), np.float32))
                t += pause
            take = np.concatenate(parts)
            dur = len(take) / sr
            if dur <= MAX_TAKE or speed > 1.25:
                break
            speed = round(speed * dur / MAX_TAKE + 0.01, 3)   # nudge tempo up, re-voice
        sf.write(os.path.join(OUT, "voice", f"scene{i + 1:02d}.wav"), take, sr)
        cues.append({"scene": i + 1, "dur": round(dur, 3), "speed": speed, "phrases": starts})
        print(f"scene {i + 1}: {dur:.2f}s speed={speed} phrases at {starts}")
    with open(os.path.join(OUT, "cues.json"), "w") as fh:
        json.dump(cues, fh, indent=1)


if __name__ == "__main__":
    main()
