# Vesper-Agent v0.5.0

Agent CLI/TUI berbasis Ollama. Berjalan lokal, data tersimpan di SQLite, dan tetap bisa dipakai saat offline (dengan cache web).

## Fitur

1. **Dynamic context switching**: router memilih model `chat`, `homework`, atau `code` dari isi pesan. Jawaban dari hasil web memakai `WEB_MODEL`.
2. **Web search & scraping**: DuckDuckGo untuk pencarian, BeautifulSoup untuk mengambil teks halaman. Kueri dan sumber ditampilkan di chat.
3. **Sesi bernama**: setiap sesi diberi judul otomatis dari pesan pertama, bisa diganti dengan `/judul`, dan dibuka dengan judul atau ID.
4. **Lanjut dan pindah sesi**: `vesper -c` melanjutkan sesi terakhir, `/buka` pindah ke sesi lama, `/baru <sesi>` membuat sesi baru dengan konteks dari sesi lama.
5. **Profil pengguna**: nama, panggilan, hobi, minat, gaya bicara, dan pekerjaan disimpan dan dipakai di semua sesi dan mode.
6. **Cross-session memory**: ringkasan sesi dibuat saat keluar atau pindah sesi.
7. **Murni CLI/TUI**: dashboard `textual` dengan panel MODEL, MEMORY, WEB, dan TOOLS.
8. **Resource efficient**: context dibatasi, riwayat dipotong, model dilepas 3 menit setelah jawaban terakhir.
9. **Local-first & offline**: hasil web di-cache 24 jam. Jika internet mati, cache dipakai.

## Struktur

```
vesper-agent/
├── main.py          # entry point: vesper atau vesper -c
├── tui.py           # tampilan TUI, perintah, dan alur chat
├── llm.py           # Ollama: streaming, ringkasan, ekstraksi profil
├── router.py        # pemilihan model otomatis
├── memory.py        # SQLite: sesi, judul, pesan, ringkasan, profil, cache
├── web.py           # pembersihan kueri, pencarian, scraping, cache
├── config.py        # model, host, batas resource, prompt
└── requirements.txt
```

## Instalasi

Butuh Python 3.10+ dan Ollama.

```bash
ollama pull qwen2.5:1.5b
ollama pull deepseek-coder:1.3b
ollama list    # cek nama model, lalu sesuaikan di config.py

cd vesper-agent
python3 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -r requirements.txt

.venv/bin/python main.py
```

Di Ubuntu 24.04, jangan pakai `pip install` langsung ke sistem. Selalu gunakan `.venv/bin/python -m pip`.

### Perintah `vesper` dari folder mana pun

```bash
mkdir -p ~/.local/bin
printf '#!/usr/bin/env bash\nexec "$HOME/Applications/vesper-agent/.venv/bin/python" "$HOME/Applications/vesper-agent/main.py" "$@"\n' > ~/.local/bin/vesper
chmod +x ~/.local/bin/vesper
```

Ubah path di atas jika folder proyekmu berada di tempat lain. Pastikan `~/.local/bin` ada di PATH.

## Perintah

| Perintah | Fungsi |
|---|---|
| `/mode <chat\|homework\|code\|auto>` | Paksa model tertentu, atau kembali ke auto |
| `/search <query>` | Cari di web lalu jawab |
| `/sesi` | Daftar sesi dengan judul dan ID (`*` = sesi aktif) |
| `/buka <id atau judul>` | Buka sesi lama dan lanjutkan chat |
| `/baru [id atau judul]` | Sesi baru, opsional dengan konteks dari sesi lama |
| `/judul <nama>` | Beri nama pada sesi ini |
| `/hapus <id atau judul>` | Hapus satu sesi |
| `/hapus kosong` | Hapus sesi yang tidak punya pesan |
| `/profil` | Lihat profil yang diingat |
| `/lupa [kunci]` | Hapus satu kunci profil, atau semua profil |
| `/sessions` | Jumlah sesi tersimpan |
| `/cache-clear` | Hapus cache web |
| `/forget` | Hapus riwayat pesan sesi ini (ringkasan tetap ada) |
| `/clear` | Bersihkan layar |
| `/help` | Bantuan |
| `/quit` | Keluar dan simpan ringkasan sesi |

Tombol: `PageUp` dan `PageDown` untuk scroll chat, `Ctrl+L` bersihkan layar, `Ctrl+Q` keluar.

## Contoh

```bash
vesper            # sesi baru
vesper -c         # lanjut sesi terakhir
```

```
/sesi                       lihat daftar
/buka latihan               buka sesi yang judulnya mengandung "latihan"
/baru latihan gitar         sesi baru, model tahu konteks sesi latihan gitar
/judul Jadwal minggu ini    beri nama sesi ini
```

## Profil Pengguna

Agent mengambil fakta pribadi dari pesan kamu, misalnya:

```
halo, nama saya Budi, saya suka main gitar, ngomongnya santai aja ya
```

Hasilnya disimpan sebagai `nama`, `hobi`, dan `gaya_bicara`. Profil dipakai di semua sesi dan semua mode. Gunakan `/profil` untuk melihatnya dan `/lupa <kunci>` untuk menghapus bagian yang salah.

## Menyalin Teks

Mouse di aplikasi dimatikan supaya teks bisa diblok di terminal. Setelah blok, tekan Ctrl+C (kalau ada teks yang diblok) atau klik kanan lalu pilih Copy. Scroll dengan PageUp dan PageDown.

## Lokasi Data

Semua data ada di `~/.localagent/agent.db`. Ubah lokasi dengan `LOCALAGENT_HOME=/path/lain`.

```bash
ls -lh ~/.localagent/agent.db
sqlite3 ~/.localagent/agent.db "SELECT key, value FROM profile;"
sqlite3 ~/.localagent/agent.db "SELECT id, title FROM sessions WHERE title IS NOT NULL;"
```

## Catatan

- Model kecil kadang salah menangkap fakta atau keliru membedakan diri sendiri dengan pengguna. Cek `/profil` dan perbaiki dengan `/lupa`.
- Scraping hanya membaca halaman statis, bukan halaman yang dibangun dengan JavaScript.
- Konteks dari `/baru <sesi>` hanya berlaku selama aplikasi berjalan. Sesi lama tetap tersimpan dan bisa dibuka lagi dengan `/buka`.
- Ringkasan dibuat saat keluar atau pindah sesi. Jika aplikasi dihentikan paksa, ringkasan tidak dibuat tetapi pesan tetap tersimpan.
- Pencarian web butuh koneksi internet. Jika gagal, agent menjawab dari pengetahuan lokal dan menampilkan pemberitahuan.
