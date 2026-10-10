"""motion_kit: the tiny engine behind every code-rendered Vibe Editing video.

Core idea: every frame is a pure function of time t.  You write `draw(canvas, t)`,
motion_kit renders it at any fps, in parallel, and pipes it to ffmpeg.

    from motion_kit import *
    S = Stage(1080, 1920, fps=30, duration=6)

    def draw(c, t):
        c.clear(rgb(S.brand, "bg"))
        k = ease_out_back(prog(t, 0.2, 0.6))            # 0 -> 1 between 0.2 s and 0.8 s
        text(c, "VIBE EDITING", S.w / 2, S.h / 2, size=140 * k, font="display", fill=rgb(S.brand, "fg"))

    if __name__ == "__main__":
        S.render(draw, "out/title.mp4", audio="work/mix.wav")      # full render, all CPU cores
        # S.stills(draw, [0.5, 1.0, 3.0])                           # check frames first
        # S.render(draw, "out/draft.mp4", draft=True)               # half-res, 15 fps draft

Requires: skia-python, numpy.  Fonts are looked up in ./fonts (see fonts.py).
"""

import math
import multiprocessing as mp
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import skia

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vibelib import FrameWriter, color, concat_videos, grab_frame, hex_rgb, load_brand, mux  # noqa: E402

# ------------------------------------------------------------------ timing + easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, k):
    return a + (b - a) * k


def prog(t, start, dur):
    """0 before start, 1 after start+dur, linear in between."""
    return clamp((t - start) / dur) if dur > 0 else float(t >= start)


def remap(x, a0, a1, b0, b1):
    return lerp(b0, b1, clamp((x - a0) / (a1 - a0)))


def ease_in_quad(k): return k * k
def ease_out_quad(k): return 1 - (1 - k) ** 2
def ease_in_out_quad(k): return 2 * k * k if k < 0.5 else 1 - (-2 * k + 2) ** 2 / 2
def ease_in_cubic(k): return k ** 3
def ease_out_cubic(k): return 1 - (1 - k) ** 3
def ease_in_out_cubic(k): return 4 * k ** 3 if k < 0.5 else 1 - (-2 * k + 2) ** 3 / 2
def ease_out_quart(k): return 1 - (1 - k) ** 4
def ease_in_expo(k): return 0.0 if k <= 0 else 2 ** (10 * k - 10)
def ease_out_expo(k): return 1.0 if k >= 1 else 1 - 2 ** (-10 * k)


def ease_in_out_expo(k):
    if k <= 0 or k >= 1:
        return float(k >= 1)
    return 2 ** (20 * k - 10) / 2 if k < 0.5 else (2 - 2 ** (-20 * k + 10)) / 2


def ease_out_back(k, s=1.70158):
    return 1 + (s + 1) * (k - 1) ** 3 + s * (k - 1) ** 2


def ease_in_back(k, s=1.70158):
    return (s + 1) * k ** 3 - s * k * k


def ease_out_elastic(k):
    if k <= 0 or k >= 1:
        return float(k >= 1)
    return 2 ** (-10 * k) * math.sin((k * 10 - 0.75) * (2 * math.pi) / 3) + 1


def ease_out_bounce(k):
    n, d = 7.5625, 2.75
    if k < 1 / d:
        return n * k * k
    if k < 2 / d:
        k -= 1.5 / d
        return n * k * k + 0.75
    if k < 2.5 / d:
        k -= 2.25 / d
        return n * k * k + 0.9375
    k -= 2.625 / d
    return n * k * k + 0.984375


def spring(t, freq=2.2, damping=0.35):
    """Damped spring from 0 to 1 (overshoots).  t in seconds since start."""
    if t <= 0:
        return 0.0
    w = 2 * math.pi * freq
    return 1 - math.exp(-damping * w * t) * math.cos(w * math.sqrt(max(1e-6, 1 - damping ** 2)) * t)


def stagger(t, i, start, each, dur, ease=ease_out_cubic):
    """Progress of item i in a staggered build (each = delay between items)."""
    return ease(prog(t, start + i * each, dur))


def beat_grid(bpm, offset=0.0):
    beat = 60.0 / bpm
    return lambda n: offset + n * beat


def pulse(t, bpm, offset=0.0, decay=6.0):
    """1 on every beat, decaying to 0 (use for beat-bumps / flashes)."""
    beat = 60.0 / bpm
    ph = ((t - offset) % beat) / beat
    return math.exp(-decay * ph) if t >= offset else 0.0


def noise1(x, seed=0):
    """Smooth 1-D value noise in [-1, 1] (handheld shake, wobble)."""
    i = math.floor(x)
    f = x - i

    def h(n):
        n = (n * 374761393 + seed * 668265263) & 0xFFFFFFFF
        n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
        return ((n ^ (n >> 16)) & 0xFFFF) / 32767.5 - 1
    u = f * f * (3 - 2 * f)
    return lerp(h(i), h(i + 1), u)


# ------------------------------------------------------------------ colour + paint
def rgb(brand_or_hex, role=None, alpha=1.0):
    """skia colour from '#RRGGBB' or (brand, 'accent'/'lime')."""
    h = color(brand_or_hex, role) if role is not None else brand_or_hex
    r, g, b = hex_rgb(h)
    return skia.Color(r, g, b, int(255 * clamp(alpha)))


def paint(col, stroke=None, aa=True, blur=0.0):
    p = skia.Paint(Color=col, AntiAlias=aa)
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur > 0:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


# ------------------------------------------------------------------ fonts + text
_FONT_CACHE = {}
FONT_DIRS = [Path("fonts"), Path(__file__).resolve().parent.parent / "fonts"]


def typeface(name="display", brand=None):
    """'display' / 'impact' / 'body' / 'mono' / 'serif' (brand roles) or a family / file name."""
    key = (name, id(brand))
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    brand = brand or load_brand(".")
    spec = brand.get("fonts", {}).get(name, name)
    fam, _, weights = spec.partition(":")
    weight = (weights.split(",")[-1] if weights else "400").rstrip("i")
    stem = fam.replace(" ", "")
    tf = None
    for d in FONT_DIRS:
        if not d.exists():
            continue
        cands = [d / f"{stem}-{weight}.ttf", d / f"{stem}.ttf", d / spec] + sorted(d.glob(f"{stem}*.ttf"))
        for c in cands:
            if c.exists() and c.is_file():
                tf = skia.Typeface.MakeFromFile(str(c))
                if tf:
                    break
        if tf:
            break
    if tf is None:
        tf = skia.Typeface(fam) or skia.Typeface()
    _FONT_CACHE[key] = tf
    return tf


def text_width(s, size, font="display", tracking=0.0):
    f = skia.Font(typeface(font), size)
    return f.measureText(s) + tracking * size * max(0, len(s) - 1)


def text(c, s, x, y, size=80, font="display", fill=None, align="center", tracking=0.0, alpha=1.0,
         stroke=None, stroke_col=None, baseline="middle"):
    """Draw a single line. align: left/center/right.  baseline: middle/alphabetic.  tracking in em."""
    if size <= 0.5 or alpha <= 0:
        return 0
    f = skia.Font(typeface(font), size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    w = text_width(s, size, font, tracking)
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    if baseline == "middle":
        m = f.getMetrics()
        y -= (m.fAscent + m.fDescent) / 2
    fill = fill if fill is not None else skia.ColorBLACK
    col = skia.Color4f(fill)
    col.fA *= alpha
    p = skia.Paint(Color4f=col, AntiAlias=True)
    ps = None
    if stroke:
        sc = skia.Color4f(stroke_col if stroke_col is not None else skia.ColorBLACK)
        sc.fA *= alpha
        ps = skia.Paint(Color4f=sc, AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=stroke,
                        StrokeJoin=skia.Paint.kRound_Join)
    if tracking == 0:
        if ps:
            c.drawString(s, x, y, f, ps)
        c.drawString(s, x, y, f, p)
    else:
        cx = x
        for ch in s:
            if ps:
                c.drawString(ch, cx, y, f, ps)
            c.drawString(ch, cx, y, f, p)
            cx += f.measureText(ch) + tracking * size
    return w


def wrap(s, size, max_w, font="body"):
    lines, cur = [], ""
    for word in s.split():
        trial = (cur + " " + word).strip()
        if text_width(trial, size, font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ------------------------------------------------------------------ shapes + images
def rrect(c, x, y, w, h, r, col, stroke=None):
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), paint(col, stroke))


def circle(c, x, y, r, col, stroke=None):
    c.drawCircle(x, y, r, paint(col, stroke))


def shadow(c, x, y, w, h, r, blur=30, dy=12, alpha=0.25):
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y + dy, w, h), r, r),
                paint(skia.Color(0, 0, 0, int(255 * alpha)), blur=blur))


_IMG_CACHE = {}


def image(path):
    if path not in _IMG_CACHE:
        _IMG_CACHE[path] = skia.Image.open(str(path))
    return _IMG_CACHE[path]


def draw_image(c, path_or_img, x, y, w=None, h=None, alpha=1.0, cover=True):
    img = image(path_or_img) if isinstance(path_or_img, (str, Path)) else path_or_img
    w = w or img.width()
    h = h or img.height()
    sw, sh = img.width(), img.height()
    if cover:
        s = max(w / sw, h / sh)
        src = skia.Rect.MakeXYWH((sw - w / s) / 2, (sh - h / s) / 2, w / s, h / s)
    else:
        src = skia.Rect.MakeWH(sw, sh)
    p = skia.Paint(AntiAlias=True, Alphaf=clamp(alpha))
    c.drawImageRect(img, src, skia.Rect.MakeXYWH(x, y, w, h), skia.SamplingOptions(skia.FilterMode.kLinear), p)


class VideoFrames:
    """Random access to frames of a video clip as skia Images (decoded once, cached as raw RGBA)."""

    def __init__(self, path, w=None, h=None, fps=30):
        from vibelib import ffmpeg_bin, probe
        import subprocess
        info = probe(path)
        self.w, self.h = w or info["width"], h or info["height"]
        self.fps = fps
        raw = subprocess.run([ffmpeg_bin(), "-v", "error", "-i", str(path), "-vf",
                              f"fps={fps},scale={self.w}:{self.h}", "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
                             capture_output=True, check=True).stdout
        self.frames = np.frombuffer(raw, np.uint8).reshape(-1, self.h, self.w, 4)

    def __len__(self):
        return len(self.frames)

    def array(self, t):
        """RGBA uint8 numpy frame at time t (holds the last frame past the end)."""
        return self.frames[int(clamp(t * self.fps, 0, len(self.frames) - 1))]

    def at(self, t):
        return skia.Image.fromarray(np.ascontiguousarray(self.array(t)), colorType=skia.kRGBA_8888_ColorType)


def with_alpha(rgb_arr, matte_arr, feather=0):
    """Combine a frame and its matte (from matte.py) into a transparent skia Image (the cut-out subject)."""
    a = matte_arr[..., 0] if matte_arr.ndim == 3 else matte_arr
    rgba = np.empty(rgb_arr.shape[:2] + (4,), np.uint8)
    k = a.astype(np.float32)[..., None] / 255
    rgba[..., :3] = (rgb_arr[..., :3] * k).astype(np.uint8)        # premultiplied
    rgba[..., 3] = a
    return skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)


# ------------------------------------------------------------------ finishing (numpy, optional)
def grain(arr, amount=0.04, seed=0):
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 255 * amount, arr.shape[:2])[..., None]
    return np.clip(arr.astype(np.float32) + n, 0, 255).astype(np.uint8)


def vignette(arr, strength=0.35):
    h, w = arr.shape[:2]
    y, x = np.ogrid[-1:1:h * 1j, -1:1:w * 1j]
    v = 1 - strength * np.clip(x * x + y * y - 0.25, 0, None)
    return np.clip(arr.astype(np.float32) * v[..., None], 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ stage: render loop
def _render_chunk(args):
    draw, w, h, fps, frames, path, scale, post, crf, alpha = args
    with FrameWriter(path, int(w * scale) // 2 * 2, int(h * scale) // 2 * 2, fps, crf=crf, preset="medium",
                     alpha=alpha) as fw:
        surf = skia.Surface(int(w * scale) // 2 * 2, int(h * scale) // 2 * 2)
        for f in frames:
            t = f / fps
            with surf as c:
                c.clear(skia.ColorTRANSPARENT)
                c.save()
                c.scale(scale, scale)
                draw(c, t)
                c.restore()
            arr = surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType,
                                                   alphaType=skia.kUnpremul_AlphaType)
            if not alpha:
                arr = arr[..., :3]
            if post:
                arr = post(arr, t)
            fw.write(arr)
    return path


class Stage:
    def __init__(self, w=1080, h=1920, fps=30, duration=10.0, brand=None):
        self.w, self.h, self.fps, self.duration = w, h, fps, duration
        self.brand = brand or load_brand(".")

    @property
    def frames(self):
        return int(round(self.duration * self.fps))

    def frame(self, draw, t, scale=1.0):
        surf = skia.Surface(int(self.w * scale), int(self.h * scale))
        with surf as c:
            c.scale(scale, scale)
            draw(c, t)
        return surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3]

    def stills(self, draw, times, out_dir="out/stills", post=None, scale=1.0, under=None):
        """PNG check frames. under="work/cut.mp4" previews an overlay on top of that footage."""
        from PIL import Image
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        paths = []
        for t in times:
            if under:
                surf = skia.Surface(int(self.w * scale), int(self.h * scale))
                with surf as c:
                    c.clear(skia.ColorTRANSPARENT)
                    c.scale(scale, scale)
                    draw(c, t)
                ov = surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType,
                                                      alphaType=skia.kUnpremul_AlphaType).astype(np.float32)
                base = grab_frame(under, t, ov.shape[1], ov.shape[0]).astype(np.float32)
                k = ov[..., 3:4] / 255
                arr = (ov[..., :3] * k + base * (1 - k)).astype(np.uint8)
            else:
                arr = self.frame(draw, t, scale)
            if post:
                arr = post(arr, t)
            p = Path(out_dir) / f"still_{t:06.2f}.png"
            Image.fromarray(arr).save(p)
            paths.append(p)
            print("  still", p)
        return paths

    def render(self, draw, out, audio=None, draft=False, workers=None, post=None, crf=17, start=0.0, end=None,
               alpha=False):
        """Render [start, end) to `out`. draft=True: half resolution, half fps (fast previews).
        alpha=True: transparent overlay -> ProRes 4444 .mov (draw() must not paint a background);
        lay it over footage with vibelib.composite() or vibe/overlay.py."""
        if alpha and not str(out).lower().endswith(".mov"):
            out = str(Path(out).with_suffix(".mov"))
        fps = self.fps / 2 if draft else self.fps
        scale = 0.5 if draft else 1.0
        end = self.duration if end is None else end
        all_frames = list(range(int(round(start * fps)), int(round(end * fps))))
        workers = workers or os.cpu_count() or 2
        workers = min(workers, max(1, len(all_frames) // 15))
        tmp = Path(tempfile.mkdtemp(prefix="vibe_render_", dir=Path(out).parent if Path(out).parent.exists() else None))
        chunks = np.array_split(np.array(all_frames), workers)
        ext = ".mov" if alpha else ".mp4"
        jobs = [(draw, self.w, self.h, fps, [int(f) for f in ch], str(tmp / f"part_{i:03d}{ext}"), scale, post, crf,
                 alpha) for i, ch in enumerate(chunks) if len(ch)]
        print(f"rendering {len(all_frames)} frames @ {fps:g} fps on {len(jobs)} worker(s)"
              f"{' (draft)' if draft else ''} ...")
        if len(jobs) == 1:
            parts = [_render_chunk(jobs[0])]
        else:
            ctx = mp.get_context("fork" if sys.platform.startswith("linux") else "spawn")
            with ctx.Pool(len(jobs)) as pool:
                parts = pool.map(_render_chunk, jobs)
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        silent = tmp / f"picture{ext}"
        concat_videos(parts, silent)
        if audio and Path(audio).exists() and not alpha:
            mux(silent, audio, out)
        else:
            os.replace(silent, out)
        for p in tmp.iterdir():
            p.unlink()
        tmp.rmdir()
        print(f"done -> {out}")
        return out
