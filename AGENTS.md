# AGENTS — python_tierra

## Mission

Python reimplementation of the **Tierra Artificial Life Simulator v6.02** core VM
(`pytierra`), with the original C sources kept as a read-only reference under
`legacy/`.

## Layout

| Path | Role |
|------|------|
| `pytierra/` | Layered Python Tierra-VM (`bootstrap` / `services` / `models` / `adapters` / `core`) |
| `docs/architecture.md` | Layer rules and dependency direction |
| `tests/` | pytest suite |
| `examples/` | CLI demos |
| `legacy/` | Pristine Tierra C mirror and related trees (reference only) |
| `scripts/` | Quality-gate helpers |
| `.cursor/rules/` | Project agent rules |

Tech debt: no Protocol ports for filesystem loaders yet (loading stays in `bootstrap`).

## Quality gates (mandatory)

Before declaring work done, run:

```powershell
.\scripts\quality_gates.ps1
```

Equivalent commands:

```powershell
ruff check pytierra tests examples
bandit -r pytierra -q -c pyproject.toml
vulture pytierra tests examples .vulture_whitelist.py --min-confidence 80
pytest tests -q --cov=pytierra --cov-fail-under=85
```

No Alembic/DB. No shell/network side effects inside the VM.
Logging only on API/loaders; hot path uses TraceBuffer.

## License

Derivative work of Tierra Simulator by Thomas S. Ray / Virtual Life.
See `legacy/tierra/license.h` and `README.md`. Document modifications clearly.
Do not misrepresent this as the original software.

## Multi-agent notes

- Scope for implementers: `pytierra/**`, `tests/**`, `examples/**`, project docs/rules.
- Treat `legacy/**` as read-only unless the user explicitly asks to change it.
- `frontend-dev` is inactive for MVP (no UI).
