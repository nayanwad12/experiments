"""One-shot build: audio + video -> out/vibe_editing_promo.mp4"""

import os
import subprocess

import audio
import video
from scipy.io import wavfile

OUT = video.OUT

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    wav = os.path.join(OUT, "audio.wav")
    wavfile.write(wav, audio.SR, (audio.build() * 32767).astype("int16"))
    video.render()
    final = os.path.join(OUT, "vibe_editing_promo.mp4")
    subprocess.run([video.FFMPEG, "-y", "-loglevel", "error", "-i", os.path.join(OUT, "video_noaudio.mp4"),
                    "-i", wav, "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest",
                    "-movflags", "+faststart", final], check=True)
    print("wrote", final)
