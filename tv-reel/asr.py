import sherpa_onnx, wave, numpy as np, json, sys
d=sys.argv[1]
r=sherpa_onnx.OfflineRecognizer.from_transducer(encoder=d+"/encoder.int8.onnx",decoder=d+"/decoder.int8.onnx",joiner=d+"/joiner.int8.onnx",tokens=d+"/tokens.txt",model_type="nemo_transducer",num_threads=4)
w=wave.open(sys.argv[2]); a=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float32)/32768
s=r.create_stream(); s.accept_waveform(16000,a); r.decode_stream(s)
res=s.result
print(res.text)
toks=list(res.tokens); ts=list(res.timestamps); dur=list(getattr(res,'durations',[]) or [])
# group tokens into words (SentencePiece ▁ marks word start)
words=[]
for i,(t,st) in enumerate(zip(toks,ts)):
    d_=dur[i] if i<len(dur) else 0.08
    if t.startswith(" ") or t.startswith("▁") or not words:
        words.append([st,st+d_,t.strip(" ▁")])
    else:
        words[-1][2]+=t; words[-1][1]=st+d_
json.dump(words,open(sys.argv[3],"w"))
for w_ in words: print(f"{w_[0]:6.2f} {w_[1]:6.2f} {w_[2]}")
