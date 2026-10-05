# Vibe Editing System: course material

**10 modules · 76 lessons · 13 h 12 min of planned content · 21 downloadable resources · 9 Claude skills**

| file | use it for |
|---|---|
| `COURSE.md` | the whole course in one readable doc: copy module/lesson titles, summaries and notes into the admin |
| `course.json` | the same content as structured JSON (modules → lessons → notes, prompts, resources) for the **Raw JSON** tab or an import script |
| `resources/pdf/*.pdf` | 21 branded PDFs for the **Course Resources** tab |
| `Vibe-Editing-Course-Resources.zip` | all PDFs + the beat-table CSV in one download |
| `../vibe-editing-system/dist/*.zip` | the 9 skill downloads (attach to resource R02 and to Module 2's lessons) |

## Filling the admin
1. **Modules tab**: create the 10 modules in this order (titles have no numbers, so reordering never breaks them).
2. **Each module**: paste `summary` as the description, then add its lessons with `title`, `summary`, the `prompt`
   (as a "Try this prompt" box) and `notes_md` as the lesson notes.
3. **Course Resources tab**: upload the 21 PDFs, the CSV and the skill zips.
4. **Lesson resources**: each lesson lists resource IDs (e.g. `R05`). Link the matching PDF.

Lessons marked `video` need a recording. Until then, the notes and prompt make each lesson usable as a reading lesson.

## Editing
Change `modules/*.md` or `resources/src/*.md`, then run `python3 course/build_course.py` to regenerate everything
(`--no-pdf` for a quick text-only rebuild).
