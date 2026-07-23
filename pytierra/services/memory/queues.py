# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Circular slicer and reaper queues."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytierra.models.cell import Cell


class CellQueues:
    def __init__(self) -> None:
        self.this_slice: int = -1
        self.top_reap: int = -1
        self.bottom_reap: int = -1
        self.num_cells: int = 0

    def ent_bot_slicer(self, cells: list[Cell], cell_id: int) -> None:
        cell = cells[cell_id]
        if self.this_slice < 0 or not cells[self.this_slice].alive:
            self.this_slice = cell_id
            cell.n_time = cell_id
            cell.p_time = cell_id
        else:
            cur = cells[self.this_slice]
            prev = cells[cur.p_time]
            cell.n_time = self.this_slice
            cell.p_time = cur.p_time
            prev.n_time = cell_id
            cur.p_time = cell_id
        cell.dem.is_active = 1

    def incr_slice_queue(self, cells: list[Cell]) -> None:
        if self.this_slice < 0:
            return
        cur = cells[self.this_slice]
        if cur.n_time >= 0:
            self.this_slice = cur.n_time

    def rmv_from_slicer(self, cells: list[Cell], cell_id: int) -> None:
        cell = cells[cell_id]
        if not cell.dem.is_active:
            return
        if cell.n_time == cell_id:
            self.this_slice = -1
        else:
            cells[cell.p_time].n_time = cell.n_time
            cells[cell.n_time].p_time = cell.p_time
            if self.this_slice == cell_id:
                self.this_slice = cell.n_time
        cell.n_time = cell.p_time = -1
        cell.dem.is_active = 0

    def ent_bot_reaper(self, cells: list[Cell], cell_id: int) -> None:
        cell = cells[cell_id]
        if self.bottom_reap < 0:
            self.top_reap = self.bottom_reap = cell_id
            cell.n_reap = cell.p_reap = cell_id
        else:
            bot = cells[self.bottom_reap]
            cell.p_reap = self.bottom_reap
            cell.n_reap = bot.n_reap
            cells[bot.n_reap].p_reap = cell_id
            bot.n_reap = cell_id
            self.bottom_reap = cell_id

    def rmv_from_reaper(self, cells: list[Cell], cell_id: int) -> None:
        cell = cells[cell_id]
        if self.top_reap < 0:
            return
        if cell.n_reap == cell_id:
            self.top_reap = self.bottom_reap = -1
        else:
            cells[cell.p_reap].n_reap = cell.n_reap
            cells[cell.n_reap].p_reap = cell.p_reap
            if self.top_reap == cell_id:
                self.top_reap = cell.n_reap
            if self.bottom_reap == cell_id:
                self.bottom_reap = cell.p_reap
        cell.n_reap = cell.p_reap = -1
