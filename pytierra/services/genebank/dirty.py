# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Mark genome hash cache dirty (callable from ISA / mutate without genebank logic)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytierra.models.cell import Cell


def mark_genome_dirty(cell: Cell) -> None:
    cell.dem.genome_hash_dirty = True


def mark_cells_dirty_at(cells: list[Cell], addr: int) -> None:
    """Invalidate hash for any live cell whose genetic region covers ``addr``."""
    for c in cells:
        if not c.alive:
            continue
        g0 = c.mm_p + c.dem.mg_p
        g1 = g0 + (c.dem.mg_s or c.mm_s)
        if g0 <= addr < g1 or (c.mm_p <= addr < c.mm_p + c.mm_s):
            mark_genome_dirty(c)
        if c.md_s and c.md_p <= addr < c.md_p + c.md_s:
            mark_genome_dirty(c)
