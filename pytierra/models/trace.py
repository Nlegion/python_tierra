# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Ring-buffer instruction trace."""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from typing import Any

from pytierra.core.settings.constants import DEFAULT_TRACE_CAPACITY


@dataclass
class TraceRecord:
    cycle: int
    cell_id: int
    ip: int
    opcode: int
    mnemonic: str
    operands: dict[str, Any]
    result: str | None = None
    err: str | None = None


class TraceBuffer:
    def __init__(self, capacity: int = DEFAULT_TRACE_CAPACITY) -> None:
        self.capacity = capacity
        self.enabled = False
        self._buf: deque[TraceRecord] = deque(maxlen=capacity)

    def clear(self) -> None:
        self._buf.clear()

    def append(self, record: TraceRecord) -> None:
        if self.enabled:
            self._buf.append(record)

    def get_trace(self) -> list[dict[str, Any]]:
        return [asdict(r) for r in self._buf]
