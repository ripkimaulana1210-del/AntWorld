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
│   ├── Laporan_UTS_Hybrid_Computing_Ripki_Maulana.docx  # Laporan akhir UTS
│   ├── Soal UTS Komputasi Paralel dan Terdistribusi 20261.pdf # Naskah soal
│   └── drafts/            # Arsip versi draft dokumen sebelumnya
│
├── results/               # Hasil eksekusi & visualisasi benchmark
│   ├── benchmark_results.csv        # Data riil hasil 36 pengujian benchmark
│   ├── run_stats.json               # Ringkasan metrik eksekusi simulasi
│   ├── speedup_vs_configuration.png # Grafik speedup & efisiensi
│   ├── time_vs_processes.png        # Grafik perbandingan waktu vs process
│   ├── time_vs_threads.png          # Grafik perbandingan waktu vs thread
│   ├── checkpoints/                 # File checkpoint state simulasi
│   ├── benchmark_io/                # File output I/O pengujian benchmark
│   ├── report_screenshots/          # Gambar diagram dan screenshot untuk laporan
│   └── archive/                     # Arsip hasil smoke test & pengujian sementara
│
├── scripts/               # Script utilitas & otomatisasi
└── tests/                 # Unit testing dan validasi pengujian (pytest)
```

## Instalasi dan Menjalankan

```powershell
python -m pip install -r requirements.txt
```

```powershell
# Demo utama: mode hybrid, dashboard otomatis aktif
python run.py

# Opsional: jangan buka browser dan/atau ubah panjang demo
python run.py --no-browser --iterations 100

# Mode baseline serial tetap tersedia
python main.py --mode serial --iterations 1000

# Hybrid lewat CLI lama (baseline serial otomatis diukur)
python main.py --mode hybrid --iterations 1000

# Hybrid dengan dashboard lokal dan checkpoint
python main.py --mode hybrid --iterations 1000 --dashboard --checkpoint
```

Perintah demo utama adalah `python run.py`. Launcher menjalankan mode Hybrid dengan ThreadPool 5, ProcessPool 3, 1390 semut, dan seed NIM; dashboard tersedia di `http://127.0.0.1:8080` dan browser dibuka otomatis. Dashboard tetap hidup setelah iterasi selesai sampai pengguna menekan Ctrl+C; Ctrl+C menghentikan ProcessPool, ThreadPool, dan server dashboard. Gunakan `--no-browser` untuk tidak membuka browser atau `--iterations N` untuk demo singkat. Opsi konfigurasi CLI lama tetap tersedia untuk eksperimen.

## Metrik Performa

- **Execution Time**: waktu wall-clock simulasi.
- **Throughput**: `jumlah_semut / execution_time` (semut per detik).
- **Speedup**: `waktu_serial / waktu_hybrid`.
- **Efficiency**: `speedup / jumlah_process × 100%`.

Nilai diukur saat runtime dan tidak dibuat secara manual. Mode hybrid mengukur serial baseline dengan jumlah semut, seed, dan iterasi yang sama kecuali `--no-baseline` digunakan.

## Benchmark dan Grafik

```powershell
python benchmark.py
python benchmark.py --threads 3 5 7 --processes 2 3 --ants 500 1000 1390 --iterations 100
```

Benchmark menjalankan seluruh kombinasi thread, process, dan jumlah semut (18 konfigurasi pada nilai default). Header terminal mencantumkan nama mahasiswa, dan setiap eksekusi diberi Run ID. `results/benchmark_results.csv` menyimpan metrik beserta `Iterations`, `Seed`, dan `Run ID`. Grafik perbandingan thread/process hanya membandingkan pengukuran yang memiliki workload dan parameter lain identik; judul grafik menampilkan Run ID yang sama dengan CSV. Grafik disimpan ke `results/`:

1. `time_vs_threads.png` — waktu terhadap jumlah thread.
2. `time_vs_processes.png` — waktu terhadap jumlah process.
3. `speedup_vs_configuration.png` — speedup dan efisiensi per konfigurasi.

Checkpoint JSON tersimpan di `results/checkpoints/`. Opsi `--checkpoint-interval` mengatur periodenya.

## Catatan Platform

Worker ProcessPool berada pada fungsi tingkat modul agar dapat dipanggil pada Windows. Jalankan program melalui entry point `main.py` (yang memiliki guard `if __name__ == '__main__'`). Hybrid dapat lebih lambat pada beban kecil karena biaya serialisasi dan komunikasi antarproses; hasil benchmark harus ditafsirkan dari pengukuran aktual.
