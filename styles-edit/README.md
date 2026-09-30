# styles-edit — "One video, 5 styles — just by saying it"

A walking-in-the-garden selfie take where every spoken command switches the entire look *and* the music:
news channel → movie trailer → cartoon → video game → 1920s silent film → rewind back to normal.
Dead air cut and played 1.08× faster (voice time-stretched, pitch kept): 45 s raw → 37.4 s, 1920×1080, 30 fps.
The selfie-camera mirror is undone so the T-shirt reads correctly.

| style | picture | sound |
| --- | --- | --- |
| hook | style chips pop on "five times", fly into a 1/5 … 5/5 tracker | punchy beat, pops, riser |
| news | red/white/navy bar wipe, VIBE 24 LIVE bug, BREAKING NEWS lower third typing the headline, scrolling ticker | news sting + urgent ticking bed |
| trailer | cut to black, 2.39 bars, teal/orange grade, darkened background + rim light, lens flare, push-in, "IN A WORLD…" title card, bold titles, flash | braam, trailer toms, voice in cinema reverb |
| cartoon | starburst iris into a glossy 3D-cartoon world (sky, sun, puffy clouds, hills, swaying trees, rising balloons, foreground bushes), smooth animated-film look on him, 3D bubble lettering: POW!, HI! on the wave, bouncing COLORFUL! | slide whistle, boings, marimba bounce |
| game | pixel dissolve into an 8-bit side-scrolling platformer: he becomes a sprite, pipes, bricks, ? blocks, spinning coins, retro score/coins/world/time HUD; on "Level up" the ? block bumps a coin out and he flashes; NES dialog box | swung chiptune, bump, coin, level-up jingle |
| 1920s | film burn, sepia B&W at 16 fps, grain, scratches, dust, flicker, gate weave, rounded 4:3 gate, ANNO 1923, silent-film intertitle | ragtime piano + projector; voice goes gramophone-thin, then *silent* under the card |
| rewind | VHS rewind through every style (RGB split, tracking noise, ◀◀ REWIND), placed in the silence before "back to normal" | tape rewind, beat drops back |
| CTA | recap grid of all 5 styles + live tile, JUST BY SAYING IT, comment box types EDIT | beat, ticks, keys |

## Run
```bash
cp <take>.mov raw/raw.mov
cd work && python3 asr.py turbo en && python3 align.py && python3 matte.py && cd ..
python3 sound.py && python3 render.py      # -> out/final.mp4
python3 trim_raw.py && python3 reel.py     # -> out/trimmed_raw.mp4, out/comparison_reel.mp4 (9:16)
```
`work/asr.py` / `align.py` / `matte.py` are the same tools as in `claude-edit/` (Whisper via sherpa-onnx,
pocketsphinx alignment, RobustVideoMatting). Raw footage and intermediates stay out of git.
