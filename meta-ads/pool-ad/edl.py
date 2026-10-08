"""edl.py: pick the best take of every line and build the A-roll.

Story edit (from the transcripts, see work/t1 + work/t2):
  take 2 (clean background, closer framing) for most lines;
  take 1 where take 2 stumbles ("in one line", "I didn't edit a single second") and for "and came here".
  Cut: take 1's walk-away ending, take 2's retakes, the 0.6 s pause before "here's how it works".

Outputs (all at 30 fps, 720x1280):
  work/a_roll.mp4     graded picture of the cut
  work/a_raw.mp4      the same cut, ungraded (used for the RAW side of the before/after)
  work/a_matte.mp4    person matte for the cut (text behind subject)
  work/voice.wav      the cut's dialogue, 48 kHz, 8 ms fades at every edit
  work/edl.json       segments + every word re-timed to the output
"""
import json
import subprocess

FPS = 30
# (take, source in, source out)  - every boundary sits in a pause
SEGMENTS = [
    (2, 0.60, 8.66),    # this is my video editing setup ... a system that does it for me
    (2, 9.06, 13.70),   # here's how it works. before I jumped in ... on my phone
    (1, 13.84, 17.42),  # told my system what I wanted, in one line. and came here
    (2, 19.88, 26.50),  # while I'm swimming ... everything. and it's done
    (1, 25.70, 30.62),  # and this video you just watched? same system. I didn't edit a single second of it
    (2, 33.02, 37.05),  # want to see how my system works? comment SYSTEM and I'll send you the details
]
GRADE = ("eq=contrast=1.06:saturation=1.08:gamma=0.98,"
         "colorbalance=rs=0.03:bs=-0.02:rm=0.02:bm=-0.01:rh=0.02:bh=-0.03,"
         "unsharp=5:5:0.45")


def fr(x):
    return round(x * FPS) / FPS


def build():
    segs, t = [], 0.0
    for take, a, b in SEGMENTS:
        a, b = fr(a), fr(b)
        segs.append({"take": take, "src_in": a, "src_out": b, "out_in": round(t, 4), "out_out": round(t + b - a, 4)})
        t += b - a
    dur = round(t, 4)

    words = []
    for s in segs:
        for w in json.load(open(f"work/t{s['take']}/words.json")):
            if w["s"] >= s["src_in"] - 0.01 and w["e"] <= s["src_out"] + 0.05:
                off = s["out_in"] - s["src_in"]
                words.append({"w": w["w"], "s": round(w["s"] + off, 3), "e": round(w["e"] + off, 3),
                              "take": s["take"], "src_s": w["s"]})
    json.dump({"fps": FPS, "duration": dur, "segments": segs, "words": words}, open("work/edl.json", "w"), indent=1)

    def video(out, src_key, extra, pix):
        inputs, parts = [], []
        for i, s in enumerate(segs):
            inputs += ["-i", f"raw/take{s['take']}.mp4" if src_key == "raw" else f"work/matte/take{s['take']}_alpha.mp4"]
            parts.append(f"[{i}:v]fps={FPS},scale=720:1280,trim=start={s['src_in']}:end={s['src_out']},"
                         f"setpts=PTS-STARTPTS{extra}[v{i}]")
        fc = ";".join(parts) + ";" + "".join(f"[v{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=0[o]"
        subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[o]",
                        "-c:v", "libx264", "-crf", "12", "-preset", "medium", "-pix_fmt", pix, out], check=True)

    video("work/a_roll.mp4", "raw", "," + GRADE, "yuv420p")
    video("work/a_raw.mp4", "raw", "", "yuv420p")
    video("work/a_matte.mp4", "matte", "", "yuv420p")

    inputs, parts = [], []
    for i, s in enumerate(segs):
        inputs += ["-i", f"raw/take{s['take']}.mp4"]
        d = s["src_out"] - s["src_in"]
        parts.append(f"[{i}:a]aresample=48000,atrim=start={s['src_in']}:end={s['src_out']},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d=0.008,afade=t=out:st={d - 0.008:.4f}:d=0.008[a{i}]")
    fc = ";".join(parts) + ";" + "".join(f"[a{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=0:a=1[o]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[o]", "-ac", "2",
                    "-c:a", "pcm_s16le", "work/voice.wav"], check=True)
    print(f"cut: {len(segs)} segments, {dur:.2f} s (from {39.28 + 37.92:.1f} s of raw footage)")
    for s in segs:
        print(f"  take{s['take']} {s['src_in']:6.2f}-{s['src_out']:6.2f}  ->  {s['out_in']:6.2f}-{s['out_out']:6.2f}")


if __name__ == "__main__":
    build()
