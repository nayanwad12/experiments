#!/usr/bin/env bash
# Full build: soundtrack -> frames -> out/two_editors_16x9.mp4 (1920x1080, 30 fps, -14 LUFS)
set -euo pipefail
cd "$(dirname "$0")"
python3 audio.py
node render.mjs "$@"
ffmpeg -y -loglevel error -i out/video.mp4 -i out/audio.wav -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p \
  -c:a aac -b:a 256k -af loudnorm=I=-14:TP=-1.5:LRA=11 -ar 48000 -movflags +faststart -shortest out/two_editors_16x9.mp4
echo "-> out/two_editors_16x9.mp4"
