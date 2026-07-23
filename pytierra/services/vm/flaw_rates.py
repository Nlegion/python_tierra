# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""C-bootstrap CalcFlawRates (InstExe.m == 0 path from bookeep.c)."""

from __future__ import annotations

from dataclasses import dataclass

from pytierra.core.settings.constants import PLOIDY


@dataclass(frozen=True, slots=True)
class FlawRates:
    rate_mut: int
    rate_mov_mut: int
    rate_flaw: int


def calc_flaw_rates(
    *,
    num_cells: int,
    average_size: int,
    soup_size: int,
    gen_per_bkg_mut: int,
    gen_per_mov_mut: int,
    gen_per_flaw: int,
    ploidy: int = PLOIDY,
) -> FlawRates:
    """Derive RateMut / RateMovMut / RateFlaw from GenPer* knobs.

    Mirrors ``CalcFlawRates`` bootstrap when ``InstExe.m == 0``:
    ``RepInst = 10 * AverageSize`` (not a soup_in config key).
    """
    if num_cells <= 0 or average_size <= 0 or soup_size <= 0:
        return FlawRates(0, 0, 0)

    avg = int(average_size)
    soup = int(soup_size)
    ploidy_i = max(1, int(ploidy))

    g_mov = int(gen_per_mov_mut or 0)
    rate_mov = (2 * g_mov * avg * ploidy_i) if g_mov else 0

    rep_inst = 10 * avg
    denom = 4 * avg
    pop_gen_time = rep_inst * (soup // denom) if denom else 0
    prob_of_hit = avg / soup
    g_bkg = int(gen_per_bkg_mut or 0)
    rate_mut = (
        int(pop_gen_time * 2.0 * g_bkg * prob_of_hit) if g_bkg and pop_gen_time else 0
    )

    g_flaw = int(gen_per_flaw or 0)
    rate_flaw = (rep_inst * g_flaw * 2) if g_flaw else 0

    return FlawRates(
        rate_mut=max(0, rate_mut),
        rate_mov_mut=max(0, rate_mov),
        rate_flaw=max(0, rate_flaw),
    )
