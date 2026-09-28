import json, time
from faster_whisper import WhisperModel
t0=time.time()
m=WhisperModel("medium.en", device="cpu", compute_type="int8", cpu_threads=4)
print("load", time.time()-t0)
prompt=("I used to spend four hours editing one reel. Cutting clips, adding captions, keyframing every little animation. "
        "Then I stopped editing and started directing. Make it pop. Vibe Editing by Ideabro Studio. Link in bio.")
segs,info=m.transcribe("audio16k.wav", word_timestamps=True, initial_prompt=prompt, vad_filter=False, beam_size=5)
words=[]
for s in segs:
    print(f"[{s.start:6.2f}-{s.end:6.2f}] {s.text}")
    for w in s.words: words.append(dict(w=w.word.strip(), s=round(w.start,3), e=round(w.end,3), p=round(w.probability,3)))
json.dump(words, open("words.json","w"), indent=0)
print("done", time.time()-t0, len(words))
