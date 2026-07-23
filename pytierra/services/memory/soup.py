# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Soup bytearray and dual-list MemFr allocator."""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field

from pytierra.core.settings.constants import DEFAULT_MAX_MAL_MULT
from pytierra.models.cell import Cell


@dataclass(order=True)
class _SizeKey:
    size: int
    start: int


@dataclass
class SoupMemory:
    soup_size: int
    soup: bytearray = field(init=False)
    by_addr: list[tuple[int, int]] = field(default_factory=list)  # (start, size)
    by_size: list[_SizeKey] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.soup = bytearray(self.soup_size)
        self.by_addr = [(0, self.soup_size)]
        self.by_size = [_SizeKey(size=self.soup_size, start=0)]

    def ad(self, addr: int) -> int:
        n = self.soup_size
        if n <= 0:
            return 0
        return addr % n

    def is_free(self, addr: int) -> bool:
        if addr < 0 or addr >= self.soup_size:
            return False
        i = bisect.bisect_right(self.by_addr, (addr, self.soup_size + 1)) - 1
        if i < 0:
            return False
        start, size = self.by_addr[i]
        return start <= addr < start + size

    def free_bytes(self) -> int:
        return sum(s for _, s in self.by_addr)

    def _remove_block(self, start: int, size: int) -> None:
        self.by_addr.remove((start, size))
        self.by_size.remove(_SizeKey(size=size, start=start))

    def _insert_block(self, start: int, size: int) -> None:
        if size <= 0:
            return
        bisect.insort(self.by_addr, (start, size))
        bisect.insort(self.by_size, _SizeKey(size=size, start=start))

    def mem_dealloc(self, start: int, size: int) -> None:
        if size <= 0:
            return
        start = self.ad(start)
        end = start + size
        # coalesce with neighbors
        i = bisect.bisect_left(self.by_addr, (start, 0))
        if i > 0:
            ps, pz = self.by_addr[i - 1]
            if ps + pz == start:
                self._remove_block(ps, pz)
                start = ps
                size = pz + size
                end = start + size
                i -= 1
        if i < len(self.by_addr):
            ns, nz = self.by_addr[i]
            if end == ns:
                self._remove_block(ns, nz)
                size += nz
        self._insert_block(start, size)

    def mem_alloc(self, size: int, pref: int, tol: int) -> int:
        """Allocate `size` bytes. pref<0 => better fit; else nearest within tol.
        Returns start address or -1."""
        if size <= 0 or size > self.soup_size:
            return -1
        # find candidates with size >= requested
        idx = bisect.bisect_left(self.by_size, _SizeKey(size=size, start=-1))
        if idx >= len(self.by_size):
            return -1

        if pref < 0:
            # better fit: smallest adequate
            key = self.by_size[idx]
            return self._carve(key.start, key.size, size, place=key.start)

        # preference: choose free block nearest to pref within tol
        best_start = -1
        best_block: tuple[int, int] | None = None
        best_dist = None
        for key in self.by_size[idx:]:
            bstart, bsize = key.start, key.size
            bend = bstart + bsize
            if bstart <= pref < bend:
                dist = 0
            elif pref < bstart:
                dist = bstart - pref
            else:
                dist = pref - (bend - size) if bend - size >= bstart else pref - bstart
            if dist > tol:
                continue
            if best_dist is None or dist < best_dist or (
                dist == best_dist and bstart < best_start
            ):
                best_dist = dist
                best_start = bstart
                best_block = (bstart, bsize)
        if best_block is None:
            return -1
        bstart, bsize = best_block
        bend = bstart + bsize
        if bstart <= pref <= bend - size:
            place = pref
        elif pref < bstart:
            place = bstart
        else:
            place = bend - size
        return self._carve(bstart, bsize, size, place=place)

    def _carve(self, bstart: int, bsize: int, size: int, *, place: int) -> int:
        self._remove_block(bstart, bsize)
        left = place - bstart
        right = (bstart + bsize) - (place + size)
        if left > 0:
            self._insert_block(bstart, left)
        if right > 0:
            self._insert_block(place + size, right)
        return place

    def mal(
        self,
        cell: Cell,
        sug_size: int,
        mode: int,
        *,
        rng_tlrand,
        mal_limit: int,
        max_mal_mult: float = DEFAULT_MAX_MAL_MULT,
        mal_sam_siz: int = 0,
        reaper_fn=None,
    ) -> tuple[int, int]:
        """Allocate daughter memory. Returns (addr, size) or (-1, 0)."""
        if sug_size <= 0 or sug_size == cell.md_s:
            return -1, 0
        if sug_size > max_mal_mult * cell.mm_s:
            return -1, 0
        size = sug_size
        if mal_sam_siz:
            size = cell.mm_s
        if not size:
            return -1, 0
        if cell.md_s:
            self.mem_dealloc(cell.md_p, cell.md_s)
            cell.md_p = cell.md_s = 0
            cell.dem.mov_daught = 0
            cell.dem.MovOffMin = 0
            cell.dem.MovOffMax = 0

        padr = -1
        while padr < 0:
            if mode == 0:
                padr = self.mem_alloc(size, 0, self.soup_size - 1)
            elif mode == 2:
                sad = rng_tlrand() % max(1, self.soup_size - size)
                padr = self.mem_alloc(size, sad, mal_limit)
            elif mode == 3:
                padr = self.mem_alloc(size, cell.mm_p, mal_limit)
            elif mode == 4:
                sad = cell.cpu.re[0] % max(1, self.soup_size - size)
                padr = self.mem_alloc(size, sad, mal_limit)
            elif mode == 5:
                sad = cell.cpu.st[cell.cpu.sp] % max(1, self.soup_size - size)
                padr = self.mem_alloc(size, sad, mal_limit)
            elif mode == 6:
                sad = cell.cpu.re[0] % max(1, self.soup_size - size)
                padr = self.mem_alloc(size, sad, mal_limit)
            else:  # mode 1 better fit
                padr = self.mem_alloc(size, -1, 0)
            if padr < 0:
                if reaper_fn is None or not reaper_fn():
                    break
        if padr < 0:
            return -1, 0
        cell.md_p = self.ad(padr)
        cell.md_s = size
        return cell.md_p, size

    def snapshot(self) -> dict:
        return {
            "soup_size": self.soup_size,
            "soup": bytes(self.soup),
            "by_addr": list(self.by_addr),
        }

    @classmethod
    def from_snapshot(cls, data: dict) -> SoupMemory:
        mem = cls(soup_size=int(data["soup_size"]))
        mem.soup = bytearray(data["soup"])
        mem.by_addr = []
        mem.by_size = []
        for start, size in data["by_addr"]:
            mem._insert_block(int(start), int(size))
        return mem
