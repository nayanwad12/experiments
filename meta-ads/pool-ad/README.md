# Pool ad: "This is my video editing setup" (Meta ad, 9:16)

Edited with the Vibe Editing System from two raw phone takes (77.2 s of footage) into a 34.8 s ad:
1080x1920, 30 fps, H.264 + AAC, -14 LUFS. Output: `out/pool_ad_v2.mp4`.

## What was cut and why
| from | kept | why |
|---|---|---|
| take 2 | hook → "...here's how it works", "...on my phone", "while I'm swimming... and it's done", CTA | clean background (no strangers), closer framing |
| take 1 | "told my system what I wanted, in one line. And came here." / "And this video you just watched? Same system. I didn't edit a single second of it." | take 2 stumbles on both lines |
| cut | take 1 ending (you walk off camera), take 2 retakes, a 0.6 s pause before "here's how it works", all dead air | |

## The edit, beat by beat
| time | what you see |
|---|---|
| 0–1.9 s | Zoom-out hook. Big text *behind* you: "this is my video / EDITING / SETUP." |
| 1.9–4.6 s | Paper to-do note: TODAY ☐ Edit videos ☐ Cut the pauses ☐ Add captions, ~5 hrs |
| 4.6–6.1 s | Note gets struck through and flies off. "I DON'T / EDIT." behind you |
| 6.1–8.0 s | Frosted-glass card rises over the water: VIBE EDITING SYSTEM · Editing video_014.mp4 |
| 8.0–15.4 s | **Full motion graphics (Vox style):** paper texture, live cut-out sticker of you, highlighter swipes. STEP 01 Record *one video* (phone with your clip playing) → STEP 02 Tell my system *what I want* (prompt types out, "just 1 line.") |
| 15.4–22 s | Paper tears away back to the pool, with a splash. A glass checklist ticks off on each word: pauses, mistakes, text, music, everything → 100% |
| 22–23 s | "DONE." behind you + phone notification: "Your video is ready." |
| 23–28 s | **Before / after:** RAW (straight from the phone, ungraded) next to FINAL. "MY EDITING TIME 00:00:00" |
| 28–31.9 s | CTA: comment box types "SYSTEM", huge "SYSTEM" behind you, "I'll DM you the details" |
| 31.9–34.8 s | Receipt end card with this video's real numbers + THE VIBE EDITING SYSTEM · Comment "SYSTEM" |

Framing stays above the chest: every shot is a face-centred crop that ends at the collarbones
(also the before/after panels, the paper sticker and the phone screen).

Captions sit **above your head**, not at the bottom: Meta's Reels ad UI covers the bottom ~35% of the screen.
All text stays inside the top 14% / bottom 35% safe zones, except the end-card CTA pill.

## Portfolio version
`out/pool_ad_portfolio.mp4`: the same ad playing inside a rounded card on a white dot-grid background, with a
bouncy "[AI] EDITED / *this video*" headline, sparkles and a "no timeline opened!" note. Everything sits inside the
Instagram Reels safe zone (top 250 px, bottom 420 px, ~60 px sides). Rebuild: `python3 portfolio.py render`.

## Sound
Your voice through a broadcast chain (EQ, compression, de-ess), an original future-bass track (drop when you
return to the pool, break for the before/after, second drop on "comment SYSTEM"), and SFX on every graphic: swishes,
pops, ticks, ding, splash, typing. Everything is synthesised, so there is nothing to license.

## Rebuild
```bash
python3 edl.py                    # pick lines from both takes -> work/a_roll.mp4, matte, voice, edl.json
python3 scene.py stills 1.5 9 22  # check frames
python3 scene.py render           # picture -> work/picture.mp4
python3 mixdown.py work/picture.mp4 out/pool_ad_v2.mp4
```
`raw/` (your footage) and `work/` are not committed. Transcripts use PocketSphinx forced alignment (the usual
Whisper model download is blocked in this environment), and the person matte uses MediaPipe's selfie segmenter.
