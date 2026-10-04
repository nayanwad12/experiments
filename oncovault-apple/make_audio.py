"""Extend the supplied 23.3 s track to exactly 30.0 s without changing its character.

    python3 make_audio.py  ->  out/audio.wav  (48 kHz stereo, 30.0 s)

1. The groove from 7.85 s is a 2-bar harmonic loop (one phrase = 4.9226 s; its chroma repeats exactly),
   so one extra copy of that phrase is spliced in right after itself (15 ms equal-power crossfade): 28.26 s.
2. The result is slowed ~6% with ffmpeg's pitch-preserving atempo to land on 30.0 s.

Original time u maps to film time:  r = (u if u < 12.7726 else u + 4.9226) * 30 / 28.26.
"""
import os
import subprocess

import imageio_ffmpeg
import numpy as np
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 48000
A, PHRASE = 7.85, 4.9226     # groove start and phrase length (seconds, measured)
TARGET = 30.0

os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
src = os.path.join(HERE, 'out', 'src48.wav')
subprocess.run([FF, '-y', '-loglevel', 'error', '-i', os.path.join(HERE, 'audio_src', 'linkedin_audio.mp3'), '-ar', str(SR), '-ac', '2', src], check=True)
sr, x = wavfile.read(src)
x = x.astype(np.float64) / 32768

a, b = int(A * SR), int((A + PHRASE) * SR)
xf = int(0.015 * SR)
head, loop, tail = x[:b], x[a:b], x[b:]
# equal-power crossfade where the loop copy starts (head ends at the phrase boundary)
w = np.linspace(0, np.pi / 2, xf)[:, None]
seam = head[-xf:] * np.cos(w) + loop[:xf] * np.sin(w)
ext = np.concatenate([head[:-xf], seam, loop[xf:], tail])
mid = os.path.join(HERE, 'out', 'ext48.wav')
wavfile.write(mid, SR, (np.clip(ext, -1, 1) * 32767).astype(np.int16))

k = (len(ext) / SR) / TARGET
subprocess.run([FF, '-y', '-loglevel', 'error', '-i', mid, '-af', f'atempo={k:.6f}', '-ar', str(SR),
                '-t', f'{TARGET}', os.path.join(HERE, 'out', 'audio.wav')], check=True)
print(f'extended {len(x) / SR:.3f}s -> {len(ext) / SR:.3f}s, atempo {k:.4f} -> out/audio.wav ({TARGET}s)')
