"""retime: slow motion, speed-ups and "fit this shot to exactly N seconds".

    python3 vibe/retime.py raw/clip.mp4 --speed 0.5 --mode flow -o work/slowmo.mp4   # smooth slow-mo
    python3 vibe/retime.py raw/clip.mp4 --duration 3.2 -o work/fit.mp4               # land on the narration
    python3 vibe/retime.py raw/clip.mp4 --speed 2 -o work/fast.mp4                   # 2x with pitch-kept audio
    python3 vibe/retime.py raw/clip.mp4 --start 1.5 --end 4.0 --speed 0.6 --mode flow -o work/x.mp4

Modes for slow motion:
    dup    repeat frames (fast, steppy; fine for speed-ups)
    blend  cross-blend neighbouring frames (soft, quick)
    flow   optical-flow interpolation (smoothest, slow to render; watch for warping on fast motion)
Audio is kept (pitch preserved) between 0.5x and 4x, otherwise dropped. Use --mute to always drop it.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vibelib import ff, nice_fps, probe  # noqa: E402


def atempo_chain(speed):
    parts, s = [], speed
    while s > 2.0:
        parts.append("atempo=2.0")
        s /= 2.0
    while s < 0.5:
        parts.append("atempo=0.5")
        s /= 0.5
    parts.append(f"atempo={s:.5f}")
    return ",".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--speed", type=float, default=None, help="0.5 = half speed, 2 = double")
    ap.add_argument("--duration", type=float, default=None, help="stretch/squeeze to this many seconds")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=None)
    ap.add_argument("--mode", default=None, choices=["dup", "blend", "flow"])
    ap.add_argument("--fps", type=float, default=None, help="output fps (default: source)")
    ap.add_argument("--mute", action="store_true")
    a = ap.parse_args()

    info = probe(a.video)
    end = a.end if a.end is not None else info["duration"]
    src_len = end - a.start
    if a.duration:
        speed = src_len / a.duration
    elif a.speed:
        speed = a.speed
    else:
        sys.exit("give --speed or --duration")
    fps = a.fps or nice_fps(info["fps"] or 30)
    mode = a.mode or ("flow" if speed < 0.75 else "dup")
    v = f"trim=start={a.start}:end={end},setpts=(PTS-STARTPTS)/{speed:.6f}"
    if mode == "flow" and speed < 1:
        v += f",minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
    elif mode == "blend" and speed < 1:
        v += f",framerate=fps={fps}:interp_start=0:interp_end=255"
    v += f",fps={fps},format=yuv420p"
    args = ["-i", a.video, "-filter_complex", f"[0:v]{v}[v]", "-map", "[v]"]
    if info["has_audio"] and not a.mute and 0.5 <= speed <= 4:
        args[3] += f";[0:a]atrim=start={a.start}:end={end},asetpts=PTS-STARTPTS,{atempo_chain(speed)}[a]"
        args += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    print(f"{src_len:.2f}s at {speed:.3f}x -> {src_len / speed:.2f}s ({mode}) ...")
    ff(*args, "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-movflags", "+faststart", a.out)
    print(f"done -> {a.out}")


if __name__ == "__main__":
    main()
