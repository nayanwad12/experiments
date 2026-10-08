# Vibe Editing Reels

- **ideabro studio glassmorphism Reel (35 s, premium glass motion graphics + CTA):** see [`glass-vibe-editing/README.md`](glass-vibe-editing/README.md)
- **Batch 2 (one Reel per skill, 3D, new music engine):** see [`batch2/README.md`](batch2/README.md)
- **Batch 1 (6 Reels):** below

# Batch 1 (6 Instagram Reels)

Six finished, narrated, vertical Reels (1080×1920, 30 fps, H.264 + AAC 48 kHz, −14 LUFS) for the Vibe
Editing page. Each one shows a different kind of video you can make with one workflow and **no AI video
tools**: no Higgsfield, Veo, Sora or Runway, and no After Effects or Premiere. Every frame is drawn in code
(skia + numpy), every sound is synthesised in numpy, and the narration is Kokoro TTS running locally.

| # | Reel | Length | File |
|---|---|---|---|
| 01 | **Prompt → Claymation**: "This claymation has no clay." | 23.7 s | [`01-claymation/out/01_claymation_no_clay.mp4`](01-claymation/out/01_claymation_no_clay.mp4) |
| 02 | **Same prompt, 5 styles**: clay, crayon, paper cut, pixel art, neon | 36.4 s | [`02-five-styles/out/02_same_prompt_five_styles.mp4`](02-five-styles/out/02_same_prompt_five_styles.mp4) |
| 03 | **"$50,000 product ad", one prompt**: premium ad for a concept product (Vibe Buds) | 25.2 s | [`03-product-ad/out/03_product_ad_one_prompt.mp4`](03-product-ad/out/03_product_ad_one_prompt.mp4) |
| 04 | **Kinetic typography quote**: "Everyone is waiting… just start." | 21.7 s | [`04-kinetic-quote/out/04_kinetic_quote.mp4`](04-kinetic-quote/out/04_kinetic_quote.mp4) |
| 05 | **Pixel-art game cutscene**: "Prompt Quest", chiptune, achievement unlocked | 21.1 s | [`05-pixel-cutscene/out/05_pixel_cutscene.mp4`](05-pixel-cutscene/out/05_pixel_cutscene.mp4) |
| 06 | **ASMR marble sorter**: 36 glass marbles, a synthesised click for every landing | 25.9 s | [`06-asmr-marbles/out/06_asmr_marbles.mp4`](06-asmr-marbles/out/06_asmr_marbles.mp4) |

All six end on the same brand card: **Vibe Editing / No AI video tools. / Just one prompt. / Follow for more.**

## Suggested posting order + captions

Post in this order: the hook formats first, then the "proof" pieces, then the calm one.

**1. Claymation (01)**
> This claymation has no clay. 🤖🌱
> No camera. No studio. No AI video generator. One sentence → every frame sculpted in code.
> Comment "CLAY" and I'll show you the prompt.
> #vibeediting #claymation #stopmotion #motiondesign #contentcreator #videoediting

**2. Same prompt, 5 styles (02)**
> Same prompt. Five completely different videos. Which one's your favourite, 1–5? 👇
> Changing the whole style took ONE word.
> #vibeediting #animation #pixelart #synthwave #papercut #creativecoding

**3. Product ad (03)**
> This looks like a $50,000 product ad. It took one prompt.
> No studio. No 3D software. No AI video tool. (Vibe Buds is a concept product.)
> #vibeediting #productvideo #adcreative #motiongraphics #brandvideo #marketing

**4. Kinetic quote (04)**
> Everyone is waiting for the perfect tool. The ones who win just start. ⚡
> Kinetic typography, one prompt, no After Effects.
> #vibeediting #kinetictypography #motivation #typography #aftereffects #reels

**5. Pixel cutscene (05)**
> I made a video game cutscene without a game engine. 🎮
> Every pixel placed by code, chiptune included. Achievement unlocked: vibe editing.
> #vibeediting #pixelart #retrogaming #8bit #gamedev #indiegame

**6. ASMR marbles (06)**
> Watch this until the end. 🎧 Every click is generated in code. No samples, no recording, no AI video tool.
> #vibeediting #oddlysatisfying #asmr #satisfying #satisfyingvideos #3dsatisfying

Tip: use the first frame of each Reel as its cover. They were designed as covers (title or hook on screen).

## How they're built

```
reels/
  common/            shared pipeline (used by all six)
    kit.py           9:16 canvas, easing, type, house captions, prompt bar, brand end card, parallel renderer
    voice.py         Kokoro narration per line + word timings (pause detection + phoneme weighting)
    sound.py         mix: voice bus, ducked music, SFX, auto-balance (voice ≥ +10 dB over the bed while speaking),
                     loudnorm to −14 LUFS, Instagram delivery encode (H.264 high, CRF 18, ≤12 Mbps)
    audio_kit.py     original music beds + SFX synthesised in numpy (no samples)
    clay.py          plasticine material: lumpy paths, boil, thumbprint texture, clay letters
  0N-*/script.py     the narration lines (edit these to change what is said)
  0N-*/build.py      timeline + scenes + sound for that Reel
```

Every visual cue reads its time from the narration (`S.find("hook", "clay")` = when "clay" is spoken),
so if a line is re-recorded or reworded, the picture and the SFX move with it.

### Rebuild

```bash
pip install skia-python numpy scipy soundfile kokoro-onnx pillow
# Kokoro model files (kokoro-v1.0.onnx, voices-v1.0.bin) from the kokoro-onnx GitHub release
#   -> /home/user/models, or set KOKORO_MODELS
python3 synth_all.py                    # narration for all six (cached per line)
cd 01-claymation
python3 build.py sheet                  # contact sheet -> out/sheet.png
python3 build.py stills 1.2 9.8         # single frames -> out/stills/
python3 build.py all                    # picture + mix -> out/01_claymation_no_clay.mp4
```

### Voices
- Narrator: `af_heart` (Reels 01, 02, 03, 05 and the tail of 04)
- Ad voice: `af_bella`, slightly slower (03)
- Quote voice: `am_michael` (04)
- ASMR: `af_nicole`, soft (06)
