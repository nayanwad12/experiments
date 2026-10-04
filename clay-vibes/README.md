# VIBE EDITING: a 40 s claymation short

**Watch:** [`out/vibe_editing_claymation.mp4`](out/vibe_editing_claymation.mp4) (1920×1080, 16:9, 24 fps, 40 s, with soundtrack)

This is a farmyard cartoon in the style of British plasticine stop-motion, told by a cheeky storybook narrator. Woolly, a clay sheep, is buried in a messy edit. At 3 a.m. a lightbulb goes on. Woolly types *"make it cozy ✨"*, smashes Enter, and the clips hop onto the timeline by themselves. The flock then watches the result with popcorn.

Every frame is generated in code, and so is every sound except the narrator, whose voice comes from an open-source text-to-speech model run offline. There is no stock footage, no samples and no AI imagery.

## How it fakes stop-motion

- **Shot on twos:** the scene has 480 unique exposures at 12 fps, and each one is held for 2 frames at 24 fps. All motion is stepped.
- **Plasticine material** (`lib.py`):
  - Every outline is hand-rolled: a static harmonic "lump" noise plus a per-exposure **boil**, so the characters shimmer the way real clay does when it is nudged between frames.
  - Shading uses a radial key light, offset inner shadows and highlights for a pillowy volume, a soft gloss and a cast shadow on the set.
  - A tiled clay texture is overlaid on top. It is generated procedurally with lumps, grit, **thumbprints** and tool scrapes.
- **Clay type:** font outlines are resampled and wobbled so the letters look hand-rolled, then extruded with a darker side wall.
- **Miniature set:** the clouds hang from visible fishing line, the sky is a painted backdrop with brush texture, the background layers are blurred for a shallow-focus miniature look, and the close-ups use real depth of field.
- **Camera post** (`video.py`): per-exposure exposure **flicker**, vignette, film grain, a scene grade (night blue, magic gold) and classic cartoon **iris** in and out.
- **Cartoon timing:** squash and stretch, bounce landings, anticipation before Enter, and pupils that track whatever is moving.

## Shots

| Time | Shot |
|---|---|
| 0–4 s | **Title.** An iris opens on the farm. The clay letters of VIBE EDITING drop in and squash on the beat. Woolly pops up behind the stone wall: "BAA!" |
| 4–12 s | **The grind.** In the barn edit suite, the window goes from day to dusk to night and the clock spins. Clip blocks lie scattered across the timeline board, film strip spills onto the floor and coffee mugs pile up. Woolly crumples a page, a clip falls off the board, the wool frizzes. The scene ends on a "#@!" bubble and a sad trombone. |
| 12–14.5 s | **The idea.** Close-up: Woolly's eyes snap open, a lightbulb pings on and Woolly rubs both hooves together. |
| 14.5–18 s | **The prompt.** An over-the-shoulder shot: Woolly types "make it cozy" one key per hoof, a clay ✨ pops off the screen and the Enter key gets smashed. |
| 18–28 s | **The magic.** A sparkle burst, then morning arrives. The film strip slurps back into the laptop, the mugs pop and the paper balls bounce away. Ten clips hop onto the timeline, each landing on a xylophone note so the edit climbs a scale. The hen wakes up, the playhead rolls, and Woolly dances. |
| 28–34 s | **The screening.** The flock watches the cozy edit on a bedsheet screen, with popcorn popping out of the bucket. Woolly turns round, winks and gives a hoof-up, and the flock goes "awww". |
| 34–40 s | **End card.** A sunset farm: VIBE EDITING slams down, then "just say the vibe." and the sign *by IDEABRO STUDIO*. Woolly winks and the iris closes on "shave and a haircut… two bits." |

## Narration and captions

The narrator is a British storybook voice (Kokoro `bm_fable`, Apache-2.0, run offline by `narration.py`). The script is written for the viewer: it opens on a relatable hook, gives one punchline per beat and lands on the call to action.

| Cue | Line |
|---|---|
| 0.3 s | "Ever spent a whole night editing... one video?" *(Woolly pops up: "BAA!")* |
| 4.3 s | "Meet Woolly. Woolly's been editing since lunch." |
| 7.6 s | "Click. Cut. Drag. Repeat." |
| 9.6 s | "Three a.m." *(the #@! bubble, then a sad trombone)* |
| 13.0 s | "Then... a bright idea!" |
| 14.6 s | "What if you could just say the vibe?" |
| 18.5 s | "Ta-da!" / "Clips? Sorted. Mess? Gone." / "Every cut lands on the beat." |
| 24.2 s | "That's vibe editing!" / "You bring the vibe. AI does the clicking." |
| 28.9 s | "Even the flock is hooked." |
| 34.4 s | "Vibe Editing... just say the vibe." *(the tagline words pop in on the narrator's words)* / "From Ideabro Studio." |

- **Checked by machine:** each take is placed at its cue and re-read faster, up to 1.3×, if it overruns its slot. Every line was checked with Whisper, both on its own and over the full mix.
- **Captions** (`captions.py`): burned in and kinetic. Words pop in as they are spoken, and the current word is shown in yellow.
- **Applied after the grade:** captions are drawn after the colour grade, so night scenes don't tint them. They stop at the end card, which already spells its words out on screen.
- **Committed takes:** the rendered takes and word timings are committed in `voice/`, so `build.py` runs without the TTS model.

## Sound

`audio.py` synthesises everything else in numpy at 120 BPM, so every cut and gag lands on the grid:

- **Score:** oom-pah tuba, strummed Karplus-Strong ukulele, glockenspiel, a whistled tune, xylophone, woodblock, snaps and shaker. The grind drops to D minor with plodding pizzicato and a sad trombone.
- **Voices:** a formant-synthesised sheep bleat (happy, surprised, grumbling and a flock "aww") and a hen cluck.
- **Foley:**
  - Clay plops, boings, slide whistles, typing, clinks, a crumple, a slurp, pops, whooshes and sparkles.
  - A swish on every cut, a buzzing lightbulb, a sprung sign that wobbles, and clay squishes on every dance step.
- **Ambience beds:**
  - The farm has a breeze, birdsong and a far-off bleat.
  - In the barn, muffled birds fade out and crickets creep in as night falls, while the hen snores.
  - Morning brings birds and a rooster's crow.
  - The screening has the whirr and gate clatter of a 24 fps projector, plus popcorn munching.
  - The end card has a sunset breeze with birds and crickets.
- **Mix:** the music and ambience duck under the narrator (fast attack, slow release). The mix is loudness-normalised to -15 LUFS.

## Build

```bash
pip install skia-python numpy scipy        # plus ffmpeg on PATH
python3 build.py                           # -> out/vibe_editing_claymation.mp4  (~5 min on 4 cores, ~73 MB)
python3 video.py stills 3.5 13.6 25.6      # preview PNGs -> out/stills/
python3 audio.py                           # soundtrack only -> out/audio.wav

# only if you change the script in timeline.NARRATION (needs the Kokoro model files):
pip install kokoro-onnx soundfile
KOKORO_DIR=/path/to/models python3 narration.py   # -> voice/*.wav + voice/lines.json
```

`timeline.py` holds every timing that picture, narration and sound share. `scenes.py` has one function per shot, `chars.py` holds the sheep and hen rigs, and `sets.py` holds the farm, the barn and the props.
