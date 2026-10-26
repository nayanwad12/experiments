# vibe-40-ad: the Meta-ad version of the 40 s "my system edited this" take

Fresh full take (39.8 s, 720x1280 HEVC 60 fps) with the ad CTA: "So if you want to learn my system, tap the
link below." Same pipeline and look as `../vibe-40` (creator-tutorial format, pauses trimmed, 1.15x), with:

- ending: WANT TO LEARN / **MY SYSTEM?** -> TAP THE LINK BELOW / **LEARN MORE** + arrow and chevrons down
  at the ad button (no comment / DM card)
- Meta Reels-ad safe zone: subtitles and the caption demo sit at y 1238, under the chin and above the bottom
  35 % that the ad caption and CTA button cover; nothing in the top 14 %
- this take is framed closer (bigger face), so the footage drop is smaller (BASE_DY 75) and the hook's
  floating UI pieces are left out

Run exactly as in `../vibe-40/README.md`; outputs `out/vibe40_ad.mp4` and `out/vibe40_ad_comparison.mp4`.

## Diary style (second reference)

`diary.py` re-edits the same take in the cozy film-diary look of the second reference clip: every spoken
word in a soft condensed serif (Fraunces Soft, butter #F6F39D) dropped into its own spot around the speaker
and built up phrase by phrase; scrapbook stickers whose word swaps (envelope with ribbon + hand-drawn stars,
lined note, cassette, taped polaroids); warm lamp-lit grade, bloom, halation, grain; jump-cut zooms.
`python3 diary.py render` -> `out/vibe40_diary.mp4`; `python3 compare_diary.py render` -> `out/vibe40_diary_comparison.mp4`.

## Scribble style (third reference)

`scribble.py` re-edits the same take in the "hand-made text / retro computer" creator style: fisheye opening
with a black ring, punchy cool grade, ONE white condensed word at a time (Bebas Neue), two-tier titles with a
big hand-drawn marker word (Permanent Marker, red #EE4B20 / yellow #F9D514) written on letter by letter with a
stop-motion boil (yellow ones behind the head), split screens with the speaker in a rounded card over a
retro desktop (system-message dialogs in blue handwriting, media player, MS-DOS export) or a light canvas
with royal-blue UI (#2553C6). `python3 scribble.py render` -> `out/vibe40_scribble.mp4`;
`python3 compare_scribble.py render` -> `out/vibe40_scribble_comparison.mp4`.
