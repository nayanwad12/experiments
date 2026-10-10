"""Word-level times for each Whisper segment: pocketsphinx forced alignment on the segment's audio.
OOV words are left out of the alignment and get interpolated between their neighbours."""
import json, re, sys
import numpy as np
from scipy.io import wavfile
from pocketsphinx import Decoder

segs = json.load(open(sys.argv[1]))
sr, A = wavfile.read("audio16k.wav")
NUM = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven",
       "8": "eight", "9": "nine", "10": "ten", "12": "twelve", "15": "fifteen", "20": "twenty", "30": "thirty"}
EXTRA = {"ai": "EY AY", "vfx": "V IY EH F EH K S", "vibe": "V AY B", "claude": "K L AO D", "cloud": "K L AW D",
         "h&m": "EY CH AH N D EH M", "hm": "EY CH AH N D EH M", "ideabro": "AY D IY AH B R OW", "zip": "Z IH P",
         "playbook": "P L EY B UH K", "markdown": "M AA R K D AW N", "chatbox": "CH AE T B AA K S",
         "skill": "S K IH L", "lms": "EH L EH M EH S", "ok": "OW K EY", "okay": "OW K EY"}
d = Decoder(samprate=16000, beam=1e-80, pbeam=1e-80, wbeam=1e-60, maxhmmpf=-1, loglevel="FATAL")
for w, p in EXTRA.items():
    if d.lookup_word(w) is None:
        d.add_word(w, p, True)

out = []
for si, sg in enumerate(segs):
    disp = re.findall(r"[A-Za-z0-9&']+", sg["text"])
    toks = [NUM.get(w, w.lower().strip("'")) for w in disp]
    ok = [bool(t) and d.lookup_word(t) is not None for t in toks]
    t0 = max(0.0, sg["s"] - 0.15); t1 = min(len(A) / sr, sg["e"] + 0.15)
    words = [dict(d=w, s=None, e=None) for w in disp]
    al = [t for t, k in zip(toks, ok) if k]
    if al:
        try:
            d.set_align_text(" ".join(al))
            d.start_utt(); d.process_raw(A[int(t0 * sr):int(t1 * sr)].tobytes(), full_utt=True); d.end_utt()
            got = [(e.word, t0 + e.start_frame / 100, t0 + (e.end_frame + 1) / 100) for e in d.seg()
                   if e.word not in ("<s>", "</s>", "<sil>", "[NOISE]")]
            got = [(re.sub(r"\(\d+\)$", "", w), s, e) for w, s, e in got]
            j = 0
            for i, k in enumerate(ok):
                if k and j < len(got):
                    words[i]["s"], words[i]["e"] = round(got[j][1], 2), round(got[j][2], 2); j += 1
        except Exception as ex:
            print("fail", si, ex)
    # interpolate gaps (OOV or failed)
    n = len(words)
    for i in range(n):
        if words[i]["s"] is None:
            lo = words[i - 1]["e"] if i > 0 and words[i - 1]["e"] is not None else sg["s"]
            k = i
            while k < n and words[k]["s"] is None: k += 1
            hi = words[k]["s"] if k < n else sg["e"]
            m = k - i
            for q in range(m):
                words[i + q]["s"] = round(lo + (hi - lo) * q / m, 2)
                words[i + q]["e"] = round(lo + (hi - lo) * (q + 1) / m, 2)
    out.append(dict(i=si, s=sg["s"], e=sg["e"], text=sg["text"], words=words))
    print(si, sg["s"], " ".join(f"{w['d']}@{w['s']:.2f}" for w in words), flush=True)
json.dump(out, open("words.json", "w"), indent=0)
