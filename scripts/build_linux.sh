#!/usr/bin/env bash
# ==============================================================================
# Garuda Stream Hub - Linux Standalone Binary Builder
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

echo "=== [1/4] Compiling native C++ telemetry engine ==="
make

echo "=== [2/4] Running unit test suite ==="
python3 -m unittest discover -s tests -v

echo "=== [3/4] Building standalone Linux executable via PyInstaller ==="
PYINSTALLER_BIN="pyinstaller"
if ! command -v pyinstaller &> /dev/null; then
    if [ -f "$HOME/.local/bin/pyinstaller" ]; then
        PYINSTALLER_BIN="$HOME/.local/bin/pyinstaller"
    else
        echo "Installing PyInstaller..."
        pip install --user pyinstaller --break-system-packages
        PYINSTALLER_BIN="$HOME/.local/bin/pyinstaller"
    fi
fi

export QT_API="pyqt6"
"$PYINSTALLER_BIN" --clean -y garuda_stream_hub.spec

echo "=== [4/4] Packaging release tarball ==="
mkdir -p dist/package
cp dist/garuda-stream-hub dist/package/
cp README.md dist/package/
cp -r assets dist/package/ 2>/dev/null || true

cd dist
tar -czvf "garuda-stream-hub-linux-x86_64.tar.gz" -C package .
rm -rf package
cd "$ROOT_DIR"

echo "=============================================================================="
echo "✔ Linux binary build complete!"
echo "Standalone Executable: dist/garuda-stream-hub"
echo "Release Tarball:      dist/garuda-stream-hub-linux-x86_64.tar.gz"
echo "=============================================================================="
