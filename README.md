# Vesper-Agent

Agent CLI/TUI berbasis [Ollama](https://ollama.com). Berjalan sepenuhnya di komputermu: chat, pencarian web, sesi, dan profil pengguna disimpan lokal di SQLite, dan tetap bisa dipakai saat internet mati (dengan cache web).

Dibuat untuk laptop dan PC dengan RAM terbatas. Ada mode performa `biasa` dan `game` supaya tetap ringan saat bermain game.

## Fitur

**Model per peran**
- Empat peran: `chat`, `homework`, `code`, dan `web`.
- `/model` membuka jendela pilihan peran, lalu daftar model yang sudah terpasang di Ollama. Pilihan disimpan di `~/.localagent/settings.json`.
- Model apa pun yang sudah di-pull atau dibuat dengan `ollama create` bisa dipakai.

**Chat dan routing**
- Router otomatis memilih peran dari isi pesan.
- Paksa mode dengan `/mode chat|homework|code`, atau kembali ke `auto`.

**Pencarian web**
- `/search <kueri>` mencari di DuckDuckGo, mengambil teks halaman, lalu menjawab dengan sumbernya.
- `/berita` mencari berita hari ini.
- `/web <url> [pertanyaan]` membaca satu halaman lalu menjelaskannya.
- Kata perintah seperti "carikan" dibuang, dan "hari ini" diganti tanggal.
- Hasil web di-cache 24 jam.

**Sesi**
- Setiap sesi diberi judul otomatis dari pesan pertama. Bisa diganti dengan `/judul`.
- `/sesi` menampilkan daftar sesi dalam jendela melayang.
- `/buka`, `/baru`, dan `/hapus` mengelola sesi. `/baru <sesi lama>` membawa konteks dari sesi lain.
- `vesper -c` melanjutkan sesi terakhir.

**Profil dan ingatan**
- Nama, panggilan, hobi, minat, gaya bicara, dan pekerjaan diambil dari pesan dan dipakai di semua sesi.
- `/profil` melihat isinya, dan `/lupa [kunci]` menghapus sebagian atau semuanya.
- Ringkasan sesi dibuat saat keluar atau pindah sesi.

**Kode**
- Di mode `code`, blok kode dari jawaban bisa disimpan ke file dengan `/buat [nama]` (tersimpan di `~/vesper-output/`).
- Perintah terminal dalam jawaban ditampilkan di blok ```bash. Vesper tidak menjalankannya sendiri.

**Performa**
- Ctrl+G berganti antara `biasa` (context 4096, teks halaman 2000) dan `game` (context 2048, teks halaman 1000).
- Kotak status di sidebar menunjukkan mode yang sedang aktif.
- Model dilepas dari RAM 3 menit setelah jawaban terakhir (`KEEP_ALIVE`).

**Antarmuka**
- TUI dengan `textual`: area chat, panel MODEL, MEMORY, WEB, dan TOOLS.
- Jawaban tampil bertahap (streaming).
- Roda mouse untuk scroll. Untuk menyalin teks, tahan Shift saat drag, lalu Ctrl+C atau klik kanan → Copy.

## Persyaratan

- Linux, macOS, atau Windows dengan Python 3.10 atau lebih baru
- [Ollama](https://ollama.com) yang sedang berjalan
- RAM minimal 4 GB untuk model kecil, 8 GB untuk model 1,5B sampai 3B

Angka di atas perkiraan. Pemakaian nyata tergantung model, jumlah context (`NUM_CTX`), dan aplikasi lain yang berjalan. Cek dengan `ollama ps` saat Vesper sedang menjawab.

## Instalasi

1. Pasang Ollama, lalu pasang model awal:

   ```bash
   ollama pull qwen2.5:1.5b
   ollama pull deepseek-coder:1.3b
   ```

2. Clone repo:

   ```bash
   git clone https://github.com/RogueZyvorix/vesper-agent.git
   cd vesper-agent
   ```

3. Pasang paket Python.

   Linux (Ubuntu 24.04 dan turunannya):

   ```bash
   python3 -m pip install --user --break-system-packages -r requirements.txt
   ```

   macOS dan Windows:

   ```bash
   python -m pip install --user -r requirements.txt
   ```

4. Jalankan:

   ```bash
   python3 main.py
   ```

   Di Windows, gunakan `python main.py`.

### Perintah `vesper` dari folder mana pun (opsional, Linux)

```bash
mkdir -p ~/.local/bin
cat > ~/.local/bin/vesper << 'EOF'
#!/usr/bin/env bash
exec python3 "$HOME/PATH/KE/vesper-agent/main.py" "$@"
EOF
chmod +x ~/.local/bin/vesper
```

Ganti `PATH/KE/vesper-agent` dengan lokasi folder proyekmu, lalu pastikan `~/.local/bin` ada di `PATH`:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc   # atau ~/.bashrc
```

Setelah itu cukup ketik `vesper` atau `vesper -c`.

## Untuk PC spek rendah

Vesper bisa dipakai di laptop atau PC dengan RAM kecil, asalkan model dan pengaturannya disesuaikan.

### Pilih model sesuai RAM

| RAM | Model yang disarankan | Catatan |
|---|---|---|
| 4 GB | `qwen2.5:0.5b` atau `llama3.2:1b` | Jawaban lebih sederhana, bahasa Indonesia kurang stabil |
| 8 GB | `qwen2.5:1.5b` | Pilihan seimbang, dipakai sebagai default |
| 16 GB ke atas | `qwen2.5:3b` atau `gemma2:2b` | Jawaban lebih lengkap dan lebih akurat |

Nama dan ukuran model bisa berubah. Cek di https://ollama.com/search sebelum memasang.

Pasang model kecil dengan:

```bash
ollama pull qwen2.5:0.5b
```

Lalu pilih lewat `/model`, atau edit `~/.localagent/settings.json`.

### Hemat RAM

1. **Pakai satu model untuk semua peran.** Setiap pergantian model memaksa Ollama memuat ulang model, dan itu paling terasa lambat di PC kecil. Di `/model`, pilih model yang sama untuk `chat`, `homework`, `code`, dan `web`.

2. **Pakai mode `game` saat butuh ringan.** Tekan Ctrl+G. Context turun ke 2048 dan teks halaman ke 1000 karakter.

3. **Kurangi lama model menetap di RAM.** Di `config.py`:

   ```python
   KEEP_ALIVE = "1m"
   ```

4. **Batasi Ollama** hanya kalau tidak ada aplikasi lain yang memakai Ollama, karena pengaturan ini berlaku global:

   - Linux: `sudo systemctl edit ollama`, lalu tambahkan
     `Environment="OLLAMA_MAX_LOADED_MODELS=1"` dan `Environment="OLLAMA_NUM_PARALLEL=1"`, kemudian `sudo systemctl restart ollama`.
   - macOS dan Windows: atur lewat aplikasi Ollama, atau set variabel lingkungan `OLLAMA_MAX_LOADED_MODELS=1` dan `OLLAMA_NUM_PARALLEL=1` sebelum Ollama dijalankan.

5. **Tutup aplikasi berat** seperti browser dengan banyak tab atau game saat butuh jawaban panjang.

### Contoh `settings.json` untuk PC kecil

```json
{
  "models": {
    "chat": "qwen2.5:0.5b",
    "homework": "qwen2.5:0.5b",
    "code": "qwen2.5:0.5b",
    "web": "qwen2.5:0.5b"
  }
}
```

### Cek pemakaian

- Linux: `free -h` dan `ollama ps`
- macOS: Activity Monitor, tab Memory
- Windows: Task Manager, tab Performance, lalu Memory

Kolom `SIZE` di `ollama ps` menunjukkan memori yang dipakai model yang sedang dimuat.

### Keterbatasan model kecil

- Model 0,5B dan 1B sering salah memahami instruksi dan kurang lancar berbahasa Indonesia. Untuk pertanyaan penting, periksa ulang jawabannya.
- Ringkasan sesi dan ekstraksi profil memakai model `web`, jadi kualitasnya ikut turun dengan model kecil.
- Untuk coding, model 0,5B hanya cocok untuk pertanyaan sederhana. Untuk script yang lebih panjang, gunakan model yang lebih besar.

## Perintah

| Perintah | Fungsi |
|---|---|
| `/model` | Pilih model untuk chat, homework, code, atau web |
| `/mode <chat\|homework\|code\|auto>` | Paksa mode untuk pesan berikutnya |
| `/search <kueri>` | Cari di web lalu jawab dengan sumber |
| `/berita` | Berita hari ini |
| `/web <url> [pertanyaan]` | Baca satu halaman lalu jelaskan |
| `/buat [nama]` | Simpan blok kode dari jawaban terakhir ke file |
| `/sesi` | Daftar sesi dalam jendela (Esc untuk tutup) |
| `/buka <id atau judul>` | Buka sesi lama |
| `/baru [id atau judul]` | Sesi baru, opsional dengan konteks dari sesi lain |
| `/judul <nama>` | Beri nama sesi ini |
| `/hapus <id atau judul>` | Hapus satu sesi |
| `/hapus kosong` | Hapus sesi tanpa pesan |
| `/profil` | Lihat profil yang diingat |
| `/lupa [kunci]` | Hapus satu kunci, atau semua profil |
| `/sessions` | Jumlah sesi tersimpan |
| `/cache-clear` | Hapus cache web |
| `/forget` | Hapus riwayat pesan sesi ini |
| `/help` | Bantuan |
| `/quit` | Keluar dan simpan ringkasan sesi |

## Tombol

| Tombol | Fungsi |
|---|---|
| `Ctrl+G` | Ganti mode game/biasa |
| `PageUp` / `PageDown` | Scroll chat |
| Roda mouse | Scroll chat |
| `Ctrl+Q` | Keluar |
| `Esc` | Tutup jendela |

## Konfigurasi

Nilai awal ada di `config.py`:

```python
DEFAULT_MODELS = {
    "chat": "qwen2.5:1.5b",
    "homework": "qwen2.5:1.5b",
    "code": "deepseek-coder:1.3b",
    "web": "qwen2.5:1.5b",
}
KEEP_ALIVE = "3m"
PRESETS = {
    "biasa": {"NUM_CTX": 4096, "PAGE_CHARS": 2000},
    "game":  {"NUM_CTX": 2048, "PAGE_CHARS": 1000},
}
```

Pilihan dari `/model` disimpan di `~/.localagent/settings.json` dan menimpa nilai awal. Kamu juga bisa mengedit file itu langsung:

```json
{
  "models": {
    "chat": "nama-model-saya",
    "homework": "qwen2.5:1.5b",
    "code": "deepseek-coder:1.3b",
    "web": "qwen2.5:1.5b"
  }
}
```

`KEEP_ALIVE` hanya berlaku untuk permintaan dari Vesper, sehingga aplikasi lain yang memakai Ollama tidak terpengaruh.

### Membuat model sendiri

Dari file GGUF, buat `Modelfile`:

```
FROM ./model-saya.gguf
PARAMETER num_ctx 4096
SYSTEM "Kamu asisten yang ringkas dan berbahasa Indonesia."
```

Lalu:

```bash
ollama create model-saya -f Modelfile
```

Model itu langsung muncul di `/model`.

## Lokasi data

| Sistem | Lokasi |
|---|---|
| Linux | `/home/<user>/.localagent/` |
| macOS | `/Users/<user>/.localagent/` |
| Windows | `C:\Users\<user>\.localagent\` |

Di dalamnya ada `agent.db` (riwayat, sesi, profil, dan cache web) dan `settings.json` (pilihan model). Folder ini tidak ada di dalam folder proyek, jadi tidak ikut ter-commit ke GitHub.

Ubah lokasi dengan `LOCALAGENT_HOME`:

- Linux/macOS: `export LOCALAGENT_HOME=/path/lain`
- Windows PowerShell: `$env:LOCALAGENT_HOME = "D:\vesper-data"`

Untuk pindah komputer, salin folder `.localagent` ke lokasi yang sama di komputer baru.

## Struktur proyek

```
vesper-agent/
├── main.py           # entry point: vesper atau vesper -c
├── tui.py            # tampilan TUI, perintah, dan alur chat
├── llm.py            # Ollama: daftar model, streaming, ringkasan, profil
├── router.py         # pemilihan peran otomatis
├── memory.py         # SQLite: sesi, judul, pesan, ringkasan, profil, cache
├── web.py            # pencarian, scraping, cache
├── config.py         # model per peran, mode performa, prompt
├── requirements.txt
├── LICENSE
└── README.md
```

## Keterbatasan

- Model kecil (sekitar 1,5B atau lebih kecil) kadang salah menangkap fakta, keliru membedakan diri sendiri dengan pengguna, atau menjawab terlalu singkat. Periksa jawaban penting.
- "Berpikir dulu" hanya simulasi lewat instruksi, bukan kemampuan model besar.
- Vesper tidak menjalankan perintah atau membaca file sendiri.
- Scraping hanya membaca halaman statis, bukan halaman yang dibangun dengan JavaScript.
- Pencarian web bergantung pada DuckDuckGo. Sumbernya tetap perlu dicek.
- Ekstraksi profil berjalan setelah setiap pesan panjang, sehingga menambah waktu sekitar 1 sampai 3 detik per jawaban.

## Lisensi

MIT. Lihat [LICENSE](LICENSE).
