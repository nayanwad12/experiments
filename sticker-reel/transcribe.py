"""Speech segments (Silero VAD) + Whisper turbo (sherpa-onnx) per segment -> work/segs.json.

Gives the text of every phrase and where it sits on the raw clock; align.py then times each word.
"""
import json
import time
from pathlib import Path

import numpy as np
import sherpa_onnx
from scipy.io import wavfile

HERE = Path(__file__).resolve().parent
M = "/home/user/models"
sr, a = wavfile.read(HERE / "work" / "audio16k.wav")
a = a.astype(np.float32) / 32768

cfg = sherpa_onnx.VadModelConfig()
cfg.silero_vad.model = f"{M}/silero_vad.onnx"
cfg.silero_vad.min_silence_duration = 0.18
cfg.silero_vad.min_speech_duration = 0.1
cfg.silero_vad.threshold = 0.4
cfg.silero_vad.max_speech_duration = 20
cfg.sample_rate = 16000
vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=120)
segs = []
w = cfg.silero_vad.window_size
for i in range(0, len(a), w):
    vad.accept_waveform(a[i:i + w])
    while not vad.empty():
        segs.append((vad.front.start / sr, len(vad.front.samples) / sr))
        vad.pop()
vad.flush()
while not vad.empty():
    segs.append((vad.front.start / sr, len(vad.front.samples) / sr))
    vad.pop()

d = f"{M}/sherpa-onnx-whisper-turbo"
rec = sherpa_onnx.OfflineRecognizer.from_whisper(
    encoder=f"{d}/turbo-encoder.int8.onnx", decoder=f"{d}/turbo-decoder.int8.onnx",
    tokens=f"{d}/turbo-tokens.txt", language="en", task="transcribe", num_threads=4)
out = []
t0 = time.time()
for s, dur in segs:
    pad = 0.15
    i0, i1 = int(max(0, s - pad) * sr), int(min(len(a) / sr, s + dur + pad) * sr)
    st = rec.create_stream()
    st.accept_waveform(sr, a[i0:i1])
    rec.decode_stream(st)
    txt = st.result.text.strip()
    out.append(dict(s=round(s, 2), e=round(s + dur, 2), text=txt))
    print(f"[{s:6.2f}-{s + dur:6.2f}] {txt}", flush=True)
(HERE / "work" / "segs.json").write_text(json.dumps(out, indent=1))
print("done", round(time.time() - t0, 1), "s")
