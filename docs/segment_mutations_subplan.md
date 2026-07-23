# Segment mutations (cro / ins / del)

Status: **implemented** — port of `GeneticOps` from [`legacy/tierra/operator.c`](../legacy/tierra/operator.c).

## Module

[`pytierra/services/mutate_segment.py`](../pytierra/services/mutate_segment.py)

Call order after `mutation_ops_div` (matches C):

1. `CrossoverInstSamSiz`
2. `CrossoverInst`
3. `InsertionInst`
4. `DeletionInst`
5. `CrossoverSeg`
6. `InsertionSeg`
7. `DeletionSeg`

`shared_gen_ops` assembles a temp genome then commits; same-size overwrites in place; resize probes `mem_alloc` first (soft-fail leaves `md` unchanged).

Wired from [`ops_repro.divide`](../pytierra/services/isa/ops_repro.py). Rates: `GenPerCroInsSamSiz`, `GenPerCroIns`, `GenPerInsIns`, `GenPerDelIns`, `GenPerCroSeg`, `GenPerInsSeg`, `GenPerDelSeg` (default 0).
