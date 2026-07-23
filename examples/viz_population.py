# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Population time series from MetricsRecorder."""

from __future__ import annotations

from pathlib import Path

try:
    import matplotlib.pyplot as plt
except ImportError as e:
    raise SystemExit('pip install -e ".[viz]"') from e

from pytierra import TierraVM
from pytierra.models.limits import SandboxLimits
from pytierra.services.metrics import MetricsRecorder

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
            "GenPerMovMut": 0,
            "GenPerDivMut": 0,
        },
        asset_root=TIERRA,
        limits=SandboxLimits(max_instructions=50_000, wall_time_s=60),
    )
    rec = MetricsRecorder(sample_every=100)
    vm.attach_recorder(rec)
    vm.start()
    vm.run(until_births=3)
    xs = [s["InstExe"] for s in rec.samples]
    plt.figure(figsize=(8, 4))
    plt.plot(xs, [s["NumCells"] for s in rec.samples], label="NumCells")
    plt.plot(xs, [s["births"] for s in rec.samples], label="births")
    plt.plot(xs, [s["deaths"] for s in rec.samples], label="deaths")
    plt.xlabel("InstExe")
    plt.legend()
    plt.title("Population")
    plt.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "viz_population.png"
    plt.savefig(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
