"""OncoXpress brand film (40 s, 16:9, 24 fps): Apple-style, white + green graphics and captions, SFX.

    python3 vo.py              # once: tighten the narration -> work/vo_edit.wav + work/vo_lines.json
    python3 build.py all       # = timeline base overlay audio final sheet

Steps
    timeline  shots + graphics + caption word times -> work/timeline.json (read by scene.js)
    base      footage track: retime, slow push-ins, one grade, grain -> work/base.mp4 (graphic slots are black)
    overlay   scene.html rendered with Playwright as a transparent overlay -> work/overlay.mov
    audio     music bed + ambience + SFX + narration -> work/mix.wav
    final     composite + mux -> out/oncoxpress_brand_film_40s.mp4
    sheet     contact sheet -> out/sheet.png

AI clips whose screens show garbled UI/text are never used; those beats are rebuilt as graphics (G1-G6).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
W, H, FPS, DUR = 1920, 1080, 24, 40.0
GRADE = ("eq=contrast=1.04:saturation=0.92:brightness=0.01,"
         "colorbalance=rs=0.01:bs=-0.02:rh=0.015:bh=-0.012,"
         "curves=all='0/0.015 0.25/0.235 0.75/0.775 1/0.985'")
FINISH = "noise=alls=3:allf=t,vignette=angle=PI/5.5"
# the generator's visible sparkle mark sits at the same spot in every 1280x720 source clip
DELOGO = "delogo=x=1130:y=570:w=60:h=60"

# Output timeline. "src": footage (src range in seconds); "gfx": graphic drawn by scene.js on black.
SHOTS = [
    dict(t=0.000, src="walk", a=0.00, b=3.30, zoom=1.05),                 # Sometimes, life changes in a moment.
    dict(t=3.083, src="search", a=3.05, b=6.30, zoom=1.06, blur=True, gfx="questions"),  # ...questions feel bigger
    dict(t=6.583, src="treatment", a=2.50, b=5.35, zoom=1.05),            # But behind every diagnosis is a person.
    dict(t=9.292, src="walk", a=3.45, b=6.15, zoom=1.04),                 # A family. A life filled with memories,
    dict(t=11.917, src="walk", a=6.30, b=8.20, zoom=1.04),                # dreams, and people who care.
    dict(t=13.833, src="doctors", a=2.75, b=4.30, zoom=1.03),             # Being heard matters.
    dict(t=15.417, gfx="options"),                                        # Understanding your options matters.
    dict(t=17.458, src="doctors", a=4.30, b=5.95, zoom=1.06),             # Because care is more than a medical conversation.
    dict(t=20.042, gfx="guidance"),                                       # It is guidance, thoughtful decisions, support...
    dict(t=24.958, src="treatment", a=6.55, b=7.95, zoom=1.04),           # Every person deserves dignity,
    dict(t=26.708, src="treatment", a=0.00, b=2.40, zoom=1.05),           # compassion, and the chance to face each
    dict(t=29.625, src="records", a=0.00, b=0.95, zoom=1.04),             # next step with support.
    dict(t=30.958, gfx="logo"),                                           # OncoXpress.
    dict(t=32.250, gfx="profile"),                                        # ...see the person behind the diagnosis.
    dict(t=35.958, gfx="endcard"),                                        # Connect with OncoXpress...
]
FACE = ("treatment", 4.90)   # still used inside the profile graphic


def run(*cmd):
    print("  $", " ".join(str(c) for c in cmd)[:200])
    subprocess.run([str(c) for c in cmd], check=True)


def frames(t):
    return int(round(t * FPS))


def timeline():
    lines = json.loads((HERE / "work/vo_lines.json").read_text())
    pages = []
    for ln in lines:
        words = ln["text"].split()
        weights = [len(re.sub(r"[^\w]", "", w)) + 2.5 + (3 if w[-1] in ",." else 0) for w in words]
        span, tot, acc = ln["e"] - ln["s"] - 0.06, sum(weights), 0.0
        timed = []
        for w, k in zip(words, weights):
            timed.append({"w": w, "s": round(ln["s"] + 0.03 + span * acc / tot, 3)})
            acc += k
        # split long lines into balanced caption pages (<= ~42 characters), preferring breaks after commas
        n_pages = -(-len(ln["text"]) // 42)
        ends, pos = [], 0
        for w in words:
            pos += len(w) + 1
            ends.append(pos)
        cuts, last = [], 0
        for k in range(1, n_pages):
            target = len(ln["text"]) * k / n_pages
            best = min(range(last, len(words) - 1),
                       key=lambda j: abs(ends[j] - target) - (7 if words[j].endswith(",") else 0))
            cuts.append(best + 1)
            last = best + 1
        for a, b in zip([0] + cuts, cuts + [len(words)]):
            pages.append(timed[a:b])
    caps = []
    for i, p in enumerate(pages):
        line_end = next(ln["e"] for ln in lines if ln["s"] <= p[-1]["s"] <= ln["e"] + 0.01)
        nxt = pages[i + 1][0]["s"] if i + 1 < len(pages) else DUR
        caps.append({"words": p, "s": p[0]["s"] - 0.04, "e": round(min(nxt - 0.02, max(line_end + 0.35, p[-1]["s"] + 0.6)), 3)})
    shots = []
    for i, s in enumerate(SHOTS):
        end = SHOTS[i + 1]["t"] if i + 1 < len(SHOTS) else DUR
        shots.append({**s, "s": s["t"], "e": end})
    tl = {"fps": FPS, "dur": DUR, "w": W, "h": H, "shots": shots, "captions": caps, "lines": lines}
    (HERE / "work/timeline.json").write_text(json.dumps(tl, indent=1))
    (HERE / "work/timeline.js").write_text("window.TL = " + json.dumps(tl) + ";\n")
    print(f"  {len(caps)} caption pages, {len(shots)} shots")


def base():
    sd = HERE / "work/shots"
    sd.mkdir(parents=True, exist_ok=True)
    parts = []
    for i, s in enumerate(SHOTS):
        end = SHOTS[i + 1]["t"] if i + 1 < len(SHOTS) else DUR
        n = frames(end) - frames(s["t"])
        out = sd / f"{i:02d}.mp4"
        if "src" not in s:
            run("ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=black:s={W}x{H}:r={FPS}",
                "-frames:v", n, "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", out)
        else:
            speed = (s["b"] - s["a"]) / (n / FPS)
            chain = f"{DELOGO},trim=start={s['a']}:end={s['b']},setpts=(PTS-STARTPTS)/{speed:.5f}"
            # gentle slow motion: motion-compensated in-betweens instead of duplicated frames
            chain += f",minterpolate=fps={FPS}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir" if speed < 0.95 else f",fps={FPS}"
            z = s.get("zoom", 1.0)
            chain += (f",scale={W * 2}:{H * 2}:flags=lanczos,zoompan=z='1+({z - 1:.4f})*on/{n}':"
                      f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS}")
            chain += "," + GRADE + ",unsharp=5:5:0.35"
            if s.get("blur"):
                chain += ",gblur=sigma=16,eq=brightness=-0.20:saturation=0.75"
            chain += f",{FINISH},tpad=stop_mode=clone:stop_duration=2"
            run("ffmpeg", "-v", "error", "-y", "-i", HERE / f"raw/{s['src']}.mp4", "-vf", chain, "-an",
                "-frames:v", n, "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", "-r", FPS, out)
        parts.append(out)
    (sd / "list.txt").write_text("".join(f"file '{p.name}'\n" for p in parts))
    run("ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", sd / "list.txt", "-c", "copy",
        HERE / "work/base.mp4")
    # graded portrait still for the profile graphic
    src, t = FACE
    run("ffmpeg", "-v", "error", "-y", "-ss", t, "-i", HERE / f"raw/{src}.mp4", "-frames:v", 1, "-vf",
        f"{DELOGO},scale={W}:{H}:flags=lanczos,{GRADE},unsharp=5:5:0.35", HERE / "work/face.jpg")


def overlay():
    run("bash", "-c", f"cd '{HERE}' && NODE_PATH=$(npm root -g) node render.cjs scene.html "
                      f"--w {W} --h {H} --fps {FPS} --dur {DUR} -o work/overlay.mov")


def audio():
    run(sys.executable, HERE / "audio.py")


def final():
    out = HERE / "out/oncoxpress_brand_film_40s.mp4"
    out.parent.mkdir(exist_ok=True)
    run("ffmpeg", "-v", "error", "-y", "-i", HERE / "work/base.mp4", "-i", HERE / "work/overlay.mov",
        "-i", HERE / "work/mix.wav", "-filter_complex", "[0:v][1:v]overlay=format=auto:shortest=1,format=yuv420p[v]",
        "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high",
        "-c:a", "aac", "-b:a", "256k", "-t", DUR, "-movflags", "+faststart", out)
    print(f"  -> {out}")


def sheet():
    out = HERE / "out/sheet.png"
    run("ffmpeg", "-v", "error", "-y", "-i", HERE / "out/oncoxpress_brand_film_40s.mp4", "-vf",
        "fps=0.5,scale=480:-1,drawtext=text='%{pts\\:hms}':x=8:y=8:fontsize=20:fontcolor=white:box=1:boxcolor=black@0.5,"
        "tile=5x4:padding=4:color=white", "-frames:v", 1, out)


STEPS = {"timeline": timeline, "base": base, "overlay": overlay, "audio": audio, "final": final, "sheet": sheet}

if __name__ == "__main__":
    todo = sys.argv[1:] or ["all"]
    if todo == ["all"]:
        todo = list(STEPS)
    for k in todo:
        print(f"[{k}]")
        STEPS[k]()
