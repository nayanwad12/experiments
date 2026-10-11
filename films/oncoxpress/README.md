# OncoXpress brand film (40 s)

`out/oncoxpress_brand_film_40s.mp4`: 1920×1080, 24 fps, H.264 + AAC, mixed to −14 LUFS. `out/sheet.png` is a contact sheet.

**Look:** Apple-style. Black graphic cards, Inter type, a purple-to-blue accent, white word-by-word captions, one clean grade with light grain across all footage.

## Edit
| time | picture | narration |
|---|---|---|
| 0.0 | corridor walk (fades up from black) | Sometimes, life changes in a moment. |
| 3.1 | **G1** floating questions over a blurred desk of papers | And suddenly, the questions feel bigger than the answers. |
| 6.6 | close-up, she turns to camera | But behind every diagnosis is a person. |
| 9.3 | waiting room, then her files | A family. A life filled with memories, dreams, and people who care. |
| 13.8 | doctors at the screen | Being heard matters. |
| 15.4 | **G2** OncoXpress care-plan UI (rebuilt) | Understanding your options matters. |
| 17.5 | doctors discussing | Because care is more than a medical conversation. |
| 20.0 | **G3** Guidance. / Thoughtful decisions. / Support. → care circle | It is guidance, thoughtful decisions… the people beside you. |
| 25.0 | close-up smile, corridor walk, phone | Every person deserves dignity, compassion… |
| 31.0 | **G4** logo reveal | OncoXpress. |
| 32.3 | **G5** her face zooms back into a patient profile | …see the person behind the diagnosis. |
| 36.0 | **G6** end card + "Take your next step" | Connect with OncoXpress to take your next step. |

All laptop and phone screens in the AI clips had garbled UI and text. Those shots are not used; G1–G6 replace them with real graphics.

**Narration cuts:** the 49.7 s narration was fitted to 40 s (`vo.py`):
- three lines dropped: "In moments like these.", "And knowing what to ask can make a difference.", "The journey may not always be easy."
- the "But" before "every person deserves" trimmed
- pauses tightened and the voice sped up 1.05×

**Music and SFX** are synthesised (no licences): a soft D-major piano/pad score that resolves on the logo, room tone under the footage, and whooshes, UI blips and clicks, risers, soft hits, sparkle and a chime.

## Rebuild
```bash
python3 vo.py          # narration edit -> work/vo_edit.wav, work/vo_lines.json
python3 build.py all   # timeline, base (footage), overlay (Playwright), audio, final, sheet
```
- Needs ffmpeg, Python with numpy/scipy, and Node with Playwright (`NODE_PATH=$(npm root -g)`).
- `fonts/Inter-var.woff2` is Inter, SIL OFL.

## Placeholders to swap
- The logo is a stand-in (an "O" ring crossed by an "X", with an "OncoXpress" wordmark). Replace the `logo()` function in `scene.js` with the real mark.
- "Meera" and her profile details in G5 are illustrative.
- The ✦ generator watermark in the AI clips is left as delivered.
