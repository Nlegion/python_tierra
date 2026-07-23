# Derivative work of Tierra Simulator — see legacy/tierra/license.h
from pytierra.models.cell import Cell
from pytierra.services.memory.queues import CellQueues


def _alive(cid: int) -> Cell:
    return Cell(cell_id=cid, alive=True)


def test_slicer_and_reaper_roundtrip():
    cells = [_alive(0), _alive(1), _alive(2)]
    q = CellQueues()
    for c in cells:
        q.ent_bot_slicer(cells, c.cell_id)
        q.ent_bot_reaper(cells, c.cell_id)
        q.num_cells += 1
    assert q.this_slice == 0
    assert q.top_reap == 0
    q.incr_slice_queue(cells)
    assert q.this_slice == 1
    q.rmv_from_slicer(cells, 1)
    q.rmv_from_reaper(cells, 0)
    assert q.top_reap in (1, 2)
    q.rmv_from_slicer(cells, 0)
    q.rmv_from_slicer(cells, 2)
    assert q.this_slice == -1
