# OncoVault teaser (BigOHealth): 40 s

**Watch:** [`out/oncovault_teaser.mp4`](out/oncovault_teaser.mp4)

A 40 second 16:9 "coming soon" teaser (1920×1080, 60 fps, AAC 320k audio) built in the OncoVault web design system:
- **Background:** a deep-green room with warm window bokeh and a vignette.
- **Cards:** frosted-glass cards with a real backdrop blur and hairline borders.
- **Type:** Lora serif headlines with the signature mint second line, the hairline-and-dot divider, and Outfit UI type.
- **Widgets:** the design's own Treatment Timeline, 60-Second Summary and OncoVault Guard.

Every frame is generated in code: an HTML Canvas engine rendered headlessly with Playwright (4-sample motion blur, dithered against banding), plus an original soundtrack synthesised in numpy.

**Music:** cinematic and hopeful, at 96 BPM (16 bars of 2.5 s) in F major (Fmaj9 → C/E → Dm9 → Bbmaj9). It has felt piano, warm pads, a soft heartbeat pulse under the opening, a bell chime for each treatment stage, a gentle groove from "One patient.", a riser and impact on the logo, and a resolving Fmaj9 swell.

| Time | Scene | Copy |
|---|---|---|
| 0–7.5 s | **Open** | "Something big is coming / from **BigOHealth**", divider, "under the mentorship of / Dr. Nitesh Rohatgi" |
| 7.5–20 s | **The journey** | "The entire cancer journey". A timeline draws as six stages arrive in pairs (from **diagnosis** to **surgery**, **radiation** to **chemotherapy**, **molecular** to **targeted therapy**), then the chips morph into one glass Treatment Timeline card: "together in a single longitudinal timeline." |
| 20–27.5 s | **One** | "One patient. / **One treatment timeline.**". The card settles into the hero layout beside the 60-Second Summary and OncoVault Guard widgets |
| 27.5–33 s | **Brand** | The ribbon mark assembles, then the OncoVault wordmark and "by BigOHealth" |
| 33–40 s | **Coming soon** | A COMING SOON pill, "Because every cancer journey deserves / **one complete story.**", and a footer: BigOHealth · Under the mentorship of Dr. Nitesh Rohatgi |

The OncoVault mark is a vector **recreation** of the logo (eight awareness ribbons around a keyhole) made from the website screenshot (`ribbonsMark()` in `teaser.js`). To use the exact artwork, supply the logo SVG and swap it in.

## Build

```bash
./build.sh                               # audio + frames + mux -> out/oncovault_teaser.mp4 (~45 min on 4 cores; resumable)
./build.sh --fps 30 --mb 2               # fast draft
node render.mjs --stills 9,18.2,24,36    # preview PNGs -> out/stills/
```

Requires Node with `playwright` (Chromium) and Python with `numpy`, `scipy` and `imageio-ffmpeg`. Rendering resumes from finished 1 s segments in `out/segs_*`, so delete that folder after you change the visuals.

To edit copy, change the strings in `teaser.js` (`STAGES`, `PAIRS` and the scene functions). If you change a cue time, update the matching constant at the top of `audio.py`. Fonts: Lora and Outfit (OFL, Google Fonts).
