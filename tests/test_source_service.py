from __future__ import annotations

import pandas as pd
import pytest

from app.services.source_service import (
    load_source_dataframe,
    validate_required_source_columns,
    validate_source_file,
)


def test_validate_source_file_rejects_unsupported_extension(tmp_path):
    source = tmp_path / "data.txt"
    source.write_text("hello", encoding="utf-8")

    errors = validate_source_file(source)
    assert "Ekstensi source hanya mendukung .xlsx atau .csv." in errors


def test_validate_source_file_accepts_csv(tmp_path):
    source = tmp_path / "data.csv"
    source.write_text("a,b\n1,2\n", encoding="utf-8")

    errors = validate_source_file(source)
    assert errors == ()


def test_validate_source_file_rejects_empty_file(tmp_path):
    source = tmp_path / "empty.csv"
    source.write_text("", encoding="utf-8")

    errors = validate_source_file(source)
    assert errors == ("File source kosong.",)


def test_load_source_dataframe_rejects_corrupted_excel(tmp_path):
    source = tmp_path / "broken.xlsx"
    source.write_text("this-is-not-an-excel-file", encoding="utf-8")

    with pytest.raises(ValueError, match="rusak atau tidak bisa dibaca"):
        load_source_dataframe(source, source_sheet="Sheet1")


def test_load_source_dataframe_matches_sheet_case_insensitively(tmp_path):
    source = tmp_path / "data.xlsx"
    pd.DataFrame([{"qty": 1}]).to_excel(source, index=False, sheet_name="SheetAktual")

    data_df = load_source_dataframe(source, source_sheet="sheetaktual")

    assert data_df.to_dict("records") == [{"qty": 1}]


def test_validate_required_source_columns_rejects_missing_columns():
    data_df = pd.DataFrame([{"qty": 1, "harga": 2}])

    with pytest.raises(ValueError, match="Kolom wajib source tidak ditemukan: tanggal"):
        validate_required_source_columns(data_df, ["qty", "tanggal"])
