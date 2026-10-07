"""Reel 05: "I made a video game cutscene, without a game engine."
A 108x192 pixel world (each pixel = 10x10 on screen), hand-coded sprites, a 5x7 bitmap font, chiptune audio.

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
from kit import W, H, Captions, Film, clamp, e_out, endcard, fill, hrand, prog  # noqa: E402
from script import LINES, VOICE  # noqa: E402
from voice import Script, narrate  # noqa: E402

vo = narrate(LINES, HERE / "work", VOICE)
S = Script(vo, [("hook", 0.4), ("nos", 0.3), ("every", 0.35), ("ach", "@", 14.0), ("cta", 0.35)])
END_T = S.end("cta") + 0.6
DUR = END_T + 3.0
FPS = 30
PX = 10
GW, GH = W // PX, H // PX          # 108 x 192

# ---------------------------------------------------------------- timeline
WALK_T0, ARRIVE_T = 0.9, S.end("every") - 0.2
SPEED = 103 / (ARRIVE_T - WALK_T0)
CHEST_X = 117
DLG1 = (ARRIVE_T + 0.15, ARRIVE_T + 1.35, "A CHEST!?")
OPEN_T = ARRIVE_T + 1.45
DLG2 = (OPEN_T + 0.6, S.t("ach") - 0.1, "YOU GOT:\nVIBE EDITING!")
ACH_T = S.t("ach")
JUMP_T = ACH_T + 0.2
CONT_T = S.t("cta") - 0.1
COINS = [26, 42, 58, 74, 90]

# ---------------------------------------------------------------- palette
P = {k: np.array([int(v[i:i + 2], 16) for i in (1, 3, 5)], np.uint8) for k, v in {
    "K": "#1A1C2C", "S": "#C0C7D6", "s": "#7C86A0", "R": "#E34D4D", "F": "#F2C29B", "B": "#3F6FD8",
    "b": "#2A4A9A", "G": "#FFD34D", "g": "#C7951F", "L": "#6B4226", "W": "#A0612E", "w": "#7A4520",
    "D": "#2B1A12", "Y": "#FFF3A1", "V": "#8C5BFF", "v": "#5A34C8", "E": "#FFFFFF", "T": "#4BBF5E",
}.items()}

SKY = ["#2B3A67", "#3C4F8C", "#5C6FB5", "#8E8FD6", "#E8A0B4", "#FFC69A"]
SKY = [np.array([int(c[i:i + 2], 16) for i in (1, 3, 5)], np.uint8) for c in SKY]


def sprite(rows):
    return [list(r) for r in rows]


KNIGHT_TOP = [
    "....RR......",
    "...RRR......",
    "..KSSSSK....",
    ".KSSSSSSK...",
    ".KSKKKKSK...",
    ".KSFFFFSK...",
    ".KSSSSSSK...",
    "..KKSSKK....",
    ".KBBGGBBK...",
    "KSBBGGBBSK..",
    "KSBBBBBBSK..",
    ".KbBBBBbK...",
]
LEGS = {
    0: ["..KBBKBBK...", "..KbbKbbK...", "..KLLKLLK...", "..KKK.KKK..."],
    1: ["..KBBKBBK...", ".KbbK.KbbK..", ".KLLK..KLLK.", ".KKK....KKK."],
    2: ["..KBBKBBK...", "...KbbbK....", "...KLLLK....", "...KKKKK...."],
}
CHEST_C = [
    "..KKKKKKKKKK..",
    ".KWWWWWWWWWWK.",
    "KWWWWWWWWWWWWK",
    "KGGGGGGGGGGGGK",
    "KwwwwwGGwwwwwK",
    "KWWWWWGKWWWWWK",
    "KWWWWWGGWWWWWK",
    "KwwwwwwwwwwwwK",
    "KGGGGGGGGGGGGK",
    "KWWWWWWWWWWWWK",
    "KKKKKKKKKKKKKK",
]
CHEST_O = [
    ".KKKKKKKKKKKK.",
    "KWWWWWWWWWWWWK",
    "KGGGGGGGGGGGGK",
    "KDDDDDDDDDDDDK",
    "KDYYYYYYYYYYDK",
    "KwwwwwGGwwwwwK",
    "KWWWWWGKWWWWWK",
    "KwwwwwwwwwwwwK",
    "KGGGGGGGGGGGGK",
    "KWWWWWWWWWWWWK",
    "KKKKKKKKKKKKKK",
]
GEM = [
    "...KKK...",
    "..KVEVK..",
    ".KVEVVvK.",
    "KVVVVVvvK",
    ".KvVVvvK.",
    "..KvvvK..",
    "...KvK...",
    "....K....",
]
TROPHY = [
    "KKKKKKKKK",
    "KGGGYGGGK",
    "GKGGYGGKG",
    "GKGGGGGKG",
    ".KGGGGGK.",
    "..KGGGK..",
    "...KgK...",
    "..KgggK..",
    ".KKKKKKK.",
]
COIN = [".KKK.", "KGYGK", "KGYGK", "KGgGK", ".KKK."]
HEART = [".K.K.", "KRKRK", "KRRRK", ".KRK.", "..K.."]

FONT = {
    "A": ".###.#...##...#######...##...##...#", "B": "####.#...##...#####.#...##...#####.",
    "C": ".###.#...##....#....#....#...#.###.", "D": "####.#...##...##...##...##...#####.",
    "E": "######....#....####.#....#....#####", "F": "######....#....####.#....#....#....",
    "G": ".###.#...##....#.####...##...#.####", "H": "#...##...##...#######...##...##...#",
    "I": ".###...#....#....#....#....#...###.", "J": "..###...#....#....#....#.#..#..##..",
    "K": "#...##..#.#.#..##...#.#..#..#.#...#", "L": "#....#....#....#....#....#....#####",
    "M": "#...###.###.#.##.#.##...##...##...#", "N": "#...##...###..##.#.##..###...##...#",
    "O": ".###.#...##...##...##...##...#.###.", "P": "####.#...##...#####.#....#....#....",
    "Q": ".###.#...##...##...##.#.##..#..##.#", "R": "####.#...##...#####.#.#..#..#.#...#",
    "S": ".#####....#.....###.....#....#####.", "T": "#####..#....#....#....#....#....#..",
    "U": "#...##...##...##...##...##...#.###.", "V": "#...##...##...##...##...#.#.#...#..",
    "W": "#...##...##...##.#.##.#.##.#.#.#.#.", "X": "#...##...#.#.#...#...#.#.#...##...#",
    "Y": "#...##...#.#.#...#....#....#....#..", "Z": "#####....#...#...#...#...#....#####",
    "0": ".###.#...##..###.#.###..##...#.###.", "1": "..#...##....#....#....#....#...###.",
    "2": ".###.#...#....#...#...#...#...#####", "3": "####.....#....#.###.....#....#####.",
    "4": "...#...##..#.#.#..#.#####...#....#.", "5": "######....####.....#....##...#.###.",
    "6": ".###.#....#....####.#...##...#.###.", "7": "#####....#...#...#...#....#....#...",
    "8": ".###.#...##...#.###.#...##...#.###.", "9": ".###.#...##...#.####....#....#.###.",
    "!": "..#....#....#....#....#.........#..", ".": "................................#..",
    ":": "......#..............#.............", "?": ".###.#...#....#...#...#.........#..",
    "-": "................###................", ">": ".#.....#.....#.....#...#...#...#...",
    "'": "..#....#.........................", ",": "...........................#...#...",
    " ": "." * 35,
}


def blit(img, spr, x, y, flip=False, scale=1):
    h = len(spr)
    for j, row in enumerate(spr):
        r = row[::-1] if flip else row
        for i, ch in enumerate(r):
            if ch == ".":
                continue
            for sy in range(scale):
                for sx in range(scale):
                    xx, yy = x + i * scale + sx, y + j * scale + sy
                    if 0 <= xx < GW and 0 <= yy < GH:
                        img[yy, xx] = P[ch]
    return h


def rect(img, x0, y0, x1, y1, c):
    x0, y0, x1, y1 = max(0, int(x0)), max(0, int(y0)), min(GW, int(x1)), min(GH, int(y1))
    if x1 > x0 and y1 > y0:
        img[y0:y1, x0:x1] = c


def ptext(img, s, x, y, c, scale=1, n=None):
    """5x7 bitmap text; n = number of characters shown (typewriter)."""
    cx = x
    shown = 0
    for line in s.split("\n"):
        cx = x
        for ch in line:
            if n is not None and shown >= n:
                return
            g = FONT.get(ch, FONT[" "])
            g = g.ljust(35, ".")
            for j in range(7):
                for i in range(5):
                    if g[j * 5 + i] == "#":
                        rect(img, cx + i * scale, y + j * scale, cx + (i + 1) * scale, y + (j + 1) * scale, c)
            cx += 6 * scale
            shown += 1
        y += 9 * scale


def text_w(s, scale=1):
    return max(len(line) for line in s.split("\n")) * 6 * scale - scale


# ---------------------------------------------------------------- world
GROUND = 150


def hero_x(t):
    if t < WALK_T0:
        return -14 + (t / WALK_T0) * 14 * 0
    return min(-12 + (t - WALK_T0) * SPEED + 0, 103)


def world(t):
    img = np.zeros((GH, GW, 3), np.uint8)
    tq = math.floor(t * 12) / 12
    hx = hero_x(t) if t >= WALK_T0 else -12
    hx = -12 + max(0, (t - WALK_T0)) * SPEED
    hx = min(hx, 103)
    cam = clamp(hx - 40, 0, 44)
    # sky bands with dithered edges
    bands = [0, 30, 55, 75, 92, 104, 118]
    for i in range(len(SKY)):
        img[bands[i]:bands[i + 1]] = SKY[i]
        if i + 1 < len(SKY):
            y = bands[i + 1]
            for x in range(0, GW, 2):
                img[y - 1, x + (y % 2)] = SKY[i + 1] if x + (y % 2) < GW else img[y - 1, 0]
                if x + 1 - (y % 2) < GW:
                    img[y, x + 1 - (y % 2)] = SKY[i]
    for i in range(26):
        if hrand(i, int(tq * 3)) > 0.25:
            img[int(hrand(i, 2) * 50), int(hrand(i, 1) * GW)] = P["E"]
    # sun
    for yy in range(-9, 10):
        half = int(math.sqrt(max(0, 81 - yy * yy)))
        y = 100 + yy
        if y < 118:
            img[y, max(0, 78 - half): min(GW, 78 + half + 1)] = P["G"] if yy < 2 else P["Y"]
    # clouds
    for i, (x0, y) in enumerate(((10, 40), (60, 25), (95, 55))):
        x = int((x0 + tq * 2 - cam * 0.15) % 140 - 20)
        rect(img, x, y, x + 18, y + 3, P["E"])
        rect(img, x + 4, y - 2, x + 12, y, P["E"])
        rect(img, x + 2, y + 3, x + 16, y + 4, np.array([200, 205, 235], np.uint8))
    # mountains (parallax 0.3)
    mx = cam * 0.3
    for i, (px, ph, c1, c2) in enumerate(((10, 38, "#4B3F7A", "#6A5CA8"), (60, 46, "#3F3570", "#5B4E9A"),
                                          (110, 34, "#4B3F7A", "#6A5CA8"), (150, 42, "#3F3570", "#5B4E9A"))):
        cx = px - mx
        for y in range(118 - ph, 122):
            half = int((y - (118 - ph)) * 1.1)
            x0, x1 = int(cx - half), int(cx + half)
            col1 = np.array([int(c1[k:k + 2], 16) for k in (1, 3, 5)], np.uint8)
            col2 = np.array([int(c2[k:k + 2], 16) for k in (1, 3, 5)], np.uint8)
            rect(img, x0, y, cx, y + 1, col2)
            rect(img, cx, y, x1, y + 1, col1)
            if y < 118 - ph + 5:
                rect(img, x0, y, x1, y + 1, P["E"])
    # far pines (parallax 0.6)
    tx = cam * 0.6
    for i in range(16):
        cx = int(i * 11 - tx + 4 * hrand(i, 7))
        top = 108 + int(8 * hrand(i, 8))
        for y in range(top, 132):
            half = (y - top) // 2 % 4 + (y - top) // 6
            rect(img, cx - half, y, cx + half + 1, y + 1, np.array([38, 92, 70], np.uint8))
    # ground
    rect(img, 0, 128, GW, GH, np.array([75, 160, 80], np.uint8))
    for x in range(0, GW):
        wx = x + int(cam)
        if (wx * 7) % 5 == 0:
            img[128, x] = np.array([110, 200, 100], np.uint8)
            img[127, x] = np.array([110, 200, 100], np.uint8)
    rect(img, 0, 138, GW, 160, np.array([196, 160, 104], np.uint8))           # dirt path
    for i in range(40):
        x = int((hrand(i, 1) * 200 - cam) % 200) - 40
        y = 140 + int(hrand(i, 2) * 18)
        rect(img, x, y, x + 2, y + 1, np.array([160, 124, 76], np.uint8))
    rect(img, 0, 160, GW, GH, np.array([62, 140, 70], np.uint8))
    for i in range(60):
        x = int((hrand(i, 3) * 300 - cam) % 300) - 60
        y = 162 + int(hrand(i, 4) * 28)
        rect(img, x, y, x + 1, y + 2, np.array([95, 185, 95], np.uint8))
    # coins + score
    score = 0
    for i, cxw in enumerate(COINS):
        got_t = WALK_T0 + (cxw - 4 + 12) / SPEED
        sx = int(cxw - cam)
        if t < got_t:
            bob = int(2 * math.sin(tq * 6 + i))
            frame = int(tq * 8 + i) % 4
            spr = COIN if frame != 2 else [r[1:4] for r in COIN]
            blit(img, spr, sx + (0 if frame != 2 else 1), GROUND - 22 + bob)
        else:
            score += 100
            k = t - got_t
            if k < 0.5:
                ptext(img, "+100", sx - 8, GROUND - 30 - int(k * 20), P["Y"])
    # chest
    chx = int(CHEST_X - cam)
    opened = t >= OPEN_T
    if opened:
        # light rays
        k = clamp((t - OPEN_T) / 0.4)
        for r in range(8):
            a = r * math.pi / 4 + tq * 0.8
            for d in range(4, int(40 * k)):
                x = int(chx + 7 + d * math.cos(a))
                y = int(GROUND - 8 + d * math.sin(a) * 0.9)
                if 0 <= x < GW and 0 <= y < GH and (d + r) % 2 == 0 and y < GROUND:
                    img[y, x] = P["Y"]
    blit(img, CHEST_O if opened else CHEST_C, chx, GROUND - 11)
    if opened:
        rise = clamp((t - OPEN_T) / 0.7)
        gy = int(GROUND - 14 - 26 * e_out(rise) + 2 * math.sin(tq * 5))
        blit(img, GEM, chx + 2, gy)
        for i in range(6):
            a = tq * 3 + i
            x, y = int(chx + 6 + 12 * math.cos(a)), int(gy + 4 + 10 * math.sin(a * 1.3))
            if 0 <= x < GW and 0 <= y < GH and hrand(i, int(tq * 12)) > 0.4:
                img[y, x] = P["E"]
    # hero
    sx = int(hx - cam)
    walking = WALK_T0 <= t < ARRIVE_T
    leg = LEGS[(int(tq * 8) % 2) if walking else 0]
    jump = 0
    if t >= JUMP_T:
        ph = (t - JUMP_T) % 0.9
        if ph < 0.5:
            jump = int(14 * math.sin(math.pi * ph / 0.5))
            leg = LEGS[2]
    bob = 1 if walking and int(tq * 8) % 2 else 0
    blit(img, KNIGHT_TOP + leg, sx, GROUND - 16 - bob - jump)
    return img, score, sx


def box(img, x0, y0, x1, y1):
    rect(img, x0, y0, x1, y1, P["K"])
    rect(img, x0 + 1, y0 + 1, x1 - 1, y1 - 1, P["E"])
    rect(img, x0 + 2, y0 + 2, x1 - 2, y1 - 2, np.array([28, 32, 60], np.uint8))


def overlays(img, t, score):
    tq = math.floor(t * 30) / 30
    rect(img, 0, 30, GW, 45, P["K"])
    ptext(img, f"SCORE {score:06d}", 4, 34, P["E"])
    for i in range(3):
        blit(img, HEART, GW - 7 - i * 7, 34)
    # title card at the start
    if t < S.t("nos") - 0.2:
        k = clamp((t - 0.05) / 0.35)
        if k > 0:
            ptext(img, "PROMPT", (GW - text_w("PROMPT", 2)) // 2, 52 - int(30 * (1 - e_out(k))), P["G"], 2)
            ptext(img, "QUEST", (GW - text_w("QUEST", 2)) // 2, 72 - int(30 * (1 - e_out(k))), P["E"], 2)
        if int(t * 2.5) % 2 == 0 and t > 0.5:
            ptext(img, "PRESS START", (GW - text_w("PRESS START")) // 2, 91, P["E"])
    for (t0, t1, msg) in (DLG1, DLG2):
        if t0 <= t < t1:
            box(img, 3, 152, GW - 3, 186)
            n = int((tq - t0) * 22)
            ptext(img, msg, 9, 159, P["E"] if "GOT" not in msg else P["Y"], 1, n)
            if n > len(msg) and int(t * 3) % 2 == 0:
                rect(img, GW - 12, 178, GW - 7, 180, P["E"])
    if t >= ACH_T:
        k = e_out(clamp((t - ACH_T) / 0.35))
        y0 = int(-40 + 88 * k)
        box(img, 4, y0, GW - 4, y0 + 36)
        blit(img, TROPHY, 7, y0 + 9, scale=2)
        ptext(img, "ACHIEVEMENT", 30, y0 + 6, P["G"])
        ptext(img, "UNLOCKED!", 30, y0 + 15, P["E"])
        ptext(img, "VIBE EDITING", 30, y0 + 25, np.array([170, 255, 120], np.uint8))
    if t >= CONT_T:
        box(img, 3, 152, GW - 3, 186)
        ptext(img, "CONTINUE?", 9, 159, P["E"])
        if int(t * 3) % 2 == 0:
            ptext(img, ">", 9, 172, P["G"])
        ptext(img, "FOLLOW", 17, 172, P["G"])


_SCAN = None
ZPX, ZW, ZH, ZY0 = 15, 72, 128, 50
KEY = np.array([255, 0, 255], np.uint8)


def draw(c, t, f):
    global _SCAN
    if t < END_T:
        img, score, hsx = world(t)
        # the world is shown 1.5x closer (each world pixel = 15x15), following the hero
        x0 = int(clamp(hsx - 24, 0, GW - ZW))
        crop = img[ZY0:ZY0 + ZH, x0:x0 + ZW]
        big = np.repeat(np.repeat(crop, ZPX, 0), ZPX, 1)
        rgba = np.dstack([big, np.full(big.shape[:2], 255, np.uint8)])
        c.drawImage(skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType), 0, 0)
        # UI layer at the finer 10x10 grid, keyed on magenta
        ov = np.zeros((GH, GW, 3), np.uint8)
        ov[:] = KEY
        overlays(ov, t, score)
        mask = np.any(ov != KEY, axis=2)
        bigo = np.repeat(np.repeat(ov, PX, 0), PX, 1)
        bigm = np.repeat(np.repeat(mask, PX, 0), PX, 1)
        rgba = np.dstack([bigo, (bigm * 255).astype(np.uint8)])
        rgba[~bigm] = 0
        c.drawImage(skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType), 0, 0)
        # CRT: scanlines + soft vignette
        if _SCAN is None:
            rec = skia.PictureRecorder()
            cc = rec.beginRecording(skia.Rect.MakeWH(W, H))
            p = fill("#000000", 0.13)
            for y in range(0, H, ZPX):
                cc.drawRect(skia.Rect.MakeXYWH(0, y + ZPX - 4, W, 4), p)
            vg = skia.GradientShader.MakeRadial(skia.Point(W / 2, H / 2), 1150,
                                                [skia.Color(0, 0, 0, 0), skia.Color(0, 0, 0, 0),
                                                 skia.Color(0, 0, 0, 110)], [0, 0.7, 1])
            cc.drawPaint(skia.Paint(Shader=vg))
            _SCAN = rec.finishRecordingAsPicture()
        c.drawPicture(_SCAN)
        # power-on at the very start
        k = clamp(t / 0.35)
        if k < 1:
            c.drawRect(skia.Rect.MakeWH(W, H * (1 - k) / 2), fill("#000000"))
            c.drawRect(skia.Rect.MakeLTRB(0, H - H * (1 - k) / 2, W, H), fill("#000000"))
        # white flash when the chest opens
        fl = math.exp(-max(0, t - OPEN_T) * 9) * (t >= OPEN_T)
        if fl > 0.03:
            c.drawPaint(fill("#FFFFFF", 0.7 * fl))
    else:
        endcard(c, t, END_T)
    CAP.draw(c, t)


CAP = Captions(S.words(), y=1010, size=82, box=True)
CAP.mute(S.t("ach") - 0.1, DUR)
film = Film(draw, DUR, FPS, out_dir=HERE / "out")


# ---------------------------------------------------------------- chiptune
def sound():
    import audio_kit as ak
    from sound import Mix
    SR = ak.SR
    m = Mix(DUR)
    m.voice(S.placements())

    def sq(f, dur, duty=0.5, vol=0.3):
        n = int(dur * SR)
        ph = (np.arange(n) * f / SR) % 1.0
        x = np.where(ph < duty, 1.0, -1.0).astype(np.float32)
        env = np.clip(np.arange(n) / (0.004 * SR), 0, 1) * np.clip((n - np.arange(n)) / (0.02 * SR), 0, 1)
        return vol * x * env * np.exp(-np.arange(n) / SR * 1.5)

    def tri(f, dur, vol=0.4):
        n = int(dur * SR)
        ph = (np.arange(n) * f / SR) % 1.0
        x = (4 * np.abs(ph - 0.5) - 1).astype(np.float32)
        return vol * x * np.clip((n - np.arange(n)) / (0.01 * SR), 0, 1)

    def nz(dur, vol=0.25, decay=30):
        n = int(dur * SR)
        rng = np.random.default_rng(1)
        x = np.repeat(rng.choice([-1.0, 1.0], n // 20 + 1), 20)[:n].astype(np.float32)
        return vol * x * np.exp(-np.arange(n) / SR * decay)

    hz = lambda mn: 440 * 2 ** ((mn - 69) / 12)  # noqa: E731
    bpm = 140
    beat = 60 / bpm
    music = np.zeros((int(DUR * SR), 2), np.float32)
    prog_ = [(60, [0, 4, 7]), (67, [0, 4, 7]), (69, [0, 3, 7]), (65, [0, 4, 7])]   # C G Am F
    melody = [76, 79, 81, 79, 76, 74, 72, 74, 76, 76, 79, 84, 81, 79, 76, 74]
    end_music = OPEN_T - 0.05
    t = 0.0
    bar = 0
    while t < END_T + 2.5:
        root, ch = prog_[bar % 4]
        for i in range(8):                                    # arpeggio
            tt = t + i * beat / 2
            if tt >= end_music and tt < ACH_T:
                continue
            nt = root + ch[i % 3] + 12 * (i // 3 % 2)
            ak.place(music, sq(hz(nt), beat / 2 * 0.9, 0.25, 0.10), tt, 0, pan=-0.3)
        for i in range(4):                                    # bass
            tt = t + i * beat
            if tt >= end_music and tt < ACH_T:
                continue
            ak.place(music, tri(hz(root - 24), beat * 0.9, 0.35), tt)
            ak.place(music, nz(0.08 if i % 2 else 0.03, 0.18 if i % 2 else 0.12, 30 if i % 2 else 80), tt)
            ak.place(music, nz(0.02, 0.06, 120), tt + beat / 2)
        if bar >= 1:                                          # lead melody
            for i in range(4):
                tt = t + i * beat
                if tt >= end_music and tt < ACH_T:
                    continue
                ak.place(music, sq(hz(melody[(bar * 4 + i) % 16]), beat * 0.85, 0.5, 0.09), tt, 0, pan=0.25)
        t += 4 * beat
        bar += 1
    m.music(music, gain_db=-8, duck_db=-7)

    # sfx
    def blip(f=880, d=0.05, v=0.25):
        return sq(f, d, 0.5, v)

    def coin():
        return np.concatenate([sq(hz(83), 0.06, 0.5, 0.3), sq(hz(88), 0.18, 0.5, 0.3)])

    def fanfare():
        notes = [72, 76, 79, 84, 79, 84]
        durs = [0.1, 0.1, 0.1, 0.25, 0.1, 0.5]
        return np.concatenate([sq(hz(n), d, 0.5, 0.3) + tri(hz(n - 12), d, 0.2) for n, d in zip(notes, durs)])

    def jump():
        n = int(0.18 * SR)
        f = np.linspace(300, 900, n)
        return 0.25 * np.where((np.cumsum(f) / SR) % 1 < 0.5, 1.0, -1.0).astype(np.float32) * np.exp(-np.arange(n) / SR * 8)

    m.sfx(sq(hz(60), 0.12, 0.5, 0.3), 0.05, -6)
    m.sfx(sq(hz(72), 0.2, 0.5, 0.3), 0.18, -6)
    for cxw in COINS:
        m.sfx(coin(), WALK_T0 + (cxw - 4 + 12) / SPEED, -8)
    for t0, t1, msg in (DLG1, DLG2):
        for i in range(len(msg)):
            if msg[i] not in " \n":
                m.sfx(blip(660 + 110 * (i % 3), 0.035, 0.2), t0 + i / 22, -14)
    m.sfx(nz(0.3, 0.3, 10), OPEN_T - 0.05, -10)
    m.sfx(fanfare(), OPEN_T + 0.05, -4)
    for k in range(4):
        m.sfx(jump(), JUMP_T + k * 0.9, -12)
    m.sfx(fanfare(), ACH_T, -8)
    m.sfx(blip(1320, 0.08, 0.3), CONT_T, -8)
    m.sfx("whoosh", END_T - 0.25, -10)
    m.sfx("ding", END_T + 0.1, -12)
    m.finish(HERE / "out" / "picture.mp4", HERE / "out" / "05_pixel_cutscene.mp4", HERE / "work")


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
