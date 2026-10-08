"""Force-align known script lines to segments of a take with PocketSphinx -> words.json"""
import sys, wave, json, numpy as np
from pocketsphinx import Decoder
take, segs_file, out = sys.argv[1], sys.argv[2], sys.argv[3]
segs = json.load(open(segs_file))
with wave.open(take) as w: pcm = np.frombuffer(w.readframes(w.getnframes()), np.int16)
SR = 16000; words = []; report = []
for s in segs:
    a, b = int(s["s"]*SR), int(s["e"]*SR)
    d = Decoder(samprate=SR, loglevel="FATAL")
    d.set_align_text(s["text"])
    d.start_utt(); d.process_raw(pcm[a:b].tobytes(), full_utt=True); d.end_utt()
    hyp = d.hyp()
    segw = [x for x in (d.seg() or []) if x.word not in ("<s>", "</s>", "<sil>", "[NOISE]")]
    if not segw: print("ALIGN FAILED", s["id"])
    nfr = max(1, (b - a) // 160)
    report.append((s["id"], s["s"], s["e"], hyp.score / nfr if hyp else None, len(segw), len(s["text"].split())))
    for x in segw:
        words.append({"w": x.word.split("(")[0], "s": round(s["s"] + x.start_frame*0.01, 3),
                      "e": round(s["s"] + (x.end_frame+1)*0.01, 3), "line": s["id"]})
json.dump(words, open(out, "w"), indent=0)
for r in report: print("%-4s %6.2f-%6.2f score/frame=%s words %d/%d" % (r[0], r[1], r[2], None if r[3] is None else round(r[3]), r[4], r[5]))
