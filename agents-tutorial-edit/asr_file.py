"""Speech segments via Silero VAD, then Whisper (sherpa-onnx) on each segment."""
import json, sys, time
import numpy as np, sherpa_onnx
from scipy.io import wavfile

M = "/home/user/models"
name = sys.argv[1] if len(sys.argv) > 1 else "small"
lang = sys.argv[2] if len(sys.argv) > 2 else ""
sr, a = wavfile.read(sys.argv[3]); a = a.astype(np.float32) / 32768

cfg = sherpa_onnx.VadModelConfig()
cfg.silero_vad.model = f"{M}/silero_vad.onnx"
cfg.silero_vad.min_silence_duration = 0.2
cfg.silero_vad.min_speech_duration = 0.15
cfg.silero_vad.threshold = 0.45
cfg.silero_vad.max_speech_duration = 20
cfg.sample_rate = 16000
vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=120)
segs = []
w = cfg.silero_vad.window_size
for i in range(0, len(a), w):
    vad.accept_waveform(a[i:i + w])
    while not vad.empty():
        segs.append((vad.front.start / sr, len(vad.front.samples) / sr)); vad.pop()
vad.flush()
while not vad.empty():
    segs.append((vad.front.start / sr, len(vad.front.samples) / sr)); vad.pop()

d = f"{M}/sherpa-onnx-whisper-{name}"
rec = sherpa_onnx.OfflineRecognizer.from_whisper(
    encoder=f"{d}/{name}-encoder.int8.onnx", decoder=f"{d}/{name}-decoder.int8.onnx",
    tokens=f"{d}/{name}-tokens.txt", language=lang, task="transcribe", num_threads=4)
out = []
t0 = time.time()
for s, dur in segs:
    pad = 0.15
    i0, i1 = int(max(0, s - pad) * sr), int(min(len(a) / sr, s + dur + pad) * sr)
    st = rec.create_stream(); st.accept_waveform(sr, a[i0:i1]); rec.decode_stream(st)
    r = st.result
    out.append(dict(s=round(s, 2), e=round(s + dur, 2), text=r.text.strip(), lang=getattr(r, "lang", "")))
    print(f"[{s:6.2f}-{s+dur:6.2f}] {getattr(r,'lang','')} {r.text.strip()}", flush=True)
json.dump(out, open(sys.argv[3] + ".json", "w"), indent=1)
print("done", round(time.time() - t0, 1))
