# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Shared execution context passed into ISA ops."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from pytierra.models.cell import Cell
from pytierra.services.memory.queues import CellQueues
from pytierra.services.memory.soup import SoupMemory
from pytierra.services.rng import TierraRNG


@dataclass
class VMContext:
    mem: SoupMemory
    cells: list[Cell]
    queues: CellQueues
    rng: TierraRNG
    ce: Cell
    nop0: int
    nop1: int
    nop_s: int
    inst_num: int
    inst_bit_num: int
    min_templ_size: int
    min_cell_size: int
    min_gen_mem_siz: int
    mov_prop_thr_div: float
    mal_limit: int
    max_mal_mult: float
    mal_sam_siz: int
    mal_mode: int
    mem_mode_free: int
    mem_mode_mine: int
    mem_mode_prot: int
    search_limit: float
    abs_search_limit: int
    average_size: int
    rate_mov_mut: int
    count_mov_mut: int
    rate_flaw: int
    count_flaw: int
    gen_per_div_mut: int
    mut_bit_prop: float
    cfg_values: dict
    counters: dict[str, Any]
    alloc_cell: Callable[[], Cell | None]
    reap_one: Callable[[], bool]
    update_average_size: Callable[[], None]
    notify_birth: Callable[[int, int], None] | None = None
    notify_death: Callable[[int], None] | None = None
    bitbucket: int = 0

    def flaw(self) -> int:
        if self.rate_flaw and self.count_flaw + 1 >= self.rate_flaw:
            self.count_flaw = self.rng.tlrand() % self.rate_flaw
            self.counters["TotFlaw"] = self.counters.get("TotFlaw", 0) + 1
            self.ce.dem.flaw += 1
            self.ce.dem.nonslfmut = 1
            return 1 if (self.rng.tcrand() % 2) else -1
        if self.rate_flaw:
            self.count_flaw += 1
        return 0

    def _owner_mode(self, cell: Cell, addr: int) -> int:
        if cell.mm_p <= addr < cell.mm_p + cell.mm_s:
            return self.mem_mode_mine
        if cell.md_s and cell.md_p <= addr < cell.md_p + cell.md_s:
            return self.mem_mode_mine
        if self.mem.is_free(addr):
            return self.mem_mode_free
        return self.mem_mode_prot

    def priv_write(self, cell: Cell, addr: int) -> bool:
        # bit1 = write protect when set in mode
        mode = self._owner_mode(cell, addr)
        return not bool(mode & 2)

    def priv_read(self, cell: Cell, addr: int) -> bool:
        mode = self._owner_mode(cell, addr)
        return not bool(mode & 4)

    def search_limit_abs(self) -> int:
        slim = int(self.search_limit * max(1, self.average_size))
        if self.abs_search_limit > 0:
            slim = max(slim, self.abs_search_limit)
        return slim
