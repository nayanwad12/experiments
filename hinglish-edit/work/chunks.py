"""Split VAD segments into <=3.2 s chunks at the quietest 40 ms point -> chunks.json."""
import json, numpy as np
from scipy.io import wavfile
sr, a = wavfile.read("audio16k.wav"); a = a.astype(np.float32) / 32768
hop = 160; rms = np.sqrt(np.convolve(a**2, np.ones(640)/640, "same")[::hop] + 1e-12)
out = []
def split(s, e):
    if e - s <= 3.2: out.append((round(s, 2), round(e, 2))); return
    lo, hi = int((s + 1.0) * 100), int((e - 1.0) * 100)
    k = lo + int(np.argmin(rms[lo:hi]))
    split(s, k / 100); split(k / 100, e)
for sg in json.load(open("segs_turbo_en.json")): split(sg["s"], sg["e"])
json.dump([dict(s=s, e=e) for s, e in out], open("chunks.json", "w"))
print(len(out), out)
