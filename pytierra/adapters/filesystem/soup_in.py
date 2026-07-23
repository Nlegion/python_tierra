# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Parse and load soup_in-style configuration files."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from pytierra.core.errors import AssetError
from pytierra.core.settings.constants import (
    DEFAULT_LAZY_TOL,
    DEFAULT_MAL_MODE,
    DEFAULT_MAL_TOL,
    DEFAULT_MAX_MAL_MULT,
    DEFAULT_MIN_CELL_SIZE,
    DEFAULT_MIN_GEN_MEM_SIZ,
    DEFAULT_MIN_TEMPL_SIZE,
    DEFAULT_MOV_PROP_THR_DIV,
    DEFAULT_NUM_CELLS_MIN,
    DEFAULT_SEARCH_LIMIT,
    DEFAULT_SLICE_SIZE,
    DEFAULT_SLICE_STYLE,
    DEFAULT_SOUP_SIZE,
)
from pytierra.models.config import TierraConfig

logger = logging.getLogger(__name__)

_KNOWN = {
    "SoupSize", "SliceSize", "SliceStyle", "SizDepSlice", "SlicePow",
    "SlicFixFrac", "SlicRanFrac", "MalMode", "MalTol", "MalSamSiz",
    "MalReapTol", "MaxMalMult", "SearchLimit", "AbsSearchLimit",
    "MovPropThrDiv", "MinCellSize", "MinGenMemSiz", "MinTemplSize",
    "NumCells", "NumCellsMin", "GenebankPath", "IMapFile", "seed",
    "new_soup", "alive", "AliveGen", "LazyTol", "DropDead",
    "GenPerBkgMut", "GenPerFlaw", "GenPerMovMut", "GenPerDivMut",
    "GenPerCroInsSamSiz", "GenPerInsIns", "GenPerDelIns", "GenPerCroIns",
    "GenPerDelSeg", "GenPerInsSeg", "GenPerCroSeg", "MutBitProp",
    "MemModeFree", "MemModeMine", "MemModeProt", "DivSameGen", "DivSameSiz",
    "debug", "DiskBank", "GeneBnker", "TierraLog",
}


def _parse_value(raw: str) -> Any:
    raw = raw.strip()
    if not raw:
        return ""
    token = raw.split()[0] if raw[0].isdigit() or raw[0] in "+-." else raw
    m = re.match(r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$", token)
    if m:
        if "." in token or "e" in token.lower():
            return float(token)
        return int(token)
    return token


def parse_soup_in(text: str) -> TierraConfig:
    cfg = TierraConfig()
    in_inoculum = False
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if not in_inoculum and "=" in s:
            left, right = s.split("=", 1)
            key = left.strip()
            val_part = right.strip()
            if not key:
                continue
            if key not in _KNOWN:
                cfg.unknown_keys.append(key)
                logger.warning(
                    "Ignoring unknown soup_in key: %s",
                    key,
                    extra={"event": "unknown_config_key"},
                )
            cfg.values[key] = _parse_value(val_part)
            continue
        in_inoculum = True
        name = s.split()[0]
        if name == "center":
            cfg.place_center = True
            continue
        if name == "space":
            continue
        cfg.inoculum.append(name)
    defaults = {
        "SoupSize": DEFAULT_SOUP_SIZE,
        "SliceSize": DEFAULT_SLICE_SIZE,
        "SliceStyle": DEFAULT_SLICE_STYLE,
        "SizDepSlice": 0,
        "SlicFixFrac": 0.0,
        "SlicRanFrac": 2.0,
        "MalMode": DEFAULT_MAL_MODE,
        "MalTol": DEFAULT_MAL_TOL,
        "MalSamSiz": 0,
        "MaxMalMult": DEFAULT_MAX_MAL_MULT,
        "SearchLimit": DEFAULT_SEARCH_LIMIT,
        "AbsSearchLimit": 0,
        "MovPropThrDiv": DEFAULT_MOV_PROP_THR_DIV,
        "MinCellSize": DEFAULT_MIN_CELL_SIZE,
        "MinGenMemSiz": DEFAULT_MIN_GEN_MEM_SIZ,
        "MinTemplSize": DEFAULT_MIN_TEMPL_SIZE,
        "NumCells": 1,
        "NumCellsMin": DEFAULT_NUM_CELLS_MIN,
        "LazyTol": DEFAULT_LAZY_TOL,
        "GenebankPath": "gb0/",
        "IMapFile": "opcode.map",
        "seed": 1,
        "GenPerBkgMut": 0,
        "GenPerFlaw": 0,
        "GenPerMovMut": 0,
        "GenPerDivMut": 0,
        "GenPerCroInsSamSiz": 0,
        "GenPerInsIns": 0,
        "GenPerDelIns": 0,
        "GenPerCroIns": 0,
        "GenPerDelSeg": 0,
        "GenPerInsSeg": 0,
        "GenPerCroSeg": 0,
        "MutBitProp": 0.2,
        "MemModeFree": 0,
        "MemModeMine": 0,
        "MemModeProt": 2,
        "DivSameGen": 0,
        "DivSameSiz": 0,
    }
    for k, v in defaults.items():
        cfg.values.setdefault(k, v)
    return cfg


def load_soup_in(path: Path | str) -> TierraConfig:
    path = Path(path)
    if not path.is_file():
        logger.error("Config file not found: %s", path, extra={"event": "asset_error"})
        raise AssetError(f"Config file not found: {path}")
    logger.info("Loading soup_in path=%s", path, extra={"event": "load_config"})
    return parse_soup_in(path.read_text(encoding="utf-8", errors="replace"))
