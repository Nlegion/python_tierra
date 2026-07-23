# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Genome and opcode-map models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InstDef:
    op: int
    cyc: int
    mnemonic: str
    regs: list[int]
    flag_C: bool = False
    decode: str = ""
    execute: str = ""


@dataclass
class OpcodeMap:
    by_op: list[InstDef] = field(default_factory=list)
    by_name: dict[str, InstDef] = field(default_factory=dict)
    nop0: int = 0
    nop1: int = 1

    @property
    def inst_num(self) -> int:
        return len(self.by_op)

    @property
    def nop_s(self) -> int:
        return self.nop0 + self.nop1


@dataclass
class GenomeMeta:
    genotype: str = ""
    header_lines: list[str] = field(default_factory=list)
    ploidy: int = 1


@dataclass
class Genome:
    meta: GenomeMeta
    code: list[int]
