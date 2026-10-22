"""Word timings for the raw take with Parakeet TDT 0.6b v2 (sherpa-onnx, token timestamps).
Decodes in ~20 s windows split at pauses. -> work/words_pk.json [{w, s, e}] (raw clock)."""
import json
import wave
from pathlib import Path

import numpy as np
import sherpa_onnx

HERE = Path(__file__).resolve().parent
M = HERE / "models" / "sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8"
ph = json.loads((HERE / "work" / "phrases.json").read_text())
with wave.open(str(HERE / "work" / "audio16k.wav")) as w:
    sr = w.getframerate()
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
rec = sherpa_onnx.OfflineRecognizer.from_transducer(
    encoder=str(M / "encoder.int8.onnx"), decoder=str(M / "decoder.int8.onnx"), joiner=str(M / "joiner.int8.onnx"),
    tokens=str(M / "tokens.txt"), num_threads=4, model_type="nemo_transducer")
# group phrases into windows <= 20 s
wins, cur = [], []
for p in ph:
    if cur and p["e"] - cur[0]["s"] > 20:
        wins.append(cur)
        cur = []
    cur.append(p)
wins.append(cur)
words = []
for wn in wins:
    s0, e0 = max(0, wn[0]["s"] - 0.3), wn[-1]["e"] + 0.3
    st = rec.create_stream()
    st.accept_waveform(sr, a[int(s0 * sr):int(e0 * sr)])
    rec.decode_stream(st)
    r = st.result
    print(f"[{s0:.2f}-{e0:.2f}] {r.text}")
    toks, ts = r.tokens, r.timestamps
    for i, (tk, t) in enumerate(zip(toks, ts)):
        t = s0 + t
        if tk.startswith(" ") or not words or i == 0:
            words.append(dict(w=tk.strip(), s=round(t, 3), e=round(t + 0.08, 3)))
        else:
            words[-1]["w"] += tk
            words[-1]["e"] = round(t + 0.08, 3)
(HERE / "work" / "words_pk.json").write_text(json.dumps(words, indent=0))
for x in words:
    print(f"{x['s']:6.2f} {x['e']:6.2f} {x['w']}")
