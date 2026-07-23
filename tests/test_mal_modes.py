# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from pytierra.models.cell import Cell
from pytierra.services.memory.soup import SoupMemory
from pytierra.services.rng import TierraRNG


def _mother(mem: SoupMemory, size: int = 80) -> Cell:
    addr = mem.mem_alloc(size, 0, mem.soup_size - 1)
    assert addr >= 0
    cell = Cell(cell_id=0, alive=True, mm_p=addr, mm_s=size)
    return cell


def test_mal_mode1_better_fit():
    mem = SoupMemory(soup_size=2000)
    cell = _mother(mem)
    rng = TierraRNG()
    rng.tsrand(1)
    addr, size = mem.mal(
        cell,
        80,
        1,
        rng_tlrand=rng.tlrand,
        mal_limit=400,
    )
    assert size == 80
    assert addr >= 0
    assert cell.md_s == 80


def test_mal_mode0_and_mode2():
    mem = SoupMemory(soup_size=4000)
    cell = _mother(mem)
    rng = TierraRNG()
    rng.tsrand(7)
    a0, s0 = mem.mal(cell, 40, 0, rng_tlrand=rng.tlrand, mal_limit=800)
    assert s0 == 40 and a0 >= 0
    # re-request different size (deallocates previous daughter)
    a2, s2 = mem.mal(cell, 60, 2, rng_tlrand=rng.tlrand, mal_limit=800)
    assert s2 == 60 and a2 >= 0


def test_mal_mode3_near_mother():
    mem = SoupMemory(soup_size=4000)
    cell = _mother(mem, size=100)
    rng = TierraRNG()
    rng.tsrand(3)
    addr, size = mem.mal(cell, 50, 3, rng_tlrand=rng.tlrand, mal_limit=500)
    assert size == 50 and addr >= 0


def test_mal_rejects_oversized_and_same_daughter_size():
    mem = SoupMemory(soup_size=1000)
    cell = _mother(mem, size=80)
    rng = TierraRNG()
    rng.tsrand(1)
    assert mem.mal(cell, 0, 1, rng_tlrand=rng.tlrand, mal_limit=400) == (-1, 0)
    assert mem.mal(cell, 500, 1, rng_tlrand=rng.tlrand, mal_limit=400) == (-1, 0)
    a, s = mem.mal(cell, 40, 1, rng_tlrand=rng.tlrand, mal_limit=400)
    assert s == 40
    # same as current md_s is rejected
    assert mem.mal(cell, 40, 1, rng_tlrand=rng.tlrand, mal_limit=400) == (-1, 0)


def test_mal_soup_full_reaper_then_fail():
    mem = SoupMemory(soup_size=200)
    cell = _mother(mem, size=100)
    # fill remaining free space
    while True:
        a = mem.mem_alloc(20, -1, 0)
        if a < 0:
            break
    calls = {"n": 0}

    def reap():
        calls["n"] += 1
        return False

    rng = TierraRNG()
    rng.tsrand(1)
    addr, size = mem.mal(
        cell,
        40,
        1,
        rng_tlrand=rng.tlrand,
        mal_limit=400,
        reaper_fn=reap,
    )
    assert (addr, size) == (-1, 0)
    assert calls["n"] >= 1
