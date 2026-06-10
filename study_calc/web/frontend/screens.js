// Per-screen content renderers (issue #6 onward). Vanilla JS; builds on
// `window.h` (dom.js) and `window.UI` (components.js). Each screen returns a
// self-contained interactive node: typing / solving update the node in place,
// without re-running the shell's full render (the shell only re-renders on a
// nav or language change). Loaded after components.js, before shell.js.
'use strict';

const Screens = {
  // Physics formula screen (issue #6). `model` is the bridge's
  // formula_screen() result; `ctx.solve(key, values)` -> Promise of the bridge's
  // solve_formula() result (or null when no backend is present, e.g. preview).
  formula(model, ctx) {
    const L = model.labels;
    const formulas = model.formulas;
    // `run` is a generation token: any state change (select / clear / a newer
    // compute) bumps it, so a late in-flight solve discards its result instead of
    // clobbering the panel. The synchronous Tk panel can't hit this race.
    const st = { index: 0, values: {}, solution: null, run: 0 };

    const current = () => formulas[st.index];

    // --- mutable islands updated in place ---
    const titleNode = h('h2', { class: 'card__title' }, []);
    const exprNode = h('p', { class: 'formula__expr' }, []);
    // Enter in any field solves, mirroring the Tk panel's <Return> binding.
    const fieldsWrap = h('div', {
      class: 'formula__fields',
      onkeydown: (e) => { if (e.key === 'Enter') { e.preventDefault(); compute(); } },
    }, []);
    const solutionContent = h('div', { class: 'solution' }, []);
    const learningContent = h('div', { class: 'learning' }, []);

    function renderFields() {
      fieldsWrap.replaceChildren(...current().variables.map((v) =>
        UI.textInput({
          label: v.label,
          value: st.values[v.symbol] || '',
          oninput: (val) => { st.values[v.symbol] = val; },
        })));
    }

    function renderSolution() {
      const s = st.solution;
      let body;
      if (s == null) body = UI.hint(L.hint);
      else if (s.ok) body = UI.result({ label: L.answer, value: s.answer });
      else body = UI.errorStrip(s.error);
      solutionContent.replaceChildren(body);
    }

    function renderLearning() {
      learningContent.replaceChildren(...learningBlocks(current().learning, L));
    }

    function select(index) {
      st.run++;
      st.index = index;
      st.values = {};
      st.solution = null;
      titleNode.textContent = current().name;
      exprNode.textContent = current().expression;
      renderFields();
      renderSolution();
      renderLearning();
    }

    async function compute() {
      // Drop the result if anything changed (formula switch, Clear, a newer
      // compute) while the async solve was in flight.
      const run = ++st.run;
      const res = await ctx.solve(current().key, st.values);
      if (run !== st.run) return;
      st.solution = res || null;
      renderSolution();
    }

    function clear() {
      st.run++;
      st.values = {};
      st.solution = null;
      renderFields();
      renderSolution();
    }

    const picker = UI.select({
      label: L.formula,
      value: current().key,
      options: formulas.map((f) => ({ value: f.key, label: f.name })),
      onchange: (key) => select(formulas.findIndex((f) => f.key === key)),
    });

    const inputCard = UI.card({
      body: [
        h('div', { class: 'card__header' }, [titleNode]),
        picker, exprNode, UI.hint(L.hint), fieldsWrap,
        h('div', { class: 'chips' }, [
          UI.button({ label: L.compute, variant: 'primary', onclick: compute }),
          UI.button({ label: L.clear, variant: 'ghost', onclick: clear }),
        ]),
      ],
    });

    const solutionCard = UI.card({ title: L.result, body: [solutionContent] });
    const learningCard = UI.card({ body: [learningContent] });

    select(0); // initialise title / expression / fields / solution / learning

    return h('div', { class: 'screen screen--formula' }, [
      h('div', { class: 'screen__col screen__col--main' }, [inputCard, solutionCard]),
      h('div', { class: 'screen__col screen__col--aside' }, [learningCard]),
    ]);
  },

  // Operations screen — backs both the symbolic-math/CAS (#7) and vectors (#8)
  // tabs. `model` is the bridge's cas_screen() / vector_screen(); each operation
  // carries an ordered `fields` list and its learning blocks. `ctx.run(op, values)`
  // (values keyed by field id) -> Promise of cas_run() / vector_run(). The right
  // card teaches the selected operation before a result and shows the engine's
  // step-by-step (green answer lines) after — mirroring the Tk shared right panel.
  operations(model, ctx) {
    if (!model.available) {
      // e.g. SymPy absent: the same friendly notice as the Tk fallback tab.
      return h('div', { class: 'screen screen--ops' }, [
        UI.card({ title: model.title, body: [UI.errorStrip(model.notice)] }),
      ]);
    }

    const L = model.labels;
    const ops = model.operations;
    // Persistent fields (expression / variable / u / v / k) keep their text
    // across op changes — the Tk panels only disable the ones the new op can't
    // use, never wiping them. The op-specific extras (e.g. CAS rate's a/b) are
    // not persistent and get cleared on every op change (Tk rebuilds them empty).
    const persistentIds = new Set();
    for (const o of ops) for (const f of o.fields) if (f.persist) persistentIds.add(f.id);
    // `run` is a generation token — see the formula screen: it discards a late
    // in-flight result when the op changes, Clear is pressed, or a newer compute
    // starts.
    const st = { op: 0, values: {}, view: null, run: 0 };

    const current = () => ops[st.op];

    const inputsWrap = h('div', { class: 'ops__inputs' }, []);
    const panelContent = h('div', { class: 'ops__panel' }, []);

    function renderInputs() {
      inputsWrap.replaceChildren(...current().fields.map((f) =>
        UI.textInput({
          label: f.label, value: st.values[f.id] || '', mono: f.mono,
          oninput: (v) => { st.values[f.id] = v; },
        })));
    }

    function renderPanel() {
      if (st.view && st.view.type === 'error') {
        panelContent.replaceChildren(UI.errorStrip(st.view.error));
      } else if (st.view && st.view.type === 'steps') {
        panelContent.replaceChildren(...st.view.steps.map((s) =>
          s.answer
            ? h('div', { class: 'result' }, [h('span', { class: 'result__value', text: s.text })])
            : h('p', { class: 'ops-step', text: s.text })));
      } else {
        // Before a result: teach the selected operation.
        panelContent.replaceChildren(...learningBlocks(current().learning, L));
      }
    }

    function selectOp(index) {
      st.run++;
      st.op = index;
      // Keep the persistent main inputs; drop the op-specific extras — mirroring
      // the Tk panels, which preserve expression/variable/u/v/k but rebuild the
      // extra fields empty.
      for (const key of Object.keys(st.values)) if (!persistentIds.has(key)) delete st.values[key];
      st.view = null;
      chipsWrap.replaceChildren(opChips());
      renderInputs();
      renderPanel();
    }

    async function compute() {
      const run = ++st.run;
      const res = await ctx.run(current().id, st.values);
      if (run !== st.run) return; // op changed / cleared / superseded — drop it
      if (!res) return; // no backend (static preview)
      st.view = res.ok ? { type: 'steps', steps: res.steps } : { type: 'error', error: res.error };
      renderPanel();
    }

    function clear() {
      st.run++;
      st.values = {};
      st.view = null;
      renderInputs();
      renderPanel();
    }

    const opChips = () => UI.chips({
      items: ops.map((o) => ({ id: o.id, label: o.label })),
      active: current().id,
      onselect: (id) => selectOp(ops.findIndex((o) => o.id === id)),
    });
    const chipsWrap = h('div', { class: 'ops__chips' }, [opChips()]);

    // Enter in any input solves (parity with the Tk <Return> binding).
    inputsWrap.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); compute(); }
    });

    const inputCard = UI.card({
      title: L.operation,
      body: [
        chipsWrap,
        UI.hint(L.hint),
        inputsWrap,
        h('div', { class: 'chips' }, [
          UI.button({ label: L.compute, variant: 'primary', onclick: compute }),
          UI.button({ label: L.clear, variant: 'ghost', onclick: clear }),
        ]),
      ],
    });
    const solutionCard = UI.card({ title: L.stepsTitle, body: [panelContent] });

    renderInputs();
    renderPanel();

    return h('div', { class: 'screen screen--formula' }, [
      h('div', { class: 'screen__col screen__col--main' }, [inputCard]),
      h('div', { class: 'screen__col screen__col--aside' }, [solutionCard]),
    ]);
  },
  // Unit converter screen (issue #9). `model` is bridge's converter_screen();
  // `ctx.run(category, value, fromUnit, toUnit)` -> Promise of convert_run()
  // (or null when the backend is absent, e.g. the browser preview).
  // All category unit lists are baked into the model so swapping categories only
  // updates the DOM — no round-trip to the backend.
  converter(model, ctx) {
    const L = model.labels;
    const cats = model.categories;

    // Generation token: prevents a stale async result from clobbering the panel
    // if the user presses Convert twice or changes category mid-flight.
    const st = { cat: 0, fromUnit: null, toUnit: null, value: '', result: null, run: 0 };

    const current = () => cats[st.cat];

    // Seed from/to with the first two units of the first category — mirrors the
    // Tk ConverterPanel which calls _refresh_units() on construction.
    const initUnits = current().units;
    st.fromUnit = initUnits[0].id;
    st.toUnit = initUnits[Math.min(1, initUnits.length - 1)].id;

    // Mutable islands updated in place.
    const chipsWrap  = h('div', { class: 'converter__chips' }, []);
    const fromWrap   = h('div', {}, []);
    const toWrap     = h('div', {}, []);
    const resultWrap = h('div', { class: 'converter__result' }, []);

    // The value input node persists across category changes; value is tracked
    // via the input event so compute() can read it without querying the DOM.
    const valueInput = h('input', { class: 'field__control', type: 'text' });
    valueInput.addEventListener('input', (e) => { st.value = e.target.value; });
    // Enter converts (parity with the Tk <Return> binding).
    valueInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); compute(); }
    });
    const valueField = UI.field(L.value, valueInput);

    function renderUnitSelects() {
      const units = current().units;
      fromWrap.replaceChildren(UI.select({
        label: L.from,
        value: st.fromUnit,
        options: units.map((u) => ({ value: u.id, label: u.label })),
        onchange: (id) => { st.fromUnit = id; },
      }));
      toWrap.replaceChildren(UI.select({
        label: L.to,
        value: st.toUnit,
        options: units.map((u) => ({ value: u.id, label: u.label })),
        onchange: (id) => { st.toUnit = id; },
      }));
    }

    function renderResult() {
      const r = st.result;
      if (!r) {
        resultWrap.replaceChildren();
      } else if (r.ok) {
        resultWrap.replaceChildren(UI.result({ label: L.result, value: r.result }));
      } else {
        resultWrap.replaceChildren(UI.errorStrip(r.error));
      }
    }

    function selectCat(index) {
      // Re-clicking the active chip is a no-op — only an actual category change
      // resets the unit selectors and clears the result (parity with the Tk
      // ConverterPanel, which refreshes only on a real <<ComboboxSelected>>).
      if (index === st.cat) return;
      st.run++;
      st.cat = index;
      const units = current().units;
      st.fromUnit = units[0].id;
      st.toUnit = units[Math.min(1, units.length - 1)].id;
      st.result = null;
      chipsWrap.replaceChildren(catChips());
      renderUnitSelects();
      renderResult();
    }

    async function compute() {
      // Drop the result if category changed, Clear was pressed, or a newer
      // compute started before this one resolved — same discipline as formula/ops.
      const run = ++st.run;
      const res = await ctx.run(current().id, st.value, st.fromUnit, st.toUnit);
      if (run !== st.run) return;
      if (!res) return; // no backend (static preview)
      st.result = res;
      renderResult();
    }

    function clear() {
      st.run++;
      st.value = '';
      valueInput.value = '';
      st.result = null;
      renderResult();
    }

    const catChips = () => UI.chips({
      items: cats.map((c) => ({ id: c.id, label: c.label })),
      active: current().id,
      onselect: (id) => selectCat(cats.findIndex((c) => c.id === id)),
    });

    // Initialise all mutable islands before the node is returned.
    chipsWrap.replaceChildren(catChips());
    renderUnitSelects();

    const converterCard = UI.card({
      title: model.title,
      body: [
        chipsWrap,
        h('div', { class: 'converter__fields' }, [valueField, fromWrap, toWrap]),
        h('div', { class: 'chips' }, [
          UI.button({ label: L.convert, variant: 'primary', onclick: compute }),
          UI.button({ label: L.clear, variant: 'ghost', onclick: clear }),
        ]),
        resultWrap,
      ],
    });

    return h('div', { class: 'screen screen--converter' }, [converterCard]);
  },

  // Periodic-table screen (issue #10). `model` is the bridge's periodic_screen();
  // `ctx.molarMass(formula)` -> Promise of molar_mass_run() (or null in preview),
  // `ctx.balance(equation)` -> Promise of balance_run() (or null in preview).
  // The 118-element grid is placed by xpos/ypos via inline style; cells are
  // coloured through `.periodic__cell--<series>` classes that map to the
  // --series-* CSS tokens. The element detail line is built client-side from the
  // pre-baked element list — no round-trip needed (mirrors converter's approach).
  periodic(model, ctx) {
    const L = model.labels;
    const els = model.elements;

    // Per-tool generation tokens — each tool gets its own counter so a slow
    // molar-mass request cannot clobber a concurrent balance result and vice versa.
    const st = { mmRun: 0, balRun: 0 };

    // --- Detail line (updated on cell click; no backend round-trip) ---
    const detailWrap = h('div', { class: 'periodic__detail' }, []);

    function fmtMass(m) {
      // Mirror Python's :g format: up to 6 significant digits, no trailing zeros.
      return parseFloat(m.toPrecision(6)).toString();
    }

    function renderDetail(el) {
      const group = el.group != null ? String(el.group) : '—'; // em dash for no group
      const text = (
        el.name + '  ·  ' + L.atomicNumber + ' ' + el.number
        + '  ·  ' + L.atomicMass + ' ' + fmtMass(el.mass) + ' ' + L.gramPerMol
        + '  ·  ' + L.group + ' ' + group + ', ' + L.period + ' ' + el.period
        + '  ·  ' + el.category
      );
      detailWrap.replaceChildren(h('p', { class: 'periodic__detail-text', text }));
    }

    // --- Periodic grid: one button per element, placed via xpos/ypos. ---
    const gridCells = els.map((el) =>
      h('button', {
        class: 'periodic__cell periodic__cell--' + el.series,
        type: 'button',
        style: 'grid-column:' + el.xpos + ';grid-row:' + el.ypos,
        title: el.name,
        onclick: () => renderDetail(el),
      }, [
        h('span', { class: 'periodic__num', text: String(el.number) }),
        h('span', { class: 'periodic__sym', text: el.symbol }),
      ])
    );
    const grid = h('div', { class: 'periodic__grid' }, gridCells);

    // --- Molar-mass tool ---
    const mmInput = h('input', { class: 'field__control', type: 'text', placeholder: 'H2O' });
    const mmResultWrap = h('div', { class: 'periodic__tool-result' }, []);

    async function computeMM() {
      const run = ++st.mmRun;
      const res = await ctx.molarMass(mmInput.value);
      if (run !== st.mmRun) return; // superseded by a newer request or Clear
      if (!res) return;             // no backend (static preview)
      mmResultWrap.replaceChildren(
        res.ok ? UI.result({ label: '', value: res.result }) : UI.errorStrip(res.error)
      );
    }
    function clearMM() {
      st.mmRun++;
      mmInput.value = '';
      mmResultWrap.replaceChildren();
    }
    // Enter computes (parity with the Tk <Return> binding).
    mmInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); computeMM(); } });

    // --- Balancer tool ---
    const balInput = h('input', {
      class: 'field__control', type: 'text',
      placeholder: 'CH4 + O2 -> CO2 + H2O',
    });
    const balResultWrap = h('div', { class: 'periodic__tool-result' }, []);

    async function computeBal() {
      const run = ++st.balRun;
      const res = await ctx.balance(balInput.value);
      if (run !== st.balRun) return;
      if (!res) return;
      balResultWrap.replaceChildren(
        res.ok ? UI.result({ label: '', value: res.result }) : UI.errorStrip(res.error)
      );
    }
    function clearBal() {
      st.balRun++;
      balInput.value = '';
      balResultWrap.replaceChildren();
    }
    balInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); computeBal(); } });

    const toolsCard = UI.card({
      title: model.title,
      body: [
        h('div', { class: 'periodic__tools' }, [
          h('div', { class: 'periodic__tool-row' }, [
            UI.field(L.molarMass, mmInput),
            h('div', { class: 'periodic__tool-actions chips' }, [
              UI.button({ label: L.compute, variant: 'primary', onclick: computeMM }),
              UI.button({ label: L.clear, variant: 'ghost', onclick: clearMM }),
            ]),
            mmResultWrap,
          ]),
          h('div', { class: 'periodic__tool-row' }, [
            UI.field(L.equation, balInput),
            h('div', { class: 'periodic__tool-actions chips' }, [
              UI.button({ label: L.balance, variant: 'primary', onclick: computeBal }),
              UI.button({ label: L.clear, variant: 'ghost', onclick: clearBal }),
            ]),
            balResultWrap,
          ]),
        ]),
      ],
    });

    const gridCard = UI.card({ body: [grid, detailWrap] });

    // Seed the detail line with hydrogen (element 1), mirroring the Tk panel
    // which calls `self._select(periodic.element("H"))` in __init__.
    const hydrogen = els.find((e) => e.symbol === 'H') || els[0];
    renderDetail(hydrogen);

    return h('div', { class: 'screen screen--periodic' }, [toolsCard, gridCard]);
  },

  // Guide overlay (issue #40). `model` is the bridge's guide_screen() result:
  // {title, intro, sections:[{head,body}]}. All strings are already localized
  // server-side — nothing is hardcoded here.
  //
  // a11y contract (mirrors the #26 modal contract):
  //   - role="dialog" + aria-modal="true" on the backdrop
  //   - focus moves to the × close button on open
  //   - focus is trapped within the dialog while open
  //   - focus returns to the trigger (#guide-btn) on close
  //   - Escape, clicking the backdrop, and the × button all dismiss
  openGuide(model) {
    // Guard against double-open: the #guide-btn handler is async, so a quick
    // double-click could otherwise stack two overlays — and only the top one
    // would be dismissable via Escape. If a guide overlay is already mounted,
    // refocus its close button instead of mounting a second.
    const existing = document.querySelector('.modal--guide');
    if (existing) {
      const btn = existing.querySelector('.modal__close');
      if (btn) btn.focus();
      return;
    }

    const trigger = document.getElementById('guide-btn');

    // `overlay` is declared before `closeBtn` so the close() closure can
    // reference it even though the assignment happens further down.
    let overlay;

    function close() {
      if (overlay) overlay.remove();
      if (trigger) trigger.focus();
    }

    const closeBtn = h('button', {
      class: 'modal__close',
      type: 'button',
      'aria-label': model.close,
      onclick: close,
    }, ['×']); // ×

    // Build the scrollable body: lead paragraph + six section head/body pairs.
    const bodyNodes = [
      h('p', { class: 'rich__body', text: model.intro }),
      ...model.sections.flatMap((sec) => [
        h('h3', { class: 'learn__heading', text: sec.head }),
        h('p', { class: 'rich__body', text: sec.body }),
      ]),
    ];

    // Use the shared UI.card factory — do not re-implement card markup.
    const card = UI.card({
      title: model.title,
      body: bodyNodes,
      class: 'guide__card',
    });

    // Inject the × button into the card header so title + close live together.
    const header = card.querySelector('.card__header');
    if (header) header.append(closeBtn);
    else card.prepend(closeBtn); // fallback if title was omitted

    overlay = h('div', {
      class: 'modal modal--guide',
      role: 'dialog',
      'aria-modal': 'true',
      'aria-label': model.title,
    }, [card]);

    // Backdrop click dismisses.
    overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });

    // Escape dismisses; Tab is trapped within the dialog.
    overlay.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { e.preventDefault(); close(); return; }
      if (e.key !== 'Tab') return;
      const focusable = Array.from(overlay.querySelectorAll(
        'button:not([disabled]), [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      ));
      if (!focusable.length) return;
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault(); last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault(); first.focus();
      }
    });

    document.body.append(overlay);
    closeBtn.focus(); // move focus into the dialog on open
  },
};

// Render the learning-card blocks (the model produced by screens.py mirrors the
// Tk ExplanationPanel: badge, theory, useful formulas, how-to-solve, key terms,
// worked example, study links — all prose already localized server-side).
function learningBlocks(blocks, L) {
  const nodes = [];
  for (const b of blocks) {
    switch (b.type) {
      case 'badge':
        nodes.push(UI.badge(b.text));
        break;
      case 'heading':
        nodes.push(h('h3', { class: 'learn__heading', text: b.text }));
        break;
      case 'body':
        nodes.push(h('p', { class: 'rich__body', text: b.text }));
        break;
      case 'hint':
        nodes.push(UI.hint(b.text));
        break;
      case 'formula':
        nodes.push(h('p', { class: 'rich__formula', text: b.text }));
        break;
      case 'steps':
        nodes.push(h('ol', { class: 'learn__steps' },
          b.items.map((s) => h('li', { text: s }))));
        break;
      case 'terms':
        nodes.push(h('ul', { class: 'learn__terms' },
          b.items.map((term) => renderTerm(term, L))));
        break;
      case 'example':
        nodes.push(renderExample(b));
        break;
      case 'links':
        nodes.push(h('div', { class: 'learn__links' },
          b.items.map((link) => h('a', {
            class: 'rich__link', text: link.text,
            href: link.href, target: '_blank', rel: 'noopener',
          }))));
        break;
    }
  }
  return nodes;
}

function renderTerm(term, L) {
  return h('li', { class: 'term' }, [
    h('span', { class: 'term__title', text: term.title }),
    h('span', { class: 'term__short', text: ' — ' + term.short }),
    h('button', {
      class: 'term__link', type: 'button',
      onclick: () => openConcept(term, L),
    }, [L.openFull]),
  ]);
}

function renderExample(ex) {
  const parts = [];
  if (ex.title) parts.push(h('p', { class: 'rich__body', text: ex.title }));
  if (ex.given.length) {
    parts.push(h('p', { class: 'rich__label', text: ex.givenLabel + ':' }));
    parts.push(h('ul', { class: 'learn__given' },
      ex.given.map((g) => h('li', { text: g }))));
  }
  if (ex.find) {
    parts.push(h('p', { class: 'rich__label' }, [
      ex.findLabel + ': ', h('span', { class: 'rich__body-inline', text: ex.find }),
    ]));
  }
  if (ex.steps.length) {
    parts.push(h('p', { class: 'rich__label', text: ex.solutionLabel + ':' }));
    parts.push(h('ol', { class: 'learn__steps' },
      ex.steps.map((s) => h('li', { text: s }))));
  }
  if (ex.answer) {
    parts.push(h('p', { class: 'rich__label' }, [
      ex.answerLabel + ': ',
      h('span', { class: 'rich__answer', text: ex.answer }),
    ]));
  }
  return h('div', { class: 'learn__example' }, parts);
}

// Key-term pop-up: full definition + related formulas + clickable "see also"
// terms (resolved one level deep in the model, so this stays self-contained).
function openConcept(concept, L) {
  const card = h('div', { class: 'modal__card' }, [
    h('button', {
      class: 'modal__close', type: 'button', 'aria-label': L.close,
      onclick: close,
    }, ['×']),
    h('h3', { class: 'modal__title', text: concept.title }),
    h('p', { class: 'rich__body', text: concept.full }),
  ]);
  if (concept.formulas.length) {
    card.append(h('h4', { class: 'learn__heading', text: L.relatedFormulas }));
    concept.formulas.forEach((f) =>
      card.append(h('p', { class: 'rich__formula', text: f })));
  }
  if (concept.seeAlso.length) {
    card.append(h('h4', { class: 'learn__heading', text: L.seeAlso }));
    card.append(h('div', { class: 'chips' }, concept.seeAlso.map((rel) =>
      h('button', {
        class: 'chip', type: 'button',
        onclick: () => { close(); openConcept(rel, L); },
      }, [rel.title]))));
  }

  const overlay = h('div', { class: 'modal' }, [card]);
  overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
  function close() { overlay.remove(); }
  document.body.append(overlay);
}

window.Screens = Screens;
