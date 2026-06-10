// Shared DOM helper for the frontend (loaded before shell.js / components.js).
// Plain <script> (no ES modules) so it works over file:// in PyWebView.
'use strict';

// Tiny hyperscript: h('tag', {class, text, onclick, ...attrs}, child|children).
// - `class` -> className, `text` -> textContent
// - `onX` function -> addEventListener('x', fn)
// - any other key -> setAttribute (skipped when null/false)
// Children may be nodes or strings; null/false are ignored.
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

window.h = h;
