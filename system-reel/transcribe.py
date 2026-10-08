"""Word-level transcript of the raw take: work/words_raw.json [{w, s, e, p}] (seconds on the raw clock)."""
import json
import sys
import time
from pathlib import Path

from faster_whisper import WhisperModel

HERE = Path(__file__).resolve().parent
PROMPT = ("This video you're watching right now... I didn't edit it. My system did. On the left is the video "
          "straight from my phone. Comment SYSTEM and I'll send you the details.")

t0 = time.time()
m = WhisperModel(sys.argv[1] if len(sys.argv) > 1 else "medium.en", device="cpu", compute_type="int8", cpu_threads=4)
segs, _ = m.transcribe(str(HERE / "work" / "audio16k.wav"), word_timestamps=True, initial_prompt=PROMPT,
                       vad_filter=False, beam_size=5, condition_on_previous_text=False)
words = []
for s in segs:
    print(f"[{s.start:6.2f}-{s.end:6.2f}] {s.text}")
    for w in s.words:
        words.append(dict(w=w.word.strip(), s=round(w.start, 3), e=round(w.end, 3), p=round(w.probability, 3)))
(HERE / "work" / "words_raw.json").write_text(json.dumps(words, indent=0))
print("done", round(time.time() - t0), "s,", len(words), "words")
