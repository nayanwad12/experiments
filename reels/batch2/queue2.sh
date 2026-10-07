#!/usr/bin/env bash
cd "$(dirname "$0")"
until grep -q "ALL DONE" queue.log; do sleep 20; done
(cd 03-logo-reveals && python3 build.py render > work/final2.log 2>&1 && python3 build.py sound >> work/final2.log 2>&1); echo "$(date +%T) 03 re-done"
echo QUEUE2 DONE
