# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Protocol ports for genebank / observer / net subsystems.

Subsystems must depend on these Protocols (and models), not on each other
or on ``services.vm``.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class GeneBankPort(Protocol):
    """Species registry + optional disk extract hooks."""

    enabled: bool

    def on_birth(
        self,
        *,
        cell_id: int,
        size: int,
        genome: bytes,
        mother_name: str,
        mother_hash: int | None,
        is_migrant: bool = False,
    ) -> str:
        """Register birth; return genotype name assigned to the cell."""
        ...

    def on_death(self, *, gen_name: str, cell_id: int) -> None:
        ...

    def register_inoculum(self, *, name: str, genome: bytes, permanent: bool = True) -> str:
        ...

    def list_genotypes(self) -> list[dict[str, Any]]:
        ...

    def get_genome_bytes(self, name: str) -> bytes | None:
        ...

    def mark_permanent(self, name: str, genome: bytes | None = None) -> None:
        ...

    def snapshot(self) -> dict[str, Any]:
        ...

    def restore(self, data: dict[str, Any]) -> None:
        ...


@runtime_checkable
class ObserverPort(Protocol):
    """Read-model / control façade used by TierraVM (in-process Beagle)."""

    def plan(self) -> dict[str, Any]:
        ...

    def overview(self) -> list[dict[str, Any]]:
        ...

    def histogram(self, kind: str = "size") -> dict[str, Any]:
        ...

    def genome_at(self, addr: int) -> bytes | None:
        ...

    def genome_of(self, name: str) -> bytes | None:
        ...

    def cell_snapshot(self, cell_id: int) -> dict[str, Any] | None:
        ...


@runtime_checkable
class MigrationPort(Protocol):
    """Host-side organism exchange (no sockets inside VM)."""

    def offer_emigrant(self, genome: bytes, meta: dict[str, Any]) -> Any:
        ...

    def poll_immigrants(self) -> list[tuple[bytes, dict[str, Any]]]:
        ...
