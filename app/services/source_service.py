from __future__ import annotations

from pathlib import Path
import shutil
from datetime import datetime


SUPPORTED_SOURCE_SUFFIXES = (".xlsx", ".csv")


def validate_source_file(path: Path) -> tuple[str, ...]:
    errors: list[str] = []
    if not path.exists():
        errors.append("File source tidak ditemukan.")
    elif not path.is_file():
        errors.append("Path source harus berupa file.")

    if path.suffix.lower() not in SUPPORTED_SOURCE_SUFFIXES:
        errors.append("Ekstensi source hanya mendukung .xlsx atau .csv.")
    return tuple(errors)


def copy_source_to_uploads(source_path: Path, uploads_dir: Path) -> Path:
    uploads_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_name = f"{source_path.stem}_{timestamp}{source_path.suffix.lower()}"
    target_path = uploads_dir / target_name
    shutil.copy2(source_path, target_path)
    return target_path
