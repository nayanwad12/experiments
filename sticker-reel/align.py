"""Force-align each VAD phrase's corrected text with pocketsphinx -> work/words.json [{w, d, s, e, seg}].

Text = what was actually said (Whisper turbo via sherpa-onnx, re-decoded in context, checked by hand),
false starts included so the edit can cut them on exact word boundaries. Display forms in DISPLAY.
"""
import json
import re
from pathlib import Path

import numpy as np
from pocketsphinx import Decoder
from scipy.io import wavfile

HERE = Path(__file__).resolve().parent
SEGS = [  # (start, end, spoken text) on the raw clock
    (0.51, 3.47, "Video editing just changed, and most people haven't noticed yet."),
    (3.87, 6.03, "For years, editing meant one thing."),
    (6.40, 7.69, "Sit in front of timeline,"),
    (8.03, 12.43, "drag clips, set keyframes, and spend six hours on a sixty second reel."),
    (12.99, 16.46, "Vibe editing flips that. You don't edit anymore. You direct."),
    (17.02, 18.92, "You tell the system what you want,"),
    (19.26, 22.00, "the same way you'd brief a top editor."),
    (22.59, 23.53, "Cut the pauses."),
    (24.09, 25.52, "Make the captions punchy."),
    (25.95, 26.73, "Put the ti"),
    (27.64, 29.07, "Put the title behind me."),
    (29.44, 30.67, "Give it a cinematic look."),
    (31.07, 31.95, "Add music"),
    (32.22, 32.88, "that builds."),
    (33.28, 34.12, "And it builds it."),
    (34.40, 35.05, "Every cut,"),
    (35.23, 36.84, "every caption, every effect,"),
    (37.12, 37.71, "every sound."),
    (38.08, 38.89, "Made in code,"),
    (39.26, 40.20, "right on your laptop."),
    (40.76, 41.42, "And it's sh"),
    (41.82, 43.18, "And it's not just reels."),
    (43.55, 45.55, "The same system makes motion graphics,"),
    (46.01, 48.17, "product ads, claymation, VFX,"),
    (48.35, 49.16, "podcast clips,"),
    (49.47, 51.18, "even fifty versions of one ad,"),
    (51.80, 53.52, "so you can test what works."),
    (54.08, 55.63, "So what do you need actually"),
    (56.83, 58.35, "So what do you actually need?"),
    (58.56, 61.48, "Your footage, your laptop, and the Vibe Editing System."),
    (62.94, 63.40, "The editing"),
    (63.80, 65.00, "skills, plus a full"),
    (65.31, 65.90, "course"),
    (66.27, 68.65, "that shows you how to direct every one of them."),
    (69.18, 70.92, "No After Effects. No Premiere Pro."),
    (71.23, 72.08, "No keyframes."),
    (72.51, 74.44, "And this video you just watched,"),
    (74.65, 76.49, "I didn't open a single editing app."),
    (76.89, 79.72, "I recorded it on my phone, and the system did the rest."),
]
DISPLAY = {"six": "6", "sixty": "60", "fifty": "50", "vfx": "VFX"}
PRON = {"ti": "T AY", "sh": "SH IH", "vfx": "V IY EH F EH K S", "claymation": "K L EY M EY SH AH N",
        "keyframes": "K IY F R EY M Z", "vibe": "V AY B", "you'd": "Y UW D", "premiere": "P R IH M IH R"}
sr, a = wavfile.read(HERE / "work" / "audio16k.wav")
# the phone's voice isolation leaves digital silence between phrases; faint dither keeps the recogniser's
# normalisation sane so it stops dropping the last word of a phrase
a = (a.astype(np.float32) + np.random.default_rng(0).normal(0, 4, len(a))).clip(-32768, 32767).astype(np.int16)
d = Decoder(samprate=16000, beam=1e-80, pbeam=1e-80, wbeam=1e-60)
out = []
for k, (s0, e0, text) in enumerate(SEGS):
    disp = [w for w in text.split()]
    toks = [re.sub(r"[^a-z0-9']", "", w.lower()) for w in disp]
    for t in set(toks):
        if t in PRON and d.lookup_word(t) is None:
            d.add_word(t, PRON[t], True)
        elif d.lookup_word(t) is None:
            print("OOV", t)
    nxt = SEGS[k + 1][0] if k + 1 < len(SEGS) else e0 + 1
    prv = SEGS[k - 1][1] if k else 0
    for pad_s, pad_e in ((0.22, 0.45), (0.3, 0.6), (0.15, 0.3)):
        pad = min(pad_s, (s0 - prv) * 0.8)
        i0, i1 = int((s0 - pad) * sr), int(min(e0 + pad_e, nxt - 0.05) * sr)
        d.set_align_text(" ".join(toks))
        d.start_utt()
        d.process_raw(a[i0:i1].tobytes(), full_utt=True)
        d.end_utt()
        seg = [x for x in d.seg() if x.word not in ("<s>", "</s>", "<sil>", "[NOISE]")] if d.hyp() else []
        if len(seg) == len(toks):
            break
        print("  got", [x.word for x in seg])
    if len(seg) != len(toks):
        print("FALLBACK", text, len(seg), len(toks))
        ts = np.linspace(s0, e0, len(toks) + 1)
        seg_t = [(ts[j], ts[j + 1]) for j in range(len(toks))]
    else:
        seg_t = [(s0 - pad + x.start_frame / 100, s0 - pad + (x.end_frame + 1) / 100) for x in seg]
    for (ws, we), w, t in zip(seg_t, disp, toks):
        dw = re.sub(r"[^\w'-]", "", w)
        dw = DISPLAY.get(t, dw)
        out.append(dict(w=t, d=dw, s=round(ws, 3), e=round(we, 3), seg=k, p=w[-1] if w[-1] in ",.?" else ""))
for i in range(len(out) - 1, 0, -1):   # "60" + "second" -> one caption word "60-second"
    if out[i]["w"] == "second" and out[i - 1]["w"] == "sixty":
        out[i - 1].update(d="60-second", e=out[i]["e"], w="sixty-second")
        del out[i]
(HERE / "work" / "words.json").write_text(json.dumps(out, indent=0))
prev = None
for o in out:
    if prev is not None and o["seg"] != prev:
        print()
    print(f"{o['s']:6.2f}-{o['e']:6.2f} {o['d']}{o['p']}", end="   ")
    prev = o["seg"]
print("\nwords", len(out))
