# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from pytierra.adapters.filesystem.soup_in import parse_soup_in
from pytierra.models.cell import Cell
from pytierra.services.isa.decode import decode
from pytierra.services.isa.execute import execute
from pytierra.services.memory.queues import CellQueues
from pytierra.services.memory.soup import SoupMemory
from pytierra.services.rng import TierraRNG
from pytierra.services.vm.context import VMContext


def test_movii_triggers_mov_mut(opcode_map):
    mem = SoupMemory(soup_size=128)
    mem.by_addr = []
    mem.by_size = []
    mem._insert_block(64, 64)
    for i in range(64):
        mem.soup[i] = 0
    mem.soup[10] = 7
    cell = Cell(cell_id=0, alive=True, mm_p=0, mm_s=64)
    cell.md_p = 0
    cell.md_s = 64
    cell.cpu.re[0] = 20
    cell.cpu.re[1] = 10
    rng = TierraRNG()
    rng.tsrand(11)
    counters: dict = {}
    ctx = VMContext(
        mem=mem,
        cells=[cell],
        queues=CellQueues(),
        rng=rng,
        ce=cell,
        nop0=opcode_map.nop0,
        nop1=opcode_map.nop1,
        nop_s=opcode_map.nop_s,
        inst_num=opcode_map.inst_num,
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
        rate_mov_mut=1,
        count_mov_mut=0,
        rate_flaw=0,
        count_flaw=0,
        gen_per_div_mut=0,
        mut_bit_prop=1.0,
        cfg_values=parse_soup_in("seed=1\n").values,
        counters=counters,
        alloc_cell=lambda: None,
        reap_one=lambda: False,
        update_average_size=lambda: None,
    )
    idef = opcode_map.by_name["movii"]
    is_ = decode(ctx, idef)
    execute(ctx, idef, is_)
    assert counters.get("TotMovMut", 0) == 1
    assert cell.dem.nonslfmut == 1
    assert cell.dem.mov_daught >= 1
    assert mem.soup[20] != 10  # not leftover register confusion
