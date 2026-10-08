# pool-ad: Vibe Editing project rules

Made with the **Ideabro Studio · Vibe Editing System**. Type: **vfx**, 9:16 (1080×1920) @ 30 fps.

## How we work (the Vibe Loop)
1. **Brief:** `brief.md` is filled in and the beat table is approved before any heavy work.
2. **Build:** timings live only in `timeline.py`, and picture and sound both read from it.
3. **Stills:** render check frames (`python3 scene.py stills …` or `python3 vibe/stills.py <video> --count 12`)
   and LOOK at the contact sheet with the Read tool before showing the user anything.
4. **Draft:** fast low-res render (`python3 scene.py draft`) for timing feedback.
5. **Final:** full render, then `python3 vibe/export.py out/<file>.mp4 --preset <platforms>`.
6. Log each round in `work/revisions.md` (what changed and why).

## Rules
- Never modify files in `raw/`. Write new files to `work/` (intermediate) or `out/` (deliverables).
- Never claim a render is done without checking stills of it.
- Brand: colours and fonts come from `brand.json`. Don't invent new colours.
- Text must sit inside the safe zone (9:16: keep 250 px clear at the top and 420 px at the bottom).
- Audio: voice is always on top. Music is ducked under the voice. Final loudness is -14 LUFS (export.py does it).
- Only use music, fonts, footage and images we have the rights to. audio_kit makes original music.
- Keep scripts deterministic (seeded randomness) so re-renders match.
- Before a long render, do a draft or a short range (`S.render(..., start=a, end=b)`).

## Toolkit (run from the project root)
| tool | does |
|---|---|
| `python3 vibe/doctor.py --kit vfx` | check / install dependencies |
| `python3 vibe/transcribe.py raw/x.mp4` | words with timestamps → work/words.json |
| `python3 vibe/cut_silence.py raw/x.mp4 --words work/words.json` | cut dead air, fillers, retakes |
| `python3 vibe/captions.py work/words_cut.json --video work/cut.mp4 --burn out/x.mp4` | animated captions |
| `python3 vibe/audio_kit.py bed / sfx / voice / mix` | music, SFX, voice clean-up, mix |
| `python3 vibe/stills.py out/x.mp4 --count 12` | contact sheet for review |
| `python3 vibe/export.py out/x.mp4 --preset reels,youtube` | platform deliverables |
| `python3 vibe/fonts.py "Family:700"` | download Google Fonts |
