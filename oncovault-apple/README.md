# OncoVault by BigOHealth: Apple-style promo (23.3 s)

**Watch:** [`out/oncovault_promo.mp4`](out/oncovault_promo.mp4)

A 23.3 second 16:9 promo (1920×1080, 60 fps) in an Apple keynote style:
- **Look:** a white canvas, Inter Tight display type, blur-up word reveals, spring physics and soft-shadow app tiles.
- **Glow:** the "intelligence" glow, tinted in OncoVault greens.
- **Logo:** none; the brand appears as a typeset wordmark only.
- **Rendering:** every frame is generated in code by an HTML Canvas engine, rendered headlessly with Playwright (4-sample motion blur, dithered against banding).

**Soundtrack:** the supplied track `audio_src/linkedin_audio.mp3` (~97 BPM, 23.3 s). The cut follows the track's structure:

| Time | Track | Scene |
|---|---|---|
| 0–4.7 s | fade-in, first hit at **1.0 s** | "Something big is coming." then "from **BigOHealth**." lands on the hit. Then "Under the mentorship of / Dr. Nitesh Rohatgi & Dr. Swarupa Mitra" |
| 4.3–7.85 s | calm section | "The entire / cancer journey." (per-letter mask rise, push-in) |
| 7.85–12.77 s | groove enters | *From diagnosis to surgery,* (7.85) / *radiation to chemotherapy,* (9.36) / *molecular to targeted therapy.* (10.87). Six green app-icon tiles drop onto one timeline on the beats in between |
| 12.77–17.6 s | second phrase | "Together in a single / **longitudinal timeline.**" with a luminous pass along the track and a slow push-in |
| 17.9–20 s | the track's peak | The **Onco**Vault wordmark rises inside a green glow capsule, then "by BigOHealth" |
| 20–23.3 s | outro | A Coming soon pill, "Because every cancer journey deserves / **one complete story.**", fade to white |

## Build

```bash
./build.sh                                # frames + mux with the supplied audio -> out/oncovault_promo.mp4 (~30 min on 4 cores; resumable)
./build.sh --fps 30 --mb 2                # fast draft
node render.mjs --stills 1.4,9.9,18.4,22  # preview PNGs -> out/stills/
```

Requires Node with `playwright` (Chromium) and Python with `imageio-ffmpeg`. Delete `out/segs_*` after you change the visuals, because rendering resumes from finished segments. To swap the track, replace `audio_src/linkedin_audio.mp3` and move the cue times in `film.js` (scene table at the top of the scene section, `PAIRS`, `TILE_T`, `TOGETHER`, and the `sBrand` times). Font: Inter Tight (OFL).
