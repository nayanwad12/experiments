# ideabro studio · Vibe Editing, glassmorphism Reel

A 35 s vertical Reel (1080×1920, 30 fps, H.264 + AAC 48 kHz, −14 LUFS) in full glassmorphism: frosted
backdrop-blur panels, gradient glass edges, specular sheens, drifting light orbs, grain and soft camera moves.

**File:** [`out/ideabro_vibe_editing_glass.mp4`](out/ideabro_vibe_editing_glass.mp4) · contact sheet: [`out/sheet.png`](out/sheet.png)

| Time | Beat | On screen |
|---|---|---|
| 0–5 s | **Hook** | Glass "viewfinder" card with a live REC timecode and frame counter: *"The video you're watching right now… was edited entirely by the* **Vibe Editing System***"* |
| 5–8 s | **No tools** | Glass tiles land and get crossed out: *No timeline. No keyframes. No After Effects.* They fall away on the drop. |
| 8–11 s | **Any video** | *"One workflow. Any motion video."* over a 3D ring of orbiting glass tiles |
| 11–16 s | **Range** | Glass coverflow with live previews: kinetic type, product ad, 3D, explainer, logo reveal |
| 16–26 s | **The process** | Glass stepper 01–04 with one panel per step: prompt typed in, scenes written in code, motion / music / voice timeline, render to 9:16, 1:1 and 16:9 |
| 26–30.5 s | **CTA** | *"Want this exact workflow?"* A cursor taps a glass **Comment VIBE** button; comment bubbles float up. |
| 30.5–35.4 s | **Brand** | Glass logo tile, **ideabro STUDIO** wordmark with a light sweep, *Comment VIBE to get the workflow* |

## Suggested caption

> This entire video was edited by one workflow. No timeline, no keyframes, no After Effects. ✨
> Comment **VIBE** and I'll send you the exact Vibe Editing workflow.
> #vibeediting #glassmorphism #motiondesign #motiongraphics #videoediting #contentcreator #ideabrostudio

## How it's built

- `script.py`: the narration lines (Kokoro TTS, local). Edit a line and rebuild; every cue moves with the voice.
- `build.py`: lays the lines on a 120 BPM grid, writes `work/timeline.json` (word timings + kick times),
  renders the page, then mixes voice, an original future-bass track (`../common/music.py`) and SFX.
- `scene.html` / `scene.js`: the whole picture as HTML/CSS glass. `renderFrame(t)` is a pure function of time,
  screenshotted frame by frame in headless Chromium by `../batch2/render3d.mjs`.

```bash
python3 build.py prep        # narration + timeline
python3 build.py sheet       # 12-still contact sheet -> out/sheet.png
python3 build.py web 3 21    # single stills -> out/web/
python3 build.py all         # picture + sound -> out/ideabro_vibe_editing_glass.mp4
```

Needs `pip install skia-python numpy scipy soundfile kokoro-onnx pillow`, the Kokoro model files in
`/home/user/models` (or `KOKORO_MODELS`), and Playwright's Chromium.
