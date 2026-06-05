from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
import re
from time import perf_counter

import pandas as pd

from app import AppPaths
from app.services.config_service import is_step_recipe_payload, load_config_payload
from app.services.output_service import write_output_workbook
from app.services.pipeline_types import PipelineError, PipelineResult, PipelineStepStatus
from app.services.recipe_service import execute_step_recipe
from app.services.target_workbook_update_service import update_target_workbooks_by_model_series
from app.services.source_service import (
    copy_source_to_uploads,
    load_source_dataframe,
    validate_required_source_columns,
    validate_source_file,
)
from app.services.transform_service import (
    apply_master_lookups,
    apply_transform_steps,
    build_output_sheets,
)


LogFn = Callable[[str], None]
ProgressFn = Callable[[PipelineStepStatus], None]

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def _build_sheet_options(config: dict) -> dict[str, dict]:
    sheet_options: dict[str, dict] = {}
    outputs = config.get("outputs")
    if not isinstance(outputs, list):
        return sheet_options

    for item in outputs:
        if not isinstance(item, dict):
            continue
        sheet_name = item.get("sheet_name")
        summary_cfg = item.get("summary")
        if not isinstance(sheet_name, str) or not isinstance(summary_cfg, dict):
            continue

        options: dict[str, object] = {}
        for key in ("title", "subtitle", "column_width", "freeze_pane"):
            value = summary_cfg.get(key)
            if value is not None:
                options[key] = value
        sheet_options[sheet_name] = options

    return sheet_options


def _safe_filename(raw_name: str) -> str:
    normalized = _UNSAFE_FILENAME_CHARS.sub("_", raw_name.strip())
    normalized = normalized.strip("._")
    return normalized or "report"


def _get_target_update_config(config: dict) -> dict | None:
    target_cfg = config.get("target_update")
    if not isinstance(target_cfg, dict):
        return None
    if target_cfg.get("enabled") is not True:
        return None
    return target_cfg


def _build_update_summary_df(update_results: list) -> pd.DataFrame:
    columns = ["file_name", "model_series", "status", "rows_written", "reason"]
    return pd.DataFrame(
        [
            {
                "file_name": item.file_name,
                "model_series": item.model_series_key,
                "status": item.status,
                "rows_written": item.rows_written,
                "reason": item.reason,
            }
            for item in update_results
        ],
        columns=columns,
    )


def run_pipeline(
    *,
    paths: AppPaths,
    source_path: Path,
    config_path: Path,
    log: LogFn,
    progress: ProgressFn | None = None,
    period_text_override: str | None = None,
    period_keydate_override: str | None = None,
    output_name_override: str | None = None,
    target_folder_path: Path | None = None,
) -> PipelineResult:
    started_at = perf_counter()

    def emit_progress(step_key: str, step_label: str, state: str, detail: str = "") -> None:
        if progress is None:
            return
        progress(
            PipelineStepStatus(
                step_key=step_key,
                step_label=step_label,
                state=state,
                detail=detail,
            )
        )

    source_errors = validate_source_file(source_path)
    if source_errors:
        raise PipelineError("; ".join(source_errors))

    emit_progress("load_config", "Load config", "running", config_path.name)
    log(f"Load config: {config_path.name}")
    try:
        config = load_config_payload(config_path)
    except ValueError as exc:
        raise PipelineError(str(exc)) from exc
    emit_progress("load_config", "Load config", "done", config_path.name)

    emit_progress("copy_source", "Copy source", "running", source_path.name)
    source_resolved = source_path.resolve()
    uploads_resolved = paths.uploads_dir.resolve()
    upload_resolved = (paths.project_root / "upload").resolve()

    in_uploads_dir = source_resolved.is_relative_to(uploads_resolved)
    in_upload_dir = source_resolved.is_relative_to(upload_resolved)

    if in_uploads_dir or in_upload_dir:
        source_copy = source_resolved
        log("Source sudah berada di folder upload(s), copy source dilewati.")
    else:
        log("Salin source ke folder uploads/")
        try:
            source_copy = copy_source_to_uploads(source_path, paths.uploads_dir)
        except OSError as exc:
            raise PipelineError(f"Gagal menyalin source ke uploads/: {exc}") from exc
    emit_progress("copy_source", "Copy source", "done", source_copy.name)

    sheet_layouts: dict[str, str] | None = None

    if is_step_recipe_payload(config):
        emit_progress("read_source", "Read source", "running", source_path.name)
        log(f"Read source workbook: {source_path.name}")
        try:
            recipe_result = execute_step_recipe(
                source_path=source_path,
                recipe_cfg=config,
                project_root=paths.project_root,
                masters_dir=paths.masters_dir,
                log=log,
                runtime_values={"period_keydate": period_keydate_override},
            )
        except ValueError as exc:
            raise PipelineError(str(exc)) from exc
        source_df = recipe_result.source_df_for_header
        output_sheets = recipe_result.output_sheets
        sheet_layouts = recipe_result.sheet_layouts
        emit_progress("read_source", "Read source", "done", f"{len(source_df)} baris")
    else:
        source_sheet = config["source_sheet"]
        emit_progress("read_source", "Read source", "running", source_path.name)
        log(f"Read source: {source_path.name}")
        try:
            raw_header_row = config.get("source_header_row")
            header_row = (
                raw_header_row
                if isinstance(raw_header_row, int) and raw_header_row > 0
                else None
            )
            source_df = load_source_dataframe(
                source_path,
                source_sheet=str(source_sheet) if source_path.suffix.lower() == ".xlsx" else None,
                header_row=header_row,
            )
        except ValueError as exc:
            raise PipelineError(str(exc)) from exc
        emit_progress("read_source", "Read source", "done", f"{len(source_df)} baris")

        try:
            validate_required_source_columns(
                source_df,
                config.get("required_source_columns"),
            )
        except ValueError as exc:
            raise PipelineError(str(exc)) from exc

        if source_df.empty:
            log("Warning: source kosong, output akan tetap dibuat.")
        else:
            log(f"Source loaded: {len(source_df)} baris, {len(source_df.columns)} kolom.")

        emit_progress("load_master", "Load master", "running")
        log("Load master & apply lookup")
        try:
            transformed_df = apply_master_lookups(
                source_df=source_df,
                masters_config=config.get("masters"),
                project_root=paths.project_root,
                masters_dir=paths.masters_dir,
                log=log,
            )
        except ValueError as exc:
            raise PipelineError(str(exc)) from exc
        emit_progress("load_master", "Load master", "done")

        emit_progress("transform", "Transform", "running")
        log("Apply transform rules")
        try:
            transformed_df = apply_transform_steps(
                data_df=transformed_df,
                transforms_cfg=config.get("transforms"),
                log=log,
            )
        except ValueError as exc:
            raise PipelineError(str(exc)) from exc
        emit_progress("transform", "Transform", "done")

        emit_progress("build_output", "Build output", "running")
        log("Build output sheets")
        try:
            output_sheets = build_output_sheets(config["outputs"], transformed_df, log)
        except ValueError as exc:
            raise PipelineError(str(exc)) from exc
        emit_progress("build_output", "Build output", "done", f"{len(output_sheets)} sheet")

    target_update_cfg = _get_target_update_config(config)
    if target_update_cfg is not None:
        if target_folder_path is None:
            raise PipelineError("Folder tujuan wajib diisi untuk job ini.")

        match_column = str(target_update_cfg.get("match_column", "model_series"))
        target_sheet_name = str(target_update_cfg.get("sheet_name", "raw"))
        source_filter_cfg = target_update_cfg.get("source_filter")
        filter_column = None
        filter_value = None
        if isinstance(source_filter_cfg, dict):
            raw_filter_column = source_filter_cfg.get("column")
            if isinstance(raw_filter_column, str) and raw_filter_column.strip():
                filter_column = raw_filter_column.strip()
                filter_value = source_filter_cfg.get("equals")

        duplicate_key_columns: tuple[str, ...] = ()
        raw_duplicate_key_columns = target_update_cfg.get("duplicate_key_columns")
        if isinstance(raw_duplicate_key_columns, list):
            duplicate_key_columns = tuple(
                str(column).strip()
                for column in raw_duplicate_key_columns
                if isinstance(column, str) and column.strip()
            )

        new_row_color: str | None = None
        raw_new_row_color = target_update_cfg.get("new_row_color")
        if isinstance(raw_new_row_color, str) and raw_new_row_color.strip():
            new_row_color = raw_new_row_color.strip()

        filename_order_prefix_cfg = target_update_cfg.get("filename_order_prefix")
        strip_order_prefix = (
            isinstance(filename_order_prefix_cfg, dict)
            and filename_order_prefix_cfg.get("enabled") is True
        )

        table_name: str | None = None
        create_table_if_missing = False
        excel_table_cfg = target_update_cfg.get("excel_table")
        if isinstance(excel_table_cfg, dict) and excel_table_cfg.get("enabled") is True:
            raw_table_name = excel_table_cfg.get("name", "RawData")
            if isinstance(raw_table_name, str) and raw_table_name.strip():
                table_name = raw_table_name.strip()
            else:
                table_name = "RawData"
            create_table_if_missing = excel_table_cfg.get("create_if_missing") is True

        emit_progress("update_targets", "Update targets", "running", target_folder_path.name)
        log(f"Scan folder tujuan: {target_folder_path}")
        try:
            update_results = update_target_workbooks_by_model_series(
                data_df=source_df,
                target_dir=target_folder_path,
                match_column=match_column,
                target_sheet_name=target_sheet_name,
                filter_column=filter_column,
                filter_value=filter_value,
                duplicate_key_columns=duplicate_key_columns,
                new_row_color=new_row_color,
                strip_order_prefix=strip_order_prefix,
                table_name=table_name,
                create_table_if_missing=create_table_if_missing,
            )
        except ValueError as exc:
            raise PipelineError(str(exc)) from exc

        updated_count = 0
        skipped_count = 0
        failed_count = 0
        for item in update_results:
            if item.status == "updated":
                updated_count += 1
            elif item.status == "failed":
                failed_count += 1
            else:
                skipped_count += 1
            detail = f"[{item.status}] {item.file_name}"
            if item.rows_written > 0:
                detail += f" ({item.rows_written} baris)"
            if item.reason:
                detail += f" - {item.reason}"
            log(detail)

        emit_progress(
            "update_targets",
            "Update targets",
            "done",
            f"updated={updated_count}, skipped={skipped_count}, failed={failed_count}",
        )
        output_sheets["update_summary"] = _build_update_summary_df(update_results)

    config_name = str(config.get("name", config_path.stem))
    output_base_name = output_name_override or config_name
    sheet_options = _build_sheet_options(config)
    output_file_name = (
        f"{_safe_filename(output_base_name)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    )
    output_path = paths.outputs_dir / output_file_name

    emit_progress("write_output", "Write output", "running", output_path.name)
    log("Write workbook (.xlsx)")
    try:
        write_output_workbook(
            output_sheets=output_sheets,
            output_path=output_path,
            outputs_dir=paths.outputs_dir,
            report_title=str(config.get("header", {}).get("title", config_name)),
            header_cfg=config.get("header", {}),
            styling_cfg=config.get("styling", {}),
            source_df=source_df,
            period_text_override=period_text_override,
            sheet_layouts=sheet_layouts,
            sheet_options=sheet_options,
        )
    except Exception as exc:
        raise PipelineError(f"Gagal menulis file output: {exc}") from exc
    emit_progress("write_output", "Write output", "done", output_path.name)

    log(f"Selesai. Output: {output_path.name}")
    return PipelineResult(
        output_path=output_path,
        source_copy_path=source_copy,
        sheets_written=len(output_sheets),
        duration_ms=max(1, int(round((perf_counter() - started_at) * 1000))),
    )
