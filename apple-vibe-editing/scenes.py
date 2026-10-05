"""Apple-style 'Vibe Editing' film. draw(c, t) paints frame t (seconds) on a skia canvas."""

import math
import random
from contextlib import contextmanager
from pathlib import Path

import skia

from timeline import *  # noqa: F401,F403

HERE = Path(__file__).resolve().parent
INK = (29, 29, 31)
GRAY = (134, 134, 139)
LIGHT = (210, 210, 215)
CARD = (245, 245, 247)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

FONTS = {
    "light": "InterTight-300.ttf", "medium": "InterTight-500.ttf", "bold": "InterTight-700.ttf",
    "heavy": "InterTight-800.ttf", "black": "InterTight-900.ttf",
    "serif": "InstrumentSerif-400.ttf", "italic": "InstrumentSerif-400-italic.ttf",
    "mono": "JetBrainsMono-400.ttf", "monob": "JetBrainsMono-500.ttf",
}
_TF = {}


# ------------------------------------------------------------------ maths
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def prog(t, s, d):
    return clamp((t - s) / d) if d > 0 else float(t >= s)


def lerp(a, b, k):
    return a + (b - a) * k


def e_out(k):            # expo out: fast arrival, long silky settle
    return 1.0 if k >= 1 else 1 - 2 ** (-10 * k)


def e_in(k):
    return k ** 3


def e_io(k):
    return 4 * k ** 3 if k < 0.5 else 1 - (-2 * k + 2) ** 3 / 2


def e_io_expo(k):
    if k <= 0 or k >= 1:
        return clamp(k)
    return 2 ** (20 * k - 10) / 2 if k < 0.5 else (2 - 2 ** (-20 * k + 10)) / 2


def e_back(k, s=1.5):
    k -= 1
    return 1 + (s + 1) * k ** 3 + s * k ** 2


def spring(x, w=19.0, z=0.42):
    if x <= 0:
        return 0.0
    return 1 - math.exp(-z * w * x) * math.cos(w * math.sqrt(1 - z * z) * x)


def wobble(x, seed=0):
    return (math.sin(x * 1.7 + seed * 3.1) * 0.5 + math.sin(x * 3.3 + seed * 1.3) * 0.3
            + math.sin(x * 7.1 + seed * 0.7) * 0.2)


# ------------------------------------------------------------------ paint + text
def col(rgb, a=1.0):
    return skia.Color(rgb[0], rgb[1], rgb[2], int(255 * clamp(a)))


def fill(rgb, a=1.0, blur=0):
    p = skia.Paint(Color=col(rgb, a), AntiAlias=True)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


def stroke(rgb, w, a=1.0):
    p = skia.Paint(Color=col(rgb, a), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=w)
    p.setStrokeCap(skia.Paint.kRound_Cap)
    p.setStrokeJoin(skia.Paint.kRound_Join)
    return p


def font(name, size):
    if name not in _TF:
        _TF[name] = skia.Typeface.MakeFromFile(str(HERE / "fonts" / FONTS[name]))
    f = skia.Font(_TF[name], size)
    f.setEdging(skia.Font.Edging.kSubpixelAntiAlias)
    f.setSubpixel(True)
    f.setLinearMetrics(True)
    return f


def measure(s, name, size, tracking=0.0):
    f = font(name, size)
    if tracking == 0:
        return f.measureText(s)
    return sum(f.measureText(ch) for ch in s) + tracking * size * max(0, len(s) - 1)


def char_xs(s, name, size, tracking=0.0):
    f = font(name, size)
    xs, x = [], 0.0
    for ch in s:
        xs.append(x)
        x += f.measureText(ch) + tracking * size
    return xs


def cap_mid(name, size):
    """offset from visual centre of capitals to the baseline."""
    m = font(name, size).getMetrics()
    return m.fCapHeight / 2


def text(c, s, x, y, name, size, rgb=INK, a=1.0, align="center", tracking=0.0, paint=None):
    """y is the visual centre of the capital letters."""
    if a <= 0.003 or size < 1:
        return 0
    f = font(name, size)
    w = measure(s, name, size, tracking)
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    yb = y + cap_mid(name, size)
    p = paint or fill(rgb, a)
    if tracking == 0:
        c.drawString(s, x, yb, f, p)
    else:
        for ch, cx in zip(s, char_xs(s, name, size, tracking)):
            c.drawString(ch, x + cx, yb, f, p)
    return w


def runs_width(runs):
    return sum(measure(s, n, z, tr) for s, n, z, tr in runs)


@contextmanager
def layer(c, a=1.0, blur=0.0, scale=1.0, cx=W / 2, cy=H / 2, dx=0.0, dy=0.0, rot=0.0, sx=None, sy=None):
    """Composite whatever is drawn inside with opacity / gaussian blur / transform."""
    c.save()
    lay = a < 0.999 or blur > 0.25
    if lay:
        p = skia.Paint()
        p.setAlphaf(clamp(a))
        if blur > 0.25:
            p.setImageFilter(skia.ImageFilters.Blur(blur, blur, skia.TileMode.kDecal))
        c.saveLayer(None, p)
    c.translate(cx + dx, cy + dy)
    if rot:
        c.rotate(rot)
    c.scale(sx if sx is not None else scale, sy if sy is not None else scale)
    c.translate(-cx, -cy)
    try:
        yield
    finally:
        if lay:
            c.restore()
        c.restore()


def blur_in(c, t, t0, dur=0.55, rise=26, blur=18, scale0=1.0, cx=W / 2, cy=H / 2):
    """Apple keynote reveal: rise + de-blur + fade. Returns the context manager (or None if hidden)."""
    k = prog(t, t0, dur)
    e = e_out(k)
    return layer(c, a=clamp(k * 2.2), blur=blur * (1 - e), dy=rise * (1 - e),
                 scale=lerp(scale0, 1, e), cx=cx, cy=cy)


def words_in(c, t, runs, x, y, times, align="center", dur=0.55, rise=30, blur=16, rgb=INK):
    """runs: list of (string, font, size, tracking) drawn on one line, each revealed at times[i]."""
    total = runs_width(runs)
    cx = x - total / 2 if align == "center" else x
    for (s, n, z, tr), t0 in zip(runs, times):
        w = measure(s, n, z, tr)
        if t >= t0:
            with blur_in(c, t, t0, dur, rise, blur, 1.0, cx + w / 2, y):
                text(c, s, cx, y, n, z, rgb, align="left", tracking=tr)
        cx += w
    return total


def shimmer_paint(x0, x1, k, base=INK, hi=(190, 190, 196)):
    """black text with a soft light band travelling across (k: 0 -> 1)."""
    span = x1 - x0
    cxp = x0 - 0.3 * span + k * 1.6 * span
    bw = 0.16 * span
    pts = [skia.Point(cxp - bw, 0), skia.Point(cxp + bw, 0)]
    sh = skia.GradientShader.MakeLinear(pts, [col(base), col(hi), col(base)], [0.0, 0.5, 1.0],
                                        skia.TileMode.kClamp)
    p = skia.Paint(AntiAlias=True)
    p.setShader(sh)
    return p


def rise_letters(c, t, s, x, y, name, size, t0, each=0.028, dur=0.7, tracking=-0.035, rgb=INK, paint=None,
                 align="center"):
    """letters rise, de-blur and fade in one after another (keynote style)."""
    w = measure(s, name, size, tracking)
    x0 = x - w / 2 if align == "center" else x
    f = font(name, size)
    yb = y + cap_mid(name, size)
    p = paint or fill(rgb)
    for i, (ch, cx) in enumerate(zip(s, char_xs(s, name, size, tracking))):
        k = prog(t, t0 + i * each, dur)
        if k <= 0:
            continue
        e = e_out(k)
        cw = f.measureText(ch)
        with layer(c, a=clamp(k * 2.2), blur=14 * (1 - e), dy=size * 0.42 * (1 - e),
                   scale=lerp(1.25, 1, e), cx=x0 + cx + cw / 2, cy=y):
            c.drawString(ch, x0 + cx, yb, f, p)
    return x0, x0 + w


def caret(c, x, y, h, t, a=1.0, rgb=INK, w=5):
    on = 1.0 if (t * 2.2) % 1 < 0.6 else 0.15
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y - h / 2, w, h), w / 2, w / 2), fill(rgb, a * on))


def rrect(c, x, y, w, h, r, p):
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), p)


def soft_shadow(c, x, y, w, h, r, a=0.10, blur=34, dy=16):
    rrect(c, x, y + dy, w, h, r, fill(BLACK, a, blur))


def star4(c, x, y, r, p):
    path = skia.Path()
    path.moveTo(x, y - r)
    path.quadTo(x, y, x + r, y)
    path.quadTo(x, y, x, y + r)
    path.quadTo(x, y, x - r, y)
    path.quadTo(x, y, x, y - r)
    path.close()
    c.drawPath(path, p)


def bg(c, rgb=WHITE):
    c.drawRect(skia.Rect.MakeWH(W, H), fill(rgb))


def roll(c, t, t_switch, draw_old, draw_new, y, dist=90, d_out=0.22, d_in=0.55):
    """old line rolls up and blurs out, new one rises from below."""
    if t < t_switch + d_out:
        k = e_in(prog(t, t_switch, d_out))
        if k < 1:
            with layer(c, a=1 - k, blur=14 * k, dy=-dist * k, cy=y):
                draw_old()
    if t >= t_switch:
        k = prog(t, t_switch + 0.06, d_in)
        e = e_out(k)
        with layer(c, a=clamp(k * 2.5), blur=16 * (1 - e), dy=dist * (1 - e), cy=y):
            draw_new()


# ================================================================== scenes
def s_apps(c, t):
    # caret blink before the first word
    if t < 0.5:
        k = prog(t, 0.08, 0.2)
        caret(c, W / 2 - 3, H / 2, 120 * e_out(k), t + 0.3, a=k, w=7)
    names = [("After Effects", "black", 190, -0.04), ("Premiere Pro", "italic", 230, -0.01),
             ("Higgsfield", "monob", 170, -0.04)]
    labels = ["SUBSCRIPTION 01", "SUBSCRIPTION 02", "SUBSCRIPTION 03"]
    cy = H / 2 + 20

    def draw_name(i):
        def f():
            s, n, z, tr = names[i]
            text(c, s, W / 2, cy, n, z, INK, tracking=tr)
        return f

    def draw_label(i):
        def f():
            text(c, labels[i], W / 2, cy - 175, "mono", 26, GRAY, tracking=0.18)
        return f

    for i, th in enumerate(APP_HITS):
        nxt = APP_HITS[i + 1] if i + 1 < len(APP_HITS) else 99
        if t < th:
            continue
        if i == 0 and t < nxt:
            k = prog(t, th, 0.6)
            e = e_out(k)
            with layer(c, a=clamp(k * 2.5), blur=22 * (1 - e), scale=lerp(1.12, 1, e), cy=cy):
                draw_name(0)()
            with blur_in(c, t, th + 0.08, 0.5, 14, 10):
                draw_label(0)()
        elif i > 0 and t < nxt + 0.25:
            roll(c, t, th, draw_name(i - 1), draw_name(i), cy, dist=110)
            roll(c, t, th, draw_label(i - 1), draw_label(i), cy - 175, dist=40)
    # gentle push-in for the whole scene is applied by the master camera
    # tiny progress dots, Apple pager style
    k = prog(t, 0.6, 0.4)
    if k > 0:
        active = sum(t >= h for h in APP_HITS) - 1
        for i in range(3):
            x = W / 2 + (i - 1) * 28
            r = 6 if i == active else 5
            c.drawCircle(x, H - 150, r, fill(INK if i == active else LIGHT, k))


NOTIFS = [("Ae", "After Effects", "Subscription renewed"),
          ("Pr", "Premiere Pro", "Monthly plan renewed"),
          ("Hf", "Higgsfield", "Out of credits · Upgrade plan"),
          ("Pl", "Plugin Bundle", "Renewal due today"),
          ("Mu", "Stock Music", "Subscription renewed"),
          ("Tp", "Templates+", "Your free trial has ended"),
          ("Fx", "Transition Pack", "Payment processed")]


def notif_card(c, x, y, w, h, ini, title, body):
    soft_shadow(c, x, y, w, h, 30, 0.09, 30, 14)
    rrect(c, x, y, w, h, 30, fill(CARD))
    rrect(c, x + 22, y + (h - 66) / 2, 66, 66, 17, fill(INK))
    text(c, ini, x + 55, y + h / 2, "bold", 28, WHITE)
    text(c, title, x + 112, y + h / 2 - 19, "bold", 29, INK, align="left")
    text(c, body, x + 112, y + h / 2 + 21, "medium", 25, GRAY, align="left")
    text(c, "now", x + w - 30, y + h / 2 - 19, "medium", 22, GRAY, align="right")


def s_subs(c, t):
    end = 5.5
    x0, cw, ch, top, gap = 1040, 740, 110, 118, 126
    # notification stack
    for i, (ini, title, body) in enumerate(NOTIFS):
        ti = NOTIF_T[i]
        if t < ti:
            continue
        k = prog(t, ti, 0.5)
        e = e_back(k, 1.2) if k < 1 else 1
        slot = sum(e_io(prog(t, NOTIF_T[j], 0.4)) for j in range(i + 1, len(NOTIFS)))
        y = top + slot * gap - (1 - e_out(k)) * 70
        sc = lerp(0.92, 1, e)
        a = clamp(k * 3)
        # exit: cards drop away, staggered from the bottom up
        kx = prog(t, end - 0.25 + (len(NOTIFS) - 1 - slot) * 0.035, 0.55)
        rot = 0
        if kx > 0:
            ex = e_in(kx)
            y += 900 * ex
            rot = (8 if i % 2 else -7) * ex
            a *= 1 - kx
        with layer(c, a=a, scale=sc, rot=rot, cx=x0 + cw / 2, cy=y + ch / 2):
            notif_card(c, x0, y, cw, ch, ini, title, body)

    # left column copy
    xa = 150
    n_in = sum(t >= x for x in NOTIF_T)
    ka = prog(t, end - 0.3, 0.35)
    with layer(c, a=1 - ka, blur=16 * ka, dy=-30 * e_in(ka)):
        with blur_in(c, t, 3.12, 0.5, 18, 10, cx=xa + 150, cy=300):
            text(c, f"INBOX · {n_in} NEW", xa, 300, "mono", 26, GRAY, align="left", tracking=0.16)
        with blur_in(c, t, 3.2, 0.6, 34, 18, cx=xa + 300, cy=420):
            text(c, "Another month.", xa, 420, "light", 96, INK, align="left", tracking=-0.03)
        with blur_in(c, t, 4.06, 0.6, 34, 18, cx=xa + 300, cy=560):
            text(c, "Another", xa, 560, "heavy", 112, INK, align="left", tracking=-0.04)
        with blur_in(c, t, 4.22, 0.6, 34, 18, cx=xa + 300, cy=690):
            text(c, "subscription.", xa, 690, "heavy", 112, INK, align="left", tracking=-0.04)


def s_whatif(c, t):
    cy1, cy2 = 400, 600
    words = ["What ", "if ", "you ", "didn't ", "need"]
    times = [5.6 + i * 0.12 for i in range(len(words))]
    words_in(c, t, [(w, "light", 74, -0.02) for w in words], W / 2, cy1, times, rgb=GRAY)
    k = prog(t, ANY_T, 0.75)
    if k > 0:
        e = e_out(k)
        with layer(c, a=clamp(k * 2.5), blur=26 * (1 - e), scale=lerp(1.18, 1, e), cy=cy2):
            text(c, "any of them?", W / 2, cy2, "italic", 250, INK, tracking=-0.015)


def s_era(c, t):
    # small line, then the big reveal
    k_up = e_io(prog(t, VIBE_T - 0.1, 0.6))
    y_small = lerp(450, 330, k_up)
    words = [("This ", "medium", 54, 0), ("is ", "medium", 54, 0), ("the era ", "medium", 54, 0),
             ("of", "medium", 54, 0)]
    words_in(c, t, words, W / 2, y_small, ERA_WORDS, rgb=GRAY)

    if t >= VIBE_T:
        ks = e_out(prog(t, VIBE_T, 1.6))
        k_sh = prog(t, SHIMMER_T, 0.9)
        s, n, z, tr = "Vibe Editing.", "black", 220, -0.045
        w = measure(s, n, z, tr)
        paint = shimmer_paint(W / 2 - w / 2, W / 2 + w / 2, k_sh) if 0 < k_sh < 1 else None
        with layer(c, scale=lerp(1.07, 1, ks), cy=560):
            rise_letters(c, t, s, W / 2, 560, n, z, VIBE_T, each=0.03, dur=0.75, tracking=tr, paint=paint)
    k = prog(t, CAPTION_T, 0.8)
    if k > 0:
        e = e_out(k)
        ln = 90 * e
        c.drawLine(W / 2 - ln, 712, W / 2 + ln, 712, stroke(INK, 3, k))
        with layer(c, a=k, blur=10 * (1 - e), cy=780):
            text(c, "DIRECT THE VIBE  ·  LET AI DO THE KEYFRAMES", W / 2, 780, "mono", 26, GRAY,
                 tracking=lerp(0.4, 0.2, e))


TRACKS = [  # (row, [(start, len, [keyframe positions 0..1])])
    (0, [(0.02, 0.30, [0.1, 0.5, 0.9]), (0.35, 0.40, [0.2, 0.7]), (0.78, 0.20, [0.4])]),
    (1, [(0.08, 0.22, [0.3, 0.8]), (0.33, 0.25, [0.5]), (0.62, 0.34, [0.15, 0.45, 0.85])]),
    (2, [(0.00, 0.45, [0.25, 0.6, 0.9]), (0.50, 0.30, [0.3, 0.7])]),
    (3, [(0.15, 0.55, [0.1, 0.35, 0.65, 0.9]), (0.74, 0.22, [0.5])]),
]


def diamonds():
    out = []
    for row, clips in TRACKS:
        for (s, ln, kfs) in clips:
            for kf in kfs:
                out.append((row, s + ln * kf))
    rnd = random.Random(4)
    order = list(range(len(out)))
    rnd.shuffle(order)
    return out, order


DIAMONDS, DIA_ORDER = diamonds()


def prompt_text_at(t, s, t0, t1):
    times = type_times(s, t0, t1)
    return s[: sum(t >= x for x in times)]


def s_describe(c, t):
    # headline
    hy = 180

    def old():
        text(c, "You don't drag keyframes.", W / 2, hy, "heavy", 78, INK, tracking=-0.03)

    def new():
        runs = [("You describe ", "heavy", 78, -0.03), ("the vibe.", "italic", 100, -0.01)]
        x = W / 2 - runs_width(runs) / 2
        for s, n, z, tr in runs:
            x += text(c, s, x, hy, n, z, INK, align="left", tracking=tr)

    if t < DESCRIBE_T:
        with blur_in(c, t, DRAG_T, 0.55, 30, 16, cy=hy):
            old()
    else:
        roll(c, t, DESCRIBE_T, old, new, hy, dist=80)

    # timeline panel -> morphs into a prompt bar
    km = e_io_expo(prog(t, MORPH_T, 0.6))
    pw, ph, pr = lerp(1320, 1120, km), lerp(430, 124, km), lerp(36, 62, km)
    pcy = lerp(600, 590, km)
    px, py = W / 2 - pw / 2, pcy - ph / 2
    soft_shadow(c, px, py, pw, ph, pr, lerp(0.0, 0.10, km), 40, 18)
    rrect(c, px, py, pw, ph, pr, fill(CARD if km < 0.5 else WHITE))
    if km >= 0.5:
        rrect(c, px, py, pw, ph, pr, stroke(LIGHT, 2, clamp((km - 0.5) * 3)))
    else:
        rrect(c, px, py, pw, ph, pr, fill(CARD, 1 - km * 2))
    ka = 1 - clamp(km * 3)  # timeline contents fade early in the morph
    if ka > 0:
        c.save()
        c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(px, py, pw, ph), pr, pr), True)
        lx, lw = px + 150, pw - 200
        ty0 = py + 95
        # ruler
        text(c, "00:00:12:04", px + 40, py + 44, "mono", 22, GRAY, a=ka, align="left")
        for i in range(25):
            x = lx + lw * i / 24
            c.drawLine(x, py + 36, x, py + (52 if i % 4 == 0 else 46), stroke(GRAY, 1.5, ka * 0.6))
        names = ["V1", "V2", "T1", "A1"]
        clip_fade = 1 - e_out(prog(t, DIAMOND_T + 0.35, 0.4))
        for row, clips in TRACKS:
            ry = ty0 + row * 76
            text(c, names[row], px + 60, ry + 28, "monob", 22, GRAY, a=ka)
            for (s, ln, kfs) in clips:
                rrect(c, lx + s * lw, ry, ln * lw - 6, 56, 12,
                      fill((226, 226, 231) if row != 3 else (214, 214, 220), ka * (0.35 + 0.65 * clip_fade)))
        for idx, (row, pos) in enumerate(DIAMONDS):
            ry = ty0 + row * 76 + 28
            td = DIAMOND_T + DIA_ORDER.index(idx) * 0.028
            kd = prog(t, td, 0.22)
            sc = 1 + 0.6 * math.sin(math.pi * clamp(kd * 1.6)) if kd < 0.62 else 0
            if kd >= 1 or sc <= 0:
                continue
            c.save()
            c.translate(lx + pos * lw, ry)
            c.rotate(45)
            c.scale(sc, sc)
            rrect(c, -10, -10, 20, 20, 4, fill(INK, ka))
            c.restore()
        # playhead
        phx = lx + lw * clamp((t - 10.9) / 1.6) * 0.8
        c.drawLine(phx, py + 30, phx, py + ph - 20, stroke(INK, 3, ka))
        c.drawCircle(phx, py + 30, 8, fill(INK, ka))
        c.restore()

    # prompt contents
    kp = prog(t, MORPH_T + 0.35, 0.3)
    if kp > 0:
        star4(c, px + 66, pcy, 20 * e_out(kp), fill(INK, kp))
        s = prompt_text_at(t, PROMPT, TYPE_T0, TYPE_T1)
        tx = px + 108
        w = text(c, s, tx, pcy, "medium", 46, INK, a=kp, align="left", tracking=-0.01)
        if not s:
            text(c, "Describe your video…", tx, pcy, "medium", 46, LIGHT, a=kp * (1 - prog(t, TYPE_T0, 0.05)),
                 align="left")
        if t < ENTER_T:
            caret(c, tx + w + 4, pcy, 54, t, a=kp, w=4)
        # send button
        bx, by = px + pw - 66, pcy
        press = 1 - 0.14 * math.sin(math.pi * prog(t, ENTER_T, 0.16))
        ready = prog(t, TYPE_T1, 0.2)
        c.drawCircle(bx, by, 40 * press * e_out(kp), fill(lerp_rgb(LIGHT, INK, ready), kp))
        c.save()
        c.translate(bx, by)
        c.scale(press, press)
        path = skia.Path()
        path.moveTo(0, 16)
        path.lineTo(0, -15)
        path.moveTo(-12, -3)
        path.lineTo(0, -15)
        path.lineTo(12, -3)
        c.drawPath(path, stroke(WHITE, 5, kp))
        c.restore()
        # iris: black circle grows out of the send button
        ki = prog(t, IRIS_T0, IRIS_T1 - IRIS_T0)
        if ki > 0:
            r = lerp(40, 2300, e_in(ki) * 0.6 + e_io(ki) * 0.4)
            c.drawCircle(bx, by, r, fill(BLACK))


def lerp_rgb(a, b, k):
    return tuple(int(lerp(a[i], b[i], k)) for i in range(3))


def morph_shape(c, x, y, s, t, rgb):
    k = 0.5 + 0.5 * math.sin(t * 5.5)
    r = lerp(s * 0.18, s / 2, k)
    w = lerp(s, s * 1.5, 0.5 + 0.5 * math.sin(t * 5.5 + 1.8))
    c.save()
    c.translate(x, y)
    c.rotate(t * 160)
    rrect(c, -w / 2, -s / 2, w, s, r, fill(rgb))
    c.restore()


def wave_bars(c, cx, cy, n, total_w, max_h, t, amp, rgb=INK, bw=None, seed=0):
    step = total_w / n
    bw = bw or step * 0.55
    for i in range(n):
        x = cx - total_w / 2 + (i + 0.5) * step
        u = i / (n - 1)
        env = math.sin(math.pi * u) ** 0.8
        v = abs(wobble(t * 9 + i * 0.55, seed + i % 5)) * 0.8 + 0.2 * abs(math.sin(t * 13 + i))
        h = max(bw, max_h * amp * env * v)
        rrect(c, x - bw / 2, cy - h / 2, bw, h, bw / 2, fill(rgb))


def s_kinetic(c, t):
    s1, s2 = "Kinetic", "type."
    n, z, tr = "black", 210, -0.04
    full = s1 + " " + s2
    w = measure(full, n, z, tr)
    x0 = W / 2 - w / 2
    f = font(n, z)
    yb = H / 2 + cap_mid(n, z)
    rnd = random.Random(11)
    for i, (ch, cx) in enumerate(zip(full, char_xs(full, n, z, tr))):
        if ch == " ":
            continue
        t0 = (KINETIC_T if i < len(s1) else TYPE_WORD_T) + (i % 8) * 0.032
        x = t - t0
        if x < 0:
            continue
        k = spring(x, 17, 0.38)
        rot0 = rnd.uniform(-50, 50)
        dy0 = rnd.uniform(180, 320) * (1 if i % 2 else -1)
        cw = f.measureText(ch)
        wav = 7 * math.sin(2 * math.pi * (t * 1.1 - i * 0.07)) * prog(t, t0 + 0.5, 0.4)
        c.save()
        c.translate(x0 + cx + cw / 2, yb - z * 0.36 + (1 - k) * dy0 + wav)
        c.rotate((1 - k) * rot0)
        sc = lerp(0.3, 1, clamp(k, 0, 1.3))
        c.scale(sc, sc)
        c.drawString(ch, -cw / 2, z * 0.36, f, fill(INK, clamp(x * 8)))
        c.restore()


def s_sound(c, t):
    words_in(c, t, [("Sound ", "heavy", 120, -0.035), ("design.", "italic", 150, -0.01)], W / 2, 430,
             [SOUND_T, DESIGN_T])
    amp = e_out(prog(t, SOUND_T + 0.05, 0.5))
    wave_bars(c, W / 2, 680, 56, 1250, 230, t, amp)


def s_features(c, t):
    # a) Smooth transitions, white on black
    if t < IRIS2_T1:
        bg(c, BLACK)
        words_in(c, t, [("Smooth ", "heavy", 124, -0.035), ("transitions.", "italic", 150, -0.01)], W / 2, 640,
                 [SMOOTH_T, TRANSITIONS_T], rgb=WHITE)
        ks = e_out(prog(t, SMOOTH_T - 0.05, 0.6))
        if ks > 0:
            morph_shape(c, W / 2, 380, 130 * ks, t, WHITE)
    # b) Kinetic type, revealed through a white iris
    if IRIS2_T0 <= t < SOUND_PUSH_T + 0.4:
        ki = e_io_expo(prog(t, IRIS2_T0, IRIS2_T1 - IRIS2_T0))
        kx = prog(t, SOUND_PUSH_T, 0.3)
        c.save()
        if ki < 1:
            p = skia.Path()
            p.addCircle(W / 2, 380, lerp(0, 2200, ki))
            c.clipPath(p, True)
        with layer(c, a=1 - kx, blur=26 * kx, dx=-W * 0.45 * e_in(kx)):
            bg(c, WHITE)
            s_kinetic(c, t)
        c.restore()
    # c) Sound design pushes in from the right
    if SOUND_PUSH_T <= t < MONTAGE[0][0]:
        k = e_out(prog(t, SOUND_PUSH_T, 0.5))
        with layer(c, a=clamp(prog(t, SOUND_PUSH_T, 0.15)), blur=20 * (1 - k), dx=W * 0.45 * (1 - k)):
            s_sound(c, t)
    # d) rapid-fire montage, hard cuts on the beat
    for i, (tm, word) in enumerate(MONTAGE):
        nxt = MONTAGE[i + 1][0] if i + 1 < len(MONTAGE) else 99
        if not (tm <= t < nxt):
            continue
        dark = i % 2 == 1
        bg(c, BLACK if dark else WHITE)
        fg = WHITE if dark else INK
        k = e_out(prog(t, tm, 0.35))
        style = [("black", 230, -0.045), ("italic", 300, -0.01), ("monob", 200, -0.05), ("light", 260, -0.04)][i]
        dx = [-60, 0, 80, 0][i] * (1 - k)
        with layer(c, scale=lerp(1.12, 1, k), dx=dx, blur=8 * (1 - k)):
            if i == 2:  # Motion: speed-trail copies
                for j in range(4, 0, -1):
                    text(c, word, W / 2 - j * 34 * (1 - k * 0.7), H / 2, style[0], style[1], fg,
                         a=0.10 * (5 - j) * (1 - k * 0.6), tracking=style[2])
            text(c, word, W / 2, H / 2, style[0], style[1], fg, tracking=style[2])
            if i == 3:
                wave_bars(c, W / 2, H / 2 + 200, 40, 700, 60, t, 1, fg, seed=3)
        text(c, f"0{i + 1}", 90, 90, "mono", 24, GRAY, align="left", tracking=0.1)


def tc(sec):
    f = int(sec * 30) % 30
    return f"00:{int(sec) // 60:02d}:{int(sec) % 60:02d}:{f:02d}"


def s_meta(c, t):
    t_rel = t - 20.3
    tr = min(0.3 + t_rel * 4.45, 20.25)  # replay of this very film, fast-forward
    k = e_io_expo(prog(t, 20.3, 0.62))
    rx, ry, rw, rh = lerp(0, 480, k), lerp(0, 175, k), lerp(W, 960, k), lerp(H, 540, k)
    rad = lerp(0, 30, k)
    if k > 0:
        soft_shadow(c, rx, ry, rw, rh, rad, 0.16 * k, 50, 26)
    c.save()
    c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(rx, ry, rw, rh), rad, rad), True)
    c.translate(rx, ry)
    c.scale(rw / W, rh / H)
    draw_film(c, tr, camera=False)
    c.restore()
    rrect(c, rx, ry, rw, rh, rad, stroke(LIGHT, 2, k))

    # headline
    hy = 92

    def h1():
        text(c, "Even this video.", W / 2, hy, "heavy", 66, INK, tracking=-0.03)

    def h2():
        runs = [("Every frame, ", "light", 66, -0.03), ("every sound,", "heavy", 66, -0.03)]
        x = W / 2 - runs_width(runs) / 2
        for s, n, z, trk in runs:
            x += text(c, s, x, hy, n, z, INK, align="left", tracking=trk)

    def h3():
        runs = [("came from ", "heavy", 66, -0.03), ("a prompt.", "italic", 84, -0.01)]
        x = W / 2 - runs_width(runs) / 2
        for s, n, z, trk in runs:
            x += text(c, s, x, hy, n, z, INK, align="left", tracking=trk)

    if t < FRAME_T:
        with blur_in(c, t, EVEN_T, 0.55, 26, 16, cy=hy):
            h1()
    elif t < PROMPT2_T:
        roll(c, t, FRAME_T, h1, h2, hy, dist=60)
    else:
        roll(c, t, PROMPT2_T, h2, h3, hy, dist=60)

    # player chrome
    kc = prog(t, 20.8, 0.5)
    if kc > 0:
        e = e_out(kc)
        cy = 752
        with layer(c, a=kc, dy=20 * (1 - e)):
            p = skia.Path()
            p.moveTo(486, cy - 13)
            p.lineTo(508, cy)
            p.lineTo(486, cy + 13)
            p.close()
            c.drawPath(p, fill(INK))
            text(c, tc(tr), 530, cy, "mono", 22, GRAY, align="left")
            bx0, bx1 = 720, 1170
            c.drawLine(bx0, cy, bx1, cy, stroke(LIGHT, 5))
            c.drawLine(bx0, cy, lerp(bx0, bx1, tr / DURATION), cy, stroke(INK, 5))
            c.drawCircle(lerp(bx0, bx1, tr / DURATION), cy, 9, fill(INK))
            pulse = 1 + 0.25 * math.exp(-8 * max(0, t - FRAME_T)) * (t >= FRAME_T)
            hi = prog(t, FRAME_T, 0.2)
            with layer(c, scale=pulse, cx=1440, cy=cy):
                text(c, f"FRAME {int(tr * FPS):04d}", 1440, cy, "monob", 22, lerp_rgb(GRAY, INK, hi),
                     align="right", tracking=0.06)
    # every sound: waveform strip
    kw = prog(t, SOUND2_T, 0.4)
    kw_out = prog(t, PROMPT2_T + 0.1, 0.35)
    if kw > 0 and kw_out < 1:
        with layer(c, a=kw * (1 - kw_out), sy=e_out(kw) * (1 - kw_out * 0.6), cy=820):
            wave_bars(c, W / 2, 820, 96, 960, 56, t, 1, INK, bw=4, seed=5)
    # prompt pill
    kp = prog(t, PROMPT2_T + 0.15, 0.6)
    if kp > 0:
        e = e_out(kp)
        pw, ph = 1060, 92
        px, py = W / 2 - pw / 2, 915 - ph / 2 + 40 * (1 - e)
        with layer(c, a=clamp(kp * 2), blur=12 * (1 - e)):
            soft_shadow(c, px, py, pw, ph, 46, 0.08, 30, 12)
            rrect(c, px, py, pw, ph, 46, fill(WHITE))
            rrect(c, px, py, pw, ph, 46, stroke(LIGHT, 2))
            star4(c, px + 52, py + ph / 2, 16, fill(INK))
            s = prompt_text_at(t, PROMPT2, PROMPT2_T0, PROMPT2_T1)
            w = text(c, s, px + 88, py + ph / 2, "mono", 28, INK, align="left")
            caret(c, px + 92 + w, py + ph / 2, 38, t, w=3)


ICONS = ["timeline", "plug", "card"]


def icon(c, kind, x, y, k, rgb=INK):
    if k <= 0:
        return
    c.save()
    c.translate(x, y)
    s = e_back(clamp(k), 1.6)
    c.scale(s, s)
    sw = 9
    if kind == "timeline":
        for i, (o, ln) in enumerate([(-40, 70), (-20, 64), (-48, 52)]):
            rrect(c, o, -36 + i * 30, ln, 18, 9, fill(rgb))
        c.drawLine(-12, -52, -12, 52, stroke(rgb, 5))
    elif kind == "plug":
        rrect(c, -30, -26, 60, 46, 14, fill(rgb))
        c.drawLine(-14, -26, -14, -50, stroke(rgb, sw))
        c.drawLine(14, -26, 14, -50, stroke(rgb, sw))
        p = skia.Path()
        p.moveTo(0, 20)
        p.cubicTo(0, 50, 30, 40, 34, 58)
        c.drawPath(p, stroke(rgb, sw))
    else:
        rrect(c, -58, -38, 116, 76, 14, stroke(rgb, 7))
        c.drawLine(-58, -14, 58, -14, stroke(rgb, 12))
        rrect(c, -42, 6, 26, 18, 4, fill(rgb))
    c.restore()


def no_sign(c, x, y, k, rgb=INK):
    if k <= 0:
        return
    r = 92
    a1 = e_io(clamp(k / 0.65))
    p = skia.Path()
    p.addArc(skia.Rect.MakeLTRB(x - r, y - r, x + r, y + r), -135, 360 * a1)
    c.drawPath(p, stroke(rgb, 9))
    a2 = e_out(prog(k, 0.55, 0.45))
    if a2 > 0:
        d = r * 0.7071
        c.drawLine(x - d, y - d, lerp(x - d, x + d, a2), lerp(y - d, y + d, a2), stroke(rgb, 9))


def s_nos(c, t):
    items = ["timeline.", "plugins.", "subscriptions."]
    x0, ys = 230, [300, 540, 780]
    z = 128
    for i, (word, t0, y) in enumerate(zip(items, NO_T, ys)):
        if t < t0:
            continue
        nxt = NO_T[i + 1] if i + 1 < len(NO_T) else 99
        dim = e_io(prog(t, nxt, 0.35)) * (1 if i < 2 else 0)
        rgb = lerp_rgb(INK, LIGHT, dim)
        with blur_in(c, t, t0, 0.6, 60, 22, cx=x0 + 400, cy=y):
            w = text(c, "No ", x0, y, "light", z, lerp_rgb(GRAY, LIGHT, dim), align="left", tracking=-0.03)
            text(c, word, x0 + w, y, "black", z, rgb, align="left", tracking=-0.045)
        ki = prog(t, t0 + 0.05, 0.4)
        icon(c, ICONS[i], 1600, y, ki, rgb)
        no_sign(c, 1600, y, prog(t, t0 + 0.22, 0.42), rgb)


def s_idea(c, t):
    words = [("Just ", "italic", 180, -0.01), ("your ", "italic", 180, -0.01), ("idea,", "italic", 180, -0.01)]
    words_in(c, t, words, W / 2, 430, IDEA_WORDS, dur=0.7, rise=34, blur=20)
    if t >= WORDS_T0 - 0.05:
        s = prompt_text_at(t, WORDS_LINE, WORDS_T0, WORDS_T1)
        full = measure(WORDS_LINE, "medium", 60, -0.01)
        x = W / 2 - full / 2
        w = text(c, s, x, 640, "medium", 60, INK, align="left", tracking=-0.01)
        caret(c, x + w + 6, 640, 64, t, w=5)
    # quiet underline that grows under the idea
    k = e_out(prog(t, 29.1, 1.2))
    if k > 0:
        c.drawLine(W / 2 - 160 * k, 540, W / 2 + 160 * k, 540, stroke(LIGHT, 3, k))


def s_end(c, t):
    with blur_in(c, t, WELCOME_T, 0.6, 24, 16, cy=360):
        text(c, "Welcome to", W / 2, 360, "medium", 54, GRAY, tracking=-0.01)
    if t >= LOGO_T:
        s, n, z, tr = "Vibe Editing.", "black", 220, -0.045
        w = measure(s, n, z, tr)
        k_sh = prog(t, LOGO_SHIMMER_T, 1.0)
        paint = shimmer_paint(W / 2 - w / 2, W / 2 + w / 2, k_sh) if 0 < k_sh < 1 else None
        ks = e_out(prog(t, LOGO_T, 1.6))
        with layer(c, scale=lerp(1.08, 1, ks), cy=530):
            rise_letters(c, t, s, W / 2, 530, n, z, LOGO_T, each=0.03, dur=0.75, tracking=tr, paint=paint)
    with blur_in(c, t, TAGLINE_T, 0.7, 26, 16, cy=690):
        text(c, "Direct the vibe.", W / 2, 690, "italic", 84, INK, tracking=-0.005)
    # recap row with strike-throughs
    items = ["After Effects", "Premiere Pro", "Higgsfield", "Subscriptions"]
    gap = 70
    ws = [measure(s, "mono", 28, 0.02) for s in items]
    x = W / 2 - (sum(ws) + gap * (len(items) - 1)) / 2
    y = 850
    for i, (s, w) in enumerate(zip(items, ws)):
        ka = prog(t, STRIKES[0] - 0.45 + i * 0.07, 0.5)
        if ka > 0:
            ks = e_io(prog(t, STRIKES[i], 0.28))
            gray = lerp_rgb(INK, GRAY, ks)
            with layer(c, a=ka, blur=8 * (1 - e_out(ka)), dy=16 * (1 - e_out(ka)), cy=y):
                text(c, s, x, y, "mono", 28, gray, align="left", tracking=0.02)
                if ks > 0:
                    c.drawLine(x - 6, y, x - 6 + (w + 12) * ks, y, stroke(INK, 3.5))
        x += w + gap


# ================================================================== master
FUNCS = {"apps": s_apps, "subs": s_subs, "whatif": s_whatif, "era": s_era, "describe": s_describe,
         "features": s_features, "meta": s_meta, "nos": s_nos, "idea": s_idea, "end": s_end}


def scene_camera(name, t, s, e):
    """slow continuous push-in inside each scene, for life."""
    return 1 + 0.035 * clamp((t - s) / max(1e-3, e - s))


def draw_film(c, t, camera=True):
    bg(c, WHITE)
    for i, (name, s, e) in enumerate(SCENES):
        kind_in, d_in = TRANS.get(name, ("cut", 0))
        nxt = SCENES[i + 1][0] if i + 1 < len(SCENES) else None
        kind_out, d_out = TRANS.get(nxt, ("cut", 0)) if nxt else ("cut", 0)
        if not (s - d_in <= t < e + d_out) and not (i == len(SCENES) - 1 and t >= s):
            continue
        a, blur, sc, dx, dy = 1.0, 0.0, 1.0, 0.0, 0.0
        # entering
        if d_in and t < s + d_in:
            k = prog(t, s - d_in, 2 * d_in)
            ee = e_out(k)
            if kind_in == "push_up":
                dy, blur, a = H * 0.3 * (1 - ee), 22 * (1 - ee), clamp(k * 2)
            elif kind_in == "zoom":
                sc, blur, a = lerp(0.82, 1, ee), 24 * (1 - ee), clamp(k * 2)
            elif kind_in == "slide_left":
                dx, blur, a = W * 0.35 * (1 - ee), 22 * (1 - ee), clamp(k * 2)
            elif kind_in == "blur":
                blur, a = 26 * (1 - ee), clamp(k * 1.5)
        # leaving
        if d_out and t >= e - d_out:
            k = prog(t, e - d_out, 2 * d_out)
            ei = e_in(k)
            if kind_out == "push_up":
                dy, blur, a = -H * 0.3 * ei, 22 * ei, 1 - clamp(k * 1.6)
            elif kind_out == "zoom":
                sc, blur, a = lerp(1, 2.4, ei), 30 * ei, 1 - clamp(k * 1.6)
            elif kind_out == "slide_left":
                dx, blur, a = -W * 0.35 * ei, 22 * ei, 1 - clamp(k * 1.6)
            elif kind_out == "blur":
                blur, a = 26 * ei, 1 - clamp(k * 1.3)
        if a <= 0.003:
            continue
        if camera:
            sc *= scene_camera(name, t, s, e)
        if name == "end":
            kf = prog(t, FADE_T0, FADE_T1 - FADE_T0)
            a *= 1 - e_io(kf)
            blur += 20 * e_in(kf)
            sc *= 1 + 0.04 * e_in(kf)
        with layer(c, a=a, blur=blur, scale=sc, dx=dx, dy=dy):
            FUNCS[name](c, t)


def draw(c, t):
    draw_film(c, t)
