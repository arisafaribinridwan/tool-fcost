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


def test_run_pipeline_supports_ordered_rules_master_for_action(app_paths):
    source_path = app_paths.project_root / "source.csv"
    pd.DataFrame(
        [
            {"part_name": "AC_CORD", "repair_comment": "need ext support"},
            {"part_name": "panel", "repair_comment": "replace unit"},
            {"part_name": "MAIN_UNIT", "repair_comment": "UPGRADE firmware"},
            {"part_name": "Other", "repair_comment": "dibawa customer"},
            {"part_name": "Other", "repair_comment": "unknown"},
        ]
    ).to_csv(source_path, index=False)

    master_path = app_paths.masters_dir / "master_table.xlsx"
    with pd.ExcelWriter(master_path) as writer:
        pd.DataFrame(
            [
                {"part_name": None, "repair_comment": "*ext", "action": "external"},
                {"part_name": "PANEL", "repair_comment": "*", "action": "replace_panel"},
                {
                    "part_name": "MAIN_UNIT",
                    "repair_comment": "*",
                    "action": "replace_main_unit",
                },
                {"part_name": None, "repair_comment": "*bawa", "action": "ZY"},
                {"part_name": None, "repair_comment": "UPGRADE", "action": "upgrade"},
            ]
        ).to_excel(writer, index=False, sheet_name="action")

    config_path = app_paths.configs_dir / "batch5_action.yaml"
    _write_yaml(
        config_path,
        "\n".join(
            [
                'name: "Batch 5 Action"',
                'source_sheet: "Sheet1"',
                "header:",
                '  title: "Batch 5 Action"',
                "masters:",
                '  - file: "masters/master_table.xlsx"',
                '    sheet_name: "action"',
                '    strategy: "ordered_rules"',
                '    target_column: "action"',
                '    value_column: "action"',
                "    matchers:",
                '      - source: "part_name"',
                '        master: "part_name"',
                '        mode: "equals"',
                '      - source: "repair_comment"',
                '        master: "repair_comment"',
                '        mode: "contains"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "part_name"',
                '      - "repair_comment"',
                '      - "action"',
            ]
        ),
    )

    result = run_pipeline(
        paths=app_paths,
        source_path=source_path,
        config_path=config_path,
        log=lambda _: None,
    )

    detail_df = pd.read_excel(result.output_path, sheet_name="Detail", skiprows=3)

    assert detail_df["action"].fillna("").tolist() == [
        "external",
        "replace_panel",
        "replace_main_unit",
        "ZY",
        "",
    ]


def test_run_pipeline_supports_lookup_for_defect_category_from_action(app_paths):
    source_path = app_paths.project_root / "source.csv"
    pd.DataFrame(
        [
            {"action": "replace_panel"},
            {"action": "factory_reset"},
            {"action": "replace_remote_control"},
            {"action": "cancel"},
            {"action": "external"},
            {"action": "unknown_action"},
        ]
    ).to_csv(source_path, index=False)

    master_path = app_paths.masters_dir / "master_table.xlsx"
    with pd.ExcelWriter(master_path) as writer:
        pd.DataFrame(
            [
                {"Repair Action": "Replace Panel", "Category": "Defect"},
                {"Repair Action": "Factory Reset", "Category": "Defect"},
                {"Repair Action": "Replace Remote", "Category": "Defect"},
                {"Repair Action": "Cancel", "Category": "N/A"},
                {"Repair Action": "External", "Category": "N/A"},
            ]
        ).to_excel(writer, index=False, sheet_name="defect_category")

    config_path = app_paths.configs_dir / "batch5_defect_category.yaml"
    _write_yaml(
        config_path,
        "\n".join(
            [
                'name: "Batch 5 Defect Category"',
                'source_sheet: "Sheet1"',
                "header:",
                '  title: "Batch 5 Defect Category"',
                "masters:",
                '  - file: "masters/master_table.xlsx"',
                '    sheet_name: "defect_category"',
                '    source_key: "action"',
                '    master_key: "Repair Action"',
                '    key_normalizer: "compact_text"',
                "    key_aliases:",
                '      replace_remote_control: "Replace Remote"',
                "    columns:",
                '      - "Category"',
                "    rename_columns:",
                '      Category: "defect_category"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "action"',
                '      - "defect_category"',
            ]
        ),
    )

    result = run_pipeline(
        paths=app_paths,
        source_path=source_path,
        config_path=config_path,
        log=lambda _: None,
    )

    detail_df = pd.read_excel(
        result.output_path,
        sheet_name="Detail",
        skiprows=3,
        keep_default_na=False,
    )

    assert detail_df["defect_category"].tolist() == [
        "Defect",
        "Defect",
        "Defect",
        "N/A",
        "N/A",
        "",
    ]


def test_run_pipeline_supports_lookup_for_defect_from_action(app_paths):
    source_path = app_paths.project_root / "source.csv"
    pd.DataFrame(
        [
            {"action": "replace_panel"},
            {"action": "factory_reset"},
            {"action": "replace_remote_control"},
            {"action": "cancel"},
            {"action": "external"},
            {"action": "unknown_action"},
        ]
    ).to_csv(source_path, index=False)

    master_path = app_paths.masters_dir / "master_table.xlsx"
    with pd.ExcelWriter(master_path) as writer:
        pd.DataFrame(
            [
                {"Repair Action": "Replace Panel", "Defect": "Panel"},
                {"Repair Action": "Factory Reset", "Defect": "Software"},
                {"Repair Action": "Replace Remote", "Defect": "Other"},
                {"Repair Action": "Cancel", "Defect": "N/A"},
                {"Repair Action": "External", "Defect": "N/A"},
            ]
        ).to_excel(writer, index=False, sheet_name="defect_category")

    config_path = app_paths.configs_dir / "batch5_defect.yaml"
    _write_yaml(
        config_path,
        "\n".join(
            [
                'name: "Batch 5 Defect"',
                'source_sheet: "Sheet1"',
                "header:",
                '  title: "Batch 5 Defect"',
                "masters:",
                '  - file: "masters/master_table.xlsx"',
                '    sheet_name: "defect_category"',
                '    source_key: "action"',
                '    master_key: "Repair Action"',
                '    key_normalizer: "compact_text"',
                "    key_aliases:",
                '      replace_remote_control: "Replace Remote"',
                "    columns:",
                '      - "Defect"',
                "    rename_columns:",
                '      Defect: "defect"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "action"',
                '      - "defect"',
            ]
        ),
    )

    result = run_pipeline(
        paths=app_paths,
        source_path=source_path,
        config_path=config_path,
        log=lambda _: None,
    )

    detail_df = pd.read_excel(
        result.output_path,
        sheet_name="Detail",
        skiprows=3,
        keep_default_na=False,
    )

    assert detail_df["defect"].tolist() == [
        "Panel",
        "Software",
        "Other",
        "N/A",
        "N/A",
        "",
    ]


def test_run_pipeline_supports_transforms_and_group_by_output(app_paths):
    source_path = app_paths.project_root / "source.csv"
    pd.DataFrame(
        [
            {"kategori": "Cat 1", "qty": 10, "harga": 10000},
            {"kategori": "Cat 2", "qty": 5, "harga": 8000},
            {"kategori": "Cat 3", "qty": 2, "harga": 12000},
        ]
    ).to_csv(source_path, index=False)

    config_path = app_paths.configs_dir / "transform_report.yaml"
    _write_yaml(
        config_path,
        "\n".join(
            [
                'name: "Transform Report"',
                'source_sheet: "Sheet1"',
                "header:",
                '  title: "Transform Report"',
                "transforms:",
                '  - type: "ensure_optional_columns"',
                "    columns:",
                '      catatan: ""',
                '  - type: "filter_rows"',
                '    column: "qty"',
                "    gte: 5",
                '  - type: "formula"',
                '    target: "total"',
                '    operation: "multiply"',
                "    operands:",
                '      - column: "qty"',
                '      - column: "harga"',
                '  - type: "conditional"',
                '    target: "bucket"',
                "    cases:",
                "      - when:",
                '          column: "total"',
                "          gte: 50000",
                '        value: "besar"',
                '    default: "kecil"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "kategori"',
                '      - "qty"',
                '      - "harga"',
                '      - "catatan"',
                '      - "total"',
                '      - "bucket"',
                '  - sheet_name: "Summary"',
                "    group_by:",
                '      by: "bucket"',
                "      aggregations:",
                '        qty: "sum"',
                '        total: "sum"',
                "    columns:",
                '      - "bucket"',
                '      - "qty"',
                '      - "total"',
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

    detail_df = pd.read_excel(
        result.output_path,
        sheet_name="Detail",
        skiprows=3,
        keep_default_na=False,
    )
    summary_df = pd.read_excel(
        result.output_path,
        sheet_name="Summary",
        skiprows=3,
        keep_default_na=False,
    )

    assert detail_df["qty"].tolist() == [10, 5]
    assert detail_df["catatan"].tolist() == ["", ""]
    assert detail_df["total"].tolist() == [100000, 40000]
    assert detail_df["bucket"].tolist() == ["besar", "kecil"]
    assert summary_df["bucket"].tolist() == ["besar", "kecil"]
    assert summary_df["qty"].tolist() == [10, 5]
    assert summary_df["total"].tolist() == [100000, 40000]
    assert any("Apply transform rules" in item for item in logs)
