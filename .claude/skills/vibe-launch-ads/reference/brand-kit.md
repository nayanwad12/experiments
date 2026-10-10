# Brand kit and layout rules

## Ideabro house style (the default when the user has no brand)

| role | colour | hex |
|---|---|---|
| `fg` / ink | near-black | `#0B0B0D` |
| `bg` / paper | warm off-white | `#F2EEE3` |
| `accent` / lime | **signature** | `#D4FF3F` |
| `accent2` / periwinkle | soft accent | `#C4C6FF` |
| blush | soft accent | `#FFCFD8` |
| ice | soft accent | `#C8F0EC` |
| orange | alert / energy | `#FF5A1F` |
| `caption` / `caption_hi` | white / lime | `#FFFFFF` / `#D4FF3F` |

| role | font (Google Fonts, OFL) | use |
|---|---|---|
| `display` | **Unbounded 900** | titles, hooks, end cards |
| `impact` | **Anton** | captions, big condensed words |
| `body` | **Inter Tight 400/700** | subtitles, paragraphs, UI |
| `mono` | **JetBrains Mono 700** | labels, chips, tags, CTAs (UPPERCASE, tracked +0.12–0.2 em) |
| `serif` | **Instrument Serif** | elegant accents, quotes, "documentary" titles |

Tagline: *Direct the vibe. Let AI do the keyframes.*  Credit line: *by Ideabro Studio*.
Look: ink-on-paper, generous negative space, one lime highlight per screen, rounded pills, bold type.

**Credit policy:** student and client work uses the client's brand. The Ideabro credit appears only when the user asks
(course projects, portfolio pieces, Ideabro promos).

## brand.json (per project)

```json
{
  "name": "Client Co",
  "tagline": "Short line for end cards",
  "colors": {"ink": "#101820", "paper": "#FFFFFF", "lime": "#FF6B00", "periwinkle": "#9AD0EC"},
  "roles":  {"bg": "paper", "fg": "ink", "accent": "lime", "accent2": "periwinkle", "caption": "paper", "caption_hi": "lime"},
  "fonts":  {"display": "Poppins:800", "impact": "Bebas Neue", "body": "Inter:400,700", "mono": "Space Mono:700", "serif": "Playfair Display:400"}
}
```
Keep the **role names**. Every script resolves colours through roles, so swapping a brand is a one-file change.
After editing fonts run `python3 vibe/fonts.py --brand`.

Getting a client's brand: ask for the hex codes and font names. Failing that, pull the colours from their logo or website
screenshot (sample the pixels with Pillow) and pick the closest Google Fonts. Confirm with the user.

## Typography rules

- Max **2 typefaces** on screen at once (display + body/mono).
- Hooks: 3–6 words, very big (cap height ≥ 7 % of the short side), high contrast.
- On-screen reading time: about 0.3 s per word + 0.5 s. Never shorter than 1 s for a line.
- Auto-fit long text: measure with `text_width()` and scale down; never let text touch the frame edge
  (keep ≥ 8 % side margins).
- UPPERCASE + tracking for labels; sentence case for anything longer than 6 words.
- Contrast: text on footage needs an outline, a shadow, a pill, or a darkened area behind it.

## Safe zones (keep text and faces inside)

| format | keep clear |
|---|---|
| 9:16 Reels / TikTok / Shorts (1080×1920) | top 250 px, bottom 420 px, right 140 px (buttons) |
| 1:1 / 4:5 feed | 6 % all round |
| 16:9 YouTube | 5 % all round, bottom-right 20 % × 15 % during the last 20 s (end screens) |

## Layout grid

Use a unit `U = min(W, H) / 1080` and size everything in `U`. The same scene then works at 1080p, 4K, 9:16 and 16:9.
Centre-weighted for vertical; rule-of-thirds for horizontal. Leave room for captions in the lower third of talking
heads.

## End card

The logo or wordmark, a single CTA (in a pill), a handle or URL. Hold for at least 2 s. In vertical video keep the CTA above
the bottom safe zone.
