#!/usr/bin/env bash
# Сборка Linux-версии Jarvis (PyInstaller onedir -> tar.gz).
# Запускать НА Linux (или в CI на ubuntu). Из-под Windows PyInstaller
# собрать Linux-бинарник НЕ может (он не кросс-платформенный).
set -e

echo "=== Building Jarvis for Linux ==="

# venv
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
pip install -e .

# PyInstaller (используем GUI-спеку; win-only hidden imports дадут лишь warnings)
rm -rf build dist
pyinstaller jarvis_gui.spec --clean --noconfirm

# Кладём рядом редактируемые файлы
cp -r plugins dist/Jarvis/ 2>/dev/null || true
cp -f mcp_servers.json dist/Jarvis/ 2>/dev/null || true
cp -f .env.example dist/Jarvis/ 2>/dev/null || true

# Лаунчер-скрипт
cat > dist/Jarvis/jarvis.sh <<'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")"
./Jarvis "$@"
EOF
chmod +x dist/Jarvis/jarvis.sh dist/Jarvis/Jarvis 2>/dev/null || true

# Упаковка
mkdir -p release_out
tar -czf "release_out/Jarvis-linux-x64.tar.gz" -C dist Jarvis

echo ""
echo "=== Done ==="
echo "Artifact: release_out/Jarvis-linux-x64.tar.gz"
echo "Run: распакуйте и запустите ./Jarvis/jarvis.sh"
