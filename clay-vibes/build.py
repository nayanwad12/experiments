"""One-shot build: soundtrack + picture -> out/vibe_editing_claymation.mp4"""

import os
import subprocess

import numpy as np
from scipy.io import wavfile

import audio
import video

OUT = video.OUT

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    wav = os.path.join(OUT, "audio.wav")
    wavfile.write(wav, audio.SR, (audio.build() * 32767).astype(np.int16))
    video.render()
    final = os.path.join(OUT, "vibe_editing_claymation.mp4")
    subprocess.run([video.FFMPEG, "-y", "-loglevel", "error", "-i", os.path.join(OUT, "video_noaudio.mp4"),
                    "-i", wav, "-c:v", "copy", "-af", "loudnorm=I=-15:TP=-1.5:LRA=11", "-ar", "48000",
                    "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", final], check=True)
    print("wrote", final)
