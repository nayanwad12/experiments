#!/bin/sh
# render every format in turn (one at a time keeps the CPU from thrashing)
cd "$(dirname "$0")"
mkdir -p logs
python3 build.py layer --fmt 9x16 --workers 4 > logs/9x16.log 2>&1
python3 build.py layer --fmt 1x1 --workers 4 > logs/1x1.log 2>&1
python3 build.py layer --fmt 16x9 --workers 3 > logs/16x9.log 2>&1
echo done > logs/queue.done
