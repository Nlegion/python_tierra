# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Build soup occupancy arrays for heatmaps (no genebank/net imports)."""

from __future__ import annotations

from typing import Any


def occupancy_array(vm: Any) -> bytearray:
    """0=free, >0 = cell_id+1 for occupied genetic/cell body bytes."""
    occ = bytearray(vm.config.soup_size)
    for c in vm.cells:
        if not c.alive or c.mm_s <= 0:
            continue
        mark = (c.cell_id % 255) + 1
        for i in range(c.mm_s):
            occ[vm.mem.ad(c.mm_p + i)] = mark
        if c.md_s:
            for i in range(c.md_s):
                occ[vm.mem.ad(c.md_p + i)] = mark
    return occ
