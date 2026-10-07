#!/usr/bin/env bash
cd "$(dirname "$0")"
until grep -q "QUEUE2 DONE" queue2.log; do sleep 20; done
(cd 04-clay-mascot && node ../render3d.mjs scene.html --fps 30 --dur 20.388 --from 10.203 --to 20.388 -o work/patch.mp4 > work/patch.log 2>&1 \
  && python3 build.py render > work/final2.log 2>&1 && python3 build.py sound >> work/final2.log 2>&1); echo "$(date +%T) 04 re-done"
echo QUEUE3 DONE
