from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.services.preflight_service import run_preflight


def _write_yaml(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_run_preflight_ready_for_classic_config(app_paths):
    source_path = app_paths.project_root / "source.csv"
    pd.DataFrame([
        {"tanggal": "2026-04-01", "kode_produk": "A", "qty": 10},
    ]).to_csv(source_path, index=False)

    master_path = app_paths.masters_dir / "produk.csv"
    pd.DataFrame([
        {"kode_produk": "A", "nama_produk": "Produk A"},
    ]).to_csv(master_path, index=False)

    config_path = app_paths.configs_dir / "report.yaml"
    _write_yaml(
        config_path,
        "\n".join(
            [
                'name: "Laporan Tes"',
                'source_sheet: "Sheet1"',
                "header:",
                '  title: "Laporan Tes"',
                "required_source_columns:",
                '  - "tanggal"',
                '  - "qty"',
                "masters:",
                '  - file: "masters/produk.csv"',
                '    key: "kode_produk"',
                "    columns:",
                '      - "nama_produk"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "tanggal"',
                '      - "qty"',
            ]
        ),
    )

    result = run_preflight(
        paths=app_paths,
        source_path=source_path,
        config_path=config_path,
    )

    assert result.status == "Ready"
    assert result.output_path is not None
    assert result.can_execute is True
    assert any(item.code == "CLASSIC_SOURCE_READY" for item in result.findings)


def test_run_preflight_blocked_when_required_columns_missing(app_paths):
    source_path = app_paths.project_root / "source.csv"
    pd.DataFrame([
        {"qty": 10},
    ]).to_csv(source_path, index=False)

    config_path = app_paths.configs_dir / "required_columns.yaml"
    _write_yaml(
        config_path,
        "\n".join(
            [
                'name: "Required Columns"',
                'source_sheet: "Sheet1"',
                "header:",
                '  title: "Required Columns"',
                "required_source_columns:",
                '  - "tanggal"',
                '  - "qty"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "qty"',
            ]
        ),
    )

    result = run_preflight(
        paths=app_paths,
        source_path=source_path,
        config_path=config_path,
    )

    assert result.status == "Blocked"
    assert result.can_execute is False
    assert any(item.code == "SOURCE_COLUMNS_MISSING" for item in result.findings)


def test_run_preflight_warns_for_sanitized_output_sheet_names(app_paths):
    source_path = app_paths.project_root / "source.csv"
    pd.DataFrame([
        {"qty": 10},
    ]).to_csv(source_path, index=False)

    config_path = app_paths.configs_dir / "sheet_names.yaml"
    _write_yaml(
        config_path,
        "\n".join(
            [
                'name: "Sanitized Sheets"',
                'source_sheet: "Sheet1"',
                "header:",
                '  title: "Sanitized Sheets"',
                "outputs:",
                '  - sheet_name: "Detail/Raw"',
                "    columns:",
                '      - "qty"',
                '  - sheet_name: "Detail/Raw"',
                "    columns:",
                '      - "qty"',
            ]
        ),
    )

    result = run_preflight(
        paths=app_paths,
        source_path=source_path,
        config_path=config_path,
    )

    assert result.status == "Warning"
    assert result.can_execute is True
    assert any(item.code == "OUTPUT_SHEET_NAME_SANITIZED" for item in result.findings)


def test_run_preflight_blocks_recipe_when_candidate_sheet_missing(app_paths):
    source_path = app_paths.project_root / "source.xlsx"
    with pd.ExcelWriter(source_path) as writer:
        pd.DataFrame([{"A": 1}]).to_excel(writer, index=False, sheet_name="SheetLain")

    config_path = app_paths.configs_dir / "recipe.yaml"
    _write_yaml(
        config_path,
        "\n".join(
            [
                'name: "Recipe Test"',
                "datasets:",
                '  working_dataset: "hasil"',
                "  canonical_columns:",
                '    - "qty"',
                "steps:",
                '  - id: "extract-awal"',
                '    type: "extract_sheet"',
                "    sheet_selector:",
                '      contains: "Data Penjualan"',
                "    header_locator:",
                '      scan_rows: [1, 3]',
                "      required:",
                '        - "qty"',
                "    select:",
                '      qty: "qty"',
                '    write_to: "hasil"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "qty"',
            ]
        ),
    )

    result = run_preflight(
        paths=app_paths,
        source_path=source_path,
        config_path=config_path,
    )

    assert result.status == "Blocked"
    assert any(item.code == "RECIPE_SHEET_NOT_FOUND" for item in result.findings)


def test_run_preflight_blocks_when_source_size_exceeds_limit(app_paths):
    source_path = app_paths.project_root / "oversize.csv"
    source_path.write_bytes(b"x" * 2 * 1024 * 1024)

    config_path = app_paths.configs_dir / "report.yaml"
    _write_yaml(
        config_path,
        "\n".join(
            [
                'name: "Laporan Tes"',
                'source_sheet: "Sheet1"',
                "header:",
                '  title: "Laporan Tes"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "qty"',
            ]
        ),
    )
    _write_yaml(
        app_paths.configs_dir / "app_limits.yaml",
        "\n".join(
            [
                "resource_guardrails:",
                "  max_source_size_mb: 1",
                "  warning_source_size_mb: 0.5",
                "  interactive_row_limit: 150000",
                '  row_limit_mode: "warning"',
                "  timeouts:",
                "    read_seconds: 45",
                "    transform_seconds: 120",
                "    write_seconds: 60",
            ]
        ),
    )

    result = run_preflight(
        paths=app_paths,
        source_path=source_path,
        config_path=config_path,
    )

    assert result.status == "Blocked"
    assert any(item.code == "SOURCE_SIZE_LIMIT_EXCEEDED" for item in result.findings)


def test_run_preflight_warns_when_source_size_near_limit(app_paths):
    source_path = app_paths.project_root / "near_limit.csv"
    source_path.write_bytes(b"x" * int(0.75 * 1024 * 1024))

    config_path = app_paths.configs_dir / "report.yaml"
    _write_yaml(
        config_path,
        "\n".join(
            [
                'name: "Laporan Tes"',
                'source_sheet: "Sheet1"',
                "header:",
                '  title: "Laporan Tes"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "qty"',
            ]
        ),
    )
    _write_yaml(
        app_paths.configs_dir / "app_limits.yaml",
        "\n".join(
            [
                "resource_guardrails:",
                "  max_source_size_mb: 2",
                "  warning_source_size_mb: 0.5",
                "  interactive_row_limit: 150000",
                '  row_limit_mode: "warning"',
                "  timeouts:",
                "    read_seconds: 45",
                "    transform_seconds: 120",
                "    write_seconds: 60",
            ]
        ),
    )

    result = run_preflight(
        paths=app_paths,
        source_path=source_path,
        config_path=config_path,
    )

    assert result.status == "Warning"
    assert any(item.code == "SOURCE_SIZE_NEAR_LIMIT" for item in result.findings)


def test_run_preflight_warns_when_row_limit_exceeded(app_paths):
    source_path = app_paths.project_root / "rows.csv"
    pd.DataFrame([{"qty": idx} for idx in range(4)]).to_csv(source_path, index=False)

    config_path = app_paths.configs_dir / "report.yaml"
    _write_yaml(
        config_path,
        "\n".join(
            [
                'name: "Laporan Tes"',
                'source_sheet: "Sheet1"',
                "header:",
                '  title: "Laporan Tes"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "qty"',
            ]
        ),
    )
    _write_yaml(
        app_paths.configs_dir / "app_limits.yaml",
        "\n".join(
            [
                "resource_guardrails:",
                "  max_source_size_mb: 75",
                "  warning_source_size_mb: 60",
                "  interactive_row_limit: 3",
                '  row_limit_mode: "warning"',
                "  timeouts:",
                "    read_seconds: 45",
                "    transform_seconds: 120",
                "    write_seconds: 60",
            ]
        ),
    )

    result = run_preflight(
        paths=app_paths,
        source_path=source_path,
        config_path=config_path,
    )

    assert result.status == "Warning"
    assert any(item.code == "SOURCE_ROW_LIMIT_EXCEEDED" for item in result.findings)
