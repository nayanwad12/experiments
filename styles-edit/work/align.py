"""Forced-align each VAD segment's corrected text with pocketsphinx -> words.json [{w,s,e,d}]."""
import json, re
import numpy as np
from pocketsphinx import Decoder
from scipy.io import wavfile

SEGS = [  # (start, end, corrected text)
 (0.62, 3.72, "I'm going to change this video five times just by saying it."),
 (4.14, 4.55, "Watch."),
 (5.10, 6.12, "Make it a news channel."),
 (6.47, 8.61, "Breaking news, editing just got easy."),
 (9.48, 11.01, "Now make it a movie trailer."),
 (11.72, 12.36, "In a world"),
 (12.71, 14.09, "where nobody edits anymore."),
 (14.89, 16.10, "Now make it a cartoon."),
 (16.94, 17.29, "Hi!"),
 (17.71, 19.05, "Everything just got colorful."),
 (19.72, 20.84, "Now make it a video game."),
 (21.61, 22.12, "Level up!"),
 (22.63, 23.69, "New skills unlocked."),
 (24.59, 25.29, "Now make it"),
 (25.55, 28.23, "an old movie from nineteen twenties."),
 (28.87, 31.88, "A silent film about a man who stopped editing."),
 (33.77, 34.25, "Back to normal."),
 (34.73, 35.43, "That was fun."),
 (36.17, 37.77, "I didn't edit any of this."),
 (38.15, 39.40, "I just said it loud."),
 (40.43, 42.12, "So comment EDIT and I will show you how."),
]
PRON = {"3d": "TH R IY D IY", "ai": "EY AY", "didn't": "D IH D AH N T"}
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
