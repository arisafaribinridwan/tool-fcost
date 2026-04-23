from __future__ import annotations

from pathlib import Path


def sanitize_log_message(message: str, *, project_root: Path) -> str:
    return _sanitize_path_text(message, project_root=project_root)


def sanitize_exception_message(message: str, *, project_root: Path) -> str:
    return _sanitize_path_text(message, project_root=project_root)


def _sanitize_path_text(message: str, *, project_root: Path) -> str:
    text = str(message)
    try:
        resolved_root = str(project_root.resolve())
    except OSError:
        resolved_root = str(project_root)
    return text.replace(resolved_root, "<runtime>")
