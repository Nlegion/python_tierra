# TierraVM API

Public entry: `from pytierra import TierraVM` (errors from `pytierra.core.errors` / package root).

## Construction

```python
from pytierra import TierraVM
from pytierra.models.limits import SandboxLimits

vm = TierraVM.from_config(
    {"SoupSize": 6000, "NumCells": 1, "seed": 42, "GenebankPath": "gb0/",
     "IMapFile": "opcode.map", "place_center": True, "inoculum": ["0080aaa"]},
    asset_root="legacy/tierra",
    limits=SandboxLimits(max_instructions=200_000, wall_time_s=60),
)
```

Or construct with a preloaded `OpcodeMap` + `TierraConfig` (tests).

## Lifecycle

| Method | Role |
|--------|------|
| `start()` | Reset soup, RNG, inoculate, begin run clock |
| `step(n=1)` | Execute up to `n` instructions via slicer |
| `run(max_instructions=None, until_births=None)` | Loop until stop / budget / births |
| `stop()` | Cooperative stop flag |
| `set_limits(**kwargs)` | Update `SandboxLimits` fields; clears stopped |
| `stats()` | Dict: NumCells, InstExe, births, deaths, free_mem, … |
| `snapshot()` / `restore(snap)` | Deterministic state dump/load |

## Limits and errors

- Host budgets `max_instructions` / `wall_time_s` → `SandboxLimitError` (state remains valid; use `set_limits` then continue).
- Create-time `SoupSize > max_soup_size` → `SandboxLimitError`.
- `max_cells` soft-fail: birth/`alloc_cell` returns `None` / `fl.E`; **no** raise.
- Bad config / inoculum OOM → `ConfigError`; missing assets → `AssetError`; API misuse → `StateError`.

Wall-time checks run on `step`/`run` force checks and every `limit_check_every` instructions — not necessarily every single instruction.

## Trace

Ring buffer (`DEFAULT_TRACE_CAPACITY`). Disabled by default.

```python
vm.enable_trace(True)
vm.run(until_births=1)
for r in vm.get_trace()[-5:]:
    print(r["cycle"], r["cell_id"], r["mnemonic"], r["ip"])
```

Each record (dict): `cycle`, `cell_id`, `ip`, `opcode`, `mnemonic`, `operands`, `result`, `err`.
When the buffer is full, oldest records are dropped.

## Mutations

- `GenPer*=0` (default in acceptance tests): classic `0080aaa` self-replication.
- `GenPer*>0`: evolution mode (point mutations + optional segment cro/ins/del via
  `GeneticOps` on divide when the corresponding `GenPer*Seg` / `GenPer*Ins` rates
  are non-zero).

### GenPer* vs Rate* (CalcFlawRates)

`GenPerBkgMut` / `GenPerMovMut` / `GenPerFlaw` are **not** “mutations per N bytes”.
They feed C-compatible `CalcFlawRates` ([`flaw_rates.py`](../pytierra/services/vm/flaw_rates.py)),
which derives instruction / copy / flaw thresholds:

| Derived | Bootstrap formula (`InstExe` million-counter unused in MVP) |
|---------|---------------------------------------------------------------|
| `rate_mov_mut` | `2 * GenPerMovMut * AverageSize * PLOIDY` |
| `rate_mut` | `int(pop_gen_time * 2 * GenPerBkgMut * AverageSize/SoupSize)` with `RepInst=10*AverageSize`, `pop_gen_time=RepInst*(SoupSize//(4*AverageSize))` |
| `rate_flaw` | `RepInst * GenPerFlaw * 2` (applied via `ctx.flaw()` in decode/ISA) |

Example: `SoupSize=12000`, `AverageSize=80`, `GenPerBkgMut=512` → `rate_mut=202069`
(not 512). Cosmic events land about every `rate_mut/2` instructions on average
(after the first threshold hit). Rates recompute when `AverageSize` changes
(`update_average_size`), on `start`, and when `set_parameter` changes a `GenPer*` key.
`TotMut` / `TotMovMut` count `mut_site` applications (same as C), not RNG probes.

Segment knobs (`GenPerCroSeg`, `GenPerInsSeg`, `GenPerDelSeg`, `GenPerCroIns`, …)
are **not** passed through `CalcFlawRates`; they are raw divide-time thresholds in
`mutate_segment.py` (see [`segment_mutations_subplan.md`](segment_mutations_subplan.md)).

### SearchLimit

`SearchLimit` is a float multiplier. Template search distance in **soup bytes**
(instructions) is `slim = int(SearchLimit * AverageSize)`, floored up to
`AbsSearchLimit` when that is > 0. Search walks from the IP forward/backward
(`ctemplate`) and stops when `dist > slim`. After mutations scramble NOP templates,
a small `slim` makes complement finds fail more often.

### SavThrMem / SavThrPop vs reaper

`SavThrMem` / `SavThrPop` control **genebank / DiskBank extract** thresholds only.
They do **not** trigger the reaper. Reaper runs on failed `mal` allocation via
`reap_one` (gated by `NumCellsMin`). See `stats()["reap_attempts"]` /
`stats()["mal_fail"]`.

## Genebank API

Enable with `GeneBnker=1`. Optional disk persist: `DiskBank=1`, `DiskBankFormat=ascii`,
`DiskBankBackend=json` (sqlite reserved).

| Method | Role |
|--------|------|
| `genotypes()` | List `{name,size,label,hash,pop,permanent,parent}` |
| `save_genotype(name)` | Force permanent + write `.tie` via deferred queue |
| `inject(name, n=1)` | Place copies from preload / DiskBank / RamBanker |

Snapshot includes `banker_version` and permanent genome bytes only.

## Metrics / visualization

```python
from pytierra.services.metrics import MetricsRecorder
rec = MetricsRecorder(sample_every=100)
vm.attach_recorder(rec)
```

See [`visualization.md`](visualization.md).

## Observer / Control API (in-process Beagle)

| Method | Role |
|--------|------|
| `plan()` / `overview()` / `histogram(kind)` | Plan, cell spans, size/gene/mem hist |
| `genome_at(addr)` / `genome_of(name)` | Genome bytes |
| `cell_snapshot(id)` | CPU/Dem dump |
| `get_parameter` / `set_parameter` | Whitelist: `SliceSize`, `GenPer*`, `GenPerFlaw`, `NumCellsMin`, `MalTol`, `MovPropThrDiv`, `MutBitProp`, `SearchLimit` |
| `step_until(pred, max_instructions=None, wall_time=None)` | Loop with VM limits as default caps |

## NET port (tests / host wiring)

Not exported as a primary public façade. Attach `InMemoryTransport` via
`attach_transport`, then `emigrate(cell_id, dest=...)` / `poll_immigrants()`.
See [`net_port.md`](net_port.md). No sockets inside the VM.

See also [`architecture.md`](architecture.md), [`known_limitations.md`](known_limitations.md).
