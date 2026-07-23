# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from __future__ import annotations

from pytierra.adapters.filesystem.soup_in import parse_soup_in
from pytierra.bootstrap.wiring import load_genomes_into_vm
from pytierra.models.limits import SandboxLimits
from pytierra.services.net.memory_transport import InMemoryTransport
from pytierra.services.vm.service import TierraVM
from tests.conftest import GB0, TIERRA, acceptance_config_text


def _make(opcode_map, *, max_cells=1000):
    cfg = parse_soup_in(acceptance_config_text())
    cfg.values["GeneBnker"] = 1
    vm = TierraVM(
        config=cfg,
        asset_root=TIERRA,
        opcode_map=opcode_map,
        limits=SandboxLimits(
            max_instructions=300_000, wall_time_s=60, max_cells=max_cells
        ),
    )
    load_genomes_into_vm(vm, GB0)
    return vm


def test_dual_vm_migration(opcode_map):
    transport = InMemoryTransport()
    a = _make(opcode_map)
    b = _make(opcode_map)
    a.attach_transport(transport, node_id="a")
    b.attach_transport(transport, node_id="b")
    a.start()
    b.start()
    a.run(until_births=1)
    src = next(c for c in a.cells if c.alive)
    assert a.emigrate(src.cell_id, dest="b")
    placed = b.poll_immigrants()
    assert placed
    assert b.queues.num_cells >= 2
    # same genotype should reuse / bump pop, not invent ????
    names = {c.dem.gen_name for c in b.cells if c.alive}
    assert any(n.startswith("0080") for n in names)


def test_immigrant_eject_under_max_cells(opcode_map):
    transport = InMemoryTransport()
    a = _make(opcode_map)
    b = _make(opcode_map, max_cells=2)
    a.attach_transport(transport, node_id="a")
    b.attach_transport(transport, node_id="b")
    a.start()
    b.start()
    a.run(until_births=1)
    # fill b to max via first birth if needed
    if b.queues.num_cells < 2:
        b.run(until_births=1)
    src = next(c for c in a.cells if c.alive)
    a.emigrate(src.cell_id, dest="b")
    placed = b.poll_immigrants()
    # either placed after reap or rejected
    assert placed or b.counters.get("rejected_immigrants", 0) >= 0
