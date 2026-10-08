# SYSTEM reel

The "I didn't edit this video, my system did" talking-head Reel: one raw phone take in, a full
Vox-style edit out (1080x1920, 30 fps), plus a side-by-side comparison reel.

**Look ("ink & highlighter"):** newsprint paper, ink black, highlighter yellow, marker red; Anton for
kinetic type, Instrument Serif italic for asides, JetBrains Mono for UI. Grain, vignette, halftone.

**What the edit does, all cued off the spoken words:**
- cuts every pause between phrases (~60 s raw → ~54 s), keeps the planted stumble on purpose
- giant kinetic type *behind* the speaker (person matte), captions word-by-word in front
- "my system did" / step chapters / "even this" / CTA swap the background for paper, yellow or a ray burst,
  with the speaker cut out as a sticker
- split screen of two phones (raw vs edited) for "on the left… on the right…"
- step tracker, viewfinder, a timeline where the stumble turns red, gets rewound (VHS) and snipped
- prompt box where "make it short / add big text / add music" type out and *happen* (music drops in)
- "system is editing" checklist ticked as each edit is named, punch zoom with speed lines, text burst
- freeze-frame burst on "…even this.", platform cards + export bar, zoom-out to a grid of the page,
  SYSTEM marquee + typed comment for the CTA
- music bed and every sound effect synthesised (reels/common/audio_kit.py), ducked, −14 LUFS

## Run

```bash
cp <take>.mp4 raw/take.mp4
ffmpeg -i raw/take.mp4 -ac 1 -ar 16000 work/audio16k.wav
python3 align.py                 # SPOKEN text (edit it to what was said) -> work/words.json
python3 matte.py                 # frames + RobustVideoMatting person matte (models/rvm_mobilenetv3_fp32.onnx)
python3 edit.py info             # the cut list
python3 edit.py stills 3.2 30    # check moments (half res)
python3 edit.py render           # -> out/system_reel.mp4
python3 compare.py render        # -> out/system_reel_comparison.mp4
```

Models: RVM from `github.com/PeterL1n/RobustVideoMatting/releases` (v1.0.0, mobilenetv3 fp32 onnx).
The spoken text in `align.py` came from a Whisper small.en pass (sherpa-onnx) and was checked by hand;
`transcribe.py` is the faster-whisper route when HuggingFace is reachable. Alignment: pocketsphinx.
