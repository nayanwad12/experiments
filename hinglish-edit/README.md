# Adaix OOH Creative Challenge: Hinglish reel edit

**v2 premium: [`out/adaix_ooh_premium.mp4`](out/adaix_ooh_premium.mp4)** (`premium.py`). This is the same cut as v1, with a new look and sound design.
- **Look:** white + orange (#FF6B1A) kinetic type with one motion-graphics system. Every word rises through a mask and leaves upward. Big Anton type sits behind the speaker or in each shot's free space. Accents use Instrument Serif italic in orange, and the HUD uses JetBrains Mono (brand, chapter 01–06, progress line).
- **Transitions:** an orange slab wipe on every shot change.
- **Word-locked graphics:**
  - an idea bulb that draws itself
  - "where?" map pins
  - Adaix and an OOH billboard behind the speaker
  - BORING / BRAND? and YEH KYA? with reaction bursts
  - city / brand / product / location brief cards
  - a radar scan for "us city pe, us location pe… already kya chal raha hai"
  - an INSIGHT → OOH IDEA flow
  - a crossed-out billboard
  - observation / insight / OOH-thinking icons
  - WINNER? behind the speaker, then a crossed-out certificate
  - a billboard that powers on for "come alive on Adaix OOH Media"
  - WORK WITH US, creativity, JOIN US, and a REGISTER NOW button with a cursor click
- **Sound:** a new "tech" music bed with matching SFX. Mastered to -14 LUFS, with light grain and a warm grade.
- **Render:** `python3 premium.py stills 5.9 13.9` · `python3 premium.py render` → `out/adaix_ooh_premium.mp4`

## v1 (minimal, white + neon green)

One raw multi-speaker phone video (48.9 s, 1080x1920, 6 shots) in, a finished minimal edit out:
**[`out/adaix_ooh_edit.mp4`](out/adaix_ooh_edit.mp4)**, 41.1 s, 1080x1920, 30 fps, H.264 + AAC, -14 LUFS.

## What the edit does
- **Dead space removed:** every pause over 0.2 s between phrases is cut (48.9 s → 41.1 s). A short beat is kept after "Yeh kya?" for the reaction.
- **Captions:** Hinglish written in English letters, revealed word by word on the exact spoken word. They are white InterTight Black; the word being spoken lights up neon green (#39FF14) and keywords stay neon.
  Entrances rotate between pop, rise and blur. Some words are set in neon serif italic (*creative, idea, insight, creativity*).
- **Caption gags, each tied to its word:**
  - "boring" loses energy and sags.
  - "billboard" and "certificate" are struck through after they're said.
  - City / brand / product / location pop in as neon pills.
  - Observation / insight / OOH thinking tick in one by one.
  - Giant **OOH** and **WINNER?** rise *behind* the speaker (RobustVideoMatting person matte).
  - "register now" becomes a neon **REGISTER NOW** button that a cursor clicks.
- **Motion:**
  - zoom-whip with motion blur on every shot change
  - punch-ins that alternate to hide the jump cuts
  - slow push-ins
  - word-locked punches on Adaix, "Boring brand?", "Yeh kya?" and "winner?"
  - shakes on "Yeh kya?" and "Ruko ruko"
- **Sound:**
  - voice clean-up (high-pass, denoise, compression, de-ess)
  - an original synthesised music bed, ducked under the voice (no stock music, no copyright claims)
  - whooshes on the cuts, pops on the pills, ticks, sparkle, ding, riser and impact into "winner", and a click on the button

## Transcript (Hinglish)
> Mind mein ek new creative idea hai, lekin samajh nahi aa raha ki show kahan karein? Isliye Adaix lekar aaya hai new OOH Creative Challenge.
> Make a boring brand… / Boring brand? / Yeh kya? / Ruko ruko, main batati hoon.
> Pick your city, pick any brand, product or location. Then see, us city pe, us location pe already kya chal raha hai. Find the insight and turn this insight into an OOH idea.
> We're not just looking for a creative billboard, we are looking for observation, insight and creative OOH thinking.
> Aur winner? Sirf certificate nahi. Your idea could actually come alive on Adaix OOH Media, and also you get a chance to work with us.
> If you want to show your creativity, join us and register now!

The lines least certain from the audio are *"Make a boring brand… / Boring brand? / Yeh kya?"* and *"creative OOH thinking"*. Whisper also heard the last one as "creative always thinking". To correct a line, edit `SEGS` in `align.py` and `GROUPS` in `edit.py`, then re-run.

## Pipeline
| step | file | what it does |
|---|---|---|
| ears | `work/asr.py` | Silero VAD + Whisper turbo (sherpa-onnx) → speech segments, English pass |
| ears | `work/whisper_np.py` | own greedy decoder over the same ONNX Whisper. sherpa-onnx caps output at about 6 tokens/s and decodes token by token, which breaks Devanagari. This decoder gives full Hindi, English and Hinglish-prompted passes. |
| ears | `work/score.py` | Whisper log-likelihood of candidate lines, used to settle ambiguous phrases |
| ears | `align.py` | pocketsphinx forced alignment of the romanized Hinglish, with hand pronunciations for the Hindi words → `work/words.json` |
| eyes | `matte.py` | frames at 30 fps + RobustVideoMatting person matte → `work/alpha.npy` |
| edit | `edit.py` | cut list, camera, captions, graphics, sound mix, delivery |

```bash
# models: sherpa-onnx-whisper-turbo + silero_vad.onnx (k2-fsa/sherpa-onnx releases, asr-models),
#         rvm_mobilenetv3_fp32.onnx (PeterL1n/RobustVideoMatting v1.0.0) in /home/user/models
pip install sherpa-onnx onnxruntime pocketsphinx skia-python opencv-python-headless scipy regex pillow
cp <take>.mp4 raw/take.mp4 && ffmpeg -i raw/take.mp4 -ac 1 -ar 16000 work/audio16k.wav
cd work && python3 asr.py turbo en && python3 chunks.py && python3 whisper_np.py en chunks.json asr_en_chunks.json && cd ..
python3 align.py && python3 matte.py
python3 edit.py info              # cut list
python3 edit.py stills 6.3 29     # check frames
python3 edit.py render            # -> out/adaix_ooh_edit.mp4  (~5 min on 4 cores)
```
Shared helpers come from `../reels/common` (kit, audio_kit, vibelib) and fonts from `../reels/fonts`.
