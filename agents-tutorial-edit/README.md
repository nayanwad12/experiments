# Agents tutorial: final cut for the LMS

A 16:36 raw OBS screen recording, edited into a clean 8:40 lesson plus 5 short lessons, ready to upload.
1920×1080, 30 fps, H.264 + AAC 192 kbps, voice loudness-normalised to −16 LUFS, `+faststart`.

| # | Lesson | Length | Starts in full cut |
| --- | --- | --- | --- |
| 01 | Introduction: What the Agent Skills Can Do | 0:57 | 0:00 |
| 02 | Installing the Vibe Editing System Skill | 0:38 | 0:57 |
| 03 | Editing a Talking-Head Video | 2:54 | 1:35 |
| 04 | Creating a Launch Ad and Combining Skills | 2:20 | 4:29 |
| 05 | The Results and Blocked Websites | 1:50 | 6:50 |

The full cut is just the five lessons back to back, with a short dip to black between them. The table's
"starts" column works as chapter markers if your LMS supports them.

## What was removed

- **OBS**: every frame of the OBS window, including the macOS desktop swipe into and out of it (start, 1:14,
  4:19, 4:49, 5:00, 5:31, 11:22, 12:36, 14:07, end). Where you were already talking over an OBS frame (the
  first 3 s, and 5:31) a clean frame of the page you were on is held under the audio.
- **Repeats and false starts**: e.g. "this is the video, this is the video", "suppose you want to create a video
  like this" ×2, "this is the starting point" ×3, "let me create another" ×2, "with the message, with the
  message", "similarly similarly", the miscount "one two three seven eight", restarts of sentences.
- **Mutters while typing** the H&M prompt (unclear audio); the dictated lines that are readable on screen
  ("add big kinetic captions", "follow the theme of the website") are kept.
- **Dead air**: silent navigation and waiting; pauses longer than 0.45 s inside sentences are tightened.
- **Off-topic screen**: a blank Google new tab (13:44 raw) is covered with the Claude chat showing the finished reel.
- **Duplicates**: the finished reel played a second time (14:57 raw) and the second explanation of the H&M
  block. The useful tip from it (screenshot the products and let Claude cut them out) is kept.
- **Levels**: the finished reels play back as system audio about 20 dB louder than the mic; they are brought
  level with your voice.

Every cut is listed with its reason in `edl.py`.

## Pipeline

| step | file | what it does |
| --- | --- | --- |
| ears | `asr.py` | Silero VAD + Whisper turbo (sherpa-onnx) → `segs.json` |
| ears | `align.py` | pocketsphinx forced alignment per segment → `words.json` (time of every word) |
| edit | `edl.py` | the edit: kept ranges by word, grouped into lessons, every cut commented |
| edit | `obs.json` | OBS windows + desktop swipes to hide (optional 3rd value = frame to hold instead) |
| edit | `build.py` | pads to word edges, trims long pauses, snaps to the 30 fps grid → `timeline.json` |
| sound | `render_audio.py` | sample-exact cuts with micro-fades, playback levelled, high-pass + denoise + 2-pass loudnorm |
| picture | `render_video.py` | decodes the source once, writes exactly the kept frames (holds over OBS) → x264, muxed |
| check | `asr_file.py` | re-transcribes each finished lesson to proof-read the edit |

```bash
# models in /home/user/models: sherpa-onnx-whisper-turbo, silero_vad.onnx (GitHub release assets)
mkdir -p raw out && cp <recording>.mp4 raw/raw.mp4
ffmpeg -i raw/raw.mp4 -vn -ac 1 -ar 16000 audio16k.wav && ffmpeg -i raw/raw.mp4 -vn -ar 48000 audio48k.wav
python3 asr.py turbo && python3 align.py segs.json      # asr.py prints segments; segs.json is parsed from its log
python3 build.py && python3 render_audio.py && python3 render_video.py
```

The finished videos are in `final/`. Raw footage and intermediate audio stay out of git.
