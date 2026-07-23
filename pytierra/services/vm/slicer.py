# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Slicer / time-slice loop (no import of service.py)."""

from __future__ import annotations

from typing import Any

from pytierra.models.trace import TraceRecord
from pytierra.services.isa.decode import decode
from pytierra.services.isa.execute import execute
from pytierra.services.mutate import cosmic_mutate
from pytierra.services.vm.helpers import check_limits


def time_slice(vm: Any, ce: Any, size_slice: int) -> None:
    ctx = vm._make_ctx(ce)
    for _ in range(max(0, size_slice)):
        if vm.stopped or not ce.alive:
            break
        check_limits(
            vm.limits,
            budget_used=vm.budget_used,
            run_started=vm._run_started,
        )
        ip = ce.cpu.ip
        op = vm.mem.soup[vm.mem.ad(ip)] % vm.opcode_map.inst_num
        idef = vm.opcode_map.by_op[op]
        ctx.ce = ce
        ctx.count_mov_mut = vm.count_mov_mut
        ctx.count_flaw = vm.count_flaw
        is_ = decode(ctx, idef)
        execute(ctx, idef, is_)
        vm.count_mov_mut = ctx.count_mov_mut
        vm.count_flaw = ctx.count_flaw
        ce.cpu.ip = vm.mem.ad(ce.cpu.ip + is_.iip)
        ce.dem.inst += idef.cyc
        ce.dem.repinst += idef.cyc
        if ce.cpu.fl.E:
            ce.dem.flags += 1
        vm.inst_exe += 1
        vm.budget_used += 1
        if vm.trace.enabled:
            vm.trace.append(
                TraceRecord(
                    cycle=vm.inst_exe,
                    cell_id=ce.cell_id,
                    ip=ip,
                    opcode=op,
                    mnemonic=idef.mnemonic,
                    operands={"sval": is_.sval, "sval2": is_.sval2},
                    err="E" if ce.cpu.fl.E else None,
                )
            )
        if vm.rate_mut:
            vm.count_mut += 1
            if vm.count_mut >= vm.rate_mut:
                addr = cosmic_mutate(
                    vm.mem,
                    rng=vm.rng,
                    mut_bit_prop=float(vm.config.get("MutBitProp", 0.2)),
                    inst_num=vm.opcode_map.inst_num,
                    inst_bit_num=max(1, (vm.opcode_map.inst_num - 1).bit_length()),
                )
                from pytierra.services.genebank.dirty import mark_cells_dirty_at

                mark_cells_dirty_at(vm.cells, addr)
                vm.counters["TotMut"] = vm.counters.get("TotMut", 0) + 1
                vm.count_mut = vm.rng.tlrand() % vm.rate_mut
        until = getattr(vm, "_until_births", None)
        if until is not None and vm.counters.get("births", 0) >= until:
            break


def slicer_step(vm: Any) -> None:
    if vm.queues.num_cells <= 0 or vm.queues.this_slice < 0:
        return
    ce = vm.cells[vm.queues.this_slice]
    if not ce.alive:
        vm.queues.incr_slice_queue(vm.cells)
        return
    v = vm.config.values
    if int(v.get("SizDepSlice", 0)):
        base = ce.mm_s
    else:
        base = int(v.get("SliceSize", 25))
    fix = float(v.get("SlicFixFrac", 0.0))
    ran = float(v.get("SlicRanFrac", 2.0))
    size_slice = int(fix * base) + (vm.rng.tlrand() % (int(ran * base) + 1))
    if vm.config.slice_style == 0:
        size_slice = base
    # Avoid zero-length slices (would stall run()/step when InstExe does not advance).
    size_slice = max(1, size_slice)
    time_slice(vm, ce, size_slice)
    vm.queues.incr_slice_queue(vm.cells)
