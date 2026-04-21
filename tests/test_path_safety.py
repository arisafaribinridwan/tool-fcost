from __future__ import annotations

import pandas as pd
import pytest

from app.services.config_service import load_config_payload, validate_config_payload
from app.services.output_service import write_output_workbook
from app.services.transform_service import resolve_master_path
from app.utils.path_safety import resolve_runtime_relative_path


def test_resolve_runtime_relative_path_rejects_traversal(tmp_path):
    with pytest.raises(ValueError, match="tidak boleh mengandung"):
        resolve_runtime_relative_path(tmp_path, "configs/../secret.yaml", root_name="configs")


def test_resolve_runtime_relative_path_rejects_absolute_path(tmp_path):
    with pytest.raises(ValueError, match="absolute path"):
        resolve_runtime_relative_path(tmp_path, "/configs/report.yaml", root_name="configs")


def test_resolve_runtime_relative_path_rejects_windows_drive_path(tmp_path):
    with pytest.raises(ValueError, match="drive path Windows"):
        resolve_runtime_relative_path(tmp_path, "C:/configs/report.yaml", root_name="configs")


def test_resolve_runtime_relative_path_supports_casefold_resolution(tmp_path):
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    config_path = config_dir / "Report.YAML"
    config_path.write_text("name: Test\nsource_sheet: Sheet1\nheader: {}\noutputs:\n  - sheet_name: A\n    columns:\n      - qty\n", encoding="utf-8")

    resolved = resolve_runtime_relative_path(tmp_path, "configs/report.yaml", root_name="configs")

    assert resolved == config_path.resolve()


def test_validate_config_payload_rejects_master_outside_masters_root():
    payload = {
        "name": "Invalid Master Root",
        "source_sheet": "Sheet1",
        "header": {},
        "masters": [{"file": "configs/report.yaml", "key": "kode_produk"}],
        "outputs": [{"sheet_name": "Detail", "columns": ["kode_produk"]}],
    }

    errors = validate_config_payload(payload)

    assert any("masters/" in item for item in errors)


def test_load_config_payload_rejects_config_outside_configs_root(tmp_path):
    outside_path = tmp_path / "report.yaml"
    outside_path.write_text("name: Test\nsource_sheet: Sheet1\nheader: {}\noutputs:\n  - sheet_name: A\n    columns:\n      - qty\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Path config tidak valid"):
        load_config_payload(outside_path)


def test_resolve_master_path_rejects_master_outside_masters_root(tmp_path):
    (tmp_path / "masters").mkdir()

    with pytest.raises(ValueError, match="Path master tidak valid"):
        resolve_master_path("configs/report.yaml", tmp_path, tmp_path / "masters")


def test_write_output_workbook_rejects_output_outside_outputs_root(tmp_path):
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()

    with pytest.raises(ValueError, match="Path output tidak valid"):
        write_output_workbook(
            output_sheets={"Detail": pd.DataFrame([{"qty": 1}])},
            output_path=tmp_path / "report.xlsx",
            outputs_dir=outputs_dir,
            report_title="Test",
            header_cfg={},
            styling_cfg={},
            source_df=pd.DataFrame([{"qty": 1}]),
        )
