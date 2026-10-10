"""timeline.json -> one H.264 file per lesson (frame-exact, same frames the audio was cut on), then mux + full cut."""
import json, subprocess, sys, time
import numpy as np

SRC = "raw/raw.mp4"
W, H, FPS = 1920, 1080, 30
FB = W * H * 3 // 2                      # yuv420p frame bytes
tl = json.load(open("timeline.json"))
only = sys.argv[1:]


def grab(t):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", SRC, "-frames:v", "1",
                        "-pix_fmt", "yuv420p", "-f", "rawvideo", "-"], capture_output=True, check=True)
    return r.stdout[:FB]


holds = {sg["hold"]: grab(sg["hold"]) for p in tl for sg in p["segs"] if sg["hold"] is not None}
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-vf", f"fps={FPS}", "-pix_fmt", "yuv420p",
                        "-f", "rawvideo", "-"], stdout=subprocess.PIPE, bufsize=FB * 4)
cur, frame = -1, None


def frame_at(k):
    """sequential reader: frame k (absolute, 30 fps grid) of the source"""
    global cur, frame
    while cur < k:
        frame = dec.stdout.read(FB); cur += 1
        assert len(frame) == FB, f"eof at {cur}"
    return frame


t0 = time.time()
for p in tl:
    if only and p["id"] not in only:
        continue
    n = p["frames"]; fd = 8
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-",
                            "-vf", f"fade=t=in:start_frame=0:nb_frames={fd},fade=t=out:start_frame={n - fd}:nb_frames={fd}",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-profile:v", "high",
                            "-pix_fmt", "yuv420p", "-g", "60", "-r", str(FPS), f"out/p{p['id']}_v.mp4"],
                           stdin=subprocess.PIPE)
    done = 0
    for sg in p["segs"]:
        for k in range(sg["f0"], sg["f1"]):
            fr = frame_at(k)
            enc.stdin.write(holds[sg["hold"]] if sg["hold"] is not None else fr)
            done += 1
    enc.stdin.close(); enc.wait()
    assert done == n
    print(f"part {p['id']}: {n} frames, {time.time() - t0:.0f}s", flush=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"out/p{p['id']}_v.mp4", "-i", f"out/p{p['id']}.wav",
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", f"out/p{p['id']}.mp4"], check=True)
dec.kill()
