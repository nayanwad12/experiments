"""cut: the edit decision list, shared by edit.py and compare.py.

Every pause between phrases is cut down to a breath, the three false starts are removed
("Put the ti-", "And it's sh-", "So what do you need actually"), and the raw clock is mapped to the output clock.
"""

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
FPS = 30
ALL = json.loads((HERE / "work" / "words.json").read_text())
CUT_AT = {25.95: "false start: \"Put the ti-\"", 40.76: "false start: \"And it's sh-\"",
          54.0: "retake: \"So what do you need actually\""}     # raw start of each phrase that goes
CUT_SEGS = {}
for _k in sorted({w["seg"] for w in ALL}):
    _s = min(w["s"] for w in ALL if w["seg"] == _k)
    for _t, _why in CUT_AT.items():
        if abs(_s - _t) < 0.15:
            CUT_SEGS[_k] = _why
assert len(CUT_SEGS) == len(CUT_AT), CUT_SEGS
WORDS = [w for w in ALL if w["seg"] not in CUT_SEGS]
for i, w in enumerate(WORDS):
    w["i"] = i
    w["k"] = re.sub(r"[^a-z0-9']", "", w["w"].lower())

PRE, POST = 0.07, 0.11          # breath kept before / after each run of speech
JOIN = PRE + POST + 0.14        # a cut has to save at least 0.14 s, otherwise the gap stays
HOLD = {}                       # word index -> seconds of room after it (held on a still frame if the take has none)
TAIL = 79.95                    # where the last run ends on the raw clock


def _find(seq, n=1):
    toks = re.sub(r"[^a-z0-9' ]", "", seq.lower()).split()
    hits = 0
    for i in range(len(WORDS) - len(toks) + 1):
        if all(WORDS[i + j]["k"] == toks[j] for j in range(len(toks))):
            hits += 1
            if hits == n:
                return i, i + len(toks) - 1
    raise KeyError(seq)


def set_hold(seq, sec):
    HOLD[_find(seq)[1]] = sec


set_hold("and it builds it", 0.40)         # the music drop lands here
set_hold("right on your laptop", 0.15)


def build_edl():
    """[(src_a, src_b, out_a, dur)]: play segments (dur = b - a) and freezes (a == b)."""
    runs = []
    for w in WORDS:
        if runs and w["s"] - runs[-1][1] < JOIN and runs[-1][3] not in HOLD:
            runs[-1][1] = max(runs[-1][1], w["e"])
            runs[-1][3] = w["i"]
        else:
            runs.append([w["s"], w["e"], w["i"], w["i"]])
    edl, t = [], 0.0
    for k, (a, b, i0, i1) in enumerate(runs):
        prev_e = runs[k - 1][1] if k else 0.0
        nxt = runs[k + 1][0] if k + 1 < len(runs) else TAIL + 1
        a = max(a - PRE, (prev_e + a) / 2, 0.0)
        hold = HOLD.get(i1, 0.0)
        want = b + POST + hold
        b = TAIL if k + 1 == len(runs) else min(want, nxt - 0.03)
        edl.append((a, b, t, b - a))
        t += b - a
        if want - b > 0.05 and k + 1 < len(runs):          # no room in the take: hold the last frame
            edl.append((b, b, t, want - b))
            t += want - b
    return edl, t


EDL, SPEECH_END = build_edl()
PLAYS = [s for s in EDL if s[3] > 0 and s[1] > s[0]]
FREEZES = [s for s in EDL if s[1] == s[0]]


def src_at(t):
    """output time -> raw time."""
    for a, b, o, d in EDL:
        if t < o + d:
            return a + (t - o) if b > a else a
    return EDL[-1][1]


def out_of(ts):
    for a, b, o, d in PLAYS:
        if a - 1e-6 <= ts <= b + 1e-6:
            return o + ts - a
    best = min(PLAYS, key=lambda s: min(abs(ts - s[0]), abs(ts - s[1])))
    return best[2] + min(max(ts - best[0], 0), best[1] - best[0])


for w in WORDS:
    w["os"], w["oe"] = out_of(w["s"]), out_of(w["e"])

CUT_TIMES = [s[2] for s in PLAYS[1:]]      # output times where a jump cut happens


def removed():
    """[(raw_a, raw_b, why)] every stretch of the raw take that is not in the edit."""
    out, prev = [], 0.0
    for a, b, o, d in PLAYS:
        if a - prev > 0.01:
            why = "pause"
            for k, v in CUT_SEGS.items():
                seg = [w for w in ALL if w["seg"] == k]
                if seg and prev - 0.05 <= seg[0]["s"] and seg[-1]["e"] <= a + 0.05:
                    why = v
            out.append((prev, a, why))
        prev = b
    return out


class P:
    """a spoken phrase on the output clock: P('cut the pauses').s / .e / .w(j) / .we(j)"""

    def __init__(self, seq, n=1):
        self.i0, self.i1 = _find(seq, n)
        self.s, self.e = WORDS[self.i0]["os"], WORDS[self.i1]["oe"]

    def w(self, j):
        return WORDS[self.i0 + j]["os"]

    def we(self, j):
        return WORDS[self.i0 + j]["oe"]


if __name__ == "__main__":
    print(f"raw {ALL[-1]['e']:.2f}s of speech -> {SPEECH_END:.2f}s, {len(PLAYS)} runs, {len(CUT_TIMES)} cuts")
    for a, b, o, d in EDL:
        ws = [w for w in WORDS if a <= w["s"] < b]
        print(f"out {o:6.2f}-{o + d:6.2f}  raw {a:6.2f}-{b:6.2f}  " + (" ".join(w["d"] for w in ws) or "[hold]"))
    print("\nremoved:")
    tot = 0
    for a, b, why in removed():
        tot += b - a
        print(f"  raw {a:6.2f}-{b:6.2f} ({b - a:4.2f}s) {why}")
    print(f"total removed {tot:.2f}s")
