#!/usr/bin/env python3
"""Generate ANT WORLD — Presentasi UTS (12 slides) [REVISI].

Source of truth: docs/Laporan_UTS_Hybrid_Computing_Ripki_Maulana.pdf (Table 5).
All benchmark numbers are taken verbatim from the report and must not be changed.

Revision notes (2nd pass):
- S3: explicit GIL rationale for ProcessPool vs ThreadPool.
- S5: definitions of chunking/barrier/merge; I/O tasks run asynchronously (not
      claimed to be always free of blocking).
- S6: enlarged, cropped real dashboard screenshot (aspect preserved).
- S7: larger table text and row spacing.
- S8: data labels on the serial-vs-hybrid chart.
- S9: distinct colour for speedup < 1,0x + labels + explicit 1,0x reference line.
- S10: lower text density; design-visible vs unmeasured separated.
- S11: scientific limitations kept (food=0, deterministic, single run).
- S12: more readable references.

Outputs:
    results/ANT_WORLD_Presentasi_UTS_Revisi.pptx   (original is NOT overwritten)

Run:  python scripts/build_antworld_ppt_revisi.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_TICK_MARK, XL_LABEL_POSITION
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt, Emu
from PIL import Image

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SHOT_DIR = Path(os.environ.get(
    "ANT_REPORT_IMAGES",
    r"C:\Users\Ace\AppData\Local\Temp\opencode\antworld_report\images"))
DASHBOARD_SHOT = SHOT_DIR / "page16_1.jpg"  # Gambar 6 — real dashboard screenshot
OUT_PPTX = RESULTS / "ANT_WORLD_Presentasi_UTS.pptx"

# ---------------------------------------------------------------------------
# Design system — navy / blue / white / grey, 16:9
# ---------------------------------------------------------------------------
NAVY = RGBColor(0x0E, 0x1F, 0x3C)
NAVY_2 = RGBColor(0x16, 0x2C, 0x54)
BLUE = RGBColor(0x1C, 0x5B, 0xA8)
BLUE_L = RGBColor(0x4A, 0x90, 0xD9)
ICE = RGBColor(0xDC, 0xE8, 0xF7)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREY = RGBColor(0x5A, 0x63, 0x72)
GREY_L = RGBColor(0xEE, 0xF1, 0xF6)
INK = RGBColor(0x1B, 0x22, 0x30)
GREEN = RGBColor(0x2E, 0x9E, 0x6B)
RED = RGBColor(0xC0, 0x39, 0x4B)
AMBER = RGBColor(0xE0, 0x8A, 0x1E)

FONT = "Calibri"
FONT_H = "Cambria"

SW = 13.333
SH = 7.5
MARGIN = 0.6
CONTENT_W = SW - 2 * MARGIN

# ---------------------------------------------------------------------------
# Official benchmark data (Table 5, verbatim from the report)
# ---------------------------------------------------------------------------
BENCH = [
    # label, threads, processes, ants, t_serial, t_hybrid, speedup, eff, thr
    ("Personal",       5, 3, 1390, 4.597952, 3.090437, 1.4878, 49.59, 449.77),
    ("Variasi thread", 1, 3, 1390, 4.668423, 3.134073, 1.4896, 49.65, 443.51),
    ("Variasi process",5, 2, 1390, 4.944367, 3.516699, 1.4060, 70.30, 395.26),
    ("Variasi data",   5, 3,  500, 1.982886, 2.157669, 0.9190, 30.63, 231.73),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def rect(slide, x, y, w, h, fill=None, line=None, shape=MSO_SHAPE.RECTANGLE,
         line_w=1.0, shadow=False):
    sh = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line; sh.line.width = Pt(line_w)
    if not shadow:
        sh.shadow.inherit = False
    return sh


def text(slide, x, y, w, h, runs, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         wrap=True, spacing=None):
    """runs: list of paragraphs; each paragraph is a list of (txt, size, bold, color, font, space_after)."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    for i, para in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if spacing:
            p.line_spacing = spacing
        for (txt, size, bold, color, font, sa) in para:
            r = p.add_run()
            r.text = txt
            r.font.size = Pt(size)
            r.font.bold = bold
            r.font.color.rgb = color
            r.font.name = font
            if sa is not None:
                p.space_after = Pt(sa)
    return tb


def title_bar(slide, kicker, heading):
    rect(slide, 0, 0, SW, 1.18, fill=NAVY)
    text(slide, MARGIN, 0.14, CONTENT_W, 0.36,
         [[(kicker.upper(), 12, True, BLUE_L, FONT, 0)]])
    text(slide, MARGIN, 0.44, CONTENT_W, 0.66,
         [[(heading, 26, True, WHITE, FONT_H, 0)]])


def page_number(slide, n):
    text(slide, SW - 1.1, SH - 0.5, 0.6, 0.3,
         [[(str(n), 11, False, GREY, FONT, 0)]], align=PP_ALIGN.RIGHT)


def footer(slide, text_str="ANT WORLD — Hybrid Parallel Ant Colony Simulation"):
    text(slide, MARGIN, SH - 0.5, 8.0, 0.3,
         [[(text_str, 9, False, GREY, FONT, 0)]])


def stat_card(slide, x, y, w, h, value, label, value_color=BLUE, value_size=30):
    rect(slide, x, y, w, h, fill=GREY_L, line=ICE, line_w=1.0,
         shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(slide, x + 0.12, y + 0.18, w - 0.24, 0.7,
         [[(value, value_size, True, value_color, FONT_H, 0)]],
         align=PP_ALIGN.CENTER)
    text(slide, x + 0.12, y + 0.18 + 0.72, w - 0.24, h - 0.9,
         [[(label, 12, False, GREY, FONT, 0)]], align=PP_ALIGN.CENTER)


def notes(slide, txt):
    slide.notes_slide.notes_text_frame.text = txt


def style_chart(chart, colors, show_values=False, number_format="0.0"):
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.include_in_layout = False
    chart.font.size = Pt(12)
    chart.font.name = FONT
    for i, s in enumerate(chart.plots[0].series):
        s.format.fill.solid()
        s.format.fill.fore_color.rgb = colors[i % len(colors)]
        if show_values:
            s.has_data_labels = True
            dl = s.data_labels
            dl.number_format = number_format
            dl.number_format_is_linked = False
            dl.font.size = Pt(11)
            dl.font.bold = True
            dl.font.color.rgb = INK
            dl.position = XL_LABEL_POSITION.OUTSIDE_END


# ---------------------------------------------------------------------------
# Slides
# ---------------------------------------------------------------------------
def slide_01_cover(prs):
    s = blank(prs)
    rect(s, 0, 0, SW, SH, fill=NAVY)
    # decorative grid (conceptual, not a screenshot)
    for gx in range(0, 14):
        rect(s, gx, 0, 0.012, SH, fill=NAVY_2)
    for gy in range(0, 8):
        rect(s, 0, gy, SW, 0.012, fill=NAVY_2)
    # accent block
    rect(s, 0, 0, 0.28, SH, fill=BLUE)
    # small ant-like markers along a pheromone trail
    trail = [(1.0, 5.9), (2.1, 5.5), (3.0, 5.9), (3.9, 5.4), (4.8, 5.8)]
    for (px, py) in trail:
        rect(s, px, py, 0.16, 0.16, fill=AMBER, shape=MSO_SHAPE.OVAL)

    text(s, 1.0, 1.35, 11.4, 0.5,
         [[("UJIAN TENGAH SEMESTER — KOMPUTASI PARALEL DAN TERDISTRIBUSI", 13, True, BLUE_L, FONT, 0)]])
    text(s, 1.0, 1.95, 11.4, 1.9,
         [[("ANT WORLD", 54, True, WHITE, FONT_H, 6)],
          [("Hybrid Parallel Ant Colony Simulation", 26, True, ICE, FONT, 0)]])
    text(s, 1.0, 4.05, 11.4, 0.6,
         [[("Hybrid Computing for Real-World Simulation and Data Processing", 15, False, BLUE_L, FONT, 0)]])
    rect(s, 1.0, 4.85, 3.2, 0.03, fill=BLUE_L)
    text(s, 1.0, 5.05, 11.4, 1.2,
         [[("Ripki Maulana  •  NIM 247006111139", 16, True, WHITE, FONT, 4)],
          [("Program Studi Informatika — Fakultas Teknik — Universitas Siliwangi — 2026",
            13, False, ICE, FONT, 0)]])
    notes(s, "Salam pembuka. Perkenalkan judul: ANT WORLD, simulasi koloni semut paralel hybrid. "
             "Sebutkan nama, NIM, dan bahwa presentasi ini meringkas laporan UTS.")


def slide_02_background(prs):
    s = blank(prs)
    title_bar(s, "Latar Belakang", "Masalah: banyak keputusan agen tiap iterasi")
    # left: text
    text(s, MARGIN, 1.45, 6.1, 4.8, [
        [("Semut menjelajah dari sarang untuk menemukan makanan, lalu kembali ke sarang.",
          15, False, INK, FONT, 10)],
        [("Feromon menjadi jejak tidak langsung yang memengaruhi keputusan berikutnya.",
          15, False, INK, FONT, 10)],
        [("Interaksi lokal antarbanyak agen membentuk perilaku kolektif (swarm intelligence).",
          15, False, INK, FONT, 10)],
        [("Setiap iterasi memuat banyak keputusan agen yang harus dihitung dan digabungkan.",
          15, False, INK, FONT, 10)],
        [("Permasalahan: meningkatkan efisiensi komputasi tanpa mengorbankan konsistensi hasil.",
          15, True, BLUE, FONT, 0)],
    ])
    # right: Nest -> Explore -> Food -> Nest diagram
    cx = 7.6
    boxes = [("Nest", 1.6, GREEN), ("Eksplorasi", 2.9, BLUE),
             ("Food", 4.2, AMBER), ("Kembali ke Nest", 5.5, GREEN)]
    for label, y, col in boxes:
        rect(s, cx, y, 3.9, 0.72, fill=col, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        text(s, cx, y + 0.12, 3.9, 0.5, [[(label, 14, True, WHITE, FONT, 0)]],
             align=PP_ALIGN.CENTER)
    # connector arrows
    for y in (2.32, 3.62, 4.92):
        c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(cx + 1.95), Inches(y),
                                   Inches(cx + 1.95), Inches(y + 0.58))
        c.line.color.rgb = GREY; c.line.width = Pt(2)
    text(s, cx, 6.35, 3.9, 0.4, [[("jalur feromon ↓  ↑", 12, False, GREY, FONT, 0)]],
         align=PP_ALIGN.CENTER)
    footer(s); page_number(s, 2)
    notes(s, "Jelaskan perilaku swarm intelligence dan mengapa simulasi ini berat komputasi. "
             "Tekankan pertanyaan inti: efisiensi vs konsistensi hasil.")


def slide_03_hybrid(prs):
    s = blank(prs)
    title_bar(s, "Konsep", "Hybrid computing: CPU-bound + I/O-bound")
    col_w = 3.85
    gap = 0.35
    x0 = MARGIN
    # CPU card
    rect(s, x0, 1.5, col_w, 4.6, fill=GREY_L, line=ICE,
         shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    rect(s, x0, 1.5, col_w, 0.62, fill=BLUE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, x0, 1.62, col_w, 0.5, [[("CPU-bound", 15, True, WHITE, FONT, 0)]],
         align=PP_ALIGN.CENTER)
    text(s, x0 + 0.25, 2.3, col_w - 0.5, 3.6, [
        [("ProcessPoolExecutor", 13, True, BLUE, FONT, 8)],
        [("• Menghitung posisi & keputusan gerak semut", 13, False, INK, FONT, 6)],
        [("• Membagi agen menjadi beberapa chunk", 13, False, INK, FONT, 6)],
        [("• Worker menghitung hasil lokal di proses terpisah", 13, False, INK, FONT, 0)],
    ])
    # I/O card
    x1 = x0 + col_w + gap
    rect(s, x1, 1.5, col_w, 4.6, fill=GREY_L, line=ICE,
         shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    rect(s, x1, 1.5, col_w, 0.62, fill=GREEN, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, x1, 1.62, col_w, 0.5, [[("I/O-bound", 15, True, WHITE, FONT, 0)]],
         align=PP_ALIGN.CENTER)
    text(s, x1 + 0.25, 2.3, col_w - 0.5, 3.6, [
        [("ThreadPoolExecutor", 13, True, GREEN, FONT, 8)],
        [("• Menulis checkpoint JSON", 13, False, INK, FONT, 6)],
        [("• Menulis statistik & CSV", 13, False, INK, FONT, 6)],
        [("• Memproses pembaruan state dashboard", 13, False, INK, FONT, 0)],
    ])
    # Main process card
    x2 = x1 + col_w + gap
    rect(s, x2, 1.5, col_w, 4.6, fill=NAVY, line=None,
         shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    rect(s, x2, 1.5, col_w, 0.62, fill=NAVY_2)
    text(s, x2, 1.62, col_w, 0.5, [[("Main process", 15, True, WHITE, FONT, 0)]],
         align=PP_ALIGN.CENTER)
    text(s, x2 + 0.25, 2.3, col_w - 0.5, 3.6, [
        [("Koordinasi & konsistensi", 13, True, BLUE_L, FONT, 8)],
        [("• Mempertahankan state global", 13, False, ICE, FONT, 6)],
        [("• Menunggu seluruh worker selesai (barrier)", 13, False, ICE, FONT, 6)],
        [("• Menggabungkan hasil & memperbarui world", 13, False, ICE, FONT, 0)],
    ])
    text(s, MARGIN, 6.35, CONTENT_W, 0.4,
         [[("Catatan: MPI tidak digunakan dalam implementasi ini (eksekusi satu komputer).",
            12, True, GREY, FONT, 0)]])
    footer(s); page_number(s, 3)
    notes(s, "Jelaskan dua jenis beban kerja dan mengapa masing-masing dipetakan ke mekanisme berbeda. "
             "Tekankan GIL pada CPython sebagai alasan ProcessPool untuk kerja CPU Python.")


def slide_04_parameters(prs):
    s = blank(prs)
    title_bar(s, "Desain Sistem", "Parameter personal dari NIM 247006111139")
    cards = [
        ("1.390", "semut (ants)", BLUE),
        ("5", "thread I/O", GREEN),
        ("3", "worker proses CPU", BLUE),
        ("100 × 100", "grid simulasi", NAVY),
        ("10", "sumber makanan", AMBER),
        ("20", "obstacle", RED),
        ("247006111139", "seed (nilai NIM)", NAVY_2),
        ("100", "iterasi per benchmark", GREEN),
    ]
    cw = (CONTENT_W - 3 * 0.3) / 4
    ch = 1.5
    for i, (val, lab, col) in enumerate(cards):
        r, c = divmod(i, 4)
        x = MARGIN + c * (cw + 0.3)
        y = 1.55 + r * (ch + 0.35)
        stat_card(s, x, y, cw, ch, val, lab, value_color=col,
                  value_size=28 if len(val) < 8 else 20)
    text(s, MARGIN, 6.5, CONTENT_W, 0.4,
         [[("Konfigurasi maksimum 1.000 iterasi, kecuali dioverride melalui argumen runtime.",
            12, True, GREY, FONT, 0)]])
    footer(s); page_number(s, 4)
    notes(s, "Sebut asal parameter: thread=39 mod 4+2, process=61 mod 3+2, data=139×10. "
             "Tegaskan seed memakai nilai NIM untuk determinisme.")


def slide_05_architecture(prs):
    s = blank(prs)
    title_bar(s, "Arsitektur", "Alur satu iterasi: chunk → pool → barrier → merge")
    # main compute pipeline
    steps = ["Konfigurasi", "Snapshot World", "Ant Chunking", "ProcessPool\nWorkers",
             "Barrier", "Result Merge", "World Update"]
    bw = 1.62
    gap = 0.16
    y = 2.1
    x = MARGIN
    for i, st in enumerate(steps):
        col = BLUE if i not in (3, 4) else NAVY_2
        rect(s, x, y, bw, 0.95, fill=col, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        text(s, x, y + 0.12, bw, 0.75, [[(st, 11.5, True, WHITE, FONT, 0)]],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        if i < len(steps) - 1:
            c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x + bw), Inches(y + 0.47),
                                       Inches(x + bw + gap), Inches(y + 0.47))
            c.line.color.rgb = GREY; c.line.width = Pt(2)
        x += bw + gap
    # notes under pipeline
    text(s, MARGIN, 3.25, CONTENT_W, 1.0, [
        [("• Worker menghitung state lokal berdasarkan snapshot; tidak menulis world global.",
          13, False, INK, FONT, 6)],
        [("• Main process menunggu seluruh future (barrier), mengurutkan hasil dengan chunk_id.",
          13, False, INK, FONT, 6)],
        [("• State global diperbarui hanya setelah hasil lengkap diterima (merge deterministik).",
          13, False, INK, FONT, 0)],
    ])
    # I/O lane
    rect(s, MARGIN, 4.55, CONTENT_W, 0.5, fill=GREEN, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, MARGIN, 4.62, CONTENT_W, 0.4,
         [[("Jalur I/O paralel — ThreadPoolExecutor", 13, True, WHITE, FONT, 0)]],
         align=PP_ALIGN.CENTER)
    io = ["Checkpoint", "Statistik / CSV", "Pembaruan Dashboard"]
    iw = (CONTENT_W - 2 * 0.3) / 3
    for i, it in enumerate(io):
        xx = MARGIN + i * (iw + 0.3)
        rect(s, xx, 5.25, iw, 0.8, fill=GREY_L, line=GREEN, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        text(s, xx, 5.42, iw, 0.5, [[(it, 13, True, INK, FONT, 0)]], align=PP_ALIGN.CENTER)
        c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(xx + iw / 2), Inches(5.05),
                                   Inches(xx + iw / 2), Inches(5.25))
        c.line.color.rgb = GREEN; c.line.width = Pt(2)
    footer(s); page_number(s, 5)
    notes(s, "Telusuri alur satu iterasi dari kiri ke kanan. Tunjukkan bahwa jalur I/O berjalan "
             "paralel dan tidak memblokir komputasi CPU.")


def slide_06_implementation(prs):
    s = blank(prs)
    title_bar(s, "Implementasi", "Python, NumPy, dan dashboard runtime")
    text(s, MARGIN, 1.45, 5.9, 4.9, [
        [("Bahasa & pustaka", 14, True, BLUE, FONT, 6)],
        [("• Python 3.14.3 sebagai bahasa implementasi", 13, False, INK, FONT, 5)],
        [("• NumPy untuk grid makanan, obstacle, dan feromon", 13, False, INK, FONT, 5)],
        [("• concurrent.futures + multiprocessing (standard library)", 13, False, INK, FONT, 10)],
        [("Model agen semut", 14, True, BLUE, FONT, 6)],
        [("• Identitas, posisi, status membawa makanan, perilaku, path", 13, False, INK, FONT, 5)],
        [("• Probabilitas gerak dipengaruhi feromon + heuristik jarak", 13, False, INK, FONT, 5)],
        [("• Penguapan feromon mencegah jejak lama bertahan", 13, False, INK, FONT, 10)],
        [("Dashboard menampilkan peta simulasi, status/iterasi, jumlah semut & makanan, "
          "konfigurasi worker, serta metrik runtime.", 12.5, True, GREY, FONT, 0)],
    ])
    # real dashboard screenshot (Gambar 6)
    if DASHBOARD_SHOT.exists():
        im = Image.open(DASHBOARD_SHOT)
        ar = im.width / im.height
        box_h = 4.7
        box_w = box_h * ar
        max_w = 5.9
        if box_w > max_w:
            box_w = max_w
            box_h = box_w / ar
        x = MARGIN + 6.3 + (5.9 - box_w) / 2
        y = 1.5
        rect(s, x - 0.08, y - 0.08, box_w + 0.16, box_h + 0.16, fill=WHITE, line=ICE)
        s.shapes.add_picture(str(DASHBOARD_SHOT), Inches(x), Inches(y),
                             Inches(box_w), Inches(box_h))
        text(s, x - 0.08, y + box_h + 0.12, box_w + 0.16, 0.4,
             [[("Screenshot dashboard ANT WORLD (Gambar 6, laporan).", 11, False, GREY, FONT, 0)]],
             align=PP_ALIGN.CENTER)
    else:
        rect(s, MARGIN + 6.3, 1.5, 5.9, 4.7, fill=GREY_L, line=ICE,
             shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        text(s, MARGIN + 6.3, 3.4, 5.9, 0.8,
             [[("Screenshot dashboard tidak tersedia di lingkungan ini.", 13, True, GREY, FONT, 0)]],
             align=PP_ALIGN.CENTER)
    footer(s); page_number(s, 6)
    notes(s, "Tunjukkan screenshot dashboard asli dari laporan (Gambar 6). Ingatkan bahwa dashboard "
             "adalah visualisasi runtime; angka pembanding tetap Tabel 5.")


def slide_07_methodology(prs):
    s = blank(prs)
    title_bar(s, "Metodologi", "Benchmark berpasangan: serial vs hybrid")
    text(s, MARGIN, 1.45, CONTENT_W, 1.5, [
        [("• Membandingkan baseline serial dan mode hybrid pada setiap konfigurasi.", 13, False, INK, FONT, 6)],
        [("• Seed, jumlah semut, dan jumlah iterasi disamakan dalam setiap pasangan.", 13, False, INK, FONT, 6)],
        [("• Setiap konfigurasi berjalan 100 iterasi; batch dijalankan tanpa server dashboard aktif.", 13, False, INK, FONT, 6)],
        [("• Metrik: execution time, speedup, efficiency, throughput, dan determinisme.", 13, False, INK, FONT, 0)],
    ])
    # config table
    rows = [
        ("Konfigurasi", "Thread", "Process", "Semut", "Keterangan"),
        ("Personal", "5", "3", "1.390", "Acuan personal"),
        ("Variasi thread", "1", "3", "1.390", "Thread diubah; lainnya tetap"),
        ("Variasi process", "5", "2", "1.390", "Process diubah; lainnya tetap"),
        ("Variasi data", "5", "3", "500", "Data diubah; lainnya tetap"),
    ]
    tbl = s.shapes.add_table(len(rows), 5, Inches(MARGIN), Inches(3.35),
                             Inches(CONTENT_W), Inches(2.6)).table
    widths = [2.6, 1.4, 1.6, 1.6, 4.94]
    for i, w in enumerate(widths):
        tbl.columns[i].width = Inches(w)
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.text = val
            p = cell.text_frame.paragraphs[0]
            p.runs[0].font.size = Pt(12.5)
            p.runs[0].font.name = FONT
            if r == 0:
                p.runs[0].font.bold = True
                p.runs[0].font.color.rgb = WHITE
                cell.fill.solid(); cell.fill.fore_color.rgb = NAVY
            else:
                p.runs[0].font.color.rgb = INK
                cell.fill.solid()
                cell.fill.fore_color.rgb = WHITE if r % 2 else GREY_L
    footer(s); page_number(s, 7)
    notes(s, "Tekankan desain berpasangan dan bahwa setiap konfigurasi hanya dijalankan sekali, "
             "sehingga hasil bersifat observasional, bukan bukti signifikansi statistik.")


def slide_08_main_result(prs):
    s = blank(prs)
    title_bar(s, "Hasil Utama", "Konfigurasi personal: 5 thread, 3 process, 1.390 semut")
    # chart serial vs hybrid
    data = CategoryChartData()
    data.categories = ["Serial", "Hybrid"]
    data.add_series("Waktu (s)", (4.597952, 3.090437))
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(MARGIN), Inches(1.5),
                            Inches(6.2), Inches(4.9), data)
    ch = gf.chart
    ch.has_title = True
    ch.chart_title.text_frame.text = "Waktu eksekusi (detik)"
    ch.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(14)
    ch.chart_title.text_frame.paragraphs[0].runs[0].font.bold = True
    style_chart(ch, [NAVY, BLUE], show_values=True, number_format="0.0000")
    # metric cards
    cards = [("1,4878×", "Speedup", GREEN), ("49,59%", "Efficiency", BLUE),
             ("449,77", "Throughput (ants/s)", AMBER)]
    cw = (5.9 - 0) / 3
    for i, (v, l, col) in enumerate(cards):
        x = MARGIN + 6.5 + i * (cw + 0.0) + i * 0.08
        stat_card(s, x, 1.7, cw - 0.08, 1.5, v, l, value_color=col, value_size=24)
    text(s, MARGIN + 6.5, 3.5, 5.9, 2.9, [
        [("Waktu serial : 4,597952 s", 13, False, INK, FONT, 4)],
        [("Waktu hybrid : 3,090437 s", 13, False, INK, FONT, 10)],
        [("Interpretasi", 13, True, BLUE, FONT, 4)],
        [("Pada konfigurasi personal ini, hybrid mencatat waktu eksekusi lebih rendah "
          "dibandingkan baseline serial, menghasilkan speedup 1,4878×.", 13, False, INK, FONT, 6)],
        [("Catatan: food collected = 0 pada seluruh konfigurasi uji.", 12, True, GREY, FONT, 0)],
    ])
    footer(s); page_number(s, 8)
    notes(s, "Tunjukkan grafik batang serial vs hybrid dengan label nilai. Tegaskan angka berasal "
             "dari Tabel 5 laporan dan tidak diubah.")


def slide_09_four_configs(prs):
    s = blank(prs)
    title_bar(s, "Perbandingan", "Speedup empat konfigurasi benchmark")
    labels = ["5T–3P\n1.390", "1T–3P\n1.390", "5T–2P\n1.390", "5T–3P\n500"]
    speedups = [1.4878, 1.4896, 1.4060, 0.9190]
    data = CategoryChartData()
    data.categories = labels
    data.add_series("Speedup (×)", tuple(speedups))
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(MARGIN), Inches(1.5),
                            Inches(7.6), Inches(4.9), data)
    ch = gf.chart
    ch.has_title = True
    ch.chart_title.text_frame.text = "Speedup per konfigurasi (garis referensi = 1,0×)"
    ch.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(14)
    ch.chart_title.text_frame.paragraphs[0].runs[0].font.bold = True
    style_chart(ch, [BLUE, BLUE, BLUE, RED], show_values=True, number_format="0.0000")
    # reference line at 1.0 via a thin shape is unreliable; annotate instead
    text(s, MARGIN, 6.45, 7.6, 0.4,
         [[("Batang merah = speedup < 1,0× (hybrid lebih lambat).", 11.5, True, GREY, FONT, 0)]])
    text(s, MARGIN + 7.9, 1.7, 4.5, 4.8, [
        [("Nilai speedup", 14, True, BLUE, FONT, 8)],
        [("• 5T–3P–1.390 : 1,4878×", 13, False, INK, FONT, 5)],
        [("• 1T–3P–1.390 : 1,4896×", 13, False, INK, FONT, 5)],
        [("• 5T–2P–1.390 : 1,4060×", 13, False, INK, FONT, 5)],
        [("• 5T–3P–500 : 0,9190×", 13, True, RED, FONT, 12)],
        [("Interpretasi", 14, True, BLUE, FONT, 6)],
        [("Konfigurasi 500 semut menghasilkan speedup di bawah satu. Hybrid tidak selalu "
          "lebih cepat karena biaya koordinasi dapat mengurangi manfaat paralelisasi.",
          13, False, INK, FONT, 0)],
    ])
    footer(s); page_number(s, 9)
    notes(s, "Bandingkan keempat konfigurasi. Garis referensi speedup = 1,0× memisahkan yang lebih "
             "cepat dari yang lebih lambat daripada serial.")


def slide_10_bottleneck(prs):
    s = blank(prs)
    title_bar(s, "Analisis", "Bottleneck: mekanisme terlihat vs dampak terukur")
    # left column: mechanisms (design)
    rect(s, MARGIN, 1.5, 4.0, 5.0, fill=GREY_L, line=ICE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, MARGIN + 0.2, 1.65, 3.6, 4.7, [
        [("Terlihat dalam desain", 14, True, NAVY, FONT, 8)],
        [("• Serialization / pickling state semut", 12.5, False, INK, FONT, 5)],
        [("• Transfer snapshot world antarproses", 12.5, False, INK, FONT, 5)],
        [("• IPC (inter-process communication)", 12.5, False, INK, FONT, 5)],
        [("• Barrier menunggu worker paling lambat", 12.5, False, INK, FONT, 5)],
        [("• Merge serial di main process", 12.5, False, INK, FONT, 5)],
        [("• 3 worker pada 2 physical core / 4 logical", 12.5, False, INK, FONT, 5)],
        [("• Biaya checkpoint & I/O bergantung opsi run", 12.5, False, INK, FONT, 0)],
    ])
    # right column: measured status
    rect(s, MARGIN + 4.3, 1.5, CONTENT_W - 4.3, 5.0, fill=WHITE, line=ICE,
         shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, MARGIN + 4.5, 1.65, CONTENT_W - 4.7, 4.7, [
        [("Status bukti", 14, True, RED, FONT, 8)],
        [("• Pickling/IPC/transfer: pola ada di source; besar biaya perlu profiling.",
          12.5, False, INK, FONT, 6)],
        [("• Barrier: mekanisme eksplisit; worker tertinggal menahan iterasi.",
          12.5, False, INK, FONT, 6)],
        [("• Merge serial: proporsi waktu belum tersedia.", 12.5, False, INK, FONT, 6)],
        [("• CPU saturation: dapat menjadi faktor; perlu hasil aktual.", 12.5, False, INK, FONT, 6)],
        [("• Memori: potensi biaya transfer; penggunaan belum tercatat.", 12.5, False, INK, FONT, 6)],
        [("• I/O: waktu terpisah tidak tercatat di CSV benchmark.", 12.5, False, INK, FONT, 10)],
        [("Bukti terukur: pada 500 semut, speedup 0,9190× menunjukkan total biaya hybrid "
          "melebihi manfaat paralel untuk workload kecil.", 12.5, True, BLUE, FONT, 0)],
    ])
    footer(s); page_number(s, 10)
    notes(s, "Bedakan jelas mana yang terlihat dari desain dan mana yang belum diukur langsung. "
             "Jangan menyatakan komponen biaya tertentu sebagai penyebab tanpa profiling.")


def slide_11_conclusion(prs):
    s = blank(prs)
    title_bar(s, "Penutup Analisis", "Kesimpulan dan saran pengembangan")
    # conclusions
    rect(s, MARGIN, 1.5, CONTENT_W / 2 - 0.15, 5.0, fill=GREY_L, line=ICE,
         shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, MARGIN + 0.2, 1.65, CONTENT_W / 2 - 0.55, 4.7, [
        [("Kesimpulan", 15, True, NAVY, FONT, 8)],
        [("• ANT WORLD menerapkan hybrid computing pada satu komputer.", 12.5, False, INK, FONT, 5)],
        [("• ProcessPoolExecutor menangani komputasi semut (CPU-bound).", 12.5, False, INK, FONT, 5)],
        [("• ThreadPoolExecutor menangani pekerjaan I/O-bound.", 12.5, False, INK, FONT, 5)],
        [("• Konfigurasi personal memperoleh speedup 1,4878×.", 12.5, True, GREEN, FONT, 5)],
        [("• Workload 500 semut memperoleh speedup 0,9190×.", 12.5, True, RED, FONT, 5)],
        [("• Hasil serial dan hybrid deterministik cocok.", 12.5, False, INK, FONT, 5)],
        [("• Food collected = 0 pada seluruh konfigurasi uji.", 12.5, False, INK, FONT, 0)],
    ])
    # suggestions
    x2 = MARGIN + CONTENT_W / 2 + 0.15
    rect(s, x2, 1.5, CONTENT_W / 2 - 0.15, 5.0, fill=WHITE, line=ICE,
         shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, x2 + 0.2, 1.65, CONTENT_W / 2 - 0.55, 4.7, [
        [("Saran", 15, True, BLUE, FONT, 8)],
        [("• Ulangi benchmark untuk median & variasi waktu.", 12.5, False, INK, FONT, 5)],
        [("• Lakukan profiling sebelum optimasi.", 12.5, False, INK, FONT, 5)],
        [("• Evaluasi chunk size & biaya transfer snapshot.", 12.5, False, INK, FONT, 5)],
        [("• Pertimbangkan shared memory hanya bila terbukti bermanfaat.", 12.5, False, INK, FONT, 5)],
        [("• Gunakan MPI hanya bila simulasi benar-benar butuh multi-node.", 12.5, False, INK, FONT, 0)],
    ])
    footer(s); page_number(s, 11)
    notes(s, "Ringkas temuan utama dan langkah berikutnya. Tekankan pelajaran: paradigma paralel "
             "dipilih berdasarkan jenis beban dan biaya koordinasi, bukan jumlah worker semata.")


def slide_12_thanks(prs):
    s = blank(prs)
    rect(s, 0, 0, SW, SH, fill=NAVY)
    rect(s, 0, 0, 0.28, SH, fill=BLUE)
    text(s, MARGIN, 1.1, 7.4, 1.6, [
        [("TERIMA KASIH", 46, True, WHITE, FONT_H, 8)],
        [("Tanya Jawab", 22, False, BLUE_L, FONT, 0)],
    ])
    text(s, MARGIN, 3.3, 7.4, 3.2, [
        [("Ripki Maulana • NIM 247006111139", 14, True, ICE, FONT, 4)],
        [("Program Studi Informatika — Universitas Siliwangi — 2026", 12.5, False, ICE, FONT, 14)],
        [("Demo: antworld-production.up.railway.app", 12, False, BLUE_L, FONT, 2)],
        [("Sumber: github.com/ripkimaulana1210-del/AntWorld", 12, False, BLUE_L, FONT, 0)],
    ])
    # references panel
    rect(s, 7.9, 1.1, SW - 7.9 - MARGIN, 5.3, fill=NAVY_2, line=BLUE,
         shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, 8.15, 1.3, SW - 8.4 - MARGIN, 4.9, [
        [("Referensi inti", 14, True, WHITE, FONT, 8)],
        [("[1] Python Software Foundation — concurrent.futures.", 10.5, False, ICE, FONT, 5)],
        [("[2] Python Software Foundation — multiprocessing.", 10.5, False, ICE, FONT, 5)],
        [("[3] G. M. Amdahl (1967) — Validity of the Single Processor Approach.", 10.5, False, ICE, FONT, 5)],
        [("[4] Dorigo, Maniezzo, Colorni (1996) — Ant System.", 10.5, False, ICE, FONT, 5)],
        [("[5] P. S. Pacheco (2011) — An Introduction to Parallel Programming.", 10.5, False, ICE, FONT, 5)],
        [("[6] Python Software Foundation — threading.", 10.5, False, ICE, FONT, 5)],
        [("[7] Prodi Informatika Unsil — Naskah Soal UTS, 2026.", 10.5, False, ICE, FONT, 0)],
    ])
    notes(s, "Tutup presentasi. Buka sesi tanya jawab. Referensi mengikuti daftar pustaka laporan.")


# ---------------------------------------------------------------------------
def build():
    prs = Presentation()
    prs.slide_width = Inches(SW)
    prs.slide_height = Inches(SH)
    slide_01_cover(prs)
    slide_02_background(prs)
    slide_03_hybrid(prs)
    slide_04_parameters(prs)
    slide_05_architecture(prs)
    slide_06_implementation(prs)
    slide_07_methodology(prs)
    slide_08_main_result(prs)
    slide_09_four_configs(prs)
    slide_10_bottleneck(prs)
    slide_11_conclusion(prs)
    slide_12_thanks(prs)
    RESULTS.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUT_PPTX))
    n = len(prs.slides._sldIdLst)
    print(f"Wrote {OUT_PPTX} with {n} slides")


if __name__ == "__main__":
    build()
