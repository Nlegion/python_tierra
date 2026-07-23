# Subplan: segment mutations (cro / ins / del) — Phase 2b

Status: **design only** — do not implement until this subplan is approved and scheduled.

## Goal

Replace [`genetic_ops_stubs`](../pytierra/services/mutate.py) with C-faithful segment operators used in Tierra evolution (crossover / insert / delete of instruction segments).

## C sources to map

| Concern | Likely C location under `legacy/tierra/` |
|---------|------------------------------------------|
| Genetic / segment ops | `instruct.c`, `operator.c`, related `genio` helpers |
| Template / `adr` interaction | `decode.c` / template search already ported in `services/isa/template.py` |
| Config rates | `GenPerCroInsSamSiz`, `GenPerInsIns`, `GenPerDelIns`, `GenPerCroIns`, `GenPerDelSeg`, `GenPerInsSeg`, `GenPerCroSeg` |

Exact function names must be confirmed by reading C before coding.

## Implementation sketch

1. Port one operator at a time (e.g. `InsIns` → `DelIns` → segment cro).
2. Memory shift helpers on `SoupMemory` (insert/delete bytes inside owned `md_*` / `mm_*` with privilege checks).
3. Update cell dem fields / IP if C does so after size change.
4. Wire rates from `cfg_values` in `divide` path (where stubs are called today).

## Synthetic verification

- Build tiny genomes that force a known cro/ins/del site.
- Compare resulting soup bytes to:
  - a recorded golden from instrumented C, or
  - a hand-computed expected buffer for the toy genome.
- Acceptance: `0080aaa` with all segment `GenPer*=0` unchanged (current suite green).
- Evolution: with high segment rates + fixed seed, size histogram / genotype diversity changes (non-flaky counter or length assert).

## Risks

- Memory shifts corrupting templates / `adr` targets.
- Infinite loops if rate `% 1 == 0` (same GenPer pitfall as div mut).
- Interaction with `mal` / reaper under fragmentation.

## Exit criteria

- Unit tests per operator + mut=0 acceptance green.
- Docs: remove “stubs” from Known limitations; update `docs/api.md` Mutations section.
