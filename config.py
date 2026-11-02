import json
import os
from pathlib import Path

APP_NAME = "Vesper-Agent"
APP_VERSION = "0.7.0"

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

HOME = Path(os.getenv("LOCALAGENT_HOME", Path.home() / ".localagent"))
SETTINGS_PATH = HOME / "settings.json"

# Peran dan model awal. Bisa diganti lewat /model, dan pilihannya disimpan di settings.json.
ROLES = ("chat", "homework", "code", "web")
DEFAULT_MODELS = {
    "chat": "qwen2.5:1.5b",
    "homework": "qwen2.5:1.5b",
    "code": "deepseek-coder:1.3b",
    "web": "qwen2.5:1.5b",
}


def _load_models() -> dict[str, str]:
    models = dict(DEFAULT_MODELS)
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        saved = data.get("models", {}) if isinstance(data, dict) else {}
        for role in ROLES:
            name = saved.get(role)
            if isinstance(name, str) and name.strip():
                models[role] = name.strip()
    except (OSError, ValueError):
        pass  # file belum ada atau rusak: pakai default
    return models


MODELS = _load_models()


def save_model(role: str, name: str) -> None:
    """Ubah model untuk satu peran dan simpan ke settings.json."""
    if role not in ROLES:
        raise ValueError(f"peran tidak dikenal: {role}")
    MODELS[role] = name
    HOME.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps({"models": MODELS}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


HISTORY_TURNS = 6       # jumlah pesan terakhir yang dikirim ulang ke model
KEEP_ALIVE = "3m"       # model Vesper dilepas 3 menit setelah jawaban terakhir (hanya untuk Vesper)
CACHE_TTL = 24 * 3600   # cache web 24 jam
SEARCH_RESULTS = 3      # jumlah hasil pencarian per query

# Mode performa. Diganti saat aplikasi berjalan dengan Ctrl+G.
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
