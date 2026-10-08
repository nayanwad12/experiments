"""Whisper turbo (sherpa-onnx ONNX export) with our own greedy decoder.

Why: sherpa-onnx caps output at ~6 tokens/s and decodes tokens one by one, which breaks Hindi.
Usage: python3 whisper_np.py <lang> <chunks.json> <out.json> [prompt]
"""
import base64, json, sys
import numpy as np, onnxruntime as ort
from scipy.io import wavfile

M = "/home/user/models/sherpa-onnx-whisper-turbo"
so = ort.SessionOptions(); so.intra_op_num_threads = 4
enc = ort.InferenceSession(f"{M}/turbo-encoder.int8.onnx", so)
dec = ort.InferenceSession(f"{M}/turbo-decoder.int8.onnx", so)
meta = enc.get_modelmeta().custom_metadata_map
LANG = dict(zip(meta["all_language_codes"].split(","), map(int, meta["all_language_tokens"].split(","))))
SOT, EOT, NOTS, TRANS, PREV = (int(meta[k]) for k in ("sot", "eot", "no_timestamps", "transcribe", "sot_prev"))
VOC = {}
for line in open(f"{M}/turbo-tokens.txt"):
    p = line.split()
    VOC[int(p[-1])] = base64.b64decode(p[0]) if len(p) == 2 else b""
BYTES2ID = {v: k for k, v in VOC.items() if k < EOT and v}


def mel_filters(sr=16000, n_fft=400, n_mels=128):
    # librosa slaney mel filterbank
    def hz2mel(f):
        f = np.asarray(f, float); m = f / (200 / 3)
        return np.where(f >= 1000, 15 + np.log(np.maximum(f, 1e-9) / 1000) / (np.log(6.4) / 27), m)
    def mel2hz(m):
        m = np.asarray(m, float); f = m * 200 / 3
        return np.where(m >= 15, 1000 * np.exp((np.log(6.4) / 27) * (m - 15)), f)
    fft = np.linspace(0, sr / 2, n_fft // 2 + 1)
    pts = mel2hz(np.linspace(hz2mel(0), hz2mel(sr / 2), n_mels + 2))
    fd = np.diff(pts); ramps = pts[:, None] - fft[None]
    w = np.maximum(0, np.minimum(-ramps[:-2] / fd[:-1, None], ramps[2:] / fd[1:, None]))
    return w * (2.0 / (pts[2:n_mels + 2] - pts[:n_mels]))[:, None]


FB = mel_filters()


def log_mel(x):
    x = np.concatenate([x, np.zeros(480000 - len(x) if len(x) < 480000 else 0, np.float32)])[:480000]
    x = np.pad(x, 200, mode="reflect")
    win = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(400) / 400)
    idx = np.arange(400)[None] + 160 * np.arange(3001)[:, None]
    spec = np.abs(np.fft.rfft(x[idx] * win, axis=1)) ** 2
    m = np.log10(np.maximum(FB @ spec[:-1].T, 1e-10))
    m = np.maximum(m, m.max() - 8)
    return ((m + 4) / 4).astype(np.float32)[None]


def encode_text(s):
    """Greedy longest-match tokenisation over the byte vocab (good enough for a prompt)."""
    b = s.encode(); out = []; i = 0
    while i < len(b):
        for j in range(min(len(b), i + 24), i, -1):
            if b[i:j] in BYTES2ID:
                out.append(BYTES2ID[b[i:j]]); i = j; break
        else:
            i += 1
    return out


def transcribe(x, lang, prompt=""):
    ck, cv = enc.run(None, {"mel": log_mel(x)})
    toks = ([PREV] + encode_text(" " + prompt.strip())[-200:] if prompt else []) + [SOT, LANG[lang], TRANS, NOTS]
    kc = np.zeros((4, 1, 448, 1280), np.float32); vc = kc.copy()
    out, offset, cur = [], 0, toks
    for _ in range(440 - len(toks)):
        logits, kc, vc = dec.run(None, {"tokens": np.array([cur], np.int64), "in_n_layer_self_k_cache": kc,
                                        "in_n_layer_self_v_cache": vc, "n_layer_cross_k": ck,
                                        "n_layer_cross_v": cv, "offset": np.array([offset], np.int64)})
        offset += len(cur)
        lg = logits[0, -1].copy(); lg[EOT + 1:] = -np.inf
        if not out: lg[EOT] = -np.inf
        t = int(lg.argmax())
        if t == EOT: break
        out.append(t); cur = [t]
        if any(len(out) >= 3 * k and out[-k:] == out[-2 * k:-k] == out[-3 * k:-2 * k] for k in range(1, 9)):
            break  # repetition loop
    return b"".join(VOC[t] for t in out).decode("utf-8", "replace").strip()


if __name__ == "__main__":
    lang, src, dst = sys.argv[1:4]
    prompt = sys.argv[4] if len(sys.argv) > 4 else ""
    sr, a = wavfile.read("audio16k.wav"); a = a.astype(np.float32) / 32768
    res = []
    for c in json.load(open(src)):
        x = a[int(max(0, c["s"] - 0.15) * sr):int(min(len(a) / sr, c["e"] + 0.15) * sr)]
        t = transcribe(x, lang, prompt)
        res.append(dict(s=c["s"], e=c["e"], text=t))
        print(f"[{c['s']:6.2f}-{c['e']:6.2f}] {t}", flush=True)
    json.dump(res, open(dst, "w"), indent=1, ensure_ascii=False)
