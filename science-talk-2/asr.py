"""Silero VAD segments -> Whisper turbo (sherpa-onnx export) greedy decode in numpy/onnxruntime.

sherpa-onnx's own recognizer drops partial UTF-8 bytes per token, which mangles Devanagari; here the
token bytes are joined first and decoded once.

    python3 asr.py hi transcribe          -> work/segs_hi_transcribe.json       (long segments, for reading)
    python3 asr.py hi transcribe --fine   -> work/segs_fine_hi_transcribe.json  (<= ~7 s segments, for timing)
    python3 asr.py en transcribe          (English hint: romanised second opinion on unclear clips)
"""
import base64, json, sys, time
from pathlib import Path
import numpy as np, onnxruntime as ort, sherpa_onnx, kaldi_native_fbank as knf
from scipy.io import wavfile

HERE = Path(__file__).resolve().parent
M = "/home/user/models"
FINE = "--fine" in sys.argv
sys.argv = [x for x in sys.argv if x != "--fine"]
D = f"{M}/sherpa-onnx-whisper-turbo"
lang = sys.argv[1] if len(sys.argv) > 1 else "hi"
task = sys.argv[2] if len(sys.argv) > 2 else "transcribe"
sr, a = wavfile.read(HERE / "work" / "audio16k.wav"); a = a.astype(np.float32) / 32768

cfg = sherpa_onnx.VadModelConfig()
cfg.silero_vad.model = f"{M}/silero_vad.onnx"
cfg.silero_vad.min_silence_duration = 0.14 if FINE else 0.22
cfg.silero_vad.min_speech_duration = 0.12
cfg.silero_vad.threshold = 0.45
cfg.silero_vad.max_speech_duration = 7 if FINE else 20
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
print("vad segments", len(segs), flush=True)

so = ort.SessionOptions(); so.inter_op_num_threads = 1; so.intra_op_num_threads = 4
enc = ort.InferenceSession(f"{D}/turbo-encoder.int8.onnx", so, providers=["CPUExecutionProvider"])
dec = ort.InferenceSession(f"{D}/turbo-decoder.int8.onnx", so, providers=["CPUExecutionProvider"])
meta = enc.get_modelmeta().custom_metadata_map
NL, NCTX, NST, NMEL = (int(meta[k]) for k in ("n_text_layer", "n_text_ctx", "n_text_state", "n_mels"))
SOT, EOT, TRANSLATE, NOTS, NOSP, BLANK = (int(meta[k]) for k in
                                          ("sot", "eot", "translate", "no_timestamps", "no_speech", "blank_id"))
lang2id = dict(zip(meta["all_language_codes"].split(","), map(int, meta["all_language_tokens"].split(","))))
sot_seq = list(map(int, meta["sot_sequence"].split(","))) + [NOTS]
sot_seq[1] = lang2id[lang]
if task == "translate":
    sot_seq[2] = TRANSLATE
TOK = {}
for line in open(f"{D}/turbo-tokens.txt"):
    t, i = line.split()
    TOK[int(i)] = base64.b64decode(t)
ENC_OUT = [o.name for o in enc.get_outputs()]
DEC_IN = [i.name for i in dec.get_inputs()]
DEC_OUT = [o.name for o in dec.get_outputs()][:3]


def mel_of(wave):
    opts = knf.WhisperFeatureOptions(); opts.dim = NMEL
    fb = knf.OnlineWhisperFbank(opts)
    fb.accept_waveform(16000, wave); fb.input_finished()
    f = np.stack([fb.get_frame(i) for i in range(fb.num_frames_ready)])
    ls = np.log10(np.clip(f, 1e-10, None))
    ls = np.maximum(ls, ls.max() - 8.0)
    m = (ls + 4.0) / 4.0
    m = np.pad(m, ((0, 1500), (0, 0)))
    if m.shape[0] > 3000:
        m = np.pad(m[:2950], ((0, 50), (0, 0)))
    return m.T[None].astype(np.float32)


def decode(wave):
    ck, cv = enc.run(ENC_OUT, {enc.get_inputs()[0].name: mel_of(wave)})
    kc = np.zeros((NL, 1, NCTX, NST), np.float32); vc = np.zeros_like(kc)
    toks = np.array([sot_seq], np.int64); off = np.zeros(1, np.int64)
    out = []
    for step in range(440):
        logits, kc, vc = dec.run(DEC_OUT, dict(zip(DEC_IN, [toks, kc, vc, ck, cv, off])))
        off += toks.shape[1]
        lg = logits[0, -1].copy()
        if step == 0:
            lg[EOT] = lg[BLANK] = -np.inf
        lg[[NOTS, SOT, NOSP, TRANSLATE]] = -np.inf
        t = int(lg.argmax())
        if t == EOT:
            break
        out.append(t)
        toks = np.array([[t]], np.int64)
        if len(out) > 12 and len(set(out[-12:])) <= 2:      # repetition loop guard
            break
    return b"".join(TOK.get(i, b"") for i in out).decode("utf-8", "replace").strip()


res, t0 = [], time.time()
for s, dur in segs:
    pad = 0.12
    i0, i1 = int(max(0, s - pad) * sr), int(min(len(a) / sr, s + dur + pad) * sr)
    txt = decode(a[i0:i1])
    res.append(dict(s=round(s, 3), e=round(s + dur, 3), text=txt))
    print(f"[{s:7.2f}-{s + dur:7.2f}] {txt}", flush=True)
json.dump(res, open(HERE / "work" / f"segs_{'fine_' if FINE else ''}{lang}_{task}.json", "w"), indent=1, ensure_ascii=False)
print("done", round(time.time() - t0, 1))
