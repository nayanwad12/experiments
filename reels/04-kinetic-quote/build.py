"""Reel 04: kinetic typography. "Everyone is waiting... just start." Every word lands on the voice.

    python3 build.py sheet | stills 1 5 9 | draft | render | sound | all
"""
import math
import sys
from pathlib import Path

import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
sys.path.insert(0, str(HERE))
from kit import (W, H, INK, LIME, PAPER, PERI, WHITE, Film, cap_height, clamp, e_back, e_expo, e_io,  # noqa: E402
                 e_out, endcard, fill, hrand, lerp, measure, prog, rrect, stroke, text)
from script import LINES, VOICE  # noqa: E402
from voice import Script, narrate  # noqa: E402

vo = narrate(LINES, HERE / "work", VOICE)
S = Script(vo, [("q1", 0.35), ("q2", 0.3), ("q3", 0.22), ("q4", 0.22), ("q5", 0.5), ("q6", 0.4), ("q7", 0.6),
                ("tail", 0.75)])
END_T = S.end("tail") + 0.5
DUR = END_T + 3.0
FPS = 30
START_T = S.find("q6", "start")

ORDER = ["q1", "q2", "q3", "q4", "q5", "q6", "q7", "tail"]
SEG = {lid: S.t(lid) - 0.12 for lid in ORDER}
BGS = {"q1": INK, "q2": LIME, "q3": PAPER, "q4": PERI, "q5": INK, "q6": LIME, "q7": PAPER, "tail": "#0F0F14"}
FGS = {"q1": WHITE, "q2": INK, "q3": INK, "q4": INK, "q5": WHITE, "q6": INK, "q7": INK, "tail": WHITE}


def seg_of(t):
    cur = ORDER[0]
    for lid in ORDER:
        if t >= SEG[lid]:
            cur = lid
    return cur


# ---------------------------------------------------------------- word blocks
def block(c, t, lid, rows, cy, fg, exit_t=None, lh=1.12, reveal="up"):
    """rows: [[(word_index, text, font, size, colour|None, extra), ...], ...]. Words reveal on their spoken time."""
    words = vo[lid]["words"]
    heights = [max(cap_height(f, s) for _, _, f, s, *_ in r) for r in rows]
    gaps = [max(s for _, _, _, s, *_ in r) * (lh - 0.72) for r in rows]
    total = sum(heights) + sum(gaps[1:])
    y = cy - total / 2
    ex = e_io(prog(t, exit_t, 0.22)) if exit_t else 0
    for ri, r in enumerate(rows):
        if ri:
            y += gaps[ri]
        y += heights[ri]
        sp = [measure(" ", f, s) * 0.9 for _, _, f, s, *_ in r]
        ws = [measure(tx, f, s) for _, tx, f, s, *_ in r]
        tot = sum(ws) + sum(sp[1:])
        x = W / 2 - tot / 2
        for wi, (idx, tx, f, s, cc, *extra) in enumerate(r):
            if wi:
                x += sp[wi]
            ts = S.start[lid] + words[min(idx, len(words) - 1)][1] - 0.05
            k = prog(t, ts, 0.28)
            if k > 0:
                ch = heights[ri]
                c.save()
                c.clipRect(skia.Rect.MakeLTRB(x - 40, y - ch * 1.35, x + ws[wi] + 40, y + s * 0.3))
                dy = (1 - e_expo(k)) * ch * 1.3 if reveal == "up" else 0
                dy -= ex * ch * 1.4
                sc = 1.0
                if "punch" in extra:
                    sc = 1 + 0.25 * math.exp(-max(0, t - ts) * 9)
                if "hl" in extra:
                    hk = e_out(prog(t, ts + 0.1, 0.25))
                    c.drawRect(skia.Rect.MakeLTRB(x - 14, y - ch - 14 + dy, x - 14 + (ws[wi] + 28) * hk, y + 18 + dy),
                               fill(LIME))
                c.translate(x + ws[wi] / 2, y + dy)
                c.scale(sc, sc)
                text(c, tx, 0, 0, f, s, cc or fg, 1.0, anchor="c", tracking=-0.02 if f in ("black", "anton") else 0)
                c.restore()
            x += ws[wi]


def bg_wipe(c, t):
    lid = seg_of(t)
    i = ORDER.index(lid)
    prev = ORDER[i - 1] if i else None
    k = e_io(prog(t, SEG[lid], 0.32))
    if prev and k < 1:
        c.drawPaint(fill(BGS[prev]))
        r = k * 2300
        cx, cy = (W / 2, H / 2) if i % 2 else (W * 0.15, H * 0.85)
        c.drawCircle(cx, cy, r, fill(BGS[lid]))
    else:
        c.drawPaint(fill(BGS[lid]))
    return lid


def draw(c, t, f):
    lid = bg_wipe(c, t)
    fg = FGS[lid]
    nxt = ORDER[ORDER.index(lid) + 1] if lid != "tail" else None
    ex = SEG[nxt] - 0.05 if nxt else None
    shake = 0
    if lid == "q1":
        block(c, t, "q1", [[(0, "Everyone", "black", 190, None)], [(1, "is", "black", 190, None)],
                           [(2, "waiting.", "italic", 260, LIME)]], 900, fg, ex)
        # waiting dots
        k = prog(t, S.w("q1", 2) + 0.3, 0.2)
        for i in range(3):
            a = k * (0.3 + 0.7 * (math.sin(t * 6 - i * 0.9) > 0))
            c.drawCircle(W / 2 - 60 + i * 60, 1290, 17, fill(WHITE, a))
    elif lid in ("q2", "q3", "q4"):
        lead = {"q2": [(0, "For", "black", 120, None), (1, "the", "black", 120, None)],
                "q3": [(0, "The", "black", 120, None)], "q4": [(0, "The", "black", 120, None)]}[lid]
        pi = len(lead)
        last = {"q2": "tool.", "q3": "time.", "q4": "skill."}[lid]
        # 'perfect' is the anchor word: same place across the three lines
        block(c, t, lid, [lead], 640, fg, ex)
        ts = S.t(lid) + vo[lid]["words"][pi][1] - 0.05
        k = e_out(prog(t, ts, 0.3)) if lid == "q2" else 1.0
        text(c, "perfect", W / 2, 960 + 80 * (1 - k), "italic", 260, fg, k)
        # the rolling last word
        tw = S.t(lid) + vo[lid]["words"][pi + 1][1] - 0.08
        kk = e_expo(prog(t, tw, 0.3))
        c.save()
        c.clipRect(skia.Rect.MakeLTRB(0, 1030, W, 1400))
        prev_word = {"q3": "tool.", "q4": "time."}.get(lid)
        if prev_word:
            text(c, prev_word, W / 2, 1310 - 330 * kk, "black", 250, fg, 1, tracking=-0.03)
        text(c, last, W / 2, 1310 + 330 * (1 - kk), "black", 250, fg, 1 if kk > 0 else 0, tracking=-0.03)
        c.restore()
        # tally marks: 1, 2, 3 "perfect" things
        n = {"q2": 1, "q3": 2, "q4": 3}[lid]
        for i in range(3):
            on = i < n
            c.drawRRect(rrect(W / 2 - 75 + i * 50 - 8, 1480, 16, 60, 8), fill(fg, 0.85 if on else 0.18))
    elif lid == "q5":
        z = 1 + 0.05 * (t - SEG["q5"])
        c.save()
        c.translate(W / 2, H / 2)
        c.scale(z, z)
        c.translate(-W / 2, -H / 2)
        block(c, t, "q5", [[(0, "But", "medium", 130, "#9A9AA2")], [(1, "the ones", "black", 170, None)],
                           [(3, "who win…", "black", 170, LIME)]], 930, fg, ex)
        c.restore()
    elif lid == "q6":
        k = prog(t, START_T - 0.04, 0.22)
        block(c, t, "q6", [[(0, "just", "italic", 180, None)]], 600, fg)
        if k > 0:
            s = lerp(2.4, 1.0, e_expo(k))
            c.save()
            c.translate(W / 2, 1160)
            c.scale(s, s)
            text(c, "START.", 0, 0, "anton", 330, INK, clamp(k * 3), tracking=-0.01)
            c.restore()
            shake = 22 * math.exp(-max(0, t - START_T) * 8)
        # flash
        fl = math.exp(-max(0, t - START_T) * 10) * (t >= START_T)
        if fl > 0.02:
            c.drawPaint(fill(WHITE, 0.5 * fl))
    elif lid == "q7":
        block(c, t, "q7", [[(0, "Your", "black", 165, None), (1, "idea", "black", 165, INK, "hl")],
                           [(2, "is the", "medium", 110, "#6A6A72")],
                           [(4, "only", "italic", 240, None), (5, "tool", "italic", 240, None)],
                           [(6, "you", "black", 165, None), (7, "need.", "black", 165, None, "punch")]], 940, fg, ex)
    else:
        rows = [(0, "Kinetic typography.", WHITE), (2, "One prompt.", LIME), (4, "No After Effects.", WHITE),
                (7, "No AI video tool.", WHITE)]
        words = vo["tail"]["words"]
        for i, (wi, s, cc) in enumerate(rows):
            ts = S.t("tail") + words[wi][1] - 0.05
            k = e_back(prog(t, ts, 0.35), 2)
            if k <= 0:
                continue
            y = 700 + i * 150
            x0, wdt = text(c, s, W / 2, y + 40 * (1 - k), "black", 92, cc, clamp(k), tracking=-0.02)
            if s.startswith("No "):
                sk = e_io(prog(t, ts + 0.45, 0.3))
                if sk > 0:
                    c.drawLine(x0 - 8, y - 30, x0 - 8 + (wdt + 16) * sk, y - 30, stroke("#FF4D5E", 10))
        text(c, "made with vibe editing", W / 2, 1420, "mono", 46, "#77777F", e_out(prog(t, S.t("tail") + 0.3, 0.5)))
    if t >= END_T:
        endcard(c, t, END_T)
    return {"shake": shake}


_SH = {}


def post(arr, g, f):
    s = g.get("shake", 0)
    if s < 0.5:
        return arr
    dx = int(s * (hrand(f, 1) - 0.5) * 2)
    dy = int(s * (hrand(f, 2) - 0.5) * 2)
    return np.roll(np.roll(arr, dx, 1), dy, 0)


film = Film(draw, DUR, FPS, post=post, out_dir=HERE / "out")


# ---------------------------------------------------------------- sound
def sound():
    import audio_kit as ak
    from sound import Mix
    m = Mix(DUR)
    m.voice(S.placements())
    SR = ak.SR
    pre = ak.music_bed("cinematic", seconds=START_T + 0.5, bpm=72, key="D", intro_bars=0, seed=2)
    pre = pre[: int(START_T * SR)]
    pre[-int(0.15 * SR):] *= np.linspace(1, 0, int(0.15 * SR))[:, None]
    post_bed = ak.music_bed("hype", seconds=DUR - START_T + 1, bpm=128, key="D", intro_bars=0, seed=8)
    bus = np.zeros((int(DUR * SR), 2), np.float32)
    ak.place(bus, pre, 0.0, 0)
    ak.place(bus, post_bed, START_T, 1.5)
    m.music(bus, gain_db=-14, duck_db=-8)
    for lid in ORDER[:-1]:
        for i, (w, s, e) in enumerate(vo[lid]["words"]):
            m.sfx("swish" if lid != "q6" else "click", S.t(lid) + s - 0.06, -20)
        if lid != "q1":
            m.sfx("whoosh", SEG[lid] - 0.05, -14)
    m.sfx("riser", START_T - 1.6, -12, dur=1.6)
    m.sfx("impact", START_T, -6)
    m.sfx("bass_drop", START_T, -10)
    for i in (0, 2, 4, 7):
        m.sfx("pop", S.t("tail") + vo["tail"]["words"][i][1], -10)
    m.sfx("whoosh", END_T - 0.25, -10)
    m.sfx("ding", END_T + 0.1, -12)
    m.finish(HERE / "out" / "picture.mp4", HERE / "out" / "04_kinetic_quote.mp4", HERE / "work")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    print(f"duration {DUR:.2f}s")
    if cmd == "sheet":
        film.sheet()
    elif cmd == "stills":
        film.stills([float(x) for x in sys.argv[2:]])
    elif cmd == "draft":
        film.render(draft=True)
    elif cmd == "render":
        film.render()
    elif cmd == "sound":
        sound()
    elif cmd == "all":
        film.render()
        sound()
