import sherpa_onnx, wave, numpy as np, sys
d=sys.argv[1]
r=sherpa_onnx.OfflineRecognizer.from_whisper(encoder=d+"/medium.en-encoder.int8.onnx",decoder=d+"/medium.en-decoder.int8.onnx",tokens=d+"/medium.en-tokens.txt",num_threads=4)
w=wave.open(sys.argv[2]); a=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float32)/32768
for s0,s1 in [(0,26.6),(26.6,41.5),(41.5,56.4),(56.4,69.0),(69.0,82.3)]:
    s=r.create_stream(); s.accept_waveform(16000,a[int(s0*16000):int(s1*16000)]); r.decode_stream(s)
    print(f"[{s0}-{s1}]",s.result.text)
