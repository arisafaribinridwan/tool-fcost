from __future__ import annotations

import pandas as pd
import pytest

from app.services.job_profile_service import (
    JOB_PROFILES_FILE_NAME,
    discover_job_profiles,
    get_job_profiles_path,
    load_job_profile_records,
    upsert_job_profile_record,
)


def _write_config(path, *, name: str = "Valid Config") -> None:
    path.write_text(
        "\n".join(
            [
                f'name: "{name}"',
                'source_sheet: "Sheet1"',
                "header:",
                '  title: "Demo"',
                "masters:",
                '  - file: "masters/master_table.xlsx"',
                '    key: "kode_produk"',
                "    columns:",
                '      - "nama_produk"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "kode_produk"',
            ]
        ),
        encoding="utf-8",
    )


def test_load_job_profile_records_returns_empty_when_registry_missing(app_paths):
    assert load_job_profile_records(app_paths.configs_dir) == []


def test_upsert_job_profile_record_creates_registry_and_persists_job(app_paths):
    _write_config(app_paths.configs_dir / "report.yaml")

    record = upsert_job_profile_record(
        app_paths.configs_dir,
        label="Monthly Report",
        config_file="report.yaml",
        enabled=True,
    )

    registry_path = get_job_profiles_path(app_paths.configs_dir)
    assert registry_path.name == JOB_PROFILES_FILE_NAME
    assert registry_path.exists()
    assert record.label == "Monthly Report"
    assert record.config_file == "report.yaml"

    loaded = load_job_profile_records(app_paths.configs_dir)
    assert [(item.id, item.label, item.config_file, item.enabled) for item in loaded] == [
        (record.id, "Monthly Report", "report.yaml", True)
    ]


def test_upsert_job_profile_record_rejects_duplicate_label(app_paths):
    _write_config(app_paths.configs_dir / "report.yaml")
    _write_config(app_paths.configs_dir / "report-2.yaml", name="Config 2")

    upsert_job_profile_record(
        app_paths.configs_dir,
        label="Monthly Report",
        config_file="report.yaml",
        enabled=True,
    )

    with pytest.raises(ValueError, match="Nama job sudah dipakai"):
        upsert_job_profile_record(
            app_paths.configs_dir,
            label="Monthly Report",
            config_file="report-2.yaml",
            enabled=True,
        )


def test_discover_job_profiles_marks_missing_config_invalid(app_paths):
    upsert_job_profile_record(
        app_paths.configs_dir,
        label="Job Missing Config",
        config_file="missing.yaml",
        enabled=True,
    )

    items = discover_job_profiles(app_paths.configs_dir)
    assert len(items) == 1
    assert items[0].is_valid is False
    assert "Config job tidak ditemukan" in items[0].errors[0]


def test_discover_job_profiles_marks_invalid_config_invalid(app_paths):
    (app_paths.configs_dir / "broken.yaml").write_text(
        "\n".join(
            [
                'name: "Broken Config"',
                "header: {}",
            ]
        ),
        encoding="utf-8",
    )
    upsert_job_profile_record(
        app_paths.configs_dir,
        label="Broken Job",
        config_file="broken.yaml",
        enabled=True,
    )

    items = discover_job_profiles(app_paths.configs_dir)
    assert len(items) == 1
    assert items[0].is_valid is False
    assert "Config job tidak valid" in items[0].errors[0]


def test_discover_job_profiles_extracts_master_files_for_recipe_config(app_paths):
    source_recipe = app_paths.configs_dir / "recipe.yaml"
    source_recipe.write_text(
        "\n".join(
            [
                'name: "Recipe Config"',
                "datasets:",
                '  working_dataset: "result"',
                "  canonical_columns:",
                '    - "part_name"',
                '    - "symptom"',
                "steps:",
                '  - id: "step_1"',
                '    type: "lookup_rules"',
                "    inputs:",
                '      - "part_name"',
                '    target_column: "symptom"',
                "    master:",
                '      file: "masters/master_table.xlsx"',
                '      sheet: "symptom"',
                '      value: "symptom"',
                "    matching:",
                '      order: "top_to_bottom"',
                "      matchers:",
                '        - source: "part_name"',
                '          master: "part_name"',
                '          mode: "equals"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "part_name"',
                '      - "symptom"',
            ]
        ),
        encoding="utf-8",
    )

    upsert_job_profile_record(
        app_paths.configs_dir,
        label="Recipe Job",
        config_file="recipe.yaml",
        enabled=True,
    )

    items = discover_job_profiles(app_paths.configs_dir)
    assert len(items) == 1
    assert items[0].is_valid is True
    assert items[0].master_files == ("masters/master_table.xlsx",)


def test_job_profile_selected_config_can_run_pipeline(app_paths):
    source_path = app_paths.project_root / "source.csv"
    pd.DataFrame([{"kode_produk": "A"}]).to_csv(source_path, index=False)

    master_path = app_paths.masters_dir / "master_table.xlsx"
    with pd.ExcelWriter(master_path) as writer:
        pd.DataFrame([{"kode_produk": "A", "nama_produk": "Produk A"}]).to_excel(
            writer,
            index=False,
            sheet_name="Sheet1",
        )

    _write_config(app_paths.configs_dir / "report.yaml")
    upsert_job_profile_record(
        app_paths.configs_dir,
        label="Monthly Report",
        config_file="report.yaml",
        enabled=True,
    )

    items = discover_job_profiles(app_paths.configs_dir)
    assert len(items) == 1
    assert items[0].config_path == app_paths.configs_dir / "report.yaml"
