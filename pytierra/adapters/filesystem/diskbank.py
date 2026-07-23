# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""ASCII DiskBank: .tie files + genebank_index.json."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from pytierra.adapters.filesystem.genome import load_tie
from pytierra.core.errors import AssetError, ConfigError
from pytierra.models.genome import OpcodeMap
from pytierra.services.genebank.write_queue import WriteJob

logger = logging.getLogger(__name__)

INDEX_NAME = "genebank_index.json"


class DiskBankStore:
    def __init__(
        self,
        root: Path,
        *,
        opcode_map: OpcodeMap,
        backend: str = "json",
        fmt: str = "ascii",
    ) -> None:
        if fmt != "ascii":
            raise ConfigError(f"DiskBankFormat={fmt!r} not implemented (only ascii)")
        if backend != "json":
            raise ConfigError(f"DiskBankBackend={backend!r} not implemented (only json)")
        self.root = Path(root)
        self.opcode_map = opcode_map
        self.backend = backend
        self.fmt = fmt
        self.index: dict[str, dict[str, Any]] = {}
        self.root.mkdir(parents=True, exist_ok=True)
        self._load_index()

    def _index_path(self) -> Path:
        return self.root / INDEX_NAME

    def _load_index(self) -> None:
        path = self._index_path()
        if not path.is_file():
            self.index = {}
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.index = dict(data.get("genotypes", {}))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Bad genebank index: %s", exc, extra={"event": "genebank_index"})
            self.index = {}

    def save_index(self) -> None:
        path = self._index_path()
        payload = {
            "version": 1,
            "backend": self.backend,
            "format": self.fmt,
            "genotypes": self.index,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def tie_path(self, name: str) -> Path:
        return self.root / f"{name}.tie"

    def write_job(self, job: WriteJob) -> bool:
        """Write .tie if hash changed. Returns True if file was written."""
        prev = self.index.get(job.name)
        if prev is not None and int(prev.get("hash", -1)) == job.hash:
            prev["pop"] = job.pop
            prev["mtime"] = time.time()
            self.save_index()
            logger.info(
                "DiskBank skip rewrite name=%s hash=%s",
                job.name,
                job.hash,
                extra={"event": "genebank_extract"},
            )
            return False
        path = self.tie_path(job.name)
        self._write_tie(path, job.name, job.genome)
        self.index[job.name] = {
            "name": job.name,
            "size": len(job.genome),
            "label": job.name[4:] if len(job.name) >= 7 else "",
            "hash": job.hash,
            "pop": job.pop,
            "permanent": job.permanent,
            "path": path.name,
            "mtime": time.time(),
        }
        self.save_index()
        logger.info(
            "DiskBank extract name=%s bytes=%d",
            job.name,
            len(job.genome),
            extra={"event": "genebank_extract"},
        )
        return True

    def _write_tie(self, path: Path, name: str, genome: bytes) -> None:
        # reverse opcode map for mnemonics
        by_op = {idef.op: idef.mnemonic for idef in self.opcode_map.by_op}
        lines = [
            "format: tie",
            f"genotype: {name}",
            f"size: {len(genome)}",
            "CODE",
            "track 0:",
        ]
        for b in genome:
            mn = by_op.get(b & 0xFF, f"op{b & 0xFF}")
            lines.append(mn)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def load_genome(self, name: str) -> bytes:
        path = self.tie_path(name)
        if not path.is_file():
            # try stem without forcing path
            raise AssetError(f"DiskBank genome not found: {name}")
        g = load_tie(path, self.opcode_map)
        # prefer filename stem if header missing
        if not g.meta.genotype:
            g.meta.genotype = path.stem
        return bytes(b & 0xFF for b in g.code)

    def list_names(self) -> list[str]:
        names = set(self.index.keys())
        for p in self.root.glob("*.tie"):
            names.add(p.stem)
        return sorted(names)
