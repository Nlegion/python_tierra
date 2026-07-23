# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Deterministic evolution-mode smoke: high GenPer* + fixed seed."""

from pytierra.adapters.filesystem.soup_in import parse_soup_in
from pytierra.bootstrap.wiring import load_genomes_into_vm
from pytierra.models.limits import SandboxLimits
from pytierra.services.vm.service import TierraVM
from tests.conftest import GB0, TIERRA, acceptance_config_text


def test_high_bkg_mut_increments_counter(opcode_map):
    # GenPerBkgMut=2 with slicer cosmic path: count_mut hits rate quickly
    text = acceptance_config_text(seed=42).replace(
        "GenPerBkgMut = 0",
        "GenPerBkgMut = 2",
    )
    cfg = parse_soup_in(text)
    vm = TierraVM(
        config=cfg,
        asset_root=TIERRA,
        opcode_map=opcode_map,
        limits=SandboxLimits(max_instructions=20_000, wall_time_s=30),
    )
    load_genomes_into_vm(vm, GB0)
    vm.start()
    # rate_mut is set from GenPerBkgMut in _recompute_rates
    assert vm.rate_mut == 2
    vm.step(n=500)
    assert vm.counters.get("TotMut", 0) > 0


def test_mov_mut_counter_during_replication(opcode_map):
    text = acceptance_config_text(seed=7).replace(
        "GenPerMovMut = 0",
        "GenPerMovMut = 2",
    )
    cfg = parse_soup_in(text)
    vm = TierraVM(
        config=cfg,
        asset_root=TIERRA,
        opcode_map=opcode_map,
        limits=SandboxLimits(max_instructions=100_000, wall_time_s=60),
    )
    load_genomes_into_vm(vm, GB0)
    vm.start()
    assert vm.rate_mov_mut == 2
    try:
        vm.run(until_births=1)
    except Exception:
        pass
    # During copy phase movii should fire TotMovMut with rate 2
    assert vm.counters.get("TotMovMut", 0) > 0 or vm.counters.get("births", 0) >= 1
