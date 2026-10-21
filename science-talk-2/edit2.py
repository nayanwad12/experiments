"""Gut -> psoriasis explainer (video 2): the full edit on top of work/base.mp4 + work/alpha.npy.

    python3 edit2.py cues | stills 5.2 30 ... | sheet | render | sfx | srt

Mature/editorial look: no emoji or stickers. Thin-line icons that draw on, mono lower-third tags, serif
italic quotes, hairline diagrams, museum-plate science images. Two looks as in video 1: CAM (footage,
giant words + plates parked BEHIND the speaker) and STUDIO (charcoal backdrop, speaker cut out at the bottom,
diagrams above). Every element is cued off a spoken word.
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
from gfx2 import (GOLD, INK, MUTED, PANEL, SAMP, TEAL, WARN, WHITE, H, W, Captions, arrow, behind,  # noqa: E402
                  big_number, box_node, clamp, comment_cta, e_in, e_io, e_out, fill, headline, lerp, lin_grad,
                  line_icon, measure, plate, quote, rad_grad, rank_rows, ring_loop, rrect, scrim, stroke, studio_bg,
                  tag, text, win)
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
    return re.sub(r"[^a-z0-9\-%]", "", s.lower())


def cue(key, word, n=1, end=False):
    hits = [w for w in WORDS if w["key"] == key and _norm(w["w"]) == _norm(word)]
    if len(hits) < n:
        raise KeyError(f"{key}:{word}#{n}")
    return hits[n - 1]["e" if end else "s"]


def seg(key):
    ws = [w for w in WORDS if w["key"] == key]
    return ws[0]["s"], ws[-1]["e"]


T = cue
SFX = []


def sfx(t, kind, gain=-12.0, **kw):
    SFX.append(dict(t=round(t, 3), kind=kind, gain_db=gain, **kw))


# ---- hook
H_GUT = T("hook1", "gut")
H_PSO = T("hook1", "psoriasis")
H_MAAN = T("hook1", "maanoge", end=True)
H_KAISE = T("hook1", "kaise")
H_THEEK = seg("hook2")[1]
H_BUT = T("hook3", "but")
H_AADHA = T("hook5", "aadha")
H_END = seg("hook5")[1]
# ---- axis + research (studio)
X_KHAR = T("axis1", "kharbon")
X_ACHHE = T("axis1", "achhe")
X_BURE = T("axis1", "bure")
X_MICRO = T("axis2", "gut")
X_SEEDHI = T("axis3", "seedhi")
X_IN = seg("axis3")[0]
X_AXIS = T("axis4", "gut-")
R_START = seg("res1")[0]
R_2025 = T("res1", "2025")
R_GHAT = T("res1", "ghat")
R_FAEC = T("res2", "faecalibacterium")
R_ANTI = T("res3", "anti-inflammatory")
R_INFL = T("res3", "inflammation")
R_70 = T("res3", "70%")
R_GUTK = T("res4", "gut")
R_IMM = T("res4", "immunity")
R_ATT = T("res5", "attack")
R_END = seg("res5")[1]
# ---- fixes
F_CHAAR = T("fix1", "chaar")
F_ONE = T("fix1", "number")
F_FIBER = T("fix2", "fiber")
F_ITEMS = [T("fix2", "sabzi"), T("fix2", "phal"), T("fix2", "daalein"), T("fix2", "chhilke")]
F_FOOD = T("fix3", "achhe")
F_END = seg("fix3")[1]
P_PRO = T("pro1", "probiotics")
P_ITEMS = [T("pro1", "dahi", 2), T("pro1", "kanji"), T("pro1", "achaar", 2)]
P_MARKET = T("pro2", "market")
P_FERM = T("pro2", "fermented")
P_BADHA = T("pro2", "badha")
P_END = seg("pro2")[1]
Q_PRE = T("pre2", "prebiotics")
Q_ITEMS = [T("pre2", "lahsun"), T("pre3", "pyaaz"), T("pre3", "kela")]
Q_FERT = T("pre3", "fertilizer")
Q_END = seg("pre3")[1]
A_FOUR = seg("anti1")[0]
A_ANTI = T("anti1", "antibiotics")
A_MAAR = T("anti1", "maar")
A_DOC = T("anti2", "doctor")
A_AYUR = T("anti2", "ayurveda")
# ---- agni (studio)
G_AGNI1 = T("anti2", "agni")
G_AGNI = T("agni1", "agni")
G_DIG = T("agni1", "digestive")
G_GUT = T("agni2", "gut")
G_BHASHA = T("agni3", "alag-alag")
G_END = seg("agni3")[1]
# ---- mom
M_MUMMY = T("mom1", "mummy")
M_DAHI = T("mom1", "dahi")
M_GUT = T("mom1", "gut")
M_SKIN = T("mom1", "skin")
M_COINC = T("mom2", "coincidence")
M_AXIS = T("mom2", "gut-skin")
M_CREAM = T("mom2", "cream")
M_PET = T("mom3", "pet")
M_END = seg("mom3")[1]
# ---- CTA
C_PART = T("cta1", "part")
C_VIT = T("cta1", "vitamin")
C_SUN = T("cta1", "sunlight")
C_MOIST = T("cta1", "moisturizer")
C_COMMENT = T("cta2", "comment")
C_PART4 = T("cta2", "part", 2)
C_SCI = T("cta2", "science")
C_DEC = T("cta2", "decision")
C_YOU = seg("cta3")[0]

S_AXIS = (seg("axis1")[0] - 0.25, R_END + 0.3)
S_AGNI = (A_AYUR - 0.3, G_END + 0.3)
STUDIOS = [S_AXIS, S_AGNI]
TR = 0.4
MOM = (seg("mom1")[0] - 0.3, M_END + 0.2)
BEHIND_CAPS = [(H_BUT - 0.05, H_AADHA - 0.12), (M_PET - 0.05, M_END + 0.25)]

# ---- sound cues (restrained: whooshes on look changes, soft ticks/clicks on reveals, low hits on headlines)
for a, b in STUDIOS:
    sfx(a - 0.15, "whoosh", -12, dur=0.6)
    sfx(b - 0.15, "whoosh", -14, dur=0.5)
for tt in (H_GUT, H_PSO, H_AADHA, F_FIBER, P_PRO, Q_PRE, A_ANTI, G_AGNI, M_COINC, C_PART, C_SCI):
    sfx(tt - 0.04, "impact", -16)
for tt in (X_KHAR, X_MICRO, R_2025, R_FAEC, R_INFL, R_GUTK, R_IMM, F_CHAAR, P_FERM, Q_FERT, A_DOC, G_DIG,
           M_DAHI, M_GUT, M_SKIN, C_VIT, C_SUN, C_MOIST):
    sfx(tt - 0.02, "tick", -14)
for tt in F_ITEMS + P_ITEMS + Q_ITEMS:
    sfx(tt - 0.02, "click", -15)
sfx(X_SEEDHI - 0.1, "riser", -18, dur=0.9)
sfx(X_AXIS, "sparkle", -15)
sfx(R_GHAT, "downlifter", -14)
sfx(R_70 - 0.05, "impact", -13)
sfx(R_ATT - 0.03, "impact", -12)
sfx(R_ATT, "glitch", -16)
sfx(A_MAAR, "glitch", -16)
sfx(C_PART4 - 0.05, "typing", -15, dur=0.6)
sfx(C_PART4 + 0.7, "click", -11)


def studio_k(t):
    k = 0.0
    for a, b in STUDIOS:
        k = max(k, e_io(clamp((t - a) / TR)) * (1 - e_io(clamp((t - b) / TR))))
    return k


# ================================================================== camera
def cut_index(t):
    for i in range(len(CUT_T) - 1):
        if t < CUT_T[i + 1]:
            return i
    return len(CUT_T) - 2


def cam(t):
    i = cut_index(t)
    a, b = CUT_T[i], CUT_T[i + 1]
    z = 1.0 if i % 2 == 0 else 1.09
    z *= 1 + 0.03 * clamp((t - a) / max(0.5, b - a))
    if t < 0.7:
        z *= lerp(1.12, 1.0, e_out(t / 0.7))
    return z, 540, 1010


# ================================================================== frames + matte
BASE = Layer(HERE / "work" / "base.mp4", W, H, FPS)
_ALPHA = None
_HEAD = None
_ex = np.clip(np.minimum(np.arange(W), W - 1 - np.arange(W)) / 70.0, 0, 1)
EDGE_FEATHER = (_ex[None, :] * np.ones((H, 1))).astype(np.float32)


def alpha_small(fi):
    global _ALPHA
    if _ALPHA is None:
        _ALPHA = np.load(HERE / "work" / "alpha.npy", mmap_mode="r")
    return _ALPHA[min(fi, len(_ALPHA) - 1)]


def head_top_series():
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
            if (HERE / "work" / "matte.log").read_text().find("matte done") >= 0:
                np.save(p, _HEAD)
    return _HEAD


def head_top_at(t):
    hs = head_top_series()
    return float(hs[min(int(t * FPS), len(hs) - 1)])


def behind_y(t0, size):
    return clamp(head_top_at(t0 + 0.3) + size * 0.3, 420, 900)


WARM = skia.ColorFilters.Matrix([
    1.06, 0.03, 0.0, 0, 0.015,
    0.02, 1.00, 0.0, 0, 0.0,
    0.0, 0.0, 0.9, 0, -0.01,
    0, 0, 0, 1, 0])
GRADE = skia.ColorFilters.Matrix([          # gentle filmic: a touch less saturation + contrast
    0.97, 0.03, 0.0, 0, -0.01,
    0.015, 0.97, 0.015, 0, -0.01,
    0.0, 0.03, 0.97, 0, -0.005,
    0, 0, 0, 1, 0])


def person_image(fi, rgba):
    a = cv2.resize(np.asarray(alpha_small(fi)), (W, H), interpolation=cv2.INTER_LINEAR)
    a = np.clip((a.astype(np.int32) - 20) * 255 // 215, 0, 255).astype(np.float32) * EDGE_FEATHER
    out = rgba.copy()
    out[..., 3] = a.astype(np.uint8)
    return skia.Image.fromarray(out, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType)


# ================================================================== small composites
def icon_tiles(c, t, items, y, t_out, size=96, gap=250, label_size=26):
    """row of line icons with mono labels: items = [(icon or None, label, t_on)]"""
    n = len(items)
    x0 = W / 2 - gap * (n - 1) / 2
    k0, a0 = win(t, items[0][2] - 0.1, t_out)
    scrim(c, x0 - gap / 2 - 10, y - size - 30, gap * n + 20, size + 150, a0, 0.5)
    for i, (ic, lab, ton) in enumerate(items):
        k, a = win(t, ton - 0.05, t_out, fin=0.6)
        if a <= 0:
            continue
        x = x0 + gap * i
        if ic:
            line_icon(c, ic, x, y - size / 2, size, k=k, a=a, width=1.5)
        else:
            c.drawCircle(x, y - size / 2, 10 * k, fill(TEAL, a))
        text(c, lab, x, y + 50, "monob", label_size, color=WHITE, a=a * k, tracking=0.1)


def dot_matrix(c, t, t0, t1, cx, cy, n_on=70, step=34, r=9):
    k, a = win(t, t0, t1, fin=0.2)
    if a <= 0:
        return
    for i in range(100):
        row, colm = divmod(i, 10)
        x = cx - step * 4.5 + colm * step
        y = cy - step * 4.5 + row * step
        on = i < n_on
        ki = clamp((t - t0 - 0.012 * i) / 0.25)
        if ki <= 0:
            continue
        if on:
            c.drawCircle(x, y, r * ki, fill(TEAL, a))
        else:
            c.drawCircle(x, y, r, stroke(WHITE, 1.4, a * 0.45 * ki))


def chapter_tag(c, t, n, t0, t1):
    tag(c, f"{n:02d} / 04", W / 2, 150, t, t0, t1, size=28, accent=TEAL)


# ================================================================== BEHIND the speaker (cam)
def draw_behind(c, t):
    # ---- hook
    if t < H_END + 0.5:
        behind(c, "GUT HEALTH", W / 2, behind_y(H_GUT, 250), 250, t, H_GUT - 0.04, H_PSO - 0.12)
        behind(c, "PSORIASIS", W / 2, behind_y(H_PSO, 250), 250, t, H_PSO - 0.04, H_MAAN + 0.4)
        if H_KAISE - 0.2 < t < H_THEEK + 0.5:
            k, a = win(t, H_KAISE - 0.05, H_THEEK + 0.15)
            scrim(c, 60, 210, 960, 330, a)
            quote(c, "Pet theek nahi, to chamdi ka kya ilaaj?", 130, 330, t, H_KAISE - 0.05, H_THEEK + 0.15,
                  size=66, maxw=820)
        behind(c, "AADHA THEEK", W / 2, behind_y(H_AADHA, 230), 230, t, H_AADHA - 0.04, H_END + 0.3)

    # ---- four fixes overview
    if F_CHAAR - 0.2 < t < F_FIBER:
        k, a = win(t, F_CHAAR - 0.1, F_FIBER - 0.3)
        scrim(c, 90, 140, 900, 640, a)
        rows = [("Fiber", "salad"), ("Probiotics", "milk"), ("Prebiotics", "plant"), ("Antibiotics: bas zaroorat par", "pill")]
        for i, (lab, ic) in enumerate(rows):
            ki, ai = win(t, F_CHAAR + 0.18 * i, F_FIBER - 0.3)
            y = 230 + 140 * i
            text(c, f"{i + 1:02d}", 150, y + 30, "serif", 80, color=WHITE, a=ai * 0.9, anchor="l")
            line_icon(c, ic, 300, y + 2, 64, k=ki, a=ai, width=1.6)
            text(c, lab, 370, y + 20, "heavy", 50 if i < 3 else 40, color=WHITE, a=ai, anchor="l")
            if i < 3:
                c.drawRect(skia.Rect.MakeXYWH(150, y + 62, 780 * ki, 1.5), fill(WHITE, 0.25 * ai))

    # ---- 01 fiber
    if F_FIBER - 0.2 < t < F_END + 0.4:
        chapter_tag(c, t, 1, F_FIBER - 0.1, F_FOOD - 0.2)
        behind(c, "FIBER", W / 2, behind_y(F_FIBER, 320), 320, t, F_FIBER - 0.04, F_FOOD - 0.2)
        icon_tiles(c, t, [("carrot", "SABZI", F_ITEMS[0]), ("apple", "PHAL", F_ITEMS[1]), ("leaf", "DAAL", F_ITEMS[2]),
                          ("bread", "CHHILKE KA AATA", F_ITEMS[3])], 330, F_FOOD - 0.2, size=84, gap=240, label_size=24)
        if t > F_FOOD - 0.2:
            k, a = win(t, F_FOOD - 0.05, F_END + 0.1)
            scrim(c, 60, 200, 960, 330, a)
            quote(c, "Fiber, achhe bacteria ka khaana hai.", 130, 330, t, F_FOOD - 0.05, F_END + 0.1, size=66,
                  maxw=840)

    # ---- 02 probiotics
    if P_PRO - 0.3 < t < P_END + 0.4:
        chapter_tag(c, t, 2, P_PRO - 0.1, P_MARKET - 0.2)
        behind(c, "PROBIOTICS", W / 2, behind_y(P_PRO, 250), 250, t, P_PRO - 0.04, P_MARKET - 0.2)
        icon_tiles(c, t, [("milk", "DAHI · FRESH", P_ITEMS[0]), ("glass-full", "KANJI", P_ITEMS[1]),
                          ("bottle", "GHAR KA ACHAAR", P_ITEMS[2])], 340, P_MARKET - 0.2, size=88, gap=300)
        if t > P_MARKET - 0.2:
            tag(c, "MARKET WALA NAHI", W / 2, 180, t, P_MARKET - 0.05, P_END + 0.1, color=WARN, size=30)
            headline(c, "Fermented food", W / 2, 360, 110, t, P_FERM - 0.05, P_END + 0.1, name="heavy")
            k, a = win(t, P_BADHA - 0.1, P_END + 0.1)
            line_icon(c, "trending-up", W / 2 - 170, 470, 70, k=k, color=TEAL, a=a, width=1.8)
            text(c, "GUT BACTERIA BADHTE HAIN", W / 2 - 120, 482, "monob", 28, color=WHITE, a=a * k, anchor="l",
                 tracking=0.1)

    # ---- 03 prebiotics
    if Q_PRE - 0.3 < t < Q_END + 0.4:
        chapter_tag(c, t, 3, Q_PRE - 0.1, Q_END + 0.1)
        behind(c, "PREBIOTICS", W / 2, behind_y(Q_PRE, 250), 250, t, Q_PRE - 0.04, Q_END + 0.1)
        k, a = win(t, Q_ITEMS[0] - 0.1, Q_END + 0.1)
        scrim(c, 110, 210, 860, 300, a, 0.5)
        x = 170
        for i, (nm, tt) in enumerate(zip(("Lahsun", "Pyaaz", "Kela"), Q_ITEMS)):
            ki, ai = win(t, tt - 0.05, Q_END + 0.1)
            text(c, nm, x, 320 + (1 - ki) * 20, "italic", 84, color=WHITE, a=ai, anchor="l")
            x += measure(nm, "italic", 84) + 60
            if i < 2:
                c.drawCircle(x - 32, 296, 6 * ki, fill(TEAL, ai))
        kf, af = win(t, Q_FERT - 0.1, Q_END + 0.1)
        line_icon(c, "plant", 230, 430, 70, k=kf, color=TEAL, a=af, width=1.8)
        text(c, "ACHHE BACTERIA KA FERTILIZER", 290, 442, "monob", 28, color=WHITE, a=af * kf, anchor="l",
             tracking=0.1)

    # ---- 04 antibiotics
    if A_FOUR - 0.3 < t < S_AGNI[0] + 0.4:
        chapter_tag(c, t, 4, A_FOUR, S_AGNI[0])
        behind(c, "ANTIBIOTICS", W / 2, behind_y(A_ANTI, 240), 240, t, A_ANTI - 0.04, A_DOC - 0.2)
        k, a = win(t, A_ANTI + 0.1, A_DOC - 0.2)
        line_icon(c, "pill", 880, 280, 120, k=k, a=a, width=1.5)
        if k > 0.6:
            c.drawLine(820, 340, 940, 220, stroke(WARN, 4, a * clamp((k - 0.6) / 0.4)))
        tag(c, "BINA ZAROORAT KE NAHI", 380, 280, t, A_ANTI + 0.4, A_DOC - 0.2, size=30, color=WHITE)
        tag(c, "ACHHE BACTERIA KO MAAR DETE HAIN", W / 2, 400, t, A_MAAR - 0.05, A_DOC - 0.2, size=28, color=WARN)
        if t > A_DOC - 0.3:
            k2, a2 = win(t, A_DOC - 0.1, S_AGNI[0])
            scrim(c, 120, 200, 840, 300, a2, 0.55)
            line_icon(c, "stethoscope", W / 2, 300, 120, k=k2, a=a2, width=1.5)
            text(c, "SIRF DOCTOR KI SALAH PAR", W / 2, 440, "monob", 32, color=WHITE, a=a2 * k2, tracking=0.12)

    # ---- mom: dahi -> gut -> skin
    if MOM[0] < t < M_PET:
        k, a = win(t, M_MUMMY - 0.1, M_COINC - 0.25)
        if a > 0:
            scrim(c, 70, 230, 940, 500, a, 0.78)
            text(c, "MUMMY KA ANUBHAV", 130, 295, "monob", 26, color=MUTED, a=a, anchor="l", tracking=0.14)
            steps = [("Dahi, roz", M_DAHI), ("Pehle gut sudhra", M_GUT), ("Phir skin theek hui", M_SKIN)]
            for i, (s, tt) in enumerate(steps):
                ki, ai = win(t, tt - 0.05, M_COINC - 0.25)
                y = 400 + 115 * i
                c.drawCircle(150, y - 18, 9, fill(TEAL if i == 2 else WHITE, ai))
                if i:
                    c.drawLine(150, y - 133 + 18, 150, lerp(y - 133 + 18, y - 30, ki), stroke(WHITE, 2, ai * 0.6))
                text(c, s, 190, y + (1 - ki) * 16, "italic", 72, color=WHITE, a=ai * ki, anchor="l")
        behind(c, "COINCIDENCE NAHI", W / 2, behind_y(M_COINC, 200), 200, t, M_COINC - 0.04, M_CREAM - 0.3)
        tag(c, "GUT–SKIN AXIS", W / 2, 170, t, M_AXIS - 0.05, M_CREAM - 0.3, size=32, accent=TEAL)
        if t > M_CREAM - 0.3:
            k3, a3 = win(t, M_CREAM - 0.1, M_PET - 0.1)
            scrim(c, 60, 210, 960, 330, a3, 0.75)
            quote(c, "Ilaaj sirf cream mein nahi.", 130, 340, t, M_CREAM - 0.1, M_PET - 0.1, size=72, maxw=860)

    # ---- CTA
    if C_PART - 0.2 < t < C_COMMENT:
        behind(c, "PART 4", W / 2, behind_y(C_PART, 330), 330, t, C_PART - 0.04, C_VIT - 0.15)
        icon_tiles(c, t, [("sun", "VITAMIN D", C_VIT), ("sun-high", "SUNLIGHT", C_SUN), ("droplet", "MOISTURIZER", C_MOIST)],
                   360, C_COMMENT - 0.2, size=120, gap=320, label_size=30)
    if C_SCI - 0.2 < t:
        behind(c, "SCIENCE", W / 2, behind_y(C_SCI, 250) - 230, 250, t, C_SCI - 0.04, TOTAL)
        behind(c, "DECISION AAPKA", W / 2, behind_y(C_SCI, 250), 150, t, C_DEC - 0.04, TOTAL)


# ================================================================== STUDIO stage
def draw_stage(c, t, sk):
    if sk <= 0:
        return
    # ---- the gut microbiome
    if S_AXIS[0] - 0.3 < t < X_IN + 0.3:
        plate(c, "bacteria", W / 2, 520, 900, 620, t, X_KHAR - 0.25, X_IN - 0.1,
              caption="GUT BACTERIA  ·  SEM-STYLE ILLUSTRATION", zoom0=1.05, zoom1=1.22)
        tag(c, "KHARBON BACTERIA", W / 2, 140, t, X_KHAR - 0.05, X_MICRO - 0.15, size=30)
        tag(c, "ACHHE", 330, 290, t, X_ACHHE - 0.05, X_IN - 0.1, size=28, accent=TEAL)
        tag(c, "BURE", 760, 640, t, X_BURE - 0.05, X_IN - 0.1, size=28, accent=WARN)
        headline(c, "Gut microbiome", W / 2, 170, 100, t, X_MICRO - 0.05, X_IN - 0.15, name="heavy")
    # ---- the axis: a straight line from gut to skin
    if X_IN - 0.3 < t < R_START + 0.3:
        plate(c, "bacteria", 290, 560, 400, 330, t, X_IN - 0.05, R_START - 0.1, caption="GUT", zoom0=1.25, zoom1=1.35)
        plate(c, "skin", 790, 560, 400, 330, t, X_IN + 0.1, R_START - 0.1, caption="SKIN", fy=0.35)
        lk = e_out(clamp((t - X_SEEDHI + 0.1) / 0.6))
        _, la = win(t, X_SEEDHI - 0.1, R_START - 0.1)
        if lk > 0:
            c.drawLine(490, 560, lerp(490, 590, lk), 560, stroke(WHITE, 3, la))
            ph = ((t - X_SEEDHI) * 0.8) % 1.0
            c.drawCircle(lerp(490, 590, ph), 560, 8, fill(TEAL, la * lk))
        headline(c, "GUT–SKIN AXIS", W / 2, 300, 130, t, X_AXIS - 0.05, R_START - 0.1)
    # ---- research: good bacteria down
    if R_START - 0.3 < t < R_INFL + 0.3:
        tag(c, "RESEARCH  ·  2025", W / 2, 140, t, R_2025 - 0.05, R_INFL - 0.15, size=30, accent=TEAL)
        headline(c, "Psoriasis patients ka gut", W / 2, 290, 74, t, R_START + 0.1, R_INFL - 0.15, name="heavy")
        plate(c, "bacteria", W / 2, 560, 800, 380, t, R_START + 0.2, R_GHAT + 0.6, caption="GUT MICROBIOME",
              zoom0=1.1, zoom1=1.3)
        dk = e_io(clamp((t - R_GHAT + 0.1) / 0.6)) * win(t, R_START + 0.2, R_GHAT + 0.6)[1]
        if dk > 0:
            c.drawRect(skia.Rect.MakeXYWH(W / 2 - 400, 370, 800, 380), fill(INK, 0.75 * dk))
        k, a = win(t, R_GHAT - 0.1, R_INFL - 0.15)
        line_icon(c, "trending-down", W / 2 - 230, 450 + 110 * (t < R_GHAT + 0.7), 110, k=k, color=WARN, a=a, width=1.6)
        text(c, "ACHHE BACTERIA", W / 2 - 150, 440 + 110 * (t < R_GHAT + 0.7), "heavy", 56, color=WHITE, a=a * k, anchor="l")
        text(c, "GHAT JAATE HAIN", W / 2 - 150, 490 + 110 * (t < R_GHAT + 0.7), "monob", 30, color=WARN, a=a * k,
             anchor="l", tracking=0.12)
        k2, a2 = win(t, R_FAEC - 0.1, R_INFL - 0.15)
        text(c, "Faecalibacterium", W / 2, 660 + (1 - k2) * 20, "italic", 104, color=WHITE, a=a2 * k2)
        c.drawRect(skia.Rect.MakeXYWH(W / 2 - 300 * k2, 700, 600 * k2, 2), fill(TEAL, a2))
        tag(c, "ANTI-INFLAMMATORY BACTERIUM", W / 2, 790, t, R_ANTI - 0.05, R_INFL - 0.15, size=28, accent=TEAL)
    # ---- anti-inflammatory -> inflammation -> 70% immune cells
    if R_INFL - 0.3 < t < R_GUTK + 0.3:
        k, a = win(t, R_INFL - 0.1, R_70 - 0.2)
        line_icon(c, "flame", W / 2, 380, 220, k=k, color=WARN, a=a, width=1.2, glow=0.6)
        text(c, "INFLAMMATION", W / 2, 600, "heavy", 70, color=WHITE, a=a * k)
        line_icon(c, "arrow-up", W / 2 + 290, 575, 70, k=k, color=WARN, a=a, width=2)
        headline(c, "70%", 330, 520, 250, t, R_70 - 0.05, R_GUTK - 0.15)
        dot_matrix(c, t, R_70 + 0.15, R_GUTK - 0.15, 790, 440, n_on=70, step=36, r=10)
        tag(c, "IMMUNE CELLS  ·  GUT MEIN", W / 2, 740, t, R_70 + 0.4, R_GUTK - 0.15, size=30)
    # ---- the chain
    if R_GUTK - 0.3 < t < S_AXIS[1] + 0.3:
        to = S_AXIS[1] - 0.25
        box_node(c, "Gut kharab", W / 2, 230, t, R_GUTK - 0.05, to, icon="virus", color=WARN, w=560)
        arrow(c, W / 2, 300, W / 2, 380, e_out(clamp((t - R_IMM + 0.2) / 0.4)), WHITE, win(t, R_IMM - 0.2, to)[1])
        box_node(c, "Immunity kharab", W / 2, 450, t, R_IMM - 0.05, to, icon="shield-x", color=WARN, w=560)
        arrow(c, W / 2, 520, W / 2, 600, e_out(clamp((t - R_ATT + 0.2) / 0.4)), WHITE, win(t, R_ATT - 0.2, to)[1])
        box_node(c, "Skin par attack", W / 2, 670, t, R_ATT - 0.05, to, icon="body-scan", color=WARN, w=560,
                 active=math.exp(-max(0, t - R_ATT) * 2))

    # ---- Ayurveda: agni
    if S_AGNI[0] - 0.3 < t < S_AGNI[1] + 0.3:
        tag(c, "AYURVEDA", W / 2, 140, t, A_AYUR - 0.05, S_AGNI[1] - 0.2, size=30, accent=GOLD)
        ka, aa = win(t, A_AYUR + 0.05, G_AGNI1 - 0.2)
        text(c, "Ayurveda", W / 2, 520 + (1 - ka) * 24, "italic", 170, color=WHITE, a=aa * ka)
        text(c, "mein kehte hain...", W / 2, 620 + (1 - ka) * 24, "italic", 64, color=MUTED, a=aa * ka)
        k, a = win(t, G_AGNI1 - 0.1, G_GUT - 0.2)
        line_icon(c, "flame", W / 2, 330, 190, k=k, color=GOLD, a=a, width=1.2, glow=0.8)
        headline(c, "AGNI", W / 2, 640, 230, t, G_AGNI1 - 0.05, G_GUT - 0.2)
        k2, a2 = win(t, G_DIG - 0.1, G_GUT - 0.2)
        text(c, "digestive fire", W / 2, 760 + (1 - k2) * 16, "italic", 76, color=WHITE, a=a2 * k2)
        if t > G_GUT - 0.3:
            k3, a3 = win(t, G_GUT - 0.1, S_AGNI[1] - 0.2)
            headline(c, "Agni theek", W / 2, 330, 110, t, G_GUT - 0.1, S_AGNI[1] - 0.2, name="heavy")
            text(c, "=", W / 2, 470, "heavy", 110, color=GOLD, a=a3 * k3)
            headline(c, "Gut health theek", W / 2, 620, 110, t, G_GUT + 0.15, S_AGNI[1] - 0.2, name="heavy")
            tag(c, "SAME BAAT  ·  ALAG BHAASHA", W / 2, 760, t, G_BHASHA - 0.05, S_AGNI[1] - 0.2, size=28)


# ================================================================== FRONT
def draw_front(c, t):
    if C_COMMENT - 0.5 < t < C_YOU + 0.5:
        comment_cta(c, t, C_COMMENT - 0.4, C_YOU + 0.2, W / 2, 1290, "PART 4", C_PART4 - 0.05)


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


CAP = Captions(build_caption_groups(), y=1570, size=72)
CAP_BEHIND = Captions(CAP.groups, y=760, size=100)
for a, b in BEHIND_CAPS:
    CAP.mute(a, b)


def behind_caps(c, t):
    for a, b in BEHIND_CAPS:
        if a <= t < b:
            CAP_BEHIND.draw(c, t, y=behind_y(a, 100) - 40)


# ================================================================== compose
def draw(c, t, f):
    fi = min(f, NB - 1)
    rgba = BASE.array(fi)
    frame = skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType)
    sk = studio_k(t)
    z, ax, ay = cam(t)
    zz, axx, ayy = lerp(z, 0.8, sk), lerp(ax, 540, sk), lerp(ay, 1920, sk)
    warm = MOM[0] <= t < MOM[1] and sk < 0.5
    paint = skia.Paint(ColorFilter=WARM if warm else GRADE)
    if sk < 1:
        c.save()
        c.translate(ax, ay)
        c.scale(z, z)
        c.translate(-ax, -ay)
        c.drawImage(frame, 0, 0, SAMP, paint)
        c.restore()
    if sk > 0:
        c.saveLayerAlpha(None, int(255 * sk))
        studio_bg(c, t)
        c.restore()
    draw_stage(c, t, sk)
    if sk < 1:
        c.saveLayerAlpha(None, int(255 * (1 - sk)))
        draw_behind(c, t)
        behind_caps(c, t)
        c.restore()
    person = person_image(fi, rgba)
    c.save()
    c.translate(axx, ayy)
    c.scale(zz, zz)
    c.translate(-lerp(ax, 540, sk), -lerp(ay, 1920, sk))
    if sk > 0:
        sp = skia.Paint(ImageFilter=skia.ImageFilters.DropShadowOnly(0, 18, 26, 26, skia.Color(0, 0, 0, int(150 * sk))))
        c.drawImage(person, 0, 0, SAMP, sp)
    c.drawImage(person, 0, 0, SAMP, paint)
    c.restore()
    draw_front(c, t)
    c.drawRect(skia.Rect.MakeWH(W, H), rad_grad(W / 2, H * 0.48, H * 0.78, ["#00000000", "#00000000", "#000000"],
                                                 [0, 0.6, 1], a=0.45))
    c.drawRect(skia.Rect.MakeXYWH(0, H - 640, W, 640), lin_grad(0, H - 640, 0, H, ["#00000000", "#000000"], a=0.5))
    CAP.draw(c, t)
    if t > E["total"]:
        c.drawRect(skia.Rect.MakeWH(W, H), fill(INK, clamp((t - E["total"]) / (TAIL - 0.2))))


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


film = Film(draw, TOTAL, FPS, out_dir=HERE / "out", sheet_n=36)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "cues"
    if cmd == "cues":
        for name in ("S_AXIS", "S_AGNI", "MOM", "BEHIND_CAPS"):
            print(name, globals()[name])
        print("total", TOTAL, "sfx", len(SFX))
    elif cmd == "stills":
        film.stills([float(x) for x in sys.argv[2:]])
    elif cmd == "sheet":
        film.sheet()
    elif cmd == "render":
        film.render(HERE / "work" / "picture.mp4")
    elif cmd == "srt":
        write_srt(HERE / "out" / "captions_hinglish.srt")
        print("-> out/captions_hinglish.srt", len(CAP.groups))
