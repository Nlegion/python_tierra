# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Genotype metadata for RamBanker."""

from __future__ import annotations

from dataclasses import dataclass, field

BANKER_VERSION = 1


@dataclass
class GenotypeRecord:
    size: int
    label: str
    hash: int
    pop: int = 0
    permanent: bool = False
    parent: str = ""
    genome: bytes | None = None  # only for permanent (and snapshot)
    live_hint: int = -1  # optional cell_id
    last_seen: bytes | None = field(default=None, repr=False)  # RAM only, not snapshotted

    @property
    def name(self) -> str:
        return f"{self.size:04d}{self.label}"

    def bytes_for_compare(self) -> bytes | None:
        if self.genome is not None:
            return self.genome
        return self.last_seen

    def to_dict(self) -> dict:
        d = {
            "size": self.size,
            "label": self.label,
            "hash": self.hash,
            "pop": self.pop,
            "permanent": self.permanent,
            "parent": self.parent,
            "live_hint": self.live_hint,
        }
        if self.permanent and self.genome is not None:
            d["genome"] = list(self.genome)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> GenotypeRecord:
        g = data.get("genome")
        return cls(
            size=int(data["size"]),
            label=str(data["label"]),
            hash=int(data["hash"]),
            pop=int(data.get("pop", 0)),
            permanent=bool(data.get("permanent", False)),
            parent=str(data.get("parent", "")),
            genome=bytes(g) if g is not None else None,
            live_hint=int(data.get("live_hint", -1)),
        )


@dataclass
class SizeClass:
    size: int
    by_label: dict[str, GenotypeRecord] = field(default_factory=dict)
    next_gi: int = 0
