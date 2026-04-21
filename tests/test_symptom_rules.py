from __future__ import annotations

import pandas as pd
import pytest

from app.services.transform_service import match_symptom_rule, prepare_symptom_rule_table
from app.services.pipeline_service import run_pipeline
from app.services.pipeline_types import PipelineError


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
