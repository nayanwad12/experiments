"""vo: tighten the 49.7 s ElevenLabs narration to fit a 40 s film.

Drops three lines, trims the "But" before "every person deserves", shortens the pauses and speeds up the voice by 5%.
Writes work/vo_edit.wav (48 kHz stereo, starts at t=0) and work/vo_lines.json (output times per line, used for
captions, cuts and SFX cues).

    python3 vo.py
"""
import json
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile

HERE = Path(__file__).resolve().parent
SR = 48000
TEMPO = 1.05
LEAD = 0.5      # silence before the first word (output seconds)
PAD = 0.04      # keep a little air around every chunk so no consonant is clipped

# (source in, source out, caption text, pause after in source seconds). Times from silencedetect + transcription.
LINES = [
    (0.000, 0.743, "Sometimes,", 0.12),
    (1.055, 2.690, "life changes in a moment.", 0.25),
    (3.285, 6.483, "And suddenly, the questions feel bigger than the answers.", 0.40),
    (7.097, 9.651, "But behind every diagnosis is a person.", 0.15),
    (10.173, 10.713, "A family.", 0.15),
    (11.358, 13.776, "A life filled with memories, dreams,", 0.10),
    (14.186, 15.168, "and people who care.", 0.35),
    # dropped: "In moments like these." (15.775-16.934)
    (17.311, 18.656, "Being heard matters.", 0.20),
    (19.042, 20.883, "Understanding your options matters.", 0.25),
    # dropped: "And knowing what to ask can make a difference." (21.310-23.910)
    (24.365, 26.810, "Because care is more than a medical conversation.", 0.20),
    (27.250, 28.133, "It is guidance,", 0.10),
    (28.481, 29.474, "thoughtful decisions,", 0.10),
    (29.784, 32.316, "and support that includes the people beside you.", 0.40),
    # dropped: "The journey may not always be easy." (32.839-34.659) and the "But" at 35.15-35.27
    (35.340, 41.309, "Every person deserves dignity, compassion, and the chance to face each next step with support.", 0.45),
    (41.811, 42.613, "OncoXpress.", 0.15),
    (43.015, 46.630, "Because cancer care should always see the person behind the diagnosis.", 0.35),
    (47.083, 49.711, "Connect with OncoXpress to take your next step.", 0.0),
]


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2)


def main():
    src = load(HERE / "raw/vo.mp3")
    parts, lines, t = [], [], 0.0
    fade = int(0.01 * SR)
    for i, (s, e, text, gap) in enumerate(LINES):
        s0 = max(0.0, s - (0 if i == 13 else PAD))     # the "But" cut must stay tight on the left
        seg = src[int(s0 * SR):int(min(e + PAD, len(src) / SR) * SR)].copy()
        ramp = np.linspace(0, 1, fade)[:, None]
        seg[:fade] *= ramp
        seg[-fade:] *= ramp[::-1]
        lines.append({"text": text, "s": t, "e": t + len(seg) / SR})
        parts += [seg, np.zeros((int(gap * SR), 2), np.float32)]
        t += len(seg) / SR + gap
    joined = np.concatenate(parts)
    tmp = HERE / "work/vo_joined.wav"
    wavfile.write(tmp, SR, joined)
    # speed up without changing pitch, and put LEAD seconds of silence in front
    out = HERE / "work/vo_edit.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-af",
                    f"atempo={TEMPO},adelay={int(LEAD * 1000)}:all=1", "-ar", str(SR), str(out)], check=True)
    for ln in lines:
        ln["s"] = round(LEAD + ln["s"] / TEMPO, 3)
        ln["e"] = round(LEAD + ln["e"] / TEMPO, 3)
    (HERE / "work/vo_lines.json").write_text(json.dumps(lines, indent=1))
    for ln in lines:
        print(f'{ln["s"]:6.2f}-{ln["e"]:6.2f}  {ln["text"]}')


if __name__ == "__main__":
    main()
