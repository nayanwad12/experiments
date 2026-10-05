# AI Footage QC Checklist
Check every generated clip before it goes near the timeline.

## Reject or cut around
- [ ] Hands: extra/missing fingers, melting, merging with objects
- [ ] Faces: identity changes, warping eyes/teeth, uncanny smiles
- [ ] Text: garbled signs, fake logos, nonsense UI on screens
- [ ] Physics: objects passing through each other, popping in/out
- [ ] Geometry: bending walls, wobbly straight lines
- [ ] Flicker: colour or brightness pumping
- [ ] Dissolves *inside* a clip (sudden morph to another scene)
- [ ] The last 0.5–1 s (often degrades or freezes)
- [ ] Generator watermark (export a clean version from your plan; don't strip it)

## Fix toolbox
| problem | fix |
|---|---|
| flaw mid-shot | split around it, or cover with a cut-away |
| garbled screen text | crop past it, defocus it, or rebuild as a real UI graphic |
| fake logo | replace with the real logo graphic |
| jitter | stabilise that shot |
| too short | slow to 0.7× (optical flow) or freeze + push-in |
| mismatched looks | one grade + grain on everything |

## The "not AI" finish
- Shots 1.5–4 s; vary the lengths
- One grade, same strength, subtle grain, light vignette
- All text/logos/numbers = real graphics
- Ambience + foley-like SFX + music
- Mix in real photos/footage where possible

## Rights
- [ ] Generated on a plan that allows commercial use
- [ ] People/brands depicted: permission or clearly fictional
- [ ] Music and voice licensed or generated
