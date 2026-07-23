# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Sandbox limits for TierraVM."""

from __future__ import annotations

from dataclasses import dataclass

from pytierra.core.errors import SandboxLimitError
from pytierra.core.settings.constants import (
    DEFAULT_LIMIT_CHECK_EVERY,
    DEFAULT_MAX_CELLS,
    DEFAULT_MAX_INSTRUCTIONS,
    DEFAULT_MAX_SOUP_SIZE,
    DEFAULT_WALL_TIME_S,
)

__all__ = ["SandboxLimitError", "SandboxLimits"]


@dataclass
class SandboxLimits:
    max_instructions: int = DEFAULT_MAX_INSTRUCTIONS
    max_cells: int = DEFAULT_MAX_CELLS
    max_soup_size: int = DEFAULT_MAX_SOUP_SIZE
    wall_time_s: float = DEFAULT_WALL_TIME_S
    limit_check_every: int = DEFAULT_LIMIT_CHECK_EVERY
