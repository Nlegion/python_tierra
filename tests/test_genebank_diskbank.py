# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from __future__ import annotations

from pathlib import Path

from pytierra.adapters.filesystem.diskbank import DiskBankStore
from pytierra.adapters.filesystem.genome import load_opcode_map, load_tie
from pytierra.adapters.filesystem.soup_in import parse_soup_in
from pytierra.bootstrap.wiring import load_genomes_into_vm
from pytierra.models.limits import SandboxLimits
from pytierra.services.genebank.hashutil import default_hash
from pytierra.services.genebank.write_queue import WriteJob
from pytierra.services.vm.service import TierraVM
from tests.conftest import GB0, TIERRA, acceptance_config_text


def test_gb0_name_from_file_stem():
    omp = load_opcode_map(GB0 / "opcode.map")
    g = load_tie(GB0 / "0080aaa.tie", omp)
    assert g.meta.genotype == "0080aaa" or Path(GB0 / "0080aaa.tie").stem == "0080aaa"


def test_skip_rewrite_same_hash(tmp_path: Path):
    omp = load_opcode_map(GB0 / "opcode.map")
    store = DiskBankStore(tmp_path, opcode_map=omp)
    genome = bytes([1] * 80)
    h = default_hash(genome)
    job = WriteJob(name="0080aaa", genome=genome, hash=h, pop=2)
    assert store.write_job(job) is True
    mtime1 = (tmp_path / "0080aaa.tie").stat().st_mtime
    content1 = (tmp_path / "0080aaa.tie").read_text(encoding="utf-8")
    assert store.write_job(job) is False
    content2 = (tmp_path / "0080aaa.tie").read_text(encoding="utf-8")
    assert content1 == content2
    assert (tmp_path / "genebank_index.json").is_file()
    assert mtime1 <= (tmp_path / "0080aaa.tie").stat().st_mtime


def test_diskbank_extract_via_vm(tmp_path: Path):
    omp = load_opcode_map(GB0 / "opcode.map")
    cfg = parse_soup_in(acceptance_config_text())
    cfg.values["GeneBnker"] = 1
    cfg.values["DiskBank"] = 1
    cfg.values["SavMinNum"] = 1
    cfg.values["SavThrMem"] = 0.0
    vm = TierraVM(
        config=cfg,
        asset_root=TIERRA,
        opcode_map=omp,
        limits=SandboxLimits(max_instructions=300_000, wall_time_s=60),
    )
    load_genomes_into_vm(vm, GB0)
    store = DiskBankStore(tmp_path, opcode_map=omp)
    vm.attach_disk_bank(store)
    vm.start()
    vm.run(until_births=1)
    vm.save_genotype("0080aaa")
    assert (tmp_path / "0080aaa.tie").is_file()
    ids = vm.inject("0080aaa", n=1)
    assert ids
