# TV reel — "Video editing just changed"

Talking-head reel styled after a retro-TV reference (off-white paper, forest green,
TV orange, Inter Tight / DM Serif / JetBrains Mono, pixel-glitch accents).
Output: 1080x1920, 30 fps, H.264 + AAC, -14 LUFS. Media is git-ignored.

## Layout expected at run time
Scripts resolve paths from the parent of the directory they run in:
`src/raw.mp4`, `fonts/` (Google Fonts), `models/` (sherpa-onnx parakeet + whisper,
RobustVideoMatting resnet50 ONNX), `work/` (scripts + intermediates).

## Pipeline
1. `decode.py` — raw HEVC 60 fps -> 30 fps RGB memmap
2. `asr.py` (parakeet TDT, word timestamps) + `wh.py` (whisper cross-check), `energy.py` / `voiced.py` (pause map)
3. `edl.py` — cut list: false starts, the repeated question take and dead pauses removed; words remapped to output time
4. `rvm.py` — person matte (RobustVideoMatting)
5. `reel.py` — scenes, captions behind the subject, motion graphics, camera, transitions (`stills` / `events` / `video` modes)
6. `audio.py` + `master.sh` — voice chain, synthesized music and SFX, ducking, loudness to -14 LUFS
7. `compare.py` — RAW vs EDITED side-by-side with live cut counters
