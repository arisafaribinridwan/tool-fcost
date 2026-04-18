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


def test_validate_config_payload_rejects_unsafe_master_path():
    payload = {
        "name": "Invalid Master Path",
        "source_sheet": "Sheet1",
        "header": {},
        "masters": [
            {
                "file": "../secret.csv",
                "key": "kode_produk",
            }
        ],
        "outputs": [{"sheet_name": "Detail", "columns": ["kode_produk"]}],
    }

    errors = validate_config_payload(payload)
    assert any("tidak valid" in item for item in errors)


def test_validate_config_payload_accepts_windows_style_master_path():
    payload = {
        "name": "Windows Path",
        "source_sheet": "Sheet1",
        "header": {},
        "masters": [
            {
                "file": r"masters\\Produk.CSV",
                "key": "kode_produk",
            }
        ],
        "outputs": [{"sheet_name": "Detail", "columns": ["kode_produk"]}],
    }

    assert validate_config_payload(payload) == ()


def test_validate_config_payload_rejects_invalid_required_source_columns():
    payload = {
        "name": "Invalid Required Columns",
        "source_sheet": "Sheet1",
        "header": {},
        "required_source_columns": "qty",
        "outputs": [{"sheet_name": "Detail", "columns": ["qty"]}],
    }

    errors = validate_config_payload(payload)
    assert any("required_source_columns" in item for item in errors)


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


def test_validate_config_payload_accepts_transforms_and_group_by_output():
    payload = {
        "name": "Transform Config",
        "source_sheet": "Sheet1",
        "header": {},
        "transforms": [
            {"type": "ensure_optional_columns", "columns": {"catatan": ""}},
            {"type": "filter_rows", "column": "qty", "gte": 5},
            {
                "type": "formula",
                "target": "total",
                "operation": "multiply",
                "operands": [{"column": "qty"}, {"column": "harga"}],
            },
            {
                "type": "conditional",
                "target": "bucket",
                "cases": [
                    {
                        "when": {"column": "total", "gte": 50000},
                        "value": "besar",
                    }
                ],
                "default": "kecil",
            },
        ],
        "outputs": [
            {"sheet_name": "Detail", "columns": ["qty", "harga", "total", "bucket"]},
            {
                "sheet_name": "Summary",
                "group_by": {
                    "by": "bucket",
                    "aggregations": {"qty": "sum", "total": "sum"},
                },
                "columns": ["bucket", "qty", "total"],
            },
        ],
    }

    assert validate_config_payload(payload) == ()


def test_validate_config_payload_rejects_invalid_formula_operation():
    payload = {
        "name": "Invalid Formula",
        "source_sheet": "Sheet1",
        "header": {},
        "transforms": [
            {
                "type": "formula",
                "target": "total",
                "operation": "power",
                "operands": [{"column": "qty"}],
            }
        ],
        "outputs": [{"sheet_name": "Detail", "columns": ["qty", "total"]}],
    }

    errors = validate_config_payload(payload)
    assert any("operation harus salah satu" in item for item in errors)


def test_validate_config_payload_accepts_step_recipe_schema():
    payload = {
        "name": "Monthly Report Final Recipe",
        "datasets": {
            "working_dataset": "result",
            "canonical_columns": ["notification", "section"],
        },
        "steps": [
            {
                "id": "sub_1_copy_gqs",
                "type": "extract_sheet",
                "sheet_selector": {"contains": "GQS"},
                "header_locator": {
                    "type": "required_columns",
                    "scan_rows": [1, 15],
                    "required": ["Notification", "Category"],
                },
                "select": {"Notification": "notification"},
                "write_to": "result",
            }
        ],
        "outputs": [{"sheet_name": "result", "columns": ["notification", "section"]}],
    }

    assert validate_config_payload(payload) == ()


def test_validate_config_payload_rejects_invalid_lookup_rules_matching_schema():
    payload = {
        "name": "Monthly Report Final Recipe",
        "datasets": {
            "working_dataset": "result",
            "canonical_columns": ["notification", "section"],
        },
        "steps": [
            {
                "id": "sub_13_add_symptom",
                "type": "lookup_rules",
                "inputs": ["part_name"],
                "target_column": "symptom",
                "master": {
                    "file": "masters/master_table.xlsx",
                    "sheet": "symptom",
                    "value": "symptom",
                },
                "matching": {
                    "order": "bottom_to_top",
                    "matchers": [
                        {
                            "source": "part_name",
                            "master": "part_name",
                            "mode": "equals",
                            "normalize": {"trim": "yes"},
                        }
                    ],
                },
            }
        ],
        "outputs": [{"sheet_name": "result", "columns": ["notification", "section"]}],
    }

    errors = validate_config_payload(payload)
    assert any(".matching.order harus salah satu" in item for item in errors)
    assert any(".normalize.trim harus berupa boolean." in item for item in errors)
