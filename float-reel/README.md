# Vibe Editing System ad: floating-UI re-edit

The same raw take and cut as `../sticker-reel`, re-edited in the style of a reference reel the user supplied
(a Pinterest pin about a motion-design tool). Only the pin's cover frame and description could be fetched; the
video host was blocked by the network policy, so the motion is inferred from that frame and the genre.

Outputs: `out/vibe_float_reel.mp4` (1080×1920, 30 fps, about 72 s) and `out/vibe_float_comparison.mp4`.

**Style, from the reference frame**
- the real room stays: a moody, cool, desaturated grade; the wall drops about a stop to grey-teal through the
  matte while the speaker keeps his light. The shot sits 170 px lower than the take, with the plain wall
  extended upward, so there is headroom like the reference
- clean app-UI components float above the speaker and act out each line: toggles, pill buttons, a slider, a
  segmented control, round icon buttons, lime and lavender cards (`style.py`)
- captions: a white handwritten caps line (Shadows Into Light, widened) over a wide heavy italic yellow keyword
  (Syne ExtraBold, slanted) with a black hand-drawn scribble under it
- zoom-blur punches at section changes, punch-ins and shakes on key words, vignette and grain

**Beats:** the hook's UI cluster pops in on "changed"; a timeline with keyframes and a 6-hour clock for the old
way; an EDIT → DIRECT switch on "you direct"; a prompt box, then one toggle per instruction that switches on as it
happens (the pauses get cut, the captions punch, TITLE goes behind him, the frame letterboxes, a BUILD meter rises
into the drop); icon buttons for every cut/caption/effect/sound; code typing on "made in code"; format tabs and
cards; a 50-tile grid with a best performer; a "what you need" checklist; the product card and skill chips;
After Effects / Premiere Pro / Keyframes toggles switching off; a RAW/EDITED switch that cuts to the untouched take
on "I recorded it on my phone"; the end card "Comment VIBE" with a typed comment.

| file | what it does |
| --- | --- |
| `style.py` | fonts, palette, UI components, the float-in motion, the scribble |
| `reel.py` | the edit: grade + shift, captions, UI per section, camera (reuses `../sticker-reel` cut list, words, matte) |
| `score.py` | new groove with the drop on the beat, UI sound design (268 cues), voice from `../sticker-reel`, −14 LUFS |
| `compare_reel.py` | raw beside edit, in sync, with live cut counters, in this style |

```bash
# needs ../sticker-reel/work (frames, alpha.npy, words.json, voice_raw.wav) from that project's pipeline
python3 reel.py stills 2.6 24.9    # check frames (half res)
python3 reel.py render             # -> out/vibe_float_reel.mp4 (also builds work/mix.wav)
python3 compare_reel.py render     # -> out/vibe_float_comparison.mp4
```
