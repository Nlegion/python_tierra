# Python Tierra-VM

**Status: experimental** — Python reimplementation of the **core VM** of
[Tierra](https://en.wikipedia.org/wiki/Tierra_(computer_simulation)) Artificial
Life Simulator **v6.02** (Thomas S. Ray / Virtual Life).

This is a **sandbox library** (`TierraVM`), not a full drop-in of the original
C application. Original sources live under [`legacy/`](legacy/) as a read-only
reference (see [`legacy/tierra/license.h`](legacy/tierra/license.h)).

Active code: [`pytierra/`](pytierra/). Latest successful research run and plots:
[`viz/`](viz/) · write-up [`docs/full_run_results.md`](docs/full_run_results.md).

## What works

| Capability | Notes |
|------------|--------|
| Soup + MemFr allocator | Fixed-size `bytearray`, dual free-list |
| Cells, slicer, reaper | Round-robin slices; reaper on failed `mal` + `NumCellsMin` |
| gb0 ISA | Decode/execute, templates, `mal` / `movii` / `divide` |
| Tierra RNG | `tsrand` / `tdrand` / `tlrand` / … + snapshot |
| Point mutations | Background, move, divide via `GenPer*` → `CalcFlawRates` |
| Segment mutations (cro/ins/del) | Ported in `mutate_segment.py`; rates default **0** (off) |
| Genebank | `RamBanker` + ASCII `DiskBank` (`.tie` + `genebank_index.json`) |
| Observer / Control API | `plan`, `overview`, `histogram`, `set_parameter`, `step_until` |
| NET | `InMemoryTransport` between VMs in-process (no sockets in VM) |
| Inoculum | Load `.tie` + `opcode.map`; multi-inoculum supported |
| Classic ancestor | `0080aaa` self-replicates (mut=0); golden at seed 42 |
| Exact birth stop | `run(until_births=…)` stops without overshoot |
| Sandbox API | `start` / `step` / `run` / `stop` / `snapshot` / `restore` / limits / trace |

Acceptance check: `python scripts/verify_optimization.py` (after
`--write-golden` once).

### Scope vs original Tierra

| Area | Original C Tierra | This port |
|------|-------------------|-----------|
| Core VM (soup, CPU, replicate) | Yes | Yes |
| **Genebank** | Full DiskBank / GeneBnker | RamBanker + ASCII DiskBank (`.tie` + index); no C XDR `.gen` yet |
| **Beagle** (observer / GUI) | Yes (`Bgl*` in `legacy/`) | In-process Observer API (no TCP/GUI) |
| **NET** (migration) | Optional `#ifdef NET` | `InMemoryTransport` only |
| Segment mutations | Yes | Ported; default rates 0 |
| Frontend / screen / audio | Yes | No |

**Why these pieces matter:** Genebank lets you name and persist species; Observer is how a host app steers the VM without a Motif client; in-memory NET is enough to prototype migration; segment ops are ready when you want size-changing evolution.

## Full-run results

Artifacts from `py -3 examples\viz_full_run.py` (seed **42**, stop at
`until_births=80`). Raw numbers:
[`viz/full_run_analysis.json`](viz/full_run_analysis.json),
[`viz/full_run_config.json`](viz/full_run_config.json). Narrative:
[`docs/full_run_results.md`](docs/full_run_results.md).

| Metric | Value |
|--------|------:|
| InstExe | 99 891 |
| births / deaths / NumCells | 80 / 4 / 77 |
| free_mem | 54 |
| soup occupancy | 99.55% |
| mal_fail / reap_attempts | 276 / 4 |
| genebank genotypes | 10 |
| rate_mut / rate_mov_mut / rate_flaw | 6 314 / 2 560 / 0 |
| TotMut / TotMovMut | 26 / 6 |
| wall_time_s | ≈0.52 |

**Config highlights:** `SoupSize=12000`, inoculum `0080aaa`,
`GenPerBkgMut = GenPerMovMut = GenPerDivMut = 16`, segment `GenPer* = 0`,
`GeneBnker=1`.

Population grows by clonal expansion until the soup is nearly full; the reaper
fires **4** times near the end (`deaths=4`). With the same soup and
**`GenPer*=512`**, `rate_mut≈202 069` — almost no mutations on a ~1e5 InstExe
horizon (pure clones, empty phylogeny). `GenPer=16` was chosen for the published
plots so mutants and the genebank tree are visible.

## Visualizations

Regenerate everything under `viz/` (folder is gitignored; scripts rewrite it):

```powershell
pip install -e ".[dev,viz]"
py -3 examples\viz_full_run.py
```

### Population growth

![Population: NumCells, births, deaths vs InstExe](viz/viz_population.png)

**How to read:** X = instructions executed. Blue `NumCells` and orange
`births` climb together (successful replication). Green `deaths` stays at 0
until late soup pressure, then rises to 4 when the reaper reclaim memory.

### Soup occupancy heatmap

![Soup occupancy heatmap at end of run](viz/viz_soup_heatmap.png)

**How to read:** Linear soup addresses wrapped into a 2D grid. Bright bands =
allocated cell memory; dark = free. Dense bright stripes ≈ soup almost full
(here ~99.5% occupied).

### Petri dish animation

![Petri-style animation of cell layout in the soup](viz/viz_petri.gif)

**How to read:** Each marker is a live cell (color ≈ genotype), projected from
soup address onto a spiral. This GIF is a **short post-run** sample (not a
frame-per-instruction movie of the whole horizon)—use it to see spatial packing
after expansion.

### Phylogeny

![Phylogeny graph of genotypes from the full run](viz/viz_phylogeny.png)

**How to read:** Nodes are genotype labels (`0080aaa` = size 80, label `aaa`).
Arrows are parent → child from birth events. This run has **10 nodes / 10 edges**
(ancestor in the center, mutants `aab`…`aaj`). An **empty** graph is expected
when mutations are off or `GenPer` is very high (e.g. 512) so only clones exist.

More detail: [`docs/visualization.md`](docs/visualization.md).

## Layout

| Path | Role |
|------|------|
| [`pytierra/`](pytierra/) | Package: `bootstrap` / `services` / `models` / `adapters` / `core` |
| [`tests/`](tests/) | pytest (coverage ≥ 85%) |
| [`examples/`](examples/) | CLI demos and viz scripts |
| [`viz/`](viz/) | Generated plots / run JSON (regenerate locally) |
| [`legacy/`](legacy/) | Original Tierra C (reference only) |
| [`scripts/`](scripts/) | Quality gates, profiling, C-compare, golden check |
| [`docs/`](docs/) | Architecture, API, viz, limitations |
| [`AGENTS.md`](AGENTS.md) | Contributor / agent notes |

## Quick start

```powershell
pip install -e ".[dev]"
python examples/run_ancestor.py
```

Genebanks and opcode maps for demos/tests: `legacy/tierra/gb0/`.

### Minimal API sketch

```python
from pytierra import TierraVM
from pytierra.models.limits import SandboxLimits

vm = TierraVM.from_config(
    {
        "SoupSize": 6000,
        "NumCells": 1,
        "seed": 42,
        "GenebankPath": "gb0/",
        "IMapFile": "opcode.map",
        "place_center": True,
        "inoculum": ["0080aaa"],
    },
    asset_root="legacy/tierra",
    limits=SandboxLimits(max_instructions=200_000, wall_time_s=60),
)
vm.start()
vm.run(until_births=1)  # exact stop — no birth overshoot
print(vm.stats())
```

Observer peek (no GUI required):

```python
print(vm.plan())                 # soup / rates / counters summary
print(vm.histogram(kind="size")) # live size histogram
vm.set_parameter("GenPerBkgMut", 16)  # recalculates Rate* via CalcFlawRates
```

Full method list, errors, TraceBuffer: [`docs/api.md`](docs/api.md).

## Configuration notes

### `GenPer*` → rates (`CalcFlawRates`)

`GenPerBkgMut` / `GenPerMovMut` / `GenPerFlaw` are **not** “mutations every N
bytes”. They feed C-compatible [`CalcFlawRates`](pytierra/services/vm/flaw_rates.py),
which derives instruction thresholds `rate_mut`, `rate_mov_mut`, `rate_flaw`.

For `SoupSize=12000`, `AverageSize=80` (classic `0080aaa`):

| GenPerBkgMut (= Mov) | rate_mut | rate_mov_mut | Typical ~1e5 InstExe effect |
|---------------------:|---------:|-------------:|-----------------------------|
| 0 | 0 | 0 | Pure replication (acceptance / golden) |
| 16 | 6 314 | 2 560 | Visible mutants (published viz run) |
| 64 | 25 258 | 10 240 | Stronger point-mutation pressure |
| 512 | 202 069 | 81 920 | Effectively clonal on short horizons |

Segment knobs (`GenPerCroSeg`, `GenPerInsSeg`, `GenPerDelSeg`, …) are **raw**
divide-time thresholds — they do **not** go through `CalcFlawRates`. Keep them
`0` unless you intentionally want size-changing ops.

### Genebank thresholds vs reaper

| Knob | Controls |
|------|----------|
| `SavThrMem` / `SavThrPop` / `SavMinNum` | Genebank / DiskBank **extract** only |
| Failed `mal` + `NumCellsMin` | **Reaper** (`reap_one`) |

Raising `SavThr*` will not kill cells. Watch `stats()["reap_attempts"]` and
`stats()["mal_fail"]` for memory pressure.

## Examples

```powershell
python examples/run_ancestor.py         # mut=0 self-replication
python examples/run_evolution.py        # mut>0 diversity probe (slow)
python examples/run_evolution_bank.py   # GeneBnker + DiskBank (.tie under temp dir)
py -3 examples\viz_full_run.py          # report JSON + all plots → viz/
```

| Script | What you get |
|--------|----------------|
| `run_ancestor.py` | Fast “does it replicate?” check |
| `run_evolution.py` | Longer mut>0 soup |
| `run_evolution_bank.py` | Species list + `.tie` files on disk |
| `viz_full_run.py` | `viz/full_run_*.json` + population / heatmap / petri / phylogeny |
| `viz_population.py` / `viz_phylogeny.py` / … | Single-plot smokes |

Multi-inoculum: several names in `inoculum` / soup_in lines; `NumCells` cycles
the list. If soup cannot fit an inoculum cell → `ConfigError` at `start()`.

### Profiling and golden

```powershell
python scripts/profile_ancestor.py --scenario births1
python scripts/profile_ancestor.py --scenario births100
python scripts/profile_ancestor.py --scenario fragmentation

python scripts/verify_optimization.py --write-golden   # once
python scripts/verify_optimization.py                  # after hot-path changes
```

Optional C↔Python metrics compare: [`scripts/c_compare/README.md`](scripts/c_compare/README.md).

## Documentation

| Doc | Contents |
|-----|----------|
| [`docs/architecture.md`](docs/architecture.md) | Layers, dependency rules |
| [`docs/api.md`](docs/api.md) | `TierraVM` API, GenPer/rates, genebank, observer |
| [`docs/visualization.md`](docs/visualization.md) | MetricsRecorder + plot scripts |
| [`docs/full_run_results.md`](docs/full_run_results.md) | Latest full-run write-up |
| [`docs/known_limitations.md`](docs/known_limitations.md) | DiskBank, NET, CalcFlawRates, reaper gaps |
| [`docs/net_port.md`](docs/net_port.md) | In-memory migration notes |
| [`docs/segment_mutations_subplan.md`](docs/segment_mutations_subplan.md) | cro/ins/del design |

## Known limitations

- Unknown `soup_in` keys (Beagle/Net/UI, …) are ignored with a WARNING.
- No Motif/TCP Beagle client; no host sockets from inside the VM.
- DiskBank is ASCII `.tie` + JSON index only (no C XDR `.gen`; sqlite reserved).
- Not claimed bit-identical to C on long evolutionary runs; use c_compare for checks.
- ISA hot path uses TraceBuffer only (no per-instruction logging).

Details: [`docs/known_limitations.md`](docs/known_limitations.md),
[`docs/architecture.md`](docs/architecture.md).

## Quality gates

Before considering a change done:

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

## License notice

The original Tierra source, documentation, and process are under the Tierra
license (non-commercial distribution terms, attribution, document modifications).
`pytierra` is an **altered / derivative** reimplementation and must not be
misrepresented as the original software. See
[`legacy/tierra/license.h`](legacy/tierra/license.h).
