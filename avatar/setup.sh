#!/usr/bin/env bash
# One-time setup: SadTalker (open-source, Apache-2.0) in its own Python 3.10 env, CPU only.
# Everything lands in $AVATAR_HOME (default ~/avatar-tools); nothing needs an account or API key.
set -euo pipefail

AVATAR_HOME="${AVATAR_HOME:-$HOME/avatar-tools}"
ST="$AVATAR_HOME/SadTalker"
mkdir -p "$AVATAR_HOME"

[ -d "$ST" ] || git clone --depth 1 https://github.com/OpenTalker/SadTalker.git "$ST"

if [ ! -x "$AVATAR_HOME/venv/bin/python" ]; then
  uv python install 3.10
  uv venv --python 3.10 "$AVATAR_HOME/venv"
fi
PY="$AVATAR_HOME/venv/bin/python"

uv pip install --python "$PY" \
  torch==2.1.2 torchvision==0.16.2 \
  numpy==1.23.4 face_alignment==1.3.5 imageio==2.19.3 imageio-ffmpeg==0.4.7 \
  librosa==0.9.2 numba resampy==0.3.1 pydub==0.25.1 scipy==1.10.1 kornia==0.6.8 \
  tqdm yacs==0.1.8 pyyaml joblib==1.1.0 scikit-image==0.19.3 basicsr==1.4.2 \
  facexlib==0.3.0 gfpgan av safetensors "setuptools<70"

# Model weights (GitHub releases).
cd "$ST"
mkdir -p checkpoints gfpgan/weights
get() { [ -s "$2" ] || curl -fL --retry 4 -o "$2.part" "$1" && { [ -s "$2" ] || mv "$2.part" "$2"; }; }
R=https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc
get $R/mapping_00109-model.pth.tar          checkpoints/mapping_00109-model.pth.tar
get $R/mapping_00229-model.pth.tar          checkpoints/mapping_00229-model.pth.tar
get $R/SadTalker_V0.0.2_256.safetensors     checkpoints/SadTalker_V0.0.2_256.safetensors
get $R/SadTalker_V0.0.2_512.safetensors     checkpoints/SadTalker_V0.0.2_512.safetensors
F=https://github.com/xinntao/facexlib/releases/download
get $F/v0.1.0/alignment_WFLW_4HG.pth        gfpgan/weights/alignment_WFLW_4HG.pth
get $F/v0.1.0/detection_Resnet50_Final.pth  gfpgan/weights/detection_Resnet50_Final.pth
get $F/v0.2.2/parsing_parsenet.pth          gfpgan/weights/parsing_parsenet.pth
get https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth gfpgan/weights/GFPGANv1.4.pth

echo "SadTalker ready in $ST"
