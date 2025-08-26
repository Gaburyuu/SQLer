# SQLer Roadmap (v0.1 → v1.0)

**North star:** a pragmatic, modern, JSON-first SQLite micro‑ORM with a clean, lazy, chainable query API; Pydantic v2 models; opt‑in optimistic locking; and a matching async stack. Friendly for beginners, sharp enough for power users.

---

## ✅ Current State (what’s implemented)
- **Sync adapter**: `SQLiteAdapter` (connect/close/execute/executemany/executescript/commit, context manager). In‑memory & on‑disk factories with sane PRAGMAs (WAL, busy_timeout, NORMAL sync for disk; memory‑optimized for RAM).
- **Document store**: `SQLerDB` ensuring per‑table schema `(_id INTEGER PK AUTOINCREMENT, data JSON NOT NULL)`; insert/upsert/bulk_upsert/find/delete/execute_sql; index helpers.
- **Query stack (lazy)**:
  - `SQLerField` → safe JSON pathing (e.g. `$.a.b[1].c`), comparisons; `like()`.
  - Arrays: correct semantics via `json_each` (`contains`, `isin`).
  - Arrays-of-objects: `.any()` (stacked `json_each`).
  - `SQLerExpression` (`&`, `|`, `~`) with param preservation.
  - `SQLerQuery` (immutable chaining: `filter/exclude/order_by/limit`; execute with `all/first/count`).
- **Tests**: adapter lifecycle, CRUD, pathing, boolean precedence, array contains/isin, `.any()` integration.

---

## 🔁 Renaming & Scope
- **Project/package name:** **SQLer** (PyPI package likely `sqler`).
- **Module rename plan:** migrate `stickler.*` → `sqler.*` (one pass refactor once model layer lands).
- **Everything future** should live under `sqler/…`.

---

## 🧱 Architecture Overview
- **Adapter layer** (`sqler.adapters.sync` / `sqler.adapters.async`): SQLite (sync) and aiosqlite (async) with identical APIs.
- **DB layer** (`sqler.db.sqler_db`): table‑agnostic document store; *no* table state on the DB object — always pass table.
- **Query layer** (`sqler.query`): fields → expressions → query; lazy, chainable; JSON‑first.
- **Model layer (new)** (`sqler.models`):
  - `SQLerModel` (Pydantic v2)
    - class‑bound DB via `set_db(db, table=None)`
    - per‑model table (**lowercase plural by default**), overridable.
    - private attrs: `_id` (internal DB id).
    - helpers: `.save()/.delete()/.refresh()/.from_id()/.query()/.filter()`
    - `SQLerQuerySet[T]` wrapper returns **model instances**.
  - `SQLerSafeModel` (opt‑in optimistic locking)
    - storage column: `_version` INTEGER
    - raises **`StaleVersionError`** on stale saves.
- **Indexes**: model sugar `User.add_index("meta.level", unique=False, where=None, name=None)` → forwards to DB and emits `json_extract` expression.
- **Relationships (phase 2)**:
  - Pydantic submodels: inline JSON.
  - SQLerModel submodels: stored as references `{ "_table": "addresses", "_id": 123 }` with recursive save/load/refresh.
- **Async parity**: mirror all public sync APIs (`AsyncSQLiteAdapter`, `AsyncSQLerQuery`, `AsyncSQLerModel`).

---

## 📁 Target Layout
```
src/
  sqler/
    __init__.py
    adapters/
      sync.py            # SQLiteAdapter, interface
      async.py           # AsyncSQLiteAdapter (aiosqlite)
    db/
      sqler_db.py        # SQLerDB (table-agnostic), index helpers
    models/
      model.py           # SQLerModel + SQLerQuerySet
      safe.py            # SQLerSafeModel (+ StaleVersionError)
    query/
      field.py           # SQLerField (JSON path ops, contains/isin/any)
      expr.py            # SQLerExpression (& | ~)
      builder.py         # SQL compilation helpers
      queryset.py        # SQLerQuery (lazy, chainable)
    utils/
      pragmas.py         # PRAGMA presets and factories
    registry.py          # model registry (table ↔ class) for relationships
    session.py           # factories for in-memory/on-disk DBs
```

---

## 🎯 Milestones & Acceptance Criteria

### M1 — Model Layer (Sync)
**Goal:** Table‑per‑model, lazy query returning model instances.

- Implement `SQLerModel`:
  - `set_db(db: SQLerDB, table: str | None = None)` → sets `cls._db`, resolves `cls._table` (default **lowercase plural** of class name), `db.ensure_table(cls._table)`.
  - Private attrs: `_id: int | None` (not part of user schema).
  - CRUD helpers:
    - `.save()` → insert/update via `SQLerDB` for `cls._table`.
    - `.delete()` → delete by `_id`.
    - `.refresh()` → rehydrate fields from DB; raise if `_id` missing/missing row.
    - `.from_id(id)` → hydrate instance; set private `_id`.
  - Query helpers:
    - `.query()` → `SQLerQuerySet[T]` (wraps `SQLerQuery` with model conversion).
    - `.filter(expr)` → `SQLerQuerySet[T]` shorthand.
    - `.all()` optional shorthand = `.query().all()`.
  - **SQLerQuerySet[T]**:
    - Chain: `filter/exclude/order_by/limit` → returns new wrapper
    - Execute: `all()->list[T]`, `first()->T|None`, `count()->int`
    - Inspect: `sql()->str`
- **Index sugar** on models: `add_index(field, *, unique=False, name=None, where=None)` → forwards to DB (`cls._db.create_index(cls._table, ...)`).
- **Tests:**
  - Save/find/delete/refresh.
  - Lazy query chain returning models (filter/order/limit/first/count).
  - `sql()` inspection.
  - Index creation works & `EXPLAIN QUERY PLAN` changes on indexed filter.

**Done when:** all tests pass; examples in README work.

---

### M2 — Safe Model (Optimistic Locking)
**Goal:** Opt‑in concurrency safety with `_version` column.

- DB: add versioned upsert helpers (`upsert_with_version(table, id, data, expected_version)`), create table with `_version INTEGER NOT NULL DEFAULT 0`.
- Model: `SQLerSafeModel(SQLerModel)`
  - Private attr: `_version: int`.
  - `.save()` semantics:
    - new row: `_version = 0` on insert.
    - update: pass `expected_version`, DB increments on success; on mismatch raise **`StaleVersionError`**.
  - `.refresh()` refreshes `_version` too.
- **Tests:**
  - Insert sets version 0; update bumps; mismatch raises `StaleVersionError`.
  - Works with normal model CRUD and queries.

**Done when:** safe tests pass; error type exported.

---

### M3 — Async Parity (aiosqlite)
**Goal:** 1:1 async mirror for adapter, query, and model.

- `AsyncSQLiteAdapter` (aiosqlite): `connect/close/execute/executemany/executescript/commit` awaitables; same pragmas (WAL friendly).
- `AsyncSQLerQuery` with `afilter/aexclude/aorder_by/alimit`, execution `all/first/count` as `await`.
- `AsyncSQLerModel` mirroring CRUD methods as `async` (or classmethod `amodel()` that returns async queryset wrapper).
- **Tests:** pytest‑asyncio for adapter + queries + models; ensure WAL mode OK on disk; shared in‑memory works with URI.

**Done when:** async tests pass and public API names mirror sync.

---

### M4 — Relationships (Phase 1: Save/Load/Refresh)
**Goal:** Correct persistence & hydration of nested SQLerModels.

- **Representation:** For fields typed as `SQLerModel` subclasses, save reference dict `{ "_table": <table>, "_id": <int> }`.
- **Save:** recursively `.save()` child first; write reference in parent JSON.
- **Load/from_id:** detect reference dict → resolve via model registry (table→class) and `.from_id()`.
- **Refresh:** recursively refresh nested SQLerModels.
- **Pydantic submodels:** inline JSON (Pydantic handles dump/validate).
- **Tests:** nested save/load/refresh across 2–3 levels; tolerate mixtures `sqler.pydantic.sqler` & `sqler.sqler.sqler`.

**Done when:** recursive operations behave; no cycles (documented as unsupported for now).

---

### M5 — Relationship Joins (Phase 2: Query)
**Goal:** First‑class queries across relations.

- **Detection:** When a field path crosses a SQLerModel relationship (e.g., `User.address.city == "Kyoto"`), compile JOIN(s) instead of a plain JSON path.
- **SQL plan:**
  - Root alias `u` for `users`; join `addresses a` on `json_extract(u.data,'$.address._id') = a._id`.
  - WHERE uses `json_extract(a.data,'$.city')`.
- **Alias mgmt:** auto‑generated aliases per join step; support 1‑level first, then multi‑level.
- **Array‑of‑object joins:** Keep `json_each` join pattern (already used by `.any()`), allow combining with relationship joins.
- **Tests:** OR/AND/NOT precedence with joined fields; multi‑hop join; join + `.any()`; `EXPLAIN QUERY PLAN` smoke.

**Done when:** complex joined filters behave and stay paramized.

---

### M6 — Docs, CI, Packaging
**Docs**
- README quickstart (sync + async), model layer, safe model, indexes, arrays with `json_each`, relationships save/load, and joined queries.
- API reference via docstrings (Google style); examples folder.

**CI**
- Python 3.12; OS matrix linux/macos/windows.
- `uv run -q ruff check .` + `pytest -q`.
- (Optional later) `ty` if stable; no mypy for now.

**Packaging**
- pyproject configured for `sqler`; `uv build`; Twine publish.
- Versioning: SemVer; changelog.

---

## ⚙️ Technical Notes & Constraints
- **SQLite JSON1 required** (most modern builds have it). Document minimum SQLite version; features like `json_each` required for array ops.
- **PRAGMAs**: on‑disk → WAL + busy_timeout + NORMAL sync; in‑memory tuned for speed. Expose optional `pragmas=` in adapter factories for power users.
- **Security**: all predicates parameterized; only table/column identifiers are interpolated (from trusted model metadata).
- **Operator precedence**: Python’s `&`/`|`/`~` precedence is handled by explicit parentheses inside `SQLerExpression`; tests cover tricky cases.

---

## 🔮 Backlog (post‑v1 niceties)
- Mid‑chain `.any(predicate)` syntax for arrays of objects: `items.any(lambda it: it["k"] > 10 & it["t"]=="x")` → compiler transforms to nested `EXISTS`+`json_each`.
- `.values()` / `.values_list()` extractors.
- FTS5 integration for text search.
- Transaction helpers (`with db.transaction(): …`).
- Connection pooling for high‑concurrency async.
- Partial document updates (`json_set`) helpers.
- Schema migrations / constraints DSL.

---

## ✅ Acceptance Snapshot
- **v0.3**: Model layer + index sugar + docs/examples.
- **v0.4**: Safe model with optimistic locking.
- **v0.5**: Async parity.
- **v0.6**: Relationship save/load/refresh.
- **v0.7**: Relationship joins in queries.
- **v1.0**: Docs polished, CI green, public API frozen.

