# OncoVault by BigOHealth: 40 s Apple-style promo

**Watch:** [`out/oncovault_promo.mp4`](out/oncovault_promo.mp4)

A 40 second 16:9 promo (1920×1080, 60 fps, AAC 320k audio) in an Apple keynote style. It uses the same engine as the original Vibe Editing launch film: a white canvas, Inter Tight display type, blur-up word reveals, spring physics and soft-shadow cards, with the "intelligence" glow re-tinted in OncoVault greens. Every frame is generated in code: an HTML Canvas engine rendered headlessly with Playwright (4-sample motion blur, dithered against banding), plus an original soundtrack synthesised in numpy.

**Music:** uplifting, at 120 BPM (20 bars of 2 s) in D major (Dmaj9 → Bm9 → Gmaj9 → A6/9):
- **Opening:** felt piano on the opening lines.
- **Timeline:** a marimba note as each stage tile lands, over a half-time pulse.
- **"One patient":** a riser and lift into the full groove.
- **Logo:** an impact and shimmer as it assembles, then a resolving Dmaj9 under the closing line.

| Time | Scene | Copy |
|---|---|---|
| 0–6 s | **Open** | "Something big is coming. / from **BigOHealth**." then "Under the mentorship of / Dr. Nitesh Rohatgi" |
| 6–10 s | **Journey** | "The entire / cancer journey." (per-letter mask rise, slow push-in) |
| 10–20 s | **Timeline** | Three big-type beats: *From diagnosis to surgery, / radiation to chemotherapy, / molecular to targeted therapy.* Six green app-icon tiles drop onto one track as the progress line fills, then "Together in a single / **longitudinal timeline.**" with a luminous pass along the track |
| 20–28 s | **One** | "One patient. / **One treatment timeline.**" beside a phone running the OncoVault timeline app (rows spring in, a 60-second summary button, and a green intelligence-glow pass) |
| 28–33 s | **Brand** | The ribbon mark assembles inside a green glow ring, then the **Onco**Vault wordmark and "by BigOHealth" |
| 33–40 s | **Coming soon** | A Coming soon pill, "Because every cancer journey deserves / **one complete story.**", and a footer: BigOHealth · Under the mentorship of Dr. Nitesh Rohatgi |

The OncoVault mark is a vector **recreation** of the logo made from the website screenshot (`ribbonsMark()` in `film.js`). The dates and treatment details in the phone UI are illustrative.

## Build

```bash
./build.sh                               # audio + frames + mux -> out/oncovault_promo.mp4 (~45 min on 4 cores; resumable)
./build.sh --fps 30 --mb 2               # fast draft
node render.mjs --stills 11,17.4,23,36   # preview PNGs -> out/stills/
```

Requires Node with `playwright` (Chromium) and Python with `numpy`, `scipy` and `imageio-ffmpeg`. Delete `out/segs_*` after you change the visuals, because rendering resumes from finished segments. If you change a cue time in `film.js`, update the matching constant at the top of `audio.py`. Font: Inter Tight (OFL).
