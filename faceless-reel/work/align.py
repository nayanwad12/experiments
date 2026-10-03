"""Forced-align the narration script (pocketsphinx) -> words.json [{w,s,e}]. Segments come from silencedetect."""
import json, re
import numpy as np
from pocketsphinx import Decoder
from scipy.io import wavfile

SEGS = [  # (start, end, text) — speech islands between pauses
 (0.08, 1.77, "It's one fourteen A M."),
 (1.96, 4.23, "Still editing one reel."),
 (4.67, 6.84, "Cuts here. Captions there."),
 (7.02, 8.75, "Keyframes everywhere."),
 (9.33, 10.11, "So I stopped."),
 (10.95, 12.33, "Meet Vibe Editing."),
 (12.85, 14.86, "One reel. Six hours."),
 (15.24, 15.73, "Ugh."),
 (16.43, 17.68, "Now take out the cutting."),
 (17.97, 21.03, "The captions. The zooms. The sound effects."),
 (21.54, 22.41, "Twelve minutes."),
 (22.71, 23.24, "Nice."),
 (23.78, 25.81, "Just type what you want. Hit enter."),
 (26.23, 26.96, "Every night."),
 (27.23, 27.97, "Before chai."),
 (28.52, 29.01, "Posted."),
 (29.51, 31.42, "Fewer clicks. More posts."),
 (31.86, 32.87, "Vibe Editing."),
 (33.32, 33.56, "Oh."),
 (33.86, 34.80, "And this whole video?"),
 (35.21, 36.22, "Made with AI."),
 (36.83, 37.97, "Comment VIBE."),
]
PRON = {"ai": "EY AY", "ugh": "AH G", "chai": "CH AY", "keyframes": "K IY F R EY M Z", "vibe": "V AY B", "a": "EY", "m": "EH M"}
sr, a = wavfile.read("n16.wav")
d = Decoder(samprate=16000, beam=1e-80, pbeam=1e-80, wbeam=1e-60)
out = []
for s0, e0, text in SEGS:
    disp = text.split()
    toks = [re.sub(r"[^a-z0-9']", "", w.lower()) for w in disp]
    for t in set(toks):
        if t in PRON and d.lookup_word(t) is None: d.add_word(t, PRON[t], True)
        elif d.lookup_word(t) is None: print("MISSING", t)
    pad = 0.2
    i0, i1 = max(0, int((s0 - pad) * sr)), int((e0 + pad) * sr)
    d.set_align_text(" ".join(toks))
    d.start_utt(); d.process_raw(a[i0:i1].tobytes(), full_utt=True); d.end_utt()
    seg = [x for x in d.seg() if x.word not in ("<s>", "</s>", "<sil>", "[NOISE]")]
    base = i0 / sr
    if len(seg) != len(toks):
        print("FALLBACK", text); ts = np.linspace(s0, e0, len(disp) + 1)
        out += [dict(w=w, s=round(ts[k], 3), e=round(ts[k + 1], 3)) for k, w in enumerate(disp)]
        continue
    out += [dict(w=w, s=round(base + x.start_frame / 100, 3), e=round(base + (x.end_frame + 1) / 100, 3)) for x, w in zip(seg, disp)]
json.dump(out, open("words.json", "w"), indent=0)
print(" ".join(f"{o['w']}@{o['s']:.2f}" for o in out))
