# Brand Kit Template
One file (`brand.json`) re-skins every video. Fill in the client's values; keep the role names.

## Fill in
| role | used for | client value |
|---|---|---|
| bg | backgrounds | #______ |
| fg | text, outlines | #______ |
| accent | highlights, CTAs, caption highlight | #______ |
| accent2 | secondary shapes, chips | #______ |
| caption | caption text | #______ |
| display font | titles, hooks | ______ |
| impact font | captions, big words | ______ |
| body font | subtitles, paragraphs | ______ |
| mono font | labels, CTAs | ______ |
| logo | transparent PNG or SVG | ______ |
| tagline / handle / URL | end cards | ______ |

## brand.json
```
{
  "name": "Client Co",
  "tagline": "Short end-card line",
  "colors": {"ink": "#101820", "paper": "#FFFFFF", "lime": "#FF6B00", "periwinkle": "#9AD0EC"},
  "roles":  {"bg": "paper", "fg": "ink", "accent": "lime", "accent2": "periwinkle", "caption": "paper", "caption_hi": "lime"},
  "fonts":  {"display": "Poppins:800", "impact": "Bebas Neue", "body": "Inter:400,700", "mono": "Space Mono:700", "serif": "Playfair Display:400"}
}
```
Prompt: *"Set up this brand from the client's logo and website colours, pick the closest Google Fonts, and show me a test frame."*

## The Ideabro house style (default)
ink **#0B0B0D** · paper **#F2EEE3** · signature lime **#D4FF3F** · periwinkle **#C4C6FF** · blush **#FFCFD8** · ice **#C8F0EC**
Fonts: Unbounded 900 · Anton · Inter Tight · JetBrains Mono · Instrument Serif

## Rules
- Max 2 typefaces per screen. One accent per screen.
- Logo never stretched, always crisp, on a clean area.
- Text ≥ 8% from the frame edges.
