# VM Developer Agent Profile

Implements the Python Tierra-VM.

## Scope

- `pytierra/**`
- `tests/**`
- `examples/**`
- project docs / `.cursor` rules when asked

## Rules

1. Read `AGENTS.md` and relevant rules before coding.
2. Keep `legacy/` C mirror read-only unless explicitly asked.
3. Add/update pytest coverage for behavior changes.
4. Run `pytest tests -q` (and `ruff check` when available).
5. No Alembic/DB steps.
