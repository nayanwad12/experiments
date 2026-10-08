"""assemble: build a cut from many clips (AI clips, stock, phone shots) using a simple JSON edit list.

    python3 vibe/assemble.py work/edit.json -o work/assembly.mp4
    python3 vibe/assemble.py work/edit.json -o work/assembly.mp4 --audio work/vo.wav

edit.json
    {
      "size": [1920, 1080], "fps": 24,
      "shots": [
        {"file": "raw/clip01.mp4", "in": 0.4, "out": 3.6},
        {"file": "raw/clip02.mp4", "in": 1.0, "out": 5.0, "dur": 2.8, "transition": "fade", "t_dur": 0.4},
        {"file": "raw/photo.jpg", "dur": 3.0, "zoom": 1.08, "transition": "dip", "t_dur": 0.5},
        {"file": "raw/clip03.mp4", "in": 0, "out": 4, "speed": 0.6, "flow": true}
      ]
    }
Shot fields
    in/out     source range in seconds (default: whole clip)
    dur        force this on-screen length (speeds the range up/down to fit), or a still image's length
    speed      playback speed (ignored if dur is set); flow=true -> optical-flow slow motion
    zoom       slow push-in to this scale over the shot (Ken Burns), e.g. 1.08
    anchor     [x, y] 0..1 crop centre when the aspect ratio differs (default [0.5, 0.5])
    transition how this shot enters: cut (default) | fade | dip (through black) | wipeleft | slideup | ...
               (any ffmpeg xfade name); t_dur = transition length (s)
Clip audio is dropped (AI clips are usually silent or noisy). Add voice/music with --audio or audio_kit.py mix.
Writes work/assembly_timing.json with each shot's start/end on the output timeline (cue graphics to it).
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vibelib import ff, filter_script_args, mux, probe  # noqa: E402

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edit")
    ap.add_argument("-o", "--out", default="work/assembly.mp4")
    ap.add_argument("--audio", default=None, help="voice/mix to lay under the picture")
    a = ap.parse_args()

    E = json.loads(Path(a.edit).read_text())
    W, H = E.get("size", [1920, 1080])
    fps = E.get("fps", 30)
    shots = E["shots"]
    inputs, parts, durs = [], [], []
    for i, s in enumerate(shots):
        f = s["file"]
        is_img = Path(f).suffix.lower() in IMAGE_EXT
        ax, ay = s.get("anchor", [0.5, 0.5])
        if is_img:
            dur = float(s.get("dur", 3.0))
            inputs += ["-loop", "1", "-t", f"{dur + 1:.3f}", "-i", f]
            chain = f"[{i}:v]trim=duration={dur:.3f},setpts=PTS-STARTPTS"
        else:
            info = probe(f)
            t_in = float(s.get("in", 0))
            t_out = float(s.get("out", info["duration"]))
            src = max(0.05, t_out - t_in)
            speed = src / float(s["dur"]) if "dur" in s else float(s.get("speed", 1.0))
            dur = src / speed
            inputs += ["-i", f]
            chain = f"[{i}:v]trim=start={t_in:.3f}:end={t_out:.3f},setpts=(PTS-STARTPTS)/{speed:.5f}"
            if s.get("flow") and speed < 1:
                chain += f",minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:vsbmc=1"
        z = float(s.get("zoom", 1.0))
        # cover-crop to the target frame (anchor decides what is kept)
        chain += (f",scale={W}:{H}:force_original_aspect_ratio=increase,"
                  f"crop={W}:{H}:(iw-{W})*{ax}:(ih-{H})*{ay},setsar=1,fps={fps}")
        if z != 1.0:
            # Ken Burns push-in (upscaled first so the slow zoom doesn't jitter)
            n = max(1, int(dur * fps))
            chain += (f",scale={W * 2}:{H * 2},zoompan=z='1+({z - 1:.4f})*on/{n}':"
                      f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={fps}")
        chain += ",format=yuv420p"
        parts.append(chain + f"[s{i}]")
        durs.append(dur)

    # chain shots with xfade / concat
    graph = list(parts)
    cur, cur_len = "[s0]", durs[0]
    timing = [{"shot": 0, "file": shots[0]["file"], "s": 0.0, "e": round(durs[0], 3)}]
    for i in range(1, len(shots)):
        tr = shots[i].get("transition", "cut")
        td = float(shots[i].get("t_dur", 0.4)) if tr != "cut" else 0.0
        td = min(td, durs[i] * 0.5, cur_len * 0.5)
        lab = f"[x{i}]"
        if tr == "cut" or td <= 0:
            graph.append(f"{cur}[s{i}]concat=n=2:v=1:a=0{lab}")
            start = cur_len
        else:
            name = "fadeblack" if tr == "dip" else tr
            off = cur_len - td
            graph.append(f"{cur}[s{i}]xfade=transition={name}:duration={td:.3f}:offset={off:.3f}{lab}")
            start = off
        cur, cur_len = lab, start + durs[i]
        timing.append({"shot": i, "file": shots[i]["file"], "s": round(start, 3), "e": round(cur_len, 3)})
    graph.append(f"{cur}null[vout]")

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    silent = out.with_name(out.stem + "_picture.mp4") if a.audio else out
    ff(*inputs, *filter_script_args(";\n".join(graph), out.with_suffix(".graph.txt")), "-map", "[vout]",
       "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-r", str(fps), "-movflags", "+faststart", silent)
    out.with_suffix(".graph.txt").unlink(missing_ok=True)
    if a.audio:
        mux(silent, a.audio, out)
        silent.unlink()
    (out.parent / f"{out.stem}_timing.json").write_text(json.dumps(timing, indent=1))
    print(f"{len(shots)} shots, {cur_len:.2f}s -> {out}  (+ {out.stem}_timing.json)")


if __name__ == "__main__":
    main()
