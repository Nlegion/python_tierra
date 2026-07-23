# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""VM snapshot / restore (no import of service.py)."""

from __future__ import annotations

import logging
from typing import Any

from pytierra.core.errors import InternalError, StateError
from pytierra.models.cell import Cell
from pytierra.services.memory.queues import CellQueues
from pytierra.services.memory.soup import SoupMemory

logger = logging.getLogger(__name__)


def take_snapshot(vm: Any) -> dict[str, Any]:
    return {
        "soup": vm.mem.snapshot(),
        "cells": [c.snapshot() for c in vm.cells],
        "queues": {
            "this_slice": vm.queues.this_slice,
            "top_reap": vm.queues.top_reap,
            "bottom_reap": vm.queues.bottom_reap,
            "num_cells": vm.queues.num_cells,
        },
        "rng": vm.rng.snapshot(),
        "inst_exe": vm.inst_exe,
        "budget_used": vm.budget_used,
        "average_size": vm.average_size,
        "counters": dict(vm.counters),
        "rates": {
            "rate_mut": vm.rate_mut,
            "count_mut": vm.count_mut,
            "rate_mov_mut": vm.rate_mov_mut,
            "count_mov_mut": vm.count_mov_mut,
            "rate_flaw": vm.rate_flaw,
            "count_flaw": vm.count_flaw,
        },
        "stopped": vm.stopped,
        "config": dict(vm.config.values),
        "inoculum": list(vm.config.inoculum),
        "place_center": vm.config.place_center,
    }


def restore_snapshot(vm: Any, snap: dict[str, Any]) -> None:
    try:
        required = (
            "soup",
            "cells",
            "queues",
            "rng",
            "inst_exe",
            "budget_used",
            "average_size",
            "counters",
            "rates",
        )
        for key in required:
            if key not in snap:
                raise StateError(f"snapshot missing key: {key}")
        vm.mem = SoupMemory.from_snapshot(snap["soup"])
        try:
            vm.cells = [Cell.from_snapshot(c) for c in snap["cells"]]
        except (KeyError, TypeError, ValueError) as exc:
            raise InternalError(f"corrupt cell snapshot: {exc}") from exc
        q = snap["queues"]
        vm.queues = CellQueues()
        vm.queues.this_slice = q["this_slice"]
        vm.queues.top_reap = q["top_reap"]
        vm.queues.bottom_reap = q["bottom_reap"]
        vm.queues.num_cells = q["num_cells"]
        vm.rng.restore(snap["rng"])
        vm.inst_exe = int(snap["inst_exe"])
        vm.budget_used = int(snap["budget_used"])
        vm.average_size = int(snap["average_size"])
        vm.counters = dict(snap["counters"])
        r = snap["rates"]
        vm.rate_mut = r["rate_mut"]
        vm.count_mut = r["count_mut"]
        vm.rate_mov_mut = r["rate_mov_mut"]
        vm.count_mov_mut = r["count_mov_mut"]
        vm.rate_flaw = r["rate_flaw"]
        vm.count_flaw = r["count_flaw"]
        vm.stopped = bool(snap.get("stopped", False))
        vm._started = True
    except StateError:
        logger.error("Restore failed: invalid snapshot", extra={"event": "state_error"})
        raise
    except InternalError:
        logger.error("Restore failed: internal invariant", extra={"event": "internal_error"})
        raise
    except (KeyError, TypeError, ValueError) as exc:
        logger.error(
            "Restore failed: %s",
            exc,
            extra={"event": "state_error"},
        )
        raise StateError(f"invalid snapshot: {exc}") from exc
    logger.info("Snapshot restored", extra={"event": "restore"})
