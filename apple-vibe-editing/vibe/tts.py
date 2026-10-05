"""tts: local AI voiceover with Kokoro (free, Apache-2.0 weights, runs on CPU, no account).

    python3 vibe/tts.py "Vibe Editing. Say the vibe, and watch it come to life." -o work/vo.wav
    python3 vibe/tts.py --script work/script.txt -o work/vo.wav --voice am_michael --gap 0.35
    python3 vibe/tts.py --list

script.txt holds one line per take. Optional per-line settings, separated by |
    id | voice | speed | text
    hook | af_heart | 1.05 | Remember editing videos?
    Now there's a new way.                  <- plain lines use --voice / --speed

Outputs
    vo.wav       all lines joined with --gap seconds of silence
    vo_<id>.wav  each line on its own (re-use in edits)
    vo.json      start/end of every line inside vo.wav, so animation can be cued to the voice
For word-level cues run transcribe.py on vo.wav afterwards.

The first run downloads the model (~330 MB) to ~/.cache/ideabro-vibe/kokoro.
Voices: af_heart, af_bella, af_nicole, af_sarah, am_michael, am_adam, am_puck, am_fenrir,
        bf_emma, bf_isabella, bm_george, bm_lewis, hf_alpha, hf_beta, hm_omega, hm_psi (Hindi) ...
"""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
FILES = ["kokoro-v1.0.onnx", "voices-v1.0.bin"]
CACHE = Path.home() / ".cache" / "ideabro-vibe" / "kokoro"
LANG = {"a": "en-us", "b": "en-gb", "h": "hi", "e": "es", "f": "fr-fr", "i": "it", "p": "pt-br",
        "j": "ja", "z": "cmn"}


def ensure_models():
    CACHE.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        dst = CACHE / f
        if dst.exists() and dst.stat().st_size > 1000:
            continue
        print(f"downloading {f} (one time) ...")
        tmp = dst.with_suffix(".part")
        urllib.request.urlretrieve(BASE + f, tmp)
        tmp.rename(dst)
    return [str(CACHE / f) for f in FILES]


def trim(x, sr, thr=0.008, pad=0.04):
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return x
    return x[max(0, idx[0] - int(pad * sr)): min(len(x), idx[-1] + int(pad * sr))]


def parse_script(path, voice, speed):
    lines = []
    for i, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines()):
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        parts = [p.strip() for p in raw.split("|")]
        if len(parts) == 4:
            lines.append((parts[0], parts[1] or voice, float(parts[2] or speed), parts[3]))
        else:
            lines.append((f"{len(lines) + 1:02d}", voice, speed, raw))
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text", nargs="?")
    ap.add_argument("--script")
    ap.add_argument("-o", "--out", default="work/vo.wav")
    ap.add_argument("--voice", default="af_heart")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--gap", type=float, default=0.35, help="silence between lines (s)")
    ap.add_argument("--list", action="store_true", help="list voices")
    a = ap.parse_args()

    try:
        from kokoro_onnx import Kokoro
        import soundfile as sf
    except ImportError:
        sys.exit("missing packages:  python3 -m pip install kokoro-onnx soundfile")
    model, voices = ensure_models()
    k = Kokoro(model, voices)
    if a.list:
        print(", ".join(sorted(k.get_voices())))
        return
    if a.script:
        lines = parse_script(a.script, a.voice, a.speed)
    elif a.text:
        lines = [("01", a.voice, a.speed, a.text)]
    else:
        ap.error("give text or --script")

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    chunks, meta, t, sr = [], [], 0.0, 24000
    for lid, voice, speed, text in lines:
        lang = LANG.get(voice[0], "en-us")
        x, sr = k.create(text, voice=voice, speed=speed, lang=lang)
        x = trim(np.asarray(x, np.float32), sr)
        sf.write(str(out.with_name(f"{out.stem}_{lid}.wav")), x, sr)
        meta.append({"id": lid, "voice": voice, "text": text, "s": round(t, 3), "e": round(t + len(x) / sr, 3)})
        print(f"  {lid:8s} {len(x) / sr:5.2f}s  {text[:70]}")
        chunks += [x, np.zeros(int(a.gap * sr), np.float32)]
        t += len(x) / sr + a.gap
    full = np.concatenate(chunks[:-1]) if len(chunks) > 1 else chunks[0]
    sf.write(str(out), full, sr)
    out.with_suffix(".json").write_text(json.dumps(meta, indent=1))
    print(f"voiceover {len(full) / sr:.1f}s -> {out}  (+ {out.with_suffix('.json').name})")


if __name__ == "__main__":
    main()
