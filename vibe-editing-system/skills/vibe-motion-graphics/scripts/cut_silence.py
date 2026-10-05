"""cut_silence: remove dead air, filler words and bad takes; optional punch-in jump cuts.

    # word-accurate (best): uses work/words.json from transcribe.py
    python3 scripts/cut_silence.py raw/take1.mp4 --words work/words.json -o work/cut.mp4

    # no transcript: cut by audio level
    python3 scripts/cut_silence.py raw/take1.mp4 -o work/cut.mp4

    # pick + reorder ranges (hook first!); silences inside them are still trimmed
    python3 scripts/cut_silence.py raw/take1.mp4 --words work/words.json --keep 41.2-46.0,3.5-38.0

    # also drop retakes by time range, and zoom every other segment 12% (classic jump cut)
    python3 scripts/cut_silence.py raw/take1.mp4 --words work/words.json --remove 12.3-18.9,40-44.2 --punch 1.12

Writes next to -o:
    edl.json        kept segments: source time -> output time (+ zoom)
    words_cut.json  words re-timed to the cut video (feed this to captions.py)
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vibelib import ff, ffmpeg_bin, filter_script_args, load_words, nice_fps, probe  # noqa: E402

FILLERS = {"um", "umm", "uh", "uhh", "uhm", "erm", "er", "ah", "ahh", "hmm", "hm", "mm", "mhm"}


def norm(w):
    return re.sub(r"[^\w']", "", w.lower())


def keep_from_words(words, gap, pre, post, drop_fillers):
    runs = []
    for w in words:
        if drop_fillers and norm(w["w"]) in FILLERS:
            runs.append(None)          # a filler breaks the run
            continue
        if runs and runs[-1] is not None and w["s"] - runs[-1][1] < gap:
            runs[-1][1] = w["e"]
        else:
            runs.append([w["s"], w["e"]])
    keep = []
    for r in runs:
        if r is None:
            continue
        a, b = max(0.0, r[0] - pre), r[1] + post
        if keep and a <= keep[-1][1]:
            keep[-1][1] = max(keep[-1][1], b)
        else:
            keep.append([a, b])
    return keep


def keep_from_audio(media, dur, noise_db, min_sil, pre, post):
    r = subprocess.run([ffmpeg_bin(), "-hide_banner", "-nostats", "-i", media, "-vn",
                        "-af", f"silencedetect=noise={noise_db}dB:d={min_sil}", "-f", "null", "-"],
                       capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    if len(ends) < len(starts):
        ends.append(dur)
    keep, t = [], 0.0
    for s, e in zip(starts, ends):
        if s > t:
            keep.append([max(0.0, t - pre), min(dur, s + post)])
        t = e
    if t < dur:
        keep.append([max(0.0, t - pre), dur])
    merged = []
    for a, b in keep:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    return merged


def subtract(keep, removes):
    for ra, rb in removes:
        nk = []
        for a, b in keep:
            if rb <= a or ra >= b:
                nk.append([a, b])
                continue
            if ra > a:
                nk.append([a, ra])
            if rb < b:
                nk.append([rb, b])
        keep = nk
    return keep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("media")
    ap.add_argument("-o", "--out", default="work/cut.mp4")
    ap.add_argument("--words", help="words.json from transcribe.py (word-accurate cuts)")
    ap.add_argument("--gap", type=float, default=0.35, help="pauses longer than this are cut (s)")
    ap.add_argument("--pre", type=float, default=0.08, help="lead-in kept before speech (s)")
    ap.add_argument("--post", type=float, default=0.14, help="tail kept after speech (s)")
    ap.add_argument("--keep-fillers", action="store_true", help="don't remove um/uh")
    ap.add_argument("--noise", type=float, default=-35, help="audio mode: silence threshold dB")
    ap.add_argument("--min-silence", type=float, default=0.45, help="audio mode: min silence length (s)")
    ap.add_argument("--remove", default="", help="extra source ranges to drop, e.g. 12.3-18.9,40-44")
    ap.add_argument("--keep", default="", help="only these source ranges, in THIS order, e.g. 41-46,3.5-38")
    ap.add_argument("--punch", type=float, default=1.0, help="zoom on every other segment, e.g. 1.12")
    ap.add_argument("--anchor", default="0.5,0.4", help="zoom centre as x,y fractions (face is usually high)")
    ap.add_argument("--crf", type=int, default=17)
    ap.add_argument("--dry-run", action="store_true", help="print the EDL, don't render")
    a = ap.parse_args()

    info = probe(a.media)
    dur, W, H = info["duration"], info["width"], info["height"]
    W -= W % 2
    H -= H % 2
    fps = nice_fps(info["fps"] or 30)

    if a.words:
        words = load_words(a.words)
        keep = keep_from_words(words, a.gap, a.pre, a.post, not a.keep_fillers)
    else:
        words = []
        keep = keep_from_audio(a.media, dur, a.noise, a.min_silence, a.pre, a.post)
    removes = []
    for part in filter(None, a.remove.split(",")):
        x, _, y = part.partition("-")
        removes.append((float(x), float(y)))
    keep = subtract(keep, removes)
    if a.keep:
        ordered = []
        for part in filter(None, a.keep.split(",")):
            x, _, y = part.partition("-")
            ka, kb = float(x), float(y)
            ordered += [[max(s0, ka), min(s1, kb)] for s0, s1 in keep if s1 > ka and s0 < kb]
        keep = ordered
    keep = [[max(0.0, x), min(dur, y)] for x, y in keep if min(dur, y) - max(0.0, x) >= 0.12]
    merged = []
    for x, y in keep:                      # join touching neighbours (only when in source order)
        if merged and abs(x - merged[-1][1]) < 1e-3:
            merged[-1][1] = y
        else:
            merged.append([x, y])
    keep = merged
    if not keep:
        sys.exit("nothing left to keep; loosen --gap / --noise")

    ax, ay = (float(v) for v in a.anchor.split(","))
    edl, t = [], 0.0
    for i, (x, y) in enumerate(keep):
        z = a.punch if (a.punch > 1.0 and i % 2 == 1) else 1.0
        edl.append({"src_s": round(x, 3), "src_e": round(y, 3), "out_s": round(t, 3), "out_e": round(t + y - x, 3),
                    "zoom": z})
        t += y - x
    print(f"{dur:.1f}s -> {t:.1f}s  ({len(edl)} segments, {dur - t:.1f}s removed)")

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    (out.parent / "edl.json").write_text(json.dumps(edl, indent=1))
    if words:
        cut_words = []
        for w in words:
            for seg in edl:
                if w["s"] >= seg["src_s"] - 0.02 and w["e"] <= seg["src_e"] + 0.02:
                    o = seg["out_s"] - seg["src_s"]
                    cut_words.append({**w, "s": round(max(seg["out_s"], w["s"] + o), 3),
                                      "e": round(min(seg["out_e"], w["e"] + o), 3)})
                    break
        (out.parent / "words_cut.json").write_text(json.dumps(cut_words, indent=0))
        print(f"words re-timed -> {out.parent / 'words_cut.json'}")
    if a.dry_run:
        for s in edl:
            print(f"  keep {s['src_s']:8.2f} - {s['src_e']:8.2f}  -> {s['out_s']:7.2f}  zoom {s['zoom']}")
        return

    parts, labels = [], []
    for i, s in enumerate(edl):
        d = s["src_e"] - s["src_s"]
        z = s["zoom"]
        crop = f",crop=iw/{z}:ih/{z}:(iw-iw/{z})*{ax}:(ih-ih/{z})*{ay}" if z > 1 else ""
        parts.append(f"[0:v]trim=start={s['src_s']}:end={s['src_e']},setpts=PTS-STARTPTS{crop},"
                     f"scale={W}:{H},setsar=1[v{i}]")
        lab = f"[v{i}]"
        if info["has_audio"]:
            fo = max(0.0, d - 0.012)
            parts.append(f"[0:a]atrim=start={s['src_s']}:end={s['src_e']},asetpts=PTS-STARTPTS,"
                         f"afade=t=in:d=0.012,afade=t=out:st={fo:.3f}:d=0.012[a{i}]")
            lab += f"[a{i}]"
        labels.append(lab)
    n = len(edl)
    if info["has_audio"]:
        parts.append("".join(labels) + f"concat=n={n}:v=1:a=1[vc][ac]")
    else:
        parts.append("".join(labels) + f"concat=n={n}:v=1:a=0[vc]")
    parts.append(f"[vc]fps={fps}[vo]")
    graph = ";\n".join(parts)
    maps = ["-map", "[vo]"] + (["-map", "[ac]"] if info["has_audio"] else [])
    print("rendering ...")
    ff("-i", a.media, *filter_script_args(graph, out.with_suffix(".graph.txt")), *maps,
       "-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf), "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out)
    out.with_suffix(".graph.txt").unlink(missing_ok=True)
    print(f"done -> {out}")


if __name__ == "__main__":
    main()
