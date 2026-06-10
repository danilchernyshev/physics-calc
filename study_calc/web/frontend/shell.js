// App shell: nav rail + header, rendered from the bridge's state (issue #4).
// Vanilla JS on purpose — the framework choice for richer components is issue #5.
// Selection (which subject/item is active) lives here, so a language switch only
// refreshes labels and the current screen is preserved.

'use strict';

const state = { data: null, subject: 0, item: 0, langOpen: false };

// Tiny hyperscript helper: h('tag', {class, text, onclick, ...attrs}, children).
function h(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value == null || value === false) continue;
    if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = value;
    else if (key.startsWith('on') && typeof value === 'function') {
      node.addEventListener(key.slice(2), value);
    } else node.setAttribute(key, value);
  }
  for (const child of [].concat(children)) {
    if (child == null || child === false) continue;
    node.append(child.nodeType ? child : document.createTextNode(child));
  }
  return node;
}

async function loadState() {
  if (window.__STUDY_CALC_STATE__) return window.__STUDY_CALC_STATE__;
  return window.pywebview.api.get_state();
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

  return h('nav', { class: 'nav' }, [
    h('div', { class: 'nav__logo' }, [
      h('span', { class: 'nav__logo-badge', text: 'Σ' }), // Σ
      h('span', { class: 'nav__wordmark', text: data.labels.appTitle }),
    ]),
    h('p', { class: 'nav__heading', text: data.labels.subjectsHeading }),
    h('div', { class: 'nav__items' }, items),
    h('div', { class: 'nav__spacer' }),
    h('div', { class: 'nav__footer' }, [
      h('button', { class: 'nav__foot-link' },
        ['ⓘ ' + data.labels.howToUse]), // ⓘ
      langMenu,
      h('button', {
        class: 'nav__foot-link',
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

  const active = subject.items[state.item];
  const placeholder = h('div', { class: 'placeholder' }, [
    h('p', { class: 'placeholder__title', text: active ? active.label : subject.label }),
    h('p', { class: 'placeholder__note', text: data.labels.placeholder }),
  ]);

  return h('main', { class: 'content' }, [
    h('h1', { class: 'header__title', text: subject.label }),
    h('p', { class: 'header__subtitle', text: subject.tagline }),
    tabs,
    placeholder,
  ]);
}

function render() {
  const data = state.data;
  const subject = data.subjects[state.subject];
  document.documentElement.lang = data.lang;
  const app = document.getElementById('app');
  app.replaceChildren(renderNav(data), renderContent(data, subject));
  app.removeAttribute('aria-busy');
}

async function init() {
  state.data = await loadState();
  render();
}

if (window.__STUDY_CALC_STATE__) init();
else window.addEventListener('pywebviewready', init);
