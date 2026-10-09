"""Force-align the romanized Hinglish transcript -> work/words.json [{w, s, e, seg}] (raw clock, seconds).

Transcript: Whisper turbo (Hindi + English + Hinglish-prompted passes, work/whisper_np.py) reconciled by hand,
ambiguous lines settled by Whisper likelihood scoring (work/score.py). Alignment: pocketsphinx over the whole take,
with hand pronunciations for the Hindi words.
"""
import json
import re
from pathlib import Path

from pocketsphinx import Decoder

HERE = Path(__file__).resolve().parent
SEGS = [  # (start, end, text) on the raw clock
    (0.78, 2.97, "Mind mein ek new creative idea hai, lekin"),
    (2.97, 4.62, "samajh nahi aa raha ki show kahan karein?"),
    (4.62, 7.59, "Isliye Adaix lekar aaya hai new OOH Creative Challenge."),
    (7.88, 8.90, "Make a boring brand..."),
    (10.31, 10.89, "Boring brand?"),
    (11.72, 12.33, "Yeh kya?"),
    (14.06, 15.37, "Ruko ruko, main batati hoon."),
    (15.63, 18.85, "Pick your city, pick any brand, product or location."),
    (19.24, 22.69, "Then see, us city pe, us location pe already kya chal raha hai."),
    (23.08, 26.79, "Find the insight and turn this insight into an OOH idea."),
    (27.40, 33.00, "We're not just looking for a creative billboard, we are looking for observation, insight "
                   "and creative OOH thinking."),
    (34.99, 42.82, "Aur winner? Sirf certificate nahi. Your idea could actually come alive on Adaix OOH Media, "
                   "and also you get a chance to work with us."),
    (43.53, 45.93, "If you want to show your creativity, join us"),
    (46.31, 47.37, "and register now!"),
]
PRON = {
    "mein": "M EY N", "ek": "EY K", "hai": "HH EH", "lekin": "L EY K IH N", "samajh": "S AH M AH JH",
    "nahi": "N AH HH IY", "aa": "AA", "raha": "R AH HH AA", "ki": "K IY", "kahan": "K AH HH AA N",
    "karein": "K AH R EY N", "isliye": "IH S L IY EY", "adaix": "AE D EH K S", "lekar": "L EY K AH R",
    "aaya": "AA Y AA", "ooh": "OW OW EY CH", "yeh": "Y EH", "kya": "K Y AA", "ruko": "R UH K OW",
    "batati": "B AH T AA T IY", "hoon": "HH UW N", "pe": "P EY", "chal": "CH AH L", "aur": "AW R",
    "sirf": "S IH R F", "main": "M EY N",
}


def tokens(text):
    disp = [w for w in re.findall(r"[A-Za-z0-9'.,?!]+", text.replace("...", "…")) if re.search(r"[A-Za-z0-9]", w)]
    return disp, [re.sub(r"[^a-z0-9']", "", w.lower()) for w in disp]


def main():
    disp, toks, seg = [], [], []
    for k, (_, _, text) in enumerate(SEGS):
        dw, tw = tokens(text)
        disp += dw; toks += [w + "_hx" if w in PRON else w for w in tw]; seg += [k] * len(dw)
    d = Decoder(samprate=16000, beam=1e-120, pbeam=1e-120, wbeam=1e-100, maxhmmpf=-1)
    for w in set(toks):
        if w.endswith("_hx"):
            d.add_word(w, PRON[w[:-3]], True)
        elif d.lookup_word(w) is None:
            raise SystemExit(f"OOV {w}")
    d.set_align_text(" ".join(toks))
    d.start_utt(); d.process_raw(open(HERE / "work" / "audio16k.wav", "rb").read()[44:], full_utt=True); d.end_utt()
    al = [x for x in d.seg() if x.word not in ("<s>", "</s>", "<sil>", "[NOISE]") and not x.word.startswith("++")]
    assert len(al) == len(toks), "alignment failed"
    out = [dict(w=w, s=round(x.start_frame / 100, 2), e=round((x.end_frame + 1) / 100, 2), seg=k)
           for x, w, k in zip(al, disp, seg)]
    (HERE / "work" / "words.json").write_text(json.dumps(out, indent=0))
    for o in out:
        print(f"{o['seg']:2d} {o['s']:6.2f} {o['e']:6.2f} {o['w']}")


if __name__ == "__main__":
    main()
