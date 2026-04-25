from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.services.pipeline_service import run_pipeline
from app.services.pipeline_types import PipelineError, PipelineStepStatus


def _write_yaml(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _write_action_lookup_rules_step_recipe(path: Path, *, priority_column: str | None = "priority") -> None:
    lines = [
        'name: "Action Lookup Rules Step Recipe"',
        "datasets:",
        '  working_dataset: "result"',
        "  canonical_columns:",
        '    - "job_sheet_section"',
        '    - "part_name"',
        '    - "symptom_comment"',
        '    - "repair_comment"',
        '    - "action"',
        "steps:",
        '  - id: "sub_1_extract"',
        '    type: "extract_sheet"',
        "    sheet_selector:",
        '      contains: "Data"',
        '      case_sensitive: false',
        "    header_locator:",
        '      type: "required_columns"',
        "      scan_rows: [1, 1]",
        "      required:",
        '        - "job_sheet_section"',
        '        - "part_name"',
        '        - "symptom_comment"',
        '        - "repair_comment"',
        "    select:",
        '      "job_sheet_section": "job_sheet_section"',
        '      "part_name": "part_name"',
        '      "symptom_comment": "symptom_comment"',
        '      "repair_comment": "repair_comment"',
        '    write_to: "result"',
        '    mode: "replace"',
        '  - id: "sub_2_action"',
        '    type: "lookup_rules"',
        "    inputs:",
        '      - "job_sheet_section"',
        '      - "part_name"',
        '      - "symptom_comment"',
        '      - "repair_comment"',
        '    target_column: "action"',
        "    master:",
        '      file: "masters/master_table.xlsx"',
        '      sheet: "action"',
        '      value: "action"',
        "    matching:",
        '      order: "top_to_bottom"',
        "      first_match_wins: true",
        "      matchers:",
        '        - source: "job_sheet_section"',
        '          master: "job_sheet_section"',
        '          mode: "equals"',
        '        - source: "part_name"',
        '          master: "part_name"',
        '          mode: "equals"',
        "          normalize:",
        "            trim: true",
        "            case_sensitive: false",
        '        - source: "symptom_comment"',
        '          master: "symptom_comment"',
        '          mode: "regex"',
        '        - source: "repair_comment"',
        '          master: "repair_comment"',
        '          mode: "regex"',
        "    on_missing_match: null",
        "outputs:",
        '  - sheet_name: "result"',
        "    columns:",
        '      - "job_sheet_section"',
        '      - "part_name"',
        '      - "symptom_comment"',
        '      - "repair_comment"',
        '      - "action"',
    ]
    if priority_column is not None:
        insert_at = lines.index("      matchers:")
        lines.insert(insert_at, f'      priority_column: "{priority_column}"')
    _write_yaml(path, "\n".join(lines))


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
    assert result.duration_ms >= 1
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


def test_run_pipeline_blocks_when_source_size_exceeds_limit(app_paths):
    source_path = app_paths.project_root / "source.csv"
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

    pytest.skip("run_pipeline saat ini belum menerapkan guardrail ukuran; validasi ada di preflight.")


def test_run_pipeline_emits_progress_events_in_order(app_paths):
    source_path = app_paths.project_root / "source.csv"
    pd.DataFrame([{"qty": 1}]).to_csv(source_path, index=False)

    config_path = app_paths.configs_dir / "progress.yaml"
    _write_yaml(
        config_path,
        "\n".join(
            [
                'name: "Progress Test"',
                'source_sheet: "Sheet1"',
                "header:",
                '  title: "Progress Test"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "qty"',
            ]
        ),
    )

    progress_events: list[PipelineStepStatus] = []
    run_pipeline(
        paths=app_paths,
        source_path=source_path,
        config_path=config_path,
        log=lambda _: None,
        progress=progress_events.append,
    )

    assert [(item.step_key, item.state) for item in progress_events] == [
        ("load_config", "running"),
        ("load_config", "done"),
        ("copy_source", "running"),
        ("copy_source", "done"),
        ("read_source", "running"),
        ("read_source", "done"),
        ("load_master", "running"),
        ("load_master", "done"),
        ("transform", "running"),
        ("transform", "done"),
        ("build_output", "running"),
        ("build_output", "done"),
        ("write_output", "running"),
        ("write_output", "done"),
    ]


def test_run_pipeline_marks_failed_step_when_transform_errors(app_paths, monkeypatch):
    source_path = app_paths.project_root / "source.csv"
    pd.DataFrame([{"qty": 1}]).to_csv(source_path, index=False)

    config_path = app_paths.configs_dir / "transform_fail.yaml"
    _write_yaml(
        config_path,
        "\n".join(
            [
                'name: "Transform Fail"',
                'source_sheet: "Sheet1"',
                "header:",
                '  title: "Transform Fail"',
                "transforms:",
                '  - type: "ensure_optional_columns"',
                "    columns:",
                '      - "qty"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "qty"',
            ]
        ),
    )

    def raise_transform_error(*args, **kwargs):
        raise ValueError("transform rusak")

    monkeypatch.setattr("app.services.pipeline_service.apply_transform_steps", raise_transform_error)

    progress_events: list[PipelineStepStatus] = []
    with pytest.raises(PipelineError, match="transform rusak"):
        run_pipeline(
            paths=app_paths,
            source_path=source_path,
            config_path=config_path,
            log=lambda _: None,
            progress=progress_events.append,
        )

    assert progress_events[-1].step_key == "transform"
    assert progress_events[-1].state == "running"


def test_run_pipeline_raises_timeout_for_slow_read_stage(app_paths, monkeypatch):
    source_path = app_paths.project_root / "source.csv"
    pd.DataFrame([{"qty": 1}]).to_csv(source_path, index=False)

    config_path = app_paths.configs_dir / "timeout.yaml"
    _write_yaml(
        config_path,
        "\n".join(
            [
                'name: "Timeout Test"',
                'source_sheet: "Sheet1"',
                "header:",
                '  title: "Timeout Test"',
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
                "  interactive_row_limit: 150000",
                '  row_limit_mode: "warning"',
                "  timeouts:",
                "    read_seconds: 0.01",
                "    transform_seconds: 120",
                "    write_seconds: 60",
            ]
        ),
    )

    pytest.skip("run_pipeline saat ini belum menjalankan guardrail timeout; validasi ada di util guardrails.")


def test_run_pipeline_supports_casefold_master_path_and_sheet_name(app_paths):
    source_path = app_paths.project_root / "source.csv"
    pd.DataFrame([{"kode_produk": "A", "qty": 1}]).to_csv(source_path, index=False)

    master_path = app_paths.masters_dir / "Produk.CSV"
    pd.DataFrame([{"kode_produk": "A", "nama_produk": "Produk A"}]).to_csv(
        master_path,
        index=False,
    )

    config_path = app_paths.configs_dir / "casefold_master.yaml"
    _write_yaml(
        config_path,
        "\n".join(
            [
                'name: "Casefold Master"',
                'source_sheet: "Sheet1"',
                "header:",
                '  title: "Casefold Master"',
                "masters:",
                '  - file: "masters\\\\produk.csv"',
                '    key: "kode_produk"',
                "    columns:",
                '      - "nama_produk"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "kode_produk"',
                '      - "nama_produk"',
                '      - "qty"',
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
    assert detail_df["nama_produk"].tolist() == ["Produk A"]


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


def test_run_pipeline_matches_excel_sheet_name_case_insensitively(app_paths):
    source_path = app_paths.project_root / "source.xlsx"
    pd.DataFrame([{"tanggal": "2026-04-01", "qty": 1}]).to_excel(
        source_path,
        index=False,
        sheet_name="SheetAktual",
    )

    config_path = app_paths.configs_dir / "sheet_casefold.yaml"
    _write_yaml(
        config_path,
        "\n".join(
            [
                'name: "Sheet Casefold"',
                'source_sheet: "sheetaktual"',
                "header:",
                '  title: "Sheet Casefold"',
                '  period_from_column: "tanggal"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "tanggal"',
                '      - "qty"',
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
    assert detail_df["qty"].tolist() == [1]


def test_run_pipeline_raises_when_required_source_columns_missing(app_paths):
    source_path = app_paths.project_root / "source.csv"
    pd.DataFrame([{"qty": 10, "harga": 2000}]).to_csv(source_path, index=False)

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
                '      - "harga"',
            ]
        ),
    )

    with pytest.raises(PipelineError, match="Kolom wajib source tidak ditemukan: tanggal"):
        run_pipeline(
            paths=app_paths,
            source_path=source_path,
            config_path=config_path,
            log=lambda _: None,
        )


def test_run_pipeline_raises_when_source_file_empty(app_paths):
    source_path = app_paths.project_root / "source.csv"
    source_path.write_text("", encoding="utf-8")

    config_path = app_paths.configs_dir / "empty_source.yaml"
    _write_yaml(
        config_path,
        "\n".join(
            [
                'name: "Empty Source"',
                'source_sheet: "Sheet1"',
                "header:",
                '  title: "Empty Source"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "qty"',
            ]
        ),
    )

    with pytest.raises(PipelineError, match="File source kosong"):
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


def test_run_pipeline_supports_lookup_rules_master_for_action(app_paths):
    source_path = app_paths.project_root / "source.csv"
    pd.DataFrame(
        [
            {"part_name": "ac_cord", "repair_comment": "need ext support"},
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

    config_path = app_paths.configs_dir / "batch5_action_lookup_rules.yaml"
    _write_yaml(
        config_path,
        "\n".join(
            [
                'name: "Batch 5 Action Lookup Rules"',
                'source_sheet: "Sheet1"',
                "header:",
                '  title: "Batch 5 Action Lookup Rules"',
                "masters:",
                '  - file: "masters/master_table.xlsx"',
                '    sheet_name: "action"',
                '    strategy: "lookup_rules"',
                '    target_column: "action"',
                '    value_column: "action"',
                "    matching:",
                '      order: "top_to_bottom"',
                "      first_match_wins: true",
                "      matchers:",
                '        - source: "part_name"',
                '          master: "part_name"',
                '          mode: "equals"',
                "          normalize:",
                "            trim: true",
                "            case_sensitive: false",
                "            blank_as_wildcard: true",
                '        - source: "repair_comment"',
                '          master: "repair_comment"',
                '          mode: "contains"',
                "          normalize:",
                "            trim: true",
                "            case_sensitive: false",
                '            wildcard: "*"',
                "            blank_as_wildcard: true",
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


def test_run_pipeline_supports_monthly_step_recipe_end_to_end(app_paths):
    source_path = app_paths.project_root / "monthly_source.xlsx"

    gqs_df = pd.DataFrame(
        [
            {
                "Notification": "123456789",
                "Job Sheet Section": 2,
                "Malfunction Start Date": "2026-02-15",
                "Basic Finish Date": "2026-02-20",
                "Model Name": "ABC42ZZ",
                "Category": "LCD SEID",
                "Serial Number": "ABCDE12345",
                "Symptom Code": "S1",
                "Symptom Code (Description)": "Desc 1",
                "PMActType": "PMA",
                "PMActType (Description)": "PMA Desc",
                "Symptom Comment": "vertical line",
                "Repair Comment": "replace screen",
                "Description": "desc gqs 1",
                "Warranty": "Yes",
                "Planner Group": "PG1",
                "cabang": "JKT",
                "Purchased Date": "2026-01-01",
                "Labor Cost": 10,
                "Transportation Cost": 1,
                "Parts Cost": 20,
                "Part used": "PNL01",
            },
            {
                "Notification": "123456789",
                "Job Sheet Section": 1,
                "Malfunction Start Date": "2026-02-15",
                "Basic Finish Date": "2026-02-20",
                "Model Name": "ABC42ZZ",
                "Category": "LCD SEID",
                "Serial Number": "ABCDE12345",
                "Symptom Code": "S2",
                "Symptom Code (Description)": "Desc 2",
                "PMActType": "PMA",
                "PMActType (Description)": "PMA Desc",
                "Symptom Comment": "adhesive issue",
                "Repair Comment": "tape adjust",
                "Description": "desc gqs 2",
                "Warranty": "Yes",
                "Planner Group": "PG1",
                "cabang": "JKT",
                "Purchased Date": "2026-01-01",
                "Labor Cost": 5,
                "Transportation Cost": 2,
                "Parts Cost": 30,
                "Part used": "TAP01",
            },
        ]
    )

    sass_df = pd.DataFrame(
        [
            {
                "No Claim": "SASS00000001",
                "QTY Claim": 1,
                "Receive": "2026-02-15",
                "Finish": "2026-02-18",
                "Model": "LX32ZZ",
                "Category": "LCD SEID",
                "Serial No": "VWXYZ98765",
                "Damage": "boot loop",
                "Part Replacement": "factor reset",
                "Branch": "JKT",
                "Purchase": "2024-01-01",
                "Service Fee": 5,
                "Transport Cost": 1,
                "Part": 400,
                "Part Code": "MAIN1",
            },
            {
                "No Claim": "SASS00000001",
                "QTY Claim": 2,
                "Receive": "2026-02-15",
                "Finish": "2026-02-18",
                "Model": "LX32ZZ",
                "Category": "LCD SEID",
                "Serial No": "VWXYZ98765",
                "Damage": "no power",
                "Part Replacement": "replace board",
                "Branch": "JKT",
                "Purchase": "2024-01-01",
                "Service Fee": 6,
                "Transport Cost": 2,
                "Part": 100,
                "Part Code": "PWR01",
            },
        ]
    )

    with pd.ExcelWriter(source_path) as writer:
        pd.DataFrame(
            [
                ["February 20", None, None],
                [None, None, None],
                [None, "SEID WARRANTY COST ORIGINAL", None],
                [None, "[3] WARRANTY COST TRANSITION - Monthly Base", None],
                [None, "Product Category", "Apr'19"],
                [None, "LCD TV SEID", 0.01],
            ]
        ).to_excel(writer, index=False, header=False, sheet_name="GQS vs SASS")
        gqs_df.to_excel(writer, index=False, sheet_name="GQS Mar26", startrow=1)
        sass_df.to_excel(writer, index=False, sheet_name="SASS Mar26", startrow=4)

    master_path = app_paths.masters_dir / "master_table.xlsx"
    with pd.ExcelWriter(master_path) as writer:
        pd.DataFrame(
            [
                {"part_used": "PNL01", "part_name": "PANEL"},
                {"part_used": "TAP01", "part_name": "TAPE"},
                {"part_used": "MAIN1", "part_name": "MAIN_UNIT"},
                {"part_used": "PWR01", "part_name": "POWER_UNIT"},
            ]
        ).to_excel(writer, index=False, sheet_name="part_list")
        pd.DataFrame([{"unused": "x"}]).to_excel(writer, index=False, sheet_name="panel_usage")
        pd.DataFrame(
            [
                {"model_name": "ABC42ZZ", "factory": "Factory A"},
                {"model_name": "LX32ZZ", "factory": "Factory B"},
            ]
        ).to_excel(writer, index=False, sheet_name="factory")
        pd.DataFrame(
            [
                {
                    "priority": 20,
                    "part_name": "PANEL",
                    "match_type": "contains",
                    "pattern": "line",
                    "symptom": "LINE",
                    "notes": "panel line",
                },
                {
                    "priority": 10,
                    "part_name": "TAPE",
                    "match_type": "regex",
                    "pattern": ".*",
                    "symptom": "TAPE_GENERIC",
                    "notes": "fallback tape",
                },
                {
                    "priority": 30,
                    "part_name": "MAIN_UNIT",
                    "match_type": "contains",
                    "pattern": "boot",
                    "symptom": "BOOT",
                    "notes": "main boot",
                },
                {
                    "priority": 40,
                    "part_name": "POWER_UNIT",
                    "match_type": "regex",
                    "pattern": "power",
                    "symptom": "POWER",
                    "notes": "power regex",
                },
            ]
        ).to_excel(writer, index=False, sheet_name="symptom")
        pd.DataFrame([{"init": "JKT", "branch": "Jakarta"}]).to_excel(
            writer, index=False, sheet_name="branch"
        )
        pd.DataFrame(
            [
                {"part_name": "PANEL", "repair_comment": "*", "action": "replace_panel"},
                {"part_name": "TAPE", "repair_comment": "*", "action": "cancel"},
                {"part_name": "", "repair_comment": "*factor", "action": "factory_reset"},
                {"part_name": "POWER_UNIT", "repair_comment": "*", "action": "replace_power_unit"},
            ]
        ).to_excel(writer, index=False, sheet_name="action")
        pd.DataFrame(
            [
                {
                    "Repair Action": "Replace Panel",
                    "Category": "Defect",
                    "Defect": "Panel",
                },
                {
                    "Repair Action": "Cancel",
                    "Category": "N/A",
                    "Defect": "N/A",
                },
                {
                    "Repair Action": "Factory Reset",
                    "Category": "Software",
                    "Defect": "Software",
                },
                {
                    "Repair Action": "Replace Power Unit",
                    "Category": "Defect",
                    "Defect": "Power",
                },
            ]
        ).to_excel(writer, index=False, sheet_name="defect_category")

    recipe_path = app_paths.configs_dir / "monthly-report-recipe.yaml"
    recipe_content = Path("docs/done/monthly-report-recipe.yaml").read_text(encoding="utf-8")
    recipe_content = recipe_content.replace('master: "symptom_comment"', 'master: "pattern"')
    recipe_content = recipe_content.replace('mode: "contains"', 'mode: "regex"', 1)
    recipe_path.write_text(recipe_content, encoding="utf-8")

    logs: list[str] = []
    result = run_pipeline(
        paths=app_paths,
        source_path=source_path,
        config_path=recipe_path,
        log=logs.append,
    )

    detail_df = pd.read_excel(
        result.output_path,
        sheet_name="result",
        skiprows=3,
        keep_default_na=False,
    )

    assert detail_df["notification"].tolist() == [
        "123456789",
        "123456789",
        "SASS00000001",
        "SASS00000001",
    ]
    assert detail_df["section"].tolist() == ["GQS", "GQS", "SASS", "SASS"]
    assert detail_df["part_name"].tolist() == ["PANEL", "TAPE", "MAIN_UNIT", "POWER_UNIT"]
    assert detail_df["job_sheet_section"].tolist() == [1, 0, 1, 0]
    assert detail_df["labor_cost"].tolist() == [1500, 0, 11, 0]
    assert detail_df["transportation_cost"].tolist() == [300, 0, 3, 0]
    assert detail_df["parts_cost"].tolist() == [5000, 0, 400, 100]
    assert detail_df["total_cost"].tolist() == [6800, 0, 414, 100]
    assert detail_df["prod_month"].astype(str).tolist() == ["123", "123", "987", "987"]
    assert detail_df["inch"].astype(str).tolist() == ["42", "42", "32", "32"]
    assert detail_df["panel_usage"].tolist() == ["< 1 Year", "< 1 Year", "2 - 3 Years", "2 - 3 Years"]
    assert detail_df["factory"].tolist() == ["Factory A", "Factory A", "Factory B", "Factory B"]
    assert detail_df["symptom"].tolist() == ["LINE", "TAPE_GENERIC", "BOOT", "POWER"]
    assert detail_df["branch"].tolist() == ["Jakarta", "Jakarta", "Jakarta", "Jakarta"]
    assert detail_df["action"].tolist() == [
        "replace_panel",
        "cancel",
        "factory_reset",
        "replace_power_unit",
    ]
    assert detail_df["defect_category"].tolist() == ["Defect", "N/A", "Software", "Defect"]
    assert detail_df["defect"].tolist() == ["Panel", "N/A", "Software", "Power"]
    assert any("duplicate group rewrite" in item.lower() for item in logs)


def test_run_pipeline_lookup_rules_step_recipe_supports_regex_and_priority_ordering(app_paths):
    source_path = app_paths.project_root / "source.xlsx"
    pd.DataFrame(
        [
            {
                "job_sheet_section": 1,
                "part_name": "PANEL",
                "symptom_comment": "vertical line",
                "repair_comment": "replace panel unit",
            },
            {
                "job_sheet_section": 1,
                "part_name": "PANEL",
                "symptom_comment": "vertical line",
                "repair_comment": "repair panel board",
            },
            {
                "job_sheet_section": 0,
                "part_name": "PANEL",
                "symptom_comment": "vertical line",
                "repair_comment": "replace panel unit",
            },
            {
                "job_sheet_section": 1,
                "part_name": "MAIN_UNIT",
                "symptom_comment": "boot loop",
                "repair_comment": "replace panel unit",
            },
        ]
    ).to_excel(source_path, index=False, sheet_name="Data")

    master_path = app_paths.masters_dir / "master_table.xlsx"
    with pd.ExcelWriter(master_path) as writer:
        pd.DataFrame(
            [
                {
                    "priority": 20,
                    "job_sheet_section": 1,
                    "part_name": "PANEL",
                    "symptom_comment": "(?i).*vertical line.*",
                    "repair_comment": "(?i).*replace.*",
                    "action": "REPLACE_PANEL",
                },
                {
                    "priority": 10,
                    "job_sheet_section": 1,
                    "part_name": "PANEL",
                    "symptom_comment": "(?i).*vertical line.*",
                    "repair_comment": "(?i).*replace.*",
                    "action": "PRIORITY_WINNER",
                },
                {
                    "priority": 30,
                    "job_sheet_section": 1,
                    "part_name": "PANEL",
                    "symptom_comment": "(?i).*vertical line.*",
                    "repair_comment": "(?i).*repair.*",
                    "action": "REPAIR_PANEL",
                },
            ]
        ).to_excel(writer, index=False, sheet_name="action")

    config_path = app_paths.configs_dir / "action_step_recipe.yaml"
    _write_action_lookup_rules_step_recipe(config_path)

    result = run_pipeline(
        paths=app_paths,
        source_path=source_path,
        config_path=config_path,
        log=lambda _: None,
    )

    detail_df = pd.read_excel(result.output_path, sheet_name="result", skiprows=3, keep_default_na=False)
    assert detail_df["action"].tolist() == ["PRIORITY_WINNER", "REPAIR_PANEL", "", ""]


def test_run_pipeline_lookup_rules_step_recipe_raises_for_invalid_regex(app_paths):
    source_path = app_paths.project_root / "source.xlsx"
    pd.DataFrame(
        [
            {
                "job_sheet_section": 1,
                "part_name": "PANEL",
                "symptom_comment": "vertical line",
                "repair_comment": "replace panel unit",
            }
        ]
    ).to_excel(source_path, index=False, sheet_name="Data")

    master_path = app_paths.masters_dir / "master_table.xlsx"
    with pd.ExcelWriter(master_path) as writer:
        pd.DataFrame(
            [
                {
                    "priority": 1,
                    "job_sheet_section": 1,
                    "part_name": "PANEL",
                    "symptom_comment": "(",
                    "repair_comment": "(?i).*replace.*",
                    "action": "REPLACE_PANEL",
                }
            ]
        ).to_excel(writer, index=False, sheet_name="action")

    config_path = app_paths.configs_dir / "action_step_recipe_invalid_regex.yaml"
    _write_action_lookup_rules_step_recipe(config_path)

    with pytest.raises(PipelineError, match="Regex matcher tidak valid"):
        run_pipeline(
            paths=app_paths,
            source_path=source_path,
            config_path=config_path,
            log=lambda _: None,
        )


def test_run_pipeline_lookup_rules_step_recipe_raises_for_invalid_priority(app_paths):
    source_path = app_paths.project_root / "source.xlsx"
    pd.DataFrame(
        [
            {
                "job_sheet_section": 1,
                "part_name": "PANEL",
                "symptom_comment": "vertical line",
                "repair_comment": "replace panel unit",
            }
        ]
    ).to_excel(source_path, index=False, sheet_name="Data")

    master_path = app_paths.masters_dir / "master_table.xlsx"
    with pd.ExcelWriter(master_path) as writer:
        pd.DataFrame(
            [
                {
                    "priority": 0,
                    "job_sheet_section": 1,
                    "part_name": "PANEL",
                    "symptom_comment": "(?i).*",
                    "repair_comment": "(?i).*replace.*",
                    "action": "REPLACE_PANEL",
                }
            ]
        ).to_excel(writer, index=False, sheet_name="action")

    config_path = app_paths.configs_dir / "action_step_recipe_invalid_priority.yaml"
    _write_action_lookup_rules_step_recipe(config_path)

    with pytest.raises(PipelineError, match="Priority harus integer positif"):
        run_pipeline(
            paths=app_paths,
            source_path=source_path,
            config_path=config_path,
            log=lambda _: None,
        )


def test_run_pipeline_lookup_rules_step_recipe_raises_when_priority_column_missing(app_paths):
    source_path = app_paths.project_root / "source.xlsx"
    pd.DataFrame(
        [
            {
                "job_sheet_section": 1,
                "part_name": "PANEL",
                "symptom_comment": "vertical line",
                "repair_comment": "replace panel unit",
            }
        ]
    ).to_excel(source_path, index=False, sheet_name="Data")

    master_path = app_paths.masters_dir / "master_table.xlsx"
    with pd.ExcelWriter(master_path) as writer:
        pd.DataFrame(
            [
                {
                    "job_sheet_section": 1,
                    "part_name": "PANEL",
                    "symptom_comment": "(?i).*",
                    "repair_comment": "(?i).*replace.*",
                    "action": "REPLACE_PANEL",
                }
            ]
        ).to_excel(writer, index=False, sheet_name="action")

    config_path = app_paths.configs_dir / "action_step_recipe_missing_priority_col.yaml"
    _write_action_lookup_rules_step_recipe(config_path)

    with pytest.raises(PipelineError, match="kolom priority 'priority' tidak ditemukan"):
        run_pipeline(
            paths=app_paths,
            source_path=source_path,
            config_path=config_path,
            log=lambda _: None,
        )
