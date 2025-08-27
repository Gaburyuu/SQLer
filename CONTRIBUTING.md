# Contributing to SQLer

Thanks for helping make SQLer better! This guide keeps contributions smooth and predictable.

## Getting Started

- Fork and clone the repo
- Ensure Python 3.12+
- Install uv and sync deps

```bash
pipx install uv
uv sync --dev
```

## Running Tests

- Full test suite (sync + async):

```bash
uv run -q pytest -q
```

- With coverage (optional gate):

```bash
uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=90
```

## Linting & Formatting

- Ruff format and lint:

```bash
uv run ruff format .
uv run ruff check .
```

Fix any issues before opening a PR.

## Style & Design

- Read the project style guide: see `STYLE_GUIDE.md`.
- Prefer small, focused PRs with tests.
- Type-hint everything; keep docstrings concise with Google style.
- Follow existing naming patterns and module layout.

## Tests

- Mirror source tree under `tests/`.
- For async tests, use `pytest.mark.asyncio` and keep fixtures non-blocking.
- Add tests for new features and bug fixes (prefer unit tests first, then integration as needed).

## Commit Messages

- Conventional Commits are encouraged (e.g., `feat:`, `fix:`, `docs:`, `refactor:`).
- Reference issues where appropriate.

## Examples

- Keep runnable examples in `examples/` and prefer in-memory DBs.
- Examples should be fast and self-contained.

## CI

- The repo runs Ruff + Pytest and a small examples smoke job on GitHub Actions.
- Keep examples quick so CI stays snappy.

## Opening a PR

- Ensure tests pass locally.
- Include a brief description, rationale, and any screenshots or logs if helpful.
- If the change touches public APIs, update the README and/or docs.

Thanks again for contributing!
