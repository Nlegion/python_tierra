# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Composition root: build TierraVM from config + filesystem assets."""

from __future__ import annotations

import logging
from pathlib import Path

from pytierra.adapters.filesystem.genome import load_opcode_map, load_tie
from pytierra.adapters.filesystem.soup_in import load_soup_in, parse_soup_in
from pytierra.models.limits import SandboxLimits
from pytierra.services.vm.service import TierraVM

logger = logging.getLogger(__name__)


def load_genomes_into_vm(vm: TierraVM, gb: Path) -> None:
    names = list(vm.config.inoculum)
    if not names and vm.config.num_cells:
        names = ["0080aaa"]
    for name in names:
        path = gb / f"{name}.tie"
        if not path.is_file():
            path = vm.asset_root / vm.config.genebank_path / f"{name}.tie"
        gen = load_tie(path, vm.opcode_map)
        vm._genomes[name] = list(gen.code)


def build_vm_from_config(
    path_or_dict: str | Path | dict,
    *,
    asset_root: str | Path | None = None,
    limits: SandboxLimits | None = None,
) -> TierraVM:
    if isinstance(path_or_dict, dict):
        place_center = bool(path_or_dict.get("place_center", False))
        lines = [
            f"{k} = {v}"
            for k, v in path_or_dict.items()
            if k not in ("inoculum", "place_center")
        ]
        for name in path_or_dict.get("inoculum", []):
            lines.append(str(name))
        cfg = parse_soup_in("\n".join(lines))
        cfg.place_center = place_center or cfg.place_center
        root = Path(asset_root or ".")
        source = "dict"
    else:
        path = Path(path_or_dict)
        cfg = load_soup_in(path)
        root = Path(asset_root) if asset_root else path.parent
        source = str(path)
    gb = (root / cfg.genebank_path).resolve()
    map_path = gb / cfg.imap_file
    if not map_path.is_file():
        map_path = root / cfg.genebank_path / cfg.imap_file
    omp = load_opcode_map(map_path)
    vm = TierraVM(config=cfg, asset_root=root, opcode_map=omp, limits=limits)
    load_genomes_into_vm(vm, gb)
    if int(cfg.get("DiskBank", 0) or 0):
        from pytierra.adapters.filesystem.diskbank import DiskBankStore

        store = DiskBankStore(
            gb,
            opcode_map=omp,
            backend=str(cfg.get("DiskBankBackend", "json")).lower(),
            fmt=str(cfg.get("DiskBankFormat", "ascii")).lower(),
        )
        vm.attach_disk_bank(store)
    logger.info(
        "TierraVM.from_config source=%s soup_size=%d",
        source,
        cfg.soup_size,
        extra={"event": "from_config"},
    )
    return vm
