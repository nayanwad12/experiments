"""Recover the clean narration stem from the v3 film soundtrack.
The music and SFX in that mix were synthesised deterministically by sound.py, so they can be regenerated
sample-exactly and subtracted: undo the soft limiter, undo the fades, subtract fx, then solve for the voice
under the side-chained music (the duck depends on the voice envelope, so iterate)."""
import sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt
sys.path.insert(0, ".")
import sound
SR = sound.SR
sound.rng = np.random.default_rng(7)
m = sound.score()
fx = sound.design()
m = m / (np.max(np.abs(m)) + 1e-9) * 10 ** (-9 / 20)
# work/film_audio.wav: ffmpeg -i work/film_v3.mp4 -vn -ac 2 -ar 48000 work/film_audio.wav
sr, y = wavfile.read("work/film_audio.wav")
y = y.astype(np.float64) / 32767
N = min(len(y), len(m))
y, m, fx = y[:N], m[:N], fx[:N]
# alignment check against the AAC decode (encoder priming)
seg = slice(int(0.2 * SR), int(0.9 * SR))
PEAK = 0.7358622994093075
k = np.tanh(1.15)
mix = np.arctanh(np.clip(y / 10 ** (-1 / 20) * k, -0.999999, 0.999999)) * PEAK / 1.15
t = np.arange(N) / SR
fade = (np.clip(t / 0.6, 0, 1) * np.clip((sound.DUR - t) / 2.0, 0, 1))[:, None]
mix = np.where(fade > 0.03, mix / np.maximum(fade, 0.03), 0)
lp4 = butter(1, 4, "lp", fs=SR, output="sos"); lp3 = butter(1, 3, "lp", fs=SR, output="sos")
def duck_of(v):
    ve = np.sqrt(np.maximum(sosfiltfilt(lp4, v[:, 0] ** 2), 0) + 1e-10)
    d = 1 - 0.62 * np.clip((20 * np.log10(ve) + 50) / 20, 0, 1)
    return sosfiltfilt(lp3, d)
v = mix - fx * 0.9 - m * 0.85
for it in range(6):
    v = mix - fx * 0.9 - m * duck_of(v)[:, None] * 0.85
# residual in a no-speech stretch (music + fx only) tells us how clean the subtraction is
def db(x): return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
print("mix 0.2-0.9s:", round(db(mix[seg]), 1), "dB   residual:", round(db(v[seg]), 1), "dB")
print("music level in gap 21.0-21.3:", round(db((m*0.85)[int(21.0*SR):int(21.3*SR)]),1), "residual:", round(db(v[int(21.0*SR):int(21.3*SR)]),1))
print("voice level 2-4s:", round(db(v[2*SR:4*SR]), 1))
wavfile.write("work/voice_v3.wav", SR, (np.clip(v, -1, 1) * 32767).astype(np.int16))
