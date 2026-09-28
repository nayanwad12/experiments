# Evolution, drawn by a single point of light

A procedural short film (~90 s, 1920×1080, 30 fps). A single point of light
paints the story of life as one continuous trail. The trail hangs in 3D, and
the camera follows the light like a long-exposure photograph: trails pile up,
light scatters into haze, depth of field softens what's near and far, and a
wet floor mirrors everything.

**Chapters:** Life (DNA double helix) → The Sea (fish) → Onto Land
(tetrapod) → The Apes → Standing Up (Australopithecus) → Fire
(Homo erectus with a torch) → Homo sapiens → Looking Up (the light spirals
into the sky) → the camera pulls back to show the whole trail.

Output: `evolution_of_light.mp4`

## How it's made

* `figures.py` holds hand-drawn single-line outlines, smoothed with a
  centripetal Catmull-Rom spline. Run it to get a 2D preview sheet.
* `render.py` places the outlines in 3D and joins them into one path. It
  times the light along that path, then renders every frame with numpy and
  OpenCV:
  * **Long exposure:** the brightness of each trail sample is set by how long
    the light stayed there, so slow strokes glow and fast links stay faint.
  * **Depth of field:** each sample is splatted into one of several blur
    layers based on its circle of confusion.
  * **Wet floor:** the trail is mirrored through y = 0. A world-space puddle
    map and Fresnel set how reflective each spot is. Puddles get a sharp,
    rippling mirror; rough floor gets vertical streaks. The floor also keeps
    the light the point has cast on it over time.
  * **Haze:** wide blurs of the lit scene are modulated by drifting fog noise,
    plus a glow around the moving point.
  * **Finish:** filmic tonemap, vignette, grain, captions.

```bash
pip install numpy scipy opencv-python-headless pillow imageio-ffmpeg
python render.py --stills 20.,57.   # preview frames (seconds) as PNG
python render.py                    # full video (uses all cores)
```

Fonts: Cormorant Garamond and Jost (SIL Open Font License, via Google Fonts).
