# Vibe Editing System
*by Ideabro Studio: Direct the vibe. Let AI do the keyframes.*

**10 modules · 76 lessons · 13 h 12 min of content · 21 downloadable resources · 9 Claude skills**

## Course outline

| # | module | lessons | time |
|---|---|---|---|
| 1 | Getting Started | 6 | 55 min |
| 2 | Vibe Editing Skills Pack (Bonus) | 12 | 89 min |
| 3 | The Director's Brief | 6 | 54 min |
| 4 | Talking-Head Editing | 8 | 88 min |
| 5 | Sound Design & Music in Code | 6 | 54 min |
| 6 | Launch Videos | 7 | 76 min |
| 7 | Motion Graphics | 8 | 80 min |
| 8 | Stylised Animation & Characters | 6 | 64 min |
| 9 | AI Footage & Advanced VFX | 9 | 98 min |
| 10 | Bulk, Workflow & Getting Paid | 8 | 134 min |

## Course resources

| id | resource | what it is |
|---|---|---|
| R01 | **Quick Start: Install in 15 Minutes** | Everything you need to make your first AI-edited video today. Mac and Windows. |
| R02 | **The Vibe Editing Skills Pack** | 9 Claude skills by Ideabro Studio. Attach the zip files from `dist/` next to this guide. |
| R03 | **The Vibe Loop: One-Pager** | Follow it on every project. It's how you get it right on the first render. |
| R04 | **100 Vibe Editing Prompts** | Copy, paste, change the details. Each one works with the Vibe Editing Skills Pack. |
| R05 | **Creative Brief Template** | Fill this in (or paste it to Claude and answer its questions) before any edit. |
| R06 | **Beat Table Template** | Plan every second before rendering. One idea per row. Times on the beat grid. |
| R07 | **Vibe Vocabulary: Feelings → Instructions** | Say the feeling. This is what the AI does with it. |
| R08 | **Feedback Phrasebook: Get It Fixed in One Round** | Formula: **WHERE** (timestamp) + **WHAT** (element) + **HOW** (direction). |
| R09 | **Hook Swipe File: 50 Scroll-Stopping Openers** | The first 2 seconds decide everything. Each hook works muted: big text + motion + contrast. |
| R10 | **Caption Style Guide** | Most social video is watched with the sound off. Captions are part of the design. |
| R11 | **Sound Design Cheat Sheet** | **beat = 60 ÷ BPM · bar = 4 beats.** Cut on bars, accent on beats. Pick the BPM so the video is a whole number of bars. |
| R12 | **Motion & Easing Cheat Sheet** | word slam · stagger rise · highlight bar · typewriter + caret · counter · strike-through · slot machine · masked reveal |
| R13 | **Platform Export Specs & Safe Zones** | All exports: H.264, AAC 48 kHz, −14 LUFS, fast-start, done by one command: |
| R14 | **AI Footage QC Checklist** | Check every generated clip before it goes near the timeline. |
| R15 | **Brand Kit Template** | One file (`brand.json`) re-skins every video. Fill in the client's values; keep the role names. |
| R16 | **Client Proposal Template (one page)** | **Prepared for:** [Client name] · **By:** [Your name / studio] · **Date:** [ ] |
| R17 | **Pricing & Packages Guide** | Price the **outcome and the speed**, not your hours. The numbers below are *example starting points*. Adjust them to your market, niche and portfolio. |
| R18 | **Delivery Checklist** | Run this before every delivery. It's what makes you look like a studio. |
| R19 | **Troubleshooting Guide** | Post in the community with: what you asked, what happened (screenshot of the error), your OS. Someone will help fast. |
| R20 | **The 30-Day Vibe Editing Challenge** | One small video a day. By day 30 you have a portfolio, a showreel and real confidence. |
| R21 | **Glossary A–Z** |  |

---

# Module 1: Getting Started

> From zero to your first AI-edited video in one sitting. Install the tools, understand the Vibe Loop, and ship a 30-second edit today.

**Outcome:** You have Claude Code + the Vibe Editing Skills installed and a finished 30-second video exported for Reels.

**Assignment:** Make a 30-second edit of any clip on your phone using only prompts. Post the before/after in the community with the hashtag #MyFirstVibeEdit.

**Module resources:** R01 Quick Start: Install in 15 Minutes, R02 The Vibe Editing Skills Pack, R03 The Vibe Loop: One-Pager, R04 100 Vibe Editing Prompts

## 1.1 Welcome: what Vibe Editing actually is
*video · 6 min*

The new way to edit: you direct in plain words, AI builds the edit in code. See real before/afters made with this exact system.

**Try this prompt:**
> Explain what you can do for me as my video editor, in 5 bullet points, then show me the menu of video types I can make.

**Lesson notes**

- **Vibe Editing = you are the director, AI is the editor.** You describe the vibe ("warm, punchy, a little dreamy") and the AI writes and runs the edit.
- Nothing is dragged on a timeline. Every cut, caption, animation and sound is a line of code, so changes are instant: "make the title land on the beat" is one sentence.
- What you'll be able to make by the end: reels, ads, motion graphics, animations, VFX, AI films, soundtracks and hundreds of personalised videos.
- What you still bring: taste, the story, the footage, and the final yes. **Taste is the new skill.**
- Mindset for this course: *don't learn buttons, learn to direct.*

## 1.2 The toolkit: Claude Code, Python, ffmpeg (and why no timeline)
*video · 8 min*

A plain-English tour of the 3 tools behind every video in this course and what each one does for you.

**Try this prompt:**
> Check my computer for everything Vibe Editing needs and tell me what's missing in plain English.

**Lesson notes**

- **Claude Code**: the AI that reads your request, writes the editing code, runs it, and checks the result. Works in the terminal, desktop app or VS Code.
- **Python**: the language the edits are written in. You will *never* have to write it yourself.
- **ffmpeg**: the engine that actually cuts, encodes and exports video. Installed automatically.
- **The Skills Pack**: Ideabro's ready-made playbooks that tell Claude exactly how to make each type of video professionally.
- Why code instead of a timeline: repeatable, versioned, instantly editable, works for 1 video or 1,000.

## 1.3 Install everything in 15 minutes
*video · 14 min*

Step-by-step install on Mac and Windows: Claude Code, Python, and the Vibe Editing Skills Pack, with a live troubleshooting walk-through.

**Try this prompt:**
> Let's make a video with the Vibe Editing System. Run the setup check and install anything missing.

**Resources:** R01 Quick Start: Install in 15 Minutes, R02 The Vibe Editing Skills Pack

**Lesson notes**

1. Install Claude Code (desktop app or `npm install -g @anthropic-ai/claude-code`).
2. Install Python 3.10+ from python.org (Windows: tick **"Add Python to PATH"**).
3. Install the Skills Pack: unzip into `~/.claude/skills/` (Windows: `%USERPROFILE%\.claude\skills\`), or install as a plugin.
4. Open Claude Code in an empty folder and say: *"Let's make a video with the Vibe Editing System."*
5. Claude runs `doctor.py`, installs what's missing, and shows test frames. **If you see the branded test frames, you're ready.**
- Windows tip: use `py` where guides say `python3`.
- "Externally managed environment" error → ask Claude: *"set up a virtual environment and re-run the doctor."*

## 1.4 Your first edit in 10 minutes
*video · 12 min*

Live: one phone clip in, a captioned and music-backed reel out. Copy the exact prompt and do it alongside.

**Try this prompt:**
> Make a 30-second Instagram reel from raw/take1.mp4. Cut the pauses and ums, add big pop captions, upbeat music under my voice, and export for Reels.

**Lesson notes**

- Drop your clip into the project's `raw/` folder (never edit originals; the system won't either).
- Claude will ask a few quick questions. Answering **"defaults are fine"** is allowed.
- Watch for the **contact sheet**: a grid of frames Claude shows you before calling anything done.
- Your files land in `out/`. The `_reels.mp4` version is ready to upload.
- 🎯 Win condition: a finished video you didn't touch a timeline for.

## 1.5 The Vibe Loop: Brief → Stills → Draft → Final
*video · 9 min*

The 7-step loop every professional Vibe Editor follows, and why it saves you hours of revisions.

**Resources:** R03 The Vibe Loop: One-Pager

**Lesson notes**

- **Brief:** say what, who it's for, where it plays, the vibe.
- **Beat table:** a time-by-time plan (what we see / hear / read). Approve it *before* rendering.
- **Build:** AI writes the edit; all timings live in one file.
- **Stills:** check frames in seconds. Fix layout here, not after a 10-minute render.
- **Draft:** fast low-res version for timing.
- **Final:** full quality, checked again.
- **Export:** one command → every platform.
- Rule: **never approve what you haven't seen as stills.**

## 1.6 Your project folder & versioning (your undo button)
*reading · 6 min*

How every project is organised, where your files go, and how versions keep you safe with clients.

**Lesson notes**

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


---

# Module 2: Vibe Editing Skills Pack (Bonus)

> 9 ready-made Claude skills that turn a sentence into a finished video. Install once, use in every module after this.

**Outcome:** All 9 skills installed and tested. You know which skill to use for any video a client asks for.

**Assignment:** Make one 10–20 second video with three different skills (e.g. a talking-head clip, a logo reveal and an AI voiceover) and post all three.

**Module resources:** R02 The Vibe Editing Skills Pack, R01 Quick Start: Install in 15 Minutes, R04 100 Vibe Editing Prompts

## 2.1 What skills are (and why they're a cheat code)
*video · 5 min*

Skills are expert playbooks for Claude. Here's how they turn "make me a reel" into a pro-level edit, every time.

**Lesson notes**

- A **skill** is a folder of instructions + tools Claude loads automatically when your request matches it.
- Without skills, AI guesses. With skills, it follows **Ideabro's production playbook**: brief, beat table, stills check, mixing rules, export specs.
- Every skill is self-contained: scripts, guides and templates included. Install one or all nine.
- You don't call them by name (but you can). Just describe the video.

## 2.2 Install in 5 minutes (zip and plugin methods)
*video · 7 min*

Two ways to install: unzip into your skills folder, or one command as a Claude Code plugin.

**Resources:** R02 The Vibe Editing Skills Pack, R01 Quick Start: Install in 15 Minutes

**Lesson notes**

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

## 2.3 Your first video with the Start Here skill
*video · 10 min*

Let the Start Here skill pick the right playbook, set up your project and show test frames, all in one conversation.

**Try this prompt:**
> Let's make a video with the Vibe Editing System. I want a 20-second promo for my Instagram page @myhandle. Use defaults.

**Lesson notes**

- The Start Here skill (`vibe-editing-system`) shows a menu of 8 video types and asks what you have (footage? logo? voice?).
- It runs setup, creates the project and renders branded test frames in ~1 minute.
- Then it switches to the matching playbook automatically.
- Say **"teach me as you go"** and it explains every step. Perfect for learning.

## 2.4 Skill: Talking-Head & Creator Videos
*video · 8 min*

Reels from raw takes, podcast clips, YouTube edits, testimonials and course lessons, cut word-accurately.

**Try this prompt:**
> Use vibe-talking-head: make a 45-second reel from raw/take1.mp4, put my strongest line first as the hook, pop captions, punch-in jump cuts.

**Lesson notes**

- Cuts silences, ums and retakes using a word-level transcript.
- Moves your best line to the front as the **hook**.
- Captions: pop / karaoke / clean / minimal, in your brand colours.
- Adds lower-thirds, stickers and music ducked under your voice.

## 2.5 Skill: Launch Videos & Ads
*video · 8 min*

Promos, product launches, social ads with variants, app demos rebuilt as crisp graphics.

**Try this prompt:**
> Use vibe-launch-ads: 25-second launch reel for my course "Vibe Editing", bold and punchy, end card ENROLL NOW, also give me 1:1 and 4:5 versions.

**Lesson notes**

- Follows the launch formula: Hook → Problem → Reveal → Proof → CTA.
- Everything locked to the music's beat.
- Variants (hooks, formats, languages) are re-renders, not re-edits.

## 2.6 Skill: Motion Graphics
*video · 8 min*

Showreels, explainers, kinetic typography, logo reveals, infographics and transparent lower-third packs.

**Try this prompt:**
> Use vibe-motion-graphics: a 6-second logo reveal for assets/logo.png with an impact on the beat and a sparkle.

**Lesson notes**

- Every frame is generated from code, so it's razor sharp at any size.
- Export **transparent packs** (ProRes 4444) to use in Premiere, CapCut or DaVinci.
- Style frames first, animation second.

## 2.7 Skill: Stylised Animation
*video · 8 min*

Claymation, crayon, paper-cut, doodle and talking cartoon mascots with no AI images.

**Try this prompt:**
> Use vibe-stylised-animation: a 20-second claymation short about a sheep who discovers vibe editing at 2am. Wordless, playful music.

**Lesson notes**

- Handmade feel from 3 tricks: **held drawings, boil, texture**.
- Characters blink, look and lip-sync to the voice automatically.

## 2.8 Skill: VFX & Editing Magic
*video · 8 min*

Background swaps, text behind you, layer splits, tracking, cinematic looks and slow motion.

**Try this prompt:**
> Use vibe-vfx: put the word VIBE in huge lime letters behind me in raw/take1.mp4, appearing when I say "vibe".

**Lesson notes**

- Person cut-outs (mattes) in one command.
- Effects start on the exact word you speak.
- Honest feasibility check before promising a client an effect.

## 2.9 Skill: AI Footage → Films
*video · 8 min*

Turn Veo/Sora/Kling clips into a film that doesn't look AI, plus faceless channel episodes.

**Try this prompt:**
> Use vibe-ai-footage: scan the clips in raw/, tell me which are usable, then cut a 60-second brand film to my voiceover raw/vo.mp3.

**Lesson notes**

- Scans every clip for morphs, garbled text and popping objects.
- Retimes shots to land on the narration.
- One grade + grain + sound design so it stops looking like AI.

## 2.10 Skill: Audio, Music & Voiceover
*video · 8 min*

Original copyright-free music, 14 sound effects, AI voiceover (incl. Hindi), audiograms and visualisers.

**Try this prompt:**
> Use vibe-audio-videos: make a chill 30-second music bed and a Hindi AI voiceover of my script in work/script.txt.

**Lesson notes**

- 7 music moods: upbeat, hype, tech, corporate, chill, cinematic, playful.
- Auto-ducking: music dips when someone talks.
- Final mix hits platform loudness (−14 LUFS) automatically.

## 2.11 Skill: Bulk & Automated Videos
*video · 8 min*

100 personalised videos from a spreadsheet, every format in one go, multi-language versions.

**Try this prompt:**
> Use vibe-bulk-videos: make a personalised welcome video for every row in students.csv using their first_name.

**Lesson notes**

- Build one hero template → test 3 rows → render the rest.
- Long names auto-fit. Non-English names supported with the right fonts.
- A report shows every video that rendered (and any that failed).

## 2.12 Updates & what's new
*reading · 3 min*

Where new skill versions are announced and how to update in 1 minute.

**Lesson notes**

- New versions are announced in the community and added to Course Resources.
- **Zip install:** delete the old `vibe-…` folders and unzip the new ones.
- **Plugin install:** run `/plugin update`.
- Changelog
  - **v1.0**: 9 skills, 20 tools, Ideabro house style, 7 music moods, 14 SFX, 4 caption styles.


---

# Module 3: The Director's Brief

> The skill that separates "AI slop" from professional work: telling the AI exactly what you want, in words it can execute.

**Outcome:** You can write a brief and a beat table that gets the edit right on the first render.

**Assignment:** Write a full brief + beat table for a 25-second promo of your own (or a dream client's) product. Share it for feedback before you render.

**Module resources:** R05 Creative Brief Template, R06 Beat Table Template, R07 Vibe Vocabulary: Feelings → Instructions, R08 Feedback Phrasebook: Get It Fixed in One Round, R09 Hook Swipe File: 50 Scroll-Stopping Openers

## 3.1 Anatomy of a great brief
*video · 10 min*

The 7 decisions every video needs. Make them up front and revisions drop by half.

**Resources:** R05 Creative Brief Template

**Lesson notes**

1. **Goal**: what should the viewer think, feel or do?
2. **Audience**: who exactly, and where are they watching?
3. **Platform + format**: Reels 9:16? YouTube 16:9? Both?
4. **Length**: target and hard limit.
5. **Message**: hook, max 3 points, one CTA.
6. **Vibe**: 3 words + references.
7. **Brand**: colours, fonts, logo, handle.
- Template prompt: *"Here's my brief: [paste]. Ask me anything missing in one message, with defaults."*

## 3.2 Beat tables: plan every second
*video · 9 min*

The pro planning tool: a time-by-time table of what we see, hear and read. Get it approved before you render.

**Try this prompt:**
> Draft a beat table for this video with columns time | what we see | what we hear | on-screen text. Keep cuts on the beat.

**Resources:** R06 Beat Table Template

**Lesson notes**

| time | picture | sound | text |
|---|---|---|---|
| 0.0–2.0 | face close-up, punch-in | impact | STOP SCROLLING |
| 2.0–6.0 | problem montage | whoosh + bed | HOURS PER REEL |
- Every row = one idea. If a row has two ideas, split it.
- Approving a beat table takes 2 minutes. Re-rendering takes 10.

## 3.3 Speaking "vibe": style vocabulary
*video · 11 min*

Translate feelings into instructions: what "premium", "punchy", "dreamy" and "cinematic" mean technically.

**Resources:** R07 Vibe Vocabulary: Feelings → Instructions

**Lesson notes**

| you say | the AI does |
|---|---|
| punchy | hard cuts on beats, slams, impacts, 0.2–0.4 s moves |
| premium | slow moves, lots of space, serif titles, muted palette |
| playful | bounce/overshoot, bright colours, pops, glockenspiel |
| cinematic | letterbox, teal-orange grade, slow push-ins, drones |
| dreamy | soft focus, glow, slow fades, pastel, chill bed |
| techy | mono fonts, grids, glitch, scan lines, tech bed |
- Combine 2–3 words max. Contradictions ("calm but frantic") confuse every editor, human or AI.

## 3.4 References & brand kits
*video · 8 min*

How to describe a reference video so the AI copies the *feel*, not the content, and how to set up a brand in one file.

**Resources:** R15 Brand Kit Template

**Lesson notes**

- Describe references as: **pace, type, colour, motion, sound**. E.g. *"pace like a MrBeast intro, type like Apple keynotes."*
- `brand.json` holds colours + fonts. Swap it and every video re-skins.
- No brand? The **Ideabro house style** is the default: ink, paper, lime.

## 3.5 Feedback that works
*video · 9 min*

The phrasing that gets a fix in one round: timestamps, specifics, and one change at a time.

**Try this prompt:**
> At 0:04.2 the title lands late. Put it on the beat. Captions one size smaller and 10% higher.

**Resources:** R08 Feedback Phrasebook: Get It Fixed in One Round

**Lesson notes**

- ❌ "Make it better" → ✅ "The hook needs more energy: faster cut at 0:01 and an impact sound."
- Always include **where** (timestamp), **what** (element), **how** (direction).
- Batch small notes into one message; send big direction changes alone.

## 3.6 Reviewing with stills & contact sheets
*video · 7 min*

How to review a 60-second video in 10 seconds using contact sheets, and what to look for.

**Lesson notes**

- Ask: *"Give me a contact sheet of the final with 12 frames."*
- Check: text inside safe zones, no typos, faces not covered, brand colours, first frame strong.
- Approve stills → then watch the full video once for timing and sound.


---

# Module 4: Talking-Head Editing

> The money module. Raw takes into scroll-stopping reels, podcast clips and YouTube videos: the edits clients pay for every week.

**Outcome:** You can turn any talking-head recording into a tight, captioned, music-backed reel and a YouTube edit.

**Assignment:** Record a 2–3 minute take about anything you know well. Deliver a 45-second reel (9:16) and a clean 16:9 cut with subtitles.

**Module resources:** R10 Caption Style Guide, R09 Hook Swipe File: 50 Scroll-Stopping Openers, R11 Sound Design Cheat Sheet, R13 Platform Export Specs & Safe Zones

## 4.1 Transcribe: every word, timestamped
*video · 9 min*

How Whisper turns speech into word-level timestamps, the foundation of every precise talking-head edit.

**Try this prompt:**
> Transcribe raw/take1.mp4. My name is Priya Sharma and my brand is Ideabro, so spell those right.

**Lesson notes**

- Runs locally and free. First run downloads the model once.
- Give names and jargon up front ("--prompt") so they're spelled right.
- Read `work/transcript.txt`. That's your paper edit. Fix spellings before captions.

## 4.2 Story edit: find the hook, kill the retakes
*video · 12 min*

Edit from the transcript, not the timeline: pick the hook, drop retakes, tighten tangents, end on the payoff.

**Try this prompt:**
> Read the transcript. Suggest the strongest hook line, list retakes to remove, and propose a 45-second cut. Don't render yet.

**Lesson notes**

- **Hook** = bold claim, surprising number, question or result. It goes in the first 2 seconds, even if you said it at minute 2.
- **Retakes**: keep the *last complete* version of a repeated sentence.
- Cut "so, um, hey guys" intros. Start mid-energy.
- End on the payoff or CTA. Cut everything after.

## 4.3 Cut dead air, ums & retakes
*video · 10 min*

Word-accurate silence cutting with natural breathing room, and how to tune pace for Reels vs YouTube.

**Try this prompt:**
> Cut the silences and filler words. Snappy social pace. Move my hook to the front and remove the retake at 12–15 seconds.

**Lesson notes**

| pace | gap setting | use for |
|---|---|---|
| frantic | 0.25 s | hype reels |
| snappy | 0.35 s | Reels/TikTok (default) |
| natural | 0.5 s | YouTube, testimonials |
- Words keep a little padding so nothing gets clipped mid-syllable.

## 4.4 Jump cuts & punch-in zooms
*video · 7 min*

The classic creator look: zoom 8–15% on every other cut, centred on your face.

**Lesson notes**

- Punch-ins hide jump cuts and add energy.
- 1.08–1.12 = subtle, 1.15+ = aggressive.
- Anchor the zoom on the face (usually ~38% from the top). Check stills so the head isn't cropped.

## 4.5 Animated captions that people actually read
*video · 12 min*

Pop, karaoke, clean and minimal styles: when to use each, sizing, safe zones and emphasis words.

**Try this prompt:**
> Add pop captions in my brand colours, highlight the words "free", "secret" and "10x", and keep them above the bottom 420 pixels.

**Resources:** R10 Caption Style Guide

**Lesson notes**

- Most social video is watched with the sound off. **Captions are not optional.**
- **Pop**: 1–3 big words, active word highlighted (Reels/TikTok).
- **Karaoke**: line fills as spoken (lyrics, quotes).
- **Clean**: sentence subtitles on a soft box (YouTube, interviews).
- **Minimal**: small outlined (cinematic, brand films).
- Never cover the mouth or eyes. Also deliver the `.srt` file for YouTube/LinkedIn.

## 4.6 Lower-thirds, B-roll & stickers
*video · 11 min*

Graphics that sit on top of your footage: name titles, emoji pops, progress bars and CTA cards, timed to your words.

**Try this prompt:**
> Add a lower-third with my name and title in the first 3 seconds, a 🔥 sticker that pops when I say "money", and a CTA card at the end.

**Lesson notes**

- Graphics render as a **transparent overlay** and are laid on top, so long videos stay fast.
- Time every graphic to a word in the transcript.
- One graphic at a time. Clutter kills retention.

## 4.7 Podcast → 5 viral clips
*video · 13 min*

Find the best self-contained moments in a long recording, reframe to vertical, caption and export a batch.

**Try this prompt:**
> Here's a 40-minute podcast in raw/. Find the 5 best 30–60 second clips, give me a table with timestamps, title and hook line, then render the ones I pick.

**Lesson notes**

- A good clip: strong first line, makes sense alone, has emotion or a useful insight, ≤ 60 s.
- Two-person podcasts: crop on whoever's speaking, or use a blurred-background vertical.
- Batch export: Reels + Shorts + TikTok in one command.

## 4.8 YouTube long-form, testimonials & course lessons
*video · 14 min*

Three more paying formats: chapters + clean captions for YouTube, warm testimonials, and screen + face-cam lessons.

**Lesson notes**

- **YouTube:** natural pace, punch-in every 5–10 s, chapters from the transcript, subtitles file, graphic every 20–40 s.
- **Testimonial:** gentle cuts, warm grade, name lower-third, chill bed at low volume.
- **Course lesson:** screen recording + round face-cam bubble, zoom into the action, callouts on key clicks.


---

# Module 5: Sound Design & Music in Code

> Sound is half the video. Generate original, copyright-free music, sound effects and voiceovers, and mix like a pro.

**Outcome:** You can score any video with an original bed, place SFX on the right frames, add an AI voiceover and deliver a broadcast-clean mix.

**Assignment:** Take any silent video (or one from Module 4) and give it a full soundtrack: music, 4+ sound effects, ducking and a −14 LUFS master.

**Module resources:** R11 Sound Design Cheat Sheet, R13 Platform Export Specs & Safe Zones

## 5.1 Why we synthesise: no copyright strikes, ever
*video · 6 min*

Why using trending audio in client work is risky, and how generated music solves it forever.

**Lesson notes**

- Music from YouTube/Spotify/TikTok libraries in client deliverables = Content ID claims, muted videos, angry clients.
- The Skills Pack *generates* original music and SFX in code, so they're yours to use commercially.
- Client has a licensed track? Use it, keep the licence note in the project.

## 5.2 Music moods, BPM & the beat grid
*video · 10 min*

7 moods, how tempo shapes energy, and the simple math that makes every cut land on the beat.

**Try this prompt:**
> Make a 30-second hype music bed at 128 BPM and plan my cuts on the bar lines.

**Resources:** R11 Sound Design Cheat Sheet

**Lesson notes**

| mood | BPM | use for |
|---|---|---|
| upbeat | 118 | creators, tutorials |
| hype | 128 | ads, reveals |
| tech | 124 | SaaS, AI |
| corporate | 110 | brand, LinkedIn |
| chill | 84 | vlogs, calm talking heads |
| cinematic | 72 | brand films, trailers |
| playful | 120 | kids, food, fun |
- **beat = 60 ÷ BPM.** At 128 BPM: 1 beat = 0.469 s, 1 bar = 1.875 s, 30 s = 16 bars.
- Cut on bars, accent on beats.

## 5.3 The SFX vocabulary
*video · 9 min*

14 sound effects and exactly when to use each so your edits feel expensive.

**Lesson notes**

- **Whoosh**: transitions (start 0.3 s *before* the cut).
- **Pop**: text and stickers appearing.
- **Impact / bass drop**: hooks, reveals, title slams.
- **Riser**: build into the big moment.
- **Click / typing**: UI, prompts.
- **Sparkle / ding**: magic, success.
- 3–6 accents per 30 s. More = noise.

## 5.4 AI voiceover (English, Hindi & more)
*video · 11 min*

Natural local AI voices for explainers, ads and faceless content, line by line, with timings.

**Try this prompt:**
> Turn work/script.txt into a voiceover with a warm female voice at normal speed, then give me word timings.

**Lesson notes**

- Write as people speak: short sentences, numbers in words, acronyms spelled out ("A.I.").
- One line per take, so you can regenerate a single line without redoing everything.
- Hindi voices included. Always have a native speaker listen once.

## 5.5 Mixing: ducking, levels & loudness
*video · 10 min*

Voice on top, music under, SFX accents, and a final master at platform loudness. All automatic, once you know the rules.

**Lesson notes**

| element | level |
|---|---|
| voice | 0 dB (reference) |
| music under voice | −8 to −12 dB, ducked 10 dB while speaking |
| SFX | −6 to −12 dB (impacts up to −3) |
| final master | −14 LUFS social, −16 LUFS podcast/web |
- Listen on phone speakers *and* headphones before delivery.

## 5.6 Fix bad audio
*video · 8 min*

Clean up noisy phone audio: high-pass, denoise, compression and de-essing in one command.

**Try this prompt:**
> Clean up the voice in raw/take1.mp4: remove background hiss and harsh S sounds, then re-mix with a chill bed.

**Lesson notes**

- Fixes: hiss, rumble, uneven volume, harsh "S" sounds.
- Can't fully fix: heavy echo, music bleeding under speech, clipping. **Re-record if possible.**
- Recording tip for students: a ₹500 lav mic beats any AI cleanup.


---

# Module 6: Launch Videos

> Videos that sell. Promos, product launches and social ads with a clear hook, one message and a CTA, all locked to the beat.

**Outcome:** You can produce a 25-second launch reel plus format and hook variants ready for ads.

**Assignment:** Make a 25-second launch reel for a real or imaginary product, in 9:16 + 1:1, with 2 different hooks. Post both hooks and let the community vote.

**Module resources:** R09 Hook Swipe File: 50 Scroll-Stopping Openers, R05 Creative Brief Template, R06 Beat Table Template, R13 Platform Export Specs & Safe Zones, R15 Brand Kit Template

## 6.1 The launch formula
*video · 10 min*

Hook → Problem → Reveal → Proof → CTA. The 25-second structure behind most ads that convert.

**Lesson notes**

| beat | job | time |
|---|---|---|
| Hook | stop the scroll | 0–3 s |
| Problem | name the pain in their words | 3–7 s |
| Reveal | product/offer appears on a bar line | 7–11 s |
| Proof | 3 benefits max, numbers, faces | 11–20 s |
| CTA | what to do now | 20–25 s |
- One video = one message. Two messages = two videos.

## 6.2 Hooks that stop the scroll
*video · 12 min*

10 proven hook patterns, how to animate each, and how to test them against each other.

**Try this prompt:**
> Give me 5 hook options for my launch video, each with on-screen text and the visual, then render the top 2 as variants.

**Resources:** R09 Hook Swipe File: 50 Scroll-Stopping Openers

**Lesson notes**

- Pattern interrupt: a crumpling timeline, a smash, a glitch.
- Bold claim: *"I made 10 reels in 1 hour."*
- Painful question: *"Still editing like it's 2015?"*
- Before/after split screen.
- A typed prompt + instant result (the vibe editing signature).
- The hook must work **muted**: big text + motion + contrast.

## 6.3 Building scenes: kinetic type, chips, counters
*video · 14 min*

The building blocks of every promo: slamming titles, benefit chips, counters, highlight bars and end cards.

**Try this prompt:**
> Build scene 2 as three benefit chips that pop in on the beat: CUTS, CAPTIONS, MUSIC. Lime and periwinkle, mono font.

**Lesson notes**

- Max 6 words per card, verbs first.
- Stagger builds by ~80 ms per item.
- Every pop gets a pop sound. Every reveal gets an impact.
- Check stills before animating.

## 6.4 Product hero shots & cut-outs
*video · 9 min*

Turn a product photo into a floating, shadowed hero shot with price and benefit callouts.

**Try this prompt:**
> Cut out raw/product.jpg, make it float with a soft shadow and slow push-in, and add a price card "₹999 today only".

**Lesson notes**

- One command removes the background from photos.
- Soft shadow + slight float + slow push-in = premium.
- Prices and claims exactly as the client wrote them.

## 6.5 App & SaaS demos (without blurry screen recordings)
*video · 12 min*

Rebuild the key screens as crisp vector UI inside a phone or laptop frame, then animate taps and typing.

**Lesson notes**

- Screen recordings scaled up look soft. Rebuilt UI stays razor sharp in any format.
- Show 2–4 key screens only: the problem moment, the magic moment, the result.
- Animate: tap ripples, typing, highlight boxes, smooth screen transitions.

## 6.6 Variants: formats, hooks & cut-downs
*video · 10 min*

Turn one ad into 9:16, 4:5, 1:1, 16:9, two hooks, and 15 s + 6 s cut-downs without re-editing.

**Try this prompt:**
> Render this ad in 9:16, 4:5 and 1:1, plus a 15-second cut-down with just hook, reveal and CTA.

**Lesson notes**

- Design once in relative units → every format adapts. Check stills per format.
- 15 s = hook + reveal + CTA. 6 s bumper = logo hit + one line + CTA.
- Name files clearly: `brand_launch_hookA_9x16_v1.mp4`.

## 6.7 Event teasers, countdowns & testimonials
*video · 9 min*

Three bonus formats clients ask for: event/webinar teasers, countdowns, and testimonial compilations.

**Lesson notes**

- **Teaser:** date-time card, speaker cards, "save your seat".
- **Countdown:** big numbers on beats, final number = impact + reveal.
- **Testimonial compilation:** face clips + quote cards in brand style, the best line first.


---

# Module 7: Motion Graphics

> Studio-quality motion design from a prompt: explainers, kinetic typography, logo reveals, infographics and transparent title packs.

**Outcome:** You can design style frames, animate them with professional timing and deliver motion packs other editors can use.

**Assignment:** Create a 20-second showreel with 4 sections (kinetic type, shapes, data, logo outro) in 16:9, plus one transparent lower-third.

**Module resources:** R12 Motion & Easing Cheat Sheet, R11 Sound Design Cheat Sheet, R13 Platform Export Specs & Safe Zones

## 7.1 Every frame is a function of time
*video · 8 min*

The one idea behind code-based motion design, and why it makes changes instant.

**Lesson notes**

- Each frame is drawn from scratch for a moment `t`. Nothing is "keyframed".
- That's why you can render any single frame instantly (stills), render in parallel, and change timings without breaking anything.
- You direct in timings and feelings. The AI handles the math.

## 7.2 Style frames first, animation second
*video · 10 min*

Approve the look of each section as a still before animating. This is how studios avoid wasted renders.

**Try this prompt:**
> Before animating, show me the key still of each section so I can approve the look.

**Lesson notes**

- Most revisions are about **design** (layout, type, colour), not motion.
- Approve 3–5 stills → then animate.
- Keep max 2 typefaces and 1 accent colour per screen.

## 7.3 Easing & timing: why things feel alive
*video · 12 min*

Ease-out, back, expo, bounce, spring: what each communicates and the timing rules pros follow.

**Resources:** R12 Motion & Easing Cheat Sheet

**Lesson notes**

| intent | easing | duration |
|---|---|---|
| arrive | ease-out expo/cubic | 0.3–0.5 s |
| playful arrive | back / spring | 0.4–0.6 s |
| leave | ease-in | 0.2–0.35 s |
| move across | ease-in-out | 0.5–0.9 s |
- Exits are faster than entrances.
- Never linear for anything that starts or stops.

## 7.4 Kinetic typography
*video · 12 min*

Word slams, staggers, highlight bars, typewriters and masked reveals, synced to voice or beat.

**Try this prompt:**
> Kinetic typography for my voiceover: each word slams in on the exact moment I say it, key words in lime with an impact sound.

**Lesson notes**

- Sync to voice: transcribe → each word animates at its timestamp.
- Reading time: 0.3 s per word + 0.5 s.
- Emphasis = size, colour, or motion. Pick one per word.

## 7.5 Logo reveals & intros
*video · 9 min*

Build a 3–6 second logo reveal from shapes, masks and an impact sound.

**Try this prompt:**
> Make a 5-second logo reveal: the logo assembles from 3 shapes, lands on the downbeat with an impact and sparkle, then the tagline types in.

**Lesson notes**

- Split the logo into parts → animate in → land on the full logo + sound.
- Hold the final logo at least 1.5 s.
- Provide transparent and solid-background versions.

## 7.6 Data & infographic videos
*video · 11 min*

Animated bar charts, lines that draw on, counters and timelines with numbers that are always exact.

**Lesson notes**

- Bars grow with ease-out. Lines draw on. Counters race with ease-out-expo.
- Label units and sources on screen.
- Numbers are copied exactly from the client. Never "rounded for style".

## 7.7 Transparent packs: lower-thirds, titles, transitions
*video · 10 min*

Export alpha-channel ProRes files you can sell or drop into Premiere, CapCut or DaVinci.

**Try this prompt:**
> Make a pack of 5 transparent lower-thirds in my brand, each 4 seconds with in-hold-out animation, plus a preview sheet.

**Lesson notes**

- Transparent = no background painted. Exported as ProRes 4444 `.mov`.
- One file per element, 3–6 s each.
- Check over dark AND light backgrounds. 💡 Packs are a sellable digital product.

## 7.8 Advanced: shaders & WebGL looks
*video · 8 min*

For liquid, glow and particle-heavy looks: render HTML/WebGL scenes headlessly into video.

**Lesson notes**

- Use for GPU looks: liquid gradients, bloom, thousands of particles, 3D.
- Everything else: stick to the standard engine (simpler, faster).
- Needs a one-time browser install (`npx playwright install chromium`).


---

# Module 8: Stylised Animation & Characters

> Handmade looks without AI images: claymation, crayon, paper-cut and cartoon mascots that blink, bounce and talk.

**Outcome:** You can make a 30–40 second stylised short with a character, a story arc and cartoon sound design.

**Assignment:** Create a 30-second animated short in the medium of your choice (clay, crayon, paper or doodle) with a mascot that reacts to something. Wordless or narrated.

**Module resources:** R12 Motion & Easing Cheat Sheet, R11 Sound Design Cheat Sheet

## 8.1 Faking a medium: held drawings, boil, texture
*video · 10 min*

The three tricks that make code look handmade, and why "smooth" is the enemy.

**Lesson notes**

- **Held drawings:** animate at 12 drawings/second (on twos), not a smooth 24/30.
- **Boil:** outlines re-wobble slightly each drawing, like real clay or crayon.
- **Texture:** paper grain, clay thumbprints, crayon tooth.
- Subtle beats strong: boil ≈ 2–3% of the shape's size.

## 8.2 Claymation
*video · 12 min*

Soft 3D clay shading, cast shadows, flicker and miniature-set depth. Plasticine without the plasticine.

**Try this prompt:**
> Make a 15-second claymation scene: a lavender clay blob character bounces onto a table, looks at the camera and blinks. Playful music, boing on each landing.

**Lesson notes**

- Clay = soft radial lighting + darker rim + soft highlight + cast shadow.
- Add exposure flicker per drawing and blurred background layers for a "miniature set".
- Squash on landing, stretch while falling.

## 8.3 Crayon & hand-drawn
*video · 10 min*

Scribble fills, shaky double outlines and sketch-on reveals on warm paper.

**Try this prompt:**
> Crayon-style 20-second explainer: a sun, a laptop and a coffee cup get sketched on, then coloured in, one per sentence of my voiceover.

**Lesson notes**

- Outline drawn twice by a "shaky hand", then zig-zag hatched fill.
- Reveal = draw the outline on, then colour in.
- Fonts: Luckiest Guy, Gochi Hand, Caveat Brush.

## 8.4 Paper-cut & stop-motion
*video · 9 min*

Flat paper layers, drop shadows, parallax and torn-paper wipes.

**Lesson notes**

- Flat colours + soft drop shadows between layers.
- Background layers move slower than foreground (parallax).
- Transitions: torn-paper shapes sliding across.

## 8.5 Characters that blink, look and talk
*video · 13 min*

Build a simple mascot rig: eyes that blink irregularly and look at things, a mouth that lip-syncs to the voice.

**Try this prompt:**
> Give my mascot eyes that look at whatever is moving, natural blinks, and a mouth that talks along with work/vo.wav.

**Lesson notes**

- Eyes look at the important thing **a beat before** the body moves.
- Irregular blinks feel alive. Regular blinks feel robotic.
- Lip-flap from the voice's loudness is convincing for cartoons.
- Keep characters "on model": same colours and proportions every shot.

## 8.6 Story structure for 30-second shorts
*video · 10 min*

Setup → problem → turn → payoff → end card. Plus gag timing that actually lands.

**Lesson notes**

- 4–6 shots, ONE acting beat per shot.
- Gag = set-up → pause → hit (the hit on a beat with a sound).
- Readable with the sound off: clear poses and silhouettes.
- End card holds ≥ 2 s.


---

# Module 9: AI Footage & Advanced VFX

> Premium films from AI clips and phone footage: cut-outs, text behind you, tracking, cinematic looks, and AI footage that doesn't look AI.

**Outcome:** You can QC and assemble AI clips into a brand film, and add pro VFX to real footage, word-locked to speech.

**Assignment:** Either (A) a 45–60 second brand film from 5+ AI clips with voiceover and real graphics, or (B) a 20-second talking-head with 3 VFX moments triggered by your words.

**Module resources:** R14 AI Footage QC Checklist, R11 Sound Design Cheat Sheet, R13 Platform Export Specs & Safe Zones, R12 Motion & Easing Cheat Sheet

## 9.1 Why AI clips look "AI" (and the fix)
*video · 9 min*

The 6 tell-tale artifacts of generated video and the editing habits that hide them.

**Resources:** R14 AI Footage QC Checklist

**Lesson notes**

- Tells: morphing hands/faces, garbled text, popping objects, melting geometry, flicker, too-smooth "plastic" look.
- Fix habits: short shots (1.5–4 s), cut before clips degrade, one grade + grain, real text and logos, real sound design.

## 9.2 Scan & select: QC every clip
*video · 11 min*

Automatic contact sheets and instability detection for every clip, then a usable-ranges list.

**Try this prompt:**
> Scan all clips in raw/ and give me a table of which are usable, the exact usable ranges, and what's wrong with the rest.

**Lesson notes**

- Review every sheet. The last 0.5–1 s of generated clips often degrades.
- Mark usable ranges → those become your edit list.
- Missing a shot? Ask for regeneration prompts or replace it with a graphic or real photo.

## 9.3 Assemble to the voiceover
*video · 12 min*

Map narration lines to shots, retime each shot to land on its words, and add transitions that don't feel cheap.

**Try this prompt:**
> Cut the usable clips to my voiceover: one shot per sentence, cut on the key words, mostly hard cuts, fade only for time jumps.

**Lesson notes**

- Keep speed changes between 0.7× and 1.4× so motion stays natural.
- Photos can be shots too (slow push-in = Ken Burns).
- Cut on the words that matter.

## 9.4 One grade to rule them all
*video · 9 min*

Unify mismatched clips with one look, film grain and a vignette. The single biggest "not AI" upgrade.

**Try this prompt:**
> Grade everything with the same clean-bright look at 80%, add subtle grain and a light vignette. Show me before/after.

**Lesson notes**

- Looks: natural, warm, cool, teal-orange, cinematic, moody, clean-bright, pastel, punchy, vintage, B&W, noir.
- Same look + same strength on every shot.
- A little grain hides the AI "plastic" smoothness.

## 9.5 Cut-outs & text behind you
*video · 12 min*

Remove or replace backgrounds and put giant text between you and the wall. The most viral VFX trick.

**Try this prompt:**
> Put the word VIBE in huge lime letters behind me, appearing when I say "vibe", and replace the background with a soft blur.

**Lesson notes**

- Best results: subject clearly separated from the background, good light, little motion blur.
- Best hair edges: the high-quality model (slower).
- Text behind subject = background → text → you on top.

## 9.6 Tracking, layers & "remove me"
*video · 13 min*

Stick graphics to a moving hand, split a shot into 3D-style layers, make yourself disappear into particles.

**Lesson notes**

- **Tracking:** follow a point frame by frame and attach a logo/label. Hide it when tracking is lost.
- **Layer split:** background / you / text, separated with depth and parallax.
- **Remove me:** a clean empty background + you fading into particles.
- Be honest with clients: if an effect will look rough, offer a stylised alternative.

## 9.7 Cinematic looks, slow-mo & speed ramps
*video · 9 min*

Letterbox, film grade, serif titles, optical-flow slow motion and speed ramps.

**Try this prompt:**
> Make it cinematic: 2.39 letterbox, teal-orange grade, slow push-in, serif titles, and slow-mo on the walk-in at 0:03.

**Lesson notes**

- Optical-flow slow-mo is smooth on gentle motion. Fast motion can warp, so check stills.
- Speed ramp = normal → slow → normal across segments.
- On vertical video, use thin cinematic bars instead of full 2.39.

## 9.8 "Say it, it happens" edits
*video · 11 min*

The signature Vibe Editing reel: speak your edit directions on camera and every effect starts on the exact word.

**Try this prompt:**
> In raw/take1.mp4 I say my edit directions out loud. Transcribe it and build each effect on the word that asks for it.

**Lesson notes**

- Record with clear directions: "zoom in on my hand", "put my logo here", "remove me".
- Every effect starts on its trigger word and ends before the next.
- This format is a portfolio magnet. Make one for yourself.

## 9.9 Faceless channels: script → episode
*video · 12 min*

A repeatable pipeline: script, AI voice, visuals per sentence, pop captions, music and export.

**Try this prompt:**
> Turn work/script.txt into a 60-second faceless Short: AI voice, one visual per sentence, pop captions, tech music bed, export for Shorts and Reels.

**Lesson notes**

- Script: hook line, 3 points, CTA. Written as spoken.
- Save the pipeline as a one-command script → every new episode is "write script, run".
- Batch many episodes with the Bulk skill (Module 10).


---

# Module 10: Bulk, Workflow & Getting Paid

> Turn the skill into income: bulk production, delivery that looks professional, pricing, proposals and your portfolio.

**Outcome:** You have a portfolio, a price list, a proposal template and a delivery workflow, and you've completed a client-style capstone.

**Assignment:** Capstone: complete a full client-style job (brief → beat table → stills approval → render → 1 revision → multi-platform delivery) and submit the folder + final videos.

**Module resources:** R16 Client Proposal Template (one page), R17 Pricing & Packages Guide, R18 Delivery Checklist, R19 Troubleshooting Guide, R20 The 30-Day Vibe Editing Challenge, R13 Platform Export Specs & Safe Zones

## 10.1 Bulk videos from a spreadsheet
*video · 12 min*

One hero template → 100 personalised videos. Test 3 rows, then render the rest with a report.

**Try this prompt:**
> Make a personalised welcome video for every row in students.csv using first_name and course. Test the first 3 rows before rendering all.

**Lesson notes**

- Collect samples including the **longest** names. That's where templates break.
- Clean data first: spaces, capitals, empty fields, duplicates.
- The report lists every video: ok / skipped / failed.
- 💰 Personalised video is a premium service: sales outreach, onboarding, events.

## 10.2 One edit → every format & language
*video · 10 min*

9:16, 4:5, 1:1 and 16:9 from one design, plus translated voiceover and captions per language.

**Lesson notes**

- Design in relative units → re-render per format → check stills.
- Translation: same number of sentences so timings hold.
- Non-Latin scripts need the right fonts (Devanagari, Japanese...).
- Always have a native speaker check one version.

## 10.3 Render faster: drafts, sections & templates
*video · 8 min*

Stills in seconds, half-res drafts, rendering just one section, and turning past projects into templates.

**Lesson notes**

- Stills → draft → final. Never full-render to check a typo.
- Render only the changed section when fixing one moment.
- Every finished project is a template: *"Save this style so the next one is a one-liner."*

## 10.4 Delivery like a pro
*video · 9 min*

File naming, platform exports, subtitles, thumbnails, contact sheets and licence notes.

**Resources:** R18 Delivery Checklist, R13 Platform Export Specs & Safe Zones

**Lesson notes**

- Names: `client_project_format_v2.mp4`.
- Deliver: platform exports + `.srt` + thumbnail still + contact sheet.
- Note licences: fonts (OFL), music (generated original), footage source.
- Keep every version. Never overwrite what the client has seen.

## 10.5 Pricing your Vibe Editing services
*video · 14 min*

Packages, per-video vs retainer pricing, and how to price on value, not hours, when AI does the heavy lifting.

**Resources:** R17 Pricing & Packages Guide

**Lesson notes**

- Sell **outcomes and turnaround**, not hours. Your speed is your margin.
- Typical packages: Reel pack (8–12 reels/month), Launch kit (promo + variants + cut-downs), Motion pack (titles + lower-thirds), Personalised campaign (per-video pricing at volume).
- Always include: revision rounds (2), formats, turnaround time.
- Retainers > one-offs.

## 10.6 Proposals, briefs & client communication
*video · 11 min*

A one-page proposal, a brief the client fills, and the update rhythm that makes clients trust you.

**Resources:** R16 Client Proposal Template (one page), R05 Creative Brief Template

**Lesson notes**

- Proposal: their goal → your plan → deliverables → timeline → price → next step.
- Send the brief template before the first call.
- Every update = file + contact sheet + 1–3 specific questions.

## 10.7 Build your portfolio in a weekend
*video · 10 min*

The 6 portfolio pieces that cover what clients buy, and how to package them into a showreel.

**Lesson notes**

1. A talking-head reel with pop captions
2. A launch promo + 1:1 variant
3. A logo reveal
4. A stylised short (clay/crayon)
5. A "say it, it happens" VFX reel
6. A before/after (raw vs edited)
- Cut your best 3 seconds of each into a 30-second showreel (Module 7).

## 10.8 Capstone: a full client-style project
*assignment · 60 min*

Put it all together: brief → beat table → stills → draft → final → revision → multi-platform delivery.

**Resources:** R05 Creative Brief Template, R06 Beat Table Template, R18 Delivery Checklist

**Lesson notes**

- Pick a real business (a friend's café, your own brand, a local gym).
- Submit: brief.md, beat table, contact sheets, final exports, revisions log.
- Graded on: hook strength, clarity, brand consistency, sound, delivery quality.
- 🏆 Top capstones get featured on the Ideabro Studio page.
