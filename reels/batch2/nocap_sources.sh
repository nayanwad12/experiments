#!/usr/bin/env bash
# Caption-free renders of batch-1 Reels, used as footage on the 3D screens in batch 2.
cd "$(dirname "$0")/.."
for d in "$@"; do
  (cd "$d" && NOCAP=1 python3 -c "import build; build.film.render(out='work/nocap.mp4')")
done
