# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Segment / dirty path registers new species in RamBanker."""

from __future__ import annotations

from pytierra.adapters.filesystem.soup_in import parse_soup_in
from pytierra.bootstrap.wiring import load_genomes_into_vm
from pytierra.models.limits import SandboxLimits
from pytierra.services.mutate import apply_segment_mutation_for_tests
from pytierra.services.vm.service import TierraVM
from tests.conftest import GB0, TIERRA, acceptance_config_text


def test_segment_like_mutation_registers_new_species(opcode_map):
    cfg = parse_soup_in(acceptance_config_text())
    cfg.values["GeneBnker"] = 1
    vm = TierraVM(
        config=cfg,
        asset_root=TIERRA,
        opcode_map=opcode_map,
        limits=SandboxLimits(max_instructions=50_000, wall_time_s=30),
    )
    load_genomes_into_vm(vm, GB0)
    vm.start()
    mother = next(c for c in vm.cells if c.alive)
    apply_segment_mutation_for_tests(mother, vm.mem, addr_offset=10, new_byte=0x11)
    assert mother.dem.genome_hash_dirty is True
    genome = bytes(
        vm.mem.soup[
            mother.mm_p + mother.dem.mg_p : mother.mm_p
            + mother.dem.mg_p
            + mother.dem.mg_s
        ]
    )
    name = vm.genebank.on_birth(
        cell_id=99,
        size=len(genome),
        genome=genome,
        mother_name="0080aaa",
        mother_hash=None,
    )
    assert name != "0080aaa"
    assert any(g["name"] == name for g in vm.genotypes())


def test_hash_survives_snapshot_after_dirty(opcode_map):
    cfg = parse_soup_in(acceptance_config_text())
    cfg.values["GeneBnker"] = 1
    vm = TierraVM(
        config=cfg,
        asset_root=TIERRA,
        opcode_map=opcode_map,
        limits=SandboxLimits(max_instructions=50_000, wall_time_s=30),
    )
    load_genomes_into_vm(vm, GB0)
    vm.start()
    c = next(x for x in vm.cells if x.alive)
    c.dem.genome_hash = 12345
    c.dem.genome_hash_dirty = False
    snap = vm.snapshot()
    vm.restore(snap)
    c2 = next(x for x in vm.cells if x.alive)
    assert c2.dem.genome_hash == 12345
    assert c2.dem.genome_hash_dirty is False
