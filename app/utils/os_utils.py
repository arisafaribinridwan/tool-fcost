from __future__ import annotations

import os
from pathlib import Path
import platform
import subprocess


def open_in_file_manager(path: Path) -> None:
    if not path.exists():
        raise RuntimeError(f"Path tidak ditemukan: {path}")

    system_name = platform.system().lower()
    try:
        if system_name == "windows":
            os.startfile(path)  # type: ignore[attr-defined]
        elif system_name == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except OSError as exc:
        raise RuntimeError(f"Gagal membuka path: {path}") from exc
