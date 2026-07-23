# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Cell, Cpu, and Dem structures."""

from __future__ import annotations

from dataclasses import dataclass, field

from pytierra.core.settings.constants import NUMREG, STACK_SIZE


@dataclass
class Flags:
    E: int = 0
    S: int = 0
    Z: int = 0


@dataclass
class Cpu:
    re: list[int] = field(default_factory=lambda: [0] * NUMREG)
    ip: int = 0
    sp: int = 0
    st: list[int] = field(default_factory=lambda: [0] * STACK_SIZE)
    fl: Flags = field(default_factory=Flags)
    slicexit: int = 0


@dataclass
class Dem:
    gen_name: str = ""
    gen_size: int = 0
    gi: int = -1
    mg_p: int = 0
    mg_s: int = 0
    fecundity: int = 0
    flags: int = 0
    mov_daught: int = 0
    MovOffMin: int = 0
    MovOffMax: int = 0
    inst: int = 0
    repinst: int = 0
    mut: int = 0
    flaw: int = 0
    is_active: int = 0  # in slicer
    dm: int = 0  # 0 mother, 1 daughter
    nonslfmut: int = 0
    daughter_id: int = -1  # index of pending daughter cell, else -1


@dataclass
class Cell:
    cell_id: int
    alive: bool = False
    mm_p: int = 0
    mm_s: int = 0
    md_p: int = 0
    md_s: int = 0
    cpu: Cpu = field(default_factory=Cpu)
    dem: Dem = field(default_factory=Dem)
    # circular slicer / reaper links (indices into vm.cells)
    n_time: int = -1
    p_time: int = -1
    n_reap: int = -1
    p_reap: int = -1

    def snapshot(self) -> dict:
        return {
            "cell_id": self.cell_id,
            "alive": self.alive,
            "mm_p": self.mm_p,
            "mm_s": self.mm_s,
            "md_p": self.md_p,
            "md_s": self.md_s,
            "cpu": {
                "re": list(self.cpu.re),
                "ip": self.cpu.ip,
                "sp": self.cpu.sp,
                "st": list(self.cpu.st),
                "fl": {"E": self.cpu.fl.E, "S": self.cpu.fl.S, "Z": self.cpu.fl.Z},
            },
            "dem": self.dem.__dict__.copy(),
            "n_time": self.n_time,
            "p_time": self.p_time,
            "n_reap": self.n_reap,
            "p_reap": self.p_reap,
        }

    @classmethod
    def from_snapshot(cls, data: dict) -> Cell:
        cell = cls(cell_id=int(data["cell_id"]))
        cell.alive = bool(data["alive"])
        cell.mm_p = int(data["mm_p"])
        cell.mm_s = int(data["mm_s"])
        cell.md_p = int(data["md_p"])
        cell.md_s = int(data["md_s"])
        c = data["cpu"]
        cell.cpu = Cpu(
            re=list(c["re"]),
            ip=int(c["ip"]),
            sp=int(c["sp"]),
            st=list(c["st"]),
            fl=Flags(**c["fl"]),
        )
        cell.dem = Dem(**data["dem"])
        cell.n_time = int(data["n_time"])
        cell.p_time = int(data["p_time"])
        cell.n_reap = int(data["n_reap"])
        cell.p_reap = int(data["p_reap"])
        return cell
