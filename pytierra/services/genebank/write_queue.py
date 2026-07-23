# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Deferred disk-bank write queue (flush outside ISA hot path)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class WriteJob:
    name: str
    genome: bytes
    hash: int
    permanent: bool = True
    pop: int = 0


class WriteQueue:
    def __init__(self, flush_fn: Callable[[WriteJob], bool] | None = None) -> None:
        self._pending: dict[str, WriteJob] = {}
        self._flush_fn = flush_fn
        self.flushed = 0
        self.skipped = 0

    def set_flush_fn(self, fn: Callable[[WriteJob], bool]) -> None:
        self._flush_fn = fn

    def enqueue(self, job: WriteJob) -> None:
        self._pending[job.name] = job

    def pending_count(self) -> int:
        return len(self._pending)

    def flush(self) -> int:
        if self._flush_fn is None:
            self._pending.clear()
            return 0
        n = 0
        for name, job in list(self._pending.items()):
            wrote = self._flush_fn(job)
            del self._pending[name]
            if wrote:
                self.flushed += 1
                n += 1
            else:
                self.skipped += 1
        if n:
            logger.info(
                "DiskBank flush wrote=%d skipped=%d",
                n,
                self.skipped,
                extra={"event": "genebank_flush"},
            )
        return n

    def snapshot(self) -> dict[str, Any]:
        return {
            "pending": [
                {
                    "name": j.name,
                    "genome": list(j.genome),
                    "hash": j.hash,
                    "permanent": j.permanent,
                    "pop": j.pop,
                }
                for j in self._pending.values()
            ]
        }

    def restore(self, data: dict[str, Any]) -> None:
        self._pending.clear()
        for item in data.get("pending", []):
            self._pending[item["name"]] = WriteJob(
                name=item["name"],
                genome=bytes(item["genome"]),
                hash=int(item["hash"]),
                permanent=bool(item.get("permanent", True)),
                pop=int(item.get("pop", 0)),
            )
