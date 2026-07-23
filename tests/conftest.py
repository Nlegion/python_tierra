# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from __future__ import annotations

from pathlib import Path

import pytest

from pytierra.adapters.filesystem.genome import load_opcode_map
from pytierra.adapters.filesystem.soup_in import parse_soup_in
from pytierra.bootstrap.wiring import load_genomes_into_vm
from pytierra.models.limits import SandboxLimits
from pytierra.services.vm.service import TierraVM

ROOT = Path(__file__).resolve().parents[1]
TIERRA = ROOT / "legacy" / "tierra"
GB0 = TIERRA / "gb0"


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


@pytest.fixture
def opcode_map():
    return load_opcode_map(GB0 / "opcode.map")


@pytest.fixture
def make_vm(opcode_map):
    def _make(**limit_kw) -> TierraVM:
        cfg = parse_soup_in(acceptance_config_text())
        limits = SandboxLimits(
            max_instructions=limit_kw.pop("max_instructions", 500_000),
            wall_time_s=limit_kw.pop("wall_time_s", 60.0),
            max_cells=limit_kw.pop("max_cells", 1000),
            **limit_kw,
        )
        vm = TierraVM(
            config=cfg,
            asset_root=TIERRA,
            opcode_map=opcode_map,
            limits=limits,
        )
        load_genomes_into_vm(vm, GB0)
        return vm

    return _make
