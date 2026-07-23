# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Stack ops."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytierra.core.settings.constants import STACK_SIZE
from pytierra.services.isa.ops_alu import do_flags, do_mods

if TYPE_CHECKING:
    from pytierra.models.isa_state import InstState
    from pytierra.services.vm.context import VMContext


def push(ctx: VMContext, is_: InstState) -> None:
    cpu = ctx.ce.cpu
    cpu.sp = (cpu.sp + 1) % STACK_SIZE
    cpu.st[cpu.sp] = is_.sval + ctx.flaw()
    cpu.fl.E = cpu.fl.S = cpu.fl.Z = 0


def pop(ctx: VMContext, is_: InstState) -> None:
    cpu = ctx.ce.cpu
    adr1 = cpu.st[cpu.sp] + ctx.flaw()
    if is_.dreg_i == -2:
        cpu.ip = ctx.mem.ad(adr1)
    elif is_.dreg_i >= 0:
        cpu.re[is_.dreg_i] = adr1
    if cpu.sp == 0:
        cpu.sp = STACK_SIZE - 1
    else:
        cpu.sp -= 1
    do_mods(ctx, is_)
    do_flags(ctx, is_)
