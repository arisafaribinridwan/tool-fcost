#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEFAULT_PYTHON="/usr/bin/python3.12"
PYTHON_EXE="${1:-$DEFAULT_PYTHON}"
VENV_DIR="${2:-$PROJECT_ROOT/.venv-linux-build}"
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"

if [[ ! -x "$PYTHON_EXE" ]]; then
  cat <<EOF >&2
Python build target tidak ditemukan: $PYTHON_EXE

Saran:
- Pastikan interpreter distro tersedia, mis. /usr/bin/python3.12
- Jika belum ada, install paket Python sistem terlebih dahulu
EOF
  exit 1
fi

if ! "$PYTHON_EXE" - <<'PY'
import importlib

required_modules = ("venv", "tkinter")
missing = []

for module_name in required_modules:
    try:
        importlib.import_module(module_name)
    except Exception:
        missing.append(module_name)

if missing:
    print(",".join(missing))
    raise SystemExit(1)
PY
then
  cat <<EOF >&2
Bootstrap build env dibatalkan karena Python sistem belum lengkap.

Kebutuhan minimum:
- paket distro yang menyediakan stdlib venv untuk Python target
- paket distro yang menyediakan dukungan Tk/Tcl

Ubuntu/Linux Mint (disarankan):
  sudo apt-get update
  sudo apt-get install -y python3-tk python3.12-venv
EOF
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_EXE" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
"$VENV_DIR/bin/python" -m pip install -r "$REQUIREMENTS_FILE"

cat <<EOF
Linux build env siap:
- Python target: $PYTHON_EXE
- Virtualenv: $VENV_DIR

Langkah berikutnya:
1. $SCRIPT_DIR/build.sh "$VENV_DIR/bin/python"
2. $SCRIPT_DIR/smoke-test.sh
EOF
