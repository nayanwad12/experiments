"""Score candidate transcripts for a time range by Whisper log-likelihood (mean per token)."""
import sys, numpy as np, regex
from scipy.io import wavfile
import whisper_np as W

RANK = {v: k for k, v in W.VOC.items() if k < W.EOT and v}
PAT = regex.compile(r"""'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+""")


def bpe(text):
    out = []
    for piece in PAT.findall(text):
        parts = [bytes([b]) for b in piece.encode()]
        while len(parts) > 1:
            best = min(range(len(parts) - 1), key=lambda i: RANK.get(parts[i] + parts[i + 1], 1 << 30))
            if parts[best] + parts[best + 1] not in RANK: break
            parts[best:best + 2] = [parts[best] + parts[best + 1]]
        out += [RANK[p] for p in parts]
    return out


def score(x, lang, text):
    ck, cv = W.enc.run(None, {"mel": W.log_mel(x)})
    pre = [W.SOT, W.LANG[lang], W.TRANS, W.NOTS]; tgt = bpe(" " + text.strip()) + [W.EOT]
    seq = pre + tgt[:-1]
    kc = np.zeros((4, 1, 448, 1280), np.float32)
    lg, _, _ = W.dec.run(None, {"tokens": np.array([seq], np.int64), "in_n_layer_self_k_cache": kc,
                               "in_n_layer_self_v_cache": kc.copy(), "n_layer_cross_k": ck, "n_layer_cross_v": cv,
                               "offset": np.array([0], np.int64)})
    lg = lg[0, len(pre) - 1:].astype(np.float64)
    lp = lg - np.log(np.exp(lg - lg.max(1, keepdims=True)).sum(1, keepdims=True)) - lg.max(1, keepdims=True)
    return float(np.mean([lp[i, t] for i, t in enumerate(tgt)]))


if __name__ == "__main__":
    s, e, lang = float(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
    sr, a = wavfile.read("audio16k.wav"); a = a.astype(np.float32) / 32768
    x = a[int((s - 0.15) * sr):int((e + 0.15) * sr)]
    for c in sorted(sys.argv[4:], key=lambda c: -score(x, lang, c)):
        print(f"{score(x, lang, c):7.3f}  {c}")
