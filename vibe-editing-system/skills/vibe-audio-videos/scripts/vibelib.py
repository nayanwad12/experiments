"""vibelib: shared helpers for the Ideabro Studio Vibe Editing System scripts.

Everything here is plain Python + ffmpeg. If ffmpeg is not on PATH, the static build
shipped with the `imageio-ffmpeg` pip package is used instead, so students never have
to install ffmpeg by hand.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ------------------------------------------------------------------ brand: Ideabro house style
# Used whenever the student has not supplied their own brand.json.
IDEABRO = {
    "name": "Ideabro Studio",
    "product": "Vibe Editing System",
    "tagline": "Direct the vibe. Let AI do the keyframes.",
    "colors": {
        "ink": "#0B0B0D",
        "paper": "#F2EEE3",
        "white": "#FFFFFF",
        "lime": "#D4FF3F",       # signature accent
        "periwinkle": "#C4C6FF",
        "blush": "#FFCFD8",
        "ice": "#C8F0EC",
        "orange": "#FF5A1F",
    },
    "roles": {"bg": "paper", "fg": "ink", "accent": "lime", "accent2": "periwinkle", "caption": "white", "caption_hi": "lime"},
    "fonts": {
        "display": "Unbounded:900",
        "impact": "Anton",
        "body": "Inter Tight:400,700",
        "mono": "JetBrains Mono:700",
        "serif": "Instrument Serif:400",
    },
}

# Canvas sizes by aspect ratio.
FORMATS = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
    "4k": (3840, 2160),
    "9:16-4k": (2160, 3840),
}


def load_brand(project_dir="."):
    """brand.json in the project if present, otherwise the Ideabro house style."""
    p = Path(project_dir) / "brand.json"
    if p.exists():
        b = json.loads(p.read_text())
        merged = json.loads(json.dumps(IDEABRO))
        for k, v in b.items():
            if isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k].update(v)
            else:
                merged[k] = v
        return merged
    return json.loads(json.dumps(IDEABRO))


def color(brand, role_or_name):
    """Resolve 'accent' / 'lime' / '#RRGGBB' to a hex string."""
    if role_or_name.startswith("#"):
        return role_or_name
    name = brand.get("roles", {}).get(role_or_name, role_or_name)
    return brand["colors"].get(name, name)


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ------------------------------------------------------------------ ffmpeg
def ffmpeg_bin():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        sys.exit("ffmpeg not found. Run:  python3 -m pip install imageio-ffmpeg   (or install ffmpeg)")


def ffprobe_bin():
    return shutil.which("ffprobe")


def ffmpeg_major():
    out = subprocess.run([ffmpeg_bin(), "-version"], capture_output=True, text=True).stdout
    m = re.search(r"ffmpeg version n?(\d+)", out)
    return int(m.group(1)) if m else 6


def run(cmd, quiet=True, cwd=None):
    """Run a command; on failure print the tail of stderr and exit."""
    cmd = [str(c) for c in cmd]
    if not quiet:
        print("$", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if r.returncode != 0:
        tail = "\n".join(r.stderr.strip().splitlines()[-25:])
        sys.exit(f"command failed ({r.returncode}): {' '.join(cmd[:6])} ...\n{tail}")
    return r


def ff(*args, quiet=True, cwd=None):
    return run([ffmpeg_bin(), "-hide_banner", "-y", *args], quiet=quiet, cwd=cwd)


def filter_script_args(graph_text, path):
    """Pass a long filter graph through a file (avoids command-line length limits, incl. Windows)."""
    Path(path).write_text(graph_text)
    if ffmpeg_major() >= 7:
        return ["-/filter_complex", str(path)]
    return ["-filter_complex_script", str(path)]


def probe(path):
    """Return {duration, width, height, fps, has_audio, sample_rate} (display orientation)."""
    path = str(path)
    info = {"duration": 0.0, "width": 0, "height": 0, "fps": 0.0, "has_audio": False, "sample_rate": 0}
    fp = ffprobe_bin()
    if fp:
        r = subprocess.run([fp, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
                           capture_output=True, text=True)
        if r.returncode == 0:
            d = json.loads(r.stdout)
            info["duration"] = float(d.get("format", {}).get("duration", 0) or 0)
            for s in d.get("streams", []):
                if s.get("codec_type") == "video" and not info["width"]:
                    w, h = int(s.get("width", 0)), int(s.get("height", 0))
                    rot = 0
                    for sd in s.get("side_data_list", []) or []:
                        if "rotation" in sd:
                            rot = int(float(sd["rotation"]))
                    rot = int(s.get("tags", {}).get("rotate", rot) or rot)
                    if abs(rot) % 180 == 90:
                        w, h = h, w
                    info["width"], info["height"] = w, h
                    num, _, den = (s.get("avg_frame_rate") or "0/1").partition("/")
                    try:
                        info["fps"] = float(num) / float(den or 1)
                    except (ValueError, ZeroDivisionError):
                        info["fps"] = 0.0
                elif s.get("codec_type") == "audio":
                    info["has_audio"] = True
                    info["sample_rate"] = int(s.get("sample_rate", 0) or 0)
            return info
    # Fallback: parse `ffmpeg -i` banner.
    r = subprocess.run([ffmpeg_bin(), "-hide_banner", "-i", path], capture_output=True, text=True)
    err = r.stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    if m:
        info["duration"] = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", err)
    if m:
        info["width"], info["height"] = int(m.group(1)), int(m.group(2))
        if re.search(r"rotation of -?90", err) or re.search(r"rotate\s*:\s*-?90|rotate\s*:\s*270", err):
            info["width"], info["height"] = info["height"], info["width"]
    m = re.search(r"([\d.]+) fps", err)
    if m:
        info["fps"] = float(m.group(1))
    m = re.search(r"Audio:.*?(\d+) Hz", err)
    if m:
        info["has_audio"], info["sample_rate"] = True, int(m.group(1))
    return info


def nice_fps(fps):
    """Snap odd phone frame rates (29.97, 59.94, 30.02 ...) to a standard rate."""
    std = min((23.976, 24, 25, 29.97, 30, 48, 50, 59.94, 60), key=lambda s: abs(fps - s))
    if abs(fps - std) < 0.08:
        return std
    return round(fps) or 30


# ------------------------------------------------------------------ frames -> video
class FrameWriter:
    """Pipe numpy RGB/RGBA frames straight into ffmpeg (H.264, yuv420p, faststart).

        with FrameWriter("out/clip.mp4", 1080, 1920, 30) as fw:
            for i in range(n): fw.write(frame_uint8_HxWx3)
    """

    def __init__(self, path, width, height, fps, crf=17, preset="medium", audio=None, pix_fmt="rgb24", alpha=False):
        """alpha=True: feed RGBA frames, write a transparent ProRes 4444 .mov (for overlays)."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        if alpha:
            pix_fmt = "rgba"
        cmd = [ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y",
               "-f", "rawvideo", "-pix_fmt", pix_fmt, "-s", f"{width}x{height}", "-r", str(fps), "-i", "-"]
        if audio:
            cmd += ["-i", str(audio)]
        if alpha:
            cmd += ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-vendor", "apl0"]
        else:
            cmd += ["-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p",
                    "-profile:v", "high", "-movflags", "+faststart"]
        if audio:
            cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
        cmd += [str(path)]
        self.w, self.h = width, height
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def write(self, frame):
        import numpy as np
        a = np.ascontiguousarray(frame, dtype=np.uint8)
        if a.shape[0] != self.h or a.shape[1] != self.w:
            raise ValueError(f"frame is {a.shape[1]}x{a.shape[0]}, writer expects {self.w}x{self.h}")
        self.proc.stdin.write(a.tobytes())

    def close(self):
        self.proc.stdin.close()
        if self.proc.wait() != 0:
            sys.exit("ffmpeg failed while encoding frames")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def concat_videos(paths, out, reencode=False):
    """Join clips with identical codecs (stream copy) or re-encode when they differ."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    lst = out.with_suffix(".concat.txt")
    lst.write_text("".join(f"file '{Path(p).resolve().as_posix()}'\n" for p in paths))
    if reencode:
        ff("-f", "concat", "-safe", "0", "-i", lst, "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", out)
    else:
        ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", out)
    lst.unlink(missing_ok=True)
    return out


def composite(base, overlay, out, at=0.0, crf=17):
    """Lay a transparent overlay .mov (from Stage.render(alpha=True)) over a video; keeps base audio."""
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    ff("-i", base, "-itsoffset", f"{at:.3f}", "-i", overlay, "-filter_complex",
       "[1:v]format=yuva444p10le[o];[0:v][o]overlay=0:0:eof_action=pass:format=auto,format=yuv420p[v]",
       "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", str(crf), "-preset", "medium",
       "-c:a", "copy", "-movflags", "+faststart", out)
    return out


def grab_frame(video, t, w=None, h=None):
    """One RGB frame of a video at time t as a numpy array."""
    import numpy as np
    info = probe(video)
    w, h = w or info["width"], h or info["height"]
    raw = subprocess.run([ffmpeg_bin(), "-v", "error", "-ss", f"{max(0, t):.3f}", "-i", str(video), "-frames:v", "1",
                          "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True).stdout
    if len(raw) < w * h * 3:
        return np.zeros((h, w, 3), np.uint8)
    return np.frombuffer(raw[: w * h * 3], np.uint8).reshape(h, w, 3)


def mux(video, audio, out):
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    ff("-i", video, "-i", audio, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
       "-shortest", "-movflags", "+faststart", out)
    return out


# ------------------------------------------------------------------ loudness
def measure_loudness(path):
    r = subprocess.run([ffmpeg_bin(), "-hide_banner", "-nostats", "-i", str(path), "-vn",
                        "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S)
    if not m:
        return None
    return json.loads(m.group(0))


def loudnorm_filter(path, lufs=-14.0, tp=-1.0, lra=11.0):
    """Two-pass EBU R128 loudnorm filter string for `path` (falls back to one-pass)."""
    m = measure_loudness(path)
    if not m or m.get("input_i") in ("-inf", None):
        return f"loudnorm=I={lufs}:TP={tp}:LRA={lra}"
    return (f"loudnorm=I={lufs}:TP={tp}:LRA={lra}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
            f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")


# ------------------------------------------------------------------ words.json
def load_words(path):
    """words.json = [{"w": "Hello", "s": 0.12, "e": 0.40, "p": 0.98}, ...] (seconds)."""
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict):
        data = data.get("words", [])
    out = []
    for w in data:
        out.append({"w": w.get("w", w.get("word", w.get("d", ""))).strip(),
                    "s": float(w.get("s", w.get("start", 0))),
                    "e": float(w.get("e", w.get("end", 0))),
                    "p": float(w.get("p", w.get("probability", 1.0)))})
    return [w for w in out if w["w"]]


def fmt_time(t):
    m, s = divmod(max(0.0, t), 60)
    return f"{int(m):02d}:{s:05.2f}"
