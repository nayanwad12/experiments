"""B2-05 Faceless channel episode (vibe-ai-footage skill's faceless recipe, but every visual is code, no AI clips):
"In 1996, one number destroyed a rocket in under forty seconds." Ariane 5 Flight 501.

Facts (ESA/CNES inquiry board report, July 1996): maiden flight 4 June 1996 from Kourou; ~37 s after lift-off both
inertial reference systems failed (the backup first) with an operand error: a 64-bit floating-point value (horizontal
bias) converted to a 16-bit signed integer (max 32,767) overflowed. The code was reused from Ariane 4. The rocket
veered, broke up and self-destructed ~39 s after lift-off. Payload: the four Cluster satellites.

    python3 build.py prep | web 2 6 | layer | sheet | stills 4 | render | sound | all
"""
import sys
from pathlib import Path

import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(HERE))
from b2 import Reel  # noqa: E402
from kit import (W, H, INK, LIME, WHITE, Captions, Film, Layer, clamp, e_back, e_out, endcard, fill, lerp,  # noqa: E402
                 measure, prog, rrect, stroke, text)
from script import LINES, VOICE  # noqa: E402
from voice import Script, narrate  # noqa: E402

FPS = 30
vo = narrate(LINES, HERE / "work", VOICE)
S = Script(vo, [("hook", "@", 0.2), ("lift", 0.2), ("inside", 0.15), ("squeeze", 0.06), ("max", 0.16), ("over", 0.12),
                ("overflow", 0.22), ("crash", 0.2), ("veer", 0.17), ("lost", 0.45), ("tail", 0.35), ("cta", 0.17)])
END_T = S.end("cta") + 0.45
DUR = END_T + 2.9
R = Reel(__file__, DUR, FPS)
LIFTOFF = S.find("lift", "lifts")
OVERFLOW = S.t("overflow")
EXPLODE = S.find("veer", "tears")
RED = "#FF3B3B"


def mission_clock(t):
    """mission elapsed time shown on screen: real flight time compressed into the edit (T+0 -> T+36.7 at the
    overflow, T+39 at break-up)."""
    if t < LIFTOFF:
        return None
    if t < OVERFLOW:
        return 36.7 * (t - LIFTOFF) / (OVERFLOW - LIFTOFF)
    if t < EXPLODE:
        return 36.7 + 2.3 * (t - OVERFLOW) / (EXPLODE - OVERFLOW)
    return 39.0


def song():
    from music import cinematic
    return cinematic(DUR, 90, "D", {"hits": [LIFTOFF, OVERFLOW, EXPLODE], "calm": [(S.t("lost") + 0.3, S.t("tail"))]},
                     seed=4)


def prep():
    R.write_timeline(dict(
        DUR=DUR, END=END_T, LIFT_LINE=S.t("lift"), LIFTOFF=LIFTOFF, INSIDE=S.t("inside"), SQUEEZE=S.t("squeeze"),
        BITS64=S.find("squeeze", "64-bit"), BITS16=S.find("squeeze", "16"), MAX=S.t("max"),
        MAXNUM=S.find("max", "32,767"), OVER=S.t("over"), OVERFLOW=OVERFLOW, CRASH=S.t("crash"),
        BACKUP=S.find("crash", "backup"), VEER=S.t("veer"), EXPLODE=EXPLODE, LOST=S.t("lost"), TAIL=S.t("tail"),
        CTA=S.t("cta")))
    print("timeline ok", f"liftoff {LIFTOFF:.2f} overflow {OVERFLOW:.2f} explode {EXPLODE:.2f}")


BG = Layer(HERE / "work" / "layer.mp4", fps=FPS)
PATCH = (11.6, 24.7)                       # re-staged bits + gauge shots: work/patch.mp4
PG = Layer(HERE / "work" / "patch.mp4", fps=FPS)


def gauge_value(t):
    """the same 'horizontal bias' reading the 3D gauge shows (scene.js), drawn crisp here."""
    from kit import e_io
    T = dict(MAXNUM=S.find("max", "32,767"), OVER=S.t("over"))
    if t < T["OVER"]:
        vk = 0.85 * e_out(prog(t, T["MAXNUM"] - 0.8, 1.4))
    else:
        vk = lerp(0.85, 1.25, e_io(prog(t, T["OVER"], OVERFLOW - T["OVER"])))
    return round(vk / 0.85 * 32767 * (1.0 + (vk - 0.85) * 3.2 if vk > 0.85 else 1))
CODE = ["-- inertial reference system (SRI)", "-- reused from Ariane 4", "",
        "procedure Align is", "   H_Bias : Float_64;", "begin", "   ...",
        "   E_BH := Integer_16 (H_Bias);", "   --  64 bits  ->  16 bits", "end Align;"]


def code_card(c, t, t0, t1):
    if not (t0 <= t < t1):
        return
    a = e_out(prog(t, t0, 0.3)) * (1 - prog(t, t1 - 0.25, 0.25))
    x0, y0, w, h = 70, 1180, W - 140, 460
    c.drawRRect(rrect(x0, y0, w, h, 24), fill("#03110a", 0.86 * a))
    c.drawRRect(rrect(x0, y0, w, h, 24), stroke("#2BFF88", 2, 0.4 * a))
    n = int((t - t0) * 7) + 1
    for i, ln in enumerate(CODE[:n]):
        hl = "Integer_16" in ln
        if hl and t > S.find("squeeze", "16") - 0.1:
            c.drawRect(skia.Rect.MakeXYWH(x0 + 24, y0 + 36 + i * 41, w - 48, 40), fill(RED, 0.25 * a))
        text(c, ln, x0 + 40, y0 + 66 + i * 41, "monob" if hl else "mono", 30, "#2BFF88" if not hl else "#FFFFFF", a,
             anchor="l")


def draw(c, t, f):
    p0 = int(round(PATCH[0] * FPS))
    if PATCH[0] <= t < PATCH[1] and (HERE / "work" / "patch.mp4").exists():
        c.drawImage(PG.image(f - p0), 0, 0)
    else:
        c.drawImage(BG.image(f), 0, 0)
    if t < S.t("lift") + 0.3:                                    # dark band behind the title
        c.drawRect(skia.Rect.MakeWH(W, 760), skia.Paint(Shader=skia.GradientShader.MakeLinear(
            [skia.Point(0, 0), skia.Point(0, 760)], [skia.Color(0, 0, 0, 170), skia.Color(0, 0, 0, 0)])))
    if S.t("max") - 0.1 <= t < OVERFLOW:                         # the reading, big and crisp
        a = e_out(prog(t, S.t("max") - 0.1, 0.3))
        v = gauge_value(t)
        c.drawRRect(rrect(W / 2 - 300, 1330, 600, 250, 30), fill("#05070b", 0.82 * a))
        c.drawRRect(rrect(W / 2 - 300, 1330, 600, 250, 30), stroke(RED if v > 32767 else "#4d8dff", 3, 0.8 * a))
        text(c, "HORIZONTAL BIAS READING", W / 2, 1385, "monob", 28, "#B9B2A0", a)
        text(c, f"{v:,}", W / 2, 1540, "anton", 150, RED if v > 32767 else WHITE, a)
    # documentary title card on the hook
    if t < S.t("lift"):
        k = e_out(prog(t, S.find("hook", "one") - 0.05, 0.4))
        text(c, "FLIGHT 501", W / 2, 360, "monob", 46, "#E8D9B8", k * 0.9, tracking=0.2)
        text(c, "ONE NUMBER.", W / 2, 520, "anton", 150, WHITE, k, shadow=20)
        k2 = e_out(prog(t, S.find("hook", "forty") - 0.1, 0.4))
        text(c, "< 40 SECONDS", W / 2, 640, "anton", 92, RED, k2, shadow=20)
    # mission clock
    mc = mission_clock(t)
    if mc is not None and t < S.t("lost"):
        a = e_out(prog(t, LIFTOFF, 0.3))
        col = RED if t >= OVERFLOW else WHITE
        text(c, f"T+{mc:05.1f}s", 60, 250, "monob", 50, col, a, anchor="l")
        text(c, "ARIANE 5 · 4 JUNE 1996 · KOUROU", 60, 300, "mono", 26, "#B9B2A0", a * 0.9, anchor="l")
    code_card(c, t, S.t("inside") + 0.4, S.t("max") - 0.1)
    # 64 -> 16 labels and the 32,767 gauge numbers are drawn in 3D; the OVERFLOW stamp is here
    if OVERFLOW <= t < S.t("crash") + 0.3:
        k = e_back(prog(t, OVERFLOW, 0.25), 2.5)
        c.save()
        c.translate(W / 2, 1000)
        c.rotate(-6)
        c.scale(lerp(1.6, 1, clamp(k)), lerp(1.6, 1, clamp(k)))
        c.drawRRect(rrect(-330, -110, 660, 160, 18), stroke(RED, 10, clamp(k)))
        text(c, "OVERFLOW", 0, 20, "anton", 130, RED, clamp(k))
        c.restore()
    # aftermath facts
    if S.t("lost") <= t < S.t("tail"):
        rows = [(S.find("lost", "Four"), "4", "satellites lost"), (S.find("lost", "Hundreds"), "$100Ms", "in hardware"),
                (S.find("lost", "conversion"), "1", "number conversion")]
        for i, (ti, big, small) in enumerate(rows):
            k = e_out(prog(t, ti - 0.05, 0.35))
            y = 640 + i * 230
            text(c, big, 90, y, "anton", 150, WHITE if i < 2 else RED, k, anchor="l", shadow=16)
            text(c, small, 90, y + 60, "medium", 44, "#E8D9B8", k, anchor="l", shadow=10)
    if t >= END_T:
        endcard(c, t, END_T)
    CAP.draw(c, t)


CAP = Captions(S.words(), y=1690, size=78, hi="#FFD34D").mute(END_T, DUR)
film = Film(draw, DUR, FPS, out_dir=HERE / "out")


def sound():
    import json
    import music as M
    from sound import Mix
    T = json.loads((HERE / "work" / "timeline.json").read_text())
    bed = song().master()
    m = Mix(DUR)
    m.voice(S.placements())
    m.music(bed, gain_db=-5, duck_db=-9, fade_out=1.5)
    sr = M.SR
    # rocket roar: filtered noise swelling from ignition, fading with distance
    n = int((T["EXPLODE"] - T["LIFTOFF"] + 0.5) * sr)
    tt = np.arange(n) / sr
    roar = M.filt(M.noise(n), "lp", 500) * 1.3 + M.filt(M.noise(n), "bp", (600, 2400)) * 0.35
    roar *= np.clip(tt / 0.6, 0, 1) * (1 - 0.6 * np.clip((tt - 3.0) / 4, 0, 1))
    roar *= np.where(tt > T["INSIDE"] - T["LIFTOFF"], 0.25, 1.0) * np.where(tt > T["VEER"] - T["LIFTOFF"], 3.0, 1.0)
    m.sfx(M.sat(roar, 1.5).astype(np.float32), T["LIFTOFF"] - 0.2, -10)
    for k in range(10):
        m.sfx("tick", T["INSIDE"] + 0.6 + k * 0.17, -18)
    for k in range(16):
        m.sfx("click", T["BITS16"] + k * 0.05, -16)
    m.sfx("riser", T["OVER"], -10, dur=T["OVERFLOW"] - T["OVER"])
    m.sfx("glitch", T["OVERFLOW"], -4)
    m.sfx("glitch", T["BACKUP"], -6)
    alarm = (np.sign(np.sin(2 * np.pi * 880 * np.arange(int(0.5 * sr)) / sr)) * 0.2).astype(np.float32)
    for k in range(3):
        m.sfx(alarm, T["CRASH"] + 0.2 + k * 0.7, -16)
    m.sfx(M.impact(4.0, 24), T["EXPLODE"], 0)
    m.sfx(M.crash(3.0), T["EXPLODE"] + 0.05, -6)
    m.sfx("whoosh", END_T - 0.25, -10)
    m.sfx("ding", END_T + 0.1, -12)
    m.finish(HERE / "out" / "picture.mp4", HERE / "out" / "B2_05_faceless_ariane.mp4", HERE / "work")


if __name__ == "__main__":
    R.cli(film, sound, prep)
