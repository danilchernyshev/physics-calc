// App shell: nav rail + header, rendered from the bridge's state (issue #4).
// Vanilla JS (the framework choice settled in #5); `h()` comes from dom.js.
// Selection (which subject/item is active) lives here, so a language switch only
// refreshes labels and the current screen is preserved.

'use strict';

// `h()` (hyperscript helper) and `UI` (components) come from dom.js / components.js,
// loaded before this script.

const state = {
  data: null, subject: 0, item: 0, langOpen: false,
  // Software updates (#74): a non-blocking startup check may flag a newer
  // release; the result is cached so opening the overlay shows it immediately.
  updateAvailable: false, updateResult: null,
};

// Tool items that render the shared operations screen → their bridge methods.
const OP_TOOLS = {
  'tool:cas': { screen: 'cas_screen', run: 'cas_run' },
  'tool:vectors': { screen: 'vector_screen', run: 'vector_run' },
};

// The bridge calls the updates overlay drives (#74 check / #75 guide / #94 apply).
// setGrade / setCourse are also exposed so the Settings overlay can mirror the
// header filter controls (epic #102, issue #123): they persist via the two-method
// API, re-render the shell, and return the fresh filter descriptor to the overlay
// so its course list updates in-place without closing and re-opening the dialog.
const updatesApi = {
  check: () => callApi('check_updates'),
  setAuto: (enabled) => callApi('set_auto_update_check', enabled),
  applyUpdate: (version) => callApi('apply_update', version),
  setGrade: async (grade) => {
    const newState = await callApi('set_active_grade', grade);
    if (newState) { state.data = newState; render(); }
    return newState ? newState.filter : null;
  },
  setCourse: async (course) => {
    const newState = await callApi('set_active_course', course);
    if (newState) { state.data = newState; render(); }
    return newState ? newState.filter : null;
  },
};

async function loadState() {
  if (window.__STUDY_CALC_STATE__) return window.__STUDY_CALC_STATE__;
  return window.pywebview.api.get_state();
}

// Call a bridge method, with a static fallback for the browser/screenshot
// preview (which injects `__STUDY_CALC_API__` instead of a live PyWebView API).
async function callApi(method, ...args) {
  const api = window.pywebview && window.pywebview.api;
  if (api && typeof api[method] === 'function') return api[method](...args);
  const preview = window.__STUDY_CALC_API__;
  if (preview && typeof preview[method] === 'function') return preview[method](...args);
  return null;
}

// --- Curriculum filter (epic #102, issue #123) ------------------------------
// Two async helpers keep the pattern uniform: call the bridge, store the fresh
// state, and re-render so the nav and the header controls both reflect the new
// selection. `render()` clamps state.subject/item to valid indices, so calling
// these from anywhere is safe even when the filter shrinks the subject list.

async function setActiveGrade(grade) {
  const newState = await callApi('set_active_grade', grade);
  if (newState) { state.data = newState; render(); }
}

async function setActiveCourse(course) {
  const newState = await callApi('set_active_course', course);
  if (newState) { state.data = newState; render(); }
}

// Build the grade + course select row that sits in the content header (shown on
// every screen, below the page title). Returns null when the model has no filter
// descriptor (preview / first load before bridge responds).
function renderFilterControls(data) {
  const filter = data.filter;
  if (!filter) return null;
  const labels = filter.labels;

  // Grade options: "all" maps to the translated label; each numeric grade
  // becomes e.g. "Grade 11" by combining labels.grade with the level number.
  const gradeOptions = filter.grades.map((g) => ({
    value: g,
    label: g === 'all' ? labels.all : `${labels.grade} ${g}`,
  }));

  // Course options are restricted to the grade currently selected; when grade
  // is "all" the course select only shows "All" (forced to all).
  const courseOptions = [{ value: 'all', label: labels.all }];
  if (filter.activeGrade !== 'all') {
    const courses = filter.gradeMap[filter.activeGrade] || [];
    courses.forEach((c) => courseOptions.push({ value: c, label: c }));
  }

  const gradeSelect = UI.select({
    label: labels.grade,
    options: gradeOptions,
    value: filter.activeGrade,
    onchange: (value) => setActiveGrade(value),
  });
  const courseSelect = UI.select({
    label: labels.course,
    options: courseOptions,
    value: filter.activeCourse,
    onchange: (value) => setActiveCourse(value),
  });
  // "Clear filter" affordance — only shown when a grade (and possibly a course)
  // is active; grade="all" means filter is off.
  const clearBtn = filter.activeGrade !== 'all'
    ? h('button', {
        class: 'filter__clear',
        type: 'button',
        'aria-label': labels.clear,
        onclick: () => setActiveGrade('all'),
      }, [labels.clear])
    : null;

  return h('div', { class: 'header__filter-row' }, [gradeSelect, courseSelect, clearBtn]);
}

// Render the "no content matches this filter" empty state that replaces the
// normal content area when the filtered nav is completely empty.
function renderNoResults(data) {
  const filter = data.filter || {};
  const labels = filter.labels || {};
  return h('main', { class: 'content' }, [
    renderFilterControls(data),
    h('div', { class: 'filter-empty' }, [
      h('p', { class: 'filter-empty__title', text: labels.noResults || '' }),
      h('p', { class: 'filter-empty__detail', text: labels.noResultsDetail || '' }),
    ]),
  ]);
}

async function setLanguage(code) {
  state.langOpen = false;
  if (window.pywebview && window.pywebview.api) {
    state.data = await window.pywebview.api.set_language(code);
  }
  render();
}

function selectSubject(index) {
  if (index === state.subject) return;
  state.subject = index;
  state.item = 0;
  render();
}

function selectItem(index) {
  state.item = index;
  render();
}

function renderNav(data) {
  const items = data.subjects.map((subject, index) =>
    h('button', {
      class: 'nav__item' + (index === state.subject ? ' nav__item--active' : ''),
      onclick: () => selectSubject(index),
    }, [
      h('span', { class: 'nav__badge', text: subject.monogram }),
      h('span', { text: subject.label }),
    ]));

  const langMenu = state.langOpen
    ? h('div', { class: 'nav__lang-menu' }, data.languages.map((lang) =>
        h('button', {
          class: 'nav__lang-option' + (lang.code === data.lang ? ' is-active' : ''),
          onclick: () => setLanguage(lang.code),
        }, [lang.label])))
    : null;

  return h('nav', {
    // Name the nav rail region for assistive tech (issue #26); <nav> already
    // carries an implicit role="navigation".
    class: 'nav',
    'aria-label': data.labels.subjectsHeading,
  }, [
    h('div', { class: 'nav__logo' }, [
      h('span', { class: 'nav__logo-badge', text: 'Σ' }), // Σ
      h('span', { class: 'nav__wordmark', text: data.labels.appTitle }),
    ]),
    h('p', { class: 'nav__heading', text: data.labels.subjectsHeading }),
    h('div', { class: 'nav__items' }, items),
    h('div', { class: 'nav__spacer' }),
    h('div', { class: 'nav__footer' }, [
      h('button', {
        class: 'nav__foot-link',
        id: 'guide-btn',
        onclick: async () => {
          const model = await callApi('guide_screen');
          if (model) Screens.openGuide(model);
        },
      }, ['ⓘ ' + data.labels.howToUse]), // ⓘ
      h('button', {
        // A subtle dot marks the button when a startup check found a newer
        // release; clicking opens the (already-fetched) details, else an idle
        // panel with a manual "Check for updates" action.
        class: 'nav__foot-link' + (state.updateAvailable ? ' nav__foot-link--alert' : ''),
        id: 'updates-btn',
        onclick: async () => {
          const model = state.updateResult || await callApi('update_screen');
          if (model) Screens.openUpdates(model, updatesApi);
        },
      }, ['⬆ ' + data.labels.updates]), // ⬆
      langMenu,
      h('button', {
        class: 'nav__foot-link',
        // Expose the language menu's open/closed state to assistive tech (#26).
        'aria-haspopup': 'true',
        'aria-expanded': state.langOpen ? 'true' : 'false',
        onclick: () => { state.langOpen = !state.langOpen; render(); },
      }, ['🌐 ' + data.labels.language + ' · '
          + data.lang.toUpperCase() + ' ▾']), // 🌐 … ▾
    ]),
  ]);
}

function renderContent(data, subject) {
  const tabs = h('div', { class: 'tabs' }, subject.items.map((item, index) =>
    h('button', {
      class: 'tab' + (index === state.item ? ' tab--active' : ''),
      onclick: () => selectItem(index),
    }, [item.label])));

  // The per-screen content is mounted asynchronously (it may need a bridge call).
  const screenMount = h('div', { class: 'screen-mount', id: 'screen-mount' }, []);

  // The title row carries an empty curriculum-chip slot (#header-badge) that
  // per-screen renderers may fill — e.g. the periodic table sets "SCH4U" beside
  // the "Chemistry" title (Figma node 23:2). It is recreated empty on every
  // render(), so non-curriculum screens simply leave it blank.
  // The filter row (#123) sits between the title and the subtitle so the selects
  // are always in view without scrolling, regardless of which screen is active.
  return h('main', { class: 'content' }, [
    h('div', { class: 'header__title-row' }, [
      h('h1', { class: 'header__title', text: subject.label }),
      h('span', { class: 'header__badge-slot', id: 'header-badge' }, []),
    ]),
    renderFilterControls(data),
    h('p', { class: 'header__subtitle', id: 'header-subtitle', text: subject.tagline }),
    tabs,
    screenMount,
  ]);
}

function placeholderNode(data, subject) {
  const active = subject.items[state.item];
  return h('div', { class: 'placeholder' }, [
    h('p', { class: 'placeholder__title', text: active ? active.label : subject.label }),
    h('p', { class: 'placeholder__note', text: data.labels.placeholder }),
  ]);
}

// Fill the content area for the active item. Section items render the physics
// formula screen (issue #6); tools and the problems surface (#7–#11) each have
// their own renderer; anything still without one falls back to the placeholder.
async function mountScreen() {
  const mount = document.getElementById('screen-mount');
  if (!mount) return;
  const data = state.data;
  const subject = data.subjects[state.subject];
  const item = subject.items[state.item];
  if (item && item.kind === 'section') {
    const model = await callApi('formula_screen', item.id);
    // Ignore a stale response if the selection changed while we awaited.
    if (document.getElementById('screen-mount') !== mount) return;
    if (model) {
      mount.replaceChildren(Screens.formula(model, {
        solve: (key, values) => callApi('solve_formula', key, values),
      }));
      return;
    }
  }
  // Operation tools (CAS, vectors) share one screen renderer; each names its
  // bridge screen + run methods.
  const opTool = item && item.kind === 'tool' && OP_TOOLS[item.id];
  if (opTool) {
    const model = await callApi(opTool.screen);
    if (document.getElementById('screen-mount') !== mount) return;
    if (model) {
      mount.replaceChildren(Screens.operations(model, {
        run: (op, values) => callApi(opTool.run, op, values),
      }));
      return;
    }
  }
  // The unit converter has its own dedicated renderer (issue #9): it is
  // category+units shaped, not operation+fields shaped like CAS/vectors.
  if (item && item.kind === 'tool' && item.id === 'tool:converter') {
    const model = await callApi('converter_screen');
    if (document.getElementById('screen-mount') !== mount) return;
    if (model) {
      mount.replaceChildren(Screens.converter(model, {
        run: (category, value, fromUnit, toUnit) =>
          callApi('convert_run', category, value, fromUnit, toUnit),
      }));
      return;
    }
  }
  // The periodic-table tool has its own dedicated renderer (issue #10): a
  // 118-element CSS grid coloured by series tokens, with molar-mass and
  // equation-balancer tools. core.periodic is always importable (no fallback).
  if (item && item.kind === 'tool' && item.id === 'tool:periodic_table') {
    const model = await callApi('periodic_screen');
    if (document.getElementById('screen-mount') !== mount) return;
    if (model) {
      mount.replaceChildren(Screens.periodic(model, {
        molarMass: (formula) => callApi('molar_mass_run', formula),
        balance: (equation) => callApi('balance_run', equation),
      }));
      // Curriculum chip beside the "Chemistry" page title (Figma node 23:2).
      const badge = document.getElementById('header-badge');
      if (badge && model.curriculumCode) badge.replaceChildren(UI.badge(model.curriculumCode));
      return;
    }
  }
  // The practice-problems surface (issue #11): a problem list on the left and the
  // selected problem's worked solution on the right. Everything (statement,
  // hidden steps/answer, video link, related-topic blocks) is baked into the
  // model, so the renderer reveals and swaps with no further round-trip.
  if (item && item.kind === 'problems') {
    const model = await callApi('problems_screen', item.id);
    if (document.getElementById('screen-mount') !== mount) return;
    if (model) {
      mount.replaceChildren(Screens.problems(model));
      // Curriculum chip beside the subject title + the Problems-specific subtitle
      // (Figma node 29:2) — the same shell-header pattern the periodic screen uses.
      const badge = document.getElementById('header-badge');
      if (badge && model.curriculumCode) badge.replaceChildren(UI.badge(model.curriculumCode));
      const subtitle = document.getElementById('header-subtitle');
      if (subtitle && model.labels && model.labels.practiceSubtitle) {
        subtitle.textContent = model.labels.practiceSubtitle;
      }
      return;
    }
  }
  mount.replaceChildren(placeholderNode(data, subject));
}

function render() {
  // Close any open body-level overlay (guide or key-term pop-up) before
  // rebuilding #app: these overlays are appended to document.body, not inside
  // #app, so the DOM rebuild below would otherwise orphan them over the page
  // in the previous language / subject / item (issue #51).
  Screens.closeOverlays();
  const data = state.data;
  document.documentElement.lang = data.lang;
  const app = document.getElementById('app');

  // When the active filter hides every subject, skip the normal content area
  // and render the no-results empty state instead (issue #123).
  if (!data.subjects || data.subjects.length === 0) {
    app.replaceChildren(renderNav(data), renderNoResults(data));
    app.removeAttribute('aria-busy');
    return;
  }

  // Clamp subject and item indices after a filter change may have shortened
  // the subject or item lists (prevents an out-of-bounds access).
  if (state.subject >= data.subjects.length) state.subject = 0;
  const subject = data.subjects[state.subject];
  if (state.item >= subject.items.length) state.item = 0;

  app.replaceChildren(renderNav(data), renderContent(data, subject));
  app.removeAttribute('aria-busy');
  mountScreen();
}

async function init() {
  state.data = await loadState();
  render();
  maybeAutoCheck();
}

// Non-blocking startup update check (#74): only when the user left auto-check on.
// It never interrupts — on a newer release it just lights the updates button's
// dot and caches the result; offline/errors stay silent.
async function maybeAutoCheck() {
  if (!state.data || !state.data.autoUpdateCheck) return;
  const result = await callApi('check_updates');
  if (result && result.status === 'available') {
    state.updateResult = result;
    state.updateAvailable = true;
    render(); // repaint the nav so the updates button shows its alert dot
  }
}

// Start as soon as we have a state source. Guard against the race where
// PyWebView has already injected its API (and fired `pywebviewready`) before
// this script attached the listener — otherwise the window stays blank.
if (window.__STUDY_CALC_STATE__ || (window.pywebview && window.pywebview.api)) init();
else window.addEventListener('pywebviewready', init);
