"""Rough transcript of the raw take with Whisper small.en (sherpa-onnx), chunked on pauses."""
import wave
import numpy as np
import sherpa_onnx

M = "models/sherpa-onnx-whisper-small.en/small.en-"
rec = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=M + "encoder.int8.onnx", decoder=M + "decoder.int8.onnx",
                                                 tokens=M + "tokens.txt", num_threads=2)
w = wave.open("work/audio16k.wav")
x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
hop = 160
e = np.sqrt(np.convolve(x ** 2, np.ones(400) / 400, "same")[::hop])
th = max(0.01, np.percentile(e, 30) * 2.5)
voiced = e > th
# segments split on pauses >= 0.35 s
segs, s, last = [], None, -99
for i, v in enumerate(voiced):
    if v:
        if s is None:
            s = i
        last = i
    elif s is not None and i - last > 35:
        segs.append((s, last)); s = None
if s is not None:
    segs.append((s, last))
for a, b in segs:
    ta, tb = a * hop / 16000, b * hop / 16000
    st = rec.create_stream()
    st.accept_waveform(16000, x[max(0, a * hop - 2400): b * hop + 2400])
    rec.decode_stream(st)
    print(f"[{ta:6.2f}-{tb:6.2f}] {st.result.text.strip()}")
