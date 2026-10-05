"""captions: word-timed animated captions (.ass) + plain subtitles (.srt), optional burn-in.

    python3 scripts/captions.py work/words_cut.json --video work/cut.mp4 --style pop -o work/captions.ass
    python3 scripts/captions.py work/words_cut.json --video work/cut.mp4 --style pop --burn out/captioned.mp4

Styles
    pop       1-3 BIG words, active word highlighted + pops (Reels/TikTok/Shorts look)   [default]
    karaoke   a line fills with colour as it is spoken
    clean     sentence subtitles on a soft box (YouTube, interviews, courses)
    minimal   small outlined subtitles, no box (cinematic, brand films)

Colours and font come from brand.json (Ideabro house style by default):
caption = text colour, caption_hi = highlight, impact font for pop/karaoke, body font for clean/minimal.
--emphasis "free,today,AI" always paints those words in the accent colour.
"""

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vibelib import color, ff, load_brand, load_words, probe  # noqa: E402


def ass_color(hexstr, alpha=0):
    r, g, b = (int(hexstr.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"


def ass_time(t):
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    cs = int(round((s - int(s)) * 100))
    s = int(s)
    if cs == 100:
        s, cs = s + 1, 0
    return f"{int(h)}:{int(m):02d}:{s:02d}.{cs:02d}"


def srt_time(t):
    h, rem = divmod(max(0.0, t), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)) % 1000:03d}"


def family(spec):
    return spec.split(":")[0].strip()


def chunk_words(words, max_words, max_chars, gap_break=0.45):
    chunks, cur = [], []
    for w in words:
        if cur:
            prev = cur[-1]
            text_len = sum(len(x["w"]) + 1 for x in cur) + len(w["w"])
            if (len(cur) >= max_words or text_len > max_chars or w["s"] - prev["e"] > gap_break
                    or re.search(r"[.?!]$", prev["w"]) or (len(cur) >= 2 and prev["w"].endswith(","))):
                chunks.append(cur)
                cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    return chunks


def clean_word(w, upper):
    w = w.strip()
    if upper:
        w = w.upper()
        w = re.sub(r"[,.]$", "", w)   # punchy captions drop trailing commas/periods
    return w.replace("{", "(").replace("}", ")")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("words")
    ap.add_argument("-o", "--out", default=None, help="captions .ass path (default: next to words)")
    ap.add_argument("--video", help="video to size captions for (or use --size)")
    ap.add_argument("--size", default=None, help="WxH, e.g. 1080x1920")
    ap.add_argument("--style", default="pop", choices=["pop", "karaoke", "clean", "minimal"])
    ap.add_argument("--font", default=None, help="font family name (default from brand.json)")
    ap.add_argument("--fonts-dir", default="fonts")
    ap.add_argument("--max-words", type=int, default=None)
    ap.add_argument("--pos", type=float, default=None, help="vertical centre of captions, 0=top 1=bottom")
    ap.add_argument("--scale", type=float, default=1.0, help="font size multiplier")
    ap.add_argument("--no-upper", action="store_true", help="keep original case for pop/karaoke")
    ap.add_argument("--emphasis", default="", help="comma list of words always in accent colour")
    ap.add_argument("--offset", type=float, default=0.0, help="shift all captions (s)")
    ap.add_argument("--burn", default=None, help="write a video with captions burned in")
    a = ap.parse_args()

    brand = load_brand(".")
    if a.size:
        W, H = (int(v) for v in a.size.lower().split("x"))
    elif a.video:
        info = probe(a.video)
        W, H = info["width"], info["height"]
    else:
        W, H = 1080, 1920
    vertical = H > W
    m = min(W, H)
    words = load_words(a.words)
    for w in words:
        w["s"] += a.offset
        w["e"] += a.offset
    emph = {e.strip().lower() for e in a.emphasis.split(",") if e.strip()}

    st = a.style
    upper = st in ("pop", "karaoke") and not a.no_upper
    fg = color(brand, "caption")
    hi = color(brand, "caption_hi")
    ink = color(brand, "fg")
    font = a.font or family(brand["fonts"]["impact" if st in ("pop", "karaoke") else "body"])
    size = {"pop": 0.12, "karaoke": 0.08, "clean": 0.048, "minimal": 0.042}[st] * m * a.scale
    max_words = a.max_words or {"pop": 3, "karaoke": 6, "clean": 12, "minimal": 10}[st]
    max_chars = {"pop": 16, "karaoke": 36, "clean": 64, "minimal": 56}[st]
    pos = a.pos if a.pos is not None else {"pop": 0.68 if vertical else 0.80, "karaoke": 0.72 if vertical else 0.84,
                                           "clean": 0.78 if vertical else 0.90,
                                           "minimal": 0.80 if vertical else 0.91}[st]
    margin_v = int(H * (1 - pos) - size * 0.6)
    margin_lr = int(W * 0.08)
    outline = {"pop": 0.075, "karaoke": 0.06, "clean": 0.0, "minimal": 0.06}[st] * size
    border_style = 3 if st == "clean" else 1
    back = ass_color(ink, 0x50) if st == "clean" else ass_color("#000000", 0x80)
    primary, secondary = (ass_color(hi), ass_color(fg)) if st == "karaoke" else (ass_color(fg), ass_color(hi))
    shadow = 0 if st in ("pop", "clean") else max(1, int(size * 0.04))
    clean_pad = int(size * 0.25) if st == "clean" else outline

    head = f"""[Script Info]
; Ideabro Studio · Vibe Editing System captions
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},{size:.0f},{primary},{secondary},{ass_color('#000000') if st != 'clean' else back},{back},-1,0,0,0,100,100,{1 if st == 'pop' else 0},0,{border_style},{clean_pad:.1f},{shadow},2,{margin_lr},{margin_lr},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events, srt = [], []
    chunks = chunk_words(words, max_words, max_chars)
    for ci, ch in enumerate(chunks):
        c0 = ch[0]["s"]
        nxt = chunks[ci + 1][0]["s"] if ci + 1 < len(chunks) else ch[-1]["e"] + 0.6
        c1 = min(max(ch[-1]["e"] + 0.25, c0 + 0.35), nxt)
        toks = [clean_word(w["w"], upper) for w in ch]
        srt.append((c0, c1, " ".join(w["w"].strip() for w in ch)))
        is_emph = [re.sub(r"[^\w']", "", w["w"].lower()) in emph for w in ch]
        if st == "pop":
            for i, w in enumerate(ch):
                s = c0 if i == 0 else w["s"]
                e = ch[i + 1]["s"] if i + 1 < len(ch) else c1
                if e - s < 0.02:
                    continue
                parts = []
                for j, tok in enumerate(toks):
                    if j == i:
                        parts.append(r"{\c" + ass_color(hi) + r"\fscx108\fscy108}" + tok + r"{\r}")
                    elif is_emph[j]:
                        parts.append(r"{\c" + ass_color(hi) + "}" + tok + r"{\r}")
                    else:
                        parts.append(tok)
                intro = r"{\fad(50,0)\fscx80\fscy80\t(0,110,\fscx100\fscy100)}" if i == 0 else ""
                events.append(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,{intro}{' '.join(parts)}")
        elif st == "karaoke":
            parts, t = [], c0
            for j, (w, tok) in enumerate(zip(ch, toks)):
                lead = int(round((w["s"] - t) * 100))
                if lead > 0:
                    parts.append(r"{\k" + str(lead) + "}")
                k = max(1, int(round((w["e"] - w["s"]) * 100)))
                col = r"\1c" + ass_color(hi) + r"\2c" + ass_color(hi) if is_emph[j] else ""
                parts.append(r"{\kf" + str(k) + col + "}" + tok + (" " if j < len(ch) - 1 else ""))
                t = w["e"]
            events.append(f"Dialogue: 0,{ass_time(c0)},{ass_time(c1)},Cap,,0,0,0,,{{\\fad(80,80)}}{''.join(parts)}")
        else:
            txt = []
            for j, tok in enumerate(toks):
                txt.append(r"{\c" + ass_color(hi) + "}" + tok + r"{\r}" if is_emph[j] else tok)
            events.append(f"Dialogue: 0,{ass_time(c0)},{ass_time(c1)},Cap,,0,0,0,,{{\\fad(60,60)}}{' '.join(txt)}")

    out = Path(a.out) if a.out else Path(a.words).with_name("captions.ass")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(head + "\n".join(events) + "\n", encoding="utf-8")
    out.with_suffix(".srt").write_text("\n".join(f"{i + 1}\n{srt_time(s)} --> {srt_time(e)}\n{t}\n"
                                                 for i, (s, e, t) in enumerate(srt)), encoding="utf-8")
    print(f"{len(chunks)} caption blocks ({st}) -> {out}  (+ {out.with_suffix('.srt').name})")

    if a.burn:
        if not a.video:
            sys.exit("--burn needs --video")
        cwd = out.parent.resolve()
        fonts_rel = os.path.relpath(Path(a.fonts_dir).resolve(), cwd).replace("\\", "/")
        vf = f"subtitles='{out.name}':fontsdir='{fonts_rel}'"
        burn = Path(a.burn).resolve()
        burn.parent.mkdir(parents=True, exist_ok=True)
        ff("-i", Path(a.video).resolve(), "-vf", vf, "-c:v", "libx264", "-crf", "17", "-preset", "medium",
           "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", burn, cwd=cwd)
        print(f"burned -> {a.burn}")


if __name__ == "__main__":
    main()
