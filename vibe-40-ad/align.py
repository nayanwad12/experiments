"""Force-align the spoken text to the raw take, one speech island at a time.

-> work/words.json [{w, d, s, e, ph}] (raw clock, seconds; ph = island index)

The text is what was actually said: Whisper medium.en and Parakeet TDT 0.6b passes (sherpa-onnx), checked by
hand ("did" heard as "dead" / "vibrating system" by Whisper; "changed" per Parakeet).
"""
import json
import re
import wave
from pathlib import Path

import numpy as np
from pocketsphinx import Decoder

HERE = Path(__file__).resolve().parent
SPOKEN = [
    "The video you are watching right now,",
    "I didn't edit it. My Vibe Editing System did.",
    "I recorded one take on my phone.",
    "Pauses, mistakes, everything.",
    "Then I told it what I want in simple words.",
    "It cut every pause down to the exact word.",
    "It added these captions.",
    "Put text behind me,",
    "and changed my background.",
    "Even the music and sound effects, made from scratch. No copyright.",
    "And before exporting, it showed me every key moment.",
    "One command, and it's ready for every platform.",
    "No timeline, no editing app,",
    "just my system.",
    "So if you want to learn my system,",
    "tap the link below.",
]
EXTRA = {"youtube": "Y UW T UW B", "ums": "AH M Z", "whooshes": "W UW SH IH Z", "retakes": "R IY T EY K S",
         "vibe": "V AY B", "workflow": "W ER K F L OW", "reels": "R IY L Z", "transcribes": "T R AE N S K R AY B Z"}

ph = json.loads((HERE / "work" / "phrases.json").read_text())
ph = ph[:len(SPOKEN)]                     # the last island (39.3 s, a breath/noise) is not speech: cut
with wave.open(str(HERE / "work" / "audio16k.wav")) as w:
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16)
SR = 16000
out = []
for k, (p, text) in enumerate(zip(ph, SPOKEN)):
    disp = re.findall(r"[A-Za-z0-9'.,?]+", text)
    toks = [re.sub(r"[^a-z0-9']", "", x.lower()) for x in disp]
    d = Decoder(samprate=SR, beam=1e-80, pbeam=1e-80, wbeam=1e-60)
    for tk in set(toks):
        if tk in EXTRA and d.lookup_word(tk) is None:
            d.add_word(tk, EXTRA[tk], True)
        elif d.lookup_word(tk) is None:
            print("OOV", tk)
    s0 = max(0.0, p["s"] - 0.15)
    s1 = p["e"] + 0.15
    d.set_align_text(" ".join(toks))
    d.start_utt()
    d.process_raw(a[int(s0 * SR):int(s1 * SR)].tobytes(), full_utt=True)
    d.end_utt()
    segs = [e for e in d.seg() if e.word not in ("<s>", "</s>", "<sil>", "[NOISE]") and not e.word.startswith("++")]
    if len(segs) < len(toks) and [re.sub(r"\(\d+\)$", "", e.word) for e in segs] == toks[:len(segs)]:
        # the tail word(s) were dropped by the decoder: keep the aligned ones, the rest run to the island end
        last = s0 + (segs[-1].end_frame + 1) / 100
        rest = len(toks) - len(segs)
        for e, dw, tk in zip(segs, disp, toks):
            out.append(dict(w=tk, d=dw, s=round(s0 + e.start_frame / 100, 3), e=round(s0 + (e.end_frame + 1) / 100, 3),
                            ph=k))
        if p["e"] + 0.05 - last < 0.12:                  # no room left: the previous word swallowed it
            prev = out[-1]
            last = round((prev["s"] + prev["e"]) / 2, 3)
            p = dict(p, e=prev["e"] - 0.05)
            prev["e"] = last
        for j in range(rest):
            a0 = last + (p["e"] + 0.05 - last) * j / rest
            a1 = last + (p["e"] + 0.05 - last) * (j + 1) / rest
            out.append(dict(w=toks[len(segs) + j], d=disp[len(segs) + j], s=round(a0, 3), e=round(a1, 3), ph=k))
        print("tail fill", k, toks[len(segs):])
        continue
    if len(segs) != len(toks):
        print("ALIGN FAIL", k, text, [e.word for e in segs])
        # fall back: spread words evenly over the island
        n = len(toks)
        for j, dw in enumerate(disp):
            out.append(dict(w=toks[j], d=dw, s=round(p["s"] + (p["e"] - p["s"]) * j / n, 3),
                            e=round(p["s"] + (p["e"] - p["s"]) * (j + 1) / n, 3), ph=k))
        continue
    for e, dw, tk in zip(segs, disp, toks):
        out.append(dict(w=tk, d=dw, s=round(s0 + e.start_frame / 100, 3), e=round(s0 + (e.end_frame + 1) / 100, 3),
                        ph=k))
(HERE / "work" / "words.json").write_text(json.dumps(out, indent=0))
cur = -1
for o in out:
    if o["ph"] != cur:
        cur = o["ph"]
        print(f"\n[{cur:2d}] ", end="")
    print(f"{o['d']}({o['s']:.2f}-{o['e']:.2f}) ", end="")
print()
