# faceless-reel: "Vibe Editing", a narrated motion reel with no face on camera

A 39.5 second, 1080×1920 (9:16), 30 fps reel built from one narration file. It follows the format of a "laptop in a dark room" product reel: the motion graphics play on a laptop screen in a purple-lit room, and a slow handheld camera push-in makes it feel filmed. Every frame is drawn in code (Canvas 2D, rendered headlessly with Playwright). The music and sound effects are synthesised in numpy, and every animation is timed to a word in the narration.

**Outputs**
- `out/vibe_editing_reel.mp4`: clean version, so you can add your own caption in Instagram.
- `out/vibe_editing_reel_caption.mp4`: the same video with the top caption "Claude cooked 😮‍💨" burned in.

## Pipeline

| step | file | what it does |
| --- | --- | --- |
| ears | `work/align.py` | silence-split phrases plus pocketsphinx forced alignment of the script, written to `work/words.json` (the onset of every word) |
| picture | `reel.js` / `reel.html` | the screen scenes, then the laptop and room composite, handheld camera, grain and vignette. Word onsets live in `W_`. |
| sound | `audio.py` | cleaned and compressed narration; a dark drone with clock ticks in act 1; a 100 BPM F–C–Am–G groove from "Meet Vibe Editing"; a tape-stop on "Oh…"; a pad swell into the CTA. About 60 SFX sit on their words, and the music is ducked under the voice. |
| caption | `caption.mjs` | a transparent PNG of the top caption, overlaid by `build.sh` |
| render | `render.mjs` | 60-frame chunks across 4 workers. It can resume after an interruption and retries failed chunks. |

## The beats

| time | narration | on screen |
| --- | --- | --- |
| 0.0 | "It's 1:14 AM." | big clock; the last digit rolls 3 → 4 on "fourteen" |
| 1.9 | "Still editing… one reel." | the clock lifts away and a timeline floods with 200 clips (with a counter); "all for *one* reel." |
| 4.6 | "Cuts here. Captions there. Keyframes everywhere." | cut cards fly in from the left and caption cards from the right; keyframe cards surround **everywhere.** |
| 9.3 | "So I stopped." | everything spirals into one orange dot, followed by silence |
| 10.9 | "Meet Vibe Editing." | the dot bursts into a cream screen and the logo draws itself |
| 12.8 | "One reel: six hours. Ugh." | counter **6h 00m**, then *Ugh.* |
| 16.4 | "Now take out the cutting. The captions. The zooms. The sound effects." | strike-through on each word; the time drops 4h 10m → 2h 30m → 1h 05m → 12m while deduction chips stack up |
| 21.5 | "Twelve minutes. Nice." | **12m** turns black and grows; *Nice.* appears |
| 23.8 | "Just type what you want. Hit enter." | prompt bar types *make it punchy, add captions, cut the pauses*; send button and ripple |
| 26.2 | "Every night. Before chai. Posted." | phone at 10:02 PM, a steaming chai cup, the "Your reel is live ✓" notification, then hearts |
| 29.5 | "Fewer clicks. More posts." | tagline with a masked reveal |
| 31.8 | "Vibe Editing." | logo |
| 33.3 | "Oh… and this whole video? Made with AI." | the screen shrinks into a window over this project's own code editor; "Made with *AI.*" |
| 36.6 | "Comment VIBE." | glowing comment pill; VIBE types itself in, then sparks |

## Run

```bash
python3 work/align.py                # only when the narration changes (needs pocketsphinx; run inside work/)
./build.sh                           # audio + frames + both MP4s (~15–25 min on 4 cores; resumable)
./build.sh --fps 24 --mb 1           # fast draft
node render.mjs --stills 8.4,21.9    # preview PNGs -> out/stills/
CAPTION="your caption" ./build.sh    # different burned-in caption
```

**Live preview:** serve the folder (`npx http-server faceless-reel`) and open `reel.html`. Space plays or pauses with the narration, and ←/→ scrub by 1 s.

**New narration?** Replace `work/narration.mp3`, update the segment texts and times in `work/align.py`, run it, and copy the new word onsets into `W_` (in `reel.js`) and `W` (in `audio.py`).

Fonts (all OFL, Google Fonts): Inter Tight, Instrument Serif, JetBrains Mono. The narration in `work/narration.mp3` was supplied by the user. Renders and frame segments stay out of git.
