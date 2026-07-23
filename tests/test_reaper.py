# Derivative work of Tierra Simulator — see legacy/tierra/license.h
def test_reap_one_frees_memory_and_updates_queues(make_vm):
    vm = make_vm(max_instructions=50_000, max_cells=100)
    vm.config.values["NumCellsMin"] = 1
    vm.start()
    # force a second cell so reaper can kill one
    c = vm.alloc_cell()
    assert c is not None
    addr = vm.mem.mem_alloc(40, -1, 0)
    assert addr >= 0
    c.alive = True
    c.mm_p = addr
    c.mm_s = 40
    vm.queues.ent_bot_slicer(vm.cells, c.cell_id)
    vm.queues.ent_bot_reaper(vm.cells, c.cell_id)
    vm.queues.num_cells += 1
    free_before = vm.mem.free_bytes()
    cells_before = vm.queues.num_cells
    assert vm.reap_one() is True
    assert vm.queues.num_cells == cells_before - 1
    assert vm.mem.free_bytes() > free_before
    assert vm.counters.get("deaths", 0) >= 1


def test_max_cells_soft_fail_does_not_reap(make_vm):
    vm = make_vm(max_cells=1, max_instructions=20_000)
    vm.start()
    assert vm.queues.num_cells == 1
    deaths_before = vm.counters.get("deaths", 0)
    assert vm.alloc_cell() is None
    assert vm.queues.num_cells == 1
    assert vm.counters.get("deaths", 0) == deaths_before


def test_mal_triggers_reaper_when_soup_full(make_vm):
    vm = make_vm(max_instructions=10_000)
    vm.config.values["NumCellsMin"] = 1
    vm.start()
    # second living cell to be reaped
    c = vm.alloc_cell()
    assert c is not None
    addr = vm.mem.mem_alloc(80, -1, 0)
    c.alive = True
    c.mm_p = addr
    c.mm_s = 80
    vm.queues.ent_bot_slicer(vm.cells, c.cell_id)
    vm.queues.ent_bot_reaper(vm.cells, c.cell_id)
    vm.queues.num_cells += 1
    # consume remaining free memory
    while vm.mem.mem_alloc(16, -1, 0) >= 0:
        pass
    mother = next(x for x in vm.cells if x.alive and x.cell_id != c.cell_id)
    free_before = vm.mem.free_bytes()
    addr, size = vm.mem.mal(
        mother,
        40,
        1,
        rng_tlrand=vm.rng.tlrand,
        mal_limit=400,
        reaper_fn=vm.reap_one,
    )
    # either allocated after reap, or still failed — reaper must have been useful
    assert vm.counters.get("deaths", 0) >= 1 or size > 0
    assert vm.mem.free_bytes() >= free_before or size > 0


def test_reaper_respects_num_cells_min(make_vm):
    vm = make_vm()
    vm.start()
    vm.config.values["NumCellsMin"] = 10
    assert vm.reap_one() is False
