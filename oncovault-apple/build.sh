#!/usr/bin/env bash
# Full build: frames -> muxed MP4 at out/oncovault_promo.mp4, using the supplied soundtrack.
set -euo pipefail
cd "$(dirname "$0")"
FFMPEG=$(python3 -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())')
mkdir -p out
python3 make_audio.py   # supplied track extended to 30.0 s -> out/audio.wav (also used by the live preview)
node render.mjs "$@"
"$FFMPEG" -y -loglevel error -i out/video.mp4 -i out/audio.wav -c:v libx264 -preset slow -crf 18 -maxrate 14M -bufsize 28M -pix_fmt yuv420p \
  -c:a aac -b:a 320k -shortest -movflags +faststart out/oncovault_promo.mp4
echo "-> out/oncovault_promo.mp4"
