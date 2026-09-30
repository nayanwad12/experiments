"""Forced-align the narration script (per energy segment) with pocketsphinx -> words.json [{w,s,e}]."""
import json, re
import numpy as np
from pocketsphinx import Decoder
from scipy.io import wavfile

SEGS = [
 (0.09, 3.36, "In cancer care, every appointment brings questions."),
 (3.77, 5.72, "Every report holds information."),
 (6.11, 8.02, "And every detail matters."),
 (8.44, 11.27, "But a patient's journey rarely lives in one place."),
 (11.70, 17.17, "Blood reports on the phone. Scans in hospital portals. Pathology reports in emails."),
 (17.51, 20.41, "Prescriptions and PDFs inside physical folders."),
 (20.80, 22.98, "Different records. Different places."),
 (23.30, 24.99, "And they rarely speak to each other."),
 (25.49, 31.46, "That's why we created OncoXpress under the leadership of Dr Aditya Sarin and Dr Shyam Agrawal,"),
 (31.73, 33.11, "powered by BigOHealth"),
 (33.36, 37.11, "to bring your entire cancer-care journey in one secure place."),
 (37.51, 40.12, "Upload your medical records exactly as they are."),
 (40.38, 43.69, "No renaming. No sorting. No complicated folders."),
 (44.00, 51.38, "OncoXpress identifies, categorizes and organizes all your reports into one clear, chronological timeline."),
 (51.68, 62.50, "It tracks tumour marker trends, vital signs, treatment history, scans, pathology, and key biomarkers, giving you a complete picture of your cancer journey, all in one place."),
 (62.89, 71.04, "With OncoXpress patients spend less time searching for documents, while doctors understand years of medical history in under 60 seconds."),
 (71.44, 72.33, "OncoXpress,"),
 (72.60, 73.86, "powered by BigOHealth."),
 (74.24, 74.93, "Faster Care."),
 (75.20, 75.97, "Trusted Care."),
]
PRON = {
 "oncoxpress": "AA NG K OW EH K S P R EH S", "bigohealth": "B IH G OW HH EH L TH",
 "aditya": "AH D IH T Y AH", "sarin": "S AA R IH N", "shyam": "SH Y AA M", "agrawal": "AH G R AA W AH L",
 "tumour": "T UW M ER", "biomarkers": "B AY OW M AA R K ER Z", "pdfs": "P IY D IY EH F S",
 "cancercare": "K AE N S ER K EH R", "60": "S IH K S T IY", "dr": "D AA K T ER", "renaming": "R IY N EY M IH NG",
 "categorizes": "K AE T AH G ER AY Z AH Z",
}
sr, a = wavfile.read("narr16k.wav")
d = Decoder(samprate=16000, beam=1e-80, pbeam=1e-80, wbeam=1e-60)
out = []
for s0, e0, text in SEGS:
    disp = text.replace("cancer-care", "cancercare").split()
    toks = [re.sub(r"[^a-z0-9']", "", w.lower()) for w in disp]
    for t in set(toks):
        if t in PRON and d.lookup_word(t) is None:
            d.add_word(t, PRON[t], True)
        elif d.lookup_word(t) is None:
            print("MISSING", t)
    pad = 0.12
    i0, i1 = int(max(0, s0 - pad) * sr), int((e0 + pad) * sr)
    d.set_align_text(" ".join(toks))
    d.start_utt(); d.process_raw(a[i0:i1].tobytes(), full_utt=True); d.end_utt()
    seg = [x for x in d.seg() if x.word not in ("<s>", "</s>", "<sil>", "[NOISE]")]
    b = i0 / sr
    if len(seg) != len(toks):
        print("FALLBACK", text, len(seg), len(toks))
        ts = np.linspace(s0, e0, len(disp) + 1)
        for k, w in enumerate(disp): out.append(dict(w=w, s=round(ts[k], 3), e=round(ts[k + 1], 3)))
        continue
    for x, w in zip(seg, disp):
        out.append(dict(w=w, s=round(b + x.start_frame / 100, 3), e=round(b + (x.end_frame + 1) / 100, 3)))
json.dump(out, open("words.json", "w"), indent=0)
for o in out: print(f"{o['s']:6.2f} {o['e']:6.2f} {o['w']}")
