# NET port contract

Python Tierra does **not** open sockets from the VM. Multi-node exchange uses a
`MigrationPort`-shaped transport attached by the host.

## In-memory transport

```python
from pytierra.services.net import InMemoryTransport

t = InMemoryTransport()
vm_a.attach_transport(t, node_id="a")
vm_b.attach_transport(t, node_id="b")
vm_a.emigrate(cell_id, dest="b")
vm_b.poll_immigrants()  # notify_birth(..., is_migrant=True)
```

## Policies

- Same genome (size → hash → memcmp) reuses the existing genotype / bumps `pop`.
- Soup / `max_cells` pressure: reaper eject, then inject; else soft-fail
  (`rejected_immigrants` counter).
- Emigration force-marks permanent in RamBanker when GeneBnker is on.

Future TCP/UDP adapters must live outside `services.isa` / slicer (host process).
