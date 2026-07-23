$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

function Invoke-PyMod {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$ModArgs)
    & py -3 -m @ModArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "==> ruff"
Invoke-PyMod ruff check pytierra tests examples

Write-Host "==> bandit"
Invoke-PyMod bandit -r pytierra -q -c pyproject.toml

Write-Host "==> vulture"
Invoke-PyMod vulture pytierra tests examples .vulture_whitelist.py --min-confidence 80

Write-Host "==> pytest+cov"
Invoke-PyMod pytest tests -q --cov=pytierra --cov-fail-under=85

Write-Host "All quality gates passed."
