# science-talk: "Stress se psoriasis" talking-head edit

A 7 min 25 s teleprompter take (Hindi, vertical 4K phone footage) cut into a natural **3 min 16 s**
Reel/Short (1080x1920, 30 fps). The cut is played at 1.2x, the Hinglish captions are kinetic and white, and the
motion graphics, real science images, music and SFX are all cued off the spoken words.

## What the edit does

- **Story edit from the transcript.** Every retaken line keeps its last complete take: the mechanism was read
  3 times, and the breathing tip, the sleep tip, the recap, the mom story and the close were each read twice.
  False starts ("…aur loop todna hi"), teleprompter pauses and dead air are dropped. Each cut was checked by
  re-decoding the audio on both sides of it. Then 1.2x (`atempo`, so the pitch stays natural), cut on exact
  frame boundaries so sound and picture can't drift.
- **Captions** are Hinglish in English letters, white Montserrat Black, built word by word with a spring pop.
  Key words are bigger and underlined. Some lines sit *behind* the speaker (person matte), along with giant
  words: SIRF 1 CHEEZ / PSORIASIS / STRESS / WEIGHTS / PART 3 / SCIENCE · DECISION AAPKA. Also exported as
  `out/captions_hinglish.srt`.
- **Two looks.** CAM: real footage with jump-cut punch-ins, and photos/graphics parked behind the head.
  STUDIO: dark science backdrop with the speaker cut out at the bottom and flowcharts above it, used for the
  mechanism, the stress loop, the 2025 meta-analysis ranking, the recap and the reversed loop.
- **Science visuals:** skin histology (H&E, epidermis + dermis), immunostained tissue, a CT brain slice
  (scikit-image's open sample data), the real 3D structure of **cortisol** (RDKit, C21H30O5) rotating,
  procedural T-cells that go overactive and attack the skin, plus Fluent 3D emoji icons (MIT).
- **Flowcharts:** STRESS → BRAIN → CORTISOL → IMMUNE → T-CELLS → SKIN; the stress ⇄ flare loop (it speeds up,
  then breaks on "loop todna hai"); the sleep chain; the recap chain; the loop running backwards in green.
- **Explainers:** 6 breaths/min counter, a 4 s in / 6 s out breathing orb, the vagus nerve line, box breathing
  traced side by side as each phase is spoken, 2-3x a day × 5 min, ranking bars (Yoga, Qigong, Brisk walking),
  20-30 min, 7-8 hours, a NON-NEGOTIABLE stamp, mom-story polaroids, a 1-2-3 start plan, and a "PART 3"
  comment box.
- **Sound:** voice chain (high-pass, denoise, presence, compression, de-ess). A synthesised "tech" music bed
  crossfades to a soft cinematic bed for the mom story, is ducked under the voice, and carries 93 word-cued SFX
  (pops, whooshes, impacts, risers, ticks, typing). Mixed to −14 LUFS.

## Pipeline

```bash
cp <take>.mp4 raw/take.mp4
ffmpeg -i raw/take.mp4 -map 0:a:0 -ac 1 -ar 16000 work/audio16k.wav
ffmpeg -i raw/take.mp4 -map 0:a:0 -ac 2 -ar 48000 work/audio48k.wav
ffmpeg -i raw/take.mp4 -map 0:v:0 -vf scale=1080:1920:flags=lanczos -c:v libx264 -crf 16 -an work/proxy1080.mp4
python3 asr.py hi transcribe --fine   # Whisper turbo (sherpa-onnx export) -> work/segs_fine_hi_transcribe.json
python3 prep_images.py      # science plates -> assets/img
python3 script.py           # the story edit -> work/edl.json (cuts + word timings)
python3 cut.py              # -> work/base.mp4 + work/voice.wav (cut, 1.2x)
python3 matte.py            # RobustVideoMatting -> work/alpha.npy
python3 edit.py stills 5.2 30    # check frames;  edit.py sheet  /  edit.py srt
python3 edit.py render      # -> work/picture.mp4
python3 sound.py            # -> work/mix.wav
ffmpeg -i work/picture.mp4 -i work/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest out/final.mp4
```

`asr.py` runs Whisper by hand (numpy + onnxruntime). sherpa-onnx's own recognizer drops
partial UTF-8 bytes per token, which mangles Devanagari, so here the token bytes are joined before decoding.
Models in `/home/user/models` (GitHub release assets): `sherpa-onnx-whisper-turbo`, `silero_vad.onnx`,
`rvm_mobilenetv3_fp32.onnx`. Icons: microsoft/fluentui-emoji. Raw footage, model outputs and renders stay out
of git.
