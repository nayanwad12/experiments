#!/bin/sh
# render every style in both aspects, one job at a time
cd "$(dirname "$0")"
mkdir -p logs
for s in 1 2 3 4 5; do
  for f in 16x9 9x16; do
    python3 build.py layer $s --fmt $f --workers 4 > logs/s$s-$f.log 2>&1
  done
done
echo done > logs/queue.done
