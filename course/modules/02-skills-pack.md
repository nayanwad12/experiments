# Module 2: Vibe Editing Skills Pack (Bonus)
> 9 ready-made Claude skills that turn a sentence into a finished video. Install once, use in every module after this.
Outcome: All 9 skills installed and tested. You know which skill to use for any video a client asks for.
Assignment: Make one 10–20 second video with three different skills (e.g. a talking-head clip, a logo reveal and an AI voiceover) and post all three.
Resources: R02, R01, R04

## What skills are (and why they're a cheat code) | video | 5 min
Summary: Skills are expert playbooks for Claude. Here's how they turn "make me a reel" into a pro-level edit, every time.
### Notes
- A **skill** is a folder of instructions + tools Claude loads automatically when your request matches it.
- Without skills, AI guesses. With skills, it follows **Ideabro's production playbook**: brief, beat table, stills check, mixing rules, export specs.
- Every skill is self-contained: scripts, guides and templates included. Install one or all nine.
- You don't call them by name (but you can). Just describe the video.

## Install in 5 minutes (zip and plugin methods) | video | 7 min
Summary: Two ways to install: unzip into your skills folder, or one command as a Claude Code plugin.
Resources: R02, R01
### Notes
**Zip method**
1. Download `vibe-editing-system-all.zip` from Course Resources.
2. Unzip so each skill folder sits in `~/.claude/skills/` (Windows: `%USERPROFILE%\.claude\skills\`).
3. Restart Claude Code → type `/skills` → you should see 9 `vibe-…` skills.

**Plugin method** (if your instructor shares the marketplace link)
```
/plugin marketplace add <owner>/<repo>
/plugin install vibe-editing-system@ideabro-studio
```
- Update later with `/plugin update` (plugin) or by replacing the folders (zip).

## Your first video with the Start Here skill | video | 10 min
Summary: Let the Start Here skill pick the right playbook, set up your project and show test frames, all in one conversation.
Prompt: Let's make a video with the Vibe Editing System. I want a 20-second promo for my Instagram page @myhandle. Use defaults.
### Notes
- The Start Here skill (`vibe-editing-system`) shows a menu of 8 video types and asks what you have (footage? logo? voice?).
- It runs setup, creates the project and renders branded test frames in ~1 minute.
- Then it switches to the matching playbook automatically.
- Say **"teach me as you go"** and it explains every step. Perfect for learning.

## Skill: Talking-Head & Creator Videos | video | 8 min
Summary: Reels from raw takes, podcast clips, YouTube edits, testimonials and course lessons, cut word-accurately.
Prompt: Use vibe-talking-head: make a 45-second reel from raw/take1.mp4, put my strongest line first as the hook, pop captions, punch-in jump cuts.
### Notes
- Cuts silences, ums and retakes using a word-level transcript.
- Moves your best line to the front as the **hook**.
- Captions: pop / karaoke / clean / minimal, in your brand colours.
- Adds lower-thirds, stickers and music ducked under your voice.

## Skill: Launch Videos & Ads | video | 8 min
Summary: Promos, product launches, social ads with variants, app demos rebuilt as crisp graphics.
Prompt: Use vibe-launch-ads: 25-second launch reel for my course "Vibe Editing", bold and punchy, end card ENROLL NOW, also give me 1:1 and 4:5 versions.
### Notes
- Follows the launch formula: Hook → Problem → Reveal → Proof → CTA.
- Everything locked to the music's beat.
- Variants (hooks, formats, languages) are re-renders, not re-edits.

## Skill: Motion Graphics | video | 8 min
Summary: Showreels, explainers, kinetic typography, logo reveals, infographics and transparent lower-third packs.
Prompt: Use vibe-motion-graphics: a 6-second logo reveal for assets/logo.png with an impact on the beat and a sparkle.
### Notes
- Every frame is generated from code, so it's razor sharp at any size.
- Export **transparent packs** (ProRes 4444) to use in Premiere, CapCut or DaVinci.
- Style frames first, animation second.

## Skill: Stylised Animation | video | 8 min
Summary: Claymation, crayon, paper-cut, doodle and talking cartoon mascots with no AI images.
Prompt: Use vibe-stylised-animation: a 20-second claymation short about a sheep who discovers vibe editing at 2am. Wordless, playful music.
### Notes
- Handmade feel from 3 tricks: **held drawings, boil, texture**.
- Characters blink, look and lip-sync to the voice automatically.

## Skill: VFX & Editing Magic | video | 8 min
Summary: Background swaps, text behind you, layer splits, tracking, cinematic looks and slow motion.
Prompt: Use vibe-vfx: put the word VIBE in huge lime letters behind me in raw/take1.mp4, appearing when I say "vibe".
### Notes
- Person cut-outs (mattes) in one command.
- Effects start on the exact word you speak.
- Honest feasibility check before promising a client an effect.

## Skill: AI Footage → Films | video | 8 min
Summary: Turn Veo/Sora/Kling clips into a film that doesn't look AI, plus faceless channel episodes.
Prompt: Use vibe-ai-footage: scan the clips in raw/, tell me which are usable, then cut a 60-second brand film to my voiceover raw/vo.mp3.
### Notes
- Scans every clip for morphs, garbled text and popping objects.
- Retimes shots to land on the narration.
- One grade + grain + sound design so it stops looking like AI.

## Skill: Audio, Music & Voiceover | video | 8 min
Summary: Original copyright-free music, 14 sound effects, AI voiceover (incl. Hindi), audiograms and visualisers.
Prompt: Use vibe-audio-videos: make a chill 30-second music bed and a Hindi AI voiceover of my script in work/script.txt.
### Notes
- 7 music moods: upbeat, hype, tech, corporate, chill, cinematic, playful.
- Auto-ducking: music dips when someone talks.
- Final mix hits platform loudness (−14 LUFS) automatically.

## Skill: Bulk & Automated Videos | video | 8 min
Summary: 100 personalised videos from a spreadsheet, every format in one go, multi-language versions.
Prompt: Use vibe-bulk-videos: make a personalised welcome video for every row in students.csv using their first_name.
### Notes
- Build one hero template → test 3 rows → render the rest.
- Long names auto-fit. Non-English names supported with the right fonts.
- A report shows every video that rendered (and any that failed).

## Updates & what's new | reading | 3 min
Summary: Where new skill versions are announced and how to update in 1 minute.
### Notes
- New versions are announced in the community and added to Course Resources.
- **Zip install:** delete the old `vibe-…` folders and unzip the new ones.
- **Plugin install:** run `/plugin update`.
- Changelog
  - **v1.0**: 9 skills, 20 tools, Ideabro house style, 7 music moods, 14 SFX, 4 caption styles.
