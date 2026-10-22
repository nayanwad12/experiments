import numpy as np,json
db=np.load("db.npy"); W=json.load(open("pk_words.json"))
runs=[(0.48,1.69),(1.90,3.42),(3.83,4.53),(4.66,5.36),(5.47,6.00),(6.37,7.65),(7.90,8.28),(8.36,9.10),(9.16,10.00),(10.09,10.71),(10.83,11.18),(11.30,12.39),
(13.00,14.28),(14.47,15.01),(15.07,15.73),(15.86,16.45),(17.01,18.89),(19.25,20.38),(20.58,20.89),(20.97,21.18),(21.26,21.98),(22.56,23.48),(24.09,24.89),(24.96,25.47),
(27.64,29.08),(29.42,30.62),(31.08,31.89),(32.17,32.83),(33.27,34.09),(34.37,35.03),(35.22,36.76),(37.11,37.76),(38.05,38.88),(39.22,40.18),
(41.82,43.11),(43.54,44.54),(44.61,45.49),(46.00,46.68),(46.89,48.10),(48.36,49.09),(49.46,51.19),(51.79,53.45),
(56.79,58.34),(58.53,60.05),(60.12,61.42),(62.72,63.39),(63.66,64.16),(64.27,64.99),(65.31,65.87),(66.23,68.66),(69.15,70.89),(71.22,71.97),
(72.49,73.06),(73.24,74.40),(74.64,76.51),(76.88,77.53),(77.60,78.31),(78.42,79.62)]
# sentence ends (index of run that ends a sentence) -> slightly longer breath
send={1,11,12,15,20,23,28,33,34,41,44,49,51,54,57}
def ext(t,dirn,lim):
    i=int(round(t*100)); k=0
    while 0<i<len(db)-1 and db[i+dirn]>-62 and k<lim: i+=dirn;k+=1
    return i/100
R=[(ext(a,-1,12),ext(b,1,18)) for a,b in runs]
# build keep segments: merge runs whose gap < 0.30
segs=[]; cur=[R[0][0]-0.06,None]
for i in range(len(R)-1):
    gap=R[i+1][0]-R[i][1]
    removed = runs[i+1][0]-runs[i][1]>0.5 and False
    if gap<0.30 and not (runs[i][1],runs[i+1][0]) in [(25.47,27.64),(40.18,41.82),(53.45,56.79)]:
        continue
    po,pi=(0.13,0.08) if i in send else (0.09,0.07)
    cur[1]=R[i][1]+po; segs.append(cur); cur=[R[i+1][0]-pi,None]
cur[1]=R[-1][1]+0.18; segs.append(cur)
fr=lambda t: round(t*30)/30
segs=[(fr(a),fr(b)) for a,b in segs]
out=[];T=0
for a,b in segs: out.append([a,b,T]); T+=b-a
print("segments",len(segs),"output dur %.2f"%T)
for a,b,t in out: print("%6.2f-%6.2f -> %6.2f"%(a,b,t))
# map words
def m(t):
    for a,b,o in out:
        if a-0.25<=t<=b+0.05: return o+min(max(t-a,0),b-a)
    return None
ons=[a for a,b in R]
def snap(s):
    c=[o for o in ons if -0.30<=o-s<=0.30]
    return min(c,key=lambda o:abs(o-s)) if c else s
words=[]
for s,e,w in W:
    s=snap(s)
    o=m(s+0.02)
    if o is None: continue
    words.append([round(o,3),round(m(min(e,s+0.6)) or o+0.2,3),w,s])
json.dump({"segs":out,"dur":T,"words":words},open("edl.json","w"),indent=0)
print(len(words),"words kept"); print(" ".join(w[2] for w in words))
