# Vibe Editing: a 60 s Vox-style explainer

A 60-second vertical (1080×1920, 30 fps) narrated motion-graphics explainer: **"The cut is becoming a sentence."**
Built entirely in code, in the Vox "mixed media" editorial collage style learned from the `vox-animation` skill:
6 scenes × 10 s, scene *N*'s narration lands on scene *N*'s picture, with one through-line object (the film strip and the
cut) that escalates from scissors on celluloid to a sentence typed on a phone.

## Design system

| Token | Value | Use |
|---|---|---|
| Warm yellow | `#F7C948` | scene fields 1 and 4, highlighter swipes |
| Off-white paper | `#F2ECDF` | scene fields 3 and 6 |
| Deep navy | `#1E2B4D` | scene fields 2 and 5, screens |
| Coral | `#EF6351` | the one loud accent: tags, the dashed cut line, marker circles |
| Ink | `#161514` | marker annotations, type |
| Teal / periwinkle | `#5FB3A8` / `#8FA2D6` | UI chips only (timeline clips, code lines) |

- **Archival cutouts:** objects are drawn as greyscale "photos", then printed through a 45° halftone into newsprint
  tone with a rough white paper border and a baked drop shadow (`design.cutout`). These include the film strip, scissors,
  a 1924 Moviola, a 1989 workstation, a laptop, a phone and a portrait frame (`cutouts.py`).
- **Paper and print:** paper grain on everything, and a halftone dot gradient that pools in the corners of each colour field.
  Torn-edge paper tags carry typewriter labels (Space Mono), plus tape strips.
- **Marker annotations:** circles, underlines, arrows, a check mark and a question mark that draw themselves.
- **Type:** Montserrat Black for headline words, Space Mono for archival labels and typed prompts. Text stays short.
- **Motion:** quick ease-out entrances with overshoot, slow push-ins, and one loud thing at a time. Every scene boundary is a
  whip-pan in which the outgoing and incoming scenes travel together under directional motion blur (the fake one-shot).

## Script (narrator: Kokoro `am_michael`)

| Scene | Narration | Picture |
|---|---|---|
| 1 | For a hundred years, editing a video meant one gesture. The cut. Now the cut is becoming a sentence. | Film strip, "100 YEARS". Scissors snip it, and the gap fills with a typed line: *cut right after the laugh* |
| 2 | In nineteen twenty-four, editors cut film by hand on a Moviola. In nineteen eighty-nine, Avid moved the cut onto screens. | 1924 Moviola cutout, scissors snipping frames. A marker arrow leads to a 1989 workstation whose timeline fills in |
| 3 | Then, in February twenty twenty-five, Andrej Karpathy coined vibe coding. Describe what you want, and let AI write the code. | A 1989 calendar page tears away to FEB 2025, then a "vibe coding" card. A laptop chat turns into cascading code |
| 4 | Vibe editing is the same idea, for video. You type: cut the pauses, add captions, make it punchy. It happens. | "vibe ~~coding~~ editing". On a phone, the prompt is typed, then gaps close, silences vanish and captions pop |
| 5 | But here's the catch. The software can make a thousand cuts. It still can't tell which one actually matters. | THE CATCH. A counter runs to 1,000 cuts filling a grid, then everything dims except one cut, circled with a "?" |
| 6 | So the cut didn't disappear. It moved, from your hands, to your words. The editor is still you. | Scissors on a dashed cut line, HANDS → WORDS, a "cut here." bubble, then a portrait frame stamped YOU |

## Build

```bash
pip install skia-python numpy scipy soundfile imageio-ffmpeg kokoro-onnx
# Kokoro model files -> ./models (from github.com/thewh1teagle/kokoro-onnx, release model-files-v1.0)
#   kokoro-v1.0.onnx, voices-v1.0.bin
python3 build.py              # narration -> frames -> mix -> out/vibe_editing_vox.mp4
python3 build.py --no-voice   # reuse out/voice + out/cues.json
python3 render.py stills 4.3 37.6   # preview PNGs
```

- `script.py`: the narration lines (split into phrases), the voice settings and the sources.
- `voice.py`: Kokoro TTS, voiced phrase by phrase. It writes `out/cues.json` with each phrase's start time, and every visual
  hit in `scenes.py` keys off those cues, so re-voicing re-syncs the picture automatically. If a take overruns, it re-voices
  the take slightly faster.
- `scenes.py`: the six scenes and their SFX cue lists. `render.py`: frames and whip-pans. `audio.py`: an original
  84 BPM score, paper and marker foley, narration ducking. `build.py` muxes and normalises to -14 LUFS.

## Sources

- Moviola, the first film-editing machine (1924): <https://en.wikipedia.org/wiki/Moviola>, <https://en.wikipedia.org/wiki/Iwan_Serrurier>
- Avid Media Composer, sold from NAB 1989: <https://en.wikipedia.org/wiki/Media_Composer>, <https://broadcastbeat.com/news/non-linear-editing-and-the-arrival-of-avid>
- Karpathy's "vibe coding" post, 2 Feb 2025: <https://knowyourmeme.com/memes/vibe-coding>; Collins Word of the Year 2025: <https://www.lbc.co.uk/tech/vibe-coding-clanker-word-of-the-year-collins>
- What vibe editing is: <https://pexo.ai/vibe-hub/vibe-editing>, <https://www.kapwing.com/resources/how-to-edit-videos-with-ai-prompts-prompts-included/>
