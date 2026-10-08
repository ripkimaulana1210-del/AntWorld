from pathlib import Path
from docx import Document

file = Path(__file__).resolve().parent.parent / 'docs' / 'Laporan_UTS_Hybrid_Computing_Ripki_Maulana.docx'
doc=Document(str(file))

def remove(p): p._element.getparent().remove(p._element)
def replace(p,text): p.clear(); p.add_run(text)

# Remove duplicate speedup caption and redundant efficiency paragraph.
for p in list(doc.paragraphs):
    if p.text.startswith('Gambar 8. Speedup dan efficiency per konfigurasi; garis S=1'):
        remove(p)
    if p.text.startswith('Efficiency konfigurasi personal adalah 49,59%'):
        remove(p)
    if p.text.startswith('Grafik yang dilaporkan pada versi ini dibentuk dari empat konfigurasi'):
        replace(p,'Grafik membandingkan pasangan dengan faktor lain tetap: jumlah thread pada 3 proses dan 1.390 ants; jumlah process pada 5 thread dan 1.390 ants; serta speedup dan efficiency untuk empat konfigurasi. Seluruh nilai diturunkan dari benchmark 100 iterasi yang sama dengan Tabel 5.')
    if p.text.startswith('Versi Python adalah versi interpreter aktif'):
        replace(p,'Interpreter yang digunakan saat pengukuran adalah Python 3.14.3. Pustaka eksternal yang tercantum sebagai dependensi project adalah NumPy, Matplotlib, dan pandas; executor menggunakan concurrent.futures serta multiprocessing dari standard library.')
    if p.text.startswith('Catatan akurasi: tidak semua mode CLI'):
        replace(p,'Launcher dashboard menunggu tombol START, mengukur baseline serial, lalu menjalankan mode hybrid. Benchmark batch menjalankan serial dan hybrid berpasangan untuk setiap konfigurasi, tanpa server dashboard aktif. Metode ini menjaga batas pengukuran benchmark terpisah dari overhead layanan dashboard.')

# Remove duplicate terminal placeholder copies everywhere except the appendix entry.
terminal=[p for p in doc.paragraphs if p.text.startswith('[SCREENSHOT BELUM TERSEDIA') and 'terminal' in p.text.lower()]
appendix=next((p for p in doc.paragraphs if p.text.strip()=='Lampiran A — Screenshot Terminal'),None)
kept=False
for p in terminal:
    if appendix and p._p.getprevious() is appendix._p and not kept:
        kept=True
    else:
        remove(p)

# Make B sections in the requested sequence and avoid stale duplicated B2 headings.
for p in doc.paragraphs:
    s=p.text.strip()
    if s=='B7. Benchmark dan Metrik':
        replace(p,'B7. Pengukuran Performa')

doc.save(str(file))
print(file)
