# Python Tierra-VM

**Status: experimental MVP** — Python reimplementation of the **core VM** of
[Tierra](https://en.wikipedia.org/wiki/Tierra_(computer_simulation)) Artificial
Life Simulator **v6.02** (Thomas S. Ray / Virtual Life).

This is a **sandbox library** (`TierraVM`), not a full drop-in of the original
C application. Original sources live under [`legacy/`](legacy/) as a read-only
reference (see [`legacy/tierra/license.h`](legacy/tierra/license.h)).

Active code: [`pytierra/`](pytierra/). Architecture: [`docs/architecture.md`](docs/architecture.md).
API: [`docs/api.md`](docs/api.md).

## License notice

The original Tierra source, documentation, and process are under the Tierra
license (non-commercial distribution terms, attribution, document modifications).
`pytierra` is an **altered / derivative** reimplementation and must not be
misrepresented as the original software.

## What works (MVP core)

| Capability | Notes |
|------------|--------|
| Soup + MemFr allocator | Fixed-size `bytearray`, dual free-list |
| Cells, slicer, reaper | Round-robin slices; reaper under memory pressure |
| gb0 ISA | Decode/execute, templates, `mal` / `movii` / `divide` |
| Tierra RNG | `tsrand` / `tdrand` / `tlrand` / … + snapshot |
| Point mutations | Background, move, divide (`GenPer*`); segment cro/ins/del are **stubs** |
| Inoculum | Load `.tie` + `opcode.map` from a genebank path; multi-inoculum supported |
| Classic ancestor | `0080aaa` self-replicates (mut=0); golden at seed 42 |
| Sandbox API | `start` / `step` / `run` / `stop` / `snapshot` / `restore` / limits / trace |

Acceptance check: `python scripts/verify_optimization.py` (after
`--write-golden` once).

## Scope vs original Tierra

| Area | Original C Tierra | This port |
|------|-------------------|-----------|
| Core VM (soup, CPU, replicate) | Yes | Yes (MVP) |
| **Genebank** (disk bank of genotypes) | Full DiskBank / GeneBnker | **Read-only** load of inoculum from `gb0/` etc.; no auto-save of new genotypes |
| **Beagle** (observer / GUI client) | Yes (`Bgl*` trees in `legacy/`) | **No** — use `stats()` / `enable_trace` / snapshot |
| **NET** (multi-node migration) | Optional `#ifdef NET` | **No** — no sockets / host side-effects by design |
| Segment mutations (cro/ins/del) | Yes | Stubs only — see [`docs/segment_mutations_subplan.md`](docs/segment_mutations_subplan.md) |
| Frontend / screen / audio | Yes | No |
| Packaging | Native binary | Installable Python package + pytest |

### Genebank / Beagle / NET (glossary)

- **Genebank** — library of genomes (`.tie` files + `opcode.map`). Original Tierra
  can write new genotypes to disk as evolution proceeds. Here we only **read**
  assets (e.g. `legacy/tierra/gb0/`) to inoculate the soup.
- **Beagle** — external observer/control client (often with GUI) attached to a
  running Tierra. Not ported; debugging is via the Python API and TraceBuffer.
- **NET** — networked Tierra nodes that exchange organisms. Out of MVP sandbox
  scope (no network I/O from the VM).

## Layout

| Path | Role |
|------|------|
| [`pytierra/`](pytierra/) | Layered package: `bootstrap` / `services` / `models` / `adapters` / `core` |
| [`tests/`](tests/) | pytest suite (coverage ≥ 85%) |
| [`examples/`](examples/) | CLI demos |
| [`legacy/`](legacy/) | Original Tierra C + Beagle/network/MSVC trees (reference only) |
| [`scripts/`](scripts/) | Quality gates, profiling, C-compare helpers, golden check |
| [`docs/`](docs/) | Architecture, API, segment-mut subplan |
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
vm.run(until_births=1)
print(vm.stats())
```

Full method list, errors, and TraceBuffer: [`docs/api.md`](docs/api.md).

### Examples

```powershell
python examples/run_ancestor.py          # mut=0 self-replication
python examples/run_evolution.py         # mut>0 diversity probe (slow)
```

Multi-inoculum: several names in `inoculum` / soup_in lines; `NumCells` cycles the list.
If soup cannot fit an inoculum cell → `ConfigError` at `start()`.

### Profiling and golden

```powershell
python scripts/profile_ancestor.py --scenario births1
python scripts/profile_ancestor.py --scenario births100
python scripts/profile_ancestor.py --scenario fragmentation

python scripts/verify_optimization.py --write-golden   # once
python scripts/verify_optimization.py                  # after hot-path changes
```

Optional C↔Python metrics compare (manual C build): [`scripts/c_compare/README.md`](scripts/c_compare/README.md).

## Known limitations

- Unknown `soup_in` keys (Beagle/Net/UI, …) are ignored with a WARNING.
- No Beagle, NET, disk genebank writer, or frontend.
- Segment mutations are stubs (point mutations work).
- Not claimed bit-identical to C on long evolutionary runs; use c_compare for checks.
- ISA hot path uses TraceBuffer only (no per-instruction logging).

Details: [`docs/architecture.md`](docs/architecture.md).

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
