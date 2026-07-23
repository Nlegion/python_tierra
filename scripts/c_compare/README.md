# C ↔ Python stats comparison

Tolerances (see `compare_stats.py`):

| Relative difference | Result |
|---------------------|--------|
| ≤ 5% | OK |
| > 5% and ≤ 10% | WARN (exit 0) |
| > 10% | FAIL (exit 1) |

Metrics: `first_birth_InstExe`, births/deaths/NumCells, `unique_genotypes` (when present), size-histogram share.

## Exact vs coarse sampling

- **`first_birth_InstExe`** is measured with `vm.step(1)` until the first birth
  (same acceptance config / seed as `tests/test_golden_first_birth.py`).
  Expected golden: **827** (`GOLDEN_FIRST_BIRTH_INST_EXE` in `acceptance.py`;
  exact birth instruction with per-insn `until_births` stop).
- **Timeline** after the first birth may use coarse `--sample-every` (default 1000)
  when `--extra-steps` or `--until-births > 1` is set. The first coarse point may
  coincide with the exact birth InstExe; that is harmless.

A hard budget (`max_instructions`) aborts if no birth occurs.

## Python export

```powershell
python scripts/c_compare/export_python_stats.py --until-births 1 -o python_stats.json
```

Shared config: [`acceptance.py`](acceptance.py).

## Optional C patch

Apply [`dump_stats_json.diff`](dump_stats_json.diff) (or [`tierra_stats_patch.diff`](tierra_stats_patch.diff))
to a **working copy** of Tierra C — not the pristine `legacy/` mirror.

## Compare

```powershell
python scripts/c_compare/compare_stats.py python_stats.json c_stats.json
```

## Wall-clock benchmark

```powershell
python scripts/c_compare/bench_wall.py --until-births 80 --out viz/bench_wall.json
```

- Always runs **Python** (`acceptance` config unless `--soup-in PATH`).
- **C is optional**: omit `--c-bin` → JSON field `c_skipped` (exit 0).
- With C:

```powershell
# 1) Copy Tierra sources to a working tree (do NOT patch pristine legacy/)
# 2) Apply dump_stats_json.diff (or tierra_stats_patch.diff)
# 3) Build the binary
# 4) Bench:
python scripts/c_compare/bench_wall.py --until-births 80 `
  --soup-in path\to\soup_in `
  --c-bin path\to\tierra.exe `
  --c-workdir path\to\run_dir `
  --c-extra-arg ...
```

`--soup-in` is copied to `--c-workdir/soup_in` before spawn. Tierra is expected to
read `soup_in` from the working directory (classic layout).
