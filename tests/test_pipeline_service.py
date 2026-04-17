from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.services.pipeline_service import run_pipeline
from app.services.pipeline_types import PipelineError


def _write_yaml(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_run_pipeline_happy_path_csv_with_master_and_pivot(app_paths):
    source_path = app_paths.project_root / "source.csv"
    source_df = pd.DataFrame(
        [
            {"tanggal": "2026-04-01", "kode_produk": "A", "qty": 10, "harga": 10000},
            {"tanggal": "2026-04-02", "kode_produk": "B", "qty": 5, "harga": 8000},
            {"tanggal": "2026-04-03", "kode_produk": "A", "qty": 3, "harga": 10000},
        ]
    )
    source_df.to_csv(source_path, index=False)

    master_path = app_paths.masters_dir / "produk.csv"
    master_df = pd.DataFrame(
        [
            {"kode_produk": "A", "nama_produk": "Produk A", "kategori": "Cat 1"},
            {"kode_produk": "B", "nama_produk": "Produk B", "kategori": "Cat 2"},
        ]
    )
    master_df.to_csv(master_path, index=False)

    config_path = app_paths.configs_dir / "report.yaml"
    _write_yaml(
        config_path,
        "\n".join(
            [
                'name: "Laporan Tes"',
                'source_sheet: "Sheet1"',
                "header:",
                '  title: "Laporan Tes"',
                '  period_from_column: "tanggal"',
                "masters:",
                '  - file: "masters/produk.csv"',
                '    key: "kode_produk"',
                "    columns:",
                '      - "nama_produk"',
                '      - "kategori"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "tanggal"',
                '      - "kode_produk"',
                '      - "nama_produk"',
                '      - "kategori"',
                '      - "qty"',
                '  - sheet_name: "Summary"',
                "    pivot:",
                '      index: "kategori"',
                '      values: "qty"',
                '      aggfunc: "sum"',
                "styling:",
                '  header_color: "1F4E78"',
                '  font: "Calibri"',
                '  number_format: "#,##0"',
                '  date_format: "DD/MM/YYYY"',
                '  freeze_pane: "A5"',
            ]
        ),
    )

    logs: list[str] = []
    result = run_pipeline(
        paths=app_paths,
        source_path=source_path,
        config_path=config_path,
        log=logs.append,
    )

    assert result.output_path.exists()
    assert result.source_copy_path.exists()
    assert result.sheets_written == 2
    assert any("Write workbook" in item for item in logs)

    detail_df = pd.read_excel(result.output_path, sheet_name="Detail", skiprows=3)
    summary_df = pd.read_excel(result.output_path, sheet_name="Summary", skiprows=3)

    assert list(detail_df.columns) == [
        "tanggal",
        "kode_produk",
        "nama_produk",
        "kategori",
        "qty",
    ]
    assert len(detail_df) == 3
    assert summary_df.loc[summary_df["kategori"] == "Cat 1", "qty"].iloc[0] == 13
    assert summary_df.loc[summary_df["kategori"] == "Cat 2", "qty"].iloc[0] == 5


def test_run_pipeline_raises_when_master_missing(app_paths):
    source_path = app_paths.project_root / "source.csv"
    pd.DataFrame(
        [{"tanggal": "2026-04-01", "kode_produk": "A", "qty": 10}]
    ).to_csv(source_path, index=False)

    config_path = app_paths.configs_dir / "missing_master.yaml"
    _write_yaml(
        config_path,
        "\n".join(
            [
                'name: "Missing Master"',
                'source_sheet: "Sheet1"',
                "header:",
                '  title: "Missing Master"',
                '  period_from_column: "tanggal"',
                "masters:",
                '  - file: "masters/not_found.csv"',
                '    key: "kode_produk"',
                "    columns:",
                '      - "nama_produk"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "tanggal"',
                '      - "kode_produk"',
                '      - "qty"',
            ]
        ),
    )

    with pytest.raises(PipelineError, match="File master tidak ditemukan"):
        run_pipeline(
            paths=app_paths,
            source_path=source_path,
            config_path=config_path,
            log=lambda _: None,
        )


def test_run_pipeline_raises_when_excel_sheet_missing(app_paths):
    source_path = app_paths.project_root / "source.xlsx"
    pd.DataFrame([{"tanggal": "2026-04-01", "qty": 1}]).to_excel(
        source_path,
        index=False,
        sheet_name="SheetAktual",
    )

    config_path = app_paths.configs_dir / "wrong_sheet.yaml"
    _write_yaml(
        config_path,
        "\n".join(
            [
                'name: "Wrong Sheet"',
                'source_sheet: "SheetTidakAda"',
                "header:",
                '  title: "Wrong Sheet"',
                '  period_from_column: "tanggal"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "tanggal"',
                '      - "qty"',
            ]
        ),
    )

    with pytest.raises(PipelineError, match="Sheet 'SheetTidakAda' tidak ditemukan"):
        run_pipeline(
            paths=app_paths,
            source_path=source_path,
            config_path=config_path,
            log=lambda _: None,
        )
