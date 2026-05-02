from __future__ import annotations

from openpyxl import load_workbook
import pandas as pd

from app.services.output_service import write_output_workbook


def test_data_summary_sheets_use_yaml_backed_layout_and_exclude_result(tmp_path):
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    output_path = outputs_dir / "report.xlsx"

    result_df = pd.DataFrame([{"notification": "N1", "section": "GQS"}])
    data1_df = pd.DataFrame(
        [
            {
                "Section": "GQS",
                "Part Name": "PANEL",
                "Labor": "=SUMIFS(result!$S:$S,result!$W:$W,\"GQS\")",
                "Transportation": 2,
                "Parts": 3,
                "Total": 4,
                "Count": 1,
                "_row_type": "data",
            },
            {
                "Section": "GQS",
                "Part Name": "MAIN_UNIT",
                "Labor": 5,
                "Transportation": 6,
                "Parts": 7,
                "Total": 8,
                "Count": 2,
                "_row_type": "data",
            },
            {
                "Section": "GQS Total",
                "Part Name": "",
                "Labor": 5,
                "Transportation": 8,
                "Parts": 10,
                "Total": 12,
                "Count": 3,
                "_row_type": "subtotal",
            },
            {
                "Section": "Grand Total",
                "Part Name": "",
                "Labor": 5,
                "Transportation": 8,
                "Parts": 10,
                "Total": 12,
                "Count": 3,
                "_row_type": "grand_total",
            },
        ]
    )
    data6_df = pd.DataFrame(
        [
            {"part_name": "PANEL", "symptom": "NO POWER", "32": 1, "Grand Total": 1},
            {"part_name": "PANEL Total", "symptom": "", "32": 1, "Grand Total": 1},
        ]
    )

    write_output_workbook(
        output_sheets={"result": result_df, "data1": data1_df, "data6": data6_df},
        output_path=output_path,
        outputs_dir=outputs_dir,
        report_title="Job Summary Result",
        header_cfg={},
        styling_cfg={"font": "Calibri", "zebra_color": "F2F2F2", "subtotal_color": "FFF2CC"},
        source_df=result_df,
        sheet_layouts={"result": "standard", "data1": "plain", "data6": "plain"},
        sheet_options={
            "data1": {
                "title": "PART COST (3 Worst)",
                "subtitle": "Part Category: PANEL | MAIN_UNIT | POWER_UNIT | OTHER",
                "column_width": 13.0,
            },
            "data6": {
                "title": "PANEL SYMPTOM INCH MATRIX",
                "subtitle": "Panel symptom matrix by inch",
                "column_width": 13.0,
            },
        },
    )

    workbook = load_workbook(output_path, data_only=False)
    data1 = workbook["data1"]
    data6 = workbook["data6"]
    result = workbook["result"]

    assert data1["A1"].value == "PART COST (3 Worst)"
    assert data1["A2"].value == "Part Category: PANEL | MAIN_UNIT | POWER_UNIT | OTHER"
    assert data1["A4"].value == "Section"
    assert data1["G4"].value == "Count"
    assert data1["A4"].fill.fgColor.rgb == "00E4DFEC"
    assert data1["F4"].fill.fgColor.rgb == "00E4DFEC"
    assert data1.auto_filter.ref is None
    assert data1["A5"].value == "GQS"
    assert data1["C5"].value == '=SUMIFS(result!$S:$S,result!$W:$W,"GQS")'
    assert data1.freeze_panes == "B5"
    assert data1.sheet_view.showGridLines is False
    assert data1.column_dimensions["A"].width == 13.0
    assert data1.column_dimensions["G"].width == 13.0
    assert "A1:G1" in {str(merged_range) for merged_range in data1.merged_cells.ranges}
    assert "A2:G2" in {str(merged_range) for merged_range in data1.merged_cells.ranges}
    assert "A5:A6" in {str(merged_range) for merged_range in data1.merged_cells.ranges}
    assert data1["C5"].number_format == "#,##0"
    assert data1["A7"].fill.fgColor.rgb == "00FFF2CC"
    assert data1["A8"].fill.fgColor.rgb == "00C6EFCE"

    assert data6["A1"].value == "PANEL SYMPTOM INCH MATRIX"
    assert data6["A4"].value == "part_name"
    assert data6.freeze_panes == "B5"
    assert data6.sheet_view.showGridLines is False
    assert data6.auto_filter.ref is None
    assert data6.column_dimensions["D"].width == 13.0
    assert "A1:D1" in {str(merged_range) for merged_range in data6.merged_cells.ranges}

    assert result["A1"].value == "Job Summary Result"
    assert result["A4"].value == "notification"
    assert result.freeze_panes == "A5"
    assert result.sheet_view.showGridLines is None
