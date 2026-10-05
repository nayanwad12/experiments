# Export specs (handled by `export.py`)

```bash
python3 vibe/export.py out/final_v1.mp4 --preset reels,youtube,square --fit blur
```

| preset | size | notes |
|---|---|---|
| `reels` / `tiktok` | 1080×1920 | H.264 High, AAC 48 kHz, −14 LUFS. Under 60 s performs best; first 2 s decide everything |
| `shorts` | 1080×1920 | ≤ 3 min |
| `youtube` | 1920×1080 | up to 60 fps; add chapters in the description; custom thumbnail |
| `youtube-4k` | 3840×2160 | only when the source is 4K |
| `feed` | 1080×1350 | 4:5, Instagram/LinkedIn/Facebook feed, takes the most screen space |
| `square` | 1080×1080 | carousels, ads |
| `linkedin` / `x` | 1920×1080 | X non-premium ≤ 2:20 |
| `whatsapp` | 720×1280 | small file for sharing |
| `web` | 1920×1080 | lighter bitrate for landing pages / hero videos (consider muted autoplay) |
| `master` | source | ProRes 422 HQ + PCM. Archive copy or hand-off to other editors |

## Reframing between aspect ratios

| `--fit` | when |
|---|---|
| `crop` (default) | the subject is centred (talking heads). Use `--anchor 0.5,0.35` to keep the face |
| `blur` | wide shots, screen recordings, landscape → vertical without losing content |
| `pad` | graphics that must stay whole; bars in the brand ink colour |

Best results: design graphics natively per format (change `timeline.W/H` and re-render) rather than reframing.

## Captions and subtitles

- Burned-in captions (`captions.py --burn`) for social (most people watch muted).
- Also deliver the `.srt` for YouTube/LinkedIn (accessibility + SEO).

## Delivery checklist

- File names: `client_project_format_v2.mp4` (e.g. `ideabro_launch_reels_v2.mp4`)
- A contact sheet (`stills.py --count 12`) checked for each export
- A thumbnail/cover frame (pick a strong still: face + 3–5 big words)
- Licences noted (fonts, music source, footage)
