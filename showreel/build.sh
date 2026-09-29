#!/usr/bin/env bash
# Full build: soundtrack -> frames -> muxed MP4 at out/vibe_editing_showreel.mp4
set -euo pipefail
cd "$(dirname "$0")"
FFMPEG=$(python3 -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())')
python3 audio.py
node render.mjs "$@"
"$FFMPEG" -y -loglevel error -i out/video.mp4 -i out/audio.wav -c:v libx264 -preset slow -b:v 18M -maxrate 24M -bufsize 36M -pix_fmt yuv420p -c:a aac -b:a 320k -shortest \
  -movflags +faststart out/vibe_editing_showreel.mp4
echo "-> out/vibe_editing_showreel.mp4"
