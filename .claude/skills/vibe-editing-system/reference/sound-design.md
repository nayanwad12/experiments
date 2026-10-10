# Sound design and music

Sound is half the video. All of it can be generated with `audio_kit.py`. It is original, so there are no copyright claims.

## Music beds

```bash
python3 vibe/audio_kit.py bed --mood hype --seconds 30 -o work/music.wav
python3 vibe/audio_kit.py bed --mood chill --bpm 84 --key A --seed 3 -o work/music.wav   # new variation
```

| mood | BPM | feel | good for |
|---|---|---|---|
| upbeat | 118 | major, plucks, four-on-floor | creators, launches, tutorials |
| hype | 128 | minor, pumping side-chain | ads, reveals, sports, showreels |
| tech | 124 | minor, driving | SaaS, AI, product demos |
| corporate | 110 | major, light | brand, explainer, LinkedIn |
| chill | 84 | lo-fi, 7th chords | vlogs, study, calm talking heads |
| cinematic | 72 | minor pads, pulses, hits | brand films, documentaries, trailers |
| playful | 120 | glockenspiel, bouncy | kids, food, fun explainers |

`--seed` gives a different variation of the same mood. `--intro-bars 2` holds the drums back for a build.

## Timing math (put it in timeline.py)

```
beat = 60 / BPM        bar = 4 beats        e.g. 128 BPM: beat 0.469 s, bar 1.875 s, 30 s = 16 bars
```
- Cut on the downbeat (bar starts). Use beats for small hits, pops and text slams.
- Choose the BPM so the video length is a whole number of bars when possible.
- Hook in the first bar; reveal on a bar line; end card on the last 2 bars.

## SFX vocabulary (`audio_kit.py sfx --list`)

| sfx | use |
|---|---|
| `whoosh` / `swish` | transitions, fast moves (start them ~0.3 s **before** the cut) |
| `pop` | text/sticker/chip appears |
| `click` / `typing` | UI, prompts, buttons |
| `tick` | timers, counters |
| `impact` / `bass_drop` | title slams, reveals, hook hit |
| `riser` / `downlifter` | build into / out of a big moment |
| `sparkle` / `ding` | magic, success, notification |
| `glitch` | errors, digital transitions |
| `shutter` | photos, screenshots, freeze frames |

Levels (in cues.json): SFX −6 to −12 dB, music −8 to −12 dB under voice, impacts up to −3 dB.
Don't put an SFX on everything. Accent 3–6 key moments per 30 s.

## Voice

- Recorded voice: `audio_kit.py voice raw/take.mp4 -o work/voice.wav --denoise` (high-pass, de-noise,
  compression, de-esser).
- AI voice: `tts.py --script work/script.txt --voice af_heart` (Hindi: `hf_alpha`, `hm_omega`).
  Write numbers and acronyms as spoken ("A.I.", "twenty twenty-six"). Short sentences sound most natural.
- Cue animation to words: run `transcribe.py work/vo.wav` and read `words.json`.

## The mix (`audio_kit.py mix work/cues.json`)

```json
{"duration": 30,
 "voice": {"file": "work/voice.wav"},
 "music": {"file": "work/music.wav", "gain_db": -9, "duck_db": -10, "fade_out": 1.5},
 "sfx": [{"t": 0.0, "kind": "impact", "gain_db": -3}, {"t": 3.45, "kind": "whoosh", "gain_db": -9}]}
```
- Ducking pulls the music down automatically while someone speaks.
- The final mix is loudness-normalised (−14 LUFS social; use `--lufs -16` for podcasts/web).
- Generate the cues from `timeline.py` (`TL.cues()`), so picture and sound never drift apart.

## Licensing

audio_kit music/SFX: original, yours to use commercially. Kokoro voices: Apache-2.0. For a client's own track, use the licensed
file only (put it in `assets/`), and ask about rights. Never pull music from YouTube/Spotify/TikTok libraries into a
deliverable.
