# <ticket/epic> — release  ·  go/no-go: dev-manager + Dev Director  ·  executes: devops / deployment-engineer

> The **Release** column, post-merge and **epic/milestone-level** (D29). A single
> ticket usually rides an epic's release rather than shipping alone.

## Pre-ship gate
- [ ] all child tickets merged
- [ ] post-merge **regression** on `master` green
- [ ] version bumped where required (`pyproject.toml`, installers, CHANGELOG)

## Go / no-go  (dev-manager + Dev Director)
- Decision: ☐ GO ☐ HOLD — <date · who>
- Notes / blockers:

## Execution  (devops / deployment-engineer)
- [ ] tag / build / publish per the project's release path
- [ ] CI green
- Artifacts / links:

## Close-out
- [ ] QA verifies done and closes the ticket(s) (only QA closes — D16)
