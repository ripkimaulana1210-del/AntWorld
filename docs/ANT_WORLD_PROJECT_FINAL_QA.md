# ANT WORLD — PROJECT-FINAL QA Report

**Deliverable:** `results/ANT_WORLD_Presentasi_UTS_PROJECT_FINAL.pptx` (12 slides, 469 KB)
**Baseline (not overwritten):** `results/ANT_WORLD_Presentasi_UTS_FINAL.pptx`
**Working dir:** `D:\Kuliah\Season 5\KPT\UTS`
**Generator:** `scripts/build_antworld_project_final.py`

---

## 1. Skills actually read and used

| Skill | Read | How it was applied |
|---|---|---|
| `presentation-craft` (+ `slides.md`, `composition.md`, `data-viz.md`, `slop.md`, `deck-spec.md`) | Yes | Craft rules: one idea/slide, assertion titles, hero the one thing, vary the form, chart-message-first; the slop detector. |
| `slop-check` | Yes | Ran the content detector (Layer 1 + prose tells) after revision. |
| `revise` | Yes | Kept the existing generator, edited the source, re-rendered, re-ran gates, did not overwrite the original. |
| `narrative` | Yes (principle) | Arc: problem → method → architecture → implementation → benchmark → evaluation → conclusion. |
| `teach-slides` | Yes (principle) | Kept every slide to one understandable idea. |
| `build-deck` | Read as reference only | Not used as renderer, to avoid risking native editable elements. Documented decision. |
| `pptx-builder` | Yes | File mechanics: generator, package verify, render, QA. |
| `pptx-deck-context` | Yes | Kept identity / narrative / source lineage stable. |
| `pptx-slide-specification` | Yes (principle) | Explicit coordinates, safe margins, no auto-layout. |
| `pptx-visual-assets` | Yes | Kept the real dashboard screenshot; no invented assets. |
| `pptx-reference-deck-analysis` / `pptx-quality-gates` | Yes | Package + geometry validation criteria. |
| `scientific-slides` | Yes (principle) | Scientific limits: single run, food=0, no unproven bottleneck, MPI not used. |
| `frontend-slides` | Not used | No web/HTML deliverable — not applicable. Documented. |

**Independent vision review:** attempted via `designer`/`oracle` sub-agents → **failed**
(provider `kiro` has no credentials). Visual QA = rendered PNG inspection + pixel/geometry
analysis. Not claimed as a human/vision pass.

## 2. Files changed
- `scripts/build_antworld_project_final.py` (new project-focused generator)
- `results/ANT_WORLD_Presentasi_UTS_PROJECT_FINAL.pptx` + `.pdf`
- `results/preview_project_final/Slide1–12.png`
- `docs/ANT_WORLD_PROJECT_FINAL_QA.md` (this file)
- Backup: `results/backup/project-final-20261014-214722/`

No OpenCode / OMO-Slim / model / provider / agent config was modified.

## 3. Architecture verification (diagram vs actual source)

Read `src/parallel.py`, `src/io_tasks.py`, `src/simulation.py`, `src/world.py`,
`src/dashboard_server.py`, `main.py`, `run.py`, `benchmark.py`.

| Diagram claim | Source evidence | Verdict |
|---|---|---|
| Main process owns canonical world + all ants | `HybridSimulation` holds `self.sim`; main applies updates | verified |
| Persistent ProcessPool across iterations | `ProcessPoolExecutor` created once in `__init__` (`parallel.py:171`) | verified |
| Build world snapshot (grids) | `world_snapshot` dict of food/obstacle/pheromone grids (`parallel.py:185-192`) | verified |
| Chunk ants per worker | `chunk_size = ceil(ants/processes)`; `ant_chunks` (`parallel.py:177-182`) | verified |
| Submit chunks to ProcessPool | `self.executor.submit(worker_step_ants, item)` (`parallel.py:202`) | verified |
| Barrier: wait all futures | `for future in futures: future.result()` (`parallel.py:206-211`) | verified |
| Deterministic merge by `chunk_id` | `results.sort(key=lambda r: r['chunk_id'])` (`parallel.py:214`) | verified |
| Main process applies world update | food/deposit/pheromone merge + pheromone decay in main (`parallel.py:222-266`) | verified |
| ThreadPool handles checkpoint / stats / CSV / dashboard | `IOTaskManager(ThreadPoolExecutor)` with `save_checkpoint_async`, `write_stats_async`, `write_csv_async`, `write_dashboard_snapshot_async` (`io_tasks.py`) | verified |
| I/O tasks run as futures, awaited only when needed | `.submit(...)` returns Future; `.result()` called only when required (final state, benchmark CSV) | verified — **not** claimed as always non-blocking |
| Dashboard = ThreadingHTTPServer + start/pause/resume/restart | `dashboard_server.py` (`ThreadingHTTPServer`, `threading.Event`) | verified |
| MPI not used (single machine) | no MPI imports anywhere; no communicator/rank | verified |

**Feature verification (S3):** grid arrays (`world.py`), agents with id/pos/has_food/
behavior/path, food sources + obstacles, pheromone deposit/decay, movement decision from
pheromone + distance heuristic (`alpha`, `beta`), and runtime metrics from
`simulation.get_metrics()` — all confirmed in source.

## 4. Per-slide changes
- **S1 Cover** — unchanged (kept).
- **S2 Masalah & tujuan** — reframed for ANT WORLD: what is simulated, the goal, why hybrid.
- **S3 Fitur & komponen** — NEW: verified components + runtime metrics (replaces old
  "Konsep hybrid" which moved into S5).
- **S4 Konfigurasi** — kept (key parameters).
- **S5 Arsitektur hybrid computing** — REWRITTEN: two-lane diagram (ProcessPool lane +
  ThreadPool lane) tied to a main-process band, coordination strip, MPI note. Answers
  soal UTS Bagian A explicitly.
- **S6 Dashboard** — reframed: what can be observed (map, status, hybrid panel, telemetry);
  large real screenshot kept.
- **S7 Implementasi teknis** — NEW: each technology tied to its role (Python, NumPy,
  ProcessPoolExecutor, ThreadPoolExecutor, multiprocessing, matplotlib/pandas).
- **S8 Hasil utama** — kept (hero 1,4878×, serial/hybrid times, efisiensi, throughput,
  food=0; speedup-not-functional-proof note).
- **S9 Perbandingan** — FIXED: added the full four-configuration data table (all
  serial/hybrid time pairs) beside the chart. Previously only speedup values were on the slide.
- **S10 Evaluasi proyek** — 3 columns: measured / design-visible / needs-profiling;
  food=0 as a functional limitation.
- **S11 Kesimpulan & pengembangan** — achieved / limits / development priorities
  (investigate food=0, functional tests, repeat benchmark, profile).
- **S12 Penutup** — kept (thanks, identity, demo/repo links, readable references).

## 5. Render + QA results

| Check | Result |
|---|---|
| PPTX opens & editable | Yes |
| Slide count | 12 |
| Package integrity / geometry | 0 problems |
| Clipping / overlap | none (Slide 6 flag = intentional full-bleed dashboard; text-area ink 0.001) |
| Render PDF + PNG | 12 PNGs + PDF, rendered from the FINAL pptx |
| Layout variety | 6 two-column / 4 stacked — varies |
| Slide 5 two-lane colours | blue lane (ProcessPool) left, green lane (ThreadPool) right, navy band — verified |
| Slide 9 colours vs legend | blue ≥1,0× bands 1–3, red <1,0× band 4 — verified |
| Anti-slop content audit | 0 findings; hype/jargon/placeholder spot-check = none |
| Prose em-dashes | 0 (short labels/footer exempted, documented) |
| Benchmark completeness | all 16 figures present, match source |

## 6. Data verification
All 16 figures matched the report and are present in the deck: `4,597952`, `3,090437`,
`1,4878`, `4,668423`, `3,134073`, `1,4896`, `4,944367`, `3,516699`, `1,4060`,
`1,982886`, `2,157669`, `0,9190`, `49,59`, `449,77`, `247006111139`, `1.390`.
Speedup = `T_serial / T_hybrid`; efficiency = speedup / number of processes.

## 7. Problems fixed vs remaining

**Fixed during this revision:**
- Architecture slide was a single serial rail → replaced with the required two-lane
  diagram (ProcessPool vs ThreadPool).
- Implementation slide was a duplicate of project components → replaced with a
  technology-to-role mapping tied to code.
- S9 missing three configurations' serial/hybrid time pairs → full table added.
- S10/S11 reframed for project evaluation and development priorities.

**Remaining / unresolved (reported honestly):**
- No vision-model review (provider credentials unavailable).
- Slide 9 reference line at 1,0× is drawn at an approximated plot height (1,0/1,7 of
  the frame), not an axis crossing.
- `build-deck` (pptxgenjs) intentionally not used as the renderer.

## 8. Baseline safety
`ANT_WORLD_Presentasi_UTS.pptx` (21:01), `..._Revisi.pptx` (21:10),
`..._AntiSlop.pptx` (21:18), `..._FINAL.pptx` (21:32) all keep their original
timestamps. PROJECT_FINAL was built afterward. Backup at
`results/backup/project-final-20261014-214722/`.

## 9. Acceptance checklist
- [x] Presentation focused on the ANT WORLD project
- [x] Soal UTS Bagian A answered explicitly (S5)
- [x] Diagram shows ProcessPool and ThreadPool lanes separately
- [x] Each lane's function matches the implementation (verified vs source)
- [x] Main process role and coordination flow clear
- [x] MPI status stated correctly (unused, single machine)
- [x] Real dashboard screenshot large and readable
- [x] Benchmark data matches source (all 16 figures)
- [x] Food collected = 0 explained honestly
- [x] No exaggerated scientific claims
- [x] References consistent
- [x] All slides rendered and inspected
- [x] Anti-slop audit run after revision
- [x] Final file opens and is editable
- [x] Old files safe
- [~] Vision review — unavailable; documented (see §7)
