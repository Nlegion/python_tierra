#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

py() { python3 -m "$@"; }

echo "==> ruff"
py ruff check pytierra tests examples

echo "==> bandit"
py bandit -r pytierra -q -c pyproject.toml

echo "==> vulture"
py vulture pytierra tests examples .vulture_whitelist.py --min-confidence 80

echo "==> pytest+cov"
py pytest tests -q --cov=pytierra --cov-fail-under=85

echo "All quality gates passed."
