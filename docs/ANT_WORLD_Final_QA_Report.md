# ANT WORLD Final QA Report

**Deck:** `ANT_WORLD_Presentasi_UTS_FINAL.pptx`
**Baseline:** `ANT_WORLD_Presentasi_UTS_AntiSlop.pptx` (not overwritten)
**Working dir:** `D:\Kuliah\Season 5\KPT\UTS`
**Date of run:** (this session)

---

## 1. Skills actually read and used

| Skill | Read? | How it was applied |
|---|---|---|
| `presentation-craft` (+ refs `slides.md`, `composition.md`, `data-viz.md`, `slop.md`, `deck-spec.md`) | Yes | Source of the craft rules: one idea per slide, assertion titles, hero the one thing, vary the form, chart-message-first, slop detector. Applied to slide copy and layout. |
| `slop-check` | Yes | Ran the detector (Layers 1 + prose tells) over the deck content after revision. |
| `revise` | Yes | Guidance followed: keep the existing generator (script-built deck), edit the source, re-render, re-run gates, do not overwrite the original. |
| `narrative` | Yes (principle) | Story arc: problem → method → results → limits → conclusion. |
| `build-deck` | Read as reference only | Not used as the renderer — switching generators would risk the native editable elements. Documented as a decision. |
| `teach-slides` | Read as reference | Confirmed the one-idea-per-slide discipline. |
| `pptx-builder` | Yes | Owned the file mechanics: generator, package verify, render, QA. |
| `pptx-deck-context` | Yes | Kept identity/narrative/source lineage stable. |
| `pptx-slide-specification` | Yes (principle) | Explicit coordinates, safe margins, no auto-layout. |
| `pptx-visual-assets` | Yes | Kept the real dashboard screenshot; no invented assets. |
| `pptx-reference-deck-analysis` / `pptx-quality-gates` | Yes | Package + geometry validation criteria. |
| `scientific-slides` | Yes (principle) | Scientific limits: single run, food=0, no unproven bottleneck, MPI not used. |
| `frontend-slides` | Not used | No web/HTML deliverable — not applicable. Documented. |

Independent visual review via vision sub-agent: **attempted, unavailable** (provider `kiro`
has no credentials). Visual QA done via rendered PNGs + pixel/geometry analysis instead.
Reported honestly, not claimed as human-style inspection.

---

## 2. Files changed

| File | Change |
|---|---|
| `scripts/build_antworld_antislop.py` → copied to `scripts/build_antworld_final.py` | FINAL generator (source of truth for the deck). |
| `results/ANT_WORLD_Presentasi_UTS_FINAL.pptx` | New final deck (baseline preserved). |
| `results/ANT_WORLD_Presentasi_UTS_FINAL.pdf` | Rendered from the FINAL pptx. |
| `results/preview_final/Slide1..12.png` | Rendered from the FINAL pptx. |
| `docs/ANT_WORLD_Final_QA_Report.md` | This report. |
| `results/backup/<timestamp>/` | Baseline backup copy. |

No OpenCode / OMO-Slim / model / provider / agent config was modified.

---

## 3. Tahap A — audit findings (categorised)

**Content & accuracy**
- C1 `Food collected = 0` present on slides 8, 11 — good; also required nowhere else. OK.
- C2 Speedup metric labelled `T_serial / T_hybrid` on slide 8 — correct per report. OK.
- C3 Slide 9 chart series names use `≥`/`<` glyphs; legends may render as tofu in some fonts. Watch on render.
- C4 Slide 4 lists `Pheromone decay / deposit 0,1 / 10,0` and `Alpha / beta 1,0 / 2,0` — verified against report table B2. OK.

**Design visual**
- D1 Slide 4 has 61 shapes (dense) — the "Konfigurasi lain" list is a long right column. Acceptable but heavy.
- D2 Slide 7 timeline bars are minor: 4 configs × 2 bars, small. Could read as decoration if not labelled.
- D3 No repeated 3-card layout — good (previous version fixed this).

**Readability**
- R1 Slide 2 left-column paragraph runs ~3 lines each — within limits.
- R2 Slide 6 half-bleed image width 6.4in covers left; text column narrow but OK.

**Charts & data**
- G1 Slide 8 chart: value axis to 6.0, direct labels — good.
- G2 Slide 9: reference line drawn manually at 1.0/1.7 of plot height — approximate; acceptable but flagged.

**References**
- F1 Slide 12 has 7 references; [4] Amdahl year 1967 and page 483-485 verified in report. Others condensed but traceable. OK.

**File integrity**
- I1 Package valid; 12 slides; 1 picture (dashboard); 2 charts. OK.

## 4. Tahap B — per-slide change plan

Substantive-first order. Keep effective elements; change only what helps.

1. Cover — keep. Add "Program Studi Informatika" clarity already present. No change beyond minor spacing.
2. Latar belakang — tighten the "beban komputasi" link: add one explicit clause connecting local decisions → compute cost. Keep loop diagram.
3. Konsep — already accurate (GIL). Keep.
4. Parameter — reduce visual weight of the long "Konfigurasi lain" list; group into ≤ 4 rows or keep but restyle. 
5. Arsitektur — accurate. Keep.
6. Implementasi — keep large real screenshot.
7. Metodologi — add hardware context line (i3-4160, 2 core/4 logical) per prompt §5.
8. Hasil utama — add explicit note that speedup is a performance comparison, not proof the simulation works functionally.
9. Perbandingan — keep; ensure 0,9190× clearly below baseline.
10. Analisis — already separates design-visible vs unmeasured. Keep.
11. Kesimpulan — add explicit "needs re-run + functional validation" line. Keep.
12. Penutup — keep icons/links; references readable.

## 5. Tahap D/E/F results

### D — Render + inspect (12 slides, 1920×1080, via PowerPoint COM)
- `results/ANT_WORLD_Presentasi_UTS_FINAL.pdf` + `results/preview_final/Slide1..12.PNG`
  rendered **from the FINAL pptx** (not a stale build).
- Structural validation: **12 slides, 0 package problems, 0 geometry problems.**
- Margin/clipping QA (content zone): 11/12 OK. **1 flagged — Slide 6** — proven a
  **false positive**: the real dashboard screenshot is intentionally full-bleed to the
  bottom-left; the flag region is image content (pixel std ≈ 81) plus the navy caption
  bar (brightness ≈ 64), and the adjoining text area has ink ≈ 0.001 (no clipping).
- Layout-variation audit: 5 two-column / 5 stacked content slides → **no single form
  dominates** (the "no dark title bar" notices are expected: the redesign deliberately
  replaced the repeated title bar with an editorial kicker + assertion title).
- Slide 9 colour/legend check: bands 1-3 **BLUE** (≥1,0×), band 4 **RED** (0,9190×) —
  matches the legend.

### E — Anti-slop audit (slop-check detector layers)
- Content audit: **0 findings** (no scaffolding, hype, business-jargon, bullet-soup, or
  wall-of-text).
- **Detector credibility verified**: planting sample slop ("revolutionary",
  "game-changer", "deep dive", "circle back", "agenda", "thank you") is correctly
  caught — so the zero result is meaningful, not a silent no-op.
- **Gap found and fixed (not hidden):** the em-dash rule in `slop.md` was not in the
  content detector, and the deck carried **5 prose em-dashes**. All 5 were rewritten
  out of the **prose**. Remaining em-dashes are confined to short **labels/footers**
  (institutional footer line, cover identity line, section kickers) and the reference
  list separator — `slop.md` exempts slide copy (a fragment by design); the reference
  separators were switched to standard IEEE comma/period style anyway.

### F — Revision + final validation
- Fixed: Slide 2 (local decision → compute cost phrasing), Slide 7 (hardware context),
  Slide 8 (speedup is a performance comparison, not functional proof), Slide 11
  (re-run + functional validation), and the 5 prose em-dashes.
- Rebuilt, re-rendered, re-ran all gates → all pass (see §8).

## 6. Benchmark verification
All 15 figures matched the report text (`4,597952`, `3,090437`, `1,4878`, `4,668423`,
`3,134073`, `1,4896`, `4,944367`, `3,516699`, `1,4060`, `1,982886`, `2,157669`,
`0,9190`, `247006111139`, `1.390`, `100 iterasi`). No silent number changes.
Speedup formula kept as `T_serial / T_hybrid`; efficiency = speedup / jumlah process.

## 7. Baseline not overwritten
Confirmed: `ANT_WORLD_Presentasi_UTS.pptx`, `..._Revisi.pptx`, `..._AntiSlop.pptx`
remain on disk with their original timestamps (13:13, 22:08, 18:29). FINAL built later
(21:32). Backup at `results/backup/20261014-212815/`.

## 8. Final validation summary

| Check | Result |
|---|---|
| PPTX opens | Yes (python-pptx + PowerPoint) |
| Slide count | 12 |
| Package integrity | 0 problems |
| Geometry / off-canvas | 0 problems |
| Text clipping / overlap | none found (1 intentional full-bleed, verified) |
| Benchmark consistency | 15/15 match source |
| Scientific claims | limits stated (single run, food=0, no proven bottleneck, MPI unused) |
| Screenshot dashboard | real, preserved (1 picture) |
| Charts | 2 native, labelled |
| Layout variety | 5 / 5 — varies |
| Anti-slop content audit | 0 findings; credibility spot-checked |
| Prose em-dashes | 0 (labels exempted, documented) |
| References | 7, IEEE-style, traceable |

## 9. Honest limitations
- No vision-capable model review: the `designer`/`oracle` sub-agents failed on missing
  provider credentials (`kiro`). Visual QA = rendered PNG inspection + pixel/geometry
  analysis, not a human/vision model pass. Not claimed otherwise.
- Slide 9's 1,0× reference line is drawn at an approximated plot height (1.0/1.7 of the
  frame), not an Excel axis crossing — adequate for presentation, noted for accuracy.
- `build-deck` (pptxgenjs) was **not** used as the renderer to avoid risking the native
  editable elements; the existing python-pptx generator was kept per `revise` guidance.

## 10. Acceptance criteria
All boxes met except the vision-review item, which is reported as unavailable rather
than claimed. See the checklist in §8.

## 11. Final artifacts
- `results/ANT_WORLD_Presentasi_UTS_FINAL.pptx`
- `results/ANT_WORLD_Presentasi_UTS_FINAL.pdf`
- `results/preview_final/Slide1.png … Slide12.png`
- `docs/ANT_WORLD_Final_QA_Report.md` (this file)
- Generator: `scripts/build_antworld_final.py`
- Backup: `results/backup/20261014-212815/`
