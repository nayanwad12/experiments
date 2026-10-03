# cover-edit: "Make my boring video viral", from boring to editorial cover

One static selfie take, filmed on a phone. The edit directions are spoken on camera, and Claude builds each one on the
word that asks for it. The video starts plain and boring and ends up as a full editorial magazine cover. The look is
cobalt and yellow throughout: halftone duotone, a marker scribble outline, tape notes, paper-cut stickers and a big
condensed headline. Every edit was made with code, with no editing apps.

Dead air is cut and the edit plays 1.05× faster (voice time-stretched, pitch kept): 51.7 s raw → 45 s final,
1080×1920 (9:16), 30 fps.

| output | what it is |
| --- | --- |
| `out/final.mp4` | the edit |
| `out/trimmed_raw.mp4` | the untouched take with the same cuts and speed, frame-for-frame aligned |
| `out/comparison_reel.mp4` | Instagram Reel, "Fully Edited by AI": ORIGINAL (small, tilted, behind) vs VIBE EDITED (big, front), in sync, inside the Reels safe zone (220 px top, 420 px bottom, 35 px left, 120 px right) |

## Pipeline

| step | file | what it does |
| --- | --- | --- |
| ears | `work/asr.py`, `work/align.py` | Silero VAD + Whisper (sherpa-onnx), then pocketsphinx forced alignment → `work/words.json` |
| eyes | `work/matte.py` | RobustVideoMatting on every frame → `alpha.npy` (him vs. the room) |
| edit | `common.py` | edit decision list, speed, word-locked timing helpers |
| sound | `sound.py` | voice clean-up chain (high-pass, denoise, EQ for clarity, de-esser, compressor, limiter). Original 118 BPM house track that builds with the edit, ducked under the voice. SFX on the words. Mastered to −14 LUFS / −1.5 dBTP |
| picture | `render.py` | every beat, word-locked; `--stills <beat…>` renders check frames |
| compare | `trim_raw.py` | raw take with the same cuts and speed-up, no effects |
| reel | `reel.py` | the comparison reel |

The four phones on "best clips" play centre-cropped 9:16 cuts of the earlier edits in this repo (`work/clip_*.npy`).

## The beats

1. **"Hi, this is a normal video. No edits, no music, nothing."**: flat grade, room tone, a ticking clock, a REC/timecode HUD.
2. **"Okay Claude, cut the pauses. See? Faster already."**: a red dashed cut line and a "−X s DEAD AIR" tape; camera bumps start.
3. **"Add the captions. Make them pop. Now change the caption style. Again. And again."**: five caption styles, each landing on its word: bold box, marker, ransom-note letters, typewriter strip, tape headline.
4. **"Cut me out of the background."**: the room turns into a cobalt halftone duotone, and a yellow marker outline draws itself around him.
5. **"Put me on a magazine cover."**: paper and grid background, "VIBE EDITING" headline behind him, masthead, barcode, issue number, an "EDITED 100% BY CLAUDE" tape banner.
6. **"Add some notes around me. Like a real designer would."**: four handwritten tape notes with arrows; stars on "designer".
7. **"Split the screen into frames."**: a 2×2 editorial grid of four live treatments.
8. **"Now show my best clips."**: four phones playing earlier edits.
9. **"Add music. Add sound effects on everything."**: a NOW PLAYING equaliser badge, WHOOSH! POP! BOOM! stickers.
10. **"Make it paper cut. Now make it move."**: die-cut white border, torn edges, paper-cut motion shapes, the headline waves.
11. **"No Premiere Pro, no After Effects, no DaVinci, no Higgsfield…"**: app cards stamp in and get struck through in red.
12. **"…just Claude."**: flash, boom, and the headline becomes "JUST CLAUDE".
13. **"From boring to this."**: a polaroid of the boring take next to the cover, with an arrow.
14. **"Comment EDIT and I will show you how."**: a comment box types EDIT and sends.

## Run

```bash
cp <take>.mp4 raw/raw.mp4
cd work && python3 asr.py turbo en && python3 align.py && python3 matte.py && cd ..
python3 sound.py
python3 render.py          # -> out/final.mp4
python3 trim_raw.py        # -> out/trimmed_raw.mp4
python3 reel.py            # -> out/comparison_reel.mp4
```

Raw footage, model outputs (`*.npy`) and intermediate renders stay out of git.
