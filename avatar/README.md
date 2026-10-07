# avatar — talking video from one photo, free

One selfie + a voice clip → an MP4 of you talking. Runs on a plain CPU with open-source models
([SadTalker](https://github.com/OpenTalker/SadTalker) for the face, Kokoro for a placeholder voice).
No account, API key or subscription.

## Run it

```bash
./setup.sh                                   # once: Python 3.10 env + ~3 GB of models in ~/avatar-tools

# photo (HEIC from iPhone is fine, convert first)
python3 -c "from pillow_heif import register_heif_opener as r; r(); from PIL import Image, ImageOps; \
ImageOps.exif_transpose(Image.open('IMG.HEIC')).convert('RGB').save('input/me.jpg', quality=95)"

# voice: your own recording (best), or a generated one
python3 ../vibe-editing-system/shared/scripts/tts.py --script input/script.txt -o work/voice.wav --voice am_michael

./make_avatar.sh input/me.jpg work/voice.wav out/avatar.mp4
```

Knobs (env vars): `SIZE=256|512`, `ENHANCE=none|gfpgan`, `STILL=0` for more head motion,
`EXPR=1.3` for bigger expressions.

## Speed (4-core CPU, no GPU)

| setting | 15 s clip |
|---|---|
| `SIZE=256` (default) | ~27 min |
| `SIZE=256 ENHANCE=gfpgan` (sharper face) | ~70 min |
| `SIZE=512` | ~2 h |

A free Google Colab GPU runs the same scripts in a minute or two.

## Photo tips

Front-facing, even light, mouth closed, face not too small in frame. Glasses are fine.
`input/`, `work/` and `out/` are git-ignored so your face and voice stay out of the repo.
