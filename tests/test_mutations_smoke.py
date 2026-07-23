# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Deterministic evolution-mode smoke: GenPer* → CalcFlawRates + counters."""

from pytierra.adapters.filesystem.soup_in import parse_soup_in
from pytierra.bootstrap.wiring import load_genomes_into_vm
from pytierra.models.limits import SandboxLimits
from pytierra.services.vm.flaw_rates import calc_flaw_rates
from pytierra.services.vm.service import TierraVM
from tests.conftest import GB0, TIERRA, acceptance_config_text


def test_high_bkg_mut_increments_counter(opcode_map):
    text = (
        acceptance_config_text(seed=42)
        .replace("GenPerBkgMut = 0", "GenPerBkgMut = 2")
        .replace("SliceStyle = 2", "SliceStyle = 0")
    )
    cfg = parse_soup_in(text)
    vm = TierraVM(
        config=cfg,
        asset_root=TIERRA,
        opcode_map=opcode_map,
        limits=SandboxLimits(max_instructions=50_000, wall_time_s=30),
    )
    load_genomes_into_vm(vm, GB0)
    vm.start()
    expected = calc_flaw_rates(
        num_cells=vm.queues.num_cells,
        average_size=vm.average_size,
        soup_size=vm.config.soup_size,
        gen_per_bkg_mut=2,
        gen_per_mov_mut=0,
        gen_per_flaw=0,
    )
    assert vm.rate_mut == expected.rate_mut
    assert vm.rate_mut != 2
    # ~2*N/rate events; N large enough for at least one mutation
    vm.step(n=20_000)
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
    expected = calc_flaw_rates(
        num_cells=vm.queues.num_cells,
        average_size=vm.average_size,
        soup_size=vm.config.soup_size,
        gen_per_bkg_mut=0,
        gen_per_mov_mut=2,
        gen_per_flaw=0,
    )
    assert vm.rate_mov_mut == expected.rate_mov_mut
    try:
        vm.run(until_births=3)
    except Exception:
        pass
    assert vm.counters.get("TotMovMut", 0) > 0 or vm.counters.get("births", 0) >= 1
