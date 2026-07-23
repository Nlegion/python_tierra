# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Export Python TierraVM metrics JSON for C comparison.

``first_birth_InstExe`` is measured with ``step(1)`` (exact). Coarse
``sample_every`` timeline is only used after the first birth for extra steps.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.c_compare.acceptance import (  # noqa: E402
    GOLDEN_FIRST_BIRTH_INST_EXE,
    acceptance_config_dict,
)
from pytierra.models.limits import SandboxLimits  # noqa: E402
from pytierra.services.vm.service import TierraVM  # noqa: E402

TIERRA = ROOT / "legacy" / "tierra"


def run_export(
    *,
    until_births: int = 1,
    sample_every: int = 1000,
    extra_steps: int = 0,
    max_instructions: int = 300_000,
) -> dict:
    vm = TierraVM.from_config(
        acceptance_config_dict(),
        asset_root=TIERRA,
        limits=SandboxLimits(
            max_instructions=max_instructions,
            wall_time_s=120,
        ),
    )
    vm.start()
    timeline: list[dict] = []
    first_birth_inst = None
    target = max(1, until_births)

    # Exact first birth: stop on the birth instruction (per-insn until_births).
    vm.run(until_births=1, max_instructions=max_instructions)
    if vm.counters.get("births", 0) < 1:
        raise RuntimeError(f"no birth within max_instructions={max_instructions}")
    first_birth_inst = vm.inst_exe

    timeline.append(
        {
            "InstExe": vm.inst_exe,
            "births": vm.counters.get("births", 0),
            "deaths": vm.counters.get("deaths", 0),
            "NumCells": vm.queues.num_cells,
        }
    )

    # Coarse sampling for additional births / extra steps.
    while (
        vm.counters.get("births", 0) < target or vm.inst_exe < first_birth_inst + extra_steps
    ) and vm.budget_used < max_instructions:
        if vm.counters.get("births", 0) >= target and extra_steps <= 0:
            break
        if (
            vm.counters.get("births", 0) >= target
            and vm.inst_exe >= first_birth_inst + extra_steps
        ):
            break
        vm.step(n=max(1, sample_every))
        timeline.append(
            {
                "InstExe": vm.inst_exe,
                "births": vm.counters.get("births", 0),
                "deaths": vm.counters.get("deaths", 0),
                "NumCells": vm.queues.num_cells,
            }
        )

    sizes = [c.mm_s for c in vm.cells if c.alive]
    hist = Counter(sizes)
    return {
        "seed": 42,
        "first_birth_InstExe": first_birth_inst,
        "golden_first_birth_InstExe": GOLDEN_FIRST_BIRTH_INST_EXE,
        "final": vm.stats(),
        "size_histogram": {str(k): v for k, v in sorted(hist.items())},
        "timeline": timeline,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--until-births", type=int, default=1)
    ap.add_argument("--sample-every", type=int, default=1000)
    ap.add_argument(
        "--extra-steps",
        type=int,
        default=0,
        help="After first birth, continue coarse sampling for this many InstExe",
    )
    ap.add_argument("-o", "--output", type=Path, default=Path("python_stats.json"))
    args = ap.parse_args()

    out = run_export(
        until_births=args.until_births,
        sample_every=args.sample_every,
        extra_steps=args.extra_steps,
    )
    args.output.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("wrote", args.output, "first_birth_InstExe=", out["first_birth_InstExe"])


if __name__ == "__main__":
    main()
