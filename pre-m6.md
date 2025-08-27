are we ready to move onto m6? -- Short answer: almost. We knocked out hydration + cycles, async batch parity, model-aware fields, and debug helpers. The one pre-M6 item still outstanding from the checklist is **delete & integrity policies** (`restrict | set_null | cascade`) + a **validate_references()** utility. I strongly recommend we land that first (it’s small, self-contained), then roll straight into M6 docs.

Here’s the tight plan to finish M5 and then start M6 immediately:

# Finish M5 (final blocker)

## Delete & integrity policies

- **API**

  - `ReferentialIntegrityError(Exception)`
  - `SQLerModel.delete(*, on_delete: Literal["restrict","set_null","cascade"]="restrict")`
  - `SQLerModel.validate_references() -> list[BrokenRef]` where `BrokenRef` holds `(table, row_id, path, target_table, target_id)`

- **Behavior**

  - `restrict`: if any row in any registered table references this row (single ref or in a list), raise `ReferentialIntegrityError`.
  - `set_null`: locate all references and replace them with `None` (for lists, remove the matching element or set to `None`—document which we choose; I suggest **set to None** for stability), then upsert referrers.
  - `cascade`: delete all referrers (respecting their own `on_delete`), with a visited set to avoid cycles.

- **Implementation sketch**

  - Use the model registry you added to enumerate bound tables.
  - Fast prefilter: `WHERE data LIKE '%"_table":"<target_table>"%' AND data LIKE '%"_id":<id>%'`.
  - Python-validate by loading JSON and walking it to confirm true refs and collect JSON paths; return those paths from `validate_references()`.
  - Apply chosen policy; keep a `visited={(table,id)}` set for cascade.

- **Tests** (`tests/sync/test_delete_integrity.py`)

  - `test_restrict_blocks_when_referenced()`
  - `test_set_null_clears_single_and_list_refs()`
  - `test_cascade_deletes_referrers_and_avoids_cycles()`

Once that’s green, we’re officially M6-ready.

---

# M6 — Docs & DX polish (go next)

## 1) README overhaul (single, thorough doc)

- **Top badges:** PyPI, CI, Ruff, license.
- **Zero-to-SQLer (60s):** install + minimal example (sync) + async snippet.
- **Model layer:** table-per-model, default table naming, `set_db`, `_id` private attr.
- **Querying:** fields, comparisons, `& | ~`, nesting, `.any()` arrays, `contains/isin/like`, order/limit, `.debug()/.explain_query_plan()`.
- **Relationships:**

  - Saving refs with `as_ref()` (and arrays of refs).
  - Filtering via `SQLerModel.ref("address").field("city") == "Kyoto"` and via `SQLerModelField`.
  - Hydration: default on, `.resolve(False)` to skip; batch behavior; cycles note.

- **Safe models:** optimistic locking, version bumps, stale update error; when to use.
- **Async parity:** quickstart for `AsyncSQLiteAdapter`, `AsyncSQLerDB`, `AsyncSQLerModel`, async queryset.
- **Indexes & perf:** `ensure_index("address._id")`, JSON path indexes, `EXPLAIN QUERY PLAN` demo.
- **Debugging:** `.debug()`, `.explain()`, `.explain_query_plan()`.
- **Limitations & roadmap:** mid-chain scoped filters (xfail), future joins, migrations.
- **Testing:** `uv run pytest -q`; Ruff pre-commit.
- **Versioning:** SemVer; Python 3.12+; Pydantic v2.

## 2) Examples folder (runnable)

- `examples/01_quickstart_sync.py`
- `examples/02_queries.py` (arrays/any/contains/isin)
- `examples/03_relationships.py` (save refs, filter, hydration)
- `examples/04_safe_models.py`
- `examples/05_async_quickstart.py`
- `examples/06_indexes_and_explain.py`

## 3) Docstrings/API polish

- Ensure public classes/methods have crisp docstrings (models, query, field, model-aware field, debug helpers).
- Keep examples short and copy-pastable.

## 4) CI tweaks (docs & checks)

- Add a README link-check job (optional).
- Keep Ruff + pytest matrix as is.
- Add an examples smoke job (run a couple of scripts).

---

## What I’d tell Codex to do next (you can paste this)

1. Implement delete/integrity policies + `validate_references()` per spec above and add the three new tests.
2. When tests pass, generate/expand README sections listed in M6, plus the `examples/` scripts.
3. Add `.resolve(False)` mention and explain/debug sections to README; include a tiny `EXPLAIN QUERY PLAN` output example.
4. Optional: add a CI job that runs one example script.

If you’re good with that, we can call M5 closed after the delete policies, and move straight into M6 docs.
