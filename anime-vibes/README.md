# VIBE EDITING: a 40 s anime short in eight anime styles

**Watch:** [`out/vibe_editing_anime.mp4`](out/vibe_editing_anime.mp4) (1920×1080, 16:9, 24 fps, 40 s, narrated, with score)

Kai is a burnt-out editor buried under a thousand clips. A glowing spirit tells him to stop fighting the timeline
and just say the vibe. Kai powers up and shouts the prompt, the edit assembles itself, and the client cries
tears of joy. Every shot uses a different anime style, and a corner tag names each one. All the drawing, music
and sound effects are generated in code, so there are no stock assets or AI images.

## The eight styles

| Time | Style | Narration | Picture |
|---|---|---|---|
| 0–5.6 s | **01 Cinematic** | "In a world drowning in footage... one editor stood alone." | A neon city at night with rain, a moon and parallax skyline. Neon kana signs flicker as video clips fall out of the sky with the rain. Then an over-the-shoulder shot of Kai at 3:47 AM, rim-lit by a chaotic timeline full of warnings. |
| 5.6–10.4 s | **02 Manga** | "Deadline: tomorrow. Clips: one thousand. Sleep: zero." | Black-and-white manga panels with halftone screentone slam in one per line. A calendar with the date circled in red, a monitor counting up to 1,000 clips that burst out of the panel, and an extreme close-up of Kai's bloodshot eyes with ゴゴゴ. |
| 10.4–14.8 s | **03 Chibi** | "Three days of cutting and keyframing... and his soul left his body." | Super-deformed Kai cries waterfall tears while the DAY 1 → 2 → 3 pages tear off. On "soul", the classic ghost floats out of his mouth to a チーン bell. |
| 14.8–19.6 s | **04 Fantasy** | Spirit: "Stop fighting the timeline, Kai. Just tell me the vibe." | A pastel sky with god rays and clouds. The cat-eared Vibe spirit descends inside a rotating magic circle, and Kai looks up with sparkling eyes. A prompt bar types "describe your vibe...". |
| 19.6–25.6 s | **05 Shōnen** | Kai: "Make it epic! Emotional! On the beat! Vibe... EDIT!" | A power-up: focus lines, flaring aura, rocks floating up, hair lifting and eyes turning gold. Each word slams in as kinetic type. Then an extreme close-up of his eyes, a black/white **impact frame** with ドンッ!, and a shockwave that blasts the clips outward under "VIBE EDIT!!". |
| 25.6–30.4 s | **06 Mecha** | "Cuts. Color. Captions. Music. Synced in seconds." | A cockpit HUD. Each module locks in on its word: clips fly onto the timeline, the preview is colour-graded from flat to vivid, captions appear and the audio waveform fills. A シンクロ率 meter climbs to 100% and a **SYNCED** stamp lands. |
| 30.4–35.2 s | **07 Shōjo** | Client: "Sugoi!" / "Even the client cried." | A pink bokeh background with roses, petals and sparkles. The client's starry eyes fill with tears of joy as すごい!! pops in, and chibi Kai peeks in with a V-sign. |
| 35.2–40 s | **08 Opening** | "Vibe Editing. Say the vibe... watch it come alive." | A sunset end card in the style of an anime opening: a striped retro sun, a giant バイブ編集 behind, and Kai and the spirit silhouetted on a hill. The **VIBE / EDITING** title slams in with a light sweep, followed by the tagline and "by IDEABRO STUDIO". |

## Look

- **Cel shading:** flat base colours with hard-edged shadow shapes clipped to each part, and ink outlines.
  Characters (`chars.py`) are vector rigs with expression controls: eye moods (normal, determined, sparkle,
  tired, happy, shock), brows, mouths (smile, shout, grin, o, wavy), blush, sweat drops, tear streams, hair
  lift for the power-up and a gold iris glow.
- **On twos:** character animation is stepped at 12 drawings a second, like TV anime, while camera moves,
  effects and type run at 24 fps.
- **Anime vocabulary:** manga focus lines redrawn 12 times a second, halftone screentone (a 45° dot lattice
  shader), an inverted impact frame, kana sound effects (ドクン, ゴゴゴ, チーン, ドンッ), fansub-style
  subtitles, cut flashes and a speed-line whip pan.
- Fonts (OFL, Google Fonts): Bangers, Dela Gothic One, Mochiy Pop One, Zen Dots and Orbitron.

## Sound

- **Narration** is [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) TTS, run locally, with a cast of four:
  - `am_onyx`: a deep anime-trailer narrator.
  - `am_puck`: Kai. His "EDIT!" gets a slap echo.
  - `af_sky`: the spirit, with a long, bright reverb.
  - `jf_alpha`: the client. Her Japanese "Sugoi!" uses hand-written phonemes.

  Each phrase is its own take, placed on a cue in `timeline.py` so the pauses land like a trailer.
- **Score** (`audio.py`) is 150 BPM in A minor (Am–F–C–G), and every cut sits on the beat grid. It is scored
  per genre:
  - Rain and a piano arpeggio for the cinematic open.
  - A tense string ostinato, a ticking clock and heartbeats under the manga.
  - Bouncy xylophone, boings and a wah-wah trombone for the chibi gag.
  - Harp, celesta and pads for the spirit.
  - A snare roll and riser for the power-up, then 80 ms of silence before the impact.
  - A full J-rock band from the impact to the end: detuned, distorted power-chord synths, bass eighths, drums
    and a lead. Glockenspiel sparkles come in for the shōjo scene.
- **SFX:** orchestral stabs, booms, crashes, whooshes, the rin bell, HUD blips, a sword "shing" and sparkle
  glisses. The music ducks about 10 dB under the voice. The mix is loudness-normalised to −14 LUFS with a
  −1.5 dBTP ceiling.

## Build

```bash
pip install skia-python numpy scipy soundfile kokoro-onnx pillow     # plus ffmpeg on PATH
# Kokoro model files -> /home/user/models (or set MODELS=...)
#   https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
#   https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
python3 build.py                        # -> out/vibe_editing_anime.mp4  (~2 min on 4 cores)
python3 video.py stills 9.8 23.65 29.9  # preview PNGs -> work/stills/
```

| File | Contents |
|---|---|
| `timeline.py` | Scene cuts, style tags and every narration cue, shared by picture and sound |
| `anime.py` | The engine: skia paint and path helpers, gradients, outlined type, screentone, focus lines, sparkles, easing |
| `chars.py` | Kai (front bust, back view, chibi), the client, the soul ghost and the Vibe spirit |
| `scenes.py` | The eight shots, subtitles, style tags and transitions |
| `narration.py` | Script and TTS |
| `audio.py` | Score, SFX and the mix |
| `video.py` | Multiprocess frame renderer piped into ffmpeg |
