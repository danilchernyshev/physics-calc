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
    const st = { index: 0, values: {}, solution: null };

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
      // Capture the formula being solved; drop the result if the user switched
      // formula while the (async) solve was in flight, so a stale answer never
      // lands under a different formula's solution card.
      const key = current().key;
      const res = await ctx.solve(key, st.values);
      if (current().key !== key) return;
      st.solution = res || null;
      renderSolution();
    }

    function clear() {
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
      class: 'modal__close', type: 'button', 'aria-label': 'Close',
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
