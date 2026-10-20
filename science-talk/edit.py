"""Stress -> psoriasis explainer: the full edit on top of work/base.mp4 (the 1.2x cut) + work/alpha.npy.

    python3 edit.py cues                  # print the cue sheet (output times)
    python3 edit.py stills 5.2 16 30      # -> out/stills/*.png  (half res)
    python3 edit.py sheet                 # -> out/sheet.png
    python3 edit.py render [--draft]      # -> work/picture.mp4

Two looks: CAM (the real footage, jump-cut punch-ins, giant words + science photos BEHIND the speaker)
and STUDIO (dark science backdrop, speaker cut out at the bottom, flowcharts above). Every graphic is
cued off a spoken word; SFX for sound.py are collected from the same cues.
"""
import json
import math
import re
import sys
from pathlib import Path

import cv2
import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gfx import (AMBER, CYAN, GREEN, INK, NAVY, RED, SAMP, VIOLET, WHITE, H, W, Captions, arrow_line,  # noqa: E402
                 behind, box_breath, chain, clamp, comment_box, counter, draw_image_cover, e_in, e_io, e_out, fill,
                 font, icon, img, lerp, lin_grad, loop_ring, measure, molecule, node, photo_card, pill, pop_k,
                 rad_grad, rank_bars, rrect, spring, stamp, stroke, studio_bg, tcell, text, title)
from kit import Film, Layer  # noqa: E402

E = json.loads((HERE / "work" / "edl.json").read_text())
FPS = E["fps"]
WORDS = E["words"]
NB = sum(c[3] for c in E["cuts"])
TAIL = 1.3
TOTAL = E["total"] + TAIL
CUT_T = [c[2] for c in E["cuts"]] + [E["total"]]


# ================================================================== cues
def _norm(s):
    return re.sub(r"[^a-z0-9\-]", "", s.lower())


def cue(key, word, n=1, end=False):
    hits = [w for w in WORDS if w["key"] == key and _norm(w["w"]) == _norm(word)]
    if len(hits) < n:
        raise KeyError(f"{key}:{word}#{n}")
    return hits[n - 1]["e" if end else "s"]


def seg(key):
    ws = [w for w in WORDS if w["key"] == key]
    return ws[0]["s"], ws[-1]["e"]


SFX = []


def sfx(t, kind, gain=-8.0, **kw):
    SFX.append(dict(t=round(t, 3), kind=kind, gain_db=gain, **kw))


# ---- studio sections (start, end)
S_MECH = (seg("mech1")[0] - 0.2, cue("fix1", "todna") + 0.75)
S_RANK = (cue("ex1", "2025") - 0.35, cue("ex3", "thoda") - 0.15)
S_RECAP = (seg("recap")[0] - 0.25, seg("recap")[1] + 0.25)
S_ULTA = (seg("mom3")[0] - 0.2, seg("mom3")[1] + 0.2)
STUDIOS = [S_MECH, S_RANK, S_RECAP, S_ULTA]
TR = 0.35
for a, b in STUDIOS:
    sfx(a - 0.12, "whoosh", -9, dur=0.5)
    sfx(b - 0.12, "swish", -10)

MOM = (seg("mom1")[0] - 0.3, seg("mom3")[0] - 0.2)
BEHIND_CAPS = [(cue("hook4", "aur"), cue("hook7", "science") - 0.08),
               (cue("cta2", "collab") - 0.1, cue("cta3", "mera") - 0.05)]


def studio_k(t):
    k = 0.0
    for a, b in STUDIOS:
        k = max(k, e_io(clamp((t - a) / TR)) * (1 - e_io(clamp((t - b) / TR))))
    return k


# ================================================================== camera (cam look)
def cut_index(t):
    for i in range(len(CUT_T) - 1):
        if t < CUT_T[i + 1]:
            return i
    return len(CUT_T) - 2


ZOOM_SKIP = set()


def cam(t):
    """zoom about the face for the CAM look: alternate 1.0 / 1.12 per cut + a slow push inside each cut."""
    i = cut_index(t)
    a, b = CUT_T[i], CUT_T[i + 1]
    z = 1.0 if i % 2 == 0 else 1.12
    z *= 1 + 0.035 * clamp((t - a) / max(0.5, b - a))
    if t < 0.6:                                # opening: snap in from wide
        z *= lerp(1.18, 1.0, e_out(t / 0.6))
    return z, 540, 1010


# ================================================================== frames + matte
BASE = Layer(HERE / "work" / "base.mp4", W, H, FPS)
_ALPHA = None
_HEAD = None


def alpha_small(fi):
    global _ALPHA
    if _ALPHA is None:
        _ALPHA = np.load(HERE / "work" / "alpha.npy", mmap_mode="r")
    return _ALPHA[min(fi, len(_ALPHA) - 1)]


def head_top_series():
    """top of the head (1080x1920 px) per output frame, smoothed; used to park text behind the head."""
    global _HEAD
    if _HEAD is None:
        p = HERE / "work" / "headtop.npy"
        if p.exists():
            _HEAD = np.load(p)
        else:
            A = np.load(HERE / "work" / "alpha.npy", mmap_mode="r")
            ht = np.zeros(len(A), np.float32)
            for i in range(len(A)):
                col = A[i][:, 150:390] > 140
                rows = np.nonzero(col.sum(1) > 12)[0]
                ht[i] = rows[0] * 2 if len(rows) else 700
            k = np.ones(31) / 31
            _HEAD = np.convolve(np.pad(ht, 15, mode="edge"), k, mode="valid")
            np.save(p, _HEAD)
    return _HEAD


def head_top_at(t):
    hs = head_top_series()
    return float(hs[min(int(t * FPS), len(hs) - 1)])


def behind_y(t0, size):
    """baseline for a giant word so the head covers its lower third (fixed for the whole word)."""
    ht = head_top_at(t0 + 0.3)
    return clamp(ht + size * 0.32, 420, 900)


WARM = skia.ColorFilters.Matrix([
    1.08, 0.04, 0.0, 0, 0.02,
    0.02, 1.00, 0.0, 0, 0.0,
    0.0, 0.0, 0.88, 0, -0.01,
    0, 0, 0, 1, 0])


_ex = np.clip(np.minimum(np.arange(W), W - 1 - np.arange(W)) / 70.0, 0, 1)
EDGE_FEATHER = (_ex[None, :] * np.ones((H, 1))).astype(np.float32)


def person_image(fi, rgba):
    a = cv2.resize(np.asarray(alpha_small(fi)), (W, H), interpolation=cv2.INTER_LINEAR)
    a = np.clip((a.astype(np.int32) - 20) * 255 // 215, 0, 255).astype(np.float32)
    a *= EDGE_FEATHER
    out = rgba.copy()
    out[..., 3] = a.astype(np.uint8)
    return skia.Image.fromarray(out, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType)


# ================================================================== section drawings
def T(key, word, n=1):
    return cue(key, word, n)


# ---- hook
H_EK = T("hook1", "ek")
H_PSO = T("hook2", "psoriasis")
H_STRESS = T("hook3", "stress")
H_SCI = T("hook7", "science")
H_TOD = T("hook9", "tod")
H_END = seg("hook9")[1]
sfx(H_EK - 0.05, "impact", -12)
sfx(H_PSO - 0.05, "swish", -10)
sfx(H_STRESS - 0.02, "impact", -5)
sfx(H_STRESS - 0.02, "bass_drop", -9)
sfx(H_SCI - 0.1, "pop", -9)
sfx(H_TOD, "glitch", -8)

# ---- mechanism
M_STRESS = T("mech1", "stress")
M_BRAIN = T("mech1", "brain")
M_CORT = T("mech2", "cortisol")
M_EMERG = T("mech2", "emergency")
M_IMM = T("mech2", "immune")
M_BIG = T("mech2", "bigaadta")
M_TC = T("mech2", "t-cells")
M_SKIN = T("mech3", "chamdi")
M_ATT = T("mech3", "attack")
M_END = seg("mech4")[1]
for tt in (M_STRESS, M_BRAIN, M_CORT, M_IMM, M_TC, M_SKIN):
    sfx(tt - 0.04, "pop", -12)
sfx(M_BRAIN - 0.1, "whoosh", -12, dur=0.4)
sfx(M_CORT, "sparkle", -10)
sfx(M_EMERG, "impact", -11)
sfx(M_BIG, "glitch", -10)
sfx(M_TC, "riser", -15, dur=1.2)
sfx(M_ATT - 0.05, "impact", -8)

# ---- loop
L0 = seg("loop1")[0] - 0.25
L_NODES = [T("loop1", "stress"), T("loop2", "cortisol"), T("loop4", "immune"), T("loop4", "flare")]
L_AGAIN = T("loop4", "stress")
L_B1, L_B2, L_B3 = T("loop5", "phir"), T("loop6", "log"), T("loop6", "ab")
L_BEND = T("loop7", "badha") + 0.4
L_LOOP = T("loop8", "loop")
L_FAST = T("loop9", "stress")
L_TOD = T("loop10", "todoge")
BREAK = T("fix1", "todna")
for tt in L_NODES:
    sfx(tt - 0.04, "pop", -10)
sfx(L_AGAIN, "ding", -12)
for tt in (L_B1, L_B2, L_B3):
    sfx(tt - 0.05, "pop", -11)
sfx(L_FAST - 0.3, "riser", -14, dur=2.4)
sfx(BREAK - 0.05, "impact", -6)
sfx(BREAK - 0.05, "glitch", -9)


def loop_phase(t):
    """pulse phase round the ring: slow, then faster on 'loop', fastest on 'stress flare stress flare'."""
    def rate(x):
        return 0.45 if x < L_LOOP else (0.9 if x < L_FAST else 1.6)
    # integrate piecewise
    ph, x = 0.0, L0
    for b in (L_LOOP, L_FAST, 1e9):
        if t <= x:
            break
        seg_end = min(t, b)
        if seg_end > x:
            ph += (seg_end - x) * rate(x)
        x = max(x, b)
    return ph


# ---- fix 1: breathing
F_TEEN = T("fix1", "teen")
F_SAANS = T("fix1", "saans")
F_SIX = T("fix1", "6")
F_IN = T("fix3", "4")
F_OUT = T("fix3", "6")
F_VAGUS = T("fix3", "vagus")
F_GIR = T("fix4", "gir")
F_BOX = T("fix4", "box")
F_BOX_T = [T("fix4", "lete"), T("fix4", "hold"), T("fix4", "chhodte"), T("fix4", "hold", 2)]
F_BOX_END = seg("fix4")[1] + 0.3
F_LEVEL = T("fix5", "cortisol")
F_DIN = T("fix6", "do-teen")
F_FIVE = T("fix6", "paanch-paanch")
F_EX = T("fix7", "exercise")
F_END7 = seg("fix7")[1]
for i, tt in enumerate((F_TEEN, F_TEEN + 0.15, F_TEEN + 0.3)):
    sfx(tt, "pop", -11, pan=(i - 1) * 0.5)
sfx(F_SAANS, "ding", -12)
sfx(F_SIX - 0.05, "impact", -12)
sfx(F_IN, "whoosh", -13, dur=1.2)
sfx(F_OUT, "downlifter", -13)
sfx(F_VAGUS, "sparkle", -10)
sfx(F_GIR, "downlifter", -11)
sfx(F_BOX - 0.05, "pop", -10)
for tt in F_BOX_T:
    sfx(tt, "tick", -11)
sfx(F_LEVEL, "ding", -11)
sfx(F_DIN, "pop", -11)
sfx(F_FIVE, "pop", -11)
sfx(F_FIVE + 0.25, "pop", -11)
sfx(F_EX - 0.1, "impact", -10)

# ---- fix 2: exercise
X_2025 = T("ex1", "2025")
X_YOGA = T("ex1", "yoga")
X_QI = T("ex3", "qigong")
X_WALK = T("ex3", "walking")
X_BRISK = T("ex3", "brisk")
X_DIL = T("ex3", "dil")
X_GYM = T("ex4", "gym")
X_WEIGHT = T("ex4", "weight")
X_BW = T("ex5", "bodyweight")
X_MIN = T("ex5", "20-30")
X_DAWAI = T("ex5", "dawai")
X_END = seg("ex5")[1]
sfx(X_2025 - 0.05, "pop", -10)
for tt in (X_YOGA, X_QI, X_WALK):
    sfx(tt - 0.05, "swish", -10)
sfx(X_BRISK, "ding", -12)
sfx(X_DIL, "pop", -11)
sfx(X_GYM, "pop", -11)
sfx(X_WEIGHT - 0.05, "impact", -11)
sfx(X_BW, "pop", -12)
sfx(X_MIN - 0.05, "tick", -10)
sfx(X_DAWAI - 0.05, "sparkle", -10)

# ---- fix 3: sleep
Z_NEEND = T("sleep1", "neend")
Z_SAAT = T("sleep1", "saat")
Z_NONNEG = T("sleep1", "non-negotiable")
Z_DEP = T("sleep2", "sleep")
Z_CORT = T("sleep2", "cortisol")
Z_FLARE = T("sleep2", "flare")
Z_END = seg("sleep2")[1]
sfx(Z_NEEND - 0.08, "impact", -11)
sfx(Z_SAAT, "tick", -11)
sfx(Z_NONNEG - 0.03, "impact", -8)
for tt in (Z_DEP, Z_CORT, Z_FLARE):
    sfx(tt - 0.04, "pop", -11)

# ---- recap
R_TEENO = T("recap", "teeno")
R_CORT = T("recap", "cortisol")
R_SHAANT = T("recap", "shaant")
R_SKIN = T("recap", "skin")
for tt in (R_TEENO, R_CORT, R_SHAANT, R_SKIN):
    sfx(tt - 0.04, "pop", -11)
sfx(R_SKIN + 0.1, "sparkle", -10)

# ---- mom
MO = [(T("mom1", "mummy"), "woman", "MUMMY"), (T("mom1", "pair"), "foot", "PAIR DIKHANA"),
      (T("mom1", "mandir"), "temple", "MANDIR"), (T("mom1", "chappal"), "sandal", "CHAPPAL")]
MO_STRESS = T("mom2", "stress")
MO_FLARE = T("mom2", "flare")
MO_ULTA = T("mom3", "ulta")
MO_NODES = [seg("mom3")[0] + 0.1 + 0.28 * i for i in range(4)]
for tt, _, _ in MO:
    sfx(tt - 0.05, "shutter", -13)
sfx(MO_STRESS, "downlifter", -12)
sfx(MO_ULTA, "sparkle", -9)

# ---- close + CTA
C_EK = T("close1", "ek")
C_STEPS = [T("close1", "saans"), T("close1", "yoga"), T("close1", "neend")]
C_END = seg("close1")[1]
A_DAWAI = T("cta1", "dawaiyan")
A_PART = T("cta2", "part")
A_COLLAB = T("cta2", "collab")
A_SCI = T("cta3", "science")
A_DEC = T("cta3", "decision")
for tt in C_STEPS:
    sfx(tt - 0.04, "ding", -12)
sfx(A_DAWAI, "pop", -11)
sfx(A_PART - 0.4, "pop", -10)
sfx(A_PART - 0.05, "typing", -12, dur=0.6)
sfx(A_PART + 0.75, "click", -8)
sfx(A_SCI - 0.05, "impact", -11)
sfx(A_DEC - 0.03, "impact", -9)


# ================================================================== graphics: BEHIND the speaker
def draw_behind(c, t):
    # ---- hook: giant words parked on the head
    if t < H_END + 0.5:
        for s, t0, t1, size in (("SIRF 1 CHEEZ", H_EK - 0.05, H_PSO - 0.15, 210),
                                ("PSORIASIS", H_PSO - 0.05, H_STRESS - 0.12, 230),
                                ("STRESS", H_STRESS - 0.03, BEHIND_CAPS[0][0] + 0.1, 330)):
            behind(c, s, W / 2, behind_y(t0, size), size, t, t0, t1)
        photo_card(c, "skin", 520, 420, 820, 560, t, H_SCI - 0.12, H_END - 0.1, label="Skin under a microscope",
                   sub="EPIDERMIS + DERMIS  ·  H&E STAIN", crack=H_TOD, fy=0.4)
        icon(c, "microscope", 900, 650, 190 * pop_k(t, H_SCI + 0.1, t1=H_END - 0.1)[0],
             a=pop_k(t, H_SCI + 0.1, t1=H_END - 0.1)[1], rot=8)

    # ---- fix 1
    if F_TEEN - 0.2 < t < F_SIX:
        labels = [("lungs", "SAANS"), ("yoga", "EXERCISE"), ("moon", "NEEND")]
        for i, (ic, lab) in enumerate(labels):
            t0 = F_TEEN + 0.15 * i
            k, a = pop_k(t, t0, t1=F_SIX - 0.25)
            dim = 1.0 if t < F_SAANS or i == 0 else 0.35
            x = 200 + 340 * i
            c.save()
            c.translate(x, 420)
            c.scale(k * (1.08 if (i == 0 and t > F_SAANS) else 1), k * (1.08 if (i == 0 and t > F_SAANS) else 1))
            c.drawRRect(rrect(-150, -170, 300, 340, 40), fill(INK, 0.4 * a * dim, blur=20))
            c.drawRRect(rrect(-150, -180, 300, 340, 40), fill("#101826", 0.92 * a))
            c.drawRRect(rrect(-150, -180, 300, 340, 40), stroke(GREEN if (i == 0 and t > F_SAANS) else WHITE, 5, a * dim))
            text(c, str(i + 1), -112, -112, "anton", 70, color=WHITE, a=a * dim, anchor="l")
            icon(c, ic, 0, -10, 150, a=a * dim, shadow=False)
            text(c, lab, 0, 120, "mont", 38, color=WHITE, a=a * dim)
            c.restore()
    if F_SIX - 0.1 < t < F_IN:
        counter(c, t, F_SIX - 0.05, F_IN - 0.2, W / 2, 560, 0, 6, lambda v: f"{int(round(v))}", size=380, dur=0.5)
        k, a = pop_k(t, F_SIX + 0.15, t1=F_IN - 0.2)
        pill(c, "SAANS PER MINUTE", W / 2, 640, 40, bg=GREEN, fg=INK, a=a, k=k)
    if F_IN - 0.1 < t < F_VAGUS:
        breath_sync(c, t, F_IN, F_OUT, F_VAGUS - 0.15, W / 2, 400, 230)
    if F_VAGUS - 0.1 < t < F_GIR:
        vagus(c, t, F_VAGUS - 0.05, F_GIR - 0.2)
    if F_GIR - 0.1 < t < F_BOX:
        k, a = pop_k(t, F_GIR - 0.08, t1=F_BOX - 0.2)
        title(c, "CORTISOL", W / 2 - 60, behind_y(F_GIR, 200), 200, t, F_GIR - 0.08, F_BOX - 0.2, color=WHITE, name="anton")
        down_arrow(c, W / 2 + 390, behind_y(F_GIR, 200) - 90, 120, k, a, GREEN)
    if F_BOX - 0.1 < t < F_BOX_END + 0.3:
        k, a = pop_k(t, F_BOX - 0.05, t1=F_BOX_END)
        pill(c, "BOX BREATHING", W / 2, 140, 40, bg=WHITE, fg=INK, a=a, k=k)
        box_sync(c, t, F_BOX + 0.1, F_BOX_T, F_BOX_END, W / 2, 480, 400)
    if F_LEVEL - 0.3 < t < F_DIN - 0.1:
        k, a = pop_k(t, F_LEVEL - 0.1, t1=F_DIN - 0.3)
        icon(c, "check", W / 2, 300, 210 * k, a=a)
        pill(c, "CORTISOL LEVEL: BALANCE", W / 2, 480, 40, bg=GREEN, fg=INK, a=a, k=k)
    if F_DIN - 0.2 < t < F_EX - 0.1:
        for i, (ic, lab) in enumerate((("sun", "SUBAH"), ("noon", "DOPAHAR"), ("moon", "RAAT"))):
            t0 = F_DIN + 0.28 * i
            k, a = pop_k(t, t0, t1=F_EX - 0.3)
            y = 210 + 175 * i
            c.save()
            c.translate(W / 2, y)
            c.scale(k, k)
            c.drawRRect(rrect(-330, -70, 660, 140, 70), fill("#101826", 0.92 * a))
            c.drawRRect(rrect(-330, -70, 660, 140, 70), stroke(WHITE, 4, a * 0.8))
            icon(c, ic, -250, 0, 110, a=a, shadow=False)
            text(c, lab, -175, 17, "mont", 46, color=WHITE, a=a, anchor="l")
            pill(c, "5 MIN", 220, 0, 34, bg=GREEN, fg=INK, a=a)
            c.restore()
    if F_EX - 0.2 < t < X_2025 - 0.3:
        chapter(c, t, F_EX - 0.08, X_2025 - 0.4, "02", "EXERCISE", ("yoga", "weights"))

    # ---- fix 2 (cam part)
    if S_RANK[1] - 0.2 < t < X_GYM - 0.1:
        k, a = pop_k(t, X_DIL - 0.1, t1=X_GYM - 0.3)
        beat = 1 + 0.08 * max(0, math.sin(t * 2 * math.pi * 1.9)) ** 8
        icon(c, "aheart", 330, 400, 260 * k * beat, a=a)
        icon(c, "walk", 720, 400, 240 * k, a=a)
        pill(c, "DIL KI DHADKAN  +  THODI TEZ", W / 2, 620, 36, bg=RED, fg=WHITE, a=a, k=k)
    if X_GYM - 0.2 < t < X_WEIGHT - 0.05:
        k, a = pop_k(t, X_GYM - 0.05, t1=X_WEIGHT - 0.2)
        title(c, "GYM?", W / 2, behind_y(X_GYM, 260), 260, t, X_GYM - 0.05, X_WEIGHT - 0.2, name="anton")
        icon(c, "cross", 860, 260, 170 * k, a=a, rot=10)
    if X_WEIGHT - 0.15 < t < X_MIN - 0.1:
        behind(c, "WEIGHTS", W / 2, behind_y(X_WEIGHT, 280), 280, t, X_WEIGHT - 0.05, X_BW - 0.25)
        k, a = pop_k(t, X_WEIGHT, t1=X_BW - 0.25)
        icon(c, "weights", 830, 200, 220 * k, a=a, rot=-6)
        for i, (ic, lab) in enumerate((("weights", "DUMBBELLS"), ("dash", "BODYWEIGHT"), ("yoga", "YOGA"))):
            k2, a2 = pop_k(t, X_BW + 0.25 * i, t1=X_MIN - 0.25)
            y = 240 + 160 * i
            c.save()
            c.translate(W / 2, y)
            c.scale(k2, k2)
            c.drawRRect(rrect(-300, -62, 600, 124, 62), fill("#101826", 0.92 * a2))
            c.drawRRect(rrect(-300, -62, 600, 124, 62), stroke(WHITE, 4, a2 * 0.8))
            icon(c, ic, -225, 0, 96, a=a2, shadow=False)
            text(c, lab, -155, 16, "mont", 44, color=WHITE, a=a2, anchor="l")
            c.restore()
    if X_MIN - 0.2 < t < X_DAWAI - 0.1:
        icon(c, "stopwatch", 860, 250, 200 * pop_k(t, X_MIN - 0.05, t1=X_DAWAI - 0.25)[0],
             a=pop_k(t, X_MIN - 0.05, t1=X_DAWAI - 0.25)[1])
        yb = head_top_at(X_MIN + 0.3) + 20
        counter(c, t, X_MIN - 0.05, X_DAWAI - 0.25, W / 2 - 80, yb, 20, 30,
                lambda v: f"20-{int(round(v))}", size=300, dur=0.6)
        k, a = pop_k(t, X_MIN + 0.3, t1=X_DAWAI - 0.25)
        pill(c, "MINUTE ROZ", W / 2 - 80, yb - 270, 40, bg=WHITE, fg=INK, a=a, k=k)
    if X_DAWAI - 0.2 < t < Z_NEEND - 0.1:
        k, a = pop_k(t, X_DAWAI - 0.05, t1=Z_NEEND - 0.3)
        behind(c, "= DAWAI", W / 2, behind_y(X_DAWAI, 260), 260, t, X_DAWAI - 0.05, Z_NEEND - 0.3)
        icon(c, "pill", 870, 230, 200 * k, a=a, rot=-20)

    # ---- fix 3: sleep
    if Z_NEEND - 0.2 < t < Z_SAAT + 0.05:
        chapter(c, t, Z_NEEND - 0.1, Z_SAAT - 0.05, "03", "NEEND", ("moon", "sleep"))
    if Z_SAAT - 0.1 < t < Z_DEP - 0.05:
        yb = head_top_at(Z_SAAT + 0.3) + 15
        counter(c, t, Z_SAAT - 0.05, Z_DEP - 0.25, W / 2 - 90, yb, 8, 8, lambda v: "7-8", size=330, dur=0.5)
        k, a = pop_k(t, Z_SAAT + 0.3, t1=Z_DEP - 0.25)
        icon(c, "bed", 880, yb - 150, 220 * k, a=a, rot=-5)
        pill(c, "GHANTE KI NEEND", W / 2 - 90, yb - 290, 40, bg=VIOLET, fg=WHITE, a=a, k=k)
    if Z_DEP - 0.2 < t < Z_END + 0.6:
        chain(c, t, [("NEEND KAM", "sleep", VIOLET, Z_DEP), ("CORTISOL BADHA", "testtube", AMBER, Z_CORT),
                     ("FLARE BADHA", "fire", RED, Z_FLARE)], W / 2, 210, 190, t_out=Z_END + 0.2, size=40)

    # ---- mom's story: polaroid memories
    if MOM[0] < t < MOM[1] + 0.4:
        pos = [(205, 330, -7), (520, 255, 4), (845, 330, 8), (360, 590, -3)]
        for i, (tt, ic, lab) in enumerate(MO):
            k, a = pop_k(t, tt - 0.05, t1=MO_STRESS - 0.35)
            if a <= 0:
                continue
            x, y, r = pos[i]
            c.save()
            c.translate(x, y + (1 - k) * 60)
            c.rotate(r + (1 - k) * 12)
            c.scale(lerp(0.7, 1, k), lerp(0.7, 1, k))
            c.drawRRect(rrect(-125, -135, 250, 300, 12), fill(INK, 0.45 * a, blur=18))
            c.drawRRect(rrect(-125, -145, 250, 300, 12), fill("#FBF7EE", a))
            c.drawRect(skia.Rect.MakeXYWH(-105, -125, 210, 200), fill("#E9E0CC", a))
            icon(c, ic, 0, -25, 170, a=a, shadow=False)
            text(c, lab, 0, 125, "montb", 26 if len(lab) > 8 else 32, color=INK, a=a)
            c.restore()
    if MO_STRESS - 0.2 < t < S_ULTA[0] + 0.3:
        k, a = pop_k(t, MO_STRESS - 0.05, t1=S_ULTA[0])
        title(c, "STRESS MANAGE", W / 2, 330, 120, t, MO_STRESS - 0.05, S_ULTA[0], name="anton")
        fk = 1 - 0.55 * e_io(clamp((t - MO_FLARE) / 1.0))
        k2, a2 = pop_k(t, MO_FLARE - 0.05, t1=S_ULTA[0])
        icon(c, "fire", W / 2 - 150, 520, 210 * k2 * fk, a=a2)
        down_arrow(c, W / 2 + 70, 600, 110, k2, a2, GREEN)
        text(c, "FLARE KAM", W / 2 + 150, 540, "mont", 54, color=WHITE, a=a2, anchor="l")

    # ---- close: start anywhere
    if C_EK - 0.2 < t < C_END + 0.5:
        k, a = pop_k(t, C_EK - 0.05, t1=C_END + 0.1)
        pill(c, "KISI EK JAGAH SE SHURU KARO", W / 2, 130, 36, bg=WHITE, fg=INK, a=a, k=k)
        steps = [("lungs", "SAANS", GREEN), ("yoga", "YOGA", CYAN), ("moon", "NEEND", VIOLET)]
        for i, (ic, lab, colr) in enumerate(steps):
            t0 = C_STEPS[i] - 0.05
            k2, a2 = pop_k(t, t0, t1=C_END + 0.1)
            y = 270 + 170 * i
            if i:
                arrow_line(c, 250, y - 120, 250, y - 52, e_out(clamp((t - t0 + 0.2) / 0.3)), WHITE, a2 * 0.8)
            c.save()
            c.translate(W / 2, y)
            c.scale(k2, k2)
            c.drawRRect(rrect(-330, -62, 660, 124, 62), fill("#101826", 0.92 * a2))
            c.drawRRect(rrect(-330, -62, 660, 124, 62), stroke(colr, 5, a2))
            text(c, str(i + 1), -290, 22, "anton", 64, color=colr, a=a2, anchor="l")
            icon(c, ic, -190, 0, 96, a=a2, shadow=False)
            text(c, lab, -120, 17, "mont", 46, color=WHITE, a=a2, anchor="l")
            icon(c, "check", 270, 0, 84 * spring(t - t0 - 0.35, w=18, z=0.4) if t > t0 + 0.35 else 0, a=a2,
                 shadow=False)
            c.restore()

    # ---- CTA
    if A_DAWAI - 0.2 < t < A_PART - 0.4:
        k, a = pop_k(t, A_DAWAI - 0.05, t1=A_PART - 0.6)
        icon(c, "pill", 330, 320, 230 * k, a=a, rot=-15)
        icon(c, "testtube", 560, 260, 190 * k, a=a, rot=10)
        icon(c, "microscope", 790, 330, 220 * k, a=a, rot=6)
        pill(c, "KYA KYA KIYA? KAHAN SE LIYA?", W / 2, 540, 36, bg=WHITE, fg=INK, a=a, k=k)
    if A_PART - 0.3 < t < BEHIND_CAPS[1][0] + 0.1:
        behind(c, "PART 3", W / 2, behind_y(A_PART, 340), 340, t, A_PART - 0.1, BEHIND_CAPS[1][0] - 0.25)
    if A_SCI - 0.2 < t:
        behind(c, "SCIENCE", W / 2, behind_y(A_SCI, 250) - 220, 250, t, A_SCI - 0.05, TOTAL)
        behind(c, "DECISION AAPKA", W / 2, behind_y(A_SCI, 250), 150, t, A_DEC - 0.05, TOTAL)


def chapter(c, t, t0, t1, num, name, icons):
    k, a = pop_k(t, t0, t1=t1)
    if a <= 0:
        return
    text(c, num, W / 2, 330, "anton", 260, color=WHITE, a=a * 0.25)
    title(c, name, W / 2, 470, 170, t, t0, t1, name="anton")
    for i, ic in enumerate(icons):
        icon(c, ic, 200 + 680 * i, 250, 200 * k, a=a, rot=(-8 if i == 0 else 8))


def down_arrow(c, x, y, s, k, a, colr):
    if k <= 0 or a <= 0:
        return
    c.save()
    c.translate(x, y + (1 - k) * -40)
    c.scale(k, k)
    p = skia.Path()
    p.moveTo(-s * 0.22, -s * 0.5); p.lineTo(s * 0.22, -s * 0.5); p.lineTo(s * 0.22, 0); p.lineTo(s * 0.5, 0)
    p.lineTo(0, s * 0.55); p.lineTo(-s * 0.5, 0); p.lineTo(-s * 0.22, 0); p.close()
    c.drawPath(p, fill(INK, 0.4 * a, blur=10))
    c.drawPath(p, fill(colr, a))
    c.restore()


def breath_sync(c, t, t_in, t_out, t_end, cx, cy, R):
    a = clamp((t - t_in + 0.1) / 0.25) * (1 - clamp((t - t_end) / 0.25))
    if a <= 0:
        return
    if t < t_out:
        k, lab, n, colr = e_io(clamp((t - t_in) / (t_out - t_in))), "SAANS ANDAR", "4s", GREEN
    else:
        k, lab, n, colr = 1 - e_io(clamp((t - t_out) / (t_end - t_out))), "SAANS BAHAR", "6s", CYAN
    r = lerp(R * 0.5, R, k)
    for i in range(3):
        c.drawCircle(cx, cy, r * (1 + 0.13 * (i + 1)), stroke(colr, 3, a * 0.3 / (i + 1)))
    c.drawCircle(cx, cy, r, rad_grad(cx, cy - r * 0.3, r * 1.3, [WHITE, colr, INK], [0, 0.5, 1.6], a=a * 0.9))
    text(c, n, cx, cy + 45, "anton", 140, color=INK, a=a * 0.9)
    pill(c, lab, cx, cy + R + 70, 40, bg=colr, fg=INK, a=a)


def box_sync(c, t, t0, sides, t_end, cx, cy, s):
    a = clamp((t - t0) / 0.3) * (1 - clamp((t - t_end) / 0.3))
    if a <= 0:
        return
    x, y = cx - s / 2, cy - s / 2
    c.drawRRect(rrect(x, y, s, s, 30), fill("#0E1626", 0.88 * a))
    c.drawRRect(rrect(x, y, s, s, 30), stroke(WHITE, 6, a * 0.45))
    pts = [(x, y + s), (x, y), (x + s, y), (x + s, y + s), (x, y + s)]
    labs = [("ANDAR 4s", x - 24, cy + 16, "r"), ("ROKO 4s", cx, y + 70, "c"), ("BAHAR 4s", x + s + 24, cy + 16, "l"),
            ("ROKO 4s", cx, y + s - 40, "c")]
    side, f = -1, 0.0
    for i in range(4):
        if t >= sides[i]:
            side = i
            nxt = sides[i + 1] if i < 3 else t_end
            f = e_io(clamp((t - sides[i]) / max(0.3, nxt - sides[i])))
    # trail
    for i in range(max(side, 0) + (1 if side >= 0 else 0)):
        if i < side:
            c.drawLine(*pts[i], *pts[i + 1], stroke(GREEN, 10, a))
    if side >= 0:
        px, py = lerp(pts[side][0], pts[side + 1][0], f), lerp(pts[side][1], pts[side + 1][1], f)
        c.drawLine(*pts[side], px, py, stroke(GREEN, 10, a))
        c.drawCircle(px, py, 36, fill(GREEN, 0.5 * a, blur=16))
        c.drawCircle(px, py, 17, fill(WHITE, a))
    for i, (lab, lx, ly, anc) in enumerate(labs):
        on = i == side
        if anc != "c":
            w = measure(lab, "mont", 44) + 44
            bx = lx - w if anc == "r" else lx
            c.drawRRect(rrect(bx, ly - 52, w, 70, 35), fill(GREEN if on else "#0E1626", 0.9 * a))
            text(c, lab, bx + w / 2, ly, "mont", 44, color=INK if on else WHITE, a=a)
        else:
            text(c, lab, lx, ly, "mont", 44, color=GREEN if on else WHITE, a=a * (1 if on else 0.6))


def vagus(c, t, t0, t1):
    k, a = pop_k(t, t0, t1=t1)
    if a <= 0:
        return
    pill(c, "VAGUS NERVE  ·  ACTIVATE", W / 2, 140, 38, bg=GREEN, fg=INK, a=a, k=k)
    bx, by, hx, hy = 250, 360, 830, 560
    icon(c, "brain", bx, by, 230 * k, a=a)
    icon(c, "aheart", hx, hy, 210 * k, a=a)
    pk = e_out(clamp((t - t0 - 0.2) / 0.9))
    p = skia.Path()
    n = 60
    for i in range(int(n * pk) + 1):
        u = i / n
        x = lerp(bx + 80, hx - 80, u)
        y = lerp(by + 40, hy - 30, u) + math.sin(u * 14 + t * 6) * 22 * math.sin(u * math.pi)
        p.moveTo(x, y) if i == 0 else p.lineTo(x, y)
    c.drawPath(p, stroke(GREEN, 18, a * 0.45, blur=10))
    c.drawPath(p, stroke(WHITE, 6, a))
    for j in range(3):
        u = ((t - t0) * 0.7 + j / 3) % 1.0
        if u <= pk:
            x = lerp(bx + 80, hx - 80, u)
            y = lerp(by + 40, hy - 30, u) + math.sin(u * 14 + t * 6) * 22 * math.sin(u * math.pi)
            c.drawCircle(x, y, 16, fill(GREEN, a, blur=6))


# ================================================================== graphics: STUDIO stage (behind the cutout)
def draw_stage(c, t, sk):
    if sk <= 0:
        return
    # ---- mechanism: icon flowchart along the top
    if S_MECH[0] - 0.3 < t < L0 + 0.3:
        a_top = 1 - clamp((t - L0) / 0.3)
        items = [("anxious", "STRESS", M_STRESS), ("brain", "BRAIN", M_BRAIN), ("testtube", "CORTISOL", M_CORT),
                 ("shield", "IMMUNE", M_IMM), ("microbe", "T-CELLS", M_TC), ("fire", "SKIN", M_SKIN)]
        xs = [95 + 178 * i for i in range(6)]
        for i, (ic, lab, tt) in enumerate(items):
            k, a = pop_k(t, tt - 0.05)
            a *= a_top * sk
            lit = math.exp(-max(0, t - tt) * 1.2)
            if i:
                arrow_line(c, xs[i - 1] + 62, 150, xs[i] - 62, 150, e_out(clamp((t - tt + 0.2) / 0.3)), WHITE,
                           0.7 * a, wdt=4, head=14)
            c.drawCircle(xs[i], 150, 70, fill(RED if i in (0, 5) else (AMBER if i == 2 else CYAN), 0.5 * lit * a,
                                                   blur=24))
            icon(c, ic, xs[i], 145, 110 * k, a=a, shadow=False)
            text(c, lab, xs[i], 245, "montb", 25, color=WHITE, a=a)
        # brain scan + cortisol
        if t < M_IMM + 0.2:
            photo_card(c, "brain_ct", 300, 560, 440, 440, t, M_BRAIN - 0.1, M_IMM - 0.15, label="Brain",
                       sub="CT SCAN", tilt=-4, accent=WHITE)
            if M_BRAIN < t < M_IMM:
                sy = 340 + ((t - M_BRAIN) * 420) % 440
                c.drawRect(skia.Rect.MakeXYWH(80, sy, 440, 6), fill(CYAN, 0.7 * (1 - clamp((t - M_IMM + 0.3) / 0.2))))
            k, a = pop_k(t, M_CORT - 0.05, t1=M_IMM - 0.15)
            if a > 0:
                molecule(c, 790, 530, 270, t - M_CORT, k, a * sk)
                pill(c, "CORTISOL", 790, 760, 36, bg=AMBER, fg=INK, a=a, k=k)
            stamp(c, "EMERGENCY HORMONE", W / 2, 880, 58, t, M_EMERG - 0.05, M_IMM - 0.2, colr=RED, rot=-4)
        # immune system disturbed
        if M_IMM - 0.3 < t < M_SKIN + 0.2:
            glitch = 14 * math.exp(-max(0, t - M_BIG) * 5) * (t > M_BIG)
            photo_card(c, "ihc", W / 2 + glitch * math.sin(t * 90), 540, 700, 520, t, M_IMM - 0.1, M_SKIN - 0.15,
                       label="Immune cells in tissue", sub="IMMUNOSTAIN  ·  MICROSCOPE", tilt=2)
            k, a = pop_k(t, M_IMM + 0.1, t1=M_SKIN - 0.15)
            icon(c, "shield", 900, 330, 170 * k, a=a, rot=12)
            icon(c, "warning", 960, 410, 100 * pop_k(t, M_BIG, t1=M_SKIN - 0.15)[0], a=a)
            if t > M_TC - 0.1:
                for i in range(9):
                    tc0 = M_TC + i * 0.07
                    if t < tc0:
                        continue
                    ang = hash_ang(i)
                    rr = 410 + 25 * math.sin(t * 2 + i)
                    x = W / 2 + math.cos(ang + (t - M_TC) * 0.5) * rr + math.sin(t * 25 + i) * 5
                    y = 540 + math.sin(ang + (t - M_TC) * 0.5) * rr * 0.74 + math.cos(t * 23 + i) * 5
                    tcell(c, x, y, 40 * spring(t - tc0, 16, 0.45), t, i, a=a, angry=clamp((t - M_TC - 0.5) / 1.0))
                pill(c, "T-CELLS  ·  OVERACTIVE", W / 2, 860, 38, bg=RED, fg=WHITE,
                     a=pop_k(t, M_TC, t1=M_SKIN - 0.15)[1], k=pop_k(t, M_TC, t1=M_SKIN - 0.15)[0])
        # T-cells attack the skin
        if M_SKIN - 0.3 < t < L0 + 0.3:
            photo_card(c, "skin", W / 2, 560, 760, 520, t, M_SKIN - 0.1, L0 - 0.05, label="Skin (epidermis)",
                       sub="T-CELLS ATTACK  →  PSORIASIS PLAQUE", tilt=-2, fy=0.35, accent=WHITE)
            for i in range(8):
                tc0 = M_SKIN + 0.2 + i * 0.12
                if t < tc0:
                    continue
                u = e_in(clamp((t - tc0) / 0.6))
                sx, sy = (-80 if i % 2 else W + 80), 300 + 70 * i
                tx, ty = W / 2 + (i - 3.5) * 70, 470 + 25 * (i % 3)
                x, y = lerp(sx, tx, u), lerp(sy, ty, u)
                a = 1 - clamp((t - tc0 - 0.6) / 0.25)
                tcell(c, x, y, 34, t, i, a=a * sk, angry=1.0)
                if u >= 1:
                    f = clamp((t - tc0 - 0.6) / 0.4)
                    c.drawCircle(tx, ty, 30 + 90 * f, fill(RED, 0.6 * (1 - f), blur=14))
            if t > M_SKIN + 1.0:
                c.drawRRect(rrect(W / 2 - 380, 300, 760, 520, 30),
                            fill(RED, 0.18 * (0.5 + 0.5 * math.sin(t * 9)) * (1 - clamp((t - L0 + 0.3) / 0.3))))
            stamp(c, "ATTACK!", 820, 860, 64, t, M_ATT - 0.05, L0 - 0.1, colr=RED, rot=6)

    # ---- the loop
    if L0 - 0.1 < t < S_MECH[1] + 0.3:
        amul = 0.28 if L_B1 - 0.2 < t < L_BEND else 1.0
        if L_B1 - 0.2 < t < L_B1:
            amul = lerp(1.0, 0.28, (t - L_B1 + 0.2) / 0.2)
        if L_BEND < t < L_BEND + 0.25:
            amul = lerp(0.28, 1.0, (t - L_BEND) / 0.25)
        items = [("STRESS", "anxious", RED, L_NODES[0]), ("CORTISOL", "testtube", AMBER, L_NODES[1]),
                 ("IMMUNE", "shield", CYAN, L_NODES[2]), ("FLARE", "fire", RED, L_NODES[3])]
        loop_ring(c, t, W / 2, 560, 285, items, L0, S_MECH[1] - 0.1, broken=BREAK, title_s=True,
                  amul=amul, phase=loop_phase(t), node_size=36)
        if L_AGAIN - 0.05 < t < L_B1:
            k, a = pop_k(t, L_AGAIN - 0.05, t1=L_B1 - 0.2)
            pill(c, "AUR STRESS!", W / 2, 120, 38, bg=RED, fg=WHITE, a=a, k=k)
        for (tt, s, x, y, r) in ((L_B1, "Phir se ho gaya!", 300, 330, -5), (L_B2, "Log kya sochenge?", 760, 470, 4),
                                 (L_B3, "Ab theek kaise hoga?", 330, 640, -3)):
            k, a = pop_k(t, tt - 0.05, t1=L_BEND - 0.25)
            bubble(c, s, x, y, k, a, r)
        if L_LOOP - 0.1 < t < L_FAST:
            k, a = pop_k(t, L_LOOP - 0.05, t1=L_FAST - 0.1)
            pill(c, "POORA LOOP", W / 2, 120, 40, bg=WHITE, fg=INK, a=a, k=k)
        if L_FAST - 0.1 < t < BREAK:
            k, a = pop_k(t, L_FAST - 0.05, t1=BREAK - 0.1)
            pill(c, "STRESS · FLARE · STRESS · FLARE", W / 2, 120, 40, bg=RED, fg=WHITE, a=a, k=k)
        if t > BREAK - 0.05:
            stamp(c, "LOOP TODO!", W / 2, 870, 74, t, BREAK - 0.03, S_MECH[1] - 0.15, colr=GREEN, fg=INK, rot=-5)

    # ---- 2025 meta-analysis ranking
    if S_RANK[0] - 0.3 < t < S_RANK[1] + 0.3:
        k, a = pop_k(t, X_2025 - 0.1, t1=S_RANK[1] - 0.15)
        icon(c, "barchart", 160, 160, 150 * k, a=a * sk, rot=-8)
        pill(c, "2025  META-ANALYSIS", 600, 130, 38, bg=WHITE, fg=INK, a=a * sk, k=k)
        title(c, "Sabse effective cortisol reducer", 600, 230, 40, t, X_2025 + 0.3, S_RANK[1] - 0.15, name="montb",
              stagger=0.012, maxw=780)
        rank_bars(c, t, [(1, "Yoga", "yoga", 0.95, GREEN, X_YOGA - 0.05), (2, "Qigong", "wind", 0.78, CYAN, X_QI - 0.05),
                         (3, "Brisk walking", "walk", 0.64, VIOLET, X_WALK - 0.05)], 70, 400, 165, 940,
                  t_out=S_RANK[1] - 0.15)
        if X_BRISK - 0.1 < t:
            k2, a2 = pop_k(t, X_BRISK - 0.05, t1=S_RANK[1] - 0.15)
            pill(c, "BRISK = THODA TEZ CHALNA", W / 2, 840, 38, bg=VIOLET, fg=WHITE, a=a2, k=k2)

    # ---- recap: three habits -> cortisol down -> calm skin
    if S_RECAP[0] - 0.3 < t < S_RECAP[1] + 0.3:
        for i, ic in enumerate(("lungs", "yoga", "moon")):
            k, a = pop_k(t, R_TEENO - 0.1 + 0.12 * i, t1=S_RECAP[1] - 0.2)
            icon(c, ic, 330 + 210 * i, 170, 150 * k, a=a * sk)
        chain(c, t, [("CORTISOL KAM", "chartdown", GREEN, R_CORT), ("IMMUNE SHAANT", "shield", GREEN, R_SHAANT),
                     ("SKIN SHAANT", "relieved", GREEN, R_SKIN)], W / 2, 400, 200, t_out=S_RECAP[1] - 0.2, size=44)
        arrow_line(c, W / 2, 255, W / 2, 330, e_out(clamp((t - R_CORT + 0.2) / 0.3)), WHITE,
                   0.8 * (1 - clamp((t - S_RECAP[1] + 0.2) / 0.2)))

    # ---- the loop runs backwards
    if S_ULTA[0] - 0.3 < t < S_ULTA[1] + 0.3:
        items = [("FLARE KAM", "relieved", GREEN, MO_NODES[0]), ("STRESS KAM", "relieved", GREEN, MO_NODES[1]),
                 ("CORTISOL KAM", "chartdown", GREEN, MO_NODES[2]), ("IMMUNE SHAANT", "shield", GREEN, MO_NODES[3])]
        loop_ring(c, t, W / 2, 560, 285, items, S_ULTA[0], S_ULTA[1] - 0.1, reverse=True, title_s=True,
                  ring_col=GREEN, phase=(t - S_ULTA[0]) * (0.4 if t < MO_ULTA else 0.9), node_size=32)
        k, a = pop_k(t, MO_ULTA - 0.05, t1=S_ULTA[1] - 0.15)
        pill(c, "LOOP ULTA CHAL GAYA", W / 2, 120, 40, bg=GREEN, fg=INK, a=a, k=k)


def hash_ang(i):
    return (i * 2.399963) % (2 * math.pi)


def bubble(c, s, x, y, k, a, rot):
    if k <= 0 or a <= 0:
        return
    w = measure(s, "mont", 44) + 150
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.scale(k, k)
    c.drawRRect(rrect(-w / 2, -60, w, 120, 60), fill(INK, 0.45 * a, blur=18))
    c.drawRRect(rrect(-w / 2, -66, w, 120, 60), fill(WHITE, a))
    p = skia.Path()
    p.moveTo(-30, 50); p.lineTo(-60, 100); p.lineTo(10, 52); p.close()
    c.drawPath(p, fill(WHITE, a))
    icon(c, "anxious", -w / 2 + 62, -6, 76, a=a, shadow=False)
    text(c, s, 35, 10, "mont", 44, color=INK, a=a)
    c.restore()


# ================================================================== graphics: FRONT
def draw_front(c, t):
    stamp(c, "NON-NEGOTIABLE", W / 2, 1290, 78, t, Z_NONNEG - 0.03, Z_DEP - 0.2, colr=RED, rot=-6)
    if A_PART - 0.6 < t < BEHIND_CAPS[1][1] + 0.4:
        comment_box(c, t, A_PART - 0.45, BEHIND_CAPS[1][1], W / 2, 1290, typed="PART 3", t_type=A_PART - 0.05)
    # impact flash
    for tt, amt in ((H_STRESS, 0.55), (BREAK, 0.4), (Z_NONNEG, 0.25)):
        if tt <= t < tt + 0.25:
            c.drawRect(skia.Rect.MakeWH(W, H), fill(WHITE, amt * (1 - (t - tt) / 0.25)))


# ================================================================== captions
def build_caption_groups():
    groups, cur = [], []
    for i, w in enumerate(WORDS):
        gap = w["s"] - WORDS[i - 1]["e"] if i else 0
        chars = sum(len(x["w"]) + 1 for x in cur)
        tail_word = (len(w["w"]) <= 7 and w["raw"].rstrip('"')[-1:] in ".,?!:" and gap < 0.2 and len(cur) < 5
                     and chars + len(w["w"]) <= 27)
        if cur and not tail_word and (len(cur) >= 4 or chars + len(w["w"]) > 20 or gap > 0.35
                                      or w["key"] != cur[-1]["key"] or w.get("big") and len(cur) >= 2):
            groups.append(dict(words=cur))
            cur = []
        cur.append(w)
        if w["raw"].rstrip('"')[-1:] in ".,?!:":
            groups.append(dict(words=cur))
            cur = []
    if cur:
        groups.append(dict(words=cur))
    return groups


CAP = Captions(build_caption_groups(), y=1560, size=76)
CAP_BEHIND = Captions(CAP.groups, y=760, size=104)
for a, b in BEHIND_CAPS:
    CAP.mute(a, b)


def behind_caps(c, t):
    for a, b in BEHIND_CAPS:
        if a <= t < b:
            CAP_BEHIND.draw(c, t, y=behind_y(a, 104) - 40)


# ================================================================== compose
_shake = [(H_STRESS, 16), (BREAK, 12), (M_ATT, 9), (Z_NONNEG, 8), (X_WEIGHT, 6)]


def draw(c, t, f):
    fi = min(f, NB - 1)
    rgba = BASE.array(fi)
    frame = skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType)
    sk = studio_k(t)
    z, ax, ay = cam(t)
    # studio: speaker scaled about the bottom centre
    zz, axx, ayy = lerp(z, 0.8, sk), lerp(ax, 540, sk), lerp(ay, 1920, sk)
    shx = shy = 0.0
    for tt, amp in _shake:
        if tt <= t < tt + 0.35:
            d = 1 - (t - tt) / 0.35
            shx += math.sin(t * 95) * amp * d
            shy += math.cos(t * 83) * amp * d
    c.save()
    c.translate(shx, shy)
    warm = MOM[0] <= t < MOM[1] + 0.1 and sk < 0.5

    def xf():
        c.translate(axx, ayy)
        c.scale(zz, zz)
        c.translate(-ax if sk < 1 else -540, -ay if sk < 1 else -1920)

    paint = skia.Paint(ColorFilter=WARM) if warm else None
    # 1. footage (CAM)
    if sk < 1:
        c.save()
        c.translate(ax, ay)
        c.scale(z, z)
        c.translate(-ax, -ay)
        c.drawImage(frame, 0, 0, SAMP, paint)
        c.restore()
    # 2. studio backdrop + stage
    if sk > 0:
        c.saveLayerAlpha(None, int(255 * sk))
        studio_bg(c, t)
        c.restore()
    draw_stage(c, t, sk)
    # 3. behind-the-speaker graphics (CAM)
    if sk < 1:
        c.saveLayerAlpha(None, int(255 * (1 - sk)))
        draw_behind(c, t)
        behind_caps(c, t)
        c.restore()
    # 4. the speaker, cut out, on top
    person = person_image(fi, rgba)
    c.save()
    c.translate(axx, ayy)
    c.scale(zz, zz)
    c.translate(-lerp(ax, 540, sk), -lerp(ay, 1920, sk))
    if sk > 0:
        sp = skia.Paint(ImageFilter=skia.ImageFilters.DropShadowOnly(0, 18, 26, 26, col_ink(0.6 * sk)))
        c.drawImage(person, 0, 0, SAMP, sp)
    c.drawImage(person, 0, 0, SAMP, paint)
    c.restore()
    # 5. front graphics, captions, grade
    draw_front(c, t)
    c.restore()
    c.drawRect(skia.Rect.MakeWH(W, H), rad_grad(W / 2, H * 0.48, H * 0.75, ["#00000000", "#00000000", "#000000"],
                                                 [0, 0.62, 1], a=0.42))
    c.drawRect(skia.Rect.MakeXYWH(0, H - 620, W, 620), lin_grad(0, H - 620, 0, H, ["#00000000", "#000000"], a=0.45))
    CAP.draw(c, t)
    if t > E["total"]:
        c.drawRect(skia.Rect.MakeWH(W, H), fill(INK, clamp((t - E["total"]) / (TAIL - 0.2))))


def col_ink(a):
    return skia.Color(0, 0, 0, int(255 * clamp(a)))


film = Film(draw, TOTAL, FPS, out_dir=HERE / "out", sheet_n=36)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "cues"
    if cmd == "cues":
        for name in ("S_MECH", "S_RANK", "S_RECAP", "S_ULTA", "MOM", "BEHIND_CAPS"):
            print(name, globals()[name])
        print("total", TOTAL, "sfx", len(SFX))
    elif cmd == "stills":
        film.stills([float(x) for x in sys.argv[2:]])
    elif cmd == "sheet":
        film.sheet()
    elif cmd == "render":
        draft = "--draft" in sys.argv
        film.render(HERE / "work" / ("draft.mp4" if draft else "picture.mp4"), draft=draft)
    elif cmd == "sfx":
        json.dump(SFX, open(HERE / "work" / "sfx.json", "w"), indent=1)
        print(len(SFX), "sfx")


def write_srt(path):
    def ts(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    lines = []
    for i, g in enumerate(CAP.groups):
        s, e = g["words"][0]["s"], g["words"][-1]["e"] + 0.25
        if i + 1 < len(CAP.groups):
            e = min(e, CAP.groups[i + 1]["words"][0]["s"])
        lines.append(f"{i + 1}\n{ts(s)} --> {ts(e)}\n{' '.join(w['w'] for w in g['words'])}\n")
    Path(path).write_text("\n".join(lines))


if __name__ == "__main__" and sys.argv[1:2] == ["srt"]:
    write_srt(HERE / "out" / "captions_hinglish.srt")
    print("-> out/captions_hinglish.srt", len(CAP.groups), "captions")
