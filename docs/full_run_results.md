# Результаты полного прогона Tierra-VM

Прогон: `py -3 examples\viz_full_run.py` (seed=42), **GenPer\*=16**, wall ≈ **0.52 s**.

Артефакты: [`viz/full_run_analysis.json`](../viz/full_run_analysis.json),
[`viz/full_run_config.json`](../viz/full_run_config.json), `viz/viz_*.png|gif`.

---

## 1. Условия

| Параметр | Значение |
|----------|----------|
| Inoculum | `0080aaa` |
| SoupSize / seed | 12 000 / 42 |
| GenPerBkg·Mov·Div | **16** (было 512 — клональный прогон) |
| GenPerFlaw / Seg·Ins | 0 / все 0 |
| Стоп | `run(until_births=80)` |

first birth **826** vs golden **827** (SoupSize 6000) — ожидаемо, Δ=1.

---

## 2. Итог

| Метрика | Значение |
|---------|----------|
| InstExe | **99 891** |
| births / deaths / NumCells | **80 / 4 / 77** |
| mal_fail / reap_attempts | **276 / 4** |
| TotMut / TotMovMut | **26 / 6** |
| rate_mut / rate_mov_mut | **6 314 / 2 560** |
| occupancy | **99.55%** (free_mem=54) |
| genebank genotypes | **10** |
| live sizes | все 80 |
| wall_time_s | ≈0.52 |

`E[TotMut]≈2×99891/6314≈31.6` — факт 26 в пределах разброса RNG.

---

## 3. Филогения

[viz_phylogeny.png](../viz/viz_phylogeny.png): **10 узлов / 10 рёбер**.  
Центр `0080aaa` → мутанты `aab`…`aaj`; вторичные ветки (`aaf→aai`, `aag→aah`).

Раньше при GenPer=512 PNG был «пустым»: TotMut=0, только клоны, рёбер parent≠child нет.

---

## 4. Прочее

- Reaper: 4 deaths при заполнении soup; `mal_fail=276` — много неудачных `mal` до/после pressure.
- Petri: 40 кадров post-run, шаг 2000 InstExe.
- Snapshot на прогоне не снимался (`tests/test_snapshot_rates.py` отдельно).
- C bench: не запускался (нет `--c-bin`).

```powershell
py -3 examples\viz_full_run.py
```
