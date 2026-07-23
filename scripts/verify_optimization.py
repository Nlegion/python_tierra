# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Golden check for run_ancestor seed=42 — gate before/after optimizations."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from pytierra.models.limits import SandboxLimits
from pytierra.services.vm.service import TierraVM

ROOT = Path(__file__).resolve().parents[1]
TIERRA = ROOT / "legacy" / "tierra"
GOLDEN = Path(__file__).with_name("golden_ancestor_seed42.json")


def run_once() -> dict:
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
    vm.run(until_births=1)
    snap = vm.snapshot()
    soup_hash = hashlib.sha256(bytes(snap["soup"]["soup"])).hexdigest()
    return {
        "InstExe": vm.inst_exe,
        "births": vm.counters.get("births", 0),
        "NumCells": vm.queues.num_cells,
        "soup_sha256": soup_hash,
        "average_size": vm.average_size,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-golden", action="store_true")
    args = ap.parse_args()
    result = run_once()
    if args.write_golden:
        GOLDEN.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("wrote", GOLDEN)
        return 0
    if not GOLDEN.is_file():
        print("missing golden; run with --write-golden", file=sys.stderr)
        return 2
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    ok = True
    for k in ("InstExe", "births", "NumCells", "soup_sha256", "average_size"):
        if result.get(k) != golden.get(k):
            print(f"FAIL {k}: got {result.get(k)} expected {golden.get(k)}")
            ok = False
        else:
            print(f"OK {k}={result.get(k)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
