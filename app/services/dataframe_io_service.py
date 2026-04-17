from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_tabular_file(
    path: Path,
    sheet_name: str | None = None,
    *,
    keep_default_na: bool = True,
) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, keep_default_na=keep_default_na)

    if suffix == ".xlsx":
        try:
            if sheet_name is None:
                return pd.read_excel(path, keep_default_na=keep_default_na)
            return pd.read_excel(
                path,
                sheet_name=sheet_name,
                keep_default_na=keep_default_na,
            )
        except ValueError as exc:
            raise ValueError(
                f"Sheet '{sheet_name}' tidak ditemukan pada file '{path.name}'."
            ) from exc

    raise ValueError(f"Format file tidak didukung: {path.suffix}")
