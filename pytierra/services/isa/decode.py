# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Decode gb0 instructions into InstState."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytierra.core.settings.constants import NUMREG
from pytierra.models.genome import InstDef
from pytierra.models.isa_state import InstState

if TYPE_CHECKING:
    from pytierra.services.vm.context import VMContext


def mo(n: int, m: int) -> int:
    if m <= 0:
        return 0
    return ((n % m) + m) % m


def _reg(idef: InstDef, idx: int) -> int:
    if idx < len(idef.regs):
        return idef.regs[idx]
    return 0


def template_size(ctx: VMContext, ip: int) -> int:
    a = ctx.mem.ad(ip + 1)
    s = 0
    while True:
        b = ctx.mem.soup[ctx.mem.ad(a + s)]
        if b != ctx.nop0 and b != ctx.nop1:
            break
        s += 1
        if s > ctx.mem.soup_size:
            break
    return s


def decode(ctx: VMContext, idef: InstDef) -> InstState:
    is_ = InstState()
    is_.iip = 1
    cpu = ctx.ce.cpu
    mn = idef.mnemonic
    dec = idef.decode

    if dec == "pnop":
        return is_

    if dec == "dec1d":
        tval = ctx.flaw() + _reg(idef, 0)
        is_.dreg_i = mo(tval, NUMREG)
        if mn == "ret":
            is_.dreg_i = -2
            is_.iip = 0
        return is_

    if dec == "dec1s":
        tval = ctx.flaw() + _reg(idef, 0)
        is_.sval = cpu.re[mo(tval, NUMREG)] + ctx.flaw()
        return is_

    if dec == "dec1d1s":
        t0 = ctx.flaw() + _reg(idef, 0)
        t1 = ctx.flaw() + _reg(idef, 1)
        is_.dreg_i = mo(t0, NUMREG)
        is_.sval = cpu.re[mo(t1, NUMREG)] + ctx.flaw()
        if mn.startswith("inc"):
            is_.sval2 = 1
        elif mn.startswith("dec"):
            is_.sval2 = -1
        elif mn == "zero":
            is_.sval = 0
        return is_

    if dec == "dec1d2s":
        t0 = ctx.flaw() + _reg(idef, 0)
        t1 = ctx.flaw() + _reg(idef, 1)
        t2 = ctx.flaw() + _reg(idef, 2)
        is_.dreg_i = mo(t0, NUMREG)
        is_.sval = cpu.re[mo(t1, NUMREG)] + ctx.flaw()
        is_.sval2 = cpu.re[mo(t2, NUMREG)]
        if mn.startswith("sub"):
            is_.sval2 = -is_.sval2
        return is_

    if dec == "dec2s":
        t0 = ctx.flaw() + _reg(idef, 0)
        t1 = ctx.flaw() + _reg(idef, 1)
        is_.sval = cpu.re[mo(t0, NUMREG)] + ctx.flaw()
        is_.sval2 = cpu.re[mo(t1, NUMREG)] + ctx.flaw()
        if mn == "ifz" or (len(mn) > 2 and mn[2] == "z"):
            is_.sval = 1 if is_.sval == 0 else 0
            is_.sval2 = 2
        if mn == "divide":
            is_.mode = 2
            if idef.flag_C:
                is_.sval = 0
        return is_

    if dec == "dec1d3s":
        t0 = ctx.flaw() + _reg(idef, 0)
        t1 = ctx.flaw() + _reg(idef, 1)
        t2 = ctx.flaw() + (_reg(idef, 2) if _reg(idef, 2) >= 0 else 0)
        t3 = ctx.flaw() + _reg(idef, 3)
        is_.dreg_i = mo(t0, NUMREG)
        is_.sval = cpu.re[mo(t1, NUMREG)]
        is_.sval2 = cpu.re[mo(t2, NUMREG)] if _reg(idef, 2) >= 0 else 0
        is_.sval3 = cpu.re[mo(t3, NUMREG)]
        is_.dran = ctx.mem.soup_size
        if mn.startswith("mal"):
            is_.mode2 = ctx.mal_mode
            is_.mode = ctx.mem_mode_prot
        return is_

    if dec == "pmovii":
        t0 = ctx.flaw() + _reg(idef, 0)
        t1 = ctx.flaw() + _reg(idef, 1)
        t0 = cpu.re[mo(t0, NUMREG)] + ctx.flaw()
        t1 = cpu.re[mo(t1, NUMREG)] + ctx.flaw()
        is_.dval = ctx.mem.ad(t0)
        is_.sval = ctx.mem.ad(t1)
        return is_

    if dec in ("decadr", "decjmp", "ptcall"):
        s = template_size(ctx, cpu.ip)
        a = ctx.mem.ad(cpu.ip + 1)
        slim = ctx.search_limit_abs()
        if dec == "ptcall":
            is_.dreg_i = -2
            is_.sval = ctx.mem.ad(cpu.ip + s + 1)
            is_.sval2 = s
            is_.sval3 = slim
            is_.dmod = ctx.mem.soup_size
            is_.dval = ctx.mem.ad(a + s + 1)
            is_.dval2 = ctx.mem.ad(a - s - 1)
            is_.mode = 0
            is_.mode2 = 1
            is_.iip = 0
            return is_
        if dec == "decjmp":
            tval = ctx.flaw() + _reg(idef, 0)
            tval = cpu.re[mo(tval, NUMREG)] + ctx.flaw()
            is_.sval = ctx.mem.ad(tval)
            is_.dreg_i = -2
            is_.sval2 = s
            is_.sval3 = slim
            is_.dval = ctx.mem.ad(a + s + 1)
            is_.dval2 = ctx.mem.ad(a - s - 1)
            is_.dmod = ctx.mem.soup_size
            is_.iip = 0
            if mn.endswith("o") or mn == "jmpo":
                is_.mode, is_.mode2 = 0, 1
            elif mn.endswith("b"):
                is_.mode, is_.mode2 = 2, 2
            elif mn.endswith("f"):
                is_.mode, is_.mode2 = 1, 1
            return is_
        # decadr
        if s:
            is_.dreg_i = mo(ctx.flaw() + _reg(idef, 0), NUMREG)
            r1 = _reg(idef, 1)
            r2 = _reg(idef, 2)
            is_.dreg2_i = mo(ctx.flaw() + r1, NUMREG) if r1 >= 0 else -3
            is_.dreg3_i = mo(ctx.flaw() + r2, NUMREG) if r2 >= 0 else -3
        else:
            is_.dreg_i = is_.dreg2_i = is_.dreg3_i = -3
        if idef.flag_C:
            if _reg(idef, 0) < 0:
                is_.dreg_i = -3
            if len(idef.regs) > 1 and idef.regs[1] < 0:
                is_.dreg2_i = -3
            if len(idef.regs) > 2 and idef.regs[2] < 0:
                is_.dreg3_i = -3
        is_.sval2 = s
        is_.dmod = ctx.mem.soup_size
        is_.dmod3 = ctx.mem.soup_size
        is_.dran2 = ctx.mem.soup_size
        is_.dval = ctx.mem.ad(a + s + 1)
        is_.dval2 = ctx.mem.ad(a - s - 1)
        is_.sval3 = slim
        is_.iip = s + 1
        if mn.endswith("o"):
            is_.mode, is_.mode2 = 0, 1
        elif mn.endswith("b"):
            is_.mode, is_.mode2 = 2, 2
        elif mn.endswith("f"):
            is_.mode, is_.mode2 = 1, 1
        return is_

    return is_
