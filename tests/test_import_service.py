from __future__ import annotations

import pytest

from app.services.import_service import import_config_to_configs, import_master_to_masters


def test_import_config_to_configs_success(app_paths):
    source = app_paths.project_root / "incoming.yaml"
    source.write_text('name: "Demo"\nsource_sheet: "Sheet1"\nheader: {}\noutputs:\n  - sheet_name: "Detail"\n    columns:\n      - "a"\n', encoding="utf-8")

    imported = import_config_to_configs(source, app_paths.configs_dir)

    assert imported.exists()
    assert imported.parent == app_paths.configs_dir
    assert imported.name == "incoming.yaml"


def test_import_config_to_configs_renames_on_collision(app_paths):
    source = app_paths.project_root / "report.yaml"
    source.write_text("name: test", encoding="utf-8")
    (app_paths.configs_dir / "report.yaml").write_text("name: existing", encoding="utf-8")

    imported = import_config_to_configs(source, app_paths.configs_dir)

    assert imported.name == "report-2.yaml"
    assert imported.exists()


def test_import_config_to_configs_rejects_reserved_registry_name(app_paths):
    source = app_paths.project_root / "job_profiles.yaml"
    source.write_text("jobs: []", encoding="utf-8")

    with pytest.raises(ValueError, match="job_profiles.yaml"):
        import_config_to_configs(source, app_paths.configs_dir)


def test_import_master_to_masters_success(app_paths):
    source = app_paths.project_root / "master.csv"
    source.write_text("a,b\n1,2\n", encoding="utf-8")

    imported = import_master_to_masters(source, app_paths.masters_dir)

    assert imported.exists()
    assert imported.parent == app_paths.masters_dir
    assert imported.name == "master.csv"


def test_import_master_to_masters_rejects_invalid_extension(app_paths):
    source = app_paths.project_root / "master.txt"
    source.write_text("not supported", encoding="utf-8")

    with pytest.raises(ValueError, match="Ekstensi master"):
        import_master_to_masters(source, app_paths.masters_dir)
