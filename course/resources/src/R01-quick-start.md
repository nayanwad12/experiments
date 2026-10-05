# Quick Start: Install in 15 Minutes
Everything you need to make your first AI-edited video today. Mac and Windows.

## What you need
| item | why | where |
|---|---|---|
| Claude Code | the AI editor | code.claude.com (desktop app, terminal or VS Code) |
| Python 3.10+ | runs the editing tools | python.org/downloads |
| Vibe Editing Skills Pack | the playbooks + toolkit | Course Resources → R02 |
| ~3 GB free disk | AI models download once | — |

## Step by step
1. **Install Python.** Windows: tick **"Add Python to PATH"** on the first screen.
2. **Install Claude Code** and sign in.
3. **Install the Skills Pack.** Unzip `vibe-editing-system-all.zip` so each `vibe-…` folder sits in:
   - Mac / Linux: `~/.claude/skills/`
   - Windows: `%USERPROFILE%\.claude\skills\`
4. **Restart Claude Code** and type `/skills`. You should see 9 skills starting with `vibe-`.
5. **Make a new empty folder**, open Claude Code in it and say:
   > Let's make a video with the Vibe Editing System. Run the setup check.
6. Claude installs what's missing (ffmpeg included) and shows **branded test frames**. ✅ You're ready.

## If something goes wrong
| you see | do this |
|---|---|
| `python3` not found (Windows) | say "use py instead of python3" |
| "externally managed environment" | say "set up a virtual environment and re-run the doctor" |
| skills don't show in `/skills` | check the folder path: `skills/vibe-talking-head/SKILL.md` |
| slow first run | normal: models download once |

## Your first prompt
> Make a 30-second Instagram reel from raw/take1.mp4. Cut the pauses and ums, add big pop captions, upbeat music, and export for Reels.
