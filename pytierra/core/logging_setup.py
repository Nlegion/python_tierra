# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Optional logging configuration for CLI / integrators."""

from __future__ import annotations

import logging

_DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def configure_logging(
    level: int = logging.INFO,
    format: str | None = None,
) -> None:
    """Configure root logging once. No-op if root already has handlers."""
    if logging.root.handlers:
        return
    logging.basicConfig(level=level, format=format or _DEFAULT_FORMAT)
