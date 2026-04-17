from __future__ import annotations

from app.services.config_service import discover_configs, validate_config_payload


def test_discover_configs_reads_valid_and_invalid_yaml(tmp_path):
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()

    (configs_dir / "valid.yaml").write_text(
        "\n".join(
            [
                'name: "Valid Config"',
                'source_sheet: "Sheet1"',
                "header: {}",
                "outputs:",
                "  - sheet_name: Detail",
                "    columns:",
                "      - col_a",
            ]
        ),
        encoding="utf-8",
    )

    (configs_dir / "invalid.yaml").write_text(
        "\n".join(
            [
                'name: "Invalid Config"',
                "header: {}",
            ]
        ),
        encoding="utf-8",
    )

    results = discover_configs(configs_dir)
    by_file = {item.path.name: item for item in results}

    assert by_file["valid.yaml"].is_valid is True
    assert by_file["valid.yaml"].name == "Valid Config"
    assert by_file["invalid.yaml"].is_valid is False
    assert "Field wajib belum lengkap" in by_file["invalid.yaml"].errors[0]


def test_validate_config_payload_rejects_non_dict_root():
    errors = validate_config_payload(["not", "a", "dict"])
    assert errors == ("Isi YAML harus berupa object/dictionary di level root.",)


def test_validate_config_payload_accepts_ordered_rules_master():
    payload = {
        "name": "Batch 5",
        "source_sheet": "result",
        "header": {},
        "masters": [
            {
                "file": "masters/master_table.xlsx",
                "sheet_name": "action",
                "strategy": "ordered_rules",
                "target_column": "action",
                "value_column": "action",
                "matchers": [
                    {"source": "part_name", "master": "part_name", "mode": "equals"},
                    {
                        "source": "repair_comment",
                        "master": "repair_comment",
                        "mode": "contains",
                    },
                ],
            }
        ],
        "outputs": [{"sheet_name": "Detail", "columns": ["part_name", "action"]}],
    }

    assert validate_config_payload(payload) == ()


def test_validate_config_payload_rejects_invalid_ordered_rules_matchers():
    payload = {
        "name": "Batch 5 Invalid",
        "source_sheet": "result",
        "header": {},
        "masters": [
            {
                "file": "masters/master_table.xlsx",
                "sheet_name": "action",
                "strategy": "ordered_rules",
                "target_column": "action",
                "value_column": "action",
                "matchers": [
                    {"source": "part_name", "master": "part_name", "mode": "wildcard"}
                ],
            }
        ],
        "outputs": [{"sheet_name": "Detail", "columns": ["part_name", "action"]}],
    }

    errors = validate_config_payload(payload)
    assert any("mode harus salah satu" in item for item in errors)


def test_validate_config_payload_accepts_lookup_with_split_keys_and_normalizer():
    payload = {
        "name": "Batch 5 Defect Category",
        "source_sheet": "result",
        "header": {},
        "masters": [
            {
                "file": "masters/master_table.xlsx",
                "sheet_name": "defect_category",
                "source_key": "action",
                "master_key": "Repair Action",
                "key_normalizer": "compact_text",
                "key_aliases": {"replace_remote_control": "Replace Remote"},
                "columns": ["Category"],
                "rename_columns": {"Category": "defect_category"},
            }
        ],
        "outputs": [{"sheet_name": "Detail", "columns": ["action", "defect_category"]}],
    }

    assert validate_config_payload(payload) == ()


def test_validate_config_payload_accepts_lookup_for_defect_output():
    payload = {
        "name": "Batch 5 Defect",
        "source_sheet": "result",
        "header": {},
        "masters": [
            {
                "file": "masters/master_table.xlsx",
                "sheet_name": "defect_category",
                "source_key": "action",
                "master_key": "Repair Action",
                "key_normalizer": "compact_text",
                "key_aliases": {"replace_remote_control": "Replace Remote"},
                "columns": ["Defect"],
                "rename_columns": {"Defect": "defect"},
            }
        ],
        "outputs": [{"sheet_name": "Detail", "columns": ["action", "defect"]}],
    }

    assert validate_config_payload(payload) == ()
