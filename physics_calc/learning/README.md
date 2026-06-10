# Learning materials

Prose study content for the calculator's right-hand learning panel, kept here —
deliberately **separate from code** — so its depth, wording and presentation can be
reshaped without touching the application. The loader is
`physics_calc/core/learning.py`; the GUI renders it in `ExplanationPanel`.

All content is **original**, written from the openly-licensed
[OpenStax *College Physics*](https://openstax.org/books/college-physics) text and
general knowledge. The paid video solutions on CollegePhysicsAnswers are linked as
external references only (see `physics_calc/domains/references.py`) — never copied.

## Layout

```
learning/
  <lang>/
    glossary/<term_id>.json   reusable term definitions
    topics/<topic_id>.json    one bundle per problem type
```

`en` is the canonical language and the fallback. A file missing in another language
is served from `en`, so partial translations never blank the panel. Add a language by
creating `learning/<code>/...` files mirroring the English ones — purely additive.

## `topics/<topic_id>.json`

`topic_id` is a physics formula `key` (e.g. `newton_2`) or a CAS operation
(`cas_factor`, `cas_derivative`, …). The panel looks the topic up by that id, so a
problem detected from user input gets its materials automatically.

```json
{
  "summary": "Short overview of this kind of problem.",
  "terms": ["force", "mass", "acceleration"],
  "formulas": ["F = m·a", "a = F/m"],
  "method": ["Step one…", "Step two…"],
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
(`tests/test_learning.py` enforces this). Every field is optional — omit `example`
or `method` and the panel simply skips that section.

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
explanation" window. `see_also` ids become further links inside that window.
