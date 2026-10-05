"""export: platform-ready deliverables with correct size, codec and loudness, in one command.

    python3 scripts/export.py out/final.mp4 --preset reels
    python3 scripts/export.py out/final.mp4 --preset reels,youtube,square --fit blur
    python3 scripts/export.py out/final.mp4 --preset master          # ProRes archive copy

Presets
    reels / tiktok / shorts   1080x1920   H.264 high, -14 LUFS
    youtube                   1920x1080   H.264 high, -14 LUFS
    youtube-4k                3840x2160
    feed                      1080x1350   (4:5, Instagram/LinkedIn feed)
    square                    1080x1080
    linkedin / x              1920x1080
    whatsapp                  720x1280    small file
    web                       1920x1080   lighter bitrate for websites/landing pages
    master                    source size, ProRes 422 HQ + PCM .mov, no loudness change

--fit when the aspect ratio changes:
    crop  fill the frame, trim the edges (use --anchor to keep the face/subject)   [default]
    pad   fit inside, brand-colour bars
    blur  fit inside over a blurred, zoomed copy (best for 16:9 -> 9:16 of wide shots)
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vibelib import color, ff, load_brand, loudnorm_filter, nice_fps, probe  # noqa: E402

V = (1080, 1920)
H169 = (1920, 1080)
PRESETS = {
    "reels": dict(size=V, crf=18, maxrate="16M", fps_max=60),
    "tiktok": dict(size=V, crf=18, maxrate="16M", fps_max=60),
    "shorts": dict(size=V, crf=18, maxrate="20M", fps_max=60),
    "youtube": dict(size=H169, crf=18, maxrate="24M", fps_max=60),
    "youtube-4k": dict(size=(3840, 2160), crf=18, maxrate="60M", fps_max=60),
    "feed": dict(size=(1080, 1350), crf=18, maxrate="12M", fps_max=60),
    "square": dict(size=(1080, 1080), crf=18, maxrate="12M", fps_max=60),
    "linkedin": dict(size=H169, crf=19, maxrate="12M", fps_max=60),
    "x": dict(size=H169, crf=19, maxrate="12M", fps_max=60),
    "whatsapp": dict(size=(720, 1280), crf=24, maxrate="2500k", fps_max=30),
    "web": dict(size=H169, crf=23, maxrate="6M", fps_max=30),
    "master": dict(size=None, prores=True),
}


def double_rate(rate):
    num, unit = float(rate[:-1]), rate[-1]
    return f"{num * 2:g}{unit}"


def vf_chain(src_w, src_h, W, H, fit, ax, ay, pad_hex):
    if (src_w, src_h) == (W, H):
        return "null", False
    if abs(src_w / src_h - W / H) < 0.01:
        return f"scale={W}:{H}:flags=lanczos", False
    if fit == "pad":
        return (f"scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,"
                f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x{pad_hex.lstrip('#')}"), False
    if fit == "blur":
        return (f"split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                f"boxblur=30:3,eq=brightness=-0.06:saturation=1.1[bg];"
                f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2"), True
    return (f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={W}:{H}:(iw-{W})*{ax}:(ih-{H})*{ay}"), False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--preset", default="reels", help="one or more, comma separated")
    ap.add_argument("--fit", default="crop", choices=["crop", "pad", "blur"])
    ap.add_argument("--anchor", default="0.5,0.4", help="crop anchor x,y (0..1)")
    ap.add_argument("--lufs", type=float, default=-14.0, help="loudness target (-14 social, -16 podcasts/web)")
    ap.add_argument("--no-loudnorm", action="store_true")
    ap.add_argument("--fps", type=float, default=None, help="force a frame rate")
    ap.add_argument("-o", "--out-dir", default="out")
    a = ap.parse_args()

    info = probe(a.video)
    if not info["width"]:
        sys.exit(f"no video stream in {a.video}")
    brand = load_brand(".")
    ax, ay = (float(v) for v in a.anchor.split(","))
    names = [p.strip() for p in a.preset.split(",") if p.strip()]
    for n in names:
        if n not in PRESETS:
            sys.exit(f"unknown preset {n!r}; choose from {', '.join(PRESETS)}")

    af_norm = None
    if info["has_audio"] and not a.no_loudnorm and any(not PRESETS[n].get("prores") for n in names):
        print(f"measuring loudness (target {a.lufs} LUFS) ...")
        af_norm = loudnorm_filter(a.video, lufs=a.lufs)

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(a.video).stem
    for n in names:
        p = PRESETS[n]
        src_fps = nice_fps(info["fps"] or 30)
        if p.get("prores"):
            out = out_dir / f"{stem}_master.mov"
            args = ["-i", a.video, "-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le"]
            if info["has_audio"]:
                args += ["-c:a", "pcm_s24le", "-ar", "48000"]
            ff(*args, out)
            print(f"  {n:11s} -> {out}  ({out.stat().st_size / 1e6:.1f} MB)")
            continue
        W, H = p["size"]
        fps = a.fps or min(src_fps, p["fps_max"])
        chain, complex_ = vf_chain(info["width"], info["height"], W, H, a.fit, ax, ay, color(brand, "fg"))
        chain = f"{chain},fps={fps},format=yuv420p,setsar=1"
        out = out_dir / f"{stem}_{n}.mp4"
        args = ["-i", a.video]
        args += ["-filter_complex", f"[0:v]{chain}[v]", "-map", "[v]"] if complex_ else ["-vf", chain, "-map", "0:v:0"]
        args += ["-c:v", "libx264", "-preset", "slow", "-crf", str(p["crf"]), "-maxrate", p["maxrate"],
                 "-bufsize", double_rate(p["maxrate"]),
                 "-profile:v", "high", "-level", "5.1" if W * H > 1920 * 1080 else "4.2",
                 "-g", str(int(round(fps * 2))), "-movflags", "+faststart"]
        if info["has_audio"]:
            args += ["-map", "0:a:0", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
            if af_norm:
                args += ["-af", af_norm]
        ff(*args, out)
        print(f"  {n:11s} -> {out}  {W}x{H} @ {fps:g}fps  ({out.stat().st_size / 1e6:.1f} MB)")
    dur = info["duration"]
    if dur > 90 and any(n in ("reels", "tiktok") for n in names):
        print(f"  note: {dur:.0f}s is long for a reel; under 60 s usually performs best")
    if dur > 180 and "shorts" in names:
        print("  note: YouTube Shorts must be 3 minutes or less")
    if dur > 140 and "x" in names:
        print("  note: X (Twitter) caps non-premium uploads at 2:20")


if __name__ == "__main__":
    main()
