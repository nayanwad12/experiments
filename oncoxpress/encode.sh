#!/usr/bin/env bash
# Encode rendered frames + mix into the deliverables.
#   out/oncoxpress_brand_film_HQ.mp4  — 24 Mbps high-quality version (full grain)
#   out/oncoxpress_brand_film.mp4         — web/share version (< 100 MB)
set -euo pipefail
cd "$(dirname "$0")"
FFMPEG=$(python3 -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())')
mkdir -p out
"$FFMPEG" -y -v error -framerate 24 -i work/frames/f%05d.png -i work/mix.wav \
  -c:v libx264 -preset slow -b:v 24M -maxrate 30M -bufsize 48M -tune grain -pix_fmt yuv420p -profile:v high -movflags +faststart \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
  -c:a aac -b:a 320k -shortest out/oncoxpress_brand_film_HQ.mp4
"$FFMPEG" -y -v error -framerate 24 -i work/frames/f%05d.png -i work/mix.wav \
  -c:v libx264 -preset slow -b:v 8200k -maxrate 11000k -bufsize 16000k -tune grain -pix_fmt yuv420p -profile:v high \
  -movflags +faststart -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
  -c:a aac -b:a 256k -shortest out/oncoxpress_brand_film.mp4
ls -la out
