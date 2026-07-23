# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from __future__ import annotations

from pytierra.adapters.filesystem.soup_in import parse_soup_in
from pytierra.bootstrap.wiring import load_genomes_into_vm
from pytierra.models.limits import SandboxLimits
from pytierra.services.genebank.hashutil import default_hash
from pytierra.services.genebank.rambank import RamBanker
from pytierra.services.vm.service import TierraVM
from tests.conftest import GB0, TIERRA, acceptance_config_text


def test_hash_collision_uses_memcmp():
    def fake_hash(_data: bytes) -> int:
        return 0xDEAD

    bank = RamBanker(hasher=fake_hash)
    a = b"\x01" * 80
    b = b"\x02" * 80
    assert fake_hash(a) == fake_hash(b)
    n1 = bank.on_birth(
        cell_id=0, size=80, genome=a, mother_name="", mother_hash=None
    )
    n2 = bank.on_birth(
        cell_id=1, size=80, genome=b, mother_name="", mother_hash=None
    )
    assert n1 != n2
    assert len(bank.list_genotypes()) == 2


def test_mut0_daughter_named_0080aaa(opcode_map):
    cfg = parse_soup_in(acceptance_config_text())
    cfg.values["GeneBnker"] = 1
    vm = TierraVM(
        config=cfg,
        asset_root=TIERRA,
        opcode_map=opcode_map,
        limits=SandboxLimits(max_instructions=300_000, wall_time_s=60),
    )
    load_genomes_into_vm(vm, GB0)
    vm.start()
    vm.run(until_births=1)
    names = {c.dem.gen_name for c in vm.cells if c.alive}
    assert "0080aaa" in names
    assert all(not n.endswith("???") for n in names)
    gens = vm.genotypes()
    assert any(g["name"] == "0080aaa" and g["pop"] >= 2 for g in gens)


def test_banker_snapshot_version(opcode_map):
    cfg = parse_soup_in(acceptance_config_text())
    cfg.values["GeneBnker"] = 1
    vm = TierraVM(
        config=cfg,
        asset_root=TIERRA,
        opcode_map=opcode_map,
        limits=SandboxLimits(max_instructions=300_000, wall_time_s=60),
    )
    load_genomes_into_vm(vm, GB0)
    vm.start()
    vm.run(until_births=1)
    snap = vm.snapshot()
    assert snap["banker_version"] == 1
    assert snap["genebank"]["enabled"] is True
    vm2 = TierraVM(
        config=cfg,
        asset_root=TIERRA,
        opcode_map=opcode_map,
        limits=SandboxLimits(max_instructions=300_000, wall_time_s=60),
    )
    load_genomes_into_vm(vm2, GB0)
    vm2.restore(snap)
    assert any(g["name"] == "0080aaa" for g in vm2.genotypes())


def test_hash_cache_copied_without_mut():
    bank = RamBanker()
    g = bytes([1, 2, 3, 4] * 20)
    h = default_hash(g)
    n = bank.register_inoculum(name="0080aaa", genome=g, permanent=True)
    assert n == "0080aaa"
    n2 = bank.on_birth(
        cell_id=1, size=80, genome=g, mother_name="0080aaa", mother_hash=h
    )
    assert n2 == "0080aaa"
