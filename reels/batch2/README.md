# Vibe Editing Reels, batch 2: one Reel per skill

Seven narrated vertical Reels (1080×1920, 30 fps, −14 LUFS), each made with one of the Vibe Editing System skills.
Compared with batch 1, they add **real 3D** (Three.js rendered headlessly in Chromium), **stronger concepts with a twist**,
a **new music engine** (arranged songs with builds and drops, mixed and mastered), a **broadcast voice chain**, and
**faster cuts on the bar grid**. Still no AI video tools: every frame is code, every sound is synthesised, and the
narration is local Kokoro TTS.

| # | Skill | Reel | Hook |
|---|---|---|---|
| B2-01 | `vibe-editing-system` (Start Here) | **Start Here trailer** · 24 s | "Every video on this page was made with one skill." A 3D wall of our real videos → tunnel flight → glass tiles shatter on "No After Effects / Premiere / AI video tools" → glass prompt → sphere of screens → 3D logo |
| B2-02 | `vibe-launch-ads` | **"This app doesn't exist"** · 25 s | A full launch ad for a concept fintech app (Saveo): 3D phone, coins into a glass jar, bars rising out of the screen, wireframe "it's all code" reveal, the ad in 4 formats |
| B2-03 | `vibe-motion-graphics` | **5 logo animations** · 26 s | Liquid chrome, particle storm, neon sign, glitch, heavy-metal slam, cut to drift phonk, ending on a "comment 1–5" recap |
| B2-04 | `vibe-stylised-animation` | **The clay mascot that's made of code** · 20 s | A 3D claymation character talks to camera (lip sync from the voice), gets poked by a giant clay finger, turns to wireframe, and watches its world drop in |
| B2-05 | `vibe-ai-footage` (faceless recipe, no AI clips) | **Ariane 5: one number, one rocket** · 48 s | Faceless documentary short on Flight 501: liftoff, inside the guidance computer, 64 bits into 16, the 32,767 overflow, both computers fail, break-up |
| B2-06 | `vibe-audio-videos` | **This song is code. Watch it build.** · 29 s | Kick → hats → bass → chords → melody → drop; each layer drives its own part of a 3D audio-reactive visualiser, with live stem meters |
| B2-07 | `vibe-bulk-videos` | **100 personalised videos, one command** · 32 s | One template × a 100-row spreadsheet: a wall of all 100, the batch run, rows becoming videos, heroes in English / Hindi / Spanish, one card in every format |

Talking-head and VFX need real footage; they come next when there's a phone take.

## Posting captions

**B2-01** · Every video on this page was made with ONE skill. No After Effects. No Premiere. No AI video tools.
You type the vibe, it builds the video. Follow to learn it first. #vibeediting #motiondesign #3danimation #creativecoding

**B2-02** · This app doesn't exist. Its launch ad does. 📱 Phone, UI, coins, charts, music: all built in code from
one prompt. (Saveo is a concept app.) #vibeediting #productvideo #appmarketing #adcreative #3d

**B2-03** · 5 logo animations, one prompt each. Which one goes on your brand? Comment 1–5 👇
#vibeediting #logoanimation #motiongraphics #branding #phonk

**B2-04** · He's made of clay… sort of. 🟢 3D claymation with lip sync to every word, shot "on twos" like real
stop-motion, and nobody touched him. What should he make next? #vibeediting #claymation #stopmotion #3dcharacter

**B2-05** · In 1996, a single number destroyed a rocket in under 40 seconds. 🚀 The Ariane 5 Flight 501 story,
made without stock footage or AI video. #vibeediting #engineering #softwarebugs #spacehistory #facelesschannel
(Source: ESA/CNES Ariane 5 Flight 501 Inquiry Board report, July 1996.)

**B2-06** · This entire song is code. 🎧 Kick, hats, bass, chords, melody… and the drop. No samples, no DAW,
no AI music. #vibeediting #musicproduction #audiovisualizer #creativecoding #edm

**B2-07** · I made 100 personalised videos with one command. Different names, languages (English, Hindi, Spanish)
and formats, from one spreadsheet. #vibeediting #automation #personalizedvideo #marketing #contentcreator

## How they're built

```
batch2/
  render3d.mjs     Three.js page -> frames in headless Chromium (SwiftShader), 4 workers, resumable, -> layer.mp4
  lib/stage.js     renderer + bloom + film-look shader (grain, vignette, chromatic aberration, grade) + helpers
  lib/b2.py        build CLI shared by all seven: prep | web <t..> | layer | sheet | stills | render | sound | all
  textpng.mjs      complex-script text (Hindi) shaped by Chromium -> PNG, composited by skia
  queue.sh         renders the remaining Reels one after another
  0N-*/script.py   narration lines (voice blends like "af_heart*0.6+af_bella*0.4")
  0N-*/scene.js    the 3D world (every frame a pure function of t, keyed to timeline.json)
  0N-*/build.py    timeline from the voice, music, 2D overlays/captions on top of the 3D layer, sound mix
../common/music.py the music engine: future_bass, phonk, synthwave, cinematic, whimsical, lofi_trap, edm_layers
```

Rebuild one: `cd batch2/03-logo-reveals && python3 build.py all` (needs `npm i` in `batch2/`, the Kokoro model files,
and Chromium for Playwright).
