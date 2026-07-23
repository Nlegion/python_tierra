# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from pathlib import Path

import pytest

from pytierra.adapters.filesystem.soup_in import parse_soup_in
from pytierra.core.errors import ConfigError, InternalError, SandboxLimitError, StateError
from pytierra.models.limits import SandboxLimits
from pytierra.services.vm.service import TierraVM

TIERRA = Path(__file__).resolve().parents[1] / "legacy" / "tierra"
GB0 = TIERRA / "gb0"


def test_step_before_start_raises(make_vm):
    vm = make_vm()
    with pytest.raises(StateError):
        vm.step(1)


def test_max_instructions_budget_and_continue(make_vm):
    vm = make_vm(max_instructions=200)
    vm.start()
    with pytest.raises(SandboxLimitError) as ei:
        vm.run()
    assert ei.value.kind == "max_instructions"
    vm.set_limits(max_instructions=5000)
    n = vm.step(50)
    assert n > 0


def test_bad_restore_missing_key(make_vm):
    vm = make_vm()
    vm.start()
    with pytest.raises(StateError):
        vm.restore({"soup": vm.mem.snapshot()})


def test_bad_restore_corrupt_cell(make_vm):
    vm = make_vm()
    vm.start()
    snap = vm.snapshot()
    snap["cells"] = [{"cell_id": 0}]  # missing fields → InternalError
    with pytest.raises(InternalError):
        vm.restore(snap)


def test_max_cells_soft_fail_step_continues(make_vm):
    vm = make_vm(max_cells=1, max_instructions=200_000)
    vm.start()
    assert vm.queues.num_cells == 1
    # Run past first replication attempt; birth must be skipped, step continues
    before = vm.inst_exe
    try:
        for _ in range(400):
            vm.step(n=500)
            if vm.budget_used > 50_000:
                break
    except SandboxLimitError:
        pass
    assert vm.inst_exe > before
    assert vm.queues.num_cells == 1
    assert vm.counters.get("births", 0) == 0


def test_no_inoculum_config_error(opcode_map):
    cfg = parse_soup_in("SoupSize = 6000\nNumCells = 0\nseed = 1\n")
    vm = TierraVM(
        config=cfg,
        asset_root=TIERRA,
        opcode_map=opcode_map,
        limits=SandboxLimits(max_instructions=1000),
    )
    with pytest.raises(ConfigError):
        vm.start()


def test_from_config_dict(opcode_map):
    vm = TierraVM.from_config(
        {
            "SoupSize": 6000,
            "NumCells": 1,
            "seed": 1,
            "GenebankPath": "gb0/",
            "IMapFile": "opcode.map",
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
            "GenPerBkgMut": 0,
            "GenPerFlaw": 0,
            "GenPerMovMut": 0,
            "GenPerDivMut": 0,
            "inoculum": ["0080aaa"],
        },
        asset_root=TIERRA,
        limits=SandboxLimits(max_instructions=10_000),
    )
    vm.start()
    assert vm.step(10) > 0


def test_stop_and_stats(make_vm):
    vm = make_vm()
    vm.start()
    vm.step(20)
    vm.stop()
    assert vm.step(10) == 0
    s = vm.stats()
    assert s["InstExe"] > 0
