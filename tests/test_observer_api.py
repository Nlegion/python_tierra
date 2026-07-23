# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from __future__ import annotations

import pytest

from pytierra.adapters.filesystem.soup_in import parse_soup_in
from pytierra.bootstrap.wiring import load_genomes_into_vm
from pytierra.core.errors import ConfigError
from pytierra.models.limits import SandboxLimits
from pytierra.services.vm.service import TierraVM
from tests.conftest import GB0, TIERRA, acceptance_config_text


def _vm_banked(opcode_map):
    cfg = parse_soup_in(acceptance_config_text())
    cfg.values["GeneBnker"] = 1
    vm = TierraVM(
        config=cfg,
        asset_root=TIERRA,
        opcode_map=opcode_map,
        limits=SandboxLimits(max_instructions=300_000, wall_time_s=60),
    )
    load_genomes_into_vm(vm, GB0)
    return vm


def test_overview_histogram_plan(opcode_map):
    vm = _vm_banked(opcode_map)
    vm.start()
    vm.run(until_births=1)
    ov = vm.overview()
    assert len(ov) >= 2
    hist = vm.histogram(kind="size")
    assert "80" in hist["buckets"]
    plan = vm.plan()
    assert plan["unique_genotypes"] >= 1
    snap = vm.cell_snapshot(ov[0]["cell_id"])
    assert snap is not None
    g = vm.genome_of("0080aaa")
    assert g is not None and len(g) == 80


def test_set_parameter_whitelist(opcode_map):
    vm = _vm_banked(opcode_map)
    vm.start()
    vm.set_parameter("SliceSize", 30)
    assert vm.get_parameter("SliceSize") == 30
    with pytest.raises(ConfigError):
        vm.set_parameter("SoupSize", 1)


def test_step_until_uses_limits(opcode_map):
    vm = _vm_banked(opcode_map)
    vm.start()
    out = vm.step_until(lambda v: v.counters["births"] >= 1, max_instructions=300_000)
    assert out["stop_reason"] == "predicate"
    assert out["births"] >= 1


def test_histogram_kinds_and_genome_at(opcode_map):
    vm = _vm_banked(opcode_map)
    vm.start()
    mother = next(c for c in vm.cells if c.alive)
    assert vm.histogram(kind="gene")["kind"] == "gene"
    assert vm.histogram(kind="mem")["buckets"]["used"] > 0
    assert vm.genome_at(mother.mm_p) is not None
    with pytest.raises(ValueError):
        vm.histogram(kind="nope")
