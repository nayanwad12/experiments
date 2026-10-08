# OncoXpress: 10 s type ad (Apple style)

**Watch:** [`out/oncoxpress_type_ad.mp4`](out/oncoxpress_type_ad.mp4)

A 10 second, text-only typographic ad (1920×1080, 60 fps, AAC 320k audio) in an Apple keynote style:
- **Type:** Inter Tight on white, with blur-up word reveals, per-letter mask rises and a rolling word slot.
- **Accent:** a blue-to-teal gradient on the product name.
- **Score:** an original 120 BPM cue in E major, synthesised in numpy (`audio.py`). Every text change lands on a beat.

| Time | Text | Music |
|---|---|---|
| 0–2 s | "The" then "**OncoXpress**" (gradient) | piano note, then chord + shimmer |
| 2–4 s | "Band." then "Ring." roll through a feathered slot | kick + marimba hit on each |
| 4–6 s | "Band and Ring." | groove starts |
| 6–8 s | "Coming soon." (per-letter rise) | riser into an impact |
| 8–10 s | End card: **OncoXpress** / "Band & Ring · Coming soon" | final chord, fade |

## Build

```bash
./build.sh                         # score + frames + mux -> out/oncoxpress_type_ad.mp4 (~15 min on 4 cores)
node render.mjs --stills 1.3,3.5,6.4,9  # preview PNGs -> out/stills/
```

Requires Node with `playwright` (Chromium) and Python with `numpy`, `scipy` and `imageio-ffmpeg`. Font: Inter Tight (OFL).
