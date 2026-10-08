# OncoXpress band and ring: 26.4 s sci-fi teaser

**Watch:** [`out/oncoxpress_teaser.mp4`](out/oncoxpress_teaser.mp4)

A 16:9 teaser (1920×1080, 60 fps, AAC 320k audio) for "The OncoXpress band and ring is coming soon", in a sci-fi hologram style:
- **Devices:** the band and ring are true 3D wireframe geometry, perspective-projected and depth-faded, drawn as additive glowing lines with a two-pass bloom. Each one materialises under a sweeping scan plane, and the band dissolves into ~900 particles that swirl and re-form as the ring.
- **Setting:** a deep-space starfield drifting toward camera, a nebula and a perspective grid floor.
- **Overlays:** HUD frames, rotating reticles, typed callouts and decoding Orbitron titles, with chromatic and slice glitches on the cuts plus scanlines.
- **Rendering:** every frame is generated in code by an HTML Canvas engine, rendered headlessly with Playwright (4-sample motion blur).

**Score:** original, synthesised in numpy (`audio.py`), at 100 BPM (1 bar = 2.4 s) in D minor:
- **Bed:** a breathing D/A drone with wind.
- **Pulse:** a sidechained 16th arpeggio whose filter opens across the film.
- **Hits:** low brass braams on each reveal, impacts and a taiko build into the final hit.
- **Effects:**
  - data blips under the typing
  - scan sweeps
  - a glitch stutter and whoosh for the particle morph
  - sync chimes.

| Time | Scene |
|---|---|
| 0–4.8 s | Boot console types in, "// INCOMING TRANSMISSION", **THE ONCOXPRESS** decodes, glitch out |
| 4.8–9.6 s | **BAND** (WEARABLE // 01): the wristband materialises under a scan plane with a reticle, a pulse trace on its display module, and callouts |
| 9.6–12 s | The band dissolves into particles that swirl across the frame |
| 12–16.8 s | **RING** (WEARABLE // 02): the particles re-form as the ring, which spins about its axis with glowing inner nodes and callouts |
| 16.8–21.6 s | Both devices side by side with a SYNC link: **THE ONCOXPRESS / BAND AND RING** |
| 21.6–26.4 s | Flash and final braam: **COMING SOON** with an anamorphic streak, fade out |

The devices are stylised holograms, not product renders. HUD labels ("DISPLAY MODULE", "INNER LAYER", "NODE 01 // ACTIVE") are decorative and make no product claims.

## Build

```bash
./build.sh                                # score + frames + mux -> out/oncoxpress_teaser.mp4 (~45 min on 4 cores; resumable)
./build.sh --fps 30 --mb 2                # fast draft
node render.mjs --stills 3.4,7.8,14.5,23  # preview PNGs -> out/stills/
```

Requires Node with `playwright` (Chromium) and Python with `numpy`, `scipy` and `imageio-ffmpeg`. Delete `out/segs_*` after you change the visuals, because rendering resumes from finished segments. Cue times live at the top of `scifi.js` and `audio.py`. Fonts: Orbitron, Rajdhani (OFL), JetBrains Mono (OFL).
