set -e
ffmpeg -v error -y -i mix_pre.wav -af "volume=2dB,alimiter=limit=0.708:attack=2:release=60:level=disabled" -ar 48000 mix_lim.wav
J=$(ffmpeg -hide_banner -i mix_lim.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | grep -A12 '^{')
I=$(echo "$J" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['input_i'],d['input_tp'],d['input_lra'],d['input_thresh'],d['target_offset'])")
set -- $I
ffmpeg -v error -y -i mix_lim.wav -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$1:measured_TP=$2:measured_LRA=$3:measured_thresh=$4:offset=$5:linear=true:print_format=summary" -ar 48000 mix_final.wav 2>&1 | tail -3
ffmpeg -hide_banner -i mix_final.wav -af ebur128=peak=true -f null - 2>&1 | grep -E "I:|Peak:" | tail -2
