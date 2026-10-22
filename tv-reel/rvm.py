import onnxruntime as ort,numpy as np,sys,time
src=np.load(sys.argv[1],mmap_mode="r"); N=src.shape[0]
so=ort.SessionOptions(); so.intra_op_num_threads=4
sess=ort.InferenceSession(sys.argv[2],so,providers=["CPUExecutionProvider"])
out=np.lib.format.open_memmap(sys.argv[3],mode="w+",dtype=np.uint8,shape=(N,1280,720))
rec=[np.zeros((1,1,1,1),np.float32)]*4
dr=np.array([0.4],np.float32)
t=time.time()
for i in range(N):
    x=(src[i].astype(np.float32)/255).transpose(2,0,1)[None]
    fgr,pha,*rec=sess.run(None,{"src":x,"r1i":rec[0],"r2i":rec[1],"r3i":rec[2],"r4i":rec[3],"downsample_ratio":dr})
    out[i]=(pha[0,0]*255+0.5).astype(np.uint8)
    if i%100==0: print(i,time.time()-t,flush=True)
out.flush(); print("done",time.time()-t)
