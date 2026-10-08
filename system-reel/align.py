"""Force-align the spoken text to the raw take: work/words.json [{w, d, s, e}] (raw clock, seconds).

The text is what was actually said (from a Whisper pass, small.en via sherpa-onnx, hand-checked).
"""
import json
import re
from pathlib import Path

from pocketsphinx import Decoder

HERE = Path(__file__).resolve().parent
SPOKEN = """The video you're watching right now, I didn't edit it. My system did.
On the left is the video straight from my phone, and on the right, what you're watching. Same video. No editing app.
I built this system for my own videos. It works in four simple steps.
Step one. I record on my phone. Just one take. Mistakes are okay. Like right now, I'm going to...
Sorry, let me say that again. Mistakes are okay.
Step two. I tell my system what I want, in simple words. Like make it short, add big text, add music.
Step three. The system edits it for me. It cuts the pauses, zooms in, adds the text, and the music, and even this.
Step four. I check it. Want a change? I just say it. Then it's ready for Instagram, YouTube, anywhere.
That's how this whole video was made, and every video on my page.
Want to see how my system works? Comment SYSTEM and I will send you the details."""

disp = [w for w in re.findall(r"[A-Za-z0-9'.,?]+", SPOKEN.replace("...", "…")) if re.search(r"[A-Za-z0-9]", w)]
toks = [re.sub(r"[^a-z0-9']", "", w.lower()) for w in disp]
d = Decoder(samprate=16000, beam=1e-120, pbeam=1e-120, wbeam=1e-100, maxhmmpf=-1)
extra = {"youtube": "Y UW T UW B", "instagram": "IH N S T AH G R AE M"}
for w in sorted(set(toks)):
    if d.lookup_word(w) is None:
        if w in extra:
            d.add_word(w, extra[w], True)
        else:
            print("OOV", w)
d.set_align_text(" ".join(toks))
raw = open(HERE / "work" / "audio16k.wav", "rb").read()[44:]
d.start_utt()
d.process_raw(raw, full_utt=True)
d.end_utt()
out = []
for e in d.seg():
    if e.word in ("<s>", "</s>", "<sil>", "[NOISE]") or e.word.startswith("++"):
        continue
    out.append(dict(w=re.sub(r"\(\d+\)$", "", e.word), s=round(e.start_frame / 100, 2), e=round((e.end_frame + 1) / 100, 2)))
print("aligned", len(out), "of", len(toks))
assert len(out) == len(toks), "alignment failed"
for o, dw in zip(out, disp):
    o["d"] = dw
(HERE / "work" / "words.json").write_text(json.dumps(out, indent=0))
prev = 0
for o in out:
    gap = o["s"] - prev
    print(f"{'  -- gap %.2f' % gap if gap > 0.25 else ''}\n{o['s']:6.2f} {o['e']:6.2f} {o['d']}" if gap > 0.25 else f"{o['s']:6.2f} {o['e']:6.2f} {o['d']}")
    prev = o["e"]
