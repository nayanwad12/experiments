"""sound: mix the narration, an original music bed and SFX, normalise for Reels, mux under the picture.

    from sound import Mix
    m = Mix(dur)
    m.voice(script.placements())               # [(wav, t)]
    m.music(bed_stereo, gain_db=-14, duck_db=-8)
    m.sfx("whoosh", 3.2, -8)                    # audio_kit SFX name, or a numpy clip
    m.finish("out/picture.mp4", "out/final.mp4")
"""

import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audio_kit as ak  # noqa: E402
from vibelib import ff, loudnorm_filter  # noqa: E402

SR = ak.SR


def reverb_ir(dur=1.4, decay=3.0, damp=5000, seed=3):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)).astype(np.float32) * np.exp(-decay * t)[:, None]
    ir = ak.filt(ir, "lp", damp)
    ir[0] = 0
    return ir / np.sqrt((ir ** 2).sum(0))


def verb(x, wet=0.2, ir=None):
    from scipy.signal import fftconvolve
    ir = reverb_ir() if ir is None else ir
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    y = np.stack([fftconvolve(x[:, i], ir[:, i])[: len(x)] for i in range(2)], 1)
    return (x * (1 - wet) + y * wet).astype(np.float32)


def broadcast(x, room=0.06):
    """radio-style voice chain: level, EQ (low cut, de-mud, presence, air), compression, de-ess, warmth, small room."""
    import music as M
    x = np.asarray(x, np.float32)
    x = x / (10 ** (M.active_rms_db(x) / 20) + 1e-9) * 10 ** (-20 / 20)          # every line at the same level
    x = M.filt(x, "hp", 85)
    x = x - 0.22 * M.filt(x, "bp", (220, 480)) + 0.32 * M.filt(x, "bp", (2400, 5200)) + 0.22 * M.filt(x, "hp", 9500)
    x = M.compressor(x, -24, 3.2, 0.004, 0.09, 6.0, knee=8)
    ess = M.filt(x, "bp", (5200, 9500))
    e = np.abs(ess).mean(1) if ess.ndim == 2 else np.abs(ess)
    e = np.convolve(e, np.ones(240) / 240, mode="same")
    k = np.clip((e - 0.02) / 0.05, 0, 0.6)
    x = x - ess * (k[:, None] if x.ndim == 2 else k)
    x = M.sat(x * 1.3, 1.2) / 1.3
    if room:
        x = x * (1 - room) + M.conv_reverb(x if x.ndim == 2 else np.stack([x, x], 1),
                                           M.reverb_ir(0.6, 9, 7000, 0.004, 5)) * room * 2.2
    return x.astype(np.float32)


class Mix:
    def __init__(self, dur):
        self.dur = dur
        self.n = int(dur * SR)
        self.vbus = np.zeros((self.n, 2), np.float32)
        self.mbus = np.zeros((self.n, 2), np.float32)
        self.fx = np.zeros((self.n, 2), np.float32)
        self.duck_db = -9

    def voice(self, placements, gain_db=0.0, warmth=True, chain="broadcast"):
        for path, t in placements:
            x = ak.read_audio(path)
            if chain == "broadcast":
                x = broadcast(x)
            elif warmth:   # gentle presence: low cut, a touch of air
                x = ak.filt(x, "hp", 70)
                x = x + 0.12 * ak.filt(x, "hp", 6000)
            ak.place(self.vbus, x, t, gain_db)
        return self

    def music(self, bed, gain_db=-14.0, duck_db=-9, t=0.0, fade_in=0.0, fade_out=1.2):
        bed = np.asarray(bed, np.float32)
        if bed.ndim == 1:
            bed = np.stack([bed, bed], 1)
        if fade_in:
            k = int(fade_in * SR)
            bed[:k] *= np.linspace(0, 1, k)[:, None]
        ak.place(self.mbus, bed, t, gain_db)
        if fade_out:
            k = int(fade_out * SR)
            self.mbus[-k:] *= np.linspace(1, 0, k)[:, None]
        self.duck_db = duck_db
        return self

    def sfx(self, kind, t, gain_db=-8.0, pan=0.0, **kw):
        clip = ak.SFX[kind](**kw) if isinstance(kind, str) else kind
        ak.place(self.fx, clip, t, gain_db, pan)
        return self

    def render(self, target_db=10.0):
        mus, fx = self.mbus, self.fx
        if np.abs(self.vbus).max() > 0:
            g = ak.duck_gain(self.vbus, min(self.duck_db, -10), release=0.4)
            mus = mus * g[:, None]
            fx = fx * (1 - 0.5 * (1 - g))[:, None]          # sfx dip half as much as the music
            # keep the narration clearly on top: trim the whole bed if speech is still masked
            on = np.abs(self.vbus).mean(1) > 0.01
            v = np.sqrt((self.vbus[on] ** 2).mean())
            b = np.sqrt(((mus + fx)[on] ** 2).mean()) + 1e-9
            short = target_db - 20 * np.log10(v / b)
            if short > 0:
                k = ak.db(-min(short, 9))
                mus, fx = mus * k, fx * k
        self.stems = {"voice": self.vbus, "music": mus, "fx": fx}
        out = mus + fx + self.vbus
        peak = np.max(np.abs(out)) or 1
        if peak > 0.98:
            out = np.tanh(out / peak * 1.3) / math.tanh(1.3) * 0.98
        return out

    def finish(self, picture, out, work="work", lufs=-14.0):
        work = Path(work)
        work.mkdir(parents=True, exist_ok=True)
        raw = work / "mix_raw.wav"
        ak.write_wav(raw, self.render())
        on = np.abs(self.vbus).mean(1) > 0.01
        if on.any():
            v = 20 * np.log10(np.sqrt((self.vbus[on] ** 2).mean()) + 1e-9)
            b = 20 * np.log10(np.sqrt(((self.stems["music"] + self.stems["fx"])[on] ** 2).mean()) + 1e-9)
            print(f"  voice-over-bed while speaking: {v - b:+.1f} dB")
        mixw = work / "mix.wav"
        ff("-i", raw, "-af", loudnorm_filter(raw, lufs, -1.0, 11), "-ar", str(SR), "-c:a", "pcm_s16le", mixw)
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        # delivery encode for Instagram: H.264 high, capped so every Reel stays under ~28 MB (shareable anywhere)
        mbps = min(12.0, 28 * 8 * 0.93 / self.dur - 0.3)
        ff("-i", picture, "-i", mixw, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "slow",
           "-crf", "18", "-maxrate", f"{mbps:.2f}M", "-bufsize", f"{2 * mbps:.2f}M", "-pix_fmt", "yuv420p", "-profile:v", "high",
           "-r", "30", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-t", f"{self.dur:.3f}",
           "-movflags", "+faststart", out)
        print("->", out)
        return out
