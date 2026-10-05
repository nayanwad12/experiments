"""fonts: download static TTF files for any Google Font (all free / open licence).

    python3 scripts/fonts.py "Anton" "Unbounded:900" "Inter Tight:400,700" -o fonts/
    python3 scripts/fonts.py --brand -o fonts/        # every font in brand.json (Ideabro defaults)

Files are saved as  fonts/<Family>-<weight>[-italic].ttf  e.g. fonts/Unbounded-900.ttf
"""

import argparse
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vibelib import load_brand  # noqa: E402

UA = "Mozilla/5.0 (compatible; vibe-editing-fonts)"  # a non-browser UA makes Google serve .ttf


def parse_spec(spec):
    fam, _, w = spec.partition(":")
    weights = [x.strip() for x in w.split(",") if x.strip()] or ["400"]
    return fam.strip(), weights


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def download(spec, out_dir):
    fam, weights = parse_spec(spec)
    axis = []
    for w in weights:
        ital = w.endswith("i")
        axis.append((1 if ital else 0, int(w.rstrip("i"))))
    axis = sorted(set(axis))
    if any(i for i, _ in axis):
        q = "ital,wght@" + ";".join(f"{i},{w}" for i, w in axis)
    else:
        q = "wght@" + ";".join(str(w) for _, w in axis)
    url = "https://fonts.googleapis.com/css2?family=" + urllib.parse.quote_plus(fam) + ":" + q
    try:
        css = fetch(url).decode()
    except Exception:
        # single-weight families (Anton) reject the axis query; retry plain
        css = fetch("https://fonts.googleapis.com/css2?family=" + urllib.parse.quote_plus(fam)).decode()
    saved = []
    for block in re.findall(r"@font-face\s*{(.*?)}", css, re.S):
        style = re.search(r"font-style:\s*(\w+)", block).group(1)
        weight = re.search(r"font-weight:\s*(\d+)", block).group(1)
        src = re.search(r"url\((.*?)\)", block).group(1)
        name = f"{fam.replace(' ', '')}-{weight}{'-italic' if style == 'italic' else ''}.ttf"
        dst = Path(out_dir) / name
        if not dst.exists():
            dst.write_bytes(fetch(src))
        saved.append(dst)
    return saved


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fonts", nargs="*", help='"Family" or "Family:400,700,400i"')
    ap.add_argument("-o", "--out", default="fonts")
    ap.add_argument("--brand", action="store_true", help="download every font listed in brand.json")
    a = ap.parse_args()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    specs = list(a.fonts)
    if a.brand:
        specs += list(load_brand(".").get("fonts", {}).values())
    if not specs:
        ap.error("name at least one font, or use --brand")
    for spec in dict.fromkeys(specs):
        try:
            for p in download(spec, a.out):
                print("  font", p)
        except Exception as e:
            print(f"  could not fetch {spec!r} ({e}); offline? the scripts fall back to a default font")


if __name__ == "__main__":
    main()
