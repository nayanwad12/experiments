# Troubleshooting Guide

| problem | ask Claude / do this |
|---|---|
| `python3` not found (Windows) | "use py instead of python3" |
| "externally managed environment" | "set up a virtual environment and re-run the doctor" |
| ffmpeg not found | "run the doctor with --install" (it installs a bundled ffmpeg) |
| skills not showing in `/skills` | check the path: `~/.claude/skills/vibe-talking-head/SKILL.md` |
| first run very slow | normal: AI models download once |
| transcription misspells names | "re-transcribe with these names: …" or fix the transcript |
| captions in the wrong font | "download the brand fonts and re-burn captions" |
| captions out of sync | "use the re-timed words file from the cut, not the raw one" |
| phone video sideways | "fix the rotation of raw/take1.mp4" |
| clicks at cuts | "add short audio fades at every cut" |
| music too loud | "music 4 dB quieter and duck more under my voice" |
| render too slow | "render a draft" / "render only 0:10–0:15" |
| out of memory | "process this shot in parts" |
| video won't play on phone | always deliver files from the export step |
| text looks blurry | render at final size; never upscale a draft |
| cut-out edges rough | "use the high-quality matte model" and better lighting next time |

## Still stuck?
Post in the community with: what you asked, what happened (screenshot of the error), your OS. Someone will help fast.
