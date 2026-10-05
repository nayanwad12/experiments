"""build_course: compile the course content into admin-ready files.

    python3 course/build_course.py            # course.json + COURSE.md + branded PDFs + resources zip
    python3 course/build_course.py --no-pdf   # text outputs only

Sources (edit these):
    course/modules/NN-*.md        one file per module (format below)
    course/resources/src/RNN-*.md one file per downloadable resource (+ any .csv/.json beside it)

Outputs (generated):
    course/course.json            every module, lesson, note, prompt and resource, for the Raw JSON tab / import
    course/COURSE.md              the whole course as one readable document (copy-paste into the admin)
    course/resources/pdf/*.pdf    branded Ideabro PDFs for the Course Resources tab
    course/Vibe-Editing-Course-Resources.zip   every PDF + template file in one download

Module file format
    # Module 3: Title
    > one-line summary
    Outcome: ...
    Assignment: ...
    Resources: R05, R06
    ## Lesson title | video | 9 min
    Summary: ...
    Prompt: ...            (optional: a copy-paste prompt students try)
    Resources: R05         (optional)
    ### Notes
    markdown ...
"""

import html
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODS = ROOT / "modules"
RES = ROOT / "resources" / "src"
PDF = ROOT / "resources" / "pdf"
BUILD = ROOT / ".build"
SCRIPTS = ROOT.parent / "vibe-editing-system" / "shared" / "scripts"


# ------------------------------------------------------------------ parse
def parse_resources():
    out = []
    for p in sorted(RES.glob("R*.md")):
        rid = p.name.split("-")[0]
        lines = p.read_text().splitlines()
        title = lines[0].lstrip("# ").strip()
        desc = next((ln.strip() for ln in lines[1:] if ln.strip() and not ln.startswith(("#", "|", "-"))), "")
        extras = sorted(x.name for x in RES.glob(f"{rid}-*") if x.suffix != ".md")
        out.append({"id": rid, "title": title, "description": desc, "file": f"{p.stem}.pdf",
                    "type": "pdf", "extra_files": extras})
    return out


def parse_module(path):
    text = path.read_text()
    head, *lessons = re.split(r"^## ", text, flags=re.M)
    m = re.match(r"# Module (\d+): (.+)", head)
    mod = {"number": int(m.group(1)), "title": m.group(2).strip(), "summary": "", "outcome": "",
           "assignment": "", "resources": [], "lessons": []}
    for ln in head.splitlines()[1:]:
        if ln.startswith(">"):
            mod["summary"] = ln[1:].strip()
        elif ln.startswith("Outcome:"):
            mod["outcome"] = ln.split(":", 1)[1].strip()
        elif ln.startswith("Assignment:"):
            mod["assignment"] = ln.split(":", 1)[1].strip()
        elif ln.startswith("Resources:"):
            mod["resources"] = [r.strip() for r in ln.split(":", 1)[1].split(",") if r.strip()]
    for i, block in enumerate(lessons, 1):
        first, _, rest = block.partition("\n")
        parts = [x.strip() for x in first.split("|")]
        title, kind, dur = parts[0], parts[1] if len(parts) > 1 else "video", parts[2] if len(parts) > 2 else ""
        meta, _, notes = rest.partition("### Notes")
        lesson = {"number": f"{mod['number']}.{i}", "title": title, "type": kind,
                  "duration_min": int(re.sub(r"\D", "", dur) or 0), "summary": "", "prompt": "",
                  "resources": [], "notes_md": notes.strip()}
        for ln in meta.splitlines():
            if ln.startswith("Summary:"):
                lesson["summary"] = ln.split(":", 1)[1].strip()
            elif ln.startswith("Prompt:"):
                lesson["prompt"] = ln.split(":", 1)[1].strip()
            elif ln.startswith("Resources:"):
                lesson["resources"] = [r.strip() for r in ln.split(":", 1)[1].split(",") if r.strip()]
        mod["lessons"].append(lesson)
    return mod


# ------------------------------------------------------------------ outputs
def write_json(course):
    (ROOT / "course.json").write_text(json.dumps(course, indent=2, ensure_ascii=False) + "\n")


def write_markdown(course, res_by_id):
    n_l = sum(len(m["lessons"]) for m in course["modules"])
    mins = sum(l["duration_min"] for m in course["modules"] for l in m["lessons"])
    out = [f"# {course['title']}", f"*by {course['by']}: {course['tagline']}*", "",
           f"**{len(course['modules'])} modules · {n_l} lessons · {mins // 60} h {mins % 60} min of content · "
           f"{len(course['resources'])} downloadable resources · 9 Claude skills**", "",
           "## Course outline", "", "| # | module | lessons | time |", "|---|---|---|---|"]
    for m in course["modules"]:
        t = sum(l["duration_min"] for l in m["lessons"])
        out.append(f"| {m['number']} | {m['title']} | {len(m['lessons'])} | {t} min |")
    out += ["", "## Course resources", "", "| id | resource | what it is |", "|---|---|---|"]
    for r in course["resources"]:
        out.append(f"| {r['id']} | **{r['title']}** | {r['description']} |")
    for m in course["modules"]:
        out += ["", "---", "", f"# Module {m['number']}: {m['title']}", "", f"> {m['summary']}", "",
                f"**Outcome:** {m['outcome']}", "", f"**Assignment:** {m['assignment']}", ""]
        if m["resources"]:
            out.append("**Module resources:** " + ", ".join(f"{r} {res_by_id[r]['title']}" for r in m["resources"]))
            out.append("")
        for l in m["lessons"]:
            out += [f"## {l['number']} {l['title']}", f"*{l['type']} · {l['duration_min']} min*", "", l["summary"], ""]
            if l["prompt"]:
                out += ["**Try this prompt:**", f"> {l['prompt']}", ""]
            if l["resources"]:
                out += ["**Resources:** " + ", ".join(f"{r} {res_by_id[r]['title']}" for r in l["resources"]), ""]
            out += ["**Lesson notes**", "", l["notes_md"], ""]
    (ROOT / "COURSE.md").write_text("\n".join(out))


CSS = """
@font-face{font-family:Display;src:url('FONTS/Unbounded-900.ttf')}
@font-face{font-family:Body;src:url('FONTS/InterTight-400.ttf')}
@font-face{font-family:Body;font-weight:700;src:url('FONTS/InterTight-700.ttf')}
@font-face{font-family:Mono;src:url('FONTS/JetBrainsMono-700.ttf')}
@page{size:A4;margin:16mm 15mm 18mm 15mm}
:root{--ink:#0B0B0D;--paper:#F2EEE3;--lime:#D4FF3F;--peri:#C4C6FF;--mute:#5d5a52}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{font-family:Body,Helvetica,Arial,sans-serif;color:var(--ink);font-size:10.5pt;line-height:1.5;margin:0}
.top{display:flex;justify-content:space-between;align-items:center;font-family:Mono,monospace;font-size:7.5pt;
     letter-spacing:.18em;text-transform:uppercase;border-bottom:1.5px solid var(--ink);padding-bottom:6px;margin-bottom:18px}
.top .id{background:var(--lime);padding:3px 8px;border-radius:99px}
h1{font-family:Display,sans-serif;font-size:27pt;line-height:1.05;text-transform:uppercase;margin:6px 0 6px;letter-spacing:-.01em}
h1+p{font-size:12pt;color:var(--mute);margin-top:0}
h2{font-family:Mono,monospace;font-size:10pt;letter-spacing:.14em;text-transform:uppercase;margin:22px 0 8px;
   display:flex;align-items:center;gap:8px;break-after:avoid}
h2:before{content:"";width:9px;height:9px;background:var(--ink);display:inline-block}
table{border-collapse:collapse;width:100%;margin:6px 0 10px;font-size:9.5pt;break-inside:auto}
tr{break-inside:avoid}
th{font-family:Mono,monospace;font-size:7.5pt;letter-spacing:.12em;text-transform:uppercase;text-align:left;
   background:var(--ink);color:var(--paper);padding:6px 8px}
td{padding:6px 8px;border-bottom:1px solid #d8d3c6;vertical-align:top}
tr:nth-child(even) td{background:#f7f5ef}
code,pre{font-family:Mono,monospace;font-size:8.5pt}
code{background:#ece8dc;padding:1px 4px;border-radius:4px}
pre{background:var(--ink);color:var(--paper);padding:10px 12px;border-radius:10px;white-space:pre-wrap}
pre code{background:none;color:inherit;padding:0}
blockquote{margin:8px 0;padding:8px 12px;border-left:5px solid var(--lime);background:#f7f5ef;border-radius:0 8px 8px 0}
ul,ol{padding-left:20px} li{margin:2px 0}
strong{font-weight:700}
.foot{position:fixed;bottom:-10mm;left:0;right:0;font-family:Mono,monospace;font-size:7pt;letter-spacing:.16em;
      text-transform:uppercase;color:var(--mute);display:flex;justify-content:space-between}
"""


def render_pdfs(resources):
    import markdown
    fonts = BUILD / "fonts"
    if not (fonts / "Unbounded-900.ttf").exists():
        fonts.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, str(SCRIPTS / "fonts.py"), "Unbounded:900", "Inter Tight:400,700",
                        "JetBrains Mono:700", "-o", str(fonts)], check=True)
    css = CSS.replace("FONTS", fonts.resolve().as_uri())
    jobs = []
    (BUILD / "html").mkdir(parents=True, exist_ok=True)
    PDF.mkdir(parents=True, exist_ok=True)
    for r in resources:
        src = next(RES.glob(f"{r['id']}-*.md"))
        body = markdown.markdown(src.read_text(), extensions=["tables", "fenced_code", "sane_lists"])
        page = (f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>"
                f"<div class='top'><span>Ideabro Studio · Vibe Editing System</span><span class='id'>{r['id']}</span></div>"
                f"{body}<div class='foot'><span>Direct the vibe. Let AI do the keyframes.</span>"
                f"<span>{html.escape(r['title'])}</span></div></body></html>")
        hp = BUILD / "html" / f"{src.stem}.html"
        hp.write_text(page)
        jobs.append([str(hp.resolve()), str((PDF / r["file"]).resolve())])
    (BUILD / "jobs.json").write_text(json.dumps(jobs))
    js = BUILD / "pdf.cjs"
    js.write_text("""
const { chromium } = require('playwright');
const jobs = require(process.argv[2]);
(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  for (const [src, out] of jobs) {
    await p.goto('file://' + src); await p.evaluate(() => document.fonts.ready);
    await p.pdf({ path: out, format: 'A4', printBackground: true, preferCSSPageSize: true });
    console.log('  pdf', out.split('/').pop());
  }
  await b.close();
})();
""")
    root = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    subprocess.run(["node", str(js), str((BUILD / "jobs.json").resolve())], check=True,
                   env={**__import__("os").environ, "NODE_PATH": root})


def write_zip(resources):
    z = ROOT / "Vibe-Editing-Course-Resources.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in resources:
            pdf = PDF / r["file"]
            if pdf.exists():
                zf.write(pdf, f"Vibe-Editing-Resources/{r['file']}")
            for x in r["extra_files"]:
                zf.write(RES / x, f"Vibe-Editing-Resources/{x}")
    return z


def main():
    resources = parse_resources()
    res_by_id = {r["id"]: r for r in resources}
    modules = [parse_module(p) for p in sorted(MODS.glob("*.md"))]
    for m in modules:
        for rid in m["resources"] + [x for l in m["lessons"] for x in l["resources"]]:
            if rid not in res_by_id:
                sys.exit(f"module {m['number']}: unknown resource {rid}")
    course = {"title": "Vibe Editing System", "by": "Ideabro Studio",
              "tagline": "Direct the vibe. Let AI do the keyframes.",
              "description": "Make reels, ads, motion graphics, animation, VFX, AI films, soundtracks and bulk "
                             "personalised videos by directing AI in plain language. No timeline, no keyframes.",
              "modules": modules, "resources": resources}
    write_json(course)
    write_markdown(course, res_by_id)
    n_l = sum(len(m["lessons"]) for m in modules)
    mins = sum(l["duration_min"] for m in modules for l in m["lessons"])
    print(f"{len(modules)} modules, {n_l} lessons, {mins // 60} h {mins % 60} min, {len(resources)} resources")
    if "--no-pdf" not in sys.argv:
        render_pdfs(resources)
        print("zip ->", write_zip(resources))


if __name__ == "__main__":
    main()
