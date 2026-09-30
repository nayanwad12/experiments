# OncoXpress, powered by BigOHealth — brand film

80 s, 1920×1080 (16:9), 24 fps, stereo. Built from 8 AI-generated clips (Gemini/Veo) and the supplied narration,
edited so it doesn't read as AI.

**Deliverable:** `out/oncoxpress_brand_film.mp4` (8 Mbps). `encode.sh` also makes a 24 Mbps full-grain version,
`out/oncoxpress_brand_film_HQ.mp4` (240 MB), which isn't committed.

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

One system from start to finish: warm **paper** (#EFEBE3) and **evergreen** (#1F6B50), both taken from the app's own UI.
Typefaces are **Lexend**, close to the app's UI font, and **Instrument Serif** for the titles. The OncoXpress logo
was pulled from the clip-8 end frame and cleaned into a sharp high-res matte (mark, wordmark and tagline separated
so they animate individually).

The app screens (upload, timeline, health overview, case summary, report detail) are rebuilt from the supplied
screenshots with a **made-up patient, "Anita Verma"**, and invented values throughout. No real patient data, names or
file names from the screenshots appear in the film.

## Edit (film time; narration starts at 1.0 s)

| time | picture |
| --- | --- |
| 0–9.3 | clip 1: ward, waiting room, the folder |
| 9.3–21.3 | the scattered records: overhead desk, phone, portal, email, PDF, paper (clips 3, 2) |
| 21.3–26.2 | split screen, "different records, different places": the four sources try to connect, and the links break |
| 26.2–28.8 | brand reveal |
| 28.8–32.6 | the doctors, super: *Under the leadership of Dr Aditya Sarin & Dr Shyam Agrawal* |
| 32.6–35.2 | still desk of scattered records, push in to the phone, *powered by BigOHealth* |
| 35.2–39.1 | "one secure place": the report cards fly into the phone's health vault, and the lock closes on "secure" |
| 39.1–63.7 | product (screens change with iOS-style pushes): upload as-is, "no renaming / sorting / folders", identifies → categorizes → organizes, timeline, tracked data (the list is scrolled word by word), a complete picture → all in one place |
| 63.7–72.4 | consultation, search in 0.4 s, doctor reading history, "under 60 seconds" |
| 72.4–80 | end card: OncoXpress, powered by BigOHealth, *Faster Care. Trusted Care.* |

## Sound

`sound.py` writes an original score: felt piano, a string pad and a soft pulse in D major / B minor. It stays unresolved
while the records are scattered, resolves on the brand, adds a heartbeat pulse under the product section and lands
on D major on the end card. Sound design covers room tone, paper, taps, typing, UI ticks, whooshes, a riser and an
impact, and a fast-running clock for "under 60 seconds". Music is side-chain ducked under the narration
(about 11 dB of separation under speech).

## Rebuild

```bash
pip install imageio-ffmpeg opencv-python-headless numpy scipy pillow pocketsphinx
# put clips as raw/clip1B.mp4 … raw/clip8B.mp4 and raw/narration.mp3
python3 work/align.py            # word timings (pocketsphinx forced alignment of the script)
node render_mg.mjs               # motion graphics -> work/mg/
python3 sound.py                 # -> work/mix.wav
python3 build.py                 # picture -> work/frames/  (--stills 12.5,40 for check frames)
./encode.sh                      # -> out/
```
