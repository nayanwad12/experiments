"""clipscan: QC a folder of AI-generated (or stock / phone) clips before editing.

    python3 vibe/clipscan.py raw/*.mp4
    python3 vibe/clipscan.py raw/ --step 0.5

For every clip it writes work/scan/<clip>_sheet.png (a frame every --step seconds) and adds a row to
work/scan/scan.md: size, fps, length, hard cuts inside the clip, and "unstable" stretches where the
picture changes far more than the camera motion around it (typical of AI morphs, warps and
objects popping in or out).

Claude: open every sheet with the Read tool and mark the usable ranges in scan.md before editing.
Look for: morphing hands/faces, garbled text or logos, objects that appear/disappear, wobbly
geometry, flicker, watermarks, and the last ~0.5 s of AI clips (they often degrade).
"""

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vibelib import ffmpeg_bin, fmt_time, probe  # noqa: E402

VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".m4v", ".avi"}


def diffs(path, fps):
    w, h = 160, 90
    raw = subprocess.run([ffmpeg_bin(), "-v", "error", "-i", str(path), "-vf", f"fps={fps},scale={w}:{h}",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
    if len(fr) < 2:
        return np.zeros(0)
    return np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))


def ranges(mask, fps, min_len=0.15):
    out, start = [], None
    for i, m in enumerate(list(mask) + [False]):
        if m and start is None:
            start = i
        elif not m and start is not None:
            if (i - start) / fps >= min_len:
                out.append((start / fps, i / fps))
            start = None
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--step", type=float, default=0.5, help="seconds between sheet frames")
    ap.add_argument("-o", "--out-dir", default="work/scan")
    a = ap.parse_args()

    files = []
    for p in a.inputs:
        p = Path(p)
        files += sorted(x for x in p.iterdir() if x.suffix.lower() in VIDEO_EXT) if p.is_dir() else [p]
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = ["| clip | size | fps | length | cuts inside | unstable stretches | usable (fill in) |",
            "|---|---|---|---|---|---|---|"]
    for f in files:
        info = probe(f)
        fps = 12
        d = diffs(f, fps)
        cuts, unstable = [], []
        if len(d):
            med = float(np.median(d)) + 1e-3
            cut_idx = np.where((d > 4 * med) & (d > 18))[0]
            cuts = [(i + 1) / fps for i in cut_idx]
            k = 5
            local = np.convolve(d, np.ones(k) / k, mode="same")
            mask = (local > 2.2 * med) & (local > 6)
            for i in cut_idx:
                mask[max(0, i - 1): i + 2] = False
            unstable = ranges(mask, fps)
        sheet = out / f"{f.stem}_sheet.png"
        n = max(1, int(info["duration"] / a.step))
        cols = 6 if info["width"] >= info["height"] else 8
        tile_w = 320 if info["width"] >= info["height"] else 200
        rows_n = -(-n // cols)
        label = ("drawtext=text='%{pts\\:hms}':x=6:y=6:fontsize=16:fontcolor=0xD4FF3F:"
                 "box=1:boxcolor=0x0B0B0D@0.7,")
        for lab in (label, ""):           # fall back to no timestamps if this ffmpeg has no default font
            vf = f"fps=1/{a.step},scale={tile_w}:-2,{lab}tile={cols}x{rows_n}:padding=4:color=0x0B0B0D"
            r = subprocess.run([ffmpeg_bin(), "-hide_banner", "-y", "-v", "error", "-i", str(f), "-vf", vf,
                                "-frames:v", "1", str(sheet)], capture_output=True)
            if r.returncode == 0:
                break
        cut_s = ", ".join(f"{c:.2f}" for c in cuts) or "-"
        un_s = ", ".join(f"{s:.1f}-{e:.1f}" for s, e in unstable) or "-"
        rows.append(f"| {f.name} | {info['width']}x{info['height']} | {info['fps']:.2f} | "
                    f"{fmt_time(info['duration'])} | {cut_s} | {un_s} | |")
        print(f"  {f.name}: {info['duration']:.1f}s, cuts [{cut_s}], unstable [{un_s}] -> {sheet}")
    (out / "scan.md").write_text("# Clip scan\n\n" + "\n".join(rows) + "\n\n"
                                 "Unstable = picture changes much faster than usual for this clip. Check those "
                                 "moments on the sheet for morphs, warps and popping objects.\n")
    print(f"report -> {out / 'scan.md'}")


if __name__ == "__main__":
    main()
