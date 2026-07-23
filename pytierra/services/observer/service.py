# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Observer read-model; receives a VM handle via methods (no import of genebank/net)."""

from __future__ import annotations

from collections import Counter
from typing import Any


class ObserverService:
    """Aggregates soup/cell/genebank views. Orchestrated by TierraVM only."""

    def plan(self, vm: Any) -> dict[str, Any]:
        gens = []
        banker = getattr(vm, "genebank", None)
        if banker is not None and getattr(banker, "enabled", False):
            gens = banker.list_genotypes()
        st = vm.stats()
        return {
            **st,
            "genotypes": gens,
            "unique_genotypes": len(gens),
            "NumCellsMin": int(vm.config.get("NumCellsMin", 1)),
            "SliceSize": int(vm.config.get("SliceSize", 25)),
        }

    def overview(self, vm: Any) -> list[dict[str, Any]]:
        out = []
        for c in vm.cells:
            if not c.alive:
                continue
            out.append(
                {
                    "cell_id": c.cell_id,
                    "addr": c.mm_p,
                    "size": c.mm_s,
                    "gen_name": c.dem.gen_name,
                    "ip": c.cpu.ip,
                    "fecundity": c.dem.fecundity,
                }
            )
        return out

    def histogram(self, vm: Any, kind: str = "size") -> dict[str, Any]:
        if kind == "size":
            ctr = Counter(c.mm_s for c in vm.cells if c.alive)
            return {"kind": "size", "buckets": {str(k): v for k, v in sorted(ctr.items())}}
        if kind == "gene":
            ctr = Counter(c.dem.gen_name for c in vm.cells if c.alive)
            return {"kind": "gene", "buckets": dict(ctr)}
        if kind == "mem":
            free = vm.mem.free_bytes()
            used = vm.config.soup_size - free
            return {"kind": "mem", "buckets": {"free": free, "used": used}}
        raise ValueError(f"unknown histogram kind: {kind}")

    def genome_at(self, vm: Any, addr: int) -> bytes | None:
        for c in vm.cells:
            if not c.alive:
                continue
            if c.mm_p <= addr < c.mm_p + c.mm_s:
                g0 = c.mm_p + c.dem.mg_p
                gsz = c.dem.mg_s or c.mm_s
                return bytes(vm.mem.soup[g0 : g0 + gsz])
        return None

    def genome_of(self, vm: Any, name: str) -> bytes | None:
        banker = getattr(vm, "genebank", None)
        if banker is not None:
            g = banker.get_genome_bytes(name)
            if g is not None:
                return g
        for c in vm.cells:
            if c.alive and c.dem.gen_name == name:
                g0 = c.mm_p + c.dem.mg_p
                gsz = c.dem.mg_s or c.mm_s
                return bytes(vm.mem.soup[g0 : g0 + gsz])
        return None

    def cell_snapshot(self, vm: Any, cell_id: int) -> dict[str, Any] | None:
        if cell_id < 0 or cell_id >= len(vm.cells):
            return None
        c = vm.cells[cell_id]
        if not c.alive:
            return None
        return c.snapshot()
