# B monogram logo animation

An 8-second, 60 fps logo sting for the white-on-black **B** monogram (`logo.webp`). The picture is real-time 3D
(Three.js) rendered frame by frame, and the sound is synthesised in numpy. No After Effects, no AI video tools.

| File | Format | Use |
|---|---|---|
| `out/B_logo_4K_16x9.mp4` | 3840×2160, 60 fps | master: YouTube intro/outro, presentations |
| `out/B_logo_1080p_16x9.mp4` | 1920×1080, 60 fps | lighter 16:9 copy |
| `out/B_logo_1080x1920_9x16.mp4` | 1080×1920, 60 fps | Reels / Shorts / TikTok / Stories |
| `out/B_logo_1080_1x1.mp4` | 1080×1080, 60 fps | feed post, profile intro |

All files are H.264 high with AAC 320k at 48 kHz, −14 LUFS and −1 dBTP, and each is under 28 MB.

## The beats

| Time | Picture | Sound |
|---|---|---|
| 0.0–0.35 | black, dust in the air | low drone fades in |
| 0.35–2.25 | **light trace**: comet heads ignite in the 45° notch, split, and race round the front and back edges of both shapes, shedding sparks | ignition zap, electric "draw" tones panned left/right, rising in pitch |
| 1.95–3.30 | **scan**: the solid B fills in along the logo's own 45° angle behind a hot scan edge, while the camera swings round to the front | riser, reverse cymbal, scan hum |
| 3.30 | **impact**: flash, shockwave ring, anamorphic streak, spark burst | sub boom, crack, metal clang, braam, hall tail |
| 3.9–5.3 | **hero**: a light band sweeps across the white ceramic face, and reflections slide over the polished chrome sides | glassy swish (left to right) and a soft chime |
| 5.6–6.55 | **dolly zoom**: the perspective flattens and the 3D B resolves into the flat logo | reverse swell |
| 6.55–8.0 | **lock-up**: the exact flat white logo on pure black, with a faint glow | clean chime chord, soft thump, tail |

The final frames are a vector rebuild of the supplied logo. It overlaps the original at 99.2% IoU, and the
differences are anti-aliasing pixels along the edges. They render untonemapped, so the white is pure #FFFFFF
and the background pure #000000.

## Files

```
logo-b/
  logo.webp     the supplied artwork
  geom.py       the B as exact vector outlines (measured from logo.webp; `python3 geom.py check` prints the overlap)
  scene.js      the 3D animation (every frame is a pure function of t)
  sting.py      sound design, synthesised from scratch
  build.py      timeline + render + sound + delivery
  deliver.py    mux and encode each format
  queue.sh      renders all three aspect ratios one after another
```

```bash
python3 build.py stills 1.6 3.3 7.5 --fmt 16x9    # check frames
./queue.sh                                         # picture for 9x16, 1x1, 16x9 (the 4K one is slow on CPU)
python3 build.py sound
python3 build.py final --fmt 16x9                  # and --fmt 9x16, --fmt 1x1
```

Changing the timing means editing `T` in `build.py`, because the picture and the sound both read from it.
