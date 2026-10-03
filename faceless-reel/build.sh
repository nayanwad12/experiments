#!/usr/bin/env bash
# Full build: soundtrack -> frames -> two muxed MP4s
#   out/vibe_editing_reel.mp4          clean (add your own caption in Instagram)
#   out/vibe_editing_reel_caption.mp4  with the "Claude cooked 😮‍💨" top caption burned in
set -euo pipefail
cd "$(dirname "$0")"
python3 audio.py
node render.mjs "$@"
node caption.mjs "${CAPTION:-Claude cooked 😮‍💨}"
ENC=(-c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -c:a aac -b:a 256k -af loudnorm=I=-14:TP=-1.5:LRA=11 -ar 48000 -movflags +faststart -shortest)
ffmpeg -y -loglevel error -i out/video.mp4 -i out/audio.wav "${ENC[@]}" out/vibe_editing_reel.mp4
ffmpeg -y -loglevel error -i out/video.mp4 -i out/caption.png -i out/audio.wav -filter_complex "[0:v][1:v]overlay[v]" -map "[v]" -map 2:a "${ENC[@]}" out/vibe_editing_reel_caption.mp4
echo "-> out/vibe_editing_reel.mp4, out/vibe_editing_reel_caption.mp4"
