# "AI edited this" Reel (soft-sell ad, 9:16)

Final: `out/ai_edited_reel.mp4`. 1080×1920, 30 fps, 47 s, H.264 + AAC, −14 LUFS, made for Instagram Reels.

Made from one handheld front-camera take (49 s) with the Vibe Editing System:
- **Stabilised:** two-pass vidstab, 1,477 frames
- **Cut:** dead air and the closing "thank you" removed, 49.2 s → 46.1 s
- **Graded:** warmer, with lifted shadows on the backlit face
- **Design:** one paper-cut editorial theme throughout, in brand colours (cream paper, periwinkle, lime, ink). The 11 scenes switch between four layouts: full-screen face, a face photo card, graphics with a face circle top-right, and graphics only.
- **"AI EDITED THIS":** a stamp that becomes a corner badge for the rest of the video
- **Captions:** word-synced pop captions on paper labels, kept inside the Reels safe zone
- **Sound:** original music with a drop on "the music", synthesised sound effects, and cleaned-up voice

Rebuild (needs `raw/take1.mp4` and the `work/` files):
```
python3 scene.py audio      # voice + music + sfx -> work/mix.wav
python3 scene.py render     # picture -> out/ai_edited_reel_picture.mp4, then mux with work/mix.wav
```
All timings are in `timeline.py`.
