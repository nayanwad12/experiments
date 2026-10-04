"""Narration with Kokoro (open-weights neural TTS, runs offline on CPU).

    python3 voice.py   ->  out/voice/scene01.wav ... + out/cues.json (scene timeline + phrase cues)

Model files go in ./models (kokoro-v1.0.onnx, voices-v1.0.bin) from
https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
"""

import json
import math
import os

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

from script import GRID, LINES, PAUSE, SPEED, TAIL, VOICE, VOICE_IN

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


def trim(x, thr=0.004):
    idx = np.where(np.abs(x) > thr)[0]
    if not len(idx):
        return x
    return x[max(idx[0] - 200, 0): idx[-1] + 1200]


def main():
    k = Kokoro(os.path.join(HERE, "models/kokoro-v1.0.onnx"), os.path.join(HERE, "models/voices-v1.0.bin"))
    os.makedirs(os.path.join(OUT, "voice"), exist_ok=True)
    cues, start = [], 0.0
    for i, line in enumerate(LINES):
        parts, starts, t = [], [], 0.0
        for text, pause in line:
            s, sr = k.create(text, voice=VOICE, speed=SPEED, lang="en-us")
            s = trim(s)
            starts.append(round(VOICE_IN + t, 3))
            parts.append(s)
            t += len(s) / sr
            parts.append(np.zeros(int(pause * PAUSE * sr), np.float32))
            t += pause * PAUSE
        take = np.concatenate(parts)
        dur = len(take) / sr
        length = math.ceil((VOICE_IN + dur + TAIL[i]) / GRID - 1e-6) * GRID
        sf.write(os.path.join(OUT, "voice", f"scene{i + 1:02d}.wav"), take, sr)
        cues.append({"scene": i + 1, "start": round(start, 4), "len": round(length, 4), "dur": round(dur, 3),
                     "phrases": starts})
        print(f"scene {i + 1}: start {start:.2f}s len {length:.2f}s take {dur:.2f}s phrases at {starts}")
        start += length
    with open(os.path.join(OUT, "cues.json"), "w") as fh:
        json.dump(cues, fh, indent=1)


if __name__ == "__main__":
    main()
