from __future__ import annotations

from app.services.source_service import validate_source_file


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
