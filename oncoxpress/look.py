"""The film look: clean, warm and soft — premium healthcare, not gritty.

Grade: gently warm white balance, true (not lifted) blacks with a hint of evergreen in the shadows, soft filmic
contrast with a creamy highlight roll-off, skin kept natural, blues eased toward the brand's teal-green.
Finish: a soft bloom on the highlights and a light vignette. No grain, no halation, no weave, no flicker —
only an invisible sub-LSB dither so gradients on the paper backgrounds never band.
All images float32 RGB in [0,1]."""
import cv2
import numpy as np

W, H = 1920, 1080
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / (W / 2)) ** 2 + ((_yy - H / 2) / (H / 2)) ** 2) / np.sqrt(2)
VIG = (1 - 0.18 * np.clip(_r, 0, 1) ** 2.4)[..., None].astype(np.float32)
LUM = np.array([0.2126, 0.7152, 0.0722], np.float32)


def grade(img, amt=1.0):
    """amt=1 full footage grade, lower for motion graphics so brand colours survive."""
    x = img.astype(np.float32)
    # warm, but only just
    x = x * np.array([1.025, 1.005, 0.965], np.float32)
    # blues -> calm teal (monitors, scrubs, walls sit with the brand green); leave skin alone
    hsv = cv2.cvtColor(np.clip(x, 0, 1), cv2.COLOR_RGB2HSV)
    h, s = hsv[..., 0], hsv[..., 1]
    blue = np.clip(1 - np.abs(h - 212) / 40, 0, 1) * np.clip(s * 1.5, 0, 1)
    lum = x @ LUM
    teal = np.stack([lum * 0.86, lum * 1.03, lum * 1.02], -1)
    x = x + (teal - x) * (0.35 * blue)[..., None]
    # saturation: a touch under neutral for elegance
    lum = x @ LUM
    x = lum[..., None] + (x - lum[..., None]) * 0.93
    # soft filmic contrast: gentle S, blacks at ~2 %, highlights rolled into cream
    c = np.clip(x, 0, 1)
    s_ = c * c * (3 - 2 * c)
    y = 0.72 * x + 0.28 * s_
    y = 0.018 + 0.975 * y
    hi = np.clip((y - 0.82) / 0.22, 0, 1)
    y = y - hi * hi * 0.045
    # split tone: whisper of evergreen in the shadows, warm cream in the highlights
    l2 = y @ LUM
    sh = np.clip(1 - l2 / 0.40, 0, 1)[..., None]
    hl = np.clip((l2 - 0.60) / 0.40, 0, 1)[..., None]
    y = y + sh * np.array([-0.006, 0.006, 0.002], np.float32) + hl * np.array([0.010, 0.004, -0.012], np.float32)
    return (img + (y - img) * amt).astype(np.float32)


def bloom(x, k=1.0):
    l = x @ LUM
    m = np.clip((l - 0.72) / 0.28, 0, 1)
    src = (x * m[..., None]).astype(np.float32)
    small = cv2.resize(src, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    b = cv2.GaussianBlur(small, (0, 0), 6)
    b = cv2.resize(b, (W, H), interpolation=cv2.INTER_LINEAR)
    return x + k * 0.10 * b * np.array([1.0, 0.97, 0.92], np.float32)


def finish(x, fi, grain_amt=1.0, hal=1.0, vig=1.0, fringe_amt=0.0, weave_amt=0.0):
    """grain_amt/fringe/weave are kept for call compatibility; the clean look uses none of them."""
    x = bloom(x, hal)
    x = x * (1 - vig + vig * VIG)
    # invisible dither (< 1 code value) to keep the paper gradients smooth after 8-bit encode
    rng = np.random.default_rng(1000 + fi)
    x = x + (rng.random((H, W, 1), dtype=np.float32) - 0.5) * (1.0 / 255)
    return np.clip(x, 0, 1)
