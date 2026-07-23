# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Load opcode.map and .tie genomes from the filesystem."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from pytierra.core.errors import AssetError
from pytierra.models.genome import Genome, GenomeMeta, InstDef, OpcodeMap

logger = logging.getLogger(__name__)

_MAP_LINE = re.compile(
    r'\{\s*(\d+)\s*,\s*(\d+)\s*,\s*"([^"]+)"\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"'
)


def load_opcode_map(path: Path | str) -> OpcodeMap:
    path = Path(path)
    if not path.is_file():
        logger.error("Opcode map not found: %s", path, extra={"event": "asset_error"})
        raise AssetError(f"Opcode map not found: {path}")
    omp = OpcodeMap()
    text = path.read_text(encoding="utf-8", errors="replace")
    opc = 0
    for line in text.splitlines():
        m = _MAP_LINE.search(line)
        if not m:
            continue
        _op0, cyc, mn, execute, decode, regs_s, flags_s = m.groups()
        regs: list[int] = []
        flag_c = False
        for ch in regs_s:
            if "a" <= ch <= "z":
                regs.append(ord(ch) - ord("a"))
            elif ch == " ":
                regs.append(-1)
                flag_c = True
        if "C" in flags_s:
            flag_c = True
        idef = InstDef(
            op=opc,
            cyc=int(cyc),
            mnemonic=mn,
            regs=regs,
            flag_C=flag_c,
            decode=decode,
            execute=execute,
        )
        omp.by_op.append(idef)
        omp.by_name[mn] = idef
        if mn == "nop0":
            omp.nop0 = opc
        elif mn == "nop1":
            omp.nop1 = opc
        opc += 1
    if not omp.by_op:
        logger.error("No opcodes parsed from %s", path, extra={"event": "asset_error"})
        raise AssetError(f"No opcodes parsed from {path}")
    logger.info(
        "Loaded opcode map path=%s opcodes=%d",
        path,
        omp.inst_num,
        extra={"event": "load_opcode_map"},
    )
    return omp


def load_tie(path: Path | str, opcode_map: OpcodeMap) -> Genome:
    path = Path(path)
    if not path.is_file():
        logger.error("Genome file not found: %s", path, extra={"event": "asset_error"})
        raise AssetError(f"Genome file not found: {path}")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    meta = GenomeMeta()
    in_code = False
    accepting = False
    code: list[int] = []
    for line in lines:
        stripped = line.strip()
        if not in_code:
            meta.header_lines.append(line)
            if stripped.lower().startswith("genotype:"):
                parts = stripped.split()
                if len(parts) >= 2:
                    meta.genotype = parts[1]
            if stripped.upper() == "CODE":
                in_code = True
            continue
        if stripped.startswith("track"):
            accepting = "0" in stripped.split()[1] if len(stripped.split()) > 1 else False
            continue
        if not accepting:
            continue
        if not stripped or stripped.startswith(";"):
            continue
        mn = stripped.split()[0]
        if mn not in opcode_map.by_name:
            logger.error(
                "Unknown mnemonic %s in %s",
                mn,
                path,
                extra={"event": "asset_error"},
            )
            raise AssetError(f"Unknown mnemonic {mn!r} in {path}")
        code.append(opcode_map.by_name[mn].op)
    if not meta.genotype:
        meta.genotype = path.stem
    logger.info(
        "Loaded genome genotype=%s size=%d path=%s",
        meta.genotype,
        len(code),
        path,
        extra={"event": "load_genome"},
    )
    return Genome(meta=meta, code=code)
