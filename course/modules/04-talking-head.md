# Module 4: Talking-Head Editing
> The money module. Raw takes into scroll-stopping reels, podcast clips and YouTube videos: the edits clients pay for every week.
Outcome: You can turn any talking-head recording into a tight, captioned, music-backed reel and a YouTube edit.
Assignment: Record a 2–3 minute take about anything you know well. Deliver a 45-second reel (9:16) and a clean 16:9 cut with subtitles.
Resources: R10, R09, R11, R13

## Transcribe: every word, timestamped | video | 9 min
Summary: How Whisper turns speech into word-level timestamps, the foundation of every precise talking-head edit.
Prompt: Transcribe raw/take1.mp4. My name is Priya Sharma and my brand is Ideabro, so spell those right.
### Notes
- Runs locally and free. First run downloads the model once.
- Give names and jargon up front ("--prompt") so they're spelled right.
- Read `work/transcript.txt`. That's your paper edit. Fix spellings before captions.

## Story edit: find the hook, kill the retakes | video | 12 min
Summary: Edit from the transcript, not the timeline: pick the hook, drop retakes, tighten tangents, end on the payoff.
Prompt: Read the transcript. Suggest the strongest hook line, list retakes to remove, and propose a 45-second cut. Don't render yet.
### Notes
- **Hook** = bold claim, surprising number, question or result. It goes in the first 2 seconds, even if you said it at minute 2.
- **Retakes**: keep the *last complete* version of a repeated sentence.
- Cut "so, um, hey guys" intros. Start mid-energy.
- End on the payoff or CTA. Cut everything after.

## Cut dead air, ums & retakes | video | 10 min
Summary: Word-accurate silence cutting with natural breathing room, and how to tune pace for Reels vs YouTube.
Prompt: Cut the silences and filler words. Snappy social pace. Move my hook to the front and remove the retake at 12–15 seconds.
### Notes
| pace | gap setting | use for |
|---|---|---|
| frantic | 0.25 s | hype reels |
| snappy | 0.35 s | Reels/TikTok (default) |
| natural | 0.5 s | YouTube, testimonials |
- Words keep a little padding so nothing gets clipped mid-syllable.

## Jump cuts & punch-in zooms | video | 7 min
Summary: The classic creator look: zoom 8–15% on every other cut, centred on your face.
### Notes
- Punch-ins hide jump cuts and add energy.
- 1.08–1.12 = subtle, 1.15+ = aggressive.
- Anchor the zoom on the face (usually ~38% from the top). Check stills so the head isn't cropped.

## Animated captions that people actually read | video | 12 min
Summary: Pop, karaoke, clean and minimal styles: when to use each, sizing, safe zones and emphasis words.
Resources: R10
Prompt: Add pop captions in my brand colours, highlight the words "free", "secret" and "10x", and keep them above the bottom 420 pixels.
### Notes
- Most social video is watched with the sound off. **Captions are not optional.**
- **Pop**: 1–3 big words, active word highlighted (Reels/TikTok).
- **Karaoke**: line fills as spoken (lyrics, quotes).
- **Clean**: sentence subtitles on a soft box (YouTube, interviews).
- **Minimal**: small outlined (cinematic, brand films).
- Never cover the mouth or eyes. Also deliver the `.srt` file for YouTube/LinkedIn.

## Lower-thirds, B-roll & stickers | video | 11 min
Summary: Graphics that sit on top of your footage: name titles, emoji pops, progress bars and CTA cards, timed to your words.
Prompt: Add a lower-third with my name and title in the first 3 seconds, a 🔥 sticker that pops when I say "money", and a CTA card at the end.
### Notes
- Graphics render as a **transparent overlay** and are laid on top, so long videos stay fast.
- Time every graphic to a word in the transcript.
- One graphic at a time. Clutter kills retention.

## Podcast → 5 viral clips | video | 13 min
Summary: Find the best self-contained moments in a long recording, reframe to vertical, caption and export a batch.
Prompt: Here's a 40-minute podcast in raw/. Find the 5 best 30–60 second clips, give me a table with timestamps, title and hook line, then render the ones I pick.
### Notes
- A good clip: strong first line, makes sense alone, has emotion or a useful insight, ≤ 60 s.
- Two-person podcasts: crop on whoever's speaking, or use a blurred-background vertical.
- Batch export: Reels + Shorts + TikTok in one command.

## YouTube long-form, testimonials & course lessons | video | 14 min
Summary: Three more paying formats: chapters + clean captions for YouTube, warm testimonials, and screen + face-cam lessons.
### Notes
- **YouTube:** natural pace, punch-in every 5–10 s, chapters from the transcript, subtitles file, graphic every 20–40 s.
- **Testimonial:** gentle cuts, warm grade, name lower-third, chill bed at low volume.
- **Course lesson:** screen recording + round face-cam bubble, zoom into the action, callouts on key clicks.
