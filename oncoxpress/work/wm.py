"""Gemini sparkle removal: reverse the alpha blend with the estimated matte, then heal the anti-aliased rim."""
import cv2, numpy as np, os
H = os.path.dirname(os.path.abspath(__file__))
X0, Y0, X1, Y1 = 1120, 560, 1200, 640
A = np.load(os.path.join(H, "wm_alpha.npy"))[..., None]
DIL = np.load(os.path.join(H, "wm_dil.npy"))
RIM = (cv2.dilate((A[..., 0] > 0.04).astype(np.uint8), np.ones((5, 5), np.uint8)) -
       cv2.erode((A[..., 0] > 0.2).astype(np.uint8), np.ones((3, 3), np.uint8))).clip(0, 1)

def clean(f):
    p = f[Y0:Y1, X0:X1].astype(np.float32)
    rec = np.clip((p - 255 * A) / (1 - A), 0, 255).astype(np.uint8)
    rec = cv2.inpaint(rec, RIM * 255, 3, cv2.INPAINT_TELEA)
    # feather the patch back so there is no seam
    m = cv2.GaussianBlur(DIL.astype(np.float32), (0, 0), 3)[..., None]
    out = f.copy()
    out[Y0:Y1, X0:X1] = (rec * m + p * (1 - m)).astype(np.uint8)
    return out
