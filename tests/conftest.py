# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from pytierra.adapters.filesystem.genome import load_opcode_map
from pytierra.adapters.filesystem.soup_in import parse_soup_in
from pytierra.bootstrap.wiring import load_genomes_into_vm
from pytierra.models.limits import SandboxLimits
from pytierra.services.vm.service import TierraVM

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.c_compare.acceptance import (  # noqa: E402
    GOLDEN_FIRST_BIRTH_INST_EXE,
    acceptance_config_text,
)

TIERRA = ROOT / "legacy" / "tierra"
GB0 = TIERRA / "gb0"

__all__ = [
    "GOLDEN_FIRST_BIRTH_INST_EXE",
    "acceptance_config_text",
    "ROOT",
    "TIERRA",
    "GB0",
]


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
