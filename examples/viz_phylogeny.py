# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Parent→child genotype graph from birth events (max_edges)."""

from __future__ import annotations

from pathlib import Path

try:
    import matplotlib.pyplot as plt
    import networkx as nx
except ImportError as e:
    raise SystemExit('pip install -e ".[viz]"') from e

from pytierra import TierraVM
from pytierra.models.limits import SandboxLimits
from pytierra.services.metrics import MetricsRecorder

ROOT = Path(__file__).resolve().parents[1]
TIERRA = ROOT / "legacy" / "tierra"
OUT_DIR = ROOT / "viz"


def main(*, max_edges: int = 200) -> None:
    vm = TierraVM.from_config(
        {
            "SoupSize": 6000,
            "NumCells": 1,
            "seed": 7,
            "GenebankPath": "gb0/",
            "IMapFile": "opcode.map",
            "GeneBnker": 1,
            "place_center": True,
            "inoculum": ["0080aaa"],
            "GenPerMovMut": 150,
            "GenPerDivMut": 150,
        },
        asset_root=TIERRA,
        limits=SandboxLimits(max_instructions=40_000, wall_time_s=60),
    )
    rec = MetricsRecorder(sample_every=500)
    vm.attach_recorder(rec)
    vm.start()
    vm.run(max_instructions=30_000)
    edges = rec.birth_edges(max_edges=max_edges)
    # also use banker parent links
    for g in vm.genotypes():
        if g.get("parent"):
            edges.append((g["parent"], g["name"]))
    g = nx.DiGraph()
    g.add_edges_from(edges[-max_edges:])
    plt.figure(figsize=(8, 6))
    if g.number_of_nodes():
        pos = nx.spring_layout(g, seed=1)
        nx.draw(g, pos, with_labels=True, node_size=400, font_size=7, arrows=True)
    plt.title(f"Phylogeny (max_edges={max_edges})")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "viz_phylogeny.png"
    plt.tight_layout()
    plt.savefig(out)
    print("wrote", out, "nodes", g.number_of_nodes())


if __name__ == "__main__":
    main()
