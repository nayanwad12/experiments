# VIBE EDITING: 40 s crayon explainer

**Watch:** [`out/vibe_editing_crayon_explainer.mp4`](out/vibe_editing_crayon_explainer.mp4)

A 40 second, 16:9 (1920×1080, 24 fps) narrated explainer for **Vibe Editing**, drawn like a kid's crayon
picture on warm paper. Every frame, every sound and the narration are generated in code.

## Look

- **Crayon through paper tooth:** a seamless paper-grain field sets how much pigment each pixel takes. Heavy
  pressure fills the grain, light pressure only catches the peaks, so every stroke comes out waxy and broken.
- **Scribble fills:** shapes are coloured in with zig-zag hatching in three pressures. The grain is stretched
  along the stroke direction, and the outline is drawn twice by a slightly shaky hand.
- **Boiling lines:** every line is re-wobbled 12 times a second, as if each frame had been redrawn by hand.
  Things get sketched on (outline first, then coloured in) and pop with an overshoot.
- **Crayon-scribble wipes** between scenes.
- Fonts (OFL / Apache, Google Fonts): Luckiest Guy (titles), Gochi Hand, Caveat Brush, Patrick Hand.

## Narration

The narration uses [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) TTS, run locally: `af_heart` reads
the narration and `am_puck` speaks the typed prompt. Word cues come from the pauses in each take, and every
pop, scribble and doodle is placed on its word.

| Time | Narration | Picture |
|---|---|---|
| 0–8 s | "Remember editing videos? Hours of cutting, dragging, and keyframing, one tiny clip at a time, until your eyes go square." | A frazzled editor at a desk. The clock spins, clips pile onto the timeline, mugs stack up, and on "square" their eyes turn square. |
| 8–11.5 s | "Now there's a new way. It's called Vibe Editing." | A lightbulb is sketched on and lights up, then **VIBE EDITING** pops in letter by letter. |
| 11.5–19.5 s | "No more fighting the timeline. You just describe the vibe you want, in plain words." / *"Make it warm, punchy, and a little dreamy."* | The timeline is scribbled out and tossed away. A speech bubble writes out the prompt, and a sun (warm), a POW! (punchy) and a cloud and moon (dreamy) pop up on their words. |
| 19.5–25.5 s | "And AI does the heavy lifting. The cuts, the colors, the captions, the music. All on the beat." | A robot lifts an "HOURS" barbell. A card pops in for each of cuts, colours, captions and music, then everything bounces on the beat. |
| 25.5–32.8 s | "What took a whole weekend, now takes a coffee break. You stay the director. AI handles the keyframes." | A weekend calendar gets scribbled in, then an arrow points to a coffee cup. Next, you sit in the director's chair with a megaphone while the robot juggles keyframes. |
| 32.8–40 s | "Vibe Editing. Say the vibe, and watch it come to life." | The end title. Doodles are drawn in and come alive, with the line "by Ideabro Studio". |

## Sound

The music is an original bed at 100 BPM in C major (C–G–Am–F), built from plucks, glockenspiel, soft bass,
kick and shaker. During the "old way" scene it plays as a muffled, tired loop over a ticking clock, and the full
band comes in on the reveal. SFX include crayon scribbles (grainy band-passed noise), pops, a boing, a punch, a
barbell thud, whooshes and sparkle glisses. The music ducks under the voice, and the mix sits at about −14 LUFS.
Everything is synthesised in numpy, so there are no samples.

## Build

```bash
pip install skia-python numpy scipy soundfile kokoro-onnx pillow
# Kokoro model files -> /home/user/models (or set MODELS=...)
#   https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
#   https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
python3 narration.py              # -> work/vo_*.wav
python3 audio.py                  # -> work/mix.wav
python3 video.py render           # -> work/picture.mp4 (about 10 min on 4 cores)
ffmpeg -i work/picture.mp4 -i work/mix.wav -c:v copy -c:a aac -b:a 192k -shortest out/vibe_editing_crayon_explainer.mp4
python3 video.py stills 4.5 18.9  # preview PNGs -> work/stills/
```

| File | Contents |
|---|---|
| `crayon.py` | The engine: paper, tooth, `Pen` (crayon lines, hatched shapes, lettering), easing, transforms |
| `scenes.py` | The six scenes, the characters and props, and the cue times |
| `narration.py` | Script and TTS |
| `audio.py` | Music, SFX and the mix |
| `video.py` | Multiprocess frame renderer piped into ffmpeg |
