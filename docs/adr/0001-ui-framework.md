# 1. UI framework for the redesign

- **Status:** Accepted
- **Date:** 2026-06-10
- **Deciders:** study-calc maintainers
- **Issue:** [#2 — Spike: choose the UI framework for the redesign](https://github.com/danilchernyshev/study-calc/issues/2)
- **Milestone:** #1 — Improve UI/UX and update design

## Context

The current GUI is a single Tkinter module (`study_calc/gui/app.py`, ~1300
lines) built on a `ttk.Notebook`. It is rebuilt wholesale on every language
change and offers the plain default `ttk` look.

The redesign (Figma file `1RKI6SYs0PJ5EEA0JQzLf7`) is a **modern flat,
card-based** concept: a dark left **navigation rail**, rounded **cards** with
**drop shadows**, a custom type scale, chips, an indigo/slate token palette
(`study-calc/color`, 21 color variables derived from the app's existing accent
colors), and a header with inner tabs. All core screens are already laid out in
Figma (CAS, Physics formula, Vectors, Converter, Periodic table, Problems
trainer).

Crucially, the **domain layer is already UI-agnostic**:

- `core/` (formula solver, units converter, `cas`, `vectors`, `periodic`,
  `explain`, `learning`) returns plain data and stable machine error `code`s,
  never display strings.
- `domains/` are declarative `Formula` sets; `navigation.py` (`SUBJECTS`) is the
  single, Tkinter-free source of truth for the tab tree.
- i18n is flat `{key: text}` JSON catalogs in `study_calc/locales/` with English
  fallback — directly consumable by *any* front end, including JavaScript.

So the question is **not** whether the logic can move — it can sit unchanged
under any UI — but which presentation toolkit best renders this specific
flat/card design while keeping the project easy to package, develop, and test.

## Decision drivers

The criteria from issue #2, weighted for a small open-source educational
desktop app distributed to students:

1. **Design fidelity** — rounded cards, drop shadows, custom fonts, dark nav
   rail, chips, a token-driven palette. This is the dominant driver: the whole
   milestone exists to land this look.
2. **Reuse of `core`/`domains`/`navigation`/i18n** — none of this should be
   rewritten.
3. **Dev effort** — small maintainer team; the design is already done in Figma.
4. **Packaging / distribution** — a Windows installer already ships
   (`INSTALL_WINDOWS.txt`, `Install.bat`); macOS/Linux should stay viable.
5. **Testability** — `core`/i18n are covered headlessly by `pytest` today; the
   GUI is not tested at all. We want to *keep* the headless core tests and gain
   a realistic way to test the UI.

## Options considered

### (a) Restyle in place on Tkinter / ttk

- **Fidelity — poor.** `ttk` styling is the toolkit's weakest area. Flat fills
  and custom fonts are achievable, but **rounded corners, drop shadows, and the
  card aesthetic require Canvas image hacks or pre-rendered bitmaps** — you end
  up fighting the toolkit and re-faking what CSS gives for free. The result
  would approximate, not match, the Figma.
- **Reuse — total** (it is the status quo).
- **Dev effort — deceptively high.** Cheap to recolor, expensive to fake the
  modern look convincingly and keep it maintainable.
- **Packaging — best.** Already works; stdlib-based (though Tkinter is a
  separate system package on some Linux distros).
- **Testability — poor.** Tkinter is hard to drive headlessly; today's tests
  deliberately avoid the GUI.

### (b) Web frontend — local HTML/CSS/JS

Two shapes were considered:

- **PyWebView** — a native OS window hosting a webview (Edge WebView2 on
  Windows, WebKit on macOS, WebKitGTK on Linux), with the Python `core` exposed
  to JavaScript through a small `js_api` **bridge**. One Python process, no
  bundled browser.
- **Local API + SPA** — a small FastAPI/Flask process serving a JS/TS SPA,
  opened in the browser or a webview.

- **Fidelity — excellent.** Cards, shadows, custom fonts, the nav rail, chips,
  and the token palette are exactly what HTML/CSS is built for. The Figma's
  `study-calc/color` variables map **1:1 onto CSS custom properties**, so the
  design can be reproduced faithfully and the tokens stay the single source of
  truth.
- **Reuse — high.** `core`/`domains`/`navigation` are reused unchanged behind a
  thin bridge; the i18n JSON catalogs are **consumed directly by the frontend**
  (same key discipline, same English fallback) — no translation layer to
  rebuild.
- **Dev effort — moderate.** A frontend must be built, but the design already
  exists with tokens, so it is translation, not invention. The bridge surface is
  small (solve / convert / CAS analyze / vectors / periodic / problems +
  learning lookups).
- **Packaging — good (PyWebView) / heavier (API+SPA).** PyWebView ships **no
  Chromium**: it uses the OS webview (WebView2 is preinstalled on Windows 11 and
  current Windows 10; a one-time runtime install otherwise), keeping bundles
  small and PyInstaller-friendly. A separate API+SPA means two processes, port
  management, and a JS build step — more moving parts than a desktop study tool
  warrants.
- **Testability — best of the field.** `core` stays on `pytest`; the UI is
  drivable end-to-end with **Playwright** (already available in this
  workspace); the bridge is unit-testable in Python.

### (c) PyQt / PySide6

- **Fidelity — very good.** Qt Style Sheets (QSS) do rounded corners and custom
  fonts; shadows via `QGraphicsDropShadowEffect`; the nav rail is
  straightforward. Slightly more effort than CSS but close.
- **Reuse — high** for `core`; the GUI is a **full rewrite** in Qt's
  widget/signal-slot model.
- **Dev effort — high.** New widget model and a real learning curve, with no
  head start from the existing Tkinter code.
- **Packaging — heavy.** PySide6 is large (hundreds of MB of Qt libraries);
  bundles are big. (Licensing is fine: PySide6 is LGPL; plain PyQt would be
  GPL/commercial.)
- **Testability — moderate.** `pytest-qt` exists and beats Tkinter, but it is
  still GUI-bound.

### (d) Toga (BeeWare)

- **Fidelity — poor-to-moderate.** Toga renders **native** widgets with a
  limited `Pack`/style model — no rich CSS, weak support for rounded cards and
  shadows. The flat/card design fights the toolkit, and the styling layer is
  still immature.
- **Reuse — high** for `core`; GUI rewritten.
- **Dev effort — moderate**, but spent fighting styling limits.
- **Packaging — good** via Briefcase (native installers, even mobile).
- **Testability — limited.**

## Decision

**Adopt a web frontend rendered via PyWebView**: a native desktop window hosting
local HTML/CSS/JS, with the existing Python `core`/`domains`/`navigation`
exposed through a thin `js_api` bridge and the i18n JSON catalogs consumed
directly by the frontend.

### Why

- It is the **only option that reproduces the Figma design faithfully without
  fighting the toolkit** — the design is literally a flat, CSS-shaped layout, and
  its color tokens drop straight into CSS custom properties.
- It **reuses the entire decoupled stack** (`core`/`domains`/`navigation` behind
  a small bridge; i18n JSON read as-is) — the thing the architecture was built
  for.
- It keeps **packaging sane** (no bundled browser; one Python process; existing
  PyInstaller/Windows-installer path adapts) and makes the **UI genuinely
  testable** with Playwright while the headless `core`/i18n `pytest` suite stays
  exactly as it is.
- PyQt/PySide and Toga both require a full GUI rewrite for *worse* (Toga) or
  *comparable-at-higher-cost* (Qt, with much heavier bundles) fidelity; staying
  on Tkinter cannot reach the target look without unmaintainable Canvas hacks.

### Migration strategy — **incremental, parallel front end**

Not a big-bang rewrite. The Tkinter app keeps running while the web UI is built
under a **new, separate entry point**, screen by screen, until parity is
reached; only then is Tkinter retired.

1. **Bridge + tokens first.** Add a `study_calc/web/` package: a PyWebView
   bootstrap, a `bridge.py` exposing `core`/`navigation` operations to JS, and a
   loader that serves the i18n catalogs. Export the Figma `study-calc/color`
   tokens (plus type scale and spacing) as CSS custom properties — the work of
   issue #3.
2. **App shell** (#4): nav rail + header in HTML/CSS, driven by
   `navigation.SUBJECTS` via the bridge so the tab tree stays single-sourced.
3. **Shared components** (#5): cards, chips, buttons, inputs, the rich-text /
   explanation panel — as reusable HTML/CSS/JS components bound to design tokens.
4. **Screens** (#6–#11), one PR each, each view talking to the bridge and
   reading i18n keys: Physics formula, CAS, Vectors, Converter, Periodic table,
   Problems.
5. **Cut over** once every screen reaches parity; remove the Tkinter GUI in a
   final PR.

`core`, `domains`, `navigation`, and the i18n contract are **reused verbatim** —
the migration adds a presentation layer, it does not touch the engine.

## Consequences

**Positive**

- Faithful, maintainable rendering of the redesign; tokens stay single-sourced.
- The UI-agnostic architecture pays off — zero engine rewrite.
- Real UI test coverage via Playwright, on top of the unchanged headless suite.
- Small, browser-free desktop bundles.

**Negative / risks**

- A new frontend skill set (HTML/CSS/JS) and a JS↔Python bridge to design and
  test.
- **WebView2 runtime dependency on Windows** — preinstalled on Windows 11 and
  current Windows 10, but older targets may need a one-time runtime install; the
  Windows installer must account for this.
- A new front-end toolchain choice (vanilla vs. a light framework such as
  Preact/Svelte) — to be decided in #5; keep it minimal.
- During migration two GUIs coexist briefly (extra surface to keep building),
  the standard cost of an incremental cutover.

**Neutral**

- `uv run --extra dev pytest` is unaffected by this decision (no code changed by
  the ADR itself); new dependencies (`pywebview`, a Playwright dev extra) arrive
  with #3/#4, not here.

## Constraints imposed on downstream issues

- **#3 (design tokens):** deliver the `study-calc/color` palette + type scale +
  spacing as **CSS custom properties** (`:root` variables), the single source of
  truth the components consume.
- **#4 (app shell):** the nav rail + header are the **PyWebView host window**;
  the tab tree is driven by `navigation.SUBJECTS` through the bridge, not
  hardcoded.
- **#5 (shared components):** implement cards/controls/rich-text as
  **HTML/CSS/JS** components bound to the #3 tokens; this issue also settles the
  vanilla-vs-light-framework choice.
- **#6–#11 (per-screen):** each screen is an **HTML view talking to the Python
  `bridge`**, reusing the matching `core` function and reading **i18n keys** (no
  display strings in the bridge); error `code`s are resolved client-side via the
  catalogs, exactly as the Tkinter app resolves them today.
