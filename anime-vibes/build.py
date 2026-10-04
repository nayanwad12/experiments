"""One-shot build: narration -> soundtrack -> picture -> out/vibe_editing_anime.mp4"""
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))


def run(*cmd):
    subprocess.run(cmd, check=True, cwd=HERE)


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "work"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    run("python3", "narration.py")
    run("python3", "audio.py")
    run("python3", "video.py", "render", "work/picture.mp4")
    run("ffmpeg", "-y", "-loglevel", "error", "-i", "work/picture.mp4", "-i", "work/mix.wav", "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", "out/vibe_editing_anime.mp4")
    print("-> out/vibe_editing_anime.mp4")
