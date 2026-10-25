"""core: words, cut list and speed for the 40 s "my system edited this" take.

Every pause between phrases is trimmed to a breath, the off-script word after the CTA is dropped, and the
whole edit then plays at SPEED (1.15x): picture by re-timing the 60 fps source frames, voice with a
pitch-preserving rubberband stretch. Times below are on the OUTPUT clock unless named src/raw.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "reels" / "common"))
import audio_kit as ak  # noqa: E402
from vibelib import ff, loudnorm_filter  # noqa: E402

cv2.setNumThreads(1)
W, H, FPS = 1080, 1920, 30
SRC_FPS = 60
SPEED = 1.15
FR = HERE / "work" / "frames"
NSRC = len(list(FR.glob("f_*.jpg")))
END_HOLD = 2.2                      # seconds (output) the end card holds after the last word

WORDS = json.loads((HERE / "work" / "words.json").read_text())
for i, w in enumerate(WORDS):
    w["i"] = i
    w["k"] = re.sub(r"[^a-z0-9']", "", w["d"].lower())
NPH = max(w["ph"] for w in WORDS) + 1
PH = [[w["i"] for w in WORDS if w["ph"] == k] for k in range(NPH)]


def build_edl():
    """[(src_a, src_b, out1_a, dur1, i0, i1)] on the 1x concatenated clock."""
    edl, t = [], 0.0
    for k in range(NPH):
        i0, i1 = PH[k][0], PH[k][-1]
        s, e = WORDS[i0]["s"], WORDS[i1]["e"]
        a = s - 0.07
        if i0 > 0:
            a = max(a, (WORDS[i0 - 1]["e"] + s) / 2)
        b = e + 0.1
        if i1 + 1 < len(WORDS):
            b = min(b, (e + WORDS[i1 + 1]["s"]) / 2)
        if k == NPH - 1:
            b = min(e + END_HOLD * SPEED, 40.9)              # stop before the off-script "interesting" (41.1 s)
        edl.append((max(0.0, a), b, t, b - max(0.0, a), i0, i1))
        t += b - max(0.0, a)
    return edl, t


EDL, TOTAL1 = build_edl()
TOTAL = TOTAL1 / SPEED
RUN_STARTS = [r[2] / SPEED for r in EDL]
for a, b, o, d, i0, i1 in EDL:
    for j in range(i0, i1 + 1):
        WORDS[j]["os"] = (o + WORDS[j]["s"] - a) / SPEED
        WORDS[j]["oe"] = (o + WORDS[j]["e"] - a) / SPEED
SPEECH_END = WORDS[-1]["oe"]


def src_at(t):
    t1 = t * SPEED
    for a, b, o, d, _, _ in EDL:
        if t1 < o + d:
            return a + max(0.0, t1 - o)
    return EDL[-1][1]


def _find(seq, n=1):
    toks = re.sub(r"[^a-z0-9' ]", "", seq.lower()).split()
    hits = 0
    for i in range(len(WORDS) - len(toks) + 1):
        if all(WORDS[i + j]["k"] == toks[j] for j in range(len(toks))):
            hits += 1
            if hits == n:
                return i, i + len(toks) - 1
    raise KeyError(seq)


class P:
    """a spoken phrase on the output clock: .s .e, .w(j) word start, .we(j) word end"""

    def __init__(self, seq, n=1):
        self.i0, self.i1 = _find(seq, n)
        self.s, self.e = WORDS[self.i0]["os"], WORDS[self.i1]["oe"]

    def w(self, j):
        return WORDS[self.i0 + j]["os"]

    def we(self, j):
        return WORDS[self.i0 + j]["oe"]


def run_start(p):
    return max(r for r in RUN_STARTS if r <= p.s + 1e-6)


# ================================================================== source
_cache = {}


def frame_rgb(fi):
    fi = int(min(max(fi, 0), NSRC - 1))
    if fi not in _cache:
        if len(_cache) > 12:
            _cache.pop(next(iter(_cache)))
        _cache[fi] = cv2.imread(str(FR / f"f_{fi + 1:05d}.jpg"))[..., ::-1]
    return _cache[fi]


_ALPHA = None


def alpha_small(fi):
    global _ALPHA
    if _ALPHA is None:
        _ALPHA = np.load(HERE / "work" / "alpha.npy", mmap_mode="r")
    return np.asarray(_ALPHA[int(min(max(fi, 0), len(_ALPHA) - 1))])


TRACK = np.load(HERE / "work" / "track.npy")
_k = np.ones(61) / 61
FACE_X = np.convolve(np.pad(TRACK[:, 1], 30, mode="edge"), _k, "valid")
FACE_Y = np.convolve(np.pad(TRACK[:, 0], 30, mode="edge"), _k, "valid") + 235


def face(ts):
    fi = int(min(max(round(ts * SRC_FPS), 0), len(FACE_X) - 1))
    return 0.5 * FACE_X[fi] + 0.5 * 540, FACE_Y[fi]


def head_top_src(ts):
    return TRACK[int(min(max(round(ts * SRC_FPS), 0), len(TRACK) - 1)), 0]


_VENV = None


def voice_env(ts):
    global _VENV
    if _VENV is None:
        import wave
        with wave.open(str(HERE / "work" / "audio16k.wav")) as wv:
            x = np.frombuffer(wv.readframes(wv.getnframes()), np.int16).astype(np.float32) / 32768
        e = np.sqrt(np.convolve(x ** 2, np.ones(400) / 400, "same"))[::160]
        _VENV = np.clip(e / (np.percentile(e, 98) + 1e-6), 0, 1)
    i = int(ts * 100)
    return float(_VENV[i]) if 0 <= i < len(_VENV) else 0.0


# ================================================================== voice
def build_voice():
    """cleaned voice, cut to the EDL with short crossfades, then stretched to SPEED (pitch kept)."""
    SR = ak.SR
    work = HERE / "work"
    clean = work / "voice_clean.wav"
    if not clean.exists():
        ff("-i", str(HERE / "raw" / "take.mp4"), "-vn", "-af",
           "highpass=f=85,afftdn=nf=-30:tn=1,equalizer=f=220:t=q:w=1.2:g=-2,equalizer=f=3200:t=q:w=1.5:g=2.5,"
           "equalizer=f=9000:t=h:w=0.7:g=1.5,acompressor=threshold=-21dB:ratio=3.2:attack=5:release=90:makeup=4,"
           "deesser=i=0.35,alimiter=limit=0.95", "-ar", str(SR), "-ac", "2", str(clean))
    raw = ak.read_audio(clean)
    n = int(TOTAL1 * SR) + 1
    v = np.zeros((n, 2), np.float32)
    xf = int(0.012 * SR)
    for a, b, o, d, i0, i1 in EDL:
        bb = min(b, WORDS[i1]["e"] + 0.15)
        seg = raw[int(a * SR):int(bb * SR)].copy()
        if len(seg) > 2 * xf:
            r = np.linspace(0, 1, xf, dtype=np.float32)[:, None]
            seg[:xf] *= r
            seg[-xf:] *= r[::-1]
        i = int(o * SR)
        seg = seg[:max(0, n - i)]
        v[i:i + len(seg)] += seg
    ak.write_wav(work / "voice_1x.wav", v)
    ff("-i", str(work / "voice_1x.wav"), "-af", f"rubberband=tempo={SPEED}:pitchq=quality:transients=smooth:formant=preserved",
       "-ar", str(SR), "-ac", "2", str(work / "voice_fast.wav"))
    out = ak.read_audio(work / "voice_fast.wav")
    m = int(TOTAL * SR) + 1
    return np.pad(out, ((0, max(0, m - len(out))), (0, 0)))[:m]


def finish(picture, audio, out, vbr="5.5M"):
    """delivery file: H.264 high, two-pass, AAC 48k, -14 LUFS, < 30 MB for a ~30 s reel."""
    ln = loudnorm_filter(audio)
    log = str(HERE / "work" / "x264pass")
    common = ["-c:v", "libx264", "-preset", "slow", "-b:v", vbr, "-maxrate", "8M", "-bufsize", "16M",
              "-pix_fmt", "yuv420p", "-profile:v", "high", "-r", str(FPS), "-passlogfile", log]
    ff("-i", str(picture), "-map", "0:v:0", *common, "-pass", "1", "-an", "-f", "null", "/dev/null")
    ff("-i", str(picture), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", *common, "-pass", "2", "-af", ln,
       "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out))
    print("->", out)


if __name__ == "__main__":
    print(f"raw {NSRC / SRC_FPS:.1f}s -> cut {TOTAL1:.2f}s -> at {SPEED}x {TOTAL:.2f}s  (speech ends {SPEECH_END:.2f})")
    for a, b, o, d, i0, i1 in EDL:
        print(f"  src {a:6.2f}-{b:6.2f}  out {o / SPEED:6.2f}  " + " ".join(WORDS[j]["d"] for j in range(i0, i1 + 1)))
