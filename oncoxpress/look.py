"""The film look: warm hazy grade (after the reference: golden haze, lifted green-teal blacks, cream highlights),
halation, vignette, chromatic fringe, gate weave and luma-weighted grain. All images float32 RGB in [0,1]."""
import cv2
import numpy as np

W, H = 1920, 1080
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / (W / 2)) ** 2 + ((_yy - H / 2) / (H / 2)) ** 2) / np.sqrt(2)
VIG = (1 - 0.30 * np.clip(_r, 0, 1) ** 2.2)[..., None].astype(np.float32)


def _curve(x):
    # lifted toe, gentle S, rolled-off cream shoulder
    x = np.clip(x, 0, 1.2)
    s = x * x * (3 - 2 * np.clip(x, 0, 1))          # smoothstep S
    y = 0.62 * x + 0.38 * s
    y = 0.055 + 0.90 * y
    return 0.96 - (0.96 - y) * (y > 0.80) * 0 + 0  # shoulder handled below


def grade(img, amt=1.0):
    """amt=1 full footage grade, lower for motion graphics so brand colours survive."""
    x = img.astype(np.float32)
    # warm the white balance
    x = x * np.array([1.045, 1.012, 0.925], np.float32)
    lum = x @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    # hue-selective moves: blues -> muted teal, greens -> olive/yellow-green
    hsv = cv2.cvtColor(np.clip(x, 0, 1), cv2.COLOR_RGB2HSV)       # H in degrees
    h, s = hsv[..., 0], hsv[..., 1]
    blue = np.clip(1 - np.abs(h - 215) / 45, 0, 1) * s
    green = np.clip(1 - np.abs(h - 120) / 50, 0, 1) * s
    tealcol = np.stack([lum * 0.80, lum * 1.02, lum * 1.00], -1)
    x = x + (tealcol - x) * (0.55 * blue)[..., None]
    olive = np.stack([lum * 0.97, lum * 1.06, lum * 0.72], -1)
    x = x + (olive - x) * (0.35 * green)[..., None]
    # overall saturation
    lum = x @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    x = lum[..., None] + (x - lum[..., None]) * 0.84
    # tone curve
    s_ = np.clip(x, 0, 1)
    s_ = s_ * s_ * (3 - 2 * s_)
    y = 0.60 * x + 0.40 * s_
    y = 0.050 + 0.905 * y
    hi = np.clip((y - 0.78) / 0.25, 0, 1)
    y = y - hi * hi * 0.06                               # roll highlights into cream
    # split tone
    l2 = y @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    sh = np.clip(1 - l2 / 0.45, 0, 1)[..., None]
    hl = np.clip((l2 - 0.55) / 0.45, 0, 1)[..., None]
    y = y + sh * np.array([-0.012, 0.010, 0.006], np.float32) + hl * np.array([0.022, 0.010, -0.028], np.float32)
    # golden haze veil
    y = y * 0.95 + np.array([0.060, 0.052, 0.030], np.float32) * 0.9
    return (img + (y - img) * amt).astype(np.float32)


def halation(x, k=1.0):
    l = x @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    m = np.clip((l - 0.70) / 0.3, 0, 1)
    src = (x * m[..., None]).astype(np.float32)
    small = cv2.resize(src, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    b1 = cv2.GaussianBlur(small, (0, 0), 3)
    b2 = cv2.GaussianBlur(small, (0, 0), 10)
    b = cv2.resize(0.6 * b1 + 0.4 * b2, (W, H), interpolation=cv2.INTER_LINEAR)
    tint = np.array([1.0, 0.55, 0.30], np.float32)
    return x + k * 0.16 * b * tint + k * 0.05 * b


def fringe(x, amt=1.0):
    if amt <= 0:
        return x
    out = x.copy()
    for ch, s in ((0, 1 + 0.0010 * amt), (2, 1 - 0.0010 * amt)):
        M = np.float32([[s, 0, (1 - s) * W / 2], [0, s, (1 - s) * H / 2]])
        out[..., ch] = cv2.warpAffine(x[..., ch], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return out


def grain(x, fi, amt=1.0):
    rng = np.random.default_rng(1000 + fi)
    g = rng.standard_normal((H // 2 + 2, W // 2 + 2)).astype(np.float32)
    g = cv2.resize(g, (W + 4, H + 4), interpolation=cv2.INTER_CUBIC)[2:H + 2, 2:W + 2]
    g2 = rng.standard_normal((H, W)).astype(np.float32)
    g = 0.75 * g + 0.45 * cv2.GaussianBlur(g2, (0, 0), 0.6)
    c = rng.standard_normal((H // 4, W // 4, 3)).astype(np.float32)
    c = cv2.resize(c, (W, H), interpolation=cv2.INTER_LINEAR)
    l = x @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    wgt = (0.55 + 1.6 * l * (1 - l))[..., None]          # strongest in the mids, like film
    return x + amt * wgt * (0.042 * g[..., None] + 0.010 * c)


def weave(x, fi, amt=1.0):
    t = fi / 24.0
    dx = amt * (0.35 * np.sin(t * 5.1) + 0.2 * np.sin(t * 13.7 + 1.3))
    dy = amt * (0.30 * np.sin(t * 4.3 + 0.7) + 0.2 * np.sin(t * 11.9))
    M = np.float32([[1.004, 0, dx - 0.002 * W], [0, 1.004, dy - 0.002 * H]])
    return cv2.warpAffine(x, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def finish(x, fi, grain_amt=1.0, hal=1.0, vig=1.0, fringe_amt=1.0, weave_amt=1.0):
    x = halation(x, hal)
    x = fringe(x, fringe_amt)
    x = x * (1 - vig + vig * VIG)
    flick = 1 + 0.006 * np.sin(fi * 2.1) * np.sin(fi * 0.37)
    x = x * flick
    x = weave(x, fi, weave_amt)
    x = grain(x, fi, grain_amt)
    return np.clip(x, 0, 1)
