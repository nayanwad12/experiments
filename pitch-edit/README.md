# Pitch edit (v2): premium explainer + kinetic type, 60 fps

- `out/pitch_edited.mp4`: the edit. 1080×1920, 60 fps, 34.3 s, −14 LUFS.
- `out/pitch_comparison.mp4`: before/after, 1920×1080, 60 fps. The raw phone take is shown next to the edit, in sync.

What v2 changed:
- **Smoother:** stabilised at the full 60 fps of the phone with vidstab (`optalgo=avg`, `maxshift=56`). The input is
  decoded through a clean intermediate first, because decoding the iPhone HEVC directly produced blocky frames.
  On top of that, a face lock uses optical flow on the face to remove the remaining walking bob, and the output is 60 fps.
- **Dead air cut:** pauses are found from speech-band energy, and any pause longer than 0.22 s is cut down to about 0.14 s.
  50.2 s became 33.1 s. The cut audio was re-transcribed and every word is intact.
- **Bigger captions:** 96 px Inter Tight, 1–2 words at a time, with the active word in neon.
- **Zoom transitions:** a zoom-blur between every scene, plus an eased punch-in on every jump cut in the full-frame scenes.
- **Layout:** in the explainer scenes the speaker is a small circle at the top right and the graphics sit in the middle
  (the old way, the system core, the step pipeline for Record → Say it → Edit, the prompt UI, "No app / editor / skills", the creator seats).
- **Full-frame scenes:** hook, step 3 demo, "talk", the magazine cover and the CTA keep kinetic type behind the head.

Rebuild: `python3 scene.py prep && python3 work/facelock.py && python3 work/matte_sel.py && python3 scene.py audio && python3 scene.py render`
(the EDL is in `work/edl60.json` and the scene timings are in `timeline.py`).
