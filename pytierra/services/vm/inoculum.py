# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Inoculate soup from preloaded genomes (no import of service.py)."""

from __future__ import annotations

import logging
from typing import Any

from pytierra.core.errors import ConfigError

logger = logging.getLogger(__name__)


def inoculate(vm: Any) -> None:
    """Place inoculum cells into ``vm`` soup/queues.

    Cycles through ``config.inoculum`` (or loaded genome keys) for ``NumCells``
    placements. Raises ``ConfigError`` if any placement cannot allocate.
    """
    names = list(vm.config.inoculum) or list(vm._genomes.keys())
    if not names:
        logger.error("No inoculum genomes", extra={"event": "config_error"})
        raise ConfigError("No inoculum genomes")
    for gname in names:
        if gname not in vm._genomes:
            logger.error(
                "Inoculum genome not loaded: %s",
                gname,
                extra={"event": "config_error"},
            )
            raise ConfigError(f"Inoculum genome not loaded: {gname}")
    n = max(1, vm.config.num_cells)
    sizes = [len(vm._genomes[names[i % len(names)]]) for i in range(n)]
    vm.average_size = max(1, sum(sizes) // len(sizes))
    for i in range(n):
        gname = names[i % len(names)]
        code = vm._genomes[gname]
        size = len(code)
        if vm.config.place_center:
            gap = vm.config.soup_size // n
            addr = (gap * i + (gap - size) // 2) % vm.config.soup_size
        else:
            addr = (i * (size + 10)) % max(1, vm.config.soup_size - size)
        got = vm.mem.mem_alloc(size, addr, vm.config.soup_size)
        if got < 0:
            got = vm.mem.mem_alloc(size, -1, 0)
        if got < 0:
            logger.error(
                "Unable to allocate inoculum size=%d index=%d",
                size,
                i,
                extra={"event": "config_error"},
            )
            raise ConfigError("Unable to allocate inoculum")
        for j, op in enumerate(code):
            vm.mem.soup[vm.mem.ad(got + j)] = op & 0xFF
        cell = vm._new_cell()
        cell.alive = True
        cell.mm_p = got
        cell.mm_s = size
        cell.cpu.ip = got
        cell.dem.gen_name = gname
        cell.dem.gen_size = size
        cell.dem.mg_p = 0
        cell.dem.mg_s = size
        vm.queues.ent_bot_slicer(vm.cells, cell.cell_id)
        vm.queues.ent_bot_reaper(vm.cells, cell.cell_id)
        vm.queues.num_cells += 1
