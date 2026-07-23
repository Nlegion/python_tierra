# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from __future__ import annotations

from types import SimpleNamespace

from pytierra.models.cell import Cell
from pytierra.services.memory.soup import SoupMemory
from pytierra.services.mutate_segment import (
    GENETIC_OPS_ORDER,
    assemble_daught,
    deletion_inst,
    genetic_ops,
    shared_gen_ops,
)
from pytierra.services.rng import TierraRNG


def test_assemble_daught_two_frags():
    soup = bytearray(b"ABCDEFGHIJ" + b"\x00" * 54)
    out = assemble_daught(soup, 64, 2, 0, 3, 5, 2)
    assert out == b"ABC" + b"FG"


def test_shared_gen_ops_same_size_overwrite():
    mem = SoupMemory(soup_size=128)
    mem.mem_alloc(40, 0, 0)
    mem.mem_alloc(40, 40, 0)
    for i in range(40):
        mem.soup[40 + i] = i
    ce = Cell(cell_id=0, alive=True, mm_p=0, mm_s=40, md_p=40, md_s=40)
    ce.dem.MovOffMin = 0
    ce.dem.MovOffMax = 39
    rng = TierraRNG()
    rng.tsrand(1)
    # same-size rewrite: two halves of existing daughter genome
    ok = shared_gen_ops(
        ce,
        mem,
        num_frag=2,
        adr1=40,
        siz1=20,
        adr2=60,
        siz2=20,
        rng=rng,
        mal_limit=20,
        max_mal_mult=3.0,
        mov_prop_thr_div=0.5,
        min_cell_size=12,
        min_gen_mem_siz=5,
        mal_mode=1,
        reap_one=lambda: False,
    )
    assert ok is True
    assert bytes(mem.soup[40:80]) == bytes(range(40))


def test_deletion_inst_shortens_genome():
    mem = SoupMemory(soup_size=256)
    mem.mem_alloc(80, 0, 0)
    mem.mem_alloc(80, 80, 0)
    ce = Cell(cell_id=0, alive=True, mm_p=0, mm_s=80, md_p=80, md_s=80)
    ce.dem.MovOffMin = 0
    ce.dem.MovOffMax = 39
    for i in range(40):
        mem.soup[80 + i] = i
    rng = TierraRNG()
    # Force rate loop: GenPerDelIns=1 → while 1 and (tlrand()%1)==0 always once per...
    # %1 == 0 always → infinite loop! Use rate=2 and scripted rng.

    class SeqRNG(TierraRNG):
        def __init__(self, seq):
            super().__init__()
            self._seq = list(seq)
            self._i = 0

        def tlrand(self):
            if self._i < len(self._seq):
                v = self._seq[self._i]
                self._i += 1
                return v
            return 1  # stop while: 1 % 2 != 0

    # rate=2: need tlrand%2==0 to enter, then del_siz, del_off, then stop
    # enter: 0; del_siz: 0 -> 1+(0%(20))=1; del_off: 0; then 1 to exit
    rng = SeqRNG([0, 0, 0, 1])
    ctx = SimpleNamespace(
        ce=ce,
        mem=mem,
        cells=[ce],
        rng=rng,
        cfg_values={"GenPerDelIns": 2},
        counters={},
        mal_limit=100,
        max_mal_mult=3.0,
        mov_prop_thr_div=0.5,
        min_cell_size=12,
        min_gen_mem_siz=5,
        mal_mode=1,
        reap_one=lambda: False,
        nop0=0,
        nop1=1,
    )
    before = bytes(mem.soup[80:120])
    changed = deletion_inst(ctx)
    assert changed
    assert ctx.counters.get("TotDelIns", 0) >= 1
    new_len = ce.dem.MovOffMax - ce.dem.MovOffMin + 1
    assert new_len < 40
    assert bytes(mem.soup[80:120]) != before or new_len != 40


def test_genetic_ops_order():
    mem = SoupMemory(soup_size=64)
    ce = Cell(cell_id=0, alive=True, mm_p=0, mm_s=32, md_p=32, md_s=32)
    ce.dem.MovOffMin = 0
    ce.dem.MovOffMax = 15
    mem.mem_alloc(32, 0, 0)
    mem.mem_alloc(32, 32, 0)
    ctx = SimpleNamespace(
        ce=ce,
        mem=mem,
        cells=[ce],
        rng=TierraRNG(),
        cfg_values={k: 0 for k in (
            "GenPerCroInsSamSiz",
            "GenPerCroIns",
            "GenPerInsIns",
            "GenPerDelIns",
            "GenPerCroSeg",
            "GenPerInsSeg",
            "GenPerDelSeg",
        )},
        counters={},
        mal_limit=20,
        max_mal_mult=3.0,
        mov_prop_thr_div=0.7,
        min_cell_size=12,
        min_gen_mem_siz=5,
        mal_mode=1,
        reap_one=lambda: False,
        nop0=0,
        nop1=1,
    )
    log: list[str] = []
    genetic_ops(ctx, call_log=log)
    assert log == list(GENETIC_OPS_ORDER)


def test_mal_fail_leaves_md_unchanged():
    mem = SoupMemory(soup_size=100)
    mem.mem_alloc(40, 0, 0)
    mem.mem_alloc(40, 40, 0)
    # almost full — little free left
    ce = Cell(cell_id=0, alive=True, mm_p=0, mm_s=40, md_p=40, md_s=40)
    ce.dem.MovOffMin = 0
    ce.dem.MovOffMax = 39
    for i in range(40):
        mem.soup[40 + i] = 7
    before = bytes(mem.soup[40:80])
    rng = TierraRNG()
    rng.tsrand(1)
    # request huge new size → rejected by max_mal_mult / min checks
    ok = shared_gen_ops(
        ce,
        mem,
        num_frag=1,
        adr1=40,
        siz1=200,
        rng=rng,
        mal_limit=20,
        max_mal_mult=1.1,
        mov_prop_thr_div=0.7,
        min_cell_size=12,
        min_gen_mem_siz=5,
        mal_mode=1,
        reap_one=lambda: False,
    )
    assert ok is False
    assert ce.md_p == 40 and ce.md_s == 40
    assert bytes(mem.soup[40:80]) == before
