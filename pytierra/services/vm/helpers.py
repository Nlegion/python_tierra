# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Shared VM helpers (no import of service.py)."""

from __future__ import annotations

import logging
import time

from pytierra.core.errors import SandboxLimitError
from pytierra.models.limits import SandboxLimits

logger = logging.getLogger(__name__)


def check_limits(
    limits: SandboxLimits,
    *,
    budget_used: int,
    run_started: float,
    force: bool = False,
) -> None:
    if force or (budget_used % limits.limit_check_every == 0):
        if budget_used >= limits.max_instructions:
            logger.warning(
                "Sandbox limit exceeded: max_instructions=%d, executed=%d",
                limits.max_instructions,
                budget_used,
                extra={"event": "sandbox_limit"},
            )
            raise SandboxLimitError(
                "max_instructions exceeded",
                kind="max_instructions",
            )
        if limits.wall_time_s > 0 and run_started:
            elapsed = time.perf_counter() - run_started
            if elapsed > limits.wall_time_s:
                logger.warning(
                    "Sandbox limit exceeded: wall_time_s=%s, elapsed=%s",
                    limits.wall_time_s,
                    elapsed,
                    extra={"event": "sandbox_limit"},
                )
                raise SandboxLimitError(
                    "wall_time_s exceeded",
                    kind="wall_time_s",
                )
