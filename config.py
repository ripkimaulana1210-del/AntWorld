"""
Konfigurasi proyek berdasarkan NIM 247006111139
"""

import os

# Parameter yang diturunkan dari NIM (dapat dioverride via environment variable)
NIM = int(os.environ.get("NIM", 247006111139))
THREADS = int(os.environ.get("THREADS", 39 % 4 + 2))  # 5 threads untuk I/O
PROCESSES = int(os.environ.get("PROCESSES", 61 % 3 + 2))  # 3 processes untuk CPU-bound tasks
ANTS = int(os.environ.get("ANTS", 139 * 10))  # 1390 semut
SEED = int(os.environ.get("SEED", 247006111139))  # Seed untuk deterministic comparison (exact NIM value)
NAMA_MAHASISWA = os.environ.get("NAMA_MAHASISWA", "Ripki Maulana")

# Konfigurasi World
WORLD_WIDTH = 100
WORLD_HEIGHT = 100
FOOD_SOURCES = 10
OBSTACLES = 20
NEST_POSITION = (50, 50)

# Konfigurasi Simulasi
MAX_ITERATIONS = int(os.environ.get("MAX_ITERATIONS", 1000))
PHEROMONE_DECAY = 0.1
PHEROMONE_DEPOSIT = 10.0
ALPHA = 1.0  # Pheromone importance
BETA = 2.0   # Distance importance

# Konfigurasi Checkpoint
CHECKPOINT_INTERVAL = 100
STATS_INTERVAL = 50
DASHBOARD_UPDATE_INTERVAL = 10

# Konfigurasi Dashboard Server (0.0.0.0 untuk Railway/container, fallback port 8080 untuk local)
DASHBOARD_HOST = os.environ.get("HOST", "0.0.0.0")
DASHBOARD_PORT = int(os.environ.get("PORT", 8080))
