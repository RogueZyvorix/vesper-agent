#!/usr/bin/env bash
# Pasang Vesper-Agent di Linux dan macOS.
# Pemakaian (dari folder proyek): ./install.sh
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="$HOME/.vesper-agent"
APP="$PREFIX/app"
VENV="$PREFIX/venv"
BIN_DIR="$HOME/.local/bin"

echo "==> Memeriksa Python"
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 belum ada. Pasang Python 3.10 atau lebih baru, lalu jalankan ulang."
  exit 1
fi
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "Butuh Python 3.10 atau lebih baru."
  exit 1
fi

if ! command -v ollama >/dev/null 2>&1; then
  echo "peringatan: ollama belum terpasang. Pasang dari https://ollama.com"
fi

echo "==> Menyalin aplikasi ke $APP"
rm -rf "$APP"
mkdir -p "$APP" "$BIN_DIR"
tar -C "$SRC" --exclude=.git --exclude=.venv --exclude=__pycache__ -cf - . | tar -C "$APP" -xf -

echo "==> Membuat lingkungan Python (venv)"
rm -rf "$VENV"
if ! python3 -m venv "$VENV"; then
  echo "Gagal membuat venv. Di Ubuntu/Debian, pasang dulu: sudo apt install python3-venv"
  exit 1
fi

echo "==> Memasang paket"
"$VENV/bin/python" -m pip install -q --upgrade pip
"$VENV/bin/python" -m pip install -q -r "$APP/requirements.txt"

echo "==> Membuat perintah vesper"
cat > "$BIN_DIR/vesper" <<EOF
#!/usr/bin/env bash
exec "$VENV/bin/python" "$APP/main.py" "\$@"
EOF
chmod +x "$BIN_DIR/vesper"

cat > "$PREFIX/install.json" <<EOF
{"os": "unix", "launcher": "$BIN_DIR/vesper", "path_added": false}
EOF

echo ""
echo "Selesai. Perintah: vesper"
case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    echo "Tambahkan ke PATH dulu (cukup sekali), lalu buka terminal baru:"
    echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc   # atau ~/.bashrc"
    ;;
esac