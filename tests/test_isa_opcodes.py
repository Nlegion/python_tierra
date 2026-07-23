# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from pytierra.adapters.filesystem.soup_in import parse_soup_in
from pytierra.models.cell import Cell
from pytierra.services.isa.decode import decode
from pytierra.services.isa.execute import execute
from pytierra.services.memory.queues import CellQueues
from pytierra.services.memory.soup import SoupMemory
from pytierra.services.rng import TierraRNG
from pytierra.services.vm.context import VMContext


def _ctx(omp, soup_bytes, ip=0):
    mem = SoupMemory(soup_size=max(256, len(soup_bytes) + 64))
    for i, b in enumerate(soup_bytes):
        mem.soup[i] = b
        # remove from free by allocating exactly? simpler: mark whole used then
    # claim range
    mem.by_addr = []
    mem.by_size = []
    if len(soup_bytes) < mem.soup_size:
        mem._insert_block(len(soup_bytes), mem.soup_size - len(soup_bytes))
    cell = Cell(cell_id=0, alive=True, mm_p=0, mm_s=len(soup_bytes))
    cell.cpu.ip = ip
    q = CellQueues()
    rng = TierraRNG()
    rng.tsrand(1)

    def alloc():
        return None

    def reap():
        return False

    def upd():
        return None

    return VMContext(
        mem=mem,
        cells=[cell],
        queues=q,
        rng=rng,
        ce=cell,
        nop0=omp.nop0,
        nop1=omp.nop1,
        nop_s=omp.nop_s,
        inst_num=omp.inst_num,
        inst_bit_num=8,
        min_templ_size=1,
        min_cell_size=12,
        min_gen_mem_siz=12,
        mov_prop_thr_div=0.7,
        mal_limit=400,
        max_mal_mult=3.0,
        mal_sam_siz=0,
        mal_mode=1,
        mem_mode_free=0,
        mem_mode_mine=0,
        mem_mode_prot=0,
        search_limit=5.0,
        abs_search_limit=0,
        average_size=80,
        rate_mov_mut=0,
        count_mov_mut=0,
        rate_flaw=0,
        count_flaw=0,
        gen_per_div_mut=0,
        mut_bit_prop=0.2,
        cfg_values=parse_soup_in("seed=1\n").values,
        counters={},
        alloc_cell=alloc,
        reap_one=reap,
        update_average_size=upd,
    ), cell


def test_zero_not0_shl(opcode_map):
    ctx, cell = _ctx(opcode_map, [0] * 32)
    idef = opcode_map.by_name["zero"]
    is_ = decode(ctx, idef)
    execute(ctx, idef, is_)
    assert cell.cpu.re[2] == 0
    idef = opcode_map.by_name["not0"]
    is_ = decode(ctx, idef)
    execute(ctx, idef, is_)
    assert cell.cpu.re[2] == 1
    idef = opcode_map.by_name["shl"]
    is_ = decode(ctx, idef)
    execute(ctx, idef, is_)
    assert cell.cpu.re[2] == 2


def test_push_pop(opcode_map):
    ctx, cell = _ctx(opcode_map, [0] * 32)
    cell.cpu.re[0] = 123
    idef = opcode_map.by_name["pushA"]
    is_ = decode(ctx, idef)
    execute(ctx, idef, is_)
    cell.cpu.re[0] = 0
    idef = opcode_map.by_name["popA"]
    is_ = decode(ctx, idef)
    execute(ctx, idef, is_)
    assert cell.cpu.re[0] == 123


def test_movii_copies(opcode_map):
    code = [0] * 64
    ctx, cell = _ctx(opcode_map, code)
    ctx.mem.soup[10] = 7
    cell.cpu.re[0] = 20  # dest AX
    cell.cpu.re[1] = 10  # src BX
    # allocate mother owns all for privilege
    cell.mm_p = 0
    cell.mm_s = 64
    idef = opcode_map.by_name["movii"]
    is_ = decode(ctx, idef)
    execute(ctx, idef, is_)
    assert ctx.mem.soup[20] == 7
