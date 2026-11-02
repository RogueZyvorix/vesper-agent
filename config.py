import os

APP_NAME = "Vesper-Agent"
APP_VERSION = "0.6.0"

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Sesuaikan dengan output `ollama list`
MODELS = {
    "chat": "qwen2.5:1.5b",
    "homework": "qwen2.5:1.5b",
    "code": "deepseek-coder:1.3b",
}

# Model untuk jawaban dari hasil web, ringkasan sesi, dan ekstraksi profil.
WEB_MODEL = "qwen2.5:1.5b"

HISTORY_TURNS = 6       # jumlah pesan terakhir yang dikirim ulang ke model
KEEP_ALIVE = "3m"       # model Vesper dilepas 3 menit setelah jawaban terakhir (hanya untuk Vesper)
CACHE_TTL = 24 * 3600   # cache web 24 jam
SEARCH_RESULTS = 3      # jumlah hasil pencarian per query

# Mode performa. Diganti saat aplikasi berjalan dengan Ctrl+Tab.
PRESETS = {
    "biasa": {"NUM_CTX": 4096, "PAGE_CHARS": 2000},
    "game": {"NUM_CTX": 2048, "PAGE_CHARS": 1000},
}
PERF_MODE = "biasa"
NUM_CTX = PRESETS[PERF_MODE]["NUM_CTX"]
PAGE_CHARS = PRESETS[PERF_MODE]["PAGE_CHARS"]


def set_perf(name: str) -> bool:
    """Ganti mode performa saat aplikasi berjalan."""
    global PERF_MODE, NUM_CTX, PAGE_CHARS
    if name not in PRESETS:
        return False
    PERF_MODE = name
    NUM_CTX = PRESETS[name]["NUM_CTX"]
    PAGE_CHARS = PRESETS[name]["PAGE_CHARS"]
    return True


SYSTEM_PROMPT = (
    "Kamu adalah asisten AI bernama Vesper. Jawab dalam Bahasa Indonesia, "
    "singkat, dan sesuai konteks. Kamu BUKAN pengguna. Informasi tentang pengguna "
    "hanya berlaku untuk pengguna, jangan dikaitkan dengan dirimu. "
    "Jika tidak yakin, katakan tidak yakin."
)
