Codex crushed it. We’re in great shape to close out relationships before rolling into M6. Here’s the tight, do-first list with concrete acceptance criteria and test targets so you can hand it straight to Codex.

# 🔒 Finish M5 (relationships) before M6

## A) Delete & integrity policies (ship-blocker)

**API**

- `SQLerModel.delete(*, on_delete: Literal["restrict","set_null","cascade"]="restrict") -> None`
- `SQLerModel.validate_references() -> list[BrokenRef]` (where `BrokenRef = dataclass(table:str, row_id:int, path:str, target_table:str, target_id:int)`)

**Behavior**

- **restrict**: if any other row (any model bound to the same DB) references this row (single ref or in a list), raise `ReferentialIntegrityError`.
- **set_null**: recursively traverse JSON of referrers; replace matching ref (or element in list) with `None`; upsert those rows.
- **cascade**: delete referrers (respecting their own `on_delete`—default to “restrict” unless caller passes “cascade” explicitly). Guard cycles.

**Implementation (pragmatic v1)**

- Use a DB-wide model registry you already have to enumerate tables.
- Find candidate referrers per table cheaply:

  - SQL prefilter: `WHERE data LIKE '%"_table":"<target>"%' AND data LIKE '%"_id":<id>%'`
  - Then Python-validate by loading JSON and walking the structure to confirm true matches and collect JSON paths.

- For `set_null`: modify in Python (walk and set `None`), then `upsert`.
- For `cascade`: delete those rows; maintain a visited set `{(table,id)}` to avoid cycles.

**Tests** (`tests/sync/test_delete_integrity.py`)

- `test_restrict_blocks_when_referenced()`
- `test_set_null_clears_single_ref_and_list_refs()`
- `test_cascade_deletes_referrers_and_avoids_cycles()`

## B) Cycle guards & deep hydration (ship-blocker)

- Hydration already batches; add a `visited: set[tuple[str,int]]` across the whole result hydration pass to prevent infinite recursion in cyclic graphs (A→B→A).
- Test with two models that reference each other; `.all()` does not recurse forever and returns hydrated once.

**Tests**

- `test_hydration_handles_cycle_once()` – hydrated objects contain single-level related instance (or a lightweight ref after first hop), no recursion.

## C) Async parity for batch hydration (ship-blocker)

- Mirror the batch resolver you added for sync into `AsyncSQLerQuerySet` with `await`ed batched fetches per table.
- Ensure `.resolve(False)` behaves identically to sync.

**Tests** (`tests/async/test_async_batch_hydration.py`)

- Same scenario as sync: 200 users → 3 addresses, assert a single `SELECT … WHERE _id IN (…)` per table (you can spy adapter calls).

## D) Debug helpers (nice-to-have, quick)

- `SQLerQuery.debug() -> tuple[str, list[Any]]` (returns current SQL & params).
- `SQLerQuery.explain(adapter) -> list[tuple]` and `explain_query_plan(adapter) -> list[tuple]]` that run:

  - `EXPLAIN <sql>` and `EXPLAIN QUERY PLAN <sql>` with the same params.

- Add passthroughs on `SQLerQuerySet` (sync & async):

  - `.debug()`, `.explain(adapter)`, `.explain_query_plan(adapter)` (async versions `await qs.explain(...)`).

**Tests** (`tests/sync/test_query_debug_explain.py`)

- `test_debug_returns_sql_and_params()`
- `test_explain_query_plan_runs_and_returns_rows()` (smoke)

## E) README additions (relationships section)

- **Saving refs**: `user.address = as_ref(addr)`; lists of refs; saving models vs saving refs; `save_deep()` (if we add it later).
- **Filtering**: `MF(User, ["address","city"]) == "Kyoto"` and `User.ref("address").field("city") == "Kyoto"`.
- **Hydration**: default on, `.resolve(False)` to skip; batch behavior; cycles note.
- **Indexes**: `ensure_index("address._id")`, `ensure_index("orders._id")`; show `qs.explain_query_plan()` diff.
- **Safe model nuance**: parent saves don’t bump child versions; update child with its own `save()` (or document `save_deep()` plan if you want it).

---

## Hand-off to Codex (drop-in spec)

1. **Delete policies**

- Add `ReferentialIntegrityError`.
- Implement `SQLerModel.delete(on_delete=...)` per rules above.
- Add `SQLerModel.validate_references()` scanning all bound tables using LIKE prefilter + Python validation.

2. **Cycle guards**

- In both sync/async hydration: maintain a `visited` set to prevent repeat hydration of the same `(table,_id)` within one materialization pass.

3. **Async batch parity**

- Port sync batch resolver to async; add tests that assert batched IN queries instead of N+1.

4. **Debug helpers**

- Implement `.debug()`, `.explain()`, `.explain_query_plan()` on `SQLerQuery` (+ wrapper on QuerySet; async variants).

5. **Tests**

- Add the 4 files outlined above; keep counts/adapter-invocation assertions to prove batching and explain usage.

Once those are green, we’re truly M6-ready. After that, I’d line up:

- **M6 Docs/Examples** (full README reorg + cookbook)
- **M7 CLI** (`sqler init`, `sqler inspect`, `sqler explain <query>` for quick introspection)
- **M8 Perf** (optional): JSON indices guidance, covering indexes demo, and a small benchmark script.

Want me to draft the test skeletons verbatim so Codex can fill in implementation, or is this enough direction?
