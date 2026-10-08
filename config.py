"""
Konfigurasi proyek berdasarkan NIM 247006111139
"""

# Parameter yang diturunkan dari NIM
NIM = 247006111139
THREADS = 39 % 4 + 2  # 5 threads untuk I/O
PROCESSES = 61 % 3 + 2  # 3 processes untuk CPU-bound tasks
ANTS = 139 * 10  # 1390 semut
SEED = 247006111139  # Seed untuk deterministic comparison (exact NIM value)
NAMA_MAHASISWA = "Ripki Maulana"

# Konfigurasi World
WORLD_WIDTH = 100
WORLD_HEIGHT = 100
FOOD_SOURCES = 10
OBSTACLES = 20
NEST_POSITION = (50, 50)

# Konfigurasi Simulasi
MAX_ITERATIONS = 1000
PHEROMONE_DECAY = 0.1
PHEROMONE_DEPOSIT = 10.0
ALPHA = 1.0  # Pheromone importance
BETA = 2.0   # Distance importance

# Konfigurasi Checkpoint
CHECKPOINT_INTERVAL = 100
STATS_INTERVAL = 50
DASHBOARD_UPDATE_INTERVAL = 10

# Konfigurasi Dashboard Server
DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 8080
