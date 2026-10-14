# ANT WORLD — Redesign from Scratch: Narrative & Visual Identity

> Fresh build from a blank canvas. No reuse of prior deck layouts. Sources:
> `docs/Laporan_UTS_Hybrid_Computing_Ripki_Maulana.pdf` (report, Table 5),
> `src/*.py` (code verification), `results/dashboard_actual.png` (real screenshot).

## Story arc (14 slides)
Problem → Concept → Architecture (×2: system + one iteration) → Implementation →
Evidence (dashboard) → Method → Results → Analysis → Limits → Conclusion.

Audience: dosen pengampu UTS. They must see (a) the hybrid architecture is real,
(b) thread vs process roles are distinct, (c) benchmark numbers are honest including
the slower 500-ant case, (d) food=0 is not hidden.

## Visual identity (new)
- **Ground:** off-white `F7F8FA`; deep navy ink `0B1B34` for text and anchors.
- **Primary accent (compute):** electric blue `1F6FEB`.
- **Secondary (thread / I/O):** green `1A9E6C`.
- **Highlight:** amber `E39218` (sparing).
- **Negative / below-baseline:** red `C0394B` (only for < 1,0× and warnings).
- **Type:** Arial (sans, projector-safe): display 34-46, section 20-24, body 16-18,
  caption 11-12. Left-aligned body; centered titles only.
- **Grid:** 0.7in margin, 0.3in gutters, one alignment rule per slide.
- **Motif:** a thin "pheromone trail" polyline used on the cover only (a data-meaningful
  mark, not repeated decor). Each content slide carries one message; layout varies.

## Slide-by-slide plan
1. **Cover** — editorial navy panel, big title, identity strip, trail motif.
2. **Problem & motivation** — 3 statements + a small "iteration cost" idea.
3. **Meet ANT WORLD** — grid diagram (nest, ants, food, obstacles) + cycle.
4. **Experiment configuration** — grouped parameter blocks, all figures from report.
5. **Why hybrid?** — two-column CPU vs I/O comparison (no "always faster" claim).
6. **Hybrid system architecture** — the flagship editable diagram (two lanes + main + MPI note).
7. **One iteration** — horizontal pipeline snapshot→chunk→pool→barrier→merge→update.
8. **Implementation & tech** — tech ↔ role mapping (Python, futures, ThreadingHTTPServer…).
9. **Application evidence** — full real dashboard screenshot + annotation callouts.
10. **Benchmark methodology** — baseline vs hybrid, 100 iterations, no dashboard, metrics.
11. **Experiment results** — grouped serial/hybrid bars per config + speedup labels.
12. **Performance analysis** — speedup / efficiency / throughput; candidate vs measured causes.
13. **Limitations & validation** — food=0 honesty, determinism vs functional correctness.
14. **Conclusion & references** — benefits from actual results, next steps, verifiable refs.

## Data (report Table 5 — must match source)
| Config | Serial(s) | Hybrid(s) | Speedup | Eff | Thr |
|---|---|---|---|---|---|
| 5T·3P·1390 | 4.597952 | 3.090437 | 1.4878 | 49.59 | 449.77 |
| 1T·3P·1390 | 4.668423 | 3.134073 | 1.4896 | 49.65 | 443.51 |
| 5T·2P·1390 | 4.944367 | 3.516699 | 1.4060 | 70.30 | 395.26 |
| 5T·3P·500  | 1.982886 | 2.157669 | 0.9190 | 30.63 | 231.73 |
Speedup = T_serial / T_hybrid. Efficiency = speedup / number_of_processes × 100%.

## Cannot verify / mark clearly
- No independent run of the app; numbers are as-reported (single run per config).
- food collected = 0 in every reported run → functional success not demonstrated.
- Demo URL and GitHub repo: not fetched this session → referenced as project links only.
