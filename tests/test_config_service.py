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
