# vibe-40: "I didn't edit this, my system did" (40 s script take)

One raw phone take (42.9 s, 720x1280 HEVC 60 fps) in; a 32.8 s 1080x1920 30 fps Reel and a raw-vs-edited
comparison out, in the creator-tutorial format of `talking-reel/creator.py` (the Pinterest reference).

- pauses between phrases trimmed to a breath, the off-script word after the CTA dropped (42.9 -> 37.7 s)
- the whole edit at **1.15x** (`core.SPEED`): picture re-timed from 60 fps source frames, voice stretched
  with rubberband (pitch and formants kept) -> 32.8 s
- the script is literal, so the edit does what it says on the word: the captions get called out, real text
  goes behind the speaker (matte), the background swaps, the music drops in on "music", stills of this
  very edit, the export; CTA "comment VIBE" with a DM landing on "I will send it to you"
- this take is framed high, so the footage is dropped ~250 px and the plain wall extended above it

## Run

```bash
cp <take>.mp4 raw/take.mp4
ffmpeg -i raw/take.mp4 -ac 1 -ar 16000 work/audio16k.wav
python3 phrases.py          # pause-split + Whisper medium.en -> work/phrases.json
python3 words.py            # Parakeet second opinion (optional)
python3 align.py            # hand-checked SPOKEN text, force-aligned -> work/words.json
python3 matte.py            # 60 fps frames + RVM matte + head track
python3 core.py             # the cut list at 1.15x
python3 reel.py sheet       # contact sheet for checking
python3 reel.py render      # -> out/vibe40_reel.mp4
python3 compare.py render   # -> out/vibe40_comparison.mp4
```

`models` links to `../talking-reel/models` (RVM + sherpa-onnx Whisper/Parakeet, not in git).
