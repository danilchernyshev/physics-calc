# <ticket> — design  ·  design lead: ui-designer  ·  research: ux-researcher  ·  handoff: design-bridge

> Runs only if the ticket touches the frontend. Engine-only ticket → mark skipped in `02-plan.md`.

## UX research & validation  (ux-researcher — A/R)
- User need / problem this UI solves:
- Findings / usability notes / personas:
- Validation: how we know the design is right

## Visual design & interaction  (ui-designer — A/R)
- Screens / states / layout:
- Interaction & flow:
- Components used / added (from `frontend/components.js` `window.UI`):

## Design tokens  (ui-designer — A/R)
- Token changes in `web/tokens.json`? <yes/no — which>
- (tokens.py emits `frontend/tokens.css`; components.css must stay token-only — no hardcoded colors)

## Accessibility intent  (ui-designer — A; accessibility-tester — C)
- Contrast, focus order, ARIA roles designed in. (Actual WCAG test → QA phase 4c.)

## Figma  (ui-designer — R, Figma MCP)
- File / node links:

## Design→code handoff  (design-bridge — R)
- tokens.css / Code Connect mapping notes for frontend (phase 3b):

## Design sign-off  (ui-designer — A/R)  ← design gate
- [ ] research done · tokens settled · a11y intent in · handoff notes ready → gate PASS
