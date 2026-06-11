# Design spec: grade/course filter control

- **Issue:** [#122 — Design the grade/course filter control](https://github.com/danilchernyshev/study-calc/issues/122)
- **Epic:** [#102 — Global Curriculum Filter](https://github.com/danilchernyshev/study-calc/issues/102)
- **Status:** Ready for implementation
- **Date:** 2026-06-10

---

## 1. Overview and goals

Students using Study Calculator for a specific Ontario course (e.g. SPH4U or
MCR3U) should be able to set their active grade and course once and have the
app surface only the content relevant to them — without hiding the rest
permanently. The filter is a **soft lens**: it hides nothing destructively; it
dims or collapses items that don't carry the matching curriculum tag, and a
single click clears it.

This control lives in two places: a **compact filter bar** in the content
header (always visible, acts immediately) and a **mirrored block** in the
Settings overlay (for users who discover preferences through settings). Both
surfaces read from and write to the same `active_grade` / `active_course`
keys in the settings store, so they stay in sync without a page reload.

---

## 2. Anatomy

### 2a. The two-select control

The control is exactly two `UI.select()` calls rendered side by side — no
custom dropdown is introduced. The existing component handles label, option
list, selected value, and change callback.

```
UI.select({
  label: t("ui.filter.grade"),
  options: gradeOptions,          // [{value:"", label:"All"}, {value:"11", label:"Grade 11"}, ...]
  value: state.activeGrade,       // "" | "11" | "12"
  onchange: onGradeChange,
})

UI.select({
  label: t("ui.filter.course"),
  options: courseOptions,         // [{value:"", label:"All"}, ...codes for active grade]
  value: state.activeCourse,      // "" | "SPH4U" | ...
  onchange: onCourseChange,
  disabled: state.activeGrade === "",   // disabled when grade = All
})
```

The `field__control` element produced by `UI.select()` gains an HTML
`disabled` attribute when grade is "All". Two small reuse-enabling changes
are required (both belong to #123), verified against the current code:

- **`UI.select()` does not yet forward a `disabled` flag** — the factory
  signature is `select({ label, options, value, onchange })`. Add a one-line
  `disabled` passthrough that sets the attribute on the `<select>`. No other
  component change.
- **There is no existing disabled rule for `.field__control`.** A native
  `<select disabled>` is dimmed by the web view by default, but for a
  consistent, token-defined look add one new rule (see section 6). This is a
  *new* rule, not an existing one.

### 2b. Option lists

Grade options are static:

| `value` | Label (resolved) |
| --- | --- |
| `""` | `t("ui.filter.all")` → "All" |
| `"11"` | `t("ui.grade", n=11)` → "Grade 11" |
| `"12"` | `t("ui.grade", n=12)` → "Grade 12" |

Course options are **derived from `CURRICULUM_GRADES`** at render time — never
hardcoded. The bridge passes the full grade→courses mapping in the shell model
(`filterMeta.gradeMap`); the frontend builds the option list from it.

When `active_grade` is "11", the course list is all `CURRICULUM_GRADES` codes
whose value equals 11, sorted alphabetically. When grade is "12", codes whose
value equals 12. Sorted alphabetically so the list is deterministic regardless
of insertion order in `CURRICULUM_GRADES`.

Example with current data (SPH3U added at Grade 11 by milestone #108):

| Grade | Course options (after "All") |
| --- | --- |
| Grade 11 | MCR3U, SPH3U |
| Grade 12 | MCV4U, MDM4U, MHF4U, SCH4U, SPH4U |

### 2c. Dependency rules

```
grade changes to "All"
  → course resets to ""
  → course select is disabled (only option: "All")

grade changes to "11" or "12"
  → course resets to ""  (course = All within that grade)
  → course select is enabled with the grade's codes

course changes to a specific code
  → active badge appears in #header-badge

course resets to ""
  → badge is removed (or reverts to per-screen chip if the screen provides one)
```

Persistence: `active_grade` is stored as an integer (11 or 12) or absent/null;
`active_course` is stored as a string ("SPH4U") or absent/null. When grade
changes, the bridge sets `active_course` to null before saving.

---

## 3. Placement

### Recommended placement: content header filter bar

**Rationale.** The language switcher in the nav footer is the closest existing
precedent for a global control — but it uses plain `<button>` elements on the
dark `--color-bg-nav` surface. `UI.select()` renders a `<select>` styled for
the light surface (`--color-bg-subtle` fill, `--color-border` border). Putting
two selects on the dark nav rail would require a dark-themed component variant
that does not exist and is out of scope for this epic. More importantly, the
curriculum filter is **active-task context** ("what am I studying right now"),
not a persistent application preference like language — it belongs beside the
content, not beside the app settings.

The content header already has the pattern of a "title row + chip slot" (Figma
nodes 23:2 / 29:2). Adding a `header__filter-bar` row between the subtitle
and the tabs makes the filter immediately visible, actionable, and contextually
attached to the content it affects. It does not crowd the nav rail.

### ASCII mockup — content header, default/All state

```
 ┌─────────────────────────────────────────────────────────────────────┐
 │                                                                     │
 │  Physics                                                            │
 │  Mechanics, thermodynamics, electromagnetism and waves              │
 │                                                                     │
 │  Grade: [All              ▾]   Course: [All              ▾]         │
 │          ·disabled-course·                                          │
 │                                                                     │
 │  Mechanics  Thermodynamics  Electromagnetism  Waves                 │
 │  ──────────────────────────────────────────────────────             │
 │                                                                     │
 │  [screen content]                                                   │
 └─────────────────────────────────────────────────────────────────────┘

 Note: "Course" select is visually dimmed (disabled attr) when Grade = All.
```

### ASCII mockup — Settings overlay (mirrored block)

The Settings overlay is opened via the "Updates" button in the nav footer
(the same surface that holds the auto-update-check toggle added in #74). The
filter controls appear as a named section above the updates block.

```
 ┌──────────────────────────────────────────────────────┐
 │  Settings                                    [Close] │
 │                                                      │
 │  CURRICULUM FILTER                                   │
 │  Show only content tagged for your active course.    │
 │  Applies across all subjects.                        │
 │                                                      │
 │  Grade:   [All              ▾]                       │
 │  Course:  [All              ▾]  (dimmed when All)    │
 │                                                      │
 │  ────────────────────────────────────────────────    │
 │                                                      │
 │  SOFTWARE UPDATES                                    │
 │  [ ] Check for updates automatically on startup      │
 │  [Check for updates]                                 │
 └──────────────────────────────────────────────────────┘
```

The Settings overlay renders the selects full-width (stacked), not inline,
since the overlay column is narrower than the header area. Same `UI.select()`
call — only the layout container changes.

---

## 4. States

### State A — default, no filter active (grade = All, course = All)

```
 header__title-row:
 ┌──────────────────────────────────┐
 │  Physics                         │  ← h1.header__title
 │                  #header-badge   │  ← empty (.header__badge-slot:empty → display:none)
 └──────────────────────────────────┘

 header__filter-bar:
 ┌──────────────────────────────────────────────────────────────┐
 │  Grade: [All              ▾]   Course: [All              ▾]  │
 │                                         [opacity: 0.45,      │
 │                                          cursor: not-allowed] │
 └──────────────────────────────────────────────────────────────┘
```

The "Course" select carries `disabled`, visually dimmed via a **new**
`.field__control[disabled] { opacity: 0.45; cursor: not-allowed; }` rule
(#123) — there is no such rule today; native disabled dimming alone is
inconsistent across web views.

### State B — grade chosen, course = All

```
 header__filter-bar:
 ┌──────────────────────────────────────────────────────────────┐
 │  Grade: [Grade 11         ▾]   Course: [All              ▾]  │
 │                                         [enabled, shows      │
 │                                          MCR3U / SPH3U]      │
 └──────────────────────────────────────────────────────────────┘

 #header-badge:  (still empty — no specific course chosen)
```

Content items from both MCR3U and SPH3U are visible (grade-level filter only).
Items with no grade tag are visible too (no tag = universal).

### State C — specific course chosen (active filter badge shown)

```
 header__title-row:
 ┌──────────────────────────────────────────────────────┐
 │  Physics      [SPH4U]                                │
 │               ↑ badge in #header-badge               │
 │               bg: --color-brand-soft                 │
 │               text: --color-brand-primary            │
 │               radius: --radius-pill                  │
 └──────────────────────────────────────────────────────┘

 header__filter-bar:
 ┌──────────────────────────────────────────────────────────────┐
 │  Grade: [Grade 12         ▾]   Course: [SPH4U            ▾]  │
 └──────────────────────────────────────────────────────────────┘
```

The badge in `#header-badge` reads exactly the course code ("SPH4U"). The
badge node is `UI.badge(model.activeCourseBadge)` — the same factory used
today for per-screen curriculum chips. When the global filter is active,
per-screen screens must suppress their own curriculum chip to avoid showing
two badges. The bridge sets `model.activeCourseBadge` in the shell state;
per-screen models check this field and omit their own `curriculumCode` when
the filter is set.

### State D — no results (active filter hides everything on this screen)

Shown in the `screen-mount` area when the filtered content set is empty for
the active screen/item combination.

```
 ┌──────────────────────────────────────────────────────────────────┐
 │                                                                  │
 │                                                                  │
 │     No content matches the current filter.                       │
 │     Try a different course, or clear the filter to see           │
 │     everything.                                                  │
 │                                                                  │
 │     [Clear filter]                                               │
 │                                                                  │
 └──────────────────────────────────────────────────────────────────┘

 Card: bg --color-bg-surface, border --color-border, radius --radius-md,
       shadow --elevation-card.
 Heading text: --color-text-strong, font-size --font-size-md,
               font-weight --font-weight-semibold.
 Detail text: --color-text-muted, font-size --font-size-base.
 "Clear filter" button: UI.button({label, variant:"ghost"}).
   onclick → sets active_grade="" + active_course="" → re-render.
```

The empty state is always a card, never a bare message, so it has the same
visual weight as other screen content.

---

## 5. Responsive / narrow behaviour

Study Calculator is a PyWebView desktop app; the "narrow" scenario is the user
resizing the window. The nav rail is fixed at 235 px; the content area gets
the remainder.

**Wide (content area >= 600 px):** the filter bar renders as a single flex row
— both selects side by side with `gap: --space-md`. Each select has
`min-width: 160px` so the label and current value are readable without
truncation.

**Narrow (content area < 600 px — approx. total window < 835 px):** the
filter bar wraps. Apply `flex-wrap: wrap` on `.header__filter-bar` so the
Course select drops to a second line when the row would overflow. No controls
are hidden; both remain operable.

**Minimum viable (content area < 300 px):** selects go full-width
(`width: 100%` on `.filter-bar__select`). The filter bar takes two full-width
lines. This edge case is unlikely in normal desktop use but must not break.

The Settings overlay selects are always stacked (full-width, one per line)
regardless of window width, since the overlay is a fixed-width panel narrower
than the header area.

---

## 6. Token mapping

Every visual property maps to a token; no raw hex or px literal appears in
the implementation CSS for this control.

| Property | Element | Token CSS var |
| --- | --- | --- |
| Background (filter bar container) | `.header__filter-bar` | transparent (inherits `--color-bg-app`) |
| Padding above filter bar | `.header__filter-bar` | `--space-sm` top |
| Padding below filter bar | `.header__filter-bar` | `--space-md` bottom |
| Gap between the two selects | `.header__filter-bar` | `--space-md` |
| Label text color | `.field__label` | `--color-text-muted` |
| Label font size | `.field__label` | `--font-size-sm` |
| Label font weight | `.field__label` | `--font-weight-medium` |
| Select control background | `.field__control` | `--color-bg-surface` *(existing rule)* |
| Select control border | `.field__control` | `1px solid --color-border-strong` *(existing)* |
| Select control border-radius | `.field__control` | `--radius-sm` *(existing)* |
| Select control text color | `.field__control` | `--color-text-strong` *(existing)* |
| Select control font | `.field__control` | `font: inherit` → `--font-size-base` *(existing)* |
| Select control padding | `.field__control` | `--space-sm --space-md` *(existing)* |
| Select focus | `.field__control:focus` | `border-color --color-brand-primary` + `box-shadow 0 0 0 3px --color-brand-soft` *(existing)* |
| Disabled select opacity | `.field__control[disabled]` | `opacity: 0.45` *(NEW rule, #123)* |
| Disabled cursor | `.field__control[disabled]` | `cursor: not-allowed` *(NEW rule, #123)* |
| Active filter badge background | `.badge` (in `#header-badge`) | `--color-brand-soft` |
| Active filter badge text | `.badge` | `--color-brand-primary` |
| Active filter badge border-radius | `.badge` | `--radius-pill` |
| Active filter badge padding | `.badge` | `--space-3xs` vertical, `--space-sm` horizontal |
| Active filter badge font size | `.badge` | `--font-size-xs` *(existing rule)* |
| Active filter badge font weight | `.badge` | `--font-weight-semibold` *(existing)* |
| Empty-state card background | `.filter-empty` | `--color-bg-surface` |
| Empty-state card border | `.filter-empty` | `1px solid --color-border` |
| Empty-state card border-radius | `.filter-empty` | `--radius-md` |
| Empty-state card shadow | `.filter-empty` | `--elevation-card` |
| Empty-state card padding | `.filter-empty` | `--space-2xl` |
| Empty-state heading color | `.filter-empty__heading` | `--color-text-strong` |
| Empty-state heading size | `.filter-empty__heading` | `--font-size-md` |
| Empty-state heading weight | `.filter-empty__heading` | `--font-weight-semibold` |
| Empty-state detail color | `.filter-empty__detail` | `--color-text-muted` |
| Empty-state detail size | `.filter-empty__detail` | `--font-size-base` |
| Empty-state top margin | `.filter-empty` | `--space-2xl` |
| Settings section heading color | `.settings__section-label` (eyebrow) | `--color-text-muted` |
| Settings section heading size | `.settings__section-label` | `--font-size-eyebrow` |
| Settings section hint color | `.settings__hint` | `--color-text-muted` |
| Settings section hint size | `.settings__hint` | `--font-size-sm` |
| Settings section divider | `<hr>` between sections | `1px solid --color-border` |
| Settings selects gap (stacked) | `.settings__filter-row` | `--space-sm` gap |
| Settings section margin | `.settings__section` | `--space-lg` top |

**Existing tokens consumed without new rules:**
- The `.badge` styling already exists in `components.css` — the active-filter
  badge reuses it unchanged.
- The `UI.button({ variant: "ghost" })` for "Clear filter" reuses the existing
  ghost-button rule.
- The `UI.select()` factory already produces `.field` / `.field__label` /
  `.field__control` — no new component is needed.

---

## 7. i18n keys

All five locales (`en`, `es`, `fr`, `ru`, `uk`) must carry every key listed
below. Course codes (SPH3U, SPH4U, MCR3U, etc.) are proper nouns and are
never translated; they appear verbatim as option labels.

Note: `ui.grade` (`"Grade {n}"`) already exists in all locales and is reused
for the Grade dropdown option labels (`t("ui.grade", n=11)` → "Grade 11").
The keys below are new additions only.

| Key | English source text |
| --- | --- |
| `ui.filter.grade` | Grade |
| `ui.filter.course` | Course |
| `ui.filter.all` | All |
| `ui.filter.badge_aria` | Active filter: {code} |
| `ui.filter.clear` | Clear filter |
| `ui.filter.no_results` | No content matches the current filter. |
| `ui.filter.no_results_detail` | Try a different course, or clear the filter to see everything. |
| `ui.filter.settings_heading` | Curriculum filter |
| `ui.filter.settings_hint` | Show only content tagged for your active course. Applies across all subjects. |

**Usage notes:**

- `ui.filter.grade` and `ui.filter.course` are the `label` arguments passed
  to the two `UI.select()` calls.
- `ui.filter.all` is the first `{value: "", label: ...}` option in both
  dropdowns.
- `ui.filter.badge_aria` is the `aria-label` attribute on the badge element
  (screen-reader text); the visible text is just the code string.
- `ui.filter.clear` is the `label` of the ghost button in the empty state.
- `ui.filter.no_results` and `ui.filter.no_results_detail` are the heading
  and detail text of the empty-state card.
- `ui.filter.settings_heading` is rendered as an eyebrow label (uppercase,
  `--font-size-eyebrow`, `--color-text-muted`) above the filter selects in
  the Settings overlay.
- `ui.filter.settings_hint` is the hint paragraph below the heading.

---

## 8. State model and hand-off notes

### 8a. Settings store keys

Two new keys join `core/settings.py`'s `DEFAULTS` dict (issue #124):

```python
DEFAULTS = {
    "auto_update_check": True,
    "active_grade": None,    # int (11 | 12) or None
    "active_course": None,   # str ("SPH4U" etc.) or None
}
```

Invariant enforced on load: if `active_grade` is None then `active_course`
must also be treated as None (a dangling course key without a grade is
discarded on read). If `active_course` is not in the set of codes for
`active_grade` it is also discarded on read (prevents stale data after
`CURRICULUM_GRADES` changes).

### 8b. Shell model additions (issue #126)

The bridge's `get_state()` return value gains two new top-level fields and
one metadata block:

```python
{
    ...,
    "activeGrade": settings.active_grade,     # int | None
    "activeCourse": settings.active_course,   # str | None
    "filterMeta": {
        "gradeMap": {                          # derived from CURRICULUM_GRADES
            11: ["MCR3U", "SPH3U"],            # sorted alphabetically
            12: ["MCV4U", "MDM4U", "MHF4U", "SCH4U", "SPH4U"],
        }
    },
}
```

The frontend builds the select option lists entirely from `filterMeta.gradeMap`
and never hardcodes course codes. The backend computes `gradeMap` by inverting
`CURRICULUM_GRADES` and sorting each bucket. Returning `activeCourseBadge`
as a convenience field (the course code string or null) avoids repeating the
null-check logic in the frontend:

```python
"activeCourseBadge": settings.active_course or None,
```

### 8c. New bridge methods (issue #125)

```python
def set_active_grade(self, grade: int | None) -> dict:
    """Persist grade; reset course to None; return refreshed shell state."""

def set_active_course(self, course: str | None) -> dict:
    """Persist course (grade must already be set); return refreshed shell state."""
```

Both methods save to the settings store, then return `self.get_state()` so
the frontend re-renders the full shell (header filter bar + badge + nav)
without a page reload. The pattern is identical to `set_language()`.

### 8d. Frontend wiring (issue #123)

`renderContent()` in `shell.js` grows a `renderFilterBar(data)` helper that
inserts `.header__filter-bar` between the subtitle `<p>` and the `.tabs` div.
The filter bar calls `UI.select()` twice, passing `data.activeGrade` and
`data.activeCourse` as selected values and `data.filterMeta.gradeMap` to
build the option lists.

`onGradeChange(value)` → calls `set_active_grade(value === "" ? null :
parseInt(value))` → on resolve, sets `state.data = result` and calls
`render()`.

`onCourseChange(value)` → calls `set_active_course(value === "" ? null :
value)` → on resolve, sets `state.data = result` and calls `render()`.

The `#header-badge` logic in `mountScreen()` gains a guard: if
`data.activeCourse` is set, the badge is populated from `data.activeCourseBadge`
(the global filter takes precedence) and per-screen curriculum chips are
suppressed for that render pass.

The empty-state card is rendered by `mountScreen()` when a screen's filtered
item list is empty. The "Clear filter" button calls
`set_active_grade(null)` to clear both grade and course in one round-trip.

### 8e. Acceptance criteria checklist

| Criterion | Covered by |
| --- | --- |
| Grade dropdown ("All", "Grade 11", "Grade 12") | Section 2b, Section 3 mockups |
| Dependent course dropdown (narrows to grade's courses) | Section 2b, Section 2c |
| Grade = All resets course = All and disables course select | Section 2c, State A mockup |
| Choosing a grade repopulates course list from CURRICULUM_GRADES | Section 2b, Section 8b |
| Placement in shell header | Section 3, State mockups A–C |
| Mirrored controls in Settings | Section 3 Settings mockup |
| Responsive / narrow behaviour | Section 5 |
| Active filter signalled via badge in #header-badge | Section 4 State C |
| No-results / empty state with "Clear filter" | Section 4 State D |
| Reuse UI.select() — no new custom dropdown | Section 2a, Section 6 |
| All values cite design tokens — no hardcoded colors/sizes | Section 6 (full table) |
| New i18n keys listed with English source text | Section 7 |
| settings keys active_grade / active_course named for #124 | Section 8a |
| Value flow: store → bridge → header + Settings | Section 8b, 8c, 8d |

### 8f. Implementation issue map

| Issue | Scope |
| --- | --- |
| **#123** | JS: `renderFilterBar()`, `onGradeChange()`, `onCourseChange()`, empty-state card; CSS: `.header__filter-bar`, `.filter-empty`; `shell.js` badge guard |
| **#124** | Python: add `active_grade` / `active_course` to `Settings.DEFAULTS` + typed properties + `set_active_grade()` / `set_active_course()` helpers on `Settings` |
| **#125** | Python: `bridge.Bridge.set_active_grade()` / `set_active_course()` methods; extend `get_state()` with `activeGrade`, `activeCourse`, `activeCourseBadge`, `filterMeta` |
| **#126** | Python: `screens.py` per-screen models suppress their `curriculumCode` when `active_course` is set; `problems_screen` and formula screens return empty-state model when filter produces no visible items |

---

## 9. Figma + code verification

This spec was cross-checked against the redesign Figma file
([1RKI6SYs0PJ5EEA0JQzLf7](https://www.figma.com/design/1RKI6SYs0PJ5EEA0JQzLf7/study-calc-%E2%80%94-Redesign),
frame `3:2` "Main") and the live `components.css` rules, per the
visual-check discipline for "matches Figma" work.

**Confirmed against the Figma frame:**

- The content header already renders **title + subtitle + a soft-blue
  curriculum pill** (`MCV4U · MHF4U`, node `3:9`) in the `#header-badge`
  slot — exactly the slot and pill style this spec reuses for the
  active-filter badge. The two-badge coordination guard in §4 State C / §8d
  is therefore a real concern (the slot is already occupied by course codes).
- The header's tab row (node `3:10`, "Symbolic math (CAS) / Vectors /
  Problems") sits directly below the subtitle — the filter bar inserts
  cleanly between them (§3).
- The language switcher (`🌐 Language · EN ▾`, node `2:30`) lives in the
  **dark** nav footer and uses plain buttons, confirming the rationale for
  keeping `UI.select()` controls on the light content surface instead (§3).
- The `UI.select()` control ("Operation ▾"), green result chip, and ghost
  "Clear" button all appear on the frame, matching the components this spec
  reuses (§2, §4 State D).

**Corrected after reading `components.css` (the design-token source of truth
won over assumed values):**

- The `.field__control` token rows in §6 now match the real rule: background
  `--color-bg-surface`, border `--color-border-strong`, text
  `--color-text-strong`, padding `--space-sm --space-md`, and a
  `box-shadow` focus ring (not an `outline`). The select is **reused
  unchanged**, not re-styled.
- The active-filter `.badge` uses `--font-size-xs` (corrected from `sm`).
- `UI.select()` has **no `disabled` passthrough today** and there is **no
  existing disabled `.field__control` rule** — both are flagged in §2a / §6
  as small additive changes scoped to #123, rather than assumed pre-existing.
