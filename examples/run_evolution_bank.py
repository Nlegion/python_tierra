# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Evolution demo with GeneBnker + DiskBank (writes under a temp bank path)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from pytierra import TierraVM
from pytierra.models.limits import SandboxLimits

ROOT = Path(__file__).resolve().parents[1]
TIERRA = ROOT / "legacy" / "tierra"


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bank = Path(tmp)
        # copy opcode map reference via GenebankPath under asset_root; use gb0 for map
        vm = TierraVM.from_config(
            {
                "SoupSize": 6000,
                "NumCells": 1,
                "seed": 7,
                "GenebankPath": "gb0/",
                "IMapFile": "opcode.map",
                "GeneBnker": 1,
                "DiskBank": 1,
                "DiskBankFormat": "ascii",
                "DiskBankBackend": "json",
                "SavMinNum": 2,
                "SavThrMem": 0.0,
                "GenPerBkgMut": 0,
                "GenPerMovMut": 200,
                "GenPerDivMut": 200,
                "place_center": True,
                "inoculum": ["0080aaa"],
            },
            asset_root=TIERRA,
            limits=SandboxLimits(max_instructions=80_000, wall_time_s=60),
        )
        # redirect disk bank to temp
        from pytierra.adapters.filesystem.diskbank import DiskBankStore

        vm.attach_disk_bank(DiskBankStore(bank, opcode_map=vm.opcode_map))
        vm.start()
        vm.run(max_instructions=50_000)
        print("stats", vm.stats())
        print("genotypes", vm.genotypes()[:10])
        print("disk files", list(bank.glob("*.tie"))[:10])


if __name__ == "__main__":
    main()
