# editorial-reel: "Same reel. Two editors." (16:9)

A 35.8 second, 1920×1080, 30 fps motion piece built from one ElevenLabs narration. It's a straight full-frame video, not the laptop layout.

**Look:** grey studio paper with a soft vignette and grain, acid-yellow panels, heavy tight grotesk type with soft drop shadows, halftone objects with baked shadows (retro computer, alarm clock, enter key, phones, film reel and frames), viewfinder corner brackets, tiny serif text blocks with a rule-and-dot, ghosted and extruded type, and a handwritten "edit by" sign-off.

**Watch:** [`out/two_editors_16x9.mp4`](out/two_editors_16x9.mp4)

## Structure

| time | narration | picture |
| --- | --- | --- |
| 0.0 | "Same reel." | yellow disc, halftone film reel rolling in, "same / reel." |
| 1.0 | "Two editors." | yellow panel slides in, split screen: **EDITOR 01** on paper, **EDITOR 02** on yellow |
| 2.3 | "Editor one opens the timeline." | left half widens; halftone computer drops in, timeline builds on its screen |
| 4.3 | "Editor two opens a chat." | right half widens; chat bubble with typing dots |
| 6.3 | "Editor one drags two hundred clips." | 70 halftone film frames rain into a pile; **200** counts up with ghost copies |
| 9.4 | "Editor two types: cut my pauses." | the bubble types *cut my pauses.* |
| 12.1 | "Editor one. Keyframes. Captions. Colour. Export…" | each word slams in with ghosts and the old ones stack below; export bar stalls at 38% |
| 16.3 | "Crash." | glitch, shake, cracked halftone screen, yellow sparks; music tape-stops |
| 17.4 | "Editor two hits enter." | yellow takes the whole frame; halftone ENTER key presses, burst lines; beat drops back in |
| 19.1 | "Six hours later… editor one posts." | alarm clock sweeps six hours; one phone, ♥ 3 |
| 22.0 | "Twelve minutes later… editor two is on reel number three." | three yellow phones deal in: 01 02 03 |
| 25.5 | "Same idea. Same footage." | identical halftone film frames in viewfinders on both halves, "=" |
| 27.5 | "The only difference?" | paper, serif text blocks, "difference?" with a yellow dot |
| 28.7 | "One of them knew… what to ask for." | extruded **WHAT TO / ASK FOR.** with ghost copies around a yellow card, computer and *make it hit.* note |
| 31.0 | "That's Vibe Editing." | "Vibe / editing." over a halftone computer with sparks |
| 32.5 | "Comment VIBE… and I'll show you how." | yellow/paper split, brackets, bubble types VIBE, bottom row word by word |
| 34.3 | (sign-off) | "edit by *Vibe Editing*" handwritten on |

**Sound** (`audio.py`, all synthesised): the narration is cleaned and compressed. The bed is an 88 BPM boom-bap groove (Fmaj7–Em7–Dm7–Cmaj7, Rhodes, swung hats, vinyl crackle). It tape-stops on "Crash.", re-enters on "enter", thins to one chord for the question and lands back on "what". About 70 SFX sit on their words, and the bed ducks under the voice.

## Run

```bash
cd work && python3 align.py && cd ..   # only if the narration changes (pocketsphinx)
./build.sh                             # audio + frames + MP4 (~40 min on 4 cores; resumable)
./build.sh --fps 24 --mb 1             # fast draft
node render.mjs --stills 8.9,18.4      # preview PNGs -> out/stills/
```

Fonts (OFL, Google Fonts): Inter Tight, Instrument Serif, Mrs Saint Delafield. The narration in `work/narration.mp3` was supplied by the user.
