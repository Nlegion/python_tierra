---
name: run-tests
description: Run full Tierra-VM quality gates (ruff, bandit, vulture, pytest-cov)
---

# Run Quality Gates

From repository root, prefer:

```powershell
.\scripts\quality_gates.ps1
```

```bash
./scripts/quality_gates.sh
```

Or manually:

```powershell
ruff check pytierra tests examples
bandit -r pytierra -q -c pyproject.toml
vulture pytierra tests examples .vulture_whitelist.py --min-confidence 80
pytest tests -q --cov=pytierra --cov-fail-under=85
```

## Report

- commands run
- pass/fail summary
- failed tests / tool findings + likely cause
- next fix step
