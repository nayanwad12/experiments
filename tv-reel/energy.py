import wave,numpy as np,json,sys
w=wave.open(sys.argv[1]); a=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float32)/32768
hop=160; n=len(a)//hop
rms=np.array([np.sqrt(np.mean(a[i*hop:(i+1)*hop]**2)+1e-12) for i in range(n)])
db=20*np.log10(rms)
np.save(sys.argv[2],db)
print("noise floor p10 %.1f  p50 %.1f p90 %.1f"%tuple(np.percentile(db,[10,50,90])))
thr=np.percentile(db,10)+12
sil=db<thr
# list silent runs >= 150ms
runs=[];i=0
while i<n:
    if sil[i]:
        j=i
        while j<n and sil[j]: j+=1
        if j-i>=15: runs.append((i/100,j/100))
        i=j
    else: i+=1
print("thr",thr)
for r in runs: print("sil %.2f-%.2f (%.2f)"%(r[0],r[1],r[1]-r[0]))
