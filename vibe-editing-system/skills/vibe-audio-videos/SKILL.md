---
name: vibe-audio-videos
description: Ideabro Studio Vibe Editing System - audio-led videos and sound design in code. Use when the user wants original copyright-free music or a soundtrack for a video, sound effects, a voiceover (recorded clean-up or local AI text-to-speech, including Hindi voices), an audiogram (podcast audio + waveform + captions + cover art), a music visualiser, a lyric or quote-over-music video, beat-synced edits where every cut lands on the music, or a mix that ducks music under voice and hits platform loudness. Also when asked to fix, clean, level or replace the audio of an existing video. Triggers on "music", "soundtrack", "sound effects", "SFX", "voiceover", "text to speech", "AI voice", "audiogram", "podcast clip with waveform", "visualizer", "beat sync", "cut to the beat", "fix the audio", "too loud", "copyright music".
---

# Audio-Led Videos & Sound Design
*Ideabro Studio · Vibe Editing System — direct the vibe, let AI do the keyframes.*

Sound is half of every video. Everything here is generated or processed locally: original music beds, SFX, AI
voiceovers, clean-ups and mixes. It is copyright-safe, so no Content ID claims. Picture is driven by the audio:
waveforms, beats and words.

Paths below are relative to **this skill's folder**: `scripts/`, `reference/`, `templates/`.

## What you can make here

| type | default |
|---|---|
| **Soundtrack for any video** | mood bed sized to the video, SFX on its cuts, ducking, −14 LUFS, muxed back |
| **AI voiceover** | Kokoro TTS line by line, cleaned, with per-line timings (+ word timings via Whisper) |
| **Voice clean-up / audio fix** | high-pass, denoise, compression, de-ess, loudness; replace bad music |
| **Audiogram** | 1:1 or 9:16, cover art/photo, animated waveform, pop/karaoke captions, title + episode, progress bar |
| **Music visualiser** | spectrum bars / circle / particles driven by the audio (FFT per frame), title, loopable |
| **Beat-synced edit** | detect beats → cut clips/photos on beats (assemble.py with beat-length shots) |
| **Lyric / quote video** | words appear on the vocal (`words.json`) over a moving background |

## Step 0: Setup (first time in a project)

1. `python3 scripts/doctor.py --kit audio --install` (Windows: `py`)
2. `python3 scripts/new_project.py <name> --kind audio --format 1:1 --fps 30` and work in it.

## Toolkit

```bash
python3 vibe/audio_kit.py bed --mood upbeat --seconds 30 -o work/music.wav      # moods: upbeat hype tech corporate chill cinematic playful
python3 vibe/audio_kit.py bed --mood chill --bpm 84 --key A --seed 4 -o work/music_b.wav   # variation
python3 vibe/audio_kit.py sfx --list                                              # whoosh pop click typing impact riser ...
python3 vibe/audio_kit.py voice raw/take.mp4 -o work/voice.wav --denoise          # clean a recorded voice
python3 vibe/tts.py --script work/script.txt -o work/vo.wav --voice af_heart       # AI voiceover (+ vo.json timings)
python3 vibe/tts.py --list                                                        # all voices (en-US/UK, Hindi, ES, FR, IT, PT, JA, ZH)
python3 vibe/transcribe.py work/vo.wav -o work/words.json                         # word timings for captions/cues
python3 vibe/audio_kit.py mix work/cues.json -o work/mix.wav --video in.mp4 --out-video out/final.mp4
```
Mixing rules and levels: `reference/sound-design.md`.

## Step 1: Brief

Ask: what the audio is for (new soundtrack / VO / fix / audiogram / visualiser) · mood words + references *(e.g. "warm lo-fi")*
· length (or the video to fit) · voice: their recording or AI (which voice, language, pace) · platform *(−14 LUFS social, −16 podcast/web)*.

## Recipes

**Soundtrack an existing video.** `stills.py` + `probe` the video → choose a mood + BPM → make the bed `--seconds <dur>` →
list the video's cuts (`clipscan.py` gives cut times) and put whooshes 0.3 s before them, impacts on reveals → `cues.json`
with `"voice": {"file": "work/voice.wav"}` if there's speech (extract with `audio_kit.py voice video.mp4`) → mix with
`--video`. If the video's cuts should land on the beat instead, re-cut it (`assemble.py` with shot `dur` = multiples of the beat).

**AI voiceover.** Write the script as spoken: short sentences, numbers in words, acronyms spelled ("A.I."). One line per
take in `work/script.txt` (`id | voice | speed | text`). Speed 0.95–1.1. Listen-check the timing via `vo.json`; regenerate
single lines by id. Run `audio_kit.py voice work/vo.wav -o work/vo_clean.wav` for a broadcast feel.

**Audiogram** (motion_kit scene):
```python
import sys; sys.path.insert(0, "vibe")
from motion_kit import *; import audio_kit as ak, numpy as np
A = ak.read_audio("work/clip.wav").mean(1); SR = ak.SR
def level(t, win=0.05):                        # loudness at time t (0..1)
    i = int(t*SR); seg = A[max(0, i-int(win*SR)//2): i+int(win*SR)//2]
    return float(min(1, np.sqrt((seg**2).mean() + 1e-9) * 6)) if len(seg) else 0.0
def spectrum(t, bands=32, n=2048):            # per-band energy for bars/circles
    i = int(t*SR); seg = A[i:i+n]
    if len(seg) < n: return np.zeros(bands)
    mag = np.abs(np.fft.rfft(seg * np.hanning(n)))[1:]
    edges = np.geomspace(1, len(mag), bands + 1).astype(int)
    return np.clip(np.log1p([mag[a:max(a+1, b)].mean() for a, b in zip(edges[:-1], edges[1:])]) / 6, 0, 1)
```
Layout: cover art/photo (`draw_image`), show + episode title (display font), waveform bars from `spectrum(t)`. To
smooth them, average `spectrum` over `t-0.03 … t+0.03`. Frames are stateless, so never keep a running average.
captions burned after with `captions.py --style karaoke`, a progress bar `lt/dur`. Export `square` and `reels`.

**Music visualiser.** Same `spectrum(t)`: radial bars around the logo, bass (`bands[0:3]`) drives a scale pulse and
a flash, particles emitted on kicks (detect: bass energy jump > threshold, precompute kick times once at load).
Loop: make the visual period divide the track length.

**Beat-synced photo/clip montage.** Beat = 60/BPM (known for audio_kit beds; for user music estimate the BPM from the
onset envelope's autocorrelation, or ask). Shots of 1, 2 or 4 beats via `assemble.py` (`"dur": beat*2`), hard cuts, speed
ramps on drops.

**Fix the audio of a video.** `audio_kit.py voice video.mp4 -o work/voice.wav --denoise` → (optional new bed) →
`mix` with `--video video.mp4` → `export.py` (loudness). For harsh room echo, suggest re-recording; heavy dereverb isn't in
this toolkit.

## Quality bar

- [ ] Voice intelligible over everything (music ducked 8–14 dB under speech)
- [ ] No clipping; final loudness −14 LUFS social / −16 podcast-web (export.py/mix measure it)
- [ ] Music starts and ends musically (fade or a hit on the last bar), never chopped mid-note at a random point
- [ ] SFX placed on exact frames (check with stills at those times), not overused
- [ ] Every piece of audio is original (audio_kit), user-owned, or licensed, and noted in `work/revisions.md`

## Reference
`reference/sound-design.md` (moods, BPM math, SFX, levels, licensing) · `reference/foundations.md` ·
`reference/motion-principles.md` · `reference/export-specs.md` · `reference/troubleshooting.md`
