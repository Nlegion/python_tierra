# Visualization

Research plots sit **outside** the ISA hot path. Collect with `MetricsRecorder`,
then plot in examples (optional `[viz]` deps).

## Install

```powershell
pip install -e ".[dev,viz]"
```

## Minimal collect + plot

```python
from pytierra import TierraVM
from pytierra.services.metrics import MetricsRecorder

vm = TierraVM.from_config(..., asset_root="legacy/tierra")
rec = MetricsRecorder(sample_every=100)
vm.attach_recorder(rec)
vm.start()
vm.run(until_births=2)

# samples: InstExe, NumCells, births, deaths, ...
# events: birth/death dicts (lightweight append only)
print(len(rec.samples), len(rec.events))
```

## Examples

Scripts live under `examples/`; generated images go to `viz/` (gitignored).

| Script | Output |
|--------|--------|
| `examples/viz_full_run.py` | all four under `viz/` (evolution-scale, mut>0) |
| `examples/viz_population.py` | `viz/viz_population.png` (short smoke) |
| `examples/viz_phylogeny.py` | `viz/viz_phylogeny.png` |
| `examples/viz_soup_heatmap.py` | `viz/viz_soup_heatmap.png` |
| `examples/viz_petri.py` | `viz/viz_petri.gif` (or `.png`) |

Full research pass (recommended):

```powershell
py -3 examples\viz_full_run.py
```

`viz_full_run` uses `vm.run(until_births=…)` for an exact birth stop, then builds
population/heatmap/phylo from `MetricsRecorder` + final state. The Petri GIF is a
**short post-run** animation (not `step(1)` across the whole horizon)—mid-run cell
density is not reconstructed. Trade-off: accurate `until_births` / pop curve vs
cheap Petri.

Detailed write-up: [`docs/full_run_results.md`](full_run_results.md)
(`viz/full_run_analysis.json`).

### Petri projection (`_xy`)

Address `mm_p` maps to a **spiral** (not fixed radius):

```text
θ = 2π * mm_p / SoupSize
r = 0.3 + 0.7 * (mm_p / SoupSize)
x, y = r·cos(θ), r·sin(θ)
```

Marker color = genotype name. Empty phylogeny with a single genotype / TotMut=0 is
expected, not a plot bug.

Phylogeny graphs can grow quickly; pass `max_edges` (default 200–500) and prefer
last-N births. Do not build NetworkX graphs inside recorder handlers.

## Architecture

- Recorder hooks: `_notify_birth` / `_notify_death` + sample after `step`/`run`.
- No sockets; matplotlib runs in the example process only.
- Missing viz packages → `SystemExit('pip install -e ".[viz]"')`.
