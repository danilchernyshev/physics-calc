// Shared card & control components (issue #5).
// Factory functions returning DOM nodes, styled by components.css on the design
// tokens. Plain <script> exposing `window.UI` (no ES modules, so it works over
// file:// in PyWebView). Every per-screen surface (#6–#11) builds from these —
// no per-screen re-implementation.
'use strict';

const UI = {
  // Rounded surface card. opts: {title, badge, body, class}. `body` is a node or
  // array of nodes; when `title`/`badge` is given a header row is added.
  card({ title = null, badge = null, body = [], class: cls = '' } = {}) {
    const children = [];
    if (title != null || badge != null) {
      children.push(h('div', { class: 'card__header' }, [
        title != null ? h('h2', { class: 'card__title', text: title }) : null,
        badge != null ? UI.badge(badge) : null,
      ]));
    }
    children.push(h('div', { class: 'card__body' }, body));
    return h('section', { class: 'card' + (cls ? ' ' + cls : '') }, children);
  },

  badge(text) { return h('span', { class: 'badge', text }); },
  eyebrow(text) { return h('p', { class: 'eyebrow', text }); },
  hint(text) { return h('p', { class: 'hint', text }); },

  // Labeled text input. opts: {label, value, placeholder, mono, oninput, width}.
  textInput({ label = null, value = '', placeholder = '', mono = false, oninput = null,
              width = null } = {}) {
    const input = h('input', {
      class: 'field__control' + (mono ? ' field__control--mono' : ''),
      type: 'text', value, placeholder,
      oninput: oninput ? (e) => oninput(e.target.value) : null,
    });
    if (width) input.style.maxWidth = width;
    return UI.field(label, input);
  },

  // Labeled <select>. opts: {label, options:[{value,label}], value, onchange}.
  select({ label = null, options = [], value = null, onchange = null } = {}) {
    const el = h('select', {
      class: 'field__control',
      onchange: onchange ? (e) => onchange(e.target.value) : null,
    }, options.map((o) => {
      const opt = h('option', { value: o.value, text: o.label });
      if (o.value === value) opt.selected = true;
      return opt;
    }));
    return UI.field(label, el);
  },

  // Wrap a control with an optional label.
  field(label, control) {
    return h('div', { class: 'field' }, [
      label != null ? h('label', { class: 'field__label', text: label }) : null,
      control,
    ]);
  },

  // Button. opts: {label, variant: 'primary'|'secondary'|'ghost', onclick, disabled, type}.
  button({ label, variant = 'primary', onclick = null, disabled = false, type = 'button' } = {}) {
    return h('button', {
      class: 'btn btn--' + variant,
      type,
      disabled: disabled || null,
      onclick,
    }, [label]);
  },

  // Selectable chip row / segmented control.
  // opts: {items:[{id,label}], active (id), onselect(id)}.
  chips({ items = [], active = null, onselect = null } = {}) {
    return h('div', { class: 'chips' }, items.map((it) =>
      UI.chip({ label: it.label, active: it.id === active,
                onclick: onselect ? () => onselect(it.id) : null })));
  },

  chip({ label, active = false, onclick = null } = {}) {
    return h('button', {
      class: 'chip' + (active ? ' chip--active' : ''),
      type: 'button', onclick,
    }, [label]);
  },

  // Green result/answer chip. opts: {label, value}.
  result({ label, value } = {}) {
    return h('div', { class: 'result' }, [
      h('span', { class: 'result__label', text: label }),
      h('span', { class: 'result__value', text: value }),
    ]);
  },

  // Red error strip (renders a localized message).
  errorStrip(text) { return h('div', { class: 'error-strip', text }); },

  // Numbered step-by-step list. items: [{text, formula}].
  steps(items = []) {
    return h('ol', { class: 'steps' }, items.map((s, i) =>
      h('li', { class: 'step' }, [
        h('span', { class: 'step__num', text: String(i + 1) }),
        h('div', { class: 'step__body' }, [
          s.text ? h('span', { class: 'step__text', text: s.text }) : null,
          s.formula ? h('span', { class: 'step__formula', text: s.formula }) : null,
        ]),
      ])));
  },

  // Rich-text block (folds the Tk _RichText vocabulary). segments:
  // [{kind:'heading'|'body'|'formula'|'label'|'link', text, href, onclick}].
  rich(segments = []) {
    return h('div', { class: 'rich' }, segments.map((seg) => {
      if (seg.kind === 'link') {
        return h('a', {
          class: 'rich__link', text: seg.text,
          href: seg.href || null,
          target: seg.href ? '_blank' : null,
          rel: seg.href ? 'noopener' : null,
          onclick: seg.onclick || null,
        });
      }
      return h('p', { class: 'rich__' + (seg.kind || 'body'), text: seg.text });
    }));
  },
};

window.UI = UI;
