# Vibe Editing Reels, batch 3: art-directed from Pinterest

Batch 3 starts from **reference boards**. Pins are pulled from Pinterest with
[`tools/pinterest-refs`](../../tools/pinterest-refs), studied, and written up as a brief. The film is then built
from scratch in code, so no pin is ever copied or shown. The reference images are gitignored, and only the brief is
committed.

| # | Reel | Brief | File |
|---|---|---|---|
| B3-01 | **ACID CHROME**: a 33.75 s music-driven hype reel for Vibe Editing. Chrome blob → type tunnel → shape morphs → "NO TIMELINE / NO KEYFRAMES / NO PLUGINS" sliced by a chrome blade → ring-tunnel drop → montage → 3D chrome logo | [`references/vibe-crazy/BRIEF.md`](../../references/vibe-crazy/BRIEF.md) | [`01-acid-chrome/out/vibe_editing_acid_chrome.mp4`](01-acid-chrome/out/vibe_editing_acid_chrome.mp4) |

## B3-01 ACID CHROME

**Look:** a black void, mirror chrome lit only by strip lights, one acid lime (`#D4FF3F`), brutalist repeated type
(Anton / Unbounded), and the same HUD on every frame (crop marks, section index, timecode, BPM, a lime progress bar
with one tick per bar). The three colours never change from the first frame to the last.

**Grid:** 128 BPM, 18 bars. Every cut, morph, slam and flash lands on a beat, and the music is written to the same grid.

| Bars | Time | Section | What happens |
|---|---|---|---|
| 0–2 | 0–3.75 s | `[01] PROMPT` | "ONE PROMPT. ZERO KEYFRAMES." The prompt types *make it crazy.*, the chrome blob pulses on each key, and on Enter it gets sucked into a point |
| 2–4 | 3.75–7.5 s | `[02] TYPE TUNNEL` | Flight down a tunnel of "VIBE EDITING" lanes that slide in opposite directions and jump on each beat. A lime lane hops around. The blob reflects the tunnel (a live cube map) |
| 4–6 | 7.5–11.25 s | `[03] MORPH` | 8 shapes, one per beat (spikes, rounded cube, twisted ridges, petals, saucer, capsule, lumps, sphere), with a stacked word behind (EASE … VIBE) and a lime ring |
| 6–8 | 11.25–15 s | `[04] NO` | NO TIMELINE / NO KEYFRAMES / NO PLUGINS slam in, and a chrome blade slices each word in half on the next beat, with a lime flash frame. Then JUST THE VIBE. |
| 8–12 | 15–22.5 s | `[05] DROP` | Flight through 64 chrome rings with lime and white light rails and speed streaks, through DIRECT / THE / VIBE. and AI / DOES THE / KEYFRAMES., with a barrel roll in bar 11 |
| 12–14 | 22.5–26.25 s | `[06] MONTAGE` | 12 recap cuts (on beats, then 8ths) re-rendering earlier moments, with every other cut an acid duotone invert. Each cut shows one word: EVERY CUT ON THE BEAT / NO AFTER EFFECTS / NO PREMIERE / JUST ONE PROMPT |
| 14–18 | 26.25–33.75 s | `[07] VIBE EDITING` | 3D chrome letters (TextGeometry from Unbounded Black) slam in one per beat, EDITING flips up, a lime light sweeps across, then the tagline and FOLLOW FOR MORE |

**Engine:** `scene.js` is a single Three.js page rendered headlessly in Chromium (SwiftShader) by
`../batch2/render3d.mjs`. Highlights:
- **Chrome:** a dynamic cube camera that sees an invisible strip-light studio (layer 1) plus the real scene. A
  gradient horizon wall gives the flat logo faces the classic chrome-type shading.
- **Picture finishing:** bloom, then a grade pass with radial chromatic fringe, a vignette, acid duotone inversion,
  the HUD composited after the grade so it stays crisp, grain, and flashes.
- **Motion blur:** the film renders at 60 fps and each pair of frames is averaged down to 30 fps (180° shutter).

**Music:** an original track in F minor (i–VI–III–VII), synthesised in numpy with `common/music.py`. It has a filtered
intro that cuts out on Enter, four-on-the-floor with reese bass and supersaw stabs, a pluck arp under the morph,
braams and impacts on the NO slams, a snare roll and riser into the drop, a vocal-chop hook, cut-synced stabs that
climb in pitch through the montage, taiko and impact slams for the logo letters, and a half-time outro. The SFX
(typing clicks, swishes, glitches, shutters) are synthesised too. The mix is mastered to −14 LUFS.

### Rebuild

```bash
cd ../batch2 && npm i && cd ../batch3/01-acid-chrome
python3 build.py stills 1.2 8.2 16 31   # preview frames -> out/web/
python3 build.py layer                  # 60 fps layer, ~25 min on 4 cores (resumable)
python3 build.py picture                # motion blur -> 30 fps
python3 build.py sound                  # music + SFX + mux -> out/vibe_editing_acid_chrome.mp4
```

### Caption

> I typed "make it crazy." and this is what came out. 🧪⚡
> Chrome, type tunnels, 3D logo, the whole soundtrack: all code, one prompt. No After Effects. No Premiere.
> #vibeediting #motiondesign #3dart #kinetictypography #creativecoding #acidgraphics
