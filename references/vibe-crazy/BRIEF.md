# ACID CHROME: art direction for the "Vibe Editing" hype reel

These notes come from about 40 Pinterest pins, collected with `tools/pinterest-refs`. The pins themselves are
gitignored. I only studied them. Nothing in the reel copies a pin.

| Folder | Search | What I took from it |
|---|---|---|
| `chrome/` | liquid chrome 3d motion design | Mirror chrome on a black void. The highlights are hard white strip lights, not soft gradients. Most of the frame is pure black, with a few bright stripes running along the forms. The forms are blobby and slightly lumpy, and they read as liquid even when still. |
| `acid/` | acid graphic design poster lime black | One loud lime on black, with no second accent. Mono labels and small metadata in the corners. Crop marks, grids and halftone grain make it feel like a print. |
| `kinetic/` | brutalist kinetic typography motion | One word repeated row after row ("MOTION MOTION", "BRIK BRIK"). Rows that slide against each other. One row inverted to pull focus. Condensed grotesk at huge sizes, filling the frame edge to edge. |
| `glass/` | 3d abstract render iridescent glass shapes | **Dropped.** Iridescent rainbow glass would add a second colour story and break the "one accent" rule. |

## The rules

1. **Three colours only.** Void black `#050505`, chrome (white in reflections), and brand lime `#D4FF3F`.
   Lime appears as light (strips, the cursor, one inverted type row) or as a solid flash frame. It never shows up as a gradient.
2. **Chrome is lit by strips, not by a sky.** The reflections come from a studio of invisible emissive bars (white
   softbox, white side strips, a lime back strip). Inside the type tunnel, the chrome reflects the type itself
   (dynamic cube map).
3. **Type is brutal.** Anton for the walls of repeated words, Unbounded Black for the hero words and the 3D logo,
   JetBrains Mono for every HUD label.
4. **A HUD runs through the whole film, so it reads as one piece.** It has corner crop marks, a section index
   `[01]–[07]`, a timecode, the BPM, and a lime progress bar. The same frame sits around every section.
5. **Everything cuts on the beat.** 128 BPM, so one bar is 1.875 s and the film is 18 bars (33.75 s). Every cut,
   morph and slam lands on a beat.
6. **Finish:** bloom on the lime and the chrome highlights, fine grain, a slight chromatic fringe at the edges, a
   vignette, and inverted flash frames on the big hits.

## Structure

| Bars | Section | What happens |
|---|---|---|
| 0–2 | `[01] PROMPT` | Chrome blob in the void. A prompt types "make it crazy". The blob reacts to each key, and on Enter it gets sucked into a point. |
| 2–4 | `[02] TYPE TUNNEL` | Flash cut into a tunnel lined with "VIBE EDITING" lanes sliding in opposite directions. The blob flies ahead and reflects the type. |
| 4–6 | `[03] MORPH` | The blob changes shape on every beat (spikes, cube, ridges, petals…). A giant word behind it changes with each shape. |
| 6–8 | `[04] NO` | NO TIMELINE / NO KEYFRAMES / NO PLUGINS slam in, and a chrome blade slices each word in half. Then JUST THE VIBE. |
| 8–12 | `[05] DROP` | Flight through chrome rings and lime strip lights. DIRECT / THE / VIBE, then AI / DOES THE / KEYFRAMES, with a barrel roll. |
| 12–14 | `[06] MONTAGE` | Accelerating recap cuts (beats, then 8ths) with inverted frames. |
| 14–18 | `[07] VIBE EDITING` | 3D chrome letters slam in one per beat, a lime light sweeps across them, then the tagline and the follow CTA. |
