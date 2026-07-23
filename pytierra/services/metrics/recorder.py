# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Lightweight metrics buffer (Observer). No heavy work in event handlers."""

from __future__ import annotations

from typing import Any


class MetricsRecorder:
    """Append-only buffers for stats samples and birth/death events."""

    def __init__(self, *, sample_every: int = 100) -> None:
        self.sample_every = max(1, int(sample_every))
        self.samples: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self._last_sample_inst = -1

    def on_birth(
        self,
        *,
        inst_exe: int,
        cell_id: int,
        gen_name: str,
        parent: str = "",
        size: int = 0,
        is_migrant: bool = False,
    ) -> None:
        self.events.append(
            {
                "kind": "birth",
                "InstExe": inst_exe,
                "cell_id": cell_id,
                "gen_name": gen_name,
                "parent": parent,
                "size": size,
                "is_migrant": is_migrant,
            }
        )

    def on_death(self, *, inst_exe: int, cell_id: int, gen_name: str) -> None:
        self.events.append(
            {
                "kind": "death",
                "InstExe": inst_exe,
                "cell_id": cell_id,
                "gen_name": gen_name,
            }
        )

    def maybe_sample(self, stats: dict[str, Any]) -> None:
        inst = int(stats.get("InstExe", 0))
        if self._last_sample_inst < 0 or inst - self._last_sample_inst >= self.sample_every:
            self.samples.append(dict(stats))
            self._last_sample_inst = inst

    def to_records(self) -> dict[str, list[dict[str, Any]]]:
        return {"samples": list(self.samples), "events": list(self.events)}

    def dataframe(self):
        """Return pandas DataFrame of samples (requires pandas / [viz])."""
        try:
            import pandas as pd
        except ImportError as exc:
            raise ImportError('pip install -e ".[viz]" for dataframe()') from exc
        return pd.DataFrame(self.samples)

    def birth_edges(self, *, max_edges: int | None = 500) -> list[tuple[str, str]]:
        """Parent→child genotype edges from birth events (last N if max_edges set)."""
        edges: list[tuple[str, str]] = []
        for ev in self.events:
            if ev.get("kind") != "birth":
                continue
            parent = ev.get("parent") or ""
            child = ev.get("gen_name") or ""
            if parent and child and parent != child:
                edges.append((parent, child))
        if max_edges is not None and len(edges) > max_edges:
            edges = edges[-max_edges:]
        return edges
