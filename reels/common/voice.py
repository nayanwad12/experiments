"""voice: Kokoro narration with word timings, so picture and captions can be cued to the voice.

    from voice import narrate
    vo = narrate(LINES, "work")          # LINES = [(id, text), ...] or (id, text, voice, speed)
    vo["hook"]["dur"]                    # seconds
    vo["hook"]["words"]                  # [(word, start, end), ...] seconds from the start of the line

Each line is synthesised on its own (work/vo_<id>.wav, 24 kHz mono) and cached by text+voice+speed.
Kokoro-onnx v1.0 does not report durations, so word times are aligned here: the take is split at its
pauses (RMS envelope), phrases (split at punctuation) are snapped to those pauses, and words inside a
phrase share the phrase by phoneme count. Good to a frame or two, which is plenty for captions.
"""

import hashlib
import json
import os
import re
from pathlib import Path

import numpy as np
import soundfile as sf

MODELS = os.environ.get("KOKORO_MODELS", "/home/user/models")
SR = 24000
_K = None


def _kokoro():
    global _K
    if _K is None:
        from kokoro_onnx import Kokoro
        _K = Kokoro(os.path.join(MODELS, "kokoro-v1.0.onnx"), os.path.join(MODELS, "voices-v1.0.bin"))
    return _K


LANGS = {"a": "en-us", "b": "en-gb", "h": "hi", "e": "es", "f": "fr-fr", "i": "it", "p": "pt-br", "j": "ja", "z": "cmn"}


def _lang(v):
    return LANGS.get(v.strip()[0], "en-us")


def _voice(v):
    """'af_heart' or a blend 'af_heart*0.6+af_bella*0.4' (style vectors mixed)."""
    if "+" not in v and "*" not in v:
        return v
    style = None
    for part in v.split("+"):
        name, _, w = part.partition("*")
        vec = _kokoro().get_voice_style(name.strip()) * float(w or 1)
        style = vec if style is None else style + vec
    return style


def _phon_len(word):
    w = re.sub(r"[^\w'’-]", "", word)
    if not w:
        return 1
    try:
        return max(1, len(_kokoro().tokenizer.phonemize(w, "en-us")))
    except Exception:
        return max(1, len(w))


def _trim(x, thr=0.006, pad=0.03):
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return x
    return x[max(0, idx[0] - int(pad * SR)): min(len(x), idx[-1] + int(pad * SR))]


def _speech_runs(x, thr_rel=0.06, min_gap=0.07):
    """[(start, end)] seconds of speech, split where the take goes quiet for >= min_gap."""
    hop = int(0.005 * SR)
    n = len(x) // hop
    rms = np.sqrt(np.convolve(x[: n * hop].reshape(n, hop).astype(np.float64).__pow__(2).mean(1),
                              np.ones(4) / 4, mode="same"))
    on = rms > thr_rel * rms.max()
    runs, i = [], 0
    while i < n:
        if on[i]:
            j = i
            while j < n and on[j]:
                j += 1
            runs.append([i * hop / SR, j * hop / SR])
            i = j
        else:
            i += 1
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] < min_gap:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    return merged


def align(text, x):
    words = text.split()
    if not words:
        return []
    weights = [_phon_len(w) + 1.5 for w in words]
    runs = _speech_runs(x)
    if not runs:
        runs = [[0.0, len(x) / SR]]
    s0, s1 = runs[0][0], runs[-1][1]
    gaps = [(runs[i][1], runs[i + 1][0]) for i in range(len(runs) - 1)]
    # phrase boundaries: after words ending in punctuation
    bounds = [i for i, w in enumerate(words[:-1]) if re.search(r"[,.;:!?…—-]$", w)]
    # expected time of each boundary if speech were uniform over phonemes, then snap to a pause
    tot = sum(weights)
    cuts, used = [], set()
    for b in bounds:
        frac = sum(weights[: b + 1]) / tot
        exp_t = s0 + frac * (s1 - s0)
        best, bd = None, 0.45
        for gi, (g0, g1) in enumerate(gaps):
            if gi in used:
                continue
            d = abs((g0 + g1) / 2 - exp_t)
            if d < bd:
                best, bd = gi, d
        if best is not None:
            used.add(best)
            cuts.append((b, gaps[best]))
    cuts.sort()
    # segments of words with known spans
    segs, start_w, t_start = [], 0, s0
    for b, (g0, g1) in cuts:
        segs.append((start_w, b + 1, t_start, g0))
        start_w, t_start = b + 1, g1
    segs.append((start_w, len(words), t_start, s1))
    out = []
    for a, b, ta, tb in segs:
        ws = weights[a:b]
        tt = sum(ws)
        acc = 0.0
        for k in range(a, b):
            ws_k = weights[k]
            st = ta + (tb - ta) * acc / tt
            acc += ws_k
            en = ta + (tb - ta) * acc / tt
            out.append((words[k], round(st, 3), round(en, 3)))
    return out


def narrate(lines, work="work", voice="af_heart", speed=1.0):
    """lines: [(id, text) | (id, text, voice, speed)]. Returns {id: {"file", "dur", "words", "text"}}."""
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    out = {}
    for ln in lines:
        lid, text = ln[0], ln[1]
        v = ln[2] if len(ln) > 2 and ln[2] else voice
        sp = ln[3] if len(ln) > 3 and ln[3] else speed
        spoken = ln[4] if len(ln) > 4 and ln[4] else text   # optional pronunciation override
        key = hashlib.sha1(f"{spoken}|{v}|{sp}".encode()).hexdigest()[:10]
        wav, meta = work / f"vo_{lid}.wav", work / f"vo_{lid}.json"
        if meta.exists() and json.loads(meta.read_text()).get("key") == key and wav.exists():
            out[lid] = json.loads(meta.read_text())
            continue
        a, sr = _kokoro().create(spoken, voice=_voice(v), speed=sp, lang=_lang(v))
        a = _trim(np.asarray(a, np.float32))
        sf.write(str(wav), a, sr)
        words = align(text, a)
        info = {"key": key, "file": str(wav), "dur": round(len(a) / sr, 3), "text": text, "words": words}
        meta.write_text(json.dumps(info, indent=1))
        out[lid] = info
        print(f"  vo {lid:<10} {info['dur']:.2f}s  {text}")
    return out


class Script:
    """Lays the lines out on the film's clock and answers timing questions.

        S = Script(vo, [("hook", 0.3), ("nocam", 0.25), ...])   # (id, gap before the line) or (id, "@", abs_t)
        S.t("hook")          # start of line
        S.end("hook")        # end of line
        S.w("hook", 2)       # start of the 3rd word
        S.words()            # all words on the film clock [(w, s, e, line_id)]
    """

    def __init__(self, vo, layout):
        self.vo, self.start = vo, {}
        t = 0.0
        for item in layout:
            lid = item[0]
            if len(item) == 3 and item[1] == "@":
                t = item[2]
            else:
                t += item[1]
            self.start[lid] = round(t, 3)
            t += vo[lid]["dur"]
        self.order = [i[0] for i in layout]
        self.total = t

    def t(self, lid):
        return self.start[lid]

    def end(self, lid):
        return self.start[lid] + self.vo[lid]["dur"]

    def w(self, lid, i):
        return self.start[lid] + self.vo[lid]["words"][i][1]

    def we(self, lid, i):
        return self.start[lid] + self.vo[lid]["words"][i][2]

    def find(self, lid, word):
        """start of the first word in line lid that starts with `word` (case-insensitive)."""
        for i, (w, s, e) in enumerate(self.vo[lid]["words"]):
            if re.sub(r"\W", "", w).lower().startswith(re.sub(r"\W", "", word).lower()):
                return self.start[lid] + s
        raise KeyError(f"{word!r} not in line {lid!r}")

    def words(self, skip=()):
        res = []
        for lid in self.order:
            if lid in skip:
                continue
            for w, s, e in self.vo[lid]["words"]:
                res.append((w, self.start[lid] + s, self.start[lid] + e, lid))
        return res

    def placements(self):
        return [(self.vo[lid]["file"], self.start[lid]) for lid in self.order]
