# C ↔ Python stats comparison

## Python export

```powershell
python scripts/c_compare/export_python_stats.py --until-births 1 -o python_stats.json
```

## C metrics patch

Apply [`tierra_stats_patch.diff`](tierra_stats_patch.diff) to a **working copy** of Tierra C (do not treat patched sources as the pristine `legacy/` mirror). Rebuild, run with the same soup_in parameters (SoupSize=6000, seed=42, mut=0, single `0080aaa`), and emit `c_stats.json` in the same schema as the Python exporter:

```json
{
  "seed": 42,
  "first_birth_InstExe": 915,
  "final": {"NumCells": 2, "InstExe": 915, "births": 1, "deaths": 0},
  "size_histogram": {"80": 2},
  "timeline": [{"InstExe": 1000, "births": 1, "deaths": 0, "NumCells": 2}]
}
```

The patch adds a small JSON dump helper; adjust line numbers if your tree differs.

## Compare

```powershell
python scripts/c_compare/compare_stats.py python_stats.json c_stats.json
```

Tolerances default to ±5% on first-birth InstExe, births/deaths/NumCells, and max size-histogram share difference.
