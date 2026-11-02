import json
import re
from datetime import date

import httpx
from bs4 import BeautifulSoup

try:
    from ddgs import DDGS
except ImportError:  # paket lama
    from duckduckgo_search import DDGS

from config import CACHE_TTL, SEARCH_RESULTS, PAGE_CHARS
from memory import Memory

UA = {"User-Agent": "Mozilla/5.0 (Vesper-Agent)"}

# Kata perintah yang tidak membantu mesin pencari
FILLER = re.compile(
    r"\b(carikan|cari|tolong|tlg|tampilkan|tunjukkan|apa|saja|dong|ya|tentang|kah)\b",
    re.IGNORECASE,
)


def clean_query(q: str) -> str:
    """Buang kata perintah dan ganti 'hari ini' dengan tanggal."""
    q = FILLER.sub(" ", q)
    if re.search(r"hari ini", q, re.IGNORECASE):
        q = re.sub(r"hari ini", " ", q, flags=re.IGNORECASE)
        q = f"{' '.join(q.split())} {date.today():%d %B %Y}"
    q = " ".join(q.split())
    return q or "berita terbaru"


def search(query: str, mem: Memory, n: int = SEARCH_RESULTS) -> tuple[list[dict], str]:
    """Return (hasil, sumber) dengan sumber = 'web' | 'cache' | 'gagal'."""
    q = clean_query(query)
    key = f"search:{q.lower()}"
    try:
        with DDGS() as ddgs:
            results = [
                {"title": r["title"], "url": r["href"], "body": r["body"]}
                for r in ddgs.text(q, max_results=n)
            ]
        if results:
            mem.cache_put(key, json.dumps(results))
            return results, "web"
    except Exception:
        pass
    cached = mem.cache_get_any(key)
    if cached:
        return json.loads(cached), "cache"
    return [], "gagal"


def fetch_text(url: str, mem: Memory, max_chars: int = PAGE_CHARS) -> str:
    key = f"page:{url}"
    cached = mem.cache_get(key, CACHE_TTL)
    if cached:
        return cached[:max_chars]
    try:
        r = httpx.get(url, headers=UA, timeout=8, follow_redirects=True)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()
        text = " ".join(soup.get_text(" ").split())
        mem.cache_put(key, text[:5000])
        return text[:max_chars]
    except Exception:
        fallback = mem.cache_get_any(key)
        return fallback[:max_chars] if fallback else ""


def web_context(query: str, mem: Memory) -> tuple[str, str, list[str], str]:
    """Return (konteks, status, daftar_url, kueri_yang_dipakai)."""
    q = clean_query(query)
    results, source = search(query, mem)
    if not results:
        return "", "tidak tersedia", [], q
    parts = []
    for r in results:
        body = fetch_text(r["url"], mem) or r["body"]
        parts.append(f"[{r['title']}]\n{body}")
    status = "online" if source == "web" else "cache (offline)"
    return "\n\n".join(parts), status, [r["url"] for r in results], q
