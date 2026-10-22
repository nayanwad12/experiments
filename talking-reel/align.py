"""Force-align the spoken text to the raw take, one speech island at a time.

-> work/words.json [{w, d, s, e, ph}] (raw clock, seconds; ph = island index)

The text is what was actually said: Whisper medium.en and Parakeet TDT 0.6b passes (sherpa-onnx), checked by
hand. Three spots are accent-ambiguous and were read in context: "vibe edit" (ASR: "Y-Bedded"), "the story
cut" (ASR: "the story card"), "key frames" (ASR: "three frames").
"""
import json
import re
import wave
from pathlib import Path

import numpy as np
from pocketsphinx import Decoder

HERE = Path(__file__).resolve().parent
SPOKEN = [
    "Here is what actually happens inside a vibe edit.",
    "Step by step.",
    "Step one. You drop in your raw footage.",
    "One take, mistakes and all.",
    "Step two.",
    "The system watches and listens.",
    "It transcribes every word,",
    "finds your strongest line,",
    "moves it into the front,",
    "because the first two seconds decides everything.",
    "Step three.",
    "The story cut. Pauses, ums, retakes.",
    "Gone.",
    "Down to the exact word.",
    "Step four. The look.",
    "Captions that hit on your voice.",
    "Text behind you.",
    "Your background swapped.",
    "Zooms on the lines that matters.",
    "Step five.",
    "Sound.",
    "Original music.",
    "Whooshes.",
    "Hits.",
    "Generated from scratch.",
    "So no copyright claims ever.",
    "And the step six,",
    "the part",
    "most editors never give you,",
    "which is proof.",
    "Before anything renders, it shows you the stills of every key moment.",
    "You say more energy, or cleaner, and it changes.",
    "Then one command exports",
    "it for reels,",
    "feeds, YouTube, every format.",
    "That's the vibe editing.",
    "You bring the taste.",
    "The system does the key frames.",
    "And yes, this exact video went through all six steps.",
    "So if you want to see",
    "what I actually recorded,",
]
EXTRA = {"youtube": "Y UW T UW B", "ums": "AH M Z", "whooshes": "W UW SH IH Z", "retakes": "R IY T EY K S",
         "vibe": "V AY B", "reels": "R IY L Z", "transcribes": "T R AE N S K R AY B Z"}

ph = json.loads((HERE / "work" / "phrases.json").read_text())
assert len(ph) == len(SPOKEN), (len(ph), len(SPOKEN))
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
