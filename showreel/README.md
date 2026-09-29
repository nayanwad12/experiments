# VIBE EDITING: 30 s motion-design showreel

**Watch:** [`out/vibe_editing_showreel.mp4`](out/vibe_editing_showreel.mp4)

A 30 second 16:9 showreel (1920×1080, 60 fps, real motion blur) for the **Vibe Editing** course. Every frame is generated in code: an HTML Canvas + WebGL2 engine rendered headlessly with Playwright, and an original soundtrack synthesised in numpy.

**Concept:** the reel is edited *by prompt*. A chat bar types a vibe ("make it pop", "make it kinetic", "make it flow"…), hits send, and the next section drops on the downbeat.

**Engine:** each frame is a pure function of `t`. It gets 6-sample sub-frame motion blur (180° shutter), a camera rig with beat punches and impact shakes, and a GLSL post pass (mip-chain bloom, radial chromatic aberration, row/block glitch displacement, flashes, vignette, film grain). The liquid backgrounds are a GPU shader: domain-warped fBm with height-field lighting, plus iridescent metaballs.

**Music:** 128 BPM, so 30 s = 64 beats = 16 bars, and every cut sits on the grid. It's in F minor (i–VI–III–VII) and fully synthesised: kick, clap, hats, sidechained rolling bass, supersaw pads and stabs, arps, risers, impacts, a beat-repeat/bitcrush glitch section, a snare roll, and UI SFX (a key click for each typed prompt character, send pops, whooshes).

| Beats | Time | Section | Craft on show |
|---|---|---|---|
| 0–8 | 0–3.75 s | **01 EASE** | graph editor: a bezier curve gets yanked from linear to expo in-out, a ball runs the ease, serif "every frame is a decision.", collapse to a dot |
| 8–16 | 3.75–7.5 s | **02 TITLE** | shockwave + shard burst, stagger-slammed justified lockup, beat palette flips, callout chips, snap-slice glitch, zoom through a 3D text tunnel |
| 16–24 | 7.5–11.25 s | **03 KINETIC TYPE** | slot-machine MOTION, counter-scrolling TYPE wall, bounce-physics TIMING with its own graph, soft-focus *feel*, "IT'S NOT THE ~~SOFTWARE~~. IT'S THE VIBE.", circle wipe |
| 24–32 | 11.25–15 s | **04 SHAPE LANGUAGE** | 12×7 Bauhaus grid driven by travelling waves, polar-morph hero shape with colour echoes, portal into… |
| 32–40 | 15–18.75 s | **05 LIQUID** | domain-warped liquid shader, FLOW track matte, iridescent metaballs splitting and merging on the beat |
| 40–48 | 18.75–22.5 s | **06 DEPTH** | 2,166-point cloud morphing each beat: sphere → torus → lattice → knot → wave → helix → "3D" → explode, with a ring tunnel and axis gizmo |
| 48–52 | 22.5–24.4 s | **07 GLITCH** | RGB-split "BORING / NOT FOUND / 404", slice displacement, pixel-sort streaks, data blocks |
| 52–56 | 24.4–26.25 s | **08 MONTAGE** | 9 accelerating recap cuts with inverts and punches, drop-out to the lime dot |
| 56–64 | 26.25–30 s | **09 VIBE EDITING** | logo resolve, typed tagline "DIRECT THE VIBE. LET AI DO THE KEYFRAMES.", ENROLL NOW, by Ideabro Studio, bookend dot |

## Build

```bash
./build.sh                               # audio + frames + mux -> out/vibe_editing_showreel.mp4 (≈50 min on 4 CPU cores; resumable)
./build.sh --fps 30 --mb 3               # ~4x faster draft
node render.mjs --stills 4.2,16.3,19.1   # preview PNGs -> out/stills/
```

Requires Node with `playwright` (Chromium; WebGL runs on SwiftShader, so no GPU is needed), plus Python with `numpy`, `scipy` and `imageio-ffmpeg`.

**Live preview:** serve the folder (`npx http-server showreel`) and open `reel.html`. Space plays or pauses with the audio, and ←/→ scrub a bar at a time.

To edit copy, change the `PROMPTS` in both `reel.js` and `audio.py` (they share cue timings), and edit the tagline/CTA in `sOutro`. Palette tokens live in `C` at the top of `reel.js`. Fonts (all OFL, Google Fonts): Unbounded, Anton, Instrument Serif, Inter Tight, JetBrains Mono.
