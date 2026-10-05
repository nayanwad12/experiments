# Module 7: Motion Graphics
> Studio-quality motion design from a prompt: explainers, kinetic typography, logo reveals, infographics and transparent title packs.
Outcome: You can design style frames, animate them with professional timing and deliver motion packs other editors can use.
Assignment: Create a 20-second showreel with 4 sections (kinetic type, shapes, data, logo outro) in 16:9, plus one transparent lower-third.
Resources: R12, R11, R13

## Every frame is a function of time | video | 8 min
Summary: The one idea behind code-based motion design, and why it makes changes instant.
### Notes
- Each frame is drawn from scratch for a moment `t`. Nothing is "keyframed".
- That's why you can render any single frame instantly (stills), render in parallel, and change timings without breaking anything.
- You direct in timings and feelings. The AI handles the math.

## Style frames first, animation second | video | 10 min
Summary: Approve the look of each section as a still before animating. This is how studios avoid wasted renders.
Prompt: Before animating, show me the key still of each section so I can approve the look.
### Notes
- Most revisions are about **design** (layout, type, colour), not motion.
- Approve 3–5 stills → then animate.
- Keep max 2 typefaces and 1 accent colour per screen.

## Easing & timing: why things feel alive | video | 12 min
Summary: Ease-out, back, expo, bounce, spring: what each communicates and the timing rules pros follow.
Resources: R12
### Notes
| intent | easing | duration |
|---|---|---|
| arrive | ease-out expo/cubic | 0.3–0.5 s |
| playful arrive | back / spring | 0.4–0.6 s |
| leave | ease-in | 0.2–0.35 s |
| move across | ease-in-out | 0.5–0.9 s |
- Exits are faster than entrances.
- Never linear for anything that starts or stops.

## Kinetic typography | video | 12 min
Summary: Word slams, staggers, highlight bars, typewriters and masked reveals, synced to voice or beat.
Prompt: Kinetic typography for my voiceover: each word slams in on the exact moment I say it, key words in lime with an impact sound.
### Notes
- Sync to voice: transcribe → each word animates at its timestamp.
- Reading time: 0.3 s per word + 0.5 s.
- Emphasis = size, colour, or motion. Pick one per word.

## Logo reveals & intros | video | 9 min
Summary: Build a 3–6 second logo reveal from shapes, masks and an impact sound.
Prompt: Make a 5-second logo reveal: the logo assembles from 3 shapes, lands on the downbeat with an impact and sparkle, then the tagline types in.
### Notes
- Split the logo into parts → animate in → land on the full logo + sound.
- Hold the final logo at least 1.5 s.
- Provide transparent and solid-background versions.

## Data & infographic videos | video | 11 min
Summary: Animated bar charts, lines that draw on, counters and timelines with numbers that are always exact.
### Notes
- Bars grow with ease-out. Lines draw on. Counters race with ease-out-expo.
- Label units and sources on screen.
- Numbers are copied exactly from the client. Never "rounded for style".

## Transparent packs: lower-thirds, titles, transitions | video | 10 min
Summary: Export alpha-channel ProRes files you can sell or drop into Premiere, CapCut or DaVinci.
Prompt: Make a pack of 5 transparent lower-thirds in my brand, each 4 seconds with in-hold-out animation, plus a preview sheet.
### Notes
- Transparent = no background painted. Exported as ProRes 4444 `.mov`.
- One file per element, 3–6 s each.
- Check over dark AND light backgrounds. 💡 Packs are a sellable digital product.

## Advanced: shaders & WebGL looks | video | 8 min
Summary: For liquid, glow and particle-heavy looks: render HTML/WebGL scenes headlessly into video.
### Notes
- Use for GPU looks: liquid gradients, bloom, thousands of particles, 3D.
- Everything else: stick to the standard engine (simpler, faster).
- Needs a one-time browser install (`npx playwright install chromium`).
