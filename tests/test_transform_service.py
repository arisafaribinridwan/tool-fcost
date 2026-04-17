from __future__ import annotations

import pandas as pd
import pytest

from app.services.transform_service import apply_transform_steps, build_output_sheets


def test_apply_transform_steps_supports_optional_filter_formula_and_conditional():
    source_df = pd.DataFrame(
        [
            {"kategori": "Cat 1", "qty": 10, "harga": 10000},
            {"kategori": "Cat 2", "qty": 5, "harga": 8000},
            {"kategori": "Cat 3", "qty": 2, "harga": 12000},
        ]
    )

    logs: list[str] = []
    result_df = apply_transform_steps(
        data_df=source_df,
        transforms_cfg=[
            {"type": "ensure_optional_columns", "columns": {"catatan": ""}},
            {"type": "filter_rows", "column": "qty", "gte": 5},
            {
                "type": "formula",
                "target": "total",
                "operation": "multiply",
                "operands": [
                    {"column": "qty"},
                    {"column": "harga"},
                ],
            },
            {
                "type": "conditional",
                "target": "segment",
                "cases": [
                    {
                        "when": {"column": "qty", "gte": 10},
                        "value": "besar",
                    },
                    {
                        "when": {"column": "kategori", "equals": "Cat 2"},
                        "value": "cat_2",
                    },
                ],
                "default": "lain",
            },
        ],
        log=logs.append,
    )

    assert result_df["qty"].tolist() == [10, 5]
    assert result_df["catatan"].tolist() == ["", ""]
    assert result_df["total"].tolist() == [100000, 40000]
    assert result_df["segment"].tolist() == ["besar", "cat_2"]
    assert any("kolom opsional" in item for item in logs)
    assert any("Filter 'qty'" in item for item in logs)


def test_apply_transform_steps_raises_clear_error_for_divide_by_zero():
    source_df = pd.DataFrame(
        [
            {"qty": 10, "divider": 2},
            {"qty": 8, "divider": 0},
        ]
    )

    with pytest.raises(ValueError, match="pembagi bernilai 0"):
        apply_transform_steps(
            data_df=source_df,
            transforms_cfg=[
                {
                    "type": "formula",
                    "target": "hasil",
                    "operation": "divide",
                    "operands": [
                        {"column": "qty"},
                        {"column": "divider"},
                    ],
                }
            ],
            log=lambda _: None,
        )


def test_build_output_sheets_supports_group_by_output():
    data_df = pd.DataFrame(
        [
            {"segment": "besar", "qty": 10, "total": 100000},
            {"segment": "cat_2", "qty": 5, "total": 40000},
            {"segment": "besar", "qty": 3, "total": 30000},
        ]
    )

    result = build_output_sheets(
        outputs_cfg=[
            {
                "sheet_name": "Summary",
                "group_by": {
                    "by": "segment",
                    "aggregations": {
                        "qty": "sum",
                        "total": "sum",
                    },
                },
                "columns": ["segment", "qty", "total"],
            }
        ],
        data_df=data_df,
        log=lambda _: None,
    )

    summary_df = result["Summary"]
    assert list(summary_df.columns) == ["segment", "qty", "total"]
    assert summary_df.loc[summary_df["segment"] == "besar", "qty"].iloc[0] == 13
    assert summary_df.loc[summary_df["segment"] == "besar", "total"].iloc[0] == 130000
    assert summary_df.loc[summary_df["segment"] == "cat_2", "qty"].iloc[0] == 5
