# Agents Guide (agents.md)

This doc is for working with **LLM agents** (GPT, Codex, Gemini, etc.) on the **SQLer** project. It captures our conventions, the system’s mental model, and the exact commands to run (with **uv**) so agents—and humans—stay in sync.

---

## Project Snapshot

- **Name:** SQLer
- **Goal:** A pragmatic, JSON‑first SQLite micro‑ORM with a lazy, chainable query API; Pydantic v2 models; opt‑in optimistic locking; and a matching async stack.
- **Python:** 3.12+
- **Key libs:** sqlite3/aiosqlite, Pydantic v2, pytest, ruff, uv
- **SQLite JSON1:** required (uses `json_extract`, `json_each`)

### Canonical Structure (src/)

```
src/
  sqler/
    adapters/   # sync.py, async.py
    db/         # sqler_db.py
    models/     # model.py, safe.py
    query/      # field.py, expr.py, builder.py, queryset.py
    utils/      # pragmas.py
    registry.py # table ↔ class registry (relationships)
```

---

## Golden Rules (Agents, Please Read Carefully)

1. **Naming:** The library is **SQLer**. Class/module names should reflect `sqler`.
2. **Table per model:** Default table = **lowercase plural** of class name (override via config). The **DB is shared**; the table is owned by the model.
3. **Private internals:** Use private attrs `_id` (always) and `_version` (safe models) on models. Users can have their own `id` or `version` fields.
4. **Lazy queries:** `.filter()` returns a **query object**; execution happens on `.all()/.first()/.count()` (and `SQLerQuerySet[T]` returns **model instances**).
5. **JSON arrays:** Implement `.contains()`/`.isin()` using **`json_each` + EXISTS**, not string matching.
6. **Nested models:**
   - **Pydantic submodels** → inline JSON
   - **SQLerModel submodels** → save as references `{ "_table": "addresses", "_id": 123 }` and resolve on load/refresh.
7. **Safe models:** `SQLerSafeModel` is **opt‑in**, uses `_version` column and raises **`StaleVersionError`** on mismatch.
8. **Security:** Always parameterize values. Only interpolate **trusted identifiers** (table names from model metadata).
9. **Docstrings:** Use **Google style** docstrings consistently for public APIs and tests.
10. **No mypy** for now. If Astral’s **`ty`** is stable, prefer it; otherwise skip type‑checking in CI.

---

## Commands (uv‑managed project)

All commands run through **uv**.

### Setup

```bash
uv sync
```

### Test

```bash
uv run pytest -q
uv run pytest -q -k "expr and contains"   # subset
uv run pytest --maxfail=1 -q               # fail fast
```

### Coverage (optional)

```bash
uv run pytest --cov=sqler --cov-report=term-missing
```

### Lint & Format (ruff)

```bash
uv run ruff check .
uv run ruff check --fix .
uv run ruff format
```

### Build & Publish

```bash
uv build
# then: twine upload dist/*
```

---

## Prompting Playbook (Templates)

Use these templates when asking an LLM to modify code. Always include the **file path**, **target function/class**, and **acceptance tests**.

### 1) Lazy Query Refactor

> Refactor `sqler.models.model.SQLerModel.filter` so it returns a lazy `SQLerQuerySet[T]` that wraps `sqler.query.queryset.SQLerQuery`. Ensure chaining works and execution happens only on `.all()/.first()/.count()`. Keep values parameterized. Update/add tests in `tests/test_models.py` for chaining and `.sql()` inspection.

### 2) Arrays via `json_each`

> Implement `SQLerField.contains/isin` using `json_each` with `EXISTS`. Avoid LIKE/string matching. Add tests in `tests/test_arrays.py` for ints/strings/mixed and nested arrays (negative case for non‑top‑level).

### 3) Relationships Save/Load/Refresh

> For fields typed as `SQLerModel`, on save recursively `.save()` the child and store `{_table, _id}`; on load/refresh, resolve via registry (table→class). Add tests covering 2–3 levels of nesting and mixed pydantic/SQLer submodels.

### 4) Relationship Joins (Phase 2)

> Enable `User.filter(User.address.city == "Kyoto")` by compiling JOINs: `users u JOIN addresses a ON json_extract(u.data,'$.address._id') = a._id` and filter on `json_extract(a.data,'$.city')`. Add tests for AND/OR/NOT and multi‑hop.

### 5) Async Parity

> Add `AsyncSQLiteAdapter` (aiosqlite), `AsyncSQLerQuery`, and `AsyncSQLerModel` with 1:1 API. Port sync tests to async with pytest‑asyncio; ensure WAL works on disk.

---

## Coding Conventions

- **Python** 3.12+, **Pydantic v2**
- **Google‑style docstrings**
- **Param order preserved** in expressions
- **Prefer small, composable helpers** (pure functions where possible)
- **Tests first** (TDD whenever feasible)

---

## PR Checklist (Agents & Humans)

- [ ] Added/updated tests (sync & async where applicable)
- [ ] `uv run ruff check .` passes; `uv run ruff format` run
- [ ] `uv run pytest -q` green locally
- [ ] Public docstrings updated (Google style)
- [ ] README/ROADMAP updated if behavior changed
- [ ] No hard‑coded paths; parameterized SQL values

---

## Gotchas & Notes

- `json_tree` is powerful but heavy—prefer `json_extract`/`json_each` until a real use‑case requires full recursion.
- In‑memory **shared** DBs use URI: `file::memory:?cache=shared`.
- WAL is recommended on disk; `synchronous=NORMAL` is a good durability/throughput trade‑off for app‑level journaling.
- Avoid cyclical model graphs for now (e.g., A→B→A). Document as unsupported.

---

## How Agents Should Respond

- Provide **complete** code blocks for changed files.
- Avoid placeholders; keep names consistent with `sqler`.
- Include tests and mention exact commands:
  - `uv run pytest -q`
  - `uv run ruff check .`
  - `uv run ruff format`

---

_This doc is the living contract for collaborating with LLMs on SQLer. If anything drifts, update this first._
