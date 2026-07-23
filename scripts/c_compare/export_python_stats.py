# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Export Python TierraVM metrics JSON for C comparison."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from pytierra.models.limits import SandboxLimits
from pytierra.services.vm.service import TierraVM

ROOT = Path(__file__).resolve().parents[2]
TIERRA = ROOT / "legacy" / "tierra"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--until-births", type=int, default=1)
    ap.add_argument("--sample-every", type=int, default=1000)
    ap.add_argument("-o", "--output", type=Path, default=Path("python_stats.json"))
    args = ap.parse_args()

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
        limits=SandboxLimits(max_instructions=300_000, wall_time_s=120),
    )
    vm.start()
    timeline = []
    first_birth_inst = None
    target = args.until_births
    while vm.counters.get("births", 0) < target and vm.budget_used < 300_000:
        vm.step(n=args.sample_every)
        timeline.append(
            {
                "InstExe": vm.inst_exe,
                "births": vm.counters.get("births", 0),
                "deaths": vm.counters.get("deaths", 0),
                "NumCells": vm.queues.num_cells,
            }
        )
        if first_birth_inst is None and vm.counters.get("births", 0) >= 1:
            first_birth_inst = vm.inst_exe

    sizes = [c.mm_s for c in vm.cells if c.alive]
    hist = Counter(sizes)
    out = {
        "seed": 42,
        "first_birth_InstExe": first_birth_inst,
        "final": vm.stats(),
        "size_histogram": {str(k): v for k, v in sorted(hist.items())},
        "timeline": timeline,
    }
    args.output.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("wrote", args.output)


if __name__ == "__main__":
    main()
