#!/usr/bin/env bash
# Sequential render queue for the remaining batch-2 Reels (avoids CPU fights). Logs: */work/*.log, queue.log
cd "$(dirname "$0")"
until grep -q "\->" 03-logo-reveals/work/final.log 2>/dev/null && grep -q "B2_03" 03-logo-reveals/work/final.log; do sleep 10; done
echo "$(date +%T) 03 final done"
(cd 07-bulk && python3 build.py render > work/final.log 2>&1 && python3 build.py sound >> work/final.log 2>&1); echo "$(date +%T) 07 done"
until grep -q "layer.mp4" 04-clay-mascot/work/layer.log 2>/dev/null && grep -q "\-> .*layer.mp4" 04-clay-mascot/work/layer.log; do sleep 10; done
echo "$(date +%T) 04 layer done"
(cd 04-clay-mascot && python3 build.py render > work/final.log 2>&1 && python3 build.py sound >> work/final.log 2>&1); echo "$(date +%T) 04 done"
(cd 05-faceless-ariane && python3 build.py layer > work/layer.log 2>&1); echo "$(date +%T) 05 layer done"
(cd 05-faceless-ariane && python3 build.py render > work/final.log 2>&1 && python3 build.py sound >> work/final.log 2>&1); echo "$(date +%T) 05 done"
(cd 06-audio-build && python3 build.py layer > work/layer.log 2>&1); echo "$(date +%T) 06 layer done"
(cd 06-audio-build && python3 build.py render > work/final.log 2>&1 && python3 build.py sound >> work/final.log 2>&1); echo "$(date +%T) 06 done"
echo ALL DONE
