"""B2-07 Bulk videos: "I made one hundred personalised videos with one command."
One welcome-card template x a 100-row spreadsheet: a perspective wall of all 100 playing at once, the batch run in a
terminal, rows turning into videos, three full-screen heroes with their own voice (English, Hindi, Spanish), and one
card re-flowing into every format.

    python3 build.py prep | sheet | stills 4 | render | sound | all
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import skia

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(HERE))
from b2 import Reel  # noqa: E402
from kit import (W, H, INK, LIME, WHITE, Captions, Film, clamp, col, e_back, e_io, e_out, endcard, fill, hrand,  # noqa: E402
                 lerp, lin_grad, measure, prog, rrect, stroke, text)
from script import LINES, VOICE  # noqa: E402
from voice import Script, narrate  # noqa: E402

FPS, BPM = 30, 88
vo = narrate(LINES, HERE / "work", VOICE)
S = Script(vo, [("hook", "@", 0.15), ("cmd", 0.1), ("how", 0.3), ("en", 0.38), ("hi", 0.2), ("es", 0.22), ("langs", 0.28),
                ("fmt", 0.14), ("tail", 1.2), ("cta", 0.23)])
END_T = S.end("cta") + 0.45
DUR = END_T + 2.9
R = Reel(__file__, DUR, FPS)

FIRST = ["Priya", "Rahul", "Sofía", "Aarav", "Meera", "Kabir", "Ananya", "Arjun", "Isha", "Vihaan", "Zara", "Rohan",
         "Diya", "Kiara", "Aditya", "Neha", "Ishaan", "Tara", "Dev", "Riya", "Lucas", "Emma", "Mateo", "Lina", "Omar",
         "Yuki", "Chloé", "Noah", "Amara", "Leo", "Fatima", "Kenji", "Elena", "Ravi", "Sana", "Jai", "Nia", "Aisha",
         "Samar", "Maya", "Kavya", "Arnav", "Pooja", "Siddharth", "Nisha", "Varun", "Anika", "Rehan", "Simran", "Karan"]
CITIES = ["Pune", "Jaipur", "Madrid", "Mumbai", "Delhi", "Bengaluru", "Chennai", "Kolkata", "Hyderabad", "Ahmedabad",
          "Lucknow", "Indore", "Goa", "Kochi", "Dubai", "London", "Toronto", "Singapore", "Berlin", "Lisbon"]
PALS = [("#1b1f3b", "#5b3df5"), ("#0e2a2a", "#1fbf8f"), ("#2a0e1e", "#ff4f7b"), ("#231a07", "#ffb547"),
        ("#0e1a2a", "#4fb3ff"), ("#1d0e2a", "#c77dff")]
ROWS = []
for i in range(100):
    name = FIRST[i % len(FIRST)] if i < 3 else FIRST[int(hrand(i, 3) * len(FIRST))]
    city = ["Pune", "Jaipur", "Madrid"][i] if i < 3 else CITIES[int(hrand(i, 5) * len(CITIES))]
    lang = ["en", "hi", "es"][i] if i < 3 else ("hi" if hrand(i, 6) > 0.8 else "es" if hrand(i, 7) > 0.88 else "en")
    ROWS.append(dict(i=i, name=name, city=city, lang=lang, pal=PALS[i % len(PALS)], seat=f"#{i + 1:03d}"))
HERO = {"en": ROWS[0], "hi": ROWS[1], "es": ROWS[2]}
WELCOME = {"en": "Welcome,", "es": "Bienvenida,", "hi": None}
SUBS = {"hi": "Hello Rahul! Welcome to the Vibe Editing family.", "es": "Hi Sofía! Welcome to the Vibe Editing family."}
HI_PNG = {"name": HERE / "work" / "hi_name.png", "welcome": HERE / "work" / "hi_welcome.png", "city": HERE / "work" / "hi_city.png"}


def song():
    from music import lofi_trap
    return lofi_trap(DUR, BPM, "Eb", {"beat": 60 / BPM * 4}, seed=3)


def prep():
    jobs = [dict(text="राहुल", out=str(HI_PNG["name"]), size=260, color="#ffffff", weight=800),
            dict(text="स्वागत है,", out=str(HI_PNG["welcome"]), size=96, color="#ffffff", weight=800),
            dict(text="जयपुर", out=str(HI_PNG["city"]), size=64, color="#ffffff", weight=800)]
    jf = HERE / "work" / "textjobs.json"
    jf.write_text(json.dumps(jobs, ensure_ascii=False))
    subprocess.run(["node", str(HERE.parent / "textpng.mjs"), str(jf)], check=True)
    import csv
    with open(HERE / "out" / "students.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["seat", "name", "city", "lang"])
        for r in ROWS:
            w.writerow([r["seat"], r["name"], r["city"], r["lang"]])
    print("prep ok")


_IMG = {}


def img(p):
    if p not in _IMG:
        _IMG[p] = skia.Image.open(str(p))
    return _IMG[p]


# ---------------------------------------------------------------- the template (one card, any size/aspect)
def card(c, lt, row, w, h, detail=True):
    """draw a personalised welcome card in local coords (0..w, 0..h). lt = seconds into the card's own clip."""
    a, b = row["pal"]
    c.save()
    c.clipRRect(rrect(0, 0, w, h, min(w, h) * 0.06), True)
    c.drawPaint(lin_grad(0, 0, w * 0.4, h, [a, b]))
    u = min(w, h / 1.4) / 1080                                 # layout unit
    landscape = w > h * 1.2
    # soft blobs
    for k in range(3):
        x = w * (0.2 + 0.6 * hrand(row["i"], k, 1)) + 40 * u * math.sin(lt * 1.3 + k)
        y = h * (0.15 + 0.7 * hrand(row["i"], k, 2))
        c.drawCircle(x, y, 260 * u, fill(WHITE, 0.06, blur=80 * u if detail else 0))
    cx = w * (0.62 if landscape else 0.5)
    cy = h * (0.5 if landscape else 0.46)
    if detail:
        pill = "VIBE EDITING · BATCH 07"
        pw = measure(pill, "monob", 30 * u) + 60 * u
        px = (w - pw) / 2 if not landscape else 60 * u
        c.drawRRect(rrect(px, 70 * u, pw, 64 * u, 32 * u), fill("#000000", 0.25))
        text(c, pill, px + pw / 2, 113 * u, "monob", 30 * u, WHITE, 0.9)
    # welcome line
    kw = e_out(prog(lt, 0.15, 0.4))
    if row["lang"] == "hi" and row is HERO["hi"] and HI_PNG["welcome"].exists():
        im = img(HI_PNG["welcome"])
        s = 0.9 * u * (w / 1080) / u if False else u * 1.0
        iw, ih = im.width() * s, im.height() * s
        c.drawImageRect(im, skia.Rect.MakeXYWH(cx - iw / 2, cy - 330 * u - ih * 0.6 + 30 * u * (1 - kw), iw, ih),
                        skia.SamplingOptions(skia.FilterMode.kLinear), skia.Paint(Alphaf=kw))
    else:
        wl = WELCOME.get(row["lang"]) or "Welcome,"
        text(c, wl, cx, cy - 300 * u + 30 * u * (1 - kw), "medium", 70 * u, WHITE, kw * 0.85)
    # the name, letters pop in
    if row["lang"] == "hi" and row is HERO["hi"] and HI_PNG["name"].exists():
        im = img(HI_PNG["name"])
        k = e_back(prog(lt, 0.35, 0.5), 1.8)
        s = u * clamp(k + 0.001)
        iw, ih = im.width() * s, im.height() * s
        c.drawImageRect(im, skia.Rect.MakeXYWH(cx - iw / 2, cy - ih * 0.62, iw, ih), skia.SamplingOptions(skia.FilterMode.kLinear))
    else:
        name = row["name"]
        size = 200 * u
        while measure(name, "unbounded", size) > (w * (0.55 if landscape else 0.86)) and size > 60 * u:
            size *= 0.92
        tw = measure(name, "unbounded", size)
        x = cx - tw / 2
        for j, ch in enumerate(name):
            k = e_back(prog(lt, 0.35 + j * 0.05, 0.35), 2.2)
            cw = measure(ch, "unbounded", size)
            if k > 0:
                c.save()
                c.translate(x + cw / 2, cy + 40 * u)
                c.scale(clamp(k), clamp(k))
                text(c, ch, 0, 0, "unbounded", size, WHITE, 1)
                c.restore()
            x += cw
    # city + seat
    kc = e_out(prog(lt, 0.9, 0.4))
    pin_y = cy + 170 * u
    city = row["city"]
    if row is HERO["hi"] and HI_PNG["city"].exists():
        im = img(HI_PNG["city"])
        iw, ih = im.width() * u * 0.9, im.height() * u * 0.9
        c.drawImageRect(im, skia.Rect.MakeXYWH(cx - iw / 2 + 30 * u, pin_y - ih * 0.72, iw, ih), skia.SamplingOptions(),
                        skia.Paint(Alphaf=kc))
        cw = iw
    else:
        cw = measure(city, "bold", 58 * u)
        text(c, city, cx + 30 * u, pin_y, "bold", 58 * u, WHITE, kc)
    px = cx - cw / 2 - 20 * u
    c.drawCircle(px, pin_y - 26 * u, 16 * u, fill(LIME, kc))
    c.drawCircle(px, pin_y - 26 * u, 6 * u, fill(a, kc))
    if detail:
        ks = e_out(prog(lt, 1.2, 0.4))
        c.drawRRect(rrect(cx - 130 * u, pin_y + 60 * u, 260 * u, 86 * u, 43 * u), fill(LIME, ks))
        text(c, f"seat {row['seat']}", cx, pin_y + 117 * u, "monob", 38 * u, INK, ks)
        # confetti
        dt = lt - 0.55
        if dt > 0:
            for k in range(36):
                ang = hrand(row["i"], k, 7) * 6.283
                v = (500 + 700 * hrand(row["i"], k, 8)) * u
                x = cx + math.cos(ang) * v * dt
                y = cy - 60 * u + math.sin(ang) * v * dt * 0.7 + 900 * u * dt * dt
                cc = (LIME, "#FFFFFF", "#FF4F7B", "#4FE3FF", "#FFB547")[k % 5]
                c.save()
                c.translate(x, y)
                c.rotate(dt * 400 * (hrand(k, 9) - 0.5))
                c.drawRect(skia.Rect.MakeXYWH(-9 * u, -4 * u, 18 * u, 8 * u), fill(cc, clamp(1.6 - dt)))
                c.restore()
    c.restore()


# ---------------------------------------------------------------- wall of 100 in perspective
def project(p, cam, f=1500):
    x, y, z = p[0] - cam[0], p[1] - cam[1], p[2] - cam[2]
    return (W / 2 + f * x / z, H / 2 + f * y / z)


def wall(c, t, cam, yaw=0.0, lt_off=0.0, highlight=None):
    tw, th, gap = 1.0, 16 / 9, 0.12
    tiles = []
    for r in ROWS:
        i = r["i"]
        col_, row_ = i % 10, i // 10
        x0 = (col_ - 4.5) * (tw + gap)
        y0 = (row_ - 4.5) * (th + gap)
        corners = []
        for dx, dy in ((0, 0), (tw, 0), (tw, th), (0, th)):
            x, y, z = x0 + dx - tw / 2, y0 + dy - th / 2, 0.0
            xr, zr = x * math.cos(yaw) + z * math.sin(yaw), -x * math.sin(yaw) + z * math.cos(yaw)
            corners.append((xr, y, zr))
        zc = sum(p[2] for p in corners) / 4
        tiles.append((zc, r, corners))
    tiles.sort(key=lambda q: -q[0])
    src = [skia.Point(0, 0), skia.Point(216, 0), skia.Point(216, 384), skia.Point(0, 384)]
    for zc, r, corners in tiles:
        pts = [project(p, cam) for p in corners]
        if any(cam[2] >= p[2] for p in corners):
            continue
        if max(p[0] for p in pts) < -50 or min(p[0] for p in pts) > W + 50 or max(p[1] for p in pts) < -50 or min(p[1] for p in pts) > H + 50:
            continue
        m = skia.Matrix()
        if not m.setPolyToPoly(src, [skia.Point(*p) for p in pts]):
            continue
        c.save()
        c.concat(m)
        lt = (t + lt_off + hrand(r["i"], 1) * 2.7) % 3.2
        card(c, lt, r, 216, 384, detail=False)
        if highlight is not None and r["i"] in highlight:
            c.drawRRect(rrect(0, 0, 216, 384, 13), stroke(LIME, 8))
        c.restore()


# ---------------------------------------------------------------- scenes
def terminal(c, t, t0):
    a = e_out(prog(t, t0, 0.3))
    x0, y0, w, h = 60, 560, W - 120, 820
    c.drawRRect(rrect(x0, y0 + 40 * (1 - a), w, h, 30), fill("#0b0c12", 0.94 * a))
    for i, cc in enumerate(("#FF5F57", "#FEBC2E", "#28C840")):
        c.drawCircle(x0 + 44 + i * 32, y0 + 40, 10, fill(cc, a))
    cmd = "python3 batch.py students.csv"
    n = int(clamp((t - t0 - 0.1) / 0.55) * len(cmd))
    text(c, "$ " + cmd[:n], x0 + 40, y0 + 120, "monob", 38, LIME, a, anchor="l")
    done = int(clamp((t - t0 - 0.75) / 1.3) * 100)
    for j in range(max(0, done - 12), done):
        r = ROWS[j]
        y = y0 + 190 + (j - max(0, done - 12)) * 46
        text(c, f"✓ {r['seat'][1:]}-{r['name'].lower()}-{r['city'].lower()}.mp4", x0 + 40, y, "mono", 32, "#cfd3dc", a,
             anchor="l")
    bw = w - 80
    c.drawRRect(rrect(x0 + 40, y0 + h - 90, bw, 34, 17), fill("#22242e", a))
    c.drawRRect(rrect(x0 + 40, y0 + h - 90, max(34, bw * done / 100), 34, 17), fill(LIME, a))
    text(c, f"{done}/100", x0 + w - 40, y0 + h - 110, "monob", 34, WHITE, a, anchor="r")


def spreadsheet(c, t, t0, t1):
    a = e_out(prog(t, t0, 0.3)) * (1 - prog(t, t1 - 0.25, 0.25))
    x0, y0, w = 60, 300, W - 120
    rh = 62
    c.drawRRect(rrect(x0, y0, w, rh * 9 + 20, 22), fill("#f6f6f2", a))
    cols = [("seat", 0.0), ("name", 0.18), ("city", 0.52), ("lang", 0.82)]
    for name, fx in cols:
        text(c, name.upper(), x0 + 30 + fx * w, y0 + 44, "monob", 28, "#6b6b75", a, anchor="l")
    hi = int(clamp((t - t0 - 0.3) / (t1 - t0 - 0.6)) * 8)
    for j in range(8):
        r = ROWS[j]
        y = y0 + 20 + (j + 1) * rh
        if j == hi:
            c.drawRect(skia.Rect.MakeXYWH(x0 + 8, y - 6, w - 16, rh - 4), fill(LIME, 0.65 * a))
        for (name, fx) in cols:
            v = r[name] if name != "lang" else {"en": "English", "hi": "Hindi", "es": "Español"}[r["lang"]]
            text(c, str(v), x0 + 30 + fx * w, y + 38, "bold" if name == "name" else "medium", 34, INK, a, anchor="l")
    # rows become tiles
    for j in range(8):
        k = e_back(prog(t, t0 + 0.3 + j * (t1 - t0 - 0.6) / 8, 0.4), 1.6)
        if k <= 0:
            continue
        tw, th = 216, 384
        gx = 60 + (j % 4) * (tw + 24) + 6
        gy = 1000 + (j // 4) * (th + 24)
        c.save()
        c.translate(gx + tw / 2, gy + th / 2)
        c.scale(clamp(k), clamp(k))
        c.translate(-tw / 2, -th / 2)
        card(c, (t - t0 - j * 0.3) % 3.2, ROWS[j], tw, th, detail=False)
        c.restore()


def hero(c, t, lid, row):
    t0 = S.t(lid) - 0.35
    lt = t - t0
    k = e_out(prog(t, t0, 0.35))
    s = lerp(0.4, 1.0, k)
    c.save()
    c.translate(W / 2, H / 2)
    c.scale(s, s)
    c.translate(-W / 2, -H / 2)
    card(c, lt, row, W, H)
    c.restore()
    flag = {"en": "ENGLISH", "hi": "हिंदी · HINDI", "es": "ESPAÑOL"}[row["lang"]]
    if row["lang"] != "hi":
        text(c, flag, W - 60, 230, "monob", 34, WHITE, k * 0.9, anchor="r")
    else:
        text(c, "HINDI", W - 60, 230, "monob", 34, WHITE, k * 0.9, anchor="r")
    if lid in SUBS:
        sa = e_out(prog(t, S.t(lid), 0.3))
        sub = SUBS[lid]
        c.drawRRect(rrect(80, 1560, W - 160, 120, 20), fill("#000000", 0.5 * sa))
        text(c, sub, W / 2, 1636, "medium", 38, WHITE, sa)


def formats(c, t, t0):
    """the Priya card re-flows: 9:16 -> 1:1 -> 16:9."""
    seq = [(0.0, 1080, 1920, "9:16"), (0.65, 1000, 1000, "1:1"), (1.3, 1000, 562, "16:9")]
    lt = t - t0
    idx = max(i for i, s in enumerate(seq) if lt >= s[0])
    prev = seq[max(0, idx - 1)]
    cur = seq[idx]
    k = e_io(prog(lt, cur[0], 0.35)) if idx else 1
    w = lerp(prev[1], cur[1], k)
    h = lerp(prev[2], cur[2], k)
    if idx == 0:
        w, h = lerp(1080, 1000, e_io(prog(lt, 0, 0.3))), lerp(1920, 1777, e_io(prog(lt, 0, 0.3)))
    c.drawPaint(fill("#0b0b10"))
    c.save()
    c.translate((W - w) / 2, (H - h) / 2)
    card(c, 2.6, HERO["en"], w, h)
    c.restore()
    text(c, cur[3], W / 2, (H - h) / 2 - 40, "monob", 56, LIME, 1)


def draw(c, t, f):
    c.drawPaint(fill("#07070b"))
    if t < S.t("cmd"):                                            # hook: the wall
        k = e_io(prog(t, 0, S.t("cmd")))
        wall(c, t, (lerp(-1.5, 0.6, k), lerp(-1.0, 0.4, k), lerp(-9.5, -13, k)), yaw=lerp(0.5, 0.25, k))
        kk = e_back(prog(t, 0.2, 0.4), 2)
        text(c, "100", W / 2, 700, "unbounded", 300, WHITE, clamp(kk), outline=16, shadow=30)
        text(c, "VIDEOS", W / 2, 860, "unbounded", 130, LIME, clamp(kk), outline=12, shadow=30)
    elif t < S.t("how"):                                          # one command
        wall(c, t, (0.6, 0.4, -16), yaw=0.25)
        c.drawPaint(fill("#000000", 0.5))
        terminal(c, t, S.t("cmd") - 0.05)
    elif t < S.t("en") - 0.35:                                    # rows -> videos
        spreadsheet(c, t, S.t("how") - 0.1, S.t("en") - 0.35)
    elif t < S.t("langs"):                                        # three heroes
        lid = "en" if t < S.t("hi") - 0.35 else "hi" if t < S.t("es") - 0.35 else "es"
        hero(c, t, lid, HERO[lid])
    elif t < S.t("fmt") - 0.1:                                    # side by side
        for j, lid in enumerate(("en", "hi", "es")):
            k = e_out(prog(t, S.t("langs") - 0.1 + j * 0.08, 0.4))
            w, h = 330, 586
            x = 30 + j * (w + 15)
            c.save()
            c.translate(x, lerp(H, 560, k))
            card(c, 2.6, HERO[lid], w, h)
            c.restore()
    elif t < S.t("tail") - 0.2:
        formats(c, t, S.t("fmt") - 0.1)
    else:                                                         # pull back to the wall
        k = e_io(prog(t, S.t("tail") - 0.2, END_T - S.t("tail")))
        wall(c, t, (lerp(0.0, 0.8, k), lerp(0.0, 0.3, k), lerp(-4.5, -19, k)), yaw=lerp(0.0, 0.45, k),
             highlight={0, 1, 2})
    if t >= END_T:
        endcard(c, t, END_T)
    CAP.draw(c, t)


CAP = Captions(S.words(skip=("en", "hi", "es")), y=1700, size=82).mute(END_T, DUR)
CAP.mute(0, S.t("cmd"))
film = Film(draw, DUR, FPS, out_dir=HERE / "out")


def sound():
    import music as M
    from sound import Mix
    bed = song().master()
    m = Mix(DUR)
    m.voice(S.placements())
    m.music(bed, gain_db=-4, duck_db=-9, fade_out=1.5)
    m.sfx("typing", S.t("cmd") + 0.05, -12, dur=0.55, cps=40)
    for k in range(25):
        m.sfx("tick", S.t("cmd") + 0.75 + k * 0.052, -18)
    for j in range(8):
        m.sfx("pop", S.t("how") + 0.2 + j * (S.t("en") - S.t("how") - 0.25) / 8, -12)
    for lid in ("en", "hi", "es"):
        m.sfx("whoosh", S.t(lid) - 0.45, -12)
        m.sfx("sparkle", S.t(lid) + 0.2, -14)
    for k in range(3):
        m.sfx("swish", S.t("fmt") - 0.1 + k * 0.65, -10)
    m.sfx("whoosh", END_T - 0.25, -10)
    m.sfx("ding", END_T + 0.1, -12)
    m.finish(HERE / "out" / "picture.mp4", HERE / "out" / "B2_07_bulk_videos.mp4", HERE / "work")


if __name__ == "__main__":
    R.cli(film, sound, prep)
