# claude-edit — "Let Claude edit your videos", done for real

One take, filmed on a phone, with the edit directions spoken on camera. Claude listens to every word
(Whisper + forced alignment), looks at the frames, and builds each effect on the exact word that asks for it.
The dead air is cut: 86 s raw → 67 s final, 1920×1080 (16:9), 30 fps.

## Pipeline

| step | file | what it does |
| --- | --- | --- |
| ears | `work/asr.py` | Silero VAD + Whisper (sherpa-onnx, `turbo`) → transcript segments |
| ears | `work/align.py` | pocketsphinx forced alignment of the corrected script → `work/words.json` (time of every word) |
| eyes | `work/matte.py` | RobustVideoMatting on every frame → `alpha.npy` (him vs. the room) |
| plate | `prep.py plate` | empty-room clean plate: masked temporal median + LaMa for the wall + headboard/sheet rebuilt from visible texture |
| track | `prep.py palm_track` | template-matched palm so the logo sits on the hand |
| edit | `common.py` | edit decision list (silences trimmed, pauses kept where an effect needs room) |
| sound | `sound.py` | voice cut + compressed, original synthesised music bed (ducked), cinematic drone, SFX on the words |
| picture | `render.py` | every effect, word-locked; `--stills <beat…>` renders check frames |

## The beats (each triggered by the spoken direction)

1. **"Editing videos manually might be over."** — kinetic type behind him, red strike, *OVER.* slam.
2. **"Zoom in on my hand."** — camera push onto the palm.
3. **"Now put my logo right here… in 3D."** — logo pops onto the tracked palm, extrudes into 3D and spins.
4. **"Make me grab the logo and throw it straight at the camera."** — wind-up, flies at the lens, glass cracks, shake, flash; the glass falls away on "Okay".
5. **"Separate this scene into layers: the background, me, and the text."** — exploded 3D view of three real layers, labelled on each word; collapses with *NO TIMELINE* sitting between room and him.
6. **"Now remove me." / "Bring me back."** — he disintegrates into particles, the empty room keeps talking, he re-forms.
7. **"Put me inside a frame on the right… the anatomy of a viral reel."** — he shrinks into a reel card; hook / retention / share build on the words.
8. **"Back to the full screen."** — card expands back.
9. **"Now put my best videos floating behind me in 3D."** — the repo's own renders play on floating 3D screens behind his cutout.
10. **"Turn this entire scene into a cinematic documentary… dramatic lighting, slow camera push-in, movie-style titles."** — letterbox, teal/orange grade, relight, push-in, serif titles, subtitles.
11. **"And all of this was edited with AI."** — recap grid of every effect.
12. **"Comment EDIT and I will show you how."** — comment box types EDIT, send.

## Run

```bash
# models (GitHub release assets): sherpa-onnx whisper-turbo, silero_vad.onnx, rvm_resnet50_fp32.onnx, lama.onnx in /home/user/models
cp <take>.mp4 raw/raw.mp4
cd work && python3 asr.py turbo en && python3 align.py && python3 matte.py && cd ..
python3 prep.py
python3 sound.py
python3 render.py          # -> out/final.mp4
```

Raw footage, model outputs (`*.npy`) and renders stay out of git.
