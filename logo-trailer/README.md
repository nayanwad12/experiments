# VIBE EDITING: 20 s logo-animation trailer

**Watch:** [`out/vibe_editing_logo_trailer.mp4`](out/vibe_editing_logo_trailer.mp4)

A 20-second, 16:9 hype trailer (1920×1080, 60 fps, real motion blur) that animates the **VIBE EDITING** wordmark in 13 different design styles. It cuts on the beat of an original 144 BPM soundtrack. Every frame is generated in code: an HTML Canvas + WebGL2 engine rendered headlessly with Playwright. Every sound is synthesised in numpy, with no samples.

144 BPM means 20 s = 48 beats = 12 bars. Every cut lands on the grid.

| Beats | Time | Section | What happens |
|---|---|---|---|
| 0–8 | 0–3.3 s | **Cold open** | Heartbeat and an anamorphic light line, then "VIBE EDITING PRESENTS". Three trailer hits with braams: **ONE NAME. / 13 STYLES. / ZERO LIMITS.** Next is a subliminal strobe of all 13 styles (one still per 1/8 beat), a white flash, and a half-beat of silence while the light converges to a point |
| 8–12 | 3.3–5 s | **01 Liquid Chrome** | The drop. A 3D extruded chrome wordmark slams in with a floor reflection, shockwave ring, sparks, light sweeps and glints |
| 12–14 | 5–5.8 s | **02 Glassmorphism** | Frosted glass card over moving colour blobs, staggered glass letters, floating glass orbs |
| 14–16 | 5.8–6.7 s | **03 Neumorphism** | Embossed "VIBE", debossed "EDITING", and a soft-UI play button, slider and toggle that flips on the beat |
| 16–18 | 6.7–7.5 s | **04 Neon Noir** | Tubes flicker on letter by letter on a brick wall. A lime frame draws itself and the sign reflects on a wet floor |
| 18–20 | 7.5–8.3 s | **05 Datamosh** | RGB split, slice displacement, pixel-sort drips, data blocks. The music beat-repeats and bitcrushes with it |
| 20–22 | 8.3–9.2 s | **06 Liquid Serif** | Playfair italic fills with a domain-warped liquid shader. The surface rises in waves and throws droplets |
| 22–24 | 9.2–10 s | **07 Claymorphism** | Puffy pastel clay letters drop in with squash-and-stretch, each with its own squish |
| 24–26 | 10–10.8 s | **08 Swiss Kinetic** | Counter-scrolling rows of outline and solid type. The hero band snaps red |
| 26–28 | 10.8–11.7 s | **09 8-Bit Arcade** | True 320×180 pixel art with a synthwave sun and grid, bouncing pixel letters, a score counter and a coin sound |
| 28–30 | 11.7–12.5 s | **10 Pop Art** | Halftone dots, a comic starburst, a hard-shadow outlined lockup and a "MEANWHILE, IN THE EDIT…" caption |
| 30–32 | 12.5–13.3 s | **11 Particle Field** | About 4,000 particles swirl in 3D, converge into the word, shimmer, then blow toward camera |
| 32–34 | 13.3–14.2 s | **12 Blueprint** | Construction lines, letter bounds, compass circles, a dimension line, a line-drawn outline, hatching and a title block |
| 34–36 | 14.2–15 s | **13 Holographic** | Iridescent foil that card-flips in, with foil stripes, a light sweep and sparkles |
| 36–40 | 15–16.7 s | **Montage** | Accelerating recut (1/2 beat, then 1/4) with inverts, a snare roll and a riser, then a half-beat of silence |
| 40–42 | 16.7–17.5 s | **Mosaic** | 13 vertical slices, one per style, slide in so the logo reads as a patchwork, then collapse |
| 42–48 | 17.5–20 s | **Hero** | Stacked chrome lockup with chromatic rim light over a liquid aura. Sweep, a scrambling tagline "ONE NAME · EVERY VIBE", a lime star, a final braam hit, fade |

Transitions between styles rotate through slice, diagonal wipe (lime edge), iris and zoom-through. Every cut also gets a camera punch, a flash and chromatic aberration. The HUD tracks the style name and a 13-tick progress bar.

## Sound

The score is in D minor (Dm–Bb–F–C) at 144 BPM. It has four-on-the-floor kicks, claps and snares, 16th hats, sidechained rolling bass, supersaw pads and stabs on every cut, and an arp that brightens toward the montage. Trailer sound design: braams (detuned saw clusters with a blasting filter), impacts, sub drops, risers, reverse cymbals, whooshes into every cut, and two silent "breaths" before the big drops.

Each style also has its own signature sound: a metallic shing for chrome, glass chimes, soft UI clicks for neumorphism, a neon buzz gated by the same hash as the on-screen flicker, glitch zaps, liquid bloops, clay boings, chiptune blips and a coin, a comic pow, a sparkle shower, a pencil scribble, and a holo glissando.

## Build

```bash
./build.sh                               # audio + frames + mux -> out/vibe_editing_logo_trailer.mp4 (resumable)
./build.sh --fps 30 --mb 2               # fast draft
node render.mjs --stills 3.8,6.3,12.2    # preview PNGs (seconds) -> out/stills/
```

Requires Node with `playwright` (Chromium; WebGL runs on SwiftShader, so no GPU is needed), plus Python with `numpy` and `scipy`, and `ffmpeg`.

**Live preview:** serve the folder (`npx http-server logo-trailer`) and open `trailer.html`. Space plays or pauses with the audio, and ←/→ scrub a bar at a time.

Each style is one `initX()` (bakes text plates once) plus one `sX(g, lb, t)` scene function in `trailer.js`. Add or reorder styles in `STYLES`, and keep the cue beats in `audio.py` in sync.

Fonts (all OFL, Google Fonts): Unbounded, Anton, Instrument Serif, JetBrains Mono, Inter Tight, Montserrat, Luckiest Guy, Syne, Tilt Neon, Press Start 2P, Playfair Display, Bungee.
