# VIBE EDITING by Ideabro Studio: 40 s launch film

**Watch:** [`out/vibe_editing_launch.mp4`](out/vibe_editing_launch.mp4)

A 40 second 16:9 launch/promo film (1920×1080, 60 fps, AAC 320k audio). It uses an Apple keynote-style layout (clean Inter Tight display type, blur-up word reveals, spring physics, bento cards, a laptop demo) in a strict **black / white / neon green (`#39FF14`)** palette, and features the **Ideabro "IB" monogram** (`logo.svg`, traced to vector from the supplied artwork). Every frame is generated in code: an HTML Canvas engine rendered headlessly with Playwright (4-sample motion blur that never crosses a hard cut, dithered against banding), plus an original soundtrack synthesised in numpy.

**Music:** fast-paced, at 150 BPM, so 40 s = 100 beats = 25 bars. It's in E minor (Em9 → Cmaj7 → G6 → Dadd9) and has a four-on-the-floor kick from the first bar, 16th hats, rolling 16th bass, syncopated saw stabs, 16th marimba arps, snare rolls into every drop, risers and impacts. UI SFX include a key click for each typed character, send and card pops, caption ticks and whooshes on each montage cut.

**Time model:** scenes are authored in "virtual" seconds on a 120 BPM grid and played at 1.25×, which lands them on the 150 BPM grid. A 4-bar montage runs in real time between 28.8 s and 35.2 s, and the end card plays at normal speed (see `warp()` in `launch.js`).

| Time | Scene | What happens |
|---|---|---|
| 0–4 s | **Cold open** | "Editing used to mean" … *keyframes. layers. render bars. endless hours.* rolls through a feathered slot, and a neon strike crosses out the last one |
| 4–8 s | **The prompt** | "Now, you just **say it.**" A prompt bar types *Make it punchy. Fast cuts, bold captions, neon accents.*, then send triggers a neon glow that blooms to the screen edges |
| 8–11 s | **Reveal** | "Introducing" / **Vibe Editing** (per-letter rise, neon block behind *Editing*) / "A course by [IB] Ideabro Studio." |
| 11–19 s | **Device demo** | A laptop rises with a mono editor UI and types *high-contrast mono grade, cut to the beat*. On the drop the AI grades the shot (deep blacks, neon sun halo, letterbox), re-cuts the timeline to the beat with neon accent clips and adds neon captions. "**AI** handles the edit." |
| 19–25.6 s | **Bento** | "Pro edits. **Zero grind.**" Six live cards: AI Captions, Motion Graphics, Color Grading (curves), Smart Cuts, Sound Design and Prompt Workflows |
| 25.6–28.8 s | **Statement** | "Less timeline." Then black floods up the screen and "More vibe." glows neon |
| 28.8–35.2 s | **Montage** | One word per beat, flipping between white, black and neon: Captions. Cuts. Color. Motion. Sound. Titles. Transitions. Prompts. Then "Edit at the speed of" builds and **vibe.** slams in neon |
| 35.2–40 s | **End card** | On black: the IB logo springs in with a neon glow and light sweep, then **Vibe Editing** and by Ideabro Studio, a neon **Enroll now** button and Learn more › |

## Build

```bash
./build.sh                               # audio + frames + mux -> out/vibe_editing_launch.mp4 (~50 min on 4 cores; resumable)
./build.sh --fps 30 --mb 2               # fast draft
node render.mjs --stills 9,15.5,29.2,37  # preview PNGs (real seconds) -> out/stills/
```

Requires Node with `playwright` (Chromium) and Python with `numpy`, `scipy` and `imageio-ffmpeg`. Rendering resumes from finished 1 s segments in `out/segs_*`, so delete that folder after you change the visuals.

**Live preview:** serve the folder (`npx http-server apple-launch`) and open `index.html`. Space plays or pauses with the audio, and ←/→ scrub by one bar.

To edit copy, change the strings in `launch.js` (`SLOT`, `PROMPT1`, `PROMPT2`, `CARDS`, `MON`, and the scene functions). If you change a cue time, update the matching real-time constant at the top of `audio.py`. Font: Inter Tight (OFL, Google Fonts).
