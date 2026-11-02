import re
from datetime import date, datetime
from pathlib import Path

import config
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, OptionList, Static
from textual.widgets.option_list import Option

from config import (
    APP_NAME, APP_VERSION, MODELS, WEB_MODEL,
    SYSTEM_PROMPT, HISTORY_TURNS, set_perf,
)
from llm import ping, stream_chat, summarize, strip_think, extract_profile
from memory import Memory
from router import route, needs_web
from web import web_context, fetch_text

OUT_DIR = Path.home() / "vesper-output"

BANNER = r"""
██╗   ██╗ ███████╗ ███████╗ ██████╗  ███████╗ ██████╗
██║   ██║ ██╔════╝ ██╔════╝ ██╔══██╗ ██╔════╝ ██╔══██╗
██║   ██║ █████╗   ███████╗ ██████╔╝ █████╗   ██████╔╝
╚██╗ ██╔╝ ██╔══╝   ╚════██║ ██╔═══╝  ██╔══╝   ██╔══██╗
 ╚████╔╝  ███████╗ ███████║ ██║      ███████╗ ██║  ██║
  ╚═══╝   ╚══════╝ ╚══════╝ ╚═╝      ╚══════╝ ╚═╝  ╚═╝
     V E S P E R - A G E N T  ·  local-first CLI
"""

HELP = """Perintah:
  /mode <chat|homework|code|auto>  paksa model (auto = deteksi otomatis)
  /search <query>                  cari di web lalu jawab
  /berita                          cari berita hari ini
  /web <url> [pertanyaan]          baca halaman web lalu jelaskan
  /buat [nama]                     simpan blok kode dari jawaban terakhir ke file
  /sesi                            daftar sesi (judul + ID) dalam jendela
  /buka <id atau judul>            buka sesi lama dan lanjutkan chat
  /baru [id atau judul]            mulai sesi baru, opsional dengan konteks dari sesi lama
  /judul <nama>                    beri nama pada sesi ini
  /hapus <id atau judul>           hapus satu sesi
  /hapus kosong                    hapus sesi yang tidak punya pesan
  /profil                          lihat profil yang diingat
  /lupa [kunci]                    hapus satu kunci, atau semua profil
  /sessions                        jumlah sesi tersimpan
  /cache-clear                     hapus cache web
  /forget                          hapus riwayat pesan sesi ini (ringkasan tetap)
  /help                            tampilkan bantuan
  /quit                            keluar (ringkasan sesi disimpan)

Tombol: Ctrl+G ganti mode game/biasa · PageUp/PageDown scroll · Ctrl+Q keluar"""

THINK_INSTRUCTION = (
    "\nSebelum menjawab, tulis langkah berpikirmu secara singkat di dalam <think>...</think>. "
    "Setelah itu tulis jawaban akhirnya tanpa tag tersebut."
)

CODE_INSTRUCTION = (
    "\nKhusus pertanyaan kode: jika perlu menjalankan perintah terminal, tulis perintahnya "
    "di dalam blok ```bash, jelaskan fungsinya, dan JANGAN mengklaim sudah menjalankannya. "
    "Jika membuat file, tulis nama file di baris sebelum blok kode, misalnya `skrip.py`."
)

CODE_BLOCK_RE = re.compile(r"```[\w+-]*\n(.*?)```", re.DOTALL)
FILENAME_RE = re.compile(r"[\w.\-]+\.[A-Za-z]{1,5}")


def parse_blocks(text: str) -> list[tuple[str | None, str]]:
    """Ambil semua blok kode dan nama file yang disebut tepat sebelumnya."""
    blocks = []
    for m in CODE_BLOCK_RE.finditer(text):
        before = text[max(0, m.start() - 80):m.start()]
        names = FILENAME_RE.findall(before)
        blocks.append((names[-1] if names else None, m.group(1)))
    return blocks


def unique_path(name: str) -> Path:
    """Path di OUT_DIR yang belum dipakai. Nama dibersihkan dari folder."""
    safe = Path(name).name or "output.txt"
    if "." not in safe:
        safe += ".txt"
    path = OUT_DIR / safe
    i = 1
    while path.exists():
        path = OUT_DIR / f"{Path(safe).stem}-{i}{Path(safe).suffix}"
        i += 1
    return path


def short_name(model: str) -> str:
    """namaorg/nama-model:tag -> nama-model"""
    name = model.split("/")[-1]
    if ":" in name and name.split(":")[1].startswith("q"):
        name = name.split(":")[0]
    return name


def make_title(text: str, n: int = 40) -> str:
    """Judul otomatis dari pesan pertama sesi."""
    t = " ".join(text.split())
    return t if len(t) <= n else t[:n].rstrip() + "…"


class SessionScreen(ModalScreen[str | None]):
    """Jendela melayang berisi daftar sesi (judul + ID)."""

    BINDINGS = [
        ("escape", "close", "Tutup"),
    ]

    DEFAULT_CSS = """
    SessionScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.6);
    }
    #box {
        width: 70;
        height: auto;
        max-height: 80%;
        border: double #f5a524;
        background: #120e07;
        padding: 1 2;
    }
    #stitle {
        color: #f5a524;
        text-style: bold;
        margin-bottom: 1;
    }
    #slist {
        height: auto;
        max-height: 24;
        background: #120e07;
        border: none;
        color: #e8e0cc;
    }
    #slist > .option-list--option-highlighted {
        background: #3a2a10;
        color: #ffd27a;
    }
    #shint {
        color: #8a8270;
        margin-top: 1;
    }
    """

    def __init__(self, rows: list[tuple], current: str):
        super().__init__()
        self.rows = rows
        self.current = current

    def compose(self) -> ComposeResult:
        options = []
        for sid, _started, _summ, _n, title in self.rows:
            mark = "▶" if sid == self.current else " "
            name = title or "(tanpa judul)"
            options.append(Option(f"{mark} {name}  [{sid}]", id=sid))
        with Vertical(id="box"):
            yield Static("SESI TERSIMPAN", id="stitle")
            yield OptionList(*options, id="slist")
            yield Static(
                "Panah atas/bawah pilih · Enter isi /buka · Esc tutup · "
                "Shift+drag untuk copy",
                id="shint",
            )

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id)

    def action_close(self) -> None:
        self.dismiss(None)


class VesperAgentApp(App):
    TITLE = APP_NAME
    SUB_TITLE = f"v{APP_VERSION} · Ollama lokal"

    CSS = """
    Screen { background: #0e0c08; }
    Header { background: #1f1608; color: #f5a524; }
    Footer { background: #1f1608; }

    #main { height: 1fr; }
    #left { width: 1fr; height: 1fr; }
    #chat { height: 1fr; padding: 0 2; }
    #prompt { border: round #f5a524; margin: 0 1 1 1; }
    #prompt:focus { border: double #ffd27a; }

    #side {
        width: 46;
        height: 1fr;
        padding: 1 1 0 1;
        border-left: solid #4a3a1e;
        background: #120e07;
    }
    .panel {
        border: round #6b4f1d;
        padding: 0 1;
        margin-bottom: 1;
        height: auto;
        color: #e8e0cc;
    }
    #p-perf {
        border: double #f5a524;
        padding: 0 1;
        margin-bottom: 1;
        height: auto;
        text-style: bold;
    }

    .msg { margin-bottom: 1; }
    .banner { color: #f5a524; text-style: bold; }
    .sys { color: #8a8270; }
    .user { color: #7fd1ff; text-style: bold; }
    .meta { color: #b8862f; }
    .agent { color: #f1ebdc; }
    """

    BINDINGS = [
        ("ctrl+q", "quit_agent", "Keluar"),
        ("pageup", "chat_up", "Scroll naik"),
        ("pagedown", "chat_down", "Scroll turun"),
        ("ctrl+g", "toggle_perf", "Mode game/biasa"),
    ]

    def __init__(self, continue_last: bool = False):
        super().__init__()
        self.continue_last = continue_last
        self.mem = Memory()
        self.history: list[dict] = []
        self.carry = ""
        self.override: str | None = None
        self.busy = False
        self.web_status = "-"
        self.ollama_ok = False
        self.last_reply = ""

    # ---------- layout ----------
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield VerticalScroll(id="chat")
                yield Input(placeholder="Tulis pesan atau ketik /help ...", id="prompt")
            with Vertical(id="side"):
                yield Static(id="p-perf")
                yield Static(id="p-model", classes="panel")
                yield Static(id="p-memory", classes="panel")
                yield Static(id="p-web", classes="panel")
                yield Static(id="p-tools", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        self.ollama_ok = ping()
        self.add_msg(Text(BANNER), "banner")
        self.add_msg(
            Text(f"Sesi {self.mem.session} dimulai. Ketik /help untuk perintah."), "sys"
        )
        if not self.ollama_ok:
            self.add_msg(
                Text("Ollama tidak terdeteksi. Jalankan `ollama serve` lalu restart.",
                     style="bold red"),
                "sys",
            )
        if self.continue_last:
            sid = self.mem.last_session_id()
            if sid:
                self.open_session(sid)
        self.query_one("#prompt", Input).focus()
        self.refresh_panels()

    # ---------- helper UI ----------
    def add_msg(self, renderable, kind: str) -> Static:
        widget = Static(renderable, classes=f"msg {kind}")
        chat = self.query_one("#chat", VerticalScroll)
        chat.mount(widget)
        chat.scroll_end(animate=False)
        return widget

    def scroll_chat(self) -> None:
        self.query_one("#chat", VerticalScroll).scroll_end(animate=False)

    def set_web_status(self, status: str) -> None:
        self.web_status = status
        self.refresh_panels()

    def refresh_panels(self) -> None:
        mode = self.override or "auto"
        ok = "[green]●[/] online" if self.ollama_ok else "[red]●[/] offline"
        busy = "[yellow]sedang menjawab[/]" if self.busy else "[dim]siap[/]"

        # kotak status mode: hijau = biasa, oranye = game
        if config.PERF_MODE == "game":
            perf_box = (
                "[bold #ff9f43]● MODE GAME[/]\n"
                f"[#ff9f43]context {config.NUM_CTX} · teks halaman {config.PAGE_CHARS}[/]\n"
                "[dim]Ctrl+G untuk kembali ke biasa[/]"
            )
        else:
            perf_box = (
                "[bold #7fd18b]● MODE BIASA[/]\n"
                f"[#7fd18b]context {config.NUM_CTX} · teks halaman {config.PAGE_CHARS}[/]\n"
                "[dim]Ctrl+G untuk mode game[/]"
            )
        self.query_one("#p-perf", Static).update(perf_box)

        self.query_one("#p-model", Static).update(
            f"[bold #f5a524]MODEL[/]\n"
            f"mode    : {mode}\n"
            f"chat    : {short_name(MODELS['chat'])}\n"
            f"homework: {short_name(MODELS['homework'])}\n"
            f"code    : {short_name(MODELS['code'])}\n"
            f"web     : {short_name(WEB_MODEL)}\n"
            f"ollama  : {ok}\n"
            f"status  : {busy}"
        )
        self.query_one("#p-memory", Static).update(
            f"[bold #f5a524]MEMORY[/]\n"
            f"sesi tersimpan : {self.mem.session_count()}\n"
            f"pesan sesi ini : {self.mem.session_msgs}\n"
            f"profil         : {len(self.mem.profile_all())} kunci\n"
            f"cache web      : {self.mem.cache_count()}\n"
            f"lokasi         : ~/.localagent/agent.db"
        )
        self.query_one("#p-web", Static).update(
            f"[bold #f5a524]WEB[/]\n"
            f"status terakhir: {self.web_status}\n"
            f"sumber: DuckDuckGo + scraping"
        )
        self.query_one("#p-tools", Static).update(
            f"[bold #f5a524]TOOLS[/]\n"
            f"/search   web search\n"
            f"/berita   berita hari ini\n"
            f"/web      baca halaman\n"
            f"/buat     simpan kode ke file\n"
            f"Ctrl+G    ganti game/biasa"
        )

    # ---------- input ----------
    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        event.input.value = ""
        if not text:
            return
        if text.startswith("/"):
            self.handle_command(text)
        else:
            self.start_chat(text)

    def handle_command(self, text: str) -> None:
        cmd, _, arg = text.partition(" ")
        arg = arg.strip()

        if cmd in ("/quit", "/exit"):
            self.action_quit_agent()
        elif cmd == "/help":
            self.add_msg(Text(HELP), "sys")
        elif cmd == "/mode":
            if arg in MODELS:
                self.override = arg
                self.add_msg(Text(f"mode diset ke {arg}"), "sys")
            elif arg in ("", "auto"):
                self.override = None
                self.add_msg(Text("mode diset ke auto"), "sys")
            else:
                self.add_msg(Text("mode tidak dikenal: chat, homework, code, auto"), "sys")
            self.refresh_panels()
        elif cmd == "/berita":
            self.start_chat("berita hari ini", force_web=True)
        elif cmd == "/web":
            if not arg:
                self.add_msg(Text("pakai: /web <url> [pertanyaan]"), "sys")
            elif self.busy:
                self.notify("Tunggu jawaban selesai dulu.", severity="warning")
            else:
                parts = arg.split(maxsplit=1)
                url = parts[0]
                if not url.startswith(("http://", "https://")):
                    self.add_msg(Text("URL harus diawali http:// atau https://"), "sys")
                else:
                    question = parts[1] if len(parts) > 1 else "jelaskan isi halaman ini dan topik utamanya"
                    self.start_chat(question, url=url)
        elif cmd == "/buat":
            self.buat_file(arg)
        elif cmd == "/profil":
            prof = self.mem.profile_all()
            if prof:
                body = "\n".join(f"  {k}: {v}" for k, v in prof.items())
                self.add_msg(Text("profil pengguna:\n" + body), "sys")
            else:
                self.add_msg(Text("profil masih kosong"), "sys")
        elif cmd == "/lupa":
            if arg:
                self.mem.profile_delete(arg)
                self.add_msg(Text(f"profil '{arg}' dihapus"), "sys")
            else:
                self.mem.profile_clear()
                self.add_msg(Text("seluruh profil dihapus"), "sys")
            self.refresh_panels()
        elif cmd == "/sesi":
            rows = self.mem.list_sessions(n=50)
            if not rows:
                self.add_msg(Text("belum ada sesi tersimpan"), "sys")
            else:
                screen = SessionScreen(rows, self.mem.session)
                self.push_screen(screen, self.on_session_picked)
        elif cmd == "/buka":
            if not arg:
                self.add_msg(Text("pakai: /buka <id atau judul>, lihat dengan /sesi"), "sys")
            elif self.busy:
                self.notify("Tunggu jawaban selesai dulu.", severity="warning")
            else:
                self.open_session(arg)
        elif cmd == "/baru":
            if self.busy:
                self.notify("Tunggu jawaban selesai dulu.", severity="warning")
            elif not arg:
                self.new_chat()
            else:
                sid = self.mem.resolve_session(arg)
                if sid is None:
                    self.add_msg(Text(f"sesi '{arg}' tidak ditemukan atau lebih dari satu cocok"), "sys")
                else:
                    self.new_chat(carry_text=self.mem.session_digest(sid))
        elif cmd == "/judul":
            if not arg:
                self.add_msg(Text("pakai: /judul <nama>"), "sys")
            else:
                self.mem.set_title(arg[:60])
                self.add_msg(Text(f"judul sesi: {arg[:60]}"), "sys")
                self.refresh_panels()
        elif cmd == "/hapus":
            if not arg:
                self.add_msg(Text("pakai: /hapus <id atau judul>, atau /hapus kosong"), "sys")
            elif self.busy:
                self.notify("Tunggu jawaban selesai dulu.", severity="warning")
            elif arg == "kosong":
                n = self.mem.prune_empty()
                self.add_msg(Text(f"{n} sesi kosong dihapus"), "sys")
                self.refresh_panels()
            else:
                sid = self.mem.resolve_session(arg)
                if sid is None:
                    self.add_msg(Text(f"sesi '{arg}' tidak ditemukan atau lebih dari satu cocok"), "sys")
                elif sid == self.mem.session:
                    self.history.clear()
                    self.carry = ""
                    self.mem.delete_session(sid)
                    self.mem.new_session()
                    self.query_one("#chat", VerticalScroll).remove_children()
                    self.add_msg(Text(f"sesi aktif dihapus. Sesi baru {self.mem.session} dimulai."), "sys")
                    self.refresh_panels()
                else:
                    self.mem.delete_session(sid)
                    self.add_msg(Text(f"sesi {sid} dihapus"), "sys")
                    self.refresh_panels()
        elif cmd == "/sessions":
            self.add_msg(Text(f"sesi tersimpan: {self.mem.session_count()}"), "sys")
        elif cmd == "/cache-clear":
            self.mem.clear_cache()
            self.add_msg(Text("cache web dihapus"), "sys")
            self.refresh_panels()
        elif cmd == "/forget":
            self.mem.clear_messages()
            self.history.clear()
            self.carry = ""
            self.add_msg(Text("riwayat pesan sesi ini dihapus"), "sys")
        elif cmd == "/search":
            if not arg:
                self.add_msg(Text("pakai: /search <query>"), "sys")
            else:
                self.start_chat(arg, force_web=True)
        else:
            self.add_msg(Text("perintah tidak dikenal, ketik /help"), "sys")

    def set_perf_mode(self, name: str) -> None:
        """Ganti mode performa. Kotak status di sidebar yang menampilkan perubahannya."""
        if self.busy:
            self.notify("Tunggu jawaban selesai dulu.", severity="warning")
            return
        set_perf(name)
        self.refresh_panels()

    def buat_file(self, arg: str) -> None:
        """Simpan blok kode dari jawaban terakhir ke ~/vesper-output/."""
        if self.busy:
            self.notify("Tunggu jawaban selesai dulu.", severity="warning")
            return
        blocks = parse_blocks(self.last_reply)
        if not blocks:
            self.add_msg(Text("tidak ada blok kode di jawaban terakhir"), "sys")
            return
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        saved = []
        for i, (name, code) in enumerate(blocks, start=1):
            if arg and i == 1:
                target = arg
            else:
                target = name or f"output-{i}.txt"
            path = unique_path(target)
            path.write_text(code, encoding="utf-8")
            saved.append(str(path))
        self.add_msg(
            Text("disimpan:\n" + "\n".join(f"  {p}" for p in saved), style="dim"),
            "sys",
        )

    def on_session_picked(self, sid: str | None) -> None:
        """Dipanggil saat jendela /sesi ditutup. Jika ada yang dipilih, isi /buka <id>."""
        prompt = self.query_one("#prompt", Input)
        if sid:
            prompt.value = f"/buka {sid}"
        prompt.focus()

    def start_chat(self, text: str, force_web: bool = False, url: str = "") -> None:
        if self.busy:
            self.notify("Masih memproses jawaban sebelumnya...", severity="warning")
            return
        self.add_msg(Text(f"▸ {text}"), "user")
        self.run_chat(text, force_web, url)

    # ---------- worker: LLM + web (thread terpisah, UI tetap responsif) ----------
    @work(thread=True, exclusive=True, group="chat")
    def run_chat(self, text: str, force_web: bool, url: str = "") -> None:
        self.busy = True
        self.call_from_thread(self.refresh_panels)
        try:
            mode = route(text, self.override)
            model = MODELS[mode]
            web_ctx = ""

            if url:
                self.call_from_thread(self.set_web_status, "membuka halaman...")
                page = fetch_text(url, self.mem, max_chars=config.PAGE_CHARS * 2)
                if not page:
                    self.call_from_thread(self.set_web_status, "gagal")
                    self.call_from_thread(
                        self.add_msg,
                        Text(f"gagal membuka halaman: {url}", style="bold red"),
                        "sys",
                    )
                    return
                self.call_from_thread(self.set_web_status, "halaman dibuka")
                web_ctx = f"[{url}]\n{page}"
                mode, model = "web", WEB_MODEL
                self.call_from_thread(
                    self.add_msg, Text(f"sumber: {url}", style="dim"), "meta"
                )

            elif force_web or needs_web(text):
                self.call_from_thread(self.set_web_status, "mencari...")
                web_ctx, status, sources, query_used = web_context(text, self.mem)
                self.call_from_thread(
                    self.add_msg, Text(f"kueri: {query_used}", style="dim"), "meta"
                )
                self.call_from_thread(self.set_web_status, status)
                if web_ctx:
                    mode, model = "web", WEB_MODEL
                    src_text = "sumber:\n" + "\n".join(f"  - {u}" for u in sources)
                    self.call_from_thread(self.add_msg, Text(src_text, style="dim"), "meta")
                else:
                    self.call_from_thread(
                        self.add_msg,
                        Text("pencarian web gagal, menjawab dari pengetahuan lokal", style="dim"),
                        "sys",
                    )

            system = (
                SYSTEM_PROMPT
                + f"\nTanggal hari ini: {date.today():%d %B %Y}. Jam sekarang: {datetime.now():%H:%M}."
            )

            if not web_ctx:
                system += THINK_INSTRUCTION
            if mode == "code":
                system += CODE_INSTRUCTION

            profile = self.mem.profile_all()
            if profile:
                nama = profile.get("panggilan") or profile.get("nama")
                system += (
                    "\n\nKamu sudah mengenal pengguna ini, seperti teman dekat. "
                    "Bicara dengan santai dan hangat."
                )
                if nama:
                    system += (
                        f" Namanya {nama}. Sebut namanya sesekali saja, "
                        "misalnya di awal atau saat menyapa. Jangan sebut di setiap kalimat."
                    )
                system += (
                    "\nProfil PENGGUNA (bukan tentang kamu, pakai bila relevan, "
                    "jangan dibacakan ulang):\n"
                    + "\n".join(f"- {k}: {v}" for k, v in profile.items())
                )

            if self.carry:
                system += (
                    "\n\nPengguna melanjutkan pekerjaan dari sesi sebelumnya. "
                    "Gunakan konteks ini untuk mengerjakan hal yang sama:\n"
                    + self.carry
                )

            summaries = self.mem.recent_summaries()
            if summaries:
                system += "\n\nRingkasan sesi sebelumnya:\n" + "\n".join(f"- {s}" for s in summaries)

            user_content = text
            if web_ctx:
                user_content = (
                    f"Hasil pencarian:\n{web_ctx}\n\n"
                    f"Pertanyaan: {text}\n\n"
                    "Jawab singkat dalam Bahasa Indonesia HANYA berdasarkan hasil di atas. "
                    "Sebutkan sumbernya. Jika hasilnya tidak relevan dengan pertanyaan, "
                    "katakan: 'Maaf, saya tidak menemukan jawaban yang jelas dari hasil pencarian.'"
                )
            elif profile:
                catatan = []
                nama_user = profile.get("panggilan") or profile.get("nama")
                if nama_user:
                    catatan.append(f"nama lawan bicaramu adalah {nama_user}")
                for k in ("hobi", "minat", "pekerjaan", "gaya_bicara"):
                    if k in profile:
                        catatan.append(f"{k.replace('_', ' ')}: {profile[k]}")
                if catatan:
                    user_content = (
                        "(Catatan tentang lawan bicaramu, BUKAN tentang kamu: "
                        + "; ".join(catatan)
                        + ".)\n"
                        + text
                    )

            messages = (
                [{"role": "system", "content": system}]
                + self.history[-HISTORY_TURNS:]
                + [{"role": "user", "content": user_content}]
            )

            self.call_from_thread(
                self.add_msg,
                Text(f"agent · {mode} · {short_name(model)}", style="italic"),
                "meta",
            )
            reply_widget = self.call_from_thread(self.add_msg, Text(""), "agent")

            reply = ""
            for chunk in stream_chat(model, messages):
                reply += chunk
                self.call_from_thread(reply_widget.update, Text(strip_think(reply)))
                self.call_from_thread(self.scroll_chat)

            reply = strip_think(reply)
            self.last_reply = reply
            # riwayat memakai pertanyaan asli, bukan versi yang berisi hasil web
            self.history += [
                {"role": "user", "content": text},
                {"role": "assistant", "content": reply},
            ]
            self.mem.add("user", text)
            self.mem.add("assistant", reply)

            if not self.mem.get_title():
                self.mem.set_title(make_title(text))

            # ekstrak profil dari pesan pengguna (bukan dari jawaban model)
            if len(text) > 15:
                try:
                    new = extract_profile(text)
                    for k, v in new.items():
                        self.mem.profile_set(k, v)
                    if new:
                        self.call_from_thread(
                            self.add_msg,
                            Text("profil diperbarui: " + ", ".join(new), style="dim"),
                            "sys",
                        )
                except Exception as e:
                    self.call_from_thread(
                        self.add_msg, Text(f"profil gagal disimpan: {e}", style="dim"), "sys"
                    )

        except Exception as e:
            self.call_from_thread(self.add_msg, Text(f"error: {e}", style="bold red"), "sys")
        finally:
            self.busy = False
            self.call_from_thread(self.refresh_panels)

    # ---------- session helpers ----------
    def finish_session(self) -> None:
        """Buat ringkasan untuk sesi yang sedang aktif sebelum pindah."""
        if self.history and self.ollama_ok:
            try:
                summary = summarize(self.history)
                if summary:
                    self.mem.set_summary(summary)
            except Exception:
                pass

    def open_session(self, query: str) -> None:
        sid = self.mem.resolve_session(query)
        if sid is None:
            self.add_msg(Text(f"sesi '{query}' tidak ditemukan atau lebih dari satu cocok"), "sys")
            return
        if sid == self.mem.session:
            self.add_msg(Text("kamu sudah di sesi ini"), "sys")
            return

        self.finish_session()
        self.mem.switch_session(sid)
        self.carry = ""

        self.query_one("#chat", VerticalScroll).remove_children()
        title = self.mem.get_title() or "(tanpa judul)"
        self.add_msg(Text(f"Sesi: {title}  [{sid}]"), "sys")

        for role, content in self.mem.load_messages(sid, limit=40):
            if role == "user":
                self.add_msg(Text(f"▸ {content}"), "user")
            else:
                self.add_msg(Text(content), "agent")

        self.history = [
            {"role": r, "content": c} for r, c in self.mem.load_messages(sid, limit=HISTORY_TURNS)
        ]
        self.last_reply = ""
        self.refresh_panels()

    def new_chat(self, carry_text: str = "") -> None:
        self.finish_session()
        self.mem.new_session()
        self.history = []
        self.carry = carry_text
        self.last_reply = ""
        self.query_one("#chat", VerticalScroll).remove_children()
        if carry_text:
            self.add_msg(
                Text(f"Sesi baru {self.mem.session} dimulai, dengan konteks dari sesi sebelumnya."),
                "sys",
            )
        else:
            self.add_msg(Text(f"Sesi baru {self.mem.session} dimulai."), "sys")
        self.refresh_panels()

    # ---------- actions ----------
    def action_toggle_perf(self) -> None:
        """Balik mode performa: biasa <-> game (Ctrl+G)."""
        new_mode = "game" if config.PERF_MODE == "biasa" else "biasa"
        self.set_perf_mode(new_mode)

    def action_chat_up(self) -> None:
        self.query_one("#chat", VerticalScroll).scroll_page_up(animate=False)

    def action_chat_down(self) -> None:
        self.query_one("#chat", VerticalScroll).scroll_page_down(animate=False)

    def action_quit_agent(self) -> None:
        self.finish_session()
        self.mem.close()
        self.exit()
