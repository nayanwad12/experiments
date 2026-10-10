"""make_audio: voice + original hype bed + SFX cues, all timed from timeline.py.

    python3 make_audio.py            -> work/cues.json, work/voice.wav, work/music.wav
then: python3 vibe/audio_kit.py mix work/cues.json -o work/mix.wav --video work/picture.mp4 --out-video out/x.mp4
"""
import json
import subprocess
import sys

import timeline as TL

ev = TL.EV
sfx = [{"t": 0.0, "kind": "impact", "gain_db": -9}]
for t0, kind in TL.TRANSITIONS:
    if kind == "strips":
        sfx.append({"t": t0 - 0.28, "kind": "swish", "gain_db": -8})
    elif kind == "wipe":
        sfx.append({"t": t0 - 0.38, "kind": "whoosh", "dur": 0.7, "gain_db": -7})
    else:
        sfx.append({"t": t0 - 0.4, "kind": "whoosh", "dur": 0.6, "gain_db": -7})
edit = [w for w in TL.WORDS if w["k"] == "EDIT"][0]["s"]
sfx += [
    {"t": 0.25, "kind": "swish", "gain_db": -15},                     # arrow draws on
    {"t": edit + 0.25, "kind": "swish", "gain_db": -11},              # strike-through
    {"t": ev["phone"][0], "kind": "pop", "gain_db": -10},
    {"t": TL.W_("RECORDED") + 0.25, "kind": "shutter", "gain_db": -12},
    {"t": ev["prompt"][0], "kind": "pop", "gain_db": -10},
    {"t": ev["prompt"][0] + 0.25, "kind": "typing", "dur": TL.W_("WANTED") - ev["prompt"][0] - 0.1, "gain_db": -13},
    {"t": TL.W_("LINE"), "kind": "click", "gain_db": -6},
    {"t": TL.W_("SWIMMING"), "kind": "sparkle", "gain_db": -13},
    *[{"t": at - 0.02, "kind": "pop", "gain_db": -8, "pan": 0.25} for _, at in ev["chips"]],
    {"t": ev["done"], "kind": "ding", "gain_db": -7},
    {"t": ev["edittime"][0], "kind": "pop", "gain_db": -10},
    *[{"t": ev["edittime"][0] + 0.3 + i * 0.12, "kind": "tick", "gain_db": -13} for i in range(5)],
    {"t": ev["comment"][0], "kind": "pop", "gain_db": -9},
    {"t": TL.W_("SYSTEM", 30.0), "kind": "typing", "dur": 0.4, "gain_db": -12},
    {"t": TL.VIDEO_DUR + 0.3, "kind": "pop", "gain_db": -9},
    {"t": TL.VIDEO_DUR + 0.45, "kind": "impact", "gain_db": -4},
    {"t": TL.VIDEO_DUR + 0.62, "kind": "pop", "gain_db": -9},
    {"t": TL.VIDEO_DUR + 0.75, "kind": "sparkle", "gain_db": -10},
]
cues = {
    "duration": TL.DURATION,
    "voice": {"file": "work/voice.wav", "gain_db": 0, "t": 0},
    "music": {"file": "work/music.wav", "gain_db": -11, "duck_db": -7, "fade_out": 1.2},
    "sfx": sorted(sfx, key=lambda s: s["t"]),
}
json.dump(cues, open("work/cues.json", "w"), indent=1)
run = lambda *a: subprocess.run([sys.executable, "vibe/audio_kit.py", *a], check=True)  # noqa: E731
run("voice", TL.VIDEO, "-o", "work/voice.wav", "--denoise")
run("bed", "--mood", TL.MOOD, "--bpm", str(TL.BPM), "--seconds", f"{TL.DURATION + 0.5:.2f}", "--intro-bars", "0",
    "--seed", "11", "-o", "work/music.wav")
print("cues ->", "work/cues.json", len(sfx), "sfx")
