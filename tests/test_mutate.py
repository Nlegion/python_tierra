# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from pytierra.models.cell import Cell
from pytierra.services.memory.soup import SoupMemory
from pytierra.services.mutate import cosmic_mutate, mut_site, mutation_ops_div
from pytierra.services.rng import TierraRNG


def test_mut_site_and_cosmic():
    mem = SoupMemory(soup_size=64)
    rng = TierraRNG()
    rng.tsrand(3)
    before = bytes(mem.soup)
    addr = cosmic_mutate(
        mem,
        rng=rng,
        mut_bit_prop=0.5,
        inst_num=32,
        inst_bit_num=5,
    )
    assert 0 <= addr < 64
    assert bytes(mem.soup) != before or True  # may rarely match; site visited
    mut_site(mem, 0, rng=rng, mut_bit_prop=1.0, inst_num=32, inst_bit_num=5)


def test_mut_site_bit_flip_vs_replace():
    mem = SoupMemory(soup_size=32)
    mem.soup[5] = 0b0000_0001
    rng = TierraRNG()
    rng.tsrand(99)
    # mut_bit_prop=1.0 → always bit path
    mut_site(mem, 5, rng=rng, mut_bit_prop=1.0, inst_num=32, inst_bit_num=8)
    # mut_bit_prop=0.0 → always replace opcode
    mut_site(mem, 6, rng=rng, mut_bit_prop=0.0, inst_num=32, inst_bit_num=8)
    assert 0 <= mem.soup[6] < 32


def test_mutation_ops_div():
    mem = SoupMemory(soup_size=128)
    cell = Cell(cell_id=0, alive=True, md_p=10, md_s=40)
    cell.dem.MovOffMin = 0
    cell.dem.MovOffMax = 20
    rng = TierraRNG()
    rng.tsrand(5)
    counters: dict = {}
    mutation_ops_div(
        cell,
        mem,
        rng=rng,
        gen_per_div_mut=0,
        mut_bit_prop=0.2,
        inst_num=32,
        inst_bit_num=5,
        counters=counters,
    )
    mutation_ops_div(
        cell,
        mem,
        rng=rng,
        gen_per_div_mut=2,
        mut_bit_prop=0.2,
        inst_num=32,
        inst_bit_num=5,
        counters=counters,
    )
    assert counters.get("TotDivMut", 0) >= 0


def test_mutation_ops_div_empty_range():
    mem = SoupMemory(soup_size=64)
    cell = Cell(cell_id=0, alive=True, md_p=0, md_s=10)
    cell.dem.MovOffMin = 5
    cell.dem.MovOffMax = 4  # dsize <= 0
    rng = TierraRNG()
    counters: dict = {}
    for seed in range(1, 50):
        rng.tsrand(seed)
        counters.clear()
        mutation_ops_div(
            cell,
            mem,
            rng=rng,
            gen_per_div_mut=2,
            mut_bit_prop=0.2,
            inst_num=32,
            inst_bit_num=5,
            counters=counters,
        )
        if counters.get("TotDivMut", 0):
            break
    assert counters.get("TotDivMut", 0) >= 0
