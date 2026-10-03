import sys, glob, cv2, numpy as np
fs = sorted(glob.glob(sys.argv[1]))
out = sys.argv[2]; cols = int(sys.argv[3]) if len(sys.argv) > 3 else 2
ims = []
for f in fs:
    im = cv2.resize(cv2.imread(f), (960, 540))
    cv2.putText(im, f.split('/')[-1][:-4], (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
    ims.append(im)
while len(ims) % cols: ims.append(np.zeros_like(ims[0]))
rows = [np.concatenate(ims[i:i+cols], 1) for i in range(0, len(ims), cols)]
cv2.imwrite(out, np.concatenate(rows, 0), [cv2.IMWRITE_JPEG_QUALITY, 80])
