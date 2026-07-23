# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""mal / divide."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytierra.services.mutate import mutation_ops_div
from pytierra.services.mutate_segment import genetic_ops

if TYPE_CHECKING:
    from pytierra.models.isa_state import InstState
    from pytierra.services.vm.context import VMContext


def malchm(ctx: VMContext, is_: InstState) -> None:
    ce = ctx.ce
    size = is_.sval
    if size < ctx.min_cell_size or size >= ctx.mem.soup_size:
        ce.cpu.fl.E = 1
        return
    addr, got = ctx.mem.mal(
        ce,
        size,
        is_.mode2,
        rng_tlrand=ctx.rng.tlrand,
        mal_limit=ctx.mal_limit,
        max_mal_mult=ctx.max_mal_mult,
        mal_sam_siz=ctx.mal_sam_siz,
        reaper_fn=ctx.reap_one,
    )
    if not got:
        ctx.counters["mal_fail"] = ctx.counters.get("mal_fail", 0) + 1
        ce.cpu.fl.E = 1
        return
    if is_.dreg_i >= 0:
        ce.cpu.re[is_.dreg_i] = addr
    ce.cpu.fl.E = ce.cpu.fl.S = ce.cpu.fl.Z = 0


def divide(ctx: VMContext, is_: InstState) -> None:
    ce = ctx.ce
    dgen = ce.dem.MovOffMax - ce.dem.MovOffMin + 1
    thresh = int(ce.md_s * ctx.mov_prop_thr_div)
    if (
        ce.md_s < ctx.min_cell_size
        or dgen < ctx.min_gen_mem_siz
        or dgen < thresh
        or ce.dem.mov_daught < thresh
    ):
        ce.cpu.fl.E = 1
        return

    div_mutated = mutation_ops_div(
        ce,
        ctx.mem,
        rng=ctx.rng,
        gen_per_div_mut=ctx.gen_per_div_mut,
        mut_bit_prop=ctx.mut_bit_prop,
        inst_num=ctx.inst_num,
        inst_bit_num=ctx.inst_bit_num,
        counters=ctx.counters,
    )
    seg_changed = genetic_ops(ctx)
    daughter_dirty = bool(
        div_mutated
        or seg_changed
        or ctx.counters.pop("_daughter_genome_dirty", 0)
        or ce.dem.nonslfmut
    )

    dgen = ce.dem.MovOffMax - ce.dem.MovOffMin + 1
    if ce.md_s < ctx.min_cell_size or dgen < ctx.min_gen_mem_siz:
        ce.cpu.fl.E = 1
        return

    nc = ctx.alloc_cell()
    if nc is None:
        ce.cpu.fl.E = 1
        return
    nc.alive = True
    nc.mm_p = ce.md_p
    nc.mm_s = ce.md_s
    nc.dem.mg_p = ce.dem.MovOffMin
    nc.dem.mg_s = dgen
    nc.dem.gen_size = dgen
    nc.dem.gen_name = f"{dgen:04d}???"
    nc.dem.dm = 0
    if daughter_dirty:
        nc.dem.genome_hash_dirty = True
        nc.dem.genome_hash = None
    else:
        nc.dem.genome_hash = ce.dem.genome_hash
        nc.dem.genome_hash_dirty = ce.dem.genome_hash is None
    nc.cpu.ip = nc.mm_p
    nc.cpu.re = list(ce.cpu.re)
    ctx.queues.ent_bot_slicer(ctx.cells, nc.cell_id)
    ctx.queues.ent_bot_reaper(ctx.cells, nc.cell_id)
    nc.dem.is_active = 1

    ce.md_p = ce.md_s = 0
    ce.dem.daughter_id = -1
    ce.dem.mov_daught = 0
    ce.dem.MovOffMin = 0
    ce.dem.MovOffMax = 0
    ce.dem.fecundity += 1
    ce.dem.repinst = 0
    ctx.queues.num_cells += 1
    ctx.counters["births"] = ctx.counters.get("births", 0) + 1
    ctx.counters["_birth_mother_id"] = ce.cell_id
    ctx.update_average_size()
    if ctx.notify_birth is not None:
        ctx.notify_birth(nc.cell_id, nc.mm_s, is_migrant=False)
    ce.cpu.fl.E = ce.cpu.fl.S = ce.cpu.fl.Z = 0
