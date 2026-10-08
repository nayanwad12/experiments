# Pitch edit: premium kinetic-type version

- `out/pitch_edited.mp4`: the edit. 1080×1920, 30 fps, 44.6 s, −14 LUFS.
- `out/pitch_comparison.mp4`: before/after, 1920×1080. The raw phone take sits next to the edit, in sync.

What was done to the 50 s handheld take:
- **Stabilised:** two-pass vidstab. Frame-to-frame jitter went from 3.2 px to 1.0 px.
- **Cut:** the dead start, the aside "like the one which you are seeing right now" and the tail are removed. 50.2 s became 43.4 s.
- **Graded:** cinematic contrast with cool shadows and warm highlights. During the type moments the background darkens and loses some colour while the person stays bright.
- **Person cut-out:** a segmentation model cuts the person out of every frame (1,304 frames), so kinetic Anton type in white and neon sits behind the head.
- **12 scenes, one theme:** full-frame scenes with kicker + headline, graphic scenes (the old way, Step 02 prompt UI, "No app / editor / skills"), a magazine cover ("VIBE" masthead behind the head, cover lines, barcode), and a dark-panel wipe with a neon edge between scenes.
- **Captions:** word-synced Inter Tight captions, with the active word in neon.
- **Sound:** an original tech music bed with a drop on "the music", synthesised sound effects, and a cleaned-up voice.

Rebuild: `python3 scene.py prep && python3 scene.py audio && python3 scene.py render`, then mux with `work/mix.wav` (all timings are in `timeline.py`).
