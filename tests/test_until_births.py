# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Exact until_births stop (per-instruction in time_slice)."""

from pytierra.adapters.filesystem.soup_in import parse_soup_in
from pytierra.bootstrap.wiring import load_genomes_into_vm
from pytierra.models.limits import SandboxLimits
from pytierra.services.vm.service import TierraVM
from tests.conftest import GB0, TIERRA, acceptance_config_text


def _make_vm(opcode_map, *, seed: int = 42):
    cfg = parse_soup_in(acceptance_config_text(seed=seed))
    vm = TierraVM(
        config=cfg,
        asset_root=TIERRA,
        opcode_map=opcode_map,
        limits=SandboxLimits(max_instructions=200_000, wall_time_s=60),
    )
    load_genomes_into_vm(vm, GB0)
    return vm


def test_run_until_births_exact(opcode_map):
    vm = _make_vm(opcode_map)
    vm.start()
    st = vm.run(until_births=5)
    assert st["births"] == 5
    assert vm.counters["births"] == 5


def test_run_until_births_already_met_no_progress(opcode_map):
    vm = _make_vm(opcode_map, seed=7)
    vm.start()
    vm.counters["births"] = 5
    before = vm.inst_exe
    st = vm.run(until_births=5)
    assert st["births"] == 5
    assert vm.inst_exe == before
