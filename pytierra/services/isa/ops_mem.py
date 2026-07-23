# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Memory move ops."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytierra.services.genebank.dirty import mark_genome_dirty
from pytierra.services.mutate import mut_site

if TYPE_CHECKING:
    from pytierra.models.isa_state import InstState
    from pytierra.services.vm.context import VMContext


def movii(ctx: VMContext, is_: InstState) -> None:
    ce = ctx.ce
    ce.cpu.fl.E = ce.cpu.fl.S = ce.cpu.fl.Z = 0
    dval = is_.dval
    sval = is_.sval
    if dval == sval:
        ce.cpu.fl.E = 1
        return
    if not (0 <= dval < ctx.mem.soup_size and 0 <= sval < ctx.mem.soup_size):
        ce.cpu.fl.E = 1
        return
    if not ctx.priv_write(ce, dval) or not ctx.priv_read(ce, sval):
        ce.cpu.fl.E = 1
        return
    ctx.mem.soup[dval] = ctx.mem.soup[sval]
    if ce.mm_p <= dval < ce.mm_p + ce.mm_s:
        mark_genome_dirty(ce)
    if ctx.rate_mov_mut and ctx.count_mov_mut >= 0:
        ctx.count_mov_mut += 1
        if ctx.count_mov_mut >= ctx.rate_mov_mut:
            mut_site(
                ctx.mem,
                dval,
                rng=ctx.rng,
                mut_bit_prop=ctx.mut_bit_prop,
                inst_num=ctx.inst_num,
                inst_bit_num=ctx.inst_bit_num,
            )
            ctx.count_mov_mut = ctx.rng.tlrand() % ctx.rate_mov_mut
            ctx.counters["TotMovMut"] = ctx.counters.get("TotMovMut", 0) + 1
            ce.dem.nonslfmut = 1
            mark_genome_dirty(ce)
            ctx.counters["_daughter_genome_dirty"] = 1
    if ce.md_s and ce.md_p <= dval < ce.md_p + ce.md_s:
        coffset = dval - ce.md_p
        if not ce.dem.mov_daught:
            ce.dem.MovOffMin = ce.dem.MovOffMax = coffset
        if coffset < ce.dem.MovOffMin:
            ce.dem.MovOffMin = coffset
        if coffset > ce.dem.MovOffMax:
            ce.dem.MovOffMax = coffset
        ce.dem.mov_daught += 1
