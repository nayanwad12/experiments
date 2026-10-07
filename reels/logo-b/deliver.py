"""deliver: mux picture + sting into the final files.

  16x9 -> out/B_logo_4K_16x9.mp4 (3840x2160 60 fps master) + out/B_logo_1080p_16x9.mp4
  9x16 -> out/B_logo_1080x1920_9x16.mp4      1x1 -> out/B_logo_1080_1x1.mp4
Every file: H.264 high, 4:2:0, AAC 320k 48 kHz, -14 LUFS, kept under ~28 MB so it can be shared anywhere.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))
from vibelib import ff  # noqa: E402

NAMES = {"16x9": "B_logo_4K_16x9", "9x16": "B_logo_1080x1920_9x16", "1x1": "B_logo_1080_1x1"}


def encode(picture, audio, out, fps, dur, crf=14, cap_mb=27.5, scale=None):
    mbps = cap_mb * 8 * 0.95 / dur - 0.33
    vf = ["-vf", f"scale={scale}:flags=lanczos"] if scale else []
    ff("-i", picture, "-i", audio, "-map", "0:v:0", "-map", "1:a:0", *vf, "-c:v", "libx264", "-preset", "slow",
       "-crf", str(crf), "-maxrate", f"{mbps:.1f}M", "-bufsize", f"{2 * mbps:.1f}M", "-pix_fmt", "yuv420p",
       "-profile:v", "high", "-tune", "film", "-r", str(fps), "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
       "-t", f"{dur:.3f}", "-movflags", "+faststart", out)
    print("->", out, f"{Path(out).stat().st_size / 1e6:.1f} MB")


def final(fmt, picture, audio, out_dir, fps, dur):
    out_dir = Path(out_dir); out_dir.mkdir(exist_ok=True)
    encode(picture, audio, out_dir / f"{NAMES[fmt]}.mp4", fps, dur)
    if fmt == "16x9":
        encode(picture, audio, out_dir / "B_logo_1080p_16x9.mp4", fps, dur, crf=15, scale="1920:1080")
