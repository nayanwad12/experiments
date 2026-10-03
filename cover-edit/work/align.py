"""Forced-align each VAD segment's corrected text with pocketsphinx -> words.json [{w,s,e,d}]."""
import json, re
import numpy as np
from pocketsphinx import Decoder
from scipy.io import wavfile

SEGS = [  # (start, end, corrected text)
 (0.78, 2.60, "Hi, this is a normal video."),
 (2.60, 4.42, "No edits, no music, nothing."),
 (5.16, 5.80, "Okay, Claude."),
 (6.09, 6.98, "Cut the pauses."),
 (7.47, 7.91, "See?"),
 (8.30, 9.16, "Faster already."),
 (9.99, 11.11, "Add the captions."),
 (11.69, 12.61, "Make them pop."),
 (13.55, 15.01, "Now change the caption style."),
 (15.53, 16.04, "Again."),
 (16.78, 17.32, "And again."),
 (18.57, 20.10, "Cut me out of the background."),
 (20.78, 22.44, "Put me on a magazine cover."),
 (23.34, 25.16, "Add some notes around me."),
 (25.48, 26.98, "Like a real designer would."),
 (27.91, 29.89, "Split the screen into frames."),
 (30.35, 32.26, "Now show my best clips."),
 (33.00, 33.70, "Add music."),
 (34.38, 35.91, "Add sound effects on everything."),
 (36.91, 38.21, "Make it paper cut."),
 (38.47, 40.10, "Now make it move."),
 (41.45, 46.41, "No Premiere Pro, no After Effects, no DaVinci, no Higgsfield, just Claude."),
 (47.15, 48.87, "From boring to this."),
 (49.16, 50.89, "Comment EDIT and I will show you how."),
]
PRON = {"claude": "K L AO D", "higgsfield": "HH IH G Z F IY L D", "davinci": "D AH V IH N CH IY", "premiere": "P R IH M IH R", "3d": "TH R IY D IY", "ai": "EY AY", "didn't": "D IH D AH N T"}
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
