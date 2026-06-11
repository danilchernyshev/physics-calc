# Learning materials

Prose study content for the calculator's right-hand learning panel. The JSON
files in this folder are the **authoring source of truth**; at runtime the app
serves the same content from the SQLite knowledgebase
(`study_calc/data/knowledgebase.db`), which is **seeded from these files** by
`scripts/seed_db.py`. The loader is `study_calc/core/learning.py` (it reads the
DB through `study_calc/core/db.py`); the web frontend renders what it returns.

> **Edit JSON, then re-seed.** Editing a JSON file alone changes nothing the app
> sees — the committed `knowledgebase.db` is what ships and what the loaders
> read. After any content change run `python scripts/seed_db.py` and commit the
> regenerated DB. `tests/test_db_in_sync.py` fails if the committed DB drifts
> from the JSON sources. See `docs/content-authoring.md` for the full workflow.

All content is **original**, written from the openly-licensed
[OpenStax *College Physics*](https://openstax.org/books/college-physics) and
[*Chemistry*](https://openstax.org/books/chemistry-2e) texts and general
knowledge. The paid video solutions on CollegePhysicsAnswers are linked as
external references only (see `study_calc/domains/references.py` and a problem's
`video_url`) — never copied.

## Layout

```
learning/
  <lang>/
    glossary/<term_id>.json   reusable term (concept) definitions
    topics/<topic_id>.json    one bundle per problem type
    problems/<problem_id>.json a single practice problem
```

`en` is the canonical language and the fallback. A file missing in another
language is served from `en`, so partial translations never blank the panel. Add
a language by creating `learning/<code>/...` files mirroring the English ones —
purely additive.

### Stable-key contract

A file's **stem is its stable id** (`topic_id` / `term_id` / `problem_id`) and is
the primary key in the DB. Existing ids **must never be renamed** — other content
references them (`problems[].topic`, `topics[].terms`, `glossary[].see_also`) and
so do the physics formula keys and CAS op names. Rename = broken links. To
replace content, edit the file in place; only ever *add* new ids.

## `topics/<topic_id>.json`

`topic_id` is a physics formula `key` (e.g. `newton_2`), a CAS operation
(`cas_factor`, `cas_derivative`, …), or a subject-prefixed id (`chem_*`, `mdm_*`,
`sph_*`). The panel looks the topic up by that id, so a problem detected from user
input gets its materials automatically.

```json
{
  "summary": "Short overview of this kind of problem.",
  "terms": ["force", "mass", "acceleration"],
  "formulas": ["F = m·a", "a = F/m"],
  "method": ["Step one…", "Step two…"],
  "courses": ["SPH4U"],
  "example": {
    "title": "Find the force on a cart",
    "given": ["m = 5 kg", "a = 2 m/s²"],
    "find": "the net force F",
    "steps": ["Apply F = m·a.", "Substitute: F = 5 · 2."],
    "answer": "F = 10 N"
  }
}
```

`terms` are glossary ids; each must have a matching `glossary/<id>.json`
(`tests/test_learning.py` enforces this). `courses` are Ontario course codes
(`SPH4U`, `MHF4U`, …) rendered as a grade badge. Every field is optional — omit
`example` or `method` and the panel simply skips that section.

## `glossary/<term_id>.json`

```json
{
  "title": "Momentum",
  "short": "One or two sentences shown inline in the panel.",
  "full": "The longer explanation shown in the pop-up window.\n\nMay use blank lines as paragraph breaks.",
  "formulas": ["p = m·v"],
  "see_also": ["velocity", "impulse"]
}
```

`short` feeds the inline blurb next to the term; `full` feeds the "Open full
explanation" window. `see_also` ids become further links inside that window and
must each resolve to another glossary file (`tests/test_learning.py` enforces it).

## `problems/<problem_id>.json`

A single practice problem for the Problems surface. It is a tagged worked example
plus a subject, optional backing topic and video.

```json
{
  "subject": "physics",
  "courses": ["SPH4U"],
  "title": "Net force on an accelerating car",
  "given": ["mass m = 1200 kg", "acceleration a = 2.5 m/s²"],
  "find": "the net force F on the car",
  "steps": ["Use Newton's second law: F = m·a.", "Substitute and multiply."],
  "answer": "F = 3000 N",
  "video_url": "https://collegephysicsanswers.com/chapter-4-...",
  "topic": "newton_2"
}
```

`subject` is one of the `navigation.SUBJECTS` ids (`physics`, `math`, `tools`,
`chemistry`) and drives the subject filter. `topic` (optional) must match an
existing `topics/<id>.json` so the related-topic blocks resolve
(`tests/test_db_seed.py::TestForeignKeys` guards this). `video_url` (optional) is
an external link only. A `difficulty` column also exists on the `problems` table
but is **not authored here yet** — it defaults to `""` and is populated by a later
milestone (M3-1); leave it out of the JSON for now.
