"""Uninstall Vesper-Agent.

Menghapus: folder aplikasi (~/.vesper-agent) dan perintah vesper.
Tidak menghapus: data chat dan profil di ~/.localagent, kecuali pakai --purge.
Tidak menghapus: folder proyek asli tempat kamu clone repo.

Pemakaian:
  vesper uninstall            konfirmasi, data tetap ada
  vesper uninstall --purge    ikut menghapus data chat dan profil
  vesper uninstall -y         tanpa konfirmasi
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PREFIX = Path.home() / ".vesper-agent"
DATA = Path(os.getenv("LOCALAGENT_HOME", str(Path.home() / ".localagent")))


def _read_info() -> dict:
    try:
        return json.loads((PREFIX / "install.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}


def _remove_from_user_path(bin_dir: str) -> None:
    ps = (
        "$p=[Environment]::GetEnvironmentVariable('Path','User');"
        f"$d='{bin_dir}';"
        "$n=(($p -split ';') | Where-Object { $_ -and $_ -ne $d }) -join ';';"
        "[Environment]::SetEnvironmentVariable('Path',$n,'User')"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=False)


def run(argv: list[str]) -> int:
    purge = "--purge" in argv
    yes = "-y" in argv or "--yes" in argv
    info = _read_info()

    if info.get("launcher"):
        launchers = [Path(info["launcher"])]
    else:  # install.json tidak ada: tebak lokasi perintah
        launchers = [Path.home() / ".local/bin/vesper", PREFIX / "bin/vesper.cmd"]

    print("Vesper-Agent uninstall")
    print(f"  folder aplikasi : {PREFIX}")
    print(f"  perintah        : {', '.join(str(p) for p in launchers)}")
    if purge:
        print(f"  DATA            : {DATA}  (riwayat, sesi, profil, pengaturan model) -> AKAN DIHAPUS")
    else:
        print(f"  data            : {DATA}  (tetap ada)")
    print("  folder proyek asli (tempat kamu clone) tidak dihapus.")

    if not yes:
        if input("\nLanjutkan? (y/N): ").strip().lower() not in ("y", "ya", "yes"):
            print("dibatalkan")
            return 0
        if purge and input("Ketik HAPUS DATA untuk menghapus data chat: ").strip() != "HAPUS DATA":
            print("dibatalkan, data tidak dihapus")
            return 0

    for p in launchers:
        if p.exists():
            p.unlink()
            print(f"dihapus: {p}")

    if info.get("os") == "windows" and info.get("path_added"):
        _remove_from_user_path(str(PREFIX / "bin"))
        print("PATH pengguna dibersihkan")

    if purge and DATA.exists():
        shutil.rmtree(DATA, ignore_errors=True)
        print(f"dihapus: {DATA}")

    if sys.platform == "win32":
        # python.exe di dalam venv sedang dipakai, jadi penghapusan dijadwalkan
        # setelah program ini selesai
        cmd = f'timeout /t 2 /nobreak >nul & rmdir /s /q "{PREFIX}"'
        subprocess.Popen(
            ["cmd", "/c", cmd],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
        print("folder aplikasi akan dihapus setelah program ini ditutup")
    else:
        shutil.rmtree(PREFIX, ignore_errors=True)
        print(f"dihapus: {PREFIX}")

    print("Selesai. Vesper sudah dihapus.")
    return 0