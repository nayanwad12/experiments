"""EDL -> frame-exact timeline per part (timeline.json)."""
import json
import numpy as np
from scipy.io import wavfile
from edl import PARTS

FPS = 30
PRE, POST = 0.10, 0.16          # padding around words
QUIET_DB, MIN_PAUSE, KEEP_SIDE = -47.5, 0.45, 0.14

words = [w for sg in json.load(open("words.json")) for w in sg["words"]]
words.sort(key=lambda w: w["s"])
obs = json.load(open("obs.json"))
sr, A = wavfile.read("audio16k.wav"); A = A.astype(np.float32) / 32768
HOP = sr // 100
n = len(A) // HOP
db = 20 * np.log10(np.sqrt((A[:n * HOP].reshape(n, HOP) ** 2).mean(1)) + 1e-9)
# smooth over 30 ms so a single dip inside a word is not a "pause"
dbs = np.convolve(db, np.ones(3) / 3, mode="same")


def find(t):
    i = min(range(len(words)), key=lambda k: abs(words[k]["s"] - t))
    assert abs(words[i]["s"] - t) < 0.006, (t, words[i])
    return i


def quietest(t, lo, hi):
    """lowest-energy 10 ms hop within [t+lo, t+hi]"""
    a, b = max(0, int((t + lo) * 100)), min(n - 1, int((t + hi) * 100))
    if b <= a: return t
    return (a + int(np.argmin(dbs[a:b + 1]))) / 100


def span(r):
    if r[0] == "raw":
        return [(r[1], r[2], True)]
    i, j = find(r[0]), find(r[1])
    cap = r[2] if len(r) > 2 else None
    s = words[i]["s"] - PRE
    if i > 0: s = max(s, words[i - 1]["e"] - 0.02)
    e = words[j]["e"] + POST
    if j + 1 < len(words): e = min(e, max(words[j + 1]["s"] - 0.03, words[j]["e"] + 0.04))
    s = quietest(s, -0.03, 0.03); e = quietest(e, -0.03, 0.04)
    if cap: e = min(e, cap)
    return [(s, e, False)]


def squeeze(s, e):
    """drop the middle of every pause >= MIN_PAUSE inside [s, e]"""
    a, b = int(s * 100), int(e * 100)
    q = dbs[a:b] < QUIET_DB
    out, cur, k = [], s, 0
    while k < len(q):
        if q[k]:
            m = k
            while m < len(q) and q[m]: m += 1
            ps, pe = (a + k) / 100, (a + m) / 100
            if pe - ps >= MIN_PAUSE and ps > s + 0.05 and pe < e - 0.05:
                out.append((cur, ps + KEEP_SIDE)); cur = pe - KEEP_SIDE
            k = m
        else:
            k += 1
    out.append((cur, e))
    return out


def obs_split(s, e):
    """split [s,e) into pieces; frames inside an OBS interval (or a covered off-topic moment) show a clean frame"""
    pieces = [(s, e, None)]
    for ob in obs:
        os_, oe = ob[0], ob[1]
        nxt = []
        for ps, pe, fz in pieces:
            if fz is not None or pe <= os_ or ps >= oe:
                nxt.append((ps, pe, fz)); continue
            a, b = max(ps, os_), min(pe, oe)
            if ps < a: nxt.append((ps, a, None))
            hold = ob[2] if len(ob) > 2 else (oe + 0.1 if oe + 0.1 < pe or ps >= os_ else os_ - 0.1)
            nxt.append((a, b, round(hold, 4)))
            if b < pe: nxt.append((b, pe, None))
        pieces = nxt
    return pieces


timeline = []
for pid, title, ranges in PARTS:
    segs = []
    for r in ranges:
        for s, e, raw in span(r):
            segs += [(s, e)] if raw else squeeze(s, e)
    # merge overlaps / tiny gaps
    segs.sort()
    merged = []
    for s, e in segs:
        if merged and s - merged[-1][1] < 0.05:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    q = []
    for s, e in merged:
        fs, fe = round(s * FPS), round(e * FPS)
        if fe - fs >= 2:
            for ps, pe, fz in obs_split(fs / FPS, fe / FPS):
                a, b = round(ps * FPS), round(pe * FPS)
                if b > a: q.append(dict(f0=a, f1=b, hold=fz))
    frames = sum(x["f1"] - x["f0"] for x in q)
    timeline.append(dict(id=pid, title=title, segs=q, frames=frames))
    print(f"part {pid}: {len(q):3d} cuts  {frames / FPS / 60:5.2f} min  {title}")
    for x in q:
        if x["hold"] is not None: print("   hold", x)
print("total", round(sum(p["frames"] for p in timeline) / FPS / 60, 2), "min (raw 16.6)")
json.dump(timeline, open("timeline.json", "w"), indent=0)
