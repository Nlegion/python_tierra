# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""In-memory genebanker (size → hash → memcmp). Helpers: hashutil, labels."""

from __future__ import annotations

from typing import Any, Callable

from pytierra.models.genotype import BANKER_VERSION, GenotypeRecord, SizeClass
from pytierra.services.genebank.hashutil import default_hash, genomes_equal
from pytierra.services.genebank.labels import int_to_lbl, lbl_to_int, parse_genotype_name


class RamBanker:
    """RAM species table. Does not import services.vm."""

    enabled: bool = True

    def __init__(self, *, hasher: Callable[[bytes], int] | None = None) -> None:
        self._hasher = hasher or default_hash
        self._classes: dict[int, SizeClass] = {}
        self._by_name: dict[str, GenotypeRecord] = {}

    def _ensure_class(self, size: int) -> SizeClass:
        sc = self._classes.get(size)
        if sc is None:
            sc = SizeClass(size=size)
            self._classes[size] = sc
        return sc

    def hash_genome(self, genome: bytes) -> int:
        return self._hasher(genome)

    def _lookup(self, size: int, h: int, genome: bytes) -> GenotypeRecord | None:
        sc = self._classes.get(size)
        if sc is None:
            return None
        for rec in sc.by_label.values():
            if rec.hash != h:
                continue
            stored = rec.bytes_for_compare()
            if stored is not None and genomes_equal(stored, genome):
                return rec
        return None

    def _new_label(self, sc: SizeClass) -> str:
        while True:
            label = int_to_lbl(sc.next_gi)
            sc.next_gi += 1
            if label not in sc.by_label:
                return label

    def _add_record(
        self,
        *,
        size: int,
        label: str,
        h: int,
        genome: bytes,
        permanent: bool,
        parent: str,
        pop: int = 0,
    ) -> GenotypeRecord:
        sc = self._ensure_class(size)
        rec = GenotypeRecord(
            size=size,
            label=label,
            hash=h,
            pop=pop,
            permanent=permanent,
            parent=parent,
            genome=bytes(genome) if permanent else None,
            last_seen=bytes(genome),
        )
        sc.by_label[label] = rec
        self._by_name[rec.name] = rec
        sc.next_gi = max(sc.next_gi, lbl_to_int(label) + 1)
        return rec

    def register_inoculum(self, *, name: str, genome: bytes, permanent: bool = True) -> str:
        parsed = parse_genotype_name(name)
        if parsed is None:
            size = len(genome)
            label = self._new_label(self._ensure_class(size))
        else:
            size, label = parsed
            if size <= 0:
                size = len(genome)
        h = self.hash_genome(genome)
        existing = self._lookup(size, h, genome)
        if existing is not None:
            if permanent:
                existing.permanent = True
                existing.genome = bytes(genome)
            existing.last_seen = bytes(genome)
            return existing.name
        if name in self._by_name:
            rec = self._by_name[name]
            rec.hash = h
            rec.last_seen = bytes(genome)
            if permanent:
                rec.permanent = True
                rec.genome = bytes(genome)
            return rec.name
        sc = self._ensure_class(size)
        if label in sc.by_label:
            label = self._new_label(sc)
        rec = self._add_record(
            size=size,
            label=label,
            h=h,
            genome=genome,
            permanent=permanent,
            parent="",
            pop=0,
        )
        return rec.name

    def on_birth(
        self,
        *,
        cell_id: int,
        size: int,
        genome: bytes,
        mother_name: str,
        mother_hash: int | None,
        is_migrant: bool = False,
    ) -> str:
        del is_migrant  # same registration path; migration stats deferred
        del size
        gsize = len(genome)
        h = self.hash_genome(genome)
        if mother_name and mother_name in self._by_name:
            mrec = self._by_name[mother_name]
            stored = mrec.bytes_for_compare()
            if (
                mrec.size == gsize
                and stored is not None
                and genomes_equal(stored, genome)
                and (mother_hash is None or mrec.hash == h or mother_hash == h)
            ):
                mrec.pop += 1
                mrec.live_hint = cell_id
                mrec.last_seen = bytes(genome)
                mrec.hash = h
                return mrec.name
        match = self._lookup(gsize, h, genome)
        if match is not None:
            match.pop += 1
            match.live_hint = cell_id
            match.last_seen = bytes(genome)
            return match.name
        sc = self._ensure_class(gsize)
        label = self._new_label(sc)
        rec = self._add_record(
            size=gsize,
            label=label,
            h=h,
            genome=genome,
            permanent=False,
            parent=mother_name,
            pop=1,
        )
        rec.live_hint = cell_id
        return rec.name

    def on_death(self, *, gen_name: str, cell_id: int) -> None:
        rec = self._by_name.get(gen_name)
        if rec is None:
            return
        rec.pop = max(0, rec.pop - 1)
        if rec.live_hint == cell_id:
            rec.live_hint = -1
        if rec.pop == 0 and not rec.permanent:
            sc = self._classes.get(rec.size)
            if sc is not None:
                sc.by_label.pop(rec.label, None)
            self._by_name.pop(gen_name, None)

    def list_genotypes(self) -> list[dict[str, Any]]:
        out = []
        for rec in sorted(self._by_name.values(), key=lambda r: (r.size, r.label)):
            out.append(
                {
                    "name": rec.name,
                    "size": rec.size,
                    "label": rec.label,
                    "hash": rec.hash,
                    "pop": rec.pop,
                    "permanent": rec.permanent,
                    "parent": rec.parent,
                }
            )
        return out

    def get_genome_bytes(self, name: str) -> bytes | None:
        rec = self._by_name.get(name)
        if rec is None:
            return None
        return rec.bytes_for_compare()

    def mark_permanent(self, name: str, genome: bytes | None = None) -> None:
        rec = self._by_name.get(name)
        if rec is None:
            return
        rec.permanent = True
        if genome is not None:
            rec.genome = bytes(genome)
            rec.hash = self.hash_genome(genome)
            rec.last_seen = bytes(genome)
        elif rec.genome is None and rec.last_seen is not None:
            rec.genome = bytes(rec.last_seen)

    def find_live_genome(
        self,
        name: str,
        *,
        cells: list[Any],
        soup: bytes | bytearray,
    ) -> bytes | None:
        rec = self._by_name.get(name)
        if rec is None:
            return None
        if rec.genome is not None:
            return bytes(rec.genome)
        for c in cells:
            if not getattr(c, "alive", False):
                continue
            if c.dem.gen_name != name:
                continue
            g0 = c.mm_p + c.dem.mg_p
            gsz = c.dem.mg_s or c.mm_s
            return bytes(soup[g0 : g0 + gsz])
        return bytes(rec.last_seen) if rec.last_seen is not None else None

    def snapshot(self) -> dict[str, Any]:
        genotypes = []
        for rec in self._by_name.values():
            d = rec.to_dict()
            if not rec.permanent:
                d.pop("genome", None)
            genotypes.append(d)
        return {
            "banker_version": BANKER_VERSION,
            "enabled": True,
            "genotypes": genotypes,
            "next_gi": {str(sz): sc.next_gi for sz, sc in self._classes.items()},
        }

    def restore(self, data: dict[str, Any]) -> None:
        self._classes.clear()
        self._by_name.clear()
        if not data or not data.get("enabled", True):
            return
        for item in data.get("genotypes", []):
            rec = GenotypeRecord.from_dict(item)
            if not rec.permanent:
                rec.genome = None
            elif rec.genome is not None:
                rec.last_seen = bytes(rec.genome)
            sc = self._ensure_class(rec.size)
            sc.by_label[rec.label] = rec
            self._by_name[rec.name] = rec
        for sz_s, gi in data.get("next_gi", {}).items():
            sc = self._ensure_class(int(sz_s))
            sc.next_gi = int(gi)
