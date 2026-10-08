"""B3-02 "Vibe Editing, explained": a Vox-style paper-cut collage explainer (1080x1920, 30 fps, ~35 s, narrated).

    python3 build.py stills 1.2 6 12    # preview frames -> out/stills/
    python3 build.py sheet              # contact sheet -> out/sheet.png
    python3 build.py render             # picture -> out/picture.mp4
    python3 build.py sound              # voice + music + paper SFX -> out/vibe_editing_vox_papercut.mp4
    python3 build.py all

Every cue reads its time from the narration (S.find("then", "keyframes") = when "keyframes" is spoken).
"""
import math
import sys
from pathlib import Path

import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "common"))
import collage as K  # noqa: E402
import props as P  # noqa: E402
from collage import INK, NEWS, RED, WHITE, YEL, jit, on_twos, pop  # noqa: E402
from kit import H, W, Film, chunk_words, clamp, e_io, e_out, fill, font, hrand, lerp, measure, prog, text  # noqa: E402
from script import LINES, VOICE  # noqa: E402
from voice import Script, narrate  # noqa: E402

FPS = 30
vo = narrate(LINES, HERE / "work", VOICE)
S = Script(vo, [("hook", 0.35), ("cut", 0.4), ("then", 0.55), ("hours", 0.5), ("what", 0.7), ("vibe", 0.3),
                ("prog", 0.65), ("list", 0.45), ("no", 0.55), ("just", 0.35), ("cta", 0.75)])
DUR = round(S.end("cta") + 1.7, 3)

# ---------------------------------------------------------------- cue sheet (all from the voice)
T = dict(
    hund=S.find("hook", "hundred"), edit=S.find("hook", "editing"), one=S.find("hook", "one"),
    cut=S.t("cut"), sc=S.find("then", "Scissors"), tape=S.find("then", "tape"), tl=S.find("then", "timelines"),
    kf=S.find("then", "keyframes"),
    hours=S.t("hours"), click=S.find("hours", "clicking"), minute=S.find("hours", "minute"),
    what=S.t("what"), never=S.find("what", "never"), drag=S.find("what", "dragged"),
    vibe0=S.t("vibe"), desc=S.find("vibe", "described"), vibe=S.find("vibe", "vibe"),
    prog0=S.t("prog"), prog=S.find("prog", "program"), direct=S.find("prog", "direct"), editor=S.find("prog", "editor"),
    list0=S.t("list"), cap=S.find("list", "Captions"), mot=S.find("list", "Motion"), anim=S.find("list", "Animation"),
    ads=S.find("list", "Ads"), all=S.find("list", "All"), prompt=S.find("list", "prompt"),
    no0=S.t("no"), ntl=S.find("no", "timeline"), nkf=S.find("no", "keyframes"),
    just=S.t("just"), you=S.find("just", "you"), vb=S.find("just", "vibe"),
    cta=S.t("cta"), by=S.find("cta", "Ideabro"), link=S.find("cta", "Link"),
)
# scene changes: a torn sheet of paper sweeps up and the scene swaps behind it (at the sheet's midpoint)
WIPE_D = 0.6
CHANGES = [T["hours"] - 0.12, T["what"] - 0.15, T["prog0"] - 0.15, T["no0"] - 0.12, T["cta"] - 0.2]
WIPE_COL = [NEWS, YEL, NEWS, YEL, NEWS]
CHAPTERS = ["CH.01  THE CUT", "CH.02  THE GRIND", "CH.03  THE VIBE", "CH.04  THE PROGRAM", "CH.05  THE SHIFT",
            "VIBE EDITING"]
STAMPS = [T["cut"] + 0.06, T["ntl"] + 0.05, T["nkf"] + 0.05, T["link"] + 0.5]
TYPED = ["> make it feel like", "  a 90s music video."]
TYPE_T0, TYPE_T1 = T["desc"] - 0.25, S.end("vibe") + 0.35


def scene_of(t):
    return sum(t >= c for c in CHANGES)


# ---------------------------------------------------------------- cached cutouts (built once, before forking)
C = {}


def warm():
    if C:
        return
    C["film"], C["film_l"], C["film_r"] = P.film_cuts()
    C["blade_a"], C["blade_b"] = P.scissor_cuts()
    C["clock"] = P.clock_cut()
    C["clip"] = P.clip_cut()
    C["slate"], C["clap"] = P.clapper_cuts()
    C["fibre"] = K.fibre_texture()


# ---------------------------------------------------------------- helpers
def headline(c, s, x, y, size, t, t0, hl=None, color=INK, seed=0, a=1.0):
    """big black sans on the desk, popped in on twos; hl=(t_hl, x_pad) adds a yellow swipe behind it."""
    k = pop(t, t0, 0.22, 1.8)
    if k <= 0:
        return
    w = measure(s, "black", size)
    jx, jy, jr = jit(seed, t, 1.0, 0.3)
    c.save()
    c.translate(x + jx, y + jy)
    c.rotate(jr)
    c.scale(k, k)
    if hl is not None:
        K.highlighter(c, -w / 2 - 22, -size * 0.78, w / 2 + 22, size * 0.12, e_out(prog(t, hl, 0.32)), seed)
    text(c, s, 0, 0, "black", size, color, a)
    c.restore()


def note(c, s, x, y, size, t, t0, rot=-5, color=RED, a=1.0):
    """handwritten marker note, written on left to right."""
    if t < t0:
        return
    k = clamp((t - t0) / max(0.25, len(s) * 0.035))
    f = font("caveat", size)
    w = f.measureText(s)
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.clipRect(skia.Rect.MakeXYWH(-w / 2 - 10, -size, (w + 20) * k, size * 1.6))
    c.drawString(s, -w / 2, 0, f, fill(color, a))
    c.restore()


def slide(t, t0, d, a, b):
    return lerp(a, b, e_out(prog(on_twos(t), t0, d)))


def keyframes(c, t, t0, n_max, region, seed, dur=1.6, scatter=None):
    """diamonds piling up; scatter=t1 sends them flying."""
    n = int(n_max * clamp((t - t0) / dur) ** 0.7) if t >= t0 else 0
    x0, y0, x1, y1 = region
    for i in range(n):
        ti = t0 + dur * (i / n_max) ** (1 / 0.7)
        k = pop(t, ti, 0.18, 2.6)
        x, y = lerp(x0, x1, hrand(seed, i, 1)), lerp(y0, y1, hrand(seed, i, 2))
        s = 22 + hrand(seed, i, 3) * 30
        rot = (hrand(seed, i, 4) - 0.5) * 30
        if scatter is not None and t > scatter:
            ks = e_io(prog(on_twos(t), scatter + hrand(seed, i, 5) * 0.15, 0.55))
            ang = math.atan2(y - (y0 + y1) / 2, x - (x0 + x1) / 2)
            x += math.cos(ang) * 1400 * ks
            y += math.sin(ang) * 1400 * ks - 300 * ks
            rot += 540 * ks * (1 if i % 2 else -1)
        if k > 0:
            P.diamond(c, x, y, s * k, rot)


# ---------------------------------------------------------------- scenes
def sc_cut(c, t):
    """CH.01: film, scissors, tape, timelines, keyframes."""
    up = slide(t, T["tl"] - 0.05, 0.4, 0, 1)                  # make room for the timeline
    # headline block
    if t < T["sc"] + 0.4:
        hk = 1 - e_io(prog(on_twos(t), T["sc"], 0.35))
        c.save()
        c.translate(0, -420 * (1 - hk))
        if t >= T["hund"] - 0.15:
            k = pop(t, T["hund"] - 0.15, 0.25)
            c.save()
            c.translate(540, 300)
            c.rotate(-1.5)
            c.scale(k, k)
            K.tag(c, "A SHORT HISTORY OF EDITING", 0, 0, 0, 36, seed=12, anchor="c")
            c.restore()
        headline(c, "100+ YEARS", 540, 470, 150, t, T["hund"], hl=T["hund"] + 0.12, seed=1)
        headline(c, "OF EDITING", 540, 600, 96, t, T["edit"], seed=2)
        note(c, "= one thing.", 700, 720, 84, t, T["one"], rot=-6)
        c.restore()
    # cover: the title card is on the desk from frame 0, then flicked away as the story starts
    if t < T["hund"]:
        ko = e_io(prog(on_twos(t), T["hund"] - 0.32, 0.3))
        c.save()
        c.translate(-60 * ko, -1100 * ko)
        c.rotate(-8 * ko)
        K.ransom(c, "VIBE", 540, 430, 150, t, -1, 0.06, seed=3)
        K.ransom(c, "EDITING", 540, 625, 125, t, -1, 0.05, seed=4)
        c.save()
        c.translate(540, 770)
        c.rotate(2)
        K.tag(c, "EXPLAINED", 0, 0, 0, 44, seed=13, anchor="c")
        c.restore()
        c.restore()
    # era tags
    if t >= T["hund"] + 0.3:
        K.tag(c, "1895 · FILM + SCISSORS", 86 - 600 * up, 890, -3, 28, seed=3)
    if t >= T["tl"]:
        K.tag(c, "1990s · TIMELINES", slide(t, T["tl"], 0.3, -500, 86), 1015, 2, 28, seed=4)
    if t >= T["kf"]:
        K.tag(c, "2010s · KEYFRAMES", slide(t, T["kf"], 0.3, 1200, 560), 1478, -2, 28, seed=5)
    # timeline slides up from below
    if t >= T["tl"] - 0.1:
        ty = slide(t, T["tl"] - 0.05, 0.4, 2300, 1260)
        P.timeline(c, 540, ty, 900, 380, seed=2, playhead=0.2 + 0.15 * on_twos(t))
    # film strip
    fx = slide(t, 0.0, 0.7, 260, 540)
    fy = lerp(1060, 780, up)
    fs = lerp(1.0, 0.82, up)
    jx, jy, jr = jit(11, t, 1.5, 0.3)
    if t < T["cut"]:
        C["film"].draw(c, fx + jx, fy + jy, -6 + jr, fs)
    else:
        sep = e_out(prog(on_twos(t), T["cut"] + 0.03, 0.3)) * (1 - e_io(prog(on_twos(t), T["sc"] + 0.05, 0.35)))
        for cut, s in ((C["film_l"], -1), (C["film_r"], 1)):
            cut.draw(c, fx + jx + s * 70 * sep, fy + jy + s * -26 * sep + 40 * sep, -6 + jr + s * 7 * sep, fs)
    # tape over the splice
    if t >= T["tape"]:
        k = pop(t, T["tape"], 0.2, 2)
        c.save()
        c.translate(fx, fy)
        c.scale(fs * k, fs * k)
        K.tape(c, 0, 0, 92, 300, -8, 7)
        c.restore()
    # scissors fly in, snip, fly out
    if T["one"] - 0.4 <= t < T["cut"] + 0.9:
        ang = 24 * (1 - e_out(prog(t, T["cut"] - 0.06, 0.07)))
        sx = slide(t, T["one"] - 0.4, 0.45, 1350, 560) + 900 * e_io(prog(on_twos(t), T["cut"] + 0.4, 0.45))
        sy = slide(t, T["one"] - 0.4, 0.45, 300, 860) + 300 * e_io(prog(on_twos(t), T["cut"] + 0.4, 0.45))
        rot = 84
        C["blade_b"].draw(c, sx, sy, rot + ang * 0.5, 1.0, pivot=(P.SC_PX, P.SC_PY))
        C["blade_a"].draw(c, sx, sy, rot - ang * 0.5, 1.0, pivot=(P.SC_PX, P.SC_PY))
    # the stamp
    if T["cut"] <= t < T["sc"] + 0.3:
        a = 1 - prog(t, T["sc"], 0.3)
        K.stamp(c, "CUT.", 560, 1060, 190, -10, prog(t, STAMPS[0], 0.12) * a)
    # keyframes everywhere
    keyframes(c, t, T["kf"], 150, (90, 330, 990, 1460), seed=21, dur=0.95)
    if t >= T["kf"] + 0.7:
        note(c, "× 1,000s", 800, 540, 96, t, T["kf"] + 0.7, rot=-8)


def sc_grind(c, t):
    """CH.02: a spinning clock, a clicking cursor, tally marks."""
    t0 = CHANGES[0]
    headline(c, "HOURS", 540, 430, 180, t, T["hours"], hl=T["hours"] + 0.1, seed=31)
    jx, jy, jr = jit(32, t, 1.5, 0.4)
    C["clock"].draw(c, 540 + jx, 900 + jy, -4 + jr, 1.15)
    P.clock_hands(c, 540 + jx, 900 + jy, on_twos(t) * 1.0 + 0.2, 1.15)
    # tally marks
    n = int(clamp((t - T["hours"]) / 2.2) * 22)
    for i in range(n):
        g, j = divmod(i, 5)
        x, y = 92 + g * 92, 1300
        if j < 4:
            K.marker(c, [(x + j * 16, y), (x + j * 16 + 3, y + 90)], 1, RED, 7)
        else:
            K.marker(c, [(x - 12, y + 70), (x + 70, y + 18)], 1, RED, 7)
    # cursor clicking
    if t >= T["click"] - 0.2:
        ph = (t - T["click"]) * 4
        down = (ph % 1) < 0.3 and t >= T["click"]
        P.cursor(c, slide(t, T["click"] - 0.2, 0.3, 1200, 830), 1190, 1.0, -8, down)
        if t >= T["click"]:
            for k in range(3):
                pk = ((ph - k * 0.33) % 1)
                K.marker(c, K.ring_pts(830, 1190, 30 + 70 * pk, 30 + 70 * pk, k, 1.0, 30), 1, RED, 5, a=1 - pk)
    # = one minute of video
    if t >= T["minute"] - 0.1:
        k = pop(t, T["minute"] - 0.1, 0.25)
        C["clip"].draw(c, 790, 1400, 5, 0.52 * k)
        K.arrow(c, 330, 1450, 590, 1420, prog(t, T["minute"] + 0.1, 0.4), bend=-0.25)
        note(c, "= 1 min", 220, 1500, 78, t, T["minute"] + 0.15, rot=-4)


def sc_vibe(c, t):
    """CH.03: the clip you never drag, then the vibe typed on paper."""
    out_ = e_io(prog(on_twos(t), T["vibe0"] - 0.1, 0.4))
    if out_ < 1:
        c.save()
        c.translate(-900 * out_, -500 * out_)
        headline(c, "WHAT IF", 540, 430, 150, t, T["what"], hl=T["what"] + 0.1, seed=41)
        jx, jy, jr = jit(42, t, 1.5, 0.3)
        drag = e_out(prog(on_twos(t), T["drag"], 0.5)) * 60
        C["clip"].draw(c, 540 + jx + drag, 860 + jy, 3 + jr, 1.0)
        cx_ = slide(t, T["what"], 0.5, 1150, 800) + drag
        P.cursor(c, cx_, 960, 1.0, -8, t > T["drag"])
        K.scribble_x(c, 600 + drag, 900, 260, prog(t, T["never"] + 0.05, 0.45))
        c.restore()
    if t >= T["vibe0"] - 0.1:
        headline(c, "DESCRIBE", 540, 400, 140, t, T["vibe0"], seed=43)
        headline(c, "THE VIBE.", 540, 545, 140, t, T["vibe"], hl=T["vibe"] + 0.08, seed=44)
        sy = slide(t, T["vibe0"] - 0.05, 0.45, 2300, 1000)
        jx, jy, jr = jit(45, t, 1.2, 0.3)
        c.save()
        c.translate(540 + jx, sy + jy)
        c.rotate(-2 + jr)
        K.paper_path(c, K.torn_path(-420, -230, 420, 230, 46, amp=6, sides="t"), WHITE, 1, (6, 11, 10, 0.3))
        f = font("mono", 50)
        n_all = sum(len(s) for s in TYPED)
        n = int(clamp((t - TYPE_T0) / (TYPE_T1 - TYPE_T0)) * n_all)
        y = -60
        for li, line in enumerate(TYPED):
            shown = line[:max(0, n)]
            n -= len(line)
            if li == 1 and t >= T["vibe"]:
                w = f.measureText(line)
                K.highlighter(c, -370 + f.measureText("  "), y - 46, -370 + w + 6, y + 12, e_out(prog(t, T["vibe"] + 0.05, 0.4)), 47)
            c.drawString(shown, -370, y, f, fill(INK))
            if 0 <= n + len(line) <= len(line) and int(t * 3) % 2 == 0:
                c.drawRect(skia.Rect.MakeXYWH(-370 + f.measureText(shown) + 4, y - 40, 26, 48), fill(INK))
            y += 80
        c.restore()
        if t >= T["vibe"]:
            for i, (x, yy, r) in enumerate([(150, 760, 46), (930, 820, 38), (880, 1280, 54), (190, 1300, 34)]):
                k = pop(t, T["vibe"] + 0.06 * i, 0.22, 2.6)
                if k > 0:
                    P.sparkle(c, x, yy, r * k, on_twos(t) * 0.8 + i)


def sc_program(c, t):
    """CH.04: the ransom-note title, the director, four kinds of video, one prompt."""
    lift = e_io(prog(on_twos(t), T["list0"] - 0.15, 0.4))
    c.save()
    c.translate(540, lerp(0, -40, lift))
    c.scale(lerp(1, 0.66, lift), lerp(1, 0.66, lift))
    c.translate(-540, 0)
    K.ransom(c, "VIBE", 540, 560, 140, t, T["prog0"], 0.06, seed=3)
    K.ransom(c, "EDITING", 540, 750, 120, t, T["prog0"] + 0.3, 0.05, seed=4)
    if t >= T["prog"]:
        k = pop(t, T["prog"], 0.25)
        c.save()
        c.translate(540, 905)
        c.scale(k, k)
        K.tag(c, "A PROGRAM BY IDEABRO STUDIO", 0, 0, 1.5, 32, seed=9, anchor="c")
        c.restore()
    c.restore()
    # the director
    gone = e_io(prog(on_twos(t), T["list0"] - 0.1, 0.4))
    if t >= T["direct"] - 0.1 and gone < 1:
        k = pop(t, T["direct"] - 0.1, 0.28)
        x = 330 - 900 * gone
        clap = 26 * (1 - e_out(prog(t, T["direct"] + 0.35, 0.06)))
        c.save()
        c.translate(x, 1230)
        c.rotate(-6)
        c.scale(0.95 * k, 0.95 * k)
        C["slate"].draw(c, 0, 0)
        C["clap"].draw(c, -P.CL_W / 2, -P.CL_H / 2 - 4, -clap, 1.0, pivot=(0, 70))
        c.restore()
        note(c, "you = the director", 760 - 900 * gone, 1080, 70, t, T["editor"] - 0.3, rot=-7)
        if t >= T["editor"]:
            K.arrow(c, 700 - 900 * gone, 1110, 560 - 900 * gone, 1190, prog(t, T["editor"], 0.35), bend=0.3)
    # four cards
    cards = [("captions", T["cap"], 300, 840, -5), ("motion", T["mot"], 780, 830, 4),
             ("animation", T["anim"], 300, 1290, 3), ("ads", T["ads"], 780, 1300, -4)]
    for i, (kind, t0, x, y, r) in enumerate(cards):
        k = pop(t, t0 - 0.05, 0.25, 2.2)
        if k > 0:
            jx, jy, jr = jit(60 + i, t, 1.2, 0.3)
            P.polaroid(c, kind, x + jx, y + jy, r + jr, 0.92 * k, t, 60 + i, kind)
    if t >= T["all"] - 0.05:
        for i, (_, _, x, y, _) in enumerate(cards):
            K.arrow(c, 540, 1065, lerp(540, x, 0.62), lerp(1065, y, 0.62), prog(t, T["all"] + 0.08 * i, 0.3),
                    w=7, bend=0.15 * (1 if i % 2 else -1))
        k = pop(t, T["all"] - 0.05, 0.25)
        c.save()
        c.translate(540, 1065)
        c.rotate(-3)
        c.scale(k, k)
        f = font("monob", 40)
        s = "> one prompt"
        w = f.measureText(s) + 50
        K.paper_path(c, K.torn_path(-w / 2, -40, w / 2, 40, 71, amp=4), WHITE, 1, (4, 8, 6, 0.3))
        if t >= T["prompt"]:
            K.highlighter(c, -w / 2 + 20, -30, w / 2 - 20, 22, e_out(prog(t, T["prompt"], 0.3)), 72)
        c.drawString(s, -w / 2 + 25, 14, f, fill(INK))
        c.restore()


def sc_shift(c, t):
    """CH.05: the timeline gets stamped and torn, keyframes blown away; just you and the vibe."""
    if t < T["just"] + 0.2:
        tear = e_io(prog(on_twos(t), T["ntl"] + 0.4, 0.6))
        cx, cy = 540, 760
        if tear <= 0:
            P.timeline(c, cx, cy, 900, 380, seed=2, playhead=0.5)
        else:
            for s in (-1, 1):
                p = skia.Path()
                xs = [cx + (hrand(5, i) - 0.5) * 50 for i in range(14)]
                ys = [cy - 230 + i * 460 / 13 for i in range(14)]
                edge = list(zip(xs, ys))
                far = cx + s * 700
                p.moveTo(far, cy - 260)
                for q in edge:
                    p.lineTo(*q)
                p.lineTo(far, cy + 260)
                p.close()
                c.save()
                c.translate(s * 700 * tear, 260 * tear)
                c.rotate(s * 18 * tear)
                P.timeline(c, cx, cy, 900, 380, seed=2, playhead=0.5, clip_path=p)
                c.restore()
        K.stamp(c, "NO", 540, 760, 200, -10, prog(t, STAMPS[1], 0.1) * (1 - prog(t, T["ntl"] + 0.4, 0.2)))
        keyframes(c, t, CHANGES[3] - 0.6, 40, (220, 1080, 860, 1330), seed=51, dur=0.01, scatter=T["nkf"] + 0.35)
        K.stamp(c, "NO", 540, 1200, 160, 8, prog(t, STAMPS[2], 0.1) * (1 - prog(t, T["nkf"] + 0.35, 0.2)))
    if t >= T["just"]:
        headline(c, "JUST", 540, 700, 190, t, T["just"], seed=81)
        headline(c, "YOU", 540, 900, 230, t, T["you"], hl=T["you"] + 0.06, seed=82)
        if t >= T["vb"]:
            note(c, "& the vibe.", 560, 1110, 150, t, T["vb"], rot=-5)
            K.marker(c, [(300, 1150), (500, 1162), (820, 1140)], prog(t, T["vb"] + 0.35, 0.3), RED, 10)
            for i, (x, y, r) in enumerate([(170, 560, 50), (920, 600, 40), (930, 1250, 56), (140, 1210, 36)]):
                k = pop(t, T["vb"] + 0.05 * i, 0.22, 2.6)
                if k > 0:
                    P.sparkle(c, x, y, r * k, on_twos(t) * 0.8 + i)


def sc_cta(c, t):
    K.ransom(c, "VIBE", 540, 640, 175, t, T["cta"] - 0.1, 0.06, seed=3)
    K.ransom(c, "EDITING", 540, 870, 140, t, T["cta"] + 0.15, 0.05, seed=4)
    if t >= T["by"] - 0.1:
        k = pop(t, T["by"] - 0.1, 0.25)
        c.save()
        c.translate(540, 1035)
        c.scale(k, k)
        K.tag(c, "BY IDEABRO STUDIO", 0, 0, -1.5, 36, seed=91, anchor="c")
        c.restore()
    if t >= T["link"] - 0.05:
        k = pop(t, T["link"] - 0.05, 0.25)
        c.save()
        c.translate(540, 1215)
        c.rotate(2)
        c.scale(k, k)
        f = font("black", 70)
        s = "LINK IN BIO  →"
        w = f.measureText(s) + 80
        K.paper_path(c, K.torn_path(-w / 2, -62, w / 2, 62, 92, amp=5), YEL, 1, (5, 9, 7, 0.3))
        c.drawString(s, -w / 2 + 40, 25, f, fill(INK))
        K.tape(c, -w / 2 + 10, -50, 120, 40, -28, 93)
        K.tape(c, w / 2 - 10, 50, 120, 40, -28, 94)
        c.restore()
    K.stamp(c, "ENROLL NOW", 640, 1400, 92, -7, prog(t, STAMPS[3], 0.12))


SCENES = [sc_cut, sc_grind, sc_vibe, sc_program, sc_shift, sc_cta]


# ---------------------------------------------------------------- overlays
def wipe(c, t):
    for i, t_mid in enumerate(CHANGES):
        k = (t - (t_mid - WIPE_D / 2)) / WIPE_D
        if not (0 <= k <= 1):
            continue
        k = on_twos(k * WIPE_D) / WIPE_D
        top = lerp(H + 60, -2340, k)
        p = K.torn_path(-60, top, W + 60, top + 2300, 100 + i, amp=22, step=26, sides="tb")
        K.paper_path(c, p, WIPE_COL[i], 1, (0, -14, 14, 0.35))
        if WIPE_COL[i] == NEWS:                     # newsprint columns
            for col_ in range(3):
                for r in range(46):
                    y = top + 120 + r * 46
                    x0 = 70 + col_ * 330
                    ln = 260 - (hrand(i, col_, r) * 90 if r % 9 == 8 else 0)
                    c.drawRect(skia.Rect.MakeXYWH(x0, y, ln, 12), fill(INK, 0.16))


def chapter(c, t):
    i = scene_of(t)
    K.tape(c, 120, 118, 110, 38, -12, 200 + i)
    K.tag(c, CHAPTERS[i], 70, 150, -2, 30, seed=210 + i)
    text(c, "VIBE EDITING, EXPLAINED", W - 70, 160, "monob", 24, INK, 0.55, anchor="r")


GROUPS = chunk_words(S.words(), max_words=3, max_chars=18)


def captions(c, t):
    if t >= CHANGES[-1]:
        return
    for gi, g in enumerate(GROUPS):
        g0, g1 = g[0][1], g[-1][2]
        nxt = GROUPS[gi + 1][0][1] if gi + 1 < len(GROUPS) else 1e9
        if not (g0 - 0.03 <= t < min(g1 + 0.3, nxt)):
            continue
        size = 62
        ws = [w for w, *_ in g]
        f = font("black", size)
        sp = f.measureText(" ")
        widths = [f.measureText(w) for w in ws]
        tot = sum(widths) + sp * (len(ws) - 1)
        y = 1590
        c.save()
        c.translate(W / 2, y)
        c.rotate((hrand(gi) - 0.5) * 3)
        K.paper_path(c, K.torn_path(-tot / 2 - 34, -66, tot / 2 + 34, 34, 300 + gi, amp=4, sides="lr"), WHITE, 1,
                     (4, 7, 6, 0.25))
        x = -tot / 2
        for wi, ((w, s, e, *_), wd) in enumerate(zip(g, widths)):
            nxt_s = g[wi + 1][1] if wi + 1 < len(g) else 1e9
            if s - 0.03 <= t < nxt_s - 0.03:
                K.highlighter(c, x - 6, -54, x + wd + 6, 14, 1, 400 + gi * 7 + wi)
            c.drawString(w, x, 0, f, fill(INK))
            x += wd + sp
        c.restore()


# ---------------------------------------------------------------- frame
def shake(t):
    s = 0.0
    for st in STAMPS:
        if t >= st:
            s += math.exp(-(t - st) * 14)
    return s


def draw(c, t, f):
    warm()
    i = scene_of(t)
    sk = shake(t)
    drift = t - ([0] + CHANGES)[i]
    cam_x, cam_y = drift * 6, drift * 4
    K.desk(c, cam_x, cam_y)
    c.save()
    z = 1.0 + 0.012 * drift
    c.translate(W / 2 + math.sin(t * 50) * 9 * sk, H / 2 + math.cos(t * 43) * 9 * sk)
    c.scale(z, z)
    c.rotate(math.sin(drift * 0.4) * 0.35)
    c.translate(-W / 2 - cam_x * 0.5, -H / 2 - cam_y * 0.5)
    SCENES[i](c, t)
    c.restore()
    chapter(c, t)
    wipe(c, t)
    captions(c, t)
    return {"f": f}


def post(arr, g, f):
    rng = np.random.default_rng(f // 2)
    grain = rng.standard_normal(arr.shape[:2]).astype(np.float32) * 6.0
    fib = C["fibre"]
    if fib.shape != arr.shape[:2]:                           # half-size previews
        k = fib.shape[0] // arr.shape[0]
        fib = fib[::k, ::k][: arr.shape[0], : arr.shape[1]]
    out = arr.astype(np.float32) * fib[..., None] + grain[..., None]
    out[..., 2] *= 0.985                                     # a touch warm, like old paper under a lamp
    return np.clip(out, 0, 255).astype(np.uint8)


film = Film(draw, DUR, FPS, post=post, out_dir=HERE / "out", warm=warm, sheet_n=24)


# ---------------------------------------------------------------- sound
def sfx_bank():
    from paper_sfx import SFX
    return SFX


def sound():
    import music as M
    from sound import Mix
    X = sfx_bank()
    bed = M.lofi_trap(DUR, 88, "Eb", {"beat": T["vibe0"]}, seed=3).master()
    m = Mix(DUR)
    m.voice(S.placements())
    m.music(bed, gain_db=-3, duck_db=-9, fade_out=1.4)
    cue = lambda name, t, g=-8: m.sfx(X[name](), t, g)  # noqa: E731
    cue("rustle", 0.12, -10)
    cue("slap", T["hund"] + 0.3, -12)
    for k in ("hund", "edit"):
        cue("pop", T[k], -14)
    cue("whoosh", T["one"] - 0.4, -10)
    cue("snip", T["cut"] - 0.06, -4)
    cue("stamp", STAMPS[0], -6)
    cue("tear", T["tape"] - 0.05, -10)
    cue("rustle", T["tl"] - 0.05, -10)
    for i in range(24):
        cue("tick", T["kf"] + i * 0.08, -16)
    for t_mid in CHANGES:
        cue("tear", t_mid - 0.25, -8)
    for i in range(int(2.6 / 0.25)):
        cue("tick", T["hours"] + i * 0.25, -14)
    for i in range(int((CHANGES[1] - T["click"]) * 4)):
        cue("clack", T["click"] + i * 0.25, -16)
    cue("pop", T["minute"] - 0.1, -12)
    cue("rustle", T["never"] + 0.05, -10)
    n_all = sum(len(s) for s in TYPED)
    for i in range(n_all):
        if (TYPED[0] + TYPED[1])[i] != " ":
            cue("type", TYPE_T0 + (TYPE_T1 - TYPE_T0) * i / n_all, -12)
    cue("sparkle", T["vibe"], -10)
    for i in range(11):
        cue("slap", T["prog0"] + (i * 0.06 if i < 4 else 0.3 + (i - 4) * 0.05), -16)
    cue("clack", T["direct"] + 0.35, -6)
    for k in ("cap", "mot", "anim", "ads"):
        cue("slap", T[k] - 0.05, -10)
    cue("pop", T["all"] - 0.05, -10)
    cue("stamp", STAMPS[1], -6)
    cue("tear", T["ntl"] + 0.4, -6)
    cue("stamp", STAMPS[2], -6)
    cue("whoosh", T["nkf"] + 0.35, -8)
    cue("sparkle", T["vb"], -10)
    for i in range(11):
        cue("slap", T["cta"] - 0.1 + (i * 0.06 if i < 4 else 0.25 + (i - 4) * 0.05), -16)
    cue("slap", T["link"] - 0.05, -10)
    cue("stamp", STAMPS[3], -5)
    m.finish(HERE / "out" / "picture.mp4", HERE / "out" / "vibe_editing_vox_papercut.mp4", HERE / "work")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    print(f"duration {DUR:.2f}s")
    if cmd == "stills":
        film.stills([float(x) for x in sys.argv[2:]])
    elif cmd == "sheet":
        film.sheet()
    elif cmd == "render":
        film.render()
    elif cmd == "sound":
        sound()
    elif cmd == "cues":
        for k, v in T.items():
            print(f"{k:8s} {v:6.2f}")
        print("changes", [round(x, 2) for x in CHANGES])
    elif cmd == "all":
        film.render()
        sound()
