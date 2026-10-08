#!/usr/bin/env bash
# Full build: frames -> muxed MP4 at out/oncoxpress_type_ad.mp4, with the synthesised score.
set -euo pipefail
cd "$(dirname "$0")"
FFMPEG=$(python3 -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())')
mkdir -p out
python3 audio.py        # synthesised score -> out/audio.wav (also used by the live preview)
node render.mjs "$@"
"$FFMPEG" -y -loglevel error -i out/video.mp4 -i out/audio.wav -c:v libx264 -preset slow -crf 18 -maxrate 14M -bufsize 28M -pix_fmt yuv420p \
  -c:a aac -b:a 320k -shortest -movflags +faststart out/oncoxpress_type_ad.mp4
echo "-> out/oncoxpress_type_ad.mp4"
