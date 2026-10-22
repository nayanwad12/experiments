# Vibe Editing System ad: paper-sticker talking-head reel

One raw phone take in (82 s, 720×1280 HEVC, 60 fps). Two files out:
`out/vibe_editing_reel.mp4` (the finished 1080×1920 / 30 fps reel, about 72 s) and `out/vibe_editing_comparison.mp4`
(the raw take beside the edit, in sync with the final audio).

**Look:** built from the reference collage: ruled notebook paper (cream, faded blue rules, red margin, punched
holes), everything cut out as a paper sticker (white die-cut border and soft shadow, the speaker included), black
DM Serif Display for the plain words, pink Playfair Display Black Italic with a dark outline for the key words,
Courier Prime for typed labels, Caveat for handwriting. Accent colours come from the reference stickers: taxi
yellow and net-bag red. The reference's own photos, brands and logos are not used. Every sticker is drawn in code,
and the editing apps are named in words only, with no logos.

## What was said (raw clock)

| part | time | line |
| --- | --- | --- |
| hook | 0.5–3.5 | Video editing just changed, and most people haven't noticed yet. |
| problem | 3.9–12.4 | For years, editing meant one thing. Sit in front of timeline, drag clips, set keyframes, and spend six hours on a 60-second reel. |
| solution | 13.0–22.0 | Vibe editing flips that. You don't edit anymore. You direct. You tell the system what you want, the same way you'd brief a top editor: |
| proof (demo) | 22.5–40.2 | Cut the pauses. Make the captions punchy. Put the title behind me. Give it a cinematic look. Add music that builds. And it builds it. Every cut, every caption, every effect, every sound, made in code, right on your laptop. |
| range | 41.8–53.5 | And it's not just reels. The same system makes motion graphics, product ads, claymation, VFX, podcast clips, even 50 versions of one ad, so you can test what works. |
| offer | 56.8–72.1 | So what do you actually need? Your footage, your laptop, and the Vibe Editing System. The editing skills, plus a full course that shows you how to direct every one of them. No After Effects. No Premiere Pro. No keyframes. |
| twist | 72.5–79.7 | And this video you just watched? I didn't open a single editing app. I recorded it on my phone, and the system did the rest. |

Cut from the take: three false starts ("Put the ti-" at 25.9, "And it's sh-" at 40.8, the retake
"So what do you need actually" at 54.0) and every pause longer than a breath. That removes 11.3 s, with 17 jump cuts.
No "um"/"uh" fillers were found in this take. The CTA is not spoken; the end card carries it ("Comment VIBE").

## Pipeline

| step | file | what it does |
| --- | --- | --- |
| ears | `transcribe.py` | Silero VAD + Whisper turbo (sherpa-onnx) → phrase text and times |
| ears | `align.py` | pocketsphinx forced alignment of the hand-checked text → `work/words.json` (every word, false starts included) |
| eyes | `matte.py` | 1080×1920 frames + RobustVideoMatting (resnet50) person matte |
| edit | `cut.py` | the cut list: pauses trimmed to a breath, false starts removed, a 0.54 s held beat for the drop |
| look | `theme.py` | paper textures, the sticker filter, caption type styles, hand-made marks |
| picture | `edit.py` | 15 sections, each with its own page and graphics, all cued to the words; captions behind the speaker |
| sound | `soundtrack.py` | voice clean-up (de-noise, EQ, compression, de-ess), original 100 BPM score with its drop on the beat, 283 SFX cues, −14 LUFS |
| compare | `compare.py` | raw vs edit side by side with live counters and the raw timeline strip |

```bash
cp <take>.mp4 raw/take.mp4
ffmpeg -i raw/take.mp4 -ac 1 -ar 16000 -c:a pcm_s16le work/audio16k.wav
ffmpeg -i raw/take.mp4 -vn -c:a pcm_s24le -ar 48000 work/voice_raw.wav
python3 transcribe.py && python3 align.py && python3 matte.py
python3 cut.py                    # print the cut list
python3 edit.py stills 2.6 24.8   # check frames (half res)
python3 edit.py render            # -> out/vibe_editing_reel.mp4
python3 compare.py render         # -> out/vibe_editing_comparison.mp4
```

Models (GitHub release assets, in `/home/user/models`): `sherpa-onnx-whisper-turbo`, `silero_vad.onnx`,
`rvm_resnet50_fp32.onnx`. Raw footage, model outputs and renders stay out of git.
