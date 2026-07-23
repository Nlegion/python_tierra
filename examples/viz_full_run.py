# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""One evolution-scale run → all plots under viz/."""

from __future__ import annotations

import json
import math
import time
from collections import Counter
from pathlib import Path

try:
    import matplotlib.pyplot as plt
    import networkx as nx
    from matplotlib import animation
except ImportError as e:
    raise SystemExit('pip install -e ".[viz]"') from e

from pytierra import TierraVM
from pytierra.core.errors import SandboxLimitError
from pytierra.models.limits import SandboxLimits
from pytierra.services.metrics import MetricsRecorder
from pytierra.services.metrics.occupancy import occupancy_array

ROOT = Path(__file__).resolve().parents[1]
TIERRA = ROOT / "legacy" / "tierra"
OUT_DIR = ROOT / "viz"

# Match examples/run_evolution.py scale
CONFIG = {
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
    "GeneBnker": 1,
    "seed": 42,
    # GenPer≈16 → visible mutants on ~1e5 InstExe (CalcFlawRates); 512 was clonal-only
    "GenPerBkgMut": 16,
    "GenPerFlaw": 0,
    "GenPerMovMut": 16,
    "GenPerDivMut": 16,
    "place_center": True,
    "inoculum": ["0080aaa"],
}
MAX_INST = 300_000
UNTIL_BIRTHS = 80
PETRI_EVERY = 2_000
MAX_PETRI_FRAMES = 40
MAX_PHYLO_EDGES = 400
SEG_KEYS = (
    "GenPerCroInsSamSiz",
    "GenPerCroIns",
    "GenPerInsIns",
    "GenPerDelIns",
    "GenPerCroSeg",
    "GenPerInsSeg",
    "GenPerDelSeg",
)


def _xy(addr: int, soup_size: int) -> tuple[float, float]:
    t = 2 * math.pi * (addr / max(1, soup_size))
    r = 0.3 + 0.7 * (addr / max(1, soup_size))
    return r * math.cos(t), r * math.sin(t)


def _petri_snapshot(vm: TierraVM) -> dict:
    pts: list[tuple[float, float, str]] = []
    for c in vm.cells:
        if not c.alive:
            continue
        x, y = _xy(c.mm_p, vm.config.soup_size)
        pts.append((x, y, c.dem.gen_name or "?"))
    return {
        "InstExe": vm.inst_exe,
        "cells": vm.queues.num_cells,
        "pts": pts,
    }


def _plot_population(rec: MetricsRecorder, out: Path) -> None:
    xs = [s["InstExe"] for s in rec.samples]
    plt.figure(figsize=(9, 4))
    plt.plot(xs, [s["NumCells"] for s in rec.samples], label="NumCells")
    plt.plot(xs, [s["births"] for s in rec.samples], label="births")
    plt.plot(xs, [s["deaths"] for s in rec.samples], label="deaths")
    plt.xlabel("InstExe")
    plt.legend()
    plt.title("Population (full run)")
    plt.tight_layout()
    plt.savefig(out)
    plt.close()


def _plot_heatmap(vm: TierraVM, out: Path) -> None:
    occ = occupancy_array(vm)
    width = 120
    rows = (len(occ) + width - 1) // width
    pad = rows * width - len(occ)
    flat = list(occ) + [0] * pad
    arr = [flat[r * width : (r + 1) * width] for r in range(rows)]
    plt.figure(figsize=(11, 5))
    plt.imshow(arr, aspect="auto", interpolation="nearest")
    plt.title(f"Soup occupancy (cells={vm.queues.num_cells} InstExe={vm.inst_exe})")
    plt.xlabel("addr % width")
    plt.ylabel("addr // width")
    plt.tight_layout()
    plt.savefig(out)
    plt.close()


def _plot_phylogeny(vm: TierraVM, rec: MetricsRecorder, out: Path) -> None:
    edges = rec.birth_edges(max_edges=MAX_PHYLO_EDGES)
    for g in vm.genotypes():
        if g.get("parent"):
            edges.append((g["parent"], g["name"]))
    graph = nx.DiGraph()
    graph.add_edges_from(edges[-MAX_PHYLO_EDGES:])
    # Clonal births (parent==child) are omitted from edges; still show live genotypes.
    for g in vm.genotypes():
        name = g.get("name")
        if name:
            graph.add_node(name)
    for c in vm.cells:
        if c.alive and c.dem.gen_name:
            graph.add_node(c.dem.gen_name)
    plt.figure(figsize=(9, 7))
    n_nodes = graph.number_of_nodes()
    n_edges = graph.number_of_edges()
    if n_edges:
        pos = nx.spring_layout(graph, seed=1)
        nx.draw(graph, pos, with_labels=True, node_size=350, font_size=6, arrows=True)
        plt.title(f"Phylogeny (nodes={n_nodes} edges={n_edges})")
    elif n_nodes:
        pos = nx.spring_layout(graph, seed=1)
        nx.draw(graph, pos, with_labels=True, node_size=800, font_size=10, arrows=False)
        plt.title(f"Phylogeny: {n_nodes} genotype(s), 0 edges (clonal only)")
        plt.figtext(
            0.5,
            0.02,
            "No parent≠child edges: TotMut=0 / all births same genotype. "
            "Try GenPer*≈16–32 for diversity.",
            ha="center",
            fontsize=9,
        )
    else:
        plt.title("Phylogeny (empty — no genotypes)")
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    print("phylogeny nodes", n_nodes, "edges", n_edges)


def _plot_petri(frames: list[dict], out: Path) -> None:
    if not frames:
        return
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)
    ax.set_aspect("equal")
    sc = ax.scatter([], [])
    title = ax.set_title("")
    colors: dict[str, tuple] = {}

    def color_for(name: str) -> tuple:
        if name not in colors:
            colors[name] = plt.cm.hsv((hash(name) % 360) / 360.0)
        return colors[name]

    def draw(i: int):
        fr = frames[i]
        xs = [p[0] for p in fr["pts"]]
        ys = [p[1] for p in fr["pts"]]
        cs = [color_for(p[2]) for p in fr["pts"]]
        sc.set_offsets(list(zip(xs, ys)) if xs else [(0, 0)])
        sc.set_color(cs if cs else ["blue"])
        title.set_text(f"InstExe={fr['InstExe']} cells={fr['cells']}")
        return sc, title

    anim = animation.FuncAnimation(
        fig, draw, frames=len(frames), interval=80, blit=False
    )
    try:
        anim.save(out, writer="pillow", fps=10)
        print("wrote", out)
    except Exception:
        draw(len(frames) - 1)
        png = out.with_suffix(".png")
        fig.savefig(png)
        print("wrote", png, "(gif writer unavailable)")
    plt.close()


def _dump_run_artifacts(vm: TierraVM, rec: MetricsRecorder, *, stop_reason: str, wall_s: float) -> None:
    cfg_out = {
        "config": dict(vm.config.values),
        "derived": {
            "rate_mut": vm.rate_mut,
            "rate_mov_mut": vm.rate_mov_mut,
            "rate_flaw": vm.rate_flaw,
            "AverageSize": vm.average_size,
            "NumCells": vm.queues.num_cells,
            "NumCellsMin": vm.config.get("NumCellsMin", 1),
            "SavThrMem": vm.config.get("SavThrMem"),
            "SavThrPop": vm.config.get("SavThrPop"),
            "MalReapTol": vm.config.get("MalReapTol"),
        },
        "stop_reason": stop_reason,
        "wall_time_s": wall_s,
        "stats": vm.stats(),
    }
    (OUT_DIR / "full_run_config.json").write_text(
        json.dumps(cfg_out, indent=2), encoding="utf-8"
    )
    ev_births = [e for e in rec.events if e.get("kind") == "birth"]
    sizes = [c.mm_s for c in vm.cells if c.alive]
    occ = occupancy_array(vm)
    occupied = sum(1 for b in occ if b)
    analysis = {
        "stop_reason": stop_reason,
        "wall_time_s": wall_s,
        "final": vm.stats(),
        "counters": {
            k: int(vm.counters.get(k, 0))
            for k in (
                "births",
                "deaths",
                "mal_fail",
                "reap_attempts",
                "TotMut",
                "TotMovMut",
                "TotFlaw",
            )
        },
        "first_birth_InstExe": ev_births[0]["InstExe"] if ev_births else None,
        "genebank_genotypes": len(vm.genotypes()),
        "size_histogram_live": dict(sorted(Counter(sizes).items())),
        "soup_occupancy_pct": round(100 * occupied / vm.config.soup_size, 2),
        "reaper_note": (
            "deaths only via failed mal → reap_one; no ReapCheck/lazy reap; "
            "SavThr* are genebank filters"
        ),
        "segment_genper_raw": {
            k: int(vm.config.get(k, 0) or 0) for k in SEG_KEYS
        },
        "segment_note": (
            "GenPer*Seg/Ins are direct divide thresholds in mutate_segment.py; "
            "not transformed by CalcFlawRates"
        ),
        "derived_rates": {
            "rate_mut": vm.rate_mut,
            "rate_mov_mut": vm.rate_mov_mut,
            "rate_flaw": vm.rate_flaw,
        },
    }
    (OUT_DIR / "full_run_analysis.json").write_text(
        json.dumps(analysis, indent=2), encoding="utf-8"
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    vm = TierraVM.from_config(
        CONFIG,
        asset_root=TIERRA,
        limits=SandboxLimits(
            max_instructions=MAX_INST,
            max_cells=200,
            wall_time_s=300,
        ),
    )
    rec = MetricsRecorder(sample_every=250)
    vm.attach_recorder(rec)
    t0 = time.perf_counter()
    vm.start()
    stop_reason = "births"
    try:
        vm.run(until_births=UNTIL_BIRTHS, max_instructions=MAX_INST)
        if vm.counters.get("births", 0) < UNTIL_BIRTHS:
            stop_reason = "max_instructions"
    except SandboxLimitError as exc:
        stop_reason = f"sandbox:{exc}"
    wall_s = time.perf_counter() - t0

    stats = vm.stats()
    print("stop_reason", stop_reason)
    print("wall_time_s", round(wall_s, 3))
    print("stats", stats)
    print("samples", len(rec.samples), "events", len(rec.events), "births", stats.get("births"))
    _dump_run_artifacts(vm, rec, stop_reason=stop_reason, wall_s=wall_s)
    print("wrote", OUT_DIR / "full_run_config.json")
    print("wrote", OUT_DIR / "full_run_analysis.json")

    pop = OUT_DIR / "viz_population.png"
    heat = OUT_DIR / "viz_soup_heatmap.png"
    phylo = OUT_DIR / "viz_phylogeny.png"
    petri = OUT_DIR / "viz_petri.gif"
    _plot_population(rec, pop)
    print("wrote", pop)
    _plot_heatmap(vm, heat)
    print("wrote", heat)
    _plot_phylogeny(vm, rec, phylo)
    print("wrote", phylo)

    # Petri after metrics dump: final + short post-run (not step(1) over full horizon)
    frames: list[dict] = [_petri_snapshot(vm)]
    try:
        for _ in range(MAX_PETRI_FRAMES - 1):
            vm.step(n=PETRI_EVERY)
            frames.append(_petri_snapshot(vm))
    except SandboxLimitError:
        frames.append(_petri_snapshot(vm))
    print("petri_frames", len(frames))
    _plot_petri(frames, petri)


if __name__ == "__main__":
    main()
