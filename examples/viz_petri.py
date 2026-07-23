# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Simple Petri-dish style animation (matplotlib). Separate process; not in VM hot path."""

from __future__ import annotations

from pathlib import Path

try:
    import matplotlib.pyplot as plt
    from matplotlib import animation
except ImportError as e:
    raise SystemExit('pip install -e ".[viz]"') from e

from pytierra import TierraVM
from pytierra.models.limits import SandboxLimits

ROOT = Path(__file__).resolve().parents[1]
TIERRA = ROOT / "legacy" / "tierra"
OUT_DIR = ROOT / "viz"


def _xy(addr: int, soup_size: int) -> tuple[float, float]:
    # map linear soup address onto a circle / spiral
    import math

    t = 2 * math.pi * (addr / max(1, soup_size))
    r = 0.3 + 0.7 * (addr / max(1, soup_size))
    return r * math.cos(t), r * math.sin(t)


def main() -> None:
    vm = TierraVM.from_config(
        {
            "SoupSize": 6000,
            "NumCells": 1,
            "seed": 42,
            "GenebankPath": "gb0/",
            "IMapFile": "opcode.map",
            "GeneBnker": 1,
            "place_center": True,
            "inoculum": ["0080aaa"],
        },
        asset_root=TIERRA,
        limits=SandboxLimits(max_instructions=80_000, wall_time_s=60),
    )
    vm.start()
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)
    ax.set_aspect("equal")
    sc = ax.scatter([], [])
    title = ax.set_title("")

    colors = {}

    def color_for(name: str) -> tuple:
        if name not in colors:
            h = hash(name) % 360
            colors[name] = plt.cm.hsv(h / 360.0)
        return colors[name]

    def frame(_i: int):
        vm.step(n=200)
        xs, ys, cs = [], [], []
        for c in vm.cells:
            if not c.alive:
                continue
            x, y = _xy(c.mm_p, vm.config.soup_size)
            xs.append(x)
            ys.append(y)
            cs.append(color_for(c.dem.gen_name or "?"))
        sc.set_offsets(list(zip(xs, ys)) if xs else [(0, 0)])
        sc.set_color(cs if cs else ["blue"])
        title.set_text(f"InstExe={vm.inst_exe} cells={vm.queues.num_cells}")
        return sc, title

    anim = animation.FuncAnimation(fig, frame, frames=40, interval=50, blit=False)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "viz_petri.gif"
    try:
        anim.save(out, writer="pillow", fps=12)
        print("wrote", out)
    except Exception:
        # pillow optional; fall back to static frame
        frame(0)
        out_png = OUT_DIR / "viz_petri.png"
        fig.savefig(out_png)
        print("wrote", out_png, "(gif writer unavailable)")


if __name__ == "__main__":
    main()
