import json, re, time
from pocketsphinx import Decoder
SCRIPT = """I used to spend four hours editing one reel.
Four. Hours. For thirty seconds of content.
Cutting clips, adding captions, keyframing every little animation…
By the time I finished editing, I had no energy left to actually create.
Then I stopped editing… and started directing.
Now I just tell AI what I want.
'Cut the silences.'
'Add captions.'
'Make it pop.'
And it does the editing for me.
This video you're watching right now?
I recorded it raw, and I didn't touch a timeline.
Because editing today isn't about knowing software.
It's about taste. It's about storytelling.
You direct. AI edits.
I'm teaching exactly how I do this in my course,
Vibe Editing by Ideabro Studio.
Captions, motion graphics, animations, ads, all just by describing what you want.
Link in bio. See you inside."""
disp = [w.strip("'") for w in re.findall(r"[A-Za-z0-9']+", SCRIPT.replace("’", "'")) if w.strip("'")]
toks = [w.lower() for w in disp]
d = Decoder(samprate=16000, beam=1e-120, pbeam=1e-120, wbeam=1e-100, maxhmmpf=-1)
extra = {"keyframing": "K IY F R EY M IH NG", "ideabro": "AY D IY AH B R OW", "ai": "EY AY",
         "storytelling": "S T AO R IY T EH L IH NG", "captions": "K AE P SH AH N Z", "vibe": "V AY B",
         "timeline": "T AY M L AY N"}
for w in set(toks):
    if d.lookup_word(w) is None:
        if w in extra:
            d.add_word(w, extra[w], True)
        else:
            print("OOV", w)
d.set_align_text(" ".join(toks))
raw = open("audio16k.wav", "rb").read()[44:]
t0 = time.time()
d.start_utt(); d.process_raw(raw, full_utt=True); d.end_utt()
print("hyp", d.hyp().hypstr[:120] if d.hyp() else None)
out = []
for e in d.seg():
    if e.word in ("<s>", "</s>", "<sil>", "[NOISE]"): continue
    out.append(dict(w=e.word, s=e.start_frame / 100, e=(e.end_frame + 1) / 100))
print("aligned", len(out), "of", len(toks), time.time() - t0)
for o, dw in zip(out, disp): o["d"] = dw
json.dump(out, open("words.json", "w"), indent=0)
for o in out: print(f"{o['s']:6.2f} {o['e']:6.2f} {o['d']}")
