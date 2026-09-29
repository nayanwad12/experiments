# claude-edit — "Let Claude edit your videos", done for real

One take, filmed on a phone, with the edit directions spoken on camera. Claude listens to every word
(Whisper + forced alignment), looks at the frames, and builds each effect on the exact word that asks for it.
The dead air is cut and the whole edit plays 1.1× faster (voice time-stretched, pitch kept): 86 s raw → 58.7 s final,
1920×1080 (16:9), 30 fps. `out/final.mp4` is the edit; `out/trimmed_raw.mp4` is the untouched take with the same cuts
and speed, frame-for-frame aligned for side-by-side comparison.

## Pipeline

| step | file | what it does |
| --- | --- | --- |
| ears | `work/asr.py` | Silero VAD + Whisper (sherpa-onnx, `turbo`) → transcript segments |
| ears | `work/align.py` | pocketsphinx forced alignment of the corrected script → `work/words.json` (time of every word) |
| eyes | `work/matte.py` | RobustVideoMatting on every frame → `alpha.npy` (him vs. the room) |
| plate | `prep.py plate` | empty-room clean plate: masked temporal median + LaMa for the wall + headboard/sheet rebuilt from visible texture |
| track | `prep.py palm_track` | template-matched palm so the logo sits on the hand |
| edit | `common.py` | edit decision list (silences trimmed, pauses kept where an effect needs room) |
| sound | `sound.py` | voice cut + time-stretched + compressed; original 128 BPM track (drops, sidechain pump, underwater filter, trailer percussion), ducked ~9 dB under the voice; SFX on the words |
| picture | `render.py` | every effect, word-locked; `--stills <beat…>` renders check frames |
| compare | `trim_raw.py` | raw take with the same cuts and speed-up, no effects |

## The beats (each triggered by the spoken direction)

1. **"Editing videos manually might be over."** — kinetic type behind him, red strike, *OVER.* slam.
2. **"Zoom in on my hand."** — camera push onto the palm.
3. **"Now put my logo right here… in 3D."** — logo pops onto the tracked palm, extrudes into 3D and spins.
4. **"Make me grab the logo and throw it straight at the camera."** — wind-up, flies at the lens, glass cracks, shake, flash; the glass falls away on "Okay".
5. **"Separate this scene into layers: the background, me, and the text."** — exploded 3D view of three real layers, labelled on each word; collapses with *NO TIMELINE* sitting between room and him.
6. **"Now remove me." / "Bring me back."** — he disintegrates into particles, the empty room keeps talking, he re-forms.
7. **"Put me inside a frame on the right… the anatomy of a viral reel."** — he shrinks into a reel card; hook / retention / share build on the words.
8. **"Back to the full screen."** — card expands back.
9. **"Now put my best videos floating behind me in 3D."** — the repo's own renders orbit him on a tilted 3D ring, behind him on the far side and in front on the near side.
10. **"Turn this entire scene into a cinematic documentary… dramatic lighting, slow camera push-in, movie-style titles."** — paper-cut motion design: a stop-motion paper diorama builds behind his die-cut cutout, turns from dusk to night with paper light rays and lit windows, parallax push-in, torn letterbox, sticker-cut title.
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
python3 trim_raw.py        # -> out/trimmed_raw.mp4
```

Raw footage, model outputs (`*.npy`) and intermediate renders stay out of git.
