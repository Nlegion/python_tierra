# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""ctemplate — complementary NOP template search."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytierra.services.memory.soup import SoupMemory


def ctemplate(
    mem: SoupMemory,
    *,
    ip: int,
    f_start: int,
    b_start: int,
    slim: int,
    tz: int,
    direction: str,
    nop0: int,
    nop1: int,
    nop_s: int,
    min_templ_size: int,
    mode_pref: int = 1,
) -> tuple[int, int, int]:
    """Search for complementary template.

    Returns (address_after_template_or_-1, mode_found, distance).
    mode_found: 0 none, 1 fwd, 2 bkwd, 3 both preference used.
    """
    if tz < min_templ_size or tz > mem.soup_size:
        return -1, 0, 0
    df = direction in ("o", "f")
    db = direction in ("o", "b")
    f = mem.ad(f_start)
    b = mem.ad(b_start)
    o = mem.ad(ip + 1)
    soup = mem.soup
    dist = 1
    while True:
        # skip non-NOP
        while True:
            f_ok = df and soup[f] in (nop0, nop1)
            b_ok = db and soup[b] in (nop0, nop1)
            if f_ok or b_ok:
                break
            if df:
                f = mem.ad(f + 1)
            if db:
                b = mem.ad(b - 1)
            dist += 1
            if dist > slim:
                return -1, 0, dist

        fmatch = 0
        if df and soup[f] in (nop0, nop1):
            fmatch = 1
            for i in range(tz):
                if soup[mem.ad(o + i)] + soup[mem.ad(f + i)] - nop_s:
                    fmatch = 0
                    break

        bmatch = 0
        if db and soup[b] in (nop0, nop1):
            bmatch = 1
            for i in range(tz):
                if soup[mem.ad(o + i)] + soup[mem.ad(b + i)] - nop_s:
                    bmatch = 0
                    break

        if fmatch and bmatch:
            if mode_pref == 1:
                return mem.ad(f + tz), 3, dist
            if mode_pref == 2:
                return mem.ad(b + tz), 3, dist
        elif fmatch:
            return mem.ad(f + tz), 1, dist
        elif bmatch:
            return mem.ad(b + tz), 2, dist

        if db:
            b = mem.ad(b - 1)
        if df:
            f = mem.ad(f + 1)
        dist += 1
        if dist > slim:
            return -1, 0, dist
