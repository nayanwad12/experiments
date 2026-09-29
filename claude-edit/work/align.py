"""Forced-align each VAD segment's corrected text with pocketsphinx -> words.json [{w,s,e,d}]."""
import json, re
import numpy as np
from pocketsphinx import Decoder
from scipy.io import wavfile

SEGS = [  # (start, end, corrected text)
 (0.55, 2.89, "Editing videos manually might be over."),
 (3.31, 3.97, "Watch this."),
 (4.65, 5.73, "Zoom in on my hand."),
 (6.63, 8.13, "Now put my logo right here"),
 (8.71, 9.35, "in 3D."),
 (10.12, 10.66, "Nice."),
 (11.21, 13.51, "Make me grab the logo and throw it"),
 (14.25, 15.14, "straight at the camera."),
 (16.75, 17.19, "Okay."),
 (17.42, 17.96, "Harder one."),
 (18.54, 20.68, "Separate this scene into layers."),
 (21.03, 23.01, "The background, me, and the text."),
 (24.52, 25.41, "Now remove me."),
 (27.98, 28.65, "Bring me back."),
 (33.71, 36.77, "Put me inside a frame on the right, and on the left"),
 (37.19, 39.33, "show me the anatomy of a viral reel."),
 (39.95, 40.42, "First,"),
 (40.71, 41.25, "the hook,"),
 (41.64, 42.57, "then retention,"),
 (43.75, 44.52, "then the share."),
 (47.21, 48.45, "Back to the full screen."),
 (50.06, 53.25, "Now put my best videos floating behind me in 3D."),
 (54.22, 54.60, "Perfect!"),
 (56.87, 57.51, "Last one."),
 (62.70, 66.57, "Turn this entire scene into a cinematic documentary about me."),
 (67.37, 68.61, "The dramatic lighting,"),
 (69.00, 70.21, "slow camera push in,"),
 (70.92, 72.26, "movie style titles."),
 (73.77, 74.60, "That's crazy."),
 (76.62, 79.72, "And all of this was edited with AI."),
 (80.65, 83.01, "Comment EDIT and I will show you how."),
]
PRON = {"3d": "TH R IY D IY", "ai": "EY AY"}
sr, a = wavfile.read("audio16k.wav")
d = Decoder(samprate=16000, beam=1e-80, pbeam=1e-80, wbeam=1e-60)
out = []
for s0, e0, text in SEGS:
    disp = text.split()
    toks = [re.sub(r"[^a-z0-9']", "", w.lower()) for w in disp]
    for t in set(toks):
        if d.lookup_word(t) is None:
            d.add_word(t, PRON[t], True)
    pad = 0.25
    i0, i1 = int((s0 - pad) * sr), int((e0 + pad) * sr)
    d.set_align_text(" ".join(toks))
    d.start_utt(); d.process_raw(a[i0:i1].tobytes(), full_utt=True); d.end_utt()
    seg = [x for x in d.seg() if x.word not in ("<s>", "</s>", "<sil>", "[NOISE]")]
    if len(seg) != len(toks):
        print("FALLBACK", text, len(seg), len(toks))
        n = len(disp); ts = np.linspace(s0, e0, n + 1)
        for k, w in enumerate(disp): out.append(dict(w=w, s=round(ts[k], 3), e=round(ts[k + 1], 3), seg=s0))
        continue
    for x, w in zip(seg, disp):
        out.append(dict(w=w, s=round(s0 - pad + x.start_frame / 100, 3), e=round(s0 - pad + (x.end_frame + 1) / 100, 3), seg=s0))
json.dump(out, open("words.json", "w"), indent=0)
for o in out: print(f"{o['s']:6.2f} {o['e']:6.2f} {o['w']}")
