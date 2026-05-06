from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
from openpyxl.worksheet.worksheet import Worksheet


@dataclass(frozen=True)
class TargetFileUpdateResult:
    file_name: str
    model_series_key: str
    status: str
    rows_written: int
    reason: str = ""


def _normalize_key(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.casefold()


def _get_target_excel_files(target_dir: Path) -> list[Path]:
    return sorted(
        [
            path
            for path in target_dir.iterdir()
            if path.is_file() and path.suffix.lower() == ".xlsx"
        ],
        key=lambda item: item.name.casefold(),
    )


def _normalize_filter_value(value: object) -> str:
    return _normalize_key(value)


def _build_row_key(
    row_values: dict[str, object],
    key_columns: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(_normalize_key(row_values.get(column)) for column in key_columns)


def _collect_existing_keys(
    worksheet: Worksheet,
    *,
    target_columns: list[str],
    duplicate_key_columns: tuple[str, ...],
) -> set[tuple[str, ...]]:
    column_index_by_name = {
        column: index + 1 for index, column in enumerate(target_columns)
    }
    missing_target_columns = [
        column for column in duplicate_key_columns if column not in column_index_by_name
    ]
    if missing_target_columns:
        raise ValueError(
            "Kolom duplicate key tidak ditemukan pada sheet target: "
            + ", ".join(missing_target_columns)
        )

    existing_keys: set[tuple[str, ...]] = set()
    for row_index in range(2, worksheet.max_row + 1):
        row_values = {
            column: worksheet.cell(
                row=row_index,
                column=column_index_by_name[column],
            ).value
            for column in duplicate_key_columns
        }
        row_key = _build_row_key(row_values, duplicate_key_columns)
        if any(row_key):
            existing_keys.add(row_key)
    return existing_keys


def _filter_new_rows(
    matched_df: pd.DataFrame,
    *,
    existing_keys: set[tuple[str, ...]],
    duplicate_key_columns: tuple[str, ...],
) -> pd.DataFrame:
    if not duplicate_key_columns:
        return matched_df

    missing_source_columns = [
        column for column in duplicate_key_columns if column not in matched_df.columns
    ]
    if missing_source_columns:
        raise ValueError(
            "Kolom duplicate key tidak ditemukan pada data source: "
            + ", ".join(missing_source_columns)
        )

    new_row_indexes: list[object] = []
    seen_in_batch: set[tuple[str, ...]] = set()
    for row_index, row in matched_df.iterrows():
        row_key = _build_row_key(row.to_dict(), duplicate_key_columns)
        if row_key in existing_keys or row_key in seen_in_batch:
            continue
        seen_in_batch.add(row_key)
        new_row_indexes.append(row_index)

    return matched_df.loc[new_row_indexes].copy()


_NO_FILL = PatternFill(fill_type=None)


def _clear_data_row_fills(worksheet: Worksheet) -> None:
    if worksheet.max_row < 2:
        return
    for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row):
        for cell in row:
            cell.fill = _NO_FILL


def _apply_row_fill(
    worksheet: Worksheet,
    *,
    row_index: int,
    column_count: int,
    color: str,
) -> None:
    fill = PatternFill(fill_type="solid", fgColor=color.upper())
    for column_index in range(1, column_count + 1):
        worksheet.cell(row=row_index, column=column_index).fill = fill


def update_target_workbooks_by_model_series(
    *,
    data_df: pd.DataFrame,
    target_dir: Path,
    match_column: str,
    target_sheet_name: str,
    filter_column: str | None = None,
    filter_value: object | None = None,
    duplicate_key_columns: tuple[str, ...] = (),
    new_row_color: str | None = None,
) -> list[TargetFileUpdateResult]:
    if not target_dir.exists() or not target_dir.is_dir():
        raise ValueError("Folder tujuan tidak ditemukan atau bukan folder.")

    if match_column not in data_df.columns:
        raise ValueError(
            f"Kolom match tidak ditemukan pada data source: {match_column}"
        )

    if filter_column is not None and filter_column not in data_df.columns:
        raise ValueError(
            f"Kolom filter tidak ditemukan pada data source: {filter_column}"
        )

    if filter_column is not None:
        expected_value = _normalize_filter_value(filter_value)
        filter_mask = (
            data_df[filter_column].map(_normalize_filter_value) == expected_value
        )
        data_df = data_df.loc[filter_mask].copy()

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
            target_columns = [
                str(value).strip()
                for value in header_values
                if isinstance(value, str) and value.strip()
            ]
            if not target_columns:
                raise ValueError("Header kolom pada baris 1 kosong.")

            write_columns = [
                column for column in target_columns if column in matched_df.columns
            ]
            if not write_columns:
                raise ValueError(
                    "Tidak ada kolom target yang cocok dengan data source."
                )

            if duplicate_key_columns:
                existing_keys = _collect_existing_keys(
                    worksheet,
                    target_columns=target_columns,
                    duplicate_key_columns=duplicate_key_columns,
                )
                matched_df = _filter_new_rows(
                    matched_df,
                    existing_keys=existing_keys,
                    duplicate_key_columns=duplicate_key_columns,
                )
                if matched_df.empty:
                    workbook.close()
                    results.append(
                        TargetFileUpdateResult(
                            file_name=target_file.name,
                            model_series_key=key,
                            status="skipped",
                            rows_written=0,
                            reason="Semua data sudah ada di sheet target.",
                        )
                    )
                    continue

            if new_row_color:
                _clear_data_row_fills(worksheet)

            for _, row in matched_df.iterrows():
                row_values: list[object] = []
                for target_column in target_columns:
                    if target_column in matched_df.columns:
                        value = row.get(target_column)
                        row_values.append(None if pd.isna(value) else value)
                    else:
                        row_values.append(None)
                worksheet.append(row_values)
                if new_row_color:
                    _apply_row_fill(
                        worksheet,
                        row_index=worksheet.max_row,
                        column_count=len(target_columns),
                        color=new_row_color,
                    )

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
