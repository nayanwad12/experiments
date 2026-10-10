"""timeline.json -> per-part cut audio (48 kHz) with click-free joins, then cleaned + loudness-normalised."""
import json, subprocess
import numpy as np
from scipy.io import wavfile

FPS, SR = 30, 48000
SPF = SR // FPS
FADE = int(0.006 * SR)
sr, src = wavfile.read("audio48k.wav")
src = src.astype(np.float32) / 32768
if src.ndim == 2: src = src.mean(1)      # mic is mono, duplicated on both channels
tl = json.load(open("timeline.json"))
# playback of finished videos is system audio, ~20 dB hotter than the mic: bring it level with the voice
env = np.ones(len(src), np.float32)
for t0, t1, gdb, rin, rout in [(272.50, 275.30, -19, 0.03, 0.03), (775.30, 814.60, -19, 0.05, 1.0)]:
    g = 10 ** (gdb / 20); a, b = int(t0 * SR), int(t1 * SR); ri, ro = int(rin * SR), int(rout * SR)
    env[a:b] = g
    env[a:a + ri] = np.linspace(1, g, ri)
    env[b - ro:b] = np.linspace(g, 0 if rout > 0.5 else 1, ro)
src = src * env
ramp = np.linspace(0, 1, FADE, dtype=np.float32)
for p in tl:
    out, segs = [], p["segs"]
    for i, sg in enumerate(segs):
        a = src[sg["f0"] * SPF: sg["f1"] * SPF].copy()
        # micro-fade only at real cuts (a piece split for a freeze frame stays continuous)
        if i == 0 or segs[i - 1]["f1"] != sg["f0"]: a[:FADE] *= ramp
        if i == len(segs) - 1 or segs[i + 1]["f0"] != sg["f1"]: a[-FADE:] *= ramp[::-1]
        out.append(a)
    y = np.concatenate(out)
    assert len(y) == p["frames"] * SPF
    edge = int(0.25 * SR)                  # soft start / end of each lesson
    y[:edge] *= np.linspace(0, 1, edge); y[-edge:] *= np.linspace(1, 0, edge)
    wavfile.write(f"out/p{p['id']}_cut.wav", SR, (y * 32767).astype(np.int16))
    # clean: high-pass, light denoise, gentle compression, 2-pass loudnorm to -16 LUFS
    pre = "highpass=f=80,afftdn=nr=10:nf=-50:tn=1,acompressor=threshold=-24dB:ratio=2.5:attack=8:release=150:makeup=2"
    m = subprocess.run(["ffmpeg", "-hide_banner", "-i", f"out/p{p['id']}_cut.wav", "-af",
                        pre + ",loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    j = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
    ln = (f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
          f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"out/p{p['id']}_cut.wav", "-af",
                    pre + "," + ln + ",aresample=48000", "-ac", "2", "-c:a", "pcm_s16le", f"out/p{p['id']}.wav"], check=True)
    print(p["id"], "in", j["input_i"], "LUFS ->", "-16", flush=True)
