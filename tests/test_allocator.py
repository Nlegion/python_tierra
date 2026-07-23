# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from pytierra.services.memory.soup import SoupMemory


def test_alloc_free_coalesce():
    mem = SoupMemory(soup_size=1000)
    a = mem.mem_alloc(100, 0, 999)
    assert a == 0
    b = mem.mem_alloc(50, -1, 0)
    assert b >= 0
    mem.mem_dealloc(a, 100)
    mem.mem_dealloc(b, 50)
    assert mem.free_bytes() == 1000


def test_better_fit_and_first_fit():
    mem = SoupMemory(soup_size=500)
    a = mem.mem_alloc(100, 0, 499)
    assert a == 0
    b = mem.mem_alloc(20, -1, 0)
    assert b == 100
    c = mem.mem_alloc(10, 200, 50)
    assert c >= 0


def test_fragmentation_coalesce_enables_large_alloc():
    mem = SoupMemory(soup_size=200)
    # Pack soup fully with 4x50 blocks — no leftover free tail.
    blocks = [mem.mem_alloc(50, -1, 0) for _ in range(4)]
    assert all(b >= 0 for b in blocks)
    assert mem.free_bytes() == 0
    mem.mem_dealloc(blocks[1], 50)
    # Only a 50-byte hole — 100-byte alloc must fail
    assert mem.mem_alloc(100, -1, 0) < 0
    mem.mem_dealloc(blocks[0], 50)
    mem.mem_dealloc(blocks[2], 50)
    # Coalesced free region of 150 at start allows 100
    big = mem.mem_alloc(100, -1, 0)
    assert big >= 0
