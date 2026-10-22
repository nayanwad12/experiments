# Vibe Editing System reel ("six steps")

One raw phone take (80 s, 720x1280 HEVC 60 fps) in; a finished 1080x1920 30 fps Reel / Meta ad out, plus a
side-by-side comparison reel.

**Look (from the reference pin):** olive ground, retro photo cards with torn, burnt edges, glowing cream
brush lettering (Caveat Brush), heavy cream caps (Montserrat Black), tomato + pink accents, a line-drawn
smiley sticker, warm film grade, halation and grain. Only the style is borrowed; no names or logos.

**What the edit does, cued to the spoken words:**
- hook: the strongest line ("this exact video went through all six steps") is lifted from 1:10 to 0:00
- every pause between phrases cut to a breath (80.3 s raw -> 73.6 s), silent tail replaced by the end card
- captions word by word *behind* the speaker (RobustVideoMatting cut-out), key words on tomato swipes;
  they move in front, onto the chest, only during the big punch-in so the head never hides them
- a different ground and layout per step: olive room (wall re-tinted via the matte), dark olive, paper,
  tomato, a rapid background swap on "background swapped", torn-paper wipes and whip pans
- motion graphics per line: drop zone + upload, transcript that finds and moves the strongest line,
  2-second hook timer, story-cut timeline that collapses on "gone", word chips with a cut point, giant text
  behind, punch-in brackets, EQ bars + score card + WHOOSH/HIT + synth wave + no-copyright stamp, PROOF
  stamp, contact sheet of stills, chat bubbles, export terminal, 9:16 / 4:5 / 16:9 / 1:1 frames, keyframes
- music synthesised (lo-fi bed, muffled, then the full beat drops on "Sound."), ducked under the voice;
  synthesised SFX on every cut and graphic; voice de-noised, EQ'd, compressed; -14 LUFS

## Run

```bash
cp <take>.mp4 raw/take.mp4
ffmpeg -i raw/take.mp4 -ac 1 -ar 16000 work/audio16k.wav
python3 phrases.py        # pause-split + Whisper medium.en (sherpa-onnx) -> work/phrases.json
python3 words.py          # Parakeet TDT 0.6b second opinion (optional)
python3 align.py          # SPOKEN text (hand-checked) force-aligned per phrase -> work/words.json
python3 matte.py          # frames + RVM matte + head track -> work/frames, work/alpha.npy, work/track.npy
python3 edit.py info      # the cut list
python3 edit.py sheet     # contact sheet for checking
python3 edit.py render    # -> out/vibe_reel.mp4
python3 compare.py render # -> out/vibe_reel_comparison.mp4
```

Models (not in git): `models/rvm_mobilenetv3_fp32.onnx` (PeterL1n/RobustVideoMatting v1.0.0),
`models/sherpa-onnx-whisper-medium.en`, `models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8`
(k2-fsa/sherpa-onnx `asr-models` release). The CTA word is `CTA_WORD` in `edit.py`.
