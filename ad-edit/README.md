# TIME ad: talking-head edit + comparison reel

The "You're not bad at content…" Meta ad (Script 1 from `meta-ad-scripts/40s-hook-scripts.md`). One raw phone take
goes in (720×1280, 60 fps, 42 s). Two files come out, both 1080×1920 at 30 fps, H.264 + AAC, −14 LUFS:

| file | what |
|---|---|
| `final/vibe_edit_time.mp4` | the finished edit (36.9 s) |
| `final/vibe_edit_time_comparison.mp4` | the raw take next to the edit, moment for moment, kept inside the Reels safe area |

**Look ("gallery white"):** warm paper, ink black, signature lime `#D4FF3F` and alert orange. Inter Tight Black
for kinetic type behind the speaker, Instrument Serif italic for asides, Unbounded for the wordmark,
JetBrains Mono for UI.

**What the edit does (every cue is read off the spoken words):**
- cuts every pause and the false start at 28 s (42 s raw → 35.7 s of speech)
- kinetic captions **behind** the speaker (person matte); each word slides up out of a mask as it is spoken.
  Accent words are orange, highlighted in lime, set in serif italic, or struck through
- "three hours": a clock ring around the head with a running timer
- "twice a week": a week card with 2 of 7 days posted. The CTA calls back to it with 7 of 7 in lime
- "here is the fix": cut to dark mode, then the VIBE EDITING wordmark reveal with a light streak
- "you record": a REC viewfinder. "you tell the system": a prompt panel where each spoken instruction types
  in and gets ticked off. "cinematic look" brings in a letterbox and teal/orange grade. The music drops on "music"
  (the tempo is chosen so the drop lands on the word), with a lime equaliser and beat pump. "edits the whole
  thing" fills a render bar
- "cuts, captions, effects, sound": lime background with feature chips popping in on each word
- "reels, feed, YouTube": the frame morphs 9:16 → 4:5 → 16:9
- "no timeline / keyframes / editor": Vox-style collage, sticker cut-out, marker strike-throughs
- "recorded on my phone / edited by the system": a raw-vs-edit wipe across the same frame
- CTA: product lockup with rays, a Learn More button with tap ripples, then the end card
- original music (future-bass, synthesised) plus about 60 synthesised sound effects, ducked under the voice

## Run

```bash
cp <take>.mp4 raw/take.mp4
ffmpeg -i raw/take.mp4 -ac 1 -ar 16000 work/audio16k.wav
python3 transcribe.py            # rough Whisper transcript, chunked on pauses (to check what was said)
python3 align.py                 # CHUNKS = the spoken text per chunk (None = cut) -> work/words.json
python3 matte.py                 # frames (1080x1920, 30 fps) + RobustVideoMatting person matte
python3 edit.py info             # cut list + caption groups
./stills.sh 1.0 8.5 16 27        # check moments -> out/row.png
python3 edit.py render           # -> out/vibe_edit_time.mp4
python3 compare.py render        # -> out/vibe_edit_time_comparison.mp4
```

Models: RVM `rvm_mobilenetv3_fp32.onnx` (github.com/PeterL1n/RobustVideoMatting, v1.0.0) and sherpa-onnx
`whisper-small.en` (github.com/k2-fsa/sherpa-onnx, asr-models). Python: skia-python, opencv-python-headless,
onnxruntime, sherpa-onnx, pocketsphinx, numpy, scipy. Shared code comes from `../reels/common` (kit, music, sound, audio_kit).
