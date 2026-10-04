"""Cartoon storybook narration, synthesised offline with Kokoro (Apache-2.0 neural TTS).

    python3 narration.py   -> voice/*.wav + voice/lines.json  (both committed, so build.py runs without the model)

Needs `pip install kokoro-onnx soundfile` and the two model files from
https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0 in $KOKORO_DIR (default ./models).
Each line is placed at its cue in timeline.NARRATION; if a take runs longer than its slot it is re-read faster.
Word timings for the captions are estimated from the take's speech envelope.
"""

import json
import os
import re

import numpy as np
import soundfile as sf

from timeline import NARRATION, NARRATOR

HERE = os.path.dirname(os.path.abspath(__file__))
VOICE_DIR = os.path.join(HERE, "voice")


def _trim(x, sr, thr=0.012):
    a = np.abs(x)
    k = int(0.01 * sr)
    env = np.convolve(a, np.ones(k) / k, "same")
    idx = np.where(env > thr)[0]
    if not len(idx):
        return x
    return x[max(0, idx[0] - 6 * k): idx[-1] + 3 * k]   # generous pre-roll keeps soft onsets (b, v)


def _word_times(x, sr, text):
    """Spread the words over the voiced stretches of the take, weighted by letters."""
    words = text.split()
    k = int(0.02 * sr)
    env = np.convolve(np.abs(x), np.ones(k) / k, "same")
    voiced = env > 0.02
    # speech time axis that skips pauses longer than 120 ms
    t = np.arange(len(x)) / sr
    gaps = np.zeros(len(x), bool)
    run = 0
    for i in range(0, len(x), k):
        if not voiced[i]:
            run += 1
        else:
            run = 0
        if run * k / sr > 0.12:
            gaps[i:i + k] = True
    speech_t = np.cumsum(~gaps) / sr
    total = speech_t[-1]
    w = np.array([len(re.sub(r"[^A-Za-z0-9]", "", wd)) + 1.5 for wd in words], float)
    starts = np.concatenate([[0], np.cumsum(w)[:-1]]) / w.sum() * total
    out = []
    for s in starts:
        i = int(np.searchsorted(speech_t, s))
        out.append(round(float(t[min(i, len(t) - 1)]), 3))
    return [[wd, ts] for wd, ts in zip(words, out)]


def main():
    from kokoro_onnx import Kokoro
    d = os.environ.get("KOKORO_DIR", os.path.join(HERE, "models"))
    k = Kokoro(os.path.join(d, "kokoro-v1.0.onnx"), os.path.join(d, "voices-v1.0.bin"))
    os.makedirs(VOICE_DIR, exist_ok=True)
    meta = []
    for i, (t0, slot, text, spoken, speed) in enumerate(NARRATION):
        sp = speed
        for _ in range(6):
            y, sr = k.create(spoken, voice=NARRATOR, speed=sp, lang="en-gb")
            y = _trim(np.asarray(y, np.float32), sr)
            if len(y) / sr <= slot:
                break
            if sp >= 1.3:
                print(f"  ! '{text}' still {len(y) / sr:.2f}s for a {slot:.2f}s slot at x{sp:.2f}")
                break
            sp = min(1.3, sp * min(1.25, len(y) / sr / slot + 0.02))
        y = y / (np.abs(y).max() + 1e-9) * 0.9
        name = f"line_{i:02d}.wav"
        sf.write(os.path.join(VOICE_DIR, name), y, sr)
        meta.append({"file": name, "t": t0, "dur": round(len(y) / sr, 3), "text": text, "speed": round(sp, 3),
                     "words": _word_times(y, sr, text)})
        print(f"{t0:6.2f}s  {len(y) / sr:4.2f}s/{slot:.2f}s  x{sp:.2f}  {text}")
    with open(os.path.join(VOICE_DIR, "lines.json"), "w") as fh:
        json.dump(meta, fh, indent=1)


if __name__ == "__main__":
    main()
