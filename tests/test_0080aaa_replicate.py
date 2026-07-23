# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from pytierra.models.limits import SandboxLimitError


def test_0080aaa_self_replicates(make_vm):
    vm = make_vm(max_instructions=300_000)
    vm.start()
    mother = next(c for c in vm.cells if c.alive)
    mother_code = bytes(vm.mem.soup[mother.mm_p : mother.mm_p + mother.mm_s])
    assert len(mother_code) == 80

    vm.run(until_births=1)
    assert vm.counters["births"] >= 1
    assert vm.queues.num_cells >= 2

    daughters = [c for c in vm.cells if c.alive and c.cell_id != mother.cell_id]
    assert daughters
    d = daughters[0]
    child = bytes(vm.mem.soup[d.mm_p : d.mm_p + d.mm_s])
    # genetic region should match mother when mut=0
    gstart = d.mm_p + d.dem.mg_p
    gsize = d.dem.mg_s or d.mm_s
    genome = bytes(vm.mem.soup[gstart : gstart + gsize])
    assert genome == mother_code or child == mother_code


def test_snapshot_restore_continues(make_vm):
    vm = make_vm(max_instructions=300_000)
    vm.start()
    vm.step(n=2000)
    snap = vm.snapshot()
    rng_next = vm.rng.tlrand()
    vm.rng.restore(snap["rng"])
    assert vm.rng.tlrand() == rng_next
    vm.restore(snap)
    vm.run(until_births=1)
    assert vm.counters["births"] >= 1


def test_sandbox_limit_continue(make_vm):
    vm = make_vm(max_instructions=500)
    vm.start()
    try:
        while True:
            vm.step(n=100)
    except SandboxLimitError as exc:
        assert exc.kind == "max_instructions"
    cells_before = vm.queues.num_cells
    inst_before = vm.inst_exe
    vm.set_limits(max_instructions=200_000)
    vm.step(n=1000)
    assert vm.inst_exe > inst_before
    assert vm.queues.num_cells >= cells_before


def test_trace_buffer(make_vm):
    vm = make_vm(max_instructions=10_000)
    vm.start()
    vm.enable_trace(True)
    vm.step(n=50)
    tr = vm.get_trace()
    assert len(tr) > 0
    assert "mnemonic" in tr[0]
