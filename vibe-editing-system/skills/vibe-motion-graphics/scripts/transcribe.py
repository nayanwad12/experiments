"""transcribe: speech -> word-level timestamps with faster-whisper (runs locally, free).

    python3 scripts/transcribe.py raw/take1.mp4 -o work/words.json
    python3 scripts/transcribe.py raw/take1.mp4 --model large-v3 --lang en --prompt "Ideabro, Vibe Editing"

Outputs (next to -o):
    words.json       [{"w": "Hello", "s": 0.12, "e": 0.40, "p": 0.98}, ...]   seconds
    segments.json    sentence-level segments
    transcript.txt   readable transcript with timestamps; fix names here, then tell Claude

Models: tiny, base, small (default, good on CPU), medium, large-v3, turbo (best speed/quality on GPU).
The first run downloads the model (75 MB to 1.6 GB) and caches it.
--prompt helps spell names and jargon correctly (brand names, people, product terms).
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vibelib import fmt_time  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("media")
    ap.add_argument("-o", "--out", default="work/words.json")
    ap.add_argument("--model", default="small")
    ap.add_argument("--lang", default=None, help="en, hi, es ... (auto-detect if omitted)")
    ap.add_argument("--prompt", default=None, help="names/jargon to bias spelling")
    ap.add_argument("--device", default="auto", help="auto, cpu, cuda")
    ap.add_argument("--translate", action="store_true", help="translate speech to English")
    a = ap.parse_args()

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper missing:  python3 -m pip install faster-whisper")

    compute = "int8"
    if a.device in ("auto", "cuda"):
        try:
            import ctranslate2
            if ctranslate2.get_cuda_device_count() > 0:
                compute = "float16"
        except Exception:
            pass
    print(f"loading whisper '{a.model}' ({compute}) ...")
    model = WhisperModel(a.model, device=a.device, compute_type=compute)
    segments, info = model.transcribe(
        a.media, language=a.lang, initial_prompt=a.prompt, word_timestamps=True,
        vad_filter=True, vad_parameters={"min_silence_duration_ms": 300},
        task="translate" if a.translate else "transcribe", beam_size=5)
    print(f"language: {info.language} ({info.language_probability:.0%})  duration {info.duration:.1f}s")

    words, segs, lines = [], [], []
    for s in segments:
        segs.append({"s": round(s.start, 3), "e": round(s.end, 3), "text": s.text.strip()})
        lines.append(f"[{fmt_time(s.start)} - {fmt_time(s.end)}] {s.text.strip()}")
        print(lines[-1])
        for w in s.words or []:
            words.append({"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3),
                          "p": round(w.probability, 3)})

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(words, indent=0))
    (out.parent / "segments.json").write_text(json.dumps(segs, indent=1))
    (out.parent / "transcript.txt").write_text("\n".join(lines) + "\n")
    low = [w for w in words if w["p"] < 0.5]
    print(f"\n{len(words)} words -> {out}")
    if low:
        print(f"{len(low)} low-confidence words (check spelling):",
              ", ".join(f"{w['w']}@{w['s']:.1f}s" for w in low[:20]))


if __name__ == "__main__":
    main()
