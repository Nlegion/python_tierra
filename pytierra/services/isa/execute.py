# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Dispatch execute for gb0 opcodes."""

from __future__ import annotations

from typing import Callable

from pytierra.models.genome import InstDef
from pytierra.models.isa_state import InstState
from pytierra.services.isa import ops_alu, ops_ctrl, ops_mem, ops_repro, ops_stack
from pytierra.services.vm.context import VMContext

ExecFn = Callable[[VMContext, InstState], None]

_EXEC: dict[str, ExecFn] = {
    "nop": ops_alu.nop,
    "nop0": ops_alu.nop,
    "nop1": ops_alu.nop,
    "not0": ops_alu.not0,
    "shl": ops_alu.shl,
    "zero": ops_alu.movdd,
    "movDC": ops_alu.movdd,
    "movBA": ops_alu.movdd,
    "movdd": ops_alu.movdd,
    "ifz": ops_alu.skip_ifz,
    "incA": ops_alu.math_add,
    "incB": ops_alu.math_add,
    "incC": ops_alu.math_add,
    "decC": ops_alu.math_add,
    "subCAB": ops_alu.math_add,
    "subAAC": ops_alu.math_add,
    "math": ops_alu.math_add,
    "add": ops_alu.math_add,
    "push": ops_stack.push,
    "pushA": ops_stack.push,
    "pushB": ops_stack.push,
    "pushC": ops_stack.push,
    "pushD": ops_stack.push,
    "pop": ops_stack.pop,
    "popA": ops_stack.pop,
    "popB": ops_stack.pop,
    "popC": ops_stack.pop,
    "popD": ops_stack.pop,
    "ret": ops_stack.pop,
    "movii": ops_mem.movii,
    "adr": ops_ctrl.adr,
    "adrb": ops_ctrl.adr,
    "adrf": ops_ctrl.adr,
    "adro": ops_ctrl.adr,
    "jmpo": ops_ctrl.adr,
    "jmpb": ops_ctrl.adr,
    "call": ops_ctrl.tcall,
    "tcall": ops_ctrl.tcall,
    "mal": ops_repro.malchm,
    "malchm": ops_repro.malchm,
    "divide": ops_repro.divide,
}


def execute(ctx: VMContext, idef: InstDef, is_: InstState) -> None:
    fn = _EXEC.get(idef.mnemonic) or _EXEC.get(idef.execute)
    if fn is None:
        ctx.ce.cpu.fl.E = 1
        return
    fn(ctx, is_)
