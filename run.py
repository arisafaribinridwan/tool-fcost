from __future__ import annotations

from app import ensure_runtime_dirs
from app.ui import run_desktop_app

if __name__ == "__main__":
    paths = ensure_runtime_dirs()
    run_desktop_app(paths)
