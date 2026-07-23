# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""CalcFlawRates bootstrap + TotMut frequency vs C formula."""

from __future__ import annotations

from pytierra.adapters.filesystem.soup_in import parse_soup_in
from pytierra.bootstrap.wiring import load_genomes_into_vm
from pytierra.core.settings.constants import PLOIDY
from pytierra.models.limits import SandboxLimits
from pytierra.services.vm.flaw_rates import calc_flaw_rates
from pytierra.services.vm.service import TierraVM
from tests.conftest import GB0, TIERRA, acceptance_config_text


def test_calc_flaw_rates_empty_soup():
    r = calc_flaw_rates(
        num_cells=0,
        average_size=80,
        soup_size=12000,
        gen_per_bkg_mut=512,
        gen_per_mov_mut=512,
        gen_per_flaw=1,
    )
    assert r.rate_mut == 0
    assert r.rate_mov_mut == 0
    assert r.rate_flaw == 0


def test_calc_flaw_rates_bootstrap_matches_c_hand_calc():
    # AverageSize=80, SoupSize=12000, GenPerBkgMut=512, GenPerMovMut=512, GenPerFlaw=1
    # RepInst = 800
    # pop_gen_time = 800 * (12000 // 320) = 800 * 37 = 29600
    # RateMut = int(29600 * 2.0 * 512 * (80/12000)) = 202069
    # RateMovMut = 2 * 512 * 80 * 1 = 81920
    # RateFlaw = 800 * 1 * 2 = 1600
    r = calc_flaw_rates(
        num_cells=1,
        average_size=80,
        soup_size=12000,
        gen_per_bkg_mut=512,
        gen_per_mov_mut=512,
        gen_per_flaw=1,
        ploidy=PLOIDY,
    )
    assert r.rate_mut == 202069
    assert r.rate_mov_mut == 81920
    assert r.rate_flaw == 1600


def test_vm_rates_from_formula_not_raw_genper(opcode_map):
    text = acceptance_config_text(seed=42).replace(
        "GenPerBkgMut = 0",
        "GenPerBkgMut = 512",
    ).replace(
        "GenPerMovMut = 0",
        "GenPerMovMut = 512",
    )
    cfg = parse_soup_in(text)
    vm = TierraVM(
        config=cfg,
        asset_root=TIERRA,
        opcode_map=opcode_map,
        limits=SandboxLimits(max_instructions=5_000, wall_time_s=30),
    )
    load_genomes_into_vm(vm, GB0)
    vm.start()
    expected = calc_flaw_rates(
        num_cells=vm.queues.num_cells,
        average_size=vm.average_size,
        soup_size=vm.config.soup_size,
        gen_per_bkg_mut=512,
        gen_per_mov_mut=512,
        gen_per_flaw=0,
    )
    assert vm.rate_mut == expected.rate_mut
    assert vm.rate_mov_mut == expected.rate_mov_mut
    assert vm.rate_mut != 512  # must not be raw GenPer*


def test_set_parameter_recomputes_rates(opcode_map):
    cfg = parse_soup_in(acceptance_config_text(seed=1))
    vm = TierraVM(
        config=cfg,
        asset_root=TIERRA,
        opcode_map=opcode_map,
        limits=SandboxLimits(max_instructions=5_000, wall_time_s=30),
    )
    load_genomes_into_vm(vm, GB0)
    vm.start()
    assert vm.rate_mut == 0
    vm.set_parameter("GenPerBkgMut", 512)
    expected = calc_flaw_rates(
        num_cells=vm.queues.num_cells,
        average_size=vm.average_size,
        soup_size=vm.config.soup_size,
        gen_per_bkg_mut=512,
        gen_per_mov_mut=0,
        gen_per_flaw=0,
    )
    assert vm.rate_mut == expected.rate_mut


def test_totmut_frequency_near_expectation(opcode_map):
    """E[TotMut] ≈ 2*N/RateMut; allow ±20% (or ±1).

    Use SliceStyle=0 so step(n) is not truncated by zero-length random slices.
    """
    text = (
        acceptance_config_text(seed=42)
        .replace("GenPerBkgMut = 0", "GenPerBkgMut = 2")
        .replace("SliceStyle = 2", "SliceStyle = 0")
    )
    cfg = parse_soup_in(text)
    n_inst = 20_000
    vm = TierraVM(
        config=cfg,
        asset_root=TIERRA,
        opcode_map=opcode_map,
        limits=SandboxLimits(max_instructions=n_inst + 1_000, wall_time_s=60),
    )
    load_genomes_into_vm(vm, GB0)
    vm.start()
    rate = vm.rate_mut
    assert rate > 0
    expected = 2.0 * n_inst / rate
    assert expected >= 5.0
    advanced = vm.step(n=n_inst)
    assert advanced == n_inst, f"executed {advanced}, want {n_inst}"
    tot = vm.counters.get("TotMut", 0)
    tol = max(1.0, 0.20 * expected)
    assert abs(tot - expected) <= tol, f"TotMut={tot} expected≈{expected:.1f} ±{tol:.1f}"


def test_stats_includes_mal_fail(opcode_map):
    cfg = parse_soup_in(acceptance_config_text(seed=3))
    vm = TierraVM(
        config=cfg,
        asset_root=TIERRA,
        opcode_map=opcode_map,
        limits=SandboxLimits(max_instructions=2_000, wall_time_s=30),
    )
    load_genomes_into_vm(vm, GB0)
    vm.start()
    st = vm.stats()
    assert "mal_fail" in st
    assert st["mal_fail"] == 0
    assert "rate_mut" in st
