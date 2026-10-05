# Foundations: how Vibe Editing works

*Ideabro Studio · Vibe Editing System*

Vibe Editing means **the student directs and Claude edits in code**. There is no timeline app. Every cut, caption, animation
and sound is a line in a script, so any change ("make the title land on the beat", "warmer", "30 % faster")
is a quick edit and a re-render, never a manual re-do.

## The Vibe Loop (follow it every time)

```
BRIEF  ->  BEAT TABLE  ->  BUILD  ->  STILLS  ->  DRAFT  ->  FINAL  ->  EXPORT
  ^                                      |          |
  +-------------- feedback --------------+----------+
```

1. **Brief.** Fill `brief.md` with the user (ask; don't guess). Ask at most 5–7 questions in one message,
   offering smart defaults, so the user can just reply "defaults are fine".
2. **Beat table.** Write a `time | picture | sound | on-screen text` table and get a yes before building.
3. **Build.** Put every timing in `timeline.py` (or the EDL). Keep code deterministic: seed all randomness.
4. **Stills.** Render 4–12 check frames and **look at them** with the Read tool. Fix layout, overflow,
   contrast and safe-zone issues now. They cost seconds to fix here and minutes after a full render.
5. **Draft.** Half resolution, half fps (`draft=True`) for timing and pacing feedback.
6. **Final.** Full quality. Re-check a contact sheet of the final file (`stills.py --count 12`).
7. **Export.** `export.py --preset …` for each platform (correct size, codec, −14 LUFS loudness).

Log every revision round in `work/revisions.md`. Version deliverables `name_v1.mp4`, `name_v2.mp4`, and never overwrite
a version the client has seen.

## Project layout (created by `new_project.py`)

| path | rule |
|---|---|
| `raw/` | the user's originals. **Read-only.** Never edit, re-encode or rename in place. |
| `assets/` | prepared inputs: cleaned logos, cutouts, licensed music |
| `fonts/` | brand fonts (`python3 vibe/fonts.py --brand`) |
| `work/` | everything intermediate: transcripts, EDLs, mattes, mixes, drafts |
| `out/` | deliverables + `out/stills/` review sheets |
| `brief.md` / `brand.json` / `timeline.py` | the creative source of truth |
| `vibe/` | the toolkit, run as `python3 vibe/<tool>.py` |

## The toolkit

| tool | use it for |
|---|---|
| `doctor.py --kit <type> --install` | first run: checks Python, ffmpeg and packages, installs what's missing |
| `new_project.py <name> --kind … --format 9:16` | scaffold a project (run from the skill's `scripts/` folder) |
| `fonts.py "Family:700"` / `--brand` | any Google Font as static TTF |
| `transcribe.py` | Whisper words with timestamps → `words.json` |
| `cut_silence.py` | remove pauses, ums, retakes; punch-in jump cuts; `words_cut.json` |
| `captions.py` | pop / karaoke / clean / minimal captions (.ass + .srt), burn-in |
| `tts.py` | local AI voiceover (Kokoro), per-line timings |
| `audio_kit.py` | `bed` original music, `sfx`, `voice` clean-up, `mix` with ducking + loudness |
| `motion_kit.py` | the frame engine: easing, text, shapes, images, video frames, parallel render |
| `matte.py` | person/subject cut-out → alpha video, background swap |
| `grade.py` | colour looks, LUTs, grain, vignette, letterbox, before/after |
| `retime.py` | slow-mo (optical flow), speed-up, fit-to-duration |
| `clipscan.py` | QC sheets + morph/cut detection for AI or stock clips |
| `batch.py` | one render per CSV row (personalised / series / variants) |
| `stills.py` | contact sheet of any video, used for review |
| `export.py` | platform deliverables, reframing (crop/pad/blur), loudness |

## Frames are functions of time

All generated graphics follow one pattern (see `scene.py`):

```python
def draw(c, t):                     # c = skia canvas, t = seconds
    background(c, t)
    name, local_t, dur = TL.scene_at(t)
    SCENES[name](c, t, local_t, dur)
```

Because a frame depends only on `t`, Claude can render any moment instantly (stills), render frames
in parallel on every CPU core, and change a timing without breaking anything else.
Animate with `prog(t, start, dur)` + an easing (`ease_out_back`, `ease_out_expo`…), never with
per-frame counters or accumulated state.

## Mixing real footage with graphics

- Load footage frames with `VideoFrames("work/cut.mp4", fps=30)` and draw them with `c.drawImage(v.at(t), 0, 0)`.
- For long clips (more than about 20 s at 1080p), don't hold every frame in RAM. Render graphics over footage in segments, or
  burn simple overlays with ffmpeg (`captions.py --burn`, `grade.py`) and use motion_kit only for the
  graphic-heavy moments.
- Person-in-front-of-text needs a matte: `matte.py` → `with_alpha(frame, matte)`.

## Performance

| need | do |
|---|---|
| quick look | `stills` (seconds) |
| timing check | `draft` = half res + half fps (≈ 8× faster) |
| one section | `S.render(draw, "work/part.mp4", start=4, end=8)` |
| slow frames | cache images/text layouts at module level; avoid per-frame file loads; blur once |
| huge batch | `batch.py --workers 1` (each render already uses every core) |

## Quality gate: check before saying "done"

- [ ] Looked at a contact sheet of the **final file** (not just the code)
- [ ] No text outside safe zones, no overflow, no typos, names spelled right
- [ ] Brand colours and fonts only, and consistent
- [ ] Every cut on a beat or a word, nothing cut mid-word
- [ ] Voice clear above music; no clipping; loudness −14 LUFS (export did it)
- [ ] Length and format match the brief; exported for each platform asked for
- [ ] Rights: music original (audio_kit) or licensed; fonts OFL; footage owned or licensed

## Talking to the user

- Speak in edits and outcomes, not code: "Title now slams in on beat 1 with a lime underline," not "changed ease to back."
- After each render, send **one contact sheet + 1–3 specific questions** ("Hook feel strong enough? Captions too big?").
- Offer two or three concrete options when the user is unsure ("punchier: faster cuts / bigger captions / bass hits").
- Never claim something works without having rendered and looked at it.
