from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook, load_workbook

from app.services.target_workbook_update_service import (
    update_target_workbooks_by_model_series,
)


def _create_target_file(
    path: Path,
    headers: list[str],
    *,
    sheet_name: str = "raw",
    rows: list[list[object]] | None = None,
) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(headers)
    for row in rows or []:
        ws.append(row)
    wb.save(path)
    wb.close()


def test_update_target_appends_filtered_matching_rows(tmp_path):
    target_file = tmp_path / "X100.xlsx"
    _create_target_file(
        target_file,
        ["model_series", "notification", "part_used", "total_cost"],
        rows=[["old", "old", "old", "old"]],
    )

    data_df = pd.DataFrame(
        [
            {
                "model_series": "x100",
                "job_sheet_section": 1,
                "notification": "N1",
                "part_used": "P1",
                "total_cost": 10,
            },
            {
                "model_series": "x100",
                "job_sheet_section": 0,
                "notification": "N0",
                "part_used": "P0",
                "total_cost": 99,
            },
            {
                "model_series": "x100",
                "job_sheet_section": "1",
                "notification": "N2",
                "part_used": "P2",
                "total_cost": 20,
            },
        ]
    )

    results = update_target_workbooks_by_model_series(
        data_df=data_df,
        target_dir=tmp_path,
        match_column="model_series",
        target_sheet_name="raw",
        filter_column="job_sheet_section",
        filter_value=1,
    )

    assert len(results) == 1
    assert results[0].status == "updated"
    assert results[0].rows_written == 2

    wb = load_workbook(target_file)
    ws = wb["raw"]
    assert ws.cell(row=2, column=1).value == "old"
    assert ws.cell(row=2, column=2).value == "old"
    assert ws.cell(row=3, column=1).value == "x100"
    assert ws.cell(row=3, column=2).value == "N1"
    assert ws.cell(row=4, column=2).value == "N2"
    assert ws.max_row == 4
    wb.close()


def test_update_target_skips_existing_duplicate_key_rows(tmp_path):
    target_file = tmp_path / "X100.xlsx"
    _create_target_file(
        target_file,
        ["model_series", "notification", "part_used", "total_cost"],
        rows=[["x100", "N1", "P1", 10]],
    )

    data_df = pd.DataFrame(
        [
            {
                "model_series": "x100",
                "notification": "N1",
                "part_used": "P1",
                "total_cost": 999,
            },
            {
                "model_series": "x100",
                "notification": "N2",
                "part_used": "P2",
                "total_cost": 20,
            },
        ]
    )

    results = update_target_workbooks_by_model_series(
        data_df=data_df,
        target_dir=tmp_path,
        match_column="model_series",
        target_sheet_name="raw",
        duplicate_key_columns=("notification", "model_series", "part_used"),
    )

    assert results[0].status == "updated"
    assert results[0].rows_written == 1

    wb = load_workbook(target_file)
    ws = wb["raw"]
    assert ws.max_row == 3
    assert ws.cell(row=2, column=2).value == "N1"
    assert ws.cell(row=2, column=4).value == 10
    assert ws.cell(row=3, column=2).value == "N2"
    assert ws.cell(row=3, column=4).value == 20
    wb.close()


def test_update_target_skips_file_when_all_rows_already_exist(tmp_path):
    target_file = tmp_path / "X100.xlsx"
    _create_target_file(
        target_file,
        ["model_series", "notification", "part_used"],
        rows=[["x100", "N1", "P1"]],
    )

    data_df = pd.DataFrame(
        [{"model_series": "x100", "notification": "N1", "part_used": "P1"}]
    )

    results = update_target_workbooks_by_model_series(
        data_df=data_df,
        target_dir=tmp_path,
        match_column="model_series",
        target_sheet_name="raw",
        duplicate_key_columns=("notification", "model_series", "part_used"),
    )

    assert results[0].status == "skipped"
    assert results[0].rows_written == 0
    assert "sudah ada" in results[0].reason

    wb = load_workbook(target_file)
    ws = wb["raw"]
    assert ws.max_row == 2
    wb.close()


def test_update_target_fails_when_target_missing_duplicate_key_column(tmp_path):
    target_file = tmp_path / "X100.xlsx"
    _create_target_file(target_file, ["model_series", "notification"])

    data_df = pd.DataFrame(
        [{"model_series": "x100", "notification": "N1", "part_used": "P1"}]
    )

    results = update_target_workbooks_by_model_series(
        data_df=data_df,
        target_dir=tmp_path,
        match_column="model_series",
        target_sheet_name="raw",
        duplicate_key_columns=("notification", "model_series", "part_used"),
    )

    assert results[0].status == "failed"
    assert "part_used" in results[0].reason


def test_update_target_skips_when_no_match(tmp_path):
    target_file = tmp_path / "X200.xlsx"
    _create_target_file(target_file, ["model_series", "notification"])

    data_df = pd.DataFrame([{"model_series": "x100", "notification": "N1"}])

    results = update_target_workbooks_by_model_series(
        data_df=data_df,
        target_dir=tmp_path,
        match_column="model_series",
        target_sheet_name="raw",
    )

    assert results[0].status == "skipped"
    assert "Tidak ada data" in results[0].reason


def test_update_target_raises_when_no_xlsx(tmp_path):
    data_df = pd.DataFrame([{"model_series": "x100"}])

    with pytest.raises(ValueError, match="tidak memiliki file .xlsx"):
        update_target_workbooks_by_model_series(
            data_df=data_df,
            target_dir=tmp_path,
            match_column="model_series",
            target_sheet_name="raw",
        )
