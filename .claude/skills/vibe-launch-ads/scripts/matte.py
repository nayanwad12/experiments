"""matte: cut the person (or main subject) out of every frame. This is the base of most VFX.

    python3 vibe/matte.py raw/take1.mp4                          # -> work/matte/take1_alpha.mp4
    python3 vibe/matte.py raw/take1.mp4 --replace-bg "#D4FF3F"   # + quick background swap preview
    python3 vibe/matte.py raw/take1.mp4 --replace-bg assets/office.jpg --model birefnet-portrait
    python3 vibe/matte.py raw/take1.mp4 --replace-bg blur        # portrait-mode style background blur
    python3 vibe/matte.py raw/product.jpg --model isnet-general-use   # still image -> assets/product_cutout.png

alpha.mp4 is a black/white matte video (white = subject) at the source size and fps.
Use it in scene.py for text-behind-subject, layer splits, remove/re-add effects, glows and outlines:
    from motion_kit import VideoFrames, with_alpha
    src, mat = VideoFrames("raw/take1.mp4"), VideoFrames("work/matte/take1_alpha.mp4")
    person = with_alpha(src.array(t), mat.array(t))      # skia Image with transparency

Models (downloaded once, automatically):
    u2net_human_seg     people, fast, good default
    birefnet-portrait   people, best edges/hair, slow
    isnet-general-use   any subject (products, pets, objects)
    u2netp              very fast, rough (drafts)
--scale 0.5 halves the processing resolution (2-4x faster). The mask is upscaled and smoothed.
"""

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vibelib import FrameWriter, ffmpeg_bin, hex_rgb, mux, nice_fps, probe  # noqa: E402


def frames(path, w, h, fps):
    p = subprocess.Popen([ffmpeg_bin(), "-v", "error", "-i", str(path), "-vf", f"fps={fps},scale={w}:{h}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    n = w * h * 3
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        yield np.frombuffer(buf, np.uint8).reshape(h, w, 3)
    p.wait()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("-o", "--out", default=None, help="alpha video path")
    ap.add_argument("--model", default="u2net_human_seg")
    ap.add_argument("--scale", type=float, default=1.0, help="processing scale (0.5 = faster)")
    ap.add_argument("--smooth", type=float, default=0.5, help="temporal smoothing 0..0.9 (less flicker)")
    ap.add_argument("--replace-bg", default=None, help='"#hex", image/video path, or "blur" for a preview')
    ap.add_argument("--max-seconds", type=float, default=None, help="only process the first N seconds")
    a = ap.parse_args()

    try:
        from PIL import Image
        from rembg import new_session, remove
    except ImportError:
        sys.exit('missing:  python3 -m pip install "rembg[cpu]" opencv-python-headless')
    import cv2

    if Path(a.video).suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"):
        out = Path(a.out) if a.out else Path("assets") / f"{Path(a.video).stem}_cutout.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        img = Image.open(a.video).convert("RGB")
        remove(img, session=new_session(a.model)).save(out)
        print(f"cutout -> {out}")
        return

    info = probe(a.video)
    W, H = info["width"] - info["width"] % 2, info["height"] - info["height"] % 2
    fps = nice_fps(info["fps"] or 30)
    pw, ph = int(W * a.scale) // 2 * 2, int(H * a.scale) // 2 * 2
    out = Path(a.out) if a.out else Path("work/matte") / f"{Path(a.video).stem}_alpha.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    total = int((min(info["duration"], a.max_seconds or 1e9)) * fps)
    print(f"matting {total} frames with {a.model} at {pw}x{ph} ...")
    session = new_session(a.model)

    bg_img = bg_vid = None
    if a.replace_bg and a.replace_bg not in ("blur",) and not a.replace_bg.startswith("#"):
        if Path(a.replace_bg).suffix.lower() in (".mp4", ".mov", ".webm", ".mkv"):
            bg_vid = frames(a.replace_bg, W, H, fps)
        else:
            bg_img = np.asarray(Image.open(a.replace_bg).convert("RGB").resize((W, H), Image.LANCZOS))
    comp_path = out.with_name(out.stem.replace("_alpha", "") + "_bgswap_silent.mp4")
    comp = FrameWriter(comp_path, W, H, fps, crf=18) if a.replace_bg else None

    prev = None
    with FrameWriter(out, W, H, fps, crf=12) as fw:
        for i, fr in enumerate(frames(a.video, W, H, fps)):
            if i >= total:
                break
            small = fr if a.scale == 1 else cv2.resize(fr, (pw, ph), interpolation=cv2.INTER_AREA)
            m = np.asarray(remove(Image.fromarray(small), session=session, only_mask=True), np.float32) / 255
            if a.scale != 1:
                m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)
            m = cv2.GaussianBlur(m, (0, 0), 1.2)
            if prev is not None and a.smooth > 0:
                m = a.smooth * prev + (1 - a.smooth) * m
            prev = m
            g = (np.clip(m, 0, 1) * 255).astype(np.uint8)
            fw.write(np.repeat(g[..., None], 3, 2))
            if comp:
                if a.replace_bg == "blur":
                    bg = cv2.GaussianBlur(fr, (0, 0), 18)
                elif a.replace_bg.startswith("#"):
                    bg = np.empty_like(fr)
                    bg[:] = hex_rgb(a.replace_bg)
                elif bg_vid is not None:
                    bg = next(bg_vid, None)
                    bg = fr if bg is None else bg
                else:
                    bg = bg_img
                k = m[..., None]
                comp.write((fr * k + bg * (1 - k)).astype(np.uint8))
            if i % 30 == 0:
                print(f"  {i}/{total}", end="\r", flush=True)
    print(f"\nmatte -> {out}")
    if comp:
        comp.close()
        final = comp_path.with_name(comp_path.name.replace("_silent", ""))
        if info["has_audio"]:
            mux(comp_path, a.video, final)
            comp_path.unlink()
        else:
            comp_path.rename(final)
        print(f"background swap preview -> {final}")


if __name__ == "__main__":
    main()
