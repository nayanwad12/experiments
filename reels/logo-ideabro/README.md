# IDEABRO STUDIO: five logo animations

Five logo stings for **IDEABRO STUDIO**: the B monogram stacked over the IDEABRO / STUDIO wordmark, in the
same five styles as the Vibe Editing logo-reveal reel. Each is 6.5 s at 60 fps with its own sound design.
The picture is real-time 3D (Three.js) rendered frame by frame, and every sound is synthesised in numpy.
No After Effects and no AI video tools.

| # | Style | What happens | Sound |
|---|---|---|---|
| 01 | **Liquid chrome** | a mercury blob churns, collapses with a splash, and the lockup grows out of it in polished chrome while droplets rain down | gloopy wobble, bubbles, splash hit, droplets, metal ring, chime |
| 02 | **Particle storm** | ~70k gold and white sparks circle in a vortex, stream in left to right, and lock into crisp artwork with a light pulse | swirling wind that pans round, sparkle grains, riser, lock hit, chime chord |
| 03 | **Neon sign** | on a brick wall, the B (warm amber) stutters on, then IDEABRO (white), then STUDIO, each glowing onto the bricks | relay clunks, a buzz on every flicker frame, hum, warm pad |
| 04 | **Glitch** | the lockup boots through a corrupted signal (torn rows, RGB split, block shifts, inversions), snaps clean, then glitches twice more | data chirps and bitcrushed stutters on each glitch frame, snap hit |
| 05 | **Heavy metal** | steel pieces drop onto concrete: the B slams (sparks, dust, shake), the letters hammer down one by one, and STUDIO lands as a plate; the camera then cranes up to a top-down hero view | whooshes, thuds, clangs tuned per letter, spark sizzle, brass swell |

The neon flicker and the glitch frames use the same hash in the picture (`stage.js E.hash`) and in the sound
(`stings.py jhash`), so every buzz and stutter lands on the frame where it's seen.

## Files

| File | Format |
|---|---|
| `out/IDEABRO_0N_<style>_16x9.mp4` | 1920×1080, 60 fps (YouTube, presentations) |
| `out/IDEABRO_0N_<style>_9x16.mp4` | 1080×1920, 60 fps (Reels, Shorts, TikTok, Stories) |
| `out/IDEABRO_5_styles_9x16.mp4` | showcase reel: title card plus all five, each labelled |

All files are H.264 high with AAC 320k at 48 kHz, −14 LUFS and −1 dBTP, and each is under 28 MB.

## Build

```
lib.js         the lockup as Three.js shapes (B from ../logo-b/geom.py, wordmark in Montserrat Black / Bold),
               a flat canvas version, the extrusion helper, the studio env, aspect-aware camera fit
s1-chrome.js … s5-metal.js   one scene per style (s1.html … s5.html load them)
stings.py      sound design per style
build.py       key times (T) for every style; stills / layer / sound / final / showcase
deliver.py     mux + encode, showcase reel
queue.sh       renders every style in both aspects; finals.sh muxes each one as it lands
```

```bash
python3 build.py stills 3 0.8 2.3 5.8          # check frames of the neon style
./queue.sh && ./finals.sh                      # all pictures, then all muxes
python3 build.py sound                         # all stings
python3 build.py showcase
```

To change the wordmark, edit `COPY` in `lib.js`. To change the timing, edit `T` in `build.py`, which both the
picture and the sound read.
