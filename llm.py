import re

import ollama

import config
from config import OLLAMA_HOST, MODELS, WEB_MODEL, KEEP_ALIVE

client = ollama.Client(host=OLLAMA_HOST)

THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)

PROFILE_KEYS = ["nama", "panggilan", "hobi", "minat", "gaya_bicara", "pekerjaan"]

PROFILE_RULES = [
    ("nama", re.compile(
        r"\bnama (?:saya|aku|gue|gw) (?:adalah |itu )?([A-Za-z][A-Za-z'-]{1,30})", re.I)),
    ("panggilan", re.compile(
        r"\bpanggil (?:saya|aku|gue|gw) ([A-Za-z][A-Za-z'-]{1,30})", re.I)),
    ("hobi", re.compile(
        r"\b(?:hobi (?:saya|aku|gue|gw) (?:adalah )?|(?:saya|aku|gue|gw) suka )([^.!\n]{2,80})", re.I)),
    ("pekerjaan", re.compile(
        r"\b(?:saya|aku|gue|gw) (?:seorang |sebagai |kerja sebagai )([^.!\n]{2,40})", re.I)),
    ("gaya_bicara", re.compile(
        r"\b(?:bicara|ngomong|ngobrol)\b[^.!\n]{0,25}?\b(santai|formal|singkat|sopan)\b", re.I)),
]

# kata yang sering ikut tertangkap di ujung nilai hobi
HOBI_STOP = re.compile(
    r"\b(santai|formal|singkat|sopan|aja|ya|dong|deh|sih|lah)\b", re.IGNORECASE
)


def ping() -> bool:
    try:
        client.list()
        return True
    except Exception:
        return False


def strip_think(text: str) -> str:
    """Buang blok <think>...</think> jika model menghasilkannya."""
    return THINK_RE.sub("", text).lstrip()


def stream_chat(model: str, messages: list[dict]):
    """Generator yang mengembalikan potongan teks satu per satu."""
    stream = client.chat(
        model=model,
        messages=messages,
        stream=True,
        keep_alive=KEEP_ALIVE,
        options={"num_ctx": config.NUM_CTX, "temperature": 0.4},
    )
    for part in stream:
        chunk = part["message"]["content"]
        if chunk:
            yield chunk


def summarize(history: list[dict]) -> str:
    """Ringkas sesi hanya dari pesan pengguna, supaya jawaban model tidak ikut diulang."""
    user_lines = [m["content"][:300] for m in history if m["role"] == "user"]
    transcript = "\n".join(f"- {line}" for line in user_lines[-12:])
    if not transcript:
        return ""
    msgs = [
        {"role": "system", "content": (
            "Dari pesan pengguna berikut, tulis maksimal 2 kalimat dalam Bahasa Indonesia. "
            "Sebutkan nama pengguna jika disebut, serta hal penting yang ia ceritakan atau minta. "
            "Keluarkan hanya ringkasannya."
        )},
        {"role": "user", "content": transcript},
    ]
    res = client.chat(
        model=WEB_MODEL,
        messages=msgs,
        keep_alive=KEEP_ALIVE,
        options={"num_ctx": 2048, "temperature": 0.2},
    )
    return strip_think(res["message"]["content"]).strip()


def extract_rules(user_text: str) -> dict[str, str]:
    """Ekstraksi cepat dan pasti dengan pola kalimat umum."""
    found: dict[str, str] = {}
    for key, pattern in PROFILE_RULES:
        m = pattern.search(user_text)
        if not m:
            continue
        value = m.group(1).strip(" ,;:-")
        if key == "hobi":
            value = HOBI_STOP.split(value, 1)[0].strip(" ,;:-")
        if value:
            found[key] = value[:80]
    return found


def extract_profile(user_text: str) -> dict[str, str]:
    """Aturan regex dulu, lalu model kecil untuk fakta yang tidak tertangkap aturan."""
    found = extract_rules(user_text)
    msgs = [
        {"role": "system", "content": (
            "Dari pesan pengguna, ambil fakta pribadi tentang PENGGUNA saja. "
            "Tulis satu baris per fakta dengan format kunci: nilai. "
            f"Kunci yang boleh dipakai: {', '.join(PROFILE_KEYS)}. "
            "Jika tidak ada fakta pribadi, tulis hanya: kosong. "
            "Jangan menambah informasi yang tidak disebut pengguna."
        )},
        {"role": "user", "content": user_text[:1000]},
    ]
    try:
        res = client.chat(
            model=WEB_MODEL,
            messages=msgs,
            keep_alive=KEEP_ALIVE,
            options={"num_ctx": 1024, "temperature": 0.0, "num_predict": 80},
        )
        text = strip_think(res["message"]["content"])
        for line in text.splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.replace("*", "").strip().lower().replace(" ", "_").strip("-* ")
            value = value.strip()
            if key in PROFILE_KEYS and value and value.lower() != "kosong" and key not in found:
                found[key] = value[:80]
    except Exception:
        pass  # aturan regex tetap tersimpan walau model gagal
    return found
