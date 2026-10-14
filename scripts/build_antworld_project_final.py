#!/usr/bin/env python3
"""ANT WORLD — Presentasi UTS, PROJECT-FINAL generator.

Project-focused revision. Derived from scripts/build_antworld_final.py (baseline
preserved). Design craft per the `presentation-craft` skill (one idea per slide,
assertion titles, hero the one thing, vary the form, no decorative filler). Scientific
accuracy per `scientific-slides`. Architecture per the ACTUAL source in src/ (validated:
persistent ProcessPoolExecutor, ThreadPoolExecutor I/O manager, barrier + chunk_id merge,
main-process world update, MPI unused).

PROJECT-FINAL changes (per-slide):
- S2: problem & goal framed for ANT WORLD.
- S3: verified features/components (grid, agents, food, obstacles, pheromone, decisions,
  status + runtime metrics).
- S5: two-lane hybrid architecture diagram (ProcessPool lane + ThreadPool lane) tied to
  main process, with coordination stage; MPI note.
- S7: implementation tied to code (Python, NumPy, concurrent.futures, multiprocessing).
- S10: evaluation separates measured / design-visible / needs-profiling; food=0 honesty.
- S11: development priorities (investigate food=0, functional tests, repeat, profile).
Data is verbatim from docs/Laporan_UTS_Hybrid_Computing_Ripki_Maulana.pdf (Table 5).
No invented figures or features.

Output: results/ANT_WORLD_Presentasi_UTS_PROJECT_FINAL.pptx
Run:    python scripts/build_antworld_project_final.py
"""
from __future__ import annotations

import os
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.util import Inches, Pt, Emu
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SHOT_DIR = Path(os.environ.get(
    "ANT_REPORT_IMAGES",
    r"C:\Users\Ace\AppData\Local\Temp\opencode\antworld_report\images"))
DASHBOARD_SHOT = SHOT_DIR / "dashboard_crop.png"
OUT_PPTX = RESULTS / "ANT_WORLD_Presentasi_UTS_PROJECT_FINAL.pptx"

# --- Palette (controlled navy/blue/white/grey; one red + one green accent) ---
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

FONT = "Calibri"
FONT_H = "Cambria"
SW, SH = 13.333, 7.5
M = 0.6
CW = SW - 2 * M

BENCH_PERSONAL = dict(threads=5, procs=3, ants=1390, ts=4.597952, th=3.090437,
                      sp=1.4878, eff=49.59, thr=449.77)


def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def rect(s, x, y, w, h, fill=None, line=None, shape=MSO_SHAPE.RECTANGLE, lw=1.0):
    sh = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line; sh.line.width = Pt(lw)
    sh.shadow.inherit = False
    return sh


def txt(s, x, y, w, h, paras, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
        wrap=True, spacing=None):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if spacing:
            p.line_spacing = spacing
        for (t, size, bold, color, font, sa) in para:
            r = p.add_run(); r.text = t
            r.font.size = Pt(size); r.font.bold = bold
            r.font.color.rgb = color; r.font.name = font
            if sa is not None:
                p.space_after = Pt(sa)
    return tb


def notes(s, t):
    s.notes_slide.notes_text_frame.text = t


def kicker_title(s, kicker, headline, sub=None):
    """Editorial title block (no full-width band): kicker + rule + assertion title."""
    txt(s, M, 0.42, CW, 0.3, [[(kicker.upper(), 11, True, BLUE, FONT, 0)]])
    rect(s, M, 0.78, 1.1, 0.035, fill=BLUE)  # short kicker rule, not a title underline
    txt(s, M, 0.92, CW, 1.0, [[(headline, 30, True, NAVY, FONT_H, 0)]], spacing=0.98)
    yy = 1.95
    if sub:
        txt(s, M, yy, CW, 0.4, [[(sub, 14, False, GREY, FONT, 0)]])
        yy += 0.5
    return yy


def footer(s, n):
    txt(s, M, SH - 0.42, 8.0, 0.3,
        [[("ANT WORLD — Hybrid Parallel Ant Colony Simulation", 8.5, False, GREY, FONT, 0)]])
    txt(s, SW - 1.0, SH - 0.42, 0.5, 0.3,
        [[(str(n), 10, True, GREY, FONT, 0)]], align=PP_ALIGN.RIGHT)


def trail_mark(s, x, y, w, color=None):
    if color is None:
        color = RGBColor(0xE0, 0x8A, 0x1E)
    """Signature motif: a pheromone-trail polyline (data-meaningful, used twice only)."""
    pts = [(0.00, 0.55), (0.18, 0.20), (0.36, 0.65), (0.55, 0.15), (0.74, 0.5), (1.0, 0.1)]
    prev = None
    for (fx, fy) in pts:
        px, py = x + fx * w, y + fy * 0.8
        if prev is not None:
            c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(prev[0]), Inches(prev[1]),
                                       Inches(px), Inches(py))
            c.line.color.rgb = color; c.line.width = Pt(2.25)
        prev = (px, py)
    for (fx, fy) in pts[1:-1]:
        rect(s, x + fx * w - 0.05, y + fy * 0.8 - 0.05, 0.1, 0.1, fill=color,
             shape=MSO_SHAPE.OVAL)


# --------------------------------------------------------------------------
# 1. COVER — full-bleed navy, single hero title + trail mark
# --------------------------------------------------------------------------
def s01(prs):
    s = blank(prs)
    rect(s, 0, 0, SW, SH, fill=NAVY)
    rect(s, 0, 0, 0.22, SH, fill=BLUE)                 # single quiet edge rule
    trail_mark(s, 8.3, 5.5, 4.2, BLUE_L)               # motif, once
    txt(s, 0.95, 3.15, 9.6, 0.5,
        [[("Ujian Tengah Semester — Komputasi Paralel dan Terdistribusi", 12.5, True, BLUE_L, FONT, 0)]])
    txt(s, 0.95, 1.55, 10.5, 2.6,
        [[("ANT WORLD", 58, True, WHITE, FONT_H, 4)],
         [("Hybrid Parallel Ant Colony Simulation", 24, True, ICE, FONT, 0)]])
    txt(s, 0.95, 3.75, 10.5, 0.5,
        [[("Hybrid Computing for Real-World Simulation and Data Processing", 14, False, BLUE_L, FONT, 0)]])
    txt(s, 0.95, 6.15, 11.4, 1.0,
        [[("Ripki Maulana  ·  NIM 247006111139", 15, True, WHITE, FONT, 3)],
         [("Program Studi Informatika — Universitas Siliwangi — 2026", 12, False, ICE, FONT, 0)]])
    notes(s, "Buka dengan satu kalimat: ini simulasi koloni semut, tapi pertanyaan sebenarnya "
             "adalah kapan paralelisme membayar biayanya. Sebut nama dan NIM.")


# --------------------------------------------------------------------------
# 2. LATAR BELAKANG — two-column: provocation left, Nest→Food→Nest loop right
# --------------------------------------------------------------------------
def s02(prs):
    s = blank(prs)
    y = kicker_title(s, "Masalah & tujuan",
                     "Keputusan agen bersifat lokal, biayanya global")
    # left: short provocation (not a wall)
    txt(s, M, y + 0.1, 5.5, 4.0, [
        [("ANT WORLD menyimulasikan koloni semut pada grid 2D: tiap agen memilih langkah "
          "dari feromon tetangga dan jarak ke sarang.", 14.5, False, INK, FONT, 11)],
        [("Tidak ada pengendali global; perilaku koloni muncul dari interaksi lokal "
          "(swarm intelligence).", 14.5, False, INK, FONT, 11)],
        [("Setiap iterasi menjalankan keputusan itu untuk 1.390 agen sekaligus — inilah "
          "beban komputasinya.", 14.5, False, INK, FONT, 11)],
        [("Tujuan: percepat simulasi iteratif ini tanpa mengubah hasil, sehingga pendekatan "
          "hybrid (proses + thread) dipilih.", 14.5, True, BLUE, FONT, 0)],
    ], spacing=1.02)
    # right: loop diagram Nest → Eksplorasi → Food → Nest (fits the 6.4in column)
    cx, cy = 7.0, y + 0.2
    nodes = [("Nest", 0.0, 0.0, GREEN), ("Eksplorasi", 1.9, 0.95, BLUE),
             ("Sumber makanan", 3.8, 0.0, RGBColor(0xE0, 0x8A, 0x1E))]
    placed = {}
    for (name, dx, dy, col) in nodes:
        bw, bh = 2.0, 0.85
        x, y2 = cx + dx, cy + dy
        rect(s, x, y2, bw, bh, fill=col, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        txt(s, x, y2 + 0.16, bw, 0.55, [[(name, 12.5, True, WHITE, FONT, 0)]],
            align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        placed[name] = (x, y2, bw, bh)
    # arrows: Nest->Eksplorasi->Food, Food->Nest (return, dashed)
    def arrow(x1, y1, x2, y2, col=GREY, dash=False):
        c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1),
                                   Inches(x2), Inches(y2))
        c.line.color.rgb = col; c.line.width = Pt(2)
        if dash:
            c.line.dash_style = 4
    nx, ny, nw, nh = placed["Nest"]
    ex, ey, ew, eh = placed["Eksplorasi"]
    fx, fy, fw, fh = placed["Sumber makanan"]
    arrow(nx + nw, ny + nh / 2, ex, ey + eh / 2)
    arrow(ex + ew, ey + eh / 2, fx, fy + fh / 2)
    arrow(fx + fw / 2, fy + fh, nx + nw / 2, ny + nh, col=GREEN, dash=True)
    txt(s, cx - 0.1, cy + 2.55, 6.0, 0.9,
        [[("Jalur penuh (garis putus-putus) = semut kembali membawa makanan. "
           "Feromon menandai rute yang berhasil.", 11.5, False, GREY, FONT, 0)]], spacing=0.98)
    footer(s, 2)
    notes(s, "Tekankan swarm intelligence: aturan lokal, pola global. Ini yang membuat "
             "simulasi berat komputasi tetapi dapat diparalelkan per-agen.")


# --------------------------------------------------------------------------
# 3. FITUR & KOMPONEN — verified against src/world.py, src/ant.py, src/simulation.py
# --------------------------------------------------------------------------
def s03(prs):
    s = blank(prs)
    y = kicker_title(s, "Fitur & komponen proyek",
                     "Apa yang benar-benar ada di ANT WORLD")
    # left: components (verified) as a labelled list, not cards
    txt(s, M, y + 0.1, 6.5, 0.35, [[("Komponen simulasi", 13, True, BLUE, FONT, 0)]])
    comps = [
        ("Grid 100 × 100", "food_grid (int), obstacle_grid (bool), pheromone_grid (float)"),
        ("Agen semut (1.390)", "id · posisi · membawa makanan · perilaku · path"),
        ("Sumber makanan / obstacle", "10 sumber, 20 obstacle, tidak menumpuk sarang"),
        ("Feromon", "deposit saat rute sukses; menguap tiap iterasi (decay)"),
        ("Keputusan gerak", "feromon × heuristik jarak ke sarang (α=1, β=2)"),
    ]
    ccy = y + 0.5
    for name, detail in comps:
        txt(s, M, ccy, 6.5, 0.28, [[(name, 12.5, True, NAVY, FONT, 0)]])
        txt(s, M, ccy + 0.28, 6.5, 0.3, [[(detail, 11.5, False, GREY, FONT, 0)]])
        ccy += 0.72
    # right: status + runtime metrics (from simulation.get_metrics)
    rx = M + 6.9
    rect(s, rx, y + 0.1, SW - M - rx, 3.8, fill=GREY_L, line=ICE,
         shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, rx + 0.25, y + 0.28, SW - M - rx - 0.5, 0.35,
        [[("Status & metrik runtime", 13, True, GREEN, FONT, 0)]])
    metrics = ["food_collected", "total_trips", "food_remaining",
               "avg_pheromone · max_pheromone", "ants_with_food",
               "status · iteration · path length"]
    myy = y + 0.75
    for m in metrics:
        txt(s, rx + 0.25, myy, SW - M - rx - 0.5, 0.35, [[("• " + m, 12, False, INK, FONT, 0)]])
        myy += 0.5
    txt(s, M, 6.1, CW, 0.5,
        [[("Semua komponen di atas diverifikasi terhadap kode sumber (src/world.py, src/ant.py, "
           "src/simulation.py), bukan asumsi.", 11.5, True, GREY, FONT, 0)]], spacing=0.98)
    footer(s, 3)
    notes(s, "Sebutkan komponen yang benar-benar ada di kode. Grid memakai NumPy; metrik runtime "
             "dibaca dari Simulation.get_metrics(). Jangan tambah fitur yang tidak ada.")


# --------------------------------------------------------------------------
# 4. PARAMETER — stat strip (one row) + grid thumbnail
# --------------------------------------------------------------------------
def s04(prs):
    s = blank(prs)
    y = kicker_title(s, "Parameter personal",
                     "Angka-angka ini berasal dari NIM, bukan dari selera",
                     sub="NIM 247006111139  →  thread = 39 mod 4 + 2, proses = 61 mod 3 + 2, data = 139 × 10")
    stats = [("1.390", "semut", BLUE), ("5", "thread I/O", GREEN),
             ("3", "worker proses", BLUE), ("100×100", "grid", NAVY)]
    sw = (CW - 3 * 0.4) / 4
    for i, (v, l, col) in enumerate(stats):
        x = M + i * (sw + 0.4)
        txt(s, x, y + 0.15, sw, 0.85, [[(v, 40, True, col, FONT_H, 0)]], align=PP_ALIGN.CENTER)
        txt(s, x, y + 1.0, sw, 0.4, [[(l, 13, False, GREY, FONT, 0)]], align=PP_ALIGN.CENTER)
        if i:
            rect(s, x - 0.2, y + 0.25, 0.012, 0.95, fill=ICE)
    # small grid thumbnail (conceptual, labelled as such)
    gy = y + 1.7
    gsize = 2.2
    gx = M
    rect(s, gx, gy, gsize, gsize, fill=WHITE, line=ICE)
    import random
    rng = random.Random(247006111139 % 1000)
    for _ in range(26):
        rect(s, gx + rng.random() * (gsize - 0.12), gy + rng.random() * (gsize - 0.12),
             0.12, 0.12, fill=GREY_L)
    rect(s, gx + gsize / 2 - 0.09, gy + gsize / 2 - 0.09, 0.18, 0.18, fill=GREEN)
    txt(s, gx, gy + gsize + 0.08, gsize, 0.4,
        [[("Grid 100×100 (ilustrasi konseptual)", 10, False, GREY, FONT, 0)]])
    # config table beside it
    items = [("Seed", "247006111139"), ("Sumber makanan", "10"), ("Obstacle", "20"),
             ("Iterasi benchmark", "100"), ("Maks. iterasi config", "1.000 (override CLI)"),
             ("Pheromone decay / deposit", "0,1 / 10,0"), ("Alpha / beta", "1,0 / 2,0")]
    tx = gx + gsize + 0.6
    txt(s, tx, gy - 0.05, CW - gsize - 0.6, 0.4, [[("Konfigurasi lain", 13, True, BLUE, FONT, 0)]])
    yy = gy + 0.42
    for k, v in items:
        txt(s, tx, yy, 4.3, 0.34, [[(k, 12.5, False, GREY, FONT, 0)]])
        txt(s, tx + 4.4, yy, 3.2, 0.34, [[(v, 12.5, True, INK, FONT, 0)]], align=PP_ALIGN.RIGHT)
        yy += 0.42
    footer(s, 4)
    notes(s, "Tunjukkan parameter unik dari NIM dan bahwa seed memakai nilai NIM untuk "
             "determinisme antara serial dan hybrid.")


# --------------------------------------------------------------------------
# 5. ARSITEKTUR — two-lane hybrid diagram (ProcessPool + ThreadPool) per soal UTS
# --------------------------------------------------------------------------
def s05(prs):
    s = blank(prs)
    y = kicker_title(s, "Arsitektur hybrid computing",
                     "Dua jalur: ProcessPool (CPU) + ThreadPool (I/O), satu main process")
    # --- Main process band on top ---
    mp_y = y - 0.02
    rect(s, M, mp_y, CW, 0.72, fill=NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, M + 0.25, mp_y + 0.02, 6.6, 0.32,
        [[("Main process — ANT WORLD", 13, True, WHITE, FONT, 0)]])
    txt(s, M + 0.25, mp_y + 0.36, 12.0, 0.3,
        [[("Pegang state global (world + 1.390 semut) · bangun snapshot grid · bagi ant jadi chunk · "
           "terapkan world update", 11, False, ICE, FONT, 0)]])
    # --- two lanes ---
    lane_y = mp_y + 0.92
    lane_h = 3.05
    lane_w = (CW - 0.6) / 2
    # Lane A: ProcessPool (left, blue/navy)
    ax = M
    rect(s, ax, lane_y, lane_w, lane_h, fill=WHITE, line=BLUE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    rect(s, ax, lane_y, lane_w, 0.52, fill=BLUE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, ax + 0.2, lane_y + 0.08, lane_w - 0.4, 0.4,
        [[("Jalur A — ProcessPoolExecutor   (CPU-bound)", 12.5, True, WHITE, FONT, 0)]])
    a_rows = [
        "Menerima chunk state semut + snapshot world",
        "Menghitung keputusan/pergerakan semut (bytecode Python)",
        "GIL: proses punya interpreter sendiri → paralel sejati",
        "Mengembalikan hasil lokal (posisi, event) ke main process",
    ]
    ry2 = lane_y + 0.72
    for r in a_rows:
        txt(s, ax + 0.22, ry2, lane_w - 0.44, 0.5, [[("• " + r, 11.5, False, INK, FONT, 0)]],
            spacing=0.98)
        ry2 += 0.55
    # Lane B: ThreadPool (right, green)
    bx = M + lane_w + 0.6
    rect(s, bx, lane_y, lane_w, lane_h, fill=WHITE, line=GREEN, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    rect(s, bx, lane_y, lane_w, 0.52, fill=GREEN, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, bx + 0.2, lane_y + 0.08, lane_w - 0.4, 0.4,
        [[("Jalur B — ThreadPoolExecutor   (I/O-bound)", 12.5, True, WHITE, FONT, 0)]])
    b_rows = [
        "Checkpoint JSON · statistik JSON · CSV hasil benchmark",
        "Pembaruan state dashboard (submit, ditunggu saat perlu)",
        "Dikirim sebagai future; tidak menunggu sendiri saat antre",
        "Thread berbagi satu proses → ringan untuk kerja menunggu",
    ]
    ry2 = lane_y + 0.72
    for r in b_rows:
        txt(s, bx + 0.22, ry2, lane_w - 0.44, 0.5, [[("• " + r, 11.5, False, INK, FONT, 0)]],
            spacing=0.98)
        ry2 += 0.55
    # arrows from main process down into both lanes
    for cx in (ax + lane_w / 2, bx + lane_w / 2):
        c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(cx), Inches(mp_y + 0.72),
                                   Inches(cx), Inches(lane_y))
        c.line.color.rgb = GREY; c.line.width = Pt(2)
    # --- coordination strip ---
    cy = lane_y + lane_h + 0.16
    rect(s, M, cy, CW, 0.6, fill=GREY_L, line=ICE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, M + 0.25, cy + 0.08, CW - 0.5, 0.45,
        [[("Koordinasi main process:  snapshot → chunk → submit ke ProcessPool → ",
           11.5, True, NAVY, FONT, 0)],
         [("barrier (tunggu semua future) → urutkan per chunk_id → merge deterministik → world update → iterasi berikutnya",
           11.5, True, NAVY, FONT, 0)]], spacing=0.98)
    txt(s, M, cy + 0.68, CW, 0.35,
        [[("MPI tidak digunakan — eksperimen berjalan pada satu komputer (tidak ada node/rank).",
           11.5, True, RED, FONT, 0)]])
    footer(s, 5)
    notes(s, "Ini jawaban Bagian A UTS: tunjukkan DUA jalur. Proses = kerja CPU (gerak semut), "
             "thread = kerja I/O (checkpoint/stats/dashboard). Main process memegang state global, "
             "barrier, merge, world update. MPI tidak dipakai. Diagram dicocokkan dengan src/parallel.py "
             "dan src/io_tasks.py.")


# --------------------------------------------------------------------------
# 6. IMPLEMENTASI — half-bleed real screenshot left, 3 tight points right
# --------------------------------------------------------------------------
def s06(prs):
    s = blank(prs)
    # full-height left bleed image
    if DASHBOARD_SHOT.exists():
        im = Image.open(DASHBOARD_SHOT)
        ar = im.width / im.height
        pane_w = 6.4
        pane_h = SH
        img_h = pane_h
        img_w = img_h * ar
        if img_w > pane_w:
            img_w = pane_w; img_h = img_w / ar
        ix = 0.0
        iy = (pane_h - img_h) / 2
        s.shapes.add_picture(str(DASHBOARD_SHOT), Inches(ix), Inches(iy),
                             Inches(img_w), Inches(img_h))
        # label over the bottom of the image
        rect(s, 0, SH - 0.7, img_w, 0.7, fill=NAVY)
        txt(s, 0.25, SH - 0.6, img_w - 0.5, 0.45,
            [[("Dashboard ANT WORLD — screenshot asli (laporan, Gambar 6)", 11, True, ICE, FONT, 0)]],
            anchor=MSO_ANCHOR.MIDDLE)
    # right column
    rx = 6.9
    txt(s, rx, 0.55, SW - rx - M, 0.3, [[("Dashboard ANT WORLD", 11, True, BLUE, FONT, 0)]])
    rect(s, rx, 0.9, 1.1, 0.035, fill=BLUE)
    txt(s, rx, 1.05, SW - rx - M, 1.0,
        [[("Yang bisa diamati saat runtime", 26, True, NAVY, FONT_H, 0)]], spacing=0.98)
    pts = [("Peta simulasi",
            "Grid, posisi semut, feromon, sumber makanan, dan sarang ditampilkan pada canvas, "
            "dengan legenda serta opsi layer."),
           ("Panel status & objek",
            "Status/iterasi, jumlah semut, makanan tersedia/terkumpul, dan panjang lintasan."),
           ("Panel hybrid computing",
            "Menampilkan pembagian tugas I/O-bound dan CPU-bound, jumlah thread/process, "
            "data, dan seed."),
           ("Telemetry performa",
            "Execution time, throughput, speedup, dan efficiency untuk sesi yang berjalan.")]
    py = 2.15
    for t, d in pts:
        rect(s, rx, py, 0.06, 0.5, fill=BLUE)
        txt(s, rx + 0.25, py - 0.02, SW - rx - M - 0.25, 0.3, [[(t, 12.5, True, BLUE, FONT, 0)]])
        txt(s, rx + 0.25, py + 0.26, SW - rx - M - 0.25, 0.6,
            [[(d, 11.5, False, INK, FONT, 0)]], spacing=0.95)
        py += 1.05
    footer(s, 6)
    notes(s, "Screenshot dashboard ASLI dari laporan (Gambar 6), bukan hasil palsu atau ilustrasi. "
             "Jelaskan apa yang bisa diamati: peta, status, panel hybrid, telemetry. Dashboard = "
             "visualisasi runtime; angka pembanding tetap Tabel 5.")


# --------------------------------------------------------------------------
# 7. IMPLEMENTASI TEKNIS — each technology tied to its role in the project
# --------------------------------------------------------------------------
def s07(prs):
    s = blank(prs)
    y = kicker_title(s, "Implementasi teknis",
                     "Setiap teknologi dan perannya di ANT WORLD")
    rows = [
        ("Python 3.14.3", "Bahasa implementasi seluruh proyek.", NAVY),
        ("NumPy", "Grid world: makanan (int), obstacle (bool), feromon (float); "
                  "vektor posisi & operasi metrik.", BLUE),
        ("concurrent.futures — ProcessPoolExecutor", "Worker CPU-bound: gerak & keputusan semut "
                  "(src/parallel.py, worker_step_ants).", BLUE),
        ("concurrent.futures — ThreadPoolExecutor", "Tugas I/O: checkpoint JSON, statistik, CSV, "
                  "state dashboard (src/io_tasks.py).", GREEN),
        ("multiprocessing (via ProcessPool)", "Proses terpisah = interpreter & GIL sendiri → "
                  "paralelisme CPU sejati.", BLUE),
        ("matplotlib / pandas", "Pembuat grafik benchmark dan tabel hasil (scripts/benchmark.py).", GREY),
    ]
    ry = y + 0.15
    for name, role, col in rows:
        rect(s, M, ry, 0.08, 0.66, fill=col)
        txt(s, M + 0.28, ry - 0.02, 5.7, 0.34, [[(name, 13, True, col, FONT, 0)]])
        txt(s, M + 6.0, ry + 0.02, CW - 6.0, 0.6, [[(role, 12, False, INK, FONT, 0)]],
            spacing=0.95)
        ry += 0.78
    txt(s, M, ry + 0.02, CW, 0.4,
        [[("Tidak ada teknologi yang dipakai tanpa peran nyata di kode; daftar ini memetakan "
           "setiap pustaka ke fungsinya.", 11.5, True, GREY, FONT, 0)]])
    footer(s, 7)
    notes(s, "Hubungkan tiap teknologi dengan fungsinya: Python bahasa utama; NumPy grid; "
             "ProcessPoolExecutor kerja CPU; ThreadPoolExecutor kerja I/O; multiprocessing "
             "memberi GIL terpisah; matplotlib/pandas untuk grafik benchmark.")


# --------------------------------------------------------------------------
# 8. HASIL UTAMA — hero number + single chart (one metric dominates)
# --------------------------------------------------------------------------
def s08(prs):
    s = blank(prs)
    y = kicker_title(s, "Hasil utama",
                     "Pada konfigurasi personal, hybrid menyelesaikan lebih cepat")
    # hero number
    txt(s, M, y + 0.05, 4.6, 1.3, [[("1,4878×", 66, True, GREEN, FONT_H, 0)]])
    txt(s, M, y + 1.35, 4.6, 0.5, [[("speedup  (T_serial / T_hybrid)", 13, False, GREY, FONT, 0)]])
    txt(s, M, y + 2.0, 4.6, 1.8, [
        [("Serial", 12.5, False, GREY, FONT, 2)],
        [("4,597952 s", 20, True, NAVY, FONT_H, 12)],
        [("Hybrid", 12.5, False, GREY, FONT, 2)],
        [("3,090437 s", 20, True, BLUE, FONT_H, 0)],
    ])
    # chart: serial vs hybrid bars, direct labels
    data = CategoryChartData()
    data.categories = ["Serial", "Hybrid"]
    data.add_series("Waktu (s)", (4.597952, 3.090437))
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(5.4), Inches(y),
                            Inches(SW - M - 5.4), Inches(4.6), data)
    ch = gf.chart
    ch.has_title = False
    ch.has_legend = False
    srs = ch.plots[0].series[0]
    srs.format.fill.solid(); srs.format.fill.fore_color.rgb = NAVY
    srs.has_data_labels = True
    dl = srs.data_labels
    dl.number_format = "0.000000"; dl.number_format_is_linked = False
    dl.font.size = Pt(15); dl.font.bold = True; dl.font.color.rgb = NAVY
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    ch.value_axis.has_major_gridlines = False
    ch.value_axis.maximum_scale = 6.0
    # caption with remaining metrics
    txt(s, 5.4, y + 4.55, SW - M - 5.4, 1.0,
        [[("Efisiensi 49,59%  ·  Throughput 449,77 ants/s  ·  Food collected = 0 pada semua konfigurasi uji.",
           12.5, False, GREY, FONT, 6)],
         [("Catatan: speedup ini perbandingan performa, bukan bukti simulasi berjalan benar secara fungsional.",
           11.5, True, GREY, FONT, 0)]], spacing=0.98)
    footer(s, 8)
    notes(s, "Angka dari Tabel 5, tidak diubah. Hybrid lebih cepat di konfigurasi personal ini.")


# --------------------------------------------------------------------------
# 9. EMPAT KONFIGURASI — bar chart, insight colored, 1.0x reference line
# --------------------------------------------------------------------------
def s09(prs):
    s = blank(prs)
    y = kicker_title(s, "Perbandingan",
                     "Menambah skala mengubah jawabannya")
    labels = ["5T·3P\n1.390", "1T·3P\n1.390", "5T·2P\n1.390", "5T·3P\n500"]
    data = CategoryChartData()
    data.categories = labels
    data.add_series("Speedup ≥ 1,0×", (1.4878, 1.4896, 1.4060, None))
    data.add_series("Speedup < 1,0×", (None, None, None, 0.9190))
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(M), Inches(y + 0.05),
                            Inches(7.0), Inches(4.2), data)
    ch = gf.chart
    ch.has_title = False
    ch.plots[0].series[0].format.fill.solid(); ch.plots[0].series[0].format.fill.fore_color.rgb = BLUE
    ch.plots[0].series[1].format.fill.solid(); ch.plots[0].series[1].format.fill.fore_color.rgb = RED
    for srs in ch.plots[0].series:
        srs.has_data_labels = True
        d = srs.data_labels
        d.number_format = "0.0000"; d.number_format_is_linked = False
        d.font.size = Pt(12); d.font.bold = True; d.font.color.rgb = INK
        try:
            d.position = XL_LABEL_POSITION.OUTSIDE_END
        except Exception:
            pass
    ch.has_legend = True
    ch.legend.position = XL_LEGEND_POSITION.BOTTOM
    ch.legend.include_in_layout = False
    ch.font.size = Pt(11); ch.font.name = FONT
    try:
        ch.value_axis.maximum_scale = 1.7; ch.value_axis.minimum_scale = 0.0
        ch.value_axis.has_major_gridlines = False
    except Exception:
        pass
    # reference line at 1.0 (dashed)
    fx, fy, fw, fh = M, y + 0.05, 7.0, 4.2
    plot_x, plot_w = fx + 0.6, fw - 0.75
    plot_top, plot_bottom = fy + 0.4, fy + 3.4
    yline = plot_bottom - (1.0 / 1.7) * (plot_bottom - plot_top)
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(plot_x), Inches(yline),
                               Inches(plot_x + plot_w), Inches(yline))
    c.line.color.rgb = GREY; c.line.width = Pt(1.5); c.line.dash_style = 4
    txt(s, plot_x + plot_w - 0.85, yline - 0.3, 0.85, 0.3,
        [[("1,0×", 11, True, GREY, FONT, 0)]], align=PP_ALIGN.RIGHT)
    # right column: full four-configuration data table (soal requires all rows)
    rx = M + 7.35
    txt(s, rx, y + 0.05, SW - M - rx, 0.3, [[("Data lengkap (Tabel 5)", 12, True, BLUE, FONT, 0)]])
    tbl_rows = [
        ("Konfigurasi", "Serial", "Hybrid", "Speedup"),
        ("5T·3P·1.390", "4,597952", "3,090437", "1,4878×"),
        ("1T·3P·1.390", "4,668423", "3,134073", "1,4896×"),
        ("5T·2P·1.390", "4,944367", "3,516699", "1,4060×"),
        ("5T·3P·500", "1,982886", "2,157669", "0,9190×"),
    ]
    tw = SW - M - rx
    tbl = s.shapes.add_table(len(tbl_rows), 4, Inches(rx), Inches(y + 0.4),
                             Inches(tw), Inches(2.35)).table
    for ci, cw in enumerate([1.45, 1.15, 1.15, 1.0]):
        tbl.columns[ci].width = Inches(cw)
    for r, row in enumerate(tbl_rows):
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.text = val
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.runs[0].font.size = Pt(10)
            p.runs[0].font.name = FONT
            if r == 0:
                p.runs[0].font.bold = True; p.runs[0].font.color.rgb = WHITE
                cell.fill.solid(); cell.fill.fore_color.rgb = NAVY
            else:
                p.runs[0].font.color.rgb = INK
                if c == 3:
                    p.runs[0].font.bold = True
                    p.runs[0].font.color.rgb = RED if r == 4 else GREEN
                cell.fill.solid()
                cell.fill.fore_color.rgb = WHITE if r % 2 else GREY_L
    txt(s, rx, y + 2.95, tw, 1.3,
        [[("Bacaan", 12, True, RED, FONT, 0)],
         [("500 semut → hybrid lebih lambat (0,9190×).", 12, False, INK, FONT, 6)],
         [("Tiga konfigurasi 1.390 semut tetap > 1,0×; speedup tidak linear.", 11.5, False, GREY, FONT, 0)]],
        spacing=0.98)
    footer(s, 9)
    notes(s, "Empat konfigurasi dari Tabel 5, semua angka ditampilkan. Batang merah = speedup < 1,0×. "
             "Garis putus-putus = ambang 1,0×. Tekankan skala kerja menentukan hasil.")


# --------------------------------------------------------------------------
# 10. EVALUASI PROYEK — measured vs design-visible vs needs-profiling
# --------------------------------------------------------------------------
def s10(prs):
    s = blank(prs)
    y = kicker_title(s, "Evaluasi proyek",
                     "Terukur, terlihat di desain, dan masih perlu profiling")
    colw = (CW - 0.6) / 3
    # Col 1: measured
    rect(s, M, y, colw, 3.85, fill=NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, M + 0.22, y + 0.2, colw - 0.44, 0.4, [[("Sudah diukur", 13.5, True, WHITE, FONT, 0)]])
    txt(s, M + 0.22, y + 0.72, colw - 0.44, 2.9, [
        [("Waktu serial & hybrid (Tabel 5)", 12, False, ICE, FONT, 9)],
        [("Speedup, efisiensi, throughput", 12, False, ICE, FONT, 9)],
        [("Kecocokan hasil serial vs hybrid", 12, False, ICE, FONT, 9)],
        [("500 semut → 0,9190× (lebih lambat)", 12, True, BLUE_L, FONT, 0)],
    ], spacing=1.0)
    # Col 2: design-visible
    x2 = M + colw + 0.3
    rect(s, x2, y, colw, 3.85, fill=GREY_L, line=ICE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, x2 + 0.22, y + 0.2, colw - 0.44, 0.4, [[("Terlihat di desain", 13.5, True, NAVY, FONT, 0)]])
    txt(s, x2 + 0.22, y + 0.72, colw - 0.44, 2.9, [
        [("Pickling state semut & snapshot", 12, False, INK, FONT, 9)],
        [("IPC antarproses", 12, False, INK, FONT, 9)],
        [("Barrier menunggu worker terakhir", 12, False, INK, FONT, 9)],
        [("Merge serial di main process", 12, False, INK, FONT, 9)],
        [("3 worker pada 2 core / 4 logical", 12, False, INK, FONT, 0)],
    ], spacing=1.0)
    # Col 3: needs profiling
    x3 = x2 + colw + 0.3
    rect(s, x3, y, colw, 3.85, fill=WHITE, line=ICE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, x3 + 0.22, y + 0.2, colw - 0.44, 0.4, [[("Perlu profiling", 13.5, True, RED, FONT, 0)]])
    txt(s, x3 + 0.22, y + 0.72, colw - 0.44, 2.9, [
        [("Besar biaya pickling / IPC / transfer", 12, False, INK, FONT, 9)],
        [("Proporsi waktu merge", 12, False, INK, FONT, 9)],
        [("Waktu I/O terpisah", 12, False, INK, FONT, 9)],
        [("Penggunaan memori saat benchmark", 12, False, INK, FONT, 0)],
    ], spacing=1.0)
    rect(s, M, y + 4.02, CW, 0.66, fill=RED, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, M + 0.25, y + 4.12, CW - 0.5, 0.46,
        [[("Keterbatasan fungsional: Food collected = 0 di semua konfigurasi → belum ada perjalanan "
           "makanan yang selesai; perlu ditelusuri.", 11.5, True, WHITE, FONT, 0)]],
        anchor=MSO_ANCHOR.MIDDLE)
    footer(s, 10)
    notes(s, "Pisahkan tiga kolom: yang sudah diukur, yang terlihat di desain, dan yang masih perlu "
             "profiling. Jangan sebut bottleneck terbukti tanpa pengukuran. Food=0 = keterbatasan "
             "fungsional yang harus ditelusuri.")


# --------------------------------------------------------------------------
# 11. KESIMPULAN & PENGEMBANGAN — implemented / benchmark shows / limits / next
# --------------------------------------------------------------------------
def s11(prs):
    s = blank(prs)
    y = kicker_title(s, "Kesimpulan & pengembangan",
                     "Arsitektur jalan; manfaat tergantung ukuran kerja")
    pw = (CW - 0.5) / 2
    rect(s, M, y, pw, 3.9, fill=NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, M + 0.3, y + 0.25, pw - 0.6, 0.4, [[("Yang sudah dicapai", 14.5, True, WHITE, FONT, 0)]])
    txt(s, M + 0.3, y + 0.85, pw - 0.6, 2.9, [
        [("Hybrid computing berjalan: ProcessPool (CPU) + ThreadPool (I/O).", 12.5, False, ICE, FONT, 9)],
        [("Main process memegang state global; hasil deterministik.", 12.5, False, ICE, FONT, 9)],
        [("Personal 1.390 semut: 1,4878× (lebih cepat).", 12.5, True, GREEN, FONT, 9)],
        [("500 semut: 0,9190× (lebih lambat).", 12.5, True, RED, FONT, 9)],
        [("Keterbatasan: Food collected = 0; sekali ukur per konfigurasi.", 12.5, False, ICE, FONT, 0)],
    ], spacing=1.0)
    x2 = M + pw + 0.5
    rect(s, x2, y, pw, 3.9, fill=GREY_L, line=ICE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, x2 + 0.3, y + 0.25, pw - 0.6, 0.4, [[("Pengembangan berikutnya", 14.5, True, BLUE, FONT, 0)]])
    txt(s, x2 + 0.3, y + 0.85, pw - 0.6, 2.9, [
        [("1. Selidiki penyebab Food collected = 0.", 12.5, True, BLUE, FONT, 9)],
        [("2. Tambah uji fungsional pergerakan & pengumpulan makanan.", 12.5, False, INK, FONT, 9)],
        [("3. Ulangi benchmark beberapa kali untuk median & variasi.", 12.5, False, INK, FONT, 9)],
        [("4. Profiling sebelum optimasi lanjutan.", 12.5, False, INK, FONT, 0)],
    ], spacing=1.0)
    footer(s, 11)
    notes(s, "Sampaikan apa yang sudah dicapai, apa yang ditunjukkan benchmark, keterbatasan, dan "
             "langkah berikutnya. Prioritas utama: selidiki food=0, uji fungsional, ulangi benchmark, "
             "profiling. Jangan klaim selesai tanpa bukti.")


# --------------------------------------------------------------------------
# 12. PENUTUP — full-bleed navy + references
# --------------------------------------------------------------------------
def s12(prs):
    s = blank(prs)
    rect(s, 0, 0, SW, SH, fill=NAVY)
    rect(s, 0, 0, 0.22, SH, fill=BLUE)
    trail_mark(s, 0.9, 5.9, 3.6, BLUE_L)               # motif, second and last use
    txt(s, 0.95, 1.3, 6.6, 1.6, [
        [("Terima kasih", 46, True, WHITE, FONT_H, 8)],
        [("Tanya jawab", 20, False, BLUE_L, FONT, 0)]])
    txt(s, 0.95, 3.4, 6.6, 2.0, [
        [("Ripki Maulana · NIM 247006111139", 13.5, True, ICE, FONT, 5)],
        [("Program Studi Informatika — Universitas Siliwangi — 2026", 12, False, ICE, FONT, 14)],
        [("Demo: antworld-production.up.railway.app", 11.5, False, BLUE_L, FONT, 3)],
        [("Sumber: github.com/ripkimaulana1210-del/AntWorld", 11.5, False, BLUE_L, FONT, 0)]])
    rect(s, 7.7, 1.3, SW - 7.7 - M, 5.0, fill=NAVY_2, line=BLUE,
         shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, 7.95, 1.5, SW - 7.95 - M - 0.2, 4.6, [
        [("Referensi inti (IEEE)", 13.5, True, WHITE, FONT, 9)],
        [("[1] Python Software Foundation. concurrent.futures, Python 3 docs.", 11, False, ICE, FONT, 7)],
        [("[2] Python Software Foundation. multiprocessing, Python 3 docs.", 11, False, ICE, FONT, 7)],
        [("[3] Python Software Foundation. threading, Python 3 docs.", 11, False, ICE, FONT, 7)],
        [("[4] G. M. Amdahl, Validity of the Single Processor Approach, 1967.", 11, False, ICE, FONT, 7)],
        [("[5] Dorigo, Maniezzo & Colorni, Ant System, IEEE Trans. SMC-B, 1996.", 11, False, ICE, FONT, 7)],
        [("[6] P. S. Pacheco, An Introduction to Parallel Programming, 2011.", 11, False, ICE, FONT, 7)],
        [("[7] Prodi Informatika Unsil, Naskah Soal UTS, 2026.", 11, False, ICE, FONT, 0)],
    ], spacing=1.0)
    notes(s, "Tutup. Buka tanya jawab. Referensi mengikuti daftar pustaka laporan.")


# official Table 5 rows reused by slide 7 bars
BENCH_ALL = [
    ("Personal", 5, 3, 1390, 4.597952, 3.090437, 1.4878, 49.59, 449.77),
    ("Variasi thread", 1, 3, 1390, 4.668423, 3.134073, 1.4896, 49.65, 443.51),
    ("Variasi process", 5, 2, 1390, 4.944367, 3.516699, 1.4060, 70.30, 395.26),
    ("Variasi data", 5, 3, 500, 1.982886, 2.157669, 0.9190, 30.63, 231.73),
]


def build():
    prs = Presentation()
    prs.slide_width = Inches(SW)
    prs.slide_height = Inches(SH)
    for fn in (s01, s02, s03, s04, s05, s06, s07, s08, s09, s10, s11, s12):
        fn(prs)
    RESULTS.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUT_PPTX))
    print(f"Wrote {OUT_PPTX} with {len(prs.slides._sldIdLst)} slides")


if __name__ == "__main__":
    build()
