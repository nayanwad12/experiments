"""kit: shared drawing + rendering for the Vibe Editing Reels (1080x1920, 9:16).

Drawing helpers (skia), easing, the house captions, the prompt bar, the brand end card,
and a parallel renderer with a small CLI (stills / sheet / render).
"""

import math
import multiprocessing as mp
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from vibelib import FrameWriter, concat_videos  # noqa: E402

W, H = 1080, 1920
FONTS_DIR = HERE.parent / "fonts"

# ---------------------------------------------------------------- brand
INK = "#0E0E11"
PAPER = "#F4F1EA"
LIME = "#D4FF3F"
WHITE = "#FFFFFF"
GREY = "#8A8A90"
PERI = "#C4C6FF"
BLUSH = "#FFCFD8"

FONTS = {
    "black": "InterTight-900.ttf", "heavy": "InterTight-800.ttf", "bold": "InterTight-700.ttf",
    "medium": "InterTight-500.ttf", "light": "InterTight-300.ttf",
    "serif": "InstrumentSerif-400.ttf", "italic": "InstrumentSerif-400-italic.ttf",
    "mono": "JetBrainsMono-400.ttf", "monob": "JetBrainsMono-500.ttf",
    "anton": "Anton.ttf", "unbounded": "Unbounded-Black.ttf", "mont": "Montserrat-Black.ttf",
    "montb": "Montserrat-Bold.ttf", "luckiest": "LuckiestGuy-Regular.ttf", "caveat": "CaveatBrush-Regular.ttf",
    "gochi": "GochiHand-Regular.ttf", "patrick": "PatrickHand-Regular.ttf", "jost": "Jost-Light.ttf",
    "cormorant": "Cormorant-Light.ttf",
}
_TF = {}


# ---------------------------------------------------------------- maths / easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, k):
    return a + (b - a) * k


def prog(t, t0, dur):
    return clamp((t - t0) / dur) if dur > 0 else float(t >= t0)


def e_out(k):
    return 1 - (1 - clamp(k)) ** 3


def e_in(k):
    return clamp(k) ** 3


def e_io(k):
    k = clamp(k)
    return 4 * k ** 3 if k < 0.5 else 1 - (-2 * k + 2) ** 3 / 2


def e_expo(k):
    k = clamp(k)
    return 1.0 if k >= 1 else 1 - 2 ** (-10 * k)


def e_back(k, s=1.7):
    k = clamp(k) - 1
    return 1 + (s + 1) * k ** 3 + s * k ** 2


def spring(x, w=18.0, z=0.4):
    if x <= 0:
        return 0.0
    return 1 - math.exp(-z * w * x) * math.cos(w * math.sqrt(1 - z * z) * x)


def hrand(*key):
    """deterministic 0..1 from any hashable key."""
    h = hash(key) & 0xFFFFFFFF
    h = (h ^ (h >> 16)) * 0x45D9F3B & 0xFFFFFFFF
    h = (h ^ (h >> 16)) * 0x45D9F3B & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFF) / 0xFFFFFF


# ---------------------------------------------------------------- colour + paint
def rgb(c):
    if isinstance(c, str):
        c = c.lstrip("#")
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(c[:3])


def mixc(a, b, k):
    a, b = rgb(a), rgb(b)
    return tuple(int(round(a[i] + (b[i] - a[i]) * clamp(k))) for i in range(3))


def col(c, a=1.0):
    r, g, b = rgb(c)
    return skia.Color(r, g, b, int(255 * clamp(a)))


def fill(c, a=1.0, blur=0):
    p = skia.Paint(Color=col(c, a), AntiAlias=True)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


def stroke(c, w, a=1.0, blur=0, cap="round"):
    p = skia.Paint(Color=col(c, a), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=w)
    p.setStrokeCap(skia.Paint.kRound_Cap if cap == "round" else skia.Paint.kButt_Cap)
    p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


def lin_grad(x0, y0, x1, y1, cols, pos=None, a=1.0):
    return skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeLinear(
        [skia.Point(x0, y0), skia.Point(x1, y1)], [col(c, a) for c in cols], pos))


def rad_grad(cx, cy, r, cols, pos=None, a=1.0):
    return skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeRadial(
        skia.Point(cx, cy), max(r, 1), [col(c, a) for c in cols], pos))


def rrect(x, y, w, h, r):
    return skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r)


# ---------------------------------------------------------------- type
def font(name, size):
    if name not in _TF:
        _TF[name] = skia.Typeface.MakeFromFile(str(FONTS_DIR / FONTS.get(name, name)))
    f = skia.Font(_TF[name], size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    f.setSubpixel(True)
    f.setLinearMetrics(True)
    return f


def measure(s, name, size, tracking=0.0):
    f = font(name, size)
    if not tracking:
        return f.measureText(s)
    return sum(f.measureText(ch) for ch in s) + tracking * size * max(0, len(s) - 1)


def text(c, s, x, y, name, size, color=INK, a=1.0, anchor="c", tracking=0.0, paint=None, outline=0,
         outline_color=INK, shadow=0):
    """Draw a single line. anchor: l / c / r (x), y is the baseline."""
    w = measure(s, name, size, tracking)
    x0 = x - w / 2 if anchor == "c" else x - w if anchor == "r" else x
    f = font(name, size)
    paints = []
    if shadow:
        paints.append(fill("#000000", 0.35 * a, blur=shadow))
    if outline:
        paints.append(stroke(outline_color, outline, a))
    paints.append(paint or fill(color, a))
    for p in paints:
        if not tracking:
            c.drawString(s, x0, y, f, p)
        else:
            xx = x0
            for ch in s:
                c.drawString(ch, xx, y, f, p)
                xx += f.measureText(ch) + tracking * size
    return x0, w


def cap_height(name, size):
    return font(name, size).getMetrics().fCapHeight


def wrap(s, name, size, max_w):
    lines, cur = [], ""
    for wd in s.split():
        tryl = (cur + " " + wd).strip()
        if measure(tryl, name, size) <= max_w or not cur:
            cur = tryl
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def text_path(s, name, size, x=0, y=0, anchor="c"):
    f = font(name, size)
    w = f.measureText(s)
    x0 = x - w / 2 if anchor == "c" else x - w if anchor == "r" else x
    return skia.TextBlob.MakeFromString(s, f), x0


# ---------------------------------------------------------------- captions (house style)
def chunk_words(words, max_words=3, max_chars=16):
    """[(w, s, e, lid)] -> [[(w, s, e), ...], ...] caption groups (break on punctuation, line change)."""
    groups, cur = [], []
    for i, wd in enumerate(words):
        w = wd[0]
        if cur and (len(cur) >= max_words or sum(len(x[0]) + 1 for x in cur) + len(w) > max_chars
                    or cur[-1][3] != wd[3]):
            groups.append(cur)
            cur = []
        cur.append(wd)
        if w[-1] in ".,!?;:…" and len(cur) >= 1:
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return groups


class Captions:
    """Bold burned-in captions, 1-3 words at a time, the spoken word lit in the accent colour.

        CAP = Captions(script.words(skip=...), y=1360)
        CAP.draw(c, t)
    """

    def __init__(self, words, y=1380, size=88, name="black", fill_c=WHITE, hi=LIME, outline=INK, upper=False,
                 hold=0.25, box=False):
        self.groups = chunk_words(words)
        self.y, self.size, self.name = y, size, name
        self.fill_c, self.hi, self.outline, self.upper, self.hold, self.box = fill_c, hi, outline, upper, hold, box
        self.off = []

    def mute(self, t0, t1):
        """hide captions between t0 and t1 (e.g. when the screen shows the words already)."""
        self.off.append((t0, t1))
        return self

    def draw(self, c, t, alpha=1.0, y=None):
        if any(a <= t < b for a, b in self.off):
            return
        y = self.y if y is None else y
        for gi, g in enumerate(self.groups):
            g0, g1 = g[0][1], g[-1][2]
            nxt = self.groups[gi + 1][0][1] if gi + 1 < len(self.groups) else 1e9
            end = min(g1 + self.hold, nxt)
            if not (g0 - 0.02 <= t < end):
                continue
            k = prog(t, g0 - 0.02, 0.16)
            sc = lerp(0.82, 1.0, e_back(k, 2.2))
            a = alpha * clamp(k * 2.5)
            ws = [(w.upper() if self.upper else w) for w, *_ in g]
            space = measure(" ", self.name, self.size) + self.size * 0.14
            widths = [measure(w, self.name, self.size) for w in ws]
            tot = sum(widths) + space * (len(ws) - 1)
            c.save()
            c.translate(W / 2, y)
            c.scale(sc, sc)
            if self.box:
                ch = cap_height(self.name, self.size)
                c.drawRRect(rrect(-tot / 2 - 28, -ch - 26, tot + 56, ch + 52, 22), fill(INK, 0.82 * a))
            x = -tot / 2
            for wi, ((w, s, e, *_), txt, wd) in enumerate(zip(g, ws, widths)):
                nxt_s = g[wi + 1][1] if wi + 1 < len(g) else end
                colr = self.hi if s - 0.03 <= t < nxt_s - 0.03 else self.fill_c
                pop = 1.0 + 0.08 * math.exp(-max(0, t - s) * 14) * (t >= s)
                c.save()
                c.translate(x + wd / 2, 0)
                c.scale(pop, pop)
                if not self.box:
                    text(c, txt, 0, 0, self.name, self.size, a=a, shadow=10, color=colr,
                         outline=self.size * 0.16, outline_color=self.outline)
                else:
                    text(c, txt, 0, 0, self.name, self.size, a=a, color=colr)
                c.restore()
                x += wd + space
            c.restore()


# ---------------------------------------------------------------- prompt bar
def prompt_bar(c, t, txt, t0, t1, cx=W / 2, cy=H / 2, w=940, dark=False, scale=1.0, a=1.0, sent_t=None,
               label="Describe your video…", size=40):
    """A chat-style prompt box that types `txt` between t0 and t1; send button flashes at sent_t."""
    n = len(txt)
    k = clamp((t - t0) / max(t1 - t0, 1e-3))
    shown = txt[: int(round(n * k))] if t >= t0 else ""
    bg, fg, sub = (("#1B1B20", WHITE, "#6E6E78") if dark else (WHITE, INK, "#A0A0A8"))
    lines = wrap(shown, "medium", size, w - 190) if shown else []
    full_lines = max(1, len(wrap(txt, "medium", size, w - 190)))
    lh = size * 1.32
    h = 70 + lh * full_lines
    c.save()
    c.translate(cx, cy)
    c.scale(scale, scale)
    x, y = -w / 2, -h / 2
    c.drawRRect(rrect(x, y + 14, w, h, 44), fill("#000000", 0.22 * a, blur=28))
    c.drawRRect(rrect(x, y, w, h, 44), fill(bg, a))
    c.drawRRect(rrect(x, y, w, h, 44), stroke("#FFFFFF" if dark else "#000000", 2, 0.08 * a))
    ty = y + 35 + size * 0.95
    if not shown:
        text(c, label, x + 52, ty, "medium", size, sub, a, anchor="l")
    for i, ln in enumerate(lines):
        text(c, ln, x + 52, ty + i * lh, "medium", size, fg, a, anchor="l")
    # caret
    if t < (sent_t or 1e9):
        blink = 1.0 if (t0 <= t <= t1) else (0.5 + 0.5 * math.cos(t * 2 * math.pi * 1.6) > 0.3)
        lx = x + 52 + (measure(lines[-1], "medium", size) + 4 if lines else 0)
        ly = ty + (len(lines) - 1) * lh if lines else ty
        c.drawRect(skia.Rect.MakeXYWH(lx, ly - size * 0.85, 4, size * 1.05), fill(LIME if dark else INK, a * blink))
    # send button
    bx, by = x + w - 66, y + h - 62
    press = 0.0
    if sent_t is not None:
        press = math.exp(-max(0, t - sent_t) * 9) * (t >= sent_t)
    br = 34 * (1 - 0.18 * press)
    ready = t >= t1
    c.drawCircle(bx, by + 16, br, fill(LIME if ready else ("#2A2A31" if dark else "#E6E6EA"), a))
    p = skia.Path()
    p.moveTo(bx, by + 16 - 14)
    p.lineTo(bx, by + 16 + 14)
    p.moveTo(bx - 11, by + 16 - 3)
    p.lineTo(bx, by + 16 - 14)
    p.lineTo(bx + 11, by + 16 - 3)
    c.drawPath(p, stroke(INK if ready else sub, 5, a))
    c.restore()
    return h * scale


# ---------------------------------------------------------------- brand end card
def endcard(c, t, t0, title="Vibe Editing", line1="No AI video tools.", line2="Just one prompt.",
            cta="Follow for more"):
    """Shared closing card: ink background, lime mark, two promise lines, follow CTA."""
    k = prog(t, t0, 0.45)
    c.drawRect(skia.Rect.MakeWH(W, H), fill(INK))
    # lime rings
    for i in range(3):
        r = 260 + i * 120 + 30 * e_out(prog(t, t0 + 0.05 * i, 0.9))
        c.drawCircle(W / 2, 760, r, stroke(LIME, 2.5, 0.16 - 0.04 * i))
    m = e_back(prog(t, t0 + 0.05, 0.5), 2.0)
    c.save()
    c.translate(W / 2, 760)
    c.scale(m, m)
    c.drawRRect(rrect(-110, -110, 220, 220, 58), fill(LIME))
    # play-spark glyph
    p = skia.Path()
    p.moveTo(-28, -46)
    p.lineTo(52, 0)
    p.lineTo(-28, 46)
    p.close()
    c.drawPath(p, fill(INK))
    c.restore()
    a1 = e_out(prog(t, t0 + 0.25, 0.4))
    text(c, title, W / 2, 1060 + 30 * (1 - a1), "black", 112, WHITE, a1, tracking=-0.03)
    a2 = e_out(prog(t, t0 + 0.55, 0.4))
    text(c, line1, W / 2, 1180 + 24 * (1 - a2), "medium", 54, "#B9B9C0", a2)
    a3 = e_out(prog(t, t0 + 0.8, 0.4))
    text(c, line2, W / 2, 1252 + 24 * (1 - a3), "italic", 66, LIME, a3)
    a4 = e_out(prog(t, t0 + 1.1, 0.4))
    bw = measure(cta, "bold", 44) + 120
    c.drawRRect(rrect(W / 2 - bw / 2, 1370 + 20 * (1 - a4), bw, 96, 48), stroke(WHITE, 3, 0.9 * a4))
    text(c, cta, W / 2 - 18, 1433 + 20 * (1 - a4), "bold", 44, WHITE, a4)
    # little arrow
    ax = W / 2 + bw / 2 - 62
    ay = 1418 + 20 * (1 - a4)
    p = skia.Path()
    p.moveTo(ax - 10, ay + 12)
    p.lineTo(ax + 10, ay - 8)
    p.moveTo(ax - 4, ay - 8)
    p.lineTo(ax + 10, ay - 8)
    p.lineTo(ax + 10, ay + 6)
    c.drawPath(p, stroke(LIME, 5, a4))
    return k


# ---------------------------------------------------------------- post effects
_grain = None


def grain(rgb_arr, f, amt=0.035, scale=2):
    global _grain
    h, w = rgb_arr.shape[:2]
    if _grain is None:
        g = np.random.default_rng(5)
        _grain = [g.standard_normal((h // scale + 1, w // scale + 1)).astype(np.float32) for _ in range(8)]
    gr = np.repeat(np.repeat(_grain[f % 8], scale, 0), scale, 1)[:h, :w]
    out = rgb_arr.astype(np.float32) + gr[..., None] * 255 * amt
    return np.clip(out, 0, 255).astype(np.uint8)


def vignette(rgb_arr, amt=0.3):
    h, w = rgb_arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    v = (1 - amt * np.clip(r - 0.5, 0, None) ** 1.5)[..., None]
    return np.clip(rgb_arr * v, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- rendering
class Film:
    """Wraps a draw(c, t, f) -> dict|None function. post(rgb, g, f) -> rgb is optional.

        film = Film(draw, dur=32.0, fps=30, post=None, out_dir="out")
        film.cli()      # python3 build.py stills 1.2 3.4 | sheet | render [--draft]
    """

    def __init__(self, draw, dur, fps=30, post=None, out_dir="out", warm=None, sheet_n=30):
        self.draw_fn, self.dur, self.fps, self.post = draw, dur, fps, post
        self.out_dir = Path(out_dir)
        self.warm, self.sheet_n = warm, sheet_n

    def frame(self, t, scale=1.0, f=None):
        f = int(round(t * self.fps)) if f is None else f
        surf = skia.Surface(int(W * scale), int(H * scale))
        with surf as c:
            c.scale(scale, scale)
            c.clear(skia.ColorBLACK)
            g = self.draw_fn(c, t, f) or {}
        arr = surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3]
        if self.post:
            arr = self.post(arr, g, f)
        return arr

    def _chunk(self, args):
        frames, path, scale = args
        w, h = int(W * scale) // 2 * 2, int(H * scale) // 2 * 2
        with FrameWriter(path, w, h, self.fps, crf=15 if scale == 1 else 22, preset="medium") as fw:
            for f in frames:
                fw.write(self.frame(f / self.fps, scale, f)[:h, :w])
        return path

    def render(self, out=None, draft=False):
        if self.warm:
            self.warm()
        scale = 0.5 if draft else 1.0
        out = Path(out or self.out_dir / ("draft.mp4" if draft else "picture.mp4"))
        out.parent.mkdir(parents=True, exist_ok=True)
        frames = list(range(int(round(self.dur * self.fps))))
        n = os.cpu_count() or 2
        tmp = Path(tempfile.mkdtemp(dir=str(out.parent)))
        parts = np.array_split(np.array(frames), n * 4)
        jobs = [([int(x) for x in p], str(tmp / f"p{i:03d}.mp4"), scale) for i, p in enumerate(parts) if len(p)]
        with mp.get_context("fork").Pool(n) as pool:
            for i, _ in enumerate(pool.imap(self._chunk, jobs)):
                print(f"\r  render {i + 1}/{len(jobs)}", end="", flush=True)
        print()
        concat_videos(sorted(tmp.glob("p*.mp4")), out)
        for p in tmp.iterdir():
            p.unlink()
        tmp.rmdir()
        print("->", out)
        return out

    def stills(self, ts, scale=0.5):
        from PIL import Image
        d = self.out_dir / "stills"
        d.mkdir(parents=True, exist_ok=True)
        if self.warm:
            self.warm()
        for t in ts:
            Image.fromarray(self.frame(t, scale)).save(d / f"s_{t:06.2f}.png")
        print("->", d)

    def sheet(self, ts=None, cols=6, scale=0.25, name="sheet.png"):
        from PIL import Image, ImageDraw
        if self.warm:
            self.warm()
        ts = ts or [round(self.dur * (i + 0.5) / self.sheet_n, 2) for i in range(self.sheet_n)]
        tiles = [self.frame(t, scale) for t in ts]
        h, w = tiles[0].shape[:2]
        rows = (len(tiles) + cols - 1) // cols
        img = Image.new("RGB", (cols * (w + 6), rows * (h + 26)), (90, 90, 90))
        d = ImageDraw.Draw(img)
        for i, (t, tile) in enumerate(zip(ts, tiles)):
            r, cc = divmod(i, cols)
            img.paste(Image.fromarray(tile), (cc * (w + 6), r * (h + 26) + 22))
            d.text((cc * (w + 6) + 4, r * (h + 26) + 4), f"{t:.2f}s", fill=(255, 255, 255))
        self.out_dir.mkdir(parents=True, exist_ok=True)
        img.save(self.out_dir / name)
        print("->", self.out_dir / name)
