# Style Guide

This guide keeps the codebase human‑readable, consistent, and a little bit fun.

Our tone is **informal but precise**. Comments read like quick notes to a teammate; code favours clarity over clever tricks.

---

## 🐍 Python Style

### ✍️ Docstrings

- **Google‑style docstrings** on all public functions & classes.
- Private helpers can rely on a single comment above the def.

### 💬 Comments

- Lower‑case; casual; semicolons; no final periods unless a full sentence.

  ```python
  # start the websocket; serve frontend on /
  # fallback to default port; configurable later
  ```

### 🔤 Naming

- No abbreviations.

  - ✅ `log_path`, `websocket_manager`, `default_encoding`
  - ❌ `lp`, `ws_mgr`, `def_enc`

- `snake_case` for everything except `PascalCase` for classes.

### ⚙️ Tooling

- Auto‑format with **ruff format** + lint with **ruff**.
- Type‑hint everything;
- This project is uv managed so always run `uv run pytest` to test, and `uv add xxx` or `uv pip install xxx` for new dependencies.

---

## 🔄 Cross‑language Rules

### ✅ Always

- Commit small, self‑contained changes.
- Write **clear tests first**, then code.
- Leave TODOs with date if helpful
- Keep public APIs stable; breakage requires semver bump.

### 🚫 Never

- Use one‑letter identifiers (except tiny lambda params).
- Hide side‑effects; be explicit.
- Check in generated artefacts (except wheel distributions in releases).

---

## 🧪 Testing Guidelines

- Python → `pytest` (run with `uv run pytest`) ; 90 % line coverage gate.
- React → `vitest` + **Playwright** for e2e.
- Mirror source tree in `tests/` or `__tests__/` folders.

* **Python tests:**
  - Write `pytest` tests for all Python and FFI-facing logic.
  - Use temp files/fixtures as needed; prefer `pytest` fixtures for setup/teardown.
* **CLI and FastAPI endpoints:**
  - Test using `pytest` and `httpx` (REST) or `websockets` (WS endpoints).
  - Test CLI via Typer's test runner or subprocess.
* **Code Coverage:**
  - Python: Aim for >90% coverage, enforce in CI.
* **Workflow:** 3. `uv run pytest` (Python/FFI/integration)

---

## 🔐 Commit & PR Hygiene

- Conventional Commits (`feat:`, `fix:`, `docs:` …) enable semantic‑release.
- Pull Requests must pass **CI**, include tests, and mention roadmap item.

> **mantra:** _let clarity win._
