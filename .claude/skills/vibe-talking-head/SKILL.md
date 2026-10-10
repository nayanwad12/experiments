---
name: vibe-talking-head
description: Ideabro Studio Vibe Editing System - talking-head and creator video editing in code. Use when the user wants to edit footage of someone talking to camera into a finished video, including Instagram Reels, TikToks or YouTube Shorts from a raw take; cutting dead air, ums, filler words and retakes; jump cuts and punch-in zooms; animated word-by-word captions (Hormozi/MrBeast style); podcast or interview clips (long recording to short vertical clips); YouTube long-form edits with chapters; testimonials; course or tutorial lessons with screen recording and face cam; lower-thirds, B-roll, stickers and music under a voice. Triggers on "edit my video", "cut the silences", "add captions/subtitles", "make reels from my podcast", "talking head", "face cam", "jump cuts".
---

# Talking-Head & Creator Videos
*Ideabro Studio · Vibe Editing System — direct the vibe, let AI do the keyframes.*

You are the editor. The user is the director. They talk in vibes ("punchier", "cleaner", "more energy") and you
turn that into a precise, word-accurate edit made in code, then show proof (contact sheets) before calling anything done.

Paths below are relative to **this skill's folder** (the "Base directory" shown when the skill loads):
`scripts/` (toolkit), `reference/` (guides), `templates/`.

## What you can make here

| type | default recipe |
|---|---|
| **Reel / TikTok / Short** from one take | 9:16, 20–60 s, silences + ums cut, punch-in every other cut, pop captions, upbeat bed, end card |
| **Podcast / interview → clips** | find the 3–5 best self-contained 20–60 s moments, hook first, 9:16 crop on the speaker, pop captions |
| **YouTube long-form** | 16:9, tight cuts (gap 0.5 s), punch-ins every 5–10 s, clean captions + .srt, chapters, lower-thirds |
| **Testimonial** | gentle cuts, clean captions, name lower-third, warm grade, chill/corporate bed |
| **Course / tutorial lesson** | screen recording + round face-cam bubble, zooms on the action, callouts, clean captions |
| **"Say it, it happens"** (effects triggered by spoken words) | do the base edit here, then use the `vibe-vfx` skill for the effects |

## Step 0: Setup (first time in a project)

1. `python3 scripts/doctor.py --kit talking-head --install`
   (Windows: `py` instead of `python3`. If pip refuses, see `reference/troubleshooting.md` for the venv fix.)
2. `python3 scripts/new_project.py <project-name> --kind talking-head --format 9:16 --fps 30`
   (`--format 16:9` for YouTube). Then work **inside that folder**. The toolkit is copied to `vibe/`.
3. Put the footage in `raw/` (copy the files the user points to; never modify originals).

If the current folder already has `vibe/` and `brief.md`, skip setup.

## Step 1: Brief (one message, smart defaults)

Ask only what you can't infer, offering defaults the user can accept with "go":
1. Platform + length? *(default: Reels/TikTok, ≤ 45 s)*
2. Caption style? pop (big words) / karaoke / clean / none *(default: pop, brand lime highlight)*
3. Music mood? *(default: upbeat, ducked under the voice)*
4. Brand: colours/fonts/handle for the end card? *(default: Ideabro house style, see `reference/brand-kit.md`)*
5. Anything to cut or keep for sure? Names to spell right?

Write the answers into `brief.md`.

## Step 2: Look and listen

```bash
python3 vibe/stills.py raw/take1.mp4 --count 9          # then READ out/stills/take1_sheet.png
python3 vibe/transcribe.py raw/take1.mp4 -o work/words.json --prompt "Names, Brand, Jargon"
```
Read `work/transcript.txt`. Fix misspelled names directly in `work/words.json` (keep the timings).
Note the framing: where the face is (for the crop anchor), the light, and whether it's handheld.

## Step 3: Story edit (the part that makes it good)

Work from the transcript, not the timeline:
- **Hook:** the single strongest line (bold claim, surprising number, question, result). It should be in the first
  2 seconds. If it's later in the take, move it to the front with `--keep`.
- **Retakes:** when a sentence is repeated, keep the **last complete** version and drop the earlier ones (`--remove`).
- **Tighten:** cut tangents, throat-clearing intros ("so, um, hey guys"), and repeated points.
- **Ending:** end on the payoff or CTA. Cut everything after.
- Podcast → clips: score candidate moments on hook strength, self-contained, emotion/value, ≤ 60 s. Present a table
  `rank | start–end | title | hook line | why`, and let the user pick.

Show the user the planned EDL in words ("Hook: 'I made 10 reels in an hour' (41.2 s) → main story 3.5–38 s, minus
retake at 12–15 s") and get a quick OK before rendering.

## Step 4: Cut

```bash
python3 vibe/cut_silence.py raw/take1.mp4 --words work/words.json -o work/cut.mp4 \
    --keep 41.2-46.0,3.5-38.0 --remove 12.3-15.0 --punch 1.1 --anchor 0.5,0.38
```
- `--gap 0.35` (default) is snappy social pacing. Use `0.5` for YouTube/testimonials and `0.25` for frantic.
- `--punch 1.08–1.15` zooms every other segment (the classic jump-cut punch-in); `--anchor` = face position.
- Writes `work/edl.json` and `work/words_cut.json` (words re-timed to the cut). Use these for everything after.
- No speech in the clip? Leave out `--words` to cut by audio level.

**Wrong aspect ratio?** (e.g. a 16:9 podcast to 9:16) reframe the cut before captioning:
`python3 vibe/export.py work/cut.mp4 --preset reels --fit crop --anchor 0.5,0.4 -o work/` → `work/cut_reels.mp4`.
For a two-person podcast, run it twice with different `--anchor x` values and cut between speakers using the words
(who speaks when), or use `--fit blur` to keep both.

## Step 5: Captions

```bash
python3 vibe/captions.py work/words_cut.json --video work/cut.mp4 --style pop \
    --emphasis "free,secret,10x" --burn work/captioned.mp4
```
- Styles: `pop` (1–3 big words, active word highlighted), `karaoke`, `clean` (YouTube/testimonials), `minimal`.
- `--pos 0.62` moves captions up (keep them above the bottom 420 px on vertical). Use `--scale 0.85` to make them smaller.
- Captions must not cover the face: check a still. The `.srt` is written too (upload it to YouTube/LinkedIn).

## Step 6: Graphics on top (optional, transparent overlay)

For hook titles, lower-thirds, emoji/sticker pops, progress bars, CTA cards: write `overlay_scene.py` with
motion_kit and render it **transparent**, then composite. That way the footage is never loaded into memory.

```python
import sys; sys.path.insert(0, "vibe")
from motion_kit import *
S = Stage(1080, 1920, fps=30, duration=DUR)          # DUR = length of work/captioned.mp4
B = S.brand
def draw(c, t):                                       # don't paint a background
    k = ease_out_back(prog(t, 0.2, 0.45)); out = ease_in_cubic(prog(t, 3.5, 0.3))
    x = lerp(-700, 60, k) - 800 * out
    rrect(c, x, 330, 640, 150, 30, rgb(B, "fg")); rrect(c, x, 330, 18, 150, 9, rgb(B, "accent"))
    text(c, "PRIYA SHARMA", x + 50, 385, size=52, font="display", fill=rgb(B, "paper"), align="left")
    text(c, "FOUNDER · IDEABRO", x + 50, 445, size=26, font="mono", fill=rgb(B, "accent"), align="left", tracking=0.15)
if __name__ == "__main__":
    S.stills(draw, [1.0, 3.0], under="work/captioned.mp4")    # check on top of the real footage
    S.render(draw, "work/overlay.mov", alpha=True)
```
`python3 vibe/overlay.py work/captioned.mp4 work/overlay.mov -o work/edited.mp4`

Time every graphic from `work/words_cut.json` (e.g. the sticker pops on the word "money"). Use the
text/motion recipes in `reference/motion-principles.md`.

## Step 7: Sound

```bash
python3 vibe/audio_kit.py voice work/edited.mp4 -o work/voice.wav --denoise
python3 vibe/audio_kit.py bed --mood upbeat --seconds <DUR> -o work/music.wav
```
Write `work/cues.json` (voice + music at −9 dB with ducking + a few SFX: pop on stickers, whoosh into the end card) and:
`python3 vibe/audio_kit.py mix work/cues.json -o work/mix.wav --video work/edited.mp4 --out-video out/<name>_v1.mp4`
Details: `reference/sound-design.md`.

## Step 8: Review and deliver

```bash
python3 vibe/stills.py out/<name>_v1.mp4 --count 12      # READ the sheet: captions, face, safe zones, end card
python3 vibe/export.py out/<name>_v1.mp4 --preset reels,shorts      # or youtube, feed, linkedin ...
```
Send the user the contact sheet + the file path + 1–3 pointed questions. Log changes in `work/revisions.md`.

## Recipes

**YouTube long-form.** `--gap 0.5 --punch 1.08`. Use `clean` captions (or just the .srt). Make chapters from
`work/segments.json` (group by topic: `00:00 Intro`, …) into `out/chapters.txt`. Add lower-thirds for names and on-screen
callouts for key numbers. Graphics/b-roll every 20–40 s keep retention up. Export `youtube`.

**Course lesson (screen + face).** Put the face in a round bubble bottom-right:
```bash
ffmpeg -i raw/screen.mp4 -i raw/face.mp4 -filter_complex "[1:v]crop='min(iw,ih)':'min(iw,ih)',scale=360:360,format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lt(hypot(X-180,Y-180),178),255,0)'[f];[0:v][f]overlay=W-w-40:H-h-40[v]" -map "[v]" -map 1:a -c:v libx264 -crf 18 -pix_fmt yuv420p work/lesson.mp4
```
then cut, captions (`clean`) and callouts as above. Zoom into the screen where the action is by cropping in an overlay
scene or by re-encoding segments with `crop=`.

**Testimonial.** `--gap 0.45`, no punch-ins. Apply `vibe/grade.py --look warm --strength 0.6`, `clean` captions, a
name + role lower-third in the first 3 s, and a chill or corporate bed at −12 dB.

**Hook variations (A/B).** Render 2–3 versions with different `--keep` first segments + different hook titles; name them
`_hookA`, `_hookB`.

## Quality bar (check on the contact sheet before saying done)

- [ ] First frame is interesting (face + hook text), no black frame or blink
- [ ] No word clipped at a cut (listen-check the EDL boundaries: words have `pre`/`post` padding)
- [ ] Captions readable, inside safe zone, not over the mouth/eyes, names spelled right
- [ ] Punch-ins keep the head fully in frame
- [ ] Music audible but clearly under the voice; ends cleanly; −14 LUFS
- [ ] Length and format match the brief

## Reference (read when needed)
- `reference/foundations.md`: the Vibe Loop, project rules, toolkit, quality gate
- `reference/brand-kit.md`: Ideabro house style, brand.json, typography, safe zones
- `reference/sound-design.md`: music moods, SFX, ducking, loudness
- `reference/motion-principles.md`: easing, kinetic type, transitions
- `reference/export-specs.md`: platform presets, reframing
- `reference/troubleshooting.md`: install and render problems
- `reference/prompt-library.md`: examples of how students can direct you
