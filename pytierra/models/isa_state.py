# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Per-instruction decode/execute state."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InstState:
    iip: int = 1
    dib: int = 1
    di: int = 0
    oip: int = 0
    mode: int = 0
    mode2: int = 0
    dreg_i: int = -1  # register index, or -2 for IP, -3 bitbucket
    dreg2_i: int = -3
    dreg3_i: int = -3
    sval: int = 0
    sval2: int = 0
    sval3: int = 0
    dval: int = 0
    dval2: int = 0
    dmod: int = 0
    dmod2: int = 0
    dmod3: int = 0
    dran: int = 0
    dran2: int = 0
    dran3: int = 0
    extras: dict = field(default_factory=dict)
