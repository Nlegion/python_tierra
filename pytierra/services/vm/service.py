# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""TierraVM — sandbox API for the Python Tierra core."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Callable

from pytierra.core.errors import ConfigError, InternalError, SandboxLimitError, StateError
from pytierra.core.settings.constants import LICENSE_NOTICE
from pytierra.models.cell import Cell
from pytierra.models.config import TierraConfig
from pytierra.models.genome import OpcodeMap
from pytierra.models.limits import SandboxLimits
from pytierra.models.trace import TraceBuffer
from pytierra.services.genebank.hashutil import default_hash
from pytierra.services.genebank.noop import NoOpGeneBank
from pytierra.services.genebank.rambank import RamBanker
from pytierra.services.genebank.write_queue import WriteJob, WriteQueue
from pytierra.services.memory.queues import CellQueues
from pytierra.services.memory.soup import SoupMemory
from pytierra.services.observer.service import ObserverService
from pytierra.services.rng import TierraRNG
from pytierra.services.vm import inoculum as inoculum_mod
from pytierra.services.vm import slicer as slicer_mod
from pytierra.services.vm import snapshot as snapshot_mod
from pytierra.services.vm.context import VMContext
from pytierra.services.vm.flaw_rates import calc_flaw_rates
from pytierra.services.vm.helpers import check_limits

logger = logging.getLogger(__name__)

_PARAM_WHITELIST = frozenset(
    {
        "SliceSize",
        "GenPerBkgMut",
        "GenPerMovMut",
        "GenPerDivMut",
        "GenPerFlaw",
        "NumCellsMin",
        "MalTol",
        "MovPropThrDiv",
        "MutBitProp",
        "SearchLimit",
    }
)


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
        self._validate_disk_bank_config()
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
        self.counters: dict[str, Any] = {
            "births": 0,
            "deaths": 0,
            "mal_fail": 0,
            "reap_attempts": 0,
        }
        self._run_started = 0.0
        self._until_births: int | None = None
        self._pending_reap: list[int] = []
        self._genomes: dict[str, list[int]] = {}
        self.node_id = "local"
        self.genebank: RamBanker | NoOpGeneBank = self._make_genebank()
        self.observer = ObserverService()
        self.write_queue = WriteQueue()
        self.disk_bank = None
        self._transport = None
        self._steps_since_flush = 0
        self.recorder = None

    def _validate_disk_bank_config(self) -> None:
        fmt = str(self.config.get("DiskBankFormat", "ascii")).lower()
        backend = str(self.config.get("DiskBankBackend", "json")).lower()
        if fmt != "ascii":
            raise ConfigError(f"DiskBankFormat={fmt!r} not implemented (only ascii)")
        if backend != "json":
            raise ConfigError(f"DiskBankBackend={backend!r} not implemented (only json)")

    def _make_genebank(self) -> RamBanker | NoOpGeneBank:
        if int(self.config.get("GeneBnker", 0) or 0):
            return RamBanker()
        return NoOpGeneBank()

    def attach_disk_bank(self, store: Any) -> None:
        self.disk_bank = store
        self.write_queue.set_flush_fn(store.write_job)

    def attach_transport(self, transport: Any, *, node_id: str = "local") -> None:
        self._transport = transport
        self.node_id = node_id

    def attach_recorder(self, recorder: Any) -> None:
        """Attach a MetricsRecorder (or compatible) for post-hoc visualization."""
        self.recorder = recorder

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

    def _cell_genome_bytes(self, cell: Cell) -> bytes:
        g0 = cell.mm_p + cell.dem.mg_p
        gsz = cell.dem.mg_s or cell.mm_s
        return bytes(self.mem.soup[g0 : g0 + gsz])

    def _ensure_cell_hash(self, cell: Cell) -> int:
        if cell.dem.genome_hash_dirty or cell.dem.genome_hash is None:
            h = default_hash(self._cell_genome_bytes(cell))
            cell.dem.genome_hash = h
            cell.dem.genome_hash_dirty = False
            return h
        return int(cell.dem.genome_hash)

    def _notify_birth(self, cell_id: int, size: int, *, is_migrant: bool = False) -> None:
        logger.debug(
            "Birth: cell_id=%d size=%d migrant=%s",
            cell_id,
            size,
            is_migrant,
            extra={"event": "birth"},
        )
        cell = self.cells[cell_id]
        mother_name = ""
        mid = self.counters.pop("_birth_mother_id", None)
        if not is_migrant and mid is not None and 0 <= int(mid) < len(self.cells):
            mother_name = self.cells[int(mid)].dem.gen_name
        if self.genebank.enabled:
            genome = self._cell_genome_bytes(cell)
            if cell.dem.genome_hash_dirty or cell.dem.genome_hash is None:
                cell.dem.genome_hash = default_hash(genome)
                cell.dem.genome_hash_dirty = False
            mother_hash = None
            if not is_migrant and mid is not None and 0 <= int(mid) < len(self.cells):
                mother = self.cells[int(mid)]
                if mother.dem.genome_hash_dirty or mother.dem.genome_hash is None:
                    mother_hash = self._ensure_cell_hash(mother)
                else:
                    mother_hash = mother.dem.genome_hash
            name = self.genebank.on_birth(
                cell_id=cell_id,
                size=size,
                genome=genome,
                mother_name=mother_name,
                mother_hash=mother_hash,
                is_migrant=is_migrant,
            )
            cell.dem.gen_name = name
            self._maybe_auto_extract(name, genome)
        if self.recorder is not None:
            self.recorder.on_birth(
                inst_exe=self.inst_exe,
                cell_id=cell_id,
                gen_name=cell.dem.gen_name,
                parent=mother_name,
                size=size,
                is_migrant=is_migrant,
            )

    def _notify_death(self, cell_id: int) -> None:
        logger.debug(
            "Death: cell_id=%d",
            cell_id,
            extra={"event": "death"},
        )
        gen_name = ""
        if 0 <= cell_id < len(self.cells):
            gen_name = self.cells[cell_id].dem.gen_name
            if self.genebank.enabled:
                self.genebank.on_death(gen_name=gen_name, cell_id=cell_id)
        if self.recorder is not None:
            self.recorder.on_death(
                inst_exe=self.inst_exe, cell_id=cell_id, gen_name=gen_name
            )

    def _recorder_sample(self) -> None:
        if self.recorder is not None:
            self.recorder.maybe_sample(self.stats())

    def _maybe_auto_extract(self, name: str, genome: bytes) -> None:
        if not int(self.config.get("DiskBank", 0) or 0) or self.disk_bank is None:
            return
        gens = {g["name"]: g for g in self.genebank.list_genotypes()}
        g = gens.get(name)
        if g is None:
            return
        sav_min = int(self.config.get("SavMinNum", 10) or 10)
        if g["pop"] < sav_min and not g.get("permanent"):
            return
        # memory occupancy threshold (simplified)
        thr = float(self.config.get("SavThrMem", 0.02) or 0.02)
        prop = (g["size"] * max(1, g["pop"])) / max(1, self.config.soup_size)
        if prop < thr and g["pop"] < sav_min:
            return
        self.genebank.mark_permanent(name, genome)
        self._enqueue_extract(name, genome)

    def _enqueue_extract(self, name: str, genome: bytes) -> None:
        h = default_hash(genome)
        pop = 0
        for g in self.genebank.list_genotypes():
            if g["name"] == name:
                pop = g["pop"]
                break
        self.write_queue.enqueue(
            WriteJob(name=name, genome=genome, hash=h, permanent=True, pop=pop)
        )

    def start(self) -> None:
        self.stopped = False
        self._started = True
        self.inst_exe = 0
        self.budget_used = 0
        self.counters = {
            "births": 0,
            "deaths": 0,
            "mal_fail": 0,
            "reap_attempts": 0,
        }
        self._until_births = None
        self.cells.clear()
        self.queues = CellQueues()
        self.mem = SoupMemory(soup_size=self.config.soup_size)
        self.genebank = self._make_genebank()
        seed = self.config.seed or 1
        self.rng.tsrand(seed)
        _ = self.rng.tlrand()
        inoculum_mod.inoculate(self)
        self.update_average_size()
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
        rates = calc_flaw_rates(
            num_cells=self.queues.num_cells,
            average_size=self.average_size,
            soup_size=self.config.soup_size,
            gen_per_bkg_mut=int(v.get("GenPerBkgMut") or 0),
            gen_per_mov_mut=int(v.get("GenPerMovMut") or 0),
            gen_per_flaw=int(v.get("GenPerFlaw") or 0),
        )
        self.rate_mut = rates.rate_mut
        self.rate_mov_mut = rates.rate_mov_mut
        self.rate_flaw = rates.rate_flaw
        self.count_mut = 0
        self.count_mov_mut = 0
        self.count_flaw = 0

    def update_average_size(self) -> None:
        alive = [c for c in self.cells if c.alive]
        if not alive:
            new_avg = 0
        else:
            new_avg = max(1, sum(c.mm_s for c in alive) // len(alive))
        changed = new_avg != self.average_size
        self.average_size = new_avg
        # Recompute when AverageSize changes or soup is empty (rates → 0).
        # SoupSize is immutable in MVP; GenPer* changes go through set_parameter.
        if changed or self.queues.num_cells == 0:
            self._recompute_rates()

    def reap_one(self) -> bool:
        self.counters["reap_attempts"] = self.counters.get("reap_attempts", 0) + 1
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
        self.update_average_size()

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

    def _boundary_flush(self) -> None:
        self._steps_since_flush += 1
        if self._steps_since_flush >= 64 or self.write_queue.pending_count() > 32:
            self.write_queue.flush()
            self._steps_since_flush = 0

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
        self._boundary_flush()
        self._recorder_sample()
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
        if until_births is not None and self.counters.get("births", 0) >= until_births:
            self._recorder_sample()
            return self.stats()
        self._run_started = time.perf_counter()
        self._until_births = until_births
        try:
            while not self.stopped:
                self._check_limits(force=True)
                if (
                    until_births is not None
                    and self.counters.get("births", 0) >= until_births
                ):
                    break
                before = self.inst_exe
                slicer_mod.slicer_step(self)
                if self.inst_exe == before:
                    break
                if self.inst_exe % 64 == 0:
                    self._boundary_flush()
                    self._recorder_sample()
        finally:
            self._until_births = None
        self.write_queue.flush()
        self._recorder_sample()
        return self.stats()

    def step_until(
        self,
        predicate: Callable[[TierraVM], bool],
        *,
        max_instructions: int | None = None,
        wall_time: float | None = None,
    ) -> dict[str, Any]:
        """Run until predicate or sandbox/local limits fire."""
        self._require_started()
        cap_inst = max_instructions if max_instructions is not None else self.limits.max_instructions
        cap_wall = wall_time if wall_time is not None else self.limits.wall_time_s
        start_budget = self.budget_used
        start_wall = time.perf_counter()
        reason = "predicate"
        while not self.stopped:
            if predicate(self):
                reason = "predicate"
                break
            if self.budget_used - start_budget >= cap_inst:
                reason = "limit"
                break
            if time.perf_counter() - start_wall >= cap_wall:
                reason = "limit"
                break
            before = self.inst_exe
            try:
                self._check_limits(force=True)
            except SandboxLimitError:
                reason = "limit"
                break
            slicer_mod.slicer_step(self)
            if self.inst_exe == before:
                reason = "idle"
                break
        self._boundary_flush()
        self._recorder_sample()
        return {**self.stats(), "stop_reason": reason}

    def stop(self) -> None:
        self.write_queue.flush()
        self._recorder_sample()
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

    def get_parameter(self, name: str) -> Any:
        if name not in _PARAM_WHITELIST and name not in self.config.values:
            raise ConfigError(f"parameter not available: {name}")
        return self.config.get(name)

    def set_parameter(self, name: str, value: Any) -> None:
        if name not in _PARAM_WHITELIST:
            raise ConfigError(f"parameter not in whitelist: {name}")
        self.config.values[name] = value
        if name.startswith("GenPer") or name == "MutBitProp":
            self._recompute_rates()
        logger.info(
            "Parameter set %s=%s",
            name,
            value,
            extra={"event": "set_parameter"},
        )

    def genotypes(self) -> list[dict[str, Any]]:
        return self.genebank.list_genotypes()

    def save_genotype(self, name: str) -> None:
        genome = None
        if isinstance(self.genebank, RamBanker):
            genome = self.genebank.find_live_genome(
                name, cells=self.cells, soup=self.mem.soup
            )
        if genome is None:
            genome = self.genebank.get_genome_bytes(name)
        if genome is None:
            raise StateError(f"genotype not found: {name}")
        self.genebank.mark_permanent(name, genome)
        if self.disk_bank is None:
            raise StateError("DiskBank not attached")
        self._enqueue_extract(name, genome)
        self.write_queue.flush()

    def inject(self, name: str, n: int = 1) -> list[int]:
        if name not in self._genomes and self.disk_bank is not None:
            code = list(self.disk_bank.load_genome(name))
            self._genomes[name] = code
        if name not in self._genomes:
            g = self.genebank.get_genome_bytes(name)
            if g is None:
                raise StateError(f"cannot inject unknown genotype: {name}")
            self._genomes[name] = list(g)
        ids: list[int] = []
        code = self._genomes[name]
        size = len(code)
        for _ in range(max(1, n)):
            while self.queues.num_cells >= self.limits.max_cells:
                if not self.reap_one():
                    break
            got = self.mem.mem_alloc(size, -1, 0)
            if got < 0:
                if not self.reap_one():
                    break
                got = self.mem.mem_alloc(size, -1, 0)
            if got < 0:
                break
            for j, op in enumerate(code):
                self.mem.soup[self.mem.ad(got + j)] = op & 0xFF
            cell = self.alloc_cell()
            if cell is None:
                self.mem.mem_dealloc(got, size)
                break
            cell.alive = True
            cell.mm_p = got
            cell.mm_s = size
            cell.cpu.ip = got
            cell.dem.gen_name = name
            cell.dem.gen_size = size
            cell.dem.mg_p = 0
            cell.dem.mg_s = size
            cell.dem.genome_hash_dirty = True
            self.queues.ent_bot_slicer(self.cells, cell.cell_id)
            self.queues.ent_bot_reaper(self.cells, cell.cell_id)
            self.queues.num_cells += 1
            self.counters["births"] = self.counters.get("births", 0) + 1
            self._notify_birth(cell.cell_id, size, is_migrant=False)
            ids.append(cell.cell_id)
        self.update_average_size()
        logger.info(
            "Inject name=%s n=%d placed=%d",
            name,
            n,
            len(ids),
            extra={"event": "genebank_inject"},
        )
        return ids

    def plan(self) -> dict[str, Any]:
        return self.observer.plan(self)

    def overview(self) -> list[dict[str, Any]]:
        return self.observer.overview(self)

    def histogram(self, kind: str = "size") -> dict[str, Any]:
        return self.observer.histogram(self, kind=kind)

    def genome_at(self, addr: int) -> bytes | None:
        return self.observer.genome_at(self, addr)

    def genome_of(self, name: str) -> bytes | None:
        return self.observer.genome_of(self, name)

    def cell_snapshot(self, cell_id: int) -> dict[str, Any] | None:
        return self.observer.cell_snapshot(self, cell_id)

    def poll_immigrants(self) -> list[int]:
        if self._transport is None:
            return []
        from pytierra.services.net.migration import accept_immigrant

        placed: list[int] = []
        for genome, meta in self._transport.poll_immigrants(self.node_id):
            cid = accept_immigrant(self, genome, meta)
            if cid is not None:
                placed.append(cid)
        return placed

    def emigrate(self, cell_id: int, *, dest: str) -> bool:
        if self._transport is None:
            raise StateError("no transport attached")
        from pytierra.services.net.migration import offer_emigrant

        return offer_emigrant(self, cell_id, self._transport, dest=dest)

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
            "mal_fail": self.counters.get("mal_fail", 0),
            "reap_attempts": self.counters.get("reap_attempts", 0),
            "free_mem": self.mem.free_bytes(),
            "AverageSize": self.average_size,
            "budget_used": self.budget_used,
            "rate_mut": self.rate_mut,
            "rate_mov_mut": self.rate_mov_mut,
            "rate_flaw": self.rate_flaw,
        }

    def snapshot(self) -> dict[str, Any]:
        return snapshot_mod.take_snapshot(self)

    def restore(self, snap: dict[str, Any]) -> None:
        snapshot_mod.restore_snapshot(self, snap)
