# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""ALU / register ops."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytierra.models.isa_state import InstState
    from pytierra.services.vm.context import VMContext


def _write_dreg(ctx: VMContext, is_: InstState, value: int) -> None:
    cpu = ctx.ce.cpu
    if is_.dreg_i == -2:
        cpu.ip = ctx.mem.ad(value)
    elif is_.dreg_i >= 0:
        cpu.re[is_.dreg_i] = value


def _read_dreg(ctx: VMContext, is_: InstState) -> int:
    cpu = ctx.ce.cpu
    if is_.dreg_i == -2:
        return cpu.ip
    if is_.dreg_i >= 0:
        return cpu.re[is_.dreg_i]
    return 0


def do_flags(ctx: VMContext, is_: InstState) -> None:
    v = _read_dreg(ctx, is_)
    ctx.ce.cpu.fl.E = 0
    ctx.ce.cpu.fl.S = 1 if v < 0 else 0
    ctx.ce.cpu.fl.Z = 1 if v == 0 else 0


def do_mods(ctx: VMContext, is_: InstState) -> None:
    if is_.dmod and is_.dreg_i >= 0:
        ctx.ce.cpu.re[is_.dreg_i] %= is_.dmod
    elif is_.dmod and is_.dreg_i == -2:
        ctx.ce.cpu.ip = ctx.mem.ad(ctx.ce.cpu.ip)
    elif is_.dran and is_.dreg_i >= 0:
        v = ctx.ce.cpu.re[is_.dreg_i]
        if v > is_.dran or v < -is_.dran:
            ctx.ce.cpu.re[is_.dreg_i] = 0
    is_.dmod = is_.dran = 0


def nop(ctx: VMContext, is_: InstState) -> None:
    ctx.ce.cpu.fl.E = ctx.ce.cpu.fl.S = ctx.ce.cpu.fl.Z = 0


def not0(ctx: VMContext, is_: InstState) -> None:
    cpu = ctx.ce.cpu
    if is_.dreg_i >= 0:
        cpu.re[is_.dreg_i] ^= 1 + ctx.flaw()
    do_mods(ctx, is_)
    do_flags(ctx, is_)


def shl(ctx: VMContext, is_: InstState) -> None:
    if is_.dreg_i >= 0:
        ctx.ce.cpu.re[is_.dreg_i] <<= 1 + ctx.flaw()
    do_mods(ctx, is_)
    do_flags(ctx, is_)


def math_add(ctx: VMContext, is_: InstState) -> None:
    _write_dreg(ctx, is_, is_.sval + is_.sval2)
    do_mods(ctx, is_)
    do_flags(ctx, is_)


def movdd(ctx: VMContext, is_: InstState) -> None:
    _write_dreg(ctx, is_, is_.sval + ctx.flaw())
    do_mods(ctx, is_)
    do_flags(ctx, is_)


def skip_ifz(ctx: VMContext, is_: InstState) -> None:
    if not is_.sval:
        is_.iip = int(is_.sval2)
    ctx.ce.cpu.fl.E = ctx.ce.cpu.fl.S = ctx.ce.cpu.fl.Z = 0
