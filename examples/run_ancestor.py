# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Run 0080aaa until first birth (or instruction budget)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from pytierra.core.errors import TierraError
from pytierra.core.logging_setup import configure_logging
from pytierra.models.limits import SandboxLimits
from pytierra.services.vm.service import TierraVM

ROOT = Path(__file__).resolve().parents[1]
TIERRA = ROOT / "legacy" / "tierra"
logger = logging.getLogger(__name__)


def main() -> int:
    configure_logging()
    try:
        vm = TierraVM.from_config(
            {
                "SoupSize": 6000,
                "SliceSize": 25,
                "SliceStyle": 2,
                "SlicFixFrac": 0,
                "SlicRanFrac": 2,
                "MalMode": 1,
                "MalTol": 20,
                "SearchLimit": 5,
                "MovPropThrDiv": 0.7,
                "MinCellSize": 12,
                "MinGenMemSiz": 12,
                "NumCells": 1,
                "GenebankPath": "gb0/",
                "IMapFile": "opcode.map",
                "seed": 42,
                "GenPerBkgMut": 0,
                "GenPerFlaw": 0,
                "GenPerMovMut": 0,
                "GenPerDivMut": 0,
                "place_center": True,
                "inoculum": ["0080aaa"],
            },
            asset_root=TIERRA,
            limits=SandboxLimits(max_instructions=200_000, wall_time_s=60),
        )
        vm.start()
        while vm.counters.get("births", 0) < 1 and vm.budget_used < 150_000:
            vm.step(n=500)
            if vm.budget_used % 5000 < 500:
                print(vm.stats())
        print("final", vm.stats())
        return 0
    except TierraError:
        logger.exception("Tierra-VM failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
