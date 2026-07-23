# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Host/API exception hierarchy for Tierra-VM."""

from __future__ import annotations


class TierraError(Exception):
    """Base error for Tierra-VM host/API failures."""


class SandboxLimitError(TierraError):
    """Host budget exceeded (max_instructions / wall_time_s) or create-time max_soup_size.

    VM state remains valid; raise only stops step/run until set_limits / intervention.
    """

    def __init__(self, message: str, *, kind: str) -> None:
        super().__init__(message)
        self.kind = kind


class ResourceExhaustedError(TierraError):
    """Operation could not complete due to a resource limit; simulation may continue.

    Prefer CPU flag soft-fail (fl.E) inside the ISA for mal/divide; use this type
    only if an API wrapper needs to surface the condition without stopping the VM.
    """


class ConfigError(TierraError):
    """Invalid or incomplete configuration / inoculum."""


class AssetError(TierraError):
    """Missing or unreadable genome / opcode map asset."""


class StateError(TierraError):
    """Invalid VM API state (e.g. step before start, corrupt restore input)."""


class InternalError(TierraError):
    """Simulator invariant violated — indicates a bug, not a user mistake."""
