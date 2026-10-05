---
name: vibe-vfx
description: Ideabro Studio Vibe Editing System - visual effects on real footage, done in code. Use when the user wants background removal or replacement, the person cut out and placed in front of text (text-behind-subject), splitting a shot into layers (background / person / text) or a 3D-style exploded layer view, removing a person and bringing them back, disintegration into particles, a logo or graphic attached to a hand or object (tracking), 3D-looking objects or floating screens in the scene, cinematic or documentary looks (letterbox, grade, film titles), slow motion and speed ramps, split screens and picture-in-picture, glows and outlines around a person, or "say it and it happens" edits where spoken directions trigger effects on the exact word. Triggers on "remove background", "green screen", "cutout", "text behind me", "track", "VFX", "effects", "slow mo", "cinematic look", "make me disappear".
---

# VFX & Editing Magic
*Ideabro Studio · Vibe Editing System — direct the vibe, let AI do the keyframes.*

Real footage with effects that would take hours of rotoscoping and keyframing. Here they are a few scripts:
**matte** (cut the person out), **track** (follow a point), **composite** (stack layers with motion_kit), and
**word-locking** (start each effect on the exact spoken word).

Paths below are relative to **this skill's folder**: `scripts/`, `reference/`, `templates/`.

## What you can make here

| effect | building blocks |
|---|---|
| background swap / blur / colour | `matte.py --replace-bg "#hex" / image / video / blur` |
| **text behind subject** | background frame → big text → cut-out person on top (`with_alpha`) |
| layer split / exploded 3D layers | bg + person + text as separate layers, then scale/offset each with perspective-ish parallax |
| remove me / bring me back | clean plate (median of frames without the person) + person alpha animated to 0 with particles |
| disintegrate / particles | sample person pixels (alpha > 0.5) into particles that drift off with noise |
| logo on hand / object (tracking) | OpenCV template or optical-flow tracking → per-frame position → draw graphic there |
| floating screens / 3D cards | skia perspective matrices (`skia.Matrix` setPolyToPoly) to map a video/image into 4 corners |
| glow / outline around person | blur the matte, colour it, draw under the person |
| cinematic / documentary look | `grade.py --look cinematic --letterbox 2.39 --grain 6 --vignette` + serif titles |
| slow-mo / speed ramp | `retime.py --speed 0.4 --mode flow`; ramps = several segments at different speeds, concatenated |
| split screen / PiP | motion_kit layout with `VideoFrames` per panel, or ffmpeg `hstack` / `overlay` |
| **say-it-happens edit** | `transcribe.py` → find the trigger words → each effect starts on its word's `s` time |

## Step 0: Setup (first time in a project)

1. `python3 scripts/doctor.py --kit vfx --install` (rembg, OpenCV, Whisper, skia; Windows: `py`)
2. `python3 scripts/new_project.py <name> --kind vfx --format 9:16 --fps 30` and work in that folder; footage in `raw/`.

## Step 1: Brief and shot check

Ask: which effects, on which moments? *(if the user spoke the directions on camera, transcribe and read them)* ·
format/length · vibe. Then inspect the footage: `python3 vibe/stills.py raw/take.mp4 --count 9`.
**Feasibility check:** a locked-off camera, the subject well separated from the background, good light and no motion blur
all make effects easy. A handheld camera needs tracking/stabilising (OpenCV), and fast motion needs a better matte model. Tell the user
honestly what will look great and what will look rough.

## Step 2: Prepare layers

```bash
python3 vibe/cut_silence.py raw/take.mp4 --words work/words.json -o work/cut.mp4   # if it's a talking take
python3 vibe/matte.py work/cut.mp4 --model u2net_human_seg            # -> work/matte/cut_alpha.mp4
#   best hair/edges: --model birefnet-portrait (slow); objects: --model isnet-general-use; draft: --scale 0.5
python3 vibe/transcribe.py work/cut.mp4 -o work/words_fx.json           # word times for triggers
```
**Clean plate** (empty background, for "remove me"): median of frames where the person has moved away, masked by the
matte. In numpy: stack N frames, set person pixels to NaN, `np.nanmedian`; fill the leftover holes with `cv2.inpaint`.

**Tracking** (logo on palm, label on object):
```python
import cv2
cap = cv2.VideoCapture("work/cut.mp4"); ok, f0 = cap.read()
x, y, w, h = 600, 900, 120, 120                       # box around the target in frame 0 (find it on a still)
tpl = cv2.cvtColor(f0[y:y+h, x:x+w], cv2.COLOR_BGR2GRAY); track = []
while ok:
    g = cv2.cvtColor(f0, cv2.COLOR_BGR2GRAY)
    r = cv2.matchTemplate(g, tpl, cv2.TM_CCOEFF_NORMED); _, score, _, (bx, by) = cv2.minMaxLoc(r)
    track.append((bx + w/2, by + h/2, score)); ok, f0 = cap.read()
# smooth the track (moving average), save work/track.json, and hide the graphic when score < 0.5
```

## Step 3: Composite with motion_kit (short shots) or overlays (long shots)

```python
import sys, json; sys.path.insert(0, "vibe")
from motion_kit import *
SRC = VideoFrames("work/cut.mp4", fps=30); MAT = VideoFrames("work/matte/cut_alpha.mp4", fps=30)
S = Stage(SRC.w, SRC.h, fps=30, duration=len(SRC) / 30); B = S.brand; U = min(S.w, S.h) / 1080
W_ = {w["w"].lower().strip(".,!?"): w["s"] for w in json.load(open("work/words_fx.json"))}

def draw(c, t):
    c.drawImage(SRC.at(t), 0, 0)                                   # 1 background (full frame)
    k = ease_out_expo(prog(t, W_.get("vibe", 1.0), 0.5))            # 2 text appears on the word "vibe"
    text(c, "VIBE", S.w/2, S.h*0.45, size=420*U*k, font="display", fill=rgb(B, "accent"))
    c.drawImage(with_alpha(SRC.array(t), MAT.array(t)), 0, 0)       # 3 person back on top = text BEHIND them
```
- `VideoFrames` holds clips in RAM: fine for shots up to ~10–15 s at 1080p. Longer: process per shot and
  concatenate, or render graphics as a transparent overlay (`S.render(..., alpha=True)` + `vibe/overlay.py`).
- Perspective (floating screens, 3D cards): `m = skia.Matrix(); m.setPolyToPoly(src4, dst4)`, then
  `c.save(); c.concat(m); c.drawImage(img, 0, 0); c.restore()`, and animate `dst4` corners.
- Particles: precompute particle start positions from the matte once (`np.argwhere(alpha > 128)[::step]`), then animate
  each as a pure function of `t` (seeded noise drift + fade). Never keep simulation state between frames.
- Effects begin **on the word** (`W_["remove"]`) and end before the next one starts.

## Step 4: Look, sound, deliver

- Grade at the end, the same for every shot: `python3 vibe/grade.py out/x.mp4 --look cinematic --strength 0.7`.
- Sound sells VFX: whoosh into transforms, impact + shake on hits, glass/glitch/sparkle for magic, a drone under
  "cinematic" moments (`audio_kit.py`). Keep the original voice, cleaned (`audio_kit.py voice`).
- `python3 vibe/stills.py out/<name>.mp4 --at <each effect time>` → READ every effect frame → export.

## Quality bar

- [ ] Matte edges clean on the stills (hair, hands, fast motion); no flicker in the alpha (raise `--smooth`)
- [ ] Tracked graphics stick (no sliding); hidden when the track is lost
- [ ] Every effect starts on its trigger word and leaves before the next one
- [ ] Light/colour of added elements matches the shot (grade them together; add shadows/glow)
- [ ] Voice intact and in sync; −14 LUFS
- [ ] Honest: if an effect looks rough, say so and offer an alternative (graphic cut-away, freeze frame, stylised look)

## Reference
`reference/foundations.md` · `reference/motion-principles.md` · `reference/sound-design.md` · `reference/brand-kit.md` ·
`reference/export-specs.md` · `reference/troubleshooting.md`
