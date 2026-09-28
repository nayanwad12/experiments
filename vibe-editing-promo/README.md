# Vibe Editing by Ideabro Studio: 30s paper-cut promo

A 30 second vertical (1080×1920, 30 fps) motion-graphics promo for Reels, built entirely in code:

- **Look:** layered cut-paper with a paper-fibre texture, soft drop shadows between layers, torn edges and die-cut sticker lettering (Montserrat Black). Paper elements animate at 12 fps for a stop-motion feel, while camera punches, shakes and the torn-paper transitions run at 30 fps.
- **Palette:** periwinkle `#C4C6FF`, lime `#E3F59B`, blush `#FFCFD8`, ice `#C8F0EC`, ink `#111111`, white paper.
- **Audio:** an original 150 BPM track (A minor, i–VI–III–VII) plus paper SFX (rustle, crumple, tear, scissors snip, whoosh, pop, stamp thud, typing, clock ticks, clapper). Everything is synthesised in numpy, so there are no samples and no copyright issues.
- **Cuts:** every cut lands on the beat grid (1 beat = 0.4 s).

| Time | Shot |
|---|---|
| 0–3.2s | HOOK: a timeline with 100 clips crumples into a paper ball. "STILL EDITING LIKE IT'S 2015?" |
| 3.2–7.2s | PROBLEM: a spinning paper clock, an hours counter and clip cards piling up. "HOURS PER REEL." |
| 7.2–11.2s | REVEAL: a chat bubble types "make it pop" and a pop-up book unfolds a video. "VIBE EDITING." |
| 11.2–23.2s | MONTAGE: CAPTIONS → MOTION (kinetic type) → ANIMATION (logo) → ADS (product) → TRANSITIONS → strobe recap → ALL / WITH / AI |
| 23.2–26.8s | PAYOFF: a clapperboard and scissors cutting film. "YOU DIRECT. AI EDITS." |
| 26.8–30s | CTA: stamped logo "VIBE EDITING by IDEABRO STUDIO", "ENROLL NOW", "LINK IN BIO" |

## Build

```bash
pip install skia-python numpy scipy imageio-ffmpeg   # skia needs libegl1 + libgl1 on Linux
python3 build.py          # -> out/vibe_editing_promo.mp4
python3 video.py stills 1.0 9.9 27.8   # preview PNGs
```

To change the CTA link, edit the `"LINK IN BIO"` text in `scenes.py` (`s_cta`). All timings, SFX cues, shakes and flashes live in `timeline.py`.
