# ANT WORLD — Anti-Slop Redesign: Narrative & Art Direction

> Working doc for rebuilding `results/ANT_WORLD_Presentasi_UTS.pptx` so it does not
> read as an AI-generated template. Craft rules from the `presentation-craft` skill
> (one idea per slide, assertion titles, hero the one thing, vary the form, slop
> detector). Data is from `docs/Laporan_UTS_Hybrid_Computing_Ripki_Maulana.pdf`
> (Table 5) — unchanged, no invented figures.

## Register

Presented academic defense deck (spoken in front of a lecturer), Indonesian.
Mix of presented slides (billboard-like) and read/data-led slides (chart + tight
supporting points). One idea per slide. The audience is the hero: the deck is about
the question "what does parallelism cost, and when does it pay?" — not about the
author or the tool.

## Art direction (scientific, editorial, controlled)

- **Palette (kept):** navy `0E1F3C` primary, `1C5BA8` blue secondary, white ground,
  grey `5A6372` for muted ink. One sharp accent used sparingly: `C0394B` red for the
  single below-1.0 result and `2E9E6B` green as the positive signal. No neon, no
  glow, no glassmorphism, no decorative gradient.
- **Type:** Cambria for titles (editorial, academic), Calibri for body (safe, metrically
  reliable). Type scale fixed: title 30-40, section 18-22, body 13-16, caption 10-11.
- **Grid:** 0.6in margin, consistent 0.3in gutters, one alignment rule. Left-aligned
  body, centered titles only.
- **Signature motif:** a thin pheromone-trail polyline (a data-meaningful mark, not a
  decorative bar). Used once on the cover and once as a divider, not on every slide.
- **No accent line under titles.** No full-width header band repeated as filler — the
  title treatment varies by slide type.

## Layout variety plan (no single device dominates)

| # | Slide | Form | One message (FROM → TO) |
|---|-------|------|--------------------------|
| 1 | Cover | Full-bleed navy, single hero title + trail mark | Topic and stakes. |
| 2 | Latar belakang | Two-column: short provocation left, Nest→Food→Nest loop diagram right | "Agent decisions are local; the cost is global." |
| 3 | Konsep hybrid | **Comparison** (two opposed panels, CPU vs I/O) + a footnote tie-bar | "Two workloads, two mechanisms — GIL decides." |
| 4 | Parameter | **Stat strip** (one row, 4 hero numbers) + small grid thumbnail | "Parameters come from the NIM, not from taste." |
| 5 | Arsitektur | **Process/flow** (7-step rail) + I/O branch | "Chunk → pool → barrier → merge, once per iteration." |
| 6 | Implementasi | **Half-bleed screenshot** (real dashboard) left, 3 tight points right | "The model is small; the runtime is observable." |
| 7 | Metodologi | **Timeline / sequence** (paired serial↔hybrid per config) | "Every config is a paired measurement." |
| 8 | Hasil utama | **Chart + hero number** (one big metric dominates) | "Personal config: hybrid is faster (1.4878×)." |
| 9 | Empat konfigurasi | **Bar chart, insight colored red** + reference line | "Scale changes the answer: 500 ants is slower." |
| 10 | Bottleneck | **Two-column contrast**: design-visible vs unmeasured | "These are hypotheses, not measurements." |
| 11 | Kesimpulan | **Statement + limits** (one hero claim, then honesty) | "Hybrid pays only when the work is large enough." |
| 12 | Penutup | Full-bleed navy, references, quiet close | "Thank you + sources." |

Forms used exactly once each: hero title, loop diagram, comparison, stat strip,
process rail, half-bleed screenshot, timeline, chart-focus, chart+reference-line
(different treatment from #8), contrast columns, statement. No run of 2×2 card grids;
the old three-identical-card slide is removed.

## Slop audit targets (from `slop.md`)

Reject before building: tacked-on strapline; wall-of-text; 6+ loose bullets; title
restating body; decoration over communication; leftover scaffolding ("Agenda",
"Thank You" filler); one device deck-wide. Delete the old repeated 3-card layout and
the slogan footers.
