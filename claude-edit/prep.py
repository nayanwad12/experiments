"""One-off prep: clean plate (LaMa inpaint of the empty room), palm track, clip frames for the floating screens.

    python3 prep.py   (needs work/frames.npy + work/alpha.npy from work/matte.py)
"""

import os
import subprocess

import cv2
import numpy as np
import onnxruntime as ort

from common import FFMPEG, HERE, SH, SW, WORK

MODELS = "/home/user/models"


def plate():
    """Empty-room plate: masked temporal median where the room is ever visible; LaMa for the wall/door he
    always covers; the headboard + sheet behind his body rebuilt by extending their visible texture."""
    f = np.load(os.path.join(WORK, "frames.npy"), mmap_mode="r")
    a = np.load(os.path.join(WORK, "alpha.npy"), mmap_mode="r")
    last = int(83.8 * 30)                               # he reaches for the phone after this
    idx = np.arange(0, last, 4)
    k5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))
    stack = np.stack([f[i] for i in idx]).astype(np.float32)
    cov = np.stack([cv2.dilate((a[i] > 0).astype(np.uint8), k5) for i in idx]) > 0
    stack[cov] = np.nan
    med = np.nanmedian(stack, axis=0)
    hole = np.isnan(med[..., 0])
    med = np.where(np.isnan(med), 0, med).astype(np.uint8)
    mask = cv2.dilate(hole.astype(np.uint8) * 255, np.ones((17, 17), np.uint8))
    ys, xs = np.nonzero(mask)
    x0 = int(np.clip((xs.min() + xs.max()) // 2 - 256, 0, SW - 512))
    ci = cv2.copyMakeBorder(med[:, x0:x0 + 512], 0, 512 - SH, 0, 0, cv2.BORDER_REFLECT)
    cm = cv2.copyMakeBorder(mask[:, x0:x0 + 512], 0, 512 - SH, 0, 0, cv2.BORDER_CONSTANT, value=0)
    so = ort.SessionOptions(); so.intra_op_num_threads = 4
    s = ort.InferenceSession(f"{MODELS}/lama.onnx", so, providers=["CPUExecutionProvider"])
    o = s.run(None, {"image": (ci.astype(np.float32) / 255).transpose(2, 0, 1)[None].copy(),
                     "mask": (cm > 127).astype(np.float32)[None, None]})[0][0].transpose(1, 2, 0)
    lama = med.copy()
    lama[:, x0:x0 + 512] = np.clip(o, 0, 255).astype(np.uint8)[:SH]
    # rebuild headboard (y 298..402) and sheet (y 402..) behind him from the visible texture on the right
    synth = lama.copy()
    HB0, HB1, XL, XV = 298, 386, 400, 628
    period = 800 - XV
    for x in range(XL, XV):
        d = XV - x
        xs_ = XV + (d % period) if (d // period) % 2 == 0 else 800 - (d % period)
        synth[HB0:HB1, x] = med[HB0:HB1, xs_]
    edge = slice(XL - 2, XL + 6)
    synth[HB0:HB1, edge] = (synth[HB0:HB1, edge].astype(np.float32) * 0.55).astype(np.uint8)
    # sheet: clean red, row colour taken from the visible sheet, plus a little blurred grain
    rng = np.random.default_rng(4)
    vis = med[HB1 + 12:, 600:675].reshape(-1, 3).astype(np.float32)
    red = vis[(vis[:, 0] > vis[:, 1] + 60) & (vis[:, 0] < 215)]
    base = np.median(red, axis=0)
    rows = SH - HB1
    shade = np.linspace(1.04, 0.9, rows)[:, None, None]
    grain = cv2.GaussianBlur(rng.normal(0, 1, (rows, XV - XL + 25)).astype(np.float32), (0, 0), 3)[..., None] * 6
    synth[HB1:, XL - 25:XV] = np.clip(base[None, None] * shade + grain, 0, 255).astype(np.uint8)
    # the door and the wall strip left of it continue straight down behind his arm
    door = np.zeros((1, 382 - 270, 3), np.float32)
    for x in range(270, 382):
        vis_rows = np.nonzero(~hole[200:297, x])[0]
        door[0, x - 270] = med[200 + (vis_rows[-1] if len(vis_rows) else 0), x]
    door = cv2.GaussianBlur(door, (1, 3), 0)
    synth[297:, 270:382] = np.clip(door * np.linspace(1, 0.85, SH - 297)[:, None, None], 0, 255).astype(np.uint8)
    synth[250:297, 270:382] = np.where(hole[250:297, 270:382, None], door, synth[250:297, 270:382])
    synth[300:, 232:270] = np.repeat(med[280:300, 232:270].mean(0, keepdims=True), SH - 300, 0).astype(np.uint8)
    # plain wall right of the door: smooth quadratic fit to the visible wall + grain, then redraw the curtain rod
    yy, xx = np.mgrid[0:SH, 0:SW].astype(np.float32)
    wall_vis = (~hole) & (xx >= 390) & (xx < 760) & (yy >= 45) & (yy < 290) & (np.abs(yy - (141 - (xx - 383) * 23 / 275)) > 6)
    wall_vis &= med.astype(np.float32).mean(2) > 150
    X = np.stack([np.ones_like(xx), xx / SW, yy / SH, (xx / SW) ** 2, (yy / SH) ** 2, xx * yy / SW / SH], -1)
    wfill = np.zeros((SH, SW, 3), np.float32)
    for c in range(3):
        coef, *_ = np.linalg.lstsq(X[wall_vis], med[..., c][wall_vis].astype(np.float32), rcond=None)
        wfill[..., c] = X @ coef
    # diffuse the visible residual (vignette, soft light) into the hole so the fit meets the real wall seamlessly
    resid = np.clip(med.astype(np.float32) - wfill + 128, 0, 255).astype(np.uint8)
    rmask = (hole | ~(wall_vis | hole)).astype(np.uint8) * 255
    rmask[:, :382] = 255
    rmask[HB0:] = 255
    rmask = cv2.dilate(hole.astype(np.uint8) * 255, np.ones((9, 9), np.uint8))
    rmask[:, :392] = 255
    resid = cv2.inpaint(resid, rmask, 25, cv2.INPAINT_TELEA).astype(np.float32) - 128
    resid = cv2.GaussianBlur(resid, (0, 0), 6)
    wfill += resid
    wfill += cv2.GaussianBlur(rng.normal(0, 1, (SH, SW)).astype(np.float32), (0, 0), 1.2)[..., None] * 1.5
    wreg = ((xx >= 382) & (yy < HB0)) | ((xx >= 382) & (xx < XL) & (yy < HB1))
    synth[wreg] = np.clip(wfill[wreg], 0, 255).astype(np.uint8)
    rod = np.zeros((SH, SW), np.uint8)
    cv2.line(rod, (383, 142), (660, 119), 255, 4, cv2.LINE_AA)
    rodpx = med[112:128, 560:650].reshape(-1, 3).astype(np.float32)
    rodc = rodpx[rodpx.mean(1) < np.percentile(rodpx.mean(1), 12)].mean(0)
    ra = (rod.astype(np.float32) / 255)[..., None]
    synth[:] = (synth * (1 - ra) + rodc * ra).astype(np.uint8)
    reg = np.zeros((SH, SW), np.float32)
    reg[HB0:, XL - 25:XV] = 1
    reg[300:, 232:XL] = 1
    reg[40:HB0, 381:760] = 1
    reg = cv2.GaussianBlur(reg, (0, 0), 2)[..., None]
    fill = (synth * reg + lama * (1 - reg)).astype(np.float32)
    soft = cv2.GaussianBlur(mask, (0, 0), 2).astype(np.float32)[..., None] / 255
    res = (fill * soft + med * (1 - soft)).astype(np.uint8)
    np.save(os.path.join(WORK, "plate.npy"), res)
    cv2.imwrite(os.path.join(WORK, "plate.png"), cv2.cvtColor(res, cv2.COLOR_RGB2BGR))
    print("plate done", x0)


def palm_track():
    """Template-match the open palm from 4.6s to 16.5s -> work/palm.npy [(frame, x, y)]."""
    f = np.load(os.path.join(WORK, "frames.npy"), mmap_mode="r")
    ref_i = int(7.0 * 30)
    x, y = 195, 322
    tpl = cv2.cvtColor(np.ascontiguousarray(f[ref_i][y - 22:y + 22, x - 50:x + 50]), cv2.COLOR_RGB2GRAY)
    out = []
    for i in range(int(4.5 * 30), int(16.6 * 30)):
        g = cv2.cvtColor(np.ascontiguousarray(f[i]), cv2.COLOR_RGB2GRAY)
        y0, y1, x0, x1 = y - 70, y + 70, max(0, x - 120), x + 120
        r = cv2.matchTemplate(g[y0:y1, x0:x1], tpl, cv2.TM_CCOEFF_NORMED)
        _, mx, _, loc = cv2.minMaxLoc(r)
        out.append((i, x0 + loc[0] + 50, y0 + loc[1] + 22, mx))
    out = np.array(out, np.float32)
    # smooth, and hold the last confident position when the match is weak
    good = out[:, 3] > 0.55
    for k in range(len(out)):
        if not good[k]:
            out[k, 1:3] = out[k - 1, 1:3] if k else (x, y)
    for c in (1, 2):
        out[:, c] = np.convolve(np.pad(out[:, c], 4, mode="edge"), np.ones(9) / 9, mode="valid")
    np.save(os.path.join(WORK, "palm.npy"), out)
    print("palm", out[::30, :4].round(2))


def clips():
    """Decode the three screen clips (repo renders) into small frame arrays."""
    root = os.path.dirname(HERE)
    spec = [("promo", "vibe-editing-promo/out/vibe_editing_promo.mp4", 0.0, 270, 480),
            ("expl", "explainer/out/explainer.mp4", 33.0, 270, 480),
            ("evo", "evolution-light/evolution_of_light.mp4", 38.0, 480, 270),
            ("promo2", "vibe-editing-promo/out/vibe_editing_promo.mp4", 17.0, 270, 480)]
    for name, path, ss, w, h in spec:
        p = subprocess.run([FFMPEG, "-v", "error", "-ss", str(ss), "-t", "7", "-i", os.path.join(root, path),
                            "-vf", f"fps=30,scale={w}:{h}:flags=lanczos", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           capture_output=True, check=True)
        arr = np.frombuffer(p.stdout, np.uint8).reshape(-1, h, w, 3)
        np.save(os.path.join(WORK, f"clip_{name}.npy"), arr)
        print("clip", name, arr.shape)


if __name__ == "__main__":
    import sys
    for step in (sys.argv[1:] or ["plate", "palm_track", "clips"]):
        globals()[step]()
