# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Immigrant inject / emigrant extract helpers (orchestrated by TierraVM)."""

from __future__ import annotations

from typing import Any


def offer_emigrant(vm: Any, cell_id: int, transport: Any, *, dest: str) -> bool:
    if cell_id < 0 or cell_id >= len(vm.cells):
        return False
    c = vm.cells[cell_id]
    if not c.alive:
        return False
    g0 = c.mm_p + c.dem.mg_p
    gsz = c.dem.mg_s or c.mm_s
    genome = bytes(vm.mem.soup[g0 : g0 + gsz])
    meta = {"gen_name": c.dem.gen_name, "size": gsz, "src": getattr(vm, "node_id", "a")}
    if getattr(vm, "genebank", None) is not None and vm.genebank.enabled:
        vm.genebank.mark_permanent(c.dem.gen_name, genome)
        if getattr(vm, "disk_bank", None) is not None:
            vm._enqueue_extract(c.dem.gen_name, genome)
    transport.offer_emigrant(genome, meta, dest=dest)
    return True


def accept_immigrant(vm: Any, genome: bytes, meta: dict[str, Any] | None = None) -> int | None:
    """Place immigrant; may reap to make space. Returns cell_id or None."""
    meta = meta or {}
    size = len(genome)
    # soft max_cells / soup pressure
    while vm.queues.num_cells >= vm.limits.max_cells:
        if not vm.reap_one():
            vm.counters["rejected_immigrants"] = vm.counters.get("rejected_immigrants", 0) + 1
            return None
    # try allocate; reap if needed
    for _ in range(8):
        got = vm.mem.mem_alloc(size, -1, 0)
        if got >= 0:
            break
        if not vm.reap_one():
            vm.counters["rejected_immigrants"] = vm.counters.get("rejected_immigrants", 0) + 1
            return None
    else:
        vm.counters["rejected_immigrants"] = vm.counters.get("rejected_immigrants", 0) + 1
        return None
    for j, op in enumerate(genome):
        vm.mem.soup[vm.mem.ad(got + j)] = op & 0xFF
    cell = vm.alloc_cell()
    if cell is None:
        vm.mem.mem_dealloc(got, size)
        vm.counters["rejected_immigrants"] = vm.counters.get("rejected_immigrants", 0) + 1
        return None
    cell.alive = True
    cell.mm_p = got
    cell.mm_s = size
    cell.cpu.ip = got
    cell.dem.mg_p = 0
    cell.dem.mg_s = size
    cell.dem.gen_size = size
    cell.dem.gen_name = str(meta.get("gen_name", f"{size:04d}???"))
    cell.dem.genome_hash_dirty = True
    vm.queues.ent_bot_slicer(vm.cells, cell.cell_id)
    vm.queues.ent_bot_reaper(vm.cells, cell.cell_id)
    vm.queues.num_cells += 1
    vm.counters["births"] = vm.counters.get("births", 0) + 1
    vm.update_average_size()
    vm._notify_birth(cell.cell_id, size, is_migrant=True)
    return cell.cell_id
