# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""No-op GeneBankPort when GeneBnker is off."""

from __future__ import annotations

from typing import Any


class NoOpGeneBank:
    enabled: bool = False

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
        return f"{size:04d}???"

    def on_death(self, *, gen_name: str, cell_id: int) -> None:
        return None

    def register_inoculum(self, *, name: str, genome: bytes, permanent: bool = True) -> str:
        return name

    def list_genotypes(self) -> list[dict[str, Any]]:
        return []

    def get_genome_bytes(self, name: str) -> bytes | None:
        return None

    def mark_permanent(self, name: str, genome: bytes | None = None) -> None:
        return None

    def snapshot(self) -> dict[str, Any]:
        return {"banker_version": 1, "enabled": False, "genotypes": []}

    def restore(self, data: dict[str, Any]) -> None:
        return None
