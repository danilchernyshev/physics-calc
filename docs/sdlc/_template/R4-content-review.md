# <ticket> — content review  ·  owner: curriculum-author

- [ ] All content original (OpenStax/general knowledge; videos & sites linked, not copied)
- [ ] Every study link resolves HTTP 200
- [ ] Course codes valid (in `CURRICULUM_GRADES`)
- [ ] Every referenced glossary term resolves; no dangling `see_also`
- [ ] DB reseeded from JSON: `python scripts/seed_db.py`; `knowledgebase.db` committed
- [ ] `uv run --extra dev pytest tests/test_learning.py tests/test_problems.py tests/test_db_in_sync.py` green
- [ ] en canonical; es/fr/uk plan recorded

## Results
<paste pytest summary>
