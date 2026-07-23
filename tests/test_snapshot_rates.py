# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Snapshot/restore preserves CalcFlawRates state; AverageSize change recomputes."""

from pytierra.adapters.filesystem.soup_in import parse_soup_in
from pytierra.bootstrap.wiring import load_genomes_into_vm
from pytierra.models.limits import SandboxLimits
from pytierra.services.vm.flaw_rates import calc_flaw_rates
from pytierra.services.vm.service import TierraVM
from tests.conftest import GB0, TIERRA, acceptance_config_text


def test_snapshot_restore_preserves_rates_and_counts(opcode_map):
    text = acceptance_config_text(seed=42).replace(
        "GenPerBkgMut = 0",
        "GenPerBkgMut = 16",
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
    vm.run(until_births=2)
    snap = vm.snapshot()
    rates_before = (
        vm.rate_mut,
        vm.count_mut,
        vm.rate_mov_mut,
        vm.count_mov_mut,
        vm.average_size,
        vm.counters.get("births", 0),
    )

    # Mutate live state away from snapshot
    vm.set_parameter("GenPerBkgMut", 512)
    assert vm.rate_mut != rates_before[0]
    if vm.queues.num_cells > 1:
        vm.reap_one()

    vm.restore(snap)
    assert vm.rate_mut == rates_before[0]
    assert vm.count_mut == rates_before[1]
    assert vm.rate_mov_mut == rates_before[2]
    assert vm.count_mov_mut == rates_before[3]
    assert vm.average_size == rates_before[4]
    assert vm.counters.get("births", 0) == rates_before[5]
    vm.step(n=100)


def test_reap_after_restore_may_recompute_rates(opcode_map):
    text = (
        acceptance_config_text(seed=3)
        .replace("GenPerBkgMut = 0", "GenPerBkgMut = 16")
        .replace("GeneBnker = 0", "GeneBnker = 1")
    )
    cfg = parse_soup_in(text)
    vm = TierraVM(
        config=cfg,
        asset_root=TIERRA,
        opcode_map=opcode_map,
        limits=SandboxLimits(max_instructions=100_000, max_cells=50, wall_time_s=60),
    )
    load_genomes_into_vm(vm, GB0)
    vm.start()
    vm.run(until_births=3)
    snap = vm.snapshot()
    vm.restore(snap)
    rate_before = vm.rate_mut
    # Force size mix if possible by injecting — otherwise just reap and check recompute path
    killed = vm.reap_one()
    assert killed or vm.queues.num_cells >= 1
    expected = calc_flaw_rates(
        num_cells=vm.queues.num_cells,
        average_size=vm.average_size,
        soup_size=vm.config.soup_size,
        gen_per_bkg_mut=16,
        gen_per_mov_mut=0,
        gen_per_flaw=0,
    )
    assert vm.rate_mut == expected.rate_mut
    # If AverageSize unchanged, rate may equal rate_before; still must match formula
    _ = rate_before
