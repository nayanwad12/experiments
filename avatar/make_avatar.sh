#!/usr/bin/env bash
# Photo + voice -> talking-head video with SadTalker (CPU, free, offline once set up).
#   ./make_avatar.sh input/me.jpg work/voice.wav out/avatar.mp4
# Env knobs: SIZE=256|512 (face model res; 512 is ~4x slower on CPU), ENHANCE=gfpgan|none, STILL=1 (less head motion),
#            EXPR=1.0 (expression strength), MAXW=1080 (photo is downscaled to this width first)
set -euo pipefail

IMG="$1"; AUDIO="$2"; OUT="${3:-out/avatar.mp4}"
AVATAR_HOME="${AVATAR_HOME:-$HOME/avatar-tools}"
ST="$AVATAR_HOME/SadTalker"; PY="$AVATAR_HOME/venv/bin/python"
SIZE="${SIZE:-256}"; ENHANCE="${ENHANCE:-gfpgan}"; STILL="${STILL:-1}"; EXPR="${EXPR:-1.0}"; MAXW="${MAXW:-1080}"

[ -x "$PY" ] || { echo "run ./setup.sh first"; exit 1; }
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT

# Keep the photo small enough that pasting the face back is fast; even dims for H.264.
ffmpeg -v error -y -i "$IMG" -vf "scale='min($MAXW,iw)':-2" "$WORK/face.png"
ffmpeg -v error -y -i "$AUDIO" -ac 1 -ar 16000 "$WORK/voice.wav"

ARGS=(--driven_audio "$WORK/voice.wav" --source_image "$WORK/face.png" --result_dir "$WORK/res"
      --preprocess full --size "$SIZE" --expression_scale "$EXPR" --cpu)
[ "$STILL" = 1 ] && ARGS+=(--still)
[ "$ENHANCE" != none ] && ARGS+=(--enhancer "$ENHANCE")

(cd "$ST" && "$PY" inference.py "${ARGS[@]}")

RES="$(find "$WORK/res" -maxdepth 1 -name '*.mp4' | head -1)"
mkdir -p "$(dirname "$OUT")"
# Re-encode with the original audio at full quality, phone-friendly H.264.
ffmpeg -v error -y -i "$RES" -i "$AUDIO" -map 0:v -map 1:a -c:v libx264 -crf 18 -preset medium \
  -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart "$OUT"
echo "done -> $OUT"
