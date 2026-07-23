# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""cProfile baselines for TierraVM (no optimization — measurement only)."""

from __future__ import annotations

import argparse
import cProfile
import pstats
from pathlib import Path

from pytierra.models.limits import SandboxLimits
from pytierra.services.vm.service import TierraVM

ROOT = Path(__file__).resolve().parents[1]
TIERRA = ROOT / "legacy" / "tierra"


def _make_vm(*, max_instructions: int) -> TierraVM:
    return TierraVM.from_config(
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
        limits=SandboxLimits(max_instructions=max_instructions, wall_time_s=120),
    )


def run_births(n: int) -> None:
    vm = _make_vm(max_instructions=max(200_000, n * 50_000))
    vm.start()
    vm.run(until_births=n)
    print("stats", vm.stats())


def run_fragmentation() -> None:
    vm = _make_vm(max_instructions=100_000)
    vm.start()
    # artificial fragmentation: allocate and free many small blocks
    addrs = []
    for _ in range(40):
        a = vm.mem.mem_alloc(16, -1, 0)
        if a < 0:
            break
        addrs.append(a)
    for a in addrs[::2]:
        vm.mem.mem_dealloc(a, 16)
    vm.run(until_births=1)
    print("stats", vm.stats())


def main() -> None:
    p = argparse.ArgumentParser(description="Profile TierraVM scenarios")
    p.add_argument(
        "--scenario",
        choices=("births1", "births100", "fragmentation"),
        default="births1",
    )
    p.add_argument("--prof", type=Path, default=None, help="optional .prof output")
    args = p.parse_args()
    targets = {
        "births1": lambda: run_births(1),
        "births100": lambda: run_births(100),
        "fragmentation": run_fragmentation,
    }
    pr = cProfile.Profile()
    pr.enable()
    targets[args.scenario]()
    pr.disable()
    stats = pstats.Stats(pr).sort_stats("cumulative")
    stats.print_stats(20)
    if args.prof:
        pr.dump_stats(str(args.prof))
        print("wrote", args.prof)


if __name__ == "__main__":
    main()
