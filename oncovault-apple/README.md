# OncoVault by BigOHealth: Apple-style promo (30 s)

**Watch:** [`out/oncovault_promo.mp4`](out/oncovault_promo.mp4)

A 30 second 16:9 promo (1920×1080, 60 fps) in an Apple keynote style:
- **Look:** a white canvas, Inter Tight display type, blur-up word reveals, spring physics and soft-shadow app tiles.
- **Glow:** the "intelligence" glow, tinted in OncoVault greens.
- **Logo:** none; the brand appears as a typeset wordmark only.
- **Rendering:** every frame is generated in code by an HTML Canvas engine, rendered headlessly with Playwright (4-sample motion blur, dithered against banding).

**Soundtrack:** the supplied track `audio_src/linkedin_audio.mp3` (~97 BPM, 23.3 s), extended to exactly 30.0 s by `make_audio.py`. The groove from 7.85 s is a 2-bar harmonic loop (one phrase = 4.92 s, with identical chroma), so one extra copy of that phrase is spliced in after itself (15 ms crossfade). The result is then slowed ~6% with pitch-preserving `atempo`. The cut follows the extended track:

| Time | Track | Scene |
|---|---|---|
| 0–5.4 s | fade-in, first hit at **1.06 s** | "Something big is coming." then "from **BigOHealth**." lands on the hit. Then "Under the mentorship of / Dr. Nitesh Rohatgi & Dr. Swarupa Mitra" |
| 5–8.4 s | calm section | "The entire / cancer journey." (per-letter mask rise, push-in) |
| 8.34–18.8 s | groove (two phrases) | *From diagnosis to surgery,* (8.34) / *radiation to chemotherapy,* (11.55) / *molecular to targeted therapy.* (15.17). Six green app-icon tiles drop onto one timeline |
| 18.8–23.9 s | next phrase | "Together in a single / **longitudinal timeline.**" with a luminous pass along the track and a slow push-in |
| 24.2–26.5 s | the track's peak | The **Onco**Vault wordmark rises inside a green glow capsule, then "by BigOHealth" |
| 26.5–30 s | outro | A Coming soon pill, "Because every cancer journey deserves / **one complete story.**", fade to white |

## Build

```bash
./build.sh                                # 30 s audio + frames + mux -> out/oncovault_promo.mp4 (~45 min on 4 cores; resumable)
./build.sh --fps 30 --mb 2                # fast draft
node render.mjs --stills 1.6,12,20,28     # preview PNGs -> out/stills/
```

Requires Node with `playwright` (Chromium) and Python with `numpy`, `scipy` and `imageio-ffmpeg`. Delete `out/segs_*` after you change the visuals, because rendering resumes from finished segments. To swap the track, replace `audio_src/linkedin_audio.mp3`, update the phrase measurements in `make_audio.py`, and move the cue times in `film.js` (scene table at the top of the scene section, `PAIRS`, `TILE_T`, `TOGETHER`, and the `sBrand` times). Font: Inter Tight (OFL).
