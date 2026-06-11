# <ticket> — implementation  ·  owner: python-pro · javascript-pro/frontend-developer · sql-pro

One artifact, one section per layer touched. Fill only the layers in scope; mark
the rest "not touched".

## Core / domains (python-pro)
- Files: <core/*, domains/*>
- What changed:
- New formula/unit/error code? → keys added to all five locales (`en/es/fr/ru/uk`); errors also in `_ERROR_KEYS`

## Web / frontend (javascript-pro / frontend-developer)
- Files: <web/*, frontend/*>
- What changed: (components/screens/tokens — no hardcoded colors, tokens only)

## Database (sql-pro)
- Schema change? <yes/no> — `data/schema.sql` + `scripts/seed_db.py` + ADR 0002
- Learning JSON changed? → reseed: `python scripts/seed_db.py`, commit `knowledgebase.db`
- Rows keyed by `(id, language)`, `en` canonical + fallback — i18n contract held
- [ ] `test_db_in_sync` green (committed DB == fresh seed)

## Key decisions / trade-offs

## Gate
- [ ] `uv run --extra dev pytest` green incl. test_i18n · test_references · test_learning · test_problems
