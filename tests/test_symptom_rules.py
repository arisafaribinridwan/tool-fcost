from __future__ import annotations

import pandas as pd
import pytest

from app.services.transform_service import match_symptom_rule, prepare_symptom_rule_table
from app.services.pipeline_service import run_pipeline
from app.services.pipeline_types import PipelineError


def _write_symptom_step_recipe(path, inputs: list[str]) -> None:
    path.write_text(
        "\n".join(
            [
                'name: "Symptom Step Recipe"',
                "datasets:",
                '  working_dataset: "result"',
                "  canonical_columns:",
                '    - "part_name"',
                '    - "symptom_comment"',
                '    - "repair_comment"',
                '    - "symptom_code_description"',
                '    - "symptom"',
                "steps:",
                '  - id: "extract"',
                '    type: "extract_sheet"',
                "    sheet_selector:",
                '      contains: "Data"',
                '      case_sensitive: false',
                "    header_locator:",
                '      type: "required_columns"',
                "      scan_rows: [1, 1]",
                "      required:",
                '        - "part_name"',
                '        - "symptom_comment"',
                "    select:",
                '      "part_name": "part_name"',
                '      "symptom_comment": "symptom_comment"',
                '      "repair_comment": "repair_comment"',
                '      "symptom_code_description": "symptom_code_description"',
                '    write_to: "result"',
                '    mode: "replace"',
                '  - id: "add_symptom"',
                '    type: "lookup_rules"',
                "    inputs:",
                *[f'      - "{input_column}"' for input_column in inputs],
                '    target_column: "symptom"',
                "    master:",
                '      file: "masters/master_table.xlsx"',
                '      sheet: "symptom"',
                '      value: "symptom"',
                "    matching:",
                '      order: "top_to_bottom"',
                "      first_match_wins: true",
                "      matchers:",
                '        - source: "part_name"',
                '          master: "part_name"',
                '          mode: "equals"',
                "          normalize:",
                "            trim: true",
                "            case_sensitive: true",
                '        - source: "symptom_comment"',
                '          master: "symptom_comment"',
                '          mode: "contains"',
                "    on_missing_match: null",
                "outputs:",
                '  - sheet_name: "result"',
                "    columns:",
                '      - "part_name"',
                '      - "symptom_comment"',
                '      - "repair_comment"',
                '      - "symptom_code_description"',
                '      - "symptom"',
            ]
        ),
        encoding="utf-8",
    )


def test_prepare_symptom_rule_table_rejects_missing_required_columns():
    master_df = pd.DataFrame(
        [{"priority": 10, "part_name": "PANEL", "pattern": "line", "symptom": "LINE"}]
    )

    with pytest.raises(ValueError, match="wajib memiliki kolom"):
        prepare_symptom_rule_table(master_df, context="Sheet symptom")


def test_prepare_symptom_rule_table_rejects_invalid_priority():
    master_df = pd.DataFrame(
        [
            {
                "priority": 0,
                "part_name": "PANEL",
                "match_type": "contains",
                "pattern": "line",
                "symptom": "LINE",
                "notes": "invalid",
            }
        ]
    )

    with pytest.raises(ValueError, match="Priority harus integer positif"):
        prepare_symptom_rule_table(master_df, context="Sheet symptom")


def test_prepare_symptom_rule_table_rejects_invalid_match_type():
    master_df = pd.DataFrame(
        [
            {
                "priority": 10,
                "part_name": "PANEL",
                "match_type": "wildcard",
                "pattern": "line",
                "symptom": "LINE",
                "notes": "invalid",
            }
        ]
    )

    with pytest.raises(ValueError, match="match_type tidak didukung"):
        prepare_symptom_rule_table(master_df, context="Sheet symptom")


def test_prepare_symptom_rule_table_sorts_by_priority_then_row_order():
    master_df = pd.DataFrame(
        [
            {
                "priority": 20,
                "part_name": "PANEL",
                "match_type": "contains",
                "pattern": "later",
                "symptom": "LATER",
                "notes": "later",
            },
            {
                "priority": 10,
                "part_name": "PANEL",
                "match_type": "contains",
                "pattern": "first",
                "symptom": "FIRST",
                "notes": "first",
            },
            {
                "priority": 20,
                "part_name": "PANEL",
                "match_type": "contains",
                "pattern": "tie-breaker",
                "symptom": "TIE",
                "notes": "tie",
            },
        ]
    )

    prepared = prepare_symptom_rule_table(master_df, context="Sheet symptom")

    assert prepared["pattern"].tolist() == ["first", "later", "tie-breaker"]


def test_prepare_symptom_rule_table_compiles_regex_once_per_rule():
    master_df = pd.DataFrame(
        [
            {
                "priority": 10,
                "part_name": "PANEL",
                "match_type": "regex",
                "pattern": r"vertical\s+line",
                "symptom": "VERTICAL_LINE",
                "notes": "compiled",
            }
        ]
    )

    prepared = prepare_symptom_rule_table(master_df, context="Sheet symptom")

    compiled = prepared.iloc[0]["_compiled_pattern"]
    assert compiled is not None
    assert compiled.pattern == r"vertical\s+line"


def test_prepare_symptom_rule_table_rejects_regex_too_long():
    master_df = pd.DataFrame(
        [
            {
                "priority": 10,
                "part_name": "PANEL",
                "match_type": "regex",
                "pattern": "a" * 513,
                "symptom": "LONG_PATTERN",
                "notes": "too long",
            }
        ]
    )

    with pytest.raises(ValueError, match="regex terlalu panjang"):
        prepare_symptom_rule_table(master_df, context="Sheet symptom")


def test_match_symptom_rule_keeps_equals_behavior():
    rule_row = pd.Series(
        {
            "match_type": "equals",
            "pattern": " Vertical   Line ",
        }
    )

    assert match_symptom_rule("vertical line", rule_row) is True
    assert match_symptom_rule("vertical lines", rule_row) is False


def test_match_symptom_rule_keeps_contains_behavior():
    rule_row = pd.Series(
        {
            "match_type": "contains",
            "pattern": "Line",
        }
    )

    assert match_symptom_rule("vertical line defect", rule_row) is True
    assert match_symptom_rule("boot failure", rule_row) is False


def test_match_symptom_rule_uses_precompiled_regex():
    prepared = prepare_symptom_rule_table(
        pd.DataFrame(
            [
                {
                    "priority": 10,
                    "part_name": "PANEL",
                    "match_type": "regex",
                    "pattern": r"vertical\s+line",
                    "symptom": "VERTICAL_LINE",
                    "notes": "compiled",
                }
            ]
        ),
        context="Sheet symptom",
    )

    rule_row = prepared.iloc[0]
    assert match_symptom_rule("Vertical   Line", rule_row) is True
    assert match_symptom_rule("horizontal line", rule_row) is False


def test_run_pipeline_rejects_invalid_symptom_sheet_priority(app_paths):
    source_path = app_paths.project_root / "source.csv"
    pd.DataFrame([{"part_name": "PANEL", "symptom_comment": "line"}]).to_csv(source_path, index=False)

    master_path = app_paths.masters_dir / "master_table.xlsx"
    with pd.ExcelWriter(master_path) as writer:
        pd.DataFrame(
            [
                {
                    "priority": 0,
                    "part_name": "PANEL",
                    "match_type": "contains",
                    "pattern": "line",
                    "symptom": "LINE",
                    "notes": "invalid priority",
                }
            ]
        ).to_excel(writer, index=False, sheet_name="symptom")

    config_path = app_paths.configs_dir / "symptom_invalid_priority.yaml"
    config_path.write_text(
        "\n".join(
            [
                'name: "Symptom Invalid Priority"',
                'source_sheet: "Sheet1"',
                "header:",
                '  title: "Symptom Invalid Priority"',
                "masters:",
                '  - file: "masters/master_table.xlsx"',
                '    sheet_name: "symptom"',
                '    strategy: "lookup_rules"',
                '    target_column: "symptom"',
                '    value_column: "symptom"',
                "    matching:",
                '      order: "top_to_bottom"',
                "      first_match_wins: true",
                "      matchers:",
                '        - source: "part_name"',
                '          master: "part_name"',
                '          mode: "equals"',
                '        - source: "symptom_comment"',
                '          master: "pattern"',
                '          mode: "contains"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "part_name"',
                '      - "symptom_comment"',
                '      - "symptom"',
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(PipelineError, match="Priority harus integer positif"):
        run_pipeline(
            paths=app_paths,
            source_path=source_path,
            config_path=config_path,
            log=lambda _: None,
        )


def test_run_pipeline_uses_symptom_priority_ordering(app_paths):
    source_path = app_paths.project_root / "source.csv"
    pd.DataFrame([{"part_name": "PANEL", "symptom_comment": "vertical line"}]).to_csv(source_path, index=False)

    master_path = app_paths.masters_dir / "master_table.xlsx"
    with pd.ExcelWriter(master_path) as writer:
        pd.DataFrame(
            [
                {
                    "priority": 20,
                    "part_name": "PANEL",
                    "match_type": "contains",
                    "pattern": "line",
                    "symptom": "GENERIC_LINE",
                    "notes": "generic",
                },
                {
                    "priority": 10,
                    "part_name": "PANEL",
                    "match_type": "regex",
                    "pattern": r"vertical\s+line",
                    "symptom": "VERTICAL_LINE",
                    "notes": "specific first",
                },
            ]
        ).to_excel(writer, index=False, sheet_name="symptom")

    config_path = app_paths.configs_dir / "symptom_priority.yaml"
    config_path.write_text(
        "\n".join(
            [
                'name: "Symptom Priority"',
                'source_sheet: "Sheet1"',
                "header:",
                '  title: "Symptom Priority"',
                "masters:",
                '  - file: "masters/master_table.xlsx"',
                '    sheet_name: "symptom"',
                '    strategy: "lookup_rules"',
                '    target_column: "symptom"',
                '    value_column: "symptom"',
                "    matching:",
                '      order: "top_to_bottom"',
                "      first_match_wins: true",
                "      matchers:",
                '        - source: "part_name"',
                '          master: "part_name"',
                '          mode: "equals"',
                '        - source: "symptom_comment"',
                '          master: "pattern"',
                '          mode: "regex"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "symptom"',
            ]
        ),
        encoding="utf-8",
    )

    result = run_pipeline(
        paths=app_paths,
        source_path=source_path,
        config_path=config_path,
        log=lambda _: None,
    )

    detail_df = pd.read_excel(result.output_path, sheet_name="Detail", skiprows=3)
    assert detail_df["symptom"].tolist() == ["VERTICAL_LINE"]


def test_run_pipeline_step_recipe_uses_symptom_fallback_source_order(app_paths):
    source_path = app_paths.project_root / "source.xlsx"
    pd.DataFrame(
        [
            {
                "part_name": "PANEL",
                "symptom_comment": "",
                "repair_comment": "UNIT-PANEL-GANTI-BLANK",
                "symptom_code_description": "",
            },
            {
                "part_name": "PANEL",
                "symptom_comment": "",
                "repair_comment": "",
                "symptom_code_description": "no picture",
            },
            {
                "part_name": "PANEL",
                "symptom_comment": "vertical line",
                "repair_comment": "UNIT-PANEL-GANTI-BLANK",
                "symptom_code_description": "no picture",
            },
        ]
    ).to_excel(source_path, index=False, sheet_name="Data")

    master_path = app_paths.masters_dir / "master_table.xlsx"
    with pd.ExcelWriter(master_path) as writer:
        pd.DataFrame(
            [
                {
                    "priority": 10,
                    "part_name": "PANEL",
                    "match_type": "contains",
                    "pattern": "blank",
                    "symptom": "BLANK",
                    "notes": "repair fallback",
                },
                {
                    "priority": 20,
                    "part_name": "PANEL",
                    "match_type": "contains",
                    "pattern": "no picture",
                    "symptom": "NO_PICTURE",
                    "notes": "description fallback",
                },
                {
                    "priority": 30,
                    "part_name": "PANEL",
                    "match_type": "contains",
                    "pattern": "vertical line",
                    "symptom": "VERTICAL_LINE",
                    "notes": "specific symptom comment",
                },
                {
                    "priority": 40,
                    "part_name": "PANEL",
                    "match_type": "contains",
                    "pattern": "line",
                    "symptom": "LINE",
                    "notes": "generic symptom comment",
                },
            ]
        ).to_excel(writer, index=False, sheet_name="symptom")

    config_path = app_paths.configs_dir / "symptom_step_recipe.yaml"
    _write_symptom_step_recipe(
        config_path,
        ["part_name", "symptom_comment", "repair_comment", "symptom_code_description"],
    )

    result = run_pipeline(
        paths=app_paths,
        source_path=source_path,
        config_path=config_path,
        log=lambda _: None,
    )

    detail_df = pd.read_excel(result.output_path, sheet_name="result", skiprows=3, keep_default_na=False)
    assert detail_df["symptom"].tolist() == ["BLANK", "NO_PICTURE", "VERTICAL_LINE"]


def test_run_pipeline_step_recipe_keeps_symptom_comment_only_compatibility(app_paths):
    source_path = app_paths.project_root / "source.xlsx"
    pd.DataFrame(
        [
            {
                "part_name": "PANEL",
                "symptom_comment": "",
                "repair_comment": "UNIT-PANEL-GANTI-BLANK",
                "symptom_code_description": "no picture",
            }
        ]
    ).to_excel(source_path, index=False, sheet_name="Data")

    master_path = app_paths.masters_dir / "master_table.xlsx"
    with pd.ExcelWriter(master_path) as writer:
        pd.DataFrame(
            [
                {
                    "priority": 10,
                    "part_name": "PANEL",
                    "match_type": "contains",
                    "pattern": "blank",
                    "symptom": "BLANK",
                    "notes": "fallback not configured",
                }
            ]
        ).to_excel(writer, index=False, sheet_name="symptom")

    config_path = app_paths.configs_dir / "symptom_step_recipe_compat.yaml"
    _write_symptom_step_recipe(config_path, ["part_name", "symptom_comment"])

    result = run_pipeline(
        paths=app_paths,
        source_path=source_path,
        config_path=config_path,
        log=lambda _: None,
    )

    detail_df = pd.read_excel(result.output_path, sheet_name="result", skiprows=3, keep_default_na=False)
    assert detail_df["symptom"].tolist() == [""]


def test_run_pipeline_legacy_symptom_rules_use_available_fallback_columns(app_paths):
    source_path = app_paths.project_root / "source.csv"
    pd.DataFrame(
        [
            {
                "part_name": "PANEL",
                "symptom_comment": "",
                "repair_comment": "UNIT-PANEL-GANTI-BLANK",
                "symptom_code_description": "",
            },
            {
                "part_name": "PANEL",
                "symptom_comment": "",
                "repair_comment": "",
                "symptom_code_description": "no picture",
            },
        ]
    ).to_csv(source_path, index=False)

    master_path = app_paths.masters_dir / "master_table.xlsx"
    with pd.ExcelWriter(master_path) as writer:
        pd.DataFrame(
            [
                {
                    "priority": 10,
                    "part_name": "PANEL",
                    "match_type": "contains",
                    "pattern": "blank",
                    "symptom": "BLANK",
                    "notes": "repair fallback",
                },
                {
                    "priority": 20,
                    "part_name": "PANEL",
                    "match_type": "contains",
                    "pattern": "no picture",
                    "symptom": "NO_PICTURE",
                    "notes": "description fallback",
                },
            ]
        ).to_excel(writer, index=False, sheet_name="symptom")

    config_path = app_paths.configs_dir / "symptom_legacy_fallback.yaml"
    config_path.write_text(
        "\n".join(
            [
                'name: "Symptom Legacy Fallback"',
                'source_sheet: "Sheet1"',
                "header:",
                '  title: "Symptom Legacy Fallback"',
                "masters:",
                '  - file: "masters/master_table.xlsx"',
                '    sheet_name: "symptom"',
                '    strategy: "lookup_rules"',
                '    target_column: "symptom"',
                '    value_column: "symptom"',
                "    matching:",
                '      order: "top_to_bottom"',
                "      first_match_wins: true",
                "      matchers:",
                '        - source: "part_name"',
                '          master: "part_name"',
                '          mode: "equals"',
                '        - source: "symptom_comment"',
                '          master: "pattern"',
                '          mode: "contains"',
                "outputs:",
                '  - sheet_name: "Detail"',
                "    columns:",
                '      - "symptom"',
            ]
        ),
        encoding="utf-8",
    )

    result = run_pipeline(
        paths=app_paths,
        source_path=source_path,
        config_path=config_path,
        log=lambda _: None,
    )

    detail_df = pd.read_excel(result.output_path, sheet_name="Detail", skiprows=3, keep_default_na=False)
    assert detail_df["symptom"].tolist() == ["BLANK", "NO_PICTURE"]
