import numpy as np,json
db=np.load("db.npy"); W=json.load(open("pk_words.json"))
thr=-55
v=db>thr
# smooth: fill gaps<60ms
runs=[];i=0;n=len(v)
while i<n:
    if v[i]:
        j=i
        while j<n and (v[j] or (j+6<n and v[j:j+6].any())): j+=1
        runs.append((i/100,j/100)); i=j
    else: i+=1
for a,b in runs:
    ws=[w[2] for w in W if w[0]<b and w[1]>a]
    pk=db[int(a*100):int(b*100)].max()
    print(f"{a:6.2f}-{b:6.2f} ({b-a:4.2f}) pk{pk:5.1f}  {' '.join(ws)}")
