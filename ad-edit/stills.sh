#!/bin/sh
# render stills at the given times and tile them into out/row.png
cd "$(dirname "$0")"
rm -f out/stills/*.png
python3 ${MOD:-edit}.py stills "$@" 2>/dev/null >/dev/null
python3 -c "
from PIL import Image; import glob
fs=sorted(glob.glob('out/stills/s_*.png')); ims=[Image.open(f).resize((270,480)) for f in fs]
row=Image.new('RGB',(270*len(ims),480)); [row.paste(im,(i*270,0)) for i,im in enumerate(ims)]; row.save('out/row.png')"
