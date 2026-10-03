"""One-shot build: narration -> frames -> mix -> out/vibe_editing_vox.mp4

    python3 build.py            # everything
    python3 build.py --no-voice # reuse out/voice + out/cues.json
"""

import os
import subprocess
import sys

import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


def run(*args):
    subprocess.run([sys.executable, *args], cwd=HERE, check=True)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    if "--no-voice" not in sys.argv:
        run("voice.py")
    run("render.py", "video")
    run("audio.py")
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
                    "-i", os.path.join(OUT, "video_noaudio.mp4"), "-i", os.path.join(OUT, "mix.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", os.path.join(OUT, "vibe_editing_vox.mp4")], check=True)
    print("done ->", os.path.join(OUT, "vibe_editing_vox.mp4"))
