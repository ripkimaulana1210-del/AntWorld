# ANT WORLD — Presentasi UTS Redesign (from scratch)

**Build:** fresh 14-slide deck, new visual identity, no reuse of prior decks.
**Sources:** `docs/Laporan_UTS_Hybrid_Computing_Ripki_Maulana.pdf` (content + Table 5),
`src/*.py` (implementation verification), `results/dashboard_actual.png` (real screenshot).

## Deliverables (local paths — this environment has no web host)

| # | Artifact | Path |
|---|---|---|
| 1 | PPTX final | `results/ANT_WORLD_Presentasi_UTS_Redesign_Final.pptx` |
| 2 | PDF | `results/ANT_WORLD_Presentasi_UTS_Redesign_Final.pdf` |
| 3 | Contact sheet | `results/ANT_WORLD_Redesign_Contact_Sheet.png` |
| — | Slide PNGs | `results/preview_redesign/Slide1–14.png` |
| — | Generator | `scripts/build_antworld_redesign.py` |
| — | Design brief | `docs/ANT_WORLD_Redesign_DesignBrief.md` |

## Ringkasan isi presentasi (14 slide)

1. **Cover** — judul, tema UTS, identitas, motif jejak feromon.
2. **Masalah & motivasi** — keputusan lokal 1.390 agen tiap iterasi; pertanyaan inti.
3. **Mengenal ANT WORLD** — diagram grid (sarang/semut/makanan/rintangan) + siklus eksplorasi.
4. **Konfigurasi eksperimen** — 3 kelompok parameter (dunia/paralelisme/algoritma), angka dari laporan.
5. **Mengapa hybrid?** — perbandingan CPU-bound vs I/O-bound + alasan GIL.
6. **Arsitektur hybrid** — diagram dua jalur (ProcessPool CPU + ThreadPool I/O) + main process + barrier; catatan MPI.
7. **Alur satu iterasi** — pipeline snapshot→chunk→pool→barrier→merge→world update.
8. **Implementasi & teknologi** — pemetaan pustaka ↔ peran (Python, NumPy, futures, ThreadingHTTPServer, matplotlib/pandas).
9. **Bukti aplikasi** — screenshot dashboard ASLI.
10. **Metodologi benchmark** — baseline vs hybrid, 100 iterasi, tanpa dashboard, metrik, perangkat uji.
11. **Hasil eksperimen** — chart serial vs hybrid + kolom speedup/efisiensi/throughput (format laporan).
12. **Analisis performa** — terukur vs kemungkinan penjelas (belum terbukti).
13. **Keterbatasan & validasi** — food collected = 0; determinisme ≠ kebenaran fungsional.
14. **Kesimpulan & referensi** — manfaat sesuai hasil aktual, pekerjaan lanjutan, referensi IEEE.

## Verifikasi (quality gate)
- Struktur: 14 slide, 0 package/geometry problem; PPTX dapat dibuka & diedit.
- Margin/clipping: 0 issue (14 slide dirender 1920×1080).
- Arsitektur (S6): dua jalur warna berbeda terverifikasi (biru ProcessPool, hijau ThreadPool, band navy).
- Data benchmark: cocok laporan, format koma Indonesia (`49,59%`, `449,77 ants/s`, `1,4878×`).
- Hasil 500 semut yang lebih lambat (0,9190×) ditampilkan eksplisit (warna merah).
- food collected = 0 dinyatakan jujur (S13).
- Anti-slop: 0 hype/jargon/scaffolding; 0 em-dash prosa.
- Render PDF + 14 PNG + contact sheet dari PPTX final yang sama.

## Hal yang belum dapat diverifikasi
1. **Repo & demo online** (`github.com/ripkimaulana1210-del/AntWorld`, `antworld-production.up.railway.app`) **tidak diakses** sesi ini — hanya dicantumkan sebagai tautan proyek, tidak diklaim berjalan.
2. **Angka benchmark** diambil apa adanya dari laporan (satu kali ukur per konfigurasi); tidak dijalankan ulang.
3. **food collected = 0** — penyebab tidak dapat dipastikan tanpa menjalankan/menginstrumentasi ulang kode.
4. **LibreOffice tidak terpasang** → render memakai PowerPoint COM (bukan LibreOffice seperti disarankan prompt); sepenuhnya setara untuk QA visual.
5. Screenshot dashboard berasal dari artefak laporan (`results/dashboard_actual.png`), bukan tangkapan sesi langsung.
