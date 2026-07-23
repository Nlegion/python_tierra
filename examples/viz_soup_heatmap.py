# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""1D soup occupancy as a heatmap strip."""

from __future__ import annotations

from pathlib import Path

try:
    import matplotlib.pyplot as plt
except ImportError as e:
    raise SystemExit('pip install -e ".[viz]"') from e

from pytierra import TierraVM
from pytierra.models.limits import SandboxLimits
from pytierra.services.metrics.occupancy import occupancy_array

ROOT = Path(__file__).resolve().parents[1]
TIERRA = ROOT / "legacy" / "tierra"
OUT_DIR = ROOT / "viz"


def main() -> None:
    vm = TierraVM.from_config(
        {
            "SoupSize": 6000,
            "NumCells": 1,
            "seed": 42,
            "GenebankPath": "gb0/",
            "IMapFile": "opcode.map",
            "place_center": True,
            "inoculum": ["0080aaa"],
        },
        asset_root=TIERRA,
        limits=SandboxLimits(max_instructions=50_000, wall_time_s=60),
    )
    vm.start()
    vm.run(until_births=2)
    occ = occupancy_array(vm)
    width = 100
    rows = (len(occ) + width - 1) // width
    pad = rows * width - len(occ)
    flat = list(occ) + [0] * pad
    arr = [flat[r * width : (r + 1) * width] for r in range(rows)]
    plt.figure(figsize=(10, 4))
    plt.imshow(arr, aspect="auto", interpolation="nearest")
    plt.title("Soup occupancy (cell marks)")
    plt.xlabel("addr % width")
    plt.ylabel("addr // width")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "viz_soup_heatmap.png"
    plt.tight_layout()
    plt.savefig(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
