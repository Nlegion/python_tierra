# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""TierraVM — sandbox API for the Python Tierra core."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from pytierra.core.errors import InternalError, SandboxLimitError, StateError
from pytierra.core.settings.constants import LICENSE_NOTICE
from pytierra.models.cell import Cell
from pytierra.models.config import TierraConfig
from pytierra.models.genome import OpcodeMap
from pytierra.models.limits import SandboxLimits
from pytierra.models.trace import TraceBuffer
from pytierra.services.memory.queues import CellQueues
from pytierra.services.memory.soup import SoupMemory
from pytierra.services.rng import TierraRNG
from pytierra.services.vm import inoculum as inoculum_mod
from pytierra.services.vm import slicer as slicer_mod
from pytierra.services.vm import snapshot as snapshot_mod
from pytierra.services.vm.context import VMContext
from pytierra.services.vm.helpers import check_limits

logger = logging.getLogger(__name__)


class TierraVM:
    """Managed Tierra virtual machine (no shell / sockets / host side-effects)."""

    def __init__(
        self,
        config: TierraConfig,
        *,
        asset_root: Path | str,
        opcode_map: OpcodeMap,
        limits: SandboxLimits | None = None,
    ) -> None:
        self.config = config
        self.asset_root = Path(asset_root)
        self.opcode_map = opcode_map
        self.limits = limits or SandboxLimits()
        if config.soup_size > self.limits.max_soup_size:
            raise SandboxLimitError(
                f"SoupSize {config.soup_size} > max_soup_size",
                kind="max_soup_size",
            )
        self.mem = SoupMemory(soup_size=config.soup_size)
        self.cells: list[Cell] = []
        self.queues = CellQueues()
        self.rng = TierraRNG()
        self.trace = TraceBuffer()
        self.stopped = False
        self._started = False
        self.inst_exe = 0
        self.budget_used = 0
        self.average_size = 80
        self.rate_mut = 0
        self.count_mut = 0
        self.rate_mov_mut = 0
        self.count_mov_mut = 0
        self.rate_flaw = 0
        self.count_flaw = 0
        self.counters: dict[str, Any] = {"births": 0, "deaths": 0}
        self._run_started = 0.0
        self._pending_reap: list[int] = []
        self._genomes: dict[str, list[int]] = {}

    @classmethod
    def from_config(
        cls,
        path_or_dict: str | Path | dict,
        *,
        asset_root: str | Path | None = None,
        limits: SandboxLimits | None = None,
    ) -> TierraVM:
        from pytierra.bootstrap.wiring import build_vm_from_config

        return build_vm_from_config(
            path_or_dict,
            asset_root=asset_root,
            limits=limits,
        )

    def _notify_birth(self, cell_id: int, size: int) -> None:
        logger.debug(
            "Birth: cell_id=%d size=%d",
            cell_id,
            size,
            extra={"event": "birth"},
        )

    def _notify_death(self, cell_id: int) -> None:
        logger.debug(
            "Death: cell_id=%d",
            cell_id,
            extra={"event": "death"},
        )

    def start(self) -> None:
        self.stopped = False
        self._started = True
        self.inst_exe = 0
        self.budget_used = 0
        self.counters = {"births": 0, "deaths": 0}
        self.cells.clear()
        self.queues = CellQueues()
        self.mem = SoupMemory(soup_size=self.config.soup_size)
        seed = self.config.seed or 1
        self.rng.tsrand(seed)
        _ = self.rng.tlrand()
        inoculum_mod.inoculate(self)
        self._recompute_rates()
        self._run_started = time.perf_counter()
        logger.info(
            "TierraVM started; %s",
            LICENSE_NOTICE,
            extra={"event": "start"},
        )

    def _new_cell(self) -> Cell:
        cid = len(self.cells)
        cell = Cell(cell_id=cid)
        self.cells.append(cell)
        return cell

    def alloc_cell(self) -> Cell | None:
        if self.queues.num_cells >= self.limits.max_cells:
            return None
        from pytierra.models.cell import Cpu, Dem

        for c in self.cells:
            if not c.alive:
                c.cpu = Cpu()
                c.dem = Dem()
                c.md_p = c.md_s = 0
                c.mm_p = c.mm_s = 0
                return c
        return self._new_cell()

    def _recompute_rates(self) -> None:
        v = self.config.values
        self.rate_mut = int(v.get("GenPerBkgMut") or 0)
        self.rate_mov_mut = int(v.get("GenPerMovMut") or 0)
        self.rate_flaw = int(v.get("GenPerFlaw") or 0)
        self.count_mut = 0
        self.count_mov_mut = 0
        self.count_flaw = 0

    def update_average_size(self) -> None:
        alive = [c for c in self.cells if c.alive]
        if not alive:
            return
        self.average_size = max(1, sum(c.mm_s for c in alive) // len(alive))

    def reap_one(self) -> bool:
        if self.queues.num_cells <= int(self.config.get("NumCellsMin", 1)):
            return False
        rid = self.queues.top_reap
        if rid < 0:
            return False
        self._reap_cell(rid)
        return True

    def _reap_cell(self, cell_id: int) -> None:
        if cell_id < 0 or cell_id >= len(self.cells):
            raise InternalError(f"reap of non-existent cell_id={cell_id}")
        cell = self.cells[cell_id]
        if not cell.alive:
            return
        self.queues.rmv_from_slicer(self.cells, cell_id)
        self.queues.rmv_from_reaper(self.cells, cell_id)
        if cell.mm_s:
            self.mem.mem_dealloc(cell.mm_p, cell.mm_s)
        if cell.md_s:
            self.mem.mem_dealloc(cell.md_p, cell.md_s)
        cell.alive = False
        cell.mm_s = cell.md_s = 0
        self.queues.num_cells = max(0, self.queues.num_cells - 1)
        self.counters["deaths"] = self.counters.get("deaths", 0) + 1
        self._notify_death(cell_id)

    def _make_ctx(self, ce: Cell) -> VMContext:
        v = self.config.values
        mal_tol = int(v.get("MalTol", 20))
        mal_limit = max(1, mal_tol * self.average_size)
        inst_bit = max(1, (self.opcode_map.inst_num - 1).bit_length())
        return VMContext(
            mem=self.mem,
            cells=self.cells,
            queues=self.queues,
            rng=self.rng,
            ce=ce,
            nop0=self.opcode_map.nop0,
            nop1=self.opcode_map.nop1,
            nop_s=self.opcode_map.nop_s,
            inst_num=self.opcode_map.inst_num,
            inst_bit_num=inst_bit,
            min_templ_size=int(v.get("MinTemplSize", 1)),
            min_cell_size=int(v.get("MinCellSize", 12)),
            min_gen_mem_siz=int(v.get("MinGenMemSiz", 12)),
            mov_prop_thr_div=float(v.get("MovPropThrDiv", 0.7)),
            mal_limit=mal_limit,
            max_mal_mult=float(v.get("MaxMalMult", 3.0)),
            mal_sam_siz=int(v.get("MalSamSiz", 0)),
            mal_mode=int(v.get("MalMode", 1)),
            mem_mode_free=int(v.get("MemModeFree", 0)),
            mem_mode_mine=int(v.get("MemModeMine", 0)),
            mem_mode_prot=int(v.get("MemModeProt", 2)),
            search_limit=float(v.get("SearchLimit", 5.0)),
            abs_search_limit=int(v.get("AbsSearchLimit", 0)),
            average_size=self.average_size,
            rate_mov_mut=self.rate_mov_mut,
            count_mov_mut=self.count_mov_mut,
            rate_flaw=self.rate_flaw,
            count_flaw=self.count_flaw,
            gen_per_div_mut=int(v.get("GenPerDivMut", 0) or 0),
            mut_bit_prop=float(v.get("MutBitProp", 0.2)),
            cfg_values=v,
            counters=self.counters,
            alloc_cell=self.alloc_cell,
            reap_one=self.reap_one,
            update_average_size=self.update_average_size,
            notify_birth=self._notify_birth,
            notify_death=self._notify_death,
        )

    def _check_limits(self, *, force: bool = False) -> None:
        check_limits(
            self.limits,
            budget_used=self.budget_used,
            run_started=self._run_started,
            force=force,
        )

    def _require_started(self) -> None:
        if not self._started:
            logger.error("VM not started", extra={"event": "state_error"})
            raise StateError("call start() before step/run")

    def step(self, n: int = 1) -> int:
        self._require_started()
        if self.stopped:
            return 0
        self._check_limits(force=True)
        start = self.inst_exe
        target = start + max(0, n)
        while self.inst_exe < target and not self.stopped:
            before = self.inst_exe
            slicer_mod.slicer_step(self)
            if self.inst_exe == before:
                break
        return self.inst_exe - start

    def run(
        self,
        *,
        max_instructions: int | None = None,
        until_births: int | None = None,
    ) -> dict[str, Any]:
        self._require_started()
        if max_instructions is not None:
            self.limits.max_instructions = max_instructions
        self._run_started = time.perf_counter()
        while not self.stopped:
            self._check_limits(force=True)
            if until_births is not None and self.counters.get("births", 0) >= until_births:
                break
            before = self.inst_exe
            slicer_mod.slicer_step(self)
            if self.inst_exe == before:
                break
        return self.stats()

    def stop(self) -> None:
        self.stopped = True
        logger.info("TierraVM stopped", extra={"event": "stop"})

    def set_limits(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            if hasattr(self.limits, k):
                setattr(self.limits, k, v)
        self.stopped = False
        logger.info(
            "Limits updated: %s",
            kwargs,
            extra={"event": "set_limits"},
        )

    def enable_trace(self, enabled: bool = True) -> None:
        self.trace.enabled = enabled
        if enabled:
            self.trace.clear()
        logger.info(
            "Trace enabled=%s",
            enabled,
            extra={"event": "enable_trace"},
        )

    def get_trace(self) -> list[dict[str, Any]]:
        return self.trace.get_trace()

    def stats(self) -> dict[str, Any]:
        return {
            "NumCells": self.queues.num_cells,
            "InstExe": self.inst_exe,
            "births": self.counters.get("births", 0),
            "deaths": self.counters.get("deaths", 0),
            "free_mem": self.mem.free_bytes(),
            "AverageSize": self.average_size,
            "budget_used": self.budget_used,
        }

    def snapshot(self) -> dict[str, Any]:
        return snapshot_mod.take_snapshot(self)

    def restore(self, snap: dict[str, Any]) -> None:
        snapshot_mod.restore_snapshot(self, snap)
