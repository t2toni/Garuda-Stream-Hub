#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Garuda Stream Hub - Launching ==="

# Build native C++ module if not yet built
EXT_SUFFIX=$(python3-config --extension-suffix)
if [ ! -f "src/native/stream_native${EXT_SUFFIX}" ]; then
    echo "[*] Compiling high-performance native C++ engine..."
    make
fi

# Run Stream Hub
exec python3 src/main.py "$@"
