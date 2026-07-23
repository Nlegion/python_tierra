# Derivative work of Tierra Simulator V5.0 / v6.02
# Copyright (c) 1991 - 1998 Thomas S. Ray / Virtual Life
# See legacy/tierra/license.h. This is a Python reimplementation of the core VM.
"""Python Tierra-VM package."""

from pytierra.core.errors import (
    AssetError,
    ConfigError,
    InternalError,
    ResourceExhaustedError,
    SandboxLimitError,
    StateError,
    TierraError,
)
from pytierra.services.vm.service import TierraVM

__all__ = [
    "TierraVM",
    "TierraError",
    "SandboxLimitError",
    "ResourceExhaustedError",
    "ConfigError",
    "AssetError",
    "StateError",
    "InternalError",
]
__version__ = "0.1.0"
