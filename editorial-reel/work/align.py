"""Forced-align the narration script (pocketsphinx) -> words.json [{w,s,e}]. Segments come from silencedetect."""
import json, re
import numpy as np
from pocketsphinx import Decoder
from scipy.io import wavfile

SEGS = [  # (start, end, text): speech islands between pauses
 (0.00, 0.70, "Same reel."), (1.08, 1.83, "Two editors."),
 (2.29, 3.90, "Editor one opens the timeline."), (4.32, 5.73, "Editor two opens a chat."),
 (6.32, 7.60, "Editor one drags"), (7.93, 8.97, "two hundred clips."),
 (9.42, 10.40, "Editor two types"), (10.70, 11.65, "cut my pauses."),
 (12.11, 12.68, "Editor one."), (13.05, 13.64, "Keyframes."), (13.95, 14.50, "Captions."),
 (14.75, 15.06, "Colour."), (15.49, 15.87, "Export."), (16.34, 16.91, "Crash."),
 (17.37, 18.63, "Editor two hits enter."), (19.11, 20.06, "Six hours later."),
 (20.48, 21.68, "Editor one posts."), (22.01, 22.98, "Twelve minutes later."),
 (23.33, 25.11, "Editor two is on reel number three."), (25.52, 27.29, "Same idea. Same footage."),
 (27.58, 28.36, "The only difference?"), (28.70, 29.52, "One of them knew"),
 (29.68, 30.60, "what to ask for."), (31.02, 32.15, "That's Vibe Editing."),
 (32.49, 33.28, "Comment VIBE."), (33.47, 34.25, "and I'll show you how."),
]
PRON = {"vibe": "V AY B", "keyframes": "K IY F R EY M Z", "colour": "K AH L ER"}
sr, a = wavfile.read("n16.wav")
d = Decoder(samprate=16000, beam=1e-80, pbeam=1e-80, wbeam=1e-60)
out = []
for s0, e0, text in SEGS:
    disp = text.split()
    toks = [re.sub(r"[^a-z0-9']", "", w.lower()) for w in disp]
    for t in set(toks):
        if t in PRON and d.lookup_word(t) is None: d.add_word(t, PRON[t], True)
        elif d.lookup_word(t) is None: print("MISSING", t)
    pad = 0.18
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
