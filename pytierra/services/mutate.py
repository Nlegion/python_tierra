# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Mutation operators (bkg / mov / div) and segment stubs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pytierra.models.cell import Cell
from pytierra.services.genebank.dirty import mark_genome_dirty

if TYPE_CHECKING:
    from pytierra.services.memory.soup import SoupMemory
    from pytierra.services.rng import TierraRNG


def mut_site(
    mem: SoupMemory,
    addr: int,
    *,
    rng: TierraRNG,
    mut_bit_prop: float,
    inst_num: int,
    inst_bit_num: int,
) -> None:
    addr = mem.ad(addr)
    if rng.tdrand() < mut_bit_prop:
        bit = rng.tirand() % max(1, inst_bit_num)
        mem.soup[addr] ^= 1 << bit
    else:
        mem.soup[addr] = rng.tirand() % max(1, inst_num)


def cosmic_mutate(
    mem: SoupMemory,
    *,
    rng: TierraRNG,
    mut_bit_prop: float,
    inst_num: int,
    inst_bit_num: int,
) -> int:
    i = rng.tlrand() % mem.soup_size
    mut_site(
        mem,
        i,
        rng=rng,
        mut_bit_prop=mut_bit_prop,
        inst_num=inst_num,
        inst_bit_num=inst_bit_num,
    )
    return i


def mutation_ops_div(
    cell: Cell,
    mem: SoupMemory,
    *,
    rng: TierraRNG,
    gen_per_div_mut: int,
    mut_bit_prop: float,
    inst_num: int,
    inst_bit_num: int,
    counters: dict[str, Any],
) -> bool:
    """Return True if any divide-time mutation was applied."""
    if not gen_per_div_mut:
        return False
    mutated = False
    while gen_per_div_mut and (rng.tlrand() % gen_per_div_mut) == 0:
        counters["TotDivMut"] = counters.get("TotDivMut", 0) + 1
        mutated = True
        dstart = cell.md_p + cell.dem.MovOffMin
        dsize = cell.dem.MovOffMax - cell.dem.MovOffMin + 1
        if dsize <= 0:
            break
        site = dstart + (rng.tlrand() % dsize)
        mut_site(
            mem,
            site,
            rng=rng,
            mut_bit_prop=mut_bit_prop,
            inst_num=inst_num,
            inst_bit_num=inst_bit_num,
        )
    return mutated


def apply_segment_mutation_for_tests(
    cell: Cell,
    mem: SoupMemory,
    *,
    addr_offset: int = 0,
    new_byte: int = 0x3F,
) -> None:
    """Test helper: point-edit genome and mark dirty (for RamBanker path tests)."""
    g0 = cell.mm_p + cell.dem.mg_p
    addr = mem.ad(g0 + addr_offset)
    mem.soup[addr] = new_byte & 0xFF
    mark_genome_dirty(cell)
