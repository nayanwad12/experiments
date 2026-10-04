"""Burned-in kinetic captions for the narration (most people watch muted).

Words pop in as the narrator says them; the word being spoken is sunshine yellow. Drawn after the
colour grade so night scenes don't tint them, and stepped at 12 fps like everything else.
"""

import skia

from lib import W, back_out, font, paint, prog
from timeline import CAPTION_UNTIL, VOICE

SIZE = 50
BASE_Y = 1022
_layout = {}


def _words(line):
    key = line["file"]
    if key not in _layout:
        f = font("Montserrat-Black.ttf", SIZE)
        gap = SIZE * 0.32
        words = [w for w, _ in line["words"]]
        widths = [f.measureText(w) for w in words]
        total = sum(widths) + gap * (len(words) - 1)
        x = W / 2 - total / 2
        out = []
        for (w, ts), wd in zip(line["words"], widths):
            out.append((w, ts, x, wd))
            x += wd + gap
        _layout[key] = (f, out)
    return _layout[key]


def draw(c, t):
    for line in VOICE:
        t0 = line["t"]
        if t0 >= CAPTION_UNTIL or not (t0 - 0.05 <= t < t0 + line["dur"] + 0.4):
            continue
        f, words = _words(line)
        shown = [i for i, (_, ts, _, _) in enumerate(words) if t >= t0 + ts - 0.04]
        if not shown:
            continue
        cur = shown[-1] if t < t0 + line["dur"] else -1
        for i in shown:
            w, ts, x, wd = words[i]
            s = 0.6 + 0.4 * back_out(prog(t, t0 + ts - 0.04, t0 + ts + 0.1), 2.4)
            c.save()
            c.translate(x + wd / 2, BASE_Y - SIZE * 0.35)
            c.scale(s * (1.08 if i == cur else 1), s * (1.08 if i == cur else 1))
            c.translate(-wd / 2, SIZE * 0.35)
            blob = skia.TextBlob.MakeFromString(w, f)
            c.drawTextBlob(blob, 4, 6, paint("#1a0f08", 0.45, blur=4))
            stroke = paint("#2B1A10", stroke=11)
            c.drawTextBlob(blob, 0, 0, stroke)
            c.drawTextBlob(blob, 0, 0, paint("#FFD84D" if i == cur else "#FFF6E6"))
            c.restore()
