from __future__ import annotations

from pathlib import Path
import zipfile

from openpyxl.utils.exceptions import InvalidFileException
import pandas as pd
from pandas.errors import EmptyDataError, ParserError


def _resolve_excel_sheet_name(
    workbook: pd.ExcelFile,
    requested_sheet: str,
    *,
    path: Path,
) -> str:
    if requested_sheet in workbook.sheet_names:
        return requested_sheet

    matches = [
        sheet_name
        for sheet_name in workbook.sheet_names
        if sheet_name.casefold() == requested_sheet.casefold()
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(
            f"Nama sheet '{requested_sheet}' ambigu pada file '{path.name}' karena cocok dengan lebih dari satu sheet."
        )
    raise ValueError(f"Sheet '{requested_sheet}' tidak ditemukan pada file '{path.name}'.")


def read_tabular_file(
    path: Path,
    sheet_name: str | None = None,
    *,
    keep_default_na: bool = True,
) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        try:
            return pd.read_csv(path, keep_default_na=keep_default_na)
        except EmptyDataError as exc:
            raise ValueError(
                f"File '{path.name}' kosong atau tidak memiliki data yang bisa dibaca."
            ) from exc
        except (ParserError, UnicodeDecodeError, OSError) as exc:
            raise ValueError(f"File '{path.name}' rusak atau tidak bisa dibaca.") from exc

    if suffix == ".xlsx":
        try:
            with pd.ExcelFile(path) as workbook:
                resolved_sheet = (
                    _resolve_excel_sheet_name(workbook, sheet_name, path=path)
                    if sheet_name is not None
                    else None
                )
                return pd.read_excel(
                    workbook,
                    sheet_name=resolved_sheet,
                    keep_default_na=keep_default_na,
                )
        except ValueError as exc:
            if str(exc).startswith("Sheet '") or str(exc).startswith("Nama sheet '"):
                raise
            raise ValueError(f"File '{path.name}' rusak atau tidak bisa dibaca.") from exc
        except (OSError, zipfile.BadZipFile, InvalidFileException) as exc:
            raise ValueError(f"File '{path.name}' rusak atau tidak bisa dibaca.") from exc

    raise ValueError(f"Format file tidak didukung: {path.suffix}")
