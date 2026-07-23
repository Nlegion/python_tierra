# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Extra coverage for segment helpers and ops."""

from __future__ import annotations

from types import SimpleNamespace

from pytierra.models.cell import Cell
from pytierra.services.memory.soup import SoupMemory
from pytierra.services.metrics.occupancy import occupancy_array
from pytierra.services.mutate_segment import (
    count_segments,
    crossover_inst,
    crossover_inst_sam_siz,
    crossover_seg,
    deletion_seg,
    find_end_seg_n,
    find_start_seg_n,
    genetic_ops,
    insertion_inst,
    insertion_seg,
)
from pytierra.services.rng import TierraRNG


class SeqRNG(TierraRNG):
    def __init__(self, seq: list[int]):
        super().__init__()
        self._seq = list(seq)
        self._i = 0

    def tlrand(self) -> int:
        if self._i < len(self._seq):
            v = self._seq[self._i]
            self._i += 1
            return v
        return 1


def _ctx(ce, mem, rng, cfg, **extra):
    return SimpleNamespace(
        ce=ce,
        mem=mem,
        cells=[ce],
        rng=rng,
        cfg_values=cfg,
        counters={},
        mal_limit=200,
        max_mal_mult=4.0,
        mov_prop_thr_div=0.4,
        min_cell_size=8,
        min_gen_mem_siz=4,
        mal_mode=1,
        reap_one=lambda: False,
        nop0=0,
        nop1=1,
        **extra,
    )


def test_count_and_find_segments():
    soup = bytearray([2, 3, 0, 4, 5, 1, 6, 7] + [0] * 56)
    # nop0=0 nop1=1 → segments around nops
    n = count_segments(soup, 64, 0, 8, 0, 1)
    assert n >= 1
    s = find_start_seg_n(soup, 64, 0, 8, 1, 0, 1)
    assert s == 0
    e = find_end_seg_n(soup, 64, 0, 8, 1, 0, 1)
    assert e >= s


def test_crossover_inst_sam_siz_inplace():
    mem = SoupMemory(soup_size=200)
    mem.mem_alloc(60, 0, 0)
    mem.mem_alloc(60, 60, 0)
    for i in range(40):
        mem.soup[60 + i] = 10
        mem.soup[i] = 20
    ce = Cell(cell_id=0, alive=True, mm_p=0, mm_s=60, md_p=60, md_s=60)
    ce.dem.MovOffMin = 0
    ce.dem.MovOffMax = 39
    ce.dem.mg_p = 0
    ce.dem.mg_s = 40
    # mate = self with same size
    rng = SeqRNG([0, 5, 1])  # enter, cross point path, stop
    ctx = _ctx(ce, mem, rng, {"GenPerCroInsSamSiz": 2, "MateSizeEp": 5})
    crossover_inst_sam_siz(ctx)
    assert ctx.counters.get("TotCroInsSamSiz", 0) >= 1


def test_insertion_and_crossover_inst():
    mem = SoupMemory(soup_size=300)
    mem.mem_alloc(80, 0, 0)
    mem.mem_alloc(80, 80, 0)
    ce = Cell(cell_id=0, alive=True, mm_p=0, mm_s=80, md_p=80, md_s=80)
    ce.dem.MovOffMin = 0
    ce.dem.MovOffMax = 39
    ce.dem.mg_p = 0
    ce.dem.mg_s = 40
    for i in range(40):
        mem.soup[80 + i] = i
        mem.soup[i] = 50 + (i % 10)
    rng = SeqRNG([0, 0, 0, 0, 1])
    ctx = _ctx(ce, mem, rng, {"GenPerInsIns": 2})
    insertion_inst(ctx)
    rng2 = SeqRNG([0, 5, 5, 1])
    ctx2 = _ctx(ce, mem, rng2, {"GenPerCroIns": 2})
    crossover_inst(ctx2)


def test_seg_ops_smoke():
    mem = SoupMemory(soup_size=300)
    mem.mem_alloc(80, 0, 0)
    mem.mem_alloc(80, 80, 0)
    # genome with nops to create segments
    pattern = [2, 3, 0, 4, 5, 1, 6, 7] * 5
    for i, b in enumerate(pattern):
        mem.soup[80 + i] = b
        mem.soup[i] = b
    ce = Cell(cell_id=0, alive=True, mm_p=0, mm_s=80, md_p=80, md_s=80)
    ce.dem.MovOffMin = 0
    ce.dem.MovOffMax = len(pattern) - 1
    ce.dem.mg_p = 0
    ce.dem.mg_s = len(pattern)
    rng = SeqRNG([0, 0, 0, 0, 0, 0, 1])
    cfg = {
        "GenPerCroSeg": 2,
        "GenPerInsSeg": 2,
        "GenPerDelSeg": 2,
        "GenPerCroInsSamSiz": 0,
        "GenPerCroIns": 0,
        "GenPerInsIns": 0,
        "GenPerDelIns": 0,
    }
    ctx = _ctx(ce, mem, rng, cfg)
    crossover_seg(ctx)
    insertion_seg(ctx)
    deletion_seg(ctx)
    log: list[str] = []
    genetic_ops(ctx, call_log=log)
    assert len(log) == 7


def test_occupancy_array(make_vm):
    vm = make_vm(max_instructions=50_000)
    vm.start()
    vm.run(until_births=1)
    occ = occupancy_array(vm)
    assert len(occ) == vm.config.soup_size
    assert any(b > 0 for b in occ)
