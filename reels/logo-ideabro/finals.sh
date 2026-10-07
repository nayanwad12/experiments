#!/bin/sh
# mux each style/format as soon as its picture is rendered
cd "$(dirname "$0")"
while :; do
  for s in 1 2 3 4 5; do
    n=$(python3 -c "print({1:'chrome',2:'particles',3:'neon',4:'glitch',5:'metal'}[$s])")
    for f in 16x9 9x16; do
      if [ -f work/$n/$f.mp4 ] && [ ! -d work/$n/$f.mp4.segs ] && [ ! -f out/IDEABRO_0${s}_${n}_$f.mp4 ]; then
        nice -n 10 python3 build.py final $s --fmt $f >> logs/finals.log 2>&1 && echo "muxed $s $f"
      fi
    done
  done
  [ -f logs/queue.done ] && [ "$(ls out/IDEABRO_0*_*.mp4 2>/dev/null | wc -l)" -ge 10 ] && break
  sleep 30
done
echo all-finals
