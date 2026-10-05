---
name: vibe-bulk-videos
description: Ideabro Studio Vibe Editing System - bulk and automated video production, where code beats a timeline. Use when the user wants many videos from one template, including personalised videos from a spreadsheet or CSV (names, companies, offers), one edit exported to every format (9:16, 1:1, 4:5, 16:9), multi-language versions with new voiceover and subtitles, a recurring content series (daily quotes, tips, news, stats, listings) generated from data, ad variant matrices (hooks x CTAs x formats) for A/B testing, or a one-command pipeline that turns a script into a finished episode. Triggers on "bulk", "batch", "100 videos", "for every row", "personalised video", "from a spreadsheet/CSV/Google Sheet", "all formats", "translate the video", "series template", "automate", "variants".
---

# Bulk & Automated Videos
*Ideabro Studio · Vibe Editing System — direct the vibe, let AI do the keyframes.*

Build **one great template**, prove it on a couple of rows, then let code produce hundreds of variations: every name,
language, format or hook. Each render is still checked, because automation multiplies mistakes as fast as it multiplies
videos.

Paths below are relative to **this skill's folder**: `scripts/`, `reference/`, `templates/`.

## What you can make here

| type | how |
|---|---|
| **Personalised videos** | CSV row → copy (name, company, offer) + optional per-row AI voice line → one MP4 each |
| **One edit → all formats** | design in `U` units, render W×H per format, or `export.py --preset reels,feed,square,youtube` |
| **Multi-language versions** | translated script per language → `tts.py` voice per language → captions in that language → render |
| **Content series** | spreadsheet of quotes/tips/stats → daily videos in a fixed branded template |
| **Ad variant matrix** | hooks × CTAs × formats → systematically named files + a report for A/B tests |
| **Script → episode pipeline** | `make_episode.py script.txt` runs TTS → visuals → captions → music → export in one go |

## Step 0: Setup (first time in a project)

1. `python3 scripts/doctor.py --kit bulk --install` (Windows: `py`)
2. `python3 scripts/new_project.py <name> --kind bulk --format 9:16 --fps 30 --duration 12` and work in it.
   `scene.py` already supports `render-row` (CSV columns that match `timeline.COPY` keys replace that copy).

## Step 1: Brief + data

Ask: what changes per video (which fields) and what stays · how many videos and where the data is (CSV, Excel, Google Sheet
→ download as CSV) · formats · per-video voice? · naming scheme for files · deadline. Get **2–3 real sample rows**
including the **longest** values (long names and long company names are where templates break).

Clean the data first (with pandas or csv): trim spaces, fix capitalisation (`Priya Sharma`, not `PRIYA sharma`), check for
empty required fields, flag rows that are too long, and dedupe. Save `data/clean.csv` and show the user the problems found.

## Step 2: The hero template

1. Make one perfect video with the sample row: `timeline.COPY` holds every variable text, and `scene.py` uses only
   `TL.COPY[...]` for those texts.
2. **Make text fit any value**: measure with `text_width()` and scale to fit, wrap long lines with `wrap()`, and set a
   minimum size. If it still doesn't fit, use a shorter fallback (first name only).
3. Test the extremes: `python3 scene.py stills` with the longest name/company, an empty optional field, non-English
   characters (é, ñ, हिंदी, 日本語). For non-Latin scripts, download fonts that support them
   (`python3 vibe/fonts.py "Noto Sans Devanagari:700" "Noto Sans JP:700"`) and choose the font per row.
4. Get the user's approval on the hero render before batching.

## Step 3: Batch

```bash
python3 vibe/batch.py data/clean.csv --cmd "python3 scene.py render-row {json} {out}" --name "{i:03d}-{slug}" --only 1-3
python3 vibe/batch.py data/clean.csv --cmd "python3 scene.py render-row {json} {out}" --name "{i:03d}-{slug}"
```
- `--only 1-3` first, then check those 3 outputs, then run the rest. Outputs that already exist are skipped, so it's safe to re-run.
- `{json}` = the row as JSON (`work/batch/<file>.json`), `{out}` = `out/batch/<file>.mp4`, any `{column}` works in `--cmd`/`--name`.
- Per-row voice: chain commands, e.g.
  `--cmd "python3 vibe/tts.py \"Hi {first_name}, welcome to Vibe Editing!\" -o work/vo_{i}.wav && python3 scene.py render-row {json} {out}"`
  and make `render-row` mix `work/vo_{row['_row']}.wav` with the bed (extend `build_audio()` to take a voice file; see `reference/sound-design.md`).
- `out/batch/report.csv` lists ok/skipped/error per row. Re-run failed rows after fixing.
- Speed: each render already uses all cores; keep `--workers 1` unless the renders are tiny.

## Step 4: QC at scale

```bash
for f in out/batch/*.mp4; do python3 vibe/stills.py "$f" --at 1.5,6.5 -o out/stills/batch; done
```
Open a sample of sheets (all of them for < 30 videos; every 10th + the longest/shortest/non-Latin rows for big batches).
Check names, overflow, and audio presence. Then export: `python3 vibe/export.py out/batch/<f>.mp4 --preset reels`
(loop over files) if the platform needs exact specs.

## Recipes

**All formats from one design.** `timeline.py` reads `VIBE_SIZE`, so render each format without editing code:
`VIBE_SIZE=1080x1350 python3 scene.py stills` then `VIBE_SIZE=1080x1350 python3 scene.py render` → `out/<name>_1080x1350.mp4`
(PowerShell: `$env:VIBE_SIZE="1080x1350"; py scene.py render`). Check stills per format and fix crowded layouts with
format-specific tweaks (`if TL.W > TL.H:` side-by-side layout). Quick fallback: `export.py --preset reels,feed,square,youtube --fit blur`.

**Multi-language.** Translate the script yourself (Claude) per language. Keep sentence count/lengths similar so timings hold.
Voices: `a*/b*` English, `h*` Hindi, `e*` Spanish, `f*` French, `i*` Italian, `p*` Portuguese, `j*` Japanese, `z*` Chinese
(`tts.py --list`). Then `transcribe.py work/vo_<lang>.wav --lang <code>` → captions per language → render
`out/<name>_<lang>.mp4`. Have a native speaker check at least one version.

**Content series.** CSV columns = `date, title, body, source`. Template auto-fits body text with `wrap()`. Name files
`{date}-{slug}`. Schedule-ready: one folder per week.

**Ad variant matrix.** Build the CSV as the cross product of hooks × CTAs (pandas `merge(how="cross")`), with name
`"H{hook_id}-C{cta_id}"`, render, then formats via export. Deliver `report.csv` + a contact sheet per variant so the
marketer can pick.

**Script → episode in one command.** Write `make_episode.py <script.txt>` that calls (via `subprocess`) `tts.py` →
`transcribe.py` → assemble/scene render → `captions.py --burn` → `audio_kit.py mix` → `export.py`, with all choices
(voice, mood, style) at the top. Then the next episode is: write script → run.

## Quality bar

- [ ] Hero template approved before batching; first 3 rows checked before the full run
- [ ] Longest / empty / non-Latin values tested on stills
- [ ] Every output exists, has audio, and is the right length (report.csv has no errors)
- [ ] Sample of contact sheets reviewed; names spelled exactly as in the data
- [ ] Files named consistently; delivered with report.csv
- [ ] Personal data handled carefully (don't commit the CSV; delete per-row JSON when done if asked)

## Reference
`reference/foundations.md` · `reference/brand-kit.md` · `reference/sound-design.md` · `reference/export-specs.md` ·
`reference/motion-principles.md` · `reference/troubleshooting.md`
