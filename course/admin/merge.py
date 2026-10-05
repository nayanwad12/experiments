"""merge: add the generated course (course/course.json) into the academy's Raw JSON without touching existing material.

    python3 course/admin/merge.py      # -> course/admin/vibe-editing.updated.json

Rules
- Every existing module, lesson, resource and course field is kept exactly as it was (verified at the end).
- Existing modules (Getting Started, Launch Videos, Motion Graphics) get new lessons appended after their own.
- New modules are appended after them (n = 4, 5, ...), with empty covers to fill in after upload.
- New lessons have no video yet: comingSoon = true, video.src = "".
- Empty course/module text fields ("" values) are filled; non-empty values are never changed.
- New resources get href "" until the files are uploaded (see the printed list).
"""

import copy
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORIG = json.loads((HERE / "original.json").read_text())
COURSE = json.loads((HERE.parent / "course.json").read_text())

# my module number -> (existing module id or None, which of my lessons to add; None = all)
PLAN = [
    (1, "getting-started", ["The toolkit: Claude Code, Python, ffmpeg (and why no timeline)",
                            "Your first edit in 10 minutes",
                            "The Vibe Loop: Brief → Stills → Draft → Final",
                            "Your project folder & versioning (your undo button)"]),
    (6, "launch-videos", None),
    (7, "motion-graphics", None),
    (2, None, None),   # Skills Pack (bonus)
    (3, None, None),   # Director's Brief
    (4, None, None),   # Talking-Head
    (5, None, None),   # Sound
    (8, None, None),   # Stylised Animation
    (9, None, None),   # AI Footage & VFX
    (10, None, None),  # Bulk, Workflow & Getting Paid
]
NEW_MODULE_IDS = {2: "skills-pack", 3: "directors-brief", 4: "talking-head-editing", 5: "sound-design-music",
                  8: "stylised-animation", 9: "ai-footage-vfx", 10: "bulk-workflow-business"}

SKILL_FILES = [
    ("vibe-editing-system", "Skill: Start Here (Vibe Editing System)",
     "Picks the right playbook for any video, sets up tools and project, shows test frames."),
    ("vibe-talking-head", "Skill: Talking-Head & Creator Videos",
     "Reels from raw takes, podcast clips, YouTube edits, testimonials, course lessons."),
    ("vibe-launch-ads", "Skill: Launch Videos & Ads",
     "Promos, product launches, social ads + variants, app demos, product videos."),
    ("vibe-motion-graphics", "Skill: Motion Graphics",
     "Showreels, explainers, kinetic type, logo reveals, infographics, transparent packs."),
    ("vibe-stylised-animation", "Skill: Stylised Animation",
     "Claymation, crayon, paper-cut, doodle and talking cartoon mascots."),
    ("vibe-vfx", "Skill: VFX & Editing Magic",
     "Background swap, text behind you, tracking, cinematic looks, slow-mo."),
    ("vibe-ai-footage", "Skill: AI Footage → Films",
     "Veo/Sora/Kling clips into films that don't look AI, faceless channels."),
    ("vibe-audio-videos", "Skill: Audio, Music & Voiceover",
     "Original music, 14 SFX, AI voiceover (incl. Hindi), audiograms, visualisers."),
    ("vibe-bulk-videos", "Skill: Bulk & Automated Videos",
     "Personalised videos from a spreadsheet, every format, multi-language."),
]

PLATFORMS = [
    ("Claude Code", "https://code.claude.com/docs", "The AI editor you direct. Desktop app, terminal or VS Code.", "Required"),
    ("Python", "https://www.python.org/downloads/", "Runs the editing tools. Install 3.10 or newer.", "Required"),
    ("FFmpeg", "https://ffmpeg.org/download.html", "The video engine (the skills install it automatically if missing).", "Auto-installed"),
    ("Google Fonts", "https://fonts.google.com", "Free brand fonts the skills download for you.", "Free"),
    ("ElevenLabs", "https://elevenlabs.io", "Premium AI voiceovers (the skills also include a free local voice).", "Optional"),
    ("Pinterest", "https://www.pinterest.com", "Collect visual references and style frames for your briefs.", "Free"),
    ("Coolors", "https://coolors.co", "Build a colour palette for a brand in seconds.", "Free"),
]


def slug(s):
    s = s.lower().replace("&", "and").replace("→", "to")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:70]


def lesson_item(lesson, idx, used_ids):
    base = slug(lesson["title"])
    lid, k = base, 2
    while lid in used_ids:
        lid, k = f"{base}-{k}", k + 1
    used_ids.add(lid)
    tags = {"reading": ["Reading"], "assignment": ["Capstone"]}.get(lesson["type"], [])
    return {
        "id": lid,
        "doc": [],
        "idx": idx,
        "desc": lesson["summary"],
        "kind": "video",
        "tags": tags,
        "type": "lesson",
        "title": lesson["title"],
        "video": {"src": "", "type": "mp4"},
        "duration": f"{lesson['duration_min']} min" if lesson["duration_min"] else "",
        "comingSoon": True,
    }


def module_description(m):
    return f"{m['summary']} By the end: {m['outcome']} Assignment: {m['assignment']}"


def main():
    out = copy.deepcopy(ORIG)
    mine = {m["number"]: m for m in COURSE["modules"]}
    used_ids = {it["id"] for m in out["modules"] for it in m["items"]}
    by_id = {m["id"]: m for m in out["modules"]}
    next_n = max(m["n"] for m in out["modules"]) + 1

    for num, existing_id, only in PLAN:
        src = mine[num]
        lessons = [l for l in src["lessons"] if only is None or l["title"] in only]
        if only is not None and len(lessons) != len(only):
            raise SystemExit(f"module {num}: some lesson titles not found")
        if existing_id:
            mod = by_id[existing_id]
            if not mod.get("description"):
                mod["description"] = module_description(src)
        else:
            mod = {"n": next_n, "id": NEW_MODULE_IDS[num], "type": "lessons", "cover": "", "items": [],
                   "title": src["title"], "banner": "", "description": module_description(src)}
            out["modules"].append(mod)
            next_n += 1
        start = len(mod["items"])
        for i, l in enumerate(lessons, start + 1):
            mod["items"].append(lesson_item(l, f"{mod['n']}.{i}", used_ids))

    # course-level text (only where empty)
    if not out.get("short"):
        out["short"] = "Direct the vibe. Let AI do the keyframes."
    if not out.get("description"):
        out["description"] = (
            "Make reels, launch videos, motion graphics, animation, VFX, AI-footage films, soundtracks and "
            "hundreds of personalised videos by directing AI in plain language. No timeline, no keyframes. "
            "10 modules, 9 ready-made Claude skills, 21 downloadable guides and templates, a 30-day challenge "
            "and a client-style capstone, by Ideabro Studio.")

    # resources (appended; existing entries untouched)
    res = out["resources"]
    res["tools"] += [
        {"tag": "Download and Use", "href": "", "text": "All 9 Claude skills in one zip. Unzip into ~/.claude/skills.",
         "title": "Vibe Editing Skills Pack (all 9 skills)"},
        {"tag": "Download and Use", "href": "", "text": "Every PDF guide, template and cheat sheet in one download.",
         "title": "Course Resources Pack (ZIP)"},
        {"tag": "Template", "href": "", "text": "Plan every second: picture, sound and on-screen text.",
         "title": "Beat Table Template (CSV)"},
    ]
    res["agents"] += [{"tag": "Download and Use", "href": "", "text": text, "title": title}
                      for _, title, text in SKILL_FILES]
    res["library"] += [{"tag": "PDF", "href": "", "text": r["description"], "title": r["title"]}
                       for r in COURSE["resources"]]
    res["platforms"] += [{"tag": tag, "href": href, "text": text, "title": title}
                         for title, href, text, tag in PLATFORMS]
    out["resourcesCount"] = sum(len(v) for v in res.values() if isinstance(v, list))

    verify(ORIG, out)
    path = HERE / "vibe-editing.updated.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    n_items = sum(len(m["items"]) for m in out["modules"])
    print(f"modules {len(ORIG['modules'])} -> {len(out['modules'])}, lessons "
          f"{sum(len(m['items']) for m in ORIG['modules'])} -> {n_items}, resources {out['resourcesCount']}")
    print("->", path)
    print("\nupload these, then paste each link into its empty href:")
    for sec, items in res.items():
        for it in items:
            if isinstance(it, dict) and not it.get("href"):
                print(f"  [{sec}] {it['title']}")
    print("\nnew modules needing a cover image (course/admin/covers/):")
    for m in out["modules"]:
        if not m["cover"]:
            print(f"  {m['n']:2d} {m['id']}")


def verify(orig, new):
    """Every original value must still be present and unchanged (empty strings may be filled)."""
    def walk(a, b, path):
        if isinstance(a, dict):
            for k, v in a.items():
                if k not in b:
                    raise SystemExit(f"lost key {path}.{k}")
                if v == "" and isinstance(b[k], str):
                    continue
                if k == "resourcesCount":
                    continue
                walk(v, b[k], f"{path}.{k}")
        elif isinstance(a, list):
            if len(b) < len(a):
                raise SystemExit(f"list shrank at {path}")
            for i, v in enumerate(a):
                walk(v, b[i], f"{path}[{i}]")
        elif a != b:
            raise SystemExit(f"changed {path}: {a!r} -> {b!r}")
    walk(orig, new, "$")


if __name__ == "__main__":
    main()
