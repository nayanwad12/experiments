# Vibe Editing System, by Ideabro Studio

**Direct the vibe. Let AI do the keyframes.**

A set of Claude skills that let anyone make finished videos by describing what they want: reels, ads,
motion graphics, animation, VFX, AI-footage films, soundtracks and bulk personalised videos. Claude edits in code
(Python + ffmpeg), checks its own work on contact sheets, and delivers platform-ready files. You never touch a timeline.

## The 9 skills

| skill | makes |
|---|---|
| `vibe-editing-system` | **Start here.** Finds the right video type, sets everything up, and works on its own (it includes all 8 playbooks) |
| `vibe-talking-head` | Reels/TikToks/Shorts from a take, podcast clips, YouTube edits, testimonials, course lessons |
| `vibe-launch-ads` | Promo reels, launches, social ads + variants, app/SaaS demos, product videos, teasers |
| `vibe-motion-graphics` | Showreels, explainers, kinetic type, logo reveals, infographics, transparent lower-third packs |
| `vibe-stylised-animation` | Claymation, crayon, paper-cut, doodle, cartoon mascots, kids' stories, generative films |
| `vibe-vfx` | Background swap, text behind you, layers, tracking, remove/re-add, cinematic looks, slow-mo |
| `vibe-ai-footage` | Veo/Sora/Kling clips into films that don't look like AI, faceless channels, AI music videos |
| `vibe-audio-videos` | Original music + SFX, AI voiceover, voice clean-up, audiograms, visualisers, beat-sync |
| `vibe-bulk-videos` | Personalised videos from a CSV, all formats, multi-language, content series, ad matrices |

Every skill is **self-contained**: it carries the full toolkit (`scripts/`), the guides (`reference/`) and
templates. A student can install just one and it works.

## Install (students)

**Requirements:** Claude Code (terminal, desktop app or VS Code), Python 3.9+, ~3 GB free disk for the AI models.
ffmpeg is installed automatically if it's missing. A GPU is optional.

### Option A: everything, as a Claude Code plugin (recommended)
In Claude Code:
```
/plugin marketplace add nayanwad12/experiments
/plugin install vibe-editing-system@ideabro-studio
```
(If you publish this folder as its own repository, use that `owner/repo` instead. It already contains its own
`.claude-plugin/marketplace.json`.)

### Option B: one skill (or all) from a zip
Download from `dist/`:
- `vibe-editing-system-all.zip` (every skill), or a single skill, e.g. `vibe-talking-head.zip`

Unzip so each skill folder sits in your skills directory:
- Mac / Linux: `~/.claude/skills/vibe-talking-head/SKILL.md`
- Windows: `%USERPROFILE%\.claude\skills\vibe-talking-head\SKILL.md`
- or just for one project: `<project>/.claude/skills/vibe-talking-head/SKILL.md`

Restart Claude Code. Check with `/skills`.

### Option C: Claude.ai / Claude Desktop (Settings → Capabilities → Skills → upload the skill zip)
This works for planning, briefs, scripts and light renders. Heavy rendering and model downloads need a real machine,
so use Claude Code for full productions.

## First run

Open Claude Code in an empty folder and say:

> Let's make a video with the Vibe Editing System.

or be specific:

> Use vibe-talking-head: make a 30-second reel from ~/Videos/take1.mp4 with pop captions and upbeat music.

Claude checks your setup (`doctor.py`), installs what's missing, creates a project folder and shows you test frames
within a couple of minutes. Then it asks a few brief questions and starts editing.

What a project looks like:
```
my-reel/
  raw/  assets/  fonts/  work/  out/      footage in, finished videos out
  brief.md  brand.json  timeline.py       the plan, the brand, every timing
  scene.py                                graphics (frames as a function of time)
  vibe/                                   the toolkit: python3 vibe/<tool>.py
  CLAUDE.md                               the rules Claude follows in this project
```

## The toolkit (in every skill's `scripts/`, copied into each project's `vibe/`)

| tool | does |
|---|---|
| `doctor.py` | checks and installs dependencies per video type |
| `new_project.py` | creates a branded project with a working starter animation |
| `fonts.py` | any Google Font as static TTF |
| `transcribe.py` | Whisper speech-to-text with word timestamps |
| `cut_silence.py` | removes pauses, ums and retakes; reorders the hook first; punch-in jump cuts |
| `captions.py` | pop / karaoke / clean / minimal animated captions + .srt, burn-in |
| `tts.py` | local AI voiceover (Kokoro, incl. Hindi), per-line timings |
| `audio_kit.py` | original music beds (7 moods), 14 SFX, voice clean-up, mixing with ducking + loudness |
| `motion_kit.py` | the frame engine: easing, text, shapes, images, video frames, parallel + transparent renders |
| `toon_kit.py` | handmade looks: clay, crayon, paper, doodles, blinking/talking characters |
| `matte.py` | person/object cut-outs (video + images), background swap |
| `overlay.py` | lays transparent graphics over footage |
| `assemble.py` | builds a cut from clips/photos with transitions, Ken Burns and retiming |
| `grade.py` | colour looks, LUTs, grain, vignette, letterbox, before/after |
| `retime.py` | slow motion (optical flow), speed-ups, fit-to-duration |
| `clipscan.py` | QC sheets + morph/cut detection for AI or stock clips |
| `batch.py` | one render per spreadsheet row |
| `stills.py` | contact sheets for review |
| `export.py` | platform deliverables (Reels, Shorts, YouTube, feed, square, master), reframing, −14 LUFS |
| `templates/web/` | optional HTML/WebGL scene + headless renderer (Playwright) |

## Brand

Default look = **Ideabro house style**: ink `#0B0B0D`, paper `#F2EEE3`, signature lime `#D4FF3F`, periwinkle `#C4C6FF`,
fonts Unbounded / Anton / Inter Tight / JetBrains Mono / Instrument Serif. Students swap in a client brand by editing one
file (`brand.json`). The "by Ideabro Studio" credit is added only when the student asks for it.

## For Ideabro: editing and releasing

```
vibe-editing-system/
  shared/scripts | reference | templates   <- edit the toolkit and guides HERE (single source of truth)
  skills/<name>/SKILL.md                   <- edit each skill's instructions HERE
  skills/<name>/scripts|reference|templates <- generated copies (don't edit)
  dist/*.zip                               <- generated downloads
  build.py
```
After any change:
```bash
python3 build.py           # sync + validate + re-zip
python3 build.py --check   # CI-style check that nothing is out of sync
```
Bump `version` in `.claude-plugin/plugin.json` (and both `marketplace.json` files) when you release, so students get
the update via `/plugin update`.

## Credits and licences

Toolkit and skills © Ideabro Studio. Third-party components are installed on the student's machine at first use:
ffmpeg (LGPL/GPL), faster-whisper (MIT), Kokoro-82M voices (Apache-2.0), rembg (MIT) and its models, skia-python (BSD),
OpenCV (Apache-2.0), Playwright (Apache-2.0), Google Fonts (OFL). Music and SFX from `audio_kit` are generated
originals, free to use commercially.
