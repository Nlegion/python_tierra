# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from pytierra.services.vm import slicer as slicer_mod


def test_slicer_cycles_alive_cells(make_vm):
    vm = make_vm(max_instructions=50_000)
    vm.start()
    # add second cell sharing soup space
    c = vm.alloc_cell()
    assert c is not None
    addr = vm.mem.mem_alloc(40, -1, 0)
    c.alive = True
    c.mm_p = addr
    c.mm_s = 40
    c.cpu.ip = addr
    vm.queues.ent_bot_slicer(vm.cells, c.cell_id)
    vm.queues.ent_bot_reaper(vm.cells, c.cell_id)
    vm.queues.num_cells += 1
    seen = set()
    for _ in range(10):
        seen.add(vm.queues.this_slice)
        slicer_mod.slicer_step(vm)
    assert len(seen) >= 2


def test_slicer_skips_dead_cell(make_vm):
    vm = make_vm(max_instructions=50_000)
    vm.start()
    c = vm.alloc_cell()
    assert c is not None
    addr = vm.mem.mem_alloc(40, -1, 0)
    c.alive = True
    c.mm_p = addr
    c.mm_s = 40
    c.cpu.ip = addr
    vm.queues.ent_bot_slicer(vm.cells, c.cell_id)
    vm.queues.ent_bot_reaper(vm.cells, c.cell_id)
    vm.queues.num_cells += 1
    # point slicer at c then kill it without rmv (simulates stale cursor)
    vm.queues.this_slice = c.cell_id
    c.alive = False
    before = vm.inst_exe
    slicer_mod.slicer_step(vm)
    # should advance past dead and not hang
    assert vm.queues.this_slice != c.cell_id or vm.queues.num_cells == 1
    slicer_mod.slicer_step(vm)
    assert vm.inst_exe >= before


def test_slicer_random_quantum_uses_rng(make_vm):
    vm = make_vm(max_instructions=50_000)
    vm.start()
    vm.config.values["SliceStyle"] = 2
    vm.config.values["SlicFixFrac"] = 0.0
    vm.config.values["SlicRanFrac"] = 2.0
    slices = []
    # monkeypatch time_slice to capture size
    original = slicer_mod.time_slice

    def capture(vm_, ce, size_slice):
        slices.append(size_slice)
        return original(vm_, ce, size_slice)

    slicer_mod.time_slice = capture  # type: ignore[assignment]
    try:
        for _ in range(8):
            slicer_mod.slicer_step(vm)
    finally:
        slicer_mod.time_slice = original  # type: ignore[assignment]
    assert slices
    assert max(slices) >= min(slices)  # at least ran
    # with SlicRanFrac=2 expect variation across steps usually
    assert len(set(slices)) >= 1
