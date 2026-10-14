# report.md — Hasil Pengecekan Website vs Spesifikasi PPT (ANT WORLD)

**Tanggal:** 14 Oktober 2026
**Jenis:** Audit kesesuaian spesifikasi (REQ dari PPT) terhadap implementasi website
**Status:** Selesai — audit berbasis bukti. Tidak ada perubahan source code/konfigurasi/deployment.

---

## Ringkasan cepat

| Status | Jumlah |
|---|---:|
| PASS | 29 |
| PARTIAL | 4 |
| FAIL | 0 |
| NOT VERIFIED | 0 |
| NOT APPLICABLE | 2 |
| **Total** | **35** |

**Cakupan PASS dapat dipertanggungjawabkan = 29 / (35 − 2) ≈ 87,9%**
(NOT APPLICABLE dikeluarkan dari penyebut; PARTIAL & NOT VERIFIED **tidak** dihitung PASS.)

**Kesimpulan:** Website secara substansial **SESUAI** dengan PPT (0 FAIL; arsitektur hybrid & deployment terbukti), tetapi **belum 100%** karena 4 butir PARTIAL dan inspeksi visual browser tidak tersedia.

---

## Yang diperiksa

| Sumber | Detail |
|---|---|
| Spec (PPT acuan) | `results/ANT_WORLD_Presentasi_UTS_Redesign_Final.pptx` (14 slide) |
| Implementasi (website) | `dashboard/index.html`, `dashboard/app.js`, `dashboard/style.css` |
| Backend | `src/dashboard_server.py`, `src/parallel.py`, `src/io_tasks.py`, `run.py`, `main.py`, `config.py` |
| Runtime live | `https://antworld-production.up.railway.app/` |

---

## Bukti runtime (probe HTTP live)

| Probe | Hasil |
|---|---|
| `GET /` | **200** · 13815 byte HTML |
| `GET /dashboard/app.js` | **200** · 40755 byte |
| `GET /dashboard/style.css` | **200** · 20177 byte |
| `GET /api/state` | **200** · `iteration=1000`, `food_collected=195`, `food_remaining=313`, `average_path_length=319.24`, `best_path_length=29`, `avg_pheromone=1.388`, `max_pheromone=800.7`, `world 100×100` |
| `GET /api/benchmark` | **200** · CSV 2967 byte (header `Threads,Processes,Data,Time,Speedup,Efficiency,Throughput,Iterations,Seed,Run ID`) |
| `POST /api/control/pause` | **409** (guard status benar, endpoint kontrol hidup) |

**Keterbatasan bukti (jujur):** screenshot browser otomatis (headless Chrome/Edge `--screenshot`) **gagal** — menggantung pada halaman remote, tidak ada PNG dihasilkan; `playwright`/`selenium` tidak terpasang. Karena itu bukti runtime = **respons HTTP + data JSON/CSV**, bukan tangkapan layar. Uji interaksi UI (klik Start/Pause/Resume/Restart, toggle layer, render canvas) belum dijalankan.

---

## Temuan PARTIAL (perlu perhatian)

| ID | Persyaratan | Kondisi sekarang | Dampak | Rekomendasi |
|---|---|---|---|---|
| REQ-010 | Telemetry throughput/speedup/efficiency | UI & kode pengisi ada (`index.html` L134-136, L145-148; `app.js` L414-416), tapi payload `/api/state` yang diprobe **tidak memuat key `performance`** | Nilai inti tema hybrid belum terkonfirmasi terisi saat run | Pastikan `run.py` (L82-89/L123-132) mengirim `performance` di payload state |
| REQ-008 | Jumlah thread & proses | UI ada (`index.html` L116/L121), tapi payload API tak menampilkan `threads`/`processes` | Panel hybrid kurang bukti runtime | Tambahkan key `threads`/`processes` ke payload state |
| REQ-009 | Menampilkan seed | UI ada (`index.html` L125), payload API tak memuat `seed` | Seed belum terverifikasi di runtime | Tambahkan key `seed` ke payload state |
| REQ-035 | Food collected = 0 (klaim benchmark) | PPT: food=0 pada benchmark; deploy live `/api/state`: `food_collected=195` | Beda konteks (benchmark vs sesi live) bisa menyesatkan | Beri label konteks pada kedua angka |

**0 FAIL** — tidak ada implementasi yang bertentangan dengan PPT. Arsitektur hybrid (ProcessPoolExecutor CPU + ThreadPoolExecutor I/O + ThreadingHTTPServer) **terverifikasi sesuai kode** (`src/parallel.py` L171/202, `src/io_tasks.py` L20, `src/dashboard_server.py` L232).

---

## Lolos verifikasi (PASS) — sorotan

- Judul, identitas (NIM 247006111139), mode HYBRID.
- Peta simulasi + legenda (semut/pheromone/food/nest/obstacle) + 3 layer toggle.
- Panel hybrid computing (THREADPOOL vs PROCESSPOOL, I/O vs CPU).
- Kontrol Start / Pause / Resume / Restart (+ modal konfirmasi).
- Telemetry food, pheromone avg/peak, path length, behavior breakdown.
- 3 chart runtime (time/speedup/food) + 3 chart benchmark (threads/processes/speedup).
- Tabel benchmark dari `results/benchmark_results.csv` (via `GET /api/benchmark`).
- Prinsip "tanpa nilai sintetis" (`app.js` L1, `index.html` L153).
- Deployment (host `0.0.0.0` + `PORT`, `Procfile`, `railway.toml`).

---

## Prioritas perbaikan

- **Critical:** tidak ada.
- **High:** REQ-010 (telemetry performa — inti tema UTS).
- **Medium:** REQ-008, REQ-009, REQ-035.
- **Low:** verifikasi visual estetika & interaksi UI.

---

## Batasan & kesimpulan

- Tidak bisa klaim "100% sesuai": 4 butir PARTIAL + tidak ada inspeksi visual browser.
- **Belum ada perbaikan apa pun** pada implementasi (sesuai instruksi: audit dulu, tunggu persetujuan).

**Referensi silang:**
- Laporan audit lengkap: `docs/audit_kesesuaian_ppt_website.md`
- Matriks keterlacakan: `docs/requirements_traceability.csv`
