# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from pathlib import Path

import pytest

from pytierra.adapters.filesystem.soup_in import parse_soup_in
from pytierra.bootstrap.wiring import load_genomes_into_vm
from pytierra.core.errors import ConfigError
from pytierra.models.limits import SandboxLimits
from pytierra.services.vm.service import TierraVM

TIERRA = Path(__file__).resolve().parents[1] / "legacy" / "tierra"
GB0 = TIERRA / "gb0"


def test_two_inocula_different_gen_names(opcode_map):
    cfg = parse_soup_in(
        """
SoupSize = 6000
NumCells = 2
seed = 1
GenebankPath = gb0/
IMapFile = opcode.map
center
0080aaa
0021aaa
"""
    )
    vm = TierraVM(
        config=cfg,
        asset_root=TIERRA,
        opcode_map=opcode_map,
        limits=SandboxLimits(max_instructions=10_000),
    )
    load_genomes_into_vm(vm, GB0)
    assert "0021aaa" in vm._genomes
    vm.start()
    alive = [c for c in vm.cells if c.alive]
    assert len(alive) == 2
    names = {c.dem.gen_name for c in alive}
    assert "0080aaa" in names
    assert "0021aaa" in names


def test_inoculum_oom_raises_config_error(opcode_map):
    cfg = parse_soup_in(
        """
SoupSize = 50
NumCells = 2
seed = 1
GenebankPath = gb0/
IMapFile = opcode.map
0080aaa
"""
    )
    vm = TierraVM(
        config=cfg,
        asset_root=TIERRA,
        opcode_map=opcode_map,
        limits=SandboxLimits(max_instructions=1000, max_soup_size=10_000),
    )
    load_genomes_into_vm(vm, GB0)
    with pytest.raises(ConfigError, match="inoculum"):
        vm.start()
