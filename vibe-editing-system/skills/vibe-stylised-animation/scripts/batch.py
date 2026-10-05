"""batch: render one video per row of a spreadsheet (personalised videos, series, variants).

    python3 vibe/batch.py data.csv --cmd "python3 scene.py render-row {json} {out}" --name "{slug}"
    python3 vibe/batch.py data.csv --cmd "..." --only 1-3          # test the first rows
    python3 vibe/batch.py data.csv --cmd "..." --workers 3

For each row this writes work/batch/<name>.json (the row as JSON) and runs --cmd with:
    {json}  path to that row's JSON          {out}   out/batch/<file>.mp4
    {file}  the file name (no extension)     {i}     row number (1-based)
    {<column>}  any CSV column, e.g. {first_name} or {name}
--name is a template for file names; {slug} is a safe version of the first column.
(Columns called json/out/file/i/slug are shadowed by these; rename them in the CSV.)
Rows whose output already exists are skipped (re-run safely after a crash). A report is
written to out/batch/report.csv.

CSV tips: first row = column names. UTF-8. Excel: "Save As > CSV UTF-8". Google Sheets: File > Download > CSV.
"""

import argparse
import csv
import json
import os
import re
import shlex
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def q(s):
    """quote a path for the shell (cmd.exe on Windows, sh elsewhere)."""
    return f'"{s}"' if os.name == "nt" else shlex.quote(s)


def slugify(s):
    s = re.sub(r"[^\w\s-]", "", str(s)).strip().lower()
    return re.sub(r"[\s_-]+", "-", s)[:60] or "row"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--cmd", required=True)
    ap.add_argument("--name", default="{i:03d}-{slug}")
    ap.add_argument("--out-dir", default="out/batch")
    ap.add_argument("--workers", type=int, default=1, help="parallel renders (each render may use all cores)")
    ap.add_argument("--only", default=None, help="row range, e.g. 1-5 or 7")
    ap.add_argument("--force", action="store_true", help="re-render existing outputs")
    a = ap.parse_args()

    with open(a.csv, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        sys.exit("CSV has no rows")
    lo, hi = 1, len(rows)
    if a.only:
        x, _, y = a.only.partition("-")
        lo, hi = int(x), int(y or x)
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    jdir = Path("work/batch")
    jdir.mkdir(parents=True, exist_ok=True)
    first_col = list(rows[0].keys())[0]

    jobs = []
    for i, row in enumerate(rows, 1):
        if not lo <= i <= hi:
            continue
        fields = {k.strip(): (v or "").strip() for k, v in row.items() if k}
        name = a.name.format(**{**fields, "i": i, "slug": slugify(fields.get(first_col, i))})
        name = re.sub(r'[<>:"/\\|?*]', "-", name)
        jp = jdir / f"{name}.json"
        jp.write_text(json.dumps({**fields, "_row": i, "_file": name}, indent=1, ensure_ascii=False))
        out = out_dir / f"{name}.mp4"
        cmd = a.cmd.format(**{**fields, "json": q(str(jp)), "out": q(str(out)), "file": name, "i": i,
                              "slug": slugify(fields.get(first_col, i))})
        jobs.append((i, name, out, cmd))

    def run(job):
        i, name, out, cmd = job
        if out.exists() and not a.force:
            return (i, name, "skipped", 0.0, "")
        t0 = time.time()
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        ok = r.returncode == 0 and out.exists()
        err = ""
        if not ok:
            lines = (r.stderr or r.stdout or "").strip().splitlines()
            err = lines[-1] if lines else "no output file"
        print(f"  [{i:3d}] {'OK ' if ok else 'ERR'} {name}  {time.time() - t0:.1f}s  {err}")
        return (i, name, "ok" if ok else "error", round(time.time() - t0, 1), err)

    print(f"{len(jobs)} job(s), {a.workers} at a time ...")
    with ThreadPoolExecutor(max_workers=max(1, a.workers)) as ex:
        results = list(ex.map(run, jobs))
    with open(out_dir / "report.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["row", "name", "status", "seconds", "error"])
        w.writerows(results)
    bad = [r for r in results if r[2] == "error"]
    print(f"done: {sum(r[2] == 'ok' for r in results)} rendered, {sum(r[2] == 'skipped' for r in results)} skipped, "
          f"{len(bad)} failed -> {out_dir / 'report.csv'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
