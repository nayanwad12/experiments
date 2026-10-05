# Vibe Editing — Apple-style explainer (40 s, 16:9)

A 40-second, 1920×1080, 60 fps motion-graphics explainer: white background, black type in four faces
(Inter Tight 300–900, Instrument Serif italic, JetBrains Mono). It has a narrated script, an original music bed and close-mic
ASMR foley. Everything is generated in code. No After Effects, no Premiere Pro, no stock assets.

**Output:** `out/vibe_editing_apple.mp4`

## Script (Kokoro TTS, voice `af_heart`)
| time | narration | picture |
|---|---|---|
| 0.0 | After Effects. Premiere Pro. Higgsfield. | caret blink, each name in a different typeface, roll transitions |
| 3.1 | Another month. Another subscription. | iOS-style subscription notifications stacking up |
| 5.5 | What if you didn't need any of them? | cards fall away, serif-italic punchline |
| 7.8 | This is the era of vibe editing. | zoom-through, letter-by-letter blur reveal, shimmer, drop at 9.0 |
| 10.9 | You don't drag keyframes. You describe the vibe. | keyframes pop off a timeline, which morphs into a prompt bar and types |
| 14.5 | Smooth transitions. Kinetic type. Sound design. | iris to black, morphing shape, spring letters, waveform |
| 18.5 | (music) | rapid cuts on the beat: Captions / Color / Motion / Music |
| 20.3 | Even this video. Every frame, every sound, came from a prompt. | the film zooms out into a player and replays itself at 4.5× |
| 24.8 | No timeline. No plugins. No subscriptions. | three rows, icons crossed out |
| 28.3 | Just your idea, and the words to describe it. | serif idea + typed line |
| 32.4 | Welcome to vibe editing. | logo lockup, "Direct the vibe.", the old tools struck through |

## Build
```bash
pip install skia-python numpy scipy soundfile kokoro-onnx pillow
python3 vibe/tts.py --script work/script.txt -o work/vo.wav --gap 0.3   # narration takes
python3 audio.py                                                          # music + foley + voice -> work/mix_raw.wav
ffmpeg -i work/mix_raw.wav -af loudnorm=I=-14:TP=-1:LRA=11 -ar 48000 work/mix.wav
python3 video.py render                                                   # -> out/picture.mp4 (all cores)
ffmpeg -i out/picture.mp4 -i work/mix.wav -c:v copy -c:a aac -b:a 256k -shortest out/vibe_editing_apple.mp4
python3 video.py sheet          # contact sheet of key frames
```
Every timing lives in `timeline.py`, and both picture and sound read it.
