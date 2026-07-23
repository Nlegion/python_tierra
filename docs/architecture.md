# Architecture

Layered layout inside `pytierra/` (inspired by scriptoservitor, adapted for a library VM).

## Layers

| Layer | Path | Responsibility |
|-------|------|----------------|
| Façade | `pytierra/__init__.py` | Public exports (`TierraVM`, errors) |
| Bootstrap | `pytierra/bootstrap/` | Composition root only (`build_vm_from_config`) |
| Services | `pytierra/services/` | VM orchestration (`services.vm`) and ISA domain logic (`services.isa`) |
| Models | `pytierra/models/` | Simulation entities and helpers (`Cell`, `OpcodeMap`, `SandboxLimits`, `InstState`, …) |
| Adapters | `pytierra/adapters/` | Peripheral I/O (filesystem loaders for soup_in / `.tie` / opcode.map) |
| Core | `pytierra/core/` | Errors, settings/constants, logging setup |

## Dependency direction

```text
examples/tests → __init__ / services.vm
bootstrap → services + adapters + models
services → models + core
adapters → models + core.errors
```

- `bootstrap` may know concrete adapters (composition root).
- `services` must not import `adapters` (assets arrive preloaded via bootstrap).
- `services.isa` and the slicer hot path must not use `logging` (TraceBuffer only).
- `services.isa` = instruction domain logic; `services.vm` = lifecycle/orchestration.

## Tech debt

- Protocol ports exist for genebank/observer/net (`models/ports.py`); filesystem
  `GenomeLoader` / `ConfigLoader` ports still deferred until a second backend appears.
- Segment mutation ops: [`mutate_segment.py`](../pytierra/services/mutate_segment.py); see [`segment_mutations_subplan.md`](segment_mutations_subplan.md).

## Known limitations

- Unknown `soup_in` keys (Beagle/Net/UI, etc.) are ignored with a WARNING — not an error.
- Beagle/NET/disk genebank: in-process ports only (see `models/ports.py`, `docs/known_limitations.md`); no TCP/sockets in VM.
- Multi-inoculum: if a cell cannot be placed (`SoupSize` too small) → `ConfigError` at `start()`.
- ISA hot path does not use Python `logging` (TraceBuffer only).
- mut=0 is the acceptance path; mut>0 is evolution mode (CI uses high `GenPer*` for determinism).
- C behavioral compare: see [`scripts/c_compare/README.md`](../scripts/c_compare/README.md) (±5% metrics).
- Before optimizing hot paths, run `python scripts/verify_optimization.py` against the golden.
