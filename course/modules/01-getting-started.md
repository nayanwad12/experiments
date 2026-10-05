# Module 1: Getting Started
> From zero to your first AI-edited video in one sitting. Install the tools, understand the Vibe Loop, and ship a 30-second edit today.
Outcome: You have Claude Code + the Vibe Editing Skills installed and a finished 30-second video exported for Reels.
Assignment: Make a 30-second edit of any clip on your phone using only prompts. Post the before/after in the community with the hashtag #MyFirstVibeEdit.
Resources: R01, R02, R03, R04

## Welcome: what Vibe Editing actually is | video | 6 min
Summary: The new way to edit: you direct in plain words, AI builds the edit in code. See real before/afters made with this exact system.
Prompt: Explain what you can do for me as my video editor, in 5 bullet points, then show me the menu of video types I can make.
### Notes
- **Vibe Editing = you are the director, AI is the editor.** You describe the vibe ("warm, punchy, a little dreamy") and the AI writes and runs the edit.
- Nothing is dragged on a timeline. Every cut, caption, animation and sound is a line of code, so changes are instant: "make the title land on the beat" is one sentence.
- What you'll be able to make by the end: reels, ads, motion graphics, animations, VFX, AI films, soundtracks and hundreds of personalised videos.
- What you still bring: taste, the story, the footage, and the final yes. **Taste is the new skill.**
- Mindset for this course: *don't learn buttons, learn to direct.*

## The toolkit: Claude Code, Python, ffmpeg (and why no timeline) | video | 8 min
Summary: A plain-English tour of the 3 tools behind every video in this course and what each one does for you.
Prompt: Check my computer for everything Vibe Editing needs and tell me what's missing in plain English.
### Notes
- **Claude Code**: the AI that reads your request, writes the editing code, runs it, and checks the result. Works in the terminal, desktop app or VS Code.
- **Python**: the language the edits are written in. You will *never* have to write it yourself.
- **ffmpeg**: the engine that actually cuts, encodes and exports video. Installed automatically.
- **The Skills Pack**: Ideabro's ready-made playbooks that tell Claude exactly how to make each type of video professionally.
- Why code instead of a timeline: repeatable, versioned, instantly editable, works for 1 video or 1,000.

## Install everything in 15 minutes | video | 14 min
Summary: Step-by-step install on Mac and Windows: Claude Code, Python, and the Vibe Editing Skills Pack, with a live troubleshooting walk-through.
Prompt: Let's make a video with the Vibe Editing System. Run the setup check and install anything missing.
Resources: R01, R02
### Notes
1. Install Claude Code (desktop app or `npm install -g @anthropic-ai/claude-code`).
2. Install Python 3.10+ from python.org (Windows: tick **"Add Python to PATH"**).
3. Install the Skills Pack: unzip into `~/.claude/skills/` (Windows: `%USERPROFILE%\.claude\skills\`), or install as a plugin.
4. Open Claude Code in an empty folder and say: *"Let's make a video with the Vibe Editing System."*
5. Claude runs `doctor.py`, installs what's missing, and shows test frames. **If you see the branded test frames, you're ready.**
- Windows tip: use `py` where guides say `python3`.
- "Externally managed environment" error → ask Claude: *"set up a virtual environment and re-run the doctor."*

## Your first edit in 10 minutes | video | 12 min
Summary: Live: one phone clip in, a captioned and music-backed reel out. Copy the exact prompt and do it alongside.
Prompt: Make a 30-second Instagram reel from raw/take1.mp4. Cut the pauses and ums, add big pop captions, upbeat music under my voice, and export for Reels.
### Notes
- Drop your clip into the project's `raw/` folder (never edit originals; the system won't either).
- Claude will ask a few quick questions. Answering **"defaults are fine"** is allowed.
- Watch for the **contact sheet**: a grid of frames Claude shows you before calling anything done.
- Your files land in `out/`. The `_reels.mp4` version is ready to upload.
- 🎯 Win condition: a finished video you didn't touch a timeline for.

## The Vibe Loop: Brief → Stills → Draft → Final | video | 9 min
Summary: The 7-step loop every professional Vibe Editor follows, and why it saves you hours of revisions.
Resources: R03
### Notes
- **Brief:** say what, who it's for, where it plays, the vibe.
- **Beat table:** a time-by-time plan (what we see / hear / read). Approve it *before* rendering.
- **Build:** AI writes the edit; all timings live in one file.
- **Stills:** check frames in seconds. Fix layout here, not after a 10-minute render.
- **Draft:** fast low-res version for timing.
- **Final:** full quality, checked again.
- **Export:** one command → every platform.
- Rule: **never approve what you haven't seen as stills.**

## Your project folder & versioning (your undo button) | reading | 6 min
Summary: How every project is organised, where your files go, and how versions keep you safe with clients.
### Notes
| folder | what lives there |
|---|---|
| `raw/` | your originals (read-only) |
| `assets/` | logos, cut-outs, licensed music |
| `work/` | drafts, transcripts, intermediate files |
| `out/` | finished videos + review stills |
| `brief.md` | the plan |
| `brand.json` | colours + fonts |
| `timeline.py` | every timing in one place |
- Name deliverables `name_v1.mp4`, `name_v2.mp4`. Never overwrite a version a client has seen.
- Ask Claude to *"log this revision in work/revisions.md"* so you always know what changed.
