# Module 9: AI Footage & Advanced VFX
> Premium films from AI clips and phone footage: cut-outs, text behind you, tracking, cinematic looks, and AI footage that doesn't look AI.
Outcome: You can QC and assemble AI clips into a brand film, and add pro VFX to real footage, word-locked to speech.
Assignment: Either (A) a 45–60 second brand film from 5+ AI clips with voiceover and real graphics, or (B) a 20-second talking-head with 3 VFX moments triggered by your words.
Resources: R14, R11, R13, R12

## Why AI clips look "AI" (and the fix) | video | 9 min
Summary: The 6 tell-tale artifacts of generated video and the editing habits that hide them.
Resources: R14
### Notes
- Tells: morphing hands/faces, garbled text, popping objects, melting geometry, flicker, too-smooth "plastic" look.
- Fix habits: short shots (1.5–4 s), cut before clips degrade, one grade + grain, real text and logos, real sound design.

## Scan & select: QC every clip | video | 11 min
Summary: Automatic contact sheets and instability detection for every clip, then a usable-ranges list.
Prompt: Scan all clips in raw/ and give me a table of which are usable, the exact usable ranges, and what's wrong with the rest.
### Notes
- Review every sheet. The last 0.5–1 s of generated clips often degrades.
- Mark usable ranges → those become your edit list.
- Missing a shot? Ask for regeneration prompts or replace it with a graphic or real photo.

## Assemble to the voiceover | video | 12 min
Summary: Map narration lines to shots, retime each shot to land on its words, and add transitions that don't feel cheap.
Prompt: Cut the usable clips to my voiceover: one shot per sentence, cut on the key words, mostly hard cuts, fade only for time jumps.
### Notes
- Keep speed changes between 0.7× and 1.4× so motion stays natural.
- Photos can be shots too (slow push-in = Ken Burns).
- Cut on the words that matter.

## One grade to rule them all | video | 9 min
Summary: Unify mismatched clips with one look, film grain and a vignette. The single biggest "not AI" upgrade.
Prompt: Grade everything with the same clean-bright look at 80%, add subtle grain and a light vignette. Show me before/after.
### Notes
- Looks: natural, warm, cool, teal-orange, cinematic, moody, clean-bright, pastel, punchy, vintage, B&W, noir.
- Same look + same strength on every shot.
- A little grain hides the AI "plastic" smoothness.

## Cut-outs & text behind you | video | 12 min
Summary: Remove or replace backgrounds and put giant text between you and the wall. The most viral VFX trick.
Prompt: Put the word VIBE in huge lime letters behind me, appearing when I say "vibe", and replace the background with a soft blur.
### Notes
- Best results: subject clearly separated from the background, good light, little motion blur.
- Best hair edges: the high-quality model (slower).
- Text behind subject = background → text → you on top.

## Tracking, layers & "remove me" | video | 13 min
Summary: Stick graphics to a moving hand, split a shot into 3D-style layers, make yourself disappear into particles.
### Notes
- **Tracking:** follow a point frame by frame and attach a logo/label. Hide it when tracking is lost.
- **Layer split:** background / you / text, separated with depth and parallax.
- **Remove me:** a clean empty background + you fading into particles.
- Be honest with clients: if an effect will look rough, offer a stylised alternative.

## Cinematic looks, slow-mo & speed ramps | video | 9 min
Summary: Letterbox, film grade, serif titles, optical-flow slow motion and speed ramps.
Prompt: Make it cinematic: 2.39 letterbox, teal-orange grade, slow push-in, serif titles, and slow-mo on the walk-in at 0:03.
### Notes
- Optical-flow slow-mo is smooth on gentle motion. Fast motion can warp, so check stills.
- Speed ramp = normal → slow → normal across segments.
- On vertical video, use thin cinematic bars instead of full 2.39.

## "Say it, it happens" edits | video | 11 min
Summary: The signature Vibe Editing reel: speak your edit directions on camera and every effect starts on the exact word.
Prompt: In raw/take1.mp4 I say my edit directions out loud. Transcribe it and build each effect on the word that asks for it.
### Notes
- Record with clear directions: "zoom in on my hand", "put my logo here", "remove me".
- Every effect starts on its trigger word and ends before the next.
- This format is a portfolio magnet. Make one for yourself.

## Faceless channels: script → episode | video | 12 min
Summary: A repeatable pipeline: script, AI voice, visuals per sentence, pop captions, music and export.
Prompt: Turn work/script.txt into a 60-second faceless Short: AI voice, one visual per sentence, pop captions, tech music bed, export for Shorts and Reels.
### Notes
- Script: hook line, 3 points, CTA. Written as spoken.
- Save the pipeline as a one-command script → every new episode is "write script, run".
- Batch many episodes with the Bulk skill (Bulk, Workflow & Getting Paid module).
