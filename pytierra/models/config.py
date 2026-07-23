# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Tierra configuration model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pytierra.core.settings.constants import (
    DEFAULT_MAL_MODE,
    DEFAULT_SLICE_SIZE,
    DEFAULT_SLICE_STYLE,
    DEFAULT_SOUP_SIZE,
)


@dataclass
class TierraConfig:
    values: dict[str, Any] = field(default_factory=dict)
    inoculum: list[str] = field(default_factory=list)
    place_center: bool = False
    unknown_keys: list[str] = field(default_factory=list)

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    @property
    def soup_size(self) -> int:
        return int(self.get("SoupSize", DEFAULT_SOUP_SIZE))

    @property
    def slice_size(self) -> int:
        return int(self.get("SliceSize", DEFAULT_SLICE_SIZE))

    @property
    def slice_style(self) -> int:
        return int(self.get("SliceStyle", DEFAULT_SLICE_STYLE))

    @property
    def mal_mode(self) -> int:
        return int(self.get("MalMode", DEFAULT_MAL_MODE))

    @property
    def seed(self) -> int:
        return int(self.get("seed", 1))

    @property
    def num_cells(self) -> int:
        return int(self.get("NumCells", 1))

    @property
    def genebank_path(self) -> str:
        return str(self.get("GenebankPath", "gb0/"))

    @property
    def imap_file(self) -> str:
        return str(self.get("IMapFile", "opcode.map"))
