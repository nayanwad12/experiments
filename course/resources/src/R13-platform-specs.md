# Platform Export Specs & Safe Zones

| platform | size | aspect | notes |
|---|---|---|---|
| Instagram Reels | 1080×1920 | 9:16 | under 60 s often performs best; first 2 s decide |
| TikTok | 1080×1920 | 9:16 | captions essential |
| YouTube Shorts | 1080×1920 | 9:16 | ≤ 3 min |
| YouTube | 1920×1080 (or 4K) | 16:9 | chapters, .srt, custom thumbnail |
| Instagram / LinkedIn feed | 1080×1350 | 4:5 | takes the most feed space |
| Square / carousel | 1080×1080 | 1:1 | ads, carousels |
| LinkedIn / X | 1920×1080 | 16:9 | X non-premium ≤ 2:20 |
| WhatsApp | 720×1280 | 9:16 | small file |
| Website hero | 1920×1080 | 16:9 | light bitrate, muted autoplay |
| Master / archive | source | — | ProRes 422 HQ + PCM |

All exports: H.264, AAC 48 kHz, −14 LUFS, fast-start, done by one command:
> Export for Reels, Shorts and YouTube.

## Safe zones (keep text & faces inside)
| format | keep clear |
|---|---|
| 9:16 | top 250 px · bottom 420 px · right 140 px |
| 4:5 / 1:1 | 6% all round |
| 16:9 | 5% all round · bottom-right corner in the last 20 s (end screens) |

## Changing aspect ratio
| method | when |
|---|---|
| crop (anchor on face) | talking heads |
| blur background | wide shots → vertical |
| pad (brand colour bars) | graphics that must stay whole |
| re-design per format | best quality for motion graphics |
