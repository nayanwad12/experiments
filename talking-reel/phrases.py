"""Phrase-level transcript: split the raw take on pauses (silencedetect), run Whisper medium.en (sherpa-onnx)
on each speech island. -> work/phrases.json [{s, e, text}] (raw clock)."""
import json
import re
import subprocess
import wave
from pathlib import Path

import numpy as np
import sherpa_onnx

HERE = Path(__file__).resolve().parent
WAV = HERE / "work" / "audio16k.wav"
M = HERE / "models" / "sherpa-onnx-whisper-medium.en"

log = subprocess.run(["ffmpeg", "-i", str(WAV), "-af", "silencedetect=noise=-38dB:d=0.25", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
with wave.open(str(WAV)) as w:
    sr = w.getframerate()
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
dur = len(a) / sr
isl = []
prev = 0.0
for s, e in zip(st, en + [dur] * (len(st) - len(en))):
    if s - prev > 0.05:
        isl.append((prev, s))
    prev = e
if dur - prev > 0.1:
    isl.append((prev, dur))

rec = sherpa_onnx.OfflineRecognizer.from_whisper(
    encoder=str(M / "medium.en-encoder.int8.onnx"), decoder=str(M / "medium.en-decoder.int8.onnx"),
    tokens=str(M / "medium.en-tokens.txt"), num_threads=4, language="en", task="transcribe")
out = []
for s, e in isl:
    s0, e0 = max(0, s - 0.08), min(dur, e + 0.08)
    st_ = rec.create_stream()
    st_.accept_waveform(sr, a[int(s0 * sr):int(e0 * sr)])
    rec.decode_stream(st_)
    txt = st_.result.text.strip()
    out.append(dict(s=round(s, 3), e=round(e, 3), text=txt))
    print(f"{s:6.2f}-{e:6.2f}  {txt}", flush=True)
(HERE / "work" / "phrases.json").write_text(json.dumps(out, indent=1))
