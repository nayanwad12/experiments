# Troubleshooting

| problem | fix |
|---|---|
| `ffmpeg not found` | `python3 -m pip install imageio-ffmpeg` (the scripts use it automatically) or install ffmpeg (`brew install ffmpeg`, `winget install Gyan.FFmpeg`, `sudo apt install ffmpeg`) |
| `No module named skia` | `python3 -m pip install skia-python`; Linux also `sudo apt install libegl1 libgl1` |
| `pip` refuses (externally managed env) | make a venv in the project: `python3 -m venv .venv && source .venv/bin/activate` (Windows: `.venv\Scripts\activate`), then run doctor again |
| Windows: `python3` not found | use `py` or `python` instead of `python3` in every command |
| Whisper is slow | `--model small` or `base`; on an NVIDIA GPU use `--model turbo` |
| Whisper misspells names | `--prompt "Ideabro, Priya Sharma, Vibe Editing"`, then fix words.json/transcript by hand |
| Captions show a different font | the font family name must match the TTF (`fonts.py` prints files); pass `--font "Anton"` and keep `--fonts-dir fonts` |
| Captions out of sync after cutting | use `work/words_cut.json` (re-timed) with the **cut** video, not the raw one |
| Phone video sideways / stretched | the scripts honour rotation metadata. If it's still wrong: `ffmpeg -i in.mp4 -vf transpose=1 work/rot.mp4` |
| Variable frame rate drift | `cut_silence.py` and `export.py` force a constant fps. For other tools first run `ffmpeg -i raw.mp4 -vf fps=30 -c:a copy work/cfr.mp4` |
| Audio clicks at cuts | cut_silence adds 12 ms fades; for custom cuts add `afade` in/out |
| Music too loud / voice buried | lower `music.gain_db` (−12) and/or `duck_db` (−14) in cues.json |
| Render very slow | stills → draft → final; cache images at module level; shorten the range with `start/end` |
| Out of memory | don't load long videos with `VideoFrames` at full res; pass `w, h` smaller or split the render |
| Kokoro download fails | download `kokoro-v1.0.onnx` and `voices-v1.0.bin` from the kokoro-onnx GitHub release into `~/.cache/ideabro-vibe/kokoro/` |
| rembg first run is slow | it downloads the model once (~170 MB). Use `--scale 0.5` for speed |
| Exported video won't play on phone | it must be H.264 yuv420p. Always deliver files from `export.py` |
| Text looks blurry | render at the final resolution; don't upscale drafts; keep text sizes in `U` units |
