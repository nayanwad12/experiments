# VIBE EDITING by Ideabro Studio: 40 s launch film

**Watch:** [`out/vibe_editing_launch.mp4`](out/vibe_editing_launch.mp4)

A 40 second 16:9 launch/promo film (1920×1080, 60 fps, AAC 320k audio) in a premium Apple keynote style: a white canvas, SF-style display type (Inter Tight), `#F5F5F7` bento cards, soft shadows, spring physics, blur-up word reveals and the rainbow "Apple Intelligence" edge glow. Every frame is generated in code: an HTML Canvas engine rendered headlessly with Playwright (4-sample motion blur, dithered against banding), plus an original soundtrack synthesised in numpy.

**Music:** 120 BPM, so 40 s = 80 beats = 20 bars. It's in D major (Dmaj9 → Bm9 → Gmaj9 → A6/9) and fully synthesised: airy pads, marimba plucks and arps, sub bass, a four-on-the-floor groove from the "AI edit" drop, risers, impacts and shimmers. UI SFX include a key click for each typed character, send pops, card pops and caption ticks. Every big moment lands on a bar line.

| Time | Scene | What happens |
|---|---|---|
| 0–5 s | **Cold open** | "Editing used to mean" … *keyframes. layers. render bars. endless hours.* rolls through a feathered slot, and the last one gets struck through |
| 5–10 s | **The prompt** | "Now, you just say it." A glass prompt bar types *Make it cinematic. Warm, punchy, with captions.*, then send triggers the rainbow glow, which blooms out to the screen edges |
| 10–14 s | **Reveal** | "Introducing" / **Vibe Editing** (per-letter mask rise, live gradient) / "A course by Ideabro Studio." |
| 14–23 s | **Device demo** | A laptop rises with an editor UI. "Just describe the vibe." types *warm cinematic grade, cut to the beat*, and on the drop the AI re-grades the shot (teal/orange, letterbox), re-cuts the timeline to the beat, moves the inspector sliders and adds captions. Then "AI handles the edit." |
| 23–32 s | **Bento** | "What you'll master / Pro edits. Zero grind." Six live cards: AI Captions, Motion Graphics, Color Grading, Smart Cuts, Sound Design and Prompt Workflows |
| 32–36 s | **Statement** | "Less timeline." / "More vibe." |
| 36–40 s | **End card** | Gradient squircle app icon with a shine sweep, **Vibe Editing**, by Ideabro Studio, then **Enroll now** and Learn more › |

## Build

```bash
./build.sh                               # audio + frames + mux -> out/vibe_editing_launch.mp4 (~20 min on 4 cores; resumable)
./build.sh --fps 30 --mb 2               # fast draft
node render.mjs --stills 11,19.5,26,38   # preview PNGs -> out/stills/
```

Requires Node with `playwright` (Chromium) and Python with `numpy`, `scipy` and `imageio-ffmpeg`.

**Live preview:** serve the folder (`npx http-server apple-launch`) and open `index.html`. Space plays or pauses with the audio, and ←/→ scrub by 2 s.

To edit copy, change the strings in `launch.js` (`SLOT`, `PROMPT1`, `PROMPT2`, `CARDS`, and the scene functions). If you change a cue time, update the matching constant at the top of `audio.py`. Fonts: Inter Tight and Instrument Serif (OFL, Google Fonts).
