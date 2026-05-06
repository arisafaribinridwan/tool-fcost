from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook


@dataclass(frozen=True)
class TargetFileUpdateResult:
    file_name: str
    model_series_key: str
    status: str
    rows_written: int
    reason: str = ""


def _normalize_key(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().casefold()


def _get_target_excel_files(target_dir: Path) -> list[Path]:
    return sorted(
        [path for path in target_dir.iterdir() if path.is_file() and path.suffix.lower() == ".xlsx"],
        key=lambda item: item.name.casefold(),
    )


def _normalize_filter_value(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.casefold()


def update_target_workbooks_by_model_series(
    *,
    data_df: pd.DataFrame,
    target_dir: Path,
    match_column: str,
    target_sheet_name: str,
    filter_column: str | None = None,
    filter_value: object | None = None,
) -> list[TargetFileUpdateResult]:
    if not target_dir.exists() or not target_dir.is_dir():
        raise ValueError("Folder tujuan tidak ditemukan atau bukan folder.")

    if match_column not in data_df.columns:
        raise ValueError(f"Kolom match tidak ditemukan pada data source: {match_column}")

    if filter_column is not None and filter_column not in data_df.columns:
        raise ValueError(f"Kolom filter tidak ditemukan pada data source: {filter_column}")

    if filter_column is not None:
        expected_value = _normalize_filter_value(filter_value)
        data_df = data_df.loc[data_df[filter_column].map(_normalize_filter_value) == expected_value].copy()

    target_files = _get_target_excel_files(target_dir)
    if not target_files:
        raise ValueError("Folder tujuan tidak memiliki file .xlsx untuk diproses.")

    results: list[TargetFileUpdateResult] = []
    normalized_series = data_df[match_column].map(_normalize_key)

    for target_file in target_files:
        key = _normalize_key(target_file.stem)
        if not key:
            results.append(
                TargetFileUpdateResult(
                    file_name=target_file.name,
                    model_series_key=key,
                    status="skipped",
                    rows_written=0,
                    reason="Nama file kosong setelah normalisasi.",
                )
            )
            continue

        matched_df = data_df.loc[normalized_series == key].copy()
        if matched_df.empty:
            results.append(
                TargetFileUpdateResult(
                    file_name=target_file.name,
                    model_series_key=key,
                    status="skipped",
                    rows_written=0,
                    reason="Tidak ada data model_series yang cocok.",
                )
            )
            continue

        try:
            workbook = load_workbook(target_file)
            if target_sheet_name not in workbook.sheetnames:
                raise ValueError(f"Sheet '{target_sheet_name}' tidak ditemukan.")
            worksheet = workbook[target_sheet_name]

            header_values = [cell.value for cell in worksheet[1]]
            target_columns = [str(value).strip() for value in header_values if isinstance(value, str) and value.strip()]
            if not target_columns:
                raise ValueError("Header kolom pada baris 1 kosong.")

            write_columns = [column for column in target_columns if column in matched_df.columns]
            if not write_columns:
                raise ValueError("Tidak ada kolom target yang cocok dengan data source.")

            for _, row in matched_df.iterrows():
                row_values: list[object] = []
                for target_column in target_columns:
                    if target_column in matched_df.columns:
                        value = row.get(target_column)
                        row_values.append(None if pd.isna(value) else value)
                    else:
                        row_values.append(None)
                worksheet.append(row_values)

            workbook.save(target_file)
            workbook.close()
            results.append(
                TargetFileUpdateResult(
                    file_name=target_file.name,
                    model_series_key=key,
                    status="updated",
                    rows_written=len(matched_df),
                )
            )
        except Exception as exc:
            results.append(
                TargetFileUpdateResult(
                    file_name=target_file.name,
                    model_series_key=key,
                    status="failed",
                    rows_written=0,
                    reason=str(exc),
                )
            )

    return results
