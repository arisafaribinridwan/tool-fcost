#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUNDLE_DIR="${1:-$PROJECT_ROOT/dist/ExcelAutoTool}"
LAUNCHER="$BUNDLE_DIR/run.sh"
TIMEOUT_SECONDS="${SMOKE_TIMEOUT_SECONDS:-8}"
RUNNER=()

if [[ ! -x "$LAUNCHER" ]]; then
  echo "Launcher bundle tidak ditemukan atau tidak executable: $LAUNCHER" >&2
  exit 1
fi

if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
  if command -v xvfb-run >/dev/null 2>&1; then
    RUNNER=("xvfb-run" "-a")
  else
    cat <<'EOF' >&2
Smoke test GUI butuh display server.

Pilihan:
- Jalankan dari sesi desktop yang punya DISPLAY/WAYLAND_DISPLAY
- Atau install xvfb lalu ulangi smoke test
EOF
    exit 1
  fi
fi

set +e
timeout "$TIMEOUT_SECONDS" "${RUNNER[@]}" "$LAUNCHER"
status=$?
set -e

if [[ $status -eq 0 || $status -eq 124 ]]; then
  cat <<EOF
Smoke test lulus:
- Launcher: $LAUNCHER
- Durasi observasi: ${TIMEOUT_SECONDS}s
- Status timeout: $status
EOF
  exit 0
fi

echo "Smoke test gagal dengan exit code: $status" >&2
exit "$status"
