# ANT WORLD — Hybrid Parallel Ant Colony Simulation

ANT WORLD adalah simulasi koloni semut pada grid 2D yang digunakan untuk menunjukkan komputasi hybrid: pekerjaan CPU dijalankan secara paralel dengan `ProcessPoolExecutor`, sedangkan pekerjaan I/O dikelola oleh `ThreadPoolExecutor`. Mode serial disediakan sebagai baseline yang setara.

## Tujuan dan Konsep Simulasi

Dunia terdiri atas sarang, sumber makanan, rintangan, peta feromon, dan semut. Semut bergerak pada delapan arah, menghindari rintangan, mencari makanan, mengikuti jejak feromon, lalu membawa makanan kembali ke sarang. Aturan sederhana ini terinspirasi Ant Colony Optimization dan dibuat agar mudah dijelaskan serta stabil untuk demo.

## Parameter Proyek

| Parameter | Nilai |
|---|---:|
| NIM dan random seed | `247006111139` |
| Thread I/O | 5 |
| Process CPU | 3 |
| Data semut | 1390 |

Nilai utama berada di `config.py`. Seed digunakan untuk membangun world dan perilaku deterministik.

## Arsitektur dan Alur

- `config.py`: parameter simulasi dan dunia.
- `src/world.py`, `src/ant.py`, `src/simulation.py`: model world, semut, dan langkah simulasi serial.
- `src/parallel.py`: pemecahan ant menjadi chunk CPU dan penggabungan hasil worker.
- `src/io_tasks.py`: checkpoint, statistik, dan file CSV melalui ThreadPool.
- `src/metrics.py`: waktu, throughput, speedup, efisiensi, dan jalur.
- `src/dashboard_server.py` + `dashboard/`: dashboard lokal dan visualisasi grid.
- `benchmark.py`: variasi konfigurasi dan grafik.

Setiap iterasi hybrid mengirim chunk semut ke process worker. Program menunggu seluruh future (barrier), menggabungkan posisi/deposit secara deterministik, kemudian memperbarui feromon global. ThreadPool digunakan untuk operasi I/O dan pembaruan dashboard, bukan untuk menggantikan komputasi CPU semut.

## Struktur Proyek

```text
UTS/
├── config.py              # Konfigurasi parameter simulasi & seed NIM
├── main.py                # Entry point CLI (serial & hybrid)
├── run.py                 # Entry point demo interaktif (hybrid + dashboard)
├── benchmark.py           # Script benchmark multi-konfigurasi & pembuat grafik
├── requirements.txt       # Daftar dependensi Python
├── README.md              # Dokumentasi proyek
├── .gitignore             # Pengabaian file build, venv, dan cache
│
├── src/                   # Source code modular
│   ├── world.py           # Model grid 2D, sarang, makanan, feromon
│   ├── ant.py             # Logika perilaku agen semut
│   ├── simulation.py      # Engine simulasi baseline serial
│   ├── parallel.py        # Komputasi hybrid (chunking & ProcessPool barrier)
│   ├── io_tasks.py        # Pengelolaan tugas I/O asinkron (ThreadPool)
│   ├── metrics.py         # Perhitungan performa (waktu, throughput, speedup, efisiensi)
│   └── dashboard_server.py# HTTP server lokal untuk web dashboard
│
├── dashboard/             # Antarmuka visualisasi web
│   ├── index.html         # Tampilan web dashboard
│   ├── style.css          # Styling tampilan visualisasi
│   └── app.js             # Client-side render & polling state
│
├── docs/                  # Laporan dan naskah dokumen
│   ├── Laporan_UTS_Hybrid_Computing_Ripki_Maulana.docx         # Laporan akhir UTS
│   ├── Laporan_UTS_Hybrid_Computing_Ripki_Maulana.pdf          # Ekspor PDF (revisi 08 Okt)
│   ├── Laporan_UTS_Hybrid_Computing_Ripki_Maulana_rev*.pdf     # Ekspor PDF revisi terbaru
│   ├── requirements_traceability.csv    # Matriks keterlacakan spesifikasi PPT → kode
│   ├── audit_kesesuaian_ppt_website.md  # Audit kesesuaian website terhadap PPT
│   ├── Soal UTS Komputasi Paralel dan Terdistribusi 20261.pdf  # Naskah soal
│   └── archive/           # Dokumen draft & laporan QA versi sebelumnya
│
├── results/               # Hasil eksekusi & visualisasi benchmark
│   ├── benchmark_results.csv            # Data riil hasil 36 pengujian benchmark
│   ├── ANT_WORLD_Presentasi_UTS_*.pptx  # Materi presentasi (versi terbaru = Redesign_Final)
│   ├── screenshots/                     # Gambar diagram & screenshot untuk laporan
│   └── archive/                         # Artefak lama: checkpoints/, benchmark_io/, backup/
│
├── scripts/               # Script utilitas & otomatisasi
└── tests/                 # Unit testing dan validasi pengujian (pytest)
```

> **Artefak regenerable.** `results/checkpoints/`, `results/benchmark_io/`, dan
> `results/run_stats.json` dihasilkan ulang saat menjalankan `run.py` / `benchmark.py`,
> sehingga tidak dilacak git. Salinan historisnya disimpan di `results/archive/`.

## Instalasi dan Menjalankan

```powershell
python -m pip install -r requirements.txt
```

```powershell
# Demo utama: mode hybrid, dashboard otomatis aktif
python run.py

# Opsional: jangan buka browser dan/atau ubah panjang demo
python run.py --no-browser --iterations 100

# Hybrid lewat CLI lama (baseline serial otomatis diukur)
python main.py --mode hybrid --iterations 1000

# Hybrid dengan dashboard lokal dan checkpoint
python main.py --mode hybrid --iterations 1000 --dashboard --checkpoint
```

Perintah demo utama adalah `python run.py`. Launcher menjalankan mode Hybrid dengan ThreadPool 5, ProcessPool 3, 1390 semut, dan seed NIM; dashboard lokal tersedia di `http://127.0.0.1:8080` dan browser dibuka otomatis. Pada Railway, server bind ke `0.0.0.0:$PORT` dan browser otomatis dinonaktifkan. Dashboard menyediakan START, PAUSE, RESUME, dan RESTART; pause menahan state simulasi, resume melanjutkan dari state tersebut, dan restart membuat world baru pada kondisi awal. Setelah selesai, dashboard tetap aktif sampai pengguna menekan RESTART atau menghentikan proses dengan Ctrl+C. Gunakan `--no-browser` untuk tidak membuka browser atau `--iterations N` untuk demo singkat. Opsi konfigurasi CLI lama tetap tersedia untuk eksperimen.

### Menjalankan Mode Serial

Untuk menjalankan simulasi serial tanpa komputasi CPU paralel, gunakan `main.py`:

```powershell
python main.py --mode serial --iterations 1000
```

Jumlah iterasi bisa disesuaikan. Jumlah semut secara default mengikuti konfigurasi
di `config.py`; gunakan `--ants` untuk mengubahnya:

```powershell
python main.py --mode serial --iterations 100 --ants 500
```

Hasil metrik ditampilkan di terminal dan disimpan ke `results/run_stats.json`
secara default. Gunakan `--output` untuk menentukan file hasil lain, misalnya
`python main.py --mode serial --iterations 1000 --output results/serial_stats.json`.
Mode ini menjalankan simulasi semut secara serial; ThreadPool hanya digunakan untuk
tugas I/O seperti menyimpan statistik atau checkpoint.

Dunia 100×100 memiliki 160 sel obstacle secara default. Layer **Obstacles** aktif secara default di peta; semut menghindari sel tersebut dan tidak dapat bergerak diagonal melewati sudut yang terhalang, baik pada simulasi serial maupun hybrid.

## Metrik Performa

- **Execution Time**: waktu wall-clock simulasi.
- **Throughput**: `jumlah_semut / execution_time` (semut per detik).
- **Speedup**: `waktu_serial / waktu_hybrid`.
- **Efficiency**: `speedup / jumlah_process × 100%`.

Nilai diukur saat runtime dan tidak dibuat secara manual. Mode hybrid mengukur serial baseline dengan jumlah semut, seed, dan iterasi yang sama kecuali `--no-baseline` digunakan.

## Benchmark dan Grafik

Jalankan perintah berikut dari folder utama proyek setelah dependensi terpasang.
Benchmark default menguji semua kombinasi konfigurasi yang ditentukan di script:

```powershell
python benchmark.py
```

Untuk uji coba lebih singkat, tentukan kombinasi thread, process, jumlah semut,
dan iterasi secara langsung:

```powershell
python benchmark.py --threads 3 5 7 --processes 2 3 --ants 500 1000 1390 --iterations 100
```

Benchmark menjalankan seluruh kombinasi thread, process, dan jumlah semut yang
diberikan (18 konfigurasi pada nilai default). Header terminal mencantumkan nama
mahasiswa dan setiap eksekusi diberi Run ID. Data metrik, termasuk `Iterations`,
`Seed`, dan `Run ID`, disimpan di `results/benchmark_results.csv`. Grafik
perbandingan thread/process hanya membandingkan pengukuran dengan workload dan
parameter lain yang identik; judul grafik menampilkan Run ID yang sama dengan CSV.
Grafik disimpan ke `results/`:

1. `time_vs_threads.png` — waktu terhadap jumlah thread.
2. `time_vs_processes.png` — waktu terhadap jumlah process.
3. `speedup_vs_configuration.png` — speedup dan efisiensi per konfigurasi.

Checkpoint JSON tersimpan di `results/checkpoints/`. Opsi `--checkpoint-interval` mengatur periodenya.

## Catatan Platform

Worker ProcessPool berada pada fungsi tingkat modul agar dapat dipanggil pada Windows. Jalankan program melalui entry point `main.py` (yang memiliki guard `if __name__ == '__main__'`). Hybrid dapat lebih lambat pada beban kecil karena biaya serialisasi dan komunikasi antarproses; hasil benchmark harus ditafsirkan dari pengukuran aktual.
