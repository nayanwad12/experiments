"""Word timings for the raw take: each pause-separated chunk is force-aligned (pocketsphinx) to the text
actually spoken in it. Chunks with text None are cut from the edit (false starts). -> work/words.json"""
import json
import re
import wave

import numpy as np
from pocketsphinx import Decoder

CHUNKS = [  # (start, end) on the raw clock, spoken text (None = drop)
    (0.30, 2.12, "You are not bad at content."),
    (2.12, 5.20, "You are just losing three hours editing every single reel."),
    (5.40, 6.75, "And that's why you post"),
    (6.85, 8.80, "twice a week instead of every day."),
    (8.90, 9.95, "And here is the fix."),
    (10.20, 11.70, "It's called the vibe editing."),
    (11.85, 14.05, "You record, you tell the system what you want."),
    (14.20, 15.20, "Cut the pauses."),
    (15.45, 16.60, "Punchy captions,"),
    (16.70, 20.50, "cinematic look, add music, and it edits the whole thing for you."),
    (20.70, 22.90, "Cuts, captions, effects, sound."),
    (23.05, 25.30, "Ready for reels, feed and YouTube."),
    (25.50, 28.15, "No timeline, no keyframes, no editor."),
    (28.30, 29.10, None),
    (29.65, 32.95, "This video, recorded on my phone, edited by the system."),
    (33.20, 36.70, "And if you want to post every day without editing every day,"),
    (36.85, 38.40, "get the vibe editing system."),
    (38.55, 39.05, "Tap"),
    (39.30, 40.10, "Learn more."),
]
EXTRA = {"youtube": "Y UW T UW B", "keyframes": "K IY F R EY M Z", "vibe": "V AY B"}

w = wave.open("work/audio16k.wav")
pcm = np.frombuffer(w.readframes(w.getnframes()), np.int16)
out = []
for a, b, text in CHUNKS:
    if text is None:
        continue
    disp = re.findall(r"[A-Za-z0-9'.,?]+", text)
    toks = [re.sub(r"[^a-z0-9']", "", d.lower()) for d in disp]
    toks = ["three" if t == "3" else t for t in toks]
    d = Decoder(samprate=16000, loglevel="FATAL")
    for t in set(toks):
        if t in EXTRA and d.lookup_word(t) is None:
            d.add_word(t, EXTRA[t], True)
        elif d.lookup_word(t) is None:
            print("OOV", t)
    d.set_align_text(" ".join(toks))
    d.start_utt()
    z = np.zeros(8000, np.int16)
    d.process_raw(np.concatenate([z, pcm[int(a * 16000):int(b * 16000)], z]).tobytes(), full_utt=True)
    d.end_utt()
    seg = [e for e in d.seg() if e.word not in ("<s>", "</s>", "<sil>", "[NOISE]") and not e.word.startswith("++")]
    assert len(seg) == len(toks), (text, [e.word for e in seg])
    for e, dw in zip(seg, disp):
        out.append(dict(w=re.sub(r"\(\d+\)$", "", e.word), d=dw, s=round(a - 0.5 + e.start_frame / 100, 2),
                        e=round(a - 0.5 + (e.end_frame + 1) / 100, 2)))
json.dump(out, open("work/words.json", "w"), indent=0)
prev = 0
for o in out:
    gap = o["s"] - prev
    print(("   -- gap %.2f\n" % gap if gap > 0.2 else "") + f"{o['s']:6.2f} {o['e']:6.2f} {o['d']}")
    prev = o["e"]
