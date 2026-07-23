# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""In-process MigrationPort connecting multiple TierraVM instances."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


class InMemoryTransport:
    """Shared mailbox keyed by node id. No sockets."""

    def __init__(self) -> None:
        self._boxes: dict[str, deque[tuple[bytes, dict[str, Any]]]] = defaultdict(deque)
        self.rejected = 0

    def offer_emigrant(
        self,
        genome: bytes,
        meta: dict[str, Any],
        *,
        dest: str,
    ) -> str:
        self._boxes[dest].append((bytes(genome), dict(meta)))
        return "ok"

    def poll_immigrants(self, node_id: str) -> list[tuple[bytes, dict[str, Any]]]:
        box = self._boxes.get(node_id)
        if not box:
            return []
        out = list(box)
        box.clear()
        return out
