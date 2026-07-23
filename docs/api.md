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
- `GenPer*>0`: evolution mode (point mutations). Segment cro/ins/del are stubs until Phase 2b.

See also [`architecture.md`](architecture.md) Known limitations.
