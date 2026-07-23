# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Control flow: adr / jmp / call."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytierra.services.isa.ops_alu import do_mods
from pytierra.services.isa.ops_stack import push
from pytierra.services.isa.template import ctemplate

if TYPE_CHECKING:
    from pytierra.models.isa_state import InstState
    from pytierra.services.vm.context import VMContext


def _adr_find(ctx: VMContext, is_: InstState) -> None:
    ce = ctx.ce
    if not is_.sval2:
        if is_.dreg_i >= 0:
            ce.cpu.re[is_.dreg_i] = is_.sval
        is_.dmod = is_.dran = 0
        return
    direction = "o"
    if is_.mode == 1:
        direction = "f"
    elif is_.mode == 2:
        direction = "b"
    adrt, mode_found, _dist = ctemplate(
        ctx.mem,
        ip=ce.cpu.ip,
        f_start=is_.dval,
        b_start=is_.dval2,
        slim=is_.sval3,
        tz=is_.sval2,
        direction=direction,
        nop0=ctx.nop0,
        nop1=ctx.nop1,
        nop_s=ctx.nop_s,
        min_templ_size=ctx.min_templ_size,
        mode_pref=is_.mode2,
    )
    if adrt < 0:
        is_.iip = is_.sval2 + 1
        ce.cpu.fl.E = 1
        is_.dmod = is_.dran = 0
        return
    if is_.dreg3_i >= 0:
        ce.cpu.re[is_.dreg3_i] = is_.sval3
    if is_.dreg2_i >= 0:
        ce.cpu.re[is_.dreg2_i] = is_.sval2
        if is_.dran2:
            pass
    if is_.dreg_i == -2:
        ce.cpu.ip = ctx.mem.ad(adrt)
    elif is_.dreg_i >= 0:
        ce.cpu.re[is_.dreg_i] = adrt
        do_mods(ctx, is_)
    ce.cpu.fl.E = ce.cpu.fl.S = ce.cpu.fl.Z = 0
    is_.extras["mode_found"] = mode_found


def adr(ctx: VMContext, is_: InstState) -> None:
    _adr_find(ctx, is_)


def tcall(ctx: VMContext, is_: InstState) -> None:
    _adr_find(ctx, is_)
    if not ctx.ce.cpu.fl.E:
        push(ctx, is_)
