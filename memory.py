import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path

HOME = Path(os.getenv("LOCALAGENT_HOME", Path.home() / ".localagent"))
DB_PATH = HOME / "agent.db"


class Memory:
    """Semua data disimpan lokal di satu file SQLite."""

    def __init__(self):
        HOME.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.con = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.con.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                started REAL,
                summary TEXT
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session TEXT,
                role TEXT,
                content TEXT,
                ts REAL
            );
            CREATE TABLE IF NOT EXISTS web_cache (
                key TEXT PRIMARY KEY,
                value TEXT,
                ts REAL
            );
            CREATE TABLE IF NOT EXISTS profile (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated REAL
            );
        """)
        try:
            self.con.execute("ALTER TABLE sessions ADD COLUMN title TEXT")
            self.con.commit()
        except sqlite3.OperationalError:
            pass  # kolom title sudah ada

        # sesi kosong dari pembukaan aplikasi sebelumnya tidak perlu disimpan
        self.con.execute(
            "DELETE FROM sessions WHERE NOT EXISTS "
            "(SELECT 1 FROM messages m WHERE m.session = sessions.id)"
        )
        self.con.commit()

        self.session = uuid.uuid4().hex[:8]
        self._exec(
            "INSERT INTO sessions (id, started) VALUES (?, ?)",
            (self.session, time.time()),
        )
        self.session_msgs = 0

    def _exec(self, sql: str, params: tuple = ()):
        with self.lock:
            self.con.execute(sql, params)
            self.con.commit()

    def _one(self, sql: str, params: tuple = ()):
        with self.lock:
            return self.con.execute(sql, params).fetchone()

    def _all(self, sql: str, params: tuple = ()):
        with self.lock:
            return self.con.execute(sql, params).fetchall()

    # ---- riwayat pesan ----
    def add(self, role: str, content: str):
        self._exec(
            "INSERT INTO messages (session, role, content, ts) VALUES (?, ?, ?, ?)",
            (self.session, role, content, time.time()),
        )
        if role == "user":
            self.session_msgs += 1

    def load_messages(self, session_id: str, limit: int = 40) -> list[tuple]:
        """Pesan sesi tertentu dalam urutan waktu: [(role, content), ...]."""
        rows = self._all(
            "SELECT role, content FROM messages WHERE session = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        )
        return list(reversed(rows))

    def clear_messages(self):
        self._exec("DELETE FROM messages WHERE session = ?", (self.session,))

    # ---- ringkasan lintas sesi ----
    def set_summary(self, summary: str):
        self._exec("UPDATE sessions SET summary = ? WHERE id = ?", (summary, self.session))

    def recent_summaries(self, n: int = 3) -> list[str]:
        rows = self._all(
            "SELECT summary FROM sessions WHERE summary IS NOT NULL AND summary != '' "
            "ORDER BY started DESC LIMIT ?",
            (n,),
        )
        return [r[0] for r in rows]

    def session_count(self) -> int:
        return self._one("SELECT COUNT(*) FROM sessions")[0]

    # ---- judul sesi ----
    def set_title(self, title: str):
        self._exec("UPDATE sessions SET title = ? WHERE id = ?", (title, self.session))

    def get_title(self) -> str | None:
        row = self._one("SELECT title FROM sessions WHERE id = ?", (self.session,))
        return row[0] if row else None

    # ---- pindah, buat, dan hapus sesi ----
    def resolve_session(self, query: str) -> str | None:
        """Cari sesi dari awalan ID atau sebagian judul. None jika tidak unik."""
        rows = self._all(
            "SELECT id FROM sessions WHERE id LIKE ? OR title LIKE ? LIMIT 2",
            (query + "%", "%" + query + "%"),
        )
        return rows[0][0] if len(rows) == 1 else None

    def last_session_id(self) -> str | None:
        """Sesi terakhir yang punya pesan, dipakai untuk `vesper -c`."""
        row = self._one(
            "SELECT s.id FROM sessions s "
            "WHERE EXISTS (SELECT 1 FROM messages m WHERE m.session = s.id) "
            "ORDER BY s.started DESC LIMIT 1"
        )
        return row[0] if row else None

    def list_sessions(self, n: int = 10) -> list[tuple]:
        """(id, started, summary, jumlah_pesan_user, title), terbaru dulu."""
        return self._all(
            "SELECT s.id, s.started, COALESCE(s.summary, ''), "
            "(SELECT COUNT(*) FROM messages m WHERE m.session = s.id AND m.role = 'user'), "
            "s.title "
            "FROM sessions s "
            "WHERE EXISTS (SELECT 1 FROM messages m2 WHERE m2.session = s.id) "
            "ORDER BY s.started DESC LIMIT ?",
            (n,),
        )

    def switch_session(self, session_id: str):
        self.session = session_id
        self.session_msgs = self._one(
            "SELECT COUNT(*) FROM messages WHERE session = ? AND role = 'user'",
            (session_id,),
        )[0]

    def new_session(self):
        self.session = uuid.uuid4().hex[:8]
        self._exec(
            "INSERT INTO sessions (id, started) VALUES (?, ?)",
            (self.session, time.time()),
        )
        self.session_msgs = 0

    def delete_session(self, session_id: str):
        self._exec("DELETE FROM messages WHERE session = ?", (session_id,))
        self._exec("DELETE FROM sessions WHERE id = ?", (session_id,))

    def prune_empty(self) -> int:
        """Hapus sesi tanpa pesan, kecuali sesi yang sedang aktif."""
        with self.lock:
            cur = self.con.execute(
                "DELETE FROM sessions WHERE id != ? AND NOT EXISTS "
                "(SELECT 1 FROM messages m WHERE m.session = sessions.id)",
                (self.session,),
            )
            self.con.commit()
            return cur.rowcount

    def session_digest(self, session_id: str, n: int = 10) -> str:
        """Konteks dari sesi lain: judul, ringkasan, dan pesan pengguna terakhir."""
        row = self._one(
            "SELECT COALESCE(title, ''), COALESCE(summary, '') FROM sessions WHERE id = ?",
            (session_id,),
        )
        if not row:
            return ""
        title, summ = row
        msgs = self._all(
            "SELECT content FROM messages WHERE session = ? AND role = 'user' "
            "ORDER BY id DESC LIMIT ?",
            (session_id, n),
        )
        lines = []
        if title:
            lines.append(f"Judul: {title}")
        if summ:
            lines.append(f"Ringkasan: {summ}")
        if msgs:
            lines.append("Pesan pengguna di sesi itu:")
            lines += [f"- {m[0][:200]}" for m in reversed(msgs)]
        return "\n".join(lines)

    # ---- profil pengguna (dipakai di semua sesi dan semua mode) ----
    def profile_set(self, key: str, value: str):
        self._exec(
            "INSERT OR REPLACE INTO profile (key, value, updated) VALUES (?, ?, ?)",
            (key, value, time.time()),
        )

    def profile_all(self) -> dict[str, str]:
        return dict(self._all("SELECT key, value FROM profile ORDER BY key"))

    def profile_delete(self, key: str):
        self._exec("DELETE FROM profile WHERE key = ?", (key,))

    def profile_clear(self):
        self._exec("DELETE FROM profile")

    # ---- cache web (juga dipakai saat offline) ----
    def cache_get(self, key: str, ttl: int) -> str | None:
        row = self._one("SELECT value, ts FROM web_cache WHERE key = ?", (key,))
        if row and time.time() - row[1] < ttl:
            return row[0]
        return None

    def cache_get_any(self, key: str) -> str | None:
        row = self._one("SELECT value FROM web_cache WHERE key = ?", (key,))
        return row[0] if row else None

    def cache_put(self, key: str, value: str):
        self._exec(
            "INSERT OR REPLACE INTO web_cache (key, value, ts) VALUES (?, ?, ?)",
            (key, value, time.time()),
        )

    def cache_count(self) -> int:
        return self._one("SELECT COUNT(*) FROM web_cache")[0]

    def clear_cache(self):
        self._exec("DELETE FROM web_cache")

    def close(self):
        with self.lock:
            self.con.close()
