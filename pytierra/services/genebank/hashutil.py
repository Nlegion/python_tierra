# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Genome hashing helpers (64-bit content hash + memcmp)."""

from __future__ import annotations

import hashlib
from typing import Callable

Hasher = Callable[[bytes], int]


def default_hash(data: bytes) -> int:
    """64-bit blake2b digest (stdlib; hash+memcmp protocol, not crypto auth)."""
    return int.from_bytes(hashlib.blake2b(data, digest_size=8).digest(), "little")


def genomes_equal(a: bytes, b: bytes) -> bool:
    return a == b
