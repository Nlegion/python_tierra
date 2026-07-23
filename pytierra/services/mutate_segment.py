# Derivative work of Tierra Simulator — see legacy/tierra/operator.c
"""Segment genetic ops (cro/ins/del). GeneticOps call order matches C."""

from __future__ import annotations

from typing import Any, Callable

from pytierra.models.cell import Cell
from pytierra.services.genebank.dirty import mark_genome_dirty
from pytierra.services.memory.soup import SoupMemory
from pytierra.services.rng import TierraRNG

# Call order after MutationOps (mutation_ops_div), for tests/spies.
GENETIC_OPS_ORDER = (
    "CrossoverInstSamSiz",
    "CrossoverInst",
    "InsertionInst",
    "DeletionInst",
    "CrossoverSeg",
    "InsertionSeg",
    "DeletionSeg",
)


def assemble_daught(
    soup: bytes | bytearray,
    soup_size: int,
    num_frag: int,
    adr1: int,
    siz1: int,
    adr2: int = 0,
    siz2: int = 0,
    adr3: int = 0,
    siz3: int = 0,
) -> bytes:
    """Pure assemble of daughter genome from up to 3 soup segments."""

    def _slice(adr: int, siz: int) -> bytes:
        if siz <= 0:
            return b""
        out = bytearray(siz)
        for i in range(siz):
            out[i] = soup[(adr + i) % soup_size]
        return bytes(out)

    parts = [_slice(adr1, siz1)]
    if num_frag > 1:
        parts.append(_slice(adr2, siz2))
    if num_frag > 2:
        parts.append(_slice(adr3, siz3))
    return b"".join(parts)


def shared_gen_ops(
    ce: Cell,
    mem: SoupMemory,
    *,
    num_frag: int,
    adr1: int,
    siz1: int,
    adr2: int = 0,
    siz2: int = 0,
    adr3: int = 0,
    siz3: int = 0,
    rng: TierraRNG,
    mal_limit: int,  # noqa: ARG001 — reserved for mal-mode realloc parity
    max_mal_mult: float,
    mov_prop_thr_div: float,
    min_cell_size: int,
    min_gen_mem_siz: int,
    mal_mode: int,  # noqa: ARG001
    reap_one: Callable[[], bool] | None,
) -> bool:
    """Apply assembled genome to daughter ``md``. True = success, False = abort (no change)."""
    n_gen = siz1 + (siz2 if num_frag > 1 else 0) + (siz3 if num_frag > 2 else 0)
    o_start = ce.md_p + ce.dem.MovOffMin
    o_gen = ce.dem.MovOffMax - ce.dem.MovOffMin + 1
    o_data = ce.md_s - o_gen
    n_cell = n_gen + o_data
    thresh = int(n_cell * mov_prop_thr_div)
    if (
        n_cell > max_mal_mult * ce.mm_s
        or n_cell < min_cell_size
        or n_gen < min_gen_mem_siz
        or n_gen < thresh
    ):
        return False

    daught = assemble_daught(
        mem.soup, mem.soup_size, num_frag, adr1, siz1, adr2, siz2, adr3, siz3
    )
    if n_gen != len(daught):
        return False

    if n_gen == o_gen:
        for i, b in enumerate(daught):
            mem.soup[mem.ad(o_start + i)] = b
        return True

    # Resize: probe alloc without destroying md; soft-fail leaves state intact.
    mov_min = ce.dem.MovOffMin
    mov_max = ce.dem.MovOffMax
    mov_daught = ce.dem.mov_daught
    old_p, old_s = ce.md_p, ce.md_s

    new_addr = -1
    for _ in range(8):
        new_addr = mem.mem_alloc(n_cell, -1, 0)
        if new_addr >= 0:
            break
        if reap_one is None or not reap_one():
            break
    if new_addr < 0:
        return False

    mem.mem_dealloc(old_p, old_s)
    ce.md_p = mem.ad(new_addr)
    ce.md_s = n_cell
    ce.dem.MovOffMin = mov_min
    ce.dem.MovOffMax = mov_max
    ce.dem.mov_daught = mov_daught
    gen_space = ce.md_s - ce.dem.MovOffMin
    n_copy = n_gen if n_gen < gen_space else gen_space
    dest = ce.md_p + ce.dem.MovOffMin
    for i in range(n_copy):
        mem.soup[mem.ad(dest + i)] = daught[i]
    ce.dem.MovOffMax = ce.dem.MovOffMin + n_copy - 1
    _ = (mal_mode, mal_limit)
    return True


def _is_nop(byte: int, nop0: int, nop1: int) -> bool:
    return byte == nop0 or byte == nop1


def count_segments(
    soup: bytes | bytearray, soup_size: int, adr: int, siz: int, nop0: int, nop1: int
) -> int:
    num = 0
    is_templ = True
    stop = adr + siz
    for i in range(adr, stop):
        b = soup[i % soup_size]
        if is_templ:
            if not _is_nop(b, nop0, nop1):
                is_templ = False
        else:
            if _is_nop(b, nop0, nop1):
                is_templ = True
                num += 1
    if siz > 0 and not _is_nop(soup[(stop - 1) % soup_size], nop0, nop1):
        num += 1
    return num


def find_start_seg_n(
    soup: bytes | bytearray,
    soup_size: int,
    adr: int,
    siz: int,
    seg_n: int,
    nop0: int,
    nop1: int,
) -> int:
    if seg_n == 1:
        return adr
    num = 1
    is_templ = True
    stop = adr + siz
    cur = adr
    while cur < stop:
        b = soup[cur % soup_size]
        if is_templ:
            if not _is_nop(b, nop0, nop1):
                is_templ = False
        else:
            if _is_nop(b, nop0, nop1):
                is_templ = True
                num += 1
        if num == seg_n:
            break
        cur += 1
    return cur


def find_end_seg_n(
    soup: bytes | bytearray,
    soup_size: int,
    adr: int,
    siz: int,
    seg_n: int,
    nop0: int,
    nop1: int,
) -> int:
    num = 1
    is_templ = True
    stop = adr + siz
    cur = adr
    while cur < stop:
        b = soup[cur % soup_size]
        if is_templ:
            if not _is_nop(b, nop0, nop1):
                is_templ = False
        else:
            if _is_nop(b, nop0, nop1):
                is_templ = True
                num += 1
        if num == seg_n + 1:
            break
        cur += 1
    return cur


def _alive_cells(cells: list[Cell]) -> list[Cell]:
    return [c for c in cells if c.alive]


def random_cell(ce: Cell, cells: list[Cell], rng: TierraRNG) -> Cell:
    alive = _alive_cells(cells)
    if not alive:
        return ce
    return alive[rng.tlrand() % len(alive)]


def find_rand_cell_of_size(
    ce: Cell, cells: list[Cell], rng: TierraRNG, size: int, tol: int
) -> Cell | None:
    alive = _alive_cells(cells)
    if not alive:
        return None
    start_i = rng.tlrand() % len(alive)
    for k in range(len(alive)):
        tc = alive[(start_i + k) % len(alive)]
        gs = tc.dem.mg_s or tc.mm_s
        if size - tol <= gs <= size + tol:
            return tc
    return None


def _sgo_kwargs(ctx: Any) -> dict:
    return {
        "rng": ctx.rng,
        "mal_limit": ctx.mal_limit,
        "max_mal_mult": ctx.max_mal_mult,
        "mov_prop_thr_div": ctx.mov_prop_thr_div,
        "min_cell_size": ctx.min_cell_size,
        "min_gen_mem_siz": ctx.min_gen_mem_siz,
        "mal_mode": ctx.mal_mode,
        "reap_one": ctx.reap_one,
    }


def crossover_inst_sam_siz(ctx: Any, *, call_log: list[str] | None = None) -> bool:
    if call_log is not None:
        call_log.append("CrossoverInstSamSiz")
    ce = ctx.ce
    rate = int(ctx.cfg_values.get("GenPerCroInsSamSiz", 0) or 0)
    tol = int(ctx.cfg_values.get("MateSizeEp", 1) or 1)
    changed = False
    while rate and (ctx.rng.tlrand() % rate) == 0:
        daught_size = ce.dem.MovOffMax - ce.dem.MovOffMin + 1
        if daught_size < 2:
            return changed
        mp = find_rand_cell_of_size(ce, ctx.cells, ctx.rng, daught_size, tol)
        if mp is None:
            return changed
        ctx.counters["TotCroInsSamSiz"] = ctx.counters.get("TotCroInsSamSiz", 0) + 1
        d_start = ce.md_p + ce.dem.MovOffMin
        m_start = mp.mm_p + mp.dem.mg_p
        m_size = mp.dem.mg_s or mp.mm_s
        siz = daught_size if daught_size <= m_size else m_size
        if siz < 2:
            continue
        cross = 1 + (ctx.rng.tlrand() % (siz - 1))
        if 2 * cross > daught_size:
            adr1 = d_start + cross
            adr2 = m_start + cross
            n = siz - cross
            for i in range(n):
                ctx.mem.soup[ctx.mem.ad(adr1 + i)] = ctx.mem.soup[ctx.mem.ad(adr2 + i)]
        else:
            for i in range(cross):
                ctx.mem.soup[ctx.mem.ad(d_start + i)] = ctx.mem.soup[
                    ctx.mem.ad(m_start + i)
                ]
        changed = True
    return changed


def crossover_inst(ctx: Any, *, call_log: list[str] | None = None) -> bool:
    if call_log is not None:
        call_log.append("CrossoverInst")
    ce = ctx.ce
    rate = int(ctx.cfg_values.get("GenPerCroIns", 0) or 0)
    changed = False
    kw = _sgo_kwargs(ctx)
    while rate and (ctx.rng.tlrand() % rate) == 0:
        o_start = ce.md_p + ce.dem.MovOffMin
        o_size = ce.dem.MovOffMax - ce.dem.MovOffMin + 1
        if o_size < 2:
            return changed
        d_cross = 1 + (ctx.rng.tlrand() % (o_size - 1))
        mp = random_cell(ce, ctx.cells, ctx.rng)
        m_start = mp.mm_p + mp.dem.mg_p
        m_size = mp.dem.mg_s or mp.mm_s
        if m_size < 2:
            continue
        m_cross = 1 + (ctx.rng.tlrand() % (m_size - 1))
        if 2 * d_cross > o_size:
            adr1, siz1 = o_start, d_cross
            adr2, siz2 = m_start + m_cross, m_size - m_cross
        else:
            adr1, siz1 = m_start, m_cross
            adr2, siz2 = o_start + d_cross, o_size - d_cross
        if shared_gen_ops(
            ce, ctx.mem, num_frag=2, adr1=adr1, siz1=siz1, adr2=adr2, siz2=siz2, **kw
        ):
            ctx.counters["TotCroIns"] = ctx.counters.get("TotCroIns", 0) + 1
            changed = True
        else:
            return changed
    return changed


def insertion_inst(ctx: Any, *, call_log: list[str] | None = None) -> bool:
    if call_log is not None:
        call_log.append("InsertionInst")
    ce = ctx.ce
    rate = int(ctx.cfg_values.get("GenPerInsIns", 0) or 0)
    changed = False
    kw = _sgo_kwargs(ctx)
    while rate and (ctx.rng.tlrand() % rate) == 0:
        o_start = ce.md_p + ce.dem.MovOffMin
        o_size = ce.dem.MovOffMax - ce.dem.MovOffMin + 1
        ins_off = ctx.rng.tlrand() % (o_size + 1)
        mp = random_cell(ce, ctx.cells, ctx.rng)
        m_start = mp.mm_p + mp.dem.mg_p
        m_size = mp.dem.mg_s or mp.mm_s
        if m_size <= 0:
            continue
        chunk = 1 + ctx.rng.tlrand() % m_size
        # C uses a 1-based offset; interpret as offset within mate genetic mem.
        chunk_start = m_start + (ctx.rng.tlrand() % (m_size - chunk + 1))
        if not ins_off or ins_off == o_size:
            if not ins_off:
                ok = shared_gen_ops(
                    ce,
                    ctx.mem,
                    num_frag=2,
                    adr1=chunk_start,
                    siz1=chunk,
                    adr2=o_start,
                    siz2=o_size,
                    **kw,
                )
            else:
                ok = shared_gen_ops(
                    ce,
                    ctx.mem,
                    num_frag=2,
                    adr1=o_start,
                    siz1=o_size,
                    adr2=chunk_start,
                    siz2=chunk,
                    **kw,
                )
            if not ok:
                return changed
        else:
            ok = shared_gen_ops(
                ce,
                ctx.mem,
                num_frag=3,
                adr1=o_start,
                siz1=ins_off,
                adr2=chunk_start,
                siz2=chunk,
                adr3=o_start + ins_off,
                siz3=o_size - ins_off,
                **kw,
            )
            if not ok:
                return changed
        ctx.counters["TotInsIns"] = ctx.counters.get("TotInsIns", 0) + 1
        changed = True
    return changed


def deletion_inst(ctx: Any, *, call_log: list[str] | None = None) -> bool:
    if call_log is not None:
        call_log.append("DeletionInst")
    ce = ctx.ce
    rate = int(ctx.cfg_values.get("GenPerDelIns", 0) or 0)
    changed = False
    kw = _sgo_kwargs(ctx)
    while rate and (ctx.rng.tlrand() % rate) == 0:
        o_start = ce.md_p + ce.dem.MovOffMin
        o_size = ce.dem.MovOffMax - ce.dem.MovOffMin + 1
        if o_size < 2:
            return changed
        del_siz = 1 + (ctx.rng.tlrand() % max(1, o_size // 2))
        del_off = ctx.rng.tlrand() % (o_size - del_siz + 1)
        if shared_gen_ops(
            ce,
            ctx.mem,
            num_frag=2,
            adr1=o_start,
            siz1=del_off,
            adr2=o_start + del_off + del_siz,
            siz2=o_size - (del_off + del_siz),
            **kw,
        ):
            ctx.counters["TotDelIns"] = ctx.counters.get("TotDelIns", 0) + 1
            changed = True
    return changed


def crossover_seg(ctx: Any, *, call_log: list[str] | None = None) -> bool:
    if call_log is not None:
        call_log.append("CrossoverSeg")
    ce = ctx.ce
    rate = int(ctx.cfg_values.get("GenPerCroSeg", 0) or 0)
    changed = False
    kw = _sgo_kwargs(ctx)
    nop0, nop1 = ctx.nop0, ctx.nop1
    while rate and (ctx.rng.tlrand() % rate) == 0:
        o_start = ce.md_p + ce.dem.MovOffMin
        o_size = ce.dem.MovOffMax - ce.dem.MovOffMin + 1
        nseg = count_segments(ctx.mem.soup, ctx.mem.soup_size, o_start, o_size, nop0, nop1)
        if nseg < 2:
            return changed
        d_cross = 2 + (ctx.rng.tlrand() % (nseg - 1))
        mp = random_cell(ce, ctx.cells, ctx.rng)
        m_start = mp.mm_p + mp.dem.mg_p
        m_size = mp.dem.mg_s or mp.mm_s
        mseg = count_segments(ctx.mem.soup, ctx.mem.soup_size, m_start, m_size, nop0, nop1)
        if mseg < 2:
            continue
        m_cross = 2 + (ctx.rng.tlrand() % (mseg - 1))
        if 2 * d_cross > nseg:
            adr1 = o_start
            siz1 = (
                find_end_seg_n(
                    ctx.mem.soup, ctx.mem.soup_size, o_start, o_size, d_cross, nop0, nop1
                )
                - adr1
            )
            adr2 = find_start_seg_n(
                ctx.mem.soup, ctx.mem.soup_size, m_start, m_size, m_cross, nop0, nop1
            )
            siz2 = m_start + m_size - adr2
        else:
            adr1 = m_start
            siz1 = (
                find_end_seg_n(
                    ctx.mem.soup, ctx.mem.soup_size, m_start, m_size, m_cross, nop0, nop1
                )
                - adr1
            )
            adr2 = find_start_seg_n(
                ctx.mem.soup, ctx.mem.soup_size, o_start, o_size, d_cross, nop0, nop1
            )
            siz2 = o_start + o_size - adr2
        if shared_gen_ops(
            ce, ctx.mem, num_frag=2, adr1=adr1, siz1=siz1, adr2=adr2, siz2=siz2, **kw
        ):
            ctx.counters["TotCroSeg"] = ctx.counters.get("TotCroSeg", 0) + 1
            changed = True
    return changed


def insertion_seg(ctx: Any, *, call_log: list[str] | None = None) -> bool:
    if call_log is not None:
        call_log.append("InsertionSeg")
    ce = ctx.ce
    rate = int(ctx.cfg_values.get("GenPerInsSeg", 0) or 0)
    changed = False
    kw = _sgo_kwargs(ctx)
    nop0, nop1 = ctx.nop0, ctx.nop1
    while rate and (ctx.rng.tlrand() % rate) == 0:
        o_start = ce.md_p + ce.dem.MovOffMin
        o_size = ce.dem.MovOffMax - ce.dem.MovOffMin + 1
        nseg = count_segments(ctx.mem.soup, ctx.mem.soup_size, o_start, o_size, nop0, nop1)
        if not nseg:
            return changed
        d_cross = 1 + (ctx.rng.tlrand() % (nseg + 1))
        mp = random_cell(ce, ctx.cells, ctx.rng)
        m_start = mp.mm_p + mp.dem.mg_p
        m_size = mp.dem.mg_s or mp.mm_s
        mseg = count_segments(ctx.mem.soup, ctx.mem.soup_size, m_start, m_size, nop0, nop1)
        if not mseg:
            return changed
        chunk_n = 1 + (ctx.rng.tlrand() % mseg)
        chunk_start_seg = 1 + ctx.rng.tlrand() % (mseg - chunk_n + 1)
        mate_chunk_start = find_start_seg_n(
            ctx.mem.soup, ctx.mem.soup_size, m_start, m_size, chunk_start_seg, nop0, nop1
        )
        mate_chunk_size = (
            find_end_seg_n(
                ctx.mem.soup,
                ctx.mem.soup_size,
                m_start,
                m_size,
                chunk_start_seg + chunk_n,
                nop0,
                nop1,
            )
            - mate_chunk_start
        )
        if d_cross == 1 or d_cross == nseg + 1:
            if d_cross == 1:
                ok = shared_gen_ops(
                    ce,
                    ctx.mem,
                    num_frag=2,
                    adr1=mate_chunk_start,
                    siz1=mate_chunk_size,
                    adr2=o_start,
                    siz2=o_size,
                    **kw,
                )
            else:
                ok = shared_gen_ops(
                    ce,
                    ctx.mem,
                    num_frag=2,
                    adr1=o_start,
                    siz1=o_size,
                    adr2=mate_chunk_start,
                    siz2=mate_chunk_size,
                    **kw,
                )
            if not ok:
                return changed
        else:
            d_off = find_end_seg_n(
                ctx.mem.soup, ctx.mem.soup_size, o_start, o_size, d_cross, nop0, nop1
            )
            ok = shared_gen_ops(
                ce,
                ctx.mem,
                num_frag=3,
                adr1=o_start,
                siz1=d_off - o_start,
                adr2=mate_chunk_start,
                siz2=mate_chunk_size,
                adr3=d_off,
                siz3=o_start + o_size - d_off,
                **kw,
            )
            if not ok:
                return changed
        ctx.counters["TotInsSeg"] = ctx.counters.get("TotInsSeg", 0) + 1
        changed = True
    return changed


def deletion_seg(ctx: Any, *, call_log: list[str] | None = None) -> bool:
    if call_log is not None:
        call_log.append("DeletionSeg")
    ce = ctx.ce
    rate = int(ctx.cfg_values.get("GenPerDelSeg", 0) or 0)
    changed = False
    kw = _sgo_kwargs(ctx)
    nop0, nop1 = ctx.nop0, ctx.nop1
    while rate and (ctx.rng.tlrand() % rate) == 0:
        o_start = ce.md_p + ce.dem.MovOffMin
        o_size = ce.dem.MovOffMax - ce.dem.MovOffMin + 1
        o_end = ce.md_p + ce.dem.MovOffMax + 1
        nseg = count_segments(ctx.mem.soup, ctx.mem.soup_size, o_start, o_size, nop0, nop1)
        if nseg < 2:
            return changed
        del_num = 1 + ctx.rng.tlrand() % max(1, nseg // 2)
        del_off_seg = 1 + ctx.rng.tlrand() % (nseg - del_num + 1)
        del_off = find_start_seg_n(
            ctx.mem.soup, ctx.mem.soup_size, o_start, o_size, del_off_seg, nop0, nop1
        )
        del_siz = (
            find_end_seg_n(
                ctx.mem.soup,
                ctx.mem.soup_size,
                o_start,
                o_size,
                del_off_seg + del_num - 1,
                nop0,
                nop1,
            )
            - del_off
        )
        if del_off_seg == 1 or del_off_seg + del_num > nseg:
            if del_off_seg == 1:
                adr1 = del_off + del_siz
                siz1 = o_end - adr1
            else:
                adr1 = o_start
                siz1 = del_off - o_start
            if not shared_gen_ops(
                ce, ctx.mem, num_frag=1, adr1=adr1, siz1=siz1, **kw
            ):
                return changed
        else:
            if not shared_gen_ops(
                ce,
                ctx.mem,
                num_frag=2,
                adr1=o_start,
                siz1=del_off - o_start,
                adr2=del_off + del_siz,
                siz2=o_end - (del_off + del_siz),
                **kw,
            ):
                return changed
        ctx.counters["TotDelSeg"] = ctx.counters.get("TotDelSeg", 0) + 1
        changed = True
    return changed


def genetic_ops(ctx: Any, *, call_log: list[str] | None = None) -> bool:
    """C GeneticOps order (MutationOps is called separately before this)."""
    changed = False
    changed |= crossover_inst_sam_siz(ctx, call_log=call_log)
    changed |= crossover_inst(ctx, call_log=call_log)
    changed |= insertion_inst(ctx, call_log=call_log)
    changed |= deletion_inst(ctx, call_log=call_log)
    changed |= crossover_seg(ctx, call_log=call_log)
    changed |= insertion_seg(ctx, call_log=call_log)
    changed |= deletion_seg(ctx, call_log=call_log)
    if changed:
        mark_genome_dirty(ctx.ce)
        ctx.counters["_daughter_genome_dirty"] = 1
    return changed
