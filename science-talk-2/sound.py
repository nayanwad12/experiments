"""Video 2 soundtrack: cleaned voice + synthesised music bed (ducked) + word-cued SFX -> work/mix.wav (-14 LUFS).

Music: 'tech' bed for the explainer, crossfading into a soft 'cinematic' bed for the mom story and the
backwards loop, then back. Everything is synthesised (reels/common/audio_kit.py), no samples.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "reels" / "common"))
import audio_kit as ak  # noqa: E402
from vibelib import loudnorm_filter  # noqa: E402

W = HERE / "work"
SR = ak.SR


def main():
    import edit2 as edit  # cue times + SFX list
    dur = edit.TOTAL
    n = int(dur * SR)

    # voice: high-pass, gentle denoise, compression, de-ess
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(W / "voice.wav"), "-af",
                    "highpass=f=85,afftdn=nf=-28,equalizer=f=3200:t=q:w=1.2:g=2.5,"
                    "acompressor=threshold=-22dB:ratio=3.2:attack=6:release=110:makeup=4,deesser=i=0.35",
                    "-ar", str(SR), "-ac", "2", str(W / "voice_fx.wav")], check=True)
    voice = np.zeros((n, 2), np.float32)
    ak.place(voice, ak.read_audio(W / "voice_fx.wav"), 0.0)

    # music: tech bed, cinematic bed under the story
    tech = ak.music_bed("tech", seconds=dur + 2, bpm=100, seed=23)[:n]
    cine = ak.music_bed("cinematic", seconds=dur + 2, seed=5)[:n]
    tech = np.pad(tech, ((0, max(0, n - len(tech))), (0, 0)))
    cine = np.pad(cine, ((0, max(0, n - len(cine))), (0, 0)))
    t = np.arange(n) / SR
    a, b = edit.MOM[0], edit.MOM[1]

    def ramp(x0, x1):
        return np.clip((t - x0) / (x1 - x0), 0, 1)
    wc = ramp(a - 1.2, a + 0.3) * (1 - ramp(b - 0.3, b + 1.2))
    music = tech * (1 - wc)[:, None] * ak.db(-21) + cine * wc[:, None] * ak.db(-15)
    music *= ak.duck_gain(voice, depth_db=-7)[:, None]
    fade_in = np.clip(t / 0.4, 0, 1)
    fade_out = 1 - np.clip((t - (dur - 1.6)) / 1.6, 0, 1)
    music *= (fade_in * fade_out)[:, None]

    # sfx
    fx = np.zeros((n, 2), np.float32)
    for s in edit.SFX:
        kind = s["kind"]
        fn = ak.SFX[kind]
        clip = fn(s["dur"]) if "dur" in s and kind in ("whoosh", "riser", "typing") else fn()
        ak.place(fx, clip, s["t"], s["gain_db"], s.get("pan", 0.0))

    out = voice + music + fx
    peak = np.max(np.abs(out)) or 1
    if peak > 0.98:
        out = np.tanh(out / peak * 1.2) / np.tanh(1.2) * 0.98
    ak.write_wav(W / "mix_raw.wav", out)
    flt = loudnorm_filter(str(W / "mix_raw.wav"), lufs=-14.0, tp=-1.0)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(W / "mix_raw.wav"), "-af", flt, "-ar", str(SR),
                    str(W / "mix.wav")], check=True)
    print("-> work/mix.wav", round(dur, 2), "s,", len(edit.SFX), "sfx")


if __name__ == "__main__":
    main()
