#!/usr/bin/env bash
cd "$(dirname "$0")"
until grep -q "QUEUE3 DONE" queue3.log; do sleep 20; done
(cd 05-faceless-ariane && node ../render3d.mjs scene.html --fps 30 --dur 47.828 --from 11.6 --to 24.7 -o work/patch.mp4 > work/patch.log 2>&1 \
  && python3 build.py render > work/final2.log 2>&1 && python3 build.py sound >> work/final2.log 2>&1); echo "$(date +%T) 05 re-done"
echo QUEUE4 DONE
