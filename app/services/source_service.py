from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil

import pandas as pd

from app.services.dataframe_io_service import read_tabular_file


SUPPORTED_SOURCE_SUFFIXES = (".xlsx", ".csv")


def validate_source_file(path: Path) -> tuple[str, ...]:
    errors: list[str] = []
    if not path.exists():
        errors.append("File source tidak ditemukan.")
        return tuple(errors)

    if not path.is_file():
        errors.append("Path source harus berupa file.")
        return tuple(errors)

    if path.suffix.lower() not in SUPPORTED_SOURCE_SUFFIXES:
        errors.append("Ekstensi source hanya mendukung .xlsx atau .csv.")
        return tuple(errors)

    try:
        if path.stat().st_size == 0:
            errors.append("File source kosong.")
    except OSError:
        errors.append("File source tidak bisa diakses.")

    return tuple(errors)


def load_source_dataframe(
    source_path: Path,
    *,
    source_sheet: str | None = None,
) -> pd.DataFrame:
    data_df = read_tabular_file(source_path, sheet_name=source_sheet)
    if len(data_df.columns) == 0:
        raise ValueError(
            f"File source '{source_path.name}' kosong atau tidak memiliki kolom yang bisa dibaca."
        )
    return data_df


def validate_required_source_columns(
    data_df: pd.DataFrame,
    required_columns: list[str] | None,
) -> None:
    if not required_columns:
        return

    missing_columns = [column for column in required_columns if column not in data_df.columns]
    if missing_columns:
        raise ValueError(
            "Kolom wajib source tidak ditemukan: " + ", ".join(missing_columns)
        )


def copy_source_to_uploads(source_path: Path, uploads_dir: Path) -> Path:
    uploads_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_name = f"{source_path.stem}_{timestamp}{source_path.suffix.lower()}"
    target_path = uploads_dir / target_name
    shutil.copy2(source_path, target_path)
    return target_path
