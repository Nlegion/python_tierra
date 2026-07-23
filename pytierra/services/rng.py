# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Tierra RNG port of trand.c (Numerical Recipes style)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pytierra.core.errors import InternalError

M1 = 259200
IA1 = 7141
IC1 = 54773
RM1 = 1.0 / M1
M2 = 134456
IA2 = 8121
IC2 = 28411
RM2 = 1.0 / M2
M3 = 243000
IA3 = 4561
IC3 = 51349

I32S_MAX = 2147483647
I16S_MAX = 32767
I8S_MAX = 127


def _trand_index(rand_ix3: int) -> int:
    """Map RandIx3 to TrandArray index; raise on invariant violation."""
    j = int(1 + ((97 * rand_ix3) / M3))
    if j > 97 or j < 1:
        raise InternalError("Tierra tdrand() index out of range")
    return j


@dataclass
class TierraRNG:
    """Single RNG state: tsrand seeds; tdrand advances; tlrand/tirand/tcrand wrap tdrand."""

    RandIx1: int = 0
    RandIx2: int = 0
    RandIx3: int = 0
    TrandArray: list[float] = field(default_factory=lambda: [0.0] * 98)

    def tsrand(self, seed: int) -> None:
        self.RandIx1 = (IC1 + int(seed)) % M1
        self.RandIx1 = (IA1 * self.RandIx1 + IC1) % M1
        self.RandIx2 = self.RandIx1 % M2
        self.RandIx1 = (IA1 * self.RandIx1 + IC1) % M1
        self.RandIx3 = self.RandIx1 % M3
        for j in range(1, 98):
            self.RandIx1 = (IA1 * self.RandIx1 + IC1) % M1
            self.RandIx2 = (IA2 * self.RandIx2 + IC2) % M2
            self.TrandArray[j] = (self.RandIx1 + self.RandIx2 * RM2) * RM1

    def tdrand(self) -> float:
        self.RandIx1 = (IA1 * self.RandIx1 + IC1) % M1
        self.RandIx2 = (IA2 * self.RandIx2 + IC2) % M2
        self.RandIx3 = (IA3 * self.RandIx3 + IC3) % M3
        j = _trand_index(self.RandIx3)
        temp = self.TrandArray[j]
        self.TrandArray[j] = (self.RandIx1 + self.RandIx2 * RM2) * RM1
        return temp

    def tlrand(self) -> int:
        return int(self.tdrand() * (float(I32S_MAX) + 1.0))

    def tirand(self) -> int:
        return int(self.tdrand() * (float(I16S_MAX) + 1.0))

    def tcrand(self) -> int:
        return int(self.tdrand() * (float(I8S_MAX) + 1.0))

    def snapshot(self) -> dict[str, Any]:
        return {
            "RandIx1": self.RandIx1,
            "RandIx2": self.RandIx2,
            "RandIx3": self.RandIx3,
            "TrandArray": list(self.TrandArray),
        }

    def restore(self, data: dict[str, Any]) -> None:
        self.RandIx1 = int(data["RandIx1"])
        self.RandIx2 = int(data["RandIx2"])
        self.RandIx3 = int(data["RandIx3"])
        self.TrandArray = list(data["TrandArray"])
