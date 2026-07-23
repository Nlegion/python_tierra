# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Longer mut>0 run — parasite / size-diversity observation (not CI-gated)."""

from __future__ import annotations

import logging
import sys
from collections import Counter
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
                "SoupSize": 12000,
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
                "NumCellsMin": 1,
                "GenebankPath": "gb0/",
                "IMapFile": "opcode.map",
                "seed": 42,
                "GenPerBkgMut": 8,
                "GenPerFlaw": 0,
                "GenPerMovMut": 8,
                "GenPerDivMut": 8,
                "place_center": True,
                "inoculum": ["0080aaa"],
            },
            asset_root=TIERRA,
            limits=SandboxLimits(
                max_instructions=500_000,
                max_cells=200,
                wall_time_s=120,
            ),
        )
        vm.start()
        vm.run(until_births=30)
        sizes = [c.mm_s for c in vm.cells if c.alive]
        hist = Counter(sizes)
        print("stats", vm.stats())
        print("size_histogram", dict(sorted(hist.items())))
        print("TotMut", vm.counters.get("TotMut", 0), "TotMovMut", vm.counters.get("TotMovMut", 0))
        return 0
    except TierraError:
        logger.exception("evolution run failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
