#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SPEC_PATH="$SCRIPT_DIR/ExcelAutoTool.spec"
BUILD_INFO_PATH="$PROJECT_ROOT/build-info.json"

if [[ $# -gt 0 ]]; then
  PYTHON_EXE="$1"
else
  for candidate in \
    "$PROJECT_ROOT/.venv-linux-build/bin/python" \
    "$PROJECT_ROOT/.venv/bin/python" \
    "python3"; do
    if [[ "$candidate" == */* ]]; then
      if [[ -x "$candidate" ]]; then
        PYTHON_EXE="$candidate"
        break
      fi
    elif command -v "$candidate" >/dev/null 2>&1; then
      PYTHON_EXE="$candidate"
      break
    fi
  done
fi

: "${PYTHON_EXE:=python3}"

GIT_COMMIT="$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || true)"
GIT_DIRTY="false"
if [[ -n "$GIT_COMMIT" ]] && [[ -n "$(git -C "$PROJECT_ROOT" status --porcelain --untracked-files=no 2>/dev/null)" ]]; then
  GIT_DIRTY="true"
fi

cat >"$BUILD_INFO_PATH" <<EOF
{
  "mode": "bundle",
  "commit": "${GIT_COMMIT}",
  "built_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "dirty": ${GIT_DIRTY},
  "python": "${PYTHON_EXE}"
}
EOF
trap 'rm -f "$BUILD_INFO_PATH"' EXIT

if ! "$PYTHON_EXE" - <<'PY'
import importlib
import sys

required_modules = ("tkinter", "customtkinter", "PyInstaller")
missing = []

for module_name in required_modules:
    try:
        importlib.import_module(module_name)
    except Exception:
        missing.append(module_name)

if missing:
    print(",".join(missing))
    raise SystemExit(1)

print(sys.version)
PY
then
  cat <<'EOF' >&2
Build Linux dibatalkan karena environment Python belum lengkap.

Kebutuhan minimum:
- modul stdlib `tkinter` harus tersedia
- package `customtkinter` harus terpasang
- package `PyInstaller` harus terpasang

Catatan Linux:
- Pada Ubuntu/Linux Mint biasanya perlu install `python3-tk`
- Gunakan Python/virtualenv yang memang punya dukungan Tk sebelum menjalankan build
EOF
  exit 1
fi

"$PYTHON_EXE" -m PyInstaller --clean --noconfirm "$SPEC_PATH"

DIST_ROOT="$PROJECT_ROOT/dist/ExcelAutoTool"
ARCHIVE_PATH="$PROJECT_ROOT/dist/ExcelAutoTool-linux-x86_64.tar.gz"

install -m 755 "$SCRIPT_DIR/run.sh" "$DIST_ROOT/run.sh"
install -d "$DIST_ROOT/configs" "$DIST_ROOT/masters" "$DIST_ROOT/uploads" "$DIST_ROOT/outputs"

if [[ -d "$PROJECT_ROOT/configs" ]]; then
  cp -a "$PROJECT_ROOT/configs/." "$DIST_ROOT/configs/"
fi

if [[ -d "$PROJECT_ROOT/masters" ]]; then
  cp -a "$PROJECT_ROOT/masters/." "$DIST_ROOT/masters/"
fi

tar -C "$PROJECT_ROOT/dist" -czf "$ARCHIVE_PATH" ExcelAutoTool

cat <<EOF
Build Linux selesai:
- Bundle: $DIST_ROOT
- Archive: $ARCHIVE_PATH

Saran pakai:
1. Extract atau simpan bundle di folder yang writable oleh user, mis. \$HOME/Apps/ExcelAutoTool
2. Jalankan ./run.sh
EOF
