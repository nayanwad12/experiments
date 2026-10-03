# OncoXpress, powered by BigOHealth — brand film

96.6 s, 1920×1080 (16:9), 24 fps, stereo, with white subtitles. Built from 11 AI-generated clips (Gemini/Veo), the supplied
narration, two later voice takes and the leadership photos, edited so it doesn't read as AI.

**Deliverable:** `out/oncoxpress_brand_film.mp4` (v4, 8 Mbps).

## v4: re-edit of the finished film

v4 was cut from the finished v3 film (`assemble_v4.py`), not re-rendered from the source clips:

- **Narration recovered from the v3 mix.** The score and SFX are deterministic synthesis (`sound.py`), so
  `work/extract_voice.py` regenerates them sample-exactly, undoes the soft limiter and fades, and solves for the voice under
  the side-chain duck. What's left of the music sits at about −70 dB, so it's inaudible.
- **"Dr Aditya Sarin"** is replaced with the corrected take (`raw/vo_aditya.mp3`), processed through the same voice chain
  and level-matched to within 0.5 dB.
- **Doctors** (29–35 s): the two-doctor shot runs about 1.1 s, cropped above the old lower-third. Then come photo cards,
  first **Dr Shyam Aggarwal** (Chairman, Medical Oncology, Sir Ganga Ram Hospital, New Delhi), then **Dr Aditya Sarin**
  (Vice President, Medical Oncology, Sir Ganga Ram Hospital, New Delhi). Portraits are cut out with U²-Net human
  segmentation (`assets/doctors/`). The narration is re-ordered to match the cards: "…of Dr Shyam Agrawal and
  Dr Aditya Sarin", cut at natural breaths, with a 1.3 s pause after the names so the cards can be read.
- **New paragraph** (74.3–89.0 s): "And this is just the beginning. Coming soon…", using the new voice take
  (`raw/vo_comingsoon.mp3`) and clip 11. The pictures are the corridor walk, then a phone with coming-soon modules, then
  the meal (diet & nutrition), the family (emotional well-being) and the scanner (diagnostics), each with a coming-soon tag,
  then "All within the same platform".
- **Subtitles**: white Lexend on a translucent plum pill, timed per phrase from forced alignment. They stay muted where the
  same words are already typeset on screen.
- **Music and SFX** are regenerated on the new timeline (`sound_v4.py`, every v3 cue moved through `v4.warp()`), with new
  cues for the cards and the coming-soon section.

## What was done to the footage

| problem in the source clips | fix |
| --- | --- |
| Gemini sparkle watermark (clips 1–2, bottom right) | alpha matte estimated from every frame, then **reverse alpha-blended** (`work/wm.py`), not blurred or cropped |
| AI morph-dissolves inside clips (3, 4, 5, 7, 8) | cut around them. Only clean runs of each shot are used |
| monitor that rotates by itself (clip 8), phone that grows out of a folder (clip 1) | cut |
| garbled AI text on screen close-ups (clip 6 entirely, clip 7 dashboard, the AI "OncoXpress" logo in clip 8) | not used. The product is shown as rebuilt app UI instead |
| screens still in shot (portal, email, PDF, desktop, monitors) | shallow-focus defocus on screen areas only (auto-detected), like a real lens focused on the person |
| clip 5 laptop scene (screen content morphs, desktop flickers) | dropped. The section is rebuilt as a still desk push-in plus a motion-graphic "secure vault" beat |
| 8 × 10 s clips vs a 76 s narration | shots retimed with optical-flow interpolation (DIS flow) to land on the words |

## Look

Clean, warm and soft, for a premium healthcare feel rather than a gritty film one (`look.py`). The white balance is
gently warm, the blacks are true, and the shadows carry a hint of evergreen. Contrast is soft and filmic with a creamy
highlight roll-off, skin stays natural, and blues are eased toward the brand's teal-green. The finish is a soft bloom
and a light vignette. There's no grain: only an invisible sub-code-value dither so the paper gradients don't band. The
motion graphics get the same grade at a lower strength, so footage and UI sit together.

## Theme

One system from start to finish, taken from the OncoXpress website: **purple** (#4A2B8E, with #6B46C1 for lighter
accents) for the app UI and primaries, **teal** (#1E7A80) for highlights, and a **lavender-white** (#F4F2F8) canvas.
Typefaces are **Lexend** for the UI and **Instrument Serif** for the titles. The OncoXpress logo was pulled from the
clip-8 end frame and cleaned into a sharp high-res matte (mark, wordmark and tagline separated so they animate
individually).

The app screens (upload, timeline, health overview, case summary, report detail) are rebuilt from the supplied
screenshots with a **made-up patient, "Anita Verma"**, and invented values throughout. No real patient data, names or
file names from the screenshots appear in the film.

## Edit (v3 film time; see v4.py for how it maps to v4)

| time | picture |
| --- | --- |
| 0–9.3 | clip 1: ward, waiting room, the folder |
| 9.3–12.5 | messy reports: the ward desk buried in paper, hands shuffling the pile (clip 9) |
| 12.5–21.3 | the scattered records: phone, MRI scans on the hospital portal (clip 10), email, PDF, paper (clips 2, 3) |
| 21.3–26.2 | split screen, "different records, different places": the four sources try to connect, and the links break |
| 26.2–28.8 | brand reveal, *powered by BigOHealth* |
| 28.8–32.6 | the doctors, super: *Under the leadership of Dr Aditya Sarin & Dr Shyam Agrawal* |
| 32.6–35.2 | still desk of scattered records, push in to the phone, *powered by BigOHealth* |
| 35.2–39.1 | "one secure place": the report cards fly into the phone's health vault, and the lock closes on "secure" |
| 39.1–63.7 | product (screens change with iOS-style pushes): upload as-is, "no renaming / sorting / folders", identifies → categorizes → organizes, timeline, tracked data (the list is scrolled word by word), a complete picture → all in one place |
| 63.7–72.4 | consultation, her still searching through paper (clip 9), doctor reading history, "under 60 seconds" |
| 72.4–80 | end card: OncoXpress, powered by BigOHealth, *Faster Care. Trusted Care.* |

## Sound

`sound.py` writes an original score: felt piano, a string pad and a soft pulse in D major / B minor. It stays unresolved
while the records are scattered, resolves on the brand, adds a heartbeat pulse under the product section and lands
on D major on the end card. Sound design covers room tone, paper, taps, typing, UI ticks, whooshes, a riser and an
impact, and a fast-running clock for "under 60 seconds". Music is side-chain ducked under the narration
(about 11 dB of separation under speech).

## Rebuild

```bash
pip install imageio-ffmpeg opencv-python-headless numpy scipy pillow pocketsphinx onnxruntime
# v3 (needs the source clips): raw/clip1B.mp4 … raw/clip10B.mp4 and raw/narration.mp3
python3 work/align.py && node render_mg.mjs && python3 sound.py && python3 build.py && ./encode.sh
# v4 (re-edit of the v3 film in out/): raw/vo_aditya.mp3, raw/vo_comingsoon.mp3, raw/clip11B.mp4
python3 work/extract_voice.py      # v3 mix -> clean narration stem
python3 sound_v4.py                # -> work/mix_v4.wav
node render_mg.mjs --v4            # doctor cards + coming-soon graphics -> work/mg4/
python3 assemble_v4.py             # -> work/frames4/   (--stills 31,80 for check frames, --cues for subtitles)
```
