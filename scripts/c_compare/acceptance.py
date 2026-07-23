# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Shared mut=0 acceptance config for golden / C-compare export."""

from __future__ import annotations

# Exact InstExe at first 0080aaa birth (seed=42, SoupSize=6000, GeneBnker=0).
# Measured with run(until_births=1) stopping on the birth instruction (per-insn check).
GOLDEN_FIRST_BIRTH_INST_EXE = 827


def acceptance_config_text(*, soup_size: int = 6000, seed: int = 42) -> str:
    return f"""
SoupSize = {soup_size}
SliceSize = 25
SliceStyle = 2
SlicFixFrac = 0
SlicRanFrac = 2
MalMode = 1
MalTol = 20
SearchLimit = 5
MovPropThrDiv = .7
MinCellSize = 12
MinGenMemSiz = 12
MinTemplSize = 1
NumCells = 1
NumCellsMin = 1
GenebankPath = gb0/
IMapFile = opcode.map
seed = {seed}
GenPerBkgMut = 0
GenPerFlaw = 0
GenPerMovMut = 0
GenPerDivMut = 0
GenPerCroInsSamSiz = 0
GenPerInsIns = 0
GenPerDelIns = 0
GenPerCroIns = 0
GenPerDelSeg = 0
GenPerInsSeg = 0
GenPerCroSeg = 0
MutBitProp = 0.2
MemModeFree = 0
MemModeMine = 0
MemModeProt = 2
center
0080aaa
"""


def acceptance_config_dict(*, soup_size: int = 6000, seed: int = 42) -> dict:
    """Dict form for TierraVM.from_config (same semantics as acceptance_config_text)."""
    return {
        "SoupSize": soup_size,
        "SliceSize": 25,
        "SliceStyle": 2,
        "SlicFixFrac": 0,
        "SlicRanFrac": 2,
        "MalMode": 1,
        "MalTol": 20,
        "SearchLimit": 5,
        "MovPropThrDiv": 0.7,
        "MinCellSize": 12,
        "MinGenMemSiz": 12,
        "MinTemplSize": 1,
        "NumCells": 1,
        "NumCellsMin": 1,
        "GenebankPath": "gb0/",
        "IMapFile": "opcode.map",
        "seed": seed,
        "GenPerBkgMut": 0,
        "GenPerFlaw": 0,
        "GenPerMovMut": 0,
        "GenPerDivMut": 0,
        "GenPerCroInsSamSiz": 0,
        "GenPerInsIns": 0,
        "GenPerDelIns": 0,
        "GenPerCroIns": 0,
        "GenPerDelSeg": 0,
        "GenPerInsSeg": 0,
        "GenPerCroSeg": 0,
        "MutBitProp": 0.2,
        "MemModeFree": 0,
        "MemModeMine": 0,
        "MemModeProt": 2,
        "place_center": True,
        "inoculum": ["0080aaa"],
    }
