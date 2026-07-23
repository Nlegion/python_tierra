# Known limitations

- **DiskBank index (`genebank_index.json`)**: fine for hundreds of genotypes. Above ~1000
  species, full rewrite on each extract may become a bottleneck. Future escape hatch:
  `DiskBankBackend=sqlite` (stub only in current release; selecting it raises `ConfigError`).
- **DiskBankFormat**: only `ascii` (`.tie`) is implemented. `binary` (C XDR `.gen`) is reserved.
- **Beagle**: in-process Observer/Control API only — no TCP/XDR Motif client.
- **NET**: `InMemoryTransport` only inside the package; VM must not open sockets.
- **Segment mutations** (cro/ins/del): implemented in `mutate_segment.py` (see
  [`segment_mutations_subplan.md`](segment_mutations_subplan.md)); keep rates 0 for mut=0 acceptance.
- **CalcFlawRates**: bootstrap path only (`RepInst = 10 * AverageSize`). C’s post–1e6
  `CalcTimeSoup` / `AvgPop*RepInst` branch is not ported; rates refresh on
  `AverageSize` change / `start` / `set_parameter(GenPer*)`, not on a million-InstExe timer.
- **SoupSize**: fixed for a VM lifetime. If a future resize is added, call the same
  rate recompute after changing soup size.
- **Reaper**: demand-driven from failed `mal` (`reap_one`); no C `ReapCheck` / lazy-reaper
  loop. `SavThrMem` / `SavThrPop` are genebank extract filters (`SavThrPop` currently unused).
- Unknown `soup_in` Beagle/Net/UI keys are ignored with a WARNING.
