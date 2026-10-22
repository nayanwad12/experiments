import sys,os,multiprocessing as mp
from PIL import Image, ImageDraw
import reel
ts=[float(x) for x in sys.argv[2].split(",")]
out=sys.argv[1]
def r(t): return t, reel.render_frame(int(round(t*30)))
with mp.Pool(4) as p: res=p.map(r,ts)
os.makedirs(out,exist_ok=True)
ims=[]
for t,fr in res:
    im=Image.fromarray(fr); im.save(f"{out}/s_{t:05.2f}.jpg",quality=90)
    th=im.resize((360,640)); d=ImageDraw.Draw(th)
    # IG safe-zone guides
    d.rectangle([0,0,359,int(220/3)],outline=(255,0,255)); d.rectangle([0,int(1540/3),359,639],outline=(255,0,255)); d.line([int(960/3),int(1000/3),int(960/3),639],fill=(255,0,255))
    d.text((5,5),f"{t:.2f}",fill=(255,0,0)); ims.append(th)
cols=6; rows=(len(ims)+cols-1)//cols
sh=Image.new("RGB",(360*cols,640*rows),(0,0,0))
for k,im in enumerate(ims): sh.paste(im,((k%cols)*360,(k//cols)*640))
sh.save(f"{out}/sheet_{sys.argv[3]}.jpg",quality=85)
