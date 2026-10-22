import subprocess,numpy as np,sys
W,H=720,1280
N=int(sys.argv[2])
mm=np.lib.format.open_memmap(sys.argv[3],mode="w+",dtype=np.uint8,shape=(N,H,W,3))
p=subprocess.Popen(["ffmpeg","-v","error","-i",sys.argv[1],"-vf","fps=30","-f","rawvideo","-pix_fmt","rgb24","-"],stdout=subprocess.PIPE)
i=0
while i<N:
    b=p.stdout.read(W*H*3)
    if len(b)<W*H*3: break
    mm[i]=np.frombuffer(b,np.uint8).reshape(H,W,3); i+=1
print("frames",i); mm.flush()
